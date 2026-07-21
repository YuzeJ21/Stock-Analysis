from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

import pandas as pd
import pytest

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
    changed_tickers: str | None = None,
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
        changed_tickers=tickers if changed_tickers is None else changed_tickers,
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


def _fundamentals(**rows: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame([{"ticker": ticker, **values} for ticker, values in rows.items()])


def _summary(*, proofs, ticker, dcf=None, peer=None, fundamentals=None):
    return build_proof_readiness_reconciliation(
        proofs=proofs,
        ticker_readiness=ticker,
        dcf_readiness=dcf if dcf is not None else pd.DataFrame(),
        peer_readiness=peer if peer is not None else pd.DataFrame(),
        fundamentals=fundamentals if fundamentals is not None else pd.DataFrame(),
    )


def _row(summary, ticker: str, lane: str):
    return next(row for row in summary.rows if row.ticker == ticker and row.lane == lane)


def test_scope_only_support_is_not_ticker_level_support():
    summary = _summary(
        proofs=[_proof(tickers="ARCT,ARDX", changed_tickers="ARDX")],
        ticker=_ticker_readiness(
            ARCT={"fundamentals_ready": "False"},
            ARDX={"fundamentals_ready": "False"},
        ),
    )

    arct = _row(summary, "ARCT", "fundamentals")
    ardx = _row(summary, "ARDX", "fundamentals")

    assert arct.proof_applicability == "scope_only_not_supported"
    assert arct.state == "currently_blocked_with_non_supporting_history"
    assert ardx.proof_applicability == "explicit_ticker_change"
    assert ardx.state == "historical_supported_currently_blocked"
    assert dict(summary.conflict_counts_by_lane) == {"fundamentals": 1}


@pytest.mark.parametrize(
    "changed_tickers",
    ["", "-", "none", "n/a", "not available", "unknown", "3289 changed tickers"],
)
def test_placeholder_changed_tickers_cannot_support(changed_tickers):
    summary = _summary(
        proofs=[_proof(changed_tickers=changed_tickers)],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.proof_applicability == "missing_ticker_change_detail"
    assert row.state == "currently_blocked_with_non_supporting_history"


def test_latest_non_supporting_proof_does_not_fall_back_to_older_explicit_support():
    summary = _summary(
        proofs=[
            _proof(batch_id="RB-OLD", review_date="2026-06-25", changed_tickers="ARCT"),
            _proof(batch_id="RB-NEW", review_date="2026-06-26", changed_tickers="-"),
        ],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.latest_batch_id == "RB-NEW"
    assert row.proof_applicability == "missing_ticker_change_detail"
    assert row.state == "currently_blocked_with_non_supporting_history"


def test_missing_current_canonical_fundamentals_row_is_diagnosed_without_historical_cause_inference():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
        dcf=_dcf_readiness(
            ARCT={
                "missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin, price"
            }
        ),
        fundamentals=_fundamentals(ARDX={"source": "sec_companyfacts"}),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.current_blocker_code == "current_canonical_row_missing"
    assert row.current_blocker_fields == (
        "free_cash_flow",
        "shares_outstanding",
        "revenue",
        "fcf_margin",
    )
    assert row.historical_payload_status == "structured_payload_not_recorded"
    assert "cannot distinguish" in row.historical_evidence_limit.lower()
    assert "yfinance" not in row.current_blocker_detail.lower()


def test_incomplete_current_canonical_fundamentals_row_reports_exact_current_fields():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, revenue, fcf_margin, price"}
        ),
        fundamentals=_fundamentals(
            ARCT={"shares_outstanding": "100", "source": "sec_companyfacts"}
        ),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.current_blocker_code == "current_required_fields_missing"
    assert row.current_blocker_fields == ("free_cash_flow", "revenue", "fcf_margin")
    assert "price" not in row.current_blocker_fields


def test_share_count_diagnosis_reports_only_shares_outstanding():
    summary = _summary(
        proofs=[_proof(lane="share_count")],
        ticker=_ticker_readiness(ARCT={}),
        dcf=_dcf_readiness(
            ARCT={
                "has_shares_outstanding": "False",
                "missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin, price",
            }
        ),
    )

    row = _row(summary, "ARCT", "share_count")
    assert row.current_blocker_code == "current_required_fields_missing"
    assert row.current_blocker_fields == ("shares_outstanding",)


def test_price_and_peer_blockers_remain_independent():
    summary = _summary(
        proofs=[
            _proof(lane="price_history", batch_id="RB-PRICE"),
            _proof(lane="peer_mapping", batch_id="RB-PEER"),
            _proof(lane="peer_valuation_inputs", batch_id="RB-PEER-VAL"),
        ],
        ticker=_ticker_readiness(
            ARCT={"price_ready": "False", "peer_ready": "False"}
        ),
        peer=_peer_readiness(ARCT={"peer_valuation_ready": "False"}),
    )

    assert _row(summary, "ARCT", "price").current_blocker_code == "current_price_missing"
    assert _row(summary, "ARCT", "peer_mapping").current_blocker_code == "current_peer_mapping_missing"
    assert (
        _row(summary, "ARCT", "peer_valuation_inputs").current_blocker_code
        == "current_peer_valuation_inputs_missing"
    )


def test_missing_canonical_fundamentals_input_affects_only_dependent_diagnosis():
    summary = _summary(
        proofs=[
            _proof(lane="fundamentals", batch_id="RB-FUND"),
            _proof(lane="price", batch_id="RB-PRICE"),
            _proof(lane="peer_mapping", batch_id="RB-PEER"),
        ],
        ticker=_ticker_readiness(
            ARCT={
                "fundamentals_ready": "False",
                "price_ready": "False",
                "peer_ready": "False",
            }
        ),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"}
        ),
        peer=_peer_readiness(ARCT={"peer_valuation_ready": "False"}),
        fundamentals=pd.DataFrame(),
    )

    assert (
        _row(summary, "ARCT", "fundamentals").current_blocker_code
        == "current_readiness_input_unavailable"
    )
    assert _row(summary, "ARCT", "price").current_blocker_code == "current_price_missing"
    assert _row(summary, "ARCT", "peer_mapping").current_blocker_code == "current_peer_mapping_missing"


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


def test_payload_exposes_applicability_and_current_blocker_axes():
    summary = _summary(
        proofs=[_proof(tickers="ARCT,ARDX", changed_tickers="ARDX")],
        ticker=_ticker_readiness(
            ARCT={"fundamentals_ready": "False"},
            ARDX={"fundamentals_ready": "False"},
        ),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"},
            ARDX={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"},
        ),
        fundamentals=_fundamentals(ARDX={"source": "sec_companyfacts"}),
    )

    payload = proof_readiness_reconciliation_payload(summary, top_n=20)

    assert payload["proof_applicability_counts"]["scope_only_not_supported"] == 1
    assert payload["proof_applicability_counts"]["explicit_ticker_change"] == 1
    assert payload["current_blocker_counts"]["current_canonical_row_missing"] == 2
    assert payload["rows"][0]["historical_payload_status"] == "structured_payload_not_recorded"
    assert "historical cause" in payload["boundary"].lower()


def test_render_exposes_two_axes_without_claiming_historical_cause():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"}
        ),
        fundamentals=_fundamentals(ARDX={"source": "sec_companyfacts"}),
    )

    rendered = render_proof_readiness_reconciliation(summary, top_n=10)

    assert "Proof applicability counts:" in rendered
    assert "Current blocker counts:" in rendered
    assert "explicit_ticker_change" in rendered
    assert "current_canonical_row_missing" in rendered
    assert "Proof applicability | Current blocker | Next safe review" in rendered
    assert "does not establish the historical cause" in rendered


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
