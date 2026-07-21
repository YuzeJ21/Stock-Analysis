import csv
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from src.commercial_source_rights import SourceRights
from src.prospective_field_proof import (
    BatchFieldProofPreview,
    FIELDS,
    FieldProofPreview,
    SCHEMA_VERSION,
    ProspectiveFieldProofRecord,
    append_reviewed_field_proof_batch,
    field_proof_identity,
    load_field_proofs,
    load_proposed_field_proofs,
    preview_field_proof_batch,
    validate_field_proof_ledger,
)


def _record(**overrides: str) -> ProspectiveFieldProofRecord:
    values = {
        "schema_version": SCHEMA_VERSION,
        "proof_id": "",
        "ticker": "NVDA",
        "field_key": "revenue_consensus",
        "readiness_contract_version": "readiness-v1",
        "observed_at": "2026-07-18T05:00:00Z",
        "retrieved_at": "2026-07-18T05:00:01Z",
        "source_id": "reviewed_csv",
        "source_ref": "file://reviewed/NVDA/revenue/20260718",
        "source_status": "identified",
        "rights_status": "unverified",
        "rights_decision_ref": "rights-review-001",
        "payload_status": "reviewed",
        "payload_sha256": "a" * 64,
        "reviewer_id": "reviewer-001",
        "reviewer_decision": "accepted",
        "reviewed_at": "2026-07-18T05:00:02Z",
        "supersedes_proof_id": "",
    }
    values.update(overrides)
    candidate = ProspectiveFieldProofRecord(**values)
    if not candidate.proof_id:
        candidate = replace(candidate, proof_id=field_proof_identity(candidate))
    return candidate


def _revision(parent: ProspectiveFieldProofRecord, **overrides: str) -> ProspectiveFieldProofRecord:
    values = {
        "observed_at": "2026-07-19T05:00:00Z",
        "retrieved_at": "2026-07-19T05:00:01Z",
        "source_ref": "file://reviewed/NVDA/revenue/20260719",
        "payload_sha256": "b" * 64,
        "reviewed_at": "2026-07-19T05:00:02Z",
        "supersedes_proof_id": parent.proof_id,
        "proof_id": "",
    }
    values.update(overrides)
    return _record(**{**asdict(parent), **values})


