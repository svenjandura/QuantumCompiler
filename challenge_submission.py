# -*- coding: utf-8 -*-

#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

"""
---------------> please fill out this section <---------------

Your Name : Sven Jandura

Your E-Mail : sven.jandura@physik.uni-muenchen.de

Description of the algorithm :

- How does the algorithm work?
- Did you use any previously published schemes? Cite relevant papers.
- What packages did you use in your code and for what part of the algorithm?
- How general is your approach? Does it work for arbitrary coupling layouts (qubit number)?
- Are there known situations when the algorithm fails?


---------------> please fill out this section <---------------
"""

# Include any Python modules needed for your implementation here

from copy import deepcopy
import random
from qiskit.qasm import Qasm
from qiskit.mapper import direction_mapper, cx_cancellation, optimize_1q_gates, Coupling
from qiskit import qasm, unroll


# The following class is the input and output circuit representation for a
# QISKit compiler
from qiskit.dagcircuit import DAGCircuit

WIDTH = 4
DEPTH = 4

def compiler_function(dag_circuit, coupling_map=None, gate_costs=None):
    """
    Modify a DAGCircuit based on a gate cost function.

    Instructions:
        Your submission involves filling in the implementation
        of this function. The function takes as input a DAGCircuit
        object, which can be generated from a QASM file by using the
        function 'qasm_to_dag_circuit' from the included
        'submission_evaluation.py' module. For more information
        on the DAGCircuit object see the or QISKit documentation
        (eg. 'help(DAGCircuit)').

    Args:
        dag_circuit (DAGCircuit): DAGCircuit object to be compiled.
        coupling_circuit (list): Coupling map for device topology.
                                 A coupling map of None corresponds an
                                 all-to-all connected topology.
        gate_costs (dict) : dictionary of gate names and costs.

    Returns:
        A modified DAGCircuit object that satisfies an input coupling_map
        and has as low a gate_cost as possible.
    """
    # I only modified the swap mapper

    coupling = Coupling(coupling_map)
    # Add swaps, so that we only use cnots that are allowed by the coupling map
    compiled_dag = my_swap_mapper(deepcopy(dag_circuit), coupling, speedup = False)
    # Expand swaps
    basis_gates = "u1,u2,u3,cx,id"  # QE target basis
    program_node_circuit = qasm.Qasm(data=compiled_dag.qasm()).parse()
    unroller_circuit = unroll.Unroller(program_node_circuit,
                                       unroll.DAGBackend(
                                           basis_gates.split(",")))
    compiled_dag = unroller_circuit.execute()
    # Change cx directions
    compiled_dag = direction_mapper(compiled_dag, coupling)
    # Simplify cx gates
    cx_cancellation(compiled_dag)
    # Simplify single qubit gates
    compiled_dag = optimize_1q_gates(compiled_dag)

    # Return the compiled dag circuit
    return compiled_dag


