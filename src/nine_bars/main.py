"""FastAPI application factory, composition root, and process entrypoint."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

from nine_bars.adapters.device_profile_writer import DeviceProfileWriter
from nine_bars.adapters.duckdb_brewlog import DuckDBBrewLog
from nine_bars.adapters.fixture_shot_source import FixtureShotSource
from nine_bars.adapters.ports import CoffeeResearcher
from nine_bars.agent.activity import AgentActivityBuffer
from nine_bars.api.dependencies import Dependencies
from nine_bars.api.router import router
from nine_bars.config import Settings, get_settings
from nine_bars.domain.models import GAGGIAMATE
from nine_bars.events.bus import EventBus
from nine_bars.mcp.protocols import DeviceTransport
from nine_bars.mcp.transports import FixtureTransport, LiveTransport
from nine_bars.research.extractor import NoopFactExtractor, PromptFactExtractor
from nine_bars.research.llm import DeepSeekChatModel
from nine_bars.research.researcher import WebResearcher
from nine_bars.web import router as web_router

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_UI_DIR = Path(__file__).resolve().parents[2] / "web" / "out"


def build_researcher(settings: Settings) -> CoffeeResearcher:
    """Construct the coffee researcher, backed by DeepSeek when a key is set."""
    if settings.deepseek_api_key:
        model = DeepSeekChatModel(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
        extractor: NoopFactExtractor | PromptFactExtractor = PromptFactExtractor(model.complete)
    else:
        extractor = NoopFactExtractor()
    return WebResearcher(extractor=extractor, timeout=settings.research_timeout_s)


def build_transport(settings: Settings) -> DeviceTransport:
    """Select the device transport: live when ``device_host`` is set, else fixtures."""
    if settings.device_host:
        return LiveTransport(settings.device_host)
    return FixtureTransport(_FIXTURES_DIR)


def build_dependencies(settings: Settings) -> Dependencies:
    """Construct the concrete adapters (composition root)."""
    transport = build_transport(settings)
    return Dependencies(
        brew_log=DuckDBBrewLog(settings.duckdb_path),
        shot_source=FixtureShotSource(_FIXTURES_DIR),
        profile_writer=DeviceProfileWriter(transport, GAGGIAMATE),
        researcher=build_researcher(settings),
        event_bus=EventBus(),
    )


def create_app(deps: Dependencies | None = None) -> FastAPI:
    """Create and return the 9Bars FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.state.deps = deps if deps is not None else build_dependencies(settings)
    app.state.activity = AgentActivityBuffer()
    app.state.agents = {}
    app.include_router(router)
    app.include_router(web_router)
    _mount_ui(app)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        """Liveness/readiness probe used by Railway and Docker health checks."""
        return {"status": "ok"}

    return app


def _mount_ui(app: FastAPI) -> None:
    """Serve the Next.js static export at ``/ui`` (no-op when it has not been built)."""

    @app.get("/ui", include_in_schema=False)
    @app.get("/ui/", include_in_schema=False)
    async def ui_index() -> FileResponse:
        return FileResponse(_UI_DIR / "index.html")

    @app.get("/ui/{path:path}", include_in_schema=False)
    async def ui(path: str) -> FileResponse:
        candidate = _UI_DIR / path
        if candidate.is_file():
            return FileResponse(candidate)
        as_html = _UI_DIR / f"{path}.html"
        if as_html.is_file():
            return FileResponse(as_html)
        index = candidate / "index.html"
        if index.is_file():
            return FileResponse(index)
        return FileResponse(_UI_DIR / "index.html")


def main() -> None:
    """Run the API server (entrypoint for the ``nine-bars`` console script)."""
    settings = get_settings()
    uvicorn.run(create_app(), host=settings.host, port=settings.port, log_level=settings.log_level)
