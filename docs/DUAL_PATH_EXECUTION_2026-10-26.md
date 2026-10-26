# OPanel dual infrastructure execution — 26 October 2026

## Authority and scope
Owner authorizes two interchangeable technical paths: existing DirectAdmin/WHM adapters and native Octalve server management without a commercial panel dependency. Console remains the only customer identity, ownership, billing and account-provisioning authority. Native runtime components belong here; Console may eventually invoke a versioned provisioning contract, not duplicate implementation.

Canonical base: OPanel 4620b6f; Console integration reference a594d15. Preserve canonical bridge and frontend/src. Do not cherry-pick the old alternative backend/frontend wholesale.

## Execution sequence and acceptance
1. Consolidate isolated-candidate security improvements into the canonical implementation: logout recovery, strict identities, responsive/browser regression.
2. Introduce a native account-worker protocol with service/binding/node isolation, signed expiring requests, durable replay protection, bounded filesystem reads, no shell, and explicitly gated directory creation. Test temporary real files, symlinks, traversal, replay and foreign account attempts.
3. Add a provider-neutral management boundary with fresh entitlement before/after external reads and separate operation capability grants. Existing overview-only grants MUST NOT authorize file access. Backend-only transport injection until enrollment, mTLS and secret-store acceptance.
4. Extend vendor usage normalization and negative fixtures against official APIs. Real vendor credentials/hosts and isolated Review acceptance are not present in this workspace; do not report mocked responses as live qualification.
5. Consolidate browser tests and CI; verify current Console wire contracts and record exact tests and blockers. Publish reviewable commits/PR; do not merge or deploy Production.

## Native deployment architecture
Control plane -> enrolled node mTLS gateway -> separate unprivileged worker per hosting account. Each worker receives an operator-owned fixed root directory, exact service/binding/node identifiers and per-worker request key. No browser-selected path root, hostname, executable, credential or arbitrary command. Gateway enrollment, cert issuance/rotation/revocation, OS quotas, website runtime/service configuration, DNS, database/mail isolation, backups and rollback must be qualified before real server enablement. A worker is not a complete replacement hosting stack.

## Progress
- Inspected both current GitHub PR heads and canonical backend/frontend. No AGENTS.md in OPanel tracked tree.
- Ruling: preserve overview-only Console v1 contract; use an additional explicit management grant for new capabilities, leaving browser management disabled until Console supplies that grant. This avoids silently widening entitlement; costs a coordinated contract upgrade.
- Live gates require actual isolated account/server and configured Console/OPanel origins; no guessed credentials or invented acceptance.

## Verified checkpoint
- Canonical implementation preserved; alternative backend/app was not merged.
- 47 backend tests passed, including native temporary filesystem operations,
  vendor usage, malformed responses, scope/capability/replay/path/audit denial.
- Current Console a594d15 issuer/service suite: 39 tests passed, synthetic DB only.
- Frontend production build passed; 6 browser regressions passed at
  360/390/768/1440px, initial authorization outage/logout and denied data access.
- React review: independent CSRF/session fetches start together, abort on cleanup;
  tokens stay in component memory and signout uses same-origin POST.
- Real deployed HTTPS SSO, live provider usage, native node enrollment/mTLS,
  OS confinement/quota and full technical modules remain unqualified. No
  Production changes, payments, account provisioning or deployments performed.
- Actual cross-repository contract test passed with Console password login,
  issuer authorize/exchange/entitlement, PKCE challenge/verifier, OPanel callback
  and session, replay rejection, suspension denial, CSRF logout. Separate
  in-memory databases and Python environments; APIClient/subprocess RPC replaces
  HTTPS transport only. This is not deployed browser SSO acceptance.
- Added pinned-Console cross-repository CI alongside backend and browser CI.

## Exact remaining acceptance gates
1. Configured isolated Console web/API and OPanel HTTPS origins, persistent
   isolated sessions DB, confidential-client secret references and callback
   registration. Exercise full Console BFF -> browser -> OPanel proxy flow.
2. Approved read-only provider account, vault-backed credential resolver and
   restricted egress; capture actual vendor version/fields/units and verify
   account owner/domain before displaying provider usage. No secrets in Git.
3. Native enrolled node gateway/mTLS and hardened OS worker confinement. Qualify
   a disposable Linux host before enabling worker directory creation remotely.
4. Console management-capability contract extension, durable audit backend,
   CSRF-protected mutation API and response validation, then connect UI to real
   inventory. Add websites, DNS, databases, email, SSL and backups incrementally
   with per-operation tests, recovery and failure acceptance; current screens
   remain disabled and do not claim successful operations.
5. Release acceptance and owner approval before merge/deploy to Production.

## Final review and corrections
Fresh independent code review found no Critical/Important exposed issue and two
minor findings. Executor regraded both as Important for this batch: unreliable
logout harms session control; an ambiguous write without its target cannot be
reconciled safely. Both were reproduced before fixing.
- Fixed: logout obtains a fresh same-origin CSRF token immediately before POST;
  rotated-token browser regression failed before and passes after the fix.
- Fixed: restricted durable audit now records binding and validated relative
  target path with request ID; control-character/traversal/oversized paths reject
  before starting an audit record. Unknown-write target tests failed then passed.
- Final full suites: 49 backend tests, 7 browser tests and Next production build
  passed. No pending schema changes. No deferred review minors.
- Reviewer declined live vendor credentials/compatibility, deployed HTTPS proxy
  cookies, native enrollment/mTLS, UID/mount isolation, OS quota and production
  audit durability. Ruling: these remain explicit release blockers; synthetic
  tests cannot establish them. Cost of treating them as complete would be
  unauthorized server operations or unreliable customer access.
- Deployment auto-triggering is disabled in root/frontend vercel.json according
  to https://vercel.com/docs/project-configuration/git-configuration. No deploy
  command was run. Existing authorization covers recording work in the draft PR;
  it does not cover Production merge or activation.
