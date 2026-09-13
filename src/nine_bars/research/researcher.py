"""Web-backed coffee researcher: fetch → extract → synthesize, gracefully offline."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

import httpx

from nine_bars.adapters.researcher_stub import ResearcherStub
from nine_bars.domain.models import CoffeeQuery, CoffeeResearch
from nine_bars.research.extract import strip_html_to_text, synthesize_coffee
from nine_bars.research.extractor import FactExtractor, NoopFactExtractor

logger = logging.getLogger(__name__)

type _Fetcher = Callable[[str], Awaitable[str]]

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _validated_url(text: str) -> str | None:
    url = text.strip()
    if not url:
        return None
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return url


def _resolve_url(query: CoffeeQuery) -> str | None:
    """Return the page URL to fetch, or ``None`` when the query is not a URL.

    Free text and names are never interpreted as URLs; only an explicit
    ``kind="url"`` query triggers a fetch.
    """
    if query.kind == "url":
        return _validated_url(query.text)
    return None


def _short(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


async def _http_fetch(url: str, timeout: float) -> str:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=_BROWSER_HEADERS) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


class WebResearcher:
    """Implements :class:`CoffeeResearcher` by fetching and extracting roaster pages.

    When no extractor is configured, or any fetch/extract step fails, it degrades
    to the no-fabrication stub and never raises.
    """

    def __init__(
        self,
        extractor: FactExtractor | None = None,
        fetch: _Fetcher | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._extractor: FactExtractor = extractor or NoopFactExtractor()
        self._fetch = fetch
        self._timeout = timeout
        self._stub = ResearcherStub()

    async def lookup(self, query: CoffeeQuery) -> CoffeeResearch:
        url = _resolve_url(query)
        if url is None:
            return await self._stub.lookup(query)
        try:
            html = await self._fetch_page(url)
            text = strip_html_to_text(html)
            if not text:
                return await self._stub.lookup(query)
            extraction = await self._extractor.extract(text, url)
        except Exception as exc:
            logger.warning("research failed for %s: %s", _short(query.text), exc)
            return await self._stub.lookup(query)
        coffee = synthesize_coffee(query, extraction)
        return CoffeeResearch(evidence=coffee.evidence, coffee=coffee)

    async def _fetch_page(self, url: str) -> str:
        if self._fetch is not None:
            return await self._fetch(url)
        return await _http_fetch(url, self._timeout)
