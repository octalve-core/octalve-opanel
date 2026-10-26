import type { Metadata } from "next";
import "./globals.css";
import "./uploads.css";
export const metadata: Metadata = {
  title: "Octalve OPanel | Hosting Management",
  description: "Secure, independent hosting management through Octalve Console.",
  referrer: "no-referrer",
};
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
