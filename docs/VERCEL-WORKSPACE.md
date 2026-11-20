# DSIQ Scientific Workspace | Vercel Hosting

## Scope

This site runs the DSIQ JavaScript computational worker from `apps/web/public/dsiq/worker.mjs` in the visitor's browser. Its results are produced by the existing engine, not mock data. This front end is not the native C/Python binary128 numerical-contraction runtime. The native implementation stays private and is not a Vercel Function.

## Deployment

- Connect the private repository `Niroop-H/DSIQ-State-Vector-Engine` to Vercel.
- Use **Root Directory** `apps/web/public/dsiq`.
- **Framework Preset** `Other` (no Node build step).
- Publish the static contents of that directory. Its `index.html` serves `/`.
- Require Vercel Authentication (or equivalent SSO/access controls) for **all** deployments. No public launch is authorized prior to completion of the laboratory release criteria.
- Do not enable Public Source or deploy the repository root. The repository root includes native engine source and private scientific materials that must not be web-served.
- Grant access only to explicitly authorized researchers. Do not share deployment URLs publicly until access controls have been tested.

## Available interactions

The UI supports restricted OpenQASM circuit editing, amplitude queries, selectable JS representations, available Pauli expectations, seeded measurement counts, configurable computational budgets, execution cancellation, evidence JSON downloads with a circuit SHA-256 digest, and three *on-demand* analytical diagnostics. Unsupported requests and resource-boundary failures are shown as errors, not substitute results.

## Local validation

From the repository root:

```sh
node tests/worker.test.mjs
node tests/dsiq.test.mjs
node apps/web/public/dsiq/ui-contract.test.mjs
```

The UI contract test checks markup and worker wiring; it does not replace a real browser end-to-end test. Chrome/Firefox integration testing should be performed against the protected Vercel deployment before any researcher receives access.

## Limits

- Browser execution uses client CPU and memory, not the native binary128 backend.
- Numerical precision, sampling, accessible gates, and query budgets differ by method.
- A correct result on a 100-qubit *structured* circuit does not imply efficient performance for every 100-qubit circuit.
- Diamond-105 release qualification remains open according to documented evidence. The site is a controlled research interface, not a certification assertion.
- The JavaScript code served to authenticated visitors is inspectable by those visitors. If the complete browser engine is also confidential, use a server-side isolated computation architecture instead of distributing it as client-side code.
