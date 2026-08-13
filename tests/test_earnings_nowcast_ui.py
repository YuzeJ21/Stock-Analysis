from __future__ import annotations

import json

from src.earnings_nowcast_report import build_nowcast_packet
from src.earnings_nowcast_ui import (
    nowcast_data_health_card,
    nowcast_public_answers,
    nowcast_state_label,
    nowcast_summary_cards,
)


def _packet() -> dict[str, object]:
    return build_nowcast_packet(
        "tests/fixtures/earnings_nowcast",
        ticker="SYN1",
        as_of_timestamp="2026-01-31T23:59:59Z",
    )


def test_blocked_nowcast_shows_no_numeric_forecast():
    cards = nowcast_summary_cards(None, ticker="NVDA")
    rendered = json.dumps(cards)

    assert "Open Data Health" in rendered
    assert "revenue_midpoint" not in rendered
    assert "eps_midpoint" not in rendered
    assert "baseline_ready" not in rendered


def test_ready_nowcast_keeps_evidence_and_model_details_advanced():
    cards = nowcast_summary_cards(_packet(), ticker="SYN1")

    assert cards[0]["title"] == "Earnings Outlook"
    assert cards[0]["state"] == "baseline_ready"
    assert cards[0]["advanced_default_open"] is False
    assert "price reaction" not in json.dumps(cards).lower()
    assert "probability" not in cards[0]


def test_data_health_card_separates_usable_state_from_missing_real_evidence():
    card = nowcast_data_health_card(None, ticker="NVDA")

    assert card["title"] == "Earnings Nowcast"
    assert card["state"] == "blocked"
    assert "point-in-time consensus" in card["body"]
    assert card["advanced_default_open"] is False


def test_ready_card_shows_ranges_and_withheld_calibration_not_numeric_probability():
    card = nowcast_summary_cards(_packet(), ticker="SYN1")[0]
    rendered = json.dumps(card).lower()

    assert "revenue range" in rendered
    assert "eps range" in rendered
    assert "numerical surprise probability is withheld" in rendered
    assert "synthetic test evidence" in rendered


def test_public_answers_follow_reviewer_question_order():
    answers = nowcast_public_answers(_packet(), ticker="SYN1")

    assert list(answers) == [
        "eligibility",
        "actuals",
        "consensus",
        "revenue",
        "eps",
        "evidence_context",
        "withheld",
        "next_action",
    ]
    assert answers["eligibility"]["status"] == "synthetic_test_only"
    assert answers["actuals"]["status"] == "synthetic_test_only"
    assert "test-only" in answers["actuals"]["answer"]
    assert "Revenue range" in answers["revenue"]["answer"]
    assert "EPS range" in answers["eps"]["answer"]
    assert "test-only" in answers["evidence_context"]["answer"]
    assert "probability" in answers["withheld"]["answer"].lower()


def test_blocked_public_answers_expose_no_numbers_or_synthetic_evidence():
    answers = nowcast_public_answers(None, ticker="NVDA")
    rendered = json.dumps(answers)

    assert answers["actuals"]["status"] == "blocked"
    assert answers["revenue"]["status"] == "withheld"
    assert answers["eps"]["status"] == "withheld"
    assert "midpoint" not in rendered
    assert not any(character.isdigit() for character in answers["revenue"]["answer"])
    assert "SYN" not in rendered
    assert answers["next_action"]["answer"] == "Open Data Health"
    assert answers["eligibility"]["status"] == "eligibility_unverified"
    assert "not been verified" in answers["eligibility"]["answer"]


def test_internal_states_have_plain_english_labels():
    assert nowcast_state_label("baseline_ready") == "Forecast range ready"
    assert nowcast_state_label("signal_context_ready") == "Evidence context ready"
    assert nowcast_state_label("backtest_insufficient") == "Backtest evidence insufficient"
    assert nowcast_state_label("backtest_ready") == "Backtest ready; probability withheld"
    assert nowcast_state_label("calibrated") == "Calibrated probability ready"
    assert nowcast_state_label("blocked") == "Source evidence required"
    assert nowcast_state_label("excluded") == "Not eligible"


def test_summary_card_body_presents_public_answers_in_review_order():
    body = nowcast_summary_cards(_packet(), ticker="SYN1")[0]["body"]

    labels = ["Eligibility:", "Actuals:", "Consensus:", "Revenue:", "EPS:", "Context:", "Withheld:", "Next:"]
    positions = [body.index(label) for label in labels]
    assert positions == sorted(positions)
    assert body.count("\n") == 7


def test_real_packet_explains_metric_definitions_and_forecast_horizon():
    packet = _packet()
    packet["evidence_scope"] = "source_backed_preview_only"
    packet["forecast"]["expected_report_date"] = "2026-04-30"
    packet["forecast"]["forecast_horizon_days"] = 89
    packet["metric_definitions"] = {
        "revenue": {"currency": "USD", "unit_scale": 1_000_000, "basis": "reported"},
        "eps": {
            "currency": "USD",
            "basis": "gaap",
            "share_basis": "diluted",
            "operations_basis": "continuing_operations",
            "split_adjustment_basis": "split_adjusted",
        },
    }

    answers = nowcast_public_answers(packet, ticker="REAL")

    combined = answers["revenue"]["answer"] + answers["eps"]["answer"]
    assert "USD millions" in combined
    assert "GAAP diluted EPS" in combined
    assert "89-day forecast horizon" in combined
    assert "expected report date 2026-04-30" in combined
