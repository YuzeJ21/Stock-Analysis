from __future__ import annotations

import pandas as pd

from src import data_health_summary as summary_mod


def test_dashboard_readiness_summary_counts_ready_blocked_and_credentials(monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.setenv("SEC_USER_AGENT", "tester@example.com")
    coverage = pd.DataFrame(
        {
            "ticker": ["NVDA", "AMD", "QQQ"],
            "has_prices": [True, False, True],
            "usable_for_momentum": [True, False, True],
            "peer_ready": [False, True, False],
        }
    )
    dcf = pd.DataFrame(
        {
            "ticker": ["NVDA", "AMD", "QQQ"],
            "asset_type": ["company", "company", "etf"],
            "is_dcf_ready": [True, False, False],
        }
    )
    earnings = pd.DataFrame({"ticker": ["NVDA"], "has_trusted_earnings": [True]})
    estimates = pd.DataFrame({"ticker": ["NVDA"], "has_trusted_analyst_estimates": [False]})

    summary = summary_mod.dashboard_readiness_summary(coverage, dcf, earnings, estimates)

    assert summary["universe_count"] == 3
    assert summary["master_universe"] == 3
    assert summary["active_universe"] == 3
    assert summary["price_ready"] == 2
    assert summary["momentum_ready"] == 2
    assert summary["dcf_ready"] == 1
    assert summary["dcf_excluded"] == 1
    assert summary["peer_ready"] == 1
    assert summary["earnings_ready"] == 1
    assert summary["analyst_ready"] == 0
    assert summary["analyst_estimates_ready"] == 0
    assert summary["missing_credentials"] == ["STOOQ_API_KEY"]
    assert summary["configured_credentials"] == ["SEC_USER_AGENT"]
    assert "Price import file folder: data/staged/prices/ -> make import-prices" in summary["manual_import_paths"]


def test_dashboard_readiness_summary_supports_current_coverage_schema_without_ticker_readiness(monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    coverage = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [True, True, False],
            "momentum_ready": [True, False, False],
            "peer_ready": [False, True, False],
        }
    )

    summary = summary_mod.dashboard_readiness_summary(coverage, None, None, None)

    assert summary["price_ready"] == 2
    assert summary["momentum_ready"] == 1
    assert summary["peer_ready"] == 1
    assert summary["missing_credentials"] == ["STOOQ_API_KEY", "SEC_USER_AGENT"]


def test_dashboard_readiness_summary_prefers_ticker_readiness_counts(monkeypatch):
    monkeypatch.setenv("STOOQ_API_KEY", "configured")
    monkeypatch.setenv("SEC_USER_AGENT", "tester@example.com")
    coverage = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [False, False, False],
            "momentum_ready": [False, False, False],
            "peer_ready": [False, False, False],
        }
    )
    ticker_readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "in_master_universe": [True, True, True],
            "in_active_universe": [True, False, False],
            "price_ready": [True, True, False],
            "momentum_ready": [True, False, False],
            "market_direction_ready": [True, True, False],
            "liquidity_ready": [True, False, False],
            "correlation_ready": [True, False, False],
            "fundamentals_ready": [True, False, False],
            "dcf_ready": [True, False, False],
            "peer_ready": [False, True, False],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "overall_readiness_state": ["partial", "partial", "blocked"],
            "excluded_features": ["", "dcf", ""],
            "updated_at": ["2026-06-17T00:00:00+00:00", "", ""],
        }
    )

    summary = summary_mod.dashboard_readiness_summary(coverage, None, None, None, ticker_readiness)

    assert summary["universe_count"] == 3
    assert summary["active_universe"] == 1
    assert summary["price_ready"] == 2
    assert summary["momentum_ready"] == 1
    assert summary["market_direction_ready"] == 2
    assert summary["liquidity_ready"] == 1
    assert summary["correlation_ready"] == 1
    assert summary["fundamentals_ready"] == 1
    assert summary["dcf_ready"] == 1
    assert summary["dcf_excluded"] == 1
    assert summary["peer_ready"] == 1
    assert summary["blocked_by_data"] == 1
    assert summary["partial"] == 2
    assert summary["missing_credentials"] == []
    assert summary["configured_credentials"] == ["STOOQ_API_KEY", "SEC_USER_AGENT"]
