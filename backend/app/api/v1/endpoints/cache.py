"""
VortexRAG — Semantic Cache Endpoints (Phase 3)
"""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.services.semantic_cache import SemanticCache

router = APIRouter()

@router.get("/stats")
async def cache_stats(current_user: str = Depends(get_current_user)):
    """Returns Redis semantic cache hit/miss statistics."""
    cache = SemanticCache()
    return await cache.get_stats()

@router.delete("/flush")
async def flush_cache(current_user: str = Depends(get_current_user)):
    """Flush all semantic cache entries."""
    cache = SemanticCache()
    await cache.flush()
    return {"status": "success", "message": "Semantic cache flushed."}
