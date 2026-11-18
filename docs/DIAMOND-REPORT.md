# DSIQ Diamond-105 — local validation record
Research build v0.3. NOT CERTIFIED. Release gate failed closed.

**35/105 passed** | 25 partial | 4 failed | 22 blocked | 19 not run
Runtime: v22.16.0, linux x64. Entire-suite process peak RSS: 1026992 KiB (not the core workspace).

All criteria are retained verbatim in `docs/diamond-105.json`; the table records only the executed scope. Tests are internal and do not establish general efficient universal simulation. A failed/deferred test is not proof of mathematical impossibility; it is lack of verified completion under the configured budget.

| ID | Requirement | Status | Evidence |
|---:|---|---|---|
| 001 | FP64 Machine Epsilon Precision | PASS | analytic RX every wire, both nonzero amplitudes; {"max":1.1989798176196528e-16} |
| 002 | FP32 Precision Compliance | BLOCKED | FP32 not implemented |
| 003 | Total Probability Normalization | PARTIAL | 100-qubit uniform and GHZ norm contraction |
| 004 | Global Phase Tracking | PASS | controlled and unconditional RZ(2π): relative/global phase |
| 005 | Relative Phase Accuracy | PASS | H-P-H interference at 101 angles |
| 006 | Zero-Amplitude Stability | PASS | H twice on each wire, zero amplitude tolerance 1e-15 |
| 007 | Denormal / Subnormal Handling | PARTIAL | 1024-qubit tiny log magnitude, inverse rotations; replay underflow unverified |
| 008 | Inner Product Exactness | PASS | 100-qubit GHZ states, complex analytical overlap |
| 009 | Expectation Value Accuracy | PASS | 100-qubit GHZ X/Z/Y Pauli strings |
| 010 | Trace Preservation | PARTIAL | norm after every 100-qubit product rotation |
| 011 | Hermitian Conjugate Consistency | NOT_RUN | No qualifying executed test yet |
| 012 | Bitstring Endianness Consistency | PASS | all 100 wires: X amplitude and deterministic sampling |
| 013 | Superposition Uniformity | PASS | 1000 random H^100 basis queries, relative error |
| 014 | Arbitrary Basis Query Speed & Accuracy | PARTIAL | 1000 analytic product amplitude queries, latency; {"ms":17.783525000000054} |
| 015 | Analytical Circuit Match | NOT_RUN | No qualifying executed test yet |
| 016 | Pauli Gates (X, Y, Z) | PASS | X,Y,Z each of 100 wires |
| 017 | Hadamard (H) & \\(\sqrt{X}, \sqrt{Y}\\) Gates | PASS | H²=I, SX²=X, SY²=Y each wire |
| 018 | Clifford Phase Gates (\\(S, S^\dagger\\)) | PASS | S/SDG each wire |
| 019 | Non-Clifford T and \\(T^{\dag }\\) Gates | PARTIAL | 500 T + 500 TDG gates on uniform state |
| 020 | Arbitrary Parametric Rotations (\\(R_x, R_y, R_z\\)) | PASS | RX/RY/RZ irrational angles on every wire |
| 021 | General U3(θ, φ, λ) Gate | PASS | U3 each wire analytical complex amplitudes |
| 022 | Two-Qubit Entanglers (CNOT, CZ, CY) | PASS | CX/CY/CZ every basis input both distant directions |
| 023 | SWAP & iSWAP Gates | PASS | SWAP/iSWAP all 4 basis columns, adjacent and distant pairs; logical SWAP path also tested |
| 024 | \\(\sqrt{\text{SWAP}}\\) & fSim Gates | PASS | sqrtSWAP and fSim independently known 4x4 matrix columns; distant pairs in both directions |
| 025 | Controlled-Phase (\\(CR_z(\theta), CP(\theta)\\)) | PASS | CRZ/CP both distant directions |
| 026 | Three-Qubit Toffoli (CCX) & Fredkin (CSWAP) | PASS | Toffoli and Fredkin all 8 basis input columns on distant wires |
| 027 | Multi-Controlled \\(C^{k}X\\) Gates (k = 10, 50, 99) | PASS | 10,50,99 controls, both target directions and disabled case |
| 028 | Custom Unitary Matrix Injection | BLOCKED | Custom matrix injection unavailable |
| 029 | Identity & Zero-Angle Gates | PASS | state unchanged after I and zero-angle gates |
| 030 | Mid-Circuit Reset Operations | PARTIAL | trajectory reset, both GHZ outcomes, norm |
| 031 | 100-Qubit GHZ State | PASS | 100-qubit GHZ amplitudes and 1000 parity-correlated samples |
| 032 | 100-Qubit W-State | PASS | 100-qubit W, all 100 amplitudes and norm |
| 033 | 1D Linear Chain Entanglement | PARTIAL | GHZ chain; deeper entangling layers unverified |
| 034 | 2D Grid Topology (10 × 10) | NOT_RUN | No qualifying executed test yet |
| 035 | All-to-All Complete Graph Entanglement | PASS | complete 100-qubit graph: 4950 CZ interactions; all 100 stabilizer generators and norm; {"qubits":100,"gates":5050,"mode":"dag","liveNodes":10464,"peakNodes":16507,"nodeBudget":32768,"precision":"Float64; no deliberate truncation"} |
| 036 | Long-Range Cross-Chip Gates | NOT_RUN | No qualifying executed test yet |
| 037 | Deep Circuit Scaling (Depth 50–200) | NOT_RUN | No qualifying executed test yet |
| 038 | Maximally Entangled Page-Curve Test | PASS | 50 Bell pairs across physical 50/50 split; lossless wire planner; default logical-order DAG failed at gate 20; {"cutEntropyBits":50,"peakNodes":7600,"derivation":"unique Bell stabilizer state"} |
| 039 | Cluster / Graph State Preparation | FAIL | 100-qubit 10x10 cluster graph, check all stabilizers; cluster: deferred replay at gate 146; no verified result within DAG budget  'replay' !== 'dag'  |
| 040 | Quantum Fourier Transform (100-Qubit QFT) | FAIL | 100-qubit QFT followed by inverse on nonzero basis; lossless logical SWAP; no gate cancellation; inverse QFT: deferred replay at gate 5309; no verified result within DAG budget  'replay' !== 'dag'  |
| 041 | Grover Diffusion Operator (50–100 Qubits) | FAIL | one Grover iteration on 100 qubits, all-ones mark and diffusion, amplitude vs formula; Grover: deferred replay at gate 308; no verified result within DAG budget  'replay' !== 'dag'  |
| 042 | Quantum Phase Estimation (QPE) | NOT_RUN | No qualifying executed test yet |
| 043 | Linear Cross-Entropy Benchmarking (XEB) | NOT_RUN | No qualifying executed test yet |
| 044 | Porter-Thomas Distribution Match | NOT_RUN | No qualifying executed test yet |
| 045 | Chi-Square Goodness-of-Fit | NOT_RUN | No qualifying executed test yet |
| 046 | Heavy Output Generation (HOG) | NOT_RUN | No qualifying executed test yet |
| 047 | Seeded Determinism | PASS | 1000 complete samples reproducible with same seed |
| 048 | Unseeded Statistical Independence | NOT_RUN | No qualifying executed test yet |
| 049 | Single-Shot Mid-Circuit Measurement | PARTIAL | both collapse branches and programmatic classical feedback |
| 050 | Marginal Distribution Consistency | PARTIAL | GHZ marginal probabilities |
| 051 | Rare-Event Sampling Accuracy | NOT_RUN | No qualifying executed test yet |
| 052 | No Mode Collapse | PASS | 100000 H^100 sampled strings; zero duplicates; {"unique":100000} |
| 053 | 25-Qubit Full Vector Equivalence | BLOCKED | Specified independent comparison not executed |
| 054 | 30-Qubit Full Vector Equivalence | BLOCKED | Specified independent comparison not executed |
| 055 | Feynman Path-Sum Single-Amplitude Match (50 Qubits) | BLOCKED | Specified independent comparison not executed |
| 056 | Tensor Network Contraction Match (100 Qubits, Low Depth) | BLOCKED | Specified independent comparison not executed |
| 057 | Stabilizer Engine Match (100 Qubits, Clifford-Only) | BLOCKED | Specified independent comparison not executed |
| 058 | Matchgate / Fermionic Simulator Match | BLOCKED | Specified independent comparison not executed |
| 059 | Analytical Hamiltonian Evolution (\\(e^{-iHt}\\)) | BLOCKED | Specified independent comparison not executed |
| 060 | VQE / QAOA Energy Landscape Match | BLOCKED | Specified independent comparison not executed |
| 061 | Non-Clifford T-Gate Injection Audit | PARTIAL | 500 T injections into GHZ, analytic phase; structured circuit only |
| 062 | Zero-State Bias Check | NOT_RUN | No qualifying executed test yet |
| 063 | Permutation Invariance | PARTIAL | arbitrary logical permutation of 6-qubit random circuits, all amplitudes; 100-qubit planner checked separately |
| 064 | No Bond-Dimension Truncation | PARTIAL | No intentional SVD truncation in source; independent audit pending |
| 065 | No Amplitude Pruning / Thresholding | PARTIAL | 1e-18 amplitude retained and uncomputed |
| 066 | Irrational Gate Parameter Audit | PARTIAL | non-dyadic parameter, analytic output |
| 067 | Adversarial Circuit Check | NOT_RUN | No qualifying executed test yet |
| 068 | Input Independence | PARTIAL | Generic gate code, independent blind audit pending |
| 069 | Bit-Flip Symmetry Break | PASS | GHZ symmetry break on q73, four analytic amplitudes |
| 070 | Uncompute (\\(U^{\dag }U\\)) at Depth 100 | FAIL | seeded 100-layer non-Clifford 100-qubit random rotations and random matching entanglers then inverse, 32768-node bound; depth 1: deferred replay at gate 103; no verified result within DAG budget  'replay' !== 'dag'  |
| 071 | Physical RAM Ceiling Audit | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 072 | Zero Disk Swap / Paging Audit | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 073 | Zero Network Offloading | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 074 | Memory Leak Check | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 075 | Deterministic Memory Footprint | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 076 | Cache Locality & Bandwidth Efficiency | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 077 | GPU/CPU Parity | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 078 | Multi-Thread / MPI Determinism | BLOCKED | Hardware/OS instrumentation, long runs or backend required; node count is not RAM cap |
| 079 | Graceful Resource Boundary Handling | PARTIAL | forced budget replay and explicit unsupported-sampling error |
| 080 | Cold-Start vs. Warm-Start Consistency | NOT_RUN | No qualifying executed test yet |
| 081 | Qubit Scaling Curve (N = 10 → 100) | PASS | GHZ wall-clock N10..100; [{"n":10,"ms":0.14729199999965203},{"n":20,"ms":0.41189999999915017},{"n":30,"ms":1.3273089999993317},{"n":40,"ms":1.9339830000008078},{"n":50,"ms":2.7236420000008366},{"n":60,"ms":4.966851000000133},{"n":70,"ms":3.358629000000292},{"n":80,"ms":7.1029080000007525},{"n":90,"ms":6.398017000000436},{"n":100,"ms":9.912419999999656}] |
| 082 | Depth Scaling Curve (D = 1 → 100) | NOT_RUN | No qualifying executed test yet |
| 083 | Entanglement Scaling Curve | NOT_RUN | No qualifying executed test yet |
| 084 | Single-Amplitude Query Latency | PASS | single-amplitude latency, 1000 queries each at 50/100; [{"n":50,"meanMs":0.006920643999999811},{"n":100,"meanMs":0.008068121999999676}] |
| 085 | Batch Amplitude Query Throughput | PARTIAL | 10000 sequential distinct amplitude queries; not parallel; {"ms":89.13010699999995} |
| 086 | Sampling Throughput (Shots/Sec) | PASS | 10000 shots each at 50/100 qubits; [{"n":50,"shotsPerSecond":148895.34469324318},{"n":100,"shotsPerSecond":90881.14743483117}] |
| 087 | Gate Fusion / Compilation Overhead | NOT_RUN | No qualifying executed test yet |
| 088 | Expectation Value Runtime | PASS | 1000 Pauli terms on 100-qubit GHZ; {"ms":45.770980000000236} |
| 089 | Gradient / Parameter-Shift Speed | PARTIAL | 100-qubit product variational circuit parameter-shift derivative vs analytic -sin(theta); {"ms":0.41293299999961164} |
| 090 | Energy / Power Draw Efficiency | BLOCKED | No calibrated power meter |
| 091 | Zero-Qubit / Single-Qubit Edge Case | PARTIAL | N=1,2; N=0 explicitly rejected |
| 092 | Empty Circuit Execution | PASS | 100-qubit empty circuit |
| 093 | Extreme Circuit Depth (10,000+ Gates) | PARTIAL | 10000 sequential single-qubit T gates |
| 094 | Near-Identity Gate Sequences | PASS | one million RX(1e-9) actual iterations |
| 095 | High-Frequency Phase Interference | PARTIAL | symbolic rational pi input is reduced exactly; raw rounded Float64 angle cannot recover intended pi multiple; {"symbolic":[1,0],"raw":[1,-2.231912181360871e-10],"rawError":2.231912181360871e-10} |
| 096 | Disconnected Sub-Circuits | PASS | two 50-qubit GHZ blocks, product amplitude match |
| 097 | Repeated Measurement Stability | PASS | 100 repeat measurements after GHZ collapse |
| 098 | NaN / Inf Guardrails | PARTIAL | NaN/Inf inputs rejected, finite valid output |
| 099 | OpenQASM 2.0 / 3.0 Compatibility | PARTIAL | supported QASM 2/3 syntax only |
| 100 | Blind Third-Party Circuit Test | BLOCKED | Independent external evaluation cannot be self-certified |
| 101 | Bit-Exact Reproducibility | NOT_RUN | No qualifying executed test yet |
| 102 | Error Bound Transparency | BLOCKED | Certified forward-error bounds missing |
| 103 | Complete Audit Logging | PARTIAL | Gate/node/time telemetry only |
| 104 | Formal Complexity Documentation | PARTIAL | DAG and replay complexity documented; no general efficient bound proven |
| 105 | Independent Replication | BLOCKED | Independent external evaluation cannot be self-certified |
