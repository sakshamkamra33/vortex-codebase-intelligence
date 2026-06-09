"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface CacheStats {
  hits: number;
  misses: number;
  hit_rate_pct: number;
  active_entries: number;
}

export default function CacheMonitorPage() {
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [flushing, setFlushing] = useState(false);

  const fetchStats = async () => {
    try {
      const token = "dummy-token-for-now";
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/cache/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch cache stats", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Poll every 5 seconds
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleFlush = async () => {
    if (!confirm("Are you sure you want to flush the semantic cache? All embeddings will be cleared.")) return;
    setFlushing(true);
    try {
      const token = "dummy-token-for-now";
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/cache/flush`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchStats();
    } catch (err) {
      console.error("Failed to flush cache", err);
    } finally {
      setFlushing(false);
    }
  };

  const costSavings = stats ? ((stats.hits * 0.005) + (stats.hits * 0.001)).toFixed(3) : "0.000";

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-bg)", position: "relative" }}>
      <div className="bg-mesh" />

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
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <Link href="/dashboard" style={{ color: "var(--color-text-muted)", textDecoration: "none", fontSize: "1.2rem" }}>
              ←
            </Link>
            <span style={{ fontWeight: 800, fontSize: "1.1rem" }}>
              <span className="gradient-text">Vortex</span>
              <span style={{ color: "var(--color-text-muted)" }}>RAG</span>
            </span>
          </div>
          <span className="badge badge-cyan">Phase 3 Active</span>
        </div>
      </header>

      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "60px 2rem", position: "relative", zIndex: 1 }}>
        <div className="fade-in-up" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 40 }}>
          <div>
            <h1 style={{ fontSize: "2rem", fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 8 }}>
              Semantic Cache Monitor
            </h1>
            <p style={{ color: "var(--color-text-muted)" }}>
              Real-time analytics for Redis-powered query caching.
            </p>
          </div>
          <button onClick={handleFlush} className="btn-ghost" disabled={flushing} style={{ border: "1px solid rgba(239, 68, 68, 0.3)", color: "#ef4444" }}>
            {flushing ? "Flushing..." : "🗑️ Flush Cache"}
          </button>
        </div>

        {loading && !stats ? (
          <div style={{ textAlign: "center", padding: "40px", color: "var(--color-text-muted)" }}>
            Loading stats...
          </div>
        ) : stats ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 20 }}>
            {/* Hit Rate */}
            <div className="glass-card fade-in-up" style={{ padding: 32, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
              <div style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 16 }}>
                Hit Rate
              </div>
              <div style={{ fontSize: "3.5rem", fontWeight: 900, color: "var(--color-success)" }}>
                {stats.hit_rate_pct}%
              </div>
            </div>

            <div className="glass-card fade-in-up" style={{ padding: 32, animationDelay: "0.1s" }}>
              <div style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 16 }}>
                Total Queries
              </div>
              <div style={{ fontSize: "2.5rem", fontWeight: 900 }}>
                {stats.hits + stats.misses}
              </div>
              <div style={{ display: "flex", gap: 16, marginTop: 12, fontSize: "0.9rem" }}>
                <span style={{ color: "var(--color-success)" }}>{stats.hits} Hits</span>
                <span style={{ color: "var(--color-error)" }}>{stats.misses} Misses</span>
              </div>
            </div>

            <div className="glass-card fade-in-up" style={{ padding: 32, animationDelay: "0.2s" }}>
              <div style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 16 }}>
                Active Entries
              </div>
              <div style={{ fontSize: "2.5rem", fontWeight: 900, color: "var(--color-accent-light)" }}>
                {stats.active_entries}
              </div>
              <div style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--color-text-faint)" }}>
                Vectors currently cached in Redis
              </div>
            </div>

            <div className="glass-card fade-in-up" style={{ padding: 32, animationDelay: "0.3s" }}>
              <div style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 16 }}>
                Est. Cost Savings
              </div>
              <div style={{ fontSize: "2.5rem", fontWeight: 900, color: "#f59e0b" }}>
                ${costSavings}
              </div>
              <div style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--color-text-faint)" }}>
                Saved API tokens & compute
              </div>
            </div>
          </div>
        ) : (
          <div className="glass-card" style={{ padding: 40, textAlign: "center", color: "var(--color-error)" }}>
            Failed to load cache statistics. Ensure Redis is connected.
          </div>
        )}
      </main>
    </div>
  );
}
