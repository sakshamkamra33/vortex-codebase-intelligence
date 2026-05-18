"use client";

import { useState } from "react";
import Link from "next/link";

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [statusMessage, setStatusMessage] = useState("Initializing RAG Agent...");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<any[]>([]);
  const [cacheHit, setCacheHit] = useState(false);
  const [latency, setLatency] = useState(0);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    setStatus("loading");
    setStatusMessage("🔍 Initiating RAG Agent...");
    setAnswer("");
    setSources([]);
    setCacheHit(false);
    
    const startTime = Date.now();

    try {
      const token = "dummy-token-for-now"; 
      
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/query/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream"
        },
        body: JSON.stringify({ question: query, use_cache: true })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to process query");
      }

      if (!res.body) {
        throw new Error("Response body is not readable");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value, { stream: !done });
          buffer += chunk;

          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const cleanLine = line.trim();
            if (cleanLine.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(cleanLine.slice(6));
                
                if (parsed.type === "status") {
                  setStatusMessage(parsed.content);
                  if (parsed.content.includes("Cache Hit")) {
                    setCacheHit(true);
                  }
                } else if (parsed.type === "token") {
                  setAnswer(prev => prev + parsed.content);
                } else if (parsed.type === "sources") {
                  setSources(parsed.content);
                } else if (parsed.type === "done") {
                  setStatus("success");
                  setLatency(Date.now() - startTime);
                } else if (parsed.type === "error") {
                  setStatus("error");
                  setAnswer(`❌ API Error: ${parsed.content}`);
                  await reader.cancel();
                  return;
                }
              } catch (parseError) {
                console.error("SSE parse error", parseError);
              }
            }
          }
        }
      }
    } catch (err: any) {
      setStatus("error");
      setAnswer(`❌ Error: ${err.message}`);
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
          <span className="badge badge-purple">Phase 3 Streaming Active</span>
        </div>
      </header>

      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "60px 2rem", position: "relative", zIndex: 1 }}>
        <div className="fade-in-up" style={{ marginBottom: 40, textAlign: "center" }}>
          <h1 style={{ fontSize: "2.2rem", fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 8 }}>
            Ask Codebase
          </h1>
          <p style={{ color: "var(--color-text-muted)" }}>
            Powered by Hybrid Search (BM25 + Vector), LangGraph Self-Correction, and Redis Semantic Cache.
          </p>
        </div>

        <form onSubmit={handleQuery} className="fade-in-up" style={{ animationDelay: "0.1s", marginBottom: 40 }}>
          <div style={{ position: "relative", display: "flex", gap: 12 }}>
            <input 
              type="text" 
              className="input-field" 
              style={{ padding: "16px 24px", fontSize: "1.1rem", borderRadius: "var(--radius-xl)" }}
              placeholder="e.g. How does the authentication middleware work?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={status === "loading"}
              required
            />
            <button 
              type="submit" 
              className="btn-primary"
              style={{ borderRadius: "var(--radius-xl)", padding: "0 32px" }}
              disabled={status === "loading"}
            >
              {status === "loading" ? "⏳" : "✨ Search"}
            </button>
          </div>
        </form>

        {status === "loading" && (
          <div className="fade-in-up glass-card" style={{ padding: 32, animationDelay: "0.2s" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--gradient-brand)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>
                  🌀
                </div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>Vortex AI</h3>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <span className="badge badge-purple" style={{ animation: "pulse 1.5s infinite" }}>
                  ⚙️ {statusMessage}
                </span>
              </div>
            </div>

            <div style={{ fontSize: "1.05rem", lineHeight: 1.8, whiteSpace: "pre-wrap", minHeight: 80 }}>
              {answer || <span style={{ color: "var(--color-text-faint)" }}>Reading files and tracing relationships...</span>}
              <span className="cursor-blink" style={{ display: "inline-block", width: 8, height: 16, background: "var(--color-primary)", marginLeft: 4 }}></span>
            </div>
          </div>
        )}

        {status === "success" && (
          <div className="fade-in-up glass-card" style={{ padding: 32, animationDelay: "0.2s" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--gradient-brand)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>
                  🌀
                </div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>Vortex AI</h3>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                {cacheHit && <span className="badge badge-green">⚡ Cache Hit</span>}
                <span className="badge badge-purple">⏱️ {latency}ms</span>
              </div>
            </div>

            <div style={{ fontSize: "1.05rem", lineHeight: 1.8, marginBottom: 32, whiteSpace: "pre-wrap" }}>
              {answer}
            </div>

            {sources && sources.length > 0 && (
              <div>
                <h4 style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Sources Retrieved
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {sources.map((src: any, idx: number) => (
                    <div key={idx} style={{ 
                      padding: "12px 16px", 
                      background: "rgba(255,255,255,0.03)", 
                      border: "1px solid var(--color-border)", 
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}>
                      <span style={{ fontFamily: "monospace", fontSize: "0.85rem", color: "var(--color-accent-light)" }}>
                        {src.file_path}
                      </span>
                      {src.score && (
                        <span style={{ fontSize: "0.8rem", color: "var(--color-text-faint)" }}>
                          Score: {src.score.toFixed(3)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {status === "error" && (
          <div className="fade-in-up glass-card" style={{ padding: 32, animationDelay: "0.2s", border: "1px solid rgba(239,68,68,0.2)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <span style={{ fontSize: 24 }}>❌</span>
              <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "#fca5a5" }}>Error Occurred</h3>
            </div>
            <div style={{ fontSize: "1rem", lineHeight: 1.6, color: "var(--color-text-muted)" }}>
              {answer}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
