from __future__ import annotations

import json

import pytest

from tests.point_in_time_universe_remediation_fixtures import (
    walk_forward_rows,
)
from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import (
    _append_registry_source,
    _decision,
    _read_contract_rows,
    _refresh_contract_digest,
    _refresh_registry_digest,
    _replace_contract_rows,
    _rewrite_csv_and_manifest,
    _rewrite_manifest,
)


@pytest.mark.parametrize("event_type", ("not-a-real-event", ""))
def test_unclassifiable_event_type_cannot_inherit_corporate_action_rights(
    tmp_path,
    event_type,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    source_id = "corporate_only_source"
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_type=event_type,
            source_id=source_id,
        ),
    )
    _append_registry_source(
        registry,
        source_id,
        ("corporate_actions",),
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw["allowed_source_ids"].append(source_id),
    )
    _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)
    exact = next(
        row
        for row in packet.excluded
        if row.contract == "events" and row.source_row == 2
    )

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(
        packet,
        "source_rights_eligibility",
    ).reason_codes == ("source_rights_event_scope_unreadable",)
    assert "source_rights_event_scope_unreadable" in exact.reason_codes


def test_internal_missing_event_type_sentinel_has_no_inferred_rights_scope():
    from types import MappingProxyType

    from src.point_in_time_universe import _raw_required_rights_scope
    from src.point_in_time_universe_contracts import (
        RAW_MISSING_CELL,
        RawEvidenceRow,
    )

    row = RawEvidenceRow(
        "events",
        "events.csv",
        2,
        MappingProxyType({"event_type": RAW_MISSING_CELL}),
    )

    assert _raw_required_rights_scope(row) is None


@pytest.mark.parametrize(
    ("contract", "malformed_field"),
    [
        ("security_identity", "valid_from"),
        ("membership", "effective_from"),
        ("events", "effective_at"),
    ],
)
def test_malformed_evidence_still_blocks_unknown_source_rights_on_exact_row(
    tmp_path,
    contract,
    malformed_field,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        rows[0][malformed_field] = "not-a-timestamp"
        rows[0]["source_id"] = "unknown_source"

    _rewrite_csv_and_manifest(manifest, contract, mutate)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["allowed_source_ids"].append("unknown_source"),
    )

    packet = validate_point_in_time_universe(manifest, registry)
    exact = next(
        row
        for row in packet.excluded
        if row.contract == contract and row.source_row == 2
    )

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(packet, "source_rights_eligibility").status == "blocked"
    assert _decision(
        packet,
        "source_rights_eligibility",
    ).reason_codes == (
        "source_rights_field_scope_missing",
        "source_rights_unknown_source",
    )
    assert "schema_timestamp_invalid" in exact.reason_codes
    assert "source_rights_unknown_source" in exact.reason_codes
    assert "source_rights_field_scope_missing" in exact.reason_codes


def test_missing_source_identity_blocks_rights_independently_on_exact_row(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(source_id=""),
    )

    packet = validate_point_in_time_universe(manifest, registry)
    exact = next(
        row
        for row in packet.excluded
        if row.contract == "security_identity" and row.source_row == 2
    )

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(
        packet,
        "source_rights_eligibility",
    ).reason_codes == ("source_rights_source_missing",)
    assert exact.reason_codes == (
        "schema_required_field_missing",
        "source_rights_source_missing",
    )


