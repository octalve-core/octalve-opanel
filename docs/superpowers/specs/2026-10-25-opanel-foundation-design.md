# OPanel independent foundation design — 2026-10-25

Status: **customer entry and identity contract confirmed by owner, 25 October 2026**. The first Django SSO/session foundation is implemented in this development PR with CI tests, but integration credentials, live browser acceptance, provider operations and deployment have NOT been accepted. Next.js UI and modules remain future work.

## Intent and authority
Build Octalve's hPanel-like technical hosting interface in octalve-core/octalve-opanel. Console remains the WHMCS-like authority for customers, service ownership, commercial catalog, invoices, settlement and provisioning. OPanel must never infer technical entitlement from a paid invoice or create hosting accounts.

## Verified integration baseline
- OPanel was empty at inspection. README bootstrap: 2cd2bb605800477fdf55b4adedae39c836c27ef2.
- Console PR #13: 89cb1f6094b9bf4058cc8df66fdee8cb74ca9a3f, draft. Read-only DirectAdmin/WHM package inventory and catalog authority. Package inventory is not customer account usage.
- Console PR #14: cfb963caa9dd272380bf795628272355ad12c930, draft, based on #13.
- GET /api/services/opanel/{service_id}/overview/ uses authenticated ownership checks with an admin exception. It returns redacted service information and latest stored usage. active means active status plus a nonempty provider_identifier; this is NOT independent provider verification.
- /api/auth/me/ and JWT create/refresh/logout contracts exist. They are not an OPanel launch-code exchange.
- ServiceUsage exposes recorded_at; absent or stale snapshots must never look live.
- No root AGENTS.md was found at the inspected Console revision.
- Re-read current heads before implementation. Never silently treat draft contracts as deployed.

## Approaches
Recommended engineering choice (not yet owner-approved): Next.js/TypeScript frontend plus independent Django REST backend. This follows existing frontend/backend conventions while separating trust boundaries and deployment lifecycles.
Alternative: Next.js with a server-only backend-for-frontend. Fewer runtimes, but introduces a second backend security stack and additional care for durable sessions/jobs.
Rejected: browser-to-provider access, embedding OPanel inside Console, shared Console session signing secrets, or duplicated billing/provisioning databases.

## Repository and deployment boundaries
frontend/: Next.js, TypeScript, responsive components, API client, browser tests.
backend/: Django REST, Console contract client, sessions, entitlement policy, adapter registry, audit records, backend tests.
contracts/: versioned schemas, synthetic fixtures and compatibility tests.
docs/: architecture, threat model, acceptance ledger and operator runbooks.
.github/workflows/: isolated checks; no automatic deployment.
Independent configuration, dependencies/lockfiles and secrets. OPanel stores only operational/session/audit data; Console remains source of ownership truth.
Production and review use separate databases, credentials and provider configuration. Review starts with synthetic providers only. Deployment is manual and remains disabled until acceptance. No production migrations.

## Authentication and entitlement contract v1 (CUSTOMER ENTRY APPROVED; not implemented in Console)
**Owner decision — mandatory:** Octalve Console is the **only customer login and account-registration system**. A hosting customer must never create, reset, or enter a separate OPanel password. After signing into Console, the customer chooses an active, verified-provisioned hosting service and selects **Manage hosting / Open OPanel**. A Console-authorized, one-use SSO code starts an **independent OPanel session**; no Console cookie, password, JWT signing key, or hosting control-panel password is reused as the OPanel session credential.

**Distinct identities:** (a) Console customer identity authenticates the human; (b) Console service entitlement authorizes the service; (c) OPanel issues its own short-lived session bound to both; (d) the DirectAdmin/cPanel account is the back-end hosting account being managed, not an independent OPanel customer identity. Provider/account identifiers and credentials are server-only. Do not create a local customer password database or second sign-up experience inside OPanel.

