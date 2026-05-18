"""
VortexRAG — Voyage AI Embedding Service
Wraps the voyage-code-2 model for generating code-optimized embeddings.
"""
import logging
from typing import List
import voyageai

from app.core.config import settings

logger = logging.getLogger("vortex")

class EmbeddingService:
    """
    Handles generating vector embeddings for code chunks and queries
    using Voyage AI's code-optimized models.
    """

    def __init__(self):
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        
        # We use the sync client wrapped in async, or native async if available
        # Voyage AI provides an AsyncClient
        if not settings.VOYAGE_API_KEY:
             logger.warning("VOYAGE_API_KEY is missing. Embeddings will fail.")
        
        self.client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts.
        
        Args:
            texts: List of strings to embed (code chunks)
            
        Returns:
            List of embeddings (vectors of floats)
        """
        if not texts:
            return []
            
        try:
            # voyage-code-2 supports input types: "document" or "query"
            response = await self.client.embed(
                texts, 
                model=self.model, 
                input_type="document"
            )
            return response.embeddings
        except Exception as e:
            logger.error(f"Failed to embed documents: {e}")
            raise

    async def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query string.
        
        Args:
            query: The user's natural language question
            
        Returns:
            Embedding vector
        """
        try:
            response = await self.client.embed(
                [query], 
                model=self.model, 
                input_type="query"
            )
            return response.embeddings[0]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise
