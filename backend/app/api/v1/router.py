"""
VortexRAG — API v1 Router
Aggregates all route modules.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, ingest, query, graph, cache, eval, github

api_router = APIRouter()

api_router.include_router(auth.router,   prefix="/auth",   tags=["Auth"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
api_router.include_router(query.router,  prefix="/query",  tags=["Query"])
api_router.include_router(graph.router,  prefix="/graph",  tags=["GraphRAG"])
api_router.include_router(cache.router,  prefix="/cache",  tags=["Cache"])
api_router.include_router(eval.router,   prefix="/eval",   tags=["Evaluation"])
api_router.include_router(github.router, prefix="/github", tags=["GitHub"])
