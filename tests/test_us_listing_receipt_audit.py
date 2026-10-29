"""Synthetic checks for dated, read-only U.S. listing receipt inspection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.us_listing_receipt_audit import build_us_listing_receipt_audit, main


NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
NASDAQ_HEADER = "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares"
OTHER_HEADER = "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol"
FOOTER = "File Creation Time: 0101202512:00"


def _snapshot(tmp_path: Path) -> Path:
    directory = tmp_path / "snapshot"
    directory.mkdir(parents=True)
    files = {
        "nasdaqlisted.txt": (
            NASDAQ_HEADER + "\n"
            + "FICTA|Fictional Alpha Common Stock|Q|N|N|100|N|N\n"
            + "FICTT|Fictional Test Security|Q|Y|N|100|N|N\n"
            + FOOTER + "|||||||\n"
        ),
        "otherlisted.txt": (
            OTHER_HEADER + "\n"
            + "FICTB|Fictional Beta Common Stock|N|FICTB|N|100|N|FICTB\n"
            + "FICTU|Fictional Test Security|N|FICTU|N|100|Y|FICTU\n"
            + FOOTER + "||||||\n"
        ),
    }
    sources = []
    for name, source, url in (
        ("nasdaqlisted.txt", "nasdaq", NASDAQ_URL),
        ("otherlisted.txt", "other", OTHER_URL),
    ):
        raw = files[name].encode()
        (directory / name).write_bytes(raw)
        sources.append(
            {
                "source": source,
                "url": url,
                "file": name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_created_at": "2025-01-01T12:00",
                "last_modified": "Wed, 01 Jan 2025 17:00:00 GMT",
                "observed_at_utc": "2025-01-01T17:01:00Z",
                "rows_excluding_test_issues": 1,
                "excluded_test_issues": 1,
            }
        )
    (directory / "manifest.json").write_text(json.dumps({"inspection_only": True, "sources": sources}))
    return directory


def _change_manifest(directory: Path, edit) -> None:
    path = directory / "manifest.json"
    payload = json.loads(path.read_text())
    edit(payload)
    path.write_text(json.dumps(payload))


def _change_file(directory: Path, name: str, text: str) -> None:
    (directory / name).write_text(text)
    _change_manifest(
        directory,
        lambda payload: next(item for item in payload["sources"] if item["file"] == name).update(
            sha256=hashlib.sha256(text.encode()).hexdigest()
        ),
    )


def test_matching_pair_reports_aggregate_counts_and_keeps_import_held(tmp_path: Path) -> None:
    result = build_us_listing_receipt_audit(_snapshot(tmp_path))

    assert result["status"] == "validated_receipts"
    assert result["inspection_only"] is True
    assert result["import_status"] == "held"
    assert result["rights_status"] == "unreviewed"
    assert result["source_created_at"] == "2025-01-01T12:00"
    assert result["total_non_test_symbols"] == 2
    assert result["excluded_test_issues"] == 2
    assert [(entry["source"], entry["rows_excluding_test_issues"]) for entry in result["sources"]] == [
        ("nasdaq", 1), ("other", 1)
    ]
    assert "FICTA" not in json.dumps(result)
    assert "FICTB" not in json.dumps(result)


def test_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    (directory / "nasdaqlisted.txt").write_text("altered")

    with pytest.raises(ValueError, match="digest_mismatch"):
        build_us_listing_receipt_audit(directory)


def test_manifest_source_identity_and_traversal_fail_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    _change_manifest(directory, lambda payload: payload["sources"][0].update(file="../nasdaqlisted.txt"))

    with pytest.raises(ValueError, match="source_identity_invalid"):
        build_us_listing_receipt_audit(directory)


def test_malformed_manifest_source_type_fails_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    _change_manifest(directory, lambda payload: payload["sources"][0].update(source=["nasdaq"]))

    with pytest.raises(ValueError, match="source_identity_invalid"):
        build_us_listing_receipt_audit(directory)


def test_bad_or_mismatched_dates_fail_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    _change_manifest(directory, lambda payload: payload["sources"][0].update(source_created_at="2025-02-30T12:00"))
    with pytest.raises(ValueError, match="date_invalid"):
        build_us_listing_receipt_audit(directory)

    directory = _snapshot(tmp_path / "second")
    _change_manifest(directory, lambda payload: payload["sources"][0].update(source_created_at="2025-01-01T12:01"))
    with pytest.raises(ValueError, match="creation_time_mismatch"):
        build_us_listing_receipt_audit(directory)


def test_unknown_source_timezone_allows_next_calendar_day_footer(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    for name in ("nasdaqlisted.txt", "otherlisted.txt"):
        text = (directory / name).read_text().replace(
            "File Creation Time: 0101202512:00", "File Creation Time: 0102202500:30"
        )
        _change_file(directory, name, text)
    _change_manifest(
        directory,
        lambda payload: [item.update(source_created_at="2025-01-02T00:30") for item in payload["sources"]],
    )

    result = build_us_listing_receipt_audit(directory)
    assert result["status"] == "validated_receipts"
    assert result["source_created_at"] == "2025-01-02T00:30"
    assert result["observed_at_utc"] == "2025-01-01T17:01:00Z"
    assert result["source_time_zone"] == "not specified by directory"


def test_missing_required_column_fails_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    text = (directory / "nasdaqlisted.txt").read_text().replace("|Test Issue", "|Testing Flag")
    _change_file(directory, "nasdaqlisted.txt", text)

    with pytest.raises(ValueError, match="schema_invalid"):
        build_us_listing_receipt_audit(directory)


def test_unknown_venue_fails_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    text = (directory / "otherlisted.txt").read_text().replace("|N|FICTB|N|100|N|", "|X|FICTB|N|100|N|")
    _change_file(directory, "otherlisted.txt", text)

    with pytest.raises(ValueError, match="exchange_code_unrecognized"):
        build_us_listing_receipt_audit(directory)


@pytest.mark.parametrize(
    ("field", "invalid", "reason"),
    [
        ("Market Category", "X", "market_category_invalid"),
        ("Financial Status", "Z", "financial_status_invalid"),
        ("NextShares", "X", "nextshares_flag_invalid"),
    ],
)
def test_invalid_nasdaq_directory_code_fails_closed(
    tmp_path: Path, field: str, invalid: str, reason: str
) -> None:
    directory = _snapshot(tmp_path)
    original = "FICTA|Fictional Alpha Common Stock|Q|N|N|100|N|N"
    values = original.split("|")
    values[NASDAQ_HEADER.split("|").index(field)] = invalid
    text = (directory / "nasdaqlisted.txt").read_text().replace(original, "|".join(values))
    _change_file(directory, "nasdaqlisted.txt", text)

    with pytest.raises(ValueError, match=reason):
        build_us_listing_receipt_audit(directory)


@pytest.mark.parametrize("name", ["nasdaqlisted.txt", "otherlisted.txt"])
@pytest.mark.parametrize("invalid", ["0", "1000000", "1.5"])
def test_invalid_round_lot_size_fails_closed(tmp_path: Path, name: str, invalid: str) -> None:
    directory = _snapshot(tmp_path)
    header = NASDAQ_HEADER if name == "nasdaqlisted.txt" else OTHER_HEADER
    original = (
        "FICTA|Fictional Alpha Common Stock|Q|N|N|100|N|N"
        if name == "nasdaqlisted.txt"
        else "FICTB|Fictional Beta Common Stock|N|FICTB|N|100|N|FICTB"
    )
    values = original.split("|")
    values[header.split("|").index("Round Lot Size")] = invalid
    text = (directory / name).read_text().replace(original, "|".join(values))
    _change_file(directory, name, text)

    with pytest.raises(ValueError, match="round_lot_size_invalid"):
        build_us_listing_receipt_audit(directory)


def test_duplicate_symbol_across_pair_fails_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    text = (directory / "otherlisted.txt").read_text().replace("FICTB", "FICTA")
    _change_file(directory, "otherlisted.txt", text)

    with pytest.raises(ValueError, match="symbol_duplicate"):
        build_us_listing_receipt_audit(directory)


def test_test_issues_are_excluded_before_symbol_uniqueness(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    text = (directory / "otherlisted.txt").read_text().replace("FICTU", "FICTA")
    _change_file(directory, "otherlisted.txt", text)

    result = build_us_listing_receipt_audit(directory)
    assert result["total_non_test_symbols"] == 2
    assert result["excluded_test_issues"] == 2


def test_symlinked_receipt_fails_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path)
    path = directory / "otherlisted.txt"
    target = tmp_path / "outside.txt"
    target.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(target)

    with pytest.raises(ValueError, match="source_file_invalid"):
        build_us_listing_receipt_audit(directory)


def test_symlinked_snapshot_ancestor_fails_closed(tmp_path: Path) -> None:
    directory = _snapshot(tmp_path / "real")
    alias = tmp_path / "alias"
    alias.symlink_to(directory.parent, target_is_directory=True)

    with pytest.raises(ValueError, match="snapshot_dir_invalid"):
        build_us_listing_receipt_audit(alias / "snapshot")


def test_cli_exit_codes_and_json_output(tmp_path: Path, capsys, monkeypatch) -> None:
    directory = _snapshot(tmp_path)
    monkeypatch.setattr("sys.argv", ["audit", "--snapshot-dir", str(directory)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["import_status"] == "held"

    (directory / "manifest.json").unlink()
    assert main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
