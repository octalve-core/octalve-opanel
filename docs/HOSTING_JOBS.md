# Operator hosting jobs

This library provides an encrypted, service-bound local queue and explicit worker
calls. It installs no daemon, HTTP endpoint, CLI, timer or server configuration.
It does not activate hosting workloads or provision authority.

## Trusted API

Construct `native_agent.jobs.JobStore` using an operator-owned private directory,
positive service ID, exact binding reference, and an operator-held 32-byte
encryption key. Keep the key outside customer workloads and browser input; keep
queue and engine control storage outside the account root. The operator must
supply the same key after reopening storage. This API creates no credential store.

`bridge.hosting_jobs.run_cycle(store, engine, *, entitlement, audit,
enabled=False, max_jobs=10, now=None)` performs one bounded cycle. `enabled` must
be exactly `True`; `max_jobs` must be an integer from 1 through 100 (booleans are
rejected). Store and engine service/binding must match before scheduling or
claiming anything. Disabled or invalid cycles raise `Refused` without touching
the queue or schedule occurrence records.

A cycle materializes due schedules once, then calls the existing `run_next` until
it processes `max_jobs` jobs or finds no eligible queued job. Its summary contains
`scheduled` and `processed` counts, state `counts`, and `jobs` containing only
`id` and `state`. It contains no payloads, results or lease tokens. Schedule
materialization can create more jobs than the execution bound; these remain
queued. Missed schedule slots are skipped, and occurrences are deduplicated.
`now` is a trusted operator/test clock override. Omit it in normal execution so
claim and completion retain fresh wall-clock lease checks. Unhandled storage
errors propagate, including failures after a native mutation: an exception does
not establish that nothing executed.

Each job is subject to fresh entitlement checks before and after execution,
existing operation capabilities, explicit mutation confirmation, and audit
boundaries. Enqueueing and schedules do not confer permission. Failed,
cancelled, succeeded and unknown jobs are terminal and are never automatically
retried. An expired running lease becomes terminal `unknown`.

`bridge.hosting_jobs.inspect_job(store, engine, job_id, *, subject_id,
entitlement)` first obtains subject-scoped status, verifies exact engine/store
service and binding identity, and requires fresh authorization for the recorded
operation. Wrong subject, binding or grant is rejected before receipt access.
The returned `job` whitelist is `id`, `operation`, `state`, `created`, `updated`,
`due`, and `schedule_id`. Reading status can expire a running lease to `unknown`;
inspection never promotes a job to success or changes it based on a receipt.

The returned `receipt` is one of:

- `{'state': 'unobserved'}` only for the engine's explicit `Refused('Unknown request.')`.
- `{'state': 'unavailable'}` for unavailable or malformed evidence.
- `state='observed'` plus `request_id`, `operation`, `outcome`, `recorded_at`.

The current `HostingEngine.receipt` schema is `request_id`, `operation`,
`outcome`, `recorded_at`, `result`. Inspection checks request ID and operation,
recognizes `started`, `succeeded`, `unknown`, `rejected`, and validates a finite,
nonnegative numeric timestamp. It excludes `result` entirely: engine receipts
can contain paths or other sensitive operation output. There is no service ID
field in the current receipt schema; service is established by the trusted
engine's configured identity and service-bound journal. No unsupported receipt
field is assumed. Neither inspection response includes payload, result, path,
secret or token fields.

## Bounds and activation prerequisites

- JSON payload/result budget: 6 MiB; at most 1000 retained jobs and 1000 schedules.
- Schedule interval: at least 300 seconds; leases: 1–300 seconds (default 60).
- Engine receipt journal has its own existing 10,000-operation bound.
- Claims are atomic across independent local SQLite instances. This is not a
  distributed claim protocol, multi-host worker service or automatic retry system.

Before activation, an operator must approve the service/account binding, confined
root and private control/queue directories, key custody and backup procedure,
current entitlement resolver, durable audit destination, capabilities, and an
explicit invocation arrangement. Native tool validation and server reload/public
verification are separate prerequisites for the relevant hosting operation.
This change supplies source library behavior only; it does not claim deployment,
server activation or live acceptance.

## Safe recovery

Stop further invocations when storage or audit evidence is unavailable. Restore
access to the same trusted queue, key, engine journal and exact service binding.
Use scoped inspection with a fresh grant and examine authorized account state
through existing tools. Treat `unavailable`, `started` and `unknown` as uncertain;
a `succeeded` receipt is evidence of native execution, not proof that postexecution
entitlement and audit checks succeeded. An `unobserved` receipt alone does not
authorize a replacement write. Preserve unknown jobs and evidence, establish what
actually happened, and obtain fresh confirmation and permission before any
separately planned replacement operation. Never edit queue state to manufacture
success or silently requeue an unknown job.

Retention maintenance, key backup/rotation and recovery are operator procedures.
No automatic retention, pruning or key rotation is implemented or claimed.

Completion failures use typed `InvalidCompletionResult` and `ExpiredJobLease`
(both remain `Refused` subclasses). Only invalid or oversized result encoding
falls back to an `unknown` completion; only a matching expired lease whose
`unknown` transition committed is accepted without another finish. Other lease
rejections, SQLite/I/O failures, unsafe queue files, and fallback storage failures
propagate and stop the cycle before another claim. After a native mutation, such
a failure can leave the job running until expiry; reconcile its receipt and never
resubmit it automatically.