def _write_csv(path: Path, records: tuple[ProspectiveFieldProofRecord, ...], *, header=FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def _reidentified(record: ProspectiveFieldProofRecord, **overrides: str) -> ProspectiveFieldProofRecord:
    values = dict(overrides)
    values["proof_id"] = ""
    candidate = replace(record, **values)
    return replace(candidate, proof_id=field_proof_identity(candidate))


def _rights_registry(
    *,
    source_id: str = "reviewed_csv",
    commercial_use: str = "approved",
    supported_fields: tuple[str, ...] = ("revenue_consensus",),
) -> dict[str, SourceRights]:
    rights = SourceRights(
        source_id=source_id,
        display_name="Reviewed CSV",
        permitted_use="reviewed research",
        commercial_use=commercial_use,
        redistribution="not approved",
        storage_limits="reviewed payload digest only",
        attribution="required",
        rate_limits="not applicable",
        authentication="local reviewed file",
        expected_freshness="point in time",
        supported_fields=supported_fields,
        fallback_priority=1,
    )
    return {source_id: rights}


def test_schema_constants_and_record_are_immutable():
    record = _record()

    assert SCHEMA_VERSION == "prospective-field-proof-v1"
    assert FIELDS == (
        "schema_version", "proof_id", "ticker", "field_key", "readiness_contract_version",
        "observed_at", "retrieved_at", "source_id", "source_ref", "source_status",
        "rights_status", "rights_decision_ref", "payload_status", "payload_sha256",
        "reviewer_id", "reviewer_decision", "reviewed_at", "supersedes_proof_id",
    )
    with pytest.raises(Exception):
        record.ticker = "AMD"


@pytest.mark.parametrize("header", [FIELDS[:-1], FIELDS + ("unexpected",), tuple(reversed(FIELDS))])
def test_loaders_require_the_exact_ordered_header(tmp_path: Path, header: tuple[str, ...]):
    ledger = tmp_path / "proofs.csv"
    _write_csv(ledger, (_record(),), header=header)

    with pytest.raises(ValueError, match="header"):
        load_field_proofs(ledger)


def test_missing_ledger_is_empty_but_present_empty_ledger_fails_closed(tmp_path: Path):
    missing = tmp_path / "missing.csv"
    empty = tmp_path / "empty.csv"
    empty.touch()

    assert load_field_proofs(missing) == ()
    with pytest.raises(ValueError, match="header"):
        load_field_proofs(empty)


def test_present_exact_header_zero_row_ledger_fails_closed(tmp_path: Path):
    ledger = tmp_path / "proofs.csv"
    _write_csv(ledger, ())

    with pytest.raises(ValueError, match="at least one data row"):
        load_field_proofs(ledger)


def test_non_regular_ledger_path_fails_closed_instead_of_looking_missing(tmp_path: Path):
    ledger = tmp_path / "proofs.csv"
    ledger.mkdir()

    with pytest.raises(ValueError, match="not a regular file"):
        load_field_proofs(ledger)


@pytest.mark.parametrize("loader", [load_field_proofs, load_proposed_field_proofs])
def test_loaders_reject_surplus_cells_beyond_the_exact_header(
    tmp_path: Path, loader
):
    ledger = tmp_path / "proofs.csv"
    record = _record()
    with ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerow([getattr(record, field) for field in FIELDS] + ["surplus"])

    with pytest.raises(ValueError, match="row 2: contains surplus cells"):
        loader(ledger)


def test_loaders_normalize_scope_for_semantic_proof_identity(tmp_path: Path):
    canonical = _record()
    variant = _reidentified(canonical, ticker=" nvda ", field_key=" Revenue_Consensus ")
    ledger = tmp_path / "proofs.csv"
    _write_csv(ledger, (variant,))

    assert field_proof_identity(variant) == field_proof_identity(canonical)
    assert load_field_proofs(ledger) == (replace(variant, ticker="nvda", field_key="Revenue_Consensus"),)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_ref", "<source-ref>", "source_ref"),
        ("reviewer_id", "unknown", "reviewer_id"),
        ("rights_decision_ref", "-", "rights_decision_ref"),
        ("payload_sha256", "", "payload_sha256"),
    ],
)
def test_required_values_reject_missing_and_placeholder_content(
    tmp_path: Path, field: str, value: str, message: str
):
    ledger = tmp_path / "proofs.csv"
    _write_csv(ledger, (_reidentified(_record(), **{field: value}),))

    with pytest.raises(ValueError, match=rf"ledger row 2: .*{message}"):
        load_field_proofs(ledger)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_status", "pending"),
        ("rights_status", "pending"),
        ("payload_status", "pending"),
        ("reviewer_decision", "pending"),
    ],
)
def test_controlled_enums_fail_closed(tmp_path: Path, field: str, value: str):
    ledger = tmp_path / "proofs.csv"
    _write_csv(ledger, (_reidentified(_record(), **{field: value}),))

    with pytest.raises(ValueError, match=rf"ledger row 2: .*{field}"):
        load_field_proofs(ledger)


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "g" * 64])
def test_payload_digest_must_be_lowercase_sha256(tmp_path: Path, digest: str):
    ledger = tmp_path / "proofs.csv"
    _write_csv(ledger, (_reidentified(_record(), payload_sha256=digest),))

    with pytest.raises(ValueError, match="ledger row 2: .*payload_sha256"):
        load_field_proofs(ledger)


