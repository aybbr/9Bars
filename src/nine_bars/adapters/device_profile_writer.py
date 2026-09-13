"""A concrete :class:`ProfileWriter` that deploys approved profiles to the device.

This is the single gated machine-write path: it fails closed on a missing token,
rejects pressures above the hardware limit, then delegates to the transport.
"""

from __future__ import annotations

from nine_bars.domain.models import ExtractionProfile, HardwareProfile, ProfileDeployResult, ProfileDraft
from nine_bars.domain.rules import pressures_within_hardware
from nine_bars.mcp.protocols import DeviceTransport
from nine_bars.mcp.types import DeviceProfile


class DeviceProfileWriter:
    """Writes approved profiles to the device."""

    def __init__(self, transport: DeviceTransport, hardware: HardwareProfile) -> None:
        self._transport = transport
        self._hardware = hardware
        self._deployed: dict[str, ExtractionProfile] = {}

    async def upload(self, draft: ProfileDraft, approval_token: str) -> ProfileDeployResult:
        if not approval_token:
            return ProfileDeployResult(profile_id="", status="failed", message="approval_required")
        device_profile = DeviceProfile.from_extraction(draft.profile)
        if not pressures_within_hardware(
            (phase.target_pressure_bar for phase in device_profile.phases), self._hardware
        ):
            return ProfileDeployResult(profile_id="", status="failed", message="pressure_exceeds_hardware")
        await self._transport.save_profile(device_profile)
        self._deployed[draft.profile.name] = draft.profile
        return ProfileDeployResult(profile_id=draft.profile.name, status="deployed")

    async def read_back(self, profile_id: str) -> ExtractionProfile:
        return self._deployed[profile_id]
