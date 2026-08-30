"""URL canonicalization and hashing tests."""

from marketpilot.research.canonicalization import (
    canonicalize_url,
    content_hash,
    request_hash,
)


def test_fragment_and_default_port_removed() -> None:
    assert canonicalize_url("HTTPS://Example.com:443/path/#frag") == "https://example.com/path"


def test_tracking_params_removed_but_meaningful_query_preserved() -> None:
    assert (
        canonicalize_url("https://example.com/a?utm_source=x&page=2")
        == "https://example.com/a?page=2"
    )


def test_trailing_slash_normalized() -> None:
    assert canonicalize_url("https://example.com/a/") == "https://example.com/a"


def test_hashes_are_deterministic() -> None:
    assert content_hash("hello") == content_hash("hello")
    assert request_hash(["a", "b"]) == request_hash(["a", "b"])
