from pathlib import Path

import pytest

from src.reviewed_batch_proof import (
    ReviewedBatchProof,
    append_reviewed_batch_proof,
    build_batch_proof_from_args,
    load_reviewed_batch_proofs,
    render_reviewed_batch_proofs,
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
