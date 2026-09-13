"""Tests for deterministic profile validation rules."""

from nine_bars.domain.models import ExtractionProfile, HardwareProfile, PhaseSettings
from nine_bars.domain.rules import (
    clamp_profile,
    is_machine_supported,
    validate_safety_bounds,
    validate_stop_start,
)


def _profile(phases: tuple[PhaseSettings, ...], temp_c: float = 93.0) -> ExtractionProfile:
    return ExtractionProfile(
        name="p",
        dose_g=18.0,
        yield_g=36.0,
        ratio=2.0,
        temp_c=temp_c,
        grind_desc="medium",
        phases=phases,
    )


def test_stop_start_flags_zero_pressure_phase() -> None:
    phases = (PhaseSettings("preinfuse", 3.0, 5.0), PhaseSettings("pause", 0.0, 3.0))

    issues = validate_stop_start(phases)

    assert len(issues) == 1
    assert issues[0].code == "stop_start_pressure"
    assert issues[0].severity == "warning"


def test_stop_start_clean_profile_has_no_issues() -> None:
    phases = (PhaseSettings("ramp", 3.0, 5.0), PhaseSettings("hold", 9.0, 20.0))

    assert validate_stop_start(phases) == []


def test_safety_bounds_flags_temp_out_of_range() -> None:
    profile = _profile((PhaseSettings("hold", 9.0, 20.0),), temp_c=110.0)

    issues = validate_safety_bounds(profile)

    assert any(issue.code == "temp_out_of_range" for issue in issues)


def test_safety_bounds_flags_pressure_out_of_range() -> None:
    profile = _profile((PhaseSettings("hold", 13.0, 20.0),))

    issues = validate_safety_bounds(profile)

    assert any(issue.code == "pressure_out_of_range" for issue in issues)


def test_safety_bounds_clean_profile_has_no_issues() -> None:
    profile = _profile((PhaseSettings("hold", 9.0, 20.0),))

    assert validate_safety_bounds(profile) == []


def test_clamp_profile_clamps_temp_and_pressure() -> None:
    profile = _profile((PhaseSettings("hold", 13.0, 20.0),), temp_c=110.0)

    clamped = clamp_profile(profile)

    assert clamped.temp_c == 100.0
    assert clamped.phases[0].target_pressure_bar == 12.0


def test_is_machine_supported_respects_hardware_limit() -> None:
    hardware = HardwareProfile(name="limited", max_pressure_bar=9.0)

    assert is_machine_supported(_profile((PhaseSettings("hold", 8.0, 20.0),)), hardware)
    assert not is_machine_supported(_profile((PhaseSettings("hold", 10.0, 20.0),)), hardware)
