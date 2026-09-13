"""The nine-bars-demo script: drive the agent through the four demo acts.

Uses a live DeepSeek model (set ``DEEPSEEK_API_KEY``) and the committed fixture
shots, replaying the dial-in arc offline on the device side. Prints the final
agent trace JSON, which the web UI reads as its activity panel.

This lives at the package root (not under ``nine_bars.agent``) because it is a
composition root: it wires the concrete adapters, which may import DuckDB.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from nine_bars.agent.activity import AgentActivityBuffer, extract_spans
from nine_bars.agent.agent import build_agent
from nine_bars.agent.model import AgentConfigurationError, build_model
from nine_bars.config import Settings
from nine_bars.domain.physics import summarize
from nine_bars.fixtures.generate import DEMO_COFFEE_ID, baseline_shot, corrected_shot
from nine_bars.main import build_dependencies

_ACTS = (
    f"A new bag of coffee just arrived (coffee id {DEMO_COFFEE_ID}). "
    "Research it and draft a starting extraction profile with a short rationale.",
    f"I pulled shot 1 of {DEMO_COFFEE_ID}. It tasted dry and harsh at the end. "
    "Save my feedback (overall 2, acidity 2, sweetness 2, body 2) and tell me the one change to make next.",
    f"I pulled shot 2 of {DEMO_COFFEE_ID} after your change. Much better: overall 4, acidity 3, sweetness 4, body 3. "
    "Review it and propose the single change to make next, if any.",
    f"Show me the full history and what we have learned about {DEMO_COFFEE_ID} so far.",
)


def main() -> None:
    """Entrypoint for the ``nine-bars-demo`` console script."""
    asyncio.run(_run())


async def _run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(duckdb_path=str(Path(tmp) / "demo.duckdb"))
        try:
            model = build_model(settings)
        except AgentConfigurationError as exc:
            print(f"error: {exc}")
            sys.exit(1)

        deps = build_dependencies(settings)
        agent = build_agent(deps, model)
        buffer = AgentActivityBuffer()

        for i, prompt in enumerate(_ACTS, start=1):
            if i == 2:
                await deps.brew_log.save_shot(summarize(baseline_shot()))
            elif i == 3:
                await deps.brew_log.save_shot(summarize(corrected_shot()))

            print(f"\n=== Act {i} ===")
            result = await agent.invoke_async(prompt)
            for span in extract_spans(result.metrics.traces):
                buffer.record(span)
            print(result.message)

        print("\n=== trace ===")
        print(buffer.to_json())


if __name__ == "__main__":
    main()
