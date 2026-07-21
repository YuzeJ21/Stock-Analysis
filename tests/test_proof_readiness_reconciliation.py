from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

import pandas as pd

from src.proof_readiness_reconciliation import (
    build_proof_readiness_reconciliation,
    filter_reconciliation_rows,
    main,
    proof_readiness_reconciliation_payload,
    render_proof_readiness_reconciliation,
)
from src.reviewed_batch_proof import ReviewedBatchProof


def _proof(
    *,
    tickers: str = "ARCT",
    lane: str = "fundamentals",
    outcome: str = "auto_supported",
    review_date: str = "2026-06-26",
    batch_id: str = "RB-1",
) -> ReviewedBatchProof:
    return ReviewedBatchProof(
        batch_id=batch_id,
        review_date=review_date,
        reviewer="reviewer",
        lane=lane,
        scope="one reviewed scope",
        tickers=tickers,
        command_run="read-only fixture command",
        validation_result="passed",
        preview_result="reviewed",
        apply_result="applied",
        pre_run_readiness_snapshot="before",
        post_run_readiness_snapshot="after",
        changed_readiness_counts="one lane changed",
        changed_tickers=tickers,
        source_files="reviewed source",
        generated_artifacts_reviewed="excluded",
        final_outcome=outcome,
        notes="fixture proof",
    )


def _ticker_readiness(**rows: dict[str, str]) -> pd.DataFrame:
    defaults = {
        "fundamentals_ready": "False",
        "dcf_ready": "False",
        "price_ready": "False",
        "peer_ready": "False",
    }
    return pd.DataFrame([{"ticker": ticker, **defaults, **values} for ticker, values in rows.items()])


def _dcf_readiness(**rows: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"ticker": ticker, "has_shares_outstanding": "False", **values} for ticker, values in rows.items()]
    )


def _peer_readiness(**rows: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame([{"ticker": ticker, "peer_valuation_ready": "False", **values} for ticker, values in rows.items()])


def _summary(*, proofs: list[ReviewedBatchProof], ticker: pd.DataFrame, dcf=None, peer=None):
    return build_proof_readiness_reconciliation(
        proofs=proofs,
        ticker_readiness=ticker,
        dcf_readiness=dcf if dcf is not None else pd.DataFrame(),
        peer_readiness=peer if peer is not None else pd.DataFrame(),
    )


def _row(summary, ticker: str, lane: str):
    return next(row for row in summary.rows if row.ticker == ticker and row.lane == lane)


def test_historical_supported_fundamentals_stays_blocked_when_current_readiness_is_false():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
    )

    row = _row(summary, "ARCT", "fundamentals")

    assert row.state == "historical_supported_currently_blocked"
    assert row.current_ready is False
    assert row.latest_batch_id == "RB-1"
    assert row.latest_outcome == "auto_supported"
    assert dict(summary.conflict_counts_by_lane) == {"fundamentals": 1}


def test_current_ready_with_matching_support_is_reconciled_without_unlocking_other_lanes():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(
            ARCT={
                "fundamentals_ready": "True",
                "dcf_ready": "False",
                "price_ready": "False",
                "peer_ready": "False",
            }
        ),
    )

    assert _row(summary, "ARCT", "fundamentals").state == "current_supported_with_matching_proof"
    assert _row(summary, "ARCT", "dcf").state == "no_proof_record"
    assert _row(summary, "ARCT", "price").state == "no_proof_record"
    assert _row(summary, "ARCT", "peer_mapping").state == "no_proof_record"


def test_later_still_blocked_proof_prevents_reuse_of_earlier_support():
    summary = _summary(
        proofs=[
            _proof(review_date="2026-06-26", outcome="supported", batch_id="RB-1"),
            _proof(review_date="2026-06-27", outcome="still_blocked", batch_id="RB-2"),
        ],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "True"}),
    )

    row = _row(summary, "ARCT", "fundamentals")

    assert row.latest_batch_id == "RB-2"
    assert row.latest_outcome == "still_blocked"
    assert row.state == "current_ready_proof_not_supporting"


def test_explicit_lane_mappings_keep_current_states_independent():
    proofs = [
        _proof(lane="fundamentals_dcf", batch_id="RB-DCF"),
        _proof(lane="share_count", batch_id="RB-SHARES"),
        _proof(lane="price_coverage", batch_id="RB-PRICE"),
        _proof(lane="peer_mapping", batch_id="RB-PEER"),
        _proof(lane="peer_valuation_inputs", batch_id="RB-PEER-VAL"),
    ]
    summary = _summary(
        proofs=proofs,
        ticker=_ticker_readiness(
            ARCT={
                "fundamentals_ready": "False",
                "dcf_ready": "True",
                "price_ready": "True",
                "peer_ready": "False",
            }
        ),
        dcf=_dcf_readiness(ARCT={"has_shares_outstanding": "True"}),
        peer=_peer_readiness(ARCT={"peer_valuation_ready": "True"}),
    )

    assert _row(summary, "ARCT", "dcf").state == "current_supported_with_matching_proof"
    assert _row(summary, "ARCT", "share_count").state == "current_supported_with_matching_proof"
    assert _row(summary, "ARCT", "price").state == "current_supported_with_matching_proof"
    assert _row(summary, "ARCT", "peer_mapping").state == "historical_supported_currently_blocked"
    assert _row(summary, "ARCT", "peer_valuation_inputs").state == "current_supported_with_matching_proof"
    assert _row(summary, "ARCT", "fundamentals").state == "no_proof_record"


