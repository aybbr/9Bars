"""Tests for the gated device profile writer."""

import asyncio

from nine_bars.adapters.device_profile_writer import DeviceProfileWriter
from nine_bars.domain.models import ExtractionProfile, HardwareProfile, PhaseSettings, ProfileDraft
from nine_bars.mcp.transports import FixtureTransport


def _run(coro):
    return asyncio.run(coro)


def _draft(pressure_bar: float = 9.0) -> ProfileDraft:
    profile = ExtractionProfile(
        name="p1",
        dose_g=18.0,
        yield_g=36.0,
        ratio=2.0,
        temp_c=93.0,
        grind_desc="medium",
        phases=(PhaseSettings("hold", pressure_bar, 20.0),),
    )
    return ProfileDraft(profile=profile, rationale="baseline")


def _writer(tmp_path, max_pressure_bar: float = 12.0) -> DeviceProfileWriter:
    return DeviceProfileWriter(
        FixtureTransport(tmp_path),
        HardwareProfile(name="limited", max_pressure_bar=max_pressure_bar),
    )


def test_upload_without_token_fails_closed(tmp_path) -> None:
    result = _run(_writer(tmp_path).upload(_draft(), ""))

    assert result.status == "failed"
    assert result.message == "approval_required"


def test_upload_with_token_deploys(tmp_path) -> None:
    result = _run(_writer(tmp_path).upload(_draft(), "token"))

    assert result.status == "deployed"
    assert result.profile_id == "p1"


def test_upload_rejects_pressure_over_hardware(tmp_path) -> None:
    result = _run(_writer(tmp_path, max_pressure_bar=9.0).upload(_draft(pressure_bar=12.0), "token"))

    assert result.status == "failed"
    assert result.message == "pressure_exceeds_hardware"


def test_read_back_returns_deployed_profile(tmp_path) -> None:
    writer = _writer(tmp_path)

    _run(writer.upload(_draft(), "token"))

    assert _run(writer.read_back("p1")).name == "p1"