def my_swap_mapper(circuit_graph, coupling, speedup = False, initial_layout = None):
    """ TODO: add description"""
    gates = read_gates(circuit_graph)
    qubits = coupling.get_qubits()
    if initial_layout == None:
        # We start with a trivial layout, no significat improvement, especially
        # for large circuits, could be achived by optimizing the initial layout
        initial_layout = {qubit : qubit for qubit in qubits}
    qasm_string = ""
    # Set the depth we are actually going to use. If speedup is true, use
    # a depth one smaller than usually
    used_depth = DEPTH
    if speedup:
        used_depth -= 1
    # This value gives a good compromise between speed and final score
    max_gates = 50 + 10 * len(coupling.get_qubits())

    # Build the initial tree
    node = build_tree(None, gates, coupling, initial_layout, used_depth, width = WIDTH, max_gates = max_gates)
    # Now actually start compiling
    run = True
    while run:
        # if no gates are left, stop ater this iteration
        run = node["remaining_gates"] != []
        # add the swap of the top node to the qasm string
        if node["swap"] != None:
            edge = node["swap"]
            qasm_string += "swap %s[%d],%s[%d]; " % (edge[0][0],
                                                    edge[0][1],
                                                    edge[1][0],
                                                    edge[1][1])
        # add all executed gates to the qasm string
        for gate in node["executed_gates"]:
            qasm_string += gate_to_qasm(gate, node["layout"])
        last_layout = node["layout"]
        # Go one step deeper into the tree. For this, choose the child with the
        # best score. This is the child whose score matches the score of the node
        for n in node["children"]:
            if n["score"] == node["score"]:
                node = n
                break
        # append one layer to the tree
        update_tree(node, coupling, width=WIDTH, max_gates = max_gates)

    # complete the qasm string
    swap_decl = "gate swap a,b { cx a,b; cx b,a; cx a,b;}"
    end_str = "barrier "    # end of the qasm code
    for q in coupling.get_qubits():
        end_str += "%s[%d]," % q
    end_str = end_str[:-1]+";\n"
    # Assume that each qubit q[i] gets measured to c[i]
    for q in circuit_graph.get_qubits():
        end_str += qubit_to_measure_string(q, last_layout, q[1])
    qasm_string = circuit_graph.qasm(decls_only=True)+swap_decl+qasm_string+end_str
    # convert qasm to a dag circuit
    basis = "u1,u2,u3,cx,id,swap"
    ast = Qasm(data=qasm_string).parse()
    u = unroll.Unroller(ast, unroll.DAGBackend(basis.split(",")))
    return u.execute()

def build_tree(swap, gates, coupling, layout, depth, width = WIDTH, max_gates = 1000000, cnot_count = 0):
    """
    Searched through multiple swaps recursively and builds a tree of all swaps
    searched

    Args:
        swap(pair of qubits): The swap the should correspond to the retured node.
                              Can be None if we are at the root of the tree.
        gates(list)         : All gates that still have to be executed
        coupling(Couling)   : coupling for device topology.
        layout(dict)        : layout after(!) swap has been applied
        depth(int)          : The depth (not including this node), to which the
                              tree should be build
        width(int)          : Maximum number of swaps to be searched through at
                              each node
        max_gates(int)      : Maximum number of gates considered
        cnot_count(int)     : The number of cnots executed so far

    Returns:
        the top node of a tree containing all swaps searched.
        A node is a dictionary of the form:
            "swap"            : The swap searched in this node
            "layout"          : The layout after the swap has been applied
            "executed_gates"  : All gates that can be executed in accordance with
                                the coupling after the swaps
            "remaining_gates" : All gates that still could not be executed
            "cnots"           : Number of total cnot executed after this node
            "children"        : List of nodes searched through starting from this
                                node. Is None if depth = 0
            "score"           : score of the node. If the node has children, it
                                is the maximum of the children score. Otherwise
                                it is evatuated from cnots and layout
    """
    node = {}
    node["swap"] = swap
    node["layout"] = layout
    executed_gates, remaining_gates, cnots = execute_free_gates(gates, coupling, layout)
    node["executed_gates"] = executed_gates
    node["remaining_gates"] = remaining_gates
    node["cnots"] = cnots + cnot_count

    # if we are at the end of the tree, score the node
    if depth == 0:
        upcoming_cnots = get_upcoming_cnots(node["remaining_gates"], len(coupling.get_qubits()))
        dist = calculate_total_distance(upcoming_cnots, coupling, layout)
        # We score using the number of cnots that can be executed and use the
        # current distance as tie-breaker
        score = node["cnots"] - 0.01 * dist
        node["score"] = score
        node["children"] = None
        return node

    # if we are not at the end of the tree, search through swaps after this swap
    node["score"], node["children"] = search_swaps(node, coupling, depth, width)
    return node

