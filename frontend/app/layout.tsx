import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "BrandGuard AI — Intelligent Brand Governance",
  description:
    "Pre-publication brand governance: tone, claims, visual and accessibility inspection with clause-level citations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
