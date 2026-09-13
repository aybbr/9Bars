"""Generate the demo shot fixtures.

The two demo shots are defined once here and written in two formats so every
replay path (``FixtureShotSource`` parquet in #4, ``FixtureTransport``
``.slog``/``.idx`` in #5) serves identical data.

The shots tell a physically-plausible dial-in story: shot #1042 over-extracts
(yield 45 g, a late pressure drop + flow spike → channeling "indicated"), and
shot #1043 is the corrected pull (yield 36 g, coupled pressure/flow →
"unconfirmed").
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from nine_bars.domain.models import Coffee, EvidenceItem, Sample, ShotTelemetry
from nine_bars.domain.physics import curve_duration_ms
from nine_bars.mcp.binary import pack_index, write_slog
from nine_bars.mcp.types import IndexEntry

BASELINE_NAME = "shot_1_baseline"
CORRECTED_NAME = "shot_2_corrected"
DEMO_COFFEE_ID = "bonanza-finca-los-pirineos"
DEMO_MACHINE_REF = "Gaggiuino v4 · Gaggia Classic Pro E24"

BASELINE_SHOT_ID = "1042"
CORRECTED_SHOT_ID = "1043"

# A plausible example coffee for the offline demo (not a verified research fact).
DEMO_COFFEE = Coffee(
    coffee_id=DEMO_COFFEE_ID,
    name="Finca Los Pirineos",
    roaster="Bonanza Coffee Roasters",
    origin="El Salvador — Usulután",
    process="Washed",
    roast_level="Light",
    roast_date="2026-08-28",
    tasting_notes=("red apple", "honey", "floral"),
    sources=("https://www.bonanzacoffee.de/",),
    evidence=(
        EvidenceItem(
            source="web",
            url="https://www.bonanzacoffee.de/",
            text="Washed process from Finca Los Pirineos on the Tecapa volcano.",
            confidence=0.9,
        ),
        EvidenceItem(
            source="web",
            url="https://www.bonanzacoffee.de/",
            text="Tasting notes: red apple, honey, floral.",
            confidence=0.9,
        ),
    ),
)


def demo_coffee_dict() -> dict[str, object]:
    """Return the demo coffee in the shape the ``research_coffee`` tool returns."""
    return {
        "name": DEMO_COFFEE.name,
        "roaster": DEMO_COFFEE.roaster,
        "origin": DEMO_COFFEE.origin,
        "process": DEMO_COFFEE.process,
        "roast_level": DEMO_COFFEE.roast_level,
        "roast_date": DEMO_COFFEE.roast_date,
        "tasting_notes": list(DEMO_COFFEE.tasting_notes),
        "sources": list(DEMO_COFFEE.sources),
        "evidence": [
            {"source": item.source, "url": item.url, "text": item.text, "confidence": item.confidence}
            for item in DEMO_COFFEE.evidence
        ],
    }


def baseline_shot() -> ShotTelemetry:
    """Return the baseline demo shot (over-extracted, dry/harsh finish)."""
    times = _sample_times(32.0)
    return ShotTelemetry(
        shot_id=BASELINE_SHOT_ID,
        machine_ref=DEMO_MACHINE_REF,
        coffee_id=DEMO_COFFEE_ID,
        dose_in_g=18.0,
        dose_out_g=45.0,
        pressure_curve=_interp(
            times,
            [(0, 0), (2, 0), (6, 3.0), (10, 9.0), (26, 9.0), (32, 6.0)],
        ),
        flow_curve=_interp(
            times,
            [(0, 0), (4, 0), (8, 1.5), (16, 2.3), (26, 2.2), (32, 3.2)],
        ),
        temperature_curve=_interp(times, [(0, 93.0), (32, 92.4)]),
        weight_curve=_interp(
            times,
            [(0, 0), (4, 0), (10, 8), (20, 24), (28, 39), (32, 45)],
        ),
    )


def corrected_shot() -> ShotTelemetry:
    """Return the corrected demo shot (yield cut to 36 g, coupled curves)."""
    times = _sample_times(27.0)
    return ShotTelemetry(
        shot_id=CORRECTED_SHOT_ID,
        machine_ref=DEMO_MACHINE_REF,
        coffee_id=DEMO_COFFEE_ID,
        dose_in_g=18.0,
        dose_out_g=36.0,
        pressure_curve=_interp(
            times,
            [(0, 0), (2, 0), (6, 3.0), (10, 9.0), (27, 8.2)],
        ),
        flow_curve=_interp(
            times,
            [(0, 0), (4, 0), (8, 1.4), (14, 2.2), (20, 2.1), (27, 1.4)],
        ),
        temperature_curve=_interp(times, [(0, 92.5), (27, 92.6)]),
        weight_curve=_interp(
            times,
            [(0, 0), (4, 0), (10, 6), (18, 20), (24, 32), (27, 36)],
        ),
    )


def write_demo_fixtures(directory: Path) -> tuple[Path, Path]:
    """Write the two demo parquet fixtures and return their paths."""
    directory.mkdir(parents=True, exist_ok=True)
    baseline_path = directory / f"{BASELINE_NAME}.parquet"
    corrected_path = directory / f"{CORRECTED_NAME}.parquet"
    _write_shot(baseline_path, baseline_shot())
    _write_shot(corrected_path, corrected_shot())
    return baseline_path, corrected_path


def write_demo_slog_fixtures(directory: Path) -> tuple[Path, Path, Path]:
    """Write the two demo ``.slog`` shots plus their ``index.idx``."""
    directory.mkdir(parents=True, exist_ok=True)
    shots = (baseline_shot(), corrected_shot())
    shot_paths = [directory / f"{shot.shot_id}.slog" for shot in shots]
    entries: list[IndexEntry] = []
    for i, (shot, path) in enumerate(zip(shots, shot_paths, strict=True)):
        path.write_bytes(write_slog(shot))
        entries.append(
            IndexEntry(
                shot_id=shot.shot_id, timestamp_ms=i * 30_000, duration_ms=curve_duration_ms(shot.pressure_curve)
            )
        )
    index_path = directory / "index.idx"
    index_path.write_bytes(pack_index(entries))
    return shot_paths[0], shot_paths[1], index_path


def _sample_times(duration: float, dt: float = 0.5) -> list[float]:
    # 0.5 s is exactly representable and matches the binary format's uniform
    # time grid, so the fixtures round-trip byte-for-byte through write_slog.
    return [round(i * dt, 2) for i in range(int(duration / dt) + 1)]


def _interp(times: list[float], points: list[tuple[float, float]]) -> tuple[Sample, ...]:
    points = sorted(points)
    result: list[Sample] = []
    i = 0
    for t in times:
        while i < len(points) - 1 and points[i + 1][0] <= t:
            i += 1
        t0, v0 = points[i]
        t1, v1 = points[min(i + 1, len(points) - 1)]
        value = v0 if t1 <= t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        result.append((t, round(value, 2)))
    return tuple(result)


def _unzip(curve: tuple[Sample, ...]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not curve:
        return (), ()
    return tuple(sample[0] for sample in curve), tuple(sample[1] for sample in curve)


def _write_shot(path: Path, shot: ShotTelemetry) -> None:
    times, pressures = _unzip(shot.pressure_curve)
    _, flows = _unzip(shot.flow_curve)
    _, temps = _unzip(shot.temperature_curve)
    _, weights = _unzip(shot.weight_curve)

    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE shot AS SELECT * FROM (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) "
            "t(shot_id, machine_ref, coffee_id, dose_in_g, dose_out_g, t, pressure, flow, temperature, weight)",
            [
                shot.shot_id,
                shot.machine_ref,
                shot.coffee_id,
                shot.dose_in_g,
                shot.dose_out_g,
                list(times),
                list(pressures),
                list(flows),
                list(temps),
                list(weights),
            ],
        )
        con.table("shot").write_parquet(str(path))
