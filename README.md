# DSIQ State Vector Engine

DSIQ is a native CPU quantum circuit simulation research project from MAH Quantum. The [native candidate guide](docs/NATIVE-RESEARCH-CANDIDATE.md) describes the supported workloads, installation and reproducible checks. The [package verification workflow](.github/workflows/native-research-candidate.yml) builds a source archive and exercises its public entry points in an extracted directory.

| Scientific question | Available evidence |
|---|---|
| Can DSIQ evolve an entire occupied state-vector sector at 100 qubits? | [Direct excitation-sector tests](benchmarks/evidence/excitation-results.json) compare all 4,950 reachable amplitudes on a two-excitation circuit. |
| Can it answer queries on circuits with gates that change excitation count? | [Connected-chain tests](benchmarks/evidence/wide-results.json) compare selected amplitudes, norm and an observable on 50- and 100-qubit circuits. |
| How does the adaptive engine perform against dense Qiskit Aer? | [Five public QASMBench circuits](benchmarks/evidence/global-cpu-45160826893.json), 10–22 qubits. The two engines return the same requested amplitudes; the faster engine varies by circuit. |

**Full-engine scientific release gate: closed.** The [November 23 release-gate run](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45161076880) recorded 87 pass, 13 partial, one fail and four blocked. The native package is a research candidate for reproduction. Fresh blind circuits and separate-team replication remain open under the [independent-review protocol](docs/INDEPENDENT-REVIEW.md). Public distribution terms are pending an owner decision.