def test_surplus_column_does_not_hide_populated_source_rights(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    rows = _read_contract_rows(manifest, "security_identity")
    rows[0]["source_id"] = "unknown_source"
    _replace_contract_rows(manifest, "security_identity", rows)
    raw = json.loads(manifest.read_text())
    entry = next(
        item
        for item in raw["files"]
        if item["contract"] == "security_identity"
    )
    path = manifest.parent / entry["path"]
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] += ",surplus"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _refresh_contract_digest(manifest, "security_identity")
    _rewrite_manifest(
        manifest,
        lambda payload: payload["allowed_source_ids"].append(
            "unknown_source"
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)
    exact = next(
        row
        for row in packet.excluded
        if row.contract == "security_identity" and row.source_row == 2
    )

    assert "schema_columns_invalid" in exact.reason_codes
    assert "source_rights_unknown_source" in exact.reason_codes
    assert _decision(packet, "source_rights_eligibility").status == "blocked"


@pytest.mark.parametrize(
    ("rights_case", "expected_reason"),
    [
        ("disallowed", "source_rights_source_not_allowed"),
        ("unreviewed", "source_rights_commercial_rights_unverified"),
        ("scope_mismatch", "source_rights_field_scope_missing"),
    ],
)
def test_populated_source_rights_failures_have_exact_row_lineage(
    tmp_path,
    rights_case,
    expected_reason,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    source_id = "review_case_source"
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(source_id=source_id),
    )
    if rights_case != "disallowed":
        scopes = (
            ("universe_membership",)
            if rights_case == "scope_mismatch"
            else ("security_identity",)
        )
        _append_registry_source(
            registry,
            source_id,
            scopes,
            commercial_use=(
                "unverified"
                if rights_case == "unreviewed"
                else "approved"
            ),
        )
        _rewrite_manifest(
            manifest,
            lambda raw: raw["allowed_source_ids"].append(source_id),
        )
        _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)
    exact = next(
        row
        for row in packet.excluded
        if row.contract == "security_identity" and row.source_row == 2
    )

    assert expected_reason in _decision(
        packet,
        "source_rights_eligibility",
    ).reason_codes
    assert expected_reason in exact.reason_codes


def test_walk_forward_history_is_strictly_prior_and_input_order_independent(
    tmp_path,
):
    from src.point_in_time_universe import _classify_evaluations
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    results = []
    for index, rows in enumerate(
        (walk_forward_rows(), list(reversed(walk_forward_rows())))
    ):
        root = tmp_path / str(index)
        root.mkdir()
        manifest, registry = build_valid_package(root)
        _replace_contract_rows(manifest, "evaluations", rows)
        _rewrite_manifest(
            manifest,
            lambda raw: raw.update(
                observation_cutoff_at="2023-01-01T00:00:00Z",
                evaluation_policy={
                    "kind": "walk_forward",
                    "minimum_history_count": 2,
                },
            ),
        )
        package = load_universe_package(manifest, registry)
        parsed = parse_universe_evidence(package)
        valid, reasons, global_reasons = _classify_evaluations(
            package.manifest,
            parsed.evaluations,
        )
        results.append(
            (
                tuple(sorted(row.evaluation_row_id for row in valid)),
                dict(reasons),
                global_reasons,
            )
        )

    assert results[0] == results[1]
    valid_ids, reasons, global_reasons = results[0]
    assert valid_ids == ("eval-bench-1-2023", "eval-research-1-2023")
    assert global_reasons == ()
    for universe in ("bench-1", "research-1"):
        assert reasons[f"eval-{universe}-2021"] == (
            "partition_minimum_history_unmet",
        )
        assert reasons[f"eval-{universe}-2022"] == (
            "partition_minimum_history_unmet",
        )
        assert reasons[f"eval-{universe}-2023"] == ()


