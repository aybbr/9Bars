"""A :class:`ShotSource` that serves the two committed demo shots in order."""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb

from nine_bars.domain.models import Sample, ShotSummary, ShotTelemetry
from nine_bars.domain.physics import summarize
from nine_bars.fixtures.generate import BASELINE_NAME, CORRECTED_NAME

_FIXTURE_NAMES = (BASELINE_NAME, CORRECTED_NAME)


class FixtureShotSource:
    """Serves ``shot_1_baseline`` then ``shot_2_corrected`` on successive calls.

    The progression is driven by an injectable counter, never the clock.
    """

    def __init__(self, fixture_dir: Path, counter: Iterator[int] | None = None) -> None:
        self._fixture_dir = fixture_dir
        self._counter = counter if counter is not None else itertools.count()

    async def latest_shot(self) -> ShotTelemetry | None:
        index = next(self._counter)
        if index >= len(_FIXTURE_NAMES):
            return None
        return await asyncio.to_thread(self._load, self._fixture_dir / f"{_FIXTURE_NAMES[index]}.parquet")

    async def get_shot(self, shot_id: str) -> ShotTelemetry:
        for name in _FIXTURE_NAMES:
            shot = await asyncio.to_thread(self._load, self._fixture_dir / f"{name}.parquet")
            if shot.shot_id == shot_id:
                return shot
        raise KeyError(f"unknown shot id: {shot_id}")

    async def history(self, coffee_id: str | None, limit: int) -> list[ShotSummary]:
        shots = await asyncio.to_thread(self._load_all)
        summaries = [summarize(shot) for shot in shots if coffee_id is None or shot.coffee_id == coffee_id]
        return summaries[:limit]

    def _load_all(self) -> list[ShotTelemetry]:
        return [self._load(self._fixture_dir / f"{name}.parquet") for name in _FIXTURE_NAMES]

    def _load(self, path: Path) -> ShotTelemetry:
        rows = duckdb.connect().execute("SELECT * FROM read_parquet(?)", [str(path)]).fetchall()
        return _row_to_shot(rows[0])


def _row_to_shot(row: tuple[Any, ...]) -> ShotTelemetry:
    shot_id, machine_ref, coffee_id, dose_in, dose_out, t, pressure, flow, temperature, weight = row
    return ShotTelemetry(
        shot_id=str(shot_id),
        machine_ref=str(machine_ref),
        coffee_id=str(coffee_id) if coffee_id is not None else None,
        dose_in_g=float(dose_in),
        dose_out_g=float(dose_out),
        pressure_curve=_zip_samples(t, pressure),
        flow_curve=_zip_samples(t, flow),
        temperature_curve=_zip_samples(t, temperature),
        weight_curve=_zip_samples(t, weight),
    )


def _zip_samples(times: Any, values: Any) -> tuple[Sample, ...]:
    return tuple((float(t), float(v)) for t, v in zip(times, values, strict=True))
