from dataclasses import replace
import math

import pytest

from src.daily_research_queue import (
    DailyQueueEvidence,
    compare_daily_queues,
    daily_queue_display_rows,
    daily_queue_summary_cards,
    evaluate_daily_queue,
)


def eligible_evidence(ticker: str = "ALFA") -> DailyQueueEvidence:
    return DailyQueueEvidence(
        ticker=ticker,
        company_name=f"{ticker} Company",
        observation_through_date="2026-07-30",
        momentum_ready=True,
        current_market_eligible=True,
        price_provenance_eligible=True,
        price_rights_eligible=True,
        price_field_scope_eligible=True,
        close=120.0,
        sma_50=110.0,
        sma_200=100.0,
        return_3m=0.12,
        return_6m=0.24,
        relative_return_vs_spy=0.08,
        valuation_state="ready",
        valuation_freshness_state="current",
        valuation_commercial_eligible=True,
        valuation_metric="price_to_fcf_per_share",
        valuation_percentile=35.0,
        free_cash_flow=125_000_000.0,
        revenue_growth=0.08,
        debt_to_equity=0.7,
        fundamentals_provenance_eligible=True,
        fundamentals_rights_eligible=True,
        fundamentals_field_scope_eligible=True,
    )


def test_exact_intersection_requires_every_approved_gate():
    result = evaluate_daily_queue((eligible_evidence(),))

    assert result.status == "eligible"
    assert [item.ticker for item in result.eligible] == ["ALFA"]
    assert result.eligible[0].blockers == ()
    assert result.withheld == ()


@pytest.mark.parametrize(
    ("changes", "blocker"),
    [
        ({"momentum_ready": False}, "momentum_not_ready"),
        ({"current_market_eligible": False}, "current_market_evidence_ineligible"),
        ({"price_provenance_eligible": False}, "price_provenance_ineligible"),
        ({"price_rights_eligible": False}, "price_rights_ineligible"),
        ({"price_field_scope_eligible": False}, "price_field_scope_ineligible"),
        ({"close": 109.0}, "price_not_above_sma50"),
        ({"sma_50": 99.0}, "sma50_not_above_sma200"),
        ({"return_3m": 0.0}, "three_month_return_not_positive"),
        ({"return_6m": -0.01}, "six_month_return_not_positive"),
        ({"relative_return_vs_spy": 0.0}, "spy_relative_return_not_positive"),
        ({"valuation_state": "insufficient_history"}, "valuation_not_ready"),
        ({"valuation_freshness_state": "stale"}, "valuation_stale"),
        ({"valuation_commercial_eligible": False}, "valuation_commercial_evidence_ineligible"),
        ({"valuation_percentile": 40.01}, "valuation_percentile_above_threshold"),
        ({"free_cash_flow": 0.0}, "free_cash_flow_not_positive"),
        ({"revenue_growth": -0.001}, "revenue_growth_negative"),
        ({"debt_to_equity": 2.01}, "debt_above_threshold"),
        ({"fundamentals_provenance_eligible": False}, "fundamentals_provenance_ineligible"),
        ({"fundamentals_rights_eligible": False}, "fundamentals_rights_ineligible"),
        ({"fundamentals_field_scope_eligible": False}, "fundamentals_field_scope_ineligible"),
    ],
)
def test_each_failed_gate_withholds(changes, blocker):
    item = evaluate_daily_queue((replace(eligible_evidence(), **changes),)).withheld[0]

    assert item.state == "withheld"
    assert blocker in item.blockers


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("close", None, "price_missing"),
        ("sma_50", math.nan, "sma50_missing"),
        ("sma_200", math.inf, "sma200_missing"),
        ("return_3m", None, "three_month_return_missing"),
        ("return_6m", math.nan, "six_month_return_missing"),
        ("relative_return_vs_spy", -math.inf, "spy_relative_return_missing"),
        ("valuation_percentile", None, "valuation_percentile_missing"),
        ("free_cash_flow", math.nan, "free_cash_flow_missing"),
        ("revenue_growth", None, "revenue_growth_missing"),
        ("debt_to_equity", math.inf, "debt_to_equity_missing"),
    ],
)
def test_missing_or_non_finite_quantitative_evidence_is_withheld(field, value, blocker):
    item = evaluate_daily_queue((replace(eligible_evidence(), **{field: value}),)).withheld[0]

    assert blocker in item.blockers


