"""Tests for the demo script's act definitions."""

from nine_bars.demo import _ACTS
from nine_bars.fixtures.generate import DEMO_COFFEE_ID


def test_demo_has_four_acts() -> None:
    assert len(_ACTS) == 4


def test_demo_acts_reference_the_demo_coffee() -> None:
    assert all(DEMO_COFFEE_ID in act for act in _ACTS)
