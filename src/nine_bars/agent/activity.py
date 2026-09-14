"""Agent activity: ordered tool spans captured from Strands trace data."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from strands.telemetry import Trace

_MAX_SUMMARY_CHARS = 200


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """One tool invocation: name, brief input/output, and duration.

    ``input_summary``/``output_summary`` are truncated for display; ``input_json``
    and ``output_json`` carry the full untruncated JSON so artifact reconstruction
    never loses data to the 200-char display limit.
    """

    tool_name: str
    input_summary: str
    output_summary: str
    duration_ms: int
    input_json: str = ""
    output_json: str = ""


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
        """Serialize the current spans as a JSON array (display fields only)."""
        return json.dumps([_display_dict(span) for span in self._spans])


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
            inputs[str(tool_use.get("toolUseId", ""))] = _full_json(tool_use.get("input"))
    if "tool_name" in node.metadata:
        tool_use_id = node.metadata.get("toolUseId")
        input_json = inputs.get(str(tool_use_id), "")
        output_json = _result_text(node.message)
        spans.append(
            SpanRecord(
                tool_name=str(node.metadata["tool_name"]),
                input_summary=_truncate(input_json),
                output_summary=_truncate(output_json),
                duration_ms=_duration_ms(node.duration()),
                input_json=input_json,
                output_json=output_json,
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
        return " ".join(parts)
    return ""


def _full_json(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, default=str)


def _truncate(text: str, limit: int = _MAX_SUMMARY_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _duration_ms(duration: float | None) -> int:
    return 0 if duration is None else round(duration * 1000)


def _display_dict(span: SpanRecord) -> dict[str, object]:
    """Return a span as the public display shape (without full-JSON fields)."""
    return {
        "tool_name": span.tool_name,
        "input_summary": span.input_summary,
        "output_summary": span.output_summary,
        "duration_ms": span.duration_ms,
    }
