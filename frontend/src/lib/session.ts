export type HostingUsage = {
  disk_used_mb: number; disk_limit_mb: number;
  bandwidth_used_mb: number; bandwidth_limit_mb: number;
  recorded_at: string;
};
export type HostingOverview = {
  label: string; domain: string; next_due_date: string;
  usage: HostingUsage | null;
};
export type PanelSession = {
  authenticated: boolean;
  subject_id?: number;
  service_id?: number;
  capabilities?: string[];
  overview?: HostingOverview | null;
  csrf_token?: string;
};
export async function currentSession(signal?: AbortSignal): Promise<PanelSession> {
  const result = await fetch("/api/session/", {
    method: "GET", cache: "no-store", credentials: "same-origin",
    signal, headers: { Accept: "application/json" },
  });
  if (!result.ok) return { authenticated: false };
  const body: unknown = await result.json();
  if (!body || typeof body !== "object") return { authenticated: false };
  const data = body as PanelSession;
  if (data.authenticated !== true ||
      !Number.isSafeInteger(data.service_id) ||
      !Number.isSafeInteger(data.subject_id) ||
      JSON.stringify(data.capabilities) !== JSON.stringify(["overview"])) {
    return { authenticated: false };
  }
  return data;
}
export function consoleDestination(): string | null {
  const raw = process.env.NEXT_PUBLIC_CONSOLE_WEB_ORIGIN || "";
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" || url.username || url.password ||
        url.pathname !== "/" || url.search || url.hash) return null;
    return url.origin;
  } catch { return null; }
}
