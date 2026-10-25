# OCTALVE OPANEL — Consolidated Independent Workspace Development Batch
**Date:** 25 October 2026
**Release category:** Review only — development implemented; no Production activation
**Primary repository:** `octalve-core/octalve-opanel` (all application files)
**Commercial integration reference:** `octalve-core/octalve-console` PRs #13 and #14

## Architecture and completed implementation

OPanel is its OWN hosting technical product, not an app hidden inside Console. Console retains authoritative customer login, financial settlement, service ownership and verified provisioning evidence. OPanel owns an independent Django backend, database-backed server session store, frontend Next.js 16 / React 19 / TypeScript, UI modules, deploy configuration and vendor adapter code.

**One account login**: user signs into Console, opens an entitled hosting service, receives a 60s/one-time PKCE-backed authorization code, browser follows the exact registered OPanel callback, OPanel redeems confidentially, rechecks latest ownership/verified vendor binding and issues its own secure HttpOnly host-only session. No second OPanel customer password.

### Interface — independent Next.js app
- `frontend/`: Next.js TypeScript workspace, own layout and styles, brand blue #0064E0, sidebar #000A16.
- Fully responsive drawer navigation and mobile/desktop layouts; service overview, verified domain/label, dated usage snapshots and next due date (read-only Console source).
- Dedicated module pages and static inventory layouts for websites, files, domains/subdomains, DNS, databases, email, SSL and backups; historical usage and access settings.
- Module toolbars and resources are expressly **not yet enabled**. No fabricated rows, no mutating API routes, no invented file or DNS contents. The provider module contracts explain authorization prerequisites.
- Customer sees meaningful error/denied/offline states instead of a sign-in page. Access is checked fresh through Django on each page navigation and no OPanel password entry exists.

### Standalone same-origin session + backend boundary
- `frontend/next.config.ts` rewrites ONLY GET/POST session and three exact /auth routes and /health to its independent Django backend via the trusted server-only `OPANEL_BACKEND_ORIGIN`. Both browser calls and session cookies stay on ONE OPanel public origin; no cross-domain JS token storage.
- Set `trailingSlash: true` to align Django paths. Fixed https backend endpoint is validated during build; no browser-supplied host can determine the upstream.
- Django `OPANEL_PUBLIC_ORIGIN` MUST match the registered `OPANEL_CALLBACK_URL` origin in Production; `CSRF_TRUSTED_ORIGINS` includes only that origin. The masked CSRF token is returned only after session authorization to the first-party UI; Django enforces CSRF on POST logout. CSRF and session cookies remain HttpOnly.
- Django never trusts browser-supplied `subject_id`, `service_id`, provider access tokens or hostnames. Identity and binding come from a server-side authenticated session; entitlements are checked against Console on every GET.
- Production sessions: secure __Host-opanel_sid, SameSite=Lax, idle expiry 15min, absolute 2h; no provider actions when Console is unreachable, stale, suspended, cross-customer, unprovisioned, wrong binding or invalid capability.
- The original Django read-only dashboard remains an independent fallback at its backend / route; the Next.js frontend owns the new public product UI.

### Provider integration contract
- `backend/bridge/providers.py` defines independent DirectAdmin and WHM account-readback adapters. Both validate fixed approved HTTPS host and port, explicit operator account, reseller owner, technical account and domain; confirm current Console entitlement before and after remote I/O. HTTP GET only with TLS verification, no redirect, fixed timeout, bounded streaming response, strict match of username/domain/reseller/suspension.
- API tokens exist only in an explicit server-side `AccountTarget` value that hides its token from repr. The module does NOT create or persist tokens. An approved OPanel credential-provisioning/secret-store binding is still REQUIRED before any real provider call.
- `OPANEL_VENDOR_READBACK_ENABLED` defaults **false**; `OPANEL_PROVIDER_ALLOWED_HOSTS` defaults empty; no public endpoint invokes `read_account()`. `execute_technical_change()` always raises `ProviderRejected` for creation, deletion, suspension, file/DNS/database/email/SSL/backup mutations.
- Console PR #14 independently performs its own provider verification for billing/SSO authority. OPanel's adapter cannot override that authority. Provider adapter design follows independently documented DirectAdmin legacy read APIs and cPanel WHM API 1.

