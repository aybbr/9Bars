"""Tests for single-variable change selection."""

import pytest

from nine_bars.domain.decision import choose_single_variable
from nine_bars.domain.models import ChangedVariable, ShotSummary, TasteFeedback


def _shot(shot_id: str, brew_ratio: float = 2.0, duration_s: float = 30.0, avg_temp_c: float = 93.0) -> ShotSummary:
    return ShotSummary(
        shot_id=shot_id,
        machine_ref="gm-1",
        dose_in_g=18.0,
        dose_out_g=brew_ratio * 18.0,
        peak_pressure_bar=9.0,
        avg_temp_c=avg_temp_c,
        brew_ratio=brew_ratio,
        duration_s=duration_s,
    )


def _feedback(acidity: int = 3, sweetness: int = 3, body: int = 3, overall: int = 3) -> TasteFeedback:
    return TasteFeedback(shot_id="s1", acidity=acidity, sweetness=sweetness, body=body, overall=overall)


def test_sour_feedback_chooses_finer_grind() -> None:
    action = choose_single_variable([_shot("s1")], _feedback(acidity=5, sweetness=1))

    assert action.changed_variable == ChangedVariable.GRIND
    assert action.proposed_value == "finer"


def test_thin_body_chooses_higher_ratio() -> None:
    action = choose_single_variable([_shot("s1")], _feedback(body=1))

    assert action.changed_variable == ChangedVariable.RATIO
    assert action.proposed_value > action.current_value


def test_fast_shot_chooses_finer_grind() -> None:
    action = choose_single_variable([_shot("s1", duration_s=15.0)], _feedback())

    assert action.changed_variable == ChangedVariable.GRIND


def test_over_extracted_chooses_lower_ratio() -> None:
    action = choose_single_variable([_shot("s1")], _feedback(acidity=1, overall=1))

    assert action.changed_variable == ChangedVariable.RATIO
    assert action.proposed_value < action.current_value


def test_default_chooses_temperature() -> None:
    action = choose_single_variable([_shot("s1")], _feedback())

    assert action.changed_variable == ChangedVariable.TEMPERATURE


def test_rationale_references_numeric_delta() -> None:
    shots = [_shot("s1", brew_ratio=2.0, duration_s=30.0), _shot("s2", brew_ratio=2.5, duration_s=18.0)]

    action = choose_single_variable(shots, _feedback(acidity=5, sweetness=1))

    assert "→" in action.rationale


def test_always_returns_exactly_one_variable() -> None:
    feedbacks = (
        _feedback(),
        _feedback(acidity=5, sweetness=1),
        _feedback(body=1),
        _feedback(acidity=1, overall=1),
    )

    for feedback in feedbacks:
        action = choose_single_variable([_shot("s1")], feedback)
        assert isinstance(action.changed_variable, ChangedVariable)


def test_empty_shots_raises() -> None:
    with pytest.raises(ValueError):
        choose_single_variable([], _feedback())
