from challenge_evaluation import load_coupling, evaluate
from challenge_submission import compiler_function
from pprint import pprint
import sys
import json

backend = "local_qiskit_simulator"
coupling_maps = [ ["circle_rand_q5","ibmqx2_q5","linear_rand_q5","ibmqx4_q5","linear_reg_q5"],
                  ["ibmqx3_q16", "linear_rand_q16", "rect_rand_q16", "rect_def_q16", "ibmqx5_q16"],
                  ["circle_reg_q20", "linear_rand_q20", "rect_rand_q20", "rect_def_q20", "rect_reg_q20"]]
qubit_numbers = [5,16,20]

ex_nr = 10
num = int(sys.argv[1])
qnum = num // 10
circuit_num = num % 10
circuit_name = 'circuits/random%d_n%d_d%d.qasm' % (circuit_num, qubit_numbers[qnum], qubit_numbers[qnum])
coupling = load_coupling(coupling_maps[qnum][circuit_num % len(coupling_maps[qnum])])["coupling_map"]
test_circuit_filenames = { circuit_name : coupling }

test_circuits = {}
for filename, cmap in test_circuit_filenames.items():
    with open(filename, 'r') as infile:
        qasm = infile.read()
        test_circuits[filename] = {"qasm": qasm, "coupling_map": cmap}

result = evaluate(compiler_function, test_circuits, verbose=True, backend = backend)
#pprint(result)

for circ in result:
    result[circ]['coupling_correct_optimized'] = bool(result[circ]['coupling_correct_optimized'])
    result[circ]['coupling_correct_original'] = bool(result[circ]['coupling_correct_original'])
    result[circ]['coupling_correct_reference'] = bool(result[circ]['coupling_correct_reference'])
    result[circ]['state_correct_optimized'] = bool(result[circ]['state_correct_optimized'])
#    for name in result[circ]:
#        if isinstance(result[circ][name], bool):
#            result[circ][name] = bool(result[circ][name])
print(json.dumps(result))
