# DSIQ State Vector Engine

MAH Quantum — confidential research and development. Experimental, not a validated production simulator or a claim of novel patentable mathematics.

DSIQ is an independently authored JavaScript numerical kernel, not a wrapper around a third-party simulator. Its primary representation is a weighted binary amplitude DAG, with on-demand coherent path replay when the DAG node budget is exhausted. It supports the unitary OpenQASM subset documented in the workbench, full-register amplitude queries, and computational-basis sampling in DAG mode. Replay does not sample yet. There is no guaranteed polynomial-time solution to arbitrary circuits, hard process-RAM cap, or complete 2^n array export. Float64 rounding, cancellation and underflow remain possible.

## Run the experimental workbench

From the repository root, run `python -m http.server 8000 --directory apps/web/public` and open `http://localhost:8000/dsiq/` (or serve it with any local static HTTP server). No quantum simulator library or npm install is needed for this module. Run `node tests/dsiq.test.mjs` with Node.js 22+ for numerical checks.

The complete inherited MAH Quantum project is packaged separately as an integrated ZIP; only the DSIQ module, validation and integration instructions are being committed in this first change. Keep this repository private pending review of IP and licensing. The browser-hosted module is inspectable by clients; do not publish it before an appropriate disclosure and deployment decision.
