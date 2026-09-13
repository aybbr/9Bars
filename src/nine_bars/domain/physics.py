"""Pure physics helpers for espresso extraction.

Grounded in the poroelastic espresso-flow research (Waszkiewicz et al.,
Phys. Fluids 2026, arXiv:2512.21528). Encoded findings:

* Flow saturates as pressure rises once the puck compacts, so pressure is not
  a linear flow lever.
* A pressure drop coincident with rising flow is the signature of an opened
  channel; repeated or stop-start pressure application promotes delamination.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nine_bars.domain.models import Sample, ShotSummary, ShotTelemetry

EvidenceStrength = Literal["indicated", "suggestive", "unconfirmed"]

PRESSURE_DROP_BAR = 2.0
FLOW_GAIN_G_S = 1.0


@dataclass(frozen=True, slots=True)
class RiskReport:
    """A channeling-risk assessment. Never expresses certainty."""

    evidence_strength: EvidenceStrength
    explanation: str


def ratio(dose_g: float, yield_g: float) -> float:
    """Return the brew ratio ``yield_g / dose_g``.

    Args:
        dose_g: Weight of dry coffee in grams.
        yield_g: Weight of liquid in the cup in grams.

    Returns:
        The dimensionless brew ratio.

    Raises:
        ValueError: If ``dose_g`` is not positive.
    """
    if dose_g <= 0:
        raise ValueError(f"dose_g must be positive, got {dose_g}")
    return yield_g / dose_g


def flow_deviation(observed: float, expected_envelope: tuple[float, float]) -> float:
    """Return the signed deviation of ``observed`` flow from an expected band.

    Zero when within ``[lower, upper]``; negative when below the lower bound
    and positive when above the upper bound.
    """
    lower, upper = expected_envelope
    if observed < lower:
        return observed - lower
    if observed > upper:
        return observed - upper
    return 0.0


def channeling_risk(
    pressure_curve: tuple[Sample, ...],
    flow_curve: tuple[Sample, ...],
) -> RiskReport:
    """Assess channeling risk from pressure and flow curves.

    A pressure drop coincident with a flow gain after peak pressure suggests
    the puck stopped holding pressure — the sign of an opened channel. The
    result is always a hypothesis (``indicated``/``suggestive``), never a
    confirmation.
    """
    if not pressure_curve or not flow_curve:
        return RiskReport("unconfirmed", "Insufficient telemetry to assess channeling.")

    peak_pressure = max(value for _, value in pressure_curve)
    peak_time = next((t for t, value in pressure_curve if value == peak_pressure), 0.0)

    late_pressures = [value for t, value in pressure_curve if t >= peak_time]
    late_flows = [value for t, value in flow_curve if t >= peak_time]
    if not late_pressures or not late_flows:
        return RiskReport("unconfirmed", "Insufficient late-shot telemetry to assess channeling.")

    pressure_drop = peak_pressure - min(late_pressures)
    flow_gain = max(late_flows) - min(late_flows)

    if pressure_drop >= PRESSURE_DROP_BAR and flow_gain >= FLOW_GAIN_G_S:
        return RiskReport(
            "indicated",
            (
                f"Pressure fell {pressure_drop:.1f} bar while flow rose {flow_gain:.1f} g/s "
                "after peak pressure, which may indicate an opened channel. "
                "Verify with taste before acting."
            ),
        )
    if pressure_drop >= PRESSURE_DROP_BAR or flow_gain >= FLOW_GAIN_G_S:
        return RiskReport(
            "suggestive",
            (
                f"Pressure fell {pressure_drop:.1f} bar or flow rose {flow_gain:.1f} g/s; "
                "this suggests possible channeling but is not conclusive."
            ),
        )
    return RiskReport("unconfirmed", "Pressure and flow stayed coupled; no channeling signal.")


def summarize(shot: ShotTelemetry) -> ShotSummary:
    """Reduce raw telemetry to a derived :class:`ShotSummary`."""
    return ShotSummary(
        shot_id=shot.shot_id,
        machine_ref=shot.machine_ref,
        coffee_id=shot.coffee_id,
        dose_in_g=shot.dose_in_g,
        dose_out_g=shot.dose_out_g,
        peak_pressure_bar=_peak(shot.pressure_curve),
        avg_temp_c=_mean(shot.temperature_curve),
        brew_ratio=ratio(shot.dose_in_g, shot.dose_out_g) if shot.dose_in_g > 0 else 0.0,
        duration_s=(
            _curve_duration(shot.weight_curve)
            or _curve_duration(shot.flow_curve)
            or _curve_duration(shot.pressure_curve)
        ),
    )


def _peak(curve: tuple[Sample, ...], default: float = 0.0) -> float:
    return max((value for _, value in curve), default=default)


def _mean(curve: tuple[Sample, ...], default: float = 0.0) -> float:
    values = [value for _, value in curve]
    return sum(values) / len(values) if values else default


def _curve_duration(curve: tuple[Sample, ...]) -> float:
    if not curve:
        return 0.0
    return curve[-1][0] - curve[0][0]


def curve_duration_ms(curve: tuple[Sample, ...]) -> int:
    """Return a curve's duration in milliseconds (0 for fewer than two samples)."""
    if len(curve) < 2:
        return 0
    return round((curve[-1][0] - curve[0][0]) * 1000)
