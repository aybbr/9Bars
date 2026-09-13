"""Tests for FixtureShotSource."""

import asyncio

import pytest

from nine_bars.adapters.fixture_shot_source import FixtureShotSource
from nine_bars.fixtures.generate import (
    BASELINE_SHOT_ID,
    CORRECTED_SHOT_ID,
    DEMO_COFFEE_ID,
    write_demo_fixtures,
)


def _run(coro):
    return asyncio.run(coro)


def test_latest_shot_returns_baseline_then_corrected(tmp_path) -> None:
    write_demo_fixtures(tmp_path)
    source = FixtureShotSource(tmp_path)

    first = _run(source.latest_shot())
    second = _run(source.latest_shot())

    assert first is not None and first.shot_id == BASELINE_SHOT_ID
    assert second is not None and second.shot_id == CORRECTED_SHOT_ID


def test_latest_shot_is_driven_by_injectable_counter(tmp_path) -> None:
    write_demo_fixtures(tmp_path)
    source = FixtureShotSource(tmp_path, counter=iter([1]))

    shot = _run(source.latest_shot())

    assert shot is not None and shot.shot_id == CORRECTED_SHOT_ID


def test_latest_shot_returns_none_when_exhausted(tmp_path) -> None:
    write_demo_fixtures(tmp_path)
    source = FixtureShotSource(tmp_path, counter=iter([2]))

    assert _run(source.latest_shot()) is None


def test_get_shot_by_id(tmp_path) -> None:
    write_demo_fixtures(tmp_path)
    source = FixtureShotSource(tmp_path)

    shot = _run(source.get_shot(CORRECTED_SHOT_ID))

    assert shot.shot_id == CORRECTED_SHOT_ID
    assert shot.dose_out_g == 36.0


def test_get_shot_unknown_raises_keyerror(tmp_path) -> None:
    write_demo_fixtures(tmp_path)
    source = FixtureShotSource(tmp_path)

    with pytest.raises(KeyError):
        _run(source.get_shot("nope"))


def test_history_returns_summaries_in_order(tmp_path) -> None:
    write_demo_fixtures(tmp_path)
    source = FixtureShotSource(tmp_path)

    history = _run(source.history(DEMO_COFFEE_ID, 10))

    assert [shot.shot_id for shot in history] == [BASELINE_SHOT_ID, CORRECTED_SHOT_ID]
