from pathlib import Path

from src.reviewed_batch_preflight import build_reviewed_batch_preflight, render_reviewed_batch_preflight


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_current_reports(root: Path) -> None:
    _write(root / "data" / "prices.csv", "ticker,date,close\n")
    _write(root / "data" / "fundamentals.csv", "ticker,source\n")
    _write(root / "data" / "peers.csv", "ticker,peer_ticker\n")
    _write(root / "data" / "earnings.csv", "ticker,source\n")
    _write(root / "data" / "analyst_estimates.csv", "ticker,source\n")
    _write(root / "data" / "reports" / "ticker_readiness_report.csv", "ticker,overall_readiness_state\nAAA,blocked\n")
    _write(root / "data" / "reports" / "feature_readiness_summary.csv", "feature,ready_count\nprice,0\n")


def test_reviewed_batch_preflight_blocks_when_prior_snapshot_missing(tmp_path: Path):
    _write_current_reports(tmp_path)

    preflight = build_reviewed_batch_preflight(
        tmp_path,
        lane="prices",
        top_n=100,
        batch_id="RB-TEST",
        review_date="2026-06-12",
    )
    rendered = render_reviewed_batch_preflight(preflight)

    assert preflight.status == "needs_preflight_fix"
    assert preflight.current_report_exists is True
    assert preflight.prior_snapshot_exists is False
    assert "prior readiness snapshot is missing" in " ".join(preflight.do_not_proceed_if)
    assert "make readiness-snapshot" in rendered
    assert "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo" in rendered
    assert "make reviewed-batch-compare LANE=prices BATCH_ID=RB-TEST REVIEW_DATE=2026-06-12 TOP_N=100" in rendered
    assert "Post-run hygiene before any public commit" in rendered
    assert "make diff-hygiene" in rendered
    assert "Keep broad generated CSV/JSON churn unstaged" in rendered
    assert "does not refresh data, apply imports" in rendered
    assert "direct buy/sell instructions" in rendered


def test_reviewed_batch_preflight_ready_when_snapshot_and_freshness_exist(tmp_path: Path):
    _write_current_reports(tmp_path)
    _write(
        tmp_path / "data" / "reports" / "ticker_readiness_report.previous.csv",
        "ticker,overall_readiness_state\nAAA,blocked\n",
    )

    preflight = build_reviewed_batch_preflight(
        tmp_path,
        lane="fundamentals",
        top_n=25,
        batch_id="RB-FUND",
        review_date="2026-06-12",
    )

    assert preflight.status == "ready_for_dry_run"
    assert preflight.lane_scope == "Fundamentals / DCF"
    assert preflight.dry_run_command == "make sec-stage-queue TOP_N=25"
    assert "data/imports/fundamentals.csv" in preflight.expected_artifacts
    assert "make diff-hygiene" in preflight.post_run_hygiene
    assert preflight.proof_record_command.startswith('make reviewed-batch-proof-record BATCH_ID="RB-FUND"')


def test_reviewed_batch_preflight_handles_share_count_lane_scope(tmp_path: Path):
    _write_current_reports(tmp_path)
    _write(
        tmp_path / "data" / "reports" / "ticker_readiness_report.previous.csv",
        "ticker,overall_readiness_state\nAAA,blocked\n",
    )

    preflight = build_reviewed_batch_preflight(
        tmp_path,
        lane="share_count",
        top_n=10,
        batch_id="RB-SHARES",
        review_date="2026-06-12",
    )
    rendered = render_reviewed_batch_preflight(preflight)

    assert preflight.status == "ready_for_dry_run"
    assert preflight.lane_scope == "Share Count Proof"
    assert preflight.dry_run_command == "make share-count-proof-queue TOP_N=10"
    assert "reviewed trusted shares_outstanding rows" in preflight.capped_execution_command
    assert "data/rejected/fundamentals_import_rejected.csv" in preflight.expected_artifacts
    assert "make reviewed-batch LANE=share_count TOP_N=10" in rendered
    assert "make reviewed-batch-compare LANE=share_count" in rendered


def test_reviewed_batch_preflight_handles_peer_lane_scope(tmp_path: Path):
    _write_current_reports(tmp_path)
    _write(
        tmp_path / "data" / "reports" / "ticker_readiness_report.previous.csv",
        "ticker,overall_readiness_state\nAAA,blocked\n",
    )

    preflight = build_reviewed_batch_preflight(
        tmp_path,
        lane="peers",
        top_n=10,
        batch_id="RB-PEERS",
        review_date="2026-06-12",
    )

    assert preflight.lane_scope == "Peer Mapping, Peer Valuation Inputs"
    assert preflight.dry_run_command == "make peer-mapping-queue TOP_N=10"
    assert "data/reports/peer_unlock_worklist.csv" in preflight.expected_artifacts
