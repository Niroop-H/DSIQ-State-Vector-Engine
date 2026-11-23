# Public circuit CPU comparison

Run the standalone Global CPU benchmark workflow or install the pinned workflow dependencies on Linux and run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python benchmarks/global/run.py`. Results go to global-results.json. Inputs are five pinned original PNNL QASMBench circuits, 10–22 qubits. This is a selected-amplitude comparison with dense Qiskit Aer; it is independent of Diamond.

The untimed preparation stage strips terminal measurements and barriers, extracts shared primitive gates and uses a dense reference to select one populated output. Each backend receives the same query indices (random probes plus zero, maximum index and a most-populated output). Both use double precision. Five fresh processes per simulator alternate order. Kernel timing includes simulator execution and output extraction; total process timing also includes runtime initialization and each backend's input preparation. Peak RSS includes the whole process. Absolute error must be at most 1e-12 on all probes; relative error must be at most 1e-9 for reference magnitudes above 1e-14. All repetitions, modes, memory, input hashes and errors are saved.

This selection does not measure sample generation, full-vector export, GPUs or optimized stabilizer baselines. Hardware, output contract and competitor settings must accompany performance claims.
