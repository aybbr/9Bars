"""Tests for pure research text/evidence helpers."""

from nine_bars.domain.models import CoffeeQuery, EvidenceItem
from nine_bars.research.extract import (
    Extraction,
    dedupe_evidence,
    slug,
    strip_html_to_text,
    synthesize_coffee,
)


def test_strip_html_to_text_removes_non_content_and_decodes_entities() -> None:
    html = (
        "<html><head><style>.x{color:red}</style>"
        "<script>var a = 1;</script></head>"
        "<body><h1>Coffee</h1><p>Notes: jasmine &amp; bergamot.</p></body></html>"
    )

    assert strip_html_to_text(html) == "Coffee Notes: jasmine & bergamot."


def test_strip_html_to_text_collapses_whitespace() -> None:
    html = "<p>  jasmine   bergamot\t\nstone fruit  </p>"

    assert strip_html_to_text(html) == "jasmine bergamot stone fruit"


def test_dedupe_evidence_drops_repeated_sources() -> None:
    first = EvidenceItem(source="web", url="https://x.co", text="Origin Guji")
    duplicate = EvidenceItem(source="web", url="https://x.co", text="Origin Guji")
    normalized = EvidenceItem(source="web", url="https://x.co", text="  ORIGIN   guji ")
    other = EvidenceItem(source="web", url="https://y.co", text="Origin Guji")

    assert dedupe_evidence([first, duplicate, normalized, other]) == (first, other)


def test_slug_is_lowercase_hyphenated() -> None:
    assert slug("Ethiopia Guji Washed") == "ethiopia-guji-washed"


def test_synthesize_coffee_maps_fields_and_sources() -> None:
    facts = (
        EvidenceItem(source="web", url="https://x.co", text="Origin Guji, Ethiopia"),
        EvidenceItem(source="web", url="https://y.co", text="Washed process"),
    )
    extraction = Extraction(name="Ethiopia Guji", roaster="The Barn", origin="Guji, Ethiopia", facts=facts)

    coffee = synthesize_coffee(CoffeeQuery(text="ignored"), extraction)

    assert coffee.name == "Ethiopia Guji"
    assert coffee.roaster == "The Barn"
    assert coffee.origin == "Guji, Ethiopia"
    assert coffee.coffee_id == "ethiopia-guji"
    assert coffee.sources == ("https://x.co", "https://y.co")
    assert coffee.evidence == facts


def test_synthesize_coffee_leaves_missing_fields_none() -> None:
    coffee = synthesize_coffee(CoffeeQuery(text="Some Coffee"), Extraction())

    assert coffee.name == "Some Coffee"
    assert coffee.roaster is None
    assert coffee.origin is None
    assert coffee.process is None
    assert coffee.sources == ()
    assert coffee.evidence == ()
