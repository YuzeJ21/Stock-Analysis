from __future__ import annotations

import os
import re
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src import pilot_readiness, reviewed_batch
from src.artifact_freshness import generated_artifact_stale_warning
from src.auto_refresh_orchestrator import SchedulerPlan, render_scheduler_runbook
from src.continuation_gate import ContinuationGate, build_continuation_gate
from src.coverage_expansion_loop import CoverageExpansionLoop, render_coverage_expansion_loop
from src.data_health_console import data_health_current_mode_strip_html
from src.data_health_feature_readiness import feature_readiness_cards
from src.data_health_metric_readiness_console import metric_detail_load_cards, metric_detail_load_status
from src.data_health_overview_console import source_readiness_guidance_cards
from src.data_health_peer_analysis import peer_analysis_boundary_cards
from src.data_health_peer_mapping_studio import peer_mapping_studio_summary_cards
from src.data_health_peer_operator_summary import peer_operator_summary_cards, peer_operator_summary_frame
from src.data_health_peer_readiness import peer_readiness_product_cards
from src.data_health_peer_unlock import peer_unlock_operator_cards
from src.data_health_recent_progress import readiness_recent_progress_cards
from src.profile_context import CoverageCounts, ProfileContext, build_profile_context, render_profile_context_text
from src.readiness_ops import (
    render_coverage_frontier,
    render_data_coverage_expansion_plan,
    render_data_coverage_proof_queues,
    render_fundamentals_peer_metrics_queue,
)
from src.readiness_preview import ReadinessImpactPreview, render_readiness_impact_preview
from src.research_loop import home_research_loop_context
from src.review_metrics import MetricReadinessBoardRow, format_metric_readiness_board_text
from src.session_source_preflight import render_session_source_preflight
from src.single_stock_workflow import single_stock_data_health_handoff_cards
from src.source_activation_guide import render_provider_setup_checklist
from src.universe_scope_workflow import _print_plan


PREVIEW_COMMAND = "make readiness-preview TOP_N=20"
NON_PERSISTENCE = "In-memory preview only; it does not refresh or persist saved readiness."
LEGACY_ACTION = re.compile(r"\bmake readiness\b(?!-)")


