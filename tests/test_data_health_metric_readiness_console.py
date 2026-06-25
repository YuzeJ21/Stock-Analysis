import pandas as pd

from src.data_health_metric_readiness_console import (
    detail_selector_requested,
    drawer_detail_flags,
    drawer_from_query,
    metric_detail_load_cards,
    metric_detail_load_status,
    metric_readiness_family_summary_cards,
    metric_readiness_family_summary_frame,
    metric_readiness_queue_cards,
    proof_detail_load_cards,
    proof_detail_load_status,
    proof_lane_shell_cards,
)


class Freshness:
    def __init__(self, status: str, message: str, refresh_command: str = "make readiness") -> None:
        self.status = status
        self.message = message
        self.refresh_command = refresh_command


def _metric_queue_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": "NVDA",
                "Benchmark": "SPY",
                "Overall State": "partial",
                "Top Blocker": "benchmark_relative_return: at least 60 aligned ticker/SPY price rows",
                "Blocker Family": "benchmark / risk",
                "Next Check": "make focus-price TICKER=NVDA",
                "Freshness": "current",
            },
            {
                "Ticker": "NVDA",
                "Benchmark": "QQQ",
                "Overall State": "blocked",
                "Top Blocker": "peer_valuation_dispersion: at least two peers with trusted valuation multiples",
                "Blocker Family": "peer dispersion",
                "Next Check": "make focus-peers TICKER=NVDA",
                "Freshness": "current",
            },
            {
                "Ticker": "QQQ",
                "Benchmark": "SPY",
                "Overall State": "excluded",
                "Top Blocker": "none",
                "Blocker Family": "none",
                "Next Check": "make stock-report-md TICKER=QQQ",
                "Freshness": "current",
            },
        ]
    )


def test_metric_console_summarizes_spy_qqq_without_rankings():
    cards = metric_readiness_queue_cards(_metric_queue_frame())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "SPY / QQQ METRIC QUEUE"
    assert "rows across spy, qqq" in rendered
    assert "not ranking" in rendered
    assert "partial metrics withhold values" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_metric_family_summary_keeps_blocked_inputs_visible():
    summary = metric_readiness_family_summary_frame(_metric_queue_frame())
    cards = metric_readiness_family_summary_cards(_metric_queue_frame())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert list(summary["Blocker Family"]) == ["benchmark / risk", "peer dispersion", "none"]
    assert "readiness triage only" in " ".join(summary["Guardrail"].astype(str)).lower()
    assert "rows with missing inputs stay blocked" in rendered
    assert "review metrics only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_metric_and_proof_detail_statuses_preserve_progressive_loading():
    current = Freshness("current", "Readiness artifacts are current.")
    stale = Freshness("stale", "Generated readiness artifacts are stale.")

    assert metric_detail_load_status("prices", current, requested=True)["status"] == "not_selected"
    assert metric_detail_load_status("metrics", current, requested=False)["status"] == "needs_request"
    assert metric_detail_load_status("metrics", stale, requested=True)["status"] == "blocked_by_snapshot_gate"
    assert metric_detail_load_status("metrics", current, requested=True)["status"] == "ready_to_load"

    assert proof_detail_load_status("metrics", current, requested=True, loaded=True)["status"] == "not_selected"
    assert proof_detail_load_status("proof", current, requested=False, loaded=False)["status"] == "deferred"
    assert proof_detail_load_status("proof", current, requested=True, loaded=False)["status"] == "loading"
    assert proof_detail_load_status("proof", stale, requested=True, loaded=False)["status"] == "blocked_by_snapshot_gate"
    assert proof_detail_load_status("proof", current, requested=True, loaded=True)["status"] == "loaded"


def test_metric_and_proof_detail_cards_are_research_only():
    rendered = " ".join(
        str(value)
        for status in [
            {"status": "blocked_by_snapshot_gate", "title": "Refresh readiness first", "body": "Generated readiness artifacts are stale.", "next_action": "make readiness"},
            {"status": "needs_request", "title": "Metric details are not loaded yet", "body": "The first metrics view is intentionally lightweight.", "next_action": "Switch Metric detail level to Review details."},
            {"status": "ready_to_load", "title": "Metric details loaded", "body": "SPY/QQQ metric-readiness rows are loaded.", "next_action": "Open the Metrics evidence drawer."},
        ]
        for card in metric_detail_load_cards(status)
        for value in card.values()
    ).lower()
    rendered += " " + " ".join(
        str(value)
        for status in [
            {"status": "blocked_by_snapshot_gate", "title": "Refresh readiness first", "body": "Generated readiness artifacts are stale.", "next_action": "make readiness"},
            {"status": "deferred", "title": "Proof details are deferred", "body": "The proof lane shell is loaded.", "next_action": "Switch Proof detail level to Review details."},
            {"status": "loading", "title": "Proof details are loading", "body": "The proof lane is building reviewed proof ledgers.", "next_action": "Wait for proof detail cards."},
            {"status": "loaded", "title": "Proof details loaded", "body": "Reviewed proof ledgers are available.", "next_action": "Open reviewed batch proof drawer."},
        ]
        for card in proof_detail_load_cards(status)
        for value in card.values()
    ).lower()

    assert "no stale counts" in rendered
    assert "no stale proof" in rendered
    assert "supported, candidate_context_only, still_blocked, skipped, or excluded" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_proof_lane_shell_cards_make_deferred_loaded_and_stale_states_explicit():
    statuses = [
        {
            "status": "blocked_by_snapshot_gate",
            "title": "Refresh readiness first",
            "body": "Generated readiness artifacts are stale.",
            "next_action": "make readiness",
        },
        {
            "status": "deferred",
            "title": "Proof details are deferred",
            "body": "The proof lane shell is loaded.",
            "next_action": "Open Proof review details.",
        },
        {
            "status": "loading",
            "title": "Proof details are loading",
            "body": "The proof lane is building reviewed proof ledgers.",
            "next_action": "Wait for proof detail cards.",
        },
        {
            "status": "loaded",
            "title": "Proof details loaded",
            "body": "Reviewed proof ledgers are available.",
            "next_action": "Open reviewed batch proof drawer.",
        },
    ]
    cards = [card for status in statuses for card in proof_lane_shell_cards(status)]
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 12
    assert "visible now" in rendered
    assert "deferred until review" in rendered
    assert "fast view shows the proof lane purpose" in rendered
    assert "reviewed proof rows, batch packet scaffolds, command fields, and snapshot comparison wait" in rendered
    assert "snapshot gate is visible" in rendered
    assert "drawers are preparing" in rendered
    assert "proof summary is ready" in rendered
    assert "does not refresh data, apply imports, record proof rows, stage files, or change canonical csvs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_drawer_and_detail_selection_helpers_route_without_commands():
    assert detail_selector_requested("details") is True
    assert detail_selector_requested(None, selector_value="Review details") is True
    assert detail_selector_requested("0", selector_value="Fast view") is False
    assert drawer_from_query("metric-details", "prices") == "metrics"
    assert drawer_from_query(["proof-record"], "prices") == "proof"
    assert drawer_from_query("source-proof", "fundamentals") == "queue"
    assert drawer_detail_flags("batch", "fundamentals") == {
        "queue": False,
        "batch": True,
        "metrics": False,
        "proof": False,
    }
