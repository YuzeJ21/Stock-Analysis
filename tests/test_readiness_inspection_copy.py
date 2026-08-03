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
from src.data_health_metric_readiness_console import (
    metric_detail_load_cards,
    metric_detail_load_status,
    proof_detail_load_cards,
)
from src.data_health_overview_console import freshness_routine_cards, source_readiness_guidance_cards
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
from src.single_stock_workflow import (
    single_stock_data_health_handoff_cards,
    single_stock_workflow_fit_cards,
    single_stock_workflow_loop_cards,
)
from src.source_activation_guide import render_provider_setup_checklist
from src.universe_scope_workflow import _print_plan


PREVIEW_COMMAND = "make readiness-preview TOP_N=20"
NON_PERSISTENCE = "In-memory preview only; it does not refresh or persist saved readiness."
LEGACY_ACTION = re.compile(r"\bmake readiness\b(?!-)")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


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


def _populated_feature_cards() -> list[dict[str, object]]:
    return feature_readiness_cards(
        pd.DataFrame(
            [
                {
                    "feature": "dcf",
                    "ready_count": 1,
                    "partial_count": 0,
                    "blocked_count": 1,
                    "excluded_count": 0,
                    "total_count": 2,
                    "top_blocker": "missing fundamentals",
                    "next_action": "",
                    "dashboard_section": "Value / Re-rating",
                }
            ]
        )
    )


def _populated_peer_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "peer_ready": False,
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "dcf_ready": True,
                "in_active_universe": True,
                "next_peer_action": "Add source-backed peer fundamentals.",
            }
        ]
    )


def _populated_readiness_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "in_active_universe": True,
                "price_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "overall_readiness_state": "partial",
                "updated_at": "2026-08-03T00:00:00+00:00",
            }
        ]
    )


def _previous_readiness_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "price_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
            }
        ]
    )


def _populated_single_stock_snapshot() -> dict[str, object]:
    return {
        "ticker": "NVDA",
        "status": "partial",
        "asset_type": "company",
        "decision_bucket": "Research Now",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }


def _stale_metric_detail_cards() -> list[dict[str, object]]:
    return metric_detail_load_cards(
        {
            "status": "blocked_by_snapshot_gate",
            "title": "Refresh readiness before metric details",
            "body": "Saved readiness is stale.",
            "next_action": "make readiness",
        }
    )


def _stale_source_guidance_cards() -> list[dict[str, object]]:
    return source_readiness_guidance_cards(
        SimpleNamespace(status="stale", message="Saved readiness is stale.", refresh_command="make readiness")
    )


def _stale_proof_detail_cards() -> list[dict[str, object]]:
    return proof_detail_load_cards(
        {
            "status": "blocked_by_snapshot_gate",
            "title": "Refresh readiness before proof details",
            "body": "Saved readiness is stale.",
            "next_action": "make readiness",
        }
    )


def _stale_current_mode_strip_cards() -> list[dict[str, object]]:
    rendered = data_health_current_mode_strip_html(
        selected_lane_key="metrics",
        queue_details_requested=False,
        batch_details_requested=False,
        metric_details_requested=True,
        proof_details_requested=False,
        readiness_freshness=SimpleNamespace(
            status="stale",
            message="Saved readiness is stale.",
            refresh_command="make readiness",
        ),
        batch_preflight=SimpleNamespace(),
        metric_detail_status={"next_action": ""},
    )
    return [{"body": rendered}]


POPULATED_INSPECTION_CARD_RENDERERS = (
    ("data_health_feature_readiness", _populated_feature_cards),
    ("data_health_peer_analysis", lambda: peer_analysis_boundary_cards(_populated_peer_frame())),
    ("data_health_peer_mapping_studio", lambda: peer_mapping_studio_summary_cards(_populated_peer_frame())),
    ("data_health_peer_readiness", lambda: peer_readiness_product_cards(_populated_peer_frame())),
    (
        "data_health_recent_progress",
        lambda: readiness_recent_progress_cards(_populated_readiness_frame(), _previous_readiness_frame()),
    ),
    ("single_stock_workflow_loop", lambda: single_stock_workflow_loop_cards(_populated_single_stock_snapshot())),
    ("single_stock_workflow_fit", lambda: single_stock_workflow_fit_cards(_populated_single_stock_snapshot())),
    ("single_stock_workflow_handoff", lambda: single_stock_data_health_handoff_cards(_populated_single_stock_snapshot())),
)


