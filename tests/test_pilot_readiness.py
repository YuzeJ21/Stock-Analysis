import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts.diff_hygiene import StatusEntry
from src.paths import DataProfile

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


@pytest.mark.parametrize("profile", ["", "unknown", "<default|demo|local>"])
def test_pilot_readiness_checks_reject_non_concrete_profile_even_with_prebuilt_queues(tmp_path, profile):
    with pytest.raises(ValueError, match="concrete readiness profile"):
        build_pilot_readiness_checks(
            tmp_path,
            profile=profile,
            source_queues=[],
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


def _write_local_profile_fixture(root: Path) -> None:
    local_data = root / "data" / "local"
    local_outputs = root / "outputs" / "local"
    _write(local_data / "prices.csv", "ticker,date,close\nLOCAL1,2026-01-01,10\nLOCAL2,2026-01-01,20\n")
    _write(
        local_data / "fundamentals.csv",
        "ticker,revenue,free_cash_flow,fcf_margin,shares_outstanding\nLOCAL1,100,10,0.10,10\nLOCAL2,200,20,0.10,20\n",
    )
    _write(local_data / "peers.csv", "ticker,peer_ticker,source\n")
    _write(local_data / "earnings.csv", "ticker,source\n")
    _write(local_data / "analyst_estimates.csv", "ticker,source\n")
    _write(
        local_data / "reports" / "ticker_readiness_report.csv",
        (
            "ticker,asset_type,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready,earnings_ready,"
            "analyst_estimates_ready,overall_readiness_state,blocked_features,excluded_features,missing_data\n"
            "LOCAL1,company,true,true,true,true,false,false,false,partial,peer,,,\n"
            "LOCAL2,company,true,false,true,false,true,false,false,partial,dcf,,,\n"
        ),
    )
    _write(
        local_data / "reports" / "data_source_status.csv",
        "source,status,manual_fallback_available\nlocal-one,available,false\nlocal-two,manual_only,true\n",
    )
    _write(
        local_outputs / "research_action_queue.csv",
        "priority,ticker,action\nP0,LOCAL1,review\nP2,LOCAL2,review\n",
    )
    _write(
        local_data / "reviewed_batch_proofs.csv",
        (
            "batch_id,lane,final_outcome,notes\n"
            "RB-LOCAL-1,prices,still_blocked,local first\n"
            "RB-LOCAL-2,fundamentals,supported,local latest\n"
        ),
    )


def _local_queue_row() -> SimpleNamespace:
    return SimpleNamespace(
        label="Local Profile Proof Queue",
        readiness_state="partial",
        ready_count=2,
        partial_count=1,
        blocked_count=1,
        top_blockers="local-only blocker: 1",
        next_safe_command="make project-status-check",
        reviewed_proof_status="unreviewed local fixture",
    )


def test_local_profile_snapshot_reads_local_counts_sources_and_actions_only(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    _write_local_profile_fixture(root)
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "default")

    from src import project_status

    monkeypatch.setattr(
        project_status,
        "build_project_status_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("exercise CSV fallback")),
    )

    snapshot = build_readiness_snapshot(root, profile="local")

    assert snapshot.total_tickers == 2
    assert snapshot.price_ready == 2
    assert snapshot.momentum_ready == 1
    assert snapshot.dcf_ready == 1
    assert snapshot.peer_ready == 1
    assert snapshot.data_sources_available == 1
    assert snapshot.data_sources_total == 2
    assert snapshot.optional_manual_lanes_locked == 1
    assert snapshot.missing_data_steps == 2
    assert snapshot.urgent_missing_data_steps == 1


def test_pilot_rejects_forged_data_profile_paths(tmp_path: Path):
    root = _sample_root(tmp_path)
    _write_local_profile_fixture(root)
    forged = DataProfile(
        name="local",
        data_dir=(root / "data").resolve(),
        outputs_dir=(root / "outputs").resolve(),
    )

    with pytest.raises(ValueError, match="validated selected profile paths"):
        build_readiness_snapshot(root, profile=forged)


def test_local_profile_controls_freshness_source_queue_preflight_and_proof_ledger(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    _write_local_profile_fixture(root)
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "default")
    seen: dict[str, object] = {}

    def _freshness(_root, *, profile=None, data_dir=None, output_dir=None):
        seen["freshness"] = (profile, Path(data_dir), Path(output_dir))
        return SimpleNamespace(status="current", message="local profile current")

    def _queues(_root, *, profile, top_n, data_dir=None, output_dir=None):
        seen["queues"] = (profile, top_n, Path(data_dir), Path(output_dir))
        return [_local_queue_row()]

    def _preflight(_root, *, output_dir=None):
        seen["preflight"] = Path(output_dir)
        return None

    monkeypatch.setattr(pilot_readiness, "readiness_freshness_status", _freshness)
    monkeypatch.setattr(pilot_readiness, "build_data_coverage_proof_queues", _queues)
    monkeypatch.setattr(pilot_readiness, "load_session_source_preflight", _preflight)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [])

    checks = build_pilot_readiness_checks(root, profile="local", top_n=7)
    by_area = {check.area: check for check in checks}

    assert seen == {
        "freshness": ("local", root / "data" / "local", root / "outputs" / "local"),
        "queues": ("local", 7, root / "data" / "local", root / "outputs" / "local"),
        "preflight": root / "outputs" / "local",
    }
    assert by_area["Readiness freshness"].detail == "local profile current"
    assert by_area["Proof ledger"].title == "2 reviewed batch proof row(s)"
    assert "RB-LOCAL-2" in by_area["Proof ledger"].detail