def test_percentile_and_debt_boundaries_are_inclusive():
    row = replace(eligible_evidence(), valuation_percentile=40.0, debt_to_equity=2.0)

    assert evaluate_daily_queue((row,)).eligible[0].ticker == "ALFA"


def test_results_and_blockers_are_deterministic_and_alphabetical():
    row = replace(
        eligible_evidence("ZETA"),
        momentum_ready=False,
        current_market_eligible=False,
        close=None,
    )

    result = evaluate_daily_queue((row, eligible_evidence("BETA"), eligible_evidence("ALFA")))

    assert [item.ticker for item in result.eligible] == ["ALFA", "BETA"]
    assert result.withheld[0].blockers[:3] == (
        "momentum_not_ready",
        "current_market_evidence_ineligible",
        "price_missing",
    )


def test_duplicate_ticker_evidence_is_rejected_instead_of_merged():
    with pytest.raises(ValueError, match="duplicate ticker evidence: ALFA"):
        evaluate_daily_queue((eligible_evidence(), eligible_evidence("alfa")))


def test_missing_baseline_never_labels_current_rows_as_new():
    current = evaluate_daily_queue((eligible_evidence("ALFA"),))

    comparison = compare_daily_queues(current, None)

    assert comparison.status == "baseline_missing"
    assert [item.ticker for item in comparison.current_eligible] == ["ALFA"]
    assert comparison.new_today == ()
    assert comparison.still_qualifies == ()
    assert comparison.exited_today == ()


def test_comparison_separates_new_still_and_exited_without_ranking():
    previous = evaluate_daily_queue((eligible_evidence("ALFA"), eligible_evidence("BETA")))
    current = evaluate_daily_queue(
        (
            eligible_evidence("ALFA"),
            eligible_evidence("GAMMA"),
            replace(eligible_evidence("BETA"), return_3m=-0.1),
        )
    )

    comparison = compare_daily_queues(current, previous)

    assert comparison.status == "comparable"
    assert [item.ticker for item in comparison.new_today] == ["GAMMA"]
    assert [item.ticker for item in comparison.still_qualifies] == ["ALFA"]
    assert [item.ticker for item in comparison.exited_today] == ["BETA"]
    assert comparison.exited_today[0].blockers == ("three_month_return_not_positive",)


def test_display_payload_is_ticker_bound_and_contains_no_ranking_or_action_fields():
    comparison = compare_daily_queues(
        evaluate_daily_queue((eligible_evidence("ALFA"),)),
        None,
    )

    rows = daily_queue_display_rows(comparison)
    cards = daily_queue_summary_cards(comparison)
    forbidden_keys = {
        "score",
        "rank",
        "recommendation",
        "probability",
        "expected_return",
        "target_price",
        "position_size",
        "action",
    }
    rendered = " ".join(
        str(value)
        for payload in (*rows, *cards)
        for key, value in payload.items()
        if key.lower() not in forbidden_keys
    ).lower()

    assert rows[0]["Ticker"] == "ALFA"
    assert rows[0]["Open Company Workbench"] == (
        "?mode=research&page=company-workbench&ticker=ALFA"
    )
    assert not any(key.lower() in forbidden_keys for payload in (*rows, *cards) for key in payload)
    for prohibited in ("buy", "sell", "expected return", "target price", "position size"):
        assert prohibited not in rendered
    assert "research candidate" in rendered


def test_empty_input_is_a_truthful_withheld_state():
    result = evaluate_daily_queue(())
    comparison = compare_daily_queues(result, None)

    assert result.status == "withheld"
    assert result.eligible == ()
    assert result.withheld == ()
    assert comparison.current_eligible == ()
    assert "No company currently passes every required evidence gate." in result.message
