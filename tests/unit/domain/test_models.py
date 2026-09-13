"""Tests for domain model immutability and derived metrics."""

from dataclasses import FrozenInstanceError

import pytest

from nine_bars.domain.models import Coffee, EvidenceItem, TasteFeedback


def test_models_are_frozen() -> None:
    coffee = Coffee(coffee_id="c1", name="Ethiopia")

    with pytest.raises(FrozenInstanceError):
        coffee.name = "changed"


def test_collection_fields_default_to_empty_tuple() -> None:
    coffee = Coffee(coffee_id="c1", name="Ethiopia")

    assert coffee.tasting_notes == ()
    assert coffee.sources == ()
    assert coffee.evidence == ()


def test_evidence_item_sourced_is_fact() -> None:
    item = EvidenceItem(source="web", text="Roasted in Berlin")

    assert item.kind == "fact"
    assert item.url is None
    assert item.confidence == 0.5


def test_evidence_item_inferred_is_hypothesis() -> None:
    item = EvidenceItem(source="inferred", text="likely a light roast")

    assert item.kind == "hypothesis"


def test_taste_feedback_note_is_optional() -> None:
    feedback = TasteFeedback(shot_id="s1", acidity=3, sweetness=3, body=3, overall=3)

    assert feedback.note is None
