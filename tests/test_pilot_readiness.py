import json
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
    render_pilot_share_brief,
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
    assert by_area["License status"].status == "manual"
    assert by_area["License status"].command == "make license-status"
    assert "portfolio/demo only" in by_area["License status"].detail
    assert by_area["Public safety"].command == "make public-check"
    assert pilot_readiness_verdict(checks) == "pilot-ready with manual gates"
    assert "does not refresh data, apply imports, stage files, commit, push, or rewrite CSVs" in rendered
    assert "Trusted Fundamentals Proof Queue" in rendered
    assert "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10" in rendered
    assert "Commit Package Handoff" in rendered
    assert "Browser QA evidence" in rendered
    assert "License status" in rendered
    assert "What license boundary applies?" in rendered
    assert "No root LICENSE file found" in rendered
    assert "do not describe as open source" in rendered
    assert "portfolio context only" in rendered
    assert "copying, redistribution, adaptation, or software reuse rights" in rendered
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
        "What license boundary applies?",
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
    assert "no root license file found" in rendered
    assert "make license-status" in rendered
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


def test_pilot_handoff_summary_uses_source_gate_when_no_queue_loaded():
    handoff = build_pilot_handoff_summary(
        [
            pilot_readiness.PilotReadinessCheck(
                area="Public safety",
                status="manual",
                title="Run the public share gate before pilot sharing",
                detail="The pilot checklist is read-only.",
                command="make public-check",
                stop_rule="Stop before public pilot sharing if public-check fails.",
            )
        ],
        source_queues=[],
    )

    proof_item = next(item for item in handoff if item.question == "What blocks deeper analysis?")
    rendered = " ".join([proof_item.answer, proof_item.next_safe_command, proof_item.boundary]).lower()

    assert proof_item.answer == "Check source-proof gate"
    assert proof_item.next_safe_command == "make project-status"
    assert "run project-status first" in rendered
    assert "provider setup" in rendered
    assert "make data-coverage-proof-queues" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


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


