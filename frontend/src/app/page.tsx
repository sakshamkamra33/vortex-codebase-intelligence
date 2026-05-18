"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

const TECH_STACK = [
  { name: "Qdrant", desc: "Vector DB", color: "#7c3aed", icon: "🔮" },
  { name: "Neo4j", desc: "Graph DB", color: "#06b6d4", icon: "🕸️" },
  { name: "Redis", desc: "Semantic Cache", color: "#ef4444", icon: "⚡" },
  { name: "LangGraph", desc: "Agent Loop", color: "#10b981", icon: "🤖" },
  { name: "FastAPI", desc: "Backend", color: "#f59e0b", icon: "🚀" },
  { name: "Ragas", desc: "Evaluation", color: "#a78bfa", icon: "📊" },
];

const FEATURES = [
  {
    icon: "🌳",
    title: "AST-Based Chunking",
    desc: "Parses code using tree-sitter into functions, classes, and methods — not arbitrary character splits. Preserves semantic boundaries.",
    badge: "Phase 2",
    badgeColor: "badge-purple",
  },
  {
    icon: "🕸️",
    title: "GraphRAG + Neo4j",
    desc: "Maps function call graphs so when Function A calls Function B across files, the system knows they're related — even in different repos.",
    badge: "Phase 3",
    badgeColor: "badge-cyan",
  },
  {
    icon: "🔍",
    title: "Hybrid Search (BM25 + Dense)",
    desc: "Combines keyword precision (BM25) with semantic understanding (voyage-code-2 embeddings) using Reciprocal Rank Fusion.",
    badge: "Phase 3",
    badgeColor: "badge-purple",
  },
  {
    icon: "⚡",
    title: "Redis Semantic Cache",
    desc: "Caches LLM responses by query similarity (cosine ≥ 0.92). Cuts API costs by ~70% and reduces latency from 3s → 100ms.",
    badge: "Phase 3",
    badgeColor: "badge-cyan",
  },
  {
    icon: "🤖",
    title: "LangGraph Self-Correction",
    desc: "A stateful multi-step agent that retrieves, grades context quality, and reruns with a better query if the first answer is poor.",
    badge: "Phase 4",
    badgeColor: "badge-purple",
  },
  {
    icon: "📊",
    title: "Ragas Evaluation",
    desc: "Automated benchmarking for Faithfulness, Context Precision, and Answer Relevance. Real numbers on your resume.",
    badge: "Phase 4",
    badgeColor: "badge-green",
  },
];

