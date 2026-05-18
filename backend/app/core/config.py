"""
VortexRAG — Central Configuration
Reads all settings from environment variables via Pydantic BaseSettings.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── General ───────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Auth ──────────────────────────────────
    SECRET_KEY: str = "change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── CORS ──────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # ── AI Providers (Groq & Voyage) ──────────
    OPENAI_API_KEY: str = ""  # Left for backwards compatibility
    OPENAI_MODEL: str = "gpt-4o"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    VOYAGE_API_KEY: str = ""
    EMBEDDING_MODEL: str = "voyage-code-2"
    EMBEDDING_DIMENSION: int = 1536

    # ── Qdrant ────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "vortex_codebase"

    # ── Neo4j ─────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "vortexpassword"

    # ── Redis ─────────────────────────────────
    REDIS_URL: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "vortexredis"
    SEMANTIC_CACHE_TTL: int = 3600
    SEMANTIC_CACHE_THRESHOLD: float = 0.92

    # ── Langfuse ──────────────────────────────
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── GitHub ────────────────────────────────
    GITHUB_APP_ID: Optional[str] = None
    GITHUB_PRIVATE_KEY_PATH: str = "./github_app.pem"
    GITHUB_WEBHOOK_SECRET: Optional[str] = None


settings = Settings()
