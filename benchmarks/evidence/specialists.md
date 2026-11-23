# DSIQ specialist CPU comparison

The first sweep used the engine before tuning. The second sweep used the same inputs after changes to controlled-phase handling, multi-controlled X gates and excitation-sector indexing. The Qulacs adapter also skips its light optimization pass for gates with more than five controls. Both snapshots include errors and timeouts.

[First sweep](./specialists-45171151123.json) · [After tuning](./specialists-45171853652.json)

## MQT Bench circuits

Each row uses the same normalized gate stream and basis-state probes across engines, one CPU thread, and three fresh processes per engine when successful. Entries are median adapter-reported milliseconds. Each adapter includes some combination of circuit construction, execution and output extraction. Cold-process measurements and peak RSS are in the JSON. The reference order is QuEST then Aer. Double-precision passes require maximum absolute probe error at most 1e-11 and relative error at most 1e-7 where the reference magnitude exceeds 1e-10. Single-precision qsim uses an absolute tolerance of 5e-4. Widths and circuit families were selected before tuning. QFT begins in the all-zero state.

| Circuit | Qubits | DSIQ | QuEST | Aer | qsim | Qulacs |
|---|---:|---:|---:|---:|---:|---:|
| QAOA | 12 | 8.07 | 1.35 | 8.82 | 9.93 | 1.77 |
| QAOA | 16 | 76.63 | 35.77 | 37.26 | 24.75 | 43.97 |
| QAOA | 20 | 822.26 | 757.15 | 490.87 | 90.05 | 879.50 |
| QFT | 12 | 1.52 | 0.28 | 4.73 | 3.36 | 0.79 |
| QFT | 16 | 3.62 | 9.37 | 30.50 | 13.21 | 15.18 |
| QFT | 20 | 3.81 | 215.50 | 460.52 | 108.77 | 342.06 |
| Grover | 12 | 31.50 | 12.50 | 55.55 | 63.79 | 8.05 |
| Grover | 16 | 327.81 | 522.33 | 770.44 | 270.43 | 281.17 |
| Grover | 20 | 36888.56 | 60261.17 | Timeout | Accuracy failure | 41109.01 |

## Two-excitation circuits on 100 qubits

The benchmark checks all 4,950 coefficients against a separately implemented two-particle oracle. Both adapters must achieve maximum absolute error below 1e-13 and relative error below 1e-9 for reference magnitudes above 1e-14. The QuSpin adapter uses spin_basis_general and ladder-operator matrix elements. Timings include basis and indexing work.

| Seed | DSIQ ms | QuSpin adapter ms | Speedup |
|---:|---:|---:|---:|
| 4183 | 72.19 | 245.33 | 3.40× |
| 12171 | 37.22 | 150.73 | 4.05× |
| 73619 | 74.11 | 258.64 | 3.49× |

Three additional seeds (3930541, 7085291 and 9991679) were checked after tuning for correctness only. All 4,950 coefficients on each agreed with the oracle to maximum absolute error below 3.6e-16.
