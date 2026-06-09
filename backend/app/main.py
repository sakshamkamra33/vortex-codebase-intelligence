"""
VortexRAG — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.qdrant import init_qdrant
from app.db.neo4j import init_neo4j
from app.db.redis import init_redis
from app.api.v1.router import api_router

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🌀 VortexRAG starting up...")

    # Initialize all database connections (graceful — app starts even if a service is down)
    try:
        await init_qdrant()
    except Exception as e:
        logger.warning(f"⚠️  Qdrant unavailable — skipping: {e}")

    try:
        await init_neo4j()
    except Exception as e:
        logger.warning(f"⚠️  Neo4j unavailable — skipping: {e}")

    try:
        await init_redis()
    except Exception as e:
        logger.warning(f"⚠️  Redis unavailable — skipping: {e}")

    logger.info("✅ VortexRAG started (some services may be degraded — check warnings above).")
    yield

    logger.info("🛑 VortexRAG shutting down...")


app = FastAPI(
    title="VortexRAG",
    description="Enterprise Codebase Intelligence & PR Review Agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "VortexRAG",
            "version": "1.0.0",
        }
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "🌀 VortexRAG — Enterprise Codebase Intelligence Platform",
        "docs": "/docs",
        "health": "/health", # Reloading backend to pick up .env
    }
