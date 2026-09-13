"""Web-UI backing routes: agent chat (SSE), activity, telemetry, and the demo loader.

These endpoints support the Next.js UI served at ``/ui``. They live outside
``nine_bars.api`` because they reach into ``nine_bars.agent`` (which the API
layer must not import). Like ``main.py`` and ``demo.py``, this module is a
composition-root concern.

The chat endpoint has two modes:

* **live** — when ``DEEPSEEK_API_KEY`` is set, it runs the real Strands agent
  and records its tool spans into the activity buffer.
* **demo** — otherwise it replays a scripted dial-in arc against the fixture
  shots, so the UI is fully exerciseable offline.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import asdict
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from nine_bars.agent.activity import AgentActivityBuffer, SpanRecord, extract_spans
from nine_bars.agent.agent import build_agent
from nine_bars.agent.model import build_model
from nine_bars.agent.tools import build_tools
from nine_bars.api.dependencies import Dependencies
from nine_bars.config import Settings, get_settings
from nine_bars.domain.physics import summarize
from nine_bars.fixtures.generate import DEMO_COFFEE_ID, baseline_shot, corrected_shot, demo_coffee_dict

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)

_MAX_SUMMARY = 200
_MAX_AGENT_TURNS = 12

_ARTIFACT_TOOLS = frozenset(
    {"research_coffee", "draft_profile", "propose_next_action", "analyze_shot", "lookup_history"}
)

# The read-only tool the agent calls to request an interactive taste rating,
# and the artifact kind the frontend renders for it.
_RATE_TOOL = "ask_for_taste_feedback"
_RATE_ARTIFACT = "rate_shot"

# The offline demo arc, as a sequence of typed steps. ``text`` emits assistant
# prose; ``tool`` runs one read-only tool; ``load`` ingests a fixture shot.
_DEMO_STEPS: list[dict[str, Any]] = [
    {"kind": "text", "text": "Let me look this up for you."},
    {"kind": "tool", "name": "research_coffee", "kwargs": {"text": "Finca Los Pirineos", "kind": "name"}},
    {
        "kind": "text",
        "text": "Found it — a washed light roast from Bonanza Coffee Roasters. Here's the evidence, then a starting profile.",
    },
    {
        "kind": "tool",
        "name": "draft_profile",
        "kwargs": {
            "name": "Finca Los Pirineos",
            "dose_g": 18.0,
            "yield_g": 45.0,
            "temp_c": 93.0,
            "grind_desc": "medium-fine",
            "rationale": "Light washed: start long at 1:2.5 for clarity, then trim the yield if the finish runs dry.",
        },
    },
    {"kind": "load", "shot": "baseline"},
    {"kind": "text", "text": "Shot #1042 is in — the finish ran dry and a little harsh. Let me read the telemetry."},
    {"kind": "tool", "name": "get_latest_shot", "kwargs": {"coffee_id": DEMO_COFFEE_ID}},
    {"kind": "tool", "name": "analyze_shot", "kwargs": {"shot_id": "1042"}},
    {
        "kind": "tool",
        "name": "save_feedback",
        "kwargs": {"shot_id": "1042", "acidity": 2, "sweetness": 2, "body": 3, "overall": 2, "note": "dry at the end"},
    },
    {
        "kind": "tool",
        "name": "propose_next_action",
        "kwargs": {
            "coffee_id": DEMO_COFFEE_ID,
            "acidity": 2,
            "sweetness": 2,
            "body": 3,
            "overall": 2,
        },
    },
    {
        "kind": "text",
        "text": "The tail over-extracted — cutting the yield from 45 g to 36 g should drop that dryness without touching grind.",
    },
    {"kind": "load", "shot": "corrected"},
    {"kind": "text", "text": "Here's shot #1043 after the yield cut."},
    {"kind": "tool", "name": "get_latest_shot", "kwargs": {"coffee_id": DEMO_COFFEE_ID}},
    {"kind": "tool", "name": "analyze_shot", "kwargs": {"shot_id": "1043"}},
    {"kind": "text", "text": "Pressure and flow stayed coupled — no channeling signal. That's the one change working."},
    {"kind": "tool", "name": "lookup_history", "kwargs": {"coffee_id": DEMO_COFFEE_ID}},
]


class ChatRequest(BaseModel):
    """The user prompt for the agent chat, with an optional bag photo."""

    prompt: str
    image: str | None = None
    session_id: str | None = None


@router.post("/agent/chat")
async def agent_chat(body: ChatRequest, request: Request) -> StreamingResponse:
    """Run the agent (live or scripted) and stream events over SSE."""
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    deps = _deps(request)
    activity = cast(AgentActivityBuffer, request.app.state.activity)
    agents = cast(dict[str, Any], request.app.state.agents)
    return StreamingResponse(
        _chat_stream(deps, activity, get_settings(), prompt, body.image, agents, body.session_id),
        media_type="text/event-stream",
    )


@router.get("/agent/activity")
async def agent_activity(request: Request) -> dict[str, object]:
    """Return the latest tool spans plus the current agent mode."""
    activity = cast(AgentActivityBuffer, request.app.state.activity)
    return {
        "spans": [asdict(span) for span in activity.snapshot()],
        "mode": "live" if get_settings().deepseek_api_key else "demo",
    }


@router.get("/shot/{shot_id}/telemetry")
async def shot_telemetry(shot_id: str, request: Request) -> dict[str, object]:
    """Return one shot's pressure/flow/temperature/weight curves for charting."""
    deps = _deps(request)
    try:
        shot = await deps.shot_source.get_shot(shot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="shot not found") from exc
    return {
        "shot_id": shot.shot_id,
        "coffee_id": shot.coffee_id,
        "dose_in_g": shot.dose_in_g,
        "dose_out_g": shot.dose_out_g,
        "pressure": _curves(shot.pressure_curve),
        "flow": _curves(shot.flow_curve),
        "temperature": _curves(shot.temperature_curve),
        "weight": _curves(shot.weight_curve),
    }


