# OPanel implementation batches — 27 October 2026

This is the authoritative execution order for the remaining hosting-control-panel programme. It reorganizes the verified inventory in HOSTING_COMPLETENESS.md and the unmerged lifecycle work; it does not restart the product or renumber historical PRs. Historical documents describe their original snapshots. A batch number here is a delivery boundary, not a claim of cPanel parity or a calendar estimate.

## Product boundaries

- OPanel lives entirely in octalve-core/octalve-opanel, with its own frontend, backend, tests and deployment configuration. Console remains the customer, ownership, commercial and provisioning authority.
- Two execution paths: OPanel's native Linux service backend, and optional account-scoped DirectAdmin/cPanel adapters. Native operation must not require buying either commercial panel.
- Login integration conflict must be resolved explicitly: Console's documented 25 October contract says one Console customer identity and no second OPanel customer credentials; current OPanel main also contains a default-off technical-login feature from a later OPanel request. Do not enable or expand that feature implicitly. Batch 8 reconciles the contracts and records the chosen customer flow before release; this batch makes no authentication change.
- No purchases, real provider/server mutations, public ACME orders, payments, provisioning, Production migrations or deployment are authorized by source implementation. Existing source-merge authorization applies after review and CI; release approval is separate.
- Privileged settings and credentials stay server-side. Customer input never selects arbitrary filesystem roots, executable commands, provider URLs, service identities or administrator APIs.
- Frontend availability follows verified service ownership, fresh operation grants and actual adapter capabilities. Example/practice views remain labelled; generated configuration and successful command exits do not prove live operation.

## Batch register

All batches require security/error-path tests, review, exact-commit CI and recorded PR/merge evidence. Customer-facing batches additionally require desktop/mobile browser acceptance, accessible forms, truthful pending/error states and customer language. Backend-only batches do not pretend to add customer pages.

