# Import your solution function
from challenge_submission import compiler_function

# Import submission evaluation and scoring functions
from challenge_evaluation import evaluate, score

# Possibly useful other helper function
from challenge_evaluation import qasm_to_dag_circuit, load_coupling, get_layout

from qiskit import QuantumProgram

from pprint import pprint
import resource

# Select the simulation backend to calculate the quantum states resulting from the circuits
# On Windows platform the C++ Simulator is not yet available with pip install
backend = 'local_qiskit_simulator'

#myres = score(compiler_function, backend = backend)
#print("Your compiler scored %6.5f x better \
#and was %6.5f x faster than the QISKit reference compiler." % myres)

# Load example circuits and coupling maps

ex_nr = 1 # examples to add per qubit number. maximum is 10 with the provided circuits
test_circuit_filenames = {}

for i in range(ex_nr):
    test_circuit_filenames['circuits/random%d_n5_d5.qasm' % i] = get_layout(5)
#for i in range(ex_nr):
#    test_circuit_filenames['circuits/random%d_n16_d16.qasm' % i] = get_layout(16)
#for i in range(ex_nr):
#    test_circuit_filenames['circuits/random%d_n20_d20.qasm' % i] = get_layout(20)

##test_circuit_filenames['my_circuit.qasm']=get_layout(5)

# store circuit, coupling map pairs in test_circuits. Circuits are in qasm form.
test_circuits = {}
for filename, cmap in test_circuit_filenames.items():
    with open(filename, 'r') as infile:
        qasm = infile.read()
        test_circuits[filename] = {"qasm": qasm, "coupling_map": cmap}


"""basis_gates = 'u1,u2,u3,cx,id'
gate_costs = {'id': 0, 'u1': 0, 'measure': 0, 'reset': 0, 'barrier': 0,
                  'u2': 1, 'u3': 1, 'U': 1,
                  'cx': 10, 'CX': 10}
# Results data structure
results = {}
# Load QASM files and extract DAG circuits
for name, circuit in test_circuits.items():
    qp = QuantumProgram()
    qp.load_qasm_text(
        circuit["qasm"], name, basis_gates=basis_gates)
    circuit["dag_original"] = qasm_to_dag_circuit(circuit["qasm"], basis_gates=basis_gates)
    test_circuits[name] = circuit
    memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(memory_usage)
    compiler_function(circuit["dag_original"], circuit["coupling_map"], gate_costs)
    memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(memory_usage)
    results[name] = {}  # build empty result dict to be filled later
    #compiler_function()"""

result = evaluate(compiler_function, test_circuits, verbose=True, backend = backend)

#memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
#print(memory_usage)

pprint(result)
