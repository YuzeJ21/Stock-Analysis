from dataclasses import replace
from pathlib import Path

import pytest

from src.earnings_consensus_collector import (
    ProspectiveConsensusRecord,
    append_reviewed_snapshot,
    collection_plan,
    load_snapshots,
    preview_collection,
)
from src.commercial_source_rights import build_source_rights_registry


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


def _rights_registry(*, source_id: str = "licensed_consensus", commercial_use: str = "approved", supported_fields=None):
    return build_source_rights_registry(
        [
            {
                "source_id": source_id,
                "display_name": "Licensed consensus fixture",
                "permitted_use": "test_only",
                "commercial_use": commercial_use,
                "redistribution": "test_only",
                "storage_limits": "temporary test paths only",
                "attribution": "fixture",
                "rate_limits": "not applicable",
                "authentication": "not applicable",
                "expected_freshness": "fixture cutoff",
                "supported_fields": supported_fields or ["revenue_consensus", "eps_consensus"],
                "fallback_priority": 1,
            }
        ]
    )


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
        rights_registry=_rights_registry(source_id="reviewed_csv"),
    )
    assert preview.state == "rejected"
    assert "fiscal_period" in preview.reason
    assert preview.commercial_evidence_ready is True
    assert preview.commercial_write_allowed is False


def test_preview_reports_independent_revenue_and_eps_commercial_scope():
    registry = _rights_registry(supported_fields=["revenue_consensus"])
    eps_registry = _rights_registry(supported_fields=["eps_consensus"])
    revenue_only = preview_collection(
        (),
        _record(source="licensed_consensus", eps_consensus=""),
        as_of="2026-07-18T06:00:00Z",
        rights_registry=registry,
    )
    mixed = preview_collection(
        (),
        _record(source="licensed_consensus"),
        as_of="2026-07-18T06:00:00Z",
        rights_registry=registry,
    )
    eps_only = preview_collection(
        (),
        _record(source="licensed_consensus", revenue_consensus=""),
        as_of="2026-07-18T06:00:00Z",
        rights_registry=eps_registry,
    )

    assert revenue_only.required_supported_fields == ("revenue_consensus",)
    assert revenue_only.missing_supported_fields == ()
    assert revenue_only.commercial_rights_approved is True
    assert revenue_only.commercial_evidence_ready is True
    assert revenue_only.commercial_write_allowed is True
    assert eps_only.required_supported_fields == ("eps_consensus",)
    assert eps_only.missing_supported_fields == ()
    assert eps_only.commercial_write_allowed is True
    assert mixed.required_supported_fields == ("revenue_consensus", "eps_consensus")
    assert mixed.missing_supported_fields == ("eps_consensus",)
    assert mixed.write_allowed is True
    assert mixed.commercial_write_allowed is False
    assert mixed.commercial_blockers == ("registered_consensus_scope_missing:eps_consensus",)


def test_preview_fails_closed_for_unknown_unverified_and_composite_exact_sources():
    unverified_registry = _rights_registry(commercial_use="unverified")
    unverified = preview_collection(
        (),
        _record(source="licensed_consensus"),
        as_of="2026-07-18T06:00:00Z",
        rights_registry=unverified_registry,
    )
    composite = preview_collection(
        (),
        _record(source="licensed_consensus + reviewed_csv"),
        as_of="2026-07-18T06:00:00Z",
        rights_registry=_rights_registry(),
    )

    assert unverified.rights_status == "commercial_rights_unverified"
    assert unverified.write_allowed is True
    assert unverified.commercial_write_allowed is False
    assert unverified.commercial_blockers[0] == "commercial_rights:commercial_rights_unverified"
    assert composite.rights_status == "unknown_source"
    assert composite.commercial_rights_approved is False
    assert composite.missing_supported_fields == ("revenue_consensus", "eps_consensus")
    assert composite.commercial_write_allowed is False


def test_commercial_append_blocks_before_filesystem_mutation(tmp_path: Path, monkeypatch):
    ledger = tmp_path / "missing-parent" / "snapshots.csv"
    monkeypatch.setenv("COMMERCIAL_RESEARCH_MODE", "1")

    with pytest.raises(ValueError, match="commercial_evidence_review_required"):
        append_reviewed_snapshot(
            ledger,
            _record(),
            confirm_reviewed=True,
            rights_registry=_rights_registry(),
        )

    assert not ledger.parent.exists()


def test_approved_commercial_append_uses_exact_metric_scopes(tmp_path: Path):
    ledger = tmp_path / "snapshots.csv"
    record = _record(source="licensed_consensus")

    append_reviewed_snapshot(
        ledger,
        record,
        confirm_reviewed=True,
        commercial_mode=True,
        rights_registry=_rights_registry(),
    )

    assert load_snapshots(ledger) == (record,)
