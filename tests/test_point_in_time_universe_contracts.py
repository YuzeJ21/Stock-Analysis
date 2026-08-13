import csv
import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

from tests.point_in_time_universe_fixture import build_valid_package


def _rewrite_csv_and_manifest(manifest, contract, mutate):
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == contract)
    path = manifest.parent / entry["path"]
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["row_count"] = len(rows)
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def _update_manifest_entry(manifest, contract, path, *, row_count=1):
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == contract)
    entry["path"] = path.relative_to(manifest.parent).as_posix()
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["row_count"] = row_count
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def _reason_codes(parsed):
    return {code for finding in parsed.findings for code in finding.reason_codes}


def test_parser_preserves_raw_order_and_normalizes_display_ticker(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(manifest, "security_identity", lambda rows: rows[0].update(ticker=" aaa "))
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert parsed.identities[0].ticker == "AAA"
    assert parsed.raw[0].contract == "security_identity"
    assert parsed.raw[0].source_row == 2


@pytest.mark.parametrize(
    "contract,column,value,reason",
    [
        ("security_identity", "valid_from", "2020-01-01", "schema_timestamp_invalid"),
        ("membership", "membership_state", "maybe", "schema_enum_invalid"),
        ("membership", "universe_kind", "portfolio", "schema_enum_invalid"),
        ("events", "event_type", "dividend", "schema_enum_invalid"),
        ("events", "ratio_numerator", "nan", "schema_ratio_invalid"),
        ("evaluations", "partition", "future", "schema_enum_invalid"),
    ],
)
def test_invalid_values_become_stable_technical_findings(tmp_path, contract, column, value, reason):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(manifest, contract, lambda rows: rows[0].update({column: value}))
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert reason in _reason_codes(parsed)


def test_split_requires_both_positive_ratio_values(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        rows[0].update(event_type="split", ratio_numerator="2", ratio_denominator="")

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_ratio_pair_required" in _reason_codes(parsed)


def test_unexpected_or_missing_columns_block_contract(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    path = manifest.parent / "identity.csv"
    path.write_text(path.read_text().replace("issuer_id,", ""), encoding="utf-8")
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == "security_identity")
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(
        ValueError,
        match="^package_csv_columns_invalid$",
    ):
        parse_universe_evidence(
            load_universe_package(manifest, registry)
        )


@pytest.mark.parametrize(
    "value",
    [
        "2020-01-01 00:00:00Z",
        "20200101T000000Z",
        "2020-01-01T00:00Z",
        "2020-01-01T00:00:00+00:00Z",
        "2020-02-30T00:00:00Z",
        "2020-01-01T00:00:00.Z",
        "2020-01-01T00:00:00Zgarbage",
    ],
)
def test_timestamp_contract_rejects_tolerant_and_malformed_utc_forms(tmp_path, value):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(valid_from=value),
    )
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_timestamp_invalid" in _reason_codes(parsed)


def test_timestamp_contract_accepts_rfc3339_utc_fractional_seconds(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(valid_from="2020-01-01T00:00:00.123Z"),
    )
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert not parsed.findings
    assert parsed.identities[0].valid_from.microsecond == 123000


@pytest.mark.parametrize("event_type", ["split", "reverse_split"])
def test_split_events_require_ratio_pair_when_both_values_are_blank(tmp_path, event_type):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(event_type=event_type, ratio_numerator="", ratio_denominator=""),
    )
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_ratio_pair_required" in _reason_codes(parsed)


def test_delisting_requires_delisted_listing_state(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(event_type="delisting", listing_state_after="active"),
    )
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_delisting_listing_state_invalid" in _reason_codes(parsed)


def test_parser_preserves_case_sensitive_opaque_identifiers(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(
            identity_row_id="Id-1a",
            security_id="Sec-Case",
            issuer_id="Issuer-Case",
            ticker="aAa",
            exchange="xNyS",
            source_id="Source-Case",
            source_ref="fixture://Identity/Case",
            supersedes_identity_row_id="Prior-Id",
        ),
    )
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))
    identity = parsed.identities[0]

    assert not parsed.findings
    assert identity.identity_row_id == "Id-1a"
    assert identity.security_id == "Sec-Case"
    assert identity.issuer_id == "Issuer-Case"
    assert identity.ticker == "AAA"
    assert identity.exchange == "xNyS"
    assert identity.source_id == "Source-Case"
    assert identity.source_ref == "fixture://Identity/Case"
    assert identity.supersedes_identity_row_id == "Prior-Id"


@pytest.mark.parametrize(
    "contract,column",
    [
        ("security_identity", "security_id"),
        ("security_identity", "source_ref"),
        ("membership", "universe_id"),
        ("membership", "universe_kind"),
        ("events", "event_type"),
        ("evaluations", "partition"),
    ],
)
def test_padded_required_identifiers_and_enums_are_rejected(tmp_path, contract, column):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        contract,
        lambda rows: rows[0].update({column: f" {rows[0][column]} "}),
    )
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_whitespace_invalid" in _reason_codes(parsed)


