# Scientific novelty evidence review — 2026-11-24
Status: documentary technical review, not a novelty certification or new experiment.

## Prior art and claims
| Mechanism | Established baseline | DSIQ research question |
|---|---|---|
| Clifford frames | Aaronson–Gottesman, https://doi.org/10.1103/PhysRevA.70.052328 | Does displacement-rank reduction reduce measured work on matched non-Clifford workloads? |
| Tensor contraction | Markov–Shi, https://doi.org/10.1137/050644756 | Does scope-derived planning improve peak memory and work against optimized contraction planners? |
| Adaptive selection / MPS | https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html | Does DSIQ automatic selection beat matched automatic and manually tuned peers including overhead? |
| Conserved excitation sector | Standard fixed-Hamming-weight subspace | Does implementation improve time and memory versus QuSpin at identical outputs? |
| Binary128 interval bounds and bounded seven-product multiplication | Established numerical techniques | Does integration provide useful certified-query coverage at lower cost? |

None of these ingredients alone establishes mathematical originality. Candidate contribution is the integrated policy and implementation; novelty of individual algorithms remains a research question. No patentability or complexity breakthrough conclusion.

## Evidence reconciliation
[Standings](../benchmarks/evidence/simulator-standings.md) reports 17/23 native fastest, 4/23 JS fastest; combined 21/23 is retrospective selection, not measured automatic routing. Entire 25-qubit vector compared against Aer on one connected circuit (33,554,432 entries, max absolute difference 3.28e-17). At 100 qubits path sweep checks 11 amplitudes and norm; two-excitation sector checks 4,950 coefficients, not arbitrary dense state. Clifford comparison checks 1,100 observables, not global phase. [v0.16](V016-CANDIDATE.md) reports 566 known queries, not a new blind campaign; 220/222 strict certificates enclose original references, two disputed references require external adjudication.

## Prospective ablation
Freeze source and workload hashes; register width 25, 30, 40, 50, 75, 100; depth 4, 10, 25, 50, 100; chain, grid and long-range connectivity; Clifford/T and continuous rotations; fixed seeds selected independently. Compare full outputs only where feasible, otherwise identical amplitude/observable requests. Disable each candidate optimization separately; compare native and automatic selection against tuned Aer MPS, quimb, Stim or other applicable baseline. Record precision, error, wall time including planning, peak RSS, work, failures and timeout. Report all paired outcomes and geometric mean speed ratios only for completed matched cases, alongside completion rates. Separate exploratory tuning from held-out workloads. Do not claim general superiority or universal polynomial scaling.
