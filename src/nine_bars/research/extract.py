"""Pure text and evidence helpers for coffee research (no I/O)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html.parser import HTMLParser

from nine_bars.domain.models import Coffee, CoffeeQuery, EvidenceItem


@dataclass(frozen=True, slots=True)
class Extraction:
    """Structured facts extracted from a single roaster page.

    ``facts`` holds sourced statements (``source="web"``, each carrying the page
    URL). The remaining fields mirror ``Coffee`` and are populated only from
    those facts, never invented.
    """

    facts: tuple[EvidenceItem, ...] = ()
    name: str | None = None
    roaster: str | None = None
    origin: str | None = None
    process: str | None = None
    roast_level: str | None = None
    roast_date: str | None = None
    tasting_notes: tuple[str, ...] = ()


_SKIPPED_TAGS = frozenset({"script", "style", "noscript", "head", "template"})

_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "tr",
        "dt",
        "dd",
        "td",
        "th",
        "article",
        "section",
        "header",
        "footer",
        "table",
        "dl",
        "ul",
        "ol",
        "br",
    }
)


class _TextExtractor(HTMLParser):
    """Collect the visible text of an HTML document, skipping non-content tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._chunks.append(data)

    @property
    def text(self) -> str:
        return " ".join("".join(self._chunks).split())


def strip_html_to_text(html: str) -> str:
    """Return the visible text of ``html`` with entities decoded and whitespace collapsed."""
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def dedupe_evidence(items: Sequence[EvidenceItem]) -> tuple[EvidenceItem, ...]:
    """Drop repeated ``(url, text)`` evidence, preserving first-seen order."""
    seen: set[tuple[str | None, str]] = set()
    result: list[EvidenceItem] = []
    for item in items:
        key = (item.url, _normalize(item.text))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


def slug(text: str) -> str:
    """Return a stable id slug for ``text``."""
    return "-".join(text.lower().split())


def _unique_sources(facts: Sequence[EvidenceItem]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.url for item in facts if item.url is not None))


def synthesize_coffee(query: CoffeeQuery, extraction: Extraction) -> Coffee:
    """Build a ``Coffee`` from extracted facts, never fabricating missing fields."""
    facts = dedupe_evidence(extraction.facts)
    name = extraction.name or query.text
    return Coffee(
        coffee_id=slug(name),
        name=name,
        roaster=extraction.roaster,
        origin=extraction.origin,
        process=extraction.process,
        roast_level=extraction.roast_level,
        roast_date=extraction.roast_date,
        tasting_notes=tuple(extraction.tasting_notes),
        sources=_unique_sources(facts),
        evidence=facts,
    )
