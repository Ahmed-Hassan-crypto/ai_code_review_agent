# AI Code Review Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/LangGraph-LLM%20Agents-orange.svg" alt="LangGraph">
  <img src="https://img.shields.io/badge/Groq-LLama%203.3-purple.svg" alt="Groq">
</p>

An AI-powered code review agent that automatically reviews GitHub Pull Requests using LangGraph and Groq LLama. Submit a PR URL and receive comprehensive reviews covering bugs, security vulnerabilities, style issues, and suggested fixes.

## Features

- **Automated Code Review** — Submit any GitHub PR URL and get instant AI-powered reviews
- **Security Analysis** — OWASP Top 10 coverage with severity ratings (Critical/High/Medium/Low/Info)
- **Style & Lint Checks** — PEP-8, naming conventions, formatting issues
- **Smart Fix Suggestions** — Before/after code fixes with explanations
- **Quality Scoring** — 1-10 scoring per file with justifications
- **PDF Reports** — Download formatted review reports
- **Webhook Support** — Auto-review on PR open/update via GitHub webhooks
- **REST API** — Full FastAPI backend with Swagger documentation

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  GitHub PR  │────▶│  FastAPI Server │────▶│ LangGraph    │
└─────────────┘     └─────────────────┘     │ Pipeline     │
                                             └──────────────┘
                                                     │
        ┌───────────────────────────────────────────┼───────────────┐
        │                   Nodes                    │               │
        ▼                   ▼                   ▼   ▼               ▼
┌──────────────┐  ┌────────────┐  ┌────────────┐  ┌───────┐  ┌──────────┐
│ Fetch Diff   │  │ Lint Review│  │Logic Review│  │ Score │  │ Post to   │
│ (PyGithub)   │  │ (Flash)    │  │ (Flash)    │  │ Files │  │ GitHub    │
└──────────────┘  └────────────┘  └────────────┘  └───────┘  └──────────┘
        │                │              │              │            │
        └────────────────┴──────────────┴──────────────┴────────────┘
                                             │
                                      ┌──────┴──────┐
                                      ▼             ▼
                               ┌──────────┐  ┌──────────────┐
                               │ Streamlit│  │ PDF Report   │
                               │ Frontend │  │ (fpdf2)      │
                               └──────────┘  └──────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | LangGraph |
| LLM | Google Gemini 2.5 Flash/Pro |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| GitHub API | PyGithub |
| PDF Generation | fpdf2 |
| Testing | pytest |
| Containerization | Docker |

## Quick Start

### Prerequisites

- Python 3.11+
- Groq API key (free at https://console.groq.com)
- GitHub Personal Access Token (with `repo` scope)

### Installation

```bash
# Clone the repository
cd ai_code_review_agent

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your keys
cp .env.example .env
# Edit .env with GOOGLE_API_KEY and GITHUB_TOKEN
```

### Running the Application

```bash
# Terminal 1 - Start FastAPI backend
python -m uvicorn server:app --reload --port 8000

# Terminal 2 - Start Streamlit frontend
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## API Usage

### Health Check
```bash
curl http://localhost:8000/health
```

### Trigger Review
```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'
```

### Get Cached Review
```bash
curl http://localhost:8000/reviews/owner/repo/123
```

### API Documentation
Visit http://localhost:8000/docs for Swagger UI.

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t ai-code-review-agent .
docker run -p 8000:8000 -e GOOGLE_API_KEY=$GOOGLE_API_KEY -e GITHUB_TOKEN=$GITHUB_TOKEN ai-code-review-agent
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_webhook.py

# Run with coverage
pytest --cov=agent --cov=github_integration --cov=utils
```

## Project Structure

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
│   ├── helpers.py            # Utilities
│   └── pdf_report.py         # PDF generation
├── tests/                    # Test suite
├── server.py                 # FastAPI backend
├── app.py                    # Streamlit frontend
├── config.py                 # Configuration management
├── models.py                 # Pydantic models
├── Dockerfile                # Docker image
├── docker-compose.yml        # Docker Compose
├── pyproject.toml            # Project config
└── pytest.ini                # Test configuration
```

## Configuration

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google Gemini API key |
| `GITHUB_TOKEN` | GitHub PAT with repo scope |
| `GITHUB_WEBHOOK_SECRET` | Secret for webhook verification |

## GitHub Webhook Setup

1. Expose local server: `ngrok http 8000`
2. Go to Repository Settings → Webhooks → Add webhook
3. Payload URL: `https://<your-ngrok-url>/webhook`
4. Content type: `application/json`
5. Secret: Same as `GITHUB_WEBHOOK_SECRET`
6. Events: Select "Pull requests"

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black .
isort .

# Type check
mypy agent github_integration utils server

# Run linting
flake8 .
```

## License

MIT License — see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

---

<p align="center">Built with ❤️ using LangGraph + Gemini</p>