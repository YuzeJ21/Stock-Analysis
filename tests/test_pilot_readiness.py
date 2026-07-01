import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.diff_hygiene import StatusEntry

from src import pilot_readiness
from src.pilot_readiness import (
    build_pilot_commit_package_handoff,
    build_pilot_handoff_summary,
    build_pilot_readiness_checks,
    build_readiness_snapshot,
    pilot_readiness_verdict,
    render_pilot_readiness_checks,
    write_pilot_readiness_packet,
)


@pytest.fixture(autouse=True)
def _stable_browser_qa_payload(monkeypatch):
    monkeypatch.setattr(
        pilot_readiness,
        "browser_qa_evidence_payload",
        lambda _root: {
            "verdict": "ready_with_manual_capture_pending",
            "committed_screenshot_assets": [
                {"Asset": "LinkedIn public dashboard thumbnail", "State": "ready"},
                {"Asset": "Public visitor home screenshot", "State": "ready"},
                {"Asset": "Operator metrics lane screenshot", "State": "ready"},
            ],
            "manual_capture_targets": [
                {"Capture Target": "Single-stock workflow fit screenshot", "State": "manual_capture_pending"},
                {"Capture Target": "Data Health proof lane screenshot", "State": "manual_capture_pending"},
            ],
            "reviewed_asset_stage_command": (
                "git add -- docs/assets/single-stock-workflow-fit-real.jpg "
                "docs/assets/operator-data-health-proof-real.jpg "
                "docs/assets/operator-data-health-queue-routing-real.jpg"
            ),
        },
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
    rendered = render_pilot_readiness_checks(
        checks,
        source_queues=[
            {
                "queue": "Trusted Fundamentals Proof Queue",
                "state": "partial",
                "blocked": 90,
                "top_blockers": "fundamentals_bundle_plus_shares: 90",
                "next_safe_command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
            }
        ],
        excluded_artifacts=["data/prices.csv"],
        commit_handoff=build_pilot_commit_package_handoff(root),
    )

    assert by_area["GitHub sync"].status == "green"
    assert by_area["Generated artifact hygiene"].status == "manual"
    assert by_area["Readiness freshness"].status == "green"
    assert by_area["Source proof gates"].status == "manual"
    assert by_area["Browser QA evidence"].status == "manual"
    assert by_area["Browser QA evidence"].command == "make browser-qa-evidence"
    assert "3 committed screenshot asset" in by_area["Browser QA evidence"].detail
    assert "Single-stock workflow fit screenshot" in by_area["Browser QA evidence"].detail
    assert "Reviewed asset staging command is available" in by_area["Browser QA evidence"].detail
    assert by_area["Public safety"].command == "make public-check"
    assert pilot_readiness_verdict(checks) == "pilot-ready with manual gates"
    assert "does not refresh data, apply imports, stage files, commit, push, or rewrite CSVs" in rendered
    assert "Trusted Fundamentals Proof Queue" in rendered
    assert "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10" in rendered
    assert "Commit Package Handoff" in rendered
    assert "Browser QA evidence" in rendered
    assert "make browser-qa-evidence" in rendered
    assert "Reviewed asset staging command is available" in rendered
    assert "Stage reviewed product package" in rendered
    assert "git add --" not in rendered
    assert "# no product/code/docs/test files to stage" in rendered
    assert "# no reviewed product package to commit" in rendered
    assert "do not create a release commit just for excluded generated churn" in rendered.lower()
    assert "1 generated artifact(s) excluded by default" in rendered
    assert "data/*.csv" in rendered
    assert "data/reports/*.csv" in rendered
    assert "outputs/*.csv" in rendered
    assert "ticker_readiness_report.previous.csv" in rendered
    assert "not investment advice" in rendered
    assert "missing fundamentals" in rendered
    assert "trade instruction" in rendered


def test_pilot_readiness_keeps_broad_sample_report_churn_manual_not_blocking(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(
        pilot_readiness,
        "load_status",
        lambda _root: [
            StatusEntry("M", "outputs/stock_reports/apld.md"),
            StatusEntry("??", "outputs/stock_reports/newco.md"),
            StatusEntry("M", "data/prices.csv"),
        ],
    )

    checks = build_pilot_readiness_checks(root, top_n=2)
    by_area = {check.area: check for check in checks}
    handoff = build_pilot_commit_package_handoff(root)
    rendered = render_pilot_readiness_checks(
        checks,
        source_queues=[
            {
                "queue": "Trusted Fundamentals Proof Queue",
                "state": "partial",
                "blocked": 90,
                "top_blockers": "fundamentals_bundle_plus_shares: 90",
                "next_safe_command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
            }
        ],
        excluded_artifacts=[
            "outputs/stock_reports/apld.md",
            "outputs/stock_reports/newco.md",
            "data/prices.csv",
        ],
        commit_handoff=handoff,
    )

    assert by_area["Generated artifact hygiene"].status == "manual"
    assert "sample report" in by_area["Generated artifact hygiene"].detail
    assert pilot_readiness_verdict(checks) == "pilot-ready with manual gates"
    assert handoff[0].status == "no_product_changes"
    assert handoff[0].command == "# no product/code/docs/test files to stage"
    assert "do not stage broad generated stock reports" in rendered.lower()


def test_pilot_commit_package_handoff_prints_product_stage_and_generated_exclusion(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(
        pilot_readiness,
        "load_status",
        lambda _root: [
            StatusEntry("M", "README.md"),
            StatusEntry("M", "src/dashboard.py"),
            StatusEntry("M", "data/prices.csv"),
        ],
    )

    handoff = build_pilot_commit_package_handoff(root)
    rendered = " ".join(
        " ".join([item.step, item.status, item.command, item.boundary])
        for item in handoff
    ).lower()

    assert handoff[0].step == "Stage reviewed product package"
    assert handoff[0].status == "ready_to_stage"
    assert "git add -- readme.md src/dashboard.py" in rendered
    assert "do not use git add -a" in rendered
    assert "make staged-hygiene-check && git diff --cached --check" in rendered
    assert 'git commit -m "package reviewed product changes"' in rendered
    assert "1 generated csv/json/report artifact" in rendered
    assert "data/*.csv" in rendered
    assert "data/reports/*.csv" in rendered
    assert "outputs/*.csv" in rendered
    assert "ticker_readiness_report.previous.csv" in rendered
    assert "stage only a specific reviewed evidence artifact" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pilot_handoff_summary_surfaces_reviewer_next_steps(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(
        pilot_readiness,
        "load_status",
        lambda _root: [StatusEntry("M", "data/prices.csv")],
    )
    checks = build_pilot_readiness_checks(root, top_n=2)
    handoff = build_pilot_handoff_summary(
        checks,
        source_queues=[
            {
                "queue": "Trusted Fundamentals Proof Queue",
                "state": "partial",
                "blocked": 90,
                "top_blockers": "fundamentals_bundle_plus_shares: 90",
                "next_safe_command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
            }
        ],
        excluded_artifacts=["data/prices.csv"],
    )
    rendered = " ".join(
        " ".join(
            [
                item.question,
                item.status,
                item.answer,
                item.next_safe_command,
                item.boundary,
            ]
        )
        for item in handoff
    ).lower()

    assert [item.question for item in handoff] == [
        "Can this be shared as a pilot?",
        "What must be reviewed first?",
        "What blocks deeper analysis?",
        "What stays out of staging?",
        "What should the reviewer run next?",
    ]
    assert "pilot-ready with manual gates" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "make dcf-input-source-command-plan" in rendered
    assert "1 generated artifact(s) excluded by default" in rendered
    assert "data/*.csv" in rendered
    assert "data/reports/*.csv" in rendered
    assert "outputs/*.csv" in rendered
    assert "ticker_readiness_report.previous.csv" in rendered
    assert "make pilot-readiness-packet output=outputs/pilot_readiness_packet.md" in rendered
    assert "not an analysis or recommendation unlock" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pilot_handoff_summary_uses_queue_priority_order_not_raw_blocked_count():
    checks = [
        pilot_readiness.PilotReadinessCheck(
            area="Source proof gates",
            status="manual",
            title="DCF Input Proof Batches leads the source-review queue",
            detail="Source review remains manual.",
            command="make data-coverage-proof-queues TOP_N=10",
            stop_rule="Do not call a lane supported until proof passes.",
        )
    ]

    handoff = build_pilot_handoff_summary(
        checks,
        source_queues=[
            {
                "queue": "DCF Input Proof Batches",
                "state": "partial",
                "blocked": 3458,
                "top_blockers": "fundamentals_bundle_plus_shares: 3459",
                "next_safe_command": "make dcf-input-proof-queue TOP_N=10",
            },
            {
                "queue": "Peer Mapping Proof Queue",
                "state": "partial",
                "blocked": 3512,
                "top_blockers": "source-backed peer mappings: 3512",
                "next_safe_command": "DRY_RUN=1 make peer-mapping-source-review TOP_N=10",
            },
        ],
    )

    proof_item = next(item for item in handoff if item.question == "What blocks deeper analysis?")

    assert proof_item.answer == "DCF Input Proof Batches"
    assert proof_item.next_safe_command == "make dcf-input-proof-queue TOP_N=10"
    assert "3,458 blocked item" in proof_item.boundary


def test_pilot_readiness_checks_reuse_prebuilt_source_queues(monkeypatch, tmp_path: Path):
    root = _sample_root(tmp_path)
    calls = {"count": 0}

    def _unexpected_queue_build(*_args, **_kwargs):
        calls["count"] += 1
        return []

    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [])
    monkeypatch.setattr(pilot_readiness, "build_data_coverage_proof_queues", _unexpected_queue_build)
    source_queues = [
        SimpleNamespace(
            label="DCF Input Proof Batches",
            readiness_state="partial",
            blocked_count=10,
            partial_count=2,
            ready_count=1,
        )
    ]

    checks = build_pilot_readiness_checks(root, top_n=10, source_queues=source_queues)
    source_check = next(check for check in checks if check.area == "Source proof gates")

    assert calls["count"] == 0
    assert source_check.status == "manual"
    assert source_check.title == "DCF Input Proof Batches leads the source-review queue"


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
    assert "Reviewer Handoff Summary" in body
    assert "Commit Package Handoff" in body
    assert "Can this be shared as a pilot?" in body
    assert "What stays out of staging?" in body
    assert "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md" in body
    assert "GitHub sync" in body
    assert "Generated artifact hygiene" in body
    assert "Browser QA evidence" in body
    assert "pending workflow capture" in body.lower()
    assert "Readiness Snapshot" in body
    assert "Source-Proof Queue Summary" in body
    assert "Latest Reviewed Batch Proof" in body
    assert "Manual Gates Still Required" in body
    assert "Generated Artifacts Excluded From Staging" in body
    assert "Default broad exclusion patterns" in body
    assert "Currently dirty generated artifacts" in body
    assert "data/prices.csv" in body
    assert "data/*.csv" in body
    assert "data/reports/*.csv" in body
    assert "outputs/*.csv" in body
    assert "ticker_readiness_report.previous.csv" in body
    assert "not investment advice" in body
    assert "No broker integration" in body
    assert "direct buy/sell instructions" in body
    assert "Blocked source inputs remain blocked" in body
    assert "refresh data, apply imports, record proof, stage files, commit, push" in body
