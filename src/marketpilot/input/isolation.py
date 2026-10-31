"""Untrusted external content isolation (Phase 1).

External research content (web pages, search snippets, LLM tool observations)
is untrusted. These helpers detect common prompt-injection signals and
sanitize text before it is placed into prompts, evidence, or memory. They are
deterministic and offline.
"""

import re

from pydantic import BaseModel, ConfigDict, Field


class InjectionSignal(BaseModel):
    """One detected prompt-injection / untrusted-content signal."""

    model_config = ConfigDict(frozen=True)

    signal: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=20)  # info | warning | danger
    snippet: str = Field(default="", max_length=300)


_IGNORE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ignore previous instructions", "danger"),
    ("ignore all previous", "danger"),
    ("disregard previous", "danger"),
    ("forget everything above", "warning"),
    ("you are now", "warning"),
    ("act as system", "warning"),
    ("system prompt", "info"),
    ("<system>", "warning"),
    ("</system>", "warning"),
    ("<|im_start|>", "info"),
    ("<|im_end|>", "info"),
    ("<|endoftext|>", "info"),
    ("new instructions", "info"),
    ("override", "info"),
    ("exfiltrate", "danger"),
    ("send to", "info"),
    ("api key", "info"),
    ("secret", "info"),
    ("password", "info"),
)

# Max length of sanitized text kept for prompting (bound untrusted payloads).
_MAX_SAFE_LENGTH = 8000


def scan_injection_signals(text: str) -> list[InjectionSignal]:
    """Detect common prompt-injection markers in untrusted text."""
    if not text:
        return []
    lowered = text.lower()
    signals: list[InjectionSignal] = []
    for pattern, severity in _IGNORE_PATTERNS:
        index = lowered.find(pattern)
        if index >= 0:
            start = max(0, index - 40)
            end = min(len(text), index + len(pattern) + 40)
            signals.append(
                InjectionSignal(
                    signal=pattern,
                    severity=severity,
                    snippet=text[start:end].replace("\n", " ")[:300],
                )
            )
    return signals


def sanitize_untrusted_text(
    text: str,
    *,
    max_length: int = _MAX_SAFE_LENGTH,
    quarantine_markers: bool = True,
) -> str:
    """Return a bounded, normalized copy of untrusted text.

    Never includes the untrusted content verbatim beyond the bound; strips
    control characters; optionally replaces injection markers with a neutral
    placeholder so the text cannot carry instruction text into a prompt.
    """
    if not text:
        return ""
    cleaned = text.replace("\x00", "").replace("\r", " ")
    # Collapse whitespace to avoid carrying hidden formatting.
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned[:max_length]
    if quarantine_markers:
        for pattern, _severity in _IGNORE_PATTERNS:
            cleaned = re.sub(re.escape(pattern), "[quarantined-content]", cleaned, flags=re.I)
    return cleaned.strip()
