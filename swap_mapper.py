def my_swap_mapper(circuit_graph, coupling_graph):
    gates = circuit_graph.serial_layers()
    qubits = coupling_graph.get_qubits()
    layout = {qubit : qubit for qubit in qubits}

    end_nodes = []
    count = 0
    while gates[count]["partition"]!=[]:
        count += 1
    end_nodes = gates[count:]
    gates = gates[:count]

    qasm_string = ""

    while len(gates) > 0:
        qasm_string += execute_possible_1q_gates(gates, coupling_graph, layout)
        if len(gates) == 0:
            break
        upcoming_cnots=get_upcoming_cnots(gates, len(qubits))
        executed = False
        while not executed:
            executed, qasm, gate = execute_possible_cx(upcoming_cnots, coupling_graph, layout)
            if executed:
                qasm_string += qasm
                gates.remove(gate)
            else:
                best_swap, best_layout, dest_dist = get_best_swap(upcoming_cnots, coupling_graph, layout)
                swap_1_physical = best_swap[0]
                swap_2_physical = best_swap[1]
                qasm_string += "swap %s[%d],%s[%d]; " % (swap_1_physical[0],
                                                         swap_1_physical[1],
                                                         swap_2_physical[0],
                                                         swap_2_physical[1])

                layout = best_layout


    swap_decl = "gate swap a,b { cx a,b; cx b,a; cx a,b;}"
    end_nodes_qasm = ""
    for node in end_nodes:
        end_nodes_qasm += node["graph"].qasm(no_decls=True, aliases = layout)
    qasm_string = circuit_graph.qasm(decls_only=True)+swap_decl+qasm_string+end_nodes_qasm

    #print(qasm_string)
    basis = "u1,u2,u3,cx,id,swap"
    ast = Qasm(data=qasm_string).parse()
    u = unroll.Unroller(ast, unroll.DAGBackend(basis.split(",")))
    print("Done.")
    return u.execute(), layout

def execute_possible_cx(upcoming_cnots, coupling, layout):
    for gate in upcoming_cnots:
        q1, q2 = qubits_from_cnot(gate)
        if coupling.distance(layout[q1], layout[q2]) == 1:
            qasm = gate["graph"].qasm(no_decls=True, aliases = layout)
            return True, qasm, gate
    return False, None, None

def execute_possible_1q_gates(gates, coupling, layout):
    qasm = ""
    blocked_qubits = []
    i = 0
    while len(blocked_qubits) < len(coupling.get_qubits()) and i < len(gates):
        gate = gates[i]
        if gate["partition"] == [] or len(gate["partition"][0]) < 2:
            if gate["partition"] == [] or not gate["partition"][0][0] in blocked_qubits:
                qasm += gate["graph"].qasm(no_decls=True, aliases = layout)
                gates.remove(gate)
                i -= 1
            elif is_gate_free(gate, gates):
                print("smth wrong")
        else:
            q1, q2 = qubits_from_cnot(gate)
            if not q1 in blocked_qubits:
                blocked_qubits.append(q1)
            if not q2 in blocked_qubits:
                blocked_qubits.append(q2)
        i += 1
    return qasm

def is_gate_free(gate, gates):
    gate_qubits = gate["partition"][0]
    for g in gates:
        if g == gate:
            return True
        for qubit in g["partition"][0]:
            if qubit in gate_qubits:
                return False


def get_best_swap(upcoming_cnots, coupling, layout):
    current_dist = calculate_total_distance(upcoming_cnots, coupling, layout)
    best_dist = current_dist
    best_layout = layout
    best_swap = None

    for edge in coupling.get_edges():
        trial_layout = deepcopy(layout)
        trial_layout[reverse_layout_lookup(layout, edge[0])] = edge[1]
        trial_layout[reverse_layout_lookup(layout, edge[1])] = edge[0]
        trial_dist = calculate_total_distance(upcoming_cnots, coupling, trial_layout)
        if trial_dist < best_dist:
            best_dist = trial_dist
            best_layout = trial_layout
            best_swap = edge

    if best_swap == None:
        print("No swap found")
        print(upcoming_cnots)
        print(layout)
    return best_swap, best_layout, best_dist
