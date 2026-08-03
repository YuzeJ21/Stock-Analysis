from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from src import dashboard
from src import reviewed_batch_proof
from src.readiness_ops import PeerReadinessSummary, build_readiness_ops_lanes


CONCRETE_PROFILES = {"default", "demo", "local"}
PROFILE_TOKEN = re.compile(r"\bPROFILE=([^\s&`.,;]+)")
ROOT = Path(__file__).resolve().parents[1]
TASK_8_RUNTIME_FILES = (
    "src/dashboard.py",
    "src/data_health_batch_console.py",
    "src/data_health_coverage_delta.py",
    "src/data_health_coverage_proof_summary.py",
    "src/data_health_dcf_source_commands.py",
    "src/data_health_dcf_source_packet.py",
    "src/data_health_proof_checklist.py",
    "src/data_health_proof_console.py",
    "src/data_health_proof_ctas.py",
    "src/data_health_proof_planner.py",
    "src/data_health_queue_outcome.py",
    "src/data_health_recent_progress.py",
    "src/data_health_trusted_fundamentals_writer.py",
    "src/data_health_trusted_pilot_console.py",
    "src/dcf_input_proof_queue.py",
    "src/dcf_readiness.py",
    "src/decision_proof_queue.py",
    "src/peer_mapping_source_review.py",
    "src/price_history_proof_queue.py",
    "src/readiness_comparison.py",
    "src/readiness_queue_dashboard.py",
    "src/research_decisions.py",
    "src/reviewed_batch.py",
    "src/reviewed_batch_command_builder.py",
    "src/reviewed_batch_preflight.py",
    "src/reviewed_batch_proof.py",
    "src/reviewed_data_proof.py",
    "src/share_count_proof_queue.py",
    "src/stock_report.py",
    "src/auto_refresh_orchestrator.py",
    "src/coverage_expansion_loop.py",
    "src/data_health_peer_analysis.py",
    "src/data_health_overview_console.py",
    "src/public_home_workflow.py",
    "src/readiness_ops.py",
    "src/source_activation_guide.py",
    "src/trusted_data_pilot.py",
)


def _render_complete_string_node(node: ast.Constant | ast.JoinedStr) -> str:
    if isinstance(node, ast.Constant):
        return str(node.value) if isinstance(node.value, str) else ""
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(str(value.value))
        elif isinstance(value, ast.FormattedValue):
            parts.append("{" + ast.unparse(value.value) + "}")
    return "".join(parts)


def _complete_runtime_strings(relative_path: str) -> list[tuple[int, str]]:
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    strings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Constant, ast.JoinedStr)):
            continue
        if isinstance(parents.get(node), (ast.JoinedStr, ast.FormattedValue)):
            continue
        rendered = _render_complete_string_node(node)
        if rendered:
            strings.append((node.lineno, rendered))
    return strings


def assert_structural_proof_sequence(
    command: str,
    *,
    profile: str,
    lane: str,
    requires_reviewed_apply: bool,
) -> None:
    """Validate one rendered proof object, not neighboring source text."""

    steps = [step.strip() for step in command.split("&&")]
    profiles = PROFILE_TOKEN.findall(command)
    assert profiles
    assert set(profiles) == {profile}
    assert profile in CONCRETE_PROFILES
    assert not any("<" in token or ">" in token or "|" in token for token in profiles)

    snapshot_index = next(index for index, step in enumerate(steps) if step == f"make readiness-snapshot PROFILE={profile}")
    compare_index = next(
        index
        for index, step in enumerate(steps)
        if step.startswith(f"make reviewed-batch-compare PROFILE={profile} LANE={lane} ")
    )
    comparison = steps[compare_index]
    assert "BATCH_ID=" in comparison
    assert "REVIEW_DATE=" in comparison
    assert "readiness-preview" not in command

    if requires_reviewed_apply:
        validate_index = next(index for index, step in enumerate(steps) if "-validate" in step)
        preview_index = next(index for index, step in enumerate(steps) if "-preview" in step)
        apply_index = next(index for index, step in enumerate(steps) if "-apply" in step)
        assert snapshot_index < validate_index < preview_index < apply_index < compare_index
    else:
        assert snapshot_index < compare_index