def test_local_profile_packet_and_share_defaults_stay_in_local_outputs(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    _write_local_profile_fixture(root)
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "default")

    from src import project_status

    monkeypatch.setattr(
        project_status,
        "build_project_status_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("exercise CSV fallback")),
    )
    monkeypatch.setattr(
        pilot_readiness,
        "readiness_freshness_status",
        lambda *_args, **_kwargs: SimpleNamespace(status="current", message="local profile current"),
    )
    monkeypatch.setattr(pilot_readiness, "build_data_coverage_proof_queues", lambda *_args, **_kwargs: [_local_queue_row()])
    monkeypatch.setattr(pilot_readiness, "load_session_source_preflight", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [])

    packet_path = write_pilot_readiness_packet(root, profile="local", top_n=2)
    share_path = pilot_readiness.write_pilot_share_brief(root, profile="local", top_n=2)
    packet = packet_path.read_text(encoding="utf-8")
    share = share_path.read_text(encoding="utf-8")

    assert packet_path == root / "outputs" / "local" / "pilot_readiness_packet.md"
    assert share_path == root / "outputs" / "local" / "pilot_share_brief.md"
    assert "| Tracked tickers | 2 |" in packet
    assert "RB-LOCAL-2 / fundamentals / supported / local latest" in packet
    assert "make pilot-readiness-packet PROFILE=local OUTPUT=outputs/local/pilot_readiness_packet.md" in packet
    assert "Price-ready setup coverage: 2/2" in share
    assert not (root / "outputs" / "pilot_readiness_packet.md").exists()
    assert not (root / "outputs" / "pilot_share_brief.md").exists()


