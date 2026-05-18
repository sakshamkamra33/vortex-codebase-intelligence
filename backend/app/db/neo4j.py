"""
VortexRAG — Neo4j Graph Database Client
Manages driver lifecycle and provides session helper.
"""
import logging
from neo4j import AsyncGraphDatabase, AsyncDriver
from app.core.config import settings

logger = logging.getLogger("vortex")

_driver: AsyncDriver | None = None


async def init_neo4j() -> None:
    global _driver
    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
        max_connection_pool_size=50,
    )
    # Verify connectivity
    await _driver.verify_connectivity()
    logger.info("✅ Neo4j connected.")

    # Create schema constraints
    async with _driver.session() as session:
        await session.run(
            "CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT function_id IF NOT EXISTS FOR (fn:Function) REQUIRE fn.id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT class_id IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE"
        )
    logger.info("✅ Neo4j schema constraints ensured.")


def get_neo4j() -> AsyncDriver:
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call init_neo4j() first.")
    return _driver


async def close_neo4j() -> None:
    if _driver:
        await _driver.close()
