"""
VortexRAG — Ingestion Endpoint (Phase 2)
Handles GitHub repository ingestion via AST chunking, embeddings, and graph building.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import logging
import uuid

from app.core.security import get_current_user
from app.services.ingestion import IngestionPipeline

logger = logging.getLogger("vortex")
router = APIRouter()

# In-memory job tracker (will be replaced by Redis/DB in prod)
_jobs: dict[str, dict] = {}


class IngestRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    languages: list[str] = ["python", "javascript", "typescript", "java", "go"]


class IngestResponse(BaseModel):
    job_id: str
    status: str
    message: str


async def run_ingestion_background(job_id: str, request: IngestRequest):
    """Background task to run the heavy ingestion pipeline."""
    _jobs[job_id]["status"] = "running"
    
    pipeline = IngestionPipeline()
    try:
        result = await pipeline.ingest_repository(
            repo_url=request.repo_url,
            branch=request.branch,
            languages=request.languages
        )
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["result"] = result
    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {e}")
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)


@router.post("/repo", response_model=IngestResponse)
async def ingest_repository(
    body: IngestRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """
    Trigger ingestion of a GitHub repository.
    Executes AST parsing, embedding to Qdrant, and graph building in Neo4j.
    Runs asynchronously in the background.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "repo_url": body.repo_url,
        "status": "queued",
        "result": None,
        "error": None
    }
    
    # Add to background tasks
    background_tasks.add_task(run_ingestion_background, job_id, body)
    
    return IngestResponse(
        job_id=job_id,
        status="queued",
        message=f"Ingestion started for {body.repo_url}. Check status via /status/{job_id}",
    )


class SyncRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    modified_files: list[str] = []
    deleted_files: list[str] = []


class SyncResponse(BaseModel):
    job_id: str
    status: str
    message: str


async def run_sync_background(job_id: str, request: SyncRequest):
    """Background task to run the incremental delta sync pipeline."""
    _jobs[job_id]["status"] = "running"
    
    pipeline = IngestionPipeline()
    try:
        result = await pipeline.sync_delta_repository(
            repo_url=request.repo_url,
            branch=request.branch,
            modified_files=request.modified_files,
            deleted_files=request.deleted_files
        )
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["result"] = result
    except Exception as e:
        logger.error(f"Sync job {job_id} failed: {e}")
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)


@router.post("/sync", response_model=SyncResponse)
async def sync_delta_repository(
    body: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """
    Trigger smart incremental delta sync.
    Deletes, chunks, vectorizes, and builds call-graphs ONLY for changed files.
    Runs asynchronously in the background.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "repo_url": body.repo_url,
        "status": "queued",
        "result": None,
        "error": None
    }
    
    # Add to background tasks
    background_tasks.add_task(run_sync_background, job_id, body)
    
    return SyncResponse(
        job_id=job_id,
        status="queued",
        message=f"Incremental sync started for {body.repo_url}. Check status via /status/{job_id}",
    )


@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    current_user: str = Depends(get_current_user),
):
    """Check the status of a background ingestion job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return _jobs[job_id]
