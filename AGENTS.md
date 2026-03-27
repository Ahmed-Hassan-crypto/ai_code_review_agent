# AGENTS.md — AI Code Review Agent

> Guidance for agentic coding agents working in this repository.

---

## Quick Start Commands

```bash
# Activate virtual environment
cd ai_code_review_agent
.venv\Scripts\Activate.ps1    # Windows
# source .venv/bin/activate    # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run the backend (Terminal 1)
python -m uvicorn server:app --reload --port 8000

# Run the frontend (Terminal 2)
streamlit run app.py
```

### Running Tests

This project has **no test suite**. Tests would be added as `tests/test_*.py` files and run with:

```bash
pytest tests/                      # Run all tests
pytest tests/test_file.py          # Run specific test file
pytest tests/test_file.py::test_func  # Run specific test function
```

### Linting

No linting configuration exists. To add linting, create a `pyproject.toml` or `.flake8` in the project root with your preferred rules.

### Environment Variables

Create a `.env` file with these required variables:

```
GOOGLE_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_pat_with_repo_scope
GITHUB_WEBHOOK_SECRET=your_hmac_secret_for_webhook_verification
```

---

## Code Style Guidelines

### General Principles

- **Language**: Python 3.11+
- **Dependencies**: Only add to `requirements.txt` if necessary
- **Type hints**: Use for function arguments and return values where beneficial
- **Docstrings**: Use for public APIs and complex logic

### Naming Conventions

- **Variables/Functions**: `snake_case` (e.g., `fetch_diff`, `lint_results`)
- **Classes**: `PascalCase` (e.g., `ReviewRequest`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- **Modules/Files**: `snake_case` (e.g., `pr_handler.py`, `nodes.py`)
- **Private functions**: Prefix with `_` (e.g., `_invoke_with_retry`)

### Import Organization

Standard library → Third-party → Local modules:

```python
import os
import json
import re

from fastapi import FastAPI
from pydantic import BaseModel

from agent.graph import review_graph
from github_integration.webhook import verify_webhook_signature
```

### Code Formatting

- Use **Black** for formatting (recommended) with default settings
- Line length: 88 characters (Black default)
- Use 4 spaces for indentation (no tabs)
- Add trailing commas for multi-line imports

### Error Handling

- Use specific exception types (e.g., `ValueError`, `HTTPException`)
- Let exceptions propagate for unrecoverable errors
- Log errors with descriptive messages
- Return meaningful HTTP status codes in FastAPI endpoints

```python
try:
    result = await run_review(request.pr_url)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")
```

### Type Annotations

Use Python's type hinting for clarity:

```python
def fetch_diff(state: dict) -> dict:
    """Fetch the PR diff from GitHub."""
    pr_url: str = state["pr_url"]
    # ...

def _parse_json_response(text: str) -> list | dict:
    # ...
```

### Async/Await

- Use `async/await` for FastAPI endpoints
- Use `asyncio.to_thread()` to run synchronous code in threads when needed
- Don't block the event loop with synchronous operations

```python
result = await asyncio.to_thread(review_graph.invoke, initial_state)
```

---

## Project Architecture

### Directory Structure

```
ai_code_review_agent/
├── agent/                     # LangGraph pipeline
│   ├── state.py              # TypedDict state schema
│   ├── prompts.py            # System prompts for LLM nodes
│   ├── nodes.py              # 8 LangGraph nodes
│   └── graph.py              # StateGraph composition
├── github_integration/       # GitHub API
│   ├── pr_handler.py         # Fetch diffs, post comments
│   └── webhook.py            # HMAC verification, event parsing
├── utils/
│   ├── helpers.py            # Utilities (truncation)
│   └── pdf_report.py         # PDF generation
├── server.py                 # FastAPI backend (4 endpoints)
├── app.py                    # Streamlit frontend
├── requirements.txt
└── .env                      # API keys
```

### Data Flow

1. PR URL received via `/review` endpoint or webhook
2. LangGraph pipeline: fetch_diff → parse_files → parallel (lint + logic) → suggest_fixes → score_files → format_review → post_review
3. Results cached in-memory by `owner/repo#pr_number`
4. Streamlit polls `/reviews` to display and generate PDF

---

## Existing Documentation

- **CLAUDE.md** — Development commands and architecture reference
- **walkthrough.md** — Usage guide and system prompts

---

## Important Implementation Details

### LLM Usage

- Model: Gemini 2.5 Flash (via `langchain-google-genai`)
- Retry logic: Exponential backoff (5s → 10s → 20s) on rate limits (429)
- JSON responses wrapped in markdown fences — strip before parsing

### GitHub Integration

- Use PyGithub library for API calls
- Webhook verification via HMAC-SHA256
- Token validation: reject placeholder values like `your_github_token_here`

### API Endpoints (server.py)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| POST | `/review` | Manual review trigger |
| POST | `/webhook` | GitHub webhook receiver |
| GET | `/reviews/{owner}/{repo}/{pr_number}` | Fetch cached results |

---

## Cursor/Copilot Rules

No `.cursorrules`, `.cursor/rules/`, or `.github/copilot-instructions.md` files exist in this project.