"""The nine-bars MCP server: read-only tools over the device boundary.

The machine write path is deliberately absent here: profiles are deployed only
through the gated approval route (``adapters/device_profile_writer.py``), never
via an MCP tool. This keeps the agent (an MCP client) read-only.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from nine_bars.domain.physics import channeling_risk, flow_deviation, summarize
from nine_bars.mcp.binary import parse_index, parse_shot, to_telemetry
from nine_bars.mcp.protocols import DeviceTransport
from nine_bars.mcp.types import ShotAnalysisDoc, ShotGeometryDoc, ShotSummaryDoc

_EXPECTED_FLOW_ENVELOPE = (0.5, 3.5)


def create_server(transport: DeviceTransport) -> MCPServer:
    """Build the MCP server with the three read-only device tools."""
    server = MCPServer(name="nine-bars-mcp")

    @server.tool(description="List shots available on the device.")
    async def list_shots(limit: int = 10) -> list[ShotSummaryDoc]:
        return await _list_shots(transport, limit)

    @server.tool(description="Return the curves for one shot.")
    async def get_shot(shot_id: str) -> ShotGeometryDoc:
        return await _get_shot(transport, shot_id)

    @server.tool(description="Analyze a shot for channeling and flow deviation.")
    async def analyze_shot(shot_id: str) -> ShotAnalysisDoc:
        return await _analyze_shot(transport, shot_id)

    return server


async def _list_shots(transport: DeviceTransport, limit: int) -> list[ShotSummaryDoc]:
    entries = parse_index(await transport.fetch_index())
    docs: list[ShotSummaryDoc] = []
    for entry in entries[:limit]:
        shot = to_telemetry(parse_shot(await transport.fetch_shot(entry.shot_id)))
        summary = summarize(shot)
        docs.append(
            ShotSummaryDoc(
                shot_id=summary.shot_id,
                coffee_id=summary.coffee_id,
                brew_ratio=summary.brew_ratio,
                duration_s=summary.duration_s,
                peak_pressure_bar=summary.peak_pressure_bar,
                avg_temp_c=summary.avg_temp_c,
            )
        )
    return docs


async def _get_shot(transport: DeviceTransport, shot_id: str) -> ShotGeometryDoc:
    shot = to_telemetry(parse_shot(await transport.fetch_shot(shot_id)))
    return ShotGeometryDoc(
        shot_id=shot.shot_id,
        pressure=list(shot.pressure_curve),
        flow=list(shot.flow_curve),
        temperature=list(shot.temperature_curve),
        weight=list(shot.weight_curve),
    )


async def _analyze_shot(transport: DeviceTransport, shot_id: str) -> ShotAnalysisDoc:
    shot = to_telemetry(parse_shot(await transport.fetch_shot(shot_id)))
    report = channeling_risk(shot.pressure_curve, shot.flow_curve)
    flow_values = [value for _, value in shot.flow_curve]
    observed = sum(flow_values) / len(flow_values) if flow_values else 0.0
    return ShotAnalysisDoc(
        shot_id=shot.shot_id,
        channeling_strength=report.evidence_strength,
        channeling_explanation=report.explanation,
        flow_deviation=flow_deviation(observed, _EXPECTED_FLOW_ENVELOPE),
    )
