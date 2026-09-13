"""Agent activity: ordered tool spans captured from Strands trace data."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from strands.telemetry import Trace

_MAX_SUMMARY_CHARS = 200


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """One tool invocation: name, brief input/output, and duration."""

    tool_name: str
    input_summary: str
    output_summary: str
    duration_ms: int


class AgentActivityBuffer:
    """A bounded, ordered list of the most recent agent tool spans."""

    def __init__(self, capacity: int = 50) -> None:
        self._capacity = capacity
        self._spans: list[SpanRecord] = []

    def record(self, span: SpanRecord) -> None:
        """Append ``span``, evicting the oldest beyond ``capacity``."""
        self._spans.append(span)
        overflow = len(self._spans) - self._capacity
        if overflow > 0:
            del self._spans[:overflow]

    def snapshot(self) -> tuple[SpanRecord, ...]:
        """Return the current spans, oldest first."""
        return tuple(self._spans)

    def to_json(self) -> str:
        """Serialize the current spans as a JSON array."""
        return json.dumps([asdict(span) for span in self._spans])


def extract_spans(traces: Sequence[Trace]) -> list[SpanRecord]:
    """Extract ordered tool spans from a Strands trace tree.

    Tool uses carry their input on the assistant message; the matching tool
    span (``metadata["tool_name"]``) carries the result and duration. A
    pre-order walk preserves chronological order.
    """
    inputs: dict[str, str] = {}
    spans: list[SpanRecord] = []
    for trace in traces:
        _walk(trace, inputs, spans)
    return spans


def _walk(node: Trace, inputs: dict[str, str], spans: list[SpanRecord]) -> None:
    for block in _content_blocks(node.message):
        tool_use = block.get("toolUse")
        if isinstance(tool_use, dict):
            inputs[str(tool_use.get("toolUseId", ""))] = _compact(tool_use.get("input"))
    if "tool_name" in node.metadata:
        tool_use_id = node.metadata.get("toolUseId")
        spans.append(
            SpanRecord(
                tool_name=str(node.metadata["tool_name"]),
                input_summary=inputs.get(str(tool_use_id), ""),
                output_summary=_result_text(node.message),
                duration_ms=_duration_ms(node.duration()),
            )
        )
    for child in node.children:
        _walk(child, inputs, spans)


def _content_blocks(message: Any) -> list[Any]:
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return content if isinstance(content, list) else []


def _result_text(message: Any) -> str:
    for block in _content_blocks(message):
        tool_result = block.get("toolResult") if isinstance(block, dict) else None
        if not isinstance(tool_result, dict):
            continue
        parts = [
            str(item["text"]) for item in tool_result.get("content") or [] if isinstance(item, dict) and "text" in item
        ]
        return _truncate(" ".join(parts))
    return ""


def _compact(value: Any) -> str:
    if value is None:
        return ""
    return _truncate(json.dumps(value, default=str))


def _truncate(text: str, limit: int = _MAX_SUMMARY_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _duration_ms(duration: float | None) -> int:
    return 0 if duration is None else round(duration * 1000)
