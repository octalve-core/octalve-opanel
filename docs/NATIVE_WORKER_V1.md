# Native OPanel worker v1

## Independent ownership
The account worker is Octalve code under backend/native_agent. It imports no
DirectAdmin, cPanel or Django components and never invokes a shell or executable.
The backend bridge selects NativeAdapter or VendorAdapter through the same
ServiceScope and operation-capability boundary. Console remains commercial and
service-ownership authority; existing overview grants cannot grant file access.

## Implemented request protocol
UTF-8 JSON <=8192 bytes, HMAC-SHA256 over exact bytes using a dedicated >=32-byte
worker key. Exact fields: version=1, node_id, service_id (positive integer),
binding_ref, request_id (32 lowercase hex characters), expires_at (integer,
strictly future, <=60 seconds), operation and relative path. Duplicate/unknown
fields, wrong scope, unsupported operation, invalid signature and stale requests
are rejected. Replay IDs persist in SQLite outside the hosting account root and
are atomically consumed before filesystem I/O. An ambiguous write must be
reconciled, never retried automatically with a new request ID.

Operations:
- files.list: direct-child names/types/regular-file sizes; no file content.
- usage.read: bounded recursive regular-file byte count, labelled account-files;
  this is not OS quota usage or database/mail usage. Bandwidth is null, not zero.
- files.mkdir: disabled by default; fixed-root relative directory creation,
  mode 0750, no replacement. Control plane additionally requires operation grant,
  explicit write gate, confirmation, and successful pre-operation audit.

Filesystems use directory descriptors and O_NOFOLLOW, rejecting traversal,
absolute paths and symlink traversal. Symlinks/special files/hard-linked files
are restricted inventory entries, excluded from file-byte usage. Read budgets:
1000 entries and 32 recursive directory levels; an exceeded budget is an error,
not a successful partial inventory. No upload, read-file, overwrite, deletion,
shell, privilege escalation, process control or account provisioning is exposed.

## Mandatory server deployment boundary (not yet implemented/accepted)
Run workers as dedicated unprivileged UIDs in account-specific mount namespaces.
Only the configured account root is mounted; no foreign account bind mounts.
The worker UID must be distinct from the website execution UID. Operator-owned
configuration pins the root, node/service/binding and secret reference; hosting
users cannot change those or access the replay database/key. The node gateway
must authenticate the control plane with mTLS, restrict traffic, validate bounded
requests/responses, rate limit, enforce deadline and response budgets, maintain
node enrollment/revocation and record durable audit outcomes. Do not expose this
Python library directly to a public socket. HMAC alone is not confidential
transport and does not authenticate responses.

## Management grant proposal (not currently issued by Console)
Keep the current v1 overview grant unchanged. A coordinated extension may add:
`management: {version: 1, capabilities: ["usage.read", "files.list"]}`.
Only a fresh confidential Console response can supply this field; never accept
it from the browser. Before AND after operations, verify subject, exact service,
binding and operation. Writes require a CSRF-protected customer confirmation
and audit sink. `run_operation` is backend-only and has no HTTP route or live
credential resolver. Test transport is injected; production enrollment is pending.

## Vendor usage sources
- DirectAdmin official legacy API: https://docs.directadmin.com/developer/api/legacy-api.html
  Account config and CMD_API_SHOW_USER_USAGE, values reported in vendor MB.
- WHM accountsummary: https://api.docs.cpanel.net/specifications/whm.openapi/account-management/accounts-accountsummary
  diskused/disklimit; bandwidth remains unknown in this operation.

Vendor responses are synthetic fixtures in acceptance tests. Approved hostnames,
TLS, no redirects and bounded response reads are enforced; production egress
control and vault integration remain required. Neither tests nor a configured
host allowlist qualify a live provider account by themselves.

The durable audit sink must be access-controlled: records include validated
relative target paths and binding references to support ambiguous-write
reconciliation. They must not be sent to general application logs or returned
to unrelated customers. Missing audit availability blocks operation start;
missing completion evidence leaves mutation outcome unknown.
