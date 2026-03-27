# AI Code Review Agent — Implementation Plan

An AI-powered code review agent that automatically reviews GitHub PRs for bugs, security vulnerabilities, and style issues. It uses a **hybrid Gemini approach** (Flash for linting, Pro for deep logic review) orchestrated by **LangGraph**, served via **FastAPI**, and controllable through a **Streamlit UI**.

## Architecture Overview

```mermaid
graph LR
    A[GitHub PR / Webhook] --> B[FastAPI Backend]
    B --> C[LangGraph Agent Graph]
    C --> D[Fetch Diff Node]
    D --> E[Parse Files Node]
    E --> F[Linter Node<br/>Gemini 2.5 Flash]
    E --> G[Logic Reviewer Node<br/>Gemini 2.5 Pro]
    F --> H[Code Fixer Node<br/>Gemini 2.5 Pro]
    G --> H
    H --> I[Scorer Node]
    I --> J[Format & Post Node]
    J --> K[GitHub PR Comment]
    B --> L[Streamlit UI]
```

**Flow**: PR URL submitted (manually or via webhook) → FastAPI receives → LangGraph graph runs → diff fetched → files parsed → parallel lint + logic review → code fixer suggests fixes → scorer rates each file 1–10 → structured comment posted back to PR.

---

## Project Structure

```
c:\2026 AI Projects\ai_code_review_agent\
├── .env                        # API keys & config
├── .venv/                      # Virtual environment (all dependencies)
├── requirements.txt
├── server.py                   # FastAPI backend
├── app.py                      # Streamlit frontend
├── agent/
│   ├── state.py                # LangGraph state schema
│   ├── graph.py                # Graph composition
│   ├── nodes.py                # All agent nodes
│   └── prompts.py              # System prompts (Senior Security Engineer)
├── github_integration/
│   ├── pr_handler.py           # Fetch PR diffs, post comments
│   └── webhook.py              # Webhook verification & parsing
└── utils/
    └── helpers.py              # Shared utilities
```

---

## Proposed Changes

### 0. Virtual Environment Setup

Create an isolated Python virtual environment (`.venv`) inside the project directory. **All dependencies will be installed here**, keeping the system Python clean.

```bash
# Create the virtual environment
cd "c:\2026 AI Projects\ai_code_review_agent"
python -m venv .venv

# Activate it (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt
```

> [!NOTE]
> Every time you open a new terminal to work on this project, you must activate the venv first:
> `.\.venv\Scripts\Activate.ps1`

---

### 1. Core Agent — `agent/`

#### [NEW] [state.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/agent/state.py)
LangGraph `TypedDict` state with fields:
- `pr_url: str` — input PR URL
- `repo_name: str`, `pr_number: int` — parsed identifiers
- `diff_text: str` — raw diff from GitHub
- `files: list[dict]` — parsed per-file diffs (`filename`, `patch`, `status`)
- `lint_results: list[dict]` — per-file lint findings (Gemini Flash)
- `logic_results: list[dict]` — per-file logic/security findings (Gemini Pro)
- `fix_suggestions: list[dict]` — per-file suggested code fixes
- `scores: list[dict]` — per-file quality scores (1–10)
- `final_review: str` — formatted markdown review comment

#### [NEW] [prompts.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/agent/prompts.py)
System prompts:
- **`SENIOR_SECURITY_ENGINEER_PROMPT`**: Core persona prompt instructing Gemini to act as a Senior Security Engineer with 15+ years experience. Covers: input validation, injection attacks, auth flaws, data exposure, race conditions, cryptographic misuse, dependency vulnerabilities, OWASP Top 10 mapping, severity ratings (Critical/High/Medium/Low/Info).
- **`LINTER_PROMPT`**: Focused on syntax, naming conventions, formatting, PEP-8 / language-specific style.
- **`CODE_FIXER_PROMPT`**: Instructs Gemini to generate specific code fix suggestions (with before/after diffs) based on the lint + logic findings.

#### [NEW] [nodes.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/agent/nodes.py)
LangGraph nodes:
| Node | Model | Purpose |
|------|-------|---------|
| `fetch_diff` | — | Uses PyGithub to fetch PR diff and metadata |
| `parse_files` | — | Splits raw diff into per-file chunks |
| `lint_review` | Gemini 2.5 Flash | Quick lint pass: syntax, naming, formatting |
| `logic_review` | Gemini 2.5 Pro | Deep review: bugs, security, architecture |
| `suggest_fixes` | Gemini 2.5 Pro | Generates concrete code fix suggestions |
| `score_files` | Gemini 2.5 Flash | Assigns 1–10 quality score per file with justification |
| `format_review` | — | Assembles all results into a structured markdown comment |
| `post_review` | — | Posts the final review comment to the GitHub PR |

#### [NEW] [graph.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/agent/graph.py)
Composes the LangGraph `StateGraph`:
```
fetch_diff → parse_files → [lint_review, logic_review] (parallel) → suggest_fixes → score_files → format_review → post_review
```
- Uses `Send()` API for **fan-out** to process files in parallel where possible.
- `lint_review` and `logic_review` run concurrently.

---

### 2. GitHub Integration — `github_integration/`

#### [NEW] [pr_handler.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/github_integration/pr_handler.py)
- `fetch_pr_diff(repo_name, pr_number, github_token)` → returns diff text + file list
- `post_review_comment(repo_name, pr_number, comment_body, github_token)` → posts an issue comment
- Uses `PyGithub` library

