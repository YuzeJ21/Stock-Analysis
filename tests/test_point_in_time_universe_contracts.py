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
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_columns_invalid" in _reason_codes(parsed)


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
    assert all(raw.contract != "security_identity" for raw in parsed.raw)


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
