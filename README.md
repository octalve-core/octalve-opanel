# Octalve OPanel

Independent technical hosting management product, maintained in `octalve-core/octalve-opanel`. Octalve Console retains commercial identity, service entitlement, billing and provisioning authority.

## Customer sign-in contract (owner-confirmed, 25 October 2026)

**One customer login: Octalve Console.** OPanel must not offer a second customer registration, password login, or password reset.

1. Customer signs into Console and opens an **active, provider-confirmed provisioned** hosting service they own.
2. Console authorizes **Manage hosting / Open OPanel** for that exact service; pending, suspended, expired, terminated and unprovisioned services are denied.
3. Secure, short-lived, single-use authorization-code exchange establishes an **independent OPanel session** bound to that customer and service. No reusable sign-in credential or provider secret enters the browser.
4. OPanel revalidates the service entitlement with Console before technical provider operations and fails closed if Console is unavailable.
5. DirectAdmin/cPanel hosting accounts are the technical accounts OPanel manages **server-to-server**. They are not separate OPanel customer identities. Hosting credentials, WHM administrator tokens and reseller secrets are never sent to the browser.

OPanel can have its own backend, session store, deployment and release pipeline; it must not duplicate the customer password database or financial authorities. OPanel logout terminates its session; returning requires a fresh Console-initiated launch (which may use the still-valid Console session).

## Implementation status

Development implementation now includes OPanel SSO start/callback, session, entitlement revalidation and CSRF-protected logout code with CI tests. **Not deployed or live-qualified:** no provider operations, provisioning, payments, tested Console integration credentials or Production hosting management. This is the secure foundation, not full OPanel. The current Console PR #14 read-only `/client/services/:id/opanel` page is an **integration prototype inside Console**, not OPanel login. It must not be presented as working independent management.

Integration references: `octalve-core/octalve-console` PR #13 and PR #14. [Detailed design](docs/superpowers/specs/2026-10-25-opanel-foundation-design.md). Application code belongs in this repository, not Console.

## Developer execution (no real provider or payment)

The independent backend is under backend/. With Python 3.12 and an isolated environment, install the pinned requirements with python -m pip install -r backend/requirements.txt. Then, from the backend/ directory, set DEBUG=true and run python manage.py test bridge. Initial startup also requires the standard Django session migrations. There are no OPanel customer user/password records. Every dashboard view revalidates the Console service entitlement, and external overview fields are validated and HTML-escaped before display.

Production requires DJANGO_SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS, CONSOLE_WEB_ORIGIN, CONSOLE_API_BASE (ends in /api), OPANEL_CALLBACK_URL (fixed HTTPS /auth/callback/), OPANEL_CLIENT_ID, and OPANEL_CLIENT_SECRET, configured in the deployment secret store. The secret must match Console's client secret, must not be committed and must not be reused as a provider token. Console separately requires OPANEL_ISSUER_ENABLED=true once genuinely qualified. All four URLs must be verified before enabling live launch.

Start endpoint: GET /auth/start/?service_id=<Console hosting service id>. After Console grants the short-lived one-time code, the callback sets an independent server-side session. The first independent interface is now a responsive, Octalve-branded read-only hosting dashboard. It displays the fresh Console-entitled service, domain, billing date, and optional historical usage snapshot; unavailable provider tools are visibly disabled. Actual technical management remains disabled. The system does not have an OPanel registration or password form.

## Read-only dashboard acceptance

- Console's confidential `POST /api/integrations/opanel/v1/entitlement/` response now includes optional `overview` with ONLY service ID, display label, domain, active status, next due date and recorded usage snapshot. It does not include raw provider config, account identifiers, customer passwords, billing secrets or live server mutation URLs.
- OPanel renders overview data only if its embedded service ID exactly matches the current authenticated session and its status is active. It independently revalidates subject/service/binding/capabilities with Console on each request. Missing or malformed overview falls back to minimal service ID; it never displays another customer's record.
- The interface is independently authored in `backend/bridge/dashboard.py`. It uses fixed CSS, no outside image/font/script requests, a no-referrer policy and CSP. All provider/Console-supplied text is escaped. Logout uses POST and CSRF; the session uses an independent HttpOnly cookie.
- Files, domains, DNS, email, SQL, SSL and backups are visible as clearly disabled future modules. They have no API routes for technical mutations. Data is a historical snapshot, never presented as live provider usage.
- The first dashboard is served by Django for the secure thin slice. An independently deployed Next.js/TypeScript frontend can replace this renderer later, but it must remain within OPanel's repository and preserve same-origin session protections; do not place OPanel itself inside Console.
- Live browser SSO and authorized provider tests are pending isolated Review environments and Vercel capacity. The existing CI uses only synthetic fixtures and a stubbed confidential Console response; green CI does not establish live API connectivity.