def test_proof_id_must_equal_semantic_identity_and_identity_is_canonical():
    record = _record()
    payload = {
        field: getattr(record, field)
        for field in FIELDS
        if field not in {"proof_id", "supersedes_proof_id"}
    }
    assert field_proof_identity(record) == hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    with pytest.raises(ValueError, match="proof_id must equal semantic identity"):
        validate_field_proof_ledger((replace(record, proof_id="f" * 64),))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("observed_at", "2026-07-18T05:00:00", "timezone-aware"),
        ("retrieved_at", "invalid", "ISO-8601"),
        ("retrieved_at", "2026-07-18T04:59:59Z", "observed_at cannot be after retrieved_at"),
        ("reviewed_at", "2026-07-18T05:00:00Z", "retrieved_at cannot be after reviewed_at"),
    ],
)
def test_timestamps_must_be_utc_aware_and_ordered_without_a_cutoff(
    tmp_path: Path, field: str, value: str, message: str
):
    ledger = tmp_path / "proofs.csv"
    _write_csv(ledger, (_reidentified(_record(), **{field: value}),))

    with pytest.raises(ValueError, match=rf"ledger row 2: .*{message}"):
        load_field_proofs(ledger)


def test_input_errors_are_row_numbered_and_loads_validate_proposed_rows(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    _write_csv(input_path, (_record(), _reidentified(_record(), reviewer_decision="pending")))

    with pytest.raises(ValueError, match="input row 3: reviewer_decision"):
        load_proposed_field_proofs(input_path)


def test_accepted_record_requires_identified_source_reviewed_payload_and_non_placeholder_reviewer():
    accepted = _record()
    for field, value in (
        ("source_status", "unavailable"),
        ("payload_status", "unavailable"),
        ("reviewer_id", "<reviewer>"),
    ):
        invalid = _reidentified(accepted, **{field: value})
        with pytest.raises(ValueError, match=field):
            validate_field_proof_ledger((invalid,))

    assert validate_field_proof_ledger((accepted,)) is None


def test_ledger_rejects_duplicate_ids_and_semantic_identities():
    root = _record()
    duplicate_identity = replace(root, proof_id=root.proof_id)

    with pytest.raises(ValueError, match="ledger row 3: duplicate proof_id"):
        validate_field_proof_ledger((root, duplicate_identity))


def test_ledger_accepts_one_linear_chain_per_independent_normalized_scope():
    root = _record()
    child = _revision(root)
    independent = _reidentified(
        _record(ticker="amd", field_key="EPS_CONSENSUS", payload_sha256="c" * 64),
        ticker=" amd ", field_key=" eps_consensus ", payload_sha256="c" * 64,
    )

    assert validate_field_proof_ledger((root, child, independent)) is None


def test_ledger_rejects_missing_and_cross_scope_parents():
    root = _record()
    missing = _revision(root, supersedes_proof_id="f" * 64)
    cross_scope = _revision(root, field_key="eps_consensus")

    with pytest.raises(ValueError, match="ledger row 3: missing parent proof"):
        validate_field_proof_ledger((root, missing))
    with pytest.raises(ValueError, match="ledger row 3: revision parent must preserve normalized scope"):
        validate_field_proof_ledger((root, cross_scope))


def test_ledger_rejects_parent_after_child_and_non_monotonic_review_time():
    root = _record()
    child = _revision(root)
    parent_after_child = replace(root, proof_id="")
    parent_after_child = replace(parent_after_child, proof_id=field_proof_identity(parent_after_child))
    child_for_future_parent = _revision(parent_after_child)
    stale_time = _revision(
        root,
        observed_at=root.observed_at,
        retrieved_at=root.retrieved_at,
        reviewed_at=root.reviewed_at,
    )

    with pytest.raises(ValueError, match="ledger row 2: revision parent must appear earlier"):
        validate_field_proof_ledger((child_for_future_parent, parent_after_child))
    with pytest.raises(ValueError, match="ledger row 3: reviewed_at must be strictly later"):
        validate_field_proof_ledger((root, stale_time))


def test_ledger_rejects_duplicate_root_fork_and_stale_leaf_revision():
    root = _record()
    child = _revision(root)
    duplicate_root = _reidentified(root, payload_sha256="c" * 64, supersedes_proof_id="")
    fork = _revision(root, payload_sha256="d" * 64)
    stale_leaf = _revision(root, payload_sha256="e" * 64, reviewed_at="2026-07-20T05:00:02Z")

    with pytest.raises(ValueError, match="exactly one root"):
        validate_field_proof_ledger((root, duplicate_root))
    with pytest.raises(ValueError, match="revision fork"):
        validate_field_proof_ledger((root, child, fork))
    with pytest.raises(ValueError, match="current leaf"):
        validate_field_proof_ledger((root, child, stale_leaf))


def test_ledger_rejects_cycle_and_disconnected_cycle():
    root = _record()
    first = _revision(root)
    cycle = _reidentified(first, payload_sha256="c" * 64)
    cycle = replace(cycle, supersedes_proof_id=cycle.proof_id)

    with pytest.raises(ValueError, match="revision cycle"):
        validate_field_proof_ledger((cycle,))
    with pytest.raises(ValueError, match="revision cycle"):
        validate_field_proof_ledger((root, first, cycle))


def test_preview_types_are_immutable_and_accepted_exact_scope_is_eligible():
    proposed = _reidentified(_record(), rights_status="approved")

    preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=_rights_registry(),
    )

    assert isinstance(preview, BatchFieldProofPreview)
    assert isinstance(preview.rows[0], FieldProofPreview)
    assert preview.technical_write_eligible is True
    assert preview.commercial_evidence_eligible is True
    assert preview.technical_blockers == ()
    assert preview.commercial_blockers == ()
    assert preview.rows[0].state == "reviewable_new"
    assert preview.rows[0].proof_identity == proposed.proof_id
    with pytest.raises(Exception):
        preview.rows = ()


