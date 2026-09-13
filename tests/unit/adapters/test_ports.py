"""Tests that concrete adapters satisfy their Protocols structurally."""

from nine_bars.adapters.duckdb_brewlog import DuckDBBrewLog
from nine_bars.adapters.fixture_shot_source import FixtureShotSource
from nine_bars.adapters.ports import BrewLog, CoffeeResearcher, ShotSource
from nine_bars.adapters.researcher_stub import ResearcherStub
from nine_bars.research.researcher import WebResearcher


def test_fixture_shot_source_satisfies_shot_source(tmp_path) -> None:
    assert isinstance(FixtureShotSource(tmp_path), ShotSource)


def test_duckdb_brewlog_satisfies_brewlog(tmp_path) -> None:
    assert isinstance(DuckDBBrewLog(tmp_path / "b.duckdb"), BrewLog)


def test_researcher_stub_satisfies_researcher() -> None:
    assert isinstance(ResearcherStub(), CoffeeResearcher)


def test_web_researcher_satisfies_researcher() -> None:
    assert isinstance(WebResearcher(), CoffeeResearcher)
