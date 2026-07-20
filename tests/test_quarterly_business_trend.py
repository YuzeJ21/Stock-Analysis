from src.earnings_nowcast_contract import QuarterlyActual
import csv

from src.quarterly_cash_generation import QuarterlyBusinessObservation

from src.quarterly_business_trend import (
    build_quarterly_trend_packet,
    load_quarterly_actuals_csv,
    quarterly_trend_rows,
)


def _actual(
    period: str,
    *,
    revenue: float | None = None,
    eps: float | None = None,
    source_ref: str | None = None,
    supersedes: str | None = None,
    revenue_currency: str = "USD",
    revenue_basis: str = "reported",
    eps_basis: str = "gaap",
    split_adjustment_basis: str = "as_reported",
) -> QuarterlyActual:
    year = int(period[:4])
    quarter = int(period[-1])
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    return QuarterlyActual(
        ticker="SYN1",
        fiscal_period=period,
        period_end_date=f"{year}-{month_day}",
        reported_at=f"{year + (1 if quarter == 4 else 0)}-{('02-15' if quarter == 4 else '05-15')}T12:00:00+00:00",
        revenue_actual=revenue,
        eps_actual=eps,
        source="synthetic_test_fixture",
        source_ref=source_ref or f"fixture:{period}",
        retrieved_at="2026-07-17T12:00:00+00:00",
        revenue_currency=revenue_currency,
        revenue_unit_scale=1.0,
        revenue_basis=revenue_basis,
        eps_currency="USD",
        eps_basis=eps_basis,
        eps_share_basis="diluted",
        eps_operations_basis="reported",
        split_adjustment_basis=split_adjustment_basis,
        supersedes_source_ref=supersedes,
    )


def _business_observation(
    period: str,
    metric: str,
    value: float,
    *,
    source_ref: str | None = None,
    supersedes: str | None = None,
) -> QuarterlyBusinessObservation:
    year = int(period[:4])
    quarter = int(period[-1])
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    return QuarterlyBusinessObservation(
        ticker="SYN1",
        fiscal_period=period,
        period_end_date=f"{year}-{month_day}",
        metric=metric,
        value=value,
        currency="USD",
        unit_scale=1.0,
        accounting_basis="reported",
        duration_basis="three_months",
        source="synthetic_test_fixture",
        source_ref=source_ref or f"fixture:{period}:{metric}",
        published_at=f"{year + (1 if quarter == 4 else 0)}-{('02-15' if quarter == 4 else '05-15')}T12:00:00+00:00",
        retrieved_at="2026-07-18T12:00:00+00:00",
        q4_evidence_state="explicit_filed_quarter" if quarter == 4 else "not_q4",
        supersedes_source_ref=supersedes,
    )


def _business_history() -> list[QuarterlyBusinessObservation]:
    values = {
        "2024-Q1": {"operating_income": 20, "cash_from_operations": 24, "capital_expenditures": -8},
        "2024-Q4": {"operating_income": 20, "cash_from_operations": 30, "capital_expenditures": -10},
        "2025-Q1": {"operating_income": 30, "cash_from_operations": 36, "capital_expenditures": -12},
    }
    return [
        _business_observation(period, metric, value)
        for period, metrics in values.items()
        for metric, value in metrics.items()
    ]


def test_quarterly_trend_calculates_sequential_and_year_over_year_only_from_explicit_periods():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [
            _actual("2024-Q1", revenue=80, eps=0.8),
            _actual("2024-Q4", revenue=100, eps=1.0),
            _actual("2025-Q1", revenue=120, eps=1.2),
        ],
        as_of="2026-07-17T23:59:59+00:00",
    )

    assert packet.status == "ready"
    assert packet.latest_fiscal_period == "2025-Q1"
    assert packet.revenue.latest_value == 120
    assert packet.revenue.sequential_change_pct == 20.0
    assert packet.revenue.year_over_year_change_pct == 50.0
    assert packet.eps.sequential_change_pct == 20.0
    assert packet.eps.year_over_year_change_pct == 50.0
    assert packet.withheld_metrics == ("operating_margin", "free_cash_flow", "fcf_margin")
    assert packet.q4_policy == "explicit_filed_quarter_only"


