# Batch 1 — durable operations foundation

Programme: [Implementation batches](IMPLEMENTATION_BATCHES.md). Scope is backend operator libraries, not a hosted scheduler or new customer UI.

## Implementation

- `native_agent/jobs.py`: encrypted service/binding-scoped SQLite queue and results; subject-scoped idempotency; atomic claims; expiring leases; queued cancellation; deduplicated recurring schedules. Unknown outcomes are terminal and are never replayed automatically.
- `bridge/hosting_management.py`: optional trusted request ID links queue jobs, native receipts and audit events while retaining fresh grants before and after execution.
- `bridge/hosting_jobs.py`: conservative single-job runner, explicitly enabled bounded cycle, and scoped receipt inspection. Inspection omits result bodies and never promotes an unknown job to success.
- [Operator API and recovery procedure](HOSTING_JOBS.md): exact bounds, activation prerequisites and remaining key/retention duties.

Local implementation history: `1e876ae` queue; `8300355` reviewed lock/lease timing fix; `b20ca00` cycle and inspection. Remote source publication may use a consolidated commit with an identical tree; the PR records that exact head and its CI evidence.

## Local evidence

After the latest worker additions:

- `DEBUG=true ../opanel-engines/.venv/bin/python backend/manage.py test bridge.test_hosting_jobs`: 43 tests passed.
- `DEBUG=true ../opanel-engines/.venv/bin/python backend/manage.py test bridge --verbosity 2`: 177 tests run, 175 passed, two skipped.
- Full discovery from the backend directory: the same 177 tests, 175 passed, two skipped.
- The two skips require local `named-checkzone` and `nginx`. GitHub native acceptance installs these validation binaries and requires the tests to execute, not skip.
- New worker tests first failed for missing APIs. Lease timing regressions demonstrated two failures before the earlier fix; malformed receipt timestamp regression also failed before guarding the input.

Evidence includes real temporary filesystem mutation, independent SQLite instances, encrypted storage inspection, entitlement revocation, interrupted/expired outcomes, cancelled/duplicate schedules, bounds and safe receipt metadata. No external server or provider account was used.

## Source acceptance gate

Before merging, complete task and whole-branch review, address blocking findings, and verify OPanel SSO, Console contract and native acceptance workflows on the exact published source. PR workflow results and merge commit are the authoritative remote evidence. A local green run alone is not merge or release evidence. Frontend source and deployment configuration are unchanged by this batch.

## Explicit limitations

- No daemon, HTTP job endpoint, installed timer or customer operation page is activated.
- Default-off cycle requires trusted operator wiring, exact binding, capabilities, fresh Console grants and durable audit. Hosted workloads must not access keys or control storage.
- SQLite is a local single-writer store, not a distributed queue. Payload/result limit is 6 MiB; jobs and schedules each retain at most 1000 entries; schedule interval minimum 300 seconds; lease maximum 300 seconds; a cycle executes at most 100 jobs.
- Materializing schedules can enqueue more work than one cycle executes. Capacity errors remain errors, never successful completion.
- Receipt inspection is evidence gathering. It does not automatically retry, undo, repair or certify an uncertain operation.
- Automatic key rotation, pruning, node installation and disaster recovery remain later batches. Existing engine budgets and operation restrictions still apply.
- No Production change, hosting purchase, provisioning, payment collection or deployment occurred.

Next: [Batch 2 execution prompt](NEXT_BATCH_PROMPT.md).
