# DSIQ competitive CPU verification, 23 November 2026

These selected-amplitude tests cover six MQT Bench circuit variants at three widths, five pinned PNNL QASMBench circuits, and two structured wide-circuit families. Each competitor in a row received the same circuit and output request. Rows with a timeout or numerical failure retain that outcome.

## MQT Bench

Median adapter time in milliseconds across three fresh processes on a CPU runner. Engine labels dsiq and dsiq-native designate the Node and standalone C++ implementations respectively. They are separately invoked. A fastest-of-two tally describes implementation coverage and does not measure automatic dispatch.

| Circuit | Qubits | dsiq | dsiq-native | quest | aer | qsim | qulacs | lightning | ddsim | Fastest passing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ghz | 12 | 3.164 | 0.078 | 0.145 | 1.725 | 1.207 | 0.129 | 26.228 | 8.419 | dsiq-native |
| ghz | 16 | 1.612 | 0.099 | 2.068 | 6.871 | 1.836 | 0.797 | 27.974 | 9.641 | dsiq-native |
| ghz | 20 | 1.846 | 18.344 | 44.924 | 114.470 | 12.338 | 17.143 | 52.132 | 22.489 | dsiq |
| grover | 12 | 20.503 | 0.480 | 7.861 | 40.917 | 50.447 | 7.402 | 53.325 | 30.247 | dsiq-native |
| grover | 16 | 443.243 | 2.414 | 651.810 | 880.682 | 395.714 | 405.678 | 401.715 | 174.978 | dsiq-native |
| grover | 20 | 35691.069 | 15.981 | 59196.959 | timeout | 7249.828 (accuracy fail) | 38371.504 | 18445.104 | 857.660 | dsiq-native |
| qaoa | 12 | 12.937 | 0.654 | 1.609 | 10.511 | 13.889 | 2.330 | 48.307 | 166.382 | dsiq-native |
| qaoa | 16 | 33.778 | 11.215 | 35.742 | 37.537 | 26.935 | 43.185 | 69.739 | 8897.476 | dsiq-native |
| qaoa | 20 | 99.243 | 228.157 | 883.199 | 565.390 | 122.958 | 1121.197 | 279.355 | timeout | dsiq |
| qaoa-fresh | 12 | 7.873 | 0.485 | 1.539 | 6.188 | 6.160 | 1.142 | 28.283 | 153.214 | dsiq-native |
| qaoa-fresh | 16 | 26.861 | 11.012 | 54.262 | 32.946 | 16.213 | 32.331 | 42.778 | 8857.445 | dsiq-native |
| qaoa-fresh | 20 | 89.077 | 291.588 | 906.559 | 449.141 | 68.383 | 868.711 | 288.149 | timeout | qsim |
| qft | 12 | 2.743 | 0.059 | 0.508 | 6.787 | 4.040 | 1.094 | 33.326 | 10.878 | dsiq-native |
| qft | 16 | 3.561 | 0.091 | 9.231 | 30.958 | 12.480 | 15.186 | 51.413 | 17.016 | dsiq-native |
| qft | 20 | 3.932 | 0.124 | 233.082 | 462.350 | 109.791 | 345.259 | 166.876 | 56.062 | dsiq-native |
| qft-input | 12 | 33.935 | 0.436 | 0.745 | 8.174 | 5.866 | 1.411 | 36.786 | 39.038 | dsiq-native |
| qft-input | 16 | 127.934 | 3.951 | 7.609 | 22.716 | 7.074 | 11.706 | 30.328 | 892.350 | dsiq-native |
| qft-input | 20 | 4225.999 | 131.317 | 274.343 | 568.719 | 118.864 | 394.117 | 175.308 | 30698.365 | qsim |

The double-precision criterion is maximum absolute error ≤ 1e-11 and relative error ≤ 1e-7 for reference magnitudes above 1e-10. Single-precision qsim uses absolute error ≤ 5e-4. References are QuEST where available, then Aer. Rotating adapter order and single-thread settings reduce order effects. Process wall times and peak RSS are included in the MQT JSON. A timed-out adapter exceeded 75 seconds in one process. APIs differ in their ability to return individual amplitudes, so these rankings apply to the requested output and adapters.

## QASMBench

Aer computed the full double-precision reference vector. The comparison checked selected complex entries with absolute error ≤ 1e-12 and relative error ≤ 1e-9 above magnitude 1e-14. Each adapter ran three times. The Qibo JIT timing includes backend setup and may benefit from compilation caches across processes.

| Circuit | Qubits | dsiq-js | dsiq-native | aer | qibo-numpy | qibo-jit | Fastest passing |
|---|---:|---:|---:|---:|---:|---:|---|
| small/ising_n10 | 10 | 9.122 | 1.453 | 13.928 | 36.934 | 440.140 | dsiq-native |
| medium/multiplier_n15 | 15 | 6.891 | 0.058 | 13.179 | 38.378 | 406.307 | dsiq-native |
| medium/qft_n18 | 18 | 28.141 | 0.519 | 100.394 | 1916.199 | 648.755 | dsiq-native |
| medium/bv_n19 | 19 | 2.236 | 14.334 | 40.238 | 127.050 | 385.615 | dsiq-js |
| medium/cat_state_n22 | 22 | 1.337 | 66.096 | 349.583 | 510.633 | 345.799 | dsiq-js |

