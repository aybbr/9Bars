"""Tests for DuckDBBrewLog persistence."""

import asyncio

import duckdb

from nine_bars.adapters.duckdb_brewlog import DuckDBBrewLog
from nine_bars.domain.models import (
    ChangedVariable,
    Coffee,
    ExtractionProfile,
    NextAction,
    PhaseSettings,
    ProfileDraft,
    ShotSummary,
    TasteFeedback,
)


def _run(coro):
    return asyncio.run(coro)


def _shot(shot_id: str, coffee_id: str = "c1") -> ShotSummary:
    return ShotSummary(
        shot_id=shot_id,
        coffee_id=coffee_id,
        machine_ref="gm-1",
        dose_in_g=18.0,
        dose_out_g=36.0,
        peak_pressure_bar=9.0,
        avg_temp_c=93.0,
        brew_ratio=2.0,
        duration_s=30.0,
    )


def _action(variable: ChangedVariable, proposed_value: float | str) -> NextAction:
    return NextAction(
        changed_variable=variable,
        current_value="current",
        proposed_value=proposed_value,
        rationale="reason",
        confidence=0.6,
    )


def test_shot_round_trips(tmp_path) -> None:
    log = DuckDBBrewLog(tmp_path / "b.duckdb")
    shot = _shot("s1")

    _run(log.save_shot(shot))

    assert _run(log.shots_for_coffee("c1")) == [shot]


def test_shots_filter_by_coffee(tmp_path) -> None:
    log = DuckDBBrewLog(tmp_path / "b.duckdb")

    _run(log.save_shot(_shot("s1", coffee_id="c1")))
    _run(log.save_shot(_shot("s2", coffee_id="c2")))

    assert [s.shot_id for s in _run(log.shots_for_coffee("c1"))] == ["s1"]


def test_next_action_round_trips(tmp_path) -> None:
    log = DuckDBBrewLog(tmp_path / "b.duckdb")
    action = _action(ChangedVariable.GRIND, "finer")

    _run(log.save_next_action("c1", action))

    assert _run(log.next_actions("c1")) == [action]


def test_next_actions_preserve_insertion_order(tmp_path) -> None:
    log = DuckDBBrewLog(tmp_path / "b.duckdb")
    first = _action(ChangedVariable.GRIND, "finer")
    second = _action(ChangedVariable.RATIO, 2.5)

    _run(log.save_next_action("c1", first))
    _run(log.save_next_action("c1", second))

    assert _run(log.next_actions("c1")) == [first, second]


def test_save_coffee_persists(tmp_path) -> None:
    db = tmp_path / "b.duckdb"
    log = DuckDBBrewLog(db)
    coffee = Coffee(
        coffee_id="c1",
        name="Ethiopia",
        roaster="R",
        tasting_notes=("berry", "citrus"),
        sources=("https://example.com",),
    )

    _run(log.save_coffee(coffee))

    with duckdb.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT coffee_id, name, roaster, tasting_notes FROM coffees WHERE coffee_id = 'c1'"
        ).fetchone()
    assert row == ("c1", "Ethiopia", "R", '["berry", "citrus"]')


def test_save_feedback_persists(tmp_path) -> None:
    db = tmp_path / "b.duckdb"
    log = DuckDBBrewLog(db)
    feedback = TasteFeedback(
        shot_id="s1",
        acidity=4,
        sweetness=2,
        body=3,
        overall=3,
        bitterness=2,
        aroma=4,
        finish=3,
        note="dry",
    )

    _run(log.save_feedback("s1", feedback))

    assert _run(log.get_feedback("s1")) == feedback

    with duckdb.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT shot_id, acidity, bitterness, aroma, finish, note FROM feedback WHERE shot_id = 's1'"
        ).fetchone()
    assert row == ("s1", 4, 2, 4, 3, "dry")


def test_feedback_migrates_legacy_schema(tmp_path) -> None:
    db = tmp_path / "b.duckdb"
    with duckdb.connect(str(db)) as conn:
        conn.execute(
            "CREATE TABLE feedback (shot_id VARCHAR PRIMARY KEY, acidity INTEGER, "
            "sweetness INTEGER, body INTEGER, overall INTEGER, note VARCHAR)"
        )
        conn.execute("INSERT INTO feedback VALUES ('legacy', 4, 2, 3, 3, 'old')")

    log = DuckDBBrewLog(db)

    legacy = _run(log.get_feedback("legacy"))
    assert legacy.note == "old"
    assert legacy.bitterness == 3
    assert legacy.aroma == 3
    assert legacy.finish == 3

    feedback = TasteFeedback(shot_id="s1", acidity=4, sweetness=2, body=3, overall=3, bitterness=1, aroma=5, finish=4)
    _run(log.save_feedback("s1", feedback))

    assert _run(log.get_feedback("s1")).bitterness == 1


def test_save_draft_persists(tmp_path) -> None:
    db = tmp_path / "b.duckdb"
    log = DuckDBBrewLog(db)
    draft = ProfileDraft(
        profile=ExtractionProfile(
            name="p1",
            dose_g=18.0,
            yield_g=36.0,
            ratio=2.0,
            temp_c=93.0,
            grind_desc="medium",
            phases=(PhaseSettings("hold", 9.0, 20.0),),
        ),
        rationale="baseline",
        assumptions=("fresh beans",),
    )

    _run(log.save_draft(draft))

    with duckdb.connect(str(db)) as conn:
        row = conn.execute("SELECT name, rationale FROM drafts WHERE name = 'p1'").fetchone()
    assert row == ("p1", "baseline")


def test_save_draft_does_not_overwrite_same_name(tmp_path) -> None:
    log = DuckDBBrewLog(tmp_path / "b.duckdb")
    profile = ExtractionProfile(name="p1", dose_g=18.0, yield_g=36.0, ratio=2.0, temp_c=93.0, grind_desc="m")

    _run(log.save_draft(ProfileDraft(profile=profile, rationale="first")))
    _run(log.save_draft(ProfileDraft(profile=profile, rationale="second")))

    with duckdb.connect(str(tmp_path / "b.duckdb")) as conn:
        count = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
    assert count == 2


def test_migrate_is_idempotent(tmp_path) -> None:
    db = tmp_path / "b.duckdb"
    log = DuckDBBrewLog(db)
    _run(log.save_shot(_shot("s1")))

    DuckDBBrewLog(db)

    assert [s.shot_id for s in _run(log.shots_for_coffee("c1"))] == ["s1"]
