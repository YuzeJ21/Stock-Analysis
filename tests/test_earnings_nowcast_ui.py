from __future__ import annotations

import json

from src.earnings_nowcast_report import build_nowcast_packet
from src.earnings_nowcast_ui import nowcast_data_health_card, nowcast_summary_cards


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
