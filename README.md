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

Architecture review only: no live OPanel SSO, sessions, provider operations, provisioning, payments or deployment are implemented/qualified. The current Console PR #14 read-only `/client/services/:id/opanel` page is an **integration prototype inside Console**, not OPanel login. It must not be presented as working independent management.

Integration references: `octalve-core/octalve-console` PR #13 and PR #14. [Detailed design](docs/superpowers/specs/2026-10-25-opanel-foundation-design.md). Application code belongs in this repository, not Console.
