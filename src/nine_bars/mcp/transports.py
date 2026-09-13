"""Concrete device transports: fixture files and live HTTP/WS."""

from __future__ import annotations

from pathlib import Path

import httpx
import websockets

from nine_bars.mcp.types import DeviceProfile


class FixtureTransport:
    """Serves ``.slog``/``.idx`` files from a fixture directory."""

    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    async def fetch_index(self) -> bytes:
        return (self._fixture_dir / "index.idx").read_bytes()

    async def fetch_shot(self, shot_id: str) -> bytes:
        return (self._fixture_dir / f"{shot_id}.slog").read_bytes()

    async def save_profile(self, profile: DeviceProfile) -> bytes:
        return profile.name.encode("utf-8")


class LiveTransport:
    """Talks to a live machine over HTTP (index/shot) and WS (profile save).

    Reuses a single :class:`httpx.AsyncClient` for the HTTP paths. A client may
    be injected for testing (e.g. ``httpx.MockTransport``). Call
    :meth:`aclose` when the transport is no longer needed.
    """

    def __init__(
        self,
        host: str,
        use_ws: bool = True,
        timeout: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._host = host.rstrip("/")
        self._use_ws = use_ws
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def fetch_index(self) -> bytes:
        response = await self._client.get(f"{self._host}/api/history/index.bin")
        response.raise_for_status()
        return response.content

    async def fetch_shot(self, shot_id: str) -> bytes:
        response = await self._client.get(f"{self._host}/api/history/{shot_id}.slog")
        response.raise_for_status()
        return response.content

    async def save_profile(self, profile: DeviceProfile) -> bytes:
        if self._use_ws:
            async with websockets.connect(f"ws://{self._host}/ws") as ws:
                await ws.send(profile.model_dump_json())
                reply = await ws.recv()
                return reply.encode("utf-8") if isinstance(reply, str) else reply
        response = await self._client.post(f"{self._host}/api/profile", json=profile.model_dump())
        response.raise_for_status()
        return response.content
