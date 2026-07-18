from pathlib import Path

import pytest

from src.commercial_source_rights import (
    build_source_rights_registry,
    load_source_rights_registry,
)
from src.earnings_nowcast_contract import QuarterlyActual
from src.quarterly_cash_generation import QuarterlyBusinessObservation
from src.quarterly_cash_generation_adapter import (
    assess_quarterly_cash_generation_adapter,
)


def _rights_registry(
    *,
    commercial_use: str = "approved",
    supported_fields: list[str] | None = None,
):
    return build_source_rights_registry(
        [
            {
                "source_id": "synthetic_adapter",
                "display_name": "Synthetic adapter fixture",
                "permitted_use": "test_only",
                "commercial_use": commercial_use,
                "redistribution": "not_applicable_test_only",
                "storage_limits": "in_memory_test_only",
                "attribution": "synthetic test fixture",
                "rate_limits": "not_applicable_test_only",
                "authentication": "none",
                "expected_freshness": "not_applicable_test_only",
                "supported_fields": supported_fields
                or [
                    "operating_income",
                    "cash_from_operations",
                    "capital_expenditures",
                ],
                "fallback_priority": 1,
            }
        ]
    )


def _observation(
    period: str = "2025-Q1",
    metric: str = "cash_from_operations",
    value: float = 100.0,
    **overrides,
) -> QuarterlyBusinessObservation:
    year = int(period[:4])
    quarter = int(period[-1])
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    values = {
        "ticker": "SYN1",
        "fiscal_period": period,
        "period_end_date": f"{year}-{month_day}",
        "metric": metric,
        "value": value,
        "currency": "USD",
        "unit_scale": 1.0,
        "accounting_basis": "gaap",
        "duration_basis": "three_months",
        "source": "synthetic_adapter",
        "source_ref": f"fixture:{period}:{metric}",
        "published_at": f"{year + (1 if quarter == 4 else 0)}-05-15T12:00:00+00:00",
        "retrieved_at": "2026-07-18T12:00:00+00:00",
        "q4_evidence_state": "explicit_filed_quarter" if quarter == 4 else "not_q4",
        "supersedes_source_ref": None,
    }
    values.update(overrides)
    return QuarterlyBusinessObservation(**values)


def _actual(
    period: str = "2025-Q1",
    *,
    revenue: float = 200.0,
    **overrides,
) -> QuarterlyActual:
    year = int(period[:4])
    quarter = int(period[-1])
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    values = {
        "ticker": "SYN1",
        "fiscal_period": period,
        "period_end_date": f"{year}-{month_day}",
        "reported_at": f"{year + (1 if quarter == 4 else 0)}-05-15T12:00:00+00:00",
        "revenue_actual": revenue,
        "eps_actual": None,
        "source": "synthetic_test_fixture",
        "source_ref": f"fixture:{period}:revenue",
        "retrieved_at": "2026-07-18T12:00:00+00:00",
        "revenue_currency": "USD",
        "revenue_unit_scale": 1.0,
        "revenue_basis": "gaap",
    }
    values.update(overrides)
    return QuarterlyActual(**values)


def _complete_rows(period: str = "2025-Q1") -> list[QuarterlyBusinessObservation]:
    return [
        _observation(period, "operating_income", 50.0),
        _observation(period, "cash_from_operations", 60.0),
        _observation(period, "capital_expenditures", -20.0),
    ]


def _assess(
    observations,
    *,
    ticker: str = "SYN1",
    source_id: str = "synthetic_adapter",
    rights_registry=None,
    revenue_actuals=None,
    as_of: str | None = None,
):
    return assess_quarterly_cash_generation_adapter(
        ticker,
        source_id,
        observations,
        [_actual()] if revenue_actuals is None else revenue_actuals,
        rights_registry=rights_registry or _rights_registry(),
        as_of=as_of,
    )


def test_complete_one_company_batch_is_accepted_for_review_without_activation():
    result = assess_quarterly_cash_generation_adapter(
        "SYN1",
        "synthetic_adapter",
        _complete_rows(),
        [_actual(revenue=200.0)],
        rights_registry=_rights_registry(),
    )

    assert result.status == "accepted_for_review"
    assert result.blockers == ()
    assert result.accepted_observation_count == 3
    assert result.reviewed_metrics == (
        "capital_expenditures",
        "cash_from_operations",
        "operating_income",
    )
    assert result.derived_point_count == 3
    assert result.explicit_q4_periods == ()
    assert result.rights_status == "approved"
    assert result.production_activation is False
    assert result.readiness_promotions == ()


@pytest.mark.parametrize(
    ("ticker", "source_id", "observations", "blocker"),
    [
        ("", "synthetic_adapter", (), "ticker_required"),
        ("SYN1", "", (), "source_id_required"),
        ("SYN1", "synthetic_adapter", (), "observations_required"),
    ],
)
def test_required_identity_and_observations_fail_closed(
    ticker,
    source_id,
    observations,
    blocker,
):
    result = _assess(observations, ticker=ticker, source_id=source_id)

    assert result.status == "blocked"
    assert blocker in result.blockers
    assert result.accepted_observation_count == 0
    assert result.production_activation is False
    assert result.readiness_promotions == ()


