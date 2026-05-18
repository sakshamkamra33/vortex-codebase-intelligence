"""
VortexRAG — Neo4j Graph Builder (Phase 2)
Handles pushing extracted CodeChunks into Neo4j to build the call-graph dependency network.
"""
import logging
from typing import List

from app.db.neo4j import get_neo4j
from app.services.ast_chunker import CodeChunk

logger = logging.getLogger("vortex")

class GraphBuilder:
    """
    Constructs the knowledge graph in Neo4j from AST chunks.
    Nodes: File, Class, Function
    Edges: CONTAINS (File->Class, File->Function, Class->Function), CALLS (Function->Function)
    """

    def __init__(self):
        self.driver = get_neo4j()

    async def build_graph(self, chunks: List[CodeChunk]) -> None:
        """
        Takes a list of code chunks and builds the Neo4j graph representation.
        We use a single transaction per batch for efficiency.
        """
        if not chunks:
            return
            
        logger.info(f"🕸️ Building Neo4j graph from {len(chunks)} chunks...")
        
        async with self.driver.session() as session:
            # 1. First pass: Create all nodes and basic containment edges
            await session.execute_write(self._create_nodes, chunks)
            
            # 2. Second pass: Create CALLS edges (this is a simplified placeholder, 
            # in a real FAANG system this would use advanced static analysis to link definitions)
            # For this MVP, we'll establish structure.
            logger.info("✅ Neo4j graph structure created successfully.")

    @staticmethod
    async def _create_nodes(tx, chunks: List[CodeChunk]):
        """
        Cypher query to merge Files, Classes, and Functions.
        MERGE ensures idempotent inserts.
        """
        query = """
        UNWIND $chunks AS chunk
        
        // 1. Ensure File node exists
        MERGE (f:File {path: chunk.file_path, repo_id: chunk.repo_id})
        
        // 2. Create the Function/Class node based on chunk type
        WITH chunk, f
        CALL {
            WITH chunk, f
            WITH chunk, f WHERE chunk.node_type CONTAINS 'function' OR chunk.node_type CONTAINS 'method'
            MERGE (fn:Function {id: chunk.id})
            SET fn.name = chunk.name,
                fn.language = chunk.language,
                fn.start_line = chunk.start_line,
                fn.end_line = chunk.end_line
            
            // Link Function to File
            MERGE (f)-[:CONTAINS]->(fn)
            
            // If it belongs to a class, link it to the class
            WITH chunk, f, fn
            WHERE chunk.parent_class IS NOT NULL
            MERGE (c:Class {id: chunk.repo_id + ':' + chunk.file_path + ':' + chunk.parent_class})
            SET c.name = chunk.parent_class,
                c.repo_id = chunk.repo_id
            MERGE (f)-[:CONTAINS]->(c)
            MERGE (c)-[:CONTAINS]->(fn)
            RETURN fn AS created_node
            
            UNION
            
            WITH chunk, f
            WITH chunk, f WHERE chunk.node_type CONTAINS 'class'
            MERGE (c:Class {id: chunk.id})
            SET c.name = chunk.name,
                c.language = chunk.language,
                c.start_line = chunk.start_line,
                c.end_line = chunk.end_line,
                c.repo_id = chunk.repo_id
            
            // Link Class to File
            MERGE (f)-[:CONTAINS]->(c)
            RETURN c AS created_node
        }
        RETURN count(created_node)
        """
        
        # Format data for Neo4j
        chunk_dicts = []
        for c in chunks:
            chunk_dicts.append({
                "id": c.id,
                "repo_id": c.repo_id,
                "file_path": c.file_path,
                "language": c.language,
                "node_type": c.node_type,
                "name": c.name,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "parent_class": c.parent_class
            })
            
        await tx.run(query, chunks=chunk_dicts)
