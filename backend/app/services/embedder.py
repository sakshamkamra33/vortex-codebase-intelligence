"""
VortexRAG — Google Gemini Embedding Service
Uses text-embedding-004 (FREE: 100 RPM, 1,500 req/day — no payment needed).
Replaces Voyage AI which requires a payment method on free tier.
"""
import asyncio
import logging
from typing import List
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger("vortex")


_QUERY_CACHE: dict = {}

class EmbeddingService:
    """
    Generates vector embeddings using Google's text-embedding-004 model.
    Completely free — just needs a Google AI Studio API key.
    Get one at: https://aistudio.google.com/apikey
    """

    def __init__(self):
        # gemini-embedding-001 has active free quota
        self.model = "models/gemini-embedding-001"
        self.fallback_models = ["models/gemini-embedding-001"]
        self.dimension = settings.EMBEDDING_DIMENSION  # 1536 — matches Qdrant collection

        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is missing. Get a free key at https://aistudio.google.com/apikey")

        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def _embed_sync(self, texts: List[str], task_type: str) -> List[List[float]]:
        """Synchronous Gemini embed call with model fallback. Runs in a thread pool."""
        last_err = None
        for model_name in self.fallback_models:
            try:
                result = genai.embed_content(
                    model=model_name,
                    content=texts,
                    task_type=task_type,
                    output_dimensionality=self.dimension,
                )
                embeddings = result["embedding"]
                if texts and not isinstance(embeddings[0], list):
                    embeddings = [embeddings]
                self.model = model_name
                return embeddings
            except Exception as e:
                last_err = e
                logger.warning(f"Embedding failed with {model_name}: {e}. Trying fallback...")
                continue
        raise last_err

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of document chunks.
        Retries automatically on 429 Resource Exhausted errors.
        """
        if not texts:
            return []
            
        logger.info(f"🔮 Embedding {len(texts)} texts with Gemini model...")
        
        max_retries = 6
        for attempt in range(1, max_retries + 1):
            try:
                return await asyncio.to_thread(self._embed_sync, texts, "retrieval_document")
            except Exception as e:
                if "429" in str(e) and attempt < max_retries:
                    wait_time = 5 * attempt
                    logger.warning(f"⏳ Gemini rate limit (429) hit. Waiting {wait_time}s before retry {attempt}/{max_retries}...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to embed documents: {e}")
                    raise

    async def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query string with instant memory cache to avoid duplicate API calls.
        """
        if query in _QUERY_CACHE:
            return _QUERY_CACHE[query]

        max_retries = 6
        for attempt in range(1, max_retries + 1):
            try:
                results = await asyncio.to_thread(self._embed_sync, [query], "retrieval_query")
                vec = results[0]
                if len(_QUERY_CACHE) > 200:
                    _QUERY_CACHE.clear()
                _QUERY_CACHE[query] = vec
                return vec
            except Exception as e:
                if "429" in str(e) and attempt < max_retries:
                    wait_time = 5 * attempt
                    logger.warning(f"⏳ Gemini rate limit (429) hit on query. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to embed query: {e}")
                    raise
