"""DuckDB-backed :class:`BrewLog` adapter.

All SQL lives in this module and nowhere else. Methods are async and offload
the synchronous DuckDB work to a worker thread so the event loop is never
blocked. Each operation uses a short-lived connection, so there is no shared
mutable connection or locking.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Literal, cast

import duckdb

from nine_bars.domain.models import (
    ChangedVariable,
    Coffee,
    EvidenceItem,
    ExtractionProfile,
    NextAction,
    PhaseSettings,
    ProfileDeployResult,
    ProfileDraft,
    ShotSummary,
    TasteFeedback,
)

_SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS coffees (
        coffee_id VARCHAR PRIMARY KEY,
        name VARCHAR NOT NULL,
        roaster VARCHAR,
        origin VARCHAR,
        process VARCHAR,
        roast_level VARCHAR,
        roast_date VARCHAR,
        tasting_notes VARCHAR NOT NULL DEFAULT '[]',
        sources VARCHAR NOT NULL DEFAULT '[]',
        evidence VARCHAR NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shots (
        shot_id VARCHAR PRIMARY KEY,
        coffee_id VARCHAR,
        machine_ref VARCHAR NOT NULL,
        dose_in_g DOUBLE NOT NULL,
        dose_out_g DOUBLE NOT NULL,
        peak_pressure_bar DOUBLE NOT NULL,
        avg_temp_c DOUBLE NOT NULL,
        brew_ratio DOUBLE NOT NULL,
        duration_s DOUBLE NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        shot_id VARCHAR PRIMARY KEY,
        acidity INTEGER,
        sweetness INTEGER,
        body INTEGER,
        overall INTEGER,
        bitterness INTEGER,
        aroma INTEGER,
        finish INTEGER,
        note VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS drafts (
        draft_id VARCHAR PRIMARY KEY,
        name VARCHAR,
        dose_g DOUBLE,
        yield_g DOUBLE,
        ratio DOUBLE,
        temp_c DOUBLE,
        grind_desc VARCHAR,
        phases VARCHAR NOT NULL DEFAULT '[]',
        rationale VARCHAR,
        assumptions VARCHAR NOT NULL DEFAULT '[]',
        evidence VARCHAR NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        event_id UUID PRIMARY KEY,
        event_type VARCHAR,
        coffee_id VARCHAR,
        payload VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deployments (
        draft_id VARCHAR PRIMARY KEY,
        profile_id VARCHAR NOT NULL,
        status VARCHAR NOT NULL,
        message VARCHAR,
        token VARCHAR NOT NULL
    )
    """,
)

# Idempotent column additions so databases created before the extended taste
# axes (bitterness/aroma/finish) migrate in place without losing rows.
_MIGRATIONS: tuple[str, ...] = (
    "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS bitterness INTEGER",
    "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS aroma INTEGER",
    "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS finish INTEGER",
)


