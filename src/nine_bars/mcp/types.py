"""MCP-layer types: binary parser intermediates and tool DTOs.

``IndexEntry`` and ``RawShot`` are internal parser results (frozen value
objects). The remaining models are pydantic because MCPServer v2 derives JSON
schemas from tool signatures, which requires pydantic (plain dataclasses are
not supported).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from nine_bars.domain.models import ExtractionProfile


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """One shot's entry in the device history index."""

    shot_id: str
    timestamp_ms: int
    duration_ms: int


@dataclass(frozen=True, slots=True)
class RawShot:
    """A parsed ``.slog`` shot before time-grid reconstruction."""

    shot_id: str
    machine_ref: str
    coffee_id: str | None
    dose_in_g: float
    dose_out_g: float
    duration_ms: int
    pressure: tuple[float, ...]
    flow: tuple[float, ...]
    temperature: tuple[float, ...]
    weight: tuple[float, ...]


class DevicePhase(BaseModel):
    """A single phase of a device profile."""

    name: str
    target_pressure_bar: float
    duration_s: float
    target_flow_g_s: float | None = None


class DeviceProfile(BaseModel):
    """The machine-facing profile sent to ``save_profile``."""

    name: str
    dose_g: float
    yield_g: float
    temp_c: float
    phases: list[DevicePhase]

    @classmethod
    def from_extraction(cls, profile: ExtractionProfile) -> DeviceProfile:
        """Build a device profile from a domain :class:`ExtractionProfile`."""
        return cls(
            name=profile.name,
            dose_g=profile.dose_g,
            yield_g=profile.yield_g,
            temp_c=profile.temp_c,
            phases=[
                DevicePhase(
                    name=phase.name,
                    target_pressure_bar=phase.target_pressure_bar,
                    duration_s=phase.duration_s,
                    target_flow_g_s=phase.target_flow_g_s,
                )
                for phase in profile.phases
            ],
        )


class ShotSummaryDoc(BaseModel):
    """A JSON-friendly shot summary for ``list_shots``."""

    shot_id: str
    coffee_id: str | None
    brew_ratio: float
    duration_s: float
    peak_pressure_bar: float
    avg_temp_c: float


class ShotGeometryDoc(BaseModel):
    """A shot's curves for ``get_shot``."""

    shot_id: str
    pressure: list[tuple[float, float]]
    flow: list[tuple[float, float]]
    temperature: list[tuple[float, float]]
    weight: list[tuple[float, float]]


class ShotAnalysisDoc(BaseModel):
    """Channeling and flow-deviation analysis for ``analyze_shot``."""

    shot_id: str
    channeling_strength: str
    channeling_explanation: str
    flow_deviation: float
