"""Fact extractors: turn roaster page text into sourced evidence (or nothing)."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from nine_bars.domain.models import EvidenceItem
from nine_bars.research.extract import Extraction


@runtime_checkable
class FactExtractor(Protocol):
    """Extracts sourced facts from a roaster page's visible text."""

    async def extract(self, text: str, url: str) -> Extraction: ...


class NoopFactExtractor:
    """Offline fallback: returns no facts and never fabricates a claim."""

    async def extract(self, text: str, url: str) -> Extraction:
        return Extraction()


_PROMPT = (
    "You are a coffee research assistant. Extract facts about a single coffee from a roaster page.\n"
    "Report ONLY facts explicitly stated in the page. If a field is absent, use null or an empty list.\n"
    "Never invent the roaster, origin, process, roast level, roast date, or tasting notes.\n"
    "Respond with a single JSON object and nothing else, using exactly this shape:\n"
    '{"name": string|null, "roaster": string|null, "origin": string|null, '
    '"process": string|null, "roast_level": string|null, "roast_date": string|null, '
    '"tasting_notes": [string], "facts": [string]}\n'
    "Each entry in `facts` must be a short statement copied from the page that supports a field.\n"
    "Page text:\n"
    "{page}"
)

_FENCED_JSON = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class PromptFactExtractor:
    """Constrained JSON extractor backed by an injected LLM completion."""

    def __init__(self, complete: Callable[[str], Awaitable[str]]) -> None:
        self._complete = complete

    async def extract(self, text: str, url: str) -> Extraction:
        prompt = _PROMPT.replace("{page}", json.dumps(text))
        raw = await self._complete(prompt)
        return _parse(raw, url)


def _parse(raw: str, url: str) -> Extraction:
    data = _extract_json(raw)
    if not isinstance(data, dict):
        return Extraction()
    facts = tuple(
        EvidenceItem(source="web", url=url, text=item.strip(), confidence=0.8)
        for item in _as_strings(data.get("facts"))
        if item.strip()
    )
    return Extraction(
        facts=facts,
        name=_optional_str(data.get("name")),
        roaster=_optional_str(data.get("roaster")),
        origin=_optional_str(data.get("origin")),
        process=_optional_str(data.get("process")),
        roast_level=_optional_str(data.get("roast_level")),
        roast_date=_optional_str(data.get("roast_date")),
        tasting_notes=tuple(item.strip() for item in _as_strings(data.get("tasting_notes")) if item.strip()),
    )


def _extract_json(raw: str) -> Any:
    fenced = _FENCED_JSON.search(raw)
    candidate = fenced.group(1) if fenced else raw
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        block = _JSON_BLOCK.search(candidate)
        if block is None:
            return None
        try:
            return json.loads(block.group(0))
        except json.JSONDecodeError:
            return None


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _as_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []
