import csv
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from src.earnings_consensus_collector import (
    FIELDS,
    ProspectiveConsensusRecord,
    append_reviewed_batch,
    append_reviewed_snapshot,
    collection_plan,
    load_snapshots,
    main,
    preview_collection,
    preview_collection_batch,
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


def _write_records(path: Path, records: tuple[ProspectiveConsensusRecord, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def _revision(record: ProspectiveConsensusRecord, *, snapshot_id: str = "snap-002") -> ProspectiveConsensusRecord:
    return replace(
        record,
        snapshot_id=snapshot_id,
        snapshot_at="2026-07-25T05:00:00Z",
        retrieved_at="2026-07-25T05:00:01Z",
        source_ref=f"file://reviewed/{record.ticker}/{record.fiscal_period}/20260725",
        revenue_consensus="102",
        supersedes_snapshot_id=record.snapshot_id,
    )


def _append_with_preview(
    ledger: Path,
    records: tuple[ProspectiveConsensusRecord, ...],
    *,
    cutoff: str = "2026-08-02T00:00:00Z",
    confirm_reviewed: bool = True,
    commercial_mode: bool | None = False,
    rights_registry=None,
) -> Path:
    existing = load_snapshots(ledger)
    preview = preview_collection_batch(
        existing,
        records,
        as_of=cutoff,
        commercial_mode=commercial_mode,
        rights_registry=rights_registry,
    )
    return append_reviewed_batch(
        ledger,
        records,
        confirm_reviewed=confirm_reviewed,
        commercial_mode=commercial_mode,
        rights_registry=rights_registry,
        review_cutoff=cutoff,
        preview_receipt=preview.preview_receipt,
    )


def _record_cli_args(
    input_path: Path,
    ledger: Path,
    records: tuple[ProspectiveConsensusRecord, ...],
    *,
    cutoff: str = "2026-08-02T00:00:00Z",
) -> list[str]:
    preview = preview_collection_batch(load_snapshots(ledger), records, as_of=cutoff)
    return [
        "record",
        "--input",
        str(input_path),
        "--ledger",
        str(ledger),
        "--as-of",
        cutoff,
        "--preview-receipt",
        preview.preview_receipt,
        "--confirm-reviewed",
    ]


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

    _append_with_preview(ledger, (_record(),))
    with pytest.raises(ValueError, match="duplicate"):
        _append_with_preview(ledger, (_record(),))

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
        _append_with_preview(
            ledger,
            (_record(),),
            commercial_mode=None,
            rights_registry=_rights_registry(),
        )

    assert not ledger.parent.exists()


def test_approved_commercial_append_uses_exact_metric_scopes(tmp_path: Path):
    ledger = tmp_path / "snapshots.csv"
    record = _record(source="licensed_consensus")

    _append_with_preview(
        ledger,
        (record,),
        commercial_mode=True,
        rights_registry=_rights_registry(),
    )

    assert load_snapshots(ledger) == (record,)


def test_record_preflights_whole_batch_before_any_append(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    ledger = tmp_path / "ledger.csv"
    first = _record()
    _write_records(input_path, (first, first))

    with pytest.raises(ValueError, match="duplicate"):
        main(_record_cli_args(input_path, ledger, (first, first)))

    assert not ledger.exists()


def test_record_cli_appends_only_the_exact_reviewed_preview(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    ledger = tmp_path / "ledger.csv"
    proposed = (_record(),)
    _write_records(input_path, proposed)

    main(_record_cli_args(input_path, ledger, proposed))

    assert load_snapshots(ledger) == proposed


def test_append_requires_cutoff_and_preview_receipt_before_mutation(tmp_path: Path):
    ledger = tmp_path / "missing-parent" / "ledger.csv"

    with pytest.raises(ValueError, match="review_cutoff"):
        append_reviewed_batch(ledger, (_record(),), confirm_reviewed=True)
    with pytest.raises(ValueError, match="preview_receipt"):
        append_reviewed_batch(
            ledger,
            (_record(),),
            confirm_reviewed=True,
            review_cutoff="2026-07-18T06:00:00Z",
        )

    assert not ledger.parent.exists()


def test_preview_uses_ordered_virtual_ledger_for_revision(tmp_path: Path, capsys):
    input_path = tmp_path / "input.csv"
    first = _record()
    _write_records(input_path, (first, _revision(first)))

    main(
        [
            "preview",
            "--input",
            str(input_path),
            "--ledger",
            str(tmp_path / "missing.csv"),
            "--as-of",
            "2026-07-26T00:00:00Z",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload.get("state") == "reviewable_batch"
    assert [row["state"] for row in payload["rows"]] == ["reviewable_new", "reviewable_revision"]
    assert payload["technical_write_allowed"] is True


def test_preview_detects_intra_batch_duplicate(tmp_path: Path, capsys):
    input_path = tmp_path / "input.csv"
    first = _record()
    _write_records(input_path, (first, first))

    main(
        [
            "preview",
            "--input",
            str(input_path),
            "--ledger",
            str(tmp_path / "missing.csv"),
            "--as-of",
            "2026-07-26T00:00:00Z",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload.get("state") == "rejected_batch"
    assert [row["state"] for row in payload["rows"]] == ["reviewable_new", "duplicate"]
    assert payload["technical_write_allowed"] is False


def test_preview_does_not_reorder_reversed_revision_chain(tmp_path: Path, capsys):
    input_path = tmp_path / "input.csv"
    first = _record()
    revision = _revision(first)
    _write_records(input_path, (revision, first))

    main(
        [
            "preview",
            "--input",
            str(input_path),
            "--ledger",
            str(tmp_path / "missing.csv"),
            "--as-of",
            "2026-07-26T00:00:00Z",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload.get("state") == "rejected_batch"
    assert payload["rows"][0]["state"] == "rejected"
    assert "supersedes_snapshot_id does not exist" in payload["rows"][0]["reason"]
    assert payload["rows"][1]["state"] == "reviewable_new"


def test_record_rejects_empty_batch_without_creating_destination(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    ledger = tmp_path / "missing-parent" / "ledger.csv"
    _write_records(input_path, ())

    with pytest.raises(ValueError, match="empty_batch"):
        main(_record_cli_args(input_path, ledger, ()))

    assert not ledger.parent.exists()


def test_batch_append_preserves_existing_bytes_when_later_row_is_invalid(tmp_path: Path):
    ledger = tmp_path / "ledger.csv"
    _append_with_preview(ledger, (_record(),))
    original_bytes = ledger.read_bytes()
    first = _record(
        snapshot_id="snap-010",
        ticker="AMD",
        source_ref="file://reviewed/AMD/2027-Q1/20260718",
    )
    conflict = replace(
        first,
        snapshot_id="snap-011",
        snapshot_at="2026-07-19T05:00:00Z",
        retrieved_at="2026-07-19T05:00:01Z",
        source_ref="file://reviewed/AMD/2027-Q1/20260719",
    )

    with pytest.raises(ValueError, match="later same-period"):
        _append_with_preview(ledger, (first, conflict))

    assert ledger.read_bytes() == original_bytes


def test_batch_append_blocks_later_commercial_rights_failure_before_mutation(tmp_path: Path):
    ledger = tmp_path / "missing-parent" / "ledger.csv"
    first = _record(source="licensed_consensus")
    revision = replace(_revision(first), source="unregistered_consensus")

    with pytest.raises(ValueError, match="batch_commercial_evidence_review_required"):
        _append_with_preview(
            ledger,
            (first, revision),
            commercial_mode=True,
            rights_registry=_rights_registry(),
        )

    assert not ledger.parent.exists()


def test_batch_append_records_valid_ordered_research_revision_chain(tmp_path: Path):
    ledger = tmp_path / "ledger.csv"
    first = _record()
    revision = _revision(first)

    _append_with_preview(ledger, (first, revision), commercial_mode=False)

    assert load_snapshots(ledger) == (first, revision)


def test_batch_append_records_valid_ordered_commercial_revision_chain(tmp_path: Path):
    ledger = tmp_path / "ledger.csv"
    first = _record(source="licensed_consensus")
    revision = _revision(first)

    _append_with_preview(
        ledger,
        (first, revision),
        commercial_mode=True,
        rights_registry=_rights_registry(),
    )

    assert load_snapshots(ledger) == (first, revision)


def test_batch_append_rejects_empty_sequence_without_mutation(tmp_path: Path):
    ledger = tmp_path / "missing-parent" / "ledger.csv"

    with pytest.raises(ValueError, match="empty_batch"):
        _append_with_preview(ledger, ())

    assert not ledger.parent.exists()


def test_existing_ledger_rows_are_validated_with_row_numbers_before_status(tmp_path: Path):
    ledger = tmp_path / "ledger.csv"
    _write_records(ledger, (_record(expected_report_date="not-a-date"),))

    with pytest.raises(ValueError, match=r"ledger row 2:.*expected_report_date"):
        main(["status", "--ledger", str(ledger)])


def test_existing_ledger_rejects_duplicate_ids_and_evidence_identities(tmp_path: Path):
    duplicate_id = tmp_path / "duplicate-id.csv"
    duplicate_identity = tmp_path / "duplicate-identity.csv"
    first = _record()
    _write_records(
        duplicate_id,
        (
            first,
            replace(
                first,
                ticker="AMD",
                source_ref="file://reviewed/AMD/2027-Q1/20260718",
            ),
        ),
    )
    _write_records(
        duplicate_identity,
        (first, replace(first, snapshot_id="snap-duplicate-evidence")),
    )

    with pytest.raises(ValueError, match="duplicate snapshot_id"):
        load_snapshots(duplicate_id)
    with pytest.raises(ValueError, match="duplicate snapshot identity"):
        load_snapshots(duplicate_identity)


@pytest.mark.parametrize(
    ("rows", "reason"),
    [
        (
            lambda first: (
                first,
                replace(
                    _revision(first),
                    supersedes_snapshot_id="missing-parent",
                ),
            ),
            "missing parent",
        ),
        (
            lambda first: (
                first,
                _revision(first),
                replace(
                    _revision(first, snapshot_id="snap-003"),
                    snapshot_at="2026-08-01T05:00:00Z",
                    retrieved_at="2026-08-01T05:00:01Z",
                    source_ref="file://reviewed/NVDA/2027-Q1/20260801",
                ),
            ),
            "fork",
        ),
        (
            lambda first: (
                replace(first, supersedes_snapshot_id="snap-002"),
                replace(_revision(first), supersedes_snapshot_id="snap-001"),
            ),
            "cycle",
        ),
        (
            lambda first: (
                first,
                replace(
                    _revision(first),
                    snapshot_at="2026-07-17T05:00:00Z",
                    retrieved_at="2026-07-17T05:00:01Z",
                ),
            ),
            "later than parent",
        ),
        (
            lambda first: (
                first,
                replace(
                    first,
                    snapshot_id="snap-second-root",
                    snapshot_at="2026-07-25T05:00:00Z",
                    retrieved_at="2026-07-25T05:00:01Z",
                    source_ref="file://reviewed/NVDA/2027-Q1/20260725",
                    revenue_consensus="102",
                ),
            ),
            "one root",
        ),
    ],
)
def test_existing_ledger_requires_one_linear_revision_chain(tmp_path: Path, rows, reason: str):
    ledger = tmp_path / "ledger.csv"
    _write_records(ledger, rows(_record()))

    with pytest.raises(ValueError, match=reason):
        load_snapshots(ledger)


def test_preview_rejects_superseding_a_non_leaf_snapshot():
    first = _record()
    second = _revision(first)
    proposed = replace(
        _revision(first, snapshot_id="snap-003"),
        snapshot_at="2026-08-01T05:00:00Z",
        retrieved_at="2026-08-01T05:00:01Z",
        source_ref="file://reviewed/NVDA/2027-Q1/20260801",
    )

    preview = preview_collection(
        (first, second),
        proposed,
        as_of="2026-08-01T06:00:00Z",
    )

    assert preview.state == "rejected"
    assert "current leaf" in preview.reason


def test_record_is_bound_to_exact_preview_cutoff_input_and_ledger_state(tmp_path: Path):
    cutoff = "2026-07-18T06:00:00Z"
    ledger = tmp_path / "ledger.csv"
    proposed = (_record(),)
    preview = preview_collection_batch(
        (),
        proposed,
        as_of=cutoff,
        commercial_mode=False,
    )

    assert preview.review_cutoff == "2026-07-18T06:00:00+00:00"
    assert len(preview.input_digest) == 64
    assert len(preview.ledger_digest) == 64
    assert len(preview.preview_receipt) == 64

    with pytest.raises(ValueError, match="preview receipt mismatch"):
        append_reviewed_batch(
            ledger,
            proposed,
            confirm_reviewed=True,
            commercial_mode=False,
            review_cutoff="2026-07-18T07:00:00Z",
            preview_receipt=preview.preview_receipt,
        )
    assert not ledger.exists()

    append_reviewed_batch(
        ledger,
        proposed,
        confirm_reviewed=True,
        commercial_mode=False,
        review_cutoff=cutoff,
        preview_receipt=preview.preview_receipt,
    )
    assert load_snapshots(ledger) == proposed


def test_changed_existing_ledger_invalidates_preview_receipt_without_mutation(tmp_path: Path):
    cutoff = "2026-07-26T00:00:00Z"
    ledger = tmp_path / "ledger.csv"
    first = _record()
    proposed = (_revision(first),)
    preview = preview_collection_batch(
        (first,),
        proposed,
        as_of=cutoff,
        commercial_mode=False,
    )
    append_reviewed_batch(
        ledger,
        (first,),
        confirm_reviewed=True,
        commercial_mode=False,
        review_cutoff="2026-07-18T06:00:00Z",
        preview_receipt=preview_collection_batch(
            (),
            (first,),
            as_of="2026-07-18T06:00:00Z",
            commercial_mode=False,
        ).preview_receipt,
    )
    original = ledger.read_bytes()
    append_reviewed_batch(
        ledger,
        (
            replace(
                proposed[0],
                snapshot_id="intervening",
                source_ref="file://reviewed/NVDA/2027-Q1/intervening",
            ),
        ),
        confirm_reviewed=True,
        commercial_mode=False,
        review_cutoff=cutoff,
        preview_receipt=preview_collection_batch(
            (first,),
            (
                replace(
                    proposed[0],
                    snapshot_id="intervening",
                    source_ref="file://reviewed/NVDA/2027-Q1/intervening",
                ),
            ),
            as_of=cutoff,
            commercial_mode=False,
        ).preview_receipt,
    )
    changed = ledger.read_bytes()

    with pytest.raises(ValueError, match="preview receipt mismatch"):
        append_reviewed_batch(
            ledger,
            proposed,
            confirm_reviewed=True,
            commercial_mode=False,
            review_cutoff=cutoff,
            preview_receipt=preview.preview_receipt,
        )

    assert changed != original
    assert ledger.read_bytes() == changed