def test_public_validator_excludes_bootstrap_and_unlocks_later_cutoff(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    semantic_results = []
    for index, rows in enumerate(
        (walk_forward_rows(), list(reversed(walk_forward_rows())))
    ):
        root = tmp_path / str(index)
        root.mkdir()
        manifest, registry = build_valid_package(root)
        _replace_contract_rows(manifest, "evaluations", rows)
        _rewrite_manifest(
            manifest,
            lambda raw: raw.update(
                observation_cutoff_at="2023-01-01T00:00:00Z",
                evaluation_policy={
                    "kind": "walk_forward",
                    "minimum_history_count": 2,
                },
            ),
        )

        packet = validate_point_in_time_universe(manifest, registry)
        semantic_results.append(
            (
                packet.decisions,
                packet.membership_digests,
                {
                    row.row_id: row.reason_codes
                    for row in packet.excluded
                    if row.contract == "evaluations"
                },
                {
                    row.row_id
                    for row in packet.raw_rows
                    if row.contract == "evaluations"
                },
            )
        )

    assert semantic_results[0] == semantic_results[1]
    decisions, digests, excluded, observed_evaluations = semantic_results[0]
    assert decisions["leakage_safe"].status == "passed"
    assert decisions["leakage_safe"].reason_codes == ()
    assert {
        (item.universe_id, item.evaluation_at)
        for item in digests
    } == {
        ("bench-1", "2023-01-01T00:00:00Z"),
        ("research-1", "2023-01-01T00:00:00Z"),
    }
    assert observed_evaluations == {
        f"eval-{universe}-{year}"
        for universe in ("bench-1", "research-1")
        for year in (2021, 2022, 2023)
    }
    assert set(excluded) == {
        "eval-bench-1-2021",
        "eval-bench-1-2022",
        "eval-research-1-2021",
        "eval-research-1-2022",
    }
    assert all(
        reasons == ("partition_minimum_history_unmet",)
        for reasons in excluded.values()
    )


def test_invalid_unavailable_and_same_time_evaluations_do_not_count_as_history(
    tmp_path,
):
    from src.point_in_time_universe import _classify_evaluations
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    rows = [
        {
            **walk_forward_rows()[0],
            "evaluation_row_id": "eval-unavailable",
            "evaluation_at": "2021-01-01T00:00:00Z",
            "available_at": "2021-01-02T00:00:00Z",
        },
        {
            **walk_forward_rows()[0],
            "evaluation_row_id": "eval-same-a",
            "evaluation_at": "2022-01-01T00:00:00Z",
            "available_at": "2022-01-01T00:00:00Z",
        },
        {
            **walk_forward_rows()[0],
            "evaluation_row_id": "eval-same-b",
            "evaluation_at": "2022-01-01T00:00:00Z",
            "available_at": "2022-01-01T00:00:00Z",
        },
    ]
    _replace_contract_rows(manifest, "evaluations", rows)
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            observation_cutoff_at="2022-01-01T00:00:00Z",
            evaluation_policy={
                "kind": "walk_forward",
                "minimum_history_count": 1,
            },
        ),
    )
    package = load_universe_package(manifest, registry)
    parsed = parse_universe_evidence(package)
    valid, reasons, _ = _classify_evaluations(
        package.manifest,
        parsed.evaluations,
    )

    assert valid == ()
    assert reasons["eval-unavailable"] == (
        "cutoff_evaluation_unavailable",
    )
    assert reasons["eval-same-a"] == (
        "partition_minimum_history_unmet",
    )
    assert reasons["eval-same-b"] == (
        "partition_minimum_history_unmet",
    )


@pytest.mark.parametrize(
    "contract",
    ("security_identity", "membership", "events"),
)
def test_retrieval_before_publication_blocks_exact_contract_row(
    tmp_path,
    contract,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        contract,
        lambda rows: rows[0].update(
            source_published_at="2020-01-03T00:00:00Z",
            retrieved_at="2020-01-02T00:00:00Z",
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)
    exact = next(
        row
        for row in packet.excluded
        if row.contract == contract and row.source_row == 2
    )

    assert _decision(packet, "technical_validity").status == "blocked"
    assert "schema_retrieved_before_publication" in exact.reason_codes
    assert packet.analysis_eligible is False


@pytest.mark.parametrize(
    ("published", "retrieved"),
    [
        ("2020-01-01T00:00:00Z", "2020-01-01T00:00:00Z"),
        ("2020-01-01T00:00:00Z", "2020-01-02T00:00:00Z"),
    ],
)
def test_publication_chronology_accepts_equality_and_valid_order(
    tmp_path,
    published,
    retrieved,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    for contract in ("security_identity", "membership", "events"):
        _rewrite_csv_and_manifest(
            manifest,
            contract,
            lambda rows: rows[0].update(
                source_published_at=published,
                retrieved_at=retrieved,
            ),
        )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "temporal_validity").status == "passed"
    assert packet.analysis_eligible is True
