# DSIQ — experimental numerical architecture (MAH Quantum)

## Scope and mathematics

All kernel code is independently authored for this project, using standard quantum mechanics and complex arithmetic. No third-party quantum simulation library is called. Weighted decision diagrams and sum-over-path algorithms are established research techniques; this prototype does not assert invention of either or validate a patent claim. The earlier affine-phase/Clifford reference-frame master equation is a research direction, not the algorithm implemented here.

For a level-q node, the amplitude function is `F_q(x) = w_(x_q) F_(q+1)(x)`. Each node stores two complex edges and a scalar phase/norm factor. Identical normalized suffixes are interned using exact Float64 keys (not tolerance-based merging). An uncontrolled 2x2 gate acts on the two child functions by their coherent linear combination; a controlled gate applies `I + P_controls (U-I)` with the computational-basis projector. SWAP is three CX gates. All branching phases are retained, with ordinary floating-point error. Samples descend through squared edge magnitudes because child functions are normalized. The logarithmic amplitude query accumulates log2 magnitude and phase along the chosen path. Returned real/imag components may underflow while log magnitude remains meaningful.

If the configured node count is exceeded, the kernel discards the DAG and accepts the remaining gate sequence. For a requested basis state it replays `⟨x|U|0⟩ = Σ_y ⟨x|G_m|y⟩ ⟨y|G_(m-1)...G_1|0⟩` via resumable depth-first traversal, summing complex terms with compensated addition. This fallback does not allocate a dense global statevector and can yield progress; it may take exponential time and use memory proportional to circuit size and stack depth. Replay Float64 products can underflow; no statistical approximation is silently substituted. Replay sampling is unavailable. Replays are cancellable, but do not persist checkpoints across a page reload.

## Interface and resource contract

- 1–4096 admitted logical qubits, 100,000 expanded operations, configurable DAG node count, up to 1024 samples. Admission bounds are not performance guarantees.
- Node count cap is not a byte/RSS limit. JS objects, maps, circuit storage, memoization, worker and replay stack all consume RAM independently. A 4 MiB native fixed-arena implementation is not yet available.
- Supported textual subset: one quantum register; H, X, Y, Z, I, S/SDG, T/TDG, RX/RY/RZ, P, U/U3, CX/CZ, CCX, SWAP, barrier. Angles use numerical literals, pi, arithmetic and parentheses. No explicit measure, reset, classical feedback, or noise; samples are final full-register computational-basis samples. q0 is rightmost.
- Local Web Worker supplies progress, cancellation and JSON evidence including input source and seed. A local run is not hardware execution. The legacy workbench remains unchanged except the added DSIQ entry and a parent quota reservation bridge. Static standalone assets are inspectable and can be reached directly; the quota bridge is not an enforceable access control. Do not expose the proprietary kernel publicly until deployment/IP review.

## Reproduce

`node tests/dsiq.test.mjs` (Node 22+); `python -m http.server 8000 --directory apps/web/public`, then visit `/dsiq/`. In the full project, enter `/1000-plus` through the original interface and select DSIQ State Vector Engine. To integrate the module into a separately unpacked copy of the original workspace, copy the `apps/web/public/dsiq` folder and run `node scripts/integrate-dsiq.mjs /path/to/workspace`.

Local checks: 60 randomized 5-qubit circuits (24 gates each), all 1920 amplitudes vs a dense reference using the same gate matrices: max abs difference 2.581e-15; 180 direct replay comparisons: max 2.221e-16. Analytic 1024-qubit phase GHZ (2048 gates, including 1024 arbitrary RZ gates), 128 shots, 63 all-zero and 65 all-one outcomes; peak allocated DAG node count 18358. 1024-qubit product rotations and T gates, log2 |amplitude| at all-ones approximately -1024. Forced six-node budget fallback verified. Parser tested for supported SWAP/broadcast and reset rejection. No full inherited npm build: offline cache did not contain all dependencies. No browser visual test or production performance claim.

## Next engineering gates

Native fixed-memory arena with measured allocator overhead, Clifford/affine phase specialization and automatic dependency slicing, scalable replay sampling, persistent checkpoints, independent gate-matrix reference, comprehensive OpenQASM parsing, adversarial numerical tests, competing-method benchmarks, and research/prior-art review before publication.
