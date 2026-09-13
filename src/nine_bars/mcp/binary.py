"""Pure binary parsers/writers for the device history format (``.idx``/``.slog``).

All integers are little-endian. Corrupt or unsupported input raises a typed
``ParseError``; ``struct.error`` never leaks. These functions perform no I/O.

Self-consistent placeholder format:

- **Index**: ``b"SIDX"`` + ``<H`` version + ``<H`` entry_size(128) + ``<I``
  entry_count + ``<I`` next_id + 16 padding, then ``entry_count`` fixed
  128-byte entries (``shot_id`` as 64-byte ASCII, ``<Q`` timestamp_ms, ``<I``
  duration_ms, reserved).
- **Shot**: ``b"SHOT"`` + ``<B`` version + ``<I`` sample_count@16 + ``<I``
  duration_ms@20 + ``<I`` timestamp@24 + ``<I`` header_size@28, then a header
  block (length-prefixed shot_id/machine_ref/coffee_id strings + ``<dd``
  dose_in_g/dose_out_g), then ``sample_count`` samples on a uniform time grid.
  Each sample is a 1-byte bitmask (pressure/flow/temperature/weight) followed
  by the set fields scaled by 100 (pressure/flow/temperature/weight as uint16,
  flow as int16).
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

from nine_bars.domain.models import PRESSURE_MAX_BAR, PRESSURE_MIN_BAR, TEMP_MAX_C, TEMP_MIN_C, Sample, ShotTelemetry
from nine_bars.domain.physics import curve_duration_ms
from nine_bars.domain.rules import clamp
from nine_bars.mcp.types import IndexEntry, RawShot

INDEX_MAGIC = b"SIDX"
SHOT_MAGIC = b"SHOT"
INDEX_ENTRY_SIZE = 128
INDEX_HEADER_SIZE = 32
SHOT_HEADER_SIZE = 32
SCALE = 100.0

_BIT_PRESSURE = 0x01
_BIT_FLOW = 0x02
_BIT_TEMPERATURE = 0x04
_BIT_WEIGHT = 0x08
_KNOWN_BITS = _BIT_PRESSURE | _BIT_FLOW | _BIT_TEMPERATURE | _BIT_WEIGHT

_INDEX_HEADER = struct.Struct("<4sHHII")
_SHOT_HEADER = struct.Struct("<4sB11xIIII")


class ParseError(ValueError):
    """Raised when device history bytes are malformed or unsupported."""


def parse_index(data: bytes) -> list[IndexEntry]:
    """Parse a device history index (``.idx``) into entries."""
    if len(data) < INDEX_HEADER_SIZE:
        raise ParseError("index file too short")
    magic, _version, entry_size, entry_count, _next_id = _INDEX_HEADER.unpack_from(data)
    if magic != INDEX_MAGIC:
        raise ParseError("bad index magic")
    if entry_size != INDEX_ENTRY_SIZE:
        raise ParseError(f"unsupported index entry size {entry_size}")
    body = data[INDEX_HEADER_SIZE:]
    if len(body) < entry_count * entry_size:
        raise ParseError("truncated index entries")
    return [_parse_index_entry(body[i * entry_size : (i + 1) * entry_size]) for i in range(entry_count)]


def parse_shot(data: bytes) -> RawShot:
    """Parse a device shot (``.slog``) into a :class:`RawShot`."""
    if len(data) < SHOT_HEADER_SIZE:
        raise ParseError("shot file too short")
    magic, version, sample_count, duration_ms, _timestamp, header_size = _SHOT_HEADER.unpack_from(data)
    if magic != SHOT_MAGIC:
        raise ParseError("bad shot magic")
    if version < 4:
        raise ParseError(f"unsupported shot version {version}")
    header_end = SHOT_HEADER_SIZE + header_size
    if len(data) < header_end:
        raise ParseError("truncated shot header block")
    shot_id, machine_ref, coffee_id, dose_in, dose_out = _parse_shot_header(data[SHOT_HEADER_SIZE:header_end])
    pressure, flow, temperature, weight = _parse_samples(data[header_end:], sample_count)
    return RawShot(
        shot_id=shot_id,
        machine_ref=machine_ref,
        coffee_id=coffee_id,
        dose_in_g=dose_in,
        dose_out_g=dose_out,
        duration_ms=duration_ms,
        pressure=tuple(pressure),
        flow=tuple(flow),
        temperature=tuple(temperature),
        weight=tuple(weight),
    )


def to_telemetry(raw: RawShot) -> ShotTelemetry:
    """Reconstruct a :class:`ShotTelemetry` from a :class:`RawShot`."""
    return ShotTelemetry(
        shot_id=raw.shot_id,
        machine_ref=raw.machine_ref,
        coffee_id=raw.coffee_id,
        dose_in_g=raw.dose_in_g,
        dose_out_g=raw.dose_out_g,
        pressure_curve=_curve(raw.duration_ms, raw.pressure),
        flow_curve=_curve(raw.duration_ms, raw.flow),
        temperature_curve=_curve(raw.duration_ms, raw.temperature),
        weight_curve=_curve(raw.duration_ms, raw.weight),
    )


def write_slog(shot: ShotTelemetry, version: int = 5) -> bytes:
    """Encode a shot as ``.slog`` bytes (inverse of :func:`parse_shot`)."""
    if version < 4:
        raise ValueError(f"unsupported shot version {version}")
    if not shot.pressure_curve:
        raise ValueError("cannot pack a shot without a pressure curve")
    n = len(shot.pressure_curve)
    for name, curve in (
        ("flow", shot.flow_curve),
        ("temperature", shot.temperature_curve),
        ("weight", shot.weight_curve),
    ):
        if curve and len(curve) != n:
            raise ValueError(f"{name} curve length {len(curve)} does not match pressure length {n}")
    duration_ms = curve_duration_ms(shot.pressure_curve)
    header_block = _pack_shot_header(shot)
    header = _SHOT_HEADER.pack(SHOT_MAGIC, version, n, duration_ms, 0, len(header_block))
    return header + header_block + _pack_samples(shot, n)


def pack_index(entries: Sequence[IndexEntry]) -> bytes:
    """Encode entries as ``.idx`` bytes (inverse of :func:`parse_index`)."""
    body = b"".join(_pack_index_entry(entry) for entry in entries)
    header = _INDEX_HEADER.pack(INDEX_MAGIC, 1, INDEX_ENTRY_SIZE, len(entries), 0)
    return header + b"\x00" * 16 + body


def _parse_index_entry(entry: bytes) -> IndexEntry:
    shot_id = entry[:64].split(b"\x00", 1)[0].decode("utf-8")
    timestamp_ms = struct.unpack_from("<Q", entry, 64)[0]
    duration_ms = struct.unpack_from("<I", entry, 72)[0]
    return IndexEntry(shot_id=shot_id, timestamp_ms=timestamp_ms, duration_ms=duration_ms)


def _pack_index_entry(entry: IndexEntry) -> bytes:
    shot_id = entry.shot_id.encode("utf-8")
    if len(shot_id) >= 64:
        raise ValueError("shot_id too long for index entry")
    return shot_id.ljust(64, b"\x00") + struct.pack("<QI", entry.timestamp_ms, entry.duration_ms) + b"\x00" * 52


def _parse_shot_header(block: bytes) -> tuple[str, str, str | None, float, float]:
    shot_id, offset = _read_len_str(block, 0)
    machine_ref, offset = _read_len_str(block, offset)
    coffee_id, offset = _read_len_str(block, offset)
    if offset + 16 > len(block):
        raise ParseError("truncated shot header block")
    dose_in, dose_out = struct.unpack_from("<dd", block, offset)
    return shot_id, machine_ref, coffee_id or None, dose_in, dose_out


def _pack_shot_header(shot: ShotTelemetry) -> bytes:
    return (
        _pack_len_str(shot.shot_id)
        + _pack_len_str(shot.machine_ref)
        + _pack_len_str(shot.coffee_id or "")
        + struct.pack("<dd", shot.dose_in_g, shot.dose_out_g)
    )


def _parse_samples(samples: bytes, count: int) -> tuple[list[float], list[float], list[float], list[float]]:
    pressure: list[float] = []
    flow: list[float] = []
    temperature: list[float] = []
    weight: list[float] = []
    offset = 0
    for _ in range(count):
        if offset >= len(samples):
            raise ParseError("truncated samples")
        bitmask = samples[offset]
        offset += 1
        if bitmask & ~_KNOWN_BITS:
            raise ParseError(f"unknown sample field bits: 0x{bitmask:02x}")
        if bitmask & _BIT_PRESSURE:
            pressure.append(_read_field(samples, offset, "<H"))
            offset += 2
        if bitmask & _BIT_FLOW:
            flow.append(_read_field(samples, offset, "<h"))
            offset += 2
        if bitmask & _BIT_TEMPERATURE:
            temperature.append(_read_field(samples, offset, "<H"))
            offset += 2
        if bitmask & _BIT_WEIGHT:
            weight.append(_read_field(samples, offset, "<H"))
            offset += 2
    if offset != len(samples):
        raise ParseError("trailing bytes after samples")
    return pressure, flow, temperature, weight


def _pack_samples(shot: ShotTelemetry, n: int) -> bytes:
    pressure = [value for _, value in shot.pressure_curve]
    flow = [value for _, value in shot.flow_curve]
    temperature = [value for _, value in shot.temperature_curve]
    weight = [value for _, value in shot.weight_curve]
    out = bytearray()
    for i in range(n):
        bitmask = _BIT_PRESSURE
        if flow:
            bitmask |= _BIT_FLOW
        if temperature:
            bitmask |= _BIT_TEMPERATURE
        if weight:
            bitmask |= _BIT_WEIGHT
        out.append(bitmask)
        out += struct.pack("<H", _scale(clamp(pressure[i], PRESSURE_MIN_BAR, PRESSURE_MAX_BAR)))
        if flow:
            out += struct.pack("<h", _scale(flow[i]))
        if temperature:
            out += struct.pack("<H", _scale(clamp(temperature[i], TEMP_MIN_C, TEMP_MAX_C)))
        if weight:
            out += struct.pack("<H", _scale(clamp(weight[i], 0.0, 600.0)))
    return bytes(out)


def _read_field(buf: bytes, offset: int, fmt: str) -> float:
    if offset + 2 > len(buf):
        raise ParseError("truncated sample field")
    (value,) = struct.unpack_from(fmt, buf, offset)
    return int(value) / SCALE


def _scale(value: float) -> int:
    return round(value * SCALE)


def _curve(duration_ms: int, values: tuple[float, ...]) -> tuple[Sample, ...]:
    n = len(values)
    if n == 0:
        return ()
    if n == 1:
        return ((0.0, values[0]),)
    step = duration_ms / 1000.0 / (n - 1)
    return tuple((step * i, value) for i, value in enumerate(values))


def _read_len_str(block: bytes, offset: int) -> tuple[str, int]:
    if offset >= len(block):
        raise ParseError("truncated string field")
    length = block[offset]
    offset += 1
    end = offset + length
    if end > len(block):
        raise ParseError("truncated string field")
    return block[offset:end].decode("utf-8"), end


def _pack_len_str(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if len(encoded) > 255:
        raise ValueError("string field too long")
    return bytes([len(encoded)]) + encoded
