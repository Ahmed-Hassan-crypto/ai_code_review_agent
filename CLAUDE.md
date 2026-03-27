# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Unix/Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Terminal 1 - Start FastAPI backend
uvicorn server:app --reload --port 8000

# Terminal 2 - Start Streamlit frontend
streamlit run app.py
```

### Testing
```bash
# Test backend health
curl http://localhost:8000/health

# Test manual review endpoint
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'

# Test Streamlit UI
# Open browser to http://localhost:8501, enter PR URL, click Review
```

## Code Architecture

### High-Level Structure
```
ai_code_review_agent/
├── agent/                # LangGraph agent pipeline
│   ├── state.py          # TypedDict state schema
│   ├── prompts.py        # System prompts for each node
│   ├── nodes.py          # 8 LangGraph nodes
│   └── graph.py          # StateGraph composition
├── github_integration/   # GitHub API integration
│   ├── pr_handler.py     # Fetch diffs, post comments via PyGithub
│   └── webhook.py        # HMAC-SHA256 webhook verification
├── utils/
│   └── pdf_report.py     # Formatted PDF report generator
├── server.py             # FastAPI backend (4 endpoints)
├── app.py                # Streamlit frontend + PDF download
├── requirements.txt      # Python dependencies
└── walkthrough.md        # Usage guide
```

### Component Responsibilities

**Agent Pipeline (LangGraph):**
- `state.py`: Defines state with `pr_url`, `diff_text`, `files`, `lint_results`, `logic_results`, `fix_suggestions`, `scores`, `final_review`
- `nodes.py`: 8 nodes in pipeline:
  - `fetch_diff`: Parses PR URL, uses PyGithub to get diff + metadata
  - `parse_files`: Splits raw diff into per-file chunks
  - `lint_review`: Groq LLama 3.3 - style, naming, PEP-8 (JSON output)
  - `logic_review`: Groq LLama 3.3 - security, bugs, architecture (markdown output)
  - `suggest_fixes`: Groq LLama 3.3 - generates before/after code fixes (JSON)
  - `score_files`: Groq LLama 3.3 - rates each file 1-10 with justification
  - `format_review`: Assembles results into GitHub-flavored markdown
  - `post_review`: Posts structured comment to GitHub PR
- `graph.py`: Composes StateGraph with parallel execution:
  - `lint_review` and `logic_review` run concurrently
  - Uses `Send()` API for fan-out parallel file processing
  - All LLM calls use `_invoke_with_retry()` with exponential backoff

**GitHub Integration:**
- `pr_handler.py`: PyGithub wrapper for fetching diffs and posting comments
- `webhook.py`: HMAC-SHA256 signature verification, event parsing for auto-trigger

**FastAPI Backend:**
- `server.py`: 4 endpoints:
  - `POST /review`: Manual trigger with PR URL
  - `POST /webhook`: GitHub webhook receiver (auto-review on PR open/push)
  - `GET /reviews/{owner}/{repo}/{pr_number}`: Fetch cached results
  - `GET /health`: Health check

**Streamlit Frontend:**
- `app.py`: Code review dashboard
  - PR URL input with one-click review button
  - Status tracker showing pipeline progress
  - Metrics dashboard (overall score, files reviewed)
  - Per-file expandable cards with tabbed views (lint/security/fixes)
  - PDF download button

**PDF Report:**
- Generates formatted PDF with title page, color-coded score bars, all findings, page numbers

### Data Flow
1. PR URL submitted (manual or webhook) → FastAPI receives
2. LangGraph graph runs: fetch diff → parse files → parallel lint+logic → suggest fixes → score → format → post
3. Results cached in-memory by `owner/repo#pr_number`
4. Streamlit polls `/reviews` endpoint to display results
5. PDF generated on-demand from cached results

### Key Technical Details
- LLM: Groq LLama 3.3 70B Versatile - fast inference, low latency
- GitHub API: PyGithub library for auth, diff fetching, comment posting
- Retry logic: Exponential backoff (5s → 10s → 20s) on rate limits
- Security prompts: OWASP Top 10 coverage, severity ratings (Critical/High/Medium/Low/Info)
- Webhook: Requires `ngrok` for local testing, HMAC-SHA256 signature verification
- PDF: fpdf2 for pure Python generation

### Environment Variables
Required in `.env`:
- `GROQ_API_KEY`: Groq API key (get from https://console.groq.com)
- `GITHUB_TOKEN`: GitHub PAT with `repo` scope
- `GITHUB_WEBHOOK_SECRET`: HMAC secret for webhook verification
