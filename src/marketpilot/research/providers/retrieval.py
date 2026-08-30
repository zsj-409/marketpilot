"""Web page retrieval and text extraction."""

import ipaddress
from abc import ABC, abstractmethod
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from marketpilot.research.canonicalization import canonicalize_url, content_hash
from marketpilot.research.errors import (
    ContentTooLargeError,
    InvalidSourceURLError,
    RetrievalHTTPError,
    RetrievalTimeoutError,
    UnsupportedContentTypeError,
)
from marketpilot.research.models import RetrievedPage
from marketpilot.research.normalization import normalize_text


class PageRetriever(ABC):
    """Provider-neutral page retrieval interface."""

    @abstractmethod
    async def retrieve(self, url: str) -> RetrievedPage:
        """Fetch and normalize one page."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def _extract_title(html: str) -> str | None:
    marker = "<title"
    lower = html.lower()
    start = lower.find(marker)
    if start < 0:
        return None
    end = lower.find("</title>", start)
    if end < 0:
        return None
    return html[start:end].split(">", 1)[-1].strip()[:1000]


def _is_public_url(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        return False
    host = parts.hostname
    if host is None:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host != "localhost" and not host.endswith(".local")
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )


class HTTPPageRetriever(PageRetriever):
    """Read-only HTTP page retriever with size, type, and host safety checks."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_bytes: int = 1_000_000,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._transport = transport

    async def retrieve(self, url: str) -> RetrievedPage:
        if not _is_public_url(url):
            raise InvalidSourceURLError(f"unsupported or private URL: {url}")
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RetrievalTimeoutError(f"page retrieval timed out: {url}") from exc
        except httpx.HTTPStatusError as exc:
            raise RetrievalHTTPError(f"HTTP {exc.response.status_code} for {url}") from exc
        except httpx.HTTPError as exc:
            raise RetrievalHTTPError(f"page retrieval failed: {exc}") from exc

        content_type = response.headers.get("content-type", "text/html").split(";")[0].lower()
        if "html" not in content_type and "text" not in content_type:
            raise UnsupportedContentTypeError(f"unsupported content type: {content_type}")
        raw = response.content
        if len(raw) > self._max_bytes:
            raise ContentTooLargeError(f"page exceeds {self._max_bytes} bytes")
        html = raw.decode("utf-8", errors="replace")
        extractor = _TextExtractor()
        try:
            extractor.feed(html)
            extractor.close()
        except Exception:
            pass
        text = normalize_text("\n".join(extractor.parts))
        canonical = canonicalize_url(str(response.url))
        return RetrievedPage(
            url=url,
            canonical_url=canonical,
            title=_extract_title(html),
            normalized_text=text,
            content_type=content_type,
            content_hash=content_hash(text),
            metadata={"provider": "http"},
        )
