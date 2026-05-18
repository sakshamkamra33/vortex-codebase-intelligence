import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "VortexRAG — Enterprise Codebase Intelligence",
  description:
    "Ask your codebase anything. Review PRs automatically. Understand architecture instantly.",
  keywords: ["RAG", "codebase", "AI", "vector search", "GraphRAG", "code intelligence"],
  openGraph: {
    title: "VortexRAG",
    description: "Enterprise Codebase Intelligence Platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
