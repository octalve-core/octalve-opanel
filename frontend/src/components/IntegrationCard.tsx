import type { IntegrationCardData } from "@/lib/integrations";

export function IntegrationCard({item}:{item:IntegrationCardData}) {
  return <article className="integration-card">
    <div className="integration-header">
      <div className="integration-logo" aria-hidden="true">{item.initial}</div>
      <div><strong>{item.name}</strong><small>{item.provider}</small></div>
    </div>
    <span className="integration-badge">{item.badge}</span>
    <p>{item.summary}</p>
    <ul>{item.requirements.map(requirement => <li key={requirement}>{requirement}</li>)}</ul>
    <button disabled type="button" title="Verified account-scoped connector and external approvals required">
      Not connected
    </button>
  </article>;
}
