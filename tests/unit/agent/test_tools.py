"""Tests for the agent tool surface."""

import asyncio
import inspect

import nine_bars.agent.tools as tools_module
from nine_bars.agent.tools import build_tools
from nine_bars.api.dependencies import Dependencies
from nine_bars.domain.physics import summarize
from nine_bars.fixtures.generate import DEMO_COFFEE_ID, baseline_shot

_EXPECTED_TOOLS = {
    "research_coffee",
    "get_latest_shot",
    "analyze_shot",
    "lookup_history",
    "save_feedback",
    "propose_next_action",
    "draft_profile",
    "ask_for_taste_feedback",
}


def test_build_tools_registers_eight_tools(deps: Dependencies) -> None:
    names = {tool._tool_name for tool in build_tools(deps)}

    assert names == _EXPECTED_TOOLS


def test_tool_surface_is_read_only(deps: Dependencies) -> None:
    names = {tool._tool_name for tool in build_tools(deps)}

    assert "save_profile" not in names
    assert "save_profile" not in inspect.getsource(tools_module)


def test_get_latest_shot_and_propose_next_action(deps: Dependencies) -> None:
    tools = {tool._tool_name: tool for tool in build_tools(deps)}

    async def run() -> None:
        await deps.brew_log.save_shot(summarize(baseline_shot()))
        latest = await tools["get_latest_shot"]._tool_func(DEMO_COFFEE_ID)
        action = await tools["propose_next_action"]._tool_func(
            DEMO_COFFEE_ID,
            acidity=2,
            sweetness=2,
            body=2,
            overall=2,
        )

        assert latest["shot_id"] == "1042"
        assert "changed_variable" in action
        assert action["rationale"]

    asyncio.run(run())


def test_draft_profile_derives_ratio(deps: Dependencies) -> None:
    tools = {tool._tool_name: tool for tool in build_tools(deps)}

    async def run() -> None:
        result = await tools["draft_profile"]._tool_func(
            name="demo",
            dose_g=18.0,
            yield_g=36.0,
            temp_c=93.0,
            grind_desc="medium-fine",
            rationale="starting point",
        )
        draft = await deps.brew_log.get_draft(result["draft_id"])

        assert draft.profile.ratio == 2.0

    asyncio.run(run())
