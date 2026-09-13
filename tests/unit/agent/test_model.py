"""Tests for agent model construction."""

import pytest

from nine_bars.agent.model import AgentConfigurationError, build_model
from nine_bars.config import Settings


def test_build_model_requires_api_key() -> None:
    with pytest.raises(AgentConfigurationError):
        build_model(Settings(deepseek_api_key=None))


def test_build_model_returns_deepseek_openai_model() -> None:
    model = build_model(Settings(deepseek_api_key="test-key", deepseek_model="deepseek-flash"))

    assert model.config["model_id"] == "deepseek-flash"
    assert model.client_args["base_url"] == "https://api.deepseek.com"
