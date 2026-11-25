import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IGR Maharashtra Free Search Automation",
  description: "Automated Playwright & FastAPI dashboard for Maharashtra Department of Registration and Stamps Free Search",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
