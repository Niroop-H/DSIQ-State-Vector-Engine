# DSIQ v0.13 — ASTRA regression and scientific validation

**CONFIDENTIAL ENGINEERING EVIDENCE — research candidate, not certified.**

Frozen source SHA-256: `2fffe9c697beae036ffe061f77184b53a51b1949708e3110225b8455fe597bd4`. Original challenge SHA-256: `585c54df2918d4d4bece7bad871911dda895711abf8b357bd0bbaa8dec5791b6`. Recomputed-reference score file SHA-256: `cb539714a0c3654eba2199a54b1f7c8d518c72b2769652db27f5e4ac8bea20d8`. Output manifest SHA-256: `1b3b52d2ab211e06e627e257d7fc5ab61d28fe99b1da5a0084eb0ebccccefebe`. All 20 original inputs were executed unchanged against the revised candidate before opening the reference score in the separate scoring process. Reference values were known from v0.12 review; this is a regression, not a new blind challenge. The original salted reveal remains unavailable.

## Regression outcome

- 20/20 complete circuits and 165/165 numerical queries within the original tolerances (absolute 1e-13; nonzero amplitude relative 1e-9).
- 336/336 requested measured norm checkpoints; each new path computes the norm by actual bra/ket contraction. All 66 strict query enclosures contain the recomputed discrepancies and are narrower than 1e-13; all 22 strict nonzero amplitude queries also have a certified relative bound <=1e-9.
- Maximum absolute error 5.33327013e-17; maximum relative amplitude error 9.41938105e-17; maximum strict absolute bound 5.33327013e-17. Comparison uses 105-digit decimal arithmetic on independently recomputed Astra reference values, not a newly verified original commitment.
- Wall time 9.421 s for the entire 20-case campaign using three workers, 45 s per-case wall/CPU soft limit, 2048 MiB per-worker address-space limit; maximum reported per-child peak RSS 80588 KiB (~78.70 MiB). Do not equate per-child maximum with total simultaneous RAM. No GPU, no paid compute, no hardware cycle counter available.

| Case | Qubits | Gates | Numerical queries | Checkpoints | Wall seconds | Peak RSS KiB | Mode |
|---|---:|---:|---:|---:|---:|---:|---|
| QFT-1 | 50 | 1321 | 8/8 | 17/17 | 0.155 | 80588 | interval-coherent-product |
| QFT-2 | 63 | 2078 | 8/8 | 17/17 | 0.160 | 80368 | interval-coherent-product |
| QFT-3 | 76 | 2996 | 8/8 | 17/17 | 0.190 | 80432 | interval-coherent-product |
| QFT-4 | 91 | 4277 | 8/8 | 16/16 | 0.196 | 80496 | interval-coherent-product |
| QFT-5 | 100 | 5149 | 8/8 | 17/17 | 0.279 | 80588 | interval-coherent-product |
| RCS-1 | 52 | 345 | 8/8 | 17/17 | 0.310 | 80260 | interval-bridge-forest |
| RCS-2 | 65 | 615 | 8/8 | 17/17 | 0.307 | 80272 | interval-bridge-forest |
| RCS-3 | 78 | 935 | 8/8 | 17/17 | 0.271 | 80288 | interval-bridge-forest |
| RCS-4 | 89 | 1331 | 8/8 | 17/17 | 0.492 | 80308 | interval-bridge-forest |
| RCS-5 | 100 | 1729 | 8/8 | 16/16 | 0.448 | 80336 | interval-bridge-forest |
| QAOA-1 | 51 | 271 | 8/8 | 16/16 | 0.251 | 80260 | interval-bridge-forest |
| QAOA-2 | 64 | 351 | 8/8 | 16/16 | 0.258 | 80264 | interval-bridge-forest |
| QAOA-3 | 77 | 409 | 8/8 | 17/17 | 0.227 | 80260 | interval-bridge-forest |
| QAOA-4 | 92 | 505 | 8/8 | 17/17 | 0.321 | 80268 | interval-bridge-forest |
| QAOA-5 | 100 | 531 | 8/8 | 17/17 | 0.271 | 80256 | interval-bridge-forest |
| UNCOMPUTE-1 | 53 | 564 | 9/9 | 17/17 | 0.210 | 80520 | interval-bridge-forest |
| UNCOMPUTE-2 | 66 | 1086 | 9/9 | 17/17 | 0.371 | 80296 | interval-bridge-forest |
| UNCOMPUTE-3 | 79 | 1680 | 9/9 | 17/17 | 0.366 | 80324 | interval-bridge-forest |
| UNCOMPUTE-4 | 94 | 2580 | 9/9 | 17/17 | 0.430 | 80396 | interval-bridge-forest |
| UNCOMPUTE-5 | 100 | 3192 | 9/9 | 17/17 | 0.420 | 80416 | interval-bridge-forest |

## Fresh non-Astra inputs and audit failure recovery

24 newly generated random circuits (seed 83491627, 6–7 qubits), with independently coded 110-decimal-digit state scatter: 4608 complex amplitude comparisons, 384 Pauli comparisons and 48 norms. All passed observed error and enclosure checks, with an explicit 1e-102 oracle rounding allowance. Maximum absolute error 4.92714049e-17; maximum relative amplitude error 1.01581047e-16. Actual SIGKILL test returned exit -9; recovered 5 journal records including an acknowledged early query and checkpoint. Interrupted execution remained failed. Standard engine and browser-worker smoke regression passed. Previous strict audit test passed 175 outputs and 433 norm checkpoints. Two local clean source directory runs of the prior 20-case rehearsal also passed as part of the full Diamond harness. No new external evaluator or separate physical host attestation.

## Diamond-105 original acceptance rerun

83 PASS, 17 PARTIAL, 1 FAIL, 4 BLOCKED, 0 NOT_RUN. All 83 previous passing IDs retained and all original criterion texts unchanged. The test harness retains its historical v0.12 label as a static string; the execution here used the v0.13 workspace. Peak RSS for the entire harness: 570396 KiB (child RSS separate). Exit 1 expected: scientific release gate closed. Raw results SHA-256 `9fbb08c1dfc059f561b8f98f990cd8c40a5f08b9735a61f7f890b990c71e11fd`.

The new regression removes all 11 prior case-completion failures for these exact inputs and addresses the reported numerical certificate tightness and missing-checkpoint defects within the tested structured domain. It does not establish universal efficient simulation, full 50–100-qubit chaotic sampling, original #70 deep arbitrary random uncomputation, complete #102 all-mode certification or #103 hardware telemetry. #100 remains blocked by the unresolved original reveal and need for new independent full-scope evaluation; #105 requires genuine independent engineering-team replication. No additional test promoted. Browser certified-auto zero-shot worker route verified; full inherited web build and production browser/performance validation not executed. New deterministic paths have finite fixed-point range and bounded structure; the separate RCS shot plan is not executed in this campaign.

## Reproduction

Run `python -B tests/astra-regression.py execute <challenge.json> <commitment.json> <new-run-dir> --timeout 45 --limit-mib 2048 --workers 3`; then run its `score` subcommand with the independently recomputed `astra-score.json` and the exact manifest digest. Run `python -B tests/v13-interval.test.py`, `node tests/worker.test.mjs`, and the original Diamond harness. Do not share proprietary source, raw execution logs or the prior reference values with new blind reviewers.
