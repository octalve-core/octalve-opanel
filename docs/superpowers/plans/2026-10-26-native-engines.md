# Native hosting engines implementation plan

Goal: replace selected simulation-only gaps with actual locally testable backend engines, preserving independent architecture and deployment gates.
Architecture: trusted per-account root and separate control storage; descriptor-relative bounded I/O, serialized jobs with durable receipts; pure validated config compilers and real certificate parsing. No arbitrary shell or user-controlled provider endpoints.
Spec: docs/HOSTING_COMPLETENESS.md; existing docs/NATIVE_WORKER_V1.md.

## Constraints and decisions
- Existing user authorization covers implementation and source merge. No further scope or merge confirmation needed; no purchases/deployments.
- Python/Django backend remains; no Console changes or new customer authority.
- Practice remains separate. New native functions never claim external DNS/HTTPS/mail success.
- Root, service ID, ownership evidence, key and capability allowlists originate from trusted operator configuration, never browser fields.

## Tasks
1. Write failing filesystem tests: actual bytes, traversal/link refusal, write digest preconditions, rename/delete confirmations and limits. Implement `native_agent/filesystem.py` with root descriptors and bounded I/O. Run backend suite.
2. Write failing backup tests: capture actual file bytes, verify digests and exact manifest, reject corruption/links/unsafe names, restore only to a new isolated directory. Implement `native_agent/backups.py`. Run backend suite.
3. Write failing config tests: DNS records including MX/TXT/CAA/SRV/NS, zone ownership and CNAME constraints; Nginx injection refusal/static root restrictions; certificate mismatched key/domain/expiry. Implement focused compilers/validator and pin dependencies. Run tests against real parsers; CI validates generated Nginx/BIND config with native tools.
4. Write failing service engine tests: wrong service, disabled capability, reused request conflict, durable outcome/restart, all real engines reached via one trusted dispatcher. Implement operation journal and dispatcher. No HTTP routes.
5. Update audit evidence and runbook, full backend/build/contract CI, one independent branch review, fix important findings with regressions, publish PR and merge verified exact head.

## Review focus
- Path/link/device races and output budgets: filesystem regressions.
- Restores that overwrite or accept corrupt archives: backup regressions.
- DNS/Nginx directive injection and unauthorized names: compiler regressions.
- Certificate private-key leakage, wrong SAN/key: certificate regressions.
- Mutation timeout/replay and permission confusion: dispatcher regressions.

## Ledger
- Pre-flight: file snapshots consume bounded `AccountFiles` operations; dispatcher consumes all engines. Configuration paths are operator-owned. No existing mutation HTTP interface will be expanded.

- Tasks 1–4 implemented and tested: native filesystem, real file backups, typed config/certificate engines, bound dispatcher and fresh grant boundary. Initial suite: 129 tests, two native-tool skips locally; CI requires tools.
- Backup review corrections reproduced RED then fixed: long-name manifests now fit the bounded 2 MiB limit; restore target paths are preflighted before filesystem writes. Suite: 131 tests, two local native-tool skips.
- Native-tool fixture uses only temporary paths and current execution user; system service configuration is never modified by tests.

- Final review: no Critical findings; Important DNS semantic validation finding reproduced RED and fixed. Generated NS records now join duplicate/TTL checks; local NS/MX/SRV aliases are rejected, required in-zone addresses and delegation glue are validated. DNS parsing is not represented as public resolution proof.
- Review scope decisions: non-cooperating writers/hostile mounts and operator storage replacement require OS isolation; installed-node crash/power-loss, reload/public-service acceptance remain release gates. Public certificate trust/ACME, database/mail consistency, quotas/retention and full parity remain open in the audit. Cost of treating these as complete would be unsafe live activation; this batch enables none. Native config tests are mandatory in CI. No minor findings were deferred.
