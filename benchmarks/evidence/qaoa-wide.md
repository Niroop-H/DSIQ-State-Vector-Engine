# DSIQ QAOA and wide-circuit results

Measurements use the adaptive browser engine in Node for dense QAOA, the native untruncated matrix-product-state (MPS) engine for path-graph QAOA, and the direct excitation-sector engine for particle-conserving circuits. A result at one width applies to the circuit family, graph and outputs tested.

## Dense QAOA

The browser engine detects a uniform initial state followed by RX mixers and ZZ interactions. Both preserve invariance under flipping every bit. It evaluates one representative of each complementary pair, batches commuting phases with equal angles and restores the full state for downstream queries. Independent gates may be interleaved in the input. Setup, checks, execution and amplitude extraction are included in the adapter timings.

| MQT Bench graph | Qubits | DSIQ ms | Fastest competitor | Competitor ms |
|---|---:|---:|---|---:|
| Original | 12 | 13.14 | QuEST | 1.61 |
| Second seed | 12 | 10.61 | QuEST | 1.05 |
| Original | 16 | 33.97 | qsim | 18.21 |
| Second seed | 16 | 37.11 | qsim | 25.25 |
| Original | 20 | 107.52 | qsim | 124.31 |
| Second seed | 20 | 85.38 | qsim | 101.75 |

Each comparison ran all five adapters on the same single-thread CPU job. The table reports the median of three fresh-process trials, excluding process startup. qsim used single precision. DSIQ, Aer, QuEST and Qulacs used double precision. All passed the probe checks on these six graphs. A previous 20-qubit run on the original graph measured 822.26 ms for DSIQ. Runner CPUs vary between jobs and workflow runs. On the original graph one DSIQ trial took 184.37 ms, above all three qsim trials. The 20-qubit lead is a median result. The second seed was selected before the scheduling fix and used during this benchmark series.

Two further dense random graphs at 21 and 22 qubits used separate seeds and wire-dependent mixer angles. For each width, an independent NumPy implementation evolved the full dense state and checked 256 DSIQ amplitudes. The worst relative error across these checks was below 1.0e-14. These two runs establish correctness at additional widths. Competitive speed was measured at 12, 16 and 20.

The specialist workflow flags any adapter accuracy failure. DSIQ passed every specialist row. Single-precision qsim missed the preset threshold on Grover at 20 qubits, which made the overall workflow red. DSIQ finished that row in 28.49 seconds, the fastest passing time.

## Wide head-to-head tests

| Qubits | Path QAOA DSIQ ms | Path QAOA quimb ms | Two excitations DSIQ ms | Two excitations QuSpin ms |
|---:|---:|---:|---:|---:|
| 50 | 26.62 | 132.48 | 21.49 | 49.62 |
| 75 | 73.98 | 293.50 | 25.78 | 80.56 |
| 100 | 108.42 | 401.74 | 72.87 | 251.16 |

The path circuits have two cost layers, independently weighted nearest-neighbor edges and wire-dependent RX angles. Both engines return the same eight selected basis amplitudes and state norm. The reference contracts spin histories across the graph. quimb 1.11.0 uses CircuitMPS with zero truncation cutoff and no maximum bond. The table gives three-process median adapter times; imports are excluded and first-use compilation can be included. Raw process timings, seeds, versions and CPU models are in the evidence.

The two-excitation tests verify every coefficient against a separate coordinate calculation for each circuit. The widths have 1,225, 2,775 and 4,950 coefficients respectively. Additional non-Clifford nearest-neighbor circuits with four and six entangling layers passed amplitude, observable and norm checks at each width.

## Dense random graphs at wide widths

The two-layer dense random graphs used 587 edges at 50 qubits, 1,346 at 75 and 2,434 at 100. The default native MPS planner exceeded its resource budget at all three widths. The adaptive engine switched to replay. Its all-zero basis amplitude remained incomplete at five million replay visits on each graph. Each run also had a 30-second adaptive process timeout. The memory/work bounds and finite trials leave open what other resources or algorithms could achieve.

## Reproduce

From the repository root, use the specialist comparison and wide path workflows for the pinned external packages. Use the following commands for the local correctness and boundary probes.

```sh
OPENBLAS_NUM_THREADS=1 python benchmarks/global/check_full_qaoa.py
OPENBLAS_NUM_THREADS=1 python benchmarks/global/wide_qaoa.py
OPENBLAS_NUM_THREADS=1 python benchmarks/global/dense_boundary.py
node tests/complement.test.mjs
```

[Measurements](./qaoa-wide-measurements.json) · [Specialist CI](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45175406257) · [Wide QAOA CI](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45175603351) · [Earlier comparison](./specialists.md)
