import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Diagram Editor",
  description: "Visual AWS architecture diagram editor",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning style={{ margin: 0, padding: 0, background: '#121212', color: '#e5e5e5', overflow: 'hidden' }}>
        {children}
      </body>
    </html>
  );
}