def test_malformed_and_descriptive_proof_fields_fail_closed():
    malformed = replace(
        _proof(
            tickers="ARCT, 3289 changed tickers, -, UNKNOWN",
            lane="fundamentals",
            outcome="supported_typo",
            review_date="not-a-date",
        ),
        final_outcome="supported_typo",
    )
    summary = _summary(
        proofs=[malformed],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "True"}),
    )

    row = _row(summary, "ARCT", "fundamentals")

    assert row.review_date_valid is False
    assert row.state == "current_ready_proof_not_supporting"
    assert {item.ticker for item in summary.rows} == {"ARCT"}


def test_valid_dated_proof_outranks_later_appended_malformed_date_and_filter_keeps_global_counts():
    summary = _summary(
        proofs=[
            _proof(
                tickers="ARCT; ARDX; ARCT",
                review_date="2026-06-30",
                outcome="supported",
                batch_id="RB-VALID",
            ),
            _proof(
                tickers="ARCT",
                review_date="bad-date",
                outcome="still_blocked",
                batch_id="RB-MALFORMED",
            ),
        ],
        ticker=_ticker_readiness(
            ARCT={"fundamentals_ready": "False"},
            ARDX={"fundamentals_ready": "False"},
        ),
    )

    assert _row(summary, "ARCT", "fundamentals").latest_batch_id == "RB-VALID"
    assert dict(summary.conflict_counts_by_lane) == {"fundamentals": 2}

    filtered = filter_reconciliation_rows(summary, tickers=("ARCT",), top_n=20)

    assert {row.ticker for row in filtered} == {"ARCT"}
    assert dict(summary.conflict_counts_by_lane) == {"fundamentals": 2}


def test_render_names_conflicts_and_non_promotion_boundary():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
    )

    rendered = render_proof_readiness_reconciliation(summary, top_n=10)

    assert "Proof-Readiness Reconciliation" in rendered
    assert "historical_supported_currently_blocked" in rendered
    assert "Current saved readiness remains authoritative" in rendered
    assert "does not restore data, promote readiness, or rewrite proof history" in rendered
    assert "Research-only" in rendered


def _write_cli_inputs(root: Path) -> None:
    reports = root / "data" / "reports"
    reports.mkdir(parents=True)
    pd.DataFrame(
        [asdict(_proof(tickers="ARCT, ARDX"))]
    ).to_csv(root / "data" / "reviewed_batch_proofs.csv", index=False)
    _ticker_readiness(
        ARCT={"fundamentals_ready": "False"},
        ARDX={"fundamentals_ready": "False"},
    ).to_csv(reports / "ticker_readiness_report.csv", index=False)
    _dcf_readiness(ARCT={}, ARDX={}).to_csv(reports / "dcf_readiness_report.csv", index=False)
    _peer_readiness(ARCT={}, ARDX={}).to_csv(reports / "peer_readiness_report.csv", index=False)


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_main_is_read_only(tmp_path, capsys):
    _write_cli_inputs(tmp_path)
    before = _file_snapshot(tmp_path)

    exit_code = main(["--root", str(tmp_path), "--top-n", "10"])

    assert exit_code == 0
    assert _file_snapshot(tmp_path) == before
    output = capsys.readouterr().out
    assert "Research-only" in output
    assert "historical_supported_currently_blocked" in output


def test_json_ticker_filter_keeps_global_counts(tmp_path, capsys):
    _write_cli_inputs(tmp_path)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--top-n",
            "20",
            "--tickers",
            "ARCT",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["conflict_counts_by_lane"] == {"fundamentals": 2}
    assert {row["ticker"] for row in payload["rows"]} == {"ARCT"}


def test_payload_top_n_bounds_rows_without_changing_summary_counts():
    summary = _summary(
        proofs=[_proof(tickers="ARCT, ARDX")],
        ticker=_ticker_readiness(
            ARCT={"fundamentals_ready": "False"},
            ARDX={"fundamentals_ready": "False"},
        ),
    )

    payload = proof_readiness_reconciliation_payload(summary, top_n=1)

    assert len(payload["rows"]) == 1
    assert payload["conflict_counts_by_lane"] == {"fundamentals": 2}
