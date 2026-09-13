"""Tests for the .idx/.slog binary parser and writer."""

import pytest

from nine_bars.fixtures.generate import baseline_shot, corrected_shot
from nine_bars.mcp.binary import ParseError, pack_index, parse_index, parse_shot, to_telemetry, write_slog
from nine_bars.mcp.types import IndexEntry


@pytest.mark.parametrize("version", [4, 5])
def test_slog_round_trips(version: int) -> None:
    for shot in (baseline_shot(), corrected_shot()):
        data = write_slog(shot, version=version)

        assert to_telemetry(parse_shot(data)) == shot


def test_index_round_trips() -> None:
    entries = [IndexEntry(shot_id="shot-1", timestamp_ms=0, duration_ms=30_000)]

    assert parse_index(pack_index(entries)) == entries


def test_parse_index_rejects_bad_magic() -> None:
    with pytest.raises(ParseError):
        parse_index(b"\x00" * 64)


def test_parse_shot_rejects_bad_magic() -> None:
    with pytest.raises(ParseError):
        parse_shot(b"\x00" * 64)


def test_parse_shot_rejects_old_version() -> None:
    data = bytearray(write_slog(baseline_shot(), version=5))
    data[4] = 3

    with pytest.raises(ParseError):
        parse_shot(bytes(data))


def test_parse_shot_rejects_unknown_field_bits() -> None:
    data = bytearray(write_slog(baseline_shot()))
    header_size = int.from_bytes(data[28:32], "little")
    data[32 + header_size] |= 0x80

    with pytest.raises(ParseError):
        parse_shot(bytes(data))


def test_parse_shot_rejects_truncated() -> None:
    data = write_slog(baseline_shot())

    with pytest.raises(ParseError):
        parse_shot(data[:20])
