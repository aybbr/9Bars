"""FastAPI routes: the HTTP surface shared by the agent and the web UI.

Enforces the human-in-the-loop invariant: the only machine write is the gated
``/draft/{id}/approve`` route, which mints an approval token server-side and
delegates to the ``ProfileWriter`` port.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from nine_bars.api.dependencies import Dependencies
from nine_bars.api.schemas import (
    ApproveRequest,
    CoffeeCreate,
    DraftCreate,
    FeedbackCreate,
    NextActionRequest,
    ResearchRequest,
)
from nine_bars.domain.decision import choose_single_variable
from nine_bars.domain.events import (
    CoffeeOnboarded,
    DomainEvent,
    NextActionProposed,
    ProfileDeployed,
    ProfileDeployFailed,
    ProfileDraftCreated,
    ShotObserved,
    TasteRecorded,
)
from nine_bars.domain.models import (
    Coffee,
    CoffeeQuery,
    CoffeeResearch,
    ExtractionProfile,
    NextAction,
    PhaseSettings,
    ProfileDeployResult,
    ProfileDraft,
    ShotSummary,
    TasteFeedback,
)
from nine_bars.events.bus import serialize

router = APIRouter(prefix="/api")

_ALL_EVENTS: tuple[type[DomainEvent], ...] = (
    CoffeeOnboarded,
    ProfileDraftCreated,
    ProfileDeployed,
    ProfileDeployFailed,
    ShotObserved,
    TasteRecorded,
    NextActionProposed,
)


def _deps(request: Request) -> Dependencies:
    deps = request.app.state.deps
    if not isinstance(deps, Dependencies):
        raise RuntimeError("dependencies not wired onto app.state.deps")
    return deps


Deps = Annotated[Dependencies, Depends(_deps)]


@router.get("/coffee")
async def list_coffees(deps: Deps) -> list[Coffee]:
    return await deps.brew_log.list_coffees()


@router.post("/coffee", status_code=201)
async def onboard_coffee(body: CoffeeCreate, deps: Deps) -> Coffee:
    coffee = Coffee(
        coffee_id=uuid.uuid4().hex,
        name=body.name,
        roaster=body.roaster,
        origin=body.origin,
        process=body.process,
        roast_level=body.roast_level,
        roast_date=body.roast_date,
        tasting_notes=tuple(body.tasting_notes),
    )
    await deps.brew_log.save_coffee(coffee)
    deps.event_bus.publish(CoffeeOnboarded(coffee))
    return coffee


@router.post("/coffee/research")
async def research_coffee(body: ResearchRequest, deps: Deps) -> CoffeeResearch:
    query = CoffeeQuery(text=body.text, kind=body.kind)
    return await deps.researcher.lookup(query)


@router.get("/coffee/{coffee_id}/shots")
async def coffee_shots(coffee_id: str, deps: Deps) -> list[ShotSummary]:
    return await deps.brew_log.shots_for_coffee(coffee_id)


@router.get("/coffee/{coffee_id}/latest-shot")
async def latest_shot(coffee_id: str, deps: Deps) -> ShotSummary:
    shots = await deps.brew_log.shots_for_coffee(coffee_id)
    if not shots:
        raise HTTPException(status_code=404, detail="no shots for coffee")
    return shots[-1]


@router.post("/draft", status_code=201)
async def create_draft(body: DraftCreate, deps: Deps) -> dict[str, str]:
    profile = ExtractionProfile(
        name=body.name,
        dose_g=body.dose_g,
        yield_g=body.yield_g,
        ratio=body.ratio,
        temp_c=body.temp_c,
        grind_desc=body.grind_desc,
        phases=tuple(
            PhaseSettings(
                name=phase.name,
                target_pressure_bar=phase.target_pressure_bar,
                duration_s=phase.duration_s,
                target_flow_g_s=phase.target_flow_g_s,
            )
            for phase in body.phases
        ),
    )
    draft = ProfileDraft(profile=profile, rationale=body.rationale, assumptions=tuple(body.assumptions))
    draft_id = await deps.brew_log.save_draft(draft)
    deps.event_bus.publish(ProfileDraftCreated(profile))
    return {"draft_id": draft_id}


@router.post("/draft/{draft_id}/approve")
async def approve_draft(draft_id: str, body: ApproveRequest, deps: Deps) -> ProfileDeployResult:
    if not body.user_confirmed:
        raise HTTPException(status_code=403, detail="approval_required")
    try:
        draft = await deps.brew_log.get_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="draft not found") from exc
    existing = await deps.brew_log.get_deployment(draft_id)
    if existing is not None:
        return existing
    token = secrets.token_urlsafe(16)
    result = await deps.profile_writer.upload(draft, token)
    await deps.brew_log.save_deployment(draft_id, result, token)
    if result.status == "deployed":
        deps.event_bus.publish(ProfileDeployed(draft_id=draft_id, profile_id=result.profile_id))
    else:
        deps.event_bus.publish(ProfileDeployFailed(draft_id=draft_id, error=result.message or "deploy_failed"))
    return result


@router.post("/feedback", status_code=201)
async def record_feedback(body: FeedbackCreate, deps: Deps) -> TasteFeedback:
    feedback = TasteFeedback(
        shot_id=body.shot_id,
        acidity=body.acidity,
        sweetness=body.sweetness,
        body=body.body,
        overall=body.overall,
        bitterness=body.bitterness,
        aroma=body.aroma,
        finish=body.finish,
        note=body.note,
    )
    await deps.brew_log.save_feedback(body.shot_id, feedback)
    deps.event_bus.publish(TasteRecorded(feedback))
    return feedback


@router.get("/shot/{shot_id}/feedback")
async def shot_feedback(shot_id: str, deps: Deps) -> TasteFeedback:
    try:
        return await deps.brew_log.get_feedback(shot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="no feedback for shot") from exc


@router.get("/events/stream")
async def events_stream(request: Request, deps: Deps) -> StreamingResponse:
    async def generate() -> AsyncIterator[str]:
        async for event in deps.event_bus.stream(*_ALL_EVENTS):
            yield f"data: {serialize(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/next-action")
async def next_action(body: NextActionRequest, deps: Deps) -> NextAction:
    shots = await deps.brew_log.shots_for_coffee(body.coffee_id)
    if not shots:
        raise HTTPException(status_code=404, detail="no shots for coffee")
    feedback = TasteFeedback(
        shot_id=shots[-1].shot_id,
        acidity=body.acidity,
        sweetness=body.sweetness,
        body=body.body,
        overall=body.overall,
    )
    action = choose_single_variable(shots, feedback)
    await deps.brew_log.save_next_action(body.coffee_id, action)
    deps.event_bus.publish(NextActionProposed(action))
    return action
