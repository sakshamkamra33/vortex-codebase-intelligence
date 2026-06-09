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


class EmbeddingService:
    """
    Generates vector embeddings using Google's text-embedding-004 model.
    Completely free — just needs a Google AI Studio API key.
    Get one at: https://aistudio.google.com/apikey
    """

    def __init__(self):
        self.model = "models/gemini-embedding-2"
        self.dimension = settings.EMBEDDING_DIMENSION  # 1536 — matches Qdrant collection

        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is missing. Get a free key at https://aistudio.google.com/apikey")

        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def _embed_sync(self, texts: List[str], task_type: str) -> List[List[float]]:
        """Synchronous Gemini embed call. Runs in a thread pool via asyncio.to_thread."""
        result = genai.embed_content(
            model=self.model,
            content=texts,
            task_type=task_type,
            output_dimensionality=self.dimension,
        )
        embeddings = result["embedding"]
        # embed_content returns a flat list when content is a single string,
        # and a list of lists when content is a list — normalise to always return list of lists.
        if texts and not isinstance(embeddings[0], list):
            embeddings = [embeddings]
        return embeddings

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of document chunks.
        Retries automatically on 429 Resource Exhausted errors.
        """
        if not texts:
            return []
            
        logger.info(f"🔮 Embedding {len(texts)} texts with Gemini model...")
        
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                return await asyncio.to_thread(self._embed_sync, texts, "retrieval_document")
            except Exception as e:
                if "429" in str(e) and attempt < max_retries:
                    wait_time = 30 * attempt  # 30s, 60s, 90s...
                    logger.warning(f"⏳ Gemini rate limit (429) hit. Waiting {wait_time}s before retry {attempt}/{max_retries}...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to embed documents: {e}")
                    raise

    async def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query string.
        Retries automatically on 429 Resource Exhausted errors.
        """
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                results = await asyncio.to_thread(self._embed_sync, [query], "retrieval_query")
                return results[0]
            except Exception as e:
                if "429" in str(e) and attempt < max_retries:
                    wait_time = 30 * attempt
                    logger.warning(f"⏳ Gemini rate limit (429) hit on query. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to embed query: {e}")
                    raise
