"""
VortexRAG — Graph Endpoint (Phase 3)
Retrieves Neo4j call graph and dependencies.
"""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.db.neo4j import get_neo4j

router = APIRouter()

@router.get("/dependencies")
async def get_dependencies(
    repo_id: str,
    current_user: str = Depends(get_current_user),
):
    """
    Traverse Neo4j call graph and return dependency chain.
    """
    driver = get_neo4j()
    
    query = """
    MATCH (f:File {repo_id: $repo_id})-[:CONTAINS]->(c)
    RETURN labels(c)[0] as type, c.name as name, f.path as file_path
    LIMIT 100
    """
    
    async with driver.session() as session:
        result = await session.run(query, repo_id=repo_id)
        records = await result.data()
        
    return {
        "repo_id": repo_id,
        "nodes": records
    }