def test_pilot_readiness_source_gate_pivots_when_queues_are_reviewed_non_actionable(monkeypatch, tmp_path: Path):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [])
    preflight_path = root / "outputs" / "session_source_preflight.json"
    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    preflight_path.write_text(
        json.dumps(
            {
                "source_actionability": {
                    "fundamentals_share_count_candidates": 548,
                    "reviewed_non_actionable_fundamentals_share_count": 548,
                    "unreviewed_fundamentals_share_count_candidates": 0,
                    "dcf_queue_reviewed_non_actionable": "yes",
                    "do_not_repeat_without_new_source": "yes",
                },
                "source_activation_console_v2": {
                    "next_executable_lane": "coverage_workflow_evidence",
                    "next_executable_command": "make project-status",
                    "operator_summary": {
                        "can_run_now": ["coverage_workflow_evidence"],
                        "needs_setup": ["fmp", "alpha_vantage", "finnhub"],
                        "avoid_repeating": ["fundamentals_share_count_source_ladder"],
                        "next_step": "make project-status",
                        "next_step_reason": "Current fundamentals/share-count blockers already have reviewed non-actionable proof.",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    source_queues = [
        SimpleNamespace(
            label="DCF Input Proof Batches",
            readiness_state="partial",
            blocked_count=90,
            partial_count=243,
            ready_count=2691,
            top_blockers="fundamentals_bundle: 242, fundamentals_bundle_plus_shares: 91",
            next_safe_command="make dcf-input-proof-queue TOP_N=10",
        )
    ]

    checks = build_pilot_readiness_checks(root, top_n=10, source_queues=source_queues)
    source_check = next(check for check in checks if check.area == "Source proof gates")

    assert source_check.status == "manual"
    assert source_check.title == "Source-proof queues reviewed or exhausted"
    assert source_check.command == "make project-status"
    assert "provider setup" in source_check.detail
    assert "do not reopen broad proof queues" in source_check.stop_rule.lower()
    assert "make data-coverage-proof-queues" not in source_check.command

    handoff = build_pilot_handoff_summary(checks, source_queues=source_queues)
    proof_item = next(item for item in handoff if item.question == "What blocks deeper analysis?")
    assert proof_item.answer == "Check source-proof gate"
    assert proof_item.next_safe_command == "make project-status"
    assert "provider setup" in proof_item.boundary.lower()
    assert "make dcf-input-proof-queue" not in proof_item.next_safe_command


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


def test_pilot_readiness_treats_pending_share_brief_as_manual_reviewed_evidence(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(
        pilot_readiness,
        "load_status",
        lambda _root: [StatusEntry("??", "outputs/pilot_share_brief.md")],
    )

    checks = build_pilot_readiness_checks(root, top_n=2)
    by_area = {check.area: check for check in checks}

    assert by_area["Generated artifact hygiene"].status == "manual"
    assert "reviewed share brief" in by_area["Generated artifact hygiene"].detail
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
    assert "Provider Setup Checklist" in body
    assert "make provider-setup-checklist" in body
    assert "Provider Activation Plan" in body
    assert "Run make project-status first; if it says queues are exhausted, do not reopen broad proof loops." in body
    assert "Run that provider's one-ticker smoke command only; do not start a broad batch from setup." in body
    assert "Configure first: FMP free tier" in body
    assert "Broadest keyed fallback here: price, fundamentals, share count, and the largest stated free-tier daily cap." in body
    assert "Do not configure all missing providers at once" in body
    assert "| Provider | Setup state | Unlock lanes | Usage | Smoke command | Cannot unlock | Safe next step |" in body
    assert "FMP free tier" in body
    assert "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>" in body
    assert "Alpha Vantage free tier" in body
    assert "Finnhub free tier" in body
    assert "Full-universe refresh without caps" in body
    assert "Broker actions, order routing, auto-trading" in body
    assert "Real key values are never printed." in body
    assert "Latest Reviewed Batch Proof" in body
    assert "Manual Gates Still Required" in body
    assert "License Decision Options" in body
    assert "Portfolio showcase only" in body
    assert "Keep no license for now" in body
    assert "Let others reuse with attribution" in body
    assert "Add MIT or Apache-2.0" in body
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


def test_pilot_share_brief_writes_concise_markdown_without_data_writes(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    output = Path("outputs/pilot_share_brief.md")
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main [ahead 1]")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "data/prices.csv")])

    brief_path = pilot_readiness.write_pilot_share_brief(root, top_n=2, output=output)
    body = brief_path.read_text(encoding="utf-8")

    assert brief_path == root / output
    assert "# Pilot Share Brief" in body
    assert "research-only product evidence" in body
    assert "What can be used now" in body
    assert "Price-ready setup coverage" in body
    assert "What is still blocked" in body
    assert "What must stay out of the share package" in body
    assert "data/prices.csv" in body
    assert "No root LICENSE file found" in body
    assert "refresh data" not in body.lower()
    assert "apply imports" not in body.lower()


def test_pilot_share_brief_summarizes_usable_blocked_and_share_boundary(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main [ahead 1]")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "data/prices.csv")])
    source_queues = [
        SimpleNamespace(
            label="DCF Input Proof Batches",
            readiness_state="partial",
            ready_count=3,
            partial_count=2,
            blocked_count=10,
            top_blockers="fundamentals_bundle_plus_shares: 10",
            next_safe_command="make dcf-input-proof-queue TOP_N=10",
        )
    ]
    checks = build_pilot_readiness_checks(root, top_n=2, source_queues=source_queues)

    brief = render_pilot_share_brief(
        checks=checks,
        snapshot=build_readiness_snapshot(root),
        source_queues=source_queues,
        excluded_artifacts=["data/prices.csv"],
    )

    assert "# Pilot Share Brief" in brief
    assert "research-only product evidence" in brief
    assert "What can be used now" in brief
    assert "Price-ready setup coverage: 1/1" in brief
    assert "Price coverage: 1/1" not in brief
    assert "DCF-ready operating-company coverage: 0/1" in brief
    assert "What is still blocked" in brief
    assert "DCF Input Proof Batches" in brief
    assert "fundamentals_bundle_plus_shares: 10" in brief
    assert "How to demo or review next" in brief
    assert "make universe-scope TOP_N=10" in brief
    assert "make risk-context" in brief
    assert "make public-check" in brief
    assert "Screenshots and scope/risk context do not update saved data or unlock blocked inputs" in brief
    assert "What must stay out of the share package" in brief
    assert "data/prices.csv" in brief
    assert "License boundary" in brief
    assert "No root LICENSE file found" in brief
    assert "not investment advice" in brief
    assert "buy" not in brief.lower()
    assert "sell" not in brief.lower()


def test_pilot_share_brief_routes_reviewed_source_queues_through_project_status(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [])
    source_queues = [
        SimpleNamespace(
            label="DCF Input Proof Batches",
            readiness_state="partial",
            ready_count=3,
            partial_count=2,
            blocked_count=10,
            top_blockers="reviewed non-actionable source ladder blockers",
            next_safe_command="make dcf-input-proof-queue TOP_N=10",
            reviewed_proof_status=(
                "current DCF/share-count source ladder has only reviewed non-actionable blockers; "
                "wait for new provider data before repeating this proof loop."
            ),
        )
    ]

    brief = render_pilot_share_brief(
        checks=build_pilot_readiness_checks(root, top_n=2, source_queues=source_queues),
        snapshot=build_readiness_snapshot(root),
        source_queues=source_queues,
        excluded_artifacts=[],
    )

    assert "Source-proof queues reviewed or exhausted" in brief
    assert "Next source-proof command: `make project-status`" in brief
    assert "make dcf-input-proof-queue TOP_N=10" not in brief
    assert "provider setup" in brief.lower()
    assert "buy" not in brief.lower()
    assert "sell" not in brief.lower()


def test_pilot_share_brief_names_provider_setup_path_without_secrets(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main [ahead 1]")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "data/prices.csv")])
    monkeypatch.setenv("FMP_API_KEY", "secret-fmp-key")
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("IBKR_HOST", raising=False)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    monkeypatch.delenv("IBKR_CLIENT_ID", raising=False)
    outputs_dir = root / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    (outputs_dir / "session_source_preflight.json").write_text(
        json.dumps(
            {
                "source_activation_console_v2": {
                    "operator_summary": {
                        "can_run_now": ["coverage_workflow_evidence"],
                        "needs_setup": ["fmp", "alpha_vantage", "finnhub"],
                        "avoid_repeating": ["fundamentals_share_count_source_ladder"],
                        "next_step": "make project-status",
                        "next_step_reason": "Current proof queues are exhausted.",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    brief = render_pilot_share_brief(
        checks=build_pilot_readiness_checks(root, top_n=2),
        snapshot=build_readiness_snapshot(root),
        source_queues=[],
        excluded_artifacts=["data/prices.csv"],
        root=root,
    )

    assert "How coverage expands next" in brief
    assert "make provider-setup-checklist" in brief
    assert "Coverage unlock decision" in brief
    assert "No broad coverage batch should run from setup alone" in brief
    assert "Provider setup only makes a source executable" in brief
    assert "readiness changes still require validate, preview, rejected-row review" in brief
    assert "Do not retry fundamentals_share_count_source_ladder" in brief
    assert "proof queues.." not in brief
    assert "Configure first: Finnhub free tier" in brief
    assert "Second fallback after FMP" in brief
    assert "Do not configure all missing providers at once" in brief
    assert "FMP free tier: configured -> price, fundamentals, share_count" in brief
    assert "smoke: `make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`" in brief
    assert "Alpha Vantage free tier: needs_key -> price, fundamentals, share_count" in brief
    assert "smoke: `make alpha-vantage-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`" in brief
    assert "Finnhub free tier: needs_key -> price, fundamentals, share_count" in brief
    assert "IBKR read-only: optional_disabled -> price" in brief
    assert "Real key values are never printed" in brief
    assert "secret-fmp-key" not in brief
