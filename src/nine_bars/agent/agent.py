"""Assemble the Strands agent from its prompt, tools, and model."""

from __future__ import annotations

from strands import Agent
from strands.models import Model

from nine_bars.agent.prompt import SYSTEM_PROMPT
from nine_bars.agent.tools import build_tools
from nine_bars.api.dependencies import Dependencies


def build_agent(deps: Dependencies, model: Model) -> Agent:
    """Build the dial-in agent from the system prompt, tools, and model."""
    return Agent(
        model=model,
        tools=build_tools(deps),
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
    )
