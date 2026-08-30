"""Research provider adapter tests."""

import httpx
import pytest

from marketpilot.research.errors import ContentTooLargeError, UnsupportedContentTypeError
from marketpilot.research.providers.retrieval import HTTPPageRetriever
from marketpilot.research.providers.search import TavilySearchProvider


async def test_tavily_search_normalization() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Pet feeder trends",
                        "url": "https://example.com/a",
                        "content": "demand rising",
                    }
                ]
            },
            request=request,
        )

    provider = TavilySearchProvider(
        api_key="fake-key",
        transport=httpx.MockTransport(handler),
    )
    results = await provider.search("pet feeder", 3)
    assert results[0].title == "Pet feeder trends"
    assert results[0].url == "https://example.com/a"


async def test_http_page_retrieval_extracts_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "<html><title>Hello</title><body>"
                "<p>Automatic pet feeder demand rising.</p></body></html>"
            ),
            headers={"content-type": "text/html"},
            request=request,
        )

    retriever = HTTPPageRetriever(transport=httpx.MockTransport(handler))
    page = await retriever.retrieve("https://example.com/pet-feeders")
    assert page.title == "Hello"
    assert "Automatic pet feeder" in page.normalized_text


async def test_unsupported_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"x", headers={"content-type": "application/pdf"}, request=request
        )

    retriever = HTTPPageRetriever(transport=httpx.MockTransport(handler))
    with pytest.raises(UnsupportedContentTypeError):
        await retriever.retrieve("https://example.com/a")


async def test_content_too_large() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"a" * 1000, headers={"content-type": "text/html"}, request=request
        )

    retriever = HTTPPageRetriever(transport=httpx.MockTransport(handler), max_bytes=100)
    with pytest.raises(ContentTooLargeError):
        await retriever.retrieve("https://example.com/a")
