"""The read-only tool surface exposed to the Strands agent.

Every tool backs onto a port (or pure domain logic) and formats its result as
JSON-serializable data. There is deliberately no machine-write tool here: a
profile is deployed only through the gated approval route, never by the agent.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from strands import tool

from nine_bars.api.dependencies import Dependencies
from nine_bars.domain.decision import choose_single_variable
from nine_bars.domain.models import (
    CoffeeQuery,
    ExtractionProfile,
    NextAction,
    PhaseSettings,
    ProfileDraft,
    ShotSummary,
    TasteFeedback,
)
from nine_bars.domain.physics import channeling_risk, flow_deviation, ratio

_EXPECTED_FLOW_ENVELOPE = (0.5, 3.5)
_QUERY_KINDS = ("name", "url", "free_text")


def build_tools(deps: Dependencies) -> list[Any]:
    """Return the eight read-only agent tools, bound to ``deps``.

    The concrete return type is ``Any`` because the Strands SDK types its tool
    objects opaquely; only the tool names matter to callers.
    """

    @tool
    async def research_coffee(text: str, kind: str = "name") -> dict[str, object]:
        """Research a coffee by name, URL, or free text and return sourced facts.

        Args:
            text: The coffee name, a roaster page URL, or a free-text description.
            kind: One of "name", "url", or "free_text". Only "url" fetches a page.

        Returns:
            Sourced coffee facts with an evidence list; empty fields mean unknown.
        """
        query = CoffeeQuery(text=text, kind=_coerce_kind(kind))
        result = await deps.researcher.lookup(query)
        coffee = result.coffee
        return {
            "name": coffee.name,
            "roaster": coffee.roaster,
            "origin": coffee.origin,
            "process": coffee.process,
            "roast_level": coffee.roast_level,
            "roast_date": coffee.roast_date,
            "tasting_notes": list(coffee.tasting_notes),
            "sources": list(coffee.sources),
            "evidence": [
                {"source": item.source, "url": item.url, "text": item.text, "confidence": item.confidence}
                for item in result.evidence
            ],
        }

    @tool
    async def get_latest_shot(coffee_id: str) -> dict[str, object]:
        """Return the most recent completed shot for a coffee, or an empty object if none."""
        shots = await deps.brew_log.shots_for_coffee(coffee_id)
        if not shots:
            return {}
        return _shot_dict(shots[-1])

    @tool
    async def analyze_shot(shot_id: str) -> dict[str, object]:
        """Analyze one shot's telemetry for channeling signals and flow deviation.

        Returns measured numbers plus a channeling assessment that is always a
        hypothesis, never a certainty.
        """
        shot = await deps.shot_source.get_shot(shot_id)
        report = channeling_risk(shot.pressure_curve, shot.flow_curve)
        flows = [value for _, value in shot.flow_curve]
        observed = sum(flows) / len(flows) if flows else 0.0
        return {
            "shot_id": shot.shot_id,
            "channeling_strength": report.evidence_strength,
            "channeling_explanation": report.explanation,
            "flow_deviation": flow_deviation(observed, _EXPECTED_FLOW_ENVELOPE),
        }

    @tool
    async def lookup_history(coffee_id: str) -> dict[str, object]:
        """Return the recorded shot history and next actions for a coffee."""
        shots = await deps.brew_log.shots_for_coffee(coffee_id)
        actions = await deps.brew_log.next_actions(coffee_id)
        return {
            "shots": [_shot_dict(shot) for shot in shots],
            "next_actions": [_action_dict(action) for action in actions],
        }

    @tool
    async def save_feedback(
        shot_id: str,
        acidity: int,
        sweetness: int,
        body: int,
        overall: int,
        bitterness: int = 3,
        aroma: int = 3,
        finish: int = 3,
        note: str | None = None,
    ) -> dict[str, object]:
        """Record taste feedback (each rating 1-5) for a completed shot."""
        feedback = TasteFeedback(
            shot_id=shot_id,
            acidity=acidity,
            sweetness=sweetness,
            body=body,
            overall=overall,
            bitterness=bitterness,
            aroma=aroma,
            finish=finish,
            note=note,
        )
        await deps.brew_log.save_feedback(shot_id, feedback)
        return {"shot_id": shot_id, "recorded": True}

    @tool
    async def propose_next_action(
        coffee_id: str,
        acidity: int,
        sweetness: int,
        body: int,
        overall: int,
    ) -> dict[str, object]:
        """Propose exactly one variable change for the next shot, grounded in the latest shot plus taste."""
        shots = await deps.brew_log.shots_for_coffee(coffee_id)
        if not shots:
            return {"error": "no shots recorded for this coffee"}
        feedback = TasteFeedback(
            shot_id=shots[-1].shot_id,
            acidity=acidity,
            sweetness=sweetness,
            body=body,
            overall=overall,
        )
        action = choose_single_variable(shots, feedback)
        await deps.brew_log.save_next_action(coffee_id, action)
        return _action_dict(action)

    @tool
    async def ask_for_taste_feedback(shot_id: str) -> dict[str, object]:
        """Ask the user to rate a shot's taste on the interactive bloom (no write)."""
        try:
            shot = await deps.brew_log.get_shot(shot_id)
            coffee_id: str | None = shot.coffee_id
        except KeyError:
            coffee_id = None
        return {"shot_id": shot_id, "coffee_id": coffee_id, "prompt": "Rate the taste of this shot."}

    @tool
    async def draft_profile(
        name: str,
        dose_g: float,
        yield_g: float,
        temp_c: float,
        grind_desc: str,
        rationale: str,
        assumptions: list[str] | None = None,
        phases: list[dict[str, object]] | None = None,
    ) -> dict[str, str]:
        """Draft an extraction profile and persist it; returns the draft id.

        The brew ratio is derived from dose and yield, not supplied. Each phase
        is a dict with keys name, target_pressure_bar, duration_s, and an
        optional target_flow_g_s.
        """
        profile = ExtractionProfile(
            name=name,
            dose_g=dose_g,
            yield_g=yield_g,
            ratio=ratio(dose_g, yield_g),
            temp_c=temp_c,
            grind_desc=grind_desc,
            phases=tuple(_phase(data) for data in (phases or [])),
        )
        draft = ProfileDraft(profile=profile, rationale=rationale, assumptions=tuple(assumptions or ()))
        draft_id = await deps.brew_log.save_draft(draft)
        return {"draft_id": draft_id}

    return [
        research_coffee,
        get_latest_shot,
        analyze_shot,
        lookup_history,
        save_feedback,
        propose_next_action,
        draft_profile,
        ask_for_taste_feedback,
    ]


