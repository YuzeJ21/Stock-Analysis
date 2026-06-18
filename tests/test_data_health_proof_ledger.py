import pandas as pd

from src.data_health_proof_ledger import case_column, latest_dcf_proof_row, latest_peer_proof_row, latest_proof_status_detail


def test_case_column_matches_case_insensitive_headers():
    frame = pd.DataFrame([{"Batch ID": "RB-1", "Final Outcome": "supported"}])

    assert case_column(frame, "batch_id") == "Batch ID"
    assert case_column(frame, "final_outcome") == "Final Outcome"
    assert case_column(frame, "missing") is None


def test_latest_dcf_proof_row_sorts_by_review_date_and_batch_id():
    frame = pd.DataFrame(
        [
            {"Batch ID": "RB-1", "Review Date": "2026-06-16", "Lane": "fundamentals", "Final Outcome": "supported"},
            {"Batch ID": "RB-3", "Review Date": "2026-06-17", "Lane": "share_count", "Final Outcome": "still_blocked"},
            {"Batch ID": "RB-2", "Review Date": "2026-06-17", "Lane": "fundamentals_dcf", "Final Outcome": "skipped"},
            {"Batch ID": "RB-9", "Review Date": "2026-06-18", "Lane": "peers", "Final Outcome": "supported"},
        ]
    )

    latest = latest_dcf_proof_row(frame)

    assert latest["Batch ID"] == "RB-3"
    assert latest["Lane"] == "share_count"
    assert latest["Final Outcome"] == "still_blocked"


def test_latest_peer_proof_row_keeps_peer_lanes_separate():
    frame = pd.DataFrame(
        [
            {"batch_id": "RB-1", "review_date": "2026-06-16", "lane": "fundamentals", "final_outcome": "supported"},
            {"batch_id": "RB-2", "review_date": "2026-06-17", "lane": "peer_mapping", "final_outcome": "still_blocked"},
            {"batch_id": "RB-3", "review_date": "2026-06-17", "lane": "peer_valuation_inputs", "final_outcome": "skipped"},
        ]
    )

    latest = latest_peer_proof_row(frame)

    assert latest["batch_id"] == "RB-3"
    assert latest["lane"] == "peer_valuation_inputs"
    assert latest["final_outcome"] == "skipped"


def test_latest_proof_row_returns_empty_series_when_lane_column_missing():
    frame = pd.DataFrame([{"Batch ID": "RB-1", "Final Outcome": "supported"}])

    assert latest_dcf_proof_row(frame).empty
    assert latest_peer_proof_row(frame).empty


def test_latest_proof_status_detail_formats_reviewed_row():
    frame = pd.DataFrame(
        [
            {
                "Batch ID": "RB-7",
                "Review Date": "2026-06-17",
                "Lane": "share_count",
                "Final Outcome": "still_blocked",
                "Changed Readiness Counts": "dcf_ready unchanged; source rows still need proof",
            }
        ]
    )
    latest = latest_dcf_proof_row(frame)

    status, detail, command = latest_proof_status_detail(
        frame,
        latest,
        empty_detail="No DCF reviewed batch proof row recorded yet.",
    )

    assert status == "still_blocked"
    assert detail == "Batch RB-7 on 2026-06-17; dcf_ready unchanged; source rows still need proof"
    assert command == "make reviewed-batch-proof"


def test_latest_proof_status_detail_uses_empty_fallback():
    status, detail, command = latest_proof_status_detail(
        None,
        None,
        empty_detail="No reviewed proof row recorded yet.",
    )

    assert status == "not_recorded"
    assert detail == "No reviewed proof row recorded yet."
    assert command == "make reviewed-batch-proof"
