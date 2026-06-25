from types import SimpleNamespace

from src import data_health_batch_console as batch_console


def _preflight(**overrides):
    values = {
        "lane": "prices",
        "lane_scope": "Price Coverage",
        "batch_id": "RB-TEST",
        "review_date": "2026-06-17",
        "status": "ready_for_dry_run",
        "current_report_exists": True,
        "prior_snapshot_exists": True,
        "freshness_status": "current",
        "freshness_message": "Readiness artifacts are current.",
        "packet_command": "DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10",
        "snapshot_command": "make readiness-snapshot",
        "dry_run_command": "make price-refresh-loop DRY_RUN=1 TOP_N=10",
        "capped_execution_command": "make price-refresh-loop TOP_N=10",
        "comparison_command": "make reviewed-batch-compare LANE=prices",
        "proof_record_command": "make reviewed-batch-proof-record",
        "do_not_proceed_if": ("dry-run scope is not reviewed",),
        "expected_artifacts": ("data/prices.csv",),
        "post_run_hygiene": ("make diff-hygiene", "make diff-hygiene-files"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _freshness(status: str = "current"):
    return SimpleNamespace(
        status=status,
        message=f"Readiness artifacts are {status}.",
        refresh_command="make readiness",
    )


def test_batch_console_lane_mapping_and_source_requirements_are_research_safe():
    assert batch_console.batch_lane_for_operator("optional") == "optional_context"
    assert batch_console.batch_lane_for_operator("unknown") == "prices"
    assert "dry-run" in batch_console.batch_source_requirement("prices")
    assert "route back to the source lane" in batch_console.batch_source_requirement("metrics")
    assert "trusted-local" in batch_console.batch_source_requirement("optional_context")


def test_batch_console_snapshot_and_preflight_gates():
    missing_snapshot = _preflight(
        status="needs_preflight_fix",
        prior_snapshot_exists=False,
        do_not_proceed_if=("prior readiness snapshot is missing; run make readiness-snapshot before a reviewed batch",),
    )

    preflight_cards = batch_console.reviewed_batch_preflight_cards(missing_snapshot)
    snapshot_cards = batch_console.reviewed_batch_snapshot_gate_cards(missing_snapshot)
    snapshot_frame = batch_console.reviewed_batch_snapshot_gate_frame(missing_snapshot)
    rendered = " ".join(str(value) for card in preflight_cards + snapshot_cards for value in card.values()).lower()

    assert preflight_cards[0]["command"] == "make reviewed-batch-preflight LANE=prices TOP_N=10"
    assert "prior readiness snapshot is missing" in rendered
    assert snapshot_cards[0]["title"] == "Save baseline snapshot first"
    assert snapshot_frame.iloc[0]["Status"] == "missing_prior_snapshot"
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_batch_console_apply_guard_separates_mutating_and_read_only_lanes():
    fundamentals = _preflight(lane="fundamentals")
    metrics = _preflight(lane="metrics", dry_run_command="make metric-readiness-board TOP_N=10")

    fundamentals_cards = batch_console.reviewed_batch_apply_guard_cards(fundamentals)
    metrics_cards = batch_console.reviewed_batch_apply_guard_cards(metrics)
    metrics_frame = batch_console.reviewed_batch_apply_guard_frame(metrics)
    rendered = " ".join(str(value) for card in fundamentals_cards + metrics_cards for value in card.values()).lower()

    assert fundamentals_cards[0]["command"] == "make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>"
    assert "validate and preview before apply" in rendered
    assert metrics_cards[0]["title"] == "Read-only lane: no apply step"
    assert metrics_cards[0]["command"] == "make metric-readiness-board TOP_N=10"
    assert "supported is not available from metric review alone" in " ".join(metrics_frame.astype(str).to_numpy().flatten()).lower()
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_batch_console_execution_cards_and_checklist_keep_copy_only_boundaries():
    preflight = _preflight(
        status="needs_preflight_fix",
        prior_snapshot_exists=False,
        do_not_proceed_if=("prior readiness snapshot is missing; run make readiness-snapshot before a reviewed batch",),
    )
    cards = batch_console.reviewed_batch_execution_cards("prices", preflight, _freshness("current"))
    checklist = batch_console.reviewed_batch_execution_checklist_frame("prices", preflight, _freshness("current"))
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    checklist_rendered = " ".join(checklist.astype(str).to_numpy().flatten()).lower()

    assert [card["kicker"] for card in cards] == [
        "BATCH LANE",
        "BATCH LOOP",
        "SNAPSHOT GATE",
        "APPLY GUARD",
        "SOURCE GATE",
        "NEXT BATCH ACTION",
    ]
    assert cards[1]["command"] == "make readiness-snapshot"
    assert "commands are copy-only" in rendered
    assert "data-readiness queue, not a security ranking" in rendered
    assert "make diff-hygiene" in checklist_rendered
    assert "dry_run=1 make reviewed-batch-proof-record" in checklist_rendered
    assert "buy" not in rendered + checklist_rendered
    assert "sell" not in rendered + checklist_rendered


def test_batch_console_sequence_cards_preserve_validate_preview_apply_boundary():
    cards = batch_console.reviewed_batch_sequence_cards(_preflight(lane="metrics"))
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["PACKET", "DRY RUN", "MUTATION GATE", "PROOF"]
    assert cards[2]["command"] == "make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>"
    assert "metrics remain read-only" in rendered
    assert "restore standard local csvs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
