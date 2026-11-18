# Independent scientific verification — DSIQ v0.12

**Research only. Do not self-certify Diamond #100 or #105.** A cryptographic commitment authenticates bytes, not the evaluator, authorship, hardware, reference correctness or the difficulty of a circuit. Reviewer and operator must exchange hashes through an authenticated external channel before revealing answers. No reference values should be sent to the DSIQ operator before the result is committed. Never supply secrets in fixture inputs.

## Prerequisites and frozen source

Use a clean Linux x86-64 or aarch64 machine with Node 22, Python 3.13, GCC, libseccomp2 and test-only Python dependencies in `tests/reference-requirements.txt`. Follow the exact frozen source archive/commit supplied to the reviewers. Record the OS/kernel, CPU/accelerators, physical RAM, runtime versions and installed package versions (`node --version`, `python --version`, `python -m pip freeze`, `lscpu`, `uname -a`). CPU counters require actual Linux perf hardware permissions/support; absence is an explicit incomplete measurement. The native headless audit limits the address space to 2 GiB by default (1–4 GiB permitted) and denies sockets and scratch writes; this is a trusted-code audit, not a general hostile-code sandbox. Larger experiments require a separately configured and documented host/runner; do not silently change the budget. Set `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1` during numerical regression.

```
python -B tests/blind-campaign.py freeze > source-manifest.json
```

Exchange the returned `sourceSHA256` in advance. Manifest includes production DSIQ modules, native sources, tests, checklist, complexity and independent-review protocol. Reviewers should also retain the archive SHA-256 and Git commit SHA, if applicable. Do not modify code after receipt of mystery circuits; if fixes are needed freeze a new candidate, preserve the failure and generate a fresh challenge.

## #100 — 20 mystery circuits (external evaluator)

The evaluator independently designs exactly 20 circuits, each 50–100 qubits, collectively including QFT, random circuit sampling (RCS), QAOA and uncompute. Independently select meaningful depths, randomness, topologies and scientific queries, including nontrivial intermediate evolution for uncompute. Use actual external numerical/or analytic references, without deriving expected answers from DSIQ. The protocol tests deterministic complex amplitudes, Pauli observables and norms; validate sampling distributions separately against external references when the RCS workload requires them. A family label alone does not establish sufficient depth or randomness. Reject trivial fixtures or absolute-tolerance-only checks that could mistake a tiny nonzero amplitude for zero. For nonzero represented amplitudes strict format requires a relative tolerance too. Extremely small values that cannot be represented in JSON binary64 require a separately specified rigorous scaled/log comparison, not silently rounding a nonzero reference to zero. Use zero-state input (explicit X gates for nonzero computational inputs) and q0 as least-significant/rightmost bit. Never use an inverse-circuit cancellation as proof of genuine forward execution.

Challenge JSON schema:

```
{"schema":"DSIQ-blind-challenge-v1","suiteId":"REVIEWER-CHOSEN-ID","circuits":[{"id":"case-01","family":"UNCOMPUTE","request":{"n":50,"gates":[...],"method":"adaptive","requireCertificate":false,"checkpointEvery":100,"queries":[{"id":"mid-a","kind":"amplitude","prefix":20,"bits":"<50 bits>"},{"id":"final-a","kind":"amplitude","prefix":40,"bits":"<50 bits>"}]}}]}
```

The full fixture must contain 20 circuits, and prefix numbers are executed gate counts. Each gate is `{name,q,controls,theta?,phi?,lambda?,piTheta?,piPhi?,piLambda?}` (documented DSIQ primitive gates; lower composite gates consistently in both independent sources). `piTheta` is a pair of decimal integer strings for a rational multiple of pi. Pauli queries use `pauli` instead of `bits`; norm queries need neither. The strict headless certified path uses binary64 supplied angles, not exact unknown real angles. `checkpointEvery` is a declared positive stride (default every gate); every requested query prefix is evaluated as well. `maxBytes` and `maxWork` control coefficient/work budget per query; outer process has cumulative timeout and address-space limit. `maxNodes` may set 1..1,000,000 subject to width admission. For strict certificates use method `certified-auto` (default) or `certified-factor` / `certified-contraction` and `requireCertificate:true`. For other unitary tests use `adaptive` / `contracted` with `requireCertificate:false`. Unsupported operations or budget exhaustion fail closed.

Only evaluator retains `reference.json`:

```
{"schema":"DSIQ-blind-reference-v1","suiteId":"REVIEWER-CHOSEN-ID","referenceMethod":"External algorithm/version and generation records","circuits":{"case-01":{"mid-a":{"real":0.25,"imag":0.0,"absoluteTolerance":1e-13,"relativeTolerance":1e-9},"final-a":{"real":1.0,"imag":0.0,"absoluteTolerance":1e-13,"relativeTolerance":1e-9}}}}
```

The displayed snippets are schematic, not test data. All circuit/query IDs and output fields must match precisely. Tolerances must be positive, absolute at most 1e-13, relative at most 1e-9. Reference values for norm/observable are real. Reference answers and salt stay with evaluator until result submission.

1. Evaluator: `python -B tests/blind-campaign.py commit challenge.json reference.json commitment.json reveal-private.json`. Send **only** challenge + commitment and authenticated hash. Do not share reveal-private or reference.
2. Operator: `python -B tests/blind-campaign.py execute challenge.json commitment.json blind-run --source-sha256 <frozen-source-hash> --timeout 120 --limit-mib 2048`. Uses individual isolated audited workers; output directory must not exist. Submit raw evidence directory and its output manifest SHA-256 to evaluator **before** reveal.
3. Evaluator: verify recorded source and output commitments, reveal references/salt, and independently run `python -B tests/blind-campaign.py score challenge.json commitment.json reveal-private.json blind-run --output-sha256 <recorded-output-manifest-hash>`. Recompute/verify every reference independently, review workload adequacy and sampling evidence. Keep failed or timed-out cases; do not replace them with easier ones. Score never sets `test100Certified=true`.

Reviewers should use their own signed statement of independence, reference methodology, exact scope, 20 case source hashes, numeric errors, failures and conclusion. No generated signature or placeholder identity constitutes approval.

## #105 — separate engineering team / clean hardware

Archive exact frozen source, install prerequisites independently, run the original complete suite and supplemental tests in a new output directory:

```
python -B tests/run-campaign.py --external --out replication-runs
python -B tests/v12-audit.test.py
```

Run the blind fixture on the second hardware environment with the same frozen source and reference commitment. Submit original logs, hardware/environment metadata, raw values, independent reference outputs, and evidence hashes. Never treat matching aggregate pass counts as full replication. The comparator verifies hash integrity, source identity and either the exact deterministic query output fields of a common blind challenge or the per-ID status correspondence of two full campaigns:

```
python -B tests/replication-check.py operator-blind-run reviewer-blind-run
python -B tests/replication-check.py operator-campaign reviewer-campaign --kind campaign
```

The campaign comparison does not prove equality of all deterministic scientific outputs. The independent team must compare them separately and explain any documented floating-point/runtime differences; timings and resource readings are inherently host-dependent. Missing tests and external engines remain incomplete. Independent reviewers must sign an actual conclusion only after reproducing the original requirements. The comparator never sets `test105Certified=true`.

## #102 / #103 — scientific audit interface

```
python -B native/scientific-audit.py --limit-mib 2048 --timeout 120 < request.json > run-audit.json
```

Raw worker results contain amplitude/observable/norm certificates for every successful strict query and every recorded intermediate norm, actual gate-prefix counts, wall time, CPU user/system time, RSS and heap/array metrics; process tree hardware CPU cycles are read with Linux perf if available (raw value and enabled/running time, not inferred from elapsed clock frequency). GPU is explicitly unused in this CPU-only path. All unavailable counters are null with a reason. An invalid, unsupported, nonfinite or unaffordable strict request does not emit a successful numerical result. Exact dyadic arithmetic evaluates represented binary64 gate coefficients; outward-rounded interval/operation bounds enclose ideal results at supplied binary64 angles on the supported gate domain. It does not establish error relative to arbitrarily specified exact real numbers. Connected contractions evaluate prefixes separately; actual coefficient evolution or contraction is performed, not just norm=1 asserted. The UI's `Strict certified auto` mode rejects sampling and selects certified factor or connected contraction; other modes are not thereby certified. The headless audit interface is not yet comprehensive telemetry for every browser/native/GPU run. Both #102/#103 remain partial until their original universality and instrumentation obligations are met.

## Local rehearsal, never external evidence

`python -B tests/v12-peer.test.py --evidence /tmp/dsiq-review-rehearsal` generates a public deterministic **local** 20-case fixture (structured RCS/QAOA, QFT and connected uncompute), creates and scores commitments and compares two clean source-directory copies on the same machine. It is a protocol and numerical regression test, not a mystery third-party audit or cross-hardware reproduction. `--local-smoke` is permitted for protocol tests only. No self-authored results may transition #100/#105 to PASS.
