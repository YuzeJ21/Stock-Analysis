import csv
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from src.prospective_field_proof import (
    FIELDS,
    SCHEMA_VERSION,
    ProspectiveFieldProofRecord,
    field_proof_identity,
    load_field_proofs,
    load_proposed_field_proofs,
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
