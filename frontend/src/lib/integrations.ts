/** Provider-neutral entries; no live connection is implied by a visible card. */
export const integrationCatalog = [
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
export type IntegrationCardData = typeof integrationCatalog[number];
