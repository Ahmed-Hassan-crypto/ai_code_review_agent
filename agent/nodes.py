"""LangGraph nodes for the AI Code Review Agent - Optimized for Speed."""

import json
import os
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from agent.prompts import (
    CODE_FIXER_PROMPT,
    LINTER_PROMPT,
    SCORER_PROMPT,
    SENIOR_SECURITY_ENGINEER_PROMPT,
)
from github_integration.pr_handler import fetch_pr_diff, post_review_comment

load_dotenv()

# ── Model Instance ────────────────────────────────────────────────────────────
model = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
)


# ── Helper ───────────────────────────────────────────────────────────────────
def _invoke_with_retry(messages, max_retries=2):
    """Invoke Groq LLM."""
    try:
        return model.invoke(messages)
    except Exception as e:
        if "429" in str(e):
            return None  # Return None on rate limit, handle gracefully
        raise


def _parse_json_response(text: str) -> list | dict:
    """Extract JSON from an LLM response."""
    if not text:
        return []
    text = text.strip()
    match = re.search(r"```(?:json)?\n?(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def _build_file_context(file_data: dict) -> str:
    """Build context for a file diff."""
    return f"File: {file_data['filename']}\nStatus: {file_data['status']}\nChanges:\n{file_data.get('patch', '')[:1500]}"


# ── Node: Fetch Diff ────────────────────────────────────────────────────────
def fetch_diff(state: dict) -> dict:
    """Fetch the PR diff from GitHub."""
    pr_url = state["pr_url"]
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, pr_url)
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")

    owner, repo, pr_number = match.group(1), match.group(2), int(match.group(3))
    github_token = os.getenv("GITHUB_TOKEN")
    pr_data = fetch_pr_diff(owner, repo, pr_number, github_token)

    return {
        "repo_owner": owner,
        "repo_name": repo,
        "pr_number": pr_number,
        "pr_title": pr_data["title"],
        "pr_body": pr_data["body"],
        "diff_text": pr_data["diff"],
        "files": pr_data["files"],
    }


# ── Combined Review Node (FASTER) ────────────────────────────────────────────
def combined_review(state: dict) -> dict:
    """Combined lint + logic review in ONE LLM call."""
    files = state["files"]
    if not files:
        return {"lint_results": [], "logic_results": []}

    # Process all files with a more detailed prompt
    all_lint = []
    all_security = []

    # Process in batches of 3 to avoid token limits
    batch_size = 3
    for i in range(0, len(files), batch_size):
        batch = files[i : i + batch_size]

        file_contexts = "\n\n---\n\n".join(_build_file_context(f) for f in batch)

        prompt = f"""You are a senior security engineer and code reviewer. 
Analyze this code diff and provide detailed findings in JSON format.

For each file, identify:
1. LINT ISSUES: Style, naming, formatting, code quality issues
2. SECURITY ISSUES: SQL injection, XSS, hardcoded secrets, authentication issues, etc.
3. LOGIC ISSUES: Bugs, logical errors, potential crashes

Files to review:
{file_contexts}

Respond with a JSON object with "lint" and "security" arrays. Each item must include:
- filename: the file name
- severity: CRITICAL, HIGH, MEDIUM, LOW, or INFO
- line: line number where issue occurs
- message: description of the issue
- suggestion: how to fix it (for security issues)

Also include a "security_summary" field with overall security assessment.

Example format:
{{"lint": [{{"filename": "auth.py", "severity": "HIGH", "line": 15, "message": "SQL injection", "suggestion": "Use parameterized queries"}}], "security": [{{"filename": "auth.py", "severity": "CRITICAL", "line": 10, "message": "Hardcoded password", "suggestion": "Use environment variables"}}, {{"filename": "auth.py", "severity": "HIGH", "line": 25, "message": "Missing authentication check", "suggestion": "Add auth validation"}}, ...]}}"""

        response = _invoke_with_retry(
            [
                {
                    "role": "system",
                    "content": "You are a senior code reviewer. Provide detailed findings. Respond ONLY with valid JSON.",
                },
                {"role": "human", "content": prompt},
            ]
        )

        if response:
            results = _parse_json_response(response.content)
            if isinstance(results, dict):
                if results.get("lint"):
                    all_lint.extend(results.get("lint", []))
                if results.get("security"):
                    all_security.extend(results.get("security", []))

    # Group by file
    lint_results = []
    for file_data in files:
        file_lint = [i for i in all_lint if i.get("filename") == file_data["filename"]]
        lint_results.append(
            {"filename": file_data["filename"], "lint_issues": file_lint}
        )

    logic_results = []
    for file_data in files:
        file_sec = [
            i for i in all_security if i.get("filename") == file_data["filename"]
        ]

        # Build detailed security review text
        if file_sec:
            review_lines = [f"Found {len(file_sec)} security issue(s):\n"]
            for issue in file_sec:
                sev = issue.get("severity", "INFO")
                review_lines.append(
                    f"- **{sev}** Line {issue.get('line', '?')}: {issue.get('message', '')}"
                )
                if issue.get("suggestion"):
                    review_lines.append(f"  Fix: {issue['suggestion']}")
            logic_review = "\n".join(review_lines)
        else:
            logic_review = "No security issues found."

        logic_results.append(
            {"filename": file_data["filename"], "logic_review": logic_review}
        )

    return {"lint_results": lint_results, "logic_results": logic_results}


