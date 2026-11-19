# DSIQ v0.16 — private candidate sync and release status

**19 November 2026 — scientific release gate CLOSED.** This status document is not an engine upgrade. At inspection, main contained v0.13 (fb48e30768e9ca49c6449b12eca09e50de75e0f6). The v0.16 source archive must still be imported and its frozen scientific source fingerprint verified before treating main as v0.16.

Expected candidate scientific source SHA-256: `ec11c1a0114b71a47e9ae404ac5ce7c8af283be18a00348512b4df5c2277877a`.

## Candidate evidence

The supplied v0.16 engineering report records 60/60 known circuits, 566/566 numerical queries, 796 measured Astra checkpoints, 992/992 fresh small-circuit amplitude comparisons, maximum known-suite absolute error 7.2387e-16, and 220/222 original strict reference enclosures. Two original Opus enclosure discrepancies await independent adjudication; alternative diagnostic values do not replace the original reference evidence. The Opus query route did not measure 6453 requested checkpoints. These are known-suite regression results, not a new blind review.

## Fresh local execution on candidate source

- `tests/v15-integer.test.py`: PASS; 10 circuits, 330 comparisons, max absolute error 5.329345993883883e-17, max relative amplitude error 1.0197647289318679e-16.
- `tests/v15-sparse.test.py`: PASS; 20 circuits, 4320 amplitude comparisons, 480 Pauli comparisons, 60 norms, 2458 relative certificates, max absolute error 5.2675670383637236e-17, max absolute bound 6.371268492882684e-17.
- Full Diamond rerun: incomplete (execution-window timeout); no new aggregate grade.

## Diamond-105 closure

Latest complete candidate report is the v0.15 intermediate result: 83 PASS, 17 PARTIAL, 1 FAIL, 4 BLOCKED. This is not a v0.16 certification. The failed check is #70 (100-layer randomized non-Clifford forward/inverse execution; representation/replay resource boundary). Partial: #43,44,46,48,53,54,56,57,75,76,78,80,98,99,101,102,103. Blocked: #77 GPU/CPU parity, #90 measured energy, #100 newly blind independent challenge, #105 independent replication. No status upgraded on the basis of incomplete reruns.

Priority: reproduce #70 with actual intermediate-state challenges and no inverse-cancellation-only credit; validate certificate arithmetic and independently adjudicate the two original discrepancies; run complete measured checkpoint and sampling campaigns; compare with named external engines on identical tasks; obtain hardware telemetry and independent blind replication. Fail closed on any unavailable, partial, stale or failing check. Do not claim arbitrary 100-qubit simulation efficiency, scientific novelty or general superiority to optimized simulators on this evidence.

Keep original requirements, thresholds and historical evidence unchanged. Candidate upgrade is not a public release or a Diamond certification.
