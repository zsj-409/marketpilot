"""Typed research and retrieval errors."""


class ResearchError(Exception):
    """Base class for normalized research errors."""


class SearchProviderError(ResearchError):
    """A search provider failed."""


class RetrievalTimeoutError(ResearchError):
    """Page retrieval timed out."""


class RetrievalHTTPError(ResearchError):
    """Page retrieval returned an HTTP failure."""


class UnsupportedContentTypeError(ResearchError):
    """Page content type is not supported."""


class ContentTooLargeError(ResearchError):
    """Page content exceeded the configured size limit."""


class InvalidSourceURLError(ResearchError):
    """A URL failed scheme or host safety validation."""


class ReplayMissError(ResearchError):
    """Replay mode could not find the requested recorded response."""


class ResearchBudgetExceededError(ResearchError):
    """A research budget limit was exceeded."""
