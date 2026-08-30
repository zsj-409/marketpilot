"""Deduplication tests."""

from marketpilot.research.dedup import SourceDeduplicator


def test_same_canonical_url_is_duplicate() -> None:
    dedup = SourceDeduplicator()
    dedup.record("s1", "https://example.com/a", "hello world content")
    assert dedup.check("https://example.com/a", "different content").duplicate


def test_same_content_hash_is_duplicate() -> None:
    dedup = SourceDeduplicator()
    dedup.record("s1", "https://example.com/a", "same body text")
    assert dedup.check("https://example.com/b", "same body text").duplicate


def test_near_duplicate_detected() -> None:
    dedup = SourceDeduplicator()
    text = "automatic pet feeder demand rising battery reliability complaint"
    dedup.record("s1", "https://example.com/a", text)
    result = dedup.check("https://example.com/b", text + " extra")
    assert result.near_duplicate


def test_distinct_pages_are_not_duplicates() -> None:
    dedup = SourceDeduplicator()
    dedup.record("s1", "https://example.com/a", "one two three four five")
    result = dedup.check("https://example.com/b", "different topic entirely here")
    assert not result.duplicate
    assert not result.near_duplicate
