"""Utility to save review as markdown file."""

import os
from datetime import datetime


def save_review_markdown(review_data: dict, output_dir: str = "reviews") -> str:
    """Save review as a markdown file and return the file path.
    
    Args:
        review_data: The review data dictionary
        output_dir: Directory to save the markdown file
        
    Returns:
        Path to the saved markdown file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    pr_title = review_data.get("pr_title", "review").replace(" ", "_")[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{pr_title}_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)
    
    # Get review content
    final_review = review_data.get("final_review", "")
    pr_url = review_data.get("pr_url", "")
    overall_score = review_data.get("overall_score", 0)
    
    # Build markdown content
    md_content = f"""# 🔍 AI Code Review Report

**PR:** {pr_title}
**URL:** {pr_url}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Overall Score:** {overall_score}/10

---

{final_review}

---

*This review was generated automatically by AI Code Review Agent*
*Full review saved to: {filepath}*
"""
    
    # Save to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    return filepath


def get_markdown_summary(review_data: dict) -> str:
    """Get a short summary markdown for GitHub comment with link to full file.
    
    Args:
        review_data: The review data dictionary
        
    Returns:
        Markdown summary with reference to full file
    """
    pr_title = review_data.get("pr_title", "Review")
    pr_url = review_data.get("pr_url", "")
    overall_score = review_data.get("overall_score", 0)
    scores = review_data.get("scores", [])
    lint_results = review_data.get("lint_results", [])
    fix_suggestions = review_data.get("fix_suggestions", [])
    
    # Count issues
    total_lint = sum(len(r.get("lint_issues", [])) for r in lint_results)
    total_fixes = sum(len(r.get("fixes", [])) for r in fix_suggestions)
    
    # Determine status
    if overall_score >= 8:
        status = "✅ APPROVED"
    elif overall_score >= 6:
        status = "⚠️ NEEDS CHANGES"
    else:
        status = "❌ REJECTED"
    
    lines = []
    lines.append("## 🔍 AI Code Review Report")
    lines.append("")
    lines.append(f"**Status:** {status}")
    lines.append(f"**Score:** {overall_score}/10")
    lines.append(f"**Files Reviewed:** {len(scores)}")
    lines.append(f"**Issues Found:** {total_lint}")
    lines.append(f"**Fixes Suggested:** {total_fixes}")
    lines.append(f"**PR:** [{pr_title}]({pr_url})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### Summary by File")
    lines.append("")
    
    for s in scores:
        fname = s.get("filename", "unknown")
        fscore = s.get("score", 7)
        
        if fscore >= 8:
            icon = "✅"
        elif fscore >= 6:
            icon = "⚠️"
        else:
            icon = "❌"
        
        lines.append(f"- {icon} **{fname}**: {fscore}/10")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Full detailed review saved to repository.*")
    
    return "\n".join(lines)