"use client";

import { useState } from "react";
import Link from "next/link";

export default function PRReviewPage() {
  const [prUrl, setPrUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<any>(null);

  const handleReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prUrl) return;

    // Parse PR URL
    const match = prUrl.match(/github\.com\/([^\/]+)\/([^\/]+)\/pull\/(\d+)/);
    if (!match) {
      setStatus("error");
      setResult({ message: "Invalid GitHub PR URL. Format: https://github.com/owner/repo/pull/123" });
      return;
    }

    const owner = match[1];
    const repo = match[2];
    const prNumber = parseInt(match[3], 10);

    setStatus("loading");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/github/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          repo_owner: owner,
          repo_name: repo,
          pr_number: prNumber,
          repo_id: `${repo}_main` // Standard main branch mapping
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to trigger PR review");
      }

      setStatus("success");
      setResult(data);
    } catch (err: any) {
      setStatus("error");
      setResult({ message: err.message || "Failed to review PR diff" });
    }
  };

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
          <span className="badge badge-purple">Phase 5 Active</span>
        </div>
      </header>

      <main style={{ maxWidth: 800, margin: "0 auto", padding: "60px 2rem", position: "relative", zIndex: 1 }}>
        <div className="fade-in-up" style={{ marginBottom: 40, textAlign: "center" }}>
          <h1 style={{ fontSize: "2.2rem", fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 8 }}>
            PR Review Agent
          </h1>
          <p style={{ color: "var(--color-text-muted)" }}>
            Automatically intercepts GitHub webhooks and runs architectural reviews via the LangGraph RAG Agent.
          </p>
        </div>

        <div className="fade-in-up glass-card" style={{ padding: 32, animationDelay: "0.1s", marginBottom: 32 }}>
          <h3 style={{ fontSize: "1.1rem", marginBottom: 16, fontWeight: 700 }}>Manual Trigger (Live Review)</h3>
          <form onSubmit={handleReview}>
            <div style={{ position: "relative", display: "flex", gap: 12 }}>
              <input 
                type="text" 
                className="input-field" 
                placeholder="https://github.com/sakshamkamra33/devops-ci-cd-dashboard/pull/1"
                value={prUrl}
                onChange={(e) => setPrUrl(e.target.value)}
                required
              />
              <button 
                type="submit" 
                className="btn-primary"
                disabled={status === "loading"}
              >
                {status === "loading" ? "⏳ Analyzing..." : "👀 Review"}
              </button>
            </div>
          </form>
        </div>

        {status === "error" && result && (
          <div className="fade-in-up glass-card" style={{ padding: 24, border: "1px solid rgba(239,68,68,0.2)", marginBottom: 32 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#fca5a5", fontWeight: 600, marginBottom: 8 }}>
              ❌ Error Occurred
            </div>
            <div style={{ fontSize: "0.95rem", color: "var(--color-text-muted)", lineHeight: 1.6 }}>{result.message}</div>
          </div>
        )}

        {status === "success" && result && (
          <div className="fade-in-up glass-card" style={{ padding: 32, animationDelay: "0.2s" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--gradient-brand)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>
                  🤖
                </div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>Agent Output</h3>
              </div>
              <span className={`badge ${result.status === 'success' ? 'badge-green' : 'badge-purple'}`}>
                {result.status === 'success' ? '🚀 Posted to GitHub' : '⚙️ Local Preview'}
              </span>
            </div>
            
            <div style={{ 
              padding: 24, 
              background: "rgba(255,255,255,0.02)", 
              border: "1px solid var(--color-border)", 
              borderRadius: "var(--radius-md)",
              whiteSpace: "pre-wrap",
              fontSize: "0.95rem",
              lineHeight: 1.7,
              color: "var(--color-text)",
              fontFamily: "inherit"
            }}>
              {result.comment}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
