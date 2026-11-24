# Industrial acceptance plan — 2026-11-24
Status: proposed acceptance criteria, not production qualification. Target: CPU research circuit-query service.

| Gate | Required evidence | Status |
|---|---|---|
| Numerical correctness | Full matched reference results for agreed domain; abs <=1e-13, relative <=1e-9 for nonzero amplitudes in existing strict protocol | Partial, project evidence |
| Scope contract | Document supported gates, precision, output types, bit ordering, limits, unsupported cases; distinguish full sector from full arbitrary state | Partial |
| Resource isolation | Measure total process RAM, timeout, concurrency, cancellation and cleanup under adverse requests; no silent fallback | Pending acceptance run |
| Reliability | Repeated cold/warm runs, deterministic seeds, crash recovery; record every failure | Pending acceptance run |
| Portability | Clean installation on each advertised OS/architecture; dependency and artifact hashes | Pending acceptance run |
| Security | Threat model, parser fuzzing, dependency audit, access control and data retention; trusted-code audit is not hostile-code isolation | Pending acceptance run |
| Auditability | Input/source/output hashes, versions, actual telemetry and error bounds with explicit missing fields | Partial |
| External assessment | Independently reproduced workload and signed acceptance by customer/evaluator | Pending |
| Distribution | Owner-approved license, IP provenance, dependency license inventory, support and vulnerability response | Pending |

## Pilot protocol
Select three customer-defined circuit families, agreed query outputs and budgets, including difficult non-Clifford cases. Freeze input before execution; report hardware, version, seed, error, end-to-end latency, peak RSS, completion and unsupported cases. Keep circuit IP confidential; set deletion schedule and access policy. No hardware validation claim from classical simulation alone. Do not promise arbitrary 100-qubit full vectors. Establish workload-specific latency and concurrency thresholds with customer before tests; publish results including failures. Release only for admitted domain when mandatory gates are independently reviewed.

## Funding milestones
Illustrative INR 100,000 research grant: 25,000 baseline and external challenge preparation; 40,000 optimization and harder workload evaluation; 35,000 replication and reporting. Actual costs and evaluator availability need confirmation. Milestones require evidence, not guaranteed scientific success.
