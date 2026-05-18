"""
VortexRAG — Hybrid Search (Phase 3 Upgrade)
Combines Qdrant dense vector search with BM25 sparse keyword search using Reciprocal Rank Fusion (RRF).
"""
import logging
import re
from typing import List, Dict, Any, Optional
from qdrant_client.models import Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi

from app.db.qdrant import get_qdrant
from app.services.embedder import EmbeddingService
from app.core.config import settings

logger = logging.getLogger("vortex")

def tokenize_code(text: str) -> List[str]:
    """Code-optimized tokenizer that extracts variables, function names, and alphanumeric keys."""
    if not text:
        return []
    return re.findall(r'[a-zA-Z0-9_]+', text.lower())

class HybridSearcher:
    def __init__(self):
        self.qdrant = get_qdrant()
        self.embedder = EmbeddingService()
        self.collection = settings.QDRANT_COLLECTION_NAME

    async def search(self, query: str, repo_id: Optional[str] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Executes a hybrid search combining dense vector search (Voyage) and sparse keyword search (BM25)
        using Reciprocal Rank Fusion (RRF) to score and rerank candidates.
        """
        logger.info(f"🔍 Running Hybrid RRF Search for query: '{query}'")
        
        # 1. Generate dense query vector
        query_vector = await self.embedder.embed_query(query)
        
        # Build filter if repo_id is specified
        query_filter = None
        if repo_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="repo_id",
                        match=MatchValue(value=repo_id)
                    )
                ]
            )

        # 2. Retrieve candidates from Qdrant (fetch more candidates to allow meaningful rank fusion)
        candidate_limit = max(top_k * 4, 40)
        search_result = await self.qdrant.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=candidate_limit,
            with_payload=True
        )

        if not search_result:
            logger.info("⚠️ No candidates retrieved from Qdrant.")
            return []

        # Convert search results into candidate dicts
        candidates = []
        for idx, hit in enumerate(search_result):
            candidates.append({
                "chunk_id": hit.payload.get("chunk_id"),
                "file_path": hit.payload.get("file_path"),
                "name": hit.payload.get("name"),
                "language": hit.payload.get("language"),
                "dense_score": hit.score,
                "code": hit.payload.get("code") or "",
                "start_line": hit.payload.get("start_line")
            })

        # 3. Compute BM25 Sparse Scores locally for candidates
        # Tokenize code payloads of candidates
        tokenized_corpus = [tokenize_code(c["code"]) for c in candidates]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Tokenize user query
        tokenized_query = tokenize_code(query)
        bm25_scores = bm25.get_scores(tokenized_query)
        
        for idx, score in enumerate(bm25_scores):
            candidates[idx]["bm25_score"] = score

        # 4. Apply Reciprocal Rank Fusion (RRF)
        # RRF Constant (k = 60 is standard to balance influence of higher and lower ranks)
        k = 60
        rrf_scores = {}

        # Sort candidates by dense rank
        dense_sorted = sorted(candidates, key=lambda x: x["dense_score"], reverse=True)
        for rank, cand in enumerate(dense_sorted):
            c_id = cand["chunk_id"]
            rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + (1.0 / (k + (rank + 1)))

        # Sort candidates by sparse rank (BM25)
        bm25_sorted = sorted(candidates, key=lambda x: x["bm25_score"], reverse=True)
        for rank, cand in enumerate(bm25_sorted):
            c_id = cand["chunk_id"]
            rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + (1.0 / (k + (rank + 1)))

        # 5. Attach aggregate RRF scores and sort
        for cand in candidates:
            cand["score"] = rrf_scores[cand["chunk_id"]]

        # Final reranking based on RRF scores
        rrf_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)
        final_results = rrf_sorted[:top_k]

        logger.info(f"✅ Reciprocal Rank Fusion completed. Reranked top {len(final_results)} chunks out of {len(candidates)} candidates.")
        return final_results
