export const modules = [
  { slug: "overview", name: "Overview", group: "Workspace", symbol: "⌂", description: "Service health, usage and billing summary.", available: true },
  { slug: "websites", name: "Websites", group: "Hosting", symbol: "▣", description: "Website creation, PHP runtime and document roots.", available: false },
  { slug: "files", name: "File manager", group: "Hosting", symbol: "▤", description: "Browse, upload and manage server files.", available: false },
  { slug: "domains", name: "Domains & subdomains", group: "Hosting", symbol: "◎", description: "Attach domains, redirects and subdomains.", available: false },
  { slug: "dns", name: "DNS manager", group: "Hosting", symbol: "⌘", description: "View and edit authoritative DNS zones.", available: false },
  { slug: "databases", name: "Databases", group: "Advanced", symbol: "▥", description: "Create databases, users and access permissions.", available: false },
  { slug: "email", name: "Email accounts", group: "Advanced", symbol: "✉", description: "Mailboxes, aliases and webmail access.", available: false },
  { slug: "ssl", name: "SSL certificates", group: "Advanced", symbol: "◇", description: "Certificate lifecycle and HTTPS settings.", available: false },
  { slug: "backups", name: "Backups", group: "Advanced", symbol: "↺", description: "Create and restore verified backups.", available: false },
  { slug: "integrations", name: "Integrations", group: "Hosting", symbol: "⬡", description: "WordPress, Cloudflare DNS and GitHub static deployment connectors.", available: false },
  { slug: "statistics", name: "Resource usage", group: "Advanced", symbol: "▦", description: "Historical disk and bandwidth measurements.", available: true },
  { slug: "settings", name: "Settings", group: "Account", symbol: "⚙", description: "Review access authority and session settings.", available: true },
] as const;

export type ModuleSlug = typeof modules[number]["slug"];
export const findModule = (slug: string) => modules.find(module => module.slug === slug);
export const moduleGroups = ["Workspace", "Hosting", "Advanced", "Account"] as const;
