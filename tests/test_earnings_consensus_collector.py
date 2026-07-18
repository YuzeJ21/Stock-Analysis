from dataclasses import replace
from pathlib import Path

import pytest

from src.earnings_consensus_collector import (
    ProspectiveConsensusRecord,
    append_reviewed_snapshot,
    collection_plan,
    preview_collection,
)


def _record(**overrides) -> ProspectiveConsensusRecord:
    values = {
        "schema_version": "earnings-consensus-prospective-v1",
        "snapshot_id": "snap-001",
        "ticker": "NVDA",
        "fiscal_period": "2027-Q1",
        "snapshot_at": "2026-07-18T05:00:00Z",
        "retrieved_at": "2026-07-18T05:00:01Z",
        "source": "reviewed_csv",
        "source_ref": "file://reviewed/NVDA/2027-Q1/20260718",
        "revenue_consensus": "100",
        "eps_consensus": "1.00",
        "revenue_currency": "USD",
        "revenue_unit_scale": "1000000",
        "revenue_basis": "reported",
        "eps_currency": "USD",
        "eps_basis": "gaap",
        "eps_share_basis": "diluted",
        "eps_operations_basis": "reported",
        "split_adjustment_basis": "as_reported",
        "expected_report_date": "2026-08-20",
        "review_state": "reviewed",
        "supersedes_snapshot_id": "",
    }
    values.update(overrides)
    return ProspectiveConsensusRecord(**values)


def test_preview_detects_duplicate_and_preserves_revision_lineage():
    first = _record()
    duplicate = preview_collection((first,), first, as_of="2026-07-18T06:00:00Z")
    revision = preview_collection(
        (first,),
        replace(
            first,
            snapshot_id="snap-002",
            snapshot_at="2026-07-25T05:00:00Z",
            retrieved_at="2026-07-25T05:00:01Z",
            source_ref="file://reviewed/NVDA/2027-Q1/20260725",
            revenue_consensus="102",
            supersedes_snapshot_id="snap-001",
        ),
        as_of="2026-07-25T06:00:00Z",
    )

    assert duplicate.state == "duplicate"
    assert revision.state == "reviewable_revision"
    assert revision.write_allowed is True


def test_preview_rejects_post_cutoff_and_cooldown_recollection():
    first = _record()
    post_cutoff = preview_collection(
        (),
        replace(
            first,
            snapshot_at="2026-07-19T05:00:00Z",
            retrieved_at="2026-07-19T05:00:01Z",
        ),
        as_of="2026-07-18T06:00:00Z",
    )
    cooldown = preview_collection(
        (first,),
        replace(
            first,
            snapshot_id="snap-002",
            snapshot_at="2026-07-18T06:00:00Z",
            retrieved_at="2026-07-18T06:00:01Z",
            source_ref="file://reviewed/NVDA/2027-Q1/20260718-2",
            supersedes_snapshot_id="snap-001",
        ),
        as_of="2026-07-18T07:00:00Z",
        cooldown_hours=24,
    )

    assert post_cutoff.state == "rejected"
    assert "cutoff" in post_cutoff.reason
    assert cooldown.state == "cooldown"
    assert cooldown.write_allowed is False


def test_append_requires_explicit_review_confirmation_and_never_overwrites(tmp_path: Path):
    ledger = tmp_path / "snapshots.csv"
    with pytest.raises(ValueError, match="confirm_reviewed"):
        append_reviewed_snapshot(ledger, _record(), confirm_reviewed=False)

    append_reviewed_snapshot(ledger, _record(), confirm_reviewed=True)
    with pytest.raises(ValueError, match="duplicate"):
        append_reviewed_snapshot(ledger, _record(), confirm_reviewed=True)

    assert ledger.read_text(encoding="utf-8").count("snap-001") == 1


def test_collection_plan_is_scheduler_ready_but_does_not_collect():
    plan = collection_plan(
        tickers=("NVDA", "AMD"),
        as_of="2026-07-18T05:00:00Z",
        cadence="weekly",
    )

    assert plan.mode == "plan_only"
    assert plan.collection_performed is False
    assert plan.tickers == ("AMD", "NVDA")
    assert plan.next_action == "Run a provider probe or reviewed CSV preview at the planned cutoff."


def test_collector_rejects_invalid_period_contract():
    preview = preview_collection(
        (),
        _record(fiscal_period="next-quarter"),
        as_of="2026-07-18T06:00:00Z",
    )
    assert preview.state == "rejected"
    assert "fiscal_period" in preview.reason