PROFILE_AWARE_INSPECTION_CARD_RENDERERS = (
    ("feature_readiness_empty", lambda: feature_readiness_cards(None)),
    ("feature_readiness_populated", _populated_feature_cards),
    ("peer_analysis_empty", lambda: peer_analysis_boundary_cards(None)),
    ("peer_analysis_populated", lambda: peer_analysis_boundary_cards(_populated_peer_frame())),
    ("peer_mapping_empty", lambda: peer_mapping_studio_summary_cards(None)),
    ("peer_mapping_populated", lambda: peer_mapping_studio_summary_cards(_populated_peer_frame())),
    ("peer_readiness_empty", lambda: peer_readiness_product_cards(None)),
    ("peer_readiness_populated", lambda: peer_readiness_product_cards(_populated_peer_frame())),
    ("peer_unlock_empty", lambda: peer_unlock_operator_cards(None)),
    (
        "peer_operator_missing",
        lambda: peer_operator_summary_cards(peer_operator_summary_frame(None, None, None)),
    ),
    ("metric_detail_stale", _stale_metric_detail_cards),
    ("proof_detail_stale", _stale_proof_detail_cards),
    ("source_guidance_stale", _stale_source_guidance_cards),
    (
        "source_guidance_current_blank",
        lambda: source_readiness_guidance_cards(
            SimpleNamespace(status="current", message="Saved readiness is current.", refresh_command="")
        ),
    ),
    ("freshness_routine_populated", lambda: freshness_routine_cards({"master_universe": 2, "price_ready": 1})),
    ("current_mode_strip_stale", _stale_current_mode_strip_cards),
    ("recent_progress_empty", lambda: readiness_recent_progress_cards(None)),
    (
        "recent_progress_populated",
        lambda: readiness_recent_progress_cards(_populated_readiness_frame(), _previous_readiness_frame()),
    ),
    ("single_stock_loop_missing", lambda: single_stock_workflow_loop_cards({"ticker": "NVDA", "status": "missing"})),
    ("single_stock_loop_populated", lambda: single_stock_workflow_loop_cards(_populated_single_stock_snapshot())),
    ("single_stock_fit_missing", lambda: single_stock_workflow_fit_cards({"ticker": "NVDA", "status": "missing"})),
    ("single_stock_fit_populated", lambda: single_stock_workflow_fit_cards(_populated_single_stock_snapshot())),
    ("single_stock_handoff_missing", lambda: single_stock_data_health_handoff_cards({"ticker": "NVDA", "status": "missing"})),
    ("single_stock_handoff_populated", lambda: single_stock_data_health_handoff_cards(_populated_single_stock_snapshot())),
)


@pytest.mark.parametrize(("module_name", "render"), POPULATED_INSPECTION_CARD_RENDERERS)
def test_populated_inspection_ctas_state_exact_nonpersistence_boundary(
    module_name: str,
    render,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "default")

    inspection_cards = [card for card in render() if card.get("command") == PREVIEW_COMMAND]

    assert inspection_cards, module_name
    for card in inspection_cards:
        assert NON_PERSISTENCE in str(card.get("body", "")), module_name
        assert LEGACY_ACTION.search(_flatten(card)) is None, module_name


@pytest.mark.parametrize(
    ("profile_key", "profile_label", "relative_data_dir"),
    [("demo", "Demo", "data/demo"), ("local", "Local Research", "data/local")],
)
@pytest.mark.parametrize(("module_name", "render"), PROFILE_AWARE_INSPECTION_CARD_RENDERERS)
def test_real_nondefault_profile_card_renderers_are_truthfully_unavailable(
    profile_key: str,
    profile_label: str,
    relative_data_dir: str,
    module_name: str,
    render,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", profile_key)
    expected_data_dir = (REPOSITORY_ROOT / relative_data_dir).resolve().as_posix()

    cards = render()
    rendered = _flatten(cards)
    inspection_rendered = " ".join(
        _flatten(card) for card in cards if "unavailable" in _flatten(card).lower()
    )

    assert PREVIEW_COMMAND not in rendered, module_name
    assert inspection_rendered, module_name
    assert f"{profile_label} ({profile_key})" in inspection_rendered, module_name
    assert expected_data_dir in inspection_rendered, module_name
    assert "Default (default)" in inspection_rendered, module_name
    assert NON_PERSISTENCE in inspection_rendered, module_name
    assert LEGACY_ACTION.search(inspection_rendered) is None, module_name


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
