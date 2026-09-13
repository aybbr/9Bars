"""Tests for the agent system prompt."""

from nine_bars.agent.prompt import SYSTEM_PROMPT


def test_prompt_encodes_one_variable_law() -> None:
    assert "one variable per shot" in SYSTEM_PROMPT.lower()
    assert "exactly one change" in SYSTEM_PROMPT.lower()


def test_prompt_guards_against_fabrication() -> None:
    assert "never invent" in SYSTEM_PROMPT.lower()
    assert "stay grounded" in SYSTEM_PROMPT.lower()


def test_prompt_measurement_vs_inference() -> None:
    assert "hypothesis" in SYSTEM_PROMPT
    assert "channeling" in SYSTEM_PROMPT


def test_prompt_requires_source_citation() -> None:
    assert "cite sources" in SYSTEM_PROMPT.lower()
