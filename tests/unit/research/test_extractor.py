"""Tests for fact extractors (offline + prompt-backed)."""

import asyncio
import json

from nine_bars.research.extract import Extraction
from nine_bars.research.extractor import FactExtractor, NoopFactExtractor, PromptFactExtractor


def test_noop_extractor_returns_empty() -> None:
    result = asyncio.run(NoopFactExtractor().extract("anything", "https://x.co"))

    assert result == Extraction()


def test_noop_extractor_satisfies_protocol() -> None:
    assert isinstance(NoopFactExtractor(), FactExtractor)


def test_prompt_extractor_parses_valid_json() -> None:
    async def fake_complete(prompt: str) -> str:
        return json.dumps(
            {
                "name": "Ethiopia Guji Washed",
                "roaster": "The Barn",
                "origin": "Guji, Ethiopia",
                "process": "Washed",
                "roast_level": "Light",
                "roast_date": "2026-09-01",
                "tasting_notes": ["jasmine", "bergamot"],
                "facts": ["Roasted by The Barn", "Origin Guji, Ethiopia", "Washed process"],
            }
        )

    result = asyncio.run(PromptFactExtractor(fake_complete).extract("page", "https://example.com/coffee"))

    assert result.roaster == "The Barn"
    assert result.origin == "Guji, Ethiopia"
    assert result.tasting_notes == ("jasmine", "bergamot")
    assert len(result.facts) == 3
    assert all(item.source == "web" for item in result.facts)
    assert all(item.url == "https://example.com/coffee" for item in result.facts)


def test_prompt_extractor_always_attaches_url_to_web_facts() -> None:
    async def fake_complete(prompt: str) -> str:
        return '{"facts": ["one", "two"]}'

    result = asyncio.run(PromptFactExtractor(fake_complete).extract("x", "https://source.org"))

    assert all(item.url == "https://source.org" for item in result.facts)


def test_prompt_extractor_rejects_garbage() -> None:
    async def fake_complete(prompt: str) -> str:
        return "I'm sorry, I can't do that."

    result = asyncio.run(PromptFactExtractor(fake_complete).extract("x", "https://example.com"))

    assert result == Extraction()


def test_prompt_extractor_json_escapes_page_text() -> None:
    captured: list[str] = []

    async def fake_complete(prompt: str) -> str:
        captured.append(prompt)
        return "{}"

    page = 'line1\nline2 "quoted" \\ backslash'
    asyncio.run(PromptFactExtractor(fake_complete).extract(page, "https://example.com"))

    prompt = captured[0]
    assert "line1\\nline2" in prompt
    assert '\\"quoted\\"' in prompt
    assert "\\\\ backslash" in prompt


def test_prompt_extractor_tolerates_fenced_json() -> None:
    async def fake_complete(prompt: str) -> str:
        return '```json\n{"roaster": "Fence Roasters"}\n```'

    result = asyncio.run(PromptFactExtractor(fake_complete).extract("x", "https://example.com"))

    assert result.roaster == "Fence Roasters"
