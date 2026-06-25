from pathlib import Path

import pandas as pd

from src.data_health_proof_console import (
    latest_batch_packet_summary,
    reviewed_batch_proof_completion_cards,
    reviewed_batch_proof_completion_frame,
    reviewed_batch_proof_ledger_preview_cards,
    reviewed_batch_proof_ledger_preview_frame,
    reviewed_batch_proof_loop_cards,
)
from src.readiness_comparison import ReadinessComparison


def _comparison(status: str = "ok") -> ReadinessComparison:
    return ReadinessComparison(
        status=status,
        before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        after_path=Path("data/reports/ticker_readiness_report.csv"),
        before_rows=2 if status == "ok" else 0,
        after_rows=2,
        changed_tickers=("AAA",) if status == "ok" else (),
        changed_count=1 if status == "ok" else 0,
        changed_readiness_counts="metric_state (blocked: 2->1)" if status == "ok" else "not available",
        freshness_status="current",
        freshness_message="Readiness artifacts are current.",
        blocking_message="" if status == "ok" else "Missing prior readiness snapshot.",
    )


def _packet_frame(*, ready: bool = False) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Batch ID": "RB-TEST",
                "Lane": "Metric Readiness Review",
                "Scope": "AAA",
                "Proposed Ticker": "AAA",
                "Dry Run Command": "make metric-readiness-board TOP_N=1",
                "Comparison Command": "make reviewed-batch-compare LANE=metrics",
                "Proof Record Scaffold": "make reviewed-batch-proof-record BATCH_ID=RB-TEST",
                "Review Date": "2026-06-17" if ready else "",
                "Validation Result": "not_applicable_read_only_metric_review" if ready else "<pass/fail/not_applicable>",
                "Preview Result": "reviewed metric blocker families" if ready else "<reviewed rows / no unexpected rows / not_applicable>",
                "Apply Result": "not_applicable_read_only_metric_review" if ready else "<not_run/applied/skipped>",
                "Changed Readiness Counts": "metric_state (blocked: 2->1)" if ready else "<before -> after counts, or none>",
                "Changed Tickers": "AAA" if ready else "<tickers changed, or none>",
                "Source Files": "metric-readiness console output",
                "Generated Artifacts Review": "excluded generated CSV churn" if ready else "<kept evidence or excluded local churn>",
                "Allowed Outcome": "still_blocked" if ready else "supported|candidate_context_only|still_blocked|skipped|excluded",
            }
        ]
    )


def test_proof_console_summary_and_loop_cards_are_research_only():
    packet = _packet_frame(ready=True)
    summary = latest_batch_packet_summary(packet)
    cards = reviewed_batch_proof_loop_cards(packet, _comparison())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert summary["batch_id"] == "RB-TEST"
    assert summary["ticker_count"] == "1"
    assert [card["kicker"] for card in cards] == ["LATEST PACKET", "COMPARISON STATUS", "PROOF RECORD"]
    assert "copy-only evidence" in rendered
    assert "supported, candidate_context_only, still_blocked, skipped, or excluded" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
    assert "order routing" not in rendered


def test_proof_console_completion_and_ledger_preview_block_placeholders():
    packet = _packet_frame(ready=False)
    comparison = _comparison(status="missing_before")

    completion_cards = reviewed_batch_proof_completion_cards(packet, comparison)
    completion_frame = reviewed_batch_proof_completion_frame(packet, comparison)
    ledger_cards = reviewed_batch_proof_ledger_preview_cards(packet, comparison)
    ledger_frame = reviewed_batch_proof_ledger_preview_frame(packet, comparison)
    rendered = " ".join(str(value) for card in completion_cards + ledger_cards for value in card.values()).lower()

    assert completion_cards[0]["kicker"] == "FINISH THIS PROOF"
    assert "proof item(s) to finish" in completion_cards[0]["title"]
    assert "validation_result" in set(completion_frame["Field"])
    assert ledger_cards[0]["title"] == "Ledger row preview is not record-ready"
    assert ledger_frame.loc[ledger_frame["Ledger Column"] == "changed_tickers"].iloc[0]["Record Readiness"] == "blocked_by_snapshot_gate"
    assert "do not record" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_proof_console_ready_ledger_preview_keeps_copy_boundary():
    packet = _packet_frame(ready=True)
    comparison = _comparison()

    cards = reviewed_batch_proof_ledger_preview_cards(packet, comparison)
    frame = reviewed_batch_proof_ledger_preview_frame(packet, comparison)

    assert cards[0]["title"] == "Ledger row preview ready after final review"
    assert frame.loc[frame["Ledger Column"] == "batch_id"].iloc[0]["Preview Value"] == "RB-TEST"
    assert frame.loc[frame["Ledger Column"] == "final_outcome"].iloc[0]["Preview Value"] == "still_blocked"
    assert set(frame["Copy Boundary"]) == {
        "Preview only; copy command only after final source/artifact review"
    }
