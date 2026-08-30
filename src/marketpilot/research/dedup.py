"""Exact and near-duplicate detection for research sources."""

from dataclasses import dataclass

from marketpilot.research.canonicalization import content_hash
from marketpilot.research.normalization import normalize_text


@dataclass(frozen=True)
class DeduplicationResult:
    """Outcome of checking one source against the store."""

    duplicate: bool
    near_duplicate: bool
    duplicate_of: str | None


def _shingles(text: str, size: int = 5) -> set[str]:
    tokens = text.split()
    if len(tokens) < size:
        return {text}
    return {" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


class SourceDeduplicator:
    """Track canonical URLs and normalized content for duplicate detection."""

    def __init__(self, near_duplicate_threshold: float = 0.75) -> None:
        self._canonical_urls: dict[str, str] = {}
        self._content_hashes: dict[str, str] = {}
        self._shingle_sets: dict[str, set[str]] = {}
        self._threshold = near_duplicate_threshold

    def check(self, canonical_url: str, text: str) -> DeduplicationResult:
        digest = content_hash(text)
        if canonical_url in self._canonical_urls:
            return DeduplicationResult(True, False, self._canonical_urls[canonical_url])
        if digest in self._content_hashes:
            return DeduplicationResult(True, False, self._content_hashes[digest])

        current_shingles = _shingles(normalize_text(text))
        for source_id, existing in self._shingle_sets.items():
            if _jaccard(current_shingles, existing) >= self._threshold:
                return DeduplicationResult(False, True, source_id)
        return DeduplicationResult(False, False, None)

    def record(self, source_id: str, canonical_url: str, text: str) -> None:
        self._canonical_urls[canonical_url] = source_id
        self._content_hashes[content_hash(text)] = source_id
        self._shingle_sets[source_id] = _shingles(normalize_text(text))
