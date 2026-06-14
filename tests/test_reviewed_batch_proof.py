from pathlib import Path

import pytest

from src.reviewed_batch_proof import (
    ReviewedBatchProof,
    append_reviewed_batch_proof,
    build_batch_proof_from_args,
    load_reviewed_batch_proofs,
    main,
    render_reviewed_batch_proofs,
    reviewed_batch_proof_validation_rows,
    reviewed_batch_proof_validation_status,
)


def _proof(**overrides) -> ReviewedBatchProof:
    values = {
        "batch_id": "RB-TEST-001",
        "review_date": "2026-06-12",
        "reviewer": "local reviewer",
        "lane": "peers",
        "scope": "top 10 peer lane",
        "tickers": "AAA,BBB",
        "command_run": "make reviewed-batch LANE=peers TOP_N=10 && make peer-mapping-queue TOP_N=25",
        "validation_result": "not_run_read_only",
        "preview_result": "not_run_read_only",
        "apply_result": "not_run_no_source_proof",
        "pre_run_readiness_snapshot": "peer-ready 9/3538",
        "post_run_readiness_snapshot": "peer-ready 9/3538",
        "changed_readiness_counts": "none",
        "changed_tickers": "none",
        "source_files": "outputs/reviewed_batch_packet.md; data/reports/peer_unlock_worklist.csv",
        "generated_artifacts_reviewed": "packet kept as evidence; broad generated churn excluded",
        "final_outcome": "skipped",
        "notes": "Read-only peer pilot; no source-backed peer rows were applied.",
    }
    values.update(overrides)
    return ReviewedBatchProof(**values)


def test_reviewed_batch_proof_round_trips_and_renders_guardrails(tmp_path: Path):
    ledger = tmp_path / "reviewed_batch_proofs.csv"
    append_reviewed_batch_proof(_proof(), ledger)

    rows = load_reviewed_batch_proofs(ledger)
    rendered = render_reviewed_batch_proofs(rows)

    assert len(rows) == 1
    assert rows[0].batch_id == "RB-TEST-001"
    assert "Reviewed Batch Proof Ledger" in rendered
    assert "validate/preview/apply: not_run_read_only / not_run_read_only / not_run_no_source_proof" in rendered
    assert "changed_readiness_counts: none" in rendered
    assert "changed_tickers: none" in rendered
    assert "supported" not in rows[0].final_outcome
    assert "investment advice" in rendered
    assert "auto-trading" in rendered
    assert "direct buy/sell instructions" in rendered


def test_reviewed_batch_proof_rejects_unknown_outcome():
    class Args:
        batch_id = "RB-TEST-001"
        review_date = "2026-06-12"
        reviewer = "local reviewer"
        lane = "peers"
        scope = "top 10"
        tickers = "AAA"
        command_run = "make reviewed-batch"
        validation_result = "not_run"
        preview_result = "not_run"
        apply_result = "not_run"
        pre_run_readiness_snapshot = "before"
        post_run_readiness_snapshot = "after"
        changed_readiness_counts = "none"
        changed_tickers = "none"
        source_files = "outputs/reviewed_batch_packet.md"
        generated_artifacts_reviewed = "excluded"
        final_outcome = "recommended"
        notes = "bad outcome"

    with pytest.raises(SystemExit):
        build_batch_proof_from_args(Args())


def test_reviewed_batch_proof_validation_accepts_reviewed_no_change_values():
    row = _proof(final_outcome="still_blocked", changed_readiness_counts="none", changed_tickers="none")

    validation_rows = reviewed_batch_proof_validation_rows(row)

    assert reviewed_batch_proof_validation_status(validation_rows) == "ready_to_record"


def test_reviewed_batch_proof_dry_run_prints_preview_without_writing(tmp_path: Path, capsys):
    ledger = tmp_path / "reviewed_batch_proofs.csv"

    result = main(
        [
            "--ledger",
            str(ledger),
            "--dry-run",
            "--batch-id",
            "RB-DRY-001",
            "--review-date",
            "2026-06-14",
            "--reviewer",
            "local reviewer",
            "--lane",
            "metrics",
            "--scope",
            "AAA",
            "--tickers",
            "AAA",
            "--command-run",
            "make metric-readiness-board TOP_N=1",
            "--validation-result",
            "not_applicable_read_only_metric_review",
            "--preview-result",
            "reviewed metric blocker families",
            "--apply-result",
            "not_applicable_read_only_metric_review",
            "--pre-run-readiness-snapshot",
            "data/reports/ticker_readiness_report.previous.csv",
            "--post-run-readiness-snapshot",
            "data/reports/ticker_readiness_report.csv",
            "--changed-readiness-counts",
            "none",
            "--changed-tickers",
            "none",
            "--source-files",
            "metric queue output",
            "--generated-artifacts-reviewed",
            "excluded generated CSV churn",
            "--final-outcome",
            "still_blocked",
            "--notes",
            "read-only metrics remained blocked",
        ]
    )
    output = capsys.readouterr().out

    assert result == 0
    assert not ledger.exists()
    assert "Reviewed Batch Proof Dry Run" in output
    assert "batch_id: RB-DRY-001" in output
    assert "Validation status: ready_to_record" in output
    assert "dry-run preview only" in output


def test_reviewed_batch_proof_dry_run_reports_invalid_without_writing(tmp_path: Path, capsys):
    ledger = tmp_path / "reviewed_batch_proofs.csv"

    result = main(
        [
            "--ledger",
            str(ledger),
            "--dry-run",
            "--batch-id",
            "RB-DRY-002",
            "--review-date",
            "2026-06-14",
            "--lane",
            "metrics",
            "--command-run",
            "make metric-readiness-board TOP_N=1",
            "--validation-result",
            "not_applicable_read_only_metric_review",
            "--preview-result",
            "reviewed",
            "--apply-result",
            "not_applicable_read_only_metric_review",
            "--changed-readiness-counts",
            "none",
            "--changed-tickers",
            "none",
            "--source-files",
            "metric queue output",
            "--generated-artifacts-reviewed",
            "excluded generated CSV churn",
            "--final-outcome",
            "maybe_supported",
        ]
    )
    output = capsys.readouterr().out

    assert result == 2
    assert not ledger.exists()
    assert "Validation status: invalid_outcome" in output
    assert "final_outcome: invalid_outcome" in output


def test_reviewed_batch_proof_record_blocks_placeholder_fields(tmp_path: Path, capsys):
    ledger = tmp_path / "reviewed_batch_proofs.csv"

    result = main(
        [
            "--ledger",
            str(ledger),
            "--record",
            "--batch-id",
            "RB-BLOCKED-001",
            "--review-date",
            "2026-06-14",
            "--lane",
            "metrics",
            "--command-run",
            "make metric-readiness-board TOP_N=1",
            "--validation-result",
            "<pass/fail/not_applicable>",
            "--preview-result",
            "reviewed",
            "--apply-result",
            "not_applicable_read_only_metric_review",
            "--changed-readiness-counts",
            "none",
            "--changed-tickers",
            "none",
            "--source-files",
            "metric queue output",
            "--generated-artifacts-reviewed",
            "excluded generated CSV churn",
            "--final-outcome",
            "still_blocked",
        ]
    )
    output = capsys.readouterr().out

    assert result == 2
    assert not ledger.exists()
    assert "Reviewed Batch Proof Record blocked" in output
    assert "validation_result: missing_required" in output
