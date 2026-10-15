"""
VortexRAG — Query Endpoint (Phase 3)
Handles natural language queries. Implements the Semantic Cache and retrieves chunks via Hybrid Search.
"""
import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.core.security import get_current_user
from app.services.semantic_cache import SemanticCache
from app.services.hybrid_search import HybridSearcher

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    repo_id: Optional[str] = None
    top_k: int = 10
    use_cache: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    cache_hit: bool
    latency_ms: float


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    body: QueryRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Ask a natural language question about the codebase.
    """
    start_time = time.time()
    
    # 1. Check Semantic Cache
    if body.use_cache:
        cache = SemanticCache()
        cached = await cache.get_cached_response(body.question, body.repo_id)
        if cached:
            latency = (time.time() - start_time) * 1000
            return QueryResponse(
                answer=cached["answer"],
                sources=cached["sources"],
                cache_hit=True,
                latency_ms=round(latency, 2)
            )

    # 2. LangGraph Agent (Retrieval + Generation + Self-Correction)
    from app.services.rag_agent import RAGAgent
    agent = RAGAgent()
    
    agent_result = await agent.run(body.question, body.repo_id)
    
    answer = agent_result["answer"]
    sources = [{"file_path": c["file_path"], "name": c["name"], "score": c.get("score", 1.0)} for c in agent_result["sources"]]

    # 4. Save to Cache
    if body.use_cache and sources:
        cache = SemanticCache()
        await cache.set_cache(body.question, answer, sources, body.repo_id)

    latency = (time.time() - start_time) * 1000
    return QueryResponse(
        answer=answer,
        sources=sources,
        cache_hit=False,
        latency_ms=round(latency, 2)
    )


@router.get("/repositories")
async def get_repositories(
    current_user: str = Depends(get_current_user),
):
    """
    Returns a list of all distinct repository IDs indexed in Qdrant.
    """
    try:
        from app.db.qdrant import get_qdrant
        from app.core.config import settings
        qdrant = get_qdrant()
        points, _ = await qdrant.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=500,
            with_payload=True
        )
        repos = set()
        for p in points:
            if p.payload and p.payload.get("repo_id"):
                repos.add(p.payload.get("repo_id"))
        return {"repositories": sorted(list(repos))}
    except Exception as e:
        return {"repositories": ["vortex-codebase-intelligence_main", "nexus-ftp-engine_main"]}


from fastapi.responses import StreamingResponse
import asyncio
import json

@router.post("/ask/stream")
async def ask_question_stream(
    body: QueryRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Ask a natural language question and receive an instant stream of status updates, tokens, and sources.
    Connects immediately to the browser with zero blocking delay.
    """
    async def event_generator():
        # 1. Immediately acknowledge connection
        yield f"data: {json.dumps({'type': 'status', 'content': '⚡ Connecting to Vortex Swarm...'})}\n\n"
        
        # 2. Check Semantic Cache
        if body.use_cache:
            try:
                cache = SemanticCache()
                cached = await cache.get_cached_response(body.question, body.repo_id)
                if cached:
                    yield f"data: {json.dumps({'type': 'status', 'content': '⚡ Cache Hit! Instant Redis retrieval...'})}\n\n"
                    await asyncio.sleep(0.05)
                    yield f"data: {json.dumps({'type': 'token', 'content': cached['answer']})}\n\n"
                    yield f"data: {json.dumps({'type': 'sources', 'content': cached['sources']})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
                    return
            except Exception as cache_err:
                pass

        # 3. Stream from LangGraph Agent
        from app.services.rag_agent import RAGAgent
        agent = RAGAgent()
        
        collected_tokens = []
        final_sources = []
        
        async for event_str in agent.run_stream(body.question, body.repo_id):
            yield event_str
            
            # Parse events to collect for the cache
            if event_str.startswith("data:"):
                try:
                    data = json.loads(event_str[5:].strip())
                    if data["type"] == "token":
                        collected_tokens.append(data["content"])
                    elif data["type"] == "sources":
                        final_sources = data["content"]
                except Exception:
                    pass
                    
        # Save to cache after complete generation
        if body.use_cache and final_sources and collected_tokens:
            try:
                full_answer = "".join(collected_tokens)
                cache = SemanticCache()
                await cache.set_cache(body.question, full_answer, final_sources, body.repo_id)
            except Exception:
                pass
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

