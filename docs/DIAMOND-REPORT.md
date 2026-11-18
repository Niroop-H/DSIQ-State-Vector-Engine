# DSIQ v0.10 — Diamond-105 condensed validation record

**INTERNAL RESEARCH VALIDATION — NOT CERTIFIED. Release eligible: false.**

83 PASS · 17 PARTIAL · 1 FAIL · 4 BLOCKED · 0 NOT_RUN. All 82 previous passes retained. #68 passed internal novel-input testing (56 generated circuit variants; 9,422 comparisons; max absolute error 2.56709e-15). Independent blind testing remains blocked. #80 and #101 gained partial restart evidence only (three fresh processes, two warm runs each; 128 queries and 128 seeded samples per run; identical scientific output digest 4132a9e33b500bca71e244cd0a6095b1dd5d196db53911e263efffa2a5b322c8).

## Executed experiments

- Connected structured non-Clifford circuit, 25 qubits, 120 gates: all 33,554,432 nonzero complex amplitudes compared to a separately implemented complete dense reference. Maximum absolute error 3.408259845555477e-17; L2 error 6.158591430883039e-16; coefficient payload 800 bytes, streaming output buffer 4 MiB, additional runtime and frame metadata excluded. Dense vector alone 512 MiB. #53 PARTIAL pending named external reference.
- Native bond/compact/affine contraction: 512 amplitude comparisons on randomized small circuits, max error 6.335327934766281e-16; 100-wire depth-four random case cross-checked. Depth-five selected-plan forecast 6,610,223,104 array bytes, not executed. #70 still FAIL: no completed 100-wire depth-100 randomized uncompute.
- Runtime Node v22.16.0 linux/x64. Acceptance harness process peak RSS 511908 KiB; child reference processes separate. Dense reference child peak ~1.38 GiB. Exit 1 expected, release gate closed.
- Manual external-oracle workflow prepared for Aer, quimb and Stim; missing dependencies and unsuccessful installation prevented execution here. Native headless contractor not browser-integrated. GPU/MPI, production React build, full QASM support, hardware instrumentation, complete error certification and independent replication remain unresolved.

## Requirement IDs

- PASS (83): 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45, 47, 49, 50, 51, 52, 55, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 104
- PARTIAL (17): 43, 44, 46, 48, 53, 54, 56, 57, 75, 76, 78, 80, 98, 99, 101, 102, 103
- FAIL (1): 70
- BLOCKED (4): 77, 90, 100, 105
- NOT_RUN (0): none

## Full evidence

This repository record is condensed because the full evidence transfer was unavailable. Complete per-test attempts, telemetry and detailed evidence are included in the downloadable v0.10 workspace and standalone artifacts.

- DSIQ-Diamond-105-v0.10-report.md — SHA256 ccfa81fb632d7bd10243a05b1c6e22c4e5c8a46832adb1d51cd74a77cf8d7123
- DSIQ-Diamond-105-v0.10-results.json — SHA256 efe44a8f231dfad33ec6ca678bddfa1c7b0d8590aa9836e2978e0793328214e9
- DSIQ-State-Vector-Engine-integrated-v0.10.zip — SHA256 80252a00d64a8474eb5bf206e4add909aa7d216692115fe9bcd65d712d1ec08d
