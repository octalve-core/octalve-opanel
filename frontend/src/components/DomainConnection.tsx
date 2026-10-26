"use client";
import type { PanelSession } from "@/lib/session";

export function DomainConnection({session}: {session:PanelSession}) {
  const domain = session.overview?.domain;
  return <div className="website-upload">
    <section className="module-toolbar"><div>
      <span className="preview-tag">DOMAIN CONNECTION</span>
      <h2>Connect your domain to hosting</h2>
      <p>Hosting ownership and domain registration ownership are different. Octalve never claims a domain is registered or DNS is connected based only on a hosting invoice.</p>
    </div></section>
    <section className="table-container">
      <table><thead><tr><th>Hosting domain</th><th>Authority</th><th>DNS status</th></tr></thead>
        <tbody><tr>
          <td>{domain || "Not available"}</td>
          <td>Console service entitlement</td>
          <td>Not externally verified</td>
        </tr></tbody></table>
    </section>
    <section className="module-hint"><h3>Domain connection steps</h3>
      <ol>
        <li>Use a domain you already own or purchase one after a registrar integration becomes available.</li>
        <li>Verify the authoritative registrar, DNS zone and hosting server IP/nameservers.</li>
        <li>Change DNS only through an approved zone-scoped provider connection.</li>
        <li>Confirm actual DNS resolution, a valid certificate and expected website content over HTTPS.</li>
      </ol>
      <p>Automatic nameserver changes, Cloudflare DNS updates, SSL issuance and live connection checks remain disabled until vendor/zone ownership is verified.</p>
    </section>
    <div className="action-area">
      <button className="disabled-primary" disabled type="button">Connect DNS (requires approval)</button>
      <button className="disabled-outline" disabled type="button">Register a domain (not available)</button>
    </div>
  </div>;
}
