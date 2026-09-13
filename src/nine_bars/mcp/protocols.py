"""Ports for the device transport layer."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nine_bars.mcp.types import DeviceProfile


@runtime_checkable
class DeviceTransport(Protocol):
    """The single hardware-facing boundary: fetch and save device history bytes."""

    async def fetch_index(self) -> bytes: ...
    async def fetch_shot(self, shot_id: str) -> bytes: ...
    async def save_profile(self, profile: DeviceProfile) -> bytes: ...
