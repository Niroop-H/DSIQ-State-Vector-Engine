# DSIQ v0.9 — Diamond-105 condensed validation record

**82/105 PASS · 16 PARTIAL · 1 FAIL · 4 BLOCKED · 2 NOT_RUN. Release gate closed.**

All 105 criteria retained. The complete local harness was executed and returned exit status 1 by design. All 81 earlier passes retained; #19 passed on tested low-displacement-rank connected circuits with interleaved Hadamards and 500/1000/5000 T/TDG gates. This is not a proof of arbitrary efficient simulation or independent certification.

- 1024-qubit encoded circuit: 11,595 gates; 36,608 bytes coefficient storage; flip rank 8; 256 support amplitudes vs independent extended-precision oracle, max absolute error 1.7268586255920952e-15; 16 off-support queries and 512 samples.
- T-gate scaling: 2,245 / 3,983 / 17,888 total gates, 3,552 coefficient bytes at all three counts; max errors 2.9865631336773386e-15 / 5.584598387299587e-15 / 2.269389623728351e-14.
- 50 randomized small circuits: 1,600 amplitude comparisons, 1,000 observable comparisons; maximum discrepancy 1.3322676295501878e-15.
- 40 nonmonomial six-qubit circuits: 2,560 full-basis probability comparisons, 5,120 draws; max error 4.440892098500626e-16.
- Supplemental 1024-qubit measurement test: 3,590 gates, 1,024 unique samples, 1,020 independent uniform readout bits and four logical measurements, 32 log-probability checks, max error 1.1368683772161603e-13. See docs/RANK-ANCILLA-EVIDENCE.json.
- Entire harness peak RSS: 560400 KiB. Coefficient bytes exclude runtime, code and metadata.
- #70 remains failed; #100/#105 require independent evaluators; #77 and #90 require unavailable hardware. The named external reference tools, MPI, production frontend build and remote CI are unverified.

The full unabridged v0.9 local report and raw JSON are included in the distributed integrated workspace; only this condensed report is committed because the file transfer bridge did not expose the full file. Raw JSON SHA-256: `56b1db5694785cf39763df322cdcec4aa58a542d5d0856ff7408f45cc4a33394`. Re-run `node --max-old-space-size=3072 tests/diamond.test.mjs diamond-results.json` for fresh evidence. Timestamps and telemetry vary.

| Test ID | Status |
|---:|---|
| 1 | PASS |
| 2 | PASS |
| 3 | PASS |
| 4 | PASS |
| 5 | PASS |
| 6 | PASS |
| 7 | PASS |
| 8 | PASS |
| 9 | PASS |
| 10 | PASS |
| 11 | PASS |
| 12 | PASS |
| 13 | PASS |
| 14 | PASS |
| 15 | PASS |
| 16 | PASS |
| 17 | PASS |
| 18 | PASS |
| 19 | PASS |
| 20 | PASS |
| 21 | PASS |
| 22 | PASS |
| 23 | PASS |
| 24 | PASS |
| 25 | PASS |
| 26 | PASS |
| 27 | PASS |
| 28 | PASS |
| 29 | PASS |
| 30 | PASS |
| 31 | PASS |
| 32 | PASS |
| 33 | PASS |
| 34 | PASS |
| 35 | PASS |
| 36 | PASS |
| 37 | PASS |
| 38 | PASS |
| 39 | PASS |
| 40 | PASS |
| 41 | PASS |
| 42 | PASS |
| 43 | PARTIAL |
| 44 | PARTIAL |
| 45 | PASS |
| 46 | PARTIAL |
| 47 | PASS |
| 48 | PARTIAL |
| 49 | PASS |
| 50 | PASS |
| 51 | PASS |
| 52 | PASS |
| 53 | PARTIAL |
| 54 | PARTIAL |
| 55 | PASS |
| 56 | PARTIAL |
| 57 | PARTIAL |
| 58 | PASS |
| 59 | PASS |
| 60 | PASS |
| 61 | PASS |
| 62 | PASS |
| 63 | PASS |
| 64 | PASS |
| 65 | PASS |
| 66 | PASS |
| 67 | PASS |
| 68 | PARTIAL |
| 69 | PASS |
| 70 | FAIL |
| 71 | PASS |
| 72 | PASS |
| 73 | PASS |
| 74 | PASS |
| 75 | PARTIAL |
| 76 | PARTIAL |
| 77 | BLOCKED |
| 78 | PARTIAL |
| 79 | PASS |
| 80 | NOT_RUN |
| 81 | PASS |
| 82 | PASS |
| 83 | PASS |
| 84 | PASS |
| 85 | PASS |
| 86 | PASS |
| 87 | PASS |
| 88 | PASS |
| 89 | PASS |
| 90 | BLOCKED |
| 91 | PASS |
| 92 | PASS |
| 93 | PASS |
| 94 | PASS |
| 95 | PASS |
| 96 | PASS |
| 97 | PASS |
| 98 | PARTIAL |
| 99 | PARTIAL |
| 100 | BLOCKED |
| 101 | NOT_RUN |
| 102 | PARTIAL |
| 103 | PARTIAL |
| 104 | PASS |
| 105 | BLOCKED |
