"""Domain events emitted as the dial-in workflow progresses.

Events are pure value objects: they carry the relevant payload and no
timestamp. Timing and identity are added by the event bus at the application
edge, keeping the domain free of any clock.
"""

from __future__ import annotations

from dataclasses import dataclass

from nine_bars.domain.models import (
    Coffee,
    ExtractionProfile,
    NextAction,
    ShotSummary,
    TasteFeedback,
)


@dataclass(frozen=True, slots=True)
class CoffeeOnboarded:
    coffee: Coffee


@dataclass(frozen=True, slots=True)
class ProfileDraftCreated:
    profile: ExtractionProfile


@dataclass(frozen=True, slots=True)
class ShotObserved:
    shot: ShotSummary


@dataclass(frozen=True, slots=True)
class TasteRecorded:
    feedback: TasteFeedback


@dataclass(frozen=True, slots=True)
class NextActionProposed:
    action: NextAction


@dataclass(frozen=True, slots=True)
class ProfileDeployed:
    draft_id: str
    profile_id: str


@dataclass(frozen=True, slots=True)
class ProfileDeployFailed:
    draft_id: str
    error: str


type DomainEvent = (
    CoffeeOnboarded
    | ProfileDraftCreated
    | ShotObserved
    | TasteRecorded
    | NextActionProposed
    | ProfileDeployed
    | ProfileDeployFailed
)