@pytest.mark.parametrize(
    ("reviewer_decision", "source_status", "payload_status", "expected_state"),
    [
        ("accepted", "identified", "reviewed", "reviewable_new"),
        ("rejected", "unavailable", "rejected", "reviewable_new"),
        ("needs_follow_up", "disputed", "unavailable", "reviewable_new"),
    ],
)
def test_review_dispositions_remain_technically_recordable_but_commercially_independent(
    reviewer_decision: str,
    source_status: str,
    payload_status: str,
    expected_state: str,
):
    proposed = _reidentified(
        _record(),
        reviewer_decision=reviewer_decision,
        source_status=source_status,
        payload_status=payload_status,
        rights_status="approved",
    )

    preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=_rights_registry(),
    )

    assert preview.rows[0].state == expected_state
    assert preview.rows[0].technical_write_eligible is True
    assert preview.technical_write_eligible is True
    assert preview.rows[0].commercial_evidence_eligible is (
        reviewer_decision == "accepted"
    )


@pytest.mark.parametrize(
    ("overrides", "technical_blocker"),
    [
        ({"source_status": "unavailable"}, "accepted records require source_status=identified"),
        ({"source_status": "disputed"}, "accepted records require source_status=identified"),
        ({"payload_status": "unavailable"}, "accepted records require payload_status=reviewed"),
        ({"payload_status": "rejected"}, "accepted records require payload_status=reviewed"),
    ],
)
def test_accepted_record_with_unreviewable_source_or_payload_is_technically_rejected(
    overrides: dict[str, str], technical_blocker: str
):
    proposed = _reidentified(_record(), **overrides)

    preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=_rights_registry(),
    )

    assert preview.technical_write_eligible is False
    assert technical_blocker in preview.technical_blockers[0]


