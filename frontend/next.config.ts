import type { NextConfig } from "next";

function backendOrigin(): string | null {
  const raw = process.env.OPANEL_BACKEND_ORIGIN;
  if (!raw) return null; // CI builds a disconnected, nonfunctional shell.
  const parsed = new URL(raw);
  if (
    parsed.protocol !== "https:" || parsed.username || parsed.password ||
    parsed.search || parsed.hash || parsed.pathname !== "/" ||
    !/^[a-z0-9.-]+$/i.test(parsed.hostname)
  ) throw new Error("OPANEL_BACKEND_ORIGIN must be one trusted HTTPS origin");
  return parsed.origin;
}

const backend = backendOrigin();
const config: NextConfig = {
  poweredByHeader: false,
  trailingSlash: true,
  async rewrites() {
    if (!backend) return [];
    // Browser sees ONE OPanel origin. The independent Django backend owns
    // HttpOnly session cookies, CSRF, callback and confidential Console calls.
    return [
      { source: "/api/session/", destination: backend + "/api/session/" },
      { source: "/auth/start/", destination: backend + "/auth/start/" },
      { source: "/auth/callback/", destination: backend + "/auth/callback/" },
      { source: "/auth/logout/", destination: backend + "/auth/logout/" },
      { source: "/health/", destination: backend + "/health/" },
    ];
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "Referrer-Policy", value: "no-referrer" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    ] }];
  },
};
export default config;
