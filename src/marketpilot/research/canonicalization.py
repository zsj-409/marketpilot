"""Deterministic URL canonicalization and hashing."""

import hashlib
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "igshid",
}


def canonicalize_url(url: str) -> str:
    """Normalize a URL deterministically without dropping meaningful query params."""

    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    hostname = parts.hostname or ""
    port = parts.port
    default_port = 443 if scheme == "https" else 80 if scheme == "http" else None
    host = f"{hostname}:{port}" if port is not None and port != default_port else hostname
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS
    ]
    query = urlencode(query_items)
    return urlunsplit(SplitResult(scheme, host, path, query, ""))


def content_hash(text: str) -> str:
    """Return a deterministic SHA-256 hash for normalized content."""

    return hashlib.sha256(text.encode()).hexdigest()


def request_hash(parts: list[str]) -> str:
    """Return a stable hash for a research request key."""

    return hashlib.sha256("\n".join(parts).encode()).hexdigest()
