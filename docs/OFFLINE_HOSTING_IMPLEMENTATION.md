# Offline hosting implementation — 26 October 2026

Owner authorizes completing and merging OPanel code without buying hosting or a VPS. Main is source integration, not authorization for Production deployment or live provider changes. Root/frontend deploymentEnabled remain false.

Implement a distinct local practice workspace with persistent simulated resources and domain-specific validations: domains/subdomains, DNS, SSL lifecycle, websites/releases/rollback, files, databases, email, backups/restore and activity. It must say simulation throughout, never fabricate certificates, send mail, resolve DNS, provision accounts or write to hosting roots. Browser and backend tests use temporary isolated storage. Customer live routes remain governed by fresh Console grants and qualified provider adapters.

Acceptance: cross-workspace isolation; revision conflicts and duplicate request replay; domain dependency rules; typed DNS validation and CNAME conflicts; simulated certificate status; release rollback; backup restoration; confirmed destructive actions; CSRF; default disabled practice API; responsive forms and real persisted API round trips. Preserve existing tests and current Console contract. Review, publish, qualify CI, then owner-authorized merge to main without deployment.

Known boundary: simulated feature completeness is not live provider implementation. Native transport, OS isolation, real vendor operations, ACME issuance, mail delivery and real backup recovery still require future server qualification.

## Goal alignment and remaining implementation

The target remains a standalone hosting control panel with two backends: native Octalve server management and optional DirectAdmin/cPanel adapters. Console alone owns commercial accounts, entitlement and provisioning policy. No rented infrastructure is necessary for this batch.

Implemented source includes independent frontend/backend, Console SSO and entitlement checks, gated technical login, provider read-only foundations, bounded native filesystem operations and first static publication on disposable roots. The new `/practice/` pages implement persisted simulated workflows. They are a development/acceptance surface, not the live technical modules and not proof of cPanel feature parity.

Still to implement and qualify: native DNS/webserver configuration and reload, ACME certificate issuance/renewal, database/user/grant operations, mailbox and delivery services, real backup/restore, resource accounting, scheduled jobs, server enrollment/transport/OS isolation and provider mutations. Shells or metadata transitions must never be marked as completion of these operations. Further offline work should implement typed operation contracts and local service integration tests, then connect the same management views through capability-gated APIs. Use disposable local services before buying any server; real-host acceptance is a later release gate.

Review corrections: dependency checks cover both domain deletion aliases; populated directories cannot become files; practice identity uses its own signed HttpOnly, SameSite=Strict, path-scoped renewable 24-hour cookie, without extending customer sessions. Mobile editors have bounded scrolling. Regression tests cover each integrity/lifetime issue and the short-phone DNS editor.

Source merge is explicitly authorized by the owner. This supersedes earlier draft-only/source-merge restrictions, but does not authorize deployments, purchases, Production migrations or live hosting operations. Deployment configuration remains disabled at both repository and frontend roots.
