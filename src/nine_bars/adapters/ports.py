"""Ports (Protocols) defining the application's integration seams.

Every integration point is an exchangeable adapter. Concrete implementations
are constructed at the composition root, never inside call sites. All methods
are async and return domain types.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nine_bars.domain.models import (
    Coffee,
    CoffeeQuery,
    CoffeeResearch,
    ExtractionProfile,
    NextAction,
    ProfileDeployResult,
    ProfileDraft,
    ShotSummary,
    ShotTelemetry,
    TasteFeedback,
)


@runtime_checkable
class ShotSource(Protocol):
    """Read-only access to machine shot telemetry and history."""

    async def latest_shot(self) -> ShotTelemetry | None: ...
    async def get_shot(self, shot_id: str) -> ShotTelemetry: ...
    async def history(self, coffee_id: str | None, limit: int) -> list[ShotSummary]: ...


@runtime_checkable
class ProfileWriter(Protocol):
    """Gated write path for deploying profiles to the machine."""

    async def upload(self, draft: ProfileDraft, approval_token: str) -> ProfileDeployResult: ...
    async def read_back(self, profile_id: str) -> ExtractionProfile: ...


@runtime_checkable
class CoffeeResearcher(Protocol):
    """Researches a coffee and returns sourced evidence."""

    async def lookup(self, query: CoffeeQuery) -> CoffeeResearch: ...


@runtime_checkable
class BrewLog(Protocol):
    """Persists the learning history: coffees, shots, feedback, drafts, actions."""

    async def save_coffee(self, coffee: Coffee) -> None: ...
    async def list_coffees(self) -> list[Coffee]: ...
    async def save_shot(self, shot: ShotSummary) -> None: ...
    async def get_shot(self, shot_id: str) -> ShotSummary: ...
    async def save_feedback(self, shot_id: str, feedback: TasteFeedback) -> None: ...
    async def get_feedback(self, shot_id: str) -> TasteFeedback: ...
    async def save_draft(self, draft: ProfileDraft) -> str: ...
    async def get_draft(self, draft_id: str) -> ProfileDraft: ...
    async def save_deployment(self, draft_id: str, result: ProfileDeployResult, token: str) -> None: ...
    async def get_deployment(self, draft_id: str) -> ProfileDeployResult | None: ...
    async def save_next_action(self, coffee_id: str, action: NextAction) -> None: ...
    async def shots_for_coffee(self, coffee_id: str) -> list[ShotSummary]: ...
    async def next_actions(self, coffee_id: str) -> list[NextAction]: ...
    async def reset(self) -> None: ...
