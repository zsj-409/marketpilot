"""Secret-handling security tests."""

from marketpilot.llm.errors import sanitize_message


def test_sanitize_message_removes_secret() -> None:
    message = "bad request super-secret-test-key while calling"
    sanitized = sanitize_message(message, ["super-secret-test-key"])
    assert "super-secret-test-key" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_message_handles_empty_secrets() -> None:
    message = "plain error"
    assert sanitize_message(message, [""]) == message
