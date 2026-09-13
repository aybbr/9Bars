"""Tests for the MCP server tools."""

import asyncio
from pathlib import Path

from nine_bars.fixtures.generate import BASELINE_SHOT_ID, CORRECTED_SHOT_ID, write_demo_slog_fixtures
from nine_bars.mcp.protocols import DeviceTransport
from nine_bars.mcp.server import _analyze_shot, _get_shot, _list_shots, create_server
from nine_bars.mcp.transports import FixtureTransport


def _run(coro):
    return asyncio.run(coro)


def _transport(tmp_path: Path) -> DeviceTransport:
    write_demo_slog_fixtures(tmp_path)
    return FixtureTransport(tmp_path)


def test_server_exposes_three_read_only_tools(tmp_path: Path) -> None:
    server = create_server(_transport(tmp_path))

    names = sorted(tool.name for tool in asyncio.run(server.list_tools()))

    assert names == ["analyze_shot", "get_shot", "list_shots"]


def test_list_shots(tmp_path: Path) -> None:
    docs = _run(_list_shots(_transport(tmp_path), limit=10))

    assert [doc.shot_id for doc in docs] == [BASELINE_SHOT_ID, CORRECTED_SHOT_ID]


def test_get_shot(tmp_path: Path) -> None:
    doc = _run(_get_shot(_transport(tmp_path), CORRECTED_SHOT_ID))

    assert doc.shot_id == CORRECTED_SHOT_ID
    assert len(doc.pressure) == len(doc.flow) == len(doc.temperature) == len(doc.weight)


def test_analyze_shot(tmp_path: Path) -> None:
    doc = _run(_analyze_shot(_transport(tmp_path), BASELINE_SHOT_ID))

    assert doc.shot_id == BASELINE_SHOT_ID
    assert doc.channeling_strength in {"indicated", "suggestive", "unconfirmed"}
