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
    MATCH (n)-[r]->(m)
    WHERE (n.repo_id = $repo_id) OR (m.repo_id = $repo_id)
    RETURN 
        id(n) as source_id, labels(n)[0] as source_label, n.name as source_name,
        type(r) as rel_type,
        id(m) as target_id, labels(m)[0] as target_label, m.name as target_name
    LIMIT 300
    """
    
    nodes_dict = {}
    links = []
    
    async with driver.session() as session:
        result = await session.run(query, repo_id=repo_id)
        records = await result.data()
        
        for record in records:
            src_id = str(record["source_id"])
            tgt_id = str(record["target_id"])
            
            if src_id not in nodes_dict:
                nodes_dict[src_id] = {"id": src_id, "label": record["source_label"], "name": record["source_name"]}
            if tgt_id not in nodes_dict:
                nodes_dict[tgt_id] = {"id": tgt_id, "label": record["target_label"], "name": record["target_name"]}
                
            links.append({
                "source": src_id,
                "target": tgt_id,
                "type": record["rel_type"]
            })
            
    return {
        "repo_id": repo_id,
        "nodes": list(nodes_dict.values()),
        "links": links
    }