def update_tree(node, coupling, width = WIDTH, max_gates = 1000000):
    """
    Updated a gived tree by adding one layer after the last one

    Args:
        node      : The node to append
        coupling  : couplig for device topology
        width     : Number of swaps searched for each node
        max_gates : maximum number of gates considered

    Returns:
        Nothing
    """
    # If the node has no children, build them to depth 1
    if node["children"] == None:
        node["score"], node["children"] = search_swaps(node, coupling, 1, width, max_gates = max_gates)
    # Else update all the children and the score of this node
    else:
        node["score"] = -10000
        for n in node["children"]:
            update_tree(n, coupling, width=width)
            if n["score"] > node["score"]:
                node["score"] = n["score"]

def search_swaps(node, coupling, depth, width=WIDTH, max_gates = 1000000):
    """
    Searches the most promising swaps and builds the nodes corresponding to
    them.

    Args:
        node      : The start node containing all fields exept "children" and "score"
        coupling  : coupling for device topology
        depth     : The search depth for each swap
        width     : The number of swaps search through
        max_gates : the maximum number of gates considered

    Returns:
        score, children
        score: score of this node, is the maximum of the scores of the children
        children: all children of this node, each containing one swap searched
    """

    #calculate the current distance
    upcoming_cnots = get_upcoming_cnots(node["remaining_gates"], len(coupling.get_qubits()), max_gates = max_gates)
    current_dist = calculate_total_distance(upcoming_cnots, coupling, node["layout"])
    # The distance after a swap can differ by at most two. In this dict we group
    # the swap by this difference
    swaps_by_difference = {}
    # A swap is just and edge in the coupling
    for edge in coupling.get_edges():
        trial_layout = deepcopy(node["layout"])
        trial_layout[reverse_layout_lookup(node["layout"], edge[0])] = edge[1]
        trial_layout[reverse_layout_lookup(node["layout"], edge[1])] = edge[0]
        trial_dist = calculate_total_distance(upcoming_cnots, coupling, trial_layout)
        diff = current_dist - trial_dist
        if diff not in swaps_by_difference:
            swaps_by_difference[diff] = []
        # For each swap also record the distance and the layout, so we don't have to
        # calculate it again
        swaps_by_difference[diff].append({"edge": edge, "dist": trial_dist, "layout": trial_layout})
        # If we have already found enough swaps with the maximum difference in
        # distance, we can stop searching
        if 2 in swaps_by_difference and len(swaps_by_difference[2]) == width:
            break

    # Now we determine the swaps that we are going to explore
    swaps_to_explore = []
    d = 2
    for i in range(min(width, len(coupling.get_edges()))):
        while d not in swaps_by_difference or swaps_by_difference[d] == []:
            d -= 1
        r = random.randrange(len(swaps_by_difference[d]))
        swaps_to_explore.append(swaps_by_difference[d][r])
        del swaps_by_difference[d][r]

    # Init the score
    score = -10000
    children = []
    for i in range(min(width, len(swaps_to_explore))):
        n = build_tree( swaps_to_explore[i]["edge"],
                        node["remaining_gates"],
                        coupling, swaps_to_explore[i]["layout"],
                        depth-1,
                        width=width,
                        max_gates = max_gates,
                        cnot_count = node["cnots"])
        children.append(n)
        if n["score"] > score:
            score = n["score"]
    return score, children


def execute_free_gates(gates, coupling, layout, max_gates = 10000000):
    """
    Finds all gates that can be executed with the current layout

    Args:
        gates(list)        : All still remaining gates
        coupling(Coupling) : coupling for device topology
        layout(dict)       : layout of the qubits
        max_gates          : maximum number of gates to be searched through

    Returns:
        executed_gates, remaining_gates, cnots
        executed_gates(list)  : gates that can be executed
        remaining_gates(list) : gates that cannot be executed
        cnots(int)            : number of cnots in executed_gates
    """
    # qubits we can't use anymore, because we could not execute a cnot
    # containing them
    blocked_qubits = []
    cnot_count = 0
    executed_gates = []
    remaining_gates = []

    # the gates we are goning to seach through
    interesting_gates = []
    # the gates that are to far away, so we ignore them
    ignored_gates = []
    if len(gates)<=max_gates:
        interesting_gates = gates
    else:
        interesting_gates = gates[:max_gates]
        ignored_gates = gates[max_gates:]
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

