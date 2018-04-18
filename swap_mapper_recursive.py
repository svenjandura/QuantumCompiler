from qiskit import qasm, unroll
from qiskit.dagcircuit import DAGCircuit
from qiskit.qasm import Qasm
from copy import deepcopy
import resource

WIDTH = 4
DEPTH = 3
MAX_GATES = 100

def my_swap_mapper_recursive(circuit_graph, coupling):
    gates = circuit_graph.serial_layers()
    qubits = coupling.get_qubits()
    layout = {qubit : qubit for qubit in qubits}

    end_nodes = []
    count = 0
    while gates[count]["partition"]!=[]:
        count += 1
    end_nodes = gates[count:]
    gates = gates[:count]

    qasm_string = ""

    executed_gates, gates, cnots = execute_free_gates(gates, coupling, layout)
    for gate in executed_gates:
        qasm_string += gate["graph"].qasm(no_decls = True, aliases = layout)

    while len(gates) > 0:
        #print(len(gates))
        score, executions, remaining = get_best_action(gates, coupling, layout, DEPTH, width = WIDTH)
        edge = executions[0][0]
        qasm_string += "swap %s[%d],%s[%d]; " % (edge[0][0],
                                                 edge[0][1],
                                                 edge[1][0],
                                                 edge[1][1])
        swaped_layout = deepcopy(layout)
        swaped_layout[reverse_layout_lookup(layout, edge[0])] = edge[1]
        swaped_layout[reverse_layout_lookup(layout, edge[1])] = edge[0]
        layout = swaped_layout

        for gate in executions[0][1]:
            qasm_string += gate["graph"].qasm(no_decls = True, aliases = layout)
            gates.remove(gate)

    swap_decl = "gate swap a,b { cx a,b; cx b,a; cx a,b;}"
    end_nodes_qasm = ""
    for node in end_nodes:
        end_nodes_qasm += node["graph"].qasm(no_decls=True, aliases = layout)
    qasm_string = circuit_graph.qasm(decls_only=True)+swap_decl+qasm_string+end_nodes_qasm

    #print(qasm_string)
    basis = "u1,u2,u3,cx,id,swap"
    ast = Qasm(data=qasm_string).parse()
    u = unroll.Unroller(ast, unroll.DAGBackend(basis.split(",")))
    #print("Done.")

    #memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    #print(memory_usage)

    return u.execute(), layout

def score_swap(gates, upcoming_cnots, coupling, layout):
    return calculate_total_distance(upcoming_cnots, coupling, layout)

def get_best_action(gates, coupling, layout, depth, width = 5, order_function = score_swap, cnot_count = 0):
    if depth == 0:
        upcoming_cnots = get_upcoming_cnots(gates, len(coupling.get_qubits()))
        dist = calculate_total_distance(upcoming_cnots, coupling, layout)
        score = cnot_count - 0.01 * dist
        return score, [], gates

    upcoming_cnots = get_upcoming_cnots(gates, len(coupling.get_qubits()))
    ordered_swaps = []

    for edge in coupling.get_edges():
        trial_layout = deepcopy(layout)
        trial_layout[reverse_layout_lookup(layout, edge[0])] = edge[1]
        trial_layout[reverse_layout_lookup(layout, edge[1])] = edge[0]
        trial_dist = order_function(gates, upcoming_cnots, coupling, trial_layout)
        position = 0
        for s in ordered_swaps:
            if s["dist"] <= trial_dist:
                position += 1
        ordered_swaps.insert(position, {"dist": trial_dist, "edge": edge, "layout": trial_layout})

    best_score = -10000
    best_executions = []
    best_remaining_gates = []
    for i in range(min(width, len(ordered_swaps))):
        trial_layout = ordered_swaps[i]["layout"]
        executed_gates, remaining_gates, cnots = execute_free_gates(gates, coupling, trial_layout)
        score, next_executions, still_remaining_gates = get_best_action(
                remaining_gates, coupling, trial_layout, depth-1, cnot_count = cnots + cnot_count)
        if score > best_score:
            best_score = score
            best_remaining_gates = still_remaining_gates
            best_executions = [(ordered_swaps[i]["edge"], executed_gates)] + next_executions
    return best_score, best_executions, best_remaining_gates

def execute_free_gates(gates, coupling, layout):
    blocked_qubits = []
    cnot_count = 0
    executed_gates = []
    remaining_gates = []
    for gate in gates:
        if len(gate["partition"][0]) == 1:
            q = gate["partition"][0][0]
            if q in blocked_qubits:
                remaining_gates.append(gate)
            else:
                executed_gates.append(gate)
        else:
            q1, q2 = qubits_from_cnot(gate)
            if q1 not in blocked_qubits and q2 not in blocked_qubits and coupling.distance(layout[q1], layout[q2]) == 1:
                executed_gates.append(gate)
                cnot_count += 1
            else:
                remaining_gates.append(gate)
                if q1 not in blocked_qubits:
                    blocked_qubits.append(q1)
                if q2 not in blocked_qubits:
                    blocked_qubits.append(q2)
    return executed_gates, remaining_gates, cnot_count

def reverse_layout_lookup(layout, qubit):
    for q in layout:
        if layout[q]==qubit:
            return q
    return None

def calculate_total_distance(gates, coupling, layout):
    dist = 0
    for gate in gates:
        q1, q2 = qubits_from_cnot(gate)
        dist += coupling.distance(layout[q1], layout[q2])
    return dist

def get_upcoming_cnots(gates, qubit_number, start=0):
    upcoming_cnots = []
    used_qubits = []
    for i in range(start, len(gates)):
        gate = gates[i]
        if (not gate["partition"]==[]) and len(gate["partition"][0])==2:
            q1,q2 = qubits_from_cnot(gate)
            if not (q1 in used_qubits or q2 in used_qubits):
                upcoming_cnots.append(gate)
            if q1 not in used_qubits:
                used_qubits.append(q1)
            if q2 not in used_qubits:
                used_qubits.append(q2)
            if len(used_qubits) >= qubit_number - 1:
                break
    return upcoming_cnots

def qubits_from_cnot(gate):
    return gate["partition"][0][0], gate["partition"][0][1]