def test_pilot_cli_and_make_leave_implicit_output_profile_scoped():
    packet_args = pilot_readiness.parse_args(["--profile", "local", "--packet"])
    share_args = pilot_readiness.parse_args(["--profile", "demo", "--share-brief"])

    assert packet_args.output is None
    assert share_args.output is None

    for target, profile in (("pilot-readiness-packet", "local"), ("pilot-share-brief", "demo")):
        result = subprocess.run(
            ["make", "-n", target, f"PROFILE={profile}"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
        )
        assert f'--profile "{profile}"' in result.stdout
        assert "--output" not in result.stdout


def test_pilot_check_renderer_keeps_selected_profile_in_reviewer_handoff():
    rendered = render_pilot_readiness_checks(
        [],
        profile="local",
        packet_path="outputs/local/pilot_readiness_packet.md",
    )

    assert (
        "make pilot-readiness-packet PROFILE=local "
        "OUTPUT=outputs/local/pilot_readiness_packet.md"
    ) in rendered
    assert "make pilot-readiness-packet PROFILE=default" not in rendered


def test_pilot_readiness_check_keeps_generated_churn_manual_not_blocking(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "data/prices.csv")])

    checks = build_pilot_readiness_checks(root, profile="default", top_n=2)
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
    assert "license-status" in by_area["Public safety"].detail
    assert "license boundary" in by_area["Public safety"].stop_rule
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

    checks = build_pilot_readiness_checks(root, profile="default", top_n=2)
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
    checks = build_pilot_readiness_checks(root, profile="default", top_n=2)
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
        "What is the share package answer?",
        "Can this be shared as a pilot?",
        "What must be reviewed first?",
        "What blocks deeper analysis?",
        "What stays out of staging?",
        "What license boundary applies?",
        "What should the reviewer run next?",
    ]
    assert "share as portfolio/demo only with manual gates" in rendered
    assert "keep generated churn excluded" in rendered
    assert "source-proof blockers stay visible" in rendered
    assert "license boundary still applies" in rendered
    assert "until a root license exists" in rendered
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
    assert "make pilot-readiness-packet profile=default output=outputs/pilot_readiness_packet.md" in rendered
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
    assert proof_item.next_safe_command == "make project-status-check"
    assert "run project-status-check first" in rendered
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

    checks = build_pilot_readiness_checks(root, profile="default", top_n=10, source_queues=source_queues)
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
                    "next_executable_command": "make project-status-check",
                    "operator_summary": {
                        "can_run_now": ["coverage_workflow_evidence"],
                        "needs_setup": ["fmp", "alpha_vantage", "finnhub"],
                        "avoid_repeating": ["fundamentals_share_count_source_ladder"],
                        "next_step": "make project-status-check",
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

    checks = build_pilot_readiness_checks(root, profile="default", top_n=10, source_queues=source_queues)
    source_check = next(check for check in checks if check.area == "Source proof gates")

    assert source_check.status == "manual"
    assert source_check.title == "Source-proof queues reviewed or exhausted"
    assert source_check.command == "make project-status-check"
    assert "provider setup" in source_check.detail
    assert "do not reopen broad proof queues" in source_check.stop_rule.lower()
    assert "make data-coverage-proof-queues" not in source_check.command

    handoff = build_pilot_handoff_summary(checks, source_queues=source_queues)
    proof_item = next(item for item in handoff if item.question == "What blocks deeper analysis?")
    assert proof_item.answer == "Check source-proof gate"
    assert proof_item.next_safe_command == "make project-status-check"
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

    checks = build_pilot_readiness_checks(root, profile="default", top_n=2)
    by_area = {check.area: check for check in checks}

    assert by_area["Generated artifact hygiene"].status == "blocked"
    assert "product/code/docs/test" in by_area["Generated artifact hygiene"].detail
    assert by_area["Readiness freshness"].status == "blocked"
    assert by_area["Readiness freshness"].command == "make readiness-preview TOP_N=20"
    assert "preview" in by_area["Readiness freshness"].stop_rule.lower()
    assert "final counts" in by_area["Readiness freshness"].stop_rule.lower()
    assert pilot_readiness_verdict(checks) == "blocked"


def test_pilot_readiness_blocks_unsynced_remote(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main [behind 1]")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [])

    checks = build_pilot_readiness_checks(root, profile="default", top_n=2)
    by_area = {check.area: check for check in checks}

    assert by_area["GitHub sync"].status == "blocked"
    assert by_area["GitHub sync"].command == "git pull --ff-only"


@pytest.mark.parametrize(
    ("comparison", "expected_status", "expected_command"),
    [
        (pilot_readiness.GitSyncComparison("origin/main", 0, 0, True), "green", "git status --short --branch"),
        (pilot_readiness.GitSyncComparison("origin/main", 0, 1, True), "manual", "git push"),
        (pilot_readiness.GitSyncComparison("origin/main", 1, 0, True), "blocked", "git pull --ff-only"),
        (pilot_readiness.GitSyncComparison("origin/main", 1, 1, True), "blocked", "git status --short --branch"),
        (pilot_readiness.GitSyncComparison("origin/main", 0, 1, False), "manual", "git push -u origin HEAD"),
    ],
)
def test_sync_check_uses_commit_counts_and_upstream_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    comparison,
    expected_status: str,
    expected_command: str,
):
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## codex/feature")
    monkeypatch.setattr(pilot_readiness, "_git_sync_comparison", lambda _root: comparison)

    check = pilot_readiness._sync_check(tmp_path)

    assert check.status == expected_status
    assert check.command == expected_command


def test_sync_check_is_manual_when_branch_has_no_upstream_or_comparable_remote(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## codex/feature")
    monkeypatch.setattr(pilot_readiness, "_git_sync_comparison", lambda _root: None)

    check = pilot_readiness._sync_check(tmp_path)

    assert check.status == "manual"
    assert "cannot be verified" in check.detail


def test_pilot_readiness_treats_pending_packet_as_manual_reviewed_evidence(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main")
    monkeypatch.setattr(
        pilot_readiness,
        "load_status",
        lambda _root: [StatusEntry("??", "outputs/pilot_readiness_packet.md")],
    )

    checks = build_pilot_readiness_checks(root, profile="default", top_n=2)
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

    checks = build_pilot_readiness_checks(root, profile="default", top_n=2)
    by_area = {check.area: check for check in checks}

    assert by_area["Generated artifact hygiene"].status == "manual"
    assert "reviewed share brief" in by_area["Generated artifact hygiene"].detail
    assert pilot_readiness_verdict(checks) == "pilot-ready with manual gates"


def test_pilot_readiness_packet_writes_review_ready_markdown_without_data_writes(tmp_path: Path, monkeypatch):
    root = _sample_root(tmp_path)
    output = Path("outputs/pilot_readiness_packet.md")
    monkeypatch.setattr(pilot_readiness, "_git_status_line", lambda _root: "## main...origin/main [ahead 1]")
    monkeypatch.setattr(pilot_readiness, "load_status", lambda _root: [StatusEntry("M", "data/prices.csv")])

    packet_path = write_pilot_readiness_packet(root, profile="default", top_n=2, output=output)
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
    assert "make pilot-readiness-packet PROFILE=default OUTPUT=outputs/pilot_readiness_packet.md" in body
    assert "GitHub sync" in body
    assert "Generated artifact hygiene" in body
    assert "Browser QA evidence" in body
    assert "pending workflow capture" in body.lower()
    assert "Readiness Snapshot" in body
    assert "Source-Proof Queue Summary" in body
    assert "Provider Setup Checklist" in body
    assert "make provider-setup-checklist" in body
    assert "Source Buckets" in body
    assert "Free public sources: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance" in body
    assert "Keyed free-tier fallbacks: configured -; needs key FMP free tier, Alpha Vantage free tier, Finnhub free tier" in body
    assert "Optional broker boundary: IBKR read-only (disabled unless explicitly configured)" in body
    assert "Provider Activation Plan" in body
    assert "Run make project-status-check first; if it says queues are exhausted, do not reopen broad proof loops." in body
    assert "Run that provider's reviewed one-ticker smoke command only; do not start a broad batch from setup." in body
    assert "Configure first: FMP free tier" in body
    assert "Broadest keyed fallback here: price, fundamentals, share count, and the largest stated free-tier daily cap." in body
    assert "Reviewed one-ticker smoke command:" in body
    assert "One-ticker smoke command:" not in body
    assert "Do not configure all missing providers at once" in body
    assert "| Provider | Setup state | Unlock lanes | Usage | Smoke command | Cannot unlock | Safe next step |" in body
    assert "FMP free tier" in body
    assert "make fmp-smoke TICKER=<ticker>" in body
    assert "Alpha Vantage free tier" in body
    assert "Finnhub free tier" in body
    assert "Full-universe refresh without caps" in body
    assert "Broker actions, order routing, auto-trading" in body
    assert "Real key values are never printed." in body
    assert "Latest Reviewed Batch Proof" in body
    assert "Manual Gates Still Required" in body
    assert "License Decision Options" in body
    assert "Controlled portfolio showcase" in body
    assert "Keep the current controlled demo license" in body
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

    brief_path = pilot_readiness.write_pilot_share_brief(root, profile="default", top_n=2, output=output)
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
    checks = build_pilot_readiness_checks(root, profile="default", top_n=2, source_queues=source_queues)

    brief = render_pilot_share_brief(
        checks=checks,
        snapshot=build_readiness_snapshot(root),
        source_queues=source_queues,
        excluded_artifacts=["data/prices.csv"],
    )

    assert "# Pilot Share Brief" in brief
    assert "research-only product evidence" in brief
    assert "## Pilot Share Answer" in brief
    assert "- Shareable now: portfolio/demo evidence with manual gates." in brief
    assert "- Not shareable as: open-source/reuse package or data-freshness proof until the license and generated-artifact gates are resolved." in brief
    assert "- Reuse rights: not granted until a root `LICENSE` exists." in brief
    assert "- GitHub pilot link: not current until reviewed local commits are pushed." in brief
    assert "- Keep local: broad generated CSV/JSON/report churn unless a specific artifact is reviewed evidence." in brief
    assert "- Next gate: run `make public-check` and keep source-proof blockers visible." in brief
    assert "What can be used now" in brief
    assert "Price-ready setup coverage: 1/1" in brief
    assert "Price coverage: 1/1" not in brief
    assert "DCF-ready operating-company coverage: 0/1" in brief
    assert "What is still blocked" in brief
    assert "DCF Input Proof Batches" in brief
    assert "fundamentals_bundle_plus_shares: 10" in brief
    assert "How to demo or review next" in brief
    assert "Final share gate sequence" in brief
    assert "GitHub sync" in brief
    assert "generated artifact hygiene" in brief
    assert "public-check" in brief
    assert "license boundary" in brief
    assert "source-proof blockers stay visible" in brief
    assert "make universe-scope TOP_N=10" in brief
    assert "make risk-context" in brief
    assert "make universe-preview-summary" in brief
    assert "capped universe source preview" in brief
    assert "Universe membership is metadata only" in brief
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
        checks=build_pilot_readiness_checks(root, profile="default", top_n=2, source_queues=source_queues),
        snapshot=build_readiness_snapshot(root),
        source_queues=source_queues,
        excluded_artifacts=[],
    )

    assert "Source-proof queues reviewed or exhausted" in brief
    assert "Next source-proof command: `make project-status-check`" in brief
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
                        "next_step": "make project-status-check",
                        "next_step_reason": "Current proof queues are exhausted.",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    brief = render_pilot_share_brief(
        checks=build_pilot_readiness_checks(root, profile="default", top_n=2),
        snapshot=build_readiness_snapshot(root),
        source_queues=[],
        excluded_artifacts=["data/prices.csv"],
        root=root,
    )

    assert "How coverage expands next" in brief
    assert "make provider-setup-checklist" in brief
    assert "Coverage unlock decision" in brief
    assert "Source buckets:" in brief
    assert "Free public sources: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance" in brief
    assert "Keyed free-tier fallbacks: configured FMP free tier; needs key Alpha Vantage free tier, Finnhub free tier" in brief
    assert "Optional broker boundary: IBKR read-only (disabled unless explicitly configured)" in brief
    assert "No broad coverage batch should run from setup alone" in brief
    assert "Provider setup only makes a source executable" in brief
    assert "readiness changes still require validate, preview, rejected-row review" in brief
    assert "Do not retry fundamentals_share_count_source_ladder" in brief
    assert "proof queues.." not in brief
    assert "Configure first: Finnhub free tier" in brief
    assert "Second fallback after FMP" in brief
    assert "Do not configure all missing providers at once" in brief
    assert "FMP free tier: configured -> price, fundamentals, share_count" in brief
    assert "reviewed smoke: `make fmp-smoke TICKER=<ticker>`" in brief
    assert "Alpha Vantage free tier: needs_key -> price, fundamentals, share_count" in brief
    assert "reviewed smoke: `make alpha-vantage-smoke TICKER=<ticker>`" in brief
    assert "Finnhub free tier: needs_key -> price, fundamentals, share_count" in brief
    assert "IBKR read-only: optional_disabled -> price" in brief
    assert "Real key values are never printed" in brief
    assert "secret-fmp-key" not in brief