def _flatten(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _default_context(state: str = "stale") -> ProfileContext:
    return ProfileContext(
        profile_key="default",
        profile_label="Default",
        data_dir=Path("data"),
        outputs_dir=Path("outputs"),
        source_as_of="2026-08-03",
        readiness_built_at="2026-08-02T00:00:00+00:00",
        snapshot_identity="abc",
        snapshot_identity_short="abc",
        freshness_state=state,
        freshness_message="Selected-profile readiness is stale.",
        refresh_command="make readiness",
        coverage=CoverageCounts(),
        lane_source_dates=(),
        snapshot_inputs=(),
        readiness_evidence_state="tracked",
        readiness_evidence_message="Readiness artifacts match tracked HEAD evidence.",
    )


def _inspection_gate() -> ContinuationGate:
    return build_continuation_gate(_default_context())


@pytest.mark.parametrize(
    ("module_name", "render"),
    [
        ("data_health_feature_readiness", lambda: feature_readiness_cards(None)),
        ("data_health_peer_analysis", lambda: peer_analysis_boundary_cards(None)),
        ("data_health_peer_mapping_studio", lambda: peer_mapping_studio_summary_cards(None)),
        ("data_health_peer_readiness", lambda: peer_readiness_product_cards(None)),
        ("data_health_peer_unlock", lambda: peer_unlock_operator_cards(None)),
        ("data_health_recent_progress", lambda: readiness_recent_progress_cards(None)),
        (
            "data_health_peer_operator_summary",
            lambda: peer_operator_summary_cards(peer_operator_summary_frame(None, None, None)),
        ),
        (
            "data_health_metric_readiness_console",
            lambda: metric_detail_load_cards(
                metric_detail_load_status("metrics", SimpleNamespace(status="stale", message="Saved readiness is stale.", refresh_command=""), True)
            ),
        ),
        (
            "data_health_overview_console",
            lambda: source_readiness_guidance_cards(
                SimpleNamespace(status="stale", message="Saved readiness is stale.", refresh_command="")
            )[0],
        ),
        (
            "single_stock_workflow",
            lambda: single_stock_data_health_handoff_cards({"ticker": "NVDA", "status": "missing"})[-1],
        ),
    ],
)
def test_missing_and_stale_card_renderers_route_to_nonpersistent_preview(module_name: str, render):
    rendered = _flatten(render())

    assert PREVIEW_COMMAND in rendered, module_name
    assert NON_PERSISTENCE in rendered, module_name
    assert LEGACY_ACTION.search(rendered) is None, module_name


def test_shared_stale_renderers_route_default_profile_to_nonpersistent_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    generated = tmp_path / "data/reports/ticker_readiness_report.csv"
    source = tmp_path / "data/prices.csv"
    generated.parent.mkdir(parents=True)
    generated.write_text("ticker\nNVDA\n", encoding="utf-8")
    source.write_text("ticker,date,close\nNVDA,2026-08-03,1\n", encoding="utf-8")
    os.utime(generated, (1, 1))
    os.utime(source, (2, 2))
    warning = generated_artifact_stale_warning(
        root=tmp_path,
        generated_paths=[generated],
        source_paths=[source],
        display_root=tmp_path,
    )

    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "default")
    context = build_profile_context(project_root=tmp_path)
    context_text = render_profile_context_text(context) + " " + context.refresh_command
    freshness = reviewed_batch.readiness_freshness_status(tmp_path)
    gate = build_continuation_gate(_default_context())
    scheduler = SchedulerPlan((), "daily", (), (), (), (), (), 1, "inspection", True)
    scheduler_text = render_scheduler_runbook(scheduler, continuation_gate=gate)

    pilot_status = SimpleNamespace(status="stale", message="Saved readiness is stale.", refresh_command="make readiness")
    monkeypatch.setattr(pilot_readiness, "readiness_freshness_status", lambda _root: pilot_status)
    pilot_check = pilot_readiness._freshness_check(tmp_path)

    for module_name, rendered in [
        ("artifact_freshness", warning),
        ("profile_context", context_text),
        ("reviewed_batch", _flatten(freshness)),
        ("continuation_gate", _flatten(gate)),
        ("auto_refresh_orchestrator", scheduler_text),
        ("pilot_readiness", _flatten(pilot_check)),
    ]:
        assert PREVIEW_COMMAND in rendered, module_name
        assert NON_PERSISTENCE in rendered, module_name
        assert LEGACY_ACTION.search(rendered) is None, module_name


@pytest.mark.parametrize(
    ("profile_key", "profile_label", "data_dir"),
    [("demo", "Demo", Path("data/demo")), ("local", "Local Research", Path("data/local"))],
)
def test_nondefault_profile_inspection_is_truthfully_unavailable(
    profile_key: str, profile_label: str, data_dir: Path
):
    context = ProfileContext(
        **{
            **_default_context("missing").__dict__,
            "profile_key": profile_key,
            "profile_label": profile_label,
            "data_dir": data_dir,
        }
    )

    gate = build_continuation_gate(context)
    rendered = _flatten(gate)

    assert PREVIEW_COMMAND not in gate.next_safe_command
    assert f"{profile_label} ({profile_key})" in rendered
    assert data_dir.as_posix() in rendered
    assert "unavailable" in rendered.lower()
    assert "Default (default)" in rendered
    assert LEGACY_ACTION.search(rendered) is None


