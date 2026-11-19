# DSIQ v0.16 | Numerical regression milestone

**Private engineering candidate — 19 November 2026. Scientific release gate remains CLOSED.**

Frozen scientific source fingerprint: `ec11c1a0114b71a47e9ae404ac5ce7c8af283be18a00348512b4df5c2277877a`.

## Final frozen-source results

| Known suite | Query-complete circuits | Numerical queries | Measured checkpoints | Elapsed campaign |
|---|---:|---:|---:|---:|
| Astra Medium | 20/20 | 165/165 | 336/336 | 24.424 s |
| Opus | 20/20 | 180/180 | NOT_RUN on query-directed route | 108.406 s |
| Astra High | 20/20 | 221/221 | 460/460 | 30.421 s |
| Total | 60/60 | 566/566 | 796 measured (Astra only) | — |

All numerical tolerances retained: absolute error <= 1e-13; relative amplitude error <= 1e-9 for nonzero reference amplitudes. All request-specific budgets retained. Workers used the original 120-second wall/CPU and 2048 MiB address-space limits, with two concurrent workers per campaign. No paid resources were used. No references are inputs to the execution workers. These are known-challenge regressions scored after execution, not new blind tests. Astra Medium uses the prior recomputed reference score (the original salted reveal was lost). Opus uses the original rounded committed references for numerical scoring; Astra High uses the revealed 80-digit reference values.

## Last two failures resolved

| Opus case | Query result | Wall time | Peak RSS | Cumulative work on final amplitude | Request work limit |
|---|---:|---:|---:|---:|---:|
| RCS-56 | 7/7 | 53.751 s | 233144 KiB (227.68 MiB) | 654208000 | 1000000000 |
| RCS-100 | 8/8 | 45.703 s | 188988 KiB (184.56 MiB) | 796916084 | 1000000000 |

Strict RCS-56: all four formerly missing final amplitudes returned bitwise equal to rounded committed complex references; largest reported relative bound among those four is 8.791e-17. RCS-100: ordinary numerical route, not certified. The maximum explicit array forecasts were 151013440 and 151702112 bytes, respectively. No uncontrolled process signal in the 20-case Opus campaign.

## Implementation

- Scope-derived hypergraph and pairwise contraction planning; local region dynamic programming and seeded tree annealing, without embedded challenge plans.
- Native binary128 complex center contraction (`__float128`), using outward propagated radii from dyadic/interval gate factors, accumulated roundoff estimates and output rounding bounds. This is an experimental certificate implementation; independent formal verification of compiler, arithmetic and numerical assumptions is pending.
- Resource-bounded seven-product fast complex matrix multiplication, with intermediate addition operations charged to the work model and scratch space included in preallocation forecasts. This is an ordinary numerical path and is not used to assert certified arithmetic.
- Budget admission, plan-scope verification, isolated worker execution and fail-closed fallback. No change to the original Diamond criteria, reference values or numerical tolerances.

## Error and certificate results

| Suite | Maximum absolute error | Maximum relative amplitude error | Strict bounds <= 1e-13 | Strict nonzero amplitude bound <= 1e-9 |
|---|---:|---:|---:|---:|
| Astra Medium | 5.3333e-17 | 9.4194e-17 | 66/66 | 22/22 |
| Opus | 7.2387e-16 | 7.5775e-11 | 68/68 | 33/33 |
| Astra High | 5.5429e-17 | 1.0157e-16 | 88/88 | 31/31 |

Of the 222 strict query certificates, 220 enclose the originally scored references; all 222 enclose references when two prior independently diagnosed Opus Pauli discrepancies are evaluated against the diagnostic values. Original Opus references remain unchanged. The diagnostic is a 100-digit dense calculation for QAOA-100/final_pauli_5 and an exact global-X symmetry argument for QAOA-50/final_pauli_3. This is not an independent reviewer adjudication. All 86 strict nonzero-amplitude relative tolerance bound checks pass. Astra High measured norm drift is zero at binary64 output precision, not a proof of exact floating-point norm preservation.

## New validation

- 14 fresh randomized 4–6-qubit circuits; 496 amplitude comparisons per new backend, 992 total, against an independently coded 100-digit dense reference. All passed, with 496 relative certificate checks.
- Maximum fresh binary128 absolute error 2.7055e-17; relative error 1.0083e-16. Maximum fresh fast-matrix absolute error 3.2273e-16.
- Four exact integer-valued complex matrix product comparisons and rejection of a tampered contraction plan passed.
- Browser worker regression smoke tests passed. The v0.16 native path is not thereby validated as a browser implementation.

## Release blockers and honest claim boundary

The 100% milestone is numerical coverage of these 60 known circuits, **not** 100% completion of all scientific criteria. Opus's query-directed route uses analytical unitarity for norm answers and does not supply all requested measured checkpoints (6453). Its audit manifest records this distinction and does not implement the full original reviewer protocol. The original strict-reference enclosure comparison retains two discrepancies. New blind reviews, independent engineering-team replication, complete hardware telemetry and more general dense/chaotic workloads remain open. CPU hardware cycle counters were unavailable; GPU not used. The latest full Diamond run was the v0.15 intermediate run, 83 PASS / 17 PARTIAL / 1 FAIL / 4 BLOCKED; not rerun for v0.16. Previous 100000-shot Astra High sampling (15/15 known-suite marginal tests) is v0.15 evidence only; Opus sampling not run. No source publication or repository update was performed in this turn.

A conventional dense complex128 statevector stores 16 * 2^n bytes (about 2.028e31 bytes for 100 qubits). Selected exact-state query algorithms exploit structure and do not materialize every coefficient. This demonstrates a useful alternative to dense storage for tested workloads, not general superiority over named optimized simulators, not a polynomial-time solution to arbitrary circuits, and not a novelty claim. Same-task external performance comparisons and fresh independent blind validation are still needed.

## Reproduction environment and integrity

Linux x86_64, Python 3.13.5, GCC 14.2.0; original test dependencies in `requirements-query-native.txt`. The two native helper shared objects were compiled locally with GCC (`-O3 -march=native -shared -fPIC` for region DP; `-O3 -fPIC -shared -fno-fast-math` for quad, linked to libquadmath and libm). The portable source build script omits `-march=native`; timings and time-bounded planning may vary across systems. No compiled binaries are distributed in the source archive. The scientific source fingerprint covers engine, native and test sources and selected original scientific documents via `tests/blind-campaign.py`; README and this report are packaging metadata. The two Astra manifests bind the fingerprint and assert source unchanged. Opus manifest binds raw outputs and challenge; post-run source snapshot matches the Astra fingerprint but the Opus wrapper does not itself attest the source hash. Private evidence retains exact inputs, revealed reference scoring material, raw per-case files, manifests, and separate score reports.

Rebuild helpers using `sh scripts/build-query-native.sh /tmp/dsiq-native`; export both paths printed by the script and set `OPENBLAS_NUM_THREADS=1`. Run `python -B tests/v16-native.test.py` and `node tests/worker.test.mjs`. Use `tests/astra-regression.py execute ... --timeout 120 --limit-mib 2048 --workers 2` for the two Astra tests, and `tests/v14-query-campaign.py ... --timeout 120 --workers 2` for Opus query-only evaluation. Inputs must be supplied unchanged, and scoring must be performed separately. The source archive does not contain challenge answers or precomputed contraction plans.
