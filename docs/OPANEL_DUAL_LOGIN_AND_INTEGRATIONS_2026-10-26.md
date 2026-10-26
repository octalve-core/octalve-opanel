# Octalve OPanel — Dual login and integrations execution contract
**26 October 2026 · Review only · No Production enablement**

## Two safe access paths (user-approved future growth)

1. **Default:** Console signup/login → owned, paid-term, provider-confirmed hosting → one-time PKCE grant → independent OPanel session. This is the preferred flow and remains unchanged.
2. **Optional:** after the customer FIRST enters OPanel via legitimate Console SSO, they can opt into a distinct **OPanel technical username/password** under Settings. Password hash is stored only in OPanel's own DB and is NEVER sent to Console, printed in an email, or equal to the provider administrator secret. The direct `/login/` form authenticates via OPanel's own `/auth/technical-login/` endpoint, but **each success and each later session use revalidates Console's exact subject/service/provider binding**. Suspension, expiry, ownership/binding change and Console outages fail closed.

**Do not conflate these credentials:** a hosting-provider account user (DirectAdmin/WHM; separate username) is not an OPanel login; WordPress admin is distinct; GitHub installation and Cloudflare zone tokens are different scoped integrations. OPanel user account is never an FTP root, WHM reseller or vendor administrator. Future hosting SFTP/password access must be provisioned/reset through approved provider mechanisms with customer-selected secrets rather than emailed reusable plaintext passwords.

## Implemented in this PR

- `backend/bridge/models.py` and migration `0001_technical_access.py`: service-unique username, owner subject, provider binding UUID, Django salted password hash, enablement and HMAC-keyed durable anti-brute-force throttle. No Console password copy.
- `backend/bridge/technical_access.py`: deterministic `op<base36(service_id)>` account username, strong password checks (minimum 14, mixed character classes), SSO-only enrollment/rotation, direct verification, IP/username throttle and live Console entitlement before new session.
- `backend/bridge/views.py`: `POST /api/technical-access/enroll/` (existing SSO+CSRF), `GET /api/technical-access/` (session scoped), `POST /auth/technical-login/` (CSRF, generic errors, fresh Console revalidation). Exact matching same-origin rewrites in `frontend/next.config.ts`.
- `frontend/src/app/login/page.tsx`, `TechnicalLoginPage`, `TechnicalAccessSettings`: user-facing optional login and password enrollment/rotation. New flag `NEXT_PUBLIC_OPANEL_TECHNICAL_LOGIN_ENABLED=false` controls visibility; backend `OPANEL_TECHNICAL_LOGIN_ENABLED=false` is authoritative.
- Every action continues to be service-scoped and `overview` only. Password login creates **no new management capability**. Repeated wrong attempts trigger lockout, and direct password login cannot re-enroll/rotate its own password without obtaining a fresh trusted Console SSO session.
- Security tests cover enrollment, hashes, wrong customer and binding, Console outage, CSRF, IP/user brute-force control, disabled-by-default behavior, and session revalidation.

**Before Production direct credential login:** qualify persistent Postgres migrations, shared rate-limit behavior across multiple workers, stronger risk controls/MFA where policy requires, password recovery via one-time account-owner-verified claim link, abuse alerts, security logging and owner acceptance. The current first-time setup is through Console SSO only; no password is delivered by email. Keep both flags OFF until these gates pass.

## Hosting-ready email lifecycle (Console-owned)

1. Customer purchases → order/unpaid invoice email (future).
2. Gateway is independently verified → payment confirmed/receipt email (future).
3. **Only when provider read-back confirms actual account** → hosting-ready notice with domain, plan, real provider account username, optional OPanel username, renewal date, Console service link and password-setup instructions.
4. Customer enters OPanel using Console SSO, sets own optional technical password in Settings.
5. Customer can later choose SSO or the separate technical login (after the latter is approved and enabled).

Console implements a queued, idempotent **notice outbox** but actual email delivery remains disabled. Emailing reusable passwords is explicitly forbidden; the optional direct-login password is never persisted in plaintext.

## Modular Integrations — own OPanel boundary

New `Integrations` sidebar module has an independent marketplace for **WordPress**, **Cloudflare** and **GitHub**.

| Connector | Authentication | Minimum hosting capability | Technical privilege boundary | Launch condition |
|---|---|---|---|---|
| WordPress / Softaculous | Verified per-account installer API/controlled token | PHP + MySQL/MariaDB, domain and HTTPS | `wordpress.install` + `database.create` for correct site | Check vendor plugin/license/version and separate WP admin |
| Cloudflare | Restricted token for a zone the customer actually controls | Domain DNS zone proof, not merely hosting-domain attachment | `dns.zone.write` + specific verified zone | Confirm authority/zone ID and preview DNS changes |
| GitHub | Selected-repository GitHub App installation | Static artifact + correct document root; build performed in isolated runner as needed | `files.publish` on own service, immutable reviewed commit | Connect approved repo/branch, build/publish signed static artifact |
| Future Node/Next.js/Python | Runtime-specific deployment engines | Actual package supports process/runtime/SSL/DB and isolation | New capability names and audited adapters | Never show as deployable solely because user owns basic hosting |

`backend/bridge/integrations.py` is the server-side **deny-by-default** registry: even arbitrary-looking frontend availability is not authorization. Console currently grants only `overview`; all connected/execution states are deliberately FALSE. `frontend/src/components/IntegrationHub.tsx` shows genuine requirements rather than claiming live support. None of these connectors calls a real API in this batch.

**Security references:** OWASP one-time credentials and email reset guidance https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html ; Softaculous https://www.softaculous.com/docs/api/api/ ; Cloudflare API permission scopes https://developers.cloudflare.com/fundamentals/api/reference/permissions/ ; GitHub App installations https://docs.github.com/en/rest/apps/installations .

## Production acceptance & rollback

- Opt-in OPanel technical credentials disabled by default; access via Console remains available when direct login disabled.
- Every hosting account binds exactly one Console service, one subject, one verified provider-account fingerprint. Technical login MUST NOT resurrect a suspended or reallocated service.
- Changing service owner/binding invalidates the old hashed record until secure re-enrollment; no silent transfer.
- No raw provider password in mail, database notifications, logs, frontend API, repository or SSR URL.
- Verify dynamic hosts, cookies, CSRF, rate limit distributed persistence and logout on two deployed environments.
- Actual integration deployments require immutable site content, DNS/SSL/live HTTP proof and supplier-runtime qualification.
- Console payment/hosting flags and OPanel technical login/integration switches remain separate; do not enable all at once.
