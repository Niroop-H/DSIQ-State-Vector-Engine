# DSIQ v0.15 — private engineering candidate

**Scientific release gate: CLOSED.** Known-challenge regression, not new blind certification. No additional expenditure. No prior engine evidence or committed reference was overwritten. Main was not updated in this turn. Candidate includes v0.14 query-native experiments plus v0.15 sparse support and precision escalation; legacy browser/adaptive paths are retained.

## Frozen source

`293ff12f03ad10670f2a1c0885fbb52748ac3279437895085cad2f67cd40364c` — canonical source manifest of audited kernel, native and test files and designated documentation, verified against packaged bytes. Both final Astra manifests record the same fingerprint and unchanged source. The native Opus query harness has per-request/output hashes but no independently timestamped source binding; the candidate source remained unchanged between those final executions. This is a local fingerprint, not independent attestation.

## Changes

- Incrementally maintain a bounded sparse map of computational basis indices, independent of qubit order and interaction connectivity. Exact structural support preflight rejects exponentially expanding cases; no magnitude threshold or reference-derived shortcut. Use rigorous 192-bit gate intervals and recenter each computed coefficient, explicitly accumulating the rounding and coefficient interval errors as an outward L1 bound dominating state L2 error. Previous state L2 error is preserved by exact unitary propagation. Pauli/norm error follows |<psi|P|psi>-<c|P|c>| <= (2+e)e <= 3e for e<1. The norm is actually evaluated on the represented state; it is not forced to one. Fixed-grid arithmetic is bounded and does not imply universal relative accuracy for arbitrarily tiny coefficients.
- Strict native query route escalates insufficient amplitude certificates and cancellation-sensitive observables to 1280-bit integer dyadic contraction with exact signed integer center/radius arithmetic, rigorous 192-bit gate-entry enclosures and binary64 output-projection error. No certificate narrowing from reference answers. Both computed enclosures must overlap; disjoint results fail closed. Escalation has explicit work, array and separator budgets; existing long-double route is retained if tighter or if escalation reaches a declared boundary.
- Offline sparse-state sampling uses exact integer cumulative weights of the represented state and seeded SHA-256 counter/rejection sampling (pseudorandom, not physical randomness). Numerical norm outputs are never normalized. Only sampling weights are normalized; the ideal measurement distribution differs in total variation by at most 2e under the state-error model.

## Final regression results

| Suite | Query-complete cases | Numerical queries within unchanged tolerance | Actual measured checkpoints | Notes |
|---|---:|---:|---:|---|
| Astra Medium | 20/20 | 165/165 | 336/336 | original reviewer salt lost, known recomputed references |
| Astra High | 20/20 | 221/221 | 460/460 | 80-digit revealed reference ledger |
| Opus | 18/20 | 172/180 | NOT_RUN | native query-only; all 26 requested norms are analytical unitary norms, not measurements |
| Total | 58/60 query-complete | 558/566 (98.5866%) | 796/796 across Astra suites | not a 58-circuit full-audit pass |

Astra High: 88/88 strict query bounds enclose the 80-digit references and meet absolute tolerance, 31/31 strict nonzero-amplitude relative certificates meet tolerance, 460/460 checkpoint norms have enclosures containing one. All measured norms round to 1.0 in binary64; max measured drift 0 at output precision. Maximum numerical error 5.54284339e-17; amplitude relative error 1.015649378e-16; campaign 18.504 s, two concurrent workers, max child RSS 83736 KiB. Astra Medium: 66/66 strict enclosures and 22/22 strict relative certificates. Campaign 24.600 s with one worker. Opus query-only: 73.873 s with one worker; zero uncontrolled signals; max numerical error 7.238637797e-16, max amplitude relative error 7.577406811e-11. All cases retain original per-request budgets, 120 s wall/CPU soft and 2048 MiB child address-space limits; native query work estimates differ from JS counters, and are not calibrated equivalent. Both Astra original inputs and Opus inputs were unchanged; reference files were used only for scoring and separate diagnostic.

