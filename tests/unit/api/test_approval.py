"""Tests for the gated profile approval flow."""

import asyncio

from fastapi.testclient import TestClient

from nine_bars.api.dependencies import Dependencies
from nine_bars.api.router import approve_draft
from nine_bars.api.schemas import ApproveRequest
from nine_bars.domain.events import ProfileDeployed
from nine_bars.domain.models import ExtractionProfile, PhaseSettings, ProfileDraft


def _draft_body() -> dict:
    return {
        "name": "p1",
        "dose_g": 18.0,
        "yield_g": 36.0,
        "ratio": 2.0,
        "temp_c": 93.0,
        "grind_desc": "medium",
        "phases": [{"name": "hold", "target_pressure_bar": 9.0, "duration_s": 20.0}],
        "rationale": "baseline",
        "assumptions": ["fresh beans"],
    }


def _draft() -> ProfileDraft:
    profile = ExtractionProfile(
        name="p1",
        dose_g=18.0,
        yield_g=36.0,
        ratio=2.0,
        temp_c=93.0,
        grind_desc="medium",
        phases=(PhaseSettings("hold", 9.0, 20.0),),
    )
    return ProfileDraft(profile=profile, rationale="baseline")


def test_approve_flow_end_to_end(client: TestClient) -> None:
    draft_id = client.post("/api/draft", json=_draft_body()).json()["draft_id"]

    response = client.post(f"/api/draft/{draft_id}/approve", json={"user_confirmed": True})

    assert response.status_code == 200
    assert response.json()["status"] == "deployed"
    assert response.json()["profile_id"] == "p1"


def test_approve_missing_draft_returns_404(client: TestClient) -> None:
    response = client.post("/api/draft/nonexistent/approve", json={"user_confirmed": True})

    assert response.status_code == 404


def test_approve_without_confirmation_returns_403(client: TestClient) -> None:
    draft_id = client.post("/api/draft", json=_draft_body()).json()["draft_id"]

    response = client.post(f"/api/draft/{draft_id}/approve", json={"user_confirmed": False})

    assert response.status_code == 403


def test_duplicate_approval_is_idempotent(client: TestClient) -> None:
    draft_id = client.post("/api/draft", json=_draft_body()).json()["draft_id"]

    first = client.post(f"/api/draft/{draft_id}/approve", json={"user_confirmed": True}).json()
    second = client.post(f"/api/draft/{draft_id}/approve", json={"user_confirmed": True}).json()

    assert first == second
    assert first["status"] == "deployed"


def test_approve_publishes_deployed_event(deps: Dependencies) -> None:
    draft_id = asyncio.run(deps.brew_log.save_draft(_draft()))

    async def scenario() -> list[ProfileDeployed]:
        events: list[ProfileDeployed] = []
        ready = asyncio.Event()

        async def collect() -> None:
            async for event in deps.event_bus.stream(ProfileDeployed, ready=ready):
                events.append(event)
                break

        task = asyncio.create_task(collect())
        await ready.wait()
        await approve_draft(draft_id, ApproveRequest(user_confirmed=True), deps)
        await task
        return events

    events = asyncio.run(scenario())

    assert len(events) == 1
    assert events[0].draft_id == draft_id