def test_quarterly_trend_keeps_supplemental_metrics_withheld_without_observations():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [_actual("2025-Q1", revenue=120, eps=1.2)],
    )

    assert packet.operating_margin.status == "withheld"
    assert packet.free_cash_flow.status == "withheld"
    assert packet.fcf_margin.status == "withheld"
    assert packet.withheld_metrics == ("operating_margin", "free_cash_flow", "fcf_margin")


def test_quarterly_trend_composes_supplemental_changes_without_changing_revenue_or_eps():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [
            _actual("2024-Q1", revenue=80, eps=0.8),
            _actual("2024-Q4", revenue=100, eps=1.0),
            _actual("2025-Q1", revenue=120, eps=1.2),
        ],
        business_observations=_business_history(),
    )

    assert packet.revenue.latest_value == 120
    assert packet.revenue.sequential_change_pct == 20.0
    assert packet.eps.latest_value == 1.2
    assert packet.eps.year_over_year_change_pct == 50.0
    assert packet.operating_margin.status == "ready"
    assert packet.operating_margin.latest_value == 0.25
    assert packet.operating_margin.sequential_change_pct == 25.0
    assert packet.operating_margin.year_over_year_change_pct == 0.0
    assert packet.free_cash_flow.status == "ready"
    assert packet.free_cash_flow.latest_value == 24.0
    assert packet.free_cash_flow.sequential_change_pct == 20.0
    assert packet.free_cash_flow.year_over_year_change_pct == 50.0
    assert packet.fcf_margin.status == "ready"
    assert packet.fcf_margin.latest_value == 0.2
    assert packet.fcf_margin.sequential_change_pct == 0.0
    assert packet.fcf_margin.year_over_year_change_pct == 0.0
    assert packet.withheld_metrics == ()


def test_quarterly_trend_keeps_ambiguous_capex_blocker_independent():
    observations = [
        _business_observation("2025-Q1", "operating_income", 30),
        _business_observation("2025-Q1", "cash_from_operations", 36),
        _business_observation("2025-Q1", "capital_expenditures", -12, source_ref="fixture:capex:a"),
        _business_observation("2025-Q1", "capital_expenditures", -18, source_ref="fixture:capex:b"),
    ]

    packet = build_quarterly_trend_packet(
        "SYN1",
        [_actual("2025-Q1", revenue=120, eps=1.2)],
        business_observations=observations,
    )

    assert packet.revenue.status == "partial"
    assert packet.eps.status == "partial"
    assert packet.operating_margin.status == "partial"
    assert packet.operating_margin.latest_value == 0.25
    assert packet.free_cash_flow.status == "blocked"
    assert packet.fcf_margin.status == "blocked"
    assert "ambiguous" in packet.free_cash_flow.withheld_reason


def test_free_cash_flow_remains_independent_when_revenue_actuals_are_missing():
    observations = [
        _business_observation("2025-Q1", "cash_from_operations", 36),
        _business_observation("2025-Q1", "capital_expenditures", -12),
    ]

    packet = build_quarterly_trend_packet(
        "SYN1",
        [],
        business_observations=observations,
    )

    assert packet.status == "blocked"
    assert packet.revenue.status == "blocked"
    assert packet.free_cash_flow.status == "partial"
    assert packet.free_cash_flow.latest_value == 24.0
    assert packet.fcf_margin.status == "blocked"


def test_quarterly_trend_resolves_explicit_revision_lineage():
    original = _actual("2025-Q4", revenue=100, eps=1.0, source_ref="fixture:original")
    revised = _actual(
        "2025-Q4",
        revenue=110,
        eps=1.1,
        source_ref="fixture:revised",
        supersedes="fixture:original",
    )

    packet = build_quarterly_trend_packet("SYN1", [original, revised])

    assert packet.latest_fiscal_period == "2025-Q4"
    assert packet.revenue.latest_value == 110
    assert packet.revenue.latest_source_ref == "fixture:revised"
    assert packet.revision_count == 1


def test_quarterly_trend_fails_closed_for_conflicting_unversioned_periods():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [
            _actual("2025-Q4", revenue=100, eps=1.0, source_ref="fixture:a"),
            _actual("2025-Q4", revenue=130, eps=1.3, source_ref="fixture:b"),
        ],
    )

    assert packet.status == "blocked"
    assert packet.revenue.status == "blocked"
    assert packet.eps.status == "blocked"
    assert packet.ambiguous_periods == ("2025-Q4",)
    assert "ambiguous" in packet.revenue.withheld_reason


