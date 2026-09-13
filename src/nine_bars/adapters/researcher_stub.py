"""A template-driven coffee researcher that never fabricates sourcing claims."""

from __future__ import annotations

from nine_bars.domain.models import Coffee, CoffeeQuery, CoffeeResearch


class ResearcherStub:
    """Fallback :class:`CoffeeResearcher` used when no search tool is configured.

    Returns an empty evidence set and a minimal ``Coffee`` built only from the
    query text. It never invents a roaster, origin, or source URL.
    """

    async def lookup(self, query: CoffeeQuery) -> CoffeeResearch:
        """Return empty evidence and a minimal coffee for ``query``."""
        return CoffeeResearch(
            evidence=(),
            coffee=Coffee(coffee_id=_slug(query.text), name=query.text),
        )


def _slug(text: str) -> str:
    return "-".join(text.lower().split())
