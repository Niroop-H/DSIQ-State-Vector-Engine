# DSIQ Operator Workbench

MAH Quantum Research Institute
Engine developer: Devashri S Industries, MAH Quantum.

## Implemented functionality

- Full-width circuit authoring above a dedicated numerical execution record.
- A pure black UI with an expandable OpenQASM source editor, local file import, fullscreen circuit focus and compact parameter controls.
- Visual circuit editor supporting 1 to 100 qubits and up to 2,048 visual gate operations.
- The existing DSIQ JavaScript Worker performs actual amplitude, observable and supported sampling computations.
- A parser-backed circuit inspector reports qubits, expanded gate operations, active wires, multi-qubit gates, qubit dependency depth, measurements and resets.
- Results include amplitude components, the basis probability derived from numerical amplitude, available norm/observable readings and actual sampled counts.
- A volatile session register retains at most 12 completed experiments, with source digests and the option to replay exact input parameters.
- Complete JSON experiment and session evidence exports, plus basic same-origin browser security headers.

## Execution and validation

The Validate and inspect action calls the same parser as the worker's execution path. Inspection reports structure only, not performance or mathematical certification.
The Execute circuit action uses the existing DSIQ Worker. Outputs shown in the execution record are produced by the worker, not placeholder values.
Re-execute selected run loads the previous circuit and parameters, invokes the worker again, and adds the new result to the session record.

## Operational security boundary

This public Vercel interface distributes browser JavaScript, which is inspectable by visitors. No proprietary native binary128 backend is distributed here.
The session history exists only in browser memory and is not a signed, tamper-evident or centralized audit log.
Access control, operator identity, role permissions, production telemetry, confidential project isolation, disaster recovery, formal validation and defence-specific assurance are separate engineering and approval requirements.
Do not use this public page for classified or operationally sensitive circuits without a separate vetted deployment and its required security controls.

## Regression commands

node tests/workbench-operator.test.mjs
node tests/circuit-editor.test.mjs
node tests/worker.test.mjs
node apps/web/public/dsiq/ui-contract.test.mjs

## Deployment

Vercel project: dsiq-research-workspace.
GitHub repository: Niroop-H/DSIQ-State-Vector-Engine, main branch.
Public browser computation only; no confidential native source included.
