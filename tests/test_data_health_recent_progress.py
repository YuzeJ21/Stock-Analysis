from __future__ import annotations

import pandas as pd

from src import data_health_recent_progress as recent_progress


def test_recent_progress_cards_missing_current_keeps_command_out_of_body():
    cards = recent_progress.readiness_recent_progress_cards(None)
    body = str(cards[0]["body"]).lower()

    assert cards[0]["title"] == "Readiness report missing"
    assert cards[0]["command"] == "make readiness"
    assert "open operator details" in body
    assert "make " not in body


def test_recent_progress_cards_show_current_only_baseline_without_prior_snapshot():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "QQQ"],
            "in_active_universe": [True, False, True],
            "price_ready": [True, False, True],
            "dcf_ready": [True, False, False],
            "peer_ready": [False, False, True],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "blocked_features": ["peer, earnings, analyst_estimates", "price, dcf, peer", "earnings, analyst_estimates"],
            "overall_readiness_state": ["partial", "blocked", "partial"],
            "updated_at": ["2026-05-28T00:00:00+00:00", "2026-05-28T00:00:00+00:00", "2026-05-28T00:00:00+00:00"],
        }
    )
    feature_summary = pd.DataFrame(
        {
            "feature": ["price", "peer"],
            "blocked_count": [1, 2],
        }
    )

    cards = recent_progress.readiness_recent_progress_cards(readiness, feature_summary_frame=feature_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "2/3 price-ready"
    assert cards[1]["title"] == "Current-only baseline"
    assert cards[1]["command"] == "make readiness-snapshot"
    assert "active universe: 2" in rendered
    assert "dcf-ready: 1" in rendered
    assert "peer-ready: 1" in rendered
    assert "peer: 2" in rendered
    assert "price: 1" in rendered
    assert "without pretending a delta exists" in rendered
    assert "save a baseline snapshot" in rendered
    assert "make " not in " ".join(str(card.get("body", "")) for card in cards).lower()
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_recent_progress_cards_compare_prior_snapshot_and_newly_ready_tickers():
    current = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "in_active_universe": [True, True, False],
            "price_ready": [True, True, False],
            "dcf_ready": [False, True, False],
            "peer_ready": [False, False, False],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "blocked_features": ["dcf, peer", "peer", "price, dcf, peer"],
            "overall_readiness_state": ["partial", "partial", "blocked"],
            "updated_at": ["2026-05-29T00:00:00+00:00", "2026-05-29T00:00:00+00:00", "2026-05-29T00:00:00+00:00"],
        }
    )
    previous = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [True, False, False],
            "dcf_ready": [False, False, False],
            "peer_ready": [False, False, False],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
        }
    )

    cards = recent_progress.readiness_recent_progress_cards(
        current,
        previous,
        previous_snapshot_label="data/reports/ticker_readiness_report.previous.csv",
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "price +1" in rendered
    assert "dcf +1" in rendered
    assert "newly ready tickers: bbb" in rendered
    assert "prior refresh timestamp" in rendered
    assert "previous vs current" in rendered
    assert "compared with saved prior readiness snapshot" in rendered
    assert "data/reports/ticker_readiness_report.previous.csv" not in rendered
    assert "snapshot -> targeted update -> compare" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
