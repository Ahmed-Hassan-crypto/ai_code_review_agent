# AI Code Review Agent - Production Ready

## Quick Deploy to Render

### Option 1: Deploy Backend Only (API + Webhook)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for production"
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Connect your GitHub

3. **Create Web Service**
   - New → Web Service
   - Connect your repository
   - Settings:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
     - Environment: Python 3.11

4. **Set Environment Variables**
   ```
   GROQ_API_KEY=your_groq_api_key
   GITHUB_TOKEN=your_github_token
   GITHUB_WEBHOOK_SECRET=your_secret
   ```

### Option 2: Deploy with Docker

```bash
# Build
docker build -t ai-code-review-agent .

# Run
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e GITHUB_TOKEN=your_token \
  -e GITHUB_WEBHOOK_SECRET=secret \
  ai-code-review-agent
```

---

## Render Deployment Steps

### Step 1: Prepare for Production

The app is already configured for deployment. Just make sure:

1. **Update .env for production**
   ```bash
   # Update these in Render Dashboard
   GROQ_API_KEY=your_actual_key
   GITHUB_TOKEN=your_actual_token
   GITHUB_WEBHOOK_SECRET=random_secret_string
   ```

2. **Create render.yaml** (optional - for auto-deploy)

### Step 3: Deploy

1. Connect GitHub repo to Render
2. Set environment variables in Render dashboard
3. Deploy!

---

## Production Features Included

| Feature | Status |
|---------|--------|
| FastAPI with Swagger UI | ✓ |
| Health check endpoint | ✓ |
| GitHub webhook support | ✓ |
| Error handling | ✓ |
| Logging | ✓ |
| Docker support | ✓ |
| PDF generation | ✓ |
| CORS enabled | ✓ |

---

## API Endpoints (Production)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/review` | Trigger review |
| POST | `/webhook` | GitHub webhook |
| GET | `/reviews/{owner}/{repo}/{pr_number}` | Get results |

### Webhook Setup for Production

After deploying to Render:

1. Get your Render URL (e.g., `https://ai-code-review.onrender.com`)
2. Go to GitHub repo → Settings → Webhooks
3. Add webhook:
   - **URL**: `https://your-app.onrender.com/webhook`
   - **Secret**: Same as `GITHUB_WEBHOOK_SECRET`
   - **Events**: Pull requests

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Get from https://console.groq.com |
| `GITHUB_TOKEN` | Yes | GitHub PAT with repo scope |
| `GITHUB_WEBHOOK_SECRET` | No | For webhook verification |
| `PORT` | Auto | Render sets this |

---

## Troubleshooting

**Build fails?**
- Make sure `requirements.txt` has all dependencies
- Check Python version is 3.11

**Runtime errors?**
- Check environment variables are set
- Check logs in Render dashboard

**Webhook not working?**
- Verify URL is correct
- Check webhook secret matches

---

## Architecture

```
                    ┌─────────────────┐
                    │   GitHub PR     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Render/Render  │
                    │   FastAPI Server │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  LangGraph       │
                    │  Pipeline        │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
   │ Groq LLM    │   │ GitHub API  │   │  PDF Gen   │
   └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Performance

- **Response time**: ~15-30 seconds
- **Rate limits**: Use `llama-3.1-8b-instant` for higher limits
- **Memory**: ~512MB recommended

---

## Ready for Production! 🚀