@router.post("/demo/load")
async def demo_load(request: Request) -> dict[str, object]:
    """Ingest the two fixture shots into the brew log (demo state, not a machine write)."""
    deps = _deps(request)
    shots = (summarize(baseline_shot()), summarize(corrected_shot()))
    for summary in shots:
        await deps.brew_log.save_shot(summary)
    return {"coffee_id": DEMO_COFFEE_ID, "shots": [summary.shot_id for summary in shots]}


def _deps(request: Request) -> Dependencies:
    return cast(Dependencies, request.app.state.deps)


async def _chat_stream(
    deps: Dependencies,
    activity: AgentActivityBuffer,
    settings: Settings,
    prompt: str,
    image: str | None = None,
    agents: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> AsyncIterator[str]:
    logger.info("agent chat: mode=%s", "live" if settings.deepseek_api_key else "demo")
    if settings.deepseek_api_key:
        yield _sse({"type": "start", "mode": "live"})
        agent = _get_agent(agents, session_id, deps, settings)
        prompt_arg: Any = prompt
        if image:
            prompt_arg = [_image_block(image), {"text": prompt}]
        result = None
        try:
            async for event in agent.stream_async(prompt_arg, limits={"turns": _MAX_AGENT_TURNS}):
                if "result" in event:
                    result = event["result"]
                elif event.get("data"):
                    yield _sse({"type": "text", "text": str(event["data"])})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        if result is None:
            yield _sse({"type": "error", "message": "The agent produced no response."})
            return
        try:
            for span in extract_spans(result.metrics.traces):
                activity.record(span)
                yield _sse({"type": "tool_result", "name": span.tool_name, "output": span.output_summary})
                artifact = _live_artifact(span)
                if artifact is not None:
                    yield _sse(artifact)
        except Exception:
            pass
        yield _sse({"type": "done", "message": _message_text(result.message), "mode": "live"})
        return

    yield _sse({"type": "start", "mode": "demo"})
    await deps.brew_log.reset()
    tools = {tool._tool_name: tool for tool in build_tools(deps)}

    for step in _DEMO_STEPS:
        kind = step["kind"]
        if kind == "text":
            yield _sse({"type": "text", "text": str(step["text"])})
            continue
        if kind == "load":
            shot = baseline_shot() if step["shot"] == "baseline" else corrected_shot()
            await deps.brew_log.save_shot(summarize(shot))
            continue

        tool_name = str(step["name"])
        kwargs = cast(dict[str, object], step["kwargs"])
        tool = tools[tool_name]
        input_summary = _compact(kwargs)
        yield _sse({"type": "tool_start", "name": tool_name, "input": input_summary})
        started = time.perf_counter()
        try:
            output = await tool._tool_func(**kwargs)
            output_summary = _compact(output)
        except Exception as exc:
            output_summary = f"error: {exc}"
            output = {"error": str(exc)}
        duration_ms = round((time.perf_counter() - started) * 1000)
        yield _sse({"type": "tool_result", "name": tool_name, "output": output_summary})
        activity.record(SpanRecord(tool_name, input_summary, output_summary, duration_ms))
        artifact = _artifact_event(tool_name, kwargs, output) if isinstance(output, dict) else None
        if artifact is not None:
            yield _sse(artifact)

    yield _sse({"type": "done", "mode": "demo"})


def _get_agent(agents: dict[str, Any] | None, session_id: str | None, deps: Dependencies, settings: Settings) -> Any:
    """Return the agent for a chat session, reusing it so conversation history persists."""
    key = session_id or "default"
    if agents is not None:
        agent = agents.get(key)
        if agent is not None:
            return agent
    agent = build_agent(deps, build_model(settings))
    if agents is not None:
        agents[key] = agent
    return agent


def _message_text(message: object) -> str:
    """Extract the visible text from a Strands ``Message`` (dict) or plain string."""
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return str(message)
    parts: list[str] = []
    for block in message.get("content") or []:
        if isinstance(block, dict) and block.get("text"):
            parts.append(str(block["text"]))
    return "\n".join(parts)


def _image_block(data_url: str) -> dict[str, object]:
    """Decode a ``data:`` URL into a Strands image content block."""
    header, _, encoded = data_url.partition(",")
    mime = header.split(":")[1].split(";")[0] if ":" in header else "image/jpeg"
    fmt = mime.split("/")[-1] or "jpeg"
    if fmt == "jpg":
        fmt = "jpeg"
    return {"image": {"format": fmt, "source": {"bytes": base64.b64decode(encoded)}}}


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


def _compact(value: object) -> str:
    text = json.dumps(value, default=str)
    return text if len(text) <= _MAX_SUMMARY else text[: _MAX_SUMMARY - 1] + "…"


def _artifact_event(tool_name: str, input: dict[str, object], output: object) -> dict[str, object] | None:
    """Build the rich artifact SSE payload for a tool, or ``None`` if not a rich tool."""
    if tool_name not in _ARTIFACT_TOOLS:
        return None
    artifact_output = demo_coffee_dict() if tool_name == "research_coffee" else output
    return {"type": "artifact", "kind": tool_name, "input": input, "output": artifact_output}


def _live_artifact(span: SpanRecord) -> dict[str, object] | None:
    """Reconstruct a rich artifact from a live tool span (best-effort).

    The rating request carries its ``shot_id`` (from the tool input) and
    ``coffee_id`` (from the tool result); the other rich tools are reconstructed
    from their JSON tool-result text when available.
    """
    if span.tool_name == _RATE_TOOL:
        input = _json_dict(span.input_summary)
        output = _json_dict(span.output_summary)
        return {
            "type": "artifact",
            "kind": _RATE_ARTIFACT,
            "input": {"shot_id": input.get("shot_id"), "coffee_id": output.get("coffee_id")},
            "output": {},
        }
    output = _json_dict(span.output_summary)
    if not output:
        return None
    return _artifact_event(span.tool_name, _json_dict(span.input_summary), output)


def _json_dict(text: str) -> dict[str, object]:
    if not text:
        return {}
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _curves(curve: tuple[tuple[float, float], ...]) -> list[list[float]]:
    return [[sample[0], sample[1]] for sample in curve]
