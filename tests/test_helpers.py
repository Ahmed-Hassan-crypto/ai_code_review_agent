"""Tests for the helper utilities."""

import pytest
from utils.helpers import truncate


class TestTruncate:
    """Test cases for the truncate utility function."""

    def test_short_text_unchanged(self):
        """Test that text under the limit is unchanged."""
        text = "Hello, World!"
        result = truncate(text, max_length=60000)
        assert result == text

    def test_exact_limit(self):
        """Test text at exactly the limit."""
        text = "a" * 60000
        result = truncate(text, max_length=60000)
        assert len(result) == 60000
        assert result == text

    def test_over_limit_truncated(self):
        """Test that text over the limit is truncated."""
        text = "a" * 100
        result = truncate(text, max_length=50)
        assert result.endswith("[TRUNCATED]")
        assert len(result) > 50
        assert len(result) < 100  # Should be shorter than original

    def test_custom_max_length(self):
        """Test truncation with custom max length."""
        text = "Hello, World! This is a longer text."
        result = truncate(text, max_length=10)
        assert "..." in result
        assert result.endswith("[TRUNCATED]")
        assert len(result) > 10

    def test_empty_string(self):
        """Test truncation of empty string."""
        result = truncate("", max_length=10)
        assert result == ""

    def test_exactly_max_plus_one(self):
        """Test text that is exactly max_length + 1."""
        text = "a" * 11
        result = truncate(text, max_length=10)
        assert result.endswith("[TRUNCATED]")
        assert len(result) > 10
