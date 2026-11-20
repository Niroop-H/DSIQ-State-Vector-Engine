# DSIQ factor-statevector optimization — 20 November 2026

## Engineering scope

Post-v0.16-frozen-source performance work on the `main` engineering branch. This change does **not** retroactively update the frozen v0.16 challenge source fingerprint, the 566-query campaign or Diamond-105 statuses; the scientific release gate is not declared open.

### Changes

1. The adaptive selection planner prefers exact factor-statevector evolution for admitted 16–31-qubit circuits composed of independent interaction components, where the earlier planner generally attempted the weighted decision-diagram path first. This is a gate-topology decision, not a benchmark-family recognizer; gate order and every gate are retained.
2. The factor evolution inner loop performs complex matrix multiplication with scalar temporaries, eliminating per-basis-pair temporary complex-array allocations. FP32 arithmetic retains the previous explicit rounding stages. No amplitude pruning, approximation, Schmidt truncation or output substitution is added.
3. The factor sampler builds read-only cumulative distribution arrays once per unchanged state, reusing them for subsequent shots. Gate operations and arbitrary unitary application invalidate the cache before state mutation. Requested sampling-scratch budgets are checked even on cache hits.
4. Sampling cache telemetry now reports `samplingScratchBytes`, `samplingCDFBuilds`, `samplingCacheHits`, and `samplingInvalidations`. The scratch bytes do not represent total process RSS.

### Measured local before/after results

Both versions were executed with Node.js 22 in seven separate processes on the same test environment. Reported values below are **medians** of the recorded samples, not universal complexity bounds:

| Structured workload | Previous code | Optimized code | Median improvement |
| --- | ---: | ---: | ---: |
| 20 qubits, four independent five-wire non-Clifford blocks, 224 gates; execution and amplitude query | 49.759 ms | 5.921 ms | 8.40× |
| 50 qubits, ten independent five-wire blocks, 2,160 gates; factor evolution | 26.752 ms | 19.929 ms | 1.34× |
| Same 50-qubit circuit, 5,000 seeded samples | 44.929 ms | 14.738 ms | 3.05× |

These circuits are highly structured; results do not establish any speed advantage on deeply connected random 45–100-qubit circuits or over Aer, QuEST, cuStateVec or other third-party systems.

### Executed checks

- `node tests/adaptive-factor-optimization.test.mjs`: 256 amplitude comparisons against independently calculated five-qubit dense component references, maximum observed error `1.5636586103463756e-18`; correct norm, single CDF build for 512 samples and cache invalidation on gate / arbitrary unitary changes.
- `node tests/factor.test.mjs`: factor differential checks, FP32 reference, deep 100-qubit structured circuits, 1,024-qubit components.
- `node tests/worker.test.mjs`: all worker mode cases.
- `node tests/dsiq.test.mjs`: 1,920 dense complex-amplitude checks, max error `2.0651342011721887e-15`.
- `node tests/advanced-v05.test.mjs`, `node tests/parallel.test.mjs`, `node tests/frame-factor.test.mjs`, `node tests/rank-frame.test.mjs`, `node tests/observable.test.mjs`, `node tests/coherent.test.mjs`.

Run reproducible benchmark sources with `node benchmarks/dsiq-adaptive-components.mjs` and `node benchmarks/dsiq-factor-sampling.mjs`. Compare against the prior commit using matched hardware and Node flags. Do not compare unrelated Vercel and local numbers.

### Engineering limits

- This optimization applies to the factorized-state path only and cannot avoid the worst-case exponential complexity of arbitrary connected quantum states.
- Cache lifetime tracks formal `apply` and `applyUnitary` mutations. Directly modifying exposed typed-array internals is not a supported mutation API.
- Holding a reference to an old sampler after mutating its engine is not supported; call `sampler()` again for the updated state.
- The retained CDF has a separate scratch allocation check. The source coefficient budget alone does not cap all runtime memory.
- The earlier 100-qubit deep randomized uncompute release gate (#70) remains unqualified.
- Full operational / defence certification and independent external review are separate work.
