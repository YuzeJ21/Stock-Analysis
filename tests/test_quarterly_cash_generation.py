import math

import pytest

from src.earnings_nowcast_contract import QuarterlyActual
from src.quarterly_cash_generation import (
    QuarterlyBusinessObservation,
    derive_quarterly_business_metrics,
)


def _observation(
    period="2025-Q1",
    metric="cash_from_operations",
    value=100.0,
    **overrides,
):
    year = int(period[:4])
    quarter = int(period[-1])
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    values = {
        "ticker": "syn1",
        "fiscal_period": period,
        "period_end_date": f"{year}-{month_day}",
        "metric": metric,
        "value": value,
        "currency": "usd",
        "unit_scale": 1.0,
        "accounting_basis": "gaap",
        "duration_basis": "three_months",
        "source": "synthetic_test_fixture",
        "source_ref": f"fixture:{period}:{metric}",
        "published_at": "2025-05-15T12:00:00+00:00",
        "retrieved_at": "2026-07-18T12:00:00+00:00",
        "q4_evidence_state": "explicit_filed_quarter" if quarter == 4 else "not_q4",
        "supersedes_source_ref": None,
    }
    values.update(overrides)
    return QuarterlyBusinessObservation(**values)


def _actual(
    period="2025-Q1",
    *,
    revenue=200.0,
    currency="USD",
    unit_scale=1.0,
    basis="gaap",
    source_ref=None,
):
    year = int(period[:4])
    quarter = int(period[-1])
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    return QuarterlyActual(
        ticker="SYN1",
        fiscal_period=period,
        period_end_date=f"{year}-{month_day}",
        reported_at="2025-05-15T12:00:00+00:00",
        revenue_actual=revenue,
        eps_actual=None,
        source="synthetic_test_fixture",
        source_ref=source_ref or f"fixture:{period}:revenue",
        retrieved_at="2026-07-18T12:00:00+00:00",
        revenue_currency=currency,
        revenue_unit_scale=unit_scale,
        revenue_basis=basis,
    )


def test_observation_normalizes_identity_and_preserves_reported_capex_sign():
    row = _observation(metric="capital_expenditures", value=-20.0)

    assert row.ticker == "SYN1"
    assert row.currency == "USD"
    assert row.metric == "capital_expenditures"
    assert row.value == -20.0
    assert row.published_at == "2025-05-15T12:00:00+00:00"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"metric": "ebitda"}, "unsupported quarterly business metric"),
        ({"fiscal_period": "2025-FY"}, "fiscal_period must use"),
        ({"value": math.inf}, "value must be finite"),
        ({"unit_scale": 0}, "unit_scale must be positive"),
        ({"published_at": "2025-05-15T12:00:00"}, "timezone-aware"),
        ({"currency": ""}, "currency is required"),
    ],
)
def test_observation_rejects_invalid_evidence(overrides, message):
    with pytest.raises(ValueError, match=message):
        _observation(**overrides)


def test_observation_requires_explicit_q4_and_rejects_q4_state_on_other_quarters():
    with pytest.raises(ValueError, match="Q4 requires explicit filed-quarter evidence"):
        _observation(period="2025-Q4", q4_evidence_state="not_q4")
    with pytest.raises(ValueError, match="non-Q4 evidence must use not_q4"):
        _observation(period="2025-Q1", q4_evidence_state="explicit_filed_quarter")


def test_derivation_uses_explicit_formula_and_preserves_component_sources():
    result = derive_quarterly_business_metrics(
        "SYN1",
        [
            _observation(metric="operating_income", value=50.0),
            _observation(metric="cash_from_operations", value=60.0),
            _observation(metric="capital_expenditures", value=-20.0),
        ],
        [_actual(revenue=200.0)],
    )

    points = {point.metric: point for point in result.points}
    assert points["operating_margin"].value == 0.25
    assert points["free_cash_flow"].value == 40.0
    assert points["fcf_margin"].value == 0.20
    assert points["free_cash_flow"].source_refs == (
        "fixture:2025-Q1:cash_from_operations",
        "fixture:2025-Q1:capital_expenditures",
    )
    assert points["operating_margin"].source_refs == (
        "fixture:2025-Q1:operating_income",
        "fixture:2025-Q1:revenue",
    )
    assert result.blockers == ()
    assert result.supplied_observation_count == 3


def test_derivation_filters_post_cutoff_without_fabricating_points():
    result = derive_quarterly_business_metrics(
        "SYN1",
        [_observation(published_at="2026-01-01T00:00:00+00:00")],
        [_actual()],
        as_of="2025-12-31T23:59:59+00:00",
    )

    assert result.points == ()
    assert "2025-Q1:cash_from_operations:post_cutoff" in result.blockers


def test_derivation_resolves_explicit_revision_lineage():
    original = _observation(
        metric="operating_income",
        value=40.0,
        source_ref="fixture:operating:original",
    )
    revised = _observation(
        metric="operating_income",
        value=50.0,
        source_ref="fixture:operating:revised",
        supersedes_source_ref="fixture:operating:original",
    )

    result = derive_quarterly_business_metrics("SYN1", [original, revised], [_actual()])
    point = next(point for point in result.points if point.metric == "operating_margin")

    assert point.value == 0.25
    assert point.source_refs[0] == "fixture:operating:revised"
    assert result.revision_count == 1


def test_ambiguous_capex_blocks_only_fcf_metrics():
    observations = [
        _observation(metric="operating_income", value=50.0),
        _observation(metric="cash_from_operations", value=60.0),
        _observation(metric="capital_expenditures", value=-20.0, source_ref="fixture:capex:a"),
        _observation(metric="capital_expenditures", value=-30.0, source_ref="fixture:capex:b"),
    ]

    result = derive_quarterly_business_metrics("SYN1", observations, [_actual()])
    points = {point.metric: point for point in result.points}

    assert points["operating_margin"].value == 0.25
    assert "free_cash_flow" not in points
    assert "fcf_margin" not in points
    assert "2025-Q1:capital_expenditures:ambiguous_revision" in result.blockers


@pytest.mark.parametrize(
    "overrides",
    [
        {"currency": "CAD"},
        {"unit_scale": 1_000.0},
        {"accounting_basis": "adjusted"},
        {"duration_basis": "year_to_date"},
        {"period_end_date": "2025-03-30"},
    ],
)
def test_incompatible_components_do_not_create_free_cash_flow(overrides):
    cfo = _observation(metric="cash_from_operations", value=60.0)
    capex = _observation(metric="capital_expenditures", value=-20.0, **overrides)

    result = derive_quarterly_business_metrics("SYN1", [cfo, capex], [_actual()])

    assert not any(point.metric in {"free_cash_flow", "fcf_margin"} for point in result.points)
    assert "2025-Q1:free_cash_flow:incompatible_components" in result.blockers


def test_incompatible_revenue_definition_blocks_margins_but_not_free_cash_flow():
    observations = [
        _observation(metric="operating_income", value=50.0, accounting_basis="reported"),
        _observation(metric="cash_from_operations", value=60.0, accounting_basis="reported"),
        _observation(metric="capital_expenditures", value=-20.0, accounting_basis="reported"),
    ]

    result = derive_quarterly_business_metrics("SYN1", observations, [_actual(basis="gaap")])
    points = {point.metric: point for point in result.points}

    assert points["free_cash_flow"].value == 40.0
    assert "operating_margin" not in points
    assert "fcf_margin" not in points
    assert "2025-Q1:operating_margin:incompatible_revenue" in result.blockers
    assert "2025-Q1:fcf_margin:incompatible_revenue" in result.blockers
