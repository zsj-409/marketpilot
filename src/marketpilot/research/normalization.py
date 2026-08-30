"""Deterministic text normalization."""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str, max_length: int = 200000) -> str:
    """Normalize Unicode, line endings, and whitespace, then bound length."""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _WHITESPACE.sub(" ", normalized)
    normalized = normalized.strip()
    return normalized[:max_length]
