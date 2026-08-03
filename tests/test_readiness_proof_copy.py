from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from src import reviewed_batch_proof


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


def test_profile_bound_proof_sequence_requires_one_explicit_profile():
    builder = getattr(reviewed_batch_proof, "profile_bound_readiness_proof_sequence", None)

    assert builder is not None, "Task 8 must expose the shared profile-bound proof sequence"
    assert inspect.signature(builder).parameters["profile"].default is inspect.Parameter.empty
    assert builder(
        profile="local",
        lane="fundamentals",
        batch_id="RB-LOCAL-001",
        review_date="2026-08-03",
        reviewed_steps=(
            "make imports-validate IMPORT_TICKERS=NVDA",
            "make imports-preview IMPORT_TICKERS=NVDA",
            "make imports-apply IMPORT_TICKERS=NVDA",
        ),
    ) == (
        "make readiness-snapshot PROFILE=local && "
        "make imports-validate IMPORT_TICKERS=NVDA && "
        "make imports-preview IMPORT_TICKERS=NVDA && "
        "make imports-apply IMPORT_TICKERS=NVDA && "
        "make reviewed-batch-compare PROFILE=local LANE=fundamentals "
        "BATCH_ID=RB-LOCAL-001 REVIEW_DATE=2026-08-03"
    )


@pytest.mark.parametrize("profile", ["", "DEFAULT", "unknown"])
def test_profile_bound_proof_sequence_rejects_missing_or_unknown_profiles(profile: str):
    builder = getattr(reviewed_batch_proof, "profile_bound_readiness_proof_sequence", None)

    assert builder is not None, "Task 8 must expose the shared profile-bound proof sequence"
    with pytest.raises(ValueError, match="explicit readiness profile"):
        builder(
            profile=profile,
            lane="prices",
            batch_id="RB-001",
            review_date="2026-08-03",
            reviewed_steps=("make price-validate", "make price-preview", "make price-apply"),
        )


def test_task_8_runtime_inventory_never_offers_the_deprecated_writer():
    offenders: list[str] = []
    pattern = re.compile(r"make readiness(?![-_])")
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, line in enumerate((ROOT / relative_path).read_text().splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{relative_path}:{line_number}: {line.strip()}")

    assert offenders == []


def test_task_8_runtime_inventory_binds_every_snapshot_and_comparison_to_one_complete_profile_scope():
    offenders: list[str] = []
    command_pattern = re.compile(r"make (readiness-snapshot|reviewed-batch-compare)([^\n\"'`]*)")
    for relative_path in TASK_8_RUNTIME_FILES:
        lines = (ROOT / relative_path).read_text().splitlines()
        for line_index, line in enumerate(lines):
            for match in command_pattern.finditer(line):
                command_window = " ".join(lines[line_index : line_index + 3])
                required_fields = ["PROFILE="]
                if match.group(1) == "reviewed-batch-compare":
                    required_fields.extend(["LANE=", "BATCH_ID=", "REVIEW_DATE="])
                missing_fields = [field for field in required_fields if field not in command_window]
                if missing_fields:
                    offenders.append(
                        f"{relative_path}:{line_index + 1}: missing {','.join(missing_fields)}: {line.strip()}"
                    )

    assert offenders == []


def test_task_8_proof_inventory_does_not_substitute_readiness_preview_for_comparison():
    offenders: list[str] = []
    proof_line = re.compile(r"proof|post.apply|post.run|comparison", re.IGNORECASE)
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, line in enumerate((ROOT / relative_path).read_text().splitlines(), start=1):
            if proof_line.search(line) and "readiness-preview" in line:
                offenders.append(f"{relative_path}:{line_number}: {line.strip()}")

    assert offenders == []