class DuckDBBrewLog:
    """Persists the dial-in learning history in a single-file DuckDB database."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _migrate(self) -> None:
        with duckdb.connect(self._db_path) as conn:
            for statement in _SCHEMA:
                conn.execute(statement)
            for statement in _MIGRATIONS:
                conn.execute(statement)

    async def save_coffee(self, coffee: Coffee) -> None:
        await asyncio.to_thread(self._save_coffee, coffee)

    async def list_coffees(self) -> list[Coffee]:
        return await asyncio.to_thread(self._list_coffees)

    async def save_shot(self, shot: ShotSummary) -> None:
        await asyncio.to_thread(self._save_shot, shot)

    async def get_shot(self, shot_id: str) -> ShotSummary:
        return await asyncio.to_thread(self._get_shot, shot_id)

    async def save_feedback(self, shot_id: str, feedback: TasteFeedback) -> None:
        await asyncio.to_thread(self._save_feedback, shot_id, feedback)

    async def get_feedback(self, shot_id: str) -> TasteFeedback:
        return await asyncio.to_thread(self._get_feedback, shot_id)

    async def save_draft(self, draft: ProfileDraft) -> str:
        return await asyncio.to_thread(self._save_draft, draft)

    async def get_draft(self, draft_id: str) -> ProfileDraft:
        return await asyncio.to_thread(self._get_draft, draft_id)

    async def save_deployment(self, draft_id: str, result: ProfileDeployResult, token: str) -> None:
        await asyncio.to_thread(self._save_deployment, draft_id, result, token)

    async def get_deployment(self, draft_id: str) -> ProfileDeployResult | None:
        return await asyncio.to_thread(self._get_deployment, draft_id)

    async def save_next_action(self, coffee_id: str, action: NextAction) -> None:
        await asyncio.to_thread(self._save_next_action, coffee_id, action)

    async def shots_for_coffee(self, coffee_id: str) -> list[ShotSummary]:
        return await asyncio.to_thread(self._shots_for_coffee, coffee_id)

    async def next_actions(self, coffee_id: str) -> list[NextAction]:
        return await asyncio.to_thread(self._next_actions, coffee_id)

    async def reset(self) -> None:
        """Delete every row (keep the schema) so a demo starts from a clean slate."""
        await asyncio.to_thread(self._reset)

    def _reset(self) -> None:
        with duckdb.connect(self._db_path) as conn:
            for table in ("coffees", "shots", "feedback", "drafts", "events", "deployments"):
                conn.execute(f"DELETE FROM {table}")

    def _save_coffee(self, coffee: Coffee) -> None:
        with duckdb.connect(self._db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO coffees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", _coffee_params(coffee))

    def _list_coffees(self) -> list[Coffee]:
        with duckdb.connect(self._db_path) as conn:
            rows = conn.execute("SELECT * FROM coffees ORDER BY rowid").fetchall()
        return [_coffee_from_row(row) for row in rows]

    def _save_shot(self, shot: ShotSummary) -> None:
        with duckdb.connect(self._db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO shots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", _shot_params(shot))

    def _get_shot(self, shot_id: str) -> ShotSummary:
        with duckdb.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT shot_id, coffee_id, machine_ref, dose_in_g, dose_out_g, peak_pressure_bar, avg_temp_c, brew_ratio, duration_s "
                "FROM shots WHERE shot_id = ?",
                [shot_id],
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown shot id: {shot_id}")
        return _shot_from_row(row)

    def _save_feedback(self, shot_id: str, feedback: TasteFeedback) -> None:
        with duckdb.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO feedback "
                "(shot_id, acidity, sweetness, body, overall, bitterness, aroma, finish, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    shot_id,
                    feedback.acidity,
                    feedback.sweetness,
                    feedback.body,
                    feedback.overall,
                    feedback.bitterness,
                    feedback.aroma,
                    feedback.finish,
                    feedback.note,
                ),
            )

    def _get_feedback(self, shot_id: str) -> TasteFeedback:
        with duckdb.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT shot_id, acidity, sweetness, body, overall, bitterness, aroma, finish, note "
                "FROM feedback WHERE shot_id = ?",
                [shot_id],
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown feedback for shot: {shot_id}")
        return _feedback_from_row(row)

    def _save_draft(self, draft: ProfileDraft) -> str:
        draft_id = str(uuid.uuid4())
        with duckdb.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO drafts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (draft_id, *_draft_params(draft))
            )
        return draft_id

    def _get_draft(self, draft_id: str) -> ProfileDraft:
        with duckdb.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT draft_id, name, dose_g, yield_g, ratio, temp_c, grind_desc, phases, rationale, assumptions, evidence "
                "FROM drafts WHERE draft_id = ?",
                [draft_id],
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown draft id: {draft_id}")
        return _draft_from_row(row)

    def _save_deployment(self, draft_id: str, result: ProfileDeployResult, token: str) -> None:
        with duckdb.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO deployments VALUES (?, ?, ?, ?, ?)",
                (draft_id, result.profile_id, result.status, result.message, token),
            )

    def _get_deployment(self, draft_id: str) -> ProfileDeployResult | None:
        with duckdb.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT profile_id, status, message FROM deployments WHERE draft_id = ?",
                [draft_id],
            ).fetchone()
        if row is None:
            return None
        profile_id, status, message = row
        return ProfileDeployResult(
            profile_id=str(profile_id),
            status=cast(Literal["deployed", "failed"], status),
            message=str(message) if message is not None else None,
        )

    def _save_next_action(self, coffee_id: str, action: NextAction) -> None:
        with duckdb.connect(self._db_path) as conn:
            conn.execute("INSERT INTO events VALUES (uuid(), ?, ?, ?)", _next_action_params(coffee_id, action))

    def _shots_for_coffee(self, coffee_id: str) -> list[ShotSummary]:
        with duckdb.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT shot_id, coffee_id, machine_ref, dose_in_g, dose_out_g, peak_pressure_bar, avg_temp_c, brew_ratio, duration_s "
                "FROM shots WHERE coffee_id = ? ORDER BY rowid",
                [coffee_id],
            ).fetchall()
        return [_shot_from_row(row) for row in rows]

    def _next_actions(self, coffee_id: str) -> list[NextAction]:
        with duckdb.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT payload FROM events WHERE event_type = ? AND coffee_id = ? ORDER BY rowid",
                ["next_action_proposed", coffee_id],
            ).fetchall()
        return [_next_action_from_json(row[0]) for row in rows]


def _coffee_params(coffee: Coffee) -> tuple[Any, ...]:
    return (
        coffee.coffee_id,
        coffee.name,
        coffee.roaster,
        coffee.origin,
        coffee.process,
        coffee.roast_level,
        coffee.roast_date,
        json.dumps(list(coffee.tasting_notes)),
        json.dumps(list(coffee.sources)),
        json.dumps([_evidence_to_dict(item) for item in coffee.evidence]),
    )


def _shot_params(shot: ShotSummary) -> tuple[Any, ...]:
    return (
        shot.shot_id,
        shot.coffee_id,
        shot.machine_ref,
        shot.dose_in_g,
        shot.dose_out_g,
        shot.peak_pressure_bar,
        shot.avg_temp_c,
        shot.brew_ratio,
        shot.duration_s,
    )


def _draft_params(draft: ProfileDraft) -> tuple[Any, ...]:
    profile = draft.profile
    phases = [
        {
            "name": phase.name,
            "target_pressure_bar": phase.target_pressure_bar,
            "duration_s": phase.duration_s,
            "target_flow_g_s": phase.target_flow_g_s,
        }
        for phase in profile.phases
    ]
    return (
        profile.name,
        profile.dose_g,
        profile.yield_g,
        profile.ratio,
        profile.temp_c,
        profile.grind_desc,
        json.dumps(phases),
        draft.rationale,
        json.dumps(list(draft.assumptions)),
        json.dumps([_evidence_to_dict(item) for item in draft.evidence]),
    )


def _next_action_params(coffee_id: str, action: NextAction) -> tuple[str, str, str]:
    payload = json.dumps(
        {
            "changed_variable": action.changed_variable.value,
            "current_value": action.current_value,
            "proposed_value": action.proposed_value,
            "rationale": action.rationale,
            "confidence": action.confidence,
        }
    )
    return ("next_action_proposed", coffee_id, payload)


def _shot_from_row(row: tuple[Any, ...]) -> ShotSummary:
    shot_id, coffee_id, machine_ref, dose_in, dose_out, peak, temp, ratio, duration = row
    return ShotSummary(
        shot_id=str(shot_id),
        coffee_id=str(coffee_id) if coffee_id is not None else None,
        machine_ref=str(machine_ref),
        dose_in_g=float(dose_in),
        dose_out_g=float(dose_out),
        peak_pressure_bar=float(peak),
        avg_temp_c=float(temp),
        brew_ratio=float(ratio),
        duration_s=float(duration),
    )


def _next_action_from_json(raw: str) -> NextAction:
    data = json.loads(raw)
    return NextAction(
        changed_variable=ChangedVariable(data["changed_variable"]),
        current_value=data["current_value"],
        proposed_value=data["proposed_value"],
        rationale=data["rationale"],
        confidence=data["confidence"],
    )


def _evidence_to_dict(item: EvidenceItem) -> dict[str, Any]:
    return {
        "source": item.source,
        "url": item.url,
        "text": item.text,
        "confidence": item.confidence,
    }


def _evidence_from_dict(data: dict[str, Any]) -> EvidenceItem:
    return EvidenceItem(
        source=data["source"],
        url=data.get("url"),
        text=data["text"],
        confidence=data.get("confidence", 0.5),
    )


def _coffee_from_row(row: tuple[Any, ...]) -> Coffee:
    coffee_id, name, roaster, origin, process, roast_level, roast_date, tasting_notes, sources, evidence = row
    return Coffee(
        coffee_id=str(coffee_id),
        name=str(name),
        roaster=str(roaster) if roaster is not None else None,
        origin=str(origin) if origin is not None else None,
        process=str(process) if process is not None else None,
        roast_level=str(roast_level) if roast_level is not None else None,
        roast_date=str(roast_date) if roast_date is not None else None,
        tasting_notes=tuple(str(item) for item in json.loads(tasting_notes)),
        sources=tuple(str(item) for item in json.loads(sources)),
        evidence=tuple(_evidence_from_dict(item) for item in json.loads(evidence)),
    )


def _feedback_from_row(row: tuple[Any, ...]) -> TasteFeedback:
    shot_id, acidity, sweetness, body, overall, bitterness, aroma, finish, note = row
    return TasteFeedback(
        shot_id=str(shot_id),
        acidity=int(acidity),
        sweetness=int(sweetness),
        body=int(body),
        overall=int(overall),
        bitterness=int(bitterness) if bitterness is not None else 3,
        aroma=int(aroma) if aroma is not None else 3,
        finish=int(finish) if finish is not None else 3,
        note=str(note) if note is not None else None,
    )


def _phase_from_dict(data: dict[str, Any]) -> PhaseSettings:
    return PhaseSettings(
        name=data["name"],
        target_pressure_bar=float(data["target_pressure_bar"]),
        duration_s=float(data["duration_s"]),
        target_flow_g_s=data.get("target_flow_g_s"),
    )


def _draft_from_row(row: tuple[Any, ...]) -> ProfileDraft:
    _draft_id, name, dose_g, yield_g, ratio, temp_c, grind_desc, phases, rationale, assumptions, evidence = row
    profile = ExtractionProfile(
        name=str(name),
        dose_g=float(dose_g),
        yield_g=float(yield_g),
        ratio=float(ratio),
        temp_c=float(temp_c),
        grind_desc=str(grind_desc),
        phases=tuple(_phase_from_dict(phase) for phase in json.loads(phases)),
    )
    return ProfileDraft(
        profile=profile,
        rationale=str(rationale),
        assumptions=tuple(str(item) for item in json.loads(assumptions)),
        evidence=tuple(_evidence_from_dict(item) for item in json.loads(evidence)),
    )