def test_mixed_ticker_and_source_mismatch_are_reported_together():
    rows = [
        _observation(),
        _observation(ticker="OTHER", source_ref="fixture:other:ticker"),
        _observation(
            metric="operating_income",
            source="other_source",
            source_ref="fixture:other:source",
        ),
    ]

    result = _assess(rows)

    assert "mixed_ticker:OTHER" in result.blockers
    assert "source_mismatch:other_source" in result.blockers
    assert result.status == "blocked"


def test_unknown_or_unverified_rights_block_acceptance():
    unknown = _assess(_complete_rows(), source_id="unknown")
    unverified = _assess(
        _complete_rows(),
        rights_registry=_rights_registry(commercial_use="unverified"),
    )

    assert "source_rights:unknown_source" in unknown.blockers
    assert "source_rights:commercial_rights_unverified" in unverified.blockers


def test_approved_source_must_explicitly_support_every_component():
    result = _assess(
        _complete_rows(),
        rights_registry=_rights_registry(supported_fields=["operating_income"]),
    )

    assert result.blockers == (
        "source_fields_missing:capital_expenditures,cash_from_operations",
    )
    assert result.status == "blocked"


def test_post_cutoff_observations_block_acceptance():
    result = _assess(
        _complete_rows(),
        as_of="2025-05-14T23:59:59+00:00",
    )

    assert "2025-Q1:operating_income:post_cutoff" in result.blockers
    assert "2025-Q1:cash_from_operations:post_cutoff" in result.blockers
    assert "2025-Q1:capital_expenditures:post_cutoff" in result.blockers
    assert "complete_derived_period_required" in result.blockers
    assert result.status == "blocked"


def test_explicit_revision_leaf_is_accepted():
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
    rows = [
        original,
        revised,
        _observation(metric="cash_from_operations", value=60.0),
        _observation(metric="capital_expenditures", value=-20.0),
    ]

    result = _assess(rows)

    assert result.status == "accepted_for_review"
    assert result.blockers == ()
    assert result.accepted_observation_count == 4
    assert result.derived_point_count == 3


def test_ambiguous_revision_blocks_complete_period_acceptance():
    rows = [
        _observation(metric="operating_income", value=50.0),
        _observation(metric="cash_from_operations", value=60.0),
        _observation(
            metric="capital_expenditures",
            value=-20.0,
            source_ref="fixture:capex:a",
        ),
        _observation(
            metric="capital_expenditures",
            value=-30.0,
            source_ref="fixture:capex:b",
        ),
    ]

    result = _assess(rows)

    assert "2025-Q1:capital_expenditures:ambiguous_revision" in result.blockers
    assert "complete_derived_period_required" in result.blockers
    assert result.status == "blocked"


def test_missing_component_is_named_and_blocks_complete_period():
    rows = [
        _observation(metric="operating_income", value=50.0),
        _observation(metric="cash_from_operations", value=60.0),
    ]

    result = _assess(rows)

    assert "2025-Q1:missing_component:capital_expenditures" in result.blockers
    assert "complete_derived_period_required" in result.blockers
    assert result.status == "blocked"


def test_missing_revenue_preserves_fcf_but_blocks_complete_period_acceptance():
    result = _assess(_complete_rows(), revenue_actuals=[])

    assert "2025-Q1:operating_margin:incompatible_revenue" in result.blockers
    assert "2025-Q1:fcf_margin:incompatible_revenue" in result.blockers
    assert "complete_derived_period_required" in result.blockers
    assert result.derived_point_count == 1
    assert result.status == "blocked"


def test_incompatible_cash_flow_components_block_complete_period_acceptance():
    rows = [
        _observation(metric="operating_income", value=50.0),
        _observation(metric="cash_from_operations", value=60.0),
        _observation(metric="capital_expenditures", value=-20.0, currency="CAD"),
    ]

    result = _assess(rows)

    assert "2025-Q1:free_cash_flow:incompatible_components" in result.blockers
    assert "complete_derived_period_required" in result.blockers
    assert result.status == "blocked"


def test_explicit_filed_q4_batch_is_accepted_and_recorded():
    result = _assess(
        _complete_rows("2025-Q4"),
        revenue_actuals=[_actual("2025-Q4")],
    )

    assert result.status == "accepted_for_review"
    assert result.explicit_q4_periods == ("2025-Q4",)
    assert result.blockers == ()


def test_q4_without_explicit_filed_quarter_is_rejected_before_acceptance():
    with pytest.raises(ValueError, match="Q4 requires explicit filed-quarter evidence"):
        _observation("2025-Q4", q4_evidence_state="not_q4")


def test_checked_in_sec_rights_do_not_silently_claim_component_support():
    rows = [
        _observation(
            metric=row.metric,
            value=row.value,
            source="sec_companyfacts",
            source_ref=f"sec:{row.fiscal_period}:{row.metric}",
        )
        for row in _complete_rows()
    ]

    result = _assess(
        rows,
        source_id="sec_companyfacts",
        rights_registry=load_source_rights_registry(),
    )

    assert result.blockers == (
        "source_fields_missing:capital_expenditures,cash_from_operations,operating_income",
    )
    assert result.status == "blocked"


def test_adapter_acceptance_module_has_no_file_network_or_cli_surface():
    source = Path("src/quarterly_cash_generation_adapter.py").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for forbidden in (
        "argparse",
        "requests",
        "urllib",
        "Path(",
        ".open(",
        "read_text(",
        "write_text(",
        "csv",
        "json",
        "output_dir",
        "__main__",
    ):
        assert forbidden not in source
    assert "quarterly-cash-generation-adapter" not in makefile