const STATS = [
  { value: "~70%", label: "API Cost Reduction", sub: "via semantic cache" },
  { value: "<100ms", label: "Cache Hit Latency", sub: "vs 3s uncached" },
  { value: "5", label: "Production Services", sub: "fully orchestrated" },
  { value: "10", label: "Build Phases", sub: "structured rollout" },
];

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    setMounted(true);
    // Check backend health
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
      .then((r) => r.ok ? setApiStatus("online") : setApiStatus("offline"))
      .catch(() => setApiStatus("offline"));
  }, []);

  return (
    <div className="noise" style={{ position: "relative", minHeight: "100vh" }}>
      {/* Background mesh */}
      <div className="bg-mesh" />

      {/* ── Navbar ────────────────────────────── */}
      <nav style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        background: "rgba(10, 10, 15, 0.8)",
        borderBottom: "1px solid var(--color-border)",
        padding: "0 2rem",
      }}>
        <div style={{
          maxWidth: 1200,
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 64,
        }}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "var(--gradient-brand)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
              animation: "spin-slow 8s linear infinite",
            }}>🌀</div>
            <span style={{ fontSize: "1.2rem", fontWeight: 800, letterSpacing: "-0.04em" }}>
              <span className="gradient-text">Vortex</span>
              <span style={{ color: "var(--color-text-muted)" }}>RAG</span>
            </span>
          </div>

          {/* Nav links */}
          <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
            <a href="#features" style={{ color: "var(--color-text-muted)", textDecoration: "none", fontSize: "0.9rem", transition: "color 0.2s" }}
               onMouseEnter={e => (e.currentTarget.style.color = "var(--color-text)")}
               onMouseLeave={e => (e.currentTarget.style.color = "var(--color-text-muted)")}>
              Features
            </a>
            <a href="#stack" style={{ color: "var(--color-text-muted)", textDecoration: "none", fontSize: "0.9rem", transition: "color 0.2s" }}
               onMouseEnter={e => (e.currentTarget.style.color = "var(--color-text)")}
               onMouseLeave={e => (e.currentTarget.style.color = "var(--color-text-muted)")}>
              Stack
            </a>

            {/* API Status badge */}
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div className="dot-live" style={{
                background: apiStatus === "online" ? "var(--color-success)" : apiStatus === "offline" ? "var(--color-error)" : "var(--color-warning)",
              }} />
              <span style={{ fontSize: "0.8rem", color: "var(--color-text-muted)" }}>
                API {apiStatus === "checking" ? "…" : apiStatus}
              </span>
            </div>

            <Link href="/dashboard" className="btn-primary" style={{ padding: "8px 20px", fontSize: "0.85rem" }}>
              Dashboard →
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ──────────────────────────────── */}
      <section style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "120px 2rem 80px",
        textAlign: "center",
        position: "relative",
        zIndex: 1,
      }}>
        {mounted && (
          <>
            <div className="fade-in-up" style={{ marginBottom: 20 }}>
              <span className="badge badge-purple">
                <span>🌀</span> Enterprise-Grade RAG Platform
              </span>
            </div>

            <h1 className="fade-in-up" style={{
              fontSize: "clamp(2.8rem, 6vw, 5rem)",
              fontWeight: 900,
              letterSpacing: "-0.04em",
              lineHeight: 1.05,
              marginBottom: 24,
              animationDelay: "0.1s",
            }}>
              Pull intelligence from
              <br />
              <span className="gradient-text">any codebase.</span>
            </h1>

            <p className="fade-in-up" style={{
              fontSize: "1.2rem",
              color: "var(--color-text-muted)",
              maxWidth: 600,
              margin: "0 auto 48px",
              lineHeight: 1.7,
              animationDelay: "0.2s",
            }}>
              AST-powered chunking · GraphRAG dependency resolution · Hybrid BM25 + Vector search ·
              Self-correcting LangGraph agent · Redis semantic cache
            </p>

            <div className="fade-in-up" style={{
              display: "flex",
              gap: 16,
              justifyContent: "center",
              flexWrap: "wrap",
              animationDelay: "0.3s",
            }}>
              <Link href="/dashboard" className="btn-primary">
                🚀 Open Dashboard
              </Link>
              <a href="https://github.com" className="btn-ghost" target="_blank" rel="noreferrer">
                ⭐ View on GitHub
              </a>
            </div>

            {/* Stats row */}
            <div className="fade-in-up" style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: 16,
              maxWidth: 800,
              margin: "80px auto 0",
              animationDelay: "0.4s",
            }}>
              {STATS.map((stat) => (
                <div key={stat.label} className="glass-card" style={{ padding: "24px 16px", textAlign: "center" }}>
                  <div style={{ fontSize: "2rem", fontWeight: 900, letterSpacing: "-0.04em" }} className="gradient-text">
                    {stat.value}
                  </div>
                  <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text)", marginTop: 4 }}>
                    {stat.label}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: 2 }}>
                    {stat.sub}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* ── Tech Stack ────────────────────────── */}
      <section id="stack" style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "60px 2rem",
        position: "relative",
        zIndex: 1,
      }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 12 }}>
            Production Stack
          </p>
          <h2 style={{ fontSize: "2rem", fontWeight: 800 }}>Built with best-in-class tools</h2>
        </div>
        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          justifyContent: "center",
        }}>
          {TECH_STACK.map((tech, i) => (
            <div key={tech.name} className="glass-card" style={{
              padding: "20px 28px",
              display: "flex",
              alignItems: "center",
              gap: 14,
              animationDelay: `${i * 0.1}s`,
            }}>
              <span style={{ fontSize: "1.8rem" }}>{tech.icon}</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: "1rem" }}>{tech.name}</div>
                <div style={{ fontSize: "0.8rem", color: "var(--color-text-muted)" }}>{tech.desc}</div>
              </div>
              <div style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: tech.color,
                boxShadow: `0 0 8px ${tech.color}`,
                marginLeft: 4,
              }} />
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ──────────────────────────── */}
      <section id="features" style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "60px 2rem 120px",
        position: "relative",
        zIndex: 1,
      }}>
        <div style={{ textAlign: "center", marginBottom: 60 }}>
          <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 12 }}>
            Core Architecture
          </p>
          <h2 style={{ fontSize: "2.2rem", fontWeight: 800, letterSpacing: "-0.03em" }}>
            What makes this <span className="gradient-text">FAANG-level</span>
          </h2>
        </div>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: 24,
        }}>
          {FEATURES.map((feature, i) => (
            <div key={feature.title} className="glass-card" style={{
              padding: "32px",
              animationDelay: `${i * 0.1}s`,
            }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
                <span style={{ fontSize: "2.2rem" }}>{feature.icon}</span>
                <span className={`badge ${feature.badgeColor}`}>{feature.badge}</span>
              </div>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: 10, letterSpacing: "-0.02em" }}>
                {feature.title}
              </h3>
              <p style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", lineHeight: 1.7 }}>
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ────────────────────────────── */}
      <footer style={{
        borderTop: "1px solid var(--color-border)",
        padding: "32px 2rem",
        textAlign: "center",
        color: "var(--color-text-muted)",
        fontSize: "0.85rem",
        position: "relative",
        zIndex: 1,
      }}>
        <span className="gradient-text" style={{ fontWeight: 700 }}>VortexRAG</span>
        {" "}— Enterprise Codebase Intelligence Platform. Built for placements. 🌀
      </footer>
    </div>
  );
}
