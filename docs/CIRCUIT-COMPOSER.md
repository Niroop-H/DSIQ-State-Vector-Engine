# DSIQ Circuit Composer | Scientific Research Workspace

Developer: Devashri S Industries. Research institution: MAH Quantum Research Institute.

## Scope

The circuit composer is a **functional** graphical circuit authoring interface, not a simulated visualization. Every placed gate generates deterministic OpenQASM 2.0 source that is executed by the existing DSIQ JavaScript Web Worker. The display of amplitudes, norm, Pauli expectations, samples and execution time comes exclusively from the worker. The composer does not generate fake numerical outputs.

The visual mode supports 1 through 100 wires and at most 2,048 sequential gate operations. The composer displays only twelve gate columns at a time, keeping the DOM bounded while retaining the full ordered gate list. Scroll vertically to reach qubits 0 through 99, or use Go to qubit. Page through the gate sequence with Previous steps, Next steps, and Page Go. These remain authoring limits, not blanket guarantees of feasible arbitrary-depth 100-qubit execution. Larger experiments, measurement/reset instructions and more sophisticated restricted OpenQASM can continue to run through the original QASM editor. Unsupported source files remain intact rather than being silently truncated on visual import.

## Supported visual operations

Single-qubit: H, X, Y, Z, S, SDG, T, TDG, SX.
Rotations: RX, RY, RZ, P, with restricted supported angle tokens such as `pi/2`, `-pi/4`, or decimal values in radians.
Multi-qubit: CX, CY, CZ, CP, SWAP and CCX, with distinct control and target wires as required.

To add a gate, select it in the gate palette, then click the ADD cell on the required wires. For CX/CY/CZ/CP, choose control before target; for CCX choose two controls and then target; for SWAP select two distinct endpoints. The chronological order of circuit columns is preserved in the emitted OpenQASM.

Use Remove, left/right reorder, Undo and Redo to modify the gate sequence. Use New circuit to reset the visual experiment, Resize wires to change its register width while preserving valid existing gates, and Import QASM to parse supported source into the visual diagram. Manual source edits are never overwritten without an explicit import or new-circuit action. Download .qasm exports the actual executable source.

## Executing and interpreting outputs

Select the **Execute circuit** button to run the current generated QASM using the existing `worker.mjs` via the existing research workspace UI. Set amplitude query, Pauli string, sampling shots, method and numerical precision in the adjacent experiment specification panel. The gate diagram itself does not perform quantum computations. It only produces verifiable inputs for the independently implemented engine worker.

Qubit 0 is the least significant bit of a computational basis query. For a 2-qubit Bell circuit `h q[0]; cx q[0],q[1];`, the state is `( |00> + |11> ) / sqrt(2)` and amplitude(11) is `sqrt(1/2)`, with `XX` expectation `1`. Test cases compare the real worker outputs with these analytical values.

The interface is pure black (`#000000`) with grayscale scientific notation. It does not represent the native binary128 backend or claim Diamond-105 certification.

## Tests

`node tests/circuit-editor.test.mjs`
`node tests/worker.test.mjs`

The circuit editor regression tests check OpenQASM serialization and import, valid and invalid register/gate/angle inputs, and true worker results for Bell entanglement, phase interference, and SWAP. Browser-level automation is recommended before considering the interface production qualified.

The **100Q GHZ** reference composer button builds `h q[0]` followed by 99 nearest-neighbor `cx` gates, sets the amplitude query to `ones`, the Pauli observable to 100 X symbols, and disables sampling by setting shots to zero. The worker computes the outputs; no values are fabricated in the UI.
