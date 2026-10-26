> **EXECUTION STATUS — 26 OCTOBER 2026:** Follow the [OPanel implementation batch scope](docs/OPANEL_MASTER_BATCH_SCOPE_2026-10-26.md), coordinated with the [Octalve Cloud master roadmap](https://github.com/octalve-core/octalve-console/blob/phase/cloud-paid-provisioning-opanel-foundation/docs/CLOUD_MASTER_EXECUTION_PLAN_2026-10-26.md). OPanel [PR #1](https://github.com/octalve-core/octalve-opanel/pull/1) remains Review-only and independent from Console. Cross-repo SSO and native worker tests do not mean a vendor account or public website has been created; provider mutations, WordPress installer and live file upload remain unqualified. 

# Octalve OPanel

Independent technical hosting management product, maintained in `octalve-core/octalve-opanel`. Octalve Console retains commercial identity, service entitlement, billing and provisioning authority.

## Batch 3/4 — Manual website upload, DNS and integrations (26 October 2026)

The module-first delivery plan and exact Review limitations are recorded in [OPanel Batch 3/4](docs/OPANEL_BATCH_3_4_STATIC_UPLOAD_AND_CONNECTORS_2026-10-26.md). Customers will retain manual static website ZIP upload alongside selected-GitHub-repository deployments. A CSRF-protected, Console-entitlement-scoped archive inspection service and a confined offline first-publication worker are implemented and synthetically tested; **no real hosting server publication or public website has been qualified**. Provider DNS/WordPress/GitHub writes, customer Publish and registrar purchase stay disabled until external acceptance. The UI is broken into independent workspaces, module components, integrations catalog and upload/connection views rather than one long file.

## Optional technical login and initial integrations (26 October 2026)

**Console → OPanel single sign-on stays the default.** A new, separately gated hosting technical username/password is now supported as an optional second way to enter OPanel after initial Console SSO enrollment. It is **not** a duplicate Console customer account or the WHM/DirectAdmin server login. Technical passwords are hashed in the independent OPanel DB, never emailed, and a successful direct login must still pass live Console entitlement. The frontend and backend flags remain OFF until MFA/recovery/distributed throttling and deployment acceptance.

An **Integrations** area now groups WordPress/Softaculous, Cloudflare DNS, and GitHub static publishing, with account/runtime proof requirements; each real connector remains disabled. See [dual login + integrations specification](docs/OPANEL_DUAL_LOGIN_AND_INTEGRATIONS_2026-10-26.md).

## Customer sign-in contract (owner-confirmed, 25 October 2026)

**One customer login: Octalve Console.** OPanel must not offer a second customer registration, password login, or password reset.

1. Customer signs into Console and opens an **active, provider-confirmed provisioned** hosting service they own.
2. Console authorizes **Manage hosting / Open OPanel** for that exact service; pending, suspended, expired, terminated and unprovisioned services are denied.
3. Secure, short-lived, single-use authorization-code exchange establishes an **independent OPanel session** bound to that customer and service. No reusable sign-in credential or provider secret enters the browser.
4. OPanel revalidates the service entitlement with Console before technical provider operations and fails closed if Console is unavailable.
5. DirectAdmin/cPanel hosting accounts are the technical accounts OPanel manages **server-to-server**. They are not separate OPanel customer identities. Hosting credentials, WHM administrator tokens and reseller secrets are never sent to the browser.

OPanel can have its own backend, session store, deployment and release pipeline; it must not duplicate the customer password database or financial authorities. OPanel logout terminates its session; returning requires a fresh Console-initiated launch (which may use the still-valid Console session).

## Implementation status

Development implementation now includes an independent Next.js 16 / React 19 / TypeScript frontend, module-specific hosting management views, secure Django SSO start/callback, entitlement revalidation, CSRF-protected logout, and backend-only DirectAdmin/WHM read-only adapter foundations with automated CI. **Not deployed or live-qualified:** no real provider requests, hosting mutation operations, settlement, provisioning, tested live Console integration credentials or Production hosting management. This is the secure foundation, not full OPanel. The current Console PR #14 read-only `/client/services/:id/opanel` page is an **integration prototype inside Console**, not OPanel login. It must not be presented as working independent management.

Integration references: `octalve-core/octalve-console` PR #13 and PR #14. [Detailed design](docs/superpowers/specs/2026-10-25-opanel-foundation-design.md). Application code belongs in this repository, not Console.

## Developer execution (no real provider or payment)

The independent backend is under backend/. With Python 3.12 and an isolated environment, install the pinned requirements with python -m pip install -r backend/requirements.txt. Then, from the backend/ directory, set DEBUG=true and run python manage.py test bridge. Initial startup also requires the standard Django session migrations. There are no OPanel customer user/password records. Every dashboard view revalidates the Console service entitlement, and external overview fields are validated and HTML-escaped before display.

Production requires DJANGO_SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS, CONSOLE_WEB_ORIGIN, CONSOLE_API_BASE (ends in /api), OPANEL_CALLBACK_URL (fixed HTTPS /auth/callback/), OPANEL_CLIENT_ID, and OPANEL_CLIENT_SECRET, configured in the deployment secret store. The secret must match Console's client secret, must not be committed and must not be reused as a provider token. Console separately requires OPANEL_ISSUER_ENABLED=true once genuinely qualified. All four URLs must be verified before enabling live launch.

Start endpoint: GET /auth/start/?service_id=<Console hosting service id>. After Console grants the short-lived one-time code, the callback sets an independent server-side session. The first independent interface is now a responsive, Octalve-branded read-only hosting dashboard. It displays the fresh Console-entitled service, domain, billing date, and optional historical usage snapshot; unavailable provider tools are visibly disabled. Actual technical management remains disabled. The system does not have an OPanel registration or password form.

## Read-only dashboard acceptance

- Console's confidential `POST /api/integrations/opanel/v1/entitlement/` response now includes optional `overview` with ONLY service ID, display label, domain, active status, next due date and recorded usage snapshot. It does not include raw provider config, account identifiers, customer passwords, billing secrets or live server mutation URLs.
- OPanel renders overview data only if its embedded service ID exactly matches the current authenticated session and its status is active. It independently revalidates subject/service/binding/capabilities with Console on each request. Missing or malformed overview falls back to minimal service ID; it never displays another customer's record.
- The new public interface is independently authored in `frontend/` using Next.js. A minimal Django fallback remains under `backend/bridge/dashboard.py`. Both use local styling and no outside image/font/script requests; the Django fallback enforces CSP/no-referrer and the Next frontend has explicit security headers. All provider/Console-supplied text is escaped. Logout uses POST and CSRF; the session uses an independent HttpOnly cookie.
- Files, domains, DNS, email, SQL, SSL and backups are visible as clearly disabled future modules. They have no API routes for technical mutations. Data is a historical snapshot, never presented as live provider usage.
- The public Next.js frontend serves `/` and `/modules/*`; exact server-side rewrites route `/auth/start/`, `/auth/callback/`, `/auth/logout/`, `/api/session/` and `/health/` to the independent Django backend. The Django renderer remains a fallback. A real deployment must provide the fixed trusted HTTPS backend origin during Next build and matching public callback origin in Django; do not place OPanel itself inside Console.
- Live browser SSO and authorized provider tests are pending isolated Review environments and Vercel capacity. The existing CI uses only synthetic fixtures and a stubbed confidential Console response; green CI does not establish live API connectivity.

## Consolidated independent frontend execution

With Node.js 22 and pnpm 10, run `cd frontend && pnpm install --no-frozen-lockfile && pnpm dev` for the development UI. CI runs strict TypeScript typecheck and a production `next build`. A standalone frontend without configured OPanel Django backend will intentionally show an **unauthorized/unavailable state** rather than bypass login or manufacture an active service.

For an integrated deployment set frontend `OPANEL_BACKEND_ORIGIN` (fixed HTTPS origin of the separate OPanel Django API) **at build time** and `NEXT_PUBLIC_CONSOLE_WEB_ORIGIN` (Console return address). Set backend `OPANEL_PUBLIC_ORIGIN` to the exact public Next.js host, `OPANEL_CALLBACK_URL` to its `/auth/callback/`, plus independent DB, encrypted secret and Console SSO client credentials. See [the consolidated batch runbook](docs/OPANEL_CONSOLIDATED_BATCH_AND_ACCEPTANCE_2026-10-25.md) and both `.env.example` files. OPanel provider read-back defaults off; host allowlisting is not a substitute for network-layer egress/DNS-rebinding protection.

Eight technical modules now have their own inventory layouts, planned actions and explicit security prerequisites. Operations remain disabled; these screens are not mock server inventory and do not indicate provider functionality is operational. The owner has authorized source integration into `main`. Production release remains blocked until real account, deployment, CSRF/proxy and live browser acceptance checks pass.

## Dual infrastructure paths (26 October 2026)

OPanel supports two implementation paths: vendor adapters for DirectAdmin/WHM,
and an independent native Octalve account worker with no commercial-panel
runtime dependency. See [execution and acceptance](docs/DUAL_PATH_EXECUTION_2026-10-26.md)
and [native worker contract](docs/NATIVE_WORKER_V1.md).

The native worker currently implements bounded file inventory, file-byte usage,
and explicitly gated directory creation. It is a tested operation engine, not an
installed server-management daemon. Browser management stays disabled: current
Console grants authorize overview only. No agent enrollment, live transport,
provider credentials or production server operations have been enabled.

### Run all hosting practice pages without buying a server

The local practice workspace has separate persistent simulated domains,
subdomains, DNS records, SSL states, websites/releases/rollback, text files,
databases, mailboxes, backup snapshots and activity. No action calls a hosting
provider, creates an actual certificate, sends email or backs up a real server.
It does not authorize or modify Console customer services.

1. Create `.venv` and install `backend/requirements.txt`.
2. Run `.venv/bin/python scripts/serve-practice.py` (PowerShell: `.venv\Scripts\python.exe scripts/serve-practice.py`). This creates disposable storage and listens only on `127.0.0.1:8301`.
3. In `frontend`, install dependencies, set `OPANEL_LOCAL_PRACTICE=true`, run `pnpm build`, then `pnpm start --hostname 127.0.0.1 --port 3300`.
4. Open `http://127.0.0.1:3300/practice/`. Keep the API process running. Data persists across page reloads during the local session and is removed when the disposable server exits.

Practice API requires DEBUG, explicit enablement, a loopback Host, isolated
configured storage, a separate signed practice cookie (24-hour renewable lifetime) and CSRF for writes. Ordinary
builds do not proxy practice requests. Automatic deployment remains disabled;
merging source to main does not qualify a live hosting release.
