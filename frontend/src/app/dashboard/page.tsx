"use client";

import Link from "next/link";

const MODULES = [
  { icon: "📥", title: "Ingest Repository", desc: "Clone a GitHub repo and trigger AST-based ingestion into Qdrant + Neo4j.", href: "/dashboard/ingest", status: "Active", ready: true },
  { icon: "💬", title: "Ask Codebase", desc: "Natural language Q&A with hybrid BM25 + vector search and LangGraph agent.", href: "/dashboard/query", status: "Active", ready: true },
  { icon: "🕸️", title: "Graph Explorer", desc: "Visualize function call graphs and dependency chains from Neo4j.", href: "/dashboard/graph", status: "Active", ready: true },
  { icon: "⚡", title: "Cache Monitor", desc: "Real-time Redis semantic cache hit/miss rates and TTL stats.", href: "/dashboard/cache", status: "Active", ready: true },
  { icon: "🤖", title: "PR Review Agent", desc: "Auto-review pull requests using the multi-step LangGraph self-correction loop.", href: "/dashboard/pr-review", status: "Active", ready: true },
  { icon: "📊", title: "Ragas Evaluation", desc: "Run benchmarks: Faithfulness, Context Precision, Answer Relevance.", href: "/dashboard/eval", status: "Active", ready: true },
];

export default function DashboardPage() {
  return (
    <div style={{ minHeight: "100vh", background: "var(--color-bg)", position: "relative" }}>
      <div className="bg-mesh" />

      {/* Header */}
      <header style={{
        background: "rgba(10,10,15,0.8)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--color-border)",
        padding: "0 2rem",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", height: 64 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <span style={{ fontSize: 20 }}>🌀</span>
            <span style={{ fontWeight: 800, fontSize: "1.1rem" }}>
              <span className="gradient-text">Vortex</span>
              <span style={{ color: "var(--color-text-muted)" }}>RAG</span>
            </span>
          </Link>
          <span className="badge badge-purple">Dashboard</span>
        </div>
      </header>

      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "60px 2rem", position: "relative", zIndex: 1 }}>
        <div className="fade-in-up" style={{ marginBottom: 48 }}>
          <h1 style={{ fontSize: "2.2rem", fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 8 }}>
            Mission Control
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: "1rem" }}>
            All VortexRAG modules — built phase by phase.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
          {MODULES.map((mod, i) => (
            <Link href={mod.ready ? mod.href : "#"} key={mod.title} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="glass-card" style={{
                padding: 28,
                opacity: mod.ready ? 1 : 0.65,
                cursor: mod.ready ? "pointer" : "default",
                animationDelay: `${i * 0.08}s`,
                height: "100%",
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
                  <span style={{ fontSize: "2rem" }}>{mod.icon}</span>
                  <span className="badge badge-purple" style={{ fontSize: "0.7rem" }}>{mod.status}</span>
                </div>
                <h2 style={{ fontSize: "1.05rem", fontWeight: 700, marginBottom: 8 }}>{mod.title}</h2>
                <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", lineHeight: 1.65 }}>{mod.desc}</p>
                {!mod.ready && (
                  <div style={{ marginTop: 16, fontSize: "0.78rem", color: "var(--color-text-faint)" }}>
                    🔒 Coming in {mod.status}
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