1. Customer is already authenticated in Console, opens an **active and independently confirmed provisioned** service, and chooses **Manage hosting / Open OPanel**. Console and OPanel follow fixed registered launch and redirect endpoints. A service ID is an identifier, never authority.
2. OPanel creates a short-lived server-stored state and PKCE challenge, binds the transaction to an HttpOnly browser cookie, and redirects to a fixed Console authorization endpoint.
3. Console authenticates the existing customer and verifies exact service ownership, supported service type, active status and provider-confirmed provisioning. No implicit admin bypass for customer launch.
4. Console issues an opaque, single-use code bound to subject, service, audience, exact registered redirect URI, PKCE challenge and a maximum 60-second lifetime.
5. OPanel validates browser-bound state and redeems the code server-to-server using PKCE and its own authenticated client identity. Console atomically consumes codes and rejects replay.
6. OPanel rotates the session ID and creates a short-lived opaque session in its independent shared store. Cookie: Secure, HttpOnly, SameSite=Lax, Path=/, __Host- prefix. No access/refresh tokens in browser storage.
7. Every technical API request revalidates service entitlement with Console; no fail-open cache. Wrong ownership returns non-enumerating denial; suspended/expired/revoked services lose access. Console outage returns unavailable and performs no provider request.
8. Logout deletes the OPanel session; Console's independent customer session need not be logged out. After OPanel session expiry, returning via Console starts a new SSO launch rather than prompting for OPanel credentials. Console revocation is observed on subsequent requests. Absolute and idle expiry are enforced server-side. Every OPanel session must be bound to its exact subject and service; switching services demands a new authorization.
9. Callback responses use no-store, no-referrer, no third-party assets; code/state/query values are excluded from logs and immediately removed by redirect.
10. CSRF token and exact Origin validation protect state-changing requests; no wildcard credentialed CORS.

