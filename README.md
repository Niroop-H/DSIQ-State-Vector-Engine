# DSIQ State Vector Engine — MAH Quantum

**Confidential experimental research v0.4 — NOT CERTIFIED.** The user-defined Diamond-105 release gate remains closed: 58 passed, 19 partial, 1 failed, 18 blocked, 9 not run in local testing. Individual scope and prior attempts: [report](docs/DIAMOND-REPORT.md) and [raw evidence](diamond-results.json).

DSIQ is an independently authored kernel using adaptive rational phase products, coherent phase-decorated product terms, weighted amplitude DAGs, scaled path replay and an explicit adjoint-Pauli observable-only evaluator. It uses no third-party quantum simulator for execution. Standard mathematical methods are not claimed as new inventions. The 4 MiB hard RAM cap and efficient arbitrary-circuit 50–100 qubit execution are not established. The depth-100 random non-Clifford uncomputation fails within tested budgets. Structured 1,024-qubit tests and a 1,200-qubit forced-replay query are not universal performance guarantees.

## Run locally
Node.js 22+: `node tests/dsiq.test.mjs`, `node tests/coherent.test.mjs`, `node tests/phase-product.test.mjs`, `node tests/observable.test.mjs`, `node tests/worker.test.mjs`. `node --max-old-space-size=3072 tests/diamond.test.mjs diamond-results.json` intentionally exits nonzero until 105/105 pass. External reference/hardware/peer validation must be performed separately. The standalone browser workbench can be served with `python -m http.server 8000 --directory apps/web/public` and opened at `http://localhost:8000/dsiq/`. The standalone UI has no quantum simulator library dependency. The full inherited workbench integration is delivered separately; its production build and browser visual behavior remain unverified here.

See [mathematical architecture](docs/DSIQ.md). Keep this repository private pending intellectual-property and deployment review. Browser-hosted source is inspectable by users; do not publish it before disclosure decisions.