def get_upcoming_cnots(gates, number_of_qubits, max_gates = 10000000):
    """
    Args:
        gates(list)      : gates to search for upcoming cnots
        number_of_qubits : number of qubits in the coupling
        max_gates        : maximum number of gates searched

    Returns: a maximal list of cnot gates such that no qubit is contained twice
             in a gate of the list and each qubit occures only in single qubit
             gates before it occures in the list
    """
    upcoming_cnots = []
    used_qubits = []
    for i in range(len(gates)):
        if i >= max_gates:
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
            # if there is at most one qubit left, we won't find another cnot
            if len(used_qubits) >= number_of_qubits - 1:
                break
    return upcoming_cnots

def reverse_layout_lookup(layout, qubit):
    """ Returns a qubit q such that layout[q] = qubit"""
    for q in layout:
        if layout[q]==qubit:
            return q

def calculate_total_distance(gates, coupling, layout):
    """ Returns the sum of all the distances of two qubits in a cnot in gates
        accordingto the layout and the coupling"""
    dist = 0
    for gate in gates:
        if len(gate["qubits"]) == 2:
            q1, q2 = qubits_from_cnot(gate)
            dist += coupling.distance(layout[q1], layout[q2])
    return dist

def qubits_from_cnot(gate):
    return gate["qubits"][0], gate["qubits"][1]

def read_gates(circuit):
    """
    Reads all gates from the circuit. We do not use circuit.serial_layers()
    because it is a lot slower and memory intensiv than this custom function.
    This function should be improved to read more general circuits than those
    provided in the challenge.

    Args:
        circuit(DAGCircuit): The DAGCircuit object to read the gates from

    Returns:
        A list of all gates in the circuit in an order such that, executed in
        that order, they yield a circuit equivalent to the original circuit.
        A gate is a dictionary with the fields
            "qasm"  : The qasm instruction without the qubits it is applied to
            "qubits": List of qubits the gate is applied to. Each qubit is in
                      the form (Register, Index)
    """
    ignored_lines = 15  #The first 15 lines are declarations, ignore them
    gates = []
    lines = circuit.qasm().splitlines()
    l = ignored_lines
    while True:
        if(lines[l][:7]=="barrier"):    #We assume there are no gates after the first barrier
            break
        line_split = lines[l].split(" ")
        qubit_split = line_split[1][:-1].split(",")
        g = { "qasm"  : line_split[0],
              "qubits": [string_to_qubit(q) for q in qubit_split] }
        gates.append(g)
        l += 1
    return gates

def string_to_qubit(qubit_string):
    """ Converts a string of the form '<register>[<index>]' to the pair
    (register, index)"""
    splits = qubit_string.split("[")
    return (splits[0], int(splits[1][:-1]))

def gate_to_qasm(gate, layout):
    """
    Converts a gate to a qasm string using the give layout

    Args:
        gate(dict)  : a gate in the form returned by read_gates
        layout(dict): mapping from current qubit names to the qubit names
                      actually written

    Returns:
        the qasm instruction for this gate as string
    """
    qasm_str = gate["qasm"]
    qasm_str += " "
    for q in gate["qubits"]:
        qasm_str += "%s[%d],"%layout[q]
    qasm_str = qasm_str[:-1] + ";\n"
    return qasm_str

def qubit_to_measure_string(q, layout, c_index):
    """ Returns the instructions that measures the qubit layout[q] into the
        classical register at index c_index as qasm string"""
    return "measure %s[%d] -> c[%s];\n" % (layout[q][0], layout[q][1], c_index)