Proposed server-to-server namespace: /api/integrations/opanel/v1/. Separate launch redemption and entitlement endpoints, authenticated with dedicated rotated service credentials (never Console's JWT signing key). Responses bind subject_id, service_id, status, provision_verified_at, allowed capabilities, entitlement revision and an opaque operational binding reference. Credentials/provider account identifiers are never returned to the browser.
An authenticated Console operational binding resolver must map the entitlement binding to provider/account identity for OPanel server use only. OPanel resolves the dedicated least-privilege provider credential through its own configured secret store. No browser-supplied provider endpoint, account name or credential reference is trusted.

Existing overview is reusable through a strict legacy client for redacted metadata and snapshots only. It cannot authorize provider calls. The Console PR #14 `/client/services/:id/opanel` view is **a Console-hosted read-only prototype** and must not be labeled a working OPanel sign-in or technical control panel. Until the independently reviewed issuer and launch/callback are implemented, the Console action should say **View hosting status**, not **Open OPanel**, and should not redirect to a nonexistent panel. When SSO is qualified, the real **Manage hosting / Open OPanel** action will use the independent launch endpoint. The new Console endpoints require a separately scoped Console integration change; foundation tests use an explicit synthetic issuer and contract fixture. Until the issuer is implemented and accepted, real Console launch must return an honest integration-unavailable state.

## Provider-neutral technical architecture
Typed adapter contract: capabilities(), get_overview(binding), get_usage(binding), then separately accepted module commands.
Normalize disk/bandwidth units, measurement timestamps, unknown limits and explicit unlimited values. Zero is not assumed unlimited. Keep source and freshness visible.
Adapter registry supports simulated DirectAdmin and cPanel variants for contract tests; real transports remain disabled until vendor-specific read-only acceptance. Do not label simulated results provider-live.
Provider binding is resolved only after fresh Console authorization and stays server-side.
Each adapter has a fixed allowlist of operations and exact approved HTTPS origins; no generic proxy or arbitrary path/URL endpoint. TLS verification, disabled redirects, bounded payloads/timeouts, controlled egress and redacted errors are mandatory. Never let DNS resolution reach metadata/link-local/internal destinations unless a specifically reviewed infrastructure route authorizes that destination.
Prefer account-scoped DirectAdmin login keys/cPanel API tokens. WHM/reseller admin credentials used for Console provisioning do not belong in OPanel request flows. Unsupported least-privilege operations stay disabled.
Provider timeouts/invalid schemas give explicit unavailable states. Retry reads within a bounded budget; never turn upstream failure into synthetic success.
Future mutation commands require schema validation, per-service lock/idempotency, audit correlation and reconciliation of ambiguous provider outcomes. Never retry a destructive operation blindly.

## Interface
Visual direction: Octalve blue #0064E0, dark sidebar #000A16, light workspace, strong typography and accessible contrast. Use official assets only when verified; text wordmark otherwise.
Desktop: fixed sidebar, service/domain heading, service status, overview and usage cards, capability modules, timestamp and refresh.
Mobile: collapsible navigation, single-column cards, generous touch targets, no horizontal page overflow. Service identity remains visible.
Navigation covers Overview, Websites, Domains/subdomains, DNS, Files, Databases, SSL, Backups and Email. Unavailable modules explain their actual capability state; no dead buttons or success toasts.
Overview displays service identity/status from Console and account-scoped usage when available. Separate recorded snapshot, simulated fixture, stale, unavailable and loading states.
No invented uptime, SSL validity, backup status or storage values. Empty/error states have useful recovery actions. Refresh is user initiated with throttling; no uncontrolled background polling.
Keyboard navigation, visible focus, semantic headings, screen-reader announcements and reduced-motion support are acceptance criteria.

## Phases
Foundation: independent scaffold/configuration, proposed contract schemas, session/entitlement policy against a synthetic Console, simulated adapter contract suite, polished overview, unavailable states, CI, architecture and acceptance ledger.
Integration: implement/qualify Console v1 launch and entitlement separately; connect real read-only account usage for DirectAdmin and cPanel after fixture and scoped-server acceptance.
Technical modules: websites/domains/subdomains inventory; then DNS and files; databases/email; SSL/backups. Each provider/capability is accepted independently before activation.
Registrar authority, DNS authority and hosting-domain attachment remain distinct. DNS edits require authoritative-zone control; certificate issuance and restore operations require explicit scopes and audit.

## Tests and acceptance
- Only one customer registration/login in Console; no independent OPanel password UI, customer password exchange or browser-visible hosting credentials. Successful Console→OPanel launch creates only an OPanel-owned, service-scoped session.
- Wrong owner/service/audience; inactive account; pending/suspended/terminated service; missing provisioning verification; revoked entitlement; cross-service session reuse.
- Expired/replayed code, state/PKCE mismatch, callback redirect tampering, session fixation/expiry/logout, CSRF and request-origin violations.
- Console outages/timeouts/invalid contracts prevent all provider calls.
- Cross-account provider binding attempts; unsupported capability; forbidden endpoint/redirect; malformed/oversized responses; credential redaction.
- Usage unit/limit/freshness validation; missing data is not zero usage or unlimited.
- Synthetic provider timeout, authentication denial and error cases.
- Browser flows at 360, 390, 768 and 1440 pixels: launch/loading/overview, mobile navigation, refresh failure, unavailable modules, keyboard use and no overflow.
- CI: pinned installs, frontend typecheck/build, backend tests, contract tests, browser tests and secret checks. No paid resource or live provider required.
- Reviewer checks exact commit and test evidence. No application merge or deployment until acceptance. Report tests actually run, never anticipated results.

## Release and remaining decisions
Next.js/Django and the visual defaults are recommended engineering choices. Owner approval of this design precedes application implementation under the architecture skill.
Builder may choose compatible pinned versions after registry/runtime verification, session-store implementation and internal component boundaries. Production domain names, dedicated integration credentials and scoped provider secrets are configured later without placing secrets in chat or GitHub.
Foundation acceptance is not full hosting-product acceptance. Keep a concrete remaining-work ledger and exact commit/PR links.

## Implementation ledger (same development PR)
- backend/opanel_project is a standalone Django project (no Console account/password database).
- backend/bridge provides GET /auth/start/, GET /auth/callback/, GET /api/session/, POST /auth/logout/ and a minimal authenticated home screen. Browser-bound state and PKCE verifier live in OPanel's database session; Console authorization code is redeemed server-to-server with a dedicated confidential client credential.
- Fresh Console entitlement validation happens on every authenticated page/API request and must return the exact subject, service and opaque binding. Any unavailable or revoked binding yields no access.
- Session cookie uses the host-only __Host- name, HttpOnly, Secure, SameSite=Lax in Production. Login rotates the session key; 15-minute idle/2-hour absolute expiry. CSRF protects logout. Callback and session responses suppress storage and referrers.
- Provider adapter methods and account mutations remain unimplemented. No actual hosting account was created or checked.
- CI installs pinned Django and runs bridge security tests; additional browser acceptance and a genuine confirmed provisioning binding remain pre-release requirements.