## Particle-conserving circuits

The simulation uses the two-excitation subspace. At 100 qubits it has 4,950 coefficients.

| Circuit | Qubits | dsiq | quspin | Fastest passing |
|---|---:|---:|---:|---|
| sector seed 12171 | 100 | 52.955 | 210.754 | dsiq |
| sector seed 4183 | 100 | 43.969 | 167.936 | dsiq |
| sector seed 73619 | 100 | 43.957 | 170.901 | dsiq |
| sector seed 945173 | 50 | 17.888 | 35.377 | dsiq |
| sector seed 945198 | 75 | 31.027 | 100.912 | dsiq |
| sector seed 945223 | 100 | 54.800 | 209.353 | dsiq |

## Accuracy and scope

Both DSIQ and quimb passed the path-circuit amplitude and norm checks at every integer width from 1 through 100 against an independent 60-decimal-digit reference. At 100 qubits the separate three-trial path benchmark took 109.53 ms in DSIQ and 406.25 ms in quimb. This establishes selected-amplitude agreement for these structured circuits. Arbitrary 50- and 100-qubit full-state execution remains unverified.

An independent NumPy implementation checked every coefficient on 240 small circuits at widths 1–12. Across 163,800 amplitudes the maximum absolute error was 3.11e-15 and maximum norm error was 3.78e-15. Another 16 seeded circuits covered each width from 13 through 20, comparing all 4,177,920 coefficients with maximum absolute error 6.67e-16 and norm error 2.23e-15. Four additional seeded Grover cases at 12, 16, 20, and 24 qubits checked signed complex amplitudes against a 60-decimal-digit analytic reference.

The native CPU implementation retains product factors when possible, uses a bounded sum of product states for supported real gates, and replays using double-precision dense evolution when representation limits are exceeded. It supports up to 24 qubits. On 16-qubit Grover the preceding run measured 708.32 ms for native DSIQ versus about 149 ms for DDSIM. After the change the same circuit measured 2.41 ms versus 174.98 ms, with both passing. The [preceding three Grover measurements](competitive-grover-before.json) retain the per-engine medians, samples, errors and CPU metadata. Separate workflow runs can use different CPUs.

Earlier full-vector verification against Aer compared 33,554,432 coefficients on one connected 25-qubit circuit with maximum absolute error 3.28e-17. Earlier Stim verification checked 1,100 Clifford observables at 100 qubits with zero discrepancy. Stim timing and global phase were not measured. A separate dense two-layer 30-qubit QAOA experiment verified one amplitude to relative difference 3.75e-15; its 50-qubit target is open. GPU, multi-node, noise simulation, full-vector throughput across all engines, the complete public corpora, and comparative speed on arbitrary 100-qubit circuits are outside these measurements. Three timings on hosted runners give an observed median, not a universal performance ordering.


The specialist CI marks the combined run failed whenever any adapter misses its criterion. DDSIM exceeded 75 seconds on both 20-qubit QAOA graphs. On 20-qubit Grover, Aer exceeded the time cap and qsim exceeded its numerical tolerance. QuEST completed as the reference. Both DSIQ implementations passed all 18 rows.

## Interpreting the rankings

MQT Bench: fastest passing adapter counts dsiq-native 14, dsiq 2, qsim 2. All adapters finished and passed on 15 of 18 rows.

dsiq passed 18/18 and was faster than all qualifying external adapters on 4 rows.

dsiq-native passed 18/18 and was faster than all qualifying external adapters on 14 rows.

QASMBench: fastest passing adapter counts dsiq-native 3, dsiq-js 2. All adapters finished and passed on 5 of 5 rows.

dsiq-native passed 5/5 and was faster than all qualifying external adapters on 5 rows.

dsiq-js passed 5/5 and was faster than all qualifying external adapters on 5 rows.

The 20-qubit second-seed QAOA and entangled-input QFT cases favor qsim. The observed maximum absolute probe errors on those circuits were respectively 1.09e-8 and 4.21e-8 for qsim, compared with 3.71e-18 and 1.73e-16 for the fastest DSIQ implementation on each. They illustrate the measured precision/speed tradeoff.

## Reproduction

From the repository root on Linux with g++, NumPy and mpmath installed:

```bash
g++ -std=c++20 -O3 -march=native native/cpu_statevector.cpp -o /tmp/dsiq-cpu
python tests/native_cpu_differential.py /tmp/dsiq-cpu
OPENBLAS_NUM_THREADS=1 python tests/native_cpu_wide_differential.py /tmp/dsiq-cpu
python tests/grover_holdout.py /tmp/dsiq-cpu
```

The workflows pin the competitor versions and QASMBench revision. The adjacent JSON files preserve circuit digests, queried indices, errors, reported times and available machine metadata. The MQT workflow artifacts also contain normalized QAOA gates.

[MQT and QuSpin run](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45220885300) · [QASMBench run](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45221050160) · [Width sweep](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45219762480) · [Wide path timing](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45219762503) · [Stim evidence](named-references-45163281654.json) · [Dense-amplitude experiment](dense-amplitude-experiment.md)
