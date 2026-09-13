"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nine_bars.adapters.device_profile_writer import DeviceProfileWriter
from nine_bars.adapters.duckdb_brewlog import DuckDBBrewLog
from nine_bars.adapters.fixture_shot_source import FixtureShotSource
from nine_bars.api.dependencies import Dependencies
from nine_bars.domain.models import GAGGIAMATE
from nine_bars.events.bus import EventBus
from nine_bars.fixtures.generate import write_demo_fixtures, write_demo_slog_fixtures
from nine_bars.main import create_app
from nine_bars.mcp.transports import FixtureTransport
from nine_bars.research.researcher import WebResearcher


def build_deps(tmp_path: Path) -> Dependencies:
    write_demo_fixtures(tmp_path)
    write_demo_slog_fixtures(tmp_path)
    return Dependencies(
        brew_log=DuckDBBrewLog(tmp_path / "brew.duckdb"),
        shot_source=FixtureShotSource(tmp_path),
        profile_writer=DeviceProfileWriter(FixtureTransport(tmp_path), GAGGIAMATE),
        researcher=WebResearcher(),
        event_bus=EventBus(),
    )


@pytest.fixture
def deps(tmp_path: Path) -> Dependencies:
    return build_deps(tmp_path)


@pytest.fixture
def client(deps: Dependencies) -> TestClient:
    return TestClient(create_app(deps))


@pytest.fixture
def web_fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "web"
