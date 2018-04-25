from qiskit import qasm, unroll
from qiskit.dagcircuit import DAGCircuit
from qiskit.qasm import Qasm
from copy import deepcopy
import resource
import time

WIDTH = 4
DEPTH = 3
MAX_GATES = 200

def my_swap_mapper_tree(circuit_graph, coupling):
    gates = read_gates(circuit_graph)
    #gates = circuit_graph.serial_layers()
    qubits = coupling.get_qubits()
    layout = {qubit : qubit for qubit in qubits}


    """end_nodes = []
    count = 0
    while gates[count]["partition"]!=[]:
        count += 1
    end_nodes = gates[count:]
    gates = gates[:count]"""

    qasm_string = ""
    node = build_tree(None, gates, coupling, layout, DEPTH + 1, width = WIDTH)
    run = True
    while run:
        run = node["remaining_gates"] != []
        if node["swap"] != None:
            edge = node["swap"]
            qasm_string += "swap %s[%d],%s[%d]; " % (edge[0][0],
                                                    edge[0][1],
                                                    edge[1][0],
                                                    edge[1][1])
        for gate in node["executed_gates"]:
            #qasm_string += gate["graph"].qasm(no_decls = True, aliases = node["layout"])
            qasm_string += gate_to_qasm(gate, node["layout"])
        last_layout = node["layout"]
        for n in node["next_nodes"]:
            if n["score"] == node["score"]:
                node = n
                break
        update_tree(node, coupling, width=WIDTH)

    swap_decl = "gate swap a,b { cx a,b; cx b,a; cx a,b;}"
    """end_nodes_qasm = ""
    for n in end_nodes:
        end_nodes_qasm += n["graph"].qasm(no_decls=True, aliases = last_layout)"""

    end_str = "barrier "
    for q in coupling.get_qubits():
        end_str += "%s[%d]," % q
    end_str = end_str[:-1]+";\n"
    for q in circuit_graph.get_qubits():
        end_str += qubit_to_measure_string(last_layout[q], q[1])
    qasm_string = circuit_graph.qasm(decls_only=True)+swap_decl+qasm_string+end_str

    basis = "u1,u2,u3,cx,id,swap"
    ast = Qasm(data=qasm_string).parse()
    u = unroll.Unroller(ast, unroll.DAGBackend(basis.split(",")))
    return u.execute(), layout

def score_swap(gates, upcoming_cnots, coupling, layout):
    return calculate_total_distance(upcoming_cnots, coupling, layout)

def do_tree_step(node, coupling, depth, width=WIDTH):
    upcoming_cnots = get_upcoming_cnots(node["remaining_gates"], len(coupling.get_qubits()))
    ordered_swaps = []
    layout = node["layout"]
    for edge in coupling.get_edges():
        trial_layout = deepcopy(layout)
        trial_layout[reverse_layout_lookup(layout, edge[0])] = edge[1]
        trial_layout[reverse_layout_lookup(layout, edge[1])] = edge[0]
        trial_dist = score_swap(node["remaining_gates"], upcoming_cnots, coupling, trial_layout)
        position = 0
        for s in ordered_swaps:
            if s["dist"] <= trial_dist:
                position += 1
        ordered_swaps.insert(position, {"dist": trial_dist, "edge": edge, "layout": trial_layout})

    score = -10000
    next_nodes = []
    for i in range(min(width, len(ordered_swaps))):
        n = build_tree(ordered_swaps[i]["edge"], node["remaining_gates"], coupling, ordered_swaps[i]["layout"], depth-1, width=width, cnot_count = node["cnots"])
        next_nodes.append(n)
        #print("examining swap "+str(depth)+ " "+str(ordered_swaps[i]["edge"])+", score: "+str(n["score"]))
        if n["score"] > score:
            score = n["score"]
    return score, next_nodes

def build_tree(swap, gates, coupling, layout, depth, width = WIDTH, cnot_count = 0):
    node = {}
    node["swap"] = swap
    node["layout"] = layout
    executed_gates, remaining_gates, cnots = execute_free_gates(gates, coupling, layout)
    node["executed_gates"] = executed_gates
    node["remaining_gates"] = remaining_gates
    node["cnots"] = cnots + cnot_count

    if depth == 1:
        upcoming_cnots = get_upcoming_cnots(node["remaining_gates"], len(coupling.get_qubits()))
        dist = calculate_total_distance(upcoming_cnots, coupling, layout)
        score = node["cnots"] - 0.01 * dist
        node["score"] = score
        node["next_nodes"] = None
        return node

    node["score"], node["next_nodes"] = do_tree_step(node, coupling, depth, width)
    return node

def update_tree(node, coupling, width = WIDTH):
    if node["next_nodes"] == None:
        node["score"], node["next_nodes"] = do_tree_step(node, coupling, 2, width)
    else:
        node["score"] = -10000
        for n in node["next_nodes"]:
            update_tree(n, coupling, width=width)
            if n["score"] > node["score"]:
                node["score"] = n["score"]

def execute_free_gates(gates, coupling, layout):
    blocked_qubits = []
    cnot_count = 0
    executed_gates = []
    remaining_gates = []

    interesting_gates = []
    ignored_gates = []
    if len(gates)<=MAX_GATES:
        interesting_gates = gates
    else:
        interesting_gates = gates[:MAX_GATES]
        ignored_gates = gates[MAX_GATES:]
    for gate in interesting_gates:
        if len(gate["qubits"]) == 1:
            q = gate["qubits"][0]
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
    return executed_gates, remaining_gates + ignored_gates, cnot_count

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
        if i >= MAX_GATES:
            break
        gate = gates[i]
        if len(gate["qubits"])==2:
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
    return gate["qubits"][0], gate["qubits"][1]

def read_gates(circuit):
    ignored_lines = 15
    gates = []
    measurements = []
    lines = circuit.qasm().splitlines()
    l = ignored_lines
    while True:
        if(lines[l][:7]=="barrier"):
            break
        space_split = lines[l].split(" ")
        qubit_split = space_split[1][:-1].split(",")
        g = {"qasm": space_split[0], "qubits": [string_to_qubit(q) for q in qubit_split]}
        gates.append(g)
        l += 1

    return gates

def string_to_qubit(qubit_string):
    splits = qubit_string.split("[")
    return (splits[0], int(splits[1][:-1]))

def print_mem():
    memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(memory_usage)

def print_time():
    millis = int(round(time.time() * 1000))
    print(millis)

def gate_to_qasm(gate, layout):
    qasm_str = gate["qasm"]
    qasm_str += " "
    for q in gate["qubits"]:
        qasm_str += "%s[%d],"%layout[q]
    qasm_str = qasm_str[:-1] + ";\n"
    return qasm_str

def qubit_to_measure_string(q, c_num):
    return "measure %s[%d] -> c[%s];\n" % (q[0], q[1], c_num)
