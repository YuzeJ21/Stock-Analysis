"""Synthetic receipt cases; no real SEC response is committed as a fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


URL = "https://www.sec.gov/files/company_tickers_exchange.json"
FIELDS = ["cik", "name", "ticker", "exchange"]


def _capture(
    root: Path,
    *,
    data: list[list[object]] | None = None,
    payload: dict[str, object] | None = None,
    map_entry: dict[str, object] | None = None,
) -> Path:
    root.mkdir()
    body = payload if payload is not None else {
        "fields": FIELDS,
        "data": data if data is not None else [
            [101, "Example A Inc.", "AAA", "NYSE"],
            [101, "Example A Inc.", "AAB", None],
        ],
    }
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    (root / "company_tickers_exchange.json").write_bytes(raw)
    entry = {
        "file": "company_tickers_exchange.json",
        "url": URL,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "last_modified": "Fri, 23 Oct 2026 21:00:38 GMT",
        "observed_at_utc": "2026-10-27T01:59:37Z",
    }
    entry.update(map_entry or {})
    manifest = {"inspection_only": True, "map": entry, "submissions": []}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _load(capture_dir: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    from src.sec_association_receipt import load_sec_association_receipt

    return load_sec_association_receipt(capture_dir)


def test_valid_receipt_keeps_each_security_search_association(tmp_path: Path) -> None:
    capture = _capture(tmp_path / "sec")
    before = {name: (capture / name).read_bytes() for name in (
        "manifest.json", "company_tickers_exchange.json",
    )}

    report, rows = _load(capture)

    assert report["url"] == URL
    assert report["sha256"] == hashlib.sha256(before["company_tickers_exchange.json"]).hexdigest()
    assert report["last_modified_at_utc"] == "2026-10-23T21:00:38Z"
    assert report["observed_at_utc"] == "2026-10-27T01:59:37Z"
    assert report["row_count"] == 2
    assert report["distinct_cik_count"] == 1
    assert report["rights_status"] == "unreviewed"
    assert report["inspection_only"] is True
    assert report["safe_to_import"] is False
    assert rows == [
        {"cik": 101, "name": "Example A Inc.", "ticker": "AAA", "exchange": "NYSE"},
        {"cik": 101, "name": "Example A Inc.", "ticker": "AAB", "exchange": ""},
    ]
    assert {name: (capture / name).read_bytes() for name in before} == before


def test_repeated_ticker_with_distinct_ciks_is_retained(tmp_path: Path) -> None:
    capture = _capture(tmp_path / "sec", data=[
        [101, "Example A Inc.", "AAA", "NYSE"],
        [202, "Example B Inc.", "AAA", "Nasdaq"],
    ])

    report, rows = _load(capture)

    assert report["row_count"] == 2
    assert report["distinct_cik_count"] == 2
    assert [(row["ticker"], row["cik"]) for row in rows] == [("AAA", 101), ("AAA", 202)]


@pytest.mark.parametrize("change", [
    {"sha256": "0" * 64},
    {"url": "https://example.test/company_tickers_exchange.json"},
    {"file": "../company_tickers_exchange.json"},
])
def test_changed_digest_or_source_identity_is_rejected(tmp_path: Path, change: dict[str, str]) -> None:
    capture = _capture(tmp_path / "sec", map_entry=change)

    with pytest.raises(ValueError):
        _load(capture)


@pytest.mark.parametrize("payload", [
    {"fields": ["ticker", "cik", "name", "exchange"], "data": [[101, "Example", "AAA", "NYSE"]]},
    {"fields": FIELDS, "data": [[101, "Example A Inc.", "AAA", "NYSE"]], "extra": 1},
    {"fields": FIELDS, "data": "not rows"},
])
def test_map_schema_must_be_exact(tmp_path: Path, payload: dict[str, object]) -> None:
    capture = _capture(tmp_path / "sec", payload=payload)

    with pytest.raises(ValueError):
        _load(capture)


@pytest.mark.parametrize("row", [
    [True, "Example A Inc.", "AAA", "NYSE"],
    [0, "Example A Inc.", "AAA", "NYSE"],
    [101, "", "AAA", "NYSE"],
    [101, "Example A Inc.", "AA A", "NYSE"],
    [101, "Example A Inc.", "AAA", 42],
    [101, "Example A Inc.", "AAA"],
])
def test_invalid_row_is_rejected(tmp_path: Path, row: list[object]) -> None:
    capture = _capture(tmp_path / "sec", data=[row])

    with pytest.raises(ValueError):
        _load(capture)


@pytest.mark.parametrize("change", [
    {"last_modified": ""},
    {"last_modified": "Fri, 23 Oct 2026 16:00:38 -0500"},
    {"last_modified": "Fri, 30 Oct 2026 21:00:38 GMT"},
    {"observed_at_utc": "2026-10-27T01:59:37"},
    {"observed_at_utc": "2026-13-27T01:59:37Z"},
])
def test_invalid_or_future_dates_are_rejected(tmp_path: Path, change: dict[str, str]) -> None:
    capture = _capture(tmp_path / "sec", map_entry=change)

    with pytest.raises(ValueError):
        _load(capture)


@pytest.mark.parametrize("target", ["manifest.json", "company_tickers_exchange.json", "capture_dir"])
def test_symlinked_inputs_are_rejected(tmp_path: Path, target: str) -> None:
    capture = _capture(tmp_path / "sec")
    if target == "capture_dir":
        alias = tmp_path / "alias"
        alias.symlink_to(capture, target_is_directory=True)
        capture = alias
    else:
        original = capture / target
        moved = capture / f"{target}.moved"
        original.rename(moved)
        original.symlink_to(moved)

    with pytest.raises(ValueError):
        _load(capture)


def test_oversized_map_is_rejected_before_parsing(tmp_path: Path) -> None:
    capture = _capture(tmp_path / "sec")
    with (capture / "company_tickers_exchange.json").open("wb") as stream:
        stream.truncate(16 * 1024 * 1024)

    with pytest.raises(ValueError):
        _load(capture)


def test_duplicate_json_object_keys_are_rejected(tmp_path: Path) -> None:
    capture = _capture(tmp_path / "sec")
    raw = b'{"fields":["cik","name","ticker","exchange"],"data":[],"data":[]}'
    (capture / "company_tickers_exchange.json").write_bytes(raw)
    manifest = json.loads((capture / "manifest.json").read_text())
    manifest["map"]["sha256"] = hashlib.sha256(raw).hexdigest()
    (capture / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError):
        _load(capture)
