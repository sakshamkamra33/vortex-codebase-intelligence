"""
VortexRAG — Services Package

Phase 2+: Core business logic lives here.

  services/
  ├── embedder.py        # Voyage AI embedding wrapper
  ├── ast_chunker.py     # tree-sitter AST-based code chunker  [Phase 2]
  ├── ingestion.py       # Full repo ingestion pipeline         [Phase 2]
  ├── graph_builder.py   # Neo4j call-graph construction        [Phase 2]
  ├── hybrid_search.py   # BM25 + vector search + RRF          [Phase 3]
  ├── semantic_cache.py  # Redis cosine similarity cache        [Phase 3]
  ├── rag_agent.py       # LangGraph self-correction agent      [Phase 4]
  ├── evaluator.py       # Ragas evaluation suite               [Phase 4]
  └── pr_reviewer.py     # GitHub PR review agent               [Phase 5]
"""
