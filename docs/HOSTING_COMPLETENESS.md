# OPanel hosting functionality audit — 26 October 2026

Target: independent account hosting control panel with native Linux management and optional DirectAdmin/cPanel adapters. Console remains the only commercial/provisioning authority. Source integration is authorized; purchases, deployments, Production migrations and live changes are not.

Reference inventory: https://docs.cpanel.net/cpanel/ (reviewed 26 October 2026). This is a functional benchmark, not a dependency, copied implementation or commitment to proprietary cPanel extensions.

| Functional area | Existing main at d30013f | Required before infrastructure-ready |
|---|---|---|
| Identity | Console PKCE, ownership/service checks, optional gated technical login | MFA/recovery, team roles, distributed abuse controls, deployed HTTPS acceptance |
| Accounts/nodes | Signed bound filesystem worker | Node enrollment, mTLS, key rotation, UID/mount isolation, quotas, revocation, installation/update/recovery |
| Files | Inventory, mkdir, static ZIP inspection/first publish | Read/write/download/rename/delete, concurrency, safe archive handling, permissions, malware scanning, audit |
| Websites/domains | UI and simulation | Real site configurations, aliases/subdomains, redirects, PHP pools, runtime/version control, atomic releases and rollback |
| DNS | Preview and simulation | Authoritative zone CRUD, SOA serials, validation, reload/readback, delegation checks, DNSSEC lifecycle |
| SSL | Simulation | Key/certificate validation and storage, ACME challenges/order lifecycle, renewals, reload/HTTPS readback |
| Databases | Metadata simulation | Scoped MySQL/MariaDB and PostgreSQL database/user/grant/password/export/import operations; integration tests |
| Email | Mailbox metadata simulation | Dovecot/Postfix integration, credentials/quotas, aliases/forwarders/autoreplies, DKIM/SPF/DMARC, spam control, webmail, delivery tests |
| Backups | Simulated resource snapshots | Real file snapshots, integrity checks, restore/rollback, DB/mail consistency, encryption, retention, offsite recovery |
| Metrics/logs | File bytes and optional provider snapshots | Disk/inodes/bandwidth/CPU/RAM accounting, access/error logs, retention, alerts |
| Jobs/runtime | No executor | Durable jobs, deduplication, progress/cancel/reconciliation; cron, PHP/Node/Python supervision |
| Security | Entitlement, CSRF, signed operations, path checks | SSH/SFTP keys, WAF/firewall policy, directory privacy, audit retention/export, rate limits, incident controls |
| Applications | Disabled connector contracts | Qualified WordPress/install/update/staging, GitHub artifact deploy, selected external connectors |
| Vendor adapters | Read-only usage foundations | Account-scoped module inventories/mutations, capability discovery and conformance for each supported provider |
| Operations | CI and default-off deployments | Installer/uninstaller, upgrade/rollback, monitoring, restore drills, supported OS matrix, capacity and failure acceptance |

## Execution policy

Implement engines against disposable local resources, with explicit operation capabilities and trusted operator configuration. Keep customer management routes fail-closed until Console grants and actual adapter resolution are qualified. No simulator is evidence that a server operation works. Do not enable a feature simply because its menu exists.

The native path is a first-class target, not dependent on purchasing cPanel/DirectAdmin. Common open-source infrastructure components (DNS/web/SQL/mail servers) are replaceable service backends, not commercial control panels. Platform qualification cannot honestly be reduced to entering a VPS IP address.

## Current native engine batch

Add bounded descriptor-relative file I/O, real file snapshots and staged restoration, strict DNS zone compilation, static Nginx virtual-host configuration, and certificate/key/SAN/date validation. Every operation remains operator-only and explicitly service-bound. These are backend building blocks, not yet customer API routes or an installed server daemon. The rows above remain open until all listed behaviors have evidence.

## Native engine evidence and operational limits

The new `backend/native_agent/engine.py` dispatcher supports real bounded file list/read/write/mkdir/rename/remove, file-byte accounting, file backup creation/restoration, DNS zone replacement, static website configuration and certificate import. `bridge/hosting_management.py` checks the exact service/binding and fresh operation grant before and after dispatch. No customer HTTP endpoint or live resolver is enabled by this batch.

- `AccountFiles` operates through directory descriptors with no-follow checks. File edits require the previous SHA-256; rename cannot overwrite an existing target. Files are limited to 4 MiB, inventories/snapshots to 1000 entries and 32 MiB. These are safety budgets, not hosting plan quotas.
- Backups contain actual bytes and an exact checksummed manifest. Restores create a new directory, never replace a running site. Paths/depth are preflighted before writes; I/O failures may leave a partial directory and an unknown receipt for reconciliation. Application/database/mail consistency, encryption and offsite retention remain unimplemented.
- DNS supports typed A/AAAA/CNAME/MX/TXT/NS/SRV/CAA, ownership scope, SOA serial preconditions and parser validation. Output stays in private control storage. No server reload, delegation or external resolution is claimed.
- Nginx output is a loopback static virtual host with scoped root, hidden-file restrictions and executable-source denial. It is validated by native tooling in CI, not installed in system configuration. Runtime pools, TLS activation and external HTTP acceptance remain open.
- Certificate imports check PEM sizes, key strength/match, validity dates and requested SAN coverage; material is saved in private versioned storage. Public chain trust, ACME issuance/renewal and TLS activation are explicitly not verified.
- A private SQLite journal records started/succeeded/unknown outcomes and request IDs. Duplicate IDs cannot repeat mutations. This is synchronous execution/reconciliation, not a background task queue or scheduler. An interrupted started request needs operator reconciliation, never blind retries.
- Control storage must be private, operator-owned and outside the account root; persisted identity binds it to one service/binding/root. Thread/process locking serializes cooperating worker operations. OS account isolation is still required against non-cooperating writers; these libraries alone are not an operating-system sandbox.

Tests: `DEBUG=true python backend/manage.py test bridge`. Native validation requires Nginx and BIND's `named-checkzone`; set `OPANEL_REQUIRE_NATIVE_TOOLS=true` to make their absence fail. CI does this on disposable Ubuntu resources and prevents package services from auto-starting. No real server should be connected until the open rows above and external acceptance are complete.
