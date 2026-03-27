"""Tests for GitHub webhook verification and parsing."""

import pytest
from github_integration.webhook import verify_webhook_signature, parse_webhook_payload


class TestVerifyWebhookSignature:
    """Test cases for webhook signature verification."""

    def test_valid_signature(self):
        """Test that a valid HMAC-SHA256 signature passes verification."""
        import hmac
        import hashlib

        payload = b'{"action": "opened"}'
        secret = "test_secret"

        signature = (
            "sha256="
            + hmac.new(
                key=secret.encode("utf-8"),
                msg=payload,
                digestmod=hashlib.sha256,
            ).hexdigest()
        )

        result = verify_webhook_signature(payload, signature, secret)
        assert result is True

    def test_invalid_signature(self):
        """Test that an invalid signature fails verification."""
        payload = b'{"action": "opened"}'
        secret = "test_secret"

        result = verify_webhook_signature(payload, "sha256=invalid", secret)
        assert result is False

    def test_empty_signature(self):
        """Test that empty signature fails verification."""
        result = verify_webhook_signature(b"{}", "", "secret")
        assert result is False

    def test_missing_sha256_prefix(self):
        """Test that signature without sha256= prefix fails."""
        result = verify_webhook_signature(b"{}", "abc123", "secret")
        assert result is False

    def test_wrong_secret(self):
        """Test that signature with wrong secret fails."""
        import hmac
        import hashlib

        payload = b'{"action": "opened"}'
        correct_secret = "correct_secret"
        wrong_secret = "wrong_secret"

        signature = (
            "sha256="
            + hmac.new(
                key=correct_secret.encode("utf-8"),
                msg=payload,
                digestmod=hashlib.sha256,
            ).hexdigest()
        )

        result = verify_webhook_signature(payload, signature, wrong_secret)
        assert result is False


class TestParseWebhookPayload:
    """Test cases for parsing GitHub webhook payloads."""

    def test_valid_opened_payload(self):
        """Test parsing a valid PR opened payload."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "html_url": "https://github.com/owner/repo/pull/123",
            },
            "repository": {
                "name": "repo",
                "owner": {"login": "owner"},
            },
        }

        result = parse_webhook_payload(payload)

        assert result is not None
        assert result["repo_owner"] == "owner"
        assert result["repo_name"] == "repo"
        assert result["pr_number"] == 123
        assert result["action"] == "opened"

    def test_valid_synchronize_payload(self):
        """Test parsing a valid PR synchronize (push) payload."""
        payload = {
            "action": "synchronize",
            "pull_request": {
                "number": 456,
                "html_url": "https://github.com/user/myproject/pull/456",
            },
            "repository": {
                "name": "myproject",
                "owner": {"login": "user"},
            },
        }

        result = parse_webhook_payload(payload)

        assert result is not None
        assert result["action"] == "synchronize"
        assert result["pr_number"] == 456

    def test_ignored_closed_action(self):
        """Test that closed PRs are ignored."""
        payload = {
            "action": "closed",
            "pull_request": {"number": 123},
            "repository": {"name": "repo", "owner": {"login": "owner"}},
        }

        result = parse_webhook_payload(payload)
        assert result is None

    def test_ignored_other_actions(self):
        """Test that other PR actions are ignored."""
        for action in ["reopened", "labeled", "assigned"]:
            payload = {
                "action": action,
                "pull_request": {"number": 123},
                "repository": {"name": "repo", "owner": {"login": "owner"}},
            }

            result = parse_webhook_payload(payload)
            assert result is None, f"Action '{action}' should be ignored"

    def test_missing_pull_request(self):
        """Test handling of payload without pull_request key."""
        payload = {
            "action": "opened",
            "repository": {"name": "repo", "owner": {"login": "owner"}},
        }

        result = parse_webhook_payload(payload)
        assert result is None

    def test_missing_repository(self):
        """Test handling of payload without repository key."""
        payload = {
            "action": "opened",
            "pull_request": {"number": 123},
        }

        result = parse_webhook_payload(payload)
        assert result is None

    def test_missing_owner_login(self):
        """Test handling of repository without owner login."""
        payload = {
            "action": "opened",
            "pull_request": {"number": 123, "html_url": "http://example.com"},
            "repository": {"name": "repo"},
        }

        result = parse_webhook_payload(payload)
        assert result is None
