"""Tests for physics helpers and channeling-risk language."""

import pytest

from nine_bars.domain.models import ShotTelemetry
from nine_bars.domain.physics import channeling_risk, flow_deviation, ratio, summarize


def test_ratio_is_yield_over_dose() -> None:
    assert ratio(18.0, 36.0) == pytest.approx(2.0)


def test_ratio_rejects_non_positive_dose() -> None:
    with pytest.raises(ValueError):
        ratio(0.0, 36.0)


def test_flow_deviation_within_envelope_is_zero() -> None:
    assert flow_deviation(2.0, (1.0, 3.0)) == 0.0


def test_flow_deviation_below_envelope_is_negative() -> None:
    assert flow_deviation(0.5, (1.0, 3.0)) == pytest.approx(-0.5)


def test_flow_deviation_above_envelope_is_positive() -> None:
    assert flow_deviation(3.5, (1.0, 3.0)) == pytest.approx(0.5)


def test_channeling_risk_indicated_on_pressure_drop_and_flow_gain() -> None:
    pressure = ((0.0, 9.0), (10.0, 9.0), (20.0, 4.0))
    flow = ((0.0, 1.0), (10.0, 1.2), (20.0, 4.0))

    report = channeling_risk(pressure, flow)

    assert report.evidence_strength == "indicated"


def test_channeling_risk_suggestive_on_partial_signal() -> None:
    pressure = ((0.0, 9.0), (10.0, 9.0), (20.0, 4.0))
    flow = ((0.0, 1.0), (10.0, 1.0), (20.0, 1.1))

    report = channeling_risk(pressure, flow)

    assert report.evidence_strength == "suggestive"


def test_channeling_risk_unconfirmed_when_no_signal() -> None:
    pressure = ((0.0, 9.0), (10.0, 9.0), (20.0, 9.0))
    flow = ((0.0, 1.0), (10.0, 1.0), (20.0, 1.0))

    report = channeling_risk(pressure, flow)

    assert report.evidence_strength == "unconfirmed"


def test_channeling_risk_never_claims_certainty() -> None:
    pressure = ((0.0, 9.0), (10.0, 9.0), (20.0, 4.0))
    flow = ((0.0, 1.0), (10.0, 1.2), (20.0, 4.0))

    report = channeling_risk(pressure, flow)

    assert "confirm" not in report.explanation.lower()
    assert "certain" not in report.explanation.lower()


def test_summarize_derives_metrics() -> None:
    shot = ShotTelemetry(
        shot_id="s1",
        machine_ref="gm-1",
        dose_in_g=18.0,
        dose_out_g=36.0,
        pressure_curve=((0.0, 2.0), (10.0, 9.0), (20.0, 8.0)),
        flow_curve=((0.0, 0.0), (10.0, 2.0), (20.0, 2.5)),
        temperature_curve=((0.0, 93.0), (20.0, 92.0)),
        weight_curve=((0.0, 0.0), (20.0, 36.0)),
    )

    summary = summarize(shot)

    assert summary.peak_pressure_bar == pytest.approx(9.0)
    assert summary.avg_temp_c == pytest.approx(92.5)
    assert summary.brew_ratio == pytest.approx(2.0)
    assert summary.duration_s == pytest.approx(20.0)
