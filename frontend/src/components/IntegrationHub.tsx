import { integrationCatalog } from "@/lib/integrations";
import { IntegrationCard } from "./IntegrationCard";

/** The page composes data-driven connectors; account mutations stay disabled. */
export function IntegrationHub() {
  return <div className="integration-hub">
    <section className="module-toolbar">
      <div><span className="preview-tag">INTEGRATIONS — IN DEVELOPMENT</span>
        <h2>Connect your website tools</h2>
        <p>Integrations are independent adapters. Each one requires an eligible hosting plan, verified customer ownership and an explicitly authorized operation.</p>
      </div>
    </section>
    <div className="integration-grid">
      {integrationCatalog.map(item => <IntegrationCard key={item.id} item={item}/>)}
    </div>
    <section className="module-hint">
      <h3>Hosting plan compatibility</h3>
      <p>A static-only hosting package cannot execute PHP, WordPress, Node.js or a server-rendered Next.js app. Each connector requires an approved backend adapter, current hosting account proof, runtime compatibility and per-operation permission.</p>
      <p>Manual ZIP upload remains independently available in Websites and File Manager. GitHub is an additional source, not a replacement.</p>
    </section>
  </div>;
}
