"""
VortexRAG — Ingestion Pipeline Orchestrator (Phase 2)
Coordinates cloning, AST parsing, embedding, vector DB storage, and graph DB storage.
"""
import logging
import os
import shutil
import tempfile
from pathlib import Path
import git
from typing import List, Optional
from qdrant_client.models import PointStruct

from app.core.config import settings
from app.db.qdrant import get_qdrant
from app.services.ast_chunker import ASTChunker, CodeChunk
from app.services.embedder import EmbeddingService
from app.services.graph_builder import GraphBuilder

logger = logging.getLogger("vortex")


class IngestionPipeline:
    def __init__(self):
        self.chunker = ASTChunker()
        self.embedder = EmbeddingService()
        self.graph_builder = GraphBuilder()
        self.qdrant = get_qdrant()

    async def ingest_repository(
        self, 
        repo_url: str, 
        branch: str = "main",
        languages: Optional[List[str]] = None
    ) -> dict:
        """
        Full ingestion pipeline: Clone -> Chunk -> Embed -> Qdrant -> Neo4j.
        """
        logger.info(f"🚀 Starting ingestion pipeline for {repo_url}")
        
        repo_name = repo_url.rstrip("/").split("/")[-1]
        repo_id = f"{repo_name}_{branch}"
        
        # 1. Clone Repo
        temp_dir = tempfile.mkdtemp(prefix=f"vortex_{repo_name}_")
        try:
            logger.info(f"Cloning {repo_url} branch {branch} to {temp_dir}...")
            # Shallow clone for speed
            git.Repo.clone_from(repo_url, temp_dir, branch=branch, depth=1)
            
            # 2. Extract AST Chunks
            chunks = self.chunker.chunk_repository(
                repo_root=Path(temp_dir),
                repo_id=repo_id,
                languages=languages
            )
            
            if not chunks:
                return {"status": "success", "message": "No supported files found to chunk.", "chunks_processed": 0}
            
            # 3. Embed & Store in Vector DB (Qdrant)
            await self._store_in_vector_db(chunks)
            
            # 4. Build Knowledge Graph (Neo4j)
            await self.graph_builder.build_graph(chunks)
            
            logger.info(f"✅ Ingestion complete for {repo_url}")
            return {
                "status": "success", 
                "message": f"Ingested {len(chunks)} chunks.", 
                "chunks_processed": len(chunks),
                "repo_id": repo_id
            }

        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            raise
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _store_in_vector_db(self, chunks: List[CodeChunk]):
        """Embeds chunks and stores them in Qdrant in batches."""
        logger.info(f"🔮 Embedding {len(chunks)} chunks and storing in Qdrant...")
        
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts_to_embed = [c.to_embed_text() for c in batch]
            
            # Embed
            embeddings = await self.embedder.embed(texts_to_embed)
            
            # Create Qdrant points
            points = []
            for j, chunk in enumerate(batch):
                # Generate a UUID or int hash from chunk.id (which is sha256 hex)
                # Qdrant supports UUID strings
                import uuid
                point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, chunk.id))
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embeddings[j],
                        payload={
                            "chunk_id": chunk.id,
                            "repo_id": chunk.repo_id,
                            "file_path": chunk.file_path,
                            "language": chunk.language,
                            "node_type": chunk.node_type,
                            "name": chunk.name,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "code": chunk.code, # Store raw code for retrieval
                        }
                    )
                )
                
            # Upsert
            await self.qdrant.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points
            )
            logger.info(f"Upserted batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")

    async def sync_delta_repository(
        self,
        repo_url: str,
        branch: str = "main",
        modified_files: Optional[List[str]] = None,
        deleted_files: Optional[List[str]] = None,
        languages: Optional[List[str]] = None
    ) -> dict:
        """
        Incremental Delta Syncing:
        - Deletes removed/changed files from Qdrant and Neo4j.
        - Clones repository and chunks only the modified/new files.
        - Vectorizes and upserts only those changed chunks to Qdrant & Neo4j.
        """
        logger.info(f"🔄 Starting incremental delta sync for {repo_url}")
        
        repo_name = repo_url.rstrip("/").split("/")[-1]
        repo_id = f"{repo_name}_{branch}"
        
        modified_files = modified_files or []
        deleted_files = deleted_files or []
        
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        from app.db.neo4j import get_neo4j
        
        # 1. Process Deletions
        files_to_delete = list(set(deleted_files + modified_files))
        
        for file_path in files_to_delete:
            logger.info(f"🧹 Removing existing indices for file: {file_path}")
            
            # Delete from Qdrant
            await self.qdrant.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="repo_id", match=MatchValue(value=repo_id)),
                        FieldCondition(key="file_path", match=MatchValue(value=file_path))
                    ]
                )
            )
            
            # Delete from Neo4j
            try:
                driver = get_neo4j()
                query = """
                MATCH (f:File {repo_id: $repo_id, path: $file_path})
                OPTIONAL MATCH (f)-[:CONTAINS]->(child)
                DETACH DELETE f, child
                """
                async with driver.session() as session:
                    await session.run(query, repo_id=repo_id, file_path=file_path)
            except Exception as graph_err:
                logger.error(f"⚠️ Failed to remove Neo4j nodes for file {file_path}: {graph_err}")

        if not modified_files:
            return {
                "status": "success",
                "message": f"Successfully deleted {len(deleted_files)} files. No modified files to sync.",
                "deleted": deleted_files,
                "upserted_chunks": 0
            }

        # 2. Process Additions & Modifications
        temp_dir = tempfile.mkdtemp(prefix=f"vortex_sync_{repo_name}_")
        try:
            logger.info(f"Cloning {repo_url} to extract modified files...")
            # Shallow clone
            git.Repo.clone_from(repo_url, temp_dir, branch=branch, depth=1)
            
            new_chunks = []
            for file_rel_path in modified_files:
                file_abs_path = Path(temp_dir) / file_rel_path
                if not file_abs_path.exists():
                    logger.warning(f"⚠️ Modified file not found in clone: {file_rel_path}")
                    continue
                
                # Chunk only this file!
                chunks = self.chunker.chunk_file(
                    file_path=file_abs_path,
                    repo_id=repo_id,
                    repo_root=Path(temp_dir)
                )
                new_chunks.extend(chunks)

            if new_chunks:
                # 3. Store in Vector DB (Qdrant)
                await self._store_in_vector_db(new_chunks)
                
                # 4. Build Call-Graph dependencies in Neo4j
                await self.graph_builder.build_graph(new_chunks)
                
                logger.info(f"✅ Incremental sync complete. Synced {len(new_chunks)} chunks across {len(modified_files)} files.")
            
            return {
                "status": "success",
                "message": f"Delta Sync complete. Deleted {len(deleted_files)} files. Upserted {len(new_chunks)} chunks.",
                "deleted": deleted_files,
                "upserted_chunks": len(new_chunks)
            }

        except Exception as e:
            logger.error(f"❌ Delta Sync failed: {e}")
            raise
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
