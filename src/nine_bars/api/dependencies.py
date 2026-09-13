"""Dependency container for the API layer."""

from __future__ import annotations

from dataclasses import dataclass

from nine_bars.adapters.ports import BrewLog, CoffeeResearcher, ProfileWriter, ShotSource
from nine_bars.events.bus import EventBus


@dataclass(frozen=True, slots=True)
class Dependencies:
    """The adapters wired at the composition root and available to routes."""

    brew_log: BrewLog
    shot_source: ShotSource
    profile_writer: ProfileWriter
    researcher: CoffeeResearcher
    event_bus: EventBus
