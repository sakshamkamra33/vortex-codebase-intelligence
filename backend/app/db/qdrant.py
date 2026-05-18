"""
VortexRAG — Qdrant Vector Database Client
Manages collection creation and provides the client singleton.
"""
import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    HnswConfigDiff,
    OptimizersConfigDiff,
)
from app.core.config import settings

logger = logging.getLogger("vortex")

_client: AsyncQdrantClient | None = None


async def init_qdrant() -> None:
    global _client
    if settings.QDRANT_URL:
        logger.info(f"🔮 Connecting to Qdrant Cloud: {settings.QDRANT_URL}")
        _client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        )
    else:
        logger.info(f"🔮 Connecting to local Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        _client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )

    collections = await _client.get_collections()
    existing = [c.name for c in collections.collections]

    if settings.QDRANT_COLLECTION_NAME not in existing:
        await _client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=200,
                full_scan_threshold=10_000,
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=20_000,
            ),
        )
        logger.info(f"✅ Qdrant collection '{settings.QDRANT_COLLECTION_NAME}' created.")
    else:
        logger.info(f"✅ Qdrant collection '{settings.QDRANT_COLLECTION_NAME}' already exists.")


def get_qdrant() -> AsyncQdrantClient:
    if _client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")
    return _client
