"use client";

/** Module-specific UI structure. Not a fake database or enabled provider API. */
const contracts = {
  databases: {
    title: "Hosting databases", subtitle: "Manage isolated databases and dedicated database users.",
    actions: ["Create database", "Add database user"], headers: ["Database", "Engine", "Allocated user", "Status"],
    empty: "Database inventories require a verified account-scoped API.",
    note: "Database credentials must stay server-side and must never appear in provider logs, redirect URLs, or the Console customer service payload.",
    details: ["Database users", "Least-privilege grants", "Backup and recovery"],
  },
  email: {
    title: "Mail accounts", subtitle: "Create and manage domain-based email accounts.",
    actions: ["Create mailbox", "Set email alias"], headers: ["Mailbox", "Domain", "Quota", "Status"],
    empty: "No verified mail-account listing has been retrieved.",
    note: "Mailbox provisioning depends on existing domain mail routing and provider permissions; passwords and reset tokens must not be sent to the browser.",
    details: ["Aliases and forwarders", "Mailbox limits", "SPF / DKIM / DMARC"],
  },
  ssl: {
    title: "TLS certificates", subtitle: "Certificate status and HTTPS configuration for hosted sites.",
    actions: ["Request certificate", "Renew certificate"], headers: ["Domain", "Issuer", "Expires", "Status"],
    empty: "Certificate status has not been verified with the provider.",
    note: "Automated issuance must verify domain control and rate limits; a successful order is not evidence that a certificate was installed.",
    details: ["Automatic renewal", "HTTP challenge validation", "Certificate installation"],
  },
  backups: {
    title: "Hosting backups", subtitle: "Review protected snapshots and verified recovery points.",
    actions: ["Create backup", "Restore backup"], headers: ["Created", "Source", "Size", "Integrity"],
    empty: "Verified backup inventory is not available.",
    note: "Restores require isolated account authority, integrity checks and a separately qualified destructive-operation confirmation.",
    details: ["Recovery points", "Backup integrity", "Restore permission"],
  },
} as const;

export type PlannedModule = keyof typeof contracts;

export function PlannedModuleDetail({slug}: {slug:string}) {
  const spec = contracts[slug as PlannedModule];
  if (!spec) return null;
  return <div className="module-detail">
    <div className="module-toolbar"><div>
      <span className="preview-tag">NOT ENABLED</span>
      <h2>{spec.title}</h2><p>{spec.subtitle}</p>
    </div><div className="action-area">{spec.actions.map((label,index) =>
      <button key={label} className={index === 0 ? "disabled-primary" : "disabled-outline"}
        disabled type="button" title="Pending account-scoped provider adapter">{label}</button>
    )}</div></div>
    <section className="table-container" aria-label={spec.title}>
      <table><thead><tr>{spec.headers.map(h => <th key={h}>{h}</th>)}</tr></thead>
        <tbody><tr><td colSpan={spec.headers.length} className="table-empty">
          <div className="empty-slate"><span className="lock-mark">◇</span>
            <strong>{spec.empty}</strong><p>Provider access is deliberately unavailable in this release. No account or resource data is fabricated.</p>
          </div></td></tr></tbody>
      </table>
    </section>
    <div className="module-lower"><section className="module-hint">
      <h3>Security and activation requirement</h3><p>{spec.note}</p>
    </section><section className="module-planned"><h3>Planned capabilities</h3>
      {spec.details.map(detail => <div className="planned-row" key={detail}>
        <span>{detail}</span><span className="coming-status">Pending</span>
      </div>)}
    </section></div>
  </div>;
}
