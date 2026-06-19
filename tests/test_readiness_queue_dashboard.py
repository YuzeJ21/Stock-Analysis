from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.readiness_queue_dashboard import (
    build_readiness_queue_drilldown_frame,
    build_readiness_queue_lane_action_frame,
    build_readiness_queue_outcome_summary_frame,
    build_readiness_queue_route_cards,
    queue_proof_packet_command,
    readiness_queue_lane_key,
)


@dataclass(frozen=True)
class FreshnessStub:
    status: str
    message: str
    refresh_command: str


def test_readiness_queue_lane_keys_and_packet_commands_keep_lanes_separate():
    assert readiness_queue_lane_key("Fundamentals / DCF Proof") == "fundamentals"
    assert readiness_queue_lane_key("Peer Mapping Proof") == "peer_mapping"
    assert readiness_queue_lane_key("Peer Valuation Inputs") == "peer_valuation_inputs"
    assert readiness_queue_lane_key("Metrics Readiness") == "metrics"
    assert queue_proof_packet_command("fundamentals") == "DRY_RUN=1 make reviewed-batch LANE=fundamentals TOP_N=10"
    assert queue_proof_packet_command("peer_mapping") == "DRY_RUN=1 make reviewed-batch LANE=peers TOP_N=10"
    assert queue_proof_packet_command("metrics") == "DRY_RUN=1 make reviewed-batch LANE=metrics TOP_N=10"


def test_readiness_queue_drilldown_builds_examples_and_stale_warning():
    queue = pd.DataFrame(
        [
            {
                "Lane": "Fundamentals / DCF Proof",
                "State": "partial",
                "Next Safe Command": "make sec-stage-queue TOP_N=25",
                "Proof Gate": "Validate -> preview -> rejected-row review -> apply only reviewed trusted rows.",
                "Source Mode": "SEC-stageable or trusted-local",
            }
        ]
    )
    ticker_readiness = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "fundamentals_ready": "false",
                "dcf_ready": "false",
                "missing_data": "dcf: revenue and free cash flow",
            }
        ]
    )
    batch_proofs = pd.DataFrame(
        [
            {
                "Batch ID": "RB-FUND-1",
                "Review Date": "2026-06-15",
                "Lane": "fundamentals",
                "Final Outcome": "still_blocked",
            }
        ]
    )

    frame = build_readiness_queue_drilldown_frame(
        queue,
        ticker_readiness_frame=ticker_readiness,
        batch_proof_frame=batch_proofs,
        freshness_status=FreshnessStub("stale", "Source CSVs changed after readiness.", "make readiness"),
    )

    row = frame.iloc[0]
    assert row["State"] == "Partial"
    assert "AAA: dcf: revenue and free cash flow" in row["Top Blocker Examples"]
    assert row["Proof Packet Command"] == "DRY_RUN=1 make reviewed-batch LANE=fundamentals TOP_N=10"
    assert "Stale: Source CSVs changed after readiness." in row["Stale / Source Warning"]
    assert "still_blocked on 2026-06-15" in row["Proof Record Status"]


def test_readiness_queue_drilldown_keeps_metric_examples_read_only():
    queue = pd.DataFrame(
        [
            {
                "Lane": "Metrics Readiness",
                "State": "partial",
                "Next Safe Command": "make metric-readiness-board TOP_N=10",
                "Proof Gate": "SPY/QQQ metrics stay gated.",
                "Source Mode": "local_readiness",
            }
        ]
    )
    metric_queue = pd.DataFrame(
        [
            {
                "Ticker": "AAA",
                "Benchmark": "SPY",
                "Overall State": "partial",
                "Top Blocker": "benchmark_relative_return",
                "Blocker Family": "benchmark / risk",
            }
        ]
    )

    frame = build_readiness_queue_drilldown_frame(queue, metric_queue_frame=metric_queue)
    row = frame.iloc[0]

    assert "AAA vs SPY: benchmark / risk - benchmark_relative_return" in row["Top Blocker Examples"]
    assert row["Proof Packet Command"] == "DRY_RUN=1 make reviewed-batch LANE=metrics TOP_N=10"
    assert "Source mode: local_readiness" in row["Stale / Source Warning"]


