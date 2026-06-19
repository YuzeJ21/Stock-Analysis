import os
from pathlib import Path

from scripts.diff_hygiene import StatusEntry

from src import pilot_readiness
from src.pilot_readiness import (
    build_pilot_readiness_checks,
    build_readiness_snapshot,
    pilot_readiness_verdict,
    render_pilot_readiness_checks,
    write_pilot_readiness_packet,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sample_root(tmp_path: Path) -> Path:
    root = tmp_path
    _write(root / "data" / "prices.csv", "ticker,date,close\nAAA,2026-01-01,10\n")
    _write(
        root / "data" / "fundamentals.csv",
        "ticker,revenue,free_cash_flow,fcf_margin,shares_outstanding\nAAA,100,10,0.10,\n",
    )
    _write(root / "data" / "peers.csv", "ticker,peer_ticker,source\n")
    _write(root / "data" / "earnings.csv", "ticker,source\n")
    _write(root / "data" / "analyst_estimates.csv", "ticker,source\n")
    _write(
        root / "data" / "reports" / "ticker_readiness_report.csv",
        (
            "ticker,asset_type,price_ready,fundamentals_ready,dcf_ready,peer_ready,earnings_ready,"
            "analyst_estimates_ready,overall_readiness_state,blocked_features,excluded_features,missing_data\n"
            "AAA,company,true,true,false,false,false,false,partial,dcf peer earnings analyst_estimates,,"
            "dcf: shares_outstanding; peers: needs at least 2 source-backed peer mappings\n"
        ),
    )
    _write(
        root / "data" / "reports" / "feature_readiness_summary.csv",
        (
            "feature,ready_count,partial_count,blocked_count,excluded_count,total_count,top_blocker,next_action,unlock_command\n"
            "price,1,0,0,0,1,-,-,-\n"
            "fundamentals,1,0,0,0,1,-,-,-\n"
        ),
    )
    _write(
        root / "data" / "reports" / "peer_readiness_report.csv",
        (
            "ticker,peer_count,mapping_status,peer_blocker_type,peer_price_ready,peer_momentum_ready,"
            "peer_fundamentals_ready,peer_valuation_ready,peer_valuation_comparison_ready\n"
            "AAA,0,missing,missing_peer_mapping,false,false,false,false,false\n"
        ),
    )
    _write(
        root / "data" / "reports" / "peer_unlock_worklist.csv",
        "priority,ticker,workflow_group,missing_peer_reason\n1,AAA,dcf_ready_peer_mapping,needs peers\n",
    )
    _write(root / "data" / "reviewed_batch_proofs.csv", "batch_id,lane,final_outcome\nRB-1,fundamentals,still_blocked\n")
    return root


def test_pilot_readiness_check_keeps_generated_churn_manual_not_blocking(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "data/prices.csv")])

    checks = build_pilot_readiness_checks(root, top_n=2)
    by_area = {check.area: check for check in checks}
    rendered = render_pilot_readiness_checks(checks)

    assert by_area["GitHub sync"].status == "green"
    assert by_area["Generated artifact hygiene"].status == "manual"
    assert by_area["Readiness freshness"].status == "green"
    assert by_area["Source proof gates"].status == "manual"
    assert by_area["Public safety"].command == "make public-check"
    assert pilot_readiness_verdict(checks) == "pilot-ready with manual gates"
    assert "does not refresh data, apply imports, stage files, commit, push, or rewrite CSVs" in rendered
    assert "not investment advice" in rendered
    assert "missing fundamentals" in rendered
    assert "trade instruction" in rendered


def test_pilot_readiness_blocks_product_dirty_and_stale_readiness(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "src/dashboard.py")])
    source_path = root / "data" / "fundamentals.csv"
    old_time = 1_700_000_000
    new_time = old_time + 100
    os.utime(root / "data" / "reports" / "ticker_readiness_report.csv", (old_time, old_time))
    os.utime(root / "data" / "reports" / "feature_readiness_summary.csv", (old_time, old_time))
    os.utime(source_path, (new_time, new_time))

    checks = build_pilot_readiness_checks(root, top_n=2)
    by_area = {check.area: check for check in checks}

    assert by_area["Generated artifact hygiene"].status == "blocked"
    assert "product/code/docs/test" in by_area["Generated artifact hygiene"].detail
    assert by_area["Readiness freshness"].status == "blocked"
    assert by_area["Readiness freshness"].command == "make readiness"
    assert pilot_readiness_verdict(checks) == "blocked"


def test_pilot_readiness_blocks_unsynced_remote(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main [behind 1]")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [])

    checks = build_pilot_readiness_checks(root, top_n=2)
    by_area = {check.area: check for check in checks}

    assert by_area["GitHub sync"].status == "blocked"
    assert by_area["GitHub sync"].command == "git pull --ff-only"


def test_pilot_readiness_treats_pending_packet_as_manual_reviewed_evidence(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(
        pilot_readiness,
        "load_status",
        lambda _root: [StatusEntry("??", "outputs/pilot_readiness_packet.md")],
    )

    checks = build_pilot_readiness_checks(root, top_n=2)
    by_area = {check.area: check for check in checks}

    assert by_area["Generated artifact hygiene"].status == "manual"
    assert "reviewed pilot packet" in by_area["Generated artifact hygiene"].detail
    assert pilot_readiness_verdict(checks) == "pilot-ready with manual gates"


def test_pilot_readiness_packet_writes_review_ready_markdown_without_data_writes(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    output = Path("outputs/pilot_readiness_packet.md")
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main [ahead 1]")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "data/prices.csv")])

    packet_path = write_pilot_readiness_packet(root, top_n=2, output=output)
    body = packet_path.read_text(encoding="utf-8")
    snapshot = build_readiness_snapshot(root)

    assert packet_path == root / output
    assert snapshot.total_tickers == 1
    assert snapshot.price_ready == 1
    assert "# Pilot Readiness Packet" in body
    assert "Verdict: pilot-ready with manual gates" in body
    assert "GitHub sync" in body
    assert "Generated artifact hygiene" in body
    assert "Readiness Snapshot" in body
    assert "Source-Proof Queue Summary" in body
    assert "Latest Reviewed Batch Proof" in body
    assert "Manual Gates Still Required" in body
    assert "Generated Artifacts Excluded From Staging" in body
    assert "data/prices.csv" in body
    assert "not investment advice" in body
    assert "No broker integration" in body
    assert "direct buy/sell instructions" in body
    assert "Blocked source inputs remain blocked" in body
    assert "refresh data, apply imports, record proof, stage files, commit, push" in body
