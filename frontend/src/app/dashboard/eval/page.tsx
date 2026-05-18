"use client";

import { useState } from "react";
import Link from "next/link";

export default function EvalPage() {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [results, setResults] = useState<any>(null);

  const runEvaluation = async () => {
    setStatus("loading");
    setResults(null);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/eval/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer dummy-token`
        }
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to run eval");

      setResults(data);
      setStatus("success");
    } catch (err) {
      setStatus("error");
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
          <span className="badge badge-purple">Phase 4 Active</span>
        </div>
      </header>

      <main style={{ maxWidth: 900, margin: "0 auto", padding: "60px 2rem", position: "relative", zIndex: 1 }}>
        <div className="fade-in-up" style={{ marginBottom: 40, textAlign: "center" }}>
          <h1 style={{ fontSize: "2.2rem", fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 8 }}>
            Ragas Evaluation
          </h1>
          <p style={{ color: "var(--color-text-muted)" }}>
            Automated benchmarking for Context Precision, Faithfulness, and Answer Relevance.
          </p>
          <div style={{ marginTop: 24 }}>
             <button onClick={runEvaluation} className="btn-primary" disabled={status === "loading"}>
                {status === "loading" ? "⏳ Running Benchmark Suite..." : "▶️ Run Full Evaluation"}
             </button>
          </div>
        </div>

        {status === "success" && results && (
          <div className="fade-in-up" style={{ animationDelay: "0.1s" }}>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <div style={{ fontSize: "4rem", fontWeight: 900, lineHeight: 1 }} className="gradient-text">
                {(results.overall_score * 100).toFixed(1)}%
              </div>
              <div style={{ color: "var(--color-text-muted)", fontWeight: 600, marginTop: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Overall RAG Score
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 20 }}>
              
              <div className="glass-card" style={{ padding: 24, textAlign: "center" }}>
                 <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>🎯</div>
                 <h3 style={{ fontSize: "1.1rem", marginBottom: 4 }}>Context Precision</h3>
                 <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--color-accent-light)" }}>
                   {(results.metrics.context_precision * 100).toFixed(1)}%
                 </div>
                 <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", marginTop: 8 }}>
                   Did we retrieve the exact right code chunks?
                 </p>
              </div>

              <div className="glass-card" style={{ padding: 24, textAlign: "center" }}>
                 <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>🛡️</div>
                 <h3 style={{ fontSize: "1.1rem", marginBottom: 4 }}>Faithfulness</h3>
                 <div style={{ fontSize: "2rem", fontWeight: 800, color: "#6ee7b7" }}>
                   {(results.metrics.faithfulness * 100).toFixed(1)}%
                 </div>
                 <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", marginTop: 8 }}>
                   Is the answer completely grounded in the retrieved code (no hallucinations)?
                 </p>
              </div>

              <div className="glass-card" style={{ padding: 24, textAlign: "center" }}>
                 <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>💡</div>
                 <h3 style={{ fontSize: "1.1rem", marginBottom: 4 }}>Answer Relevance</h3>
                 <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--color-primary-light)" }}>
                   {(results.metrics.answer_relevancy * 100).toFixed(1)}%
                 </div>
                 <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", marginTop: 8 }}>
                   Did the agent directly answer the user's prompt?
                 </p>
              </div>

            </div>
          </div>
        )}
      </main>
    </div>
  );
}
