"""GitHub Webhook verification and payload parsing."""

import hashlib
import hmac


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the GitHub webhook HMAC-SHA256 signature.
    
    Args:
        payload: Raw request body bytes
        signature: The X-Hub-Signature-256 header value
        secret: Your webhook secret string
        
    Returns:
        True if the signature is valid
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def parse_webhook_payload(payload: dict) -> dict | None:
    """Parse a GitHub pull_request webhook payload.
    
    Args:
        payload: The parsed JSON body from GitHub
        
    Returns:
        dict with repo_owner, repo_name, pr_number, action — or None if not actionable
    """
    action = payload.get("action")

    # Only trigger on new PRs or new commits pushed to a PR
    if action not in ("opened", "synchronize"):
        return None

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})

    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    pr_number = pr.get("number")

    if not all([owner, repo_name, pr_number]):
        return None

    pr_url = pr.get("html_url", f"https://github.com/{owner}/{repo_name}/pull/{pr_number}")

    return {
        "repo_owner": owner,
        "repo_name": repo_name,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "action": action,
    }