# ── Combined Fixes + Score (FASTER) ───────────────────────────────────────────
def combined_fixes_and_score(state: dict) -> dict:
    """Generate fixes and scores with accurate scoring based on issues."""
    files = state["files"]
    lint_results = state.get("lint_results", [])
    logic_results = state.get("logic_results", [])
    fix_suggestions = state.get("fix_suggestions", [])

    if not files:
        return {"fix_suggestions": [], "scores": []}

    # Calculate scores based on actual issues found
    fix_suggestions = []
    scores = []

    for file_data in files:
        fname = file_data["filename"]

        # Get lint issues for this file
        f_lint = next((r for r in lint_results if r["filename"] == fname), {})
        lint_issues = f_lint.get("lint_issues", [])

        # Get security issues for this file
        f_logic = next((r for r in logic_results if r["filename"] == fname), {})
        logic_text = f_logic.get("logic_review", "")

        # Count issues
        num_lint = len(lint_issues)
        num_security = 0
        if (
            logic_text
            and "No security issues" not in logic_text
            and "Found 0" not in logic_text
        ):
            # Parse security issues count from logic_review
            import re

            match = re.search(r"Found (\d+)", logic_text)
            if match:
                num_security = int(match.group(1))

        # Calculate score based on issues
        # Start with 10, deduct points for issues
        base_score = 10

        # Deduct for critical issues
        critical_count = sum(1 for i in lint_issues if i.get("severity") == "CRITICAL")
        high_count = sum(1 for i in lint_issues if i.get("severity") == "HIGH")
        medium_count = sum(1 for i in lint_issues if i.get("severity") == "MEDIUM")

        # Apply penalties
        deductions = (
            (critical_count * 3)
            + (high_count * 2)
            + (medium_count * 1)
            + (num_security * 2)
        )

        # Calculate final score (minimum 1)
        score = max(1, base_score - deductions)

        # Generate justification
        if score >= 8:
            justification = f"Clean code, {num_lint} lint issue(s), {num_security} security issue(s)"
        elif score >= 6:
            justification = f"Some issues found - {num_lint} lint, {num_security} security. Needs minor fixes."
        elif score >= 4:
            justification = f"Several issues - {num_lint} lint, {num_security} security. Requires attention."
        else:
            justification = f"Multiple critical issues - {num_lint} lint, {num_security} security. Needs major fixes."

        scores.append(
            {
                "filename": fname,
                "score": score,
                "justification": justification,
                "issues_count": num_lint + num_security,
            }
        )

        # Generate fixes based on issues
        fixes = []

        # Create fixes for lint issues
        for issue in lint_issues:
            fixes.append(
                {
                    "issue_title": f"Fix: {issue.get('message', 'Issue')[:50]}",
                    "severity": issue.get("severity", "MEDIUM"),
                    "original_code": "Code with issue (see line "
                    + str(issue.get("line", "?"))
                    + ")",
                    "fixed_code": issue.get("suggestion", "Fixed code"),
                    "explanation": f"Line {issue.get('line', '?')}: {issue.get('message', '')}",
                }
            )

        fix_suggestions.append(
            {
                "filename": fname,
                "fixes": fixes,
            }
        )

    return {"fix_suggestions": fix_suggestions, "scores": scores}


