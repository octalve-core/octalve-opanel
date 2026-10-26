"use client";

/** A discoverable but fail-closed integration marketplace.
 * Connected state is NOT inferred from marketing, guessed hosting type, or
 * the currently overview-only Console entitlement.
 */
const integrations = [
  {id:"wordpress",initial:"W",name:"WordPress",provider:"Softaculous or qualified installer",
   badge:"PHP + Database required",summary:"Install and manage WordPress when the specific hosting account supports a verified PHP runtime, SQL database and approved installer.",
   requirements:["Verified PHP and MySQL/MariaDB runtime","Account-scoped installation API","Separate WordPress administrator password","TLS-ready domain and rollback"]},
  {id:"cloudflare",initial:"C",name:"Cloudflare",provider:"Domain DNS and security",
   badge:"Zone ownership required",summary:"Connect a Cloudflare zone after proving the customer controls that zone and approves a narrowly scoped API integration.",
   requirements:["Verified DNS-zone authority","Zone-scoped DNS permission only","Safe A / AAAA / CNAME change preview","Reconciliation and rollback after DNS updates"]},
  {id:"github",initial:"G",name:"GitHub",provider:"Static website deployment",
   badge:"Static sites first",summary:"Select an authorized GitHub repository and publish a verified static build to this hosting account without sharing GitHub passwords.",
   requirements:["GitHub App, selected repositories only","Approved branch, immutable commit SHA","Static HTML/CSS/JS output artifact","Atomic publish to account-specific document root"]},
] as const;

export function IntegrationHub() {
  return <div className="integration-hub">
    <section className="module-toolbar">
      <div><span className="preview-tag">INTEGRATIONS — IN DEVELOPMENT</span>
        <h2>Connect your website tools</h2>
        <p>Integrations are independent adapters. Each one requires an eligible hosting plan, verified customer ownership and an explicitly authorized operation.</p>
      </div>
    </section>
    <div className="integration-grid">{integrations.map(item =>
      <article className="integration-card" key={item.id}>
        <div className="integration-header"><div className="integration-logo" aria-hidden="true">{item.initial}</div>
          <div><strong>{item.name}</strong><small>{item.provider}</small></div>
        </div>
        <span className="integration-badge">{item.badge}</span>
        <p>{item.summary}</p>
        <ul>{item.requirements.map(r => <li key={r}>{r}</li>)}</ul>
        <button disabled type="button" title="A verified account-scoped connector must be approved first">Not connected</button>
      </article>
    )}</div>
    <section className="module-hint">
      <h3>Hosting plan compatibility</h3>
      <p>A static-only hosting package cannot execute PHP, WordPress, Node.js or a server-rendered Next.js app. An integration is activated only after the technical backend verifies the purchased hosting plan, actual supported runtime, account ownership, permissions and the live deployment adapter. More connectors can be added without replacing the OPanel interface.</p>
    </section>
  </div>;
}
