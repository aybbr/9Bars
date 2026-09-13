"""Deterministic profile validation rules."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from typing import Literal

from nine_bars.domain.models import (
    PRESSURE_MAX_BAR,
    PRESSURE_MIN_BAR,
    TEMP_MAX_C,
    TEMP_MIN_C,
    ExtractionProfile,
    HardwareProfile,
    PhaseSettings,
)


@dataclasses.dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single profile validation finding."""

    code: str
    message: str
    severity: Literal["error", "warning"]


def validate_stop_start(phases: tuple[PhaseSettings, ...]) -> list[ValidationIssue]:
    """Flag stop-start pressure structures that risk puck delamination.

    Any phase that drops pressure to zero inside an otherwise pressurised
    profile is a stop-start pattern; the poroelastic research links such pauses
    to delamination and channelling.
    """
    if not any(phase.target_pressure_bar > 0 for phase in phases):
        return []
    return [
        ValidationIssue(
            code="stop_start_pressure",
            message=(
                f"Phase '{phase.name}' pauses pressure mid-profile; stop-start "
                "pressure promotes puck delamination and channelling."
            ),
            severity="warning",
        )
        for phase in phases
        if phase.target_pressure_bar <= 0
    ]


def validate_safety_bounds(profile: ExtractionProfile) -> list[ValidationIssue]:
    """Flag temperatures and pressures outside the hardware-safe range."""
    issues: list[ValidationIssue] = []
    if not TEMP_MIN_C <= profile.temp_c <= TEMP_MAX_C:
        issues.append(
            ValidationIssue(
                code="temp_out_of_range",
                message=f"Temperature {profile.temp_c}°C outside {TEMP_MIN_C}-{TEMP_MAX_C}°C.",
                severity="error",
            )
        )
    issues.extend(
        ValidationIssue(
            code="pressure_out_of_range",
            message=(
                f"Phase '{phase.name}' targets {phase.target_pressure_bar} bar, "
                f"outside {PRESSURE_MIN_BAR}-{PRESSURE_MAX_BAR} bar."
            ),
            severity="error",
        )
        for phase in profile.phases
        if not PRESSURE_MIN_BAR <= phase.target_pressure_bar <= PRESSURE_MAX_BAR
    )
    return issues


def clamp(value: float, low: float, high: float) -> float:
    """Return ``value`` constrained to ``[low, high]``."""
    return max(low, min(high, value))


def clamp_phase(phase: PhaseSettings) -> PhaseSettings:
    """Return a copy of ``phase`` with pressure clamped to safe bounds."""
    return dataclasses.replace(
        phase,
        target_pressure_bar=clamp(phase.target_pressure_bar, PRESSURE_MIN_BAR, PRESSURE_MAX_BAR),
    )


def clamp_profile(profile: ExtractionProfile) -> ExtractionProfile:
    """Return a copy of ``profile`` with temperature and pressures clamped."""
    return dataclasses.replace(
        profile,
        temp_c=clamp(profile.temp_c, TEMP_MIN_C, TEMP_MAX_C),
        phases=tuple(clamp_phase(phase) for phase in profile.phases),
    )


def pressures_within_hardware(pressures: Iterable[float], hardware: HardwareProfile) -> bool:
    """Return whether every pressure is within the hardware's capability."""
    return all(pressure <= hardware.max_pressure_bar for pressure in pressures)


def is_machine_supported(profile: ExtractionProfile, hardware: HardwareProfile) -> bool:
    """Return whether every phase's pressure is within the hardware's capability."""
    return pressures_within_hardware((phase.target_pressure_bar for phase in profile.phases), hardware)
