"""GitHub PR handler — using direct GitHub API for reliability."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

MAX_FILES = 30


def fetch_pr_diff(owner: str, repo: str, pr_number: int, github_token: str) -> dict:
    """Fetch a PR's diff using GitHub REST API directly."""

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
    )

    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    max_retries = 3

    for attempt in range(max_retries):
        try:
            # Get PR info
            pr_url = f"{base_url}/pulls/{pr_number}"
            pr_resp = session.get(pr_url, timeout=30)
            pr_resp.raise_for_status()
            pr_data = pr_resp.json()

            # Get PR files
            files_url = f"{base_url}/pulls/{pr_number}/files"
            files_resp = session.get(files_url, timeout=60)
            files_resp.raise_for_status()
            files_data = files_resp.json()

            # Process files (limit to MAX_FILES)
            files = []
            for i, f in enumerate(files_data[:MAX_FILES]):
                files.append(
                    {
                        "filename": f.get("filename", ""),
                        "status": f.get("status", ""),
                        "patch": f.get("patch", ""),
                        "additions": f.get("additions", 0),
                        "deletions": f.get("deletions", 0),
                        "changes": f.get("changes", 0),
                    }
                )

            if len(files_data) > MAX_FILES:
                logger.warning(
                    f"Limited to {MAX_FILES} files (total: {len(files_data)})"
                )

            # Build diff string (limit each file to 5000 chars)
            diff_parts = []
            for f in files:
                if f["patch"]:
                    patch = f["patch"][:5000]
                    diff_parts.append(
                        f"--- a/{f['filename']}\n+++ b/{f['filename']}\n{patch}"
                    )

            full_diff = "\n\n".join(diff_parts)

            logger.info(f"Fetched {len(files)} files from PR #{pr_number}")

            return {
                "title": pr_data.get("title", ""),
                "body": pr_data.get("body", "") or "",
                "diff": full_diff,
                "files": files,
            }

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                logger.warning(
                    f"Timeout (attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                raise RuntimeError(
                    "GitHub API timeout. The PR may be too large. Try a smaller PR."
                )
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                logger.warning(f"API error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"GitHub API error: {str(e)}")


def post_review_comment(
    owner: str, repo: str, pr_number: int, comment_body: str, github_token: str
) -> bool:
    """Post a review comment on a GitHub PR."""
    try:
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AI-Code-Review-Agent",
            }
        )

        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = session.post(url, json={"body": comment_body}, timeout=30)
        resp.raise_for_status()

        logger.info(f"Posted review comment on PR #{pr_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to post comment: {str(e)}")
        return False