# ── Legacy Nodes (for compatibility) ──────────────────────────────────────────
def lint_review(state: dict) -> dict:
    """Legacy lint review - redirects to combined."""
    return combined_review(state)


def logic_review(state: dict) -> dict:
    """Legacy logic review - returns empty (combined handles it)."""
    return {"logic_results": []}


def suggest_fixes(state: dict) -> dict:
    """Legacy suggest fixes - redirects to combined."""
    return combined_fixes_and_score(state)


def score_files(state: dict) -> dict:
    """Legacy score files - returns empty (combined handles it)."""
    return {"scores": []}


# ── Node: Format Review ──────────────────────────────────────────────────────
def format_review(state: dict) -> dict:
    """Assemble results into detailed markdown review for GitHub comment."""
    scores = state.get("scores", [])
    lint_results = state.get("lint_results", [])
    logic_results = state.get("logic_results", [])
    fix_suggestions = state.get("fix_suggestions", [])

    overall = sum(s["score"] for s in scores) / len(scores) if scores else 0

    # Determine overall status emoji
    if overall >= 8:
        status_emoji = "✅"
        status_text = "Great work!"
    elif overall >= 6:
        status_emoji = "⚠️"
        status_text = "Needs some improvements"
    else:
        status_emoji = "❌"
        status_text = "Requires attention"

    lines = []
    lines.append("## 🔍 AI Code Review Report")
    lines.append("")
    lines.append(f"**Overall Quality Score:** {overall:.1f}/10 {status_emoji}")
    lines.append(f"**Status:** {status_text}")
    lines.append(f"**Files Reviewed:** {len(scores)}")
    lines.append("---")
    lines.append("")

    # Summary of issues
    total_lint = sum(len(r.get("lint_issues", [])) for r in lint_results)
    total_fixes = sum(len(r.get("fixes", [])) for r in fix_suggestions)

    if total_lint > 0 or total_fixes > 0:
        lines.append("### 📊 Summary")
        lines.append(f"- **Total Issues Found:** {total_lint}")
        if total_fixes > 0:
            lines.append(f"- **Suggested Fixes:** {total_fixes}")
        lines.append("")

    # Per-file detailed review
    for score_data in scores:
        fname = score_data["filename"]
        fscore = score_data["score"]
        justification = score_data.get("justification", "No justification provided")

        # File header
        if fscore >= 8:
            file_emoji = "✅"
        elif fscore >= 6:
            file_emoji = "⚠️"
        else:
            file_emoji = "❌"

        lines.append(f"### {file_emoji} `{fname}`")
        lines.append(f"**Score:** {fscore}/10")
        lines.append(f"**Rating:** {justification}")
        lines.append("")

        # Lint Issues
        file_lint = next((r for r in lint_results if r["filename"] == fname), {})
        lint_issues = file_lint.get("lint_issues", [])

        if lint_issues:
            lines.append("#### 🧹 Lint Issues Found")
            for issue in lint_issues:
                severity = issue.get("severity", "INFO")
                line = issue.get("line", "?")
                message = issue.get("message", "")
                suggestion = issue.get("suggestion", "")

                sev_emoji = (
                    "🔴"
                    if severity == "ERROR"
                    else ("🟡" if severity == "WARNING" else "ℹ️")
                )
                lines.append(f"- {sev_emoji} **{severity}** at Line {line}: {message}")
                if suggestion:
                    lines.append(f"  > 💡 Suggestion: {suggestion}")
            lines.append("")

        # Security/Logic Review
        file_logic = next((r for r in logic_results if r["filename"] == fname), {})
        logic_text = file_logic.get("logic_review", "")

        if logic_text:
            lines.append("#### 🛡️ Security & Logic Review")
            # Clean and truncate long text
            if len(logic_text) > 1500:
                logic_text = logic_text[:1500] + "..."
            lines.append(logic_text)
            lines.append("")

        # Suggested Fixes
        file_fixes = next((r for r in fix_suggestions if r["filename"] == fname), {})
        fixes = file_fixes.get("fixes", [])

        if fixes:
            lines.append("#### 🔧 Suggested Fixes")
            for fix in fixes:
                title = fix.get("issue_title", "Fix")
                severity = fix.get("severity", "N/A")
                original = fix.get("original_code", "")
                fixed = fix.get("fixed_code", "")
                explanation = fix.get("explanation", "")

                lines.append(f"**{title}** ({severity})")
                if original and fixed:
                    lines.append("```diff")
                    lines.append(f"- {original}")
                    lines.append(f"+ {fixed}")
                    lines.append("```")
                if explanation:
                    lines.append(f"> {explanation}")
                lines.append("")

        if not lint_issues and not logic_text and not fixes:
            lines.append("✅ No issues found in this file.")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("*This review was automatically generated by AI Code Review Agent.*")

    final_review = "\n".join(lines)

    # Truncate if too long for GitHub (65536 chars max)
    if len(final_review) > 60000:
        final_review = (
            final_review[:60000] + "\n\n... *(Review truncated - too many findings)*"
        )

    return {"final_review": final_review, "overall_score": round(overall, 1)}