def test_profile_bound_proof_sequence_renders_one_concrete_profile_in_order():
    command = reviewed_batch_proof.profile_bound_readiness_proof_sequence(
        profile="local",
        lane="fundamentals",
        batch_id="RB-LOCAL-001",
        review_date="2026-08-03",
        reviewed_steps=(
            "make imports-validate IMPORT_TICKERS=NVDA",
            "make imports-preview IMPORT_TICKERS=NVDA",
            "make imports-apply IMPORT_TICKERS=NVDA",
        ),
    )

    assert command == (
        "make readiness-snapshot PROFILE=local && "
        "make imports-validate IMPORT_TICKERS=NVDA && "
        "make imports-preview IMPORT_TICKERS=NVDA && "
        "make imports-apply IMPORT_TICKERS=NVDA && "
        "make reviewed-batch-compare PROFILE=local LANE=fundamentals "
        "BATCH_ID=RB-LOCAL-001 REVIEW_DATE=2026-08-03"
    )
    assert_structural_proof_sequence(
        command,
        profile="local",
        lane="fundamentals",
        requires_reviewed_apply=True,
    )


@pytest.mark.parametrize(
    "profile",
    [
        "",
        "DEFAULT",
        "unknown",
        "<default|demo|local>",
        "<profile>",
        "default|demo|local",
        "${PROFILE}",
        "PROFILE=default",
    ],
)
def test_profile_bound_proof_sequence_rejects_missing_unknown_and_placeholder_profiles(profile: str):
    with pytest.raises(ValueError, match="concrete readiness profile"):
        reviewed_batch_proof.profile_bound_readiness_proof_sequence(
            profile=profile,
            lane="prices",
            batch_id="RB-001",
            review_date="2026-08-03",
            reviewed_steps=("make price-validate", "make price-preview", "make price-apply"),
        )


def test_profile_bound_proof_sequence_rejects_missing_comparison_scope():
    for field, values in (
        ("lane", {"lane": ""}),
        ("batch_id", {"batch_id": "<reviewed_batch_id>"}),
        ("review_date", {"review_date": "<yyyy-mm-dd>"}),
    ):
        arguments = {
            "profile": "default",
            "lane": "prices",
            "batch_id": "RB-001",
            "review_date": "2026-08-03",
            "reviewed_steps": ("make price-validate", "make price-preview", "make price-apply"),
            **values,
        }
        with pytest.raises(ValueError, match=field):
            reviewed_batch_proof.profile_bound_readiness_proof_sequence(**arguments)


def test_active_proof_profile_resolver_follows_selected_environment(monkeypatch, tmp_path):
    resolver = getattr(reviewed_batch_proof, "resolve_readiness_proof_profile", None)
    assert resolver is not None

    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    assert resolver(project_root=tmp_path) == "local"
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "<default|demo|local>")
    with pytest.raises(ValueError, match="concrete readiness profile"):
        resolver(project_root=tmp_path)


@pytest.mark.parametrize("profile", ["", " ", "DEFAULT", "unknown", "<profile>"])
def test_proof_profile_resolver_rejects_non_concrete_explicit_values(profile, tmp_path):
    with pytest.raises(ValueError, match="concrete readiness profile"):
        reviewed_batch_proof.resolve_readiness_proof_profile(profile, project_root=tmp_path)


def test_readiness_ops_renders_structural_proof_objects_for_selected_local_profile(tmp_path):
    peer_summary = PeerReadinessSummary(
        total_count=0,
        peer_mapping_ready=0,
        peer_price_ready=0,
        peer_momentum_ready=0,
        peer_fundamentals_ready=0,
        peer_valuation_ready=0,
        peer_valuation_comparison_ready=0,
        missing_mapping=0,
        missing_peer_price=0,
        missing_peer_momentum=0,
        missing_peer_fundamentals=0,
        peer_valuation_blocked=0,
        source_context="test fixture",
    )

    lanes = build_readiness_ops_lanes(
        tmp_path,
        profile="local",
        dcf_input_rows=[],
        share_count_rows=[],
        peer_summary=peer_summary,
    )

    expected = {
        "price_coverage": ("prices", True),
        "fundamentals_dcf": ("fundamentals", True),
        "share_count_proof": ("share_count", True),
        "peer_mapping": ("peers", True),
        "peer_valuation_inputs": ("peers", True),
        "earnings_locked": ("optional_context", True),
        "analyst_estimates_locked": ("optional_context", True),
        "excluded_not_applicable": ("excluded", False),
    }
    for row in lanes:
        lane, requires_apply = expected[row.lane]
        assert_structural_proof_sequence(
            row.proof_command,
            profile="local",
            lane=lane,
            requires_reviewed_apply=requires_apply,
        )