@pytest.mark.parametrize(
    ("record_overrides", "registry", "commercial_blocker"),
    [
        ({"source_id": "unknown"}, _rights_registry(), "commercial_rights:unknown_source"),
        ({}, _rights_registry(commercial_use="unverified"), "commercial_rights:commercial_rights_unverified"),
        ({"field_key": "unsupported_field"}, _rights_registry(), "registered_field_scope_missing:unsupported_field"),
        ({"rights_status": "unverified"}, _rights_registry(), "record_rights_status:unverified"),
        ({"rights_decision_ref": "<rights-decision>"}, _rights_registry(), "rights_decision_ref_required"),
    ],
)
def test_commercial_eligibility_fails_closed_without_exact_approved_rights_scope(
    record_overrides: dict[str, str],
    registry: dict[str, SourceRights],
    commercial_blocker: str,
):
    proposed = _reidentified(_record(rights_status="approved"), **record_overrides)

    preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )

    assert preview.commercial_evidence_eligible is False
    assert commercial_blocker in preview.commercial_blockers[0]


def test_research_mode_keeps_technical_recording_independent_from_commercial_eligibility():
    proposed = _record(rights_status="unverified")

    preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=_rights_registry(commercial_use="unverified"),
    )

    assert preview.technical_write_eligible is True
    assert preview.commercial_evidence_eligible is False
    assert preview.state == "reviewable_batch"


def test_batch_preview_uses_a_virtual_ledger_for_same_batch_revision():
    root = _reidentified(_record(), rights_status="approved")
    child = _reidentified(_revision(root), rights_status="approved")

    preview = preview_field_proof_batch(
        (),
        (root, child),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=True,
        rights_registry=_rights_registry(),
    )

    assert [row.state for row in preview.rows] == ["reviewable_new", "reviewable_revision"]
    assert preview.technical_write_eligible is True
    assert preview.commercial_evidence_eligible is True


def _records_digest(records: tuple[ProspectiveFieldProofRecord, ...]) -> str:
    return hashlib.sha256(
        json.dumps(
            [asdict(record) for record in records],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _registry_digest(registry: dict[str, SourceRights]) -> str:
    payload = [asdict(registry[source_id]) for source_id in sorted(registry)]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_preview_receipt_is_deterministic_and_binds_every_review_input():
    existing = (_reidentified(_record(), rights_status="approved"),)
    proposed = (
        _reidentified(
            _record(ticker="AMD", payload_sha256="c" * 64), rights_status="approved"
        ),
    )
    registry = _rights_registry()

    first = preview_field_proof_batch(
        existing,
        proposed,
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )
    second = preview_field_proof_batch(
        existing,
        proposed,
        as_of="2026-07-20T00:00:00+00:00",
        commercial_mode=False,
        rights_registry=dict(reversed(tuple(registry.items()))),
    )

    expected_ledger_digest = _records_digest(existing)
    expected_input_digest = _records_digest(proposed)
    expected_registry_digest = _registry_digest(registry)
    expected_receipt = hashlib.sha256(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "review_cutoff": "2026-07-20T00:00:00+00:00",
                "commercial_mode": False,
                "ledger_digest": expected_ledger_digest,
                "input_digest": expected_input_digest,
                "source_rights_registry_digest": expected_registry_digest,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert first.ledger_digest == expected_ledger_digest
    assert first.input_digest == expected_input_digest
    assert first.source_rights_registry_digest == expected_registry_digest
    assert first.preview_receipt == expected_receipt
    assert second.preview_receipt == expected_receipt


def test_preview_receipt_changes_with_input_cutoff_mode_or_registry():
    proposed = _reidentified(_record(), rights_status="approved")
    registry = _rights_registry()
    baseline = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )

    changed_input = preview_field_proof_batch(
        (),
        (_reidentified(proposed, payload_sha256="d" * 64),),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )
    changed_cutoff = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-21T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )
    changed_mode = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=True,
        rights_registry=registry,
    )
    changed_registry = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=_rights_registry(supported_fields=("eps_consensus",)),
    )

    assert len(
        {
            baseline.preview_receipt,
            changed_input.preview_receipt,
            changed_cutoff.preview_receipt,
            changed_mode.preview_receipt,
            changed_registry.preview_receipt,
        }
    ) == 5