def test_readiness_queue_lane_action_routes_mutating_and_read_only_lanes():
    metrics = build_readiness_queue_lane_action_frame(
        {
            "Lane": "Metrics Readiness",
            "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=metrics TOP_N=10",
            "Stale / Source Warning": "Source mode: local_readiness. Metrics stay gated.",
            "Proof Record Status": "No reviewed batch proof row recorded for this lane yet.",
        }
    )
    peer = build_readiness_queue_lane_action_frame(
        {
            "Lane": "Peer Mapping Proof",
            "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=peers TOP_N=10",
            "Stale / Source Warning": "Source mode: manual/source-reviewed.",
            "Proof Record Status": "No reviewed batch proof row recorded for this lane yet.",
        }
    )

    metric_gate = metrics.loc[metrics["Step"].eq("2. Validate / preview gate")].iloc[0]
    peer_gate = peer.loc[peer["Step"].eq("2. Validate / preview gate")].iloc[0]
    rendered = " ".join(str(value) for value in metrics.to_numpy().ravel()).lower()

    assert metric_gate["Status"] == "read_only_metric_review"
    assert "do not run import/apply commands" in metric_gate["Operator Decision"].lower()
    assert peer_gate["Status"] == "validate_preview_apply"
    assert "make reviewed-batch-compare LANE=peers" in " ".join(str(value) for value in peer.to_numpy().ravel())
    assert "?mode=operator&page=data-health&lane=metrics&drawer=queue" in rendered
    assert "?mode=operator&page=data-health&lane=metrics&drawer=source-proof" in rendered
    assert "?mode=operator&page=data-health&lane=proof&drawer=comparison" in rendered
    assert "navigation-only" in rendered
    assert "does not run commands or write data" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_readiness_queue_route_cards_summarize_navigation_without_unlocking_data():
    cards = build_readiness_queue_route_cards(
        {
            "Lane": "Fundamentals / DCF Proof",
            "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=fundamentals TOP_N=10",
            "Stale / Source Warning": "Source mode: SEC-stageable. Validate before preview.",
            "Proof Record Status": "No reviewed batch proof row recorded for this lane yet.",
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["ROUTE 1", "ROUTE 2", "ROUTE 3", "STOP RULE"]
    assert "fundamentals / dcf proof: open queue packet" in rendered
    assert "?mode=operator&page=data-health&lane=fundamentals&drawer=queue" in rendered
    assert "navigation-only" in rendered
    assert "gate state: validate_preview_apply" in rendered
    assert "keep validate, preview, rejected-row review, and apply/skip as explicit reviewed steps" in rendered
    assert "?mode=operator&page=data-health&lane=proof&drawer=comparison" in rendered
    assert "?mode=operator&page=data-health&lane=proof&drawer=proof-record" in rendered
    assert "do not treat a route as an unlock" in rendered
    assert "missing source inputs stay blocked" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_readiness_queue_outcome_summary_reads_latest_batch_outcomes():
    queue = pd.DataFrame(
        [
            {
                "Lane": "Fundamentals / DCF Proof",
                "State": "partial",
                "Next Safe Command": "make sec-stage-queue TOP_N=25",
            },
            {
                "Lane": "Peer Mapping Proof",
                "State": "partial",
                "Next Safe Command": "make peer-mapping-queue TOP_N=25",
            },
            {
                "Lane": "Metrics Readiness",
                "State": "partial",
                "Next Safe Command": "make metric-readiness-board TOP_N=10",
            },
        ]
    )
    proofs = pd.DataFrame(
        [
            {
                "Batch ID": "RB-OLD",
                "Review Date": "2026-06-14",
                "Lane": "fundamentals",
                "Final Outcome": "still_blocked",
                "Changed Tickers": "none",
                "Changed Readiness Counts": "none",
            },
            {
                "Batch ID": "RB-FUND",
                "Review Date": "2026-06-15",
                "Lane": "fundamentals",
                "Final Outcome": "supported",
                "Changed Tickers": "AAA",
                "Changed Readiness Counts": "dcf_ready 26->27",
            },
            {
                "Batch ID": "RB-PEER",
                "Review Date": "2026-06-15",
                "Lane": "peers",
                "Final Outcome": "still_blocked",
                "Changed Tickers": "none",
                "Changed Readiness Counts": "none",
            },
        ]
    )

    frame = build_readiness_queue_outcome_summary_frame(queue, proofs)
    by_lane = {row["Lane"]: row for _, row in frame.iterrows()}
    rendered = " ".join(str(value) for value in frame.to_numpy().ravel()).lower()

    assert by_lane["Fundamentals / DCF Proof"]["Latest Outcome"] == "supported"
    assert by_lane["Fundamentals / DCF Proof"]["Batch ID"] == "RB-FUND"
    assert by_lane["Fundamentals / DCF Proof"]["Changed Tickers"] == "AAA"
    assert by_lane["Peer Mapping Proof"]["Latest Outcome"] == "still_blocked"
    assert by_lane["Metrics Readiness"]["Latest Outcome"] == "not_recorded"
    assert by_lane["Metrics Readiness"]["Proof Ledger Command"] == "make reviewed-batch-proof"
    assert "security" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
