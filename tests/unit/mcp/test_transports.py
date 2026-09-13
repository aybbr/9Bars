"""Tests for device transport structural conformance and the live HTTP paths."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from nine_bars.mcp.protocols import DeviceTransport
from nine_bars.mcp.transports import FixtureTransport, LiveTransport
from nine_bars.mcp.types import DevicePhase, DeviceProfile


def test_fixture_transport_satisfies_protocol(tmp_path: Path) -> None:
    assert isinstance(FixtureTransport(tmp_path), DeviceTransport)


def test_live_transport_satisfies_protocol() -> None:
    assert isinstance(LiveTransport("http://example.com"), DeviceTransport)


def _profile() -> DeviceProfile:
    return DeviceProfile(
        name="p1",
        dose_g=18.0,
        yield_g=36.0,
        temp_c=93.0,
        phases=[DevicePhase(name="hold", target_pressure_bar=9.0, duration_s=20.0)],
    )


def test_live_fetch_index() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/history/index.bin"
        return httpx.Response(200, content=b"INDEX")

    async def scenario() -> bytes:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        transport = LiveTransport("http://machine", client=client)
        try:
            return await transport.fetch_index()
        finally:
            await client.aclose()

    assert asyncio.run(scenario()) == b"INDEX"


def test_live_fetch_shot() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/history/1042.slog"
        return httpx.Response(200, content=b"SHOT")

    async def scenario() -> bytes:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        transport = LiveTransport("http://machine", client=client)
        try:
            return await transport.fetch_shot("1042")
        finally:
            await client.aclose()

    assert asyncio.run(scenario()) == b"SHOT"


def test_live_save_profile_http() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/profile"
        assert json.loads(request.content)["name"] == "p1"
        return httpx.Response(200, content=b"ok")

    async def scenario() -> bytes:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        transport = LiveTransport("http://machine", use_ws=False, client=client)
        try:
            return await transport.save_profile(_profile())
        finally:
            await client.aclose()

    assert asyncio.run(scenario()) == b"ok"


def test_live_http_error_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"missing")

    async def scenario() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        transport = LiveTransport("http://machine", client=client)
        try:
            await transport.fetch_shot("9999")
        finally:
            await client.aclose()

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(scenario())
