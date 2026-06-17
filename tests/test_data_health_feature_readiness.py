from __future__ import annotations

import pandas as pd

from src import data_health_feature_readiness as feature_readiness


def test_feature_readiness_cards_surface_top_blockers_and_price_dry_run():
    feature_summary = pd.DataFrame(
        [
            {
                "feature": "price",
                "ready_count": 240,
                "partial_count": 0,
                "blocked_count": 3298,
                "excluded_count": 0,
                "total_count": 3538,
                "top_blocker": "needs price rows",
                "next_action": "make price-worklist TOP_N=25",
                "dashboard_section": "Price Coverage",
            },
            {
                "feature": "dcf",
                "ready_count": 23,
                "partial_count": 0,
                "blocked_count": 3513,
                "excluded_count": 2,
                "total_count": 3538,
                "top_blocker": "missing fundamentals",
                "next_action": "make dcf-readiness",
                "dashboard_section": "Value / Re-rating",
            },
        ]
    )

    cards = feature_readiness.feature_readiness_cards(feature_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "dcf: 23/3538 ready" in rendered
    assert "price: 240/3538 ready" in rendered
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "avoids repeating small worklists manually" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_feature_readiness_cards_use_plain_missing_output_language():
    cards = feature_readiness.feature_readiness_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Feature readiness not ready yet"
    assert cards[0]["command"] == "make readiness"
    assert "run readiness to rebuild the feature proof" in rendered
    assert "data/reports/feature_readiness_summary.csv" not in rendered
    assert "not generated" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_feature_readiness_cards_show_optional_context_as_locked_workflow():
    feature_summary = pd.DataFrame(
        [
            {
                "feature": "earnings",
                "ready_count": 0,
                "partial_count": 0,
                "blocked_count": 3538,
                "excluded_count": 0,
                "total_count": 3538,
                "top_blocker": "earnings: trusted local CSV input",
                "next_action": "make import-earnings",
                "dashboard_section": "Optional Context",
            },
            {
                "feature": "analyst_estimates",
                "ready_count": 0,
                "partial_count": 0,
                "blocked_count": 3538,
                "excluded_count": 0,
                "total_count": 3538,
                "top_blocker": "analyst_estimates: trusted local CSV input",
                "next_action": "make import-analyst-estimates",
                "dashboard_section": "Optional Context",
            },
        ]
    )

    cards = feature_readiness.feature_readiness_cards(feature_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "earnings: 0/3538 ready" in rendered
    assert "analyst_estimates: 0/3538 ready" in rendered
    assert "intentionally locked" in rendered
    assert "schema-only templates" in rendered
    assert "data/staged/earnings/" in rendered
    assert "data/imports/earnings.csv" in rendered
    assert "data/staged/analyst_estimates/" in rendered
    assert "data/imports/analyst_estimates.csv" in rendered
    assert "make templates" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