## Deployment topology (not yet executed)
```
Console customer/browser
  → Console private-authorised hosting service
  → OPanel public HTTPS origin (Next.js frontend)
     ├─ /, /modules/* : independent Next.js pages
     ├─ /api/session/ : fixed rewrite → OPanel Django backend
     ├─ /auth/start/ : fixed rewrite → OPanel Django backend
     ├─ /auth/callback/ : fixed rewrite → OPanel Django backend
     ├─ /auth/logout/ : fixed rewrite → OPanel Django backend
     └─ /health/ : fixed rewrite → OPanel Django backend
                                    └─ HTTPS confidential exchange + entitlement
                                       → Console API (no customer JWT/token sharing)
```

Server-only Next.js frontend settings (must exist **at Next build time**):
- `OPANEL_BACKEND_ORIGIN`: exact HTTPS origin of **OPanel's own Django backend**.
- `NEXT_PUBLIC_CONSOLE_WEB_ORIGIN`: exact public HTTPS Console origin, used solely for return navigation.

Server-only OPanel Django settings:
- `DEBUG=false`, `DJANGO_SECRET_KEY` unique (do not reuse Console), persistent independent `DATABASE_URL`, `ALLOWED_HOSTS` for actual incoming proxy Host, `OPANEL_PUBLIC_ORIGIN` (public Next.js origin), `OPANEL_CALLBACK_URL` (exact public origin + /auth/callback/).
- `CONSOLE_WEB_ORIGIN`, `CONSOLE_API_BASE` ending /api, `OPANEL_CLIENT_ID`, `OPANEL_CLIENT_SECRET` (dedicated confidential SSO client), trusted HTTPS certificate/DNS.
- `OPANEL_TRUST_PROXY` must be false unless the reverse proxy sanitises X-Forwarded-Proto and the backend is not externally reachable outside that proxy.
- `OPANEL_VENDOR_READBACK_ENABLED=false`, `OPANEL_PROVIDER_ALLOWED_HOSTS=` until provider, token and egress approval.
- Run Django `migrate` on the **independent OPanel database**, never Console's Neon DB. Deploys/session cookies/secret rotation and review approval are separate.

### Required security and operational gates before enabling any vendor network requests
1. Inspect TLS certificate, DNS ownership, full backend egress policy, host allowlist and internal-IP/DNS-rebinding protection; hostname allowlisting alone is NOT sufficient.
2. Verify dedicated least-privileged DirectAdmin/WHM test/reseller credentials stored in a private secret manager and delivered to exact account binding (not in cookies, source code, Console UI, or test logs).
3. Obtain authorised test hosting account with exact vendor username, domain and reseller. Confirm independent Console provider-readback evidence, paid/synthetic isolation and binding expiry policy.
4. Run cross-product browser SSO: correct customer, another customer, staff, suspended/unprovisioned, replayed PKCE, callback tampering, missing CSRF, logout, idle/absolute session expiry, Console API outage, and provider-readback suspension.
5. Confirm no technical operation is exposed from modules, no provider administrator token leaks, exact host routing and no background provider calls during UI navigation.
6. Verify responsive layouts (phone/tablet/desktop), browser login/refresh/redirect and independent app DNS.
7. Meet dependency-ordered Review acceptance before any approved merges; Vercel's current build-rate-limit must be resolved without unnecessary deployments.
8. Do not migrate Console Production, collect live funds, or run WHM/DirectAdmin account creation to qualify UI functionality.

## Validated development checks
- `.github/workflows/opanel-web.yml`: independent TypeScript typecheck and Next production build.
- `.github/workflows/opanel-sso.yml`: Django system check, migrations check, callback/session/CSRF tests, XSS/cross-user response tests, read-only vendor adapter negative tests.
- Console PR #14 remains the source of confidential entitlement/overview, verified provider binding and browser authorization, tested by its C1 + disposable PostgreSQL acceptance.
- **CI success does not establish a live cross-repo provider/SSO browser test**. Keep both PRs in draft and Production unchanged pending evidence.

## Remaining deliverables blocked on external infrastructure
- Real provider readback, host-scoped credential delivery and periodic reconciliation.
- Paid transaction settlement worker, idempotent provisioning and compensation lifecycle.
- Qualified write adapters for DNS, sites, files, SQL, mail, SSL, backups with individual audited scopes, rate limits, rollbacks and anti-cross-tenant enforcement.
- Full end-to-end browser acceptance, Preview/Production deployments, user-visible live hosting management.
