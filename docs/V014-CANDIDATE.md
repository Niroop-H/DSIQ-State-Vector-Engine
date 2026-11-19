# DSIQ v0.14 engineering candidate — private validation report

**Release gate: CLOSED.** This is an experimental, opt-in native query backend, not a production release or a rerun of the original Opus acceptance protocol. The frozen v0.13 GitHub main build remains unchanged. Do not distribute this archive to reviewers. No proprietary implementation was transmitted to an outside reviewer.

## Implemented changes

- Compact tensor-factor construction with exact inverse cancellation and CX–diagonal–CX parity-phase fusion.
- Algebra-aware backwards observable cones and exact bra/ket terminal-index linking, including Y phases and X/Y complement constraints.
- Graph-based elimination portfolio with allocation forecasts, separate pairwise contraction fallback, and explicit work/memory/separator boundaries independent of physical wire order.
- Experimental extended-precision outward Euclidean-radius contraction using the existing fixed-grid gate intervals; includes binary64 projection and relative bounds. Its elementary rounding assumptions are platform-dependent and still require wider validation.
- Opt-in Linux query worker with process-group supervision, inherited address-space/CPU limits, seccomp restrictions, and partial-result recovery. Strict requests are never downgraded to the uncertified path.
- Legacy audit recovers the last acknowledged process metrics, and classifies failures from concrete signal/diagnostic evidence rather than assuming physical OOM.

## Frozen engineering source

Source manifest SHA-256: `98374cd6ae6ec313919cbb57ef0f59d40c16e4e3cbfc5c429d69179e252771d6`. This is a local candidate fingerprint, not a signed or externally timestamped release. The original Diamond criteria are unchanged. Source and reference evaluation were separate processes; the previous references were already known, so these are regressions, not blind challenges.

## Opus query-only regression

| Metric | Result |
|---|---:|
| Cases with all requested numerical queries returned within tolerance | 18/20 |
| Numerical queries within tolerance | 172/180 |
| Maximum absolute discrepancy against rounded committed references | 7.238637797e-16 |
| Maximum relative amplitude discrepancy | 7.577406811e-11 |
| Returned strict interval outputs | 64 |
| Enclosed rounded reference | 63/64 |
| Strict absolute radii ≤ 1e-13 | 64/64 |
| Strict nonzero amplitude relative bounds ≤ 1e-9 | 26/29 |
| Uncontrolled termination signals | 0 |
| Wall time, three parallel workers | 26.356 s |
| Peak reported child RSS | 496004 KiB |

All 26 explicit norm queries in this campaign are **analytic unitarity proofs**, not state measurements. Per-stride norm checkpoint measurements were NOT_RUN. Consequently these are query completeness results and cannot be counted as official Opus circuit passes. The same 120 s wall/CPU limit and 2048 MiB address-space cap were applied per worker; the native implementation charges its own conservative work units, not a calibrated equivalent of the legacy engine counters.

| Case | Numerical queries | Result |
|---|---:|---|
| UNC-100 | 13/13 | QUERIES_COMPLETED |
| UNC-96 | 10/10 | QUERIES_COMPLETED |
| UNC-60 | 12/12 | QUERIES_COMPLETED |
| RCS-80 | 7/7 | QUERIES_COMPLETED |
| QAOA-64 | 9/9 | QUERIES_COMPLETED |
| RCS-99 | 7/7 | QUERIES_COMPLETED |
| QAOA-70 | 9/9 | QUERIES_COMPLETED |
| RCS-64 | 7/7 | QUERIES_COMPLETED |
| QFT-73 | 8/8 | QUERIES_COMPLETED |
| QFT-57 | 8/8 | QUERIES_COMPLETED |
| RCS-100 | 4/8 | INCOMPLETE |
| QFT-88 | 8/8 | QUERIES_COMPLETED |
| QFT-50 | 8/8 | QUERIES_COMPLETED |
| QAOA-50 | 9/9 | QUERIES_COMPLETED |
| UNC-50 | 10/10 | QUERIES_COMPLETED |
| QFT-100 | 8/8 | QUERIES_COMPLETED |
| QAOA-100 | 11/11 | QUERIES_COMPLETED |
| RCS-56 | 3/7 | INCOMPLETE |
| UNC-75 | 12/12 | QUERIES_COMPLETED |
| QAOA-90 | 9/9 | QUERIES_COMPLETED |

## Unresolved observations

- RCS-56 and RCS-100: four final amplitudes each remain blocked by resource forecasts. No increase of the predeclared budgets; alternative bond and affine planner diagnostics also rejected the requests.
- QAOA-100 final_pauli_5: difference from rounded committed reference `5.169606324977803e-22` exceeds the reported radius `5.3312424693202035e-24`. The discrepancy is far below the numerical tolerance, but an independent higher-precision oracle is needed to distinguish under-enclosure from reference uncertainty. Do not count it as a valid certificate pass.
- Three of 29 strict nonzero-amplitude intervals do not certify the requested relative tolerance, even though their returned centers pass the numerical comparison.
- Full actual checkpoint schedule, RCS sampling, CPU/GPU hardware counters, separate-host replication, generic deeply entangled and deep arbitrary random circuits, production browser integration, and the full 105-point rerun remain open.
- The original v0.13 Diamond report remains historical: 83 PASS / 17 PARTIAL / 1 FAIL / 4 BLOCKED. No criterion promoted.

## Preserved and new validation

- Astra known regression via the existing audited route: 20/20 circuits, 165/165 outputs, 336/336 measured checkpoints, 66/66 requested certificates within tolerance and enclosing compared discrepancies. All 22 relative bounds within tolerance. Wall time 9.562 s with three workers.
- 12 fresh randomized circuits at 4–6 qubits against an independently coded 110-digit dense state reference. Both native backends passed 1,112 comparisons each (896 amplitudes, 192 Pauli expectations, 24 measured norms); total 2,224 comparisons. All 327 eligible nonzero amplitudes passed the relative-bound target in the interval backend.
- Independent tiny-amplitude test: approximately 9.999999990000049e-301, relative interval bound 1.4911561772168808e-16. Strict downgrade refusal and isolated measured-norm smoke test passed.
- Legacy strict scientific audit test: 175 certified outputs and 433 measured norm checkpoints passed; browser worker smoke tests passed. The entire Diamond-105 suite was not rerun.

## Reproduce (Linux/WSL with existing Node and Python)

The new route is explicitly opt-in; it does not replace the legacy scientific runner. It requires extended IEEE long double (at least 63 mantissa bits) for its radius backend, Linux seccomp, and the numerical dependencies shown below. Do not mark its output as the measured-checkpoint protocol.

```bash
python -B tests/v14-query.test.py
python -B native/query-audit.py --timeout 120 --limit-mib 2048 < request.json
python -B native/query-audit.py --measure-norms < request.json
python -B tests/v14-query-campaign.py challenge.json private-run --workers 3
```

`--measure-norms` attempts actual double-layer contractions for explicit norm queries. It does not execute all stride checkpoints; those remain NOT_RUN. No reference file is supplied to the execution worker. No GPU resources or additional paid compute used.

Tested versions: numpy 2.3.5, opt_einsum 3.4.0, mpmath 1.3.0. Python 3.13.5. Linux x86-64.

## Decision

Do not release v0.14 to another blind evaluator yet. Preserve v0.13 and use this source locally for research. The source archive is confidential; the historical reviewer packet contains only public interface information.