@pytest.mark.parametrize(
    "contract,column",
    [
        ("security_identity", "supersedes_identity_row_id"),
        ("membership", "supersedes_membership_row_id"),
        ("events", "successor_security_id"),
        ("events", "supersedes_event_row_id"),
    ],
)
def test_padded_optional_opaque_identifiers_are_rejected(tmp_path, contract, column):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(manifest, contract, lambda rows: rows[0].update({column: " Parent-Id "}))
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_whitespace_invalid" in _reason_codes(parsed)


@pytest.mark.parametrize("extra", [False, True])
def test_missing_or_surplus_cells_block_the_csv_contract(tmp_path, extra):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    path = manifest.parent / "identity.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    headers = list(row)
    values = [row[header] for header in headers]
    if extra:
        values.append("surplus")
    else:
        values.pop()
    path.write_text(",".join(headers) + "\n" + ",".join(values) + "\n", encoding="utf-8")
    _update_manifest_entry(manifest, "security_identity", path)
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_columns_invalid" in _reason_codes(parsed)
    malformed_raw = next(raw for raw in parsed.raw if raw.contract == "security_identity")
    assert parsed.raw[0] is malformed_raw
    assert malformed_raw.source_row == 2
    assert not parsed.identities
    assert all(isinstance(key, str) and isinstance(value, str) for key, value in malformed_raw.values.items())
    assert malformed_raw.values["identity_row_id"] == "id-1"
    assert malformed_raw.values["security_id"] == "sec-1"
    if extra:
        assert malformed_raw.values["__surplus_cell_0__"] == "surplus"
    else:
        assert malformed_raw.values["supersedes_identity_row_id"] == "__missing_csv_cell__"


def test_raw_evidence_preserves_manifest_relative_source_file(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    source = manifest.parent / "identity.csv"
    nested = manifest.parent / "nested" / "identity.csv"
    nested.parent.mkdir()
    source.rename(nested)
    _update_manifest_entry(manifest, "security_identity", nested)
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert parsed.raw[0].source_file == "nested/identity.csv"


def test_records_and_raw_values_are_immutable(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    with pytest.raises(FrozenInstanceError):
        parsed.identities[0].ticker = "CHANGED"
    with pytest.raises(FrozenInstanceError):
        parsed.raw[0].source_file = "changed.csv"
    with pytest.raises(TypeError):
        parsed.raw[0].values["ticker"] = "CHANGED"


def test_repeated_parsing_uses_verified_snapshots_after_paths_disappear(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    loaded = load_universe_package(manifest, registry)
    first = parse_universe_evidence(loaded)

    for path in loaded.files.values():
        path.unlink()
    registry.unlink()

    second = parse_universe_evidence(loaded)

    assert second == first


@pytest.mark.parametrize(
    "contract,start_column,end_column,reason",
    [
        (
            "security_identity",
            "valid_from",
            "valid_to",
            "schema_identity_interval_reversed",
        ),
        (
            "membership",
            "effective_from",
            "effective_to",
            "schema_membership_interval_reversed",
        ),
    ],
)
def test_reversed_intervals_become_schema_findings(
    tmp_path,
    contract,
    start_column,
    end_column,
    reason,
):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        contract,
        lambda rows: rows[0].update(
            {
                start_column: "2020-06-01T00:00:00Z",
                end_column: "2020-05-01T00:00:00Z",
            }
        ),
    )

    parsed = parse_universe_evidence(
        load_universe_package(manifest, registry)
    )

    finding = next(
        item
        for item in parsed.findings
        if reason in item.reason_codes
    )
    assert finding.contract == contract
    assert finding.source_row == 2
    assert finding.row_id in {"id-1", "member-bench-1"}
    normalized = (
        parsed.identities
        if contract == "security_identity"
        else parsed.memberships
    )
    assert all(
        getattr(
            row,
            (
                "identity_row_id"
                if contract == "security_identity"
                else "membership_row_id"
            ),
        )
        != finding.row_id
        for row in normalized
    )


@pytest.mark.parametrize("across_universes", [False, True])
def test_duplicate_evaluation_ids_are_globally_excluded(
    tmp_path,
    across_universes,
):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)

    def duplicate(rows):
        if across_universes:
            rows[1]["evaluation_row_id"] = rows[0]["evaluation_row_id"]
        else:
            rows.append(
                {
                    **rows[0],
                    "source_ref": "fixture://evaluation/bench-duplicate",
                }
            )

    _rewrite_csv_and_manifest(manifest, "evaluations", duplicate)

    parsed = parse_universe_evidence(
        load_universe_package(manifest, registry)
    )
    duplicate_findings = [
        item
        for item in parsed.findings
        if item.row_id == "eval-bench-1"
    ]

    assert len(duplicate_findings) == 2
    assert all(
        item.reason_codes
        == ("schema_evaluation_row_id_duplicate",)
        for item in duplicate_findings
    )
    assert all(
        evaluation.evaluation_row_id != "eval-bench-1"
        for evaluation in parsed.evaluations
    )


def test_same_time_evaluations_with_distinct_ids_remain_valid(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)

    parsed = parse_universe_evidence(
        load_universe_package(manifest, registry)
    )

    assert not parsed.findings
    assert {
        evaluation.evaluation_row_id
        for evaluation in parsed.evaluations
    } == {"eval-bench-1", "eval-research-1"}
    assert len({
        evaluation.evaluation_at
        for evaluation in parsed.evaluations
    }) == 1
