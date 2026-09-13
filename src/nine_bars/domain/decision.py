"""Deterministic single-variable change selection for the next shot."""

from __future__ import annotations

from collections.abc import Sequence

from nine_bars.domain.models import TEMP_MIN_C, ChangedVariable, NextAction, ShotSummary, TasteFeedback

SOUR_ACIDITY = 4
LOW_SWEETNESS = 2
THIN_BODY = 2
FAST_SHOT_DURATION_S = 24.0
TARGET_BREW_RATIO = 2.0
OVER_ACIDITY = 2
LOW_OVERALL = 2
RATIO_STEP = 0.5
TEMP_STEP_C = 1.0
MIN_BREW_RATIO = 1.0
BASE_CONFIDENCE = 0.5
DEFAULT_CONFIDENCE = 0.4


def choose_single_variable(
    shots: Sequence[ShotSummary],
    feedback: TasteFeedback,
) -> NextAction:
    """Choose exactly one variable to change, with a grounded rationale.

    The rule table is grounded in poroelastic espresso-flow research
    (arXiv:2512.21528): flow saturates as pressure compacts the puck, so low
    flow is fixed by grind rather than pressure, and a fast shot with low
    extraction indicates channelling or an overly coarse grind.

    Args:
        shots: Completed shots in chronological order.
        feedback: Taste feedback for the most recent shot.

    Returns:
        A single :class:`NextAction`.

    Raises:
        ValueError: If ``shots`` is empty.
    """
    latest = _require_latest(shots)

    for rule in (
        _grind_finer_if_sour,
        _ratio_up_if_thin,
        _grind_finer_if_fast,
        _ratio_down_if_over,
    ):
        action = rule(latest, feedback, shots)
        if action is not None:
            return action

    return _temperature_step(latest, feedback, shots)


def _require_latest(shots: Sequence[ShotSummary]) -> ShotSummary:
    if not shots:
        raise ValueError("choose_single_variable requires at least one shot")
    return shots[-1]


def _grind_finer_if_sour(
    latest: ShotSummary,
    feedback: TasteFeedback,
    shots: Sequence[ShotSummary],
) -> NextAction | None:
    if feedback.acidity >= SOUR_ACIDITY and feedback.sweetness <= LOW_SWEETNESS:
        return NextAction(
            changed_variable=ChangedVariable.GRIND,
            current_value="current grind",
            proposed_value="finer",
            rationale=(
                f"Sourness (acidity {feedback.acidity}/5, sweetness {feedback.sweetness}/5) "
                f"indicates under-extraction. {_delta_context(shots)} Grinding finer raises "
                "extraction and body; raising pressure is not the lever because flow "
                "saturates once the puck compacts."
            ),
            confidence=_confidence(feedback.acidity - SOUR_ACIDITY),
        )
    return None


def _ratio_up_if_thin(
    latest: ShotSummary,
    feedback: TasteFeedback,
    shots: Sequence[ShotSummary],
) -> NextAction | None:
    if feedback.body <= THIN_BODY:
        return NextAction(
            changed_variable=ChangedVariable.RATIO,
            current_value=latest.brew_ratio,
            proposed_value=round(latest.brew_ratio + RATIO_STEP, 1),
            rationale=(
                f"Thin body ({feedback.body}/5) suggests low solubles yield. "
                f"{_delta_context(shots)} Extending the yield raises extraction while the "
                "puck still holds soluble material."
            ),
            confidence=_confidence(THIN_BODY - feedback.body),
        )
    return None


def _grind_finer_if_fast(
    latest: ShotSummary,
    feedback: TasteFeedback,
    shots: Sequence[ShotSummary],
) -> NextAction | None:
    if latest.duration_s < FAST_SHOT_DURATION_S and latest.brew_ratio >= TARGET_BREW_RATIO:
        return NextAction(
            changed_variable=ChangedVariable.GRIND,
            current_value="current grind",
            proposed_value="finer",
            rationale=(
                f"The shot finished fast ({latest.duration_s:.1f}s) at ratio "
                f"{latest.brew_ratio:.1f}; fast flow with low extraction indicates channelling "
                "or a coarse grind. Grinding finer adds resistance."
            ),
            confidence=_confidence((FAST_SHOT_DURATION_S - latest.duration_s) / 5.0),
        )
    return None


def _ratio_down_if_over(
    latest: ShotSummary,
    feedback: TasteFeedback,
    shots: Sequence[ShotSummary],
) -> NextAction | None:
    if feedback.acidity <= OVER_ACIDITY and feedback.overall <= LOW_OVERALL:
        return NextAction(
            changed_variable=ChangedVariable.RATIO,
            current_value=latest.brew_ratio,
            proposed_value=round(max(MIN_BREW_RATIO, latest.brew_ratio - RATIO_STEP), 1),
            rationale=(
                f"Low acidity ({feedback.acidity}/5) with low overall ({feedback.overall}/5) "
                f"suggests over-extraction. {_delta_context(shots)} Cutting the yield removes "
                "the harsh, over-extracted tail."
            ),
            confidence=_confidence(LOW_OVERALL - feedback.overall),
        )
    return None


def _temperature_step(
    latest: ShotSummary,
    feedback: TasteFeedback,
    shots: Sequence[ShotSummary],
) -> NextAction:
    return NextAction(
        changed_variable=ChangedVariable.TEMPERATURE,
        current_value=latest.avg_temp_c,
        proposed_value=round(max(TEMP_MIN_C, latest.avg_temp_c - TEMP_STEP_C), 1),
        rationale=(
            f"No dominant taste fault detected (overall {feedback.overall}/5). "
            f"{_delta_context(shots)} A small temperature step is the safest single refinement."
        ),
        confidence=DEFAULT_CONFIDENCE,
    )


def _delta_context(shots: Sequence[ShotSummary]) -> str:
    latest = shots[-1]
    if len(shots) >= 2:
        previous = shots[-2]
        return (
            f"Brew ratio moved {previous.brew_ratio:.1f} → {latest.brew_ratio:.1f} and "
            f"shot time {previous.duration_s:.1f}s → {latest.duration_s:.1f}s."
        )
    return f"First shot: brew ratio {latest.brew_ratio:.1f}, shot time {latest.duration_s:.1f}s."


def _confidence(delta: float) -> float:
    return min(1.0, max(0.0, BASE_CONFIDENCE + 0.1 * delta))
