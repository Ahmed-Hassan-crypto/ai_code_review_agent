"""Centralized configuration management for the AI Code Review Agent."""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GitHubConfig:
    """GitHub API configuration."""

    token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    webhook_secret: str = field(
        default_factory=lambda: os.getenv("GITHUB_WEBHOOK_SECRET", "")
    )

    @property
    def is_configured(self) -> bool:
        """Check if GitHub credentials are properly configured."""
        return bool(self.token and self.token != "your_github_token_here")


@dataclass
class GroqConfig:
    """Groq API configuration."""

    api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.1

    @property
    def is_configured(self) -> bool:
        """Check if Groq API key is configured."""
        return bool(self.api_key and self.api_key != "your_groq_api_key_here")


@dataclass
class AppConfig:
    """Application configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Get CORS allowed origins."""
        return self.cors_origins if self.cors_origins != ["*"] else ["*"]


@dataclass
class Config:
    """Main configuration container."""

    github: GitHubConfig = field(default_factory=GitHubConfig)
    groq: GroqConfig = field(default_factory=GroqConfig)
    app: AppConfig = field(default_factory=AppConfig)

    def validate(self) -> list[str]:
        """Validate configuration and return list of validation errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.groq.is_configured:
            errors.append("GROQ_API_KEY is not configured or is a placeholder")

        if not self.github.token:
            errors.append("GITHUB_TOKEN is not configured")
        elif self.github.token == "your_github_token_here":
            errors.append("GITHUB_TOKEN is still a placeholder value")

        return errors

    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


# Global config instance
config = Config()