def test_append_requires_confirmation_receipt_and_a_nonempty_batch(tmp_path: Path):
    ledger = tmp_path / "proofs.csv"
    proposed = _reidentified(_record(), rights_status="approved")
    registry = _rights_registry()
    preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )

    with pytest.raises(ValueError, match="confirm_reviewed"):
        append_reviewed_field_proof_batch(
            ledger,
            (proposed,),
            confirm_reviewed=False,
            commercial_mode=False,
            rights_registry=registry,
            review_cutoff=preview.review_cutoff,
            preview_receipt=preview.preview_receipt,
        )
    with pytest.raises(ValueError, match="preview_receipt"):
        append_reviewed_field_proof_batch(
            ledger,
            (proposed,),
            confirm_reviewed=True,
            commercial_mode=False,
            rights_registry=registry,
            review_cutoff=preview.review_cutoff,
            preview_receipt=None,
        )

    empty = preview_field_proof_batch(
        (),
        (),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )
    with pytest.raises(ValueError, match="empty_batch"):
        append_reviewed_field_proof_batch(
            ledger,
            (),
            confirm_reviewed=True,
            commercial_mode=False,
            rights_registry=registry,
            review_cutoff=empty.review_cutoff,
            preview_receipt=empty.preview_receipt,
        )
    assert not ledger.exists()


def test_append_rejects_stale_receipt_after_ledger_change_without_writing(tmp_path: Path):
    ledger = tmp_path / "proofs.csv"
    proposed = _reidentified(
        _record(ticker="AMD", payload_sha256="c" * 64), rights_status="approved"
    )
    registry = _rights_registry()
    preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )
    intervening = _reidentified(_record(), rights_status="approved")
    _write_csv(ledger, (intervening,))
    before = ledger.read_bytes()

    with pytest.raises(ValueError, match="preview receipt mismatch"):
        append_reviewed_field_proof_batch(
            ledger,
            (proposed,),
            confirm_reviewed=True,
            commercial_mode=False,
            rights_registry=registry,
            review_cutoff=preview.review_cutoff,
            preview_receipt=preview.preview_receipt,
        )

    assert ledger.read_bytes() == before


@pytest.mark.parametrize("change", ["input", "cutoff", "mode", "registry"])
def test_append_rejects_receipt_after_any_other_bound_input_changes(
    tmp_path: Path, change: str
):
    ledger = tmp_path / "proofs.csv"
    proposed = _reidentified(_record(), rights_status="approved")
    records = (proposed,)
    cutoff = "2026-07-20T00:00:00Z"
    commercial_mode = False
    registry = _rights_registry()
    preview = preview_field_proof_batch(
        (),
        records,
        as_of=cutoff,
        commercial_mode=commercial_mode,
        rights_registry=registry,
    )
    if change == "input":
        records = (_reidentified(proposed, payload_sha256="d" * 64),)
    elif change == "cutoff":
        cutoff = "2026-07-21T00:00:00Z"
    elif change == "mode":
        commercial_mode = True
    else:
        registry = _rights_registry(supported_fields=("eps_consensus",))

    with pytest.raises(ValueError, match="preview receipt mismatch"):
        append_reviewed_field_proof_batch(
            ledger,
            records,
            confirm_reviewed=True,
            commercial_mode=commercial_mode,
            rights_registry=registry,
            review_cutoff=cutoff,
            preview_receipt=preview.preview_receipt,
        )
    assert not ledger.exists()


