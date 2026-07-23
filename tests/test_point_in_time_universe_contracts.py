import csv
import hashlib
import json

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

    assert reason in {code for finding in parsed.findings for code in finding.reason_codes}


def test_split_requires_both_positive_ratio_values(tmp_path):
    from src.point_in_time_universe_contracts import parse_universe_evidence
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        rows[0].update(event_type="split", ratio_numerator="2", ratio_denominator="")

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))

    assert "schema_ratio_pair_required" in {code for finding in parsed.findings for code in finding.reason_codes}


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

    assert "schema_columns_invalid" in {code for finding in parsed.findings for code in finding.reason_codes}