| Batch | Deliverable and scope | Prerequisites | Acceptance evidence |
|---|---|---|---|
| 1 — Durable operations foundation | Encrypted local job/result storage; subject-scoped idempotency; worker leases; queued cancellation; recurring schedules without catch-up storms; bounded default-off worker cycle; safe receipt inspection | Existing bound engines and Console grants | Actual SQLite concurrency/restart tests; revoked/wrong-binding grants denied; expired writes stay unknown; no replay; secrets absent from reports; real temporary file execution |
| 2 — Encrypted component backups | Required-component manifests; files/PostgreSQL/mail exporters; per-component versus quiesced consistency; authenticated encryption; immutable local/S3-compatible storage; verified recovery into isolated components | 1 | Real encrypt/store/fetch/decrypt roundtrip; wrong key/tenant/tamper/truncation rejected; exporter failure rejects whole request; qualified native exporter tests; no occupied-service restore |
| 3 — DNS and static site activation | Typed domains/aliases/subdomains; authoritative zone activation; syntax checks; durable activation intents; reload/readback; delegation diagnosis; atomic static releases/rollback | 1; existing DNS/web/file engines | Disposable BIND/Nginx service tests; injection/ownership failures; crash/readback/reload failures; previous configuration retained; controlled DNS/HTTP probes |
| 4 — Application runtimes | PHP pools and approved versions/extensions/settings; Node/Python process supervision; restricted systemd configuration; deployments, health checks, restart and rollback | 3 | Actual disposable runtime starts/HTTP checks; user/path/process limits; failed release restores previous service; no arbitrary privileged shell |
| 5 — SSL lifecycle | Maintained ACME client; HTTP-01 first; scoped DNS-01/wildcards when supported; issuance/orders; renewal scheduling; HTTPS activation/readback and expiry alerts | 1,3; DNS authority for DNS-01 | Local ACME/Pebble fixtures and native TLS acceptance; invalid material rejected; renewal failure/timeout stays truthful; public CA/domain proof later |
| 6 — Customer file management | Capability API; read/download/edit/mkdir/rename/delete; safe chmod; resumable bounded uploads; conflict checks; archive extraction budgets and quarantine/scanning | 1; qualified resolver | Real API-to-engine temporary files; CSRF/cross-service/path/link/overwrite tests; interrupted upload resume; mobile forms/confirmation; quota refusal |
| 7 — Database administration | Scoped MariaDB and PostgreSQL database/user/grant/password lifecycle; connection details; safe import/export; isolated restore drivers and backup integration | 1,2 | Disposable real databases; least privilege and cross-account denial; dump/restore data comparison; failed import recovery; no account-provisioning authority duplication |
| 8 — Customer identity and access qualification | Reconcile Console SSO versus legacy optional technical-login contract; single-use launch/expiry/logout/suspension tests; Console-owned MFA/recovery and scoped team roles; abuse controls | 1; read current Console contract | Actual isolated browser flow; replay/wrong ownership/revocation denied; no duplicated customer authority; explicit contract decision recorded; no Production auth changes |
| 9 — Email hosting | Dovecot/Postfix mailbox credentials/quotas; aliases/forwarders/autoreplies/Sieve; DKIM/SPF/DMARC; spam controls; webmail session integration; mailbox recovery | 1,2,3,5,8 | Disposable SMTP/IMAP delivery and isolation; no open relay; spoofing/loop/quota tests; actual mailbox restore; external reputation/PTR acceptance later |
| 10 — Node lifecycle and isolation | Signed enrollment/mTLS, key rotation/revocation; dedicated UID/mount/process isolation; account disk/inode/resource limits; worker supervision; supported OS installer and health inventory | 1; runtime architecture from4 | Disposable VM/container isolation tests as appropriate; wrong-node/revoked key denied; install/restart/uninstall safety; deny live execution until host isolation passes |
| 11 — Security and account tools | SFTP/SSH key lifecycle; confined scheduled customer tasks; directory privacy; IP/WAF policy; audit retention/export; incident controls; restricted API tokens | 8,10; web layer3 | Boundary/privilege/command-injection tests; key revocation; cron scope/limits; protected-directory checks; auditable policy changes; no unrestricted root terminal |
| 12 — Usage, logs and alerts | Disk/inodes/bandwidth/CPU/RAM accounting; bounded access/error logs; usage history; quotas/alerts; operational job backlog and failure metrics | 1,3,4,9,10 | Measurements from disposable workloads; reset/rotation/retention tests; no invented zero usage; tenant log separation; thresholds and delivery deduplication |
| 13 — Backups and disaster recovery completion | Integrate DB/mail restore drivers, safe retention and legal-hold policy, key rotation/recovery, scheduled account backups, offsite drills, selected-component restore/rollback | 2,7,9,10,12 | Restored files/SQL/mail match checksums/data; lost-node/key scenarios; interrupted transfer/restore recovery; retention cannot delete only recovery copy |
| 14 — Provider adapter completeness | Account-scoped DirectAdmin and cPanel inventories/mutations for supported modules; provider capability/version discovery; common conformance suite and failure translation | Relevant native/module contracts;8 | Simulated provider failure tests first, then authorized real account read-only and mutation qualification; reseller/admin authority never exposed |
| 15 — Applications and connectors | WordPress install/update/staging/restore; GitHub artifact releases; selected DNS integrations; dependency/version policies | 2–8,10; relevant module qualification | Real disposable application operation, signed/verified artifact handling, restricted credentials, update rollback; no paid proprietary-panel dependency |
| 16 — Product and release qualification | Finish all technical inner-page API/UI wiring; responsive/accessibility acceptance; installer upgrades/rollback; migrations/recovery planning; supported OS/capacity/failure matrix; operator runbooks | 1–15 | End-to-end exact build with real isolated services; crash/disk-full/network failures; cross-tenant checks; upgrade and restore drills; owner release acceptance |

These batches are sequenced delivery work, not permission to expose earlier native features before Batch 10's OS isolation and Batch 16's release gates. If a batch is too large for one reviewable PR, split it into named sub-batches with evidence; do not silently drop requirements or claim the whole batch complete.

## Detailed implementation decisions

**1:** Preserve the existing reviewed JobStore and receipt correlation; add a single bounded operator cycle, disabled unless explicitly enabled by trusted code. Inspection provides evidence only and cannot relabel uncertain mutations as successful. This is a local operator library, not a distributed queue, installed daemon or production scheduler. Retention maintenance and key rotation remain assigned to 10/13.

**2:** Use external 32-byte AES-GCM keys, unique random nonces and authenticated service/binding/snapshot context. Required component failure fails the entire backup. PostgreSQL single-database snapshots and Dovecot mailbox synchronization are not cross-component consistency; only a trusted quiescence window can establish that. Use immutable object names, conditional writes and readback digests. Local store tests prove roundtrip logic, not offsite disaster recovery. Native exporters run only against disposable fixtures. Driver-specific bounded limits must be documented; no unsupported unlimited-upload claim.

