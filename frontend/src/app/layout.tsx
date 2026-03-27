import type { Metadata } from "next";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

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
    <html lang="en" suppressHydrationWarning className={cn("dark font-sans", geist.variable)}>
      <body suppressHydrationWarning style={{ margin: 0, padding: 0, background: '#121212', color: '#e5e5e5', overflow: 'hidden' }}>
        {children}
      </body>
    </html>
  );
}