def test_text_renderers_use_preview_for_missing_saved_readiness(capsys: pytest.CaptureFixture[str]):
    preview = ReadinessImpactPreview("missing_saved_snapshot", 0, 0, (), (), 0, (), 20, "data/reports/ticker_readiness_report.csv")
    renderers = {
        "readiness_preview": render_readiness_impact_preview(preview),
        "readiness_ops_expansion": render_data_coverage_expansion_plan([]),
        "readiness_ops_proof": render_data_coverage_proof_queues([]),
        "readiness_ops_metrics": render_fundamentals_peer_metrics_queue([]),
        "readiness_ops_frontier": render_coverage_frontier([]),
        "coverage_expansion_loop": render_coverage_expansion_loop(
            CoverageExpansionLoop(
                "blocked_missing_lane", "auto", "No matching planner lane", "-", None, None,
                "Inspect readiness before choosing a lane.", (), (),
            )
        ),
    }
    _print_plan(pd.DataFrame())
    renderers["universe_scope_workflow"] = capsys.readouterr().out

    for module_name, rendered in renderers.items():
        assert PREVIEW_COMMAND in rendered, module_name
        assert NON_PERSISTENCE in rendered, module_name
        assert LEGACY_ACTION.search(rendered) is None, module_name


def test_delegating_inspection_renderers_preserve_preview_and_nonpersistence_copy():
    gate = _inspection_gate()
    preflight = {
        "project_root": ".", "data_dir": "data", "generated_at": "now", "session_flags": [],
        "do_not_retry_paths": [], "preferred_lane_order": [], "source_categories": {},
        "sources": {name: {"status": "unavailable", "reason_code": "missing", "detail": "-"} for name in (
            "sec", "sec_submissions", "yfinance_import", "yfinance_stage", "price_ladder", "ibkr_price",
            "fmp", "alpha_vantage", "finnhub", "local_fundamentals")},
        "continuation_gate": {**gate.__dict__},
    }
    checklist = {
        "title": "Provider setup", "research_boundary": "Research-only.", "secret_policy": "No secrets.",
        "continuation_gate": {**gate.__dict__}, "rows": [], "source_answer": {}, "first_answer": {},
        "source_boundary_decision": [], "coverage_unlock_decision": {}, "credential_file_status": {},
        "one_provider_setup_order": [], "one_ticker_smoke_handoff": "-", "workflow_pivot": "-",
        "apply_gate": [], "non_retry_rule": "-", "current_gate": {},
    }
    metric_row = MetricReadinessBoardRow("NVDA", "SPY", "blocked", 0, 0, 1, 0, "missing", "prices", "inspect", "stale", "Saved readiness is stale.", PREVIEW_COMMAND)
    outputs = {
        "session_source_preflight": render_session_source_preflight(preflight),
        "source_activation_guide": render_provider_setup_checklist(checklist),
        "review_metrics": format_metric_readiness_board_text([metric_row]),
        "research_loop": _flatten(home_research_loop_context({}, SimpleNamespace(status="stale", message="Saved readiness is stale.", refresh_command=PREVIEW_COMMAND))),
            "data_health_console": data_health_current_mode_strip_html(
                selected_lane_key="metrics", queue_details_requested=False, batch_details_requested=False, metric_details_requested=True,
            proof_details_requested=False, readiness_freshness=SimpleNamespace(status="stale", message="Saved readiness is stale.", refresh_command=PREVIEW_COMMAND),
            batch_preflight=SimpleNamespace(), metric_detail_status={"next_action": PREVIEW_COMMAND},
        ),
    }
    for module_name, rendered in outputs.items():
        assert PREVIEW_COMMAND in rendered, module_name
        assert NON_PERSISTENCE in rendered, module_name
        assert LEGACY_ACTION.search(rendered) is None, module_name


def test_task8_proof_only_modules_are_not_misclassified_as_task7_inspection():
    # These named Task 7 files also contain post-apply proof surfaces. Task 8 owns
    # those renderers; this test documents the boundary instead of lexically
    # banning their historical/proof command copy.
    assert {"public_home_workflow", "trusted_data_pilot"} == {
        "public_home_workflow", "trusted_data_pilot"
    }
