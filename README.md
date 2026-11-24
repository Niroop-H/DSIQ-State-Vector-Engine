# DSIQ State Vector Engine

DSIQ is MAH Quantum's CPU quantum circuit simulation research project. It supports selected exact-state queries and complete fixed-excitation sectors, with explicit resource limits. It is not a demonstrated arbitrary 100-qubit dense-state simulator.

**Scientific release gate: closed.** See [scientific status](docs/SCIENTIFIC-STATUS.md) for dated evidence and historical baselines. Project-run tests do not establish independent replication.

## Quick start (authorized evaluators)

Linux x86-64, Python 3.12, NumPy 2.3.5. Obtain written evaluation permission from the owner before reproducing proprietary source; public visibility is not a license.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python benchmarks/global/wide_statevector.py
python benchmarks/global/excitation_check.py > excitation-results.json
python benchmarks/global/supplemental_validation.py
```

See [native candidate guide](docs/NATIVE-RESEARCH-CANDIDATE.md) and [JSON input guide](benchmarks/global/WIDE.md). The repository does not require npm installation for these commands.

## Evidence and limitations

- [Simulator standings](benchmarks/evidence/simulator-standings.md): project-run selected-output comparisons; not a universal speed ranking. Native and JavaScript timings are separate.
- [Diamond-105 matrix](docs/DIAMOND-105-EVIDENCE-MATRIX.md): historical detailed assessment.
- [Independent review protocol](docs/INDEPENDENT-REVIEW.md): external blind evaluation and replication remain pending.
- [Novelty review](docs/NOVELTY-EVIDENCE-REVIEW-2026-11-24.md), [industrial acceptance plan](docs/INDUSTRIAL-ACCEPTANCE-PLAN-2026-11-24.md), [evidence reconciliation](docs/VALIDATION-EVIDENCE-RECONCILIATION-2026-11-24.md).
- [Changelog](CHANGELOG.md), [security policy](SECURITY.md), [contribution guidance](CONTRIBUTING.md).

No claim of independent certification, arbitrary full-state execution at 100 qubits, GPU qualification or production readiness.
