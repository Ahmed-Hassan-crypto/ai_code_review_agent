"""Pydantic models for request/response validation."""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ReviewRequest(BaseModel):
    """Request model for triggering a code review."""

    pr_url: str = Field(..., description="GitHub Pull Request URL")


class ReviewResponse(BaseModel):
    """Response model for a completed review."""

    status: str = Field(..., description="Status of the review request")
    pr_url: str = Field(..., description="The PR URL that was reviewed")
    overall_score: float = Field(
        ..., ge=0, le=10, description="Overall quality score 0-10"
    )
    scores: list[dict] = Field(default_factory=list, description="Per-file scores")
    lint_results: list[dict] = Field(default_factory=list, description="Lint findings")
    logic_results: list[dict] = Field(
        default_factory=list, description="Security/logic findings"
    )
    fix_suggestions: list[dict] = Field(
        default_factory=list, description="Suggested fixes"
    )
    final_review: str = Field(default="", description="Formatted review in markdown")


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""

    status: str = Field(..., description="Status of the webhook processing")
    pr_url: Optional[str] = Field(None, description="PR URL if applicable")
    action: Optional[str] = Field(
        None, description="GitHub action that triggered webhook"
    )
    message: Optional[str] = Field(None, description="Additional message")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="API version")


class ErrorResponse(BaseModel):
    """Response model for error responses."""

    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Detailed error message")
    status_code: int = Field(..., description="HTTP status code")
