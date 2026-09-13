"""Tests for domain event value objects."""

from dataclasses import FrozenInstanceError

import pytest

from nine_bars.domain.events import (
    CoffeeOnboarded,
    NextActionProposed,
    ProfileDraftCreated,
    ShotObserved,
    TasteRecorded,
)
from nine_bars.domain.models import (
    ChangedVariable,
    Coffee,
    ExtractionProfile,
    NextAction,
    ShotSummary,
    TasteFeedback,
)


def test_events_are_frozen() -> None:
    event = CoffeeOnboarded(coffee=Coffee(coffee_id="c1", name="Ethiopia"))

    with pytest.raises(FrozenInstanceError):
        event.coffee = None


def test_event_carries_payload() -> None:
    coffee = Coffee(coffee_id="c1", name="Ethiopia")
    assert CoffeeOnboarded(coffee).coffee == coffee

    profile = ExtractionProfile(name="p", dose_g=18.0, yield_g=36.0, ratio=2.0, temp_c=93.0, grind_desc="m")
    assert ProfileDraftCreated(profile).profile == profile

    shot = ShotSummary(
        shot_id="s1",
        machine_ref="m",
        dose_in_g=18.0,
        dose_out_g=36.0,
        peak_pressure_bar=9.0,
        avg_temp_c=93.0,
        brew_ratio=2.0,
        duration_s=30.0,
    )
    assert ShotObserved(shot).shot == shot

    feedback = TasteFeedback(shot_id="s1", acidity=3, sweetness=3, body=3, overall=3)
    assert TasteRecorded(feedback).feedback == feedback

    action = NextAction(
        changed_variable=ChangedVariable.GRIND,
        current_value="coarse",
        proposed_value="finer",
        rationale="reason",
        confidence=0.5,
    )
    assert NextActionProposed(action).action == action
