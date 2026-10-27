# Hosting service lifecycle implementation plan

Goal: implement the six outstanding areas through tested, independent service components, retaining explicit external acceptance requirements.
Base: 77a56c79c558afe15501915bb2e53fa107e512f7.

Global constraints: OPanel repository only. Console owns commercial identity/provisioning; operation grants are fresh and exact service/binding. No purchases, deployments, Production migrations, public ACME requests or live provider changes. User already authorizes implementation and verified source merge. Default-off activation; tests use disposable local roots/services. No simulator or successful command exit is external acceptance.

Execution: subagent-driven sequential implementation tasks with task review and final review. Research uses official sources. Root records task interfaces and evidence here. Unknown mutation outcomes require reconciliation, never automatic retry.

1. Durable encrypted jobs, worker leases, cancellation, scheduling and receipt reconciliation.
2. Encrypted component backups, consistency evidence, immutable offsite transfer/restore contract, scheduled backup integration.
3. Validated DNS/site activation and rollback, runtime configurations and controlled execution, readback verification.
4. ACME issuance/renewal orchestration and TLS activation with staging/local acceptance.
5. Scoped customer file operations API/UI, permission controls and larger staged uploads.
6. Cross-module integration, failure/security/native tests, source publication and merge.

Remaining external evidence: actual delegated domain/registrar authority, public CA issuance, offsite provider credentials, supported runtime binaries, node OS isolation, production host behavior and authorized release. Features blocked by missing evidence must stay unavailable.

## Batch programme mapping

The owner requested numbered delivery batches on 27 October. [IMPLEMENTATION_BATCHES.md](../../IMPLEMENTATION_BATCHES.md) now defines execution order and acceptance. This plan remains the historical technical decomposition: task1 maps to Batch1; task2 to Batch2; task3 spans Batches3–4; task4 to Batch5; task5 to Batch6. Cross-module qualification is required per batch and again in Batch16. Completing Batch1 does not complete this six-task lifecycle plan.