**3–5:** Separate configuration generation, activation and externally observed serving state. Each activation journals intent before mutation, validates, retains the previous revision, reloads, verifies and records rollback where appropriate. Timeout means uncertain. Runtime executables, users, ports, paths and approved versions are operator configuration. ACME staging/local acceptance is distinct from public trust and successful renewal. DNS delegation and registrar authority stay outside a customer zone-edit operation.

**6–9:** Reuse fresh Console ownership and scoped management grants at the API boundary and at execution. Explicitly confirm destructive operations; use revisions/preconditions. Frontend success requires a verified backend outcome. Passwords and raw provider errors never enter audit records. Imports/restores target isolated resources first. Console owns customer identity; mailbox/database/SFTP credentials are scoped technical resources, not a replacement customer login.

**10–16:** Validate supported OS/kernel/systemd combinations, quotas and privileged boundaries on disposable hosts. Implement installation and upgrades as versioned, recoverable operations. Each optional provider advertises only proven capabilities. User-facing text describes actions and errors, not internal frameworks, schemas or development workflow. Full hosting readiness includes install/upgrade/restore evidence, not merely menus or passing unit tests.

## Research and source ledger

Primary sources reviewed 27 October 2026; revisit exact versions before each batch implementation. These are interoperability/behaviour references, not copied proprietary source or mandatory commercial dependencies.

| Source | Design consequence | Batches |
|---|---|---|
| https://docs.cpanel.net/cpanel/ | Functional benchmark includes files, domains, SQL, email, metrics, security and application tooling; the six-area table alone is incomplete | All |
| https://sqlite.org/lang_transaction.html | One writer; transactions may contend. Sample default lease time after acquiring write lock; do not promise fleet-scale queue semantics | 1 |
| https://docs.celeryq.dev/en/stable/userguide/tasks.html | Task delivery/retry and execution are separate; automatic retries require idempotence. OPanel instead preserves ambiguous writes for reconciliation | 1 |
| https://cryptography.io/en/latest/hazmat/primitives/aead/ | Authenticate context as well as payload, never reuse a nonce with a key, reject wrong-key/tampered ciphertext | 1,2,13 |
| https://www.postgresql.org/docs/current/app-pgdump.html | Single-database consistency does not cover files/mail or cluster-wide roles; restore scripts require controlled trust | 2,7,13 |
| https://doc.dovecot.org/main/core/man/doveadm-sync.1.html | Mail backup is mailbox-aware synchronization; source and destination selection and destructive destination behaviour need explicit control | 2,9,13 |
| https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html | Conditional writes prevent accidental object replacement; use maintained SDK signing, immutable names and separate readback verification | 2,13 |
| https://bind9.readthedocs.io/en/v9.20.18/manpages.html | Zone/config validation and reload control are distinct steps; qualification must query resulting authoritative state | 3 |
| https://nginx.org/en/docs/control.html | Reload may retain the old configuration; a command return alone cannot establish the intended site is serving | 3,4,5 |
| https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html | Isolation controls depend on kernel/system manager support; generated configuration is insufficient evidence | 4,10,11 |
| https://letsencrypt.org/docs/challenge-types/ | HTTP-01 uses port80 and cannot issue wildcard certificates; DNS-01 needs scoped DNS authority | 5 |
| https://eff-certbot.readthedocs.io/en/stable/using.html | Reuse maintained ACME tooling with controlled directories and renewal lifecycle; do not accept customer hooks | 5 |
| https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/ | Stream/stage bounded uploads; application resource limits and publication validation remain required | 6 |
| https://docs.directadmin.com/developer/api/ and https://api.docs.cpanel.net/ | Version and account scope each provider operation; commercial panel APIs are optional adapters, never native dependencies | 14 |

## Status and continuation

Batch 1: implementation/qualification in progress. Existing reviewed queue commits `1e876ae` and `8300355` are included; operator-cycle additions and merge evidence are recorded in BATCH_01_ACCEPTANCE.md. Batches 2–16: pending, not implemented by this plan.

Next batch prompt is in [NEXT_BATCH_PROMPT.md](NEXT_BATCH_PROMPT.md). Batch 2 must re-read current main, this register, research and the previous acceptance report before editing; do not repeat Batch 1 or assume a server exists.