#### [NEW] [webhook.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/github_integration/webhook.py)
- `verify_webhook_signature(payload, signature, secret)` — HMAC-SHA256 verification
- `parse_webhook_payload(payload)` — extracts `action`, `pr_number`, `repo_name` from the webhook JSON
- Only triggers on `action == "opened"` or `action == "synchronize"` (new PR or new commits pushed)

---

### 3. FastAPI Backend — `server.py`

#### [NEW] [server.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/server.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhook` | POST | Receives GitHub webhook, verifies signature, triggers review graph |
| `/review` | POST | Manual trigger — accepts `{ "pr_url": "..." }`, triggers review graph |
| `/reviews/{owner}/{repo}/{pr_number}` | GET | Returns cached review results (stored in-memory dict) |
| `/health` | GET | Health check |

- Runs review graph asynchronously using `asyncio.to_thread()`
- Stores results in an in-memory dictionary keyed by `owner/repo#pr_number`

---

### 4. Streamlit Frontend — [app.py](file:///c:/2026%20AI%20Projects/multi_agent_researcher/app.py)

#### [NEW] [app.py](file:///c:/2026%20AI%20Projects/ai_code_review_agent/app.py)

UI sections:
1. **Header** — "🔍 AI Code Review Agent" title + description
2. **PR Input** — Text input for GitHub PR URL + "Review" button
3. **Status** — Spinner/progress bar while review runs
4. **Results Dashboard**:
   - Overall summary with aggregated score
   - Per-file expandable sections showing:
     - Quality score (1–10) with color indicator
     - Lint findings
     - Security/logic findings with severity badges
     - Suggested code fixes (rendered as diff blocks)
5. **Sidebar** — Configuration (GitHub token input, model selection override)

Calls FastAPI `/review` endpoint via `requests`.

---

### 5. Configuration & Dependencies

#### [NEW] [.env](file:///c:/2026%20AI%20Projects/ai_code_review_agent/.env)
```
GOOGLE_API_KEY=AIzaSyDfDXlQVkaxC3hD7g-XgxHmbanwLebtPro
GITHUB_TOKEN=<user_must_provide>
GITHUB_WEBHOOK_SECRET=<user_must_provide>
```

#### [NEW] [requirements.txt](file:///c:/2026%20AI%20Projects/ai_code_review_agent/requirements.txt)
```
streamlit
langgraph
langchain-google-genai
PyGithub
fastapi
uvicorn
python-dotenv
requests
```

---

### 6. GitHub Webhook Setup

> [!IMPORTANT]
> **User action required**: After deployment, you need to configure a GitHub Webhook on your repository:
> 1. Go to your repo → **Settings** → **Webhooks** → **Add webhook**
> 2. **Payload URL**: `https://<your-server>/webhook`
> 3. **Content type**: `application/json`
> 4. **Secret**: The same value as `GITHUB_WEBHOOK_SECRET` in your [.env](file:///c:/2026%20AI%20Projects/multi_agent_researcher/.env)
> 5. **Events**: Select "Pull requests"
> 6. For local testing, use **ngrok** to expose your FastAPI server: `ngrok http 8000`

---

## User Review Required

> [!IMPORTANT]
> **GitHub Token needed**: You must provide a **GitHub Personal Access Token** with `repo` scope to fetch PR diffs and post review comments. Please add it to the [.env](file:///c:/2026%20AI%20Projects/multi_agent_researcher/.env) file after project creation.

> [!WARNING]
> **Webhook requires public URL**: The GitHub webhook endpoint needs a publicly accessible URL. For local development, we'll use **ngrok** or similar tunneling. For production, you'd deploy the FastAPI server.

> [!NOTE]
> **Hybrid model approach**: The plan uses Gemini 2.5 Flash for quick linting/scoring and Gemini 2.5 Pro for deep logic/security review and fix suggestions. This balances speed vs. depth while keeping costs optimal.

---

## Verification Plan

### Automated Tests
1. **End-to-end test with a real PR**:
   ```bash
   # 0. Activate virtual environment
   cd "c:\2026 AI Projects\ai_code_review_agent"
   .\.venv\Scripts\Activate.ps1

   # 1. Start FastAPI server
   python -m uvicorn server:app --port 8000
   
   # 2. Send a manual review request (in another terminal)
   curl -X POST http://localhost:8000/review -H "Content-Type: application/json" -d "{\"pr_url\": \"https://github.com/<owner>/<repo>/pull/<number>\"}"
   ```
   - Verify the response contains lint results, logic results, fix suggestions, and scores.

2. **Streamlit UI test**:
   ```bash
   cd "c:\2026 AI Projects\ai_code_review_agent"
   streamlit run app.py
   ```
   - Open in browser, paste a PR URL, click Review, verify results render correctly.

### Manual Verification
1. **User provides a GitHub Token** and a test PR URL
2. Submit the PR URL through the Streamlit UI
3. Verify that:
   - Diff is fetched correctly
   - Lint findings are populated (style/formatting issues)
   - Logic findings show security/bug analysis
   - Fix suggestions contain actual code diffs
   - Each file has a 1–10 quality score
   - A review comment is posted on the actual GitHub PR
4. **Webhook test** (requires ngrok):
   - Start ngrok, configure webhook on a test repo
   - Open a new PR → verify auto-review triggers
