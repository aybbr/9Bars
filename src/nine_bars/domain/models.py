"""Domain models for the espresso dial-in workflow.

Every model is an immutable ``@dataclass(frozen=True, slots=True)`` value
object. This module is pure: it performs no I/O and reads no clock, network,
or storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Sample = tuple[float, float]
"""A single telemetry sample as ``(time_s, value)``."""


class ChangedVariable(StrEnum):
    """The single dial-in variable an agent is allowed to change per shot."""

    GRIND = "grind"
    DOSE = "dose"
    RATIO = "ratio"
    TEMPERATURE = "temperature"
    PROFILE_PHASE = "profile_phase"


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """A single piece of evidence with its origin and confidence.

    ``kind`` is derived from ``source``: inferred items are always hypotheses
    and can never masquerade as facts.
    """

    source: Literal["web", "user_history", "inferred"]
    text: str
    url: str | None = None
    confidence: float = 0.5

    @property
    def kind(self) -> Literal["fact", "hypothesis"]:
        return "hypothesis" if self.source == "inferred" else "fact"


@dataclass(frozen=True, slots=True)
class Coffee:
    """A coffee's identity plus its researched attributes."""

    coffee_id: str
    name: str
    roaster: str | None = None
    origin: str | None = None
    process: str | None = None
    roast_level: str | None = None
    roast_date: str | None = None
    tasting_notes: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()


@dataclass(frozen=True, slots=True)
class Setup:
    """The user's machine, grinder, and preferences."""

    machine: str
    grinder: str
    basket_size_g: float
    preferred_dose_g: float
    preferred_ratio: float
    preferred_temp_c: float
    grinder_setting: str


@dataclass(frozen=True, slots=True)
class PhaseSettings:
    """A single phase of an extraction profile."""

    name: str
    target_pressure_bar: float
    duration_s: float
    target_flow_g_s: float | None = None


@dataclass(frozen=True, slots=True)
class ExtractionProfile:
    """A device-facing extraction profile (recipe plus phases)."""

    name: str
    dose_g: float
    yield_g: float
    ratio: float
    temp_c: float
    grind_desc: str
    phases: tuple[PhaseSettings, ...] = ()


@dataclass(frozen=True, slots=True)
class ShotSummary:
    """Derived metrics for one completed shot."""

    shot_id: str
    machine_ref: str
    dose_in_g: float
    dose_out_g: float
    peak_pressure_bar: float
    avg_temp_c: float
    brew_ratio: float
    duration_s: float
    coffee_id: str | None = None


@dataclass(frozen=True, slots=True)
class ShotTelemetry:
    """Raw time series plus doses for one shot."""

    shot_id: str
    machine_ref: str
    dose_in_g: float
    dose_out_g: float
    pressure_curve: tuple[Sample, ...] = ()
    flow_curve: tuple[Sample, ...] = ()
    temperature_curve: tuple[Sample, ...] = ()
    weight_curve: tuple[Sample, ...] = ()
    coffee_id: str | None = None


@dataclass(frozen=True, slots=True)
class TasteFeedback:
    """Structured sensory feedback for one shot (ratings 1-5).

    ``acidity``, ``sweetness``, ``bitterness``, ``body``, ``aroma``, and
    ``finish`` describe the taste on a 1-5 intensity scale; ``overall`` is the
    drinker's holistic judgement. The decision rules only consume the original
    four (``acidity``, ``sweetness``, ``body``, ``overall``); the extra axes are
    stored and surfaced but do not yet drive a recommendation.
    """

    shot_id: str
    acidity: int
    sweetness: int
    body: int
    overall: int
    bitterness: int = 3
    aroma: int = 3
    finish: int = 3
    note: str | None = None


@dataclass(frozen=True, slots=True)
class NextAction:
    """A single proposed change for the next shot."""

    changed_variable: ChangedVariable
    current_value: float | str
    proposed_value: float | str
    rationale: str
    confidence: float


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    """Capabilities of a supported machine (GaggiMate/Gaggiuino)."""

    name: str
    max_pressure_bar: float


TEMP_MIN_C = 25.0
TEMP_MAX_C = 100.0
PRESSURE_MIN_BAR = 0.0
PRESSURE_MAX_BAR = 12.0

GAGGIAMATE = HardwareProfile(name="gaggimate", max_pressure_bar=PRESSURE_MAX_BAR)
GAGGIUINO_API = HardwareProfile(name="gaggiuino", max_pressure_bar=PRESSURE_MAX_BAR)


@dataclass(frozen=True, slots=True)
class ProfileDraft:
    """A proposed extraction profile with its rationale and evidence."""

    profile: ExtractionProfile
    rationale: str
    assumptions: tuple[str, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfileDeployResult:
    """The outcome of uploading a profile to the machine."""

    profile_id: str
    status: Literal["deployed", "failed"]
    deployed_profile: ExtractionProfile | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class CoffeeQuery:
    """A research query for onboarding a new coffee."""

    text: str
    kind: Literal["name", "url", "free_text"] = "free_text"


@dataclass(frozen=True, slots=True)
class CoffeeResearch:
    """Sourced research findings plus a synthesized coffee draft."""

    evidence: tuple[EvidenceItem, ...]
    coffee: Coffee
