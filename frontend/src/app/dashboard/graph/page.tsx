"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import ForceGraph2D from "react-force-graph-2d";

interface GraphData {
  nodes: { id: string; label: string; name: string }[];
  links: { source: string; target: string; type: string }[];
}

export default function GraphExplorerPage() {
  const [repoId, setRepoId] = useState("sakshamkamra33/vortex-codebase-intelligence_main");
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fgRef = useRef<any>(null);

  // Determine color based on node type
  const getNodeColor = (label: string) => {
    switch (label) {
      case "File": return "#7c3aed"; // Purple
      case "Function": return "#06b6d4"; // Cyan
      case "Class": return "#f59e0b"; // Amber
      default: return "#9ca3af";
    }
  };

  const fetchGraph = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!repoId) return;

    setLoading(true);
    setError("");
    
    // Normalize repo ID string to match backend standard
    // e.g. https://github.com/org/repo -> repo_main
    const formattedId = repoId.split('/').pop() || repoId;

    try {
      const token = "dummy-token-for-now";
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/graph/dependencies?repo_id=${formattedId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const resData = await res.json();
      if (!res.ok) throw new Error(resData.detail || "Failed to fetch graph");
      
      if (resData.nodes.length === 0) {
        throw new Error("No nodes found for this repository. Try ingesting it first.");
      }

      setData({
        nodes: resData.nodes,
        links: resData.links
      });
      
      // Auto-zoom to fit after data loads
      setTimeout(() => {
        if (fgRef.current) fgRef.current.zoomToFit(400);
      }, 500);
      
    } catch (err: any) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial load
    fetchGraph();
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-bg)", position: "relative", display: "flex", flexDirection: "column" }}>
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
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <form onSubmit={fetchGraph} style={{ display: "flex", gap: 8 }}>
              <input 
                type="text" 
                value={repoId}
                onChange={(e) => setRepoId(e.target.value)}
                placeholder="Repo ID (e.g. repo_main)"
                style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid var(--color-border)",
                  color: "white",
                  padding: "4px 12px",
                  borderRadius: "4px",
                  fontSize: "0.85rem",
                  width: 250
                }}
              />
              <button type="submit" className="btn-primary" style={{ padding: "4px 12px", fontSize: "0.85rem" }}>
                Load
              </button>
            </form>
            <span className="badge badge-cyan">Phase 3 Active</span>
          </div>
        </div>
      </header>

      <main style={{ flex: 1, position: "relative", zIndex: 1, display: "flex", flexDirection: "column" }}>
        {loading && (
          <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", zIndex: 10 }}>
            <div style={{ background: "rgba(10,10,15,0.9)", padding: "24px 40px", borderRadius: "12px", border: "1px solid var(--color-border)", display: "flex", alignItems: "center", gap: 16 }}>
              <span className="spinner">🌀</span> Fetching Graph Topology...
            </div>
          </div>
        )}
        
        {error && !error.includes("No nodes found") && (
          <div style={{ position: "absolute", top: 40, left: "50%", transform: "translateX(-50%)", zIndex: 10, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", padding: "16px 24px", borderRadius: "8px", color: "#fca5a5" }}>
            {error}
          </div>
        )}

        {error && error.includes("No nodes found") && (
          <div className="fade-in-up" style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center", width: "100%", padding: "0 20px" }}>
            <div style={{ fontSize: "4rem", marginBottom: 16 }}>📭</div>
            <h3 style={{ fontSize: "1.8rem", fontWeight: 800, marginBottom: 12, letterSpacing: "-0.02em" }}>Graph Database is Empty</h3>
            <p style={{ color: "var(--color-text-muted)", marginBottom: 32, maxWidth: 450, margin: "0 auto 32px", lineHeight: 1.6 }}>
              Looks like there are no nodes in the Neo4j graph for this repository. You need to ingest the code first so we can build the dependency web!
            </p>
            <Link href="/dashboard/ingest" className="btn-primary" style={{ display: "inline-flex", padding: "10px 24px" }}>
              🚀 Go to Ingestion
            </Link>
          </div>
        )}

        <div style={{ position: "absolute", bottom: 20, left: 20, zIndex: 10, background: "rgba(10,10,15,0.8)", padding: 16, borderRadius: 8, border: "1px solid var(--color-border)" }}>
          <h4 style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--color-text-muted)", marginBottom: 12 }}>Legend</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}><div style={{ width: 12, height: 12, borderRadius: "50%", background: "#7c3aed" }}/> <span style={{ fontSize: "0.85rem" }}>File</span></div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}><div style={{ width: 12, height: 12, borderRadius: "50%", background: "#06b6d4" }}/> <span style={{ fontSize: "0.85rem" }}>Function</span></div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}><div style={{ width: 12, height: 12, borderRadius: "50%", background: "#f59e0b" }}/> <span style={{ fontSize: "0.85rem" }}>Class</span></div>
          </div>
        </div>

        {data && (
          <div style={{ flex: 1, width: "100%", height: "100%" }}>
            <ForceGraph2D
              ref={fgRef}
              graphData={data}
              nodeLabel="name"
              nodeColor={(node: any) => getNodeColor(node.label)}
              nodeRelSize={6}
              linkColor={() => "rgba(255,255,255,0.15)"}
              linkWidth={1.5}
              linkDirectionalArrowLength={3.5}
              linkDirectionalArrowRelPos={1}
              backgroundColor="#0a0a0f"
              d3Force={(d3: any) => {
                // Adjust physics forces for a better spread
                d3.force("charge").strength(-400);
                d3.force("link").distance(50);
              }}
              onNodeClick={(node: any) => {
                // Center camera on node when clicked
                fgRef.current.centerAt(node.x, node.y, 1000);
                fgRef.current.zoom(4, 2000);
              }}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                const label = node.name;
                const fontSize = 12/globalScale;
                ctx.font = `${fontSize}px Sans-Serif`;
                
                // Draw circle
                ctx.beginPath();
                ctx.arc(node.x, node.y, 4, 0, 2 * Math.PI, false);
                ctx.fillStyle = getNodeColor(node.label);
                ctx.fill();
                
                // Draw text
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.fillText(label, node.x, node.y + 8);
              }}
            />
          </div>
        )}
      </main>
    </div>
  );
}