def test_mixed_validity_batch_is_all_or_nothing(tmp_path: Path):
    ledger = tmp_path / "proofs.csv"
    valid = _reidentified(_record(), rights_status="approved")
    invalid = _reidentified(
        _record(ticker="AMD", payload_sha256="c" * 64),
        rights_status="approved",
        source_status="unavailable",
    )
    registry = _rights_registry()
    preview = preview_field_proof_batch(
        (),
        (valid, invalid),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )

    assert preview.technical_write_eligible is False
    with pytest.raises(ValueError, match="rejected_batch"):
        append_reviewed_field_proof_batch(
            ledger,
            (valid, invalid),
            confirm_reviewed=True,
            commercial_mode=False,
            rights_registry=registry,
            review_cutoff=preview.review_cutoff,
            preview_receipt=preview.preview_receipt,
        )
    assert not ledger.exists()


def test_append_writes_one_header_and_rows_once_in_reviewed_order(tmp_path: Path):
    ledger = tmp_path / "proofs.csv"
    root = _reidentified(_record(), rights_status="approved")
    child = _reidentified(_revision(root), rights_status="approved")
    registry = _rights_registry()
    preview = preview_field_proof_batch(
        (),
        (root, child),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=True,
        rights_registry=registry,
    )

    result = append_reviewed_field_proof_batch(
        ledger,
        (root, child),
        confirm_reviewed=True,
        commercial_mode=True,
        rights_registry=registry,
        review_cutoff=preview.review_cutoff,
        preview_receipt=preview.preview_receipt,
    )

    assert result == ledger
    assert load_field_proofs(ledger) == (root, child)
    assert ledger.read_text(encoding="utf-8").count(",".join(FIELDS)) == 1

    prior_bytes = ledger.read_bytes()
    grandchild = _reidentified(
        _revision(
            child,
            observed_at="2026-07-20T05:00:00Z",
            retrieved_at="2026-07-20T05:00:01Z",
            reviewed_at="2026-07-20T05:00:02Z",
            payload_sha256="c" * 64,
        ),
        rights_status="approved",
    )
    revision_preview = preview_field_proof_batch(
        (root, child),
        (grandchild,),
        as_of="2026-07-21T00:00:00Z",
        commercial_mode=True,
        rights_registry=registry,
    )
    append_reviewed_field_proof_batch(
        ledger,
        (grandchild,),
        confirm_reviewed=True,
        commercial_mode=True,
        rights_registry=registry,
        review_cutoff=revision_preview.review_cutoff,
        preview_receipt=revision_preview.preview_receipt,
    )

    assert ledger.read_bytes().startswith(prior_bytes)
    assert load_field_proofs(ledger) == (root, child, grandchild)
    assert ledger.read_text(encoding="utf-8").count(",".join(FIELDS)) == 1


def test_research_append_can_record_technical_proof_while_commercial_mode_fails_closed(
    tmp_path: Path,
):
    proposed = _record(rights_status="unverified")
    registry = _rights_registry(commercial_use="unverified")
    research_ledger = tmp_path / "research.csv"
    commercial_ledger = tmp_path / "commercial.csv"
    research_preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=False,
        rights_registry=registry,
    )
    commercial_preview = preview_field_proof_batch(
        (),
        (proposed,),
        as_of="2026-07-20T00:00:00Z",
        commercial_mode=True,
        rights_registry=registry,
    )

    append_reviewed_field_proof_batch(
        research_ledger,
        (proposed,),
        confirm_reviewed=True,
        commercial_mode=False,
        rights_registry=registry,
        review_cutoff=research_preview.review_cutoff,
        preview_receipt=research_preview.preview_receipt,
    )
    with pytest.raises(ValueError, match="batch_commercial_evidence_review_required"):
        append_reviewed_field_proof_batch(
            commercial_ledger,
            (proposed,),
            confirm_reviewed=True,
            commercial_mode=True,
            rights_registry=registry,
            review_cutoff=commercial_preview.review_cutoff,
            preview_receipt=commercial_preview.preview_receipt,
        )

    assert load_field_proofs(research_ledger) == (proposed,)
    assert not commercial_ledger.exists()