def test_quarterly_trend_withholds_incompatible_metric_definitions_and_missing_comparisons():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [
            _actual("2024-Q4", revenue=100, eps=1.0, revenue_currency="USD", eps_basis="gaap"),
            _actual("2025-Q1", revenue=120, eps=1.2, revenue_currency="CAD", eps_basis="adjusted"),
        ],
    )

    assert packet.revenue.status == "partial"
    assert packet.revenue.sequential_change_pct is None
    assert packet.revenue.year_over_year_change_pct is None
    assert "incompatible" in packet.revenue.withheld_reason
    assert packet.eps.sequential_change_pct is None
    assert "incompatible" in packet.eps.withheld_reason


def test_quarterly_trend_blocks_companyfacts_unverified_eps_but_keeps_revenue():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [
            _actual(
                "2024-Q1",
                revenue=80,
                eps=0.8,
                split_adjustment_basis="companyfacts_split_basis_unverified",
            ),
            _actual(
                "2024-Q4",
                revenue=100,
                eps=1.0,
                split_adjustment_basis="companyfacts_split_basis_unverified",
            ),
            _actual(
                "2025-Q1",
                revenue=120,
                eps=1.2,
                split_adjustment_basis="companyfacts_split_basis_unverified",
            ),
        ],
    )

    assert packet.status == "partial"
    assert packet.revenue.status == "ready"
    assert packet.revenue.latest_value == 120
    assert packet.eps.status == "blocked"
    assert packet.eps.latest_value is None
    assert "split basis" in packet.eps.withheld_reason.lower()


def test_quarterly_trend_never_uses_mixed_unverified_eps_periods():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [
            _actual("2024-Q1", revenue=80, eps=0.8),
            _actual("2024-Q4", revenue=100, eps=1.0),
            _actual(
                "2025-Q1",
                revenue=120,
                eps=99.0,
                split_adjustment_basis="companyfacts_split_basis_unverified",
            ),
        ],
    )

    assert packet.eps.status == "partial"
    assert packet.eps.latest_fiscal_period == "2024-Q4"
    assert packet.eps.latest_value == 1.0
    assert "2025-Q1" in packet.eps.withheld_reason


def test_quarterly_trend_does_not_derive_missing_q4_or_invent_unsupported_metrics():
    packet = build_quarterly_trend_packet("SYN1", [_actual("2025-Q3", revenue=90, eps=0.9)])
    rows = quarterly_trend_rows(packet)

    assert packet.status == "partial"
    assert packet.latest_fiscal_period == "2025-Q3"
    assert packet.revenue.sequential_change_pct is None
    assert "previous quarter unavailable" in packet.revenue.missing_comparisons
    assert {row["Metric"] for row in rows} == {"Revenue", "EPS", "Operating margin", "Free cash flow", "FCF margin"}
    unsupported = [row for row in rows if row["Metric"] == "Operating margin"][0]
    assert unsupported["State"] == "withheld"
    assert "explicit versioned quarterly source contract" in unsupported["Boundary"]


def test_quarterly_trend_filters_post_cutoff_and_other_tickers():
    future = _actual("2025-Q4", revenue=200, eps=2.0)
    other = QuarterlyActual(**{**future.__dict__, "ticker": "OTHER", "source_ref": "fixture:other"})

    packet = build_quarterly_trend_packet(
        "SYN1",
        [future, other],
        as_of="2025-01-01T00:00:00+00:00",
    )

    assert packet.status == "blocked"
    assert packet.available_periods == ()
    assert packet.message == "No source-backed quarterly actual is available by the review cutoff."


def test_quarterly_actual_csv_loader_validates_rows_and_reports_rejections(tmp_path):
    path = tmp_path / "quarterly_actuals.csv"
    fields = list(_actual("2025-Q1", revenue=100, eps=1.0).__dict__)
    valid = {key: getattr(_actual("2025-Q1", revenue=100, eps=1.0), key) for key in fields}
    invalid = {**valid, "fiscal_period": "2025-FY", "source_ref": "fixture:invalid"}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(valid)
        writer.writerow(invalid)

    result = load_quarterly_actuals_csv(path)

    assert [row.fiscal_period for row in result.actuals] == ["2025-Q1"]
    assert result.accepted_count == 1
    assert result.rejected_count == 1
    assert result.rejected_rows[0]["row_number"] == 3
    assert "fiscal_period" in result.rejected_rows[0]["reason"]
