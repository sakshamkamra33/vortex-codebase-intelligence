"""
VortexRAG — Ragas Evaluation Endpoint (Phase 4)
"""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.services.evaluator import RagasEvaluator

router = APIRouter()


@router.post("/run")
async def run_evaluation(
    repo_id: str = "vortex_main", 
    current_user: str = Depends(get_current_user)
):
    """Run Ragas evaluation suite against the current index."""
    evaluator = RagasEvaluator()
    results = await evaluator.run_evaluation(repo_id)
    return results
