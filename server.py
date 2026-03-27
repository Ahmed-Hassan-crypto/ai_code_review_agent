"""FastAPI backend for the AI Code Review Agent."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.graph import review_graph
from config import config
from github_integration.webhook import parse_webhook_payload, verify_webhook_signature

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
    title="AI Code Review Agent",
    description="Automated code review powered by LangGraph and Groq. "
    "Submit GitHub PR URLs to receive comprehensive code reviews including "
    "lint issues, security vulnerabilities, and suggested fixes.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api-docs",
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
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root page - show the Streamlit UI interface."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Code Review Agent</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 40px;
                max-width: 600px;
                width: 100%;
            }
            .logo {
                font-size: 48px;
                text-align: center;
                margin-bottom: 20px;
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 10px;
                font-size: 28px;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                color: #333;
                margin-bottom: 8px;
                font-weight: 500;
            }
            input[type="text"] {
                width: 100%;
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input[type="text"]:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
            }
            .result {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                display: none;
            }
            .result.show {
                display: block;
            }
            .score {
                font-size: 48px;
                font-weight: bold;
                text-align: center;
                margin: 20px 0;
            }
            .score.high { color: #28a745; }
            .score.medium { color: #ffc107; }
            .score.low { color: #dc3545; }
            .badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                margin: 5px;
            }
            .badge.pass { background: #d4edda; color: #155724; }
            .badge.warn { background: #fff3cd; color: #856404; }
            .badge.fail { background: #f8d7da; color: #721c24; }
            .footer {
                text-align: center;
                margin-top: 30px;
                color: #999;
                font-size: 14px;
            }
            .loading {
                text-align: center;
                padding: 20px;
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🔍</div>
            <h1>AI Code Review Agent</h1>
            <p class="subtitle">Automated code reviews powered by LangGraph + Groq</p>
            
            <div class="form-group">
                <label for="prUrl">GitHub Pull Request URL</label>
                <input type="text" id="prUrl" placeholder="https://github.com/owner/repo/pull/123">
            </div>
            
            <button onclick="submitReview()">Review PR</button>
            
            <div id="loading" class="loading" style="display: none;">
                <div class="spinner"></div>
                <p style="margin-top: 15px;">Analyzing code...</p>
            </div>
            
            <div id="result" class="result">
                <h2 style="text-align: center; margin-bottom: 10px;">Review Complete!</h2>
                <div id="scoreDisplay" class="score">0/10</div>
                <div id="statusBadge" class="badge">-</div>
                
                <div id="filesList" style="margin-top: 20px;"></div>
                
                <div id="githubMessage" style="margin-top: 20px; padding: 15px; background: #d4edda; border-radius: 10px; display: none;">
                    <p style="color: #155724; font-weight: 600;">✅ Review report added to GitHub PR comment!</p>
                </div>
                
                <div id="downloadSection" style="margin-top: 20px; text-align: center; display: none;">
                    <button id="downloadPdfBtn" onclick="downloadPDF()" style="background: #28a745; margin-top: 10px;">📥 Download PDF Report</button>
                </div>
            </div>
            
            <div class="footer">
                Powered by LangGraph • Groq LLM • FastAPI
            </div>
        </div>
        
        <script>
            async function submitReview() {
                const prUrl = document.getElementById('prUrl').value;
                if (!prUrl) {
                    alert('Please enter a GitHub PR URL');
                    return;
                }
                
                document.getElementById('loading').style.display = 'block';
                document.getElementById('result').classList.remove('show');
                
                try {
                    const apiUrl = window.location.origin;
                    const response = await fetch(apiUrl + '/review', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ pr_url: prUrl })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showResult(data);
                        
                        // Show GitHub message
                        document.getElementById('githubMessage').style.display = 'block';
                        
                        // Show download button
                        document.getElementById('downloadSection').style.display = 'block';
                        
                        // Store data for PDF download
                        window.reviewData = data;
                    } else {
                        alert('Error: ' + (data.detail || 'Failed to review'));
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
                
                document.getElementById('loading').style.display = 'none';
            }
            
            function showResult(data) {
                const resultDiv = document.getElementById('result');
                const score = data.overall_score || 0;
                
                document.getElementById('scoreDisplay').textContent = score + '/10';
                document.getElementById('scoreDisplay').className = 'score ' + (score >= 7 ? 'high' : score >= 5 ? 'medium' : 'low');
                
                const statusBadge = document.getElementById('statusBadge');
                if (score >= 7) {
                    statusBadge.textContent = '✅ PASSED';
                    statusBadge.className = 'badge pass';
                } else if (score >= 5) {
                    statusBadge.textContent = '⚠️ NEEDS WORK';
                    statusBadge.className = 'badge warn';
                } else {
                    statusBadge.textContent = '❌ FAILED';
                    statusBadge.className = 'badge fail';
                }
                
                // Show files
                const filesList = document.getElementById('filesList');
                const scores = data.scores || [];
                
                if (scores.length > 0) {
                    let html = '<h3>Files Reviewed:</h3>';
                    scores.forEach(s => {
                        const icon = s.score >= 7 ? '✅' : s.score >= 5 ? '⚠️' : '❌';
                        html += '<div style="padding: 10px; margin: 5px 0; background: white; border-radius: 8px;">' + icon + ' <strong>' + s.filename + '</strong> - ' + s.score + '/10</div>';
                    });
                    filesList.innerHTML = html;
                }
                
                resultDiv.classList.add('show');
            }
            
            async function downloadPDF() {
                const data = window.reviewData;
                if (!data) {
                    alert('No review data available');
                    return;
                }
                
                try {
                    const apiUrl = window.location.origin;
                    const response = await fetch(apiUrl + '/pdf', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'code_review_' + (data.pr_title || 'report').replace(/[^a-z0-9]/gi, '_').substring(0, 30) + '.pdf';
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    } else {
                        alert('Failed to generate PDF');
                    }
                } catch (error) {
                    alert('Error downloading PDF: ' + error.message);
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


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


@app.post("/pdf")
async def generate_pdf(request: dict):
    """Generate PDF from review data."""
    try:
        from utils.pdf_report import generate_review_pdf
        pdf_bytes = generate_review_pdf(request)
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=code_review.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


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
        raise HTTPException(
            status_code=404, detail="Review not found. Trigger a review first."
        )
    return review_store[key]