[Packaged candidate verification](benchmarks/evidence/native-candidate-45163019894.json) records 33 passed cases including 24 wide cases across three seeds. [Download the verified candidate and raw outputs](https://github.com/Niroop-H/DSIQ-State-Vector-Engine/actions/runs/45163019894/artifacts/14812701658).

## Earlier engineering reports and Studio documentation

The following sections describe versioned milestones and the inherited Studio. Some installation instructions and file references apply to its larger upstream checkout.

# DSIQ State Vector Engine v0.16 — private engineering candidate

**566/566 known numerical regression queries, 60/60 query-complete circuits. Scientific release gate CLOSED.** Native scope-derived contraction planning, binary128 precision escalation and bounded fast matrix contraction. See `docs/V016-CANDIDATE.md` for the verified results, exact scope and unresolved release blockers.

Documentation: [v0.16 release and verification status](docs/V016-SYNC-STATUS.md) · [Diamond-105 evidence matrix](docs/DIAMOND-105-EVIDENCE-MATRIX.md) · [frozen source manifest](SCIENTIFIC-SOURCE-MANIFEST.json). The native query path is not validated as a browser implementation. The historical v0.15 intermediate result was 83/105 PASS.

Research build; the Diamond-105 scientific release gate remains closed. New in v0.13: bounded 192-bit outward-rounded coherent product sums, single-use graph-bridge block-forest contraction, incremental headless prefix evolution and crash-resilient audit journaling. Certified-auto zero-shot browser queries use the new selector. See `docs/COMPLEXITY.md` and `tests/v13-interval.test.py`. Known reviewer challenges are regression evidence only, not new blind validation.  New in v0.10: direct monomial frame queries and bounded native basis streaming, actual full dense comparison on a connected 25-qubit circuit, native-host real/complex bond and compact affine tensor contraction, randomized internal fixture-independence audit, and a manual named-external-oracle workflow. See `docs/DSIQ.md`. The native host backend uses NumPy for numerical linear algebra only and is not browser-integrated. New in v0.9: invertible GF(2) displacement-rank coordinate reduction for Clifford-frame evolution and a commuting-Pauli measurement planner that supports nonmonomial final Clifford frames for bounded active rank. Run `node tests/rank-frame.test.mjs` for full encoded-support comparisons against an independent extended-precision reference. Retained from v0.8: Clifford reference-frame factors, coherent affine output projection, pair contraction with explicit index-scratch forecasts, certified connected dyadic queries, and deeper norm/denormal validation. See `docs/COMPLEXITY.md`. Retained from v0.7: double-layer contraction for conditional sampling, normalization and Pauli queries; affine parity elimination; preallocation forecasts; exact represented-coefficient dyadic arithmetic; certified FP64 factor arithmetic; and a resource-limited Linux audit runner. Default coefficient budget is 64 MiB (browser maximum 512 MiB); no universal memory bound is asserted. Retained from v0.6: memory-bounded amplitude tensor contraction and coherent slicing, analytical open-chain TFIM evolution in an admitted vacuum chart, direct multi-controlled RY, native threaded factor evolution and full-basis streaming comparisons of structured circuits. Run `python -m pip install -r tests/reference-requirements.txt` for test-only reference dependencies; run `node tests/native.test.mjs`, `node tests/parallel.test.mjs`, and `node tests/ladder.test.mjs` for targeted regressions; `node --max-old-space-size=3072 tests/diamond.test.mjs diamond-results.json` for the full fail-closed acceptance gate. No unconditional universal efficiency or total-process 4 MiB guarantee. See `docs/DIAMOND-REPORT.md` and raw results.

Experimental independent DSIQ numerical module under the existing 1000+ workbench. See [DSIQ architecture and limitations](docs/DSIQ.md). Run `node tests/dsiq.test.mjs` before building the inherited web project. The standalone DSIQ interface may be run without npm dependencies: `python -m http.server 8000 --directory apps/web/public` then open `http://localhost:8000/dsiq/`.

---

# MAH Quantum™ Development Studio

Developed by **Devashri S Quantum**. A free-to-use, proprietary-source browser-local quantum circuit simulator with a visual composer, executable OpenQASM editor, and circuit transpiler. No API key, paid service, or backend is required for the studio.

**Current research scope (November 2026):** exact dense statevector simulation through **20 qubits**, selected exact Clifford/separable/partitioned calculations in the **100-qubit Studio**, and a **1,000–4,096 logical-qubit research workspace** for mathematically tractable families. These are classical simulations, **not** access to a physical quantum processor or unrestricted universal thousands-of-qubits computation. See [scalability](docs/SCALABLE_QUANTUM_ENGINE.md), [1000+ tools](docs/1000PLUS_SCIENTIFIC_INDUSTRIAL_WORKBENCH.md), and [validation evidence](docs/TECHNICAL_VALIDATION_20_QUBIT.md).

## Workspace

- **Composer:** edit targets, controls, angles, and measurement destinations; reorder operations; undo/redo. Supports H, X, Y, Z, S, T, I, RX, RY, RZ, U, CX, CZ, SWAP, CCX, barriers, and terminal measurements.
- **Code:** import, edit, compile, and run the supported static OpenQASM 2/3 subset, now including exact lowering for `cp`, `cu1`, `crx`, `cry`, `crz`, `rzz`, `cy`, `ch`, `cswap`, `ccz` and `iswap`. Circuit and code share one validated program model. Download QASM or export a Qiskit Python script; Python is not executed in the browser.
- **Inspector:** step through ideal evolution, inspect amplitudes and phases, Bloch vectors, reduced-state purity, and Pauli expectation values.
- **Transpiler:** eliminate adjacent inverse/identity gates, fuse rotations, decompose to U + CX, and optionally route to bidirectional nearest-neighbor connectivity. Routing restores logical ordering; equivalence is up to global phase. Preview before applying.
- **Results:** reproducible seeded shot sampling, observed versus ideal histograms, statevector tables, and CSV/JSON downloads. Simulations run in a cancellable Web Worker.
- **Projects and jobs:** local draft autosave, up to 30 saved circuit snapshots and 20 recent jobs, restore/rerun, JSON import/export. Browser storage is device-specific; export backups before clearing it.
- **Examples:** Bell, GHZ, Grover search, Deutsch–Jozsa, phase interference, and Toffoli circuits.
- **Visuals:** MAH Quantum branding, dark gold workspace, optional animated 3D-style quantum core, and reduced-motion support.

## Scope and numerical conventions

The supported **dense statevector** engine executes up to **20 qubits**. The 100-qubit Studio and the separate 1,000–4,096-qubit research workspace switch among exact Clifford stabilizer tableau, exact separable-state, and explicitly bounded partitioned non-Clifford engines as appropriate; unsupported entangled circuits fail visibly. Workload and shot limits vary by workspace/solver. The OpenQASM parser supports a documented static subset of QASM 2/3, not arbitrary QASM 3 control flow. Browser execution has no physical QPU connection, IBM account, mid-circuit measurement, reset, classical branching, loops, pulse scheduling or arbitrary user-defined gates. This is independent classical simulation, not IBM Quantum feature parity.

Bit strings use the highest bit on the left (`q[n-1]…q[0]`, or classical `c[n-1]…c[0]` for explicit measurements). Unmeasured classical bits remain zero. Without explicit measurements, all qubits are sampled. Statevectors and inspector values describe ideal evolution before terminal measurement.

Optional generic noise uses normalized Monte Carlo trajectories for amplitude damping, pure dephasing, stochastic Pauli errors, and asymmetric readout errors. T1, T2, and gate time use the same units; T2 must not exceed 2×T1. This is not a calibrated hardware model. Noisy runs are limited to 16 million shot × operation × state-size work units to keep browser workloads bounded. The displayed statevector remains an explicitly labelled ideal reference; no fabricated fidelity score is shown.

## Development

```bash
npm install
npm run dev:web
```

Use the local URL printed by Vite. A separate backend is unnecessary for browser execution.

```bash
npm test
npm run build:web
npm run build:engine
```

The test suite covers basic quantum math, QASM round trips and diagnostics, measurement mapping, seeded sampling, Bloch vectors, Pauli expectations, Grover search, noise behavior, validation, gate decompositions, and routed state equivalence. Production web assets are emitted to `apps/web/dist`. Existing Vercel configuration is retained.

## Code organization

- `apps/engine/src/studio/`: shared program validation, safe QASM parser, serializers, simulation, and transpilation.
- `apps/engine/src/math/` and `simulator/QuantumCircuit.ts`: complex matrix and statevector operations.
- `apps/web/src/`: React workspace, local persistence, and simulation worker.
- `api/circuit/simulate.ts`: optional compatibility endpoint using the same simulator and validation.
- `apps/engine/src/server.ts`: optional Express server (`npm run dev:engine`).

The compatibility endpoint accepts `qubits`, optional `bits`, `steps`, `shots`, `seed`, and `noiseModel`. Browser jobs do not call it. Legacy HTML/PDF manuals describe the earlier interface; use the in-app Guide and this README for current behavior.

## License

Proprietary software. Copyright © 2026 MAH Quantum™. This checkout has no top-level license file.

## Quantum technology workbenches

Dedicated pages: `/studio` (Quantum Computing), `/lab` (Quantum Lab Twin), `/sensing` (Quantum Sensing & Metrology), and `/communication` (Quantum Communication & Cryptography). The new workbenches compute locally without paid APIs.

See [the laboratory architecture, equations, operator exercises and deployment guide](docs/QUANTUM_LAB.md). Optional stateless Python service configuration is in `render.yaml`; the frontend does not require it.

## Full-page hardware playground

`/lab` now opens the configurable Quantum Playground: ten hardware models, connected optical and thermal signals, Explore/Study/Research modes, five guided goals, parameter sweeps, measurement exports and project save/import. The original four transient exercises are at `/lab/operations`. Read the [playground operator and physics guide](docs/PLAYGROUND.md).


## Scientific/industrial integration status

The **1,000+ Qubit** console includes reproducible large-circuit research models, computed connectivity and measurement graphs, sampled-run comparisons, a searchable **reference-only** equipment atlas, and a **2–10-variable p=1 QAOA/MaxCut** experimental optimization bench with an exhaustive classical optimum.

**Industry Integration Bridge** (controlled pilot): documented `/api/v1/capabilities`, `/api/v1/execute`, and `/api/v1/batch` APIs; strict server-only Bearer key; bounded supported QASM execution and weighted MaxCut; Python client and SHA-256 evidence. Browser-local work remains free, with no server credentials required. See [interoperability contract](docs/INDUSTRY_INTEROPERABILITY_V1.md), [OpenAPI](docs/openapi-industry-v1.yaml) and [Python SDK](sdk/python/README.md). The server API is disabled until a strong private `MAH_QUANTUM_INDUSTRY_API_KEY` is configured on the host. Never put the key in `VITE_` settings or a browser.

**Physical Hardware Bridge** provides *customer-side* read-only SCPI/TCP and Modbus/TCP telemetry gateways and offline unverified browser previews; SCPI single-sweep operation is locally gated by independently qualified operator and safety checks. This is not a certified production controller or a live machine connection from the browser. OPC UA, VISA/USB, general PLC control, arbitrary lab actuation and real QPUs are **not connected**. See [equipment integration and safety requirements](docs/PHYSICAL_EQUIPMENT_INTEGRATION.md).

To run the local test suite and compile the web/engine:

```bash
npm ci
npm test
npm run build:web
npm run build:engine
node scripts/verify_industry_routes.mjs
python -m unittest discover -s sdk/python -p 'test_*.py'
```

Passing offline CI does not establish third-party instrument compatibility, production safety certification, hosted API availability, quantum advantage, or commercial SLA readiness. Commissioning requires qualified vendor/site validation.

## Scientific Hamiltonian and variational diagnostics

The **1000+ Qubit** research console now includes a **Hamiltonian Lab** for statistically rigorous I/Z/ZZ diagonal observables over actual sampled bitstrings, editable and importable Ising coefficients, per-term expectation tables, sampled energy spectrum, Z–Z moment matrix, finite-shot confidence intervals, shot-budget planning, and SHA-256-linked analysis exports. The industrial MaxCut/QAOA bench additionally exports and visualizes all **324 actual multiscale γ/β objective evaluations**.

These are executed *classical numerical experiments*. The Hamiltonian lab is not a general molecular chemistry, VQE, non-diagonal Hamiltonian, hardware calibration, or ground-state solver; the QAOA module uses only 2–10 decision variables, not the 1,000+ circuit engine. View [scientific equations, input contracts and validation](docs/SCIENTIFIC_HAMILTONIAN_ANALYSIS.md). Hardware and commercial operational capabilities remain limited as described above.

### License and release boundary

The hosted browser experience may be used without a subscription, but the source is **UNLICENSED / proprietary**. Free use does not grant open-source modification or redistribution rights. Industrial use of real equipment requires separate vendor/site qualification.

## Security and correctness audit

The [November 2026 34-point remediation ledger](docs/SECURITY_CORRECTNESS_AUDIT_2026_11.md) records the fixes, regression tests and residual distributed/hardware deployment limitations. Passing CI is not a physical certification.

## Five-hour execution allowance (first stage)

The **Studio, 1000+ Qubit workspace and industrial QAOA workbench share 20 execution launches**, followed by five hours of cooldown after the last credit. With `MAH_QUANTUM_QUOTA_SECRET` configured server-side, the same-origin `/api/usage` route checks a volatile HMAC-hashed network address; the browser never reads or stores a network identifier. **Clearing browser data does not reset the allowance within the same running server instance**. If the endpoint is unavailable, the UI visibly switches to browser-only fallback credits that can be reset by clearing site data. The separate browser access-code policy remains unchanged.

The server-authenticated industry API separately limits a network address to **20 execute jobs** and then a **five-hour cooldown** (batch operations consume multiple credits; inspect-only jobs do not). Both the browser quota endpoint and industry API use temporary HMAC network digests, not stored raw IPs. Their counters are process-local and cannot guarantee enforcement across serverless instances or restarts. A shared short-lived server-side quota store and genuine user accounts are required to make the limit durable. See [execution credits, privacy, setup and deployment limitations](docs/WORKSPACE_ACCESS.md).

**Remaining roadmap:** durable account/project identity, distributed rate limits and jobs, CPU/GPU backend adapters, expanded QASM dynamic control, third-party mathematical conformance, instrument qualification and commercial service terms. These features are not delivered by the execution quota change.

### v0.11 scientific campaign

New headless execution paths: untruncated QR MPS (`native/mps_exact.py`) and all-assignment native coherent slicing (`native/sliced_bond.py`). These are separate from the deployed/browser engine. The full original 105-point release gate remains authoritative. Run `python tests/run-campaign.py --external` with the documented Python/Node dependencies to produce a timestamped, hash-bound campaign record; named reference tests are attempted only when their actual optional packages are present. No certification is issued unless the original criteria are all satisfied. Independent blind review and reproduction remain external obligations.

### DSIQ v0.12 — independent review and strict audit

The first priority is original Diamond #100, #105, #103 and #102. See [independent-review protocol](docs/INDEPENDENT-REVIEW.md). The new challenge runner verifies prereveal source/result commitments, a strict 20-case format and full query coverage; local smoke tests are not independent evidence. The exact-output replication comparator does not certify reviewer identity or clean hardware. `native/scientific-audit.py` exports CPU and RSS telemetry and actual intermediate norm checkpoints, with real hardware cycle counts only where Linux perf is available. `certified-auto` emits certified factor/contraction results only on its supported unitary domain or rejects; browser selection requires zero shots. Original requirements are unchanged, and the release gate remains closed unless all 105 actually pass. Run `node tests/v12-additions.mjs` for targeted local protocol and strict numerical validation. See the versioned report for observed status, not an assumed approval.


## v0.14 experimental engineering candidate (release gate closed)

See `docs/V014-CANDIDATE.md` for exact scope, opt-in native execution and unresolved findings. Historical Diamond results and v0.13 release artifacts are not new v0.14 acceptance evidence.
