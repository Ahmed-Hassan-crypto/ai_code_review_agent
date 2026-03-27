"""FastAPI backend for the AI Code Review Agent."""

import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from agent.graph import review_graph
from github_integration.webhook import verify_webhook_signature, parse_webhook_payload
from config import config

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── In-memory store for review results ───────────────────────────────────────
review_store: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown hooks."""
    print("🚀 AI Code Review Agent server is running!")
    yield
    print("👋 Shutting down.")


app = FastAPI(
    title="AI Code Review Agent API",
    description="Automated code review powered by LangGraph and Google Gemini. "
    "Submit GitHub PR URLs to receive comprehensive code reviews including "
    "lint issues, security vulnerabilities, and suggested fixes.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Review", "description": "Code review endpoints"},
        {"name": "Webhook", "description": "GitHub webhook endpoints"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ───────────────────────────────────────────────────────────
class ReviewRequest(BaseModel):
    pr_url: str


# ── Helper: run the review graph ─────────────────────────────────────────────
async def run_review(pr_url: str) -> dict:
    """Run the LangGraph review pipeline in a background thread."""
    initial_state = {
        "pr_url": pr_url,
        "repo_owner": "",
        "repo_name": "",
        "pr_number": 0,
        "pr_title": "",
        "pr_body": "",
        "diff_text": "",
        "files": [],
        "lint_results": [],
        "logic_results": [],
        "fix_suggestions": [],
        "scores": [],
        "final_review": "",
        "overall_score": 0.0,
    }

    result = await asyncio.to_thread(review_graph.invoke, initial_state)
    
    # Store result
    key = f"{result.get('repo_owner', '')}/{result.get('repo_name', '')}#{result.get('pr_number', 0)}"
    review_store[key] = {
        "pr_url": pr_url,
        "pr_title": result.get("pr_title", ""),
        "overall_score": result.get("overall_score", 0),
        "scores": result.get("scores", []),
        "lint_results": result.get("lint_results", []),
        "logic_results": result.get("logic_results", []),
        "fix_suggestions": result.get("fix_suggestions", []),
        "final_review": result.get("final_review", ""),
    }

    return review_store[key]


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "AI Code Review Agent"}


@app.post("/review")
async def trigger_review(request: ReviewRequest):
    """Manually trigger a code review for a GitHub PR.
    
    Body: { "pr_url": "https://github.com/owner/repo/pull/123" }
    """
    try:
        result = await run_review(request.pr_url)
        return {
            "status": "completed",
            "pr_url": request.pr_url,
            "overall_score": result["overall_score"],
            "scores": result["scores"],
            "lint_results": result["lint_results"],
            "logic_results": result["logic_results"],
            "fix_suggestions": result["fix_suggestions"],
            "final_review": result["final_review"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


@app.post("/webhook")
async def github_webhook(request: Request):
    """Receive GitHub webhook events and auto-trigger reviews on PR events."""
    # Verify signature
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if secret:
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_webhook_signature(body, signature, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    
    # Parse the webhook event
    parsed = parse_webhook_payload(payload)
    if parsed is None:
        return {"status": "ignored", "reason": "Not an actionable PR event"}

    # Run review asynchronously (don't block the webhook response)
    asyncio.create_task(run_review(parsed["pr_url"]))

    return {
        "status": "accepted",
        "pr_url": parsed["pr_url"],
        "action": parsed["action"],
        "message": f"Review triggered for PR #{parsed['pr_number']}",
    }


@app.get("/reviews/{owner}/{repo}/{pr_number}")
async def get_review(owner: str, repo: str, pr_number: int):
    """Fetch a cached review result."""
    key = f"{owner}/{repo}#{pr_number}"
    if key not in review_store:
        raise HTTPException(status_code=404, detail="Review not found. Trigger a review first.")
    return review_store[key]
