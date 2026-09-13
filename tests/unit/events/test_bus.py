"""Tests for the event bus and SSE serialization."""

import asyncio
import json

from nine_bars.domain.events import ShotObserved, TasteRecorded
from nine_bars.domain.models import ShotSummary, TasteFeedback
from nine_bars.events.bus import EventBus, serialize


def _shot() -> ShotSummary:
    return ShotSummary(
        shot_id="s1",
        machine_ref="gm-1",
        dose_in_g=18.0,
        dose_out_g=36.0,
        peak_pressure_bar=9.0,
        avg_temp_c=93.0,
        brew_ratio=2.0,
        duration_s=30.0,
    )


def _feedback() -> TasteFeedback:
    return TasteFeedback(shot_id="s1", acidity=3, sweetness=3, body=3, overall=3)


def test_serialize_emits_typed_json() -> None:
    data = json.loads(serialize(ShotObserved(shot=_shot())))

    assert data["type"] == "ShotObserved"
    assert data["data"]["shot"]["shot_id"] == "s1"
    assert data["data"]["shot"]["brew_ratio"] == 2.0


def test_publish_delivers_to_subscriber() -> None:
    bus = EventBus()

    async def scenario() -> list[ShotObserved]:
        events: list[ShotObserved] = []
        ready = asyncio.Event()

        async def collect() -> None:
            async for event in bus.stream(ShotObserved, ready=ready):
                events.append(event)
                break

        task = asyncio.create_task(collect())
        await ready.wait()
        bus.publish(ShotObserved(shot=_shot()))
        await task
        return events

    events = asyncio.run(scenario())

    assert len(events) == 1
    assert events[0].shot.shot_id == "s1"


def test_publish_ignores_unsubscribed_types() -> None:
    bus = EventBus()

    async def scenario() -> list[ShotObserved]:
        events: list[ShotObserved] = []
        ready = asyncio.Event()

        async def collect() -> None:
            async for event in bus.stream(ShotObserved, ready=ready):
                events.append(event)
                break

        task = asyncio.create_task(collect())
        await ready.wait()
        bus.publish(TasteRecorded(feedback=_feedback()))  # no subscriber
        bus.publish(ShotObserved(shot=_shot()))
        await task
        return events

    events = asyncio.run(scenario())

    assert len(events) == 1
