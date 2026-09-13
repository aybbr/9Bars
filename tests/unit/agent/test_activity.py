"""Tests for agent activity span extraction and the ring buffer."""

from strands.telemetry import Trace

from nine_bars.agent.activity import AgentActivityBuffer, SpanRecord, extract_spans


def _tool_cycle(tool_name: str, tool_use_id: str, input_payload: object, output_text: str) -> Trace:
    assistant = Trace(name="stream_messages")
    assistant.message = {
        "role": "assistant",
        "content": [{"toolUse": {"toolUseId": tool_use_id, "name": tool_name, "input": input_payload}}],
    }
    tool_span = Trace(name=f"Tool: {tool_name}", metadata={"toolUseId": tool_use_id, "tool_name": tool_name})
    tool_span.message = {"role": "user", "content": [{"toolResult": {"content": [{"text": output_text}]}}]}
    tool_span.end_time = tool_span.start_time + 0.25
    root = Trace(name="Cycle 1")
    root.children = [assistant, tool_span]
    return root


def test_extract_spans_orders_and_summarizes() -> None:
    spans = extract_spans([_tool_cycle("analyze_shot", "t1", {"shot_id": "shot-1"}, "flow_deviation 0.0")])

    assert len(spans) == 1
    span = spans[0]
    assert span.tool_name == "analyze_shot"
    assert "shot-1" in span.input_summary
    assert span.output_summary == "flow_deviation 0.0"
    assert span.duration_ms == 250


def test_extract_spans_preserves_multiple_tools_in_order() -> None:
    root = Trace(name="Cycle 1")
    root.children = [
        _tool_cycle("analyze_shot", "t1", {"shot_id": "shot-1"}, "a"),
        _tool_cycle("save_feedback", "t2", {"overall": 2}, "b"),
    ]

    spans = extract_spans([root])

    assert [span.tool_name for span in spans] == ["analyze_shot", "save_feedback"]


def test_buffer_caps_capacity() -> None:
    buffer = AgentActivityBuffer(capacity=2)
    for name in ("a", "b", "c"):
        buffer.record(SpanRecord(name, "", "", 1))

    assert [span.tool_name for span in buffer.snapshot()] == ["b", "c"]


def test_buffer_to_json() -> None:
    buffer = AgentActivityBuffer()
    buffer.record(SpanRecord("analyze_shot", "i", "o", 1))

    assert '"tool_name": "analyze_shot"' in buffer.to_json()
