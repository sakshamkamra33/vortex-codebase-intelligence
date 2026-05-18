"""VortexRAG — GitHub App webhook endpoint (Phase 5)."""
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
import hmac
import hashlib
import logging

from app.core.config import settings
from app.services.pr_reviewer import PRReviewer

logger = logging.getLogger("vortex")
router = APIRouter()

async def process_webhook_background(payload: dict, event: str):
    """Background task to run the PR Reviewer without blocking GitHub's webhook delivery."""
    if event == "pull_request" and payload.get("action") in ["opened", "synchronize"]:
        repo_full_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        repo_id = f"{payload['repository']['name']}_{payload['pull_request']['base']['ref']}"
        
        reviewer = PRReviewer()
        try:
            await reviewer.review_pr(repo_full_name, pr_number, repo_id)
        except Exception as e:
            logger.error(f"Failed to process PR webhook: {e}")


@router.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives GitHub App webhook events.
    Verifies payload signature and triggers the PR Review Agent on new/updated PRs.
    """
    payload_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event = request.headers.get("X-GitHub-Event", "unknown")
    
    # 1. Verify Signature (if secret is configured)
    if settings.GITHUB_WEBHOOK_SECRET and signature:
        mac = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode(),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = f"sha256={mac.hexdigest()}"
        if not hmac.compare_digest(expected_signature, signature):
            logger.warning("Invalid GitHub webhook signature.")
            raise HTTPException(status_code=403, detail="Invalid signature")

    # 2. Parse payload and trigger background task
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    logger.info(f"📥 Received GitHub webhook event: {event}")
    
    background_tasks.add_task(process_webhook_background, payload, event)
    
    return {"status": "accepted", "event": event}


from pydantic import BaseModel

class PRReviewRequest(BaseModel):
    repo_owner: str
    repo_name: str
    pr_number: int
    repo_id: str

@router.post("/review")
async def manual_pr_review(body: PRReviewRequest):
    """
    Manually triggers an architectural review of a specific GitHub Pull Request
    and returns the review comments directly to the frontend.
    """
    reviewer = PRReviewer()
    repo_full_name = f"{body.repo_owner}/{body.repo_name}"
    try:
        result = await reviewer.review_pr(repo_full_name, body.pr_number, body.repo_id)
        return result
    except Exception as e:
        logger.error(f"Manual PR review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

