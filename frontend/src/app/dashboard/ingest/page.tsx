"use client";

import { useState } from "react";
import Link from "next/link";

export default function IngestPage() {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [jobId, setJobId] = useState("");

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;

    setStatus("loading");
    setMessage("Initializing ingestion pipeline...");

    try {
      // Stub: in a real app, you'd get the JWT token here
      const token = "dummy-token-for-now"; 
      
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ingest/repo`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ repo_url: repoUrl, branch })
      });

      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Failed to start ingestion");
      }

      setJobId(data.job_id);
      setStatus("success");
      setMessage(data.message);
      
      // Optionally start polling for status here
    } catch (err: any) {
      setStatus("error");
      setMessage(err.message);
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
          <span className="badge badge-purple">Phase 2 Active</span>
        </div>
      </header>

      <main style={{ maxWidth: 800, margin: "0 auto", padding: "60px 2rem", position: "relative", zIndex: 1 }}>
        <div className="fade-in-up" style={{ marginBottom: 40 }}>
          <h1 style={{ fontSize: "2rem", fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 8 }}>
            Ingest Repository
          </h1>
          <p style={{ color: "var(--color-text-muted)" }}>
            Clone a GitHub repo, extract semantic chunks via tree-sitter AST, and store embeddings in Qdrant and the dependency graph in Neo4j.
          </p>
        </div>

        <form onSubmit={handleIngest} className="glass-card fade-in-up" style={{ padding: 32, animationDelay: "0.1s" }}>
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", marginBottom: 8, fontSize: "0.9rem", fontWeight: 600 }}>GitHub Repository URL</label>
            <input 
              type="text" 
              className="input-field" 
              placeholder="https://github.com/fastapi/fastapi"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              required
            />
          </div>

          <div style={{ marginBottom: 32 }}>
            <label style={{ display: "block", marginBottom: 8, fontSize: "0.9rem", fontWeight: 600 }}>Branch</label>
            <input 
              type="text" 
              className="input-field" 
              placeholder="main"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary" 
            style={{ width: "100%", justifyContent: "center" }}
            disabled={status === "loading"}
          >
            {status === "loading" ? "⏳ Initializing Pipeline..." : "🚀 Start Ingestion"}
          </button>

          {status === "success" && (
            <div style={{ marginTop: 24, padding: 16, background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "var(--radius-md)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#6ee7b7", fontWeight: 600, marginBottom: 4 }}>
                ✅ Ingestion Queued
              </div>
              <div style={{ fontSize: "0.9rem", color: "var(--color-text-muted)" }}>{message}</div>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-faint)", marginTop: 8 }}>Job ID: {jobId}</div>
            </div>
          )}

          {status === "error" && (
            <div style={{ marginTop: 24, padding: 16, background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "var(--radius-md)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#fca5a5", fontWeight: 600, marginBottom: 4 }}>
                ❌ Error
              </div>
              <div style={{ fontSize: "0.9rem", color: "var(--color-text-muted)" }}>{message}</div>
            </div>
          )}
        </form>
        
        <div className="fade-in-up" style={{ marginTop: 32, animationDelay: "0.2s" }}>
           <h3 style={{ fontSize: "1.1rem", marginBottom: 12 }}>Under the hood (Phase 2):</h3>
           <ul style={{ color: "var(--color-text-muted)", fontSize: "0.9rem", lineHeight: 1.8, paddingLeft: 20 }}>
             <li><strong>AST Chunker:</strong> Parses code into `Function` and `Class` nodes instead of character splitting.</li>
             <li><strong>Voyage Embedder:</strong> Embeds chunks using `voyage-code-2` optimized for source code.</li>
             <li><strong>Qdrant Upsert:</strong> Stores vectors + metadata for fast cosine similarity search.</li>
             <li><strong>Neo4j Graph:</strong> Builds `File -[:CONTAINS]-&gt; Function` relationships.</li>
           </ul>
        </div>
      </main>
    </div>
  );
}
