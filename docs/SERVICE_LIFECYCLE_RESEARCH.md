# Hosting service lifecycle research — 27 October 2026

This implementation builds independent OPanel modules around established service interfaces. A provider adapter remains optional. No server purchase, public certificate request, external storage write, deployment or Production migration is part of research/CI.

## Evidence and design consequences

| Area | Primary documentation | Consequence for OPanel |
|---|---|---|
| Interrupted jobs | https://docs.celeryq.dev/en/stable/userguide/tasks.html and https://github.com/celery/celery/blob/main/docs/faq.rst | Queue delivery is not exactly-once execution. Persist operation IDs before mutation; expire leases to unknown; reconcile receipts instead of replaying writes. |
| PostgreSQL backup | https://www.postgresql.org/docs/current/app-pgdump.html | A dump is consistent for one database, not a coordinated files/mail/application snapshot. Use an explicitly scoped exporter; never copy a running database's raw files and label them consistent. |
| Mail backup | https://doc.dovecot.org/main/core/man/doveadm-sync.1.html | Mail synchronization/backup is mailbox-aware. Record mailbox scope and export evidence; a generic file archive alone is not full mailbox recovery. |
| Encryption | https://cryptography.io/en/latest/hazmat/primitives/aead/ | Use authenticated encryption, random unique nonces, separate operator-held keys, and service/binding/version as associated data; refuse wrong-key/context/tamper. |
| Offsite objects | https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html | Immutable object names, conditional create, content digest verification and independent restore tests; an upload response is not recovery proof. Credentials and bucket/prefix are trusted configuration. |
| DNS operation | https://bind9.readthedocs.io/en/v9.20.18/manpages.html | Validate zones/config before activation, reload only owned zones with configured control credentials, query SOA/records after reload. Nameserver delegation belongs to registrar/Console authority. |
| Nginx activation | https://nginx.org/en/docs/control.html | Syntax checking and reload are separate. Keep previous configuration and verify serving after reload; failures require rollback/reconciliation. No arbitrary customer directives. |
| Runtime confinement | https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html | Dedicated users, restricted filesystem access and privilege controls are deployment requirements. Generating a unit does not prove OS isolation. |
| Certificate automation | https://eff-certbot.readthedocs.io/en/stable/using.html | Use maintained ACME tooling; renew on a schedule, inspect resulting certificate and activate only verified material. Never use customer-provided shell hooks. |
| ACME domain proof | https://letsencrypt.org/docs/challenge-types/ | HTTP-01 needs reachable port80 and does not issue wildcards. DNS-01 needs narrowly scoped DNS authority. Local/staging success is not publicly trusted HTTPS acceptance. |
| Uploads | https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/ | Stream/stage bounded chunks outside public roots, validate quota/digest/type, then atomically commit through the account worker. Do not read arbitrarily large request bodies into memory. |

## Architecture decisions

- Keep current Django/Next.js boundaries and exact Console entitlement contract. A new API must resolve its server-side adapter from verified service binding and capability grants; it cannot accept provider URLs, account roots or administrator credentials from the customer.
- Start with a durable single-node queue suitable for the existing operator-local worker. Do not imply distributed/fleet capacity. Encrypt queued payload/result data; receipt metadata does not contain file bodies or private keys.
- Component backups carry explicit consistency evidence. Missing database/mail exporters must produce unavailable/partial scope, never an apparently complete account backup. Cross-component quiescence is a separate requirement.
- Activation is validate → retain previous → install candidate → reload → read back → success. A timeout is unknown; automatic success from exit0 is forbidden. Restore configuration on definite failed verification, record rollback outcome separately.
- No remote terminal or arbitrary shell command execution is introduced. Runtime executables, service IDs, filesystem roots and operation argv templates are operator-owned.
- Keep feature availability derived from both fresh grants and proven adapter capabilities. Existing simulation pages do not become live operations merely by changing their labels.

## Qualification layers

1. Pure validation and malicious-input tests.
2. Actual temporary filesystem/database/crypto and subprocess tests.
3. Disposable native service integration in CI (DNS/web/TLS/runtime/exporters where available).
4. Actual isolated host acceptance: OS boundaries, public DNS/delegation/ACME, offsite store, restore drills, resource limits.
5. Owner acceptance and explicit Production release.

Only the layers actually executed may be reported as passed. Code implementation cannot remove the need for layers4–5.
