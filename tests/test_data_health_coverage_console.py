from types import SimpleNamespace

import pandas as pd

from src import data_health_coverage_console as coverage_console
from src.readiness_ops import ReadinessLane


def _lane(**overrides):
    values = {
        "lane": "fundamentals_dcf",
        "label": "Fundamentals / DCF Proof",
        "readiness_state": "blocked",
        "workflow_mode": "preview_first_reviewed_apply",
        "total_count": 100,
        "ready_count": 5,
        "partial_count": 10,
        "blocked_count": 85,
        "excluded_count": 0,
        "unlock_impact": 85,
        "source_lane": "trusted_fundamentals",
        "source_readiness": "trusted local rows only",
        "next_safe_command": "make sec-stage-queue TOP_N=25",
        "proof_command": "make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch> && make readiness",
        "generated_churn_policy": "Keep generated CSV churn out unless reviewed as evidence.",
        "stale_proof_warning": "current",
        "notes": "Fundamentals stay blocked until source proof exists.",
    }
    values.update(overrides)
    return ReadinessLane(**values)


def _preflight(**overrides):
    values = {
        "packet_command": "DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10",
        "snapshot_command": "make readiness-snapshot",
        "proof_record_command": "make reviewed-batch-proof-record",
        "status": "ready_for_dry_run",
        "prior_snapshot_exists": True,
        "do_not_proceed_if": ("dry-run scope is not reviewed",),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _loop(**overrides):
    values = {
        "status": "ready_for_reviewed_dry_run",
        "selected_lane": "price_coverage",
        "selected_label": "Price Coverage",
        "reviewed_batch_lane": "prices",
        "planner_step": None,
        "preflight": _preflight(),
        "next_safe_action": "Run the reviewed packet, inspect dry-run scope, then compare before proof.",
        "copy_only_sequence": ("make coverage-expansion-loop LANE=prices TOP_N=10",),
        "do_not_proceed_if": ("dry-run scope is not reviewed",),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_coverage_frontier_frame_and_cards_rank_data_operations_not_securities():
    lanes = [
        _lane(
            lane="price_coverage",
            label="Price Coverage",
            workflow_mode="dry_run_first",
            unlock_impact=40,
            next_safe_command="make price-refresh-loop DRY_RUN=1 TOP_N=100",
        ),
        _lane(
            lane="excluded_not_applicable",
            label="Excluded / Not Applicable",
            workflow_mode="excluded",
            unlock_impact=999,
        ),
    ]

    frame = coverage_console.coverage_frontier_frame_from_lanes(lanes, top_n=5)
    cards = coverage_console.coverage_frontier_cards(frame)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert frame["Lane"].tolist() == ["Price Coverage"]
    assert cards[0]["kicker"] == "FRONTIER #1"
    assert cards[0]["command"] == "make price-refresh-loop DRY_RUN=1 TOP_N=100"
    assert "operations queue" in rendered
    assert "not a security recommendation" in rendered
    assert "batch lane" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_coverage_frontier_cards_handle_empty_frame_with_copy_only_command():
    cards = coverage_console.coverage_frontier_cards(pd.DataFrame())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    body = str(cards[0]["body"]).lower()

    assert cards[0]["title"] == "No batch frontier rows yet"
    assert cards[0]["command"] == "make coverage-frontier TOP_N=10"
    assert "ranks data operations, not securities" in rendered
    assert "open operator details" in body
    assert "make " not in body


def test_coverage_expansion_loop_ready_state_keeps_proof_boundary_visible():
    loop = _loop()

    cards = coverage_console.coverage_expansion_loop_cards(loop)
    frame = coverage_console.coverage_expansion_loop_frame(loop)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    frame_rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert cards[0]["title"] == "Coverage loop ready"
    assert cards[0]["command"] == "DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10"
    assert "planner -> preflight -> packet -> proof path" in rendered
    assert frame["Step"].tolist() == ["Status", "Planner gate", "Preflight gate", "Proof boundary"]
    assert "source proof, validation, preview/apply decision" in frame_rendered
    assert "generated csv/json churn is not classified" in frame_rendered
    assert "buy" not in rendered + frame_rendered
    assert "sell" not in rendered + frame_rendered


def test_coverage_expansion_loop_blocked_lane_does_not_create_fake_plan():
    loop = _loop(
        status="blocked_missing_lane",
        selected_lane="not_a_lane",
        selected_label="No matching planner lane",
        reviewed_batch_lane="-",
        preflight=None,
        next_safe_action="Run make readiness and make data-coverage-planner TOP_N=10.",
        copy_only_sequence=("make readiness", "make data-coverage-planner TOP_N=10"),
        do_not_proceed_if=("no planner lane exists for the requested scope",),
    )

    cards = coverage_console.coverage_expansion_loop_cards(loop)
    frame = coverage_console.coverage_expansion_loop_frame(loop)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Pick a planner lane first"
    assert cards[0]["command"] == "make data-coverage-planner TOP_N=10"
    assert "did not return a matching lane" in rendered
    assert frame.iloc[1]["Command"] == "make data-coverage-planner TOP_N=10"
