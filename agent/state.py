"""LangGraph state schema for the AI Code Review Agent."""

import operator
from typing import Annotated, TypedDict


class FileReview(TypedDict):
    """Review data for a single file."""

    filename: str
    patch: str
    status: str
    lint_issues: list[dict]
    logic_issues: list[dict]
    fix_suggestions: list[dict]
    score: int
    score_justification: str


class AgentState(TypedDict):
    """Main state for the code review agent graph."""

    # Input
    pr_url: str

    # Parsed from URL
    repo_owner: str
    repo_name: str
    pr_number: int
    pr_title: str
    pr_body: str

    # Fetched from GitHub
    diff_text: str
    files: list[dict]

    # Review results
    lint_results: Annotated[list[dict], operator.add]
    logic_results: Annotated[list[dict], operator.add]
    fix_suggestions: Annotated[list[dict], operator.add]
    scores: Annotated[list[dict], operator.add]

    # Final output
    final_review: str
    overall_score: float
