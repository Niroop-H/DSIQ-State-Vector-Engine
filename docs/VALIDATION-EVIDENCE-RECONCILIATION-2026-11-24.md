# Validation evidence reconciliation — 2026-11-24
Status: document audit only. No new executions or independent endorsement.

| Evidence | Scope | Qualification |
|---|---|---|
| [README](../README.md), November 23 gate | 87 pass / 13 partial / 1 fail / 4 blocked | Gate closed; retain original run and per-ID records |
| [Detailed matrix](DIAMOND-105-EVIDENCE-MATRIX.md) | Earlier detailed statuses | Not interchangeable with November 23 status snapshot |
| [v0.16](V016-CANDIDATE.md) | 60 known circuits, 566 queries | Missing Opus measured checkpoints; two original strict-reference discrepancies |
| [Standings](../benchmarks/evidence/simulator-standings.md) | Project-run named external software comparisons | Independent algorithms/software, not independent evaluator or replication |
| [Independent protocol](INDEPENDENT-REVIEW.md) | External 20-case challenge and clean-team replication | Execution and attestation pending |

## Reviewer handoff
Follow the existing independent protocol without lowering criteria. Freeze candidate commit and source/archive hashes; evaluator preregisters challenge and references using authenticated commitments. Operator receives no expected numerical answers before committing raw results. Separate engineering team reproduces on clean hardware. Preserve every failure, timeout and unsupported request. For tiny nonzero amplitudes use relative as well as absolute error; for zeros use absolute error. Distinguish measured from analytical norms. Obtain independent adjudication of the two strict-reference discrepancies. Do not count known challenge replay as blind validation.

## Diamond-70 investigation
Earlier detailed matrix records resource exhaustion on 100-wire depth-100 randomized non-Clifford forward/inverse workload. Reconcile exact current case against November 23 raw evidence first. Record forward midpoint queries independently before inverse; cancellation alone is not evidence of forward execution. Sweep fixed budgets and log planning, node/term counts, visits, peak RSS, time, and completion. Preserve original test unchanged; diagnostic easier cases cannot replace it.

## Attestation (blank until actual evaluator completes)
Evaluator/team identity and independence; date; source SHA; machine and dependency manifest; challenge/reference/output hashes; reference algorithm; per-query errors; all incomplete outcomes; conflict disclosures; signed conclusion and scope. No self-certification of Diamond 100/105.