def _coerce_kind(kind: str) -> Literal["name", "url", "free_text"]:
    return cast(Literal["name", "url", "free_text"], kind if kind in _QUERY_KINDS else "name")


def _shot_dict(shot: ShotSummary) -> dict[str, object]:
    return {
        "shot_id": shot.shot_id,
        "coffee_id": shot.coffee_id,
        "dose_in_g": shot.dose_in_g,
        "dose_out_g": shot.dose_out_g,
        "brew_ratio": shot.brew_ratio,
        "peak_pressure_bar": shot.peak_pressure_bar,
        "avg_temp_c": shot.avg_temp_c,
        "duration_s": shot.duration_s,
    }


def _action_dict(action: NextAction) -> dict[str, object]:
    return {
        "changed_variable": action.changed_variable.value,
        "current_value": action.current_value,
        "proposed_value": action.proposed_value,
        "rationale": action.rationale,
        "confidence": action.confidence,
    }


def _phase(data: dict[str, object]) -> PhaseSettings:
    return PhaseSettings(
        name=_to_str(data.get("name")),
        target_pressure_bar=_to_float(data.get("target_pressure_bar")),
        duration_s=_to_float(data.get("duration_s")),
        target_flow_g_s=_optional_float(data.get("target_flow_g_s")),
    )


def _to_str(value: object) -> str:
    return "" if value is None else str(value)


def _to_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        return _to_float(value)
    return None