# ── Node: Post Review ────────────────────────────────────────────────────────
def post_review(state: dict) -> dict:
    """Post FULL review to GitHub - saves markdown file and posts complete review."""
    import logging
    import os
    from datetime import datetime

    import requests

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    print("=" * 50)
    print("POST REVIEW NODE EXECUTED")
    print("=" * 50)

    github_token = os.getenv("GITHUB_TOKEN")
    print(f"GitHub Token present: {bool(github_token)}")
    print(
        f"Token value: {github_token[:10]}... if exists" if github_token else "No token"
    )

    if not github_token or github_token == "your_github_token_here":
        print("ERROR: No GitHub token or placeholder token!")
        return {"comment_posted": False, "reason": "No GitHub token configured"}

    try:
        # Get full review content
        final_review = state.get("final_review", "")
        overall = state.get("overall_score", 0)

        print(f"Final review length: {len(final_review)}")
        print(f"Overall score: {overall}")

        if not final_review:
            print("ERROR: No final review content!")
            return {"comment_posted": False, "reason": "No review content"}

        # Save markdown file locally
        pr_title = state.get("pr_title", "Review").replace(" ", "_")[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_review_{pr_title}_{timestamp}.md"

        reviews_dir = "reviews"
        os.makedirs(reviews_dir, exist_ok=True)
        filepath = os.path.join(reviews_dir, filename)

        # Write full markdown file
        full_md = f"""# 🔍 AI Code Review Report

**PR:** {state.get('pr_title', 'Review')}
**URL:** https://github.com/{state['repo_owner']}/{state['repo_name']}/pull/{state['pr_number']}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Overall Score:** {overall}/10

---

{final_review}

---

*Generated by AI Code Review Agent*
*Full review saved to: {filename}*
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_md)

        print(f"Saved review to {filepath}")

        # Post the FULL detailed review to GitHub
        # Truncate if needed (GitHub has 65536 char limit per comment)
        if len(final_review) > 60000:
            review_to_post = final_review[:60000] + "\n\n... *(Full review truncated)*"
        else:
            review_to_post = final_review

        # Build comment with header + full review
        header = f"""## 🔍 AI Code Review Report

**Overall Score:** {overall}/10
**PR:** {state.get('pr_title', 'Review')}
**Full Review Details:**

---
"""

        full_comment = header + review_to_post + f"""

---
*Full markdown review saved to: `{filename}`*
*Generated by AI Code Review Agent*"""

        print(f"Comment length: {len(full_comment)}")
        print("Posting to GitHub...")

        # Post to GitHub
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        url = f"https://api.github.com/repos/{state['repo_owner']}/{state['repo_name']}/issues/{state['pr_number']}/comments"
        print(f"URL: {url}")

        resp = session.post(url, json={"body": full_comment}, timeout=30)

        print(f"Response status: {resp.status_code}")
        print(f"Response text: {resp.text[:200] if resp.text else 'No response'}")

        if resp.status_code == 201:
            print(f"SUCCESS: Posted FULL review comment to PR #{state['pr_number']}")
            return {"comment_posted": True, "markdown_file": filename}
        else:
            print(f"ERROR: Failed to post - {resp.status_code}")
            return {"comment_posted": False, "reason": f"API error: {resp.status_code}"}

    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        logger.error(f"Error posting review: {str(e)}")
        return {"comment_posted": False, "reason": str(e)}