## Opus certificate discrepancy

64/64 returned strict answers meet absolute-radius target; 29/29 returned strict nonzero amplitudes have relative radius <= 1e-9. 62/64 bounds enclose the original rounded committed reference values. Two cannot be counted as original-reference enclosure passes. A separately coded 100-digit dense scatter on the rigorously justified 12-wire causal subcircuit gives QAOA-100/final_pauli_5 = 6.5090102671497287593e-14 (matches integer solver); QAOA-50/final_pauli_3 = exactly zero by verified global-X symmetry of every phase-pair and mixer. Both independent results fall inside engine bounds, so 64/64 are consistent if these two diagnostic references are used. The original commitment remains unchanged; ask the independent reviewer to reproduce these findings before revising any official score. Diagnostic source and output are in private evidence.

## Fresh and supplemental tests

- Direct sparse kernel: 20 new circuits, 4,320 amplitudes, 480 Pauli expectations, 60 norms, all 4,860 comparisons passed against 110-digit dense scatter; 2,458 relative enclosures passed; estimate refusal exercised. Max absolute discrepancy 5.267567038e-17.
- Direct integer precision kernel: 10 new circuits, 330 comparisons against 110-digit dense scatter, all passed enclosure and numerical checks. Max absolute discrepancy 5.329345994e-17. These are small randomized cases, not proof of unbounded scaling.
- Astra High sampling: 5 x 20,000 shots, 15/15 preregistered marginal tests pass (minimum p=0.10251735, Bonferroni threshold 0.00333333); exact binomial tests and confidence intervals retained. Known-reference regression, not blind. Sampling and fresh small-circuit checks were executed before final symbolic-angle guard and overlap-consistency hardening; no changes to sampling probabilities or test references. Independent seed determinism, different seed and correlated basis support smoke checks passed on 3-qubit fixture.
- Browser worker smoke suite passed on final source. Full 105-point harness rerun on candidate before final native precision/guard hardening retained every previous passing ID: 83 PASS / 17 PARTIAL / 1 FAIL / 4 BLOCKED, release eligible=false. Original criteria unchanged. No aggregate criterion promoted. This is not a full Diamond rerun after the final native edits.

## Remaining release blockers

1. RCS-56 and RCS-100 in Opus: eight final amplitude queries remain missing. Additional structural/planner diagnostics failed to find a feasible contraction under the original budgets. No increased limit, fabricated value, or silent approximation was used.
2. Opus actual measured per-stride norm checkpoints (6,453) not rerun; query-only norm results are analytical. The four missing strict amplitude certificates are unresolved. Original committed reference enclosure disagreements require reviewer confirmation.
3. General deeper chaotic circuits, exact Opus RCS sampling, all-mode certification, hardware CPU/GPU cycle telemetry and independent team/host replication remain unresolved. No GPU or separate physical host was used. The full production/UI build was not tested.
4. Do not claim universal polynomial simulation, perfect engine, independently certified release, or 105/105. Keep private engine and evidence archives confidential.

## Reproduce

Linux/WSL, Node 22, Python 3.13, numpy, opt_einsum, mpmath, SciPy for sample scoring. Existing seccomp isolation required for audit. No reference file is passed to execution workers.

```sh
python -B tests/v15-sparse.test.py
python -B tests/v15-integer.test.py
node tests/worker.test.mjs
python -B tests/astra-regression.py execute challenge.json commitment.json new-audit --timeout 120 --workers 2
python -B tests/v14-query-campaign.py challenge.json new-native-query-run --timeout 120 --workers 1
python -B tests/v15-sampling-campaign.py challenge.json new-sampling-run
```

The last sampling command is admitted only for bounded exact-support RCS inputs. The native query route does not claim measured-checkpoint protocol conformance.
