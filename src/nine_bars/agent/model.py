"""Agent model construction: the DeepSeek-backed Strands model."""

from __future__ import annotations

from strands.models import Model
from strands.models.openai import OpenAIModel

from nine_bars.config import Settings


class AgentConfigurationError(RuntimeError):
    """Raised when the agent cannot be built from the current configuration."""


def build_model(settings: Settings) -> Model:
    """Build the DeepSeek model for the Strands agent.

    DeepSeek is reached through Strands' built-in OpenAI provider (DeepSeek's
    API is OpenAI-compatible). A missing API key is a hard configuration error,
    surfaced immediately rather than silently at the first call.
    """
    if not settings.deepseek_api_key:
        raise AgentConfigurationError(
            "DeepSeek is not configured: set DEEPSEEK_API_KEY before building the agent model."
        )
    return OpenAIModel(
        model_id=settings.deepseek_model,
        client_args={
            "base_url": settings.deepseek_base_url,
            "api_key": settings.deepseek_api_key,
        },
        # DeepSeek enables chain-of-thought by default; strands does not round-trip
        # `reasoning_content` across tool-call turns, which breaks the agent loop.
        # `extra_body` is required because the openai SDK rejects unknown top-level
        # kwargs and forwards only `extra_body` into the request body.
        params={"extra_body": {"thinking": {"type": "disabled"}}},
    )