def test_structural_validator_catches_profile_mutation_and_order_mutation():
    valid = reviewed_batch_proof.profile_bound_readiness_proof_sequence(
        profile="demo",
        lane="prices",
        batch_id="RB-DEMO-001",
        review_date="2026-08-03",
        reviewed_steps=("make price-validate", "make price-preview", "make price-apply"),
    )

    with pytest.raises(AssertionError):
        assert_structural_proof_sequence(
            valid.replace("PROFILE=demo LANE=prices", "PROFILE=local LANE=prices"),
            profile="demo",
            lane="prices",
            requires_reviewed_apply=True,
        )
    with pytest.raises(AssertionError):
        assert_structural_proof_sequence(
            valid.replace("make price-preview && make price-apply", "make price-apply && make price-preview"),
            profile="demo",
            lane="prices",
            requires_reviewed_apply=True,
        )


def test_dashboard_readiness_ops_cache_keys_concrete_selected_profile(tmp_path):
    dashboard.cached_readiness_ops_lanes.cache_clear()

    default_rows = dashboard.cached_readiness_ops_lanes(str(tmp_path), "default")
    local_rows = dashboard.cached_readiness_ops_lanes(str(tmp_path), "local")

    assert "PROFILE=default" in default_rows[0].proof_command
    assert "PROFILE=local" in local_rows[0].proof_command
    assert default_rows[0].proof_command != local_rows[0].proof_command


def test_dashboard_readiness_ops_frame_uses_actual_selected_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "demo")
    dashboard.cached_readiness_ops_lanes.cache_clear()

    frame = dashboard.data_health_readiness_ops_center_frame(tmp_path)

    assert not frame.empty
    assert frame["Proof Command"].str.contains("PROFILE=demo", regex=False).all()
    assert not frame["Proof Command"].str.contains("PROFILE=default", regex=False).any()


def test_dashboard_recent_progress_calls_bind_actual_selected_profile_structurally():
    tree = ast.parse((ROOT / "src/dashboard.py").read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "readiness_recent_progress_cards"
    ]

    assert len(calls) == 2
    for call in calls:
        profile_keyword = next((keyword for keyword in call.keywords if keyword.arg == "profile"), None)
        assert profile_keyword is not None
        assert ast.unparse(profile_keyword.value) == "_active_data_profile_name()"


def test_task_8_complete_runtime_literals_never_offer_writer_or_placeholder_profile():
    offenders: list[str] = []
    deprecated_writer = re.compile(r"make readiness(?![-_])")
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, rendered in _complete_runtime_strings(relative_path):
            if deprecated_writer.search(rendered):
                offenders.append(f"{relative_path}:{line_number}: deprecated writer: {rendered}")
            for profile in PROFILE_TOKEN.findall(rendered):
                if "<" in profile or ">" in profile or "|" in profile:
                    offenders.append(f"{relative_path}:{line_number}: placeholder profile: {rendered}")

    assert offenders == []


def test_task_8_complete_proof_literals_keep_command_fields_in_one_object():
    offenders: list[str] = []
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, rendered in _complete_runtime_strings(relative_path):
            if "make readiness-snapshot" not in rendered and "make reviewed-batch-compare" not in rendered:
                continue
            profiles = PROFILE_TOKEN.findall(rendered)
            if not profiles or len(set(profiles)) != 1:
                offenders.append(f"{relative_path}:{line_number}: profile mismatch: {rendered}")
                continue
            if "make reviewed-batch-compare" in rendered:
                comparison = rendered[rendered.index("make reviewed-batch-compare") :]
                missing = [field for field in ("PROFILE=", "LANE=", "BATCH_ID=", "REVIEW_DATE=") if field not in comparison]
                if missing:
                    offenders.append(f"{relative_path}:{line_number}: missing {','.join(missing)}: {rendered}")
            if "make readiness-snapshot" in rendered and "make reviewed-batch-compare" in rendered:
                if rendered.index("make readiness-snapshot") > rendered.index("make reviewed-batch-compare"):
                    offenders.append(f"{relative_path}:{line_number}: compare precedes snapshot: {rendered}")
                if re.search(r"make [\w-]+-apply\b", rendered):
                    ordered = (
                        rendered.index("make readiness-snapshot"),
                        re.search(r"make [\w-]+-validate\b", rendered).start(),
                        re.search(r"make [\w-]+-preview\b", rendered).start(),
                        re.search(r"make [\w-]+-apply\b", rendered).start(),
                        rendered.index("make reviewed-batch-compare"),
                    )
                    if tuple(sorted(ordered)) != ordered:
                        offenders.append(f"{relative_path}:{line_number}: reviewed order is invalid: {rendered}")

    assert offenders == []


def test_task_8_complete_runtime_literals_never_present_preview_as_proof():
    offenders: list[str] = []
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, rendered in _complete_runtime_strings(relative_path):
            lowered = rendered.lower()
            if "readiness-preview" in lowered and any(token in lowered for token in ("proof", "post-run", "post-apply", "comparison")):
                offenders.append(f"{relative_path}:{line_number}: {rendered}")

    assert offenders == []
