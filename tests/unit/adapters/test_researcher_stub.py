"""Tests for ResearcherStub."""

import asyncio

from nine_bars.adapters.researcher_stub import ResearcherStub
from nine_bars.domain.models import CoffeeQuery


def test_lookup_returns_empty_evidence() -> None:
    result = asyncio.run(ResearcherStub().lookup(CoffeeQuery(text="Ethiopia")))

    assert result.evidence == ()


def test_lookup_never_fabricates_sources() -> None:
    result = asyncio.run(ResearcherStub().lookup(CoffeeQuery(text="Ethiopia")))

    assert result.coffee.roaster is None
    assert result.coffee.origin is None
    assert result.coffee.sources == ()
