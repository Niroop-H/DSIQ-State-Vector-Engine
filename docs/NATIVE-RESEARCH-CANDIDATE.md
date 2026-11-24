# DSIQ State Vector Engine | Native CPU research candidate

This source package runs two native Python CPU backends for quantum circuit simulation. It includes the engine sources, example input and numerical checks. Use Linux x86-64, Python 3.12 and NumPy 2.3.5 to reproduce the tested configuration. The repository describes this software as proprietary. Public distribution terms are pending owner approval.

## Reproduce from the extracted package

```sh
sha256sum -c SHA256SUMS
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python benchmarks/global/wide_statevector.py
python benchmarks/global/excitation_check.py > excitation-results.json
```

Each verification command exits with a nonzero status on a failed numerical check. The first writes wide-results.json. Both calculations use independently implemented references written by the project team. Timings describe the machine executing the checks. Record the package SHA-256, CPU, Python build and NumPy version when sharing measurements.

## Tested scientific scope

| Execution path | Workload | Verified output |
|---|---|---|
| Direct complex128 state vector in a fixed-excitation basis | 50 and 100 qubits with two excitations, 14 mixing layers and long-range non-Clifford gates | Every in-sector amplitude, two out-of-sector zero amplitudes and state norm. An independently coded two-particle reference is cross-checked against a dense eight-qubit simulation. |
| Untruncated matrix-product state | Connected 50- and 100-qubit chains with local rotations and 2, 4 or 6 alternating entangling layers | Eight complex amplitudes, one central Pauli-X expectation and the norm per circuit. References use a spatial path sum and dense simulation of the observable’s causal cone. |

The direct backend scales with the binomial coefficient for the chosen width and excitation count. It rejects unsupported gates and requests beyond its work or coefficient budget. The matrix-product backend has an explicit memory and work budget. Arbitrary dense 100-qubit circuits, GPU execution, browser parity and market leadership are outside the verified scope. Run the example in [the input guide](../benchmarks/global/WIDE.md) to send a circuit through the native JSON entry point.

## Scientific release status

This package is a candidate for independent reproduction. The full-engine release gate remains closed. External blind testing and independent replication require a reviewer and operator distinct from the development team. The repository maintains the full review protocol and run history.
