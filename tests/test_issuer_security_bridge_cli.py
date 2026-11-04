"""End-to-end synthetic receipt checks for the read-only bridge command."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
SEC_URL = "https://www.sec.gov/files/company_tickers_exchange.json"


def _directory_capture(root: Path) -> Path:
    root.mkdir()
    files = {
        "nasdaqlisted.txt": (
            "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
            "FICTA|Fictional Alpha Common Stock|Q|N|N|100|N|N\n"
            "FICTT|Fictional Test Security|Q|Y|N|100|N|N\n"
            "File Creation Time: 0101202512:00|||||||\n"
        ),
        "otherlisted.txt": (
            "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
            "FICTB|Fictional Beta Common Stock|N|FICTB|N|100|N|FICTB\n"
            "FICTU|Fictional Test Security|N|FICTU|N|100|Y|FICTU\n"
            "File Creation Time: 0101202512:00||||||\n"
        ),
    }
    sources = []
    for source, filename, url in (
        ("nasdaq", "nasdaqlisted.txt", NASDAQ_URL),
        ("other", "otherlisted.txt", OTHER_URL),
    ):
        raw = files[filename].encode()
        (root / filename).write_bytes(raw)
        sources.append({
            "source": source,
            "file": filename,
            "url": url,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_created_at": "2025-01-01T12:00",
            "last_modified": "Wed, 01 Jan 2025 17:00:00 GMT",
            "observed_at_utc": "2025-01-01T17:01:00Z",
            "rows_excluding_test_issues": 1,
            "excluded_test_issues": 1,
        })
    (root / "manifest.json").write_text(json.dumps({"inspection_only": True, "sources": sources}))
    return root


def _sec_capture(root: Path, *, last_modified: str = "Wed, 01 Jan 2025 16:00:00 GMT") -> Path:
    root.mkdir()
    raw = json.dumps({
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [[1001, "Fictional Alpha Inc.", "FICTA", "Nasdaq"]],
    }).encode()
    (root / "company_tickers_exchange.json").write_bytes(raw)
    (root / "manifest.json").write_text(json.dumps({
        "inspection_only": True,
        "map": {
            "file": "company_tickers_exchange.json",
            "url": SEC_URL,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "last_modified": last_modified,
            "observed_at_utc": "2025-01-01T17:01:00Z",
        },
        "submissions": [],
    }))
    return root


def _run(directory: Path, sec: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, "-m", "src.issuer_security_bridge",
            "--directory-snapshot", str(directory),
            "--sec-capture", str(sec),
            "--top-n", "1",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )


def _bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


def test_cli_compares_synthetic_same_date_receipts_without_writing(tmp_path: Path):
    directory = _directory_capture(tmp_path / "directory")
    sec = _sec_capture(tmp_path / "sec")
    before = _bytes(tmp_path)

    run = _run(directory, sec)
    report = json.loads(run.stdout)

    assert run.returncode == 0
    assert run.stderr == ""
    assert report["status"] == "same_date_inspection"
    assert report["comparison_counts"]["exact_act_leads"] == 1
    assert report["comparison_counts"]["directory_rows_without_sec_lead"] == 1
    assert report["inputs"]["directory_excluded_test_issues"] == 2
    assert report["safe_to_import"] is False
    assert "Fictional Alpha Inc." not in run.stdout
    assert _bytes(tmp_path) == before


def test_cli_reports_cutoff_mismatch_as_blocked_result(tmp_path: Path):
    directory = _directory_capture(tmp_path / "directory")
    sec = _sec_capture(
        tmp_path / "sec", last_modified="Mon, 30 Dec 2024 16:00:00 GMT"
    )

    run = _run(directory, sec)
    report = json.loads(run.stdout)

    assert run.returncode == 2
    assert report["status"] == "cutoff_mismatch"
    assert report["comparison_performed"] is False
    assert report["comparison_counts"] is None
    assert report["review_queue"] == []
    assert report["source_alignment"]["directory_date"] == "2025-01-01"
    assert report["source_alignment"]["sec_date"] == "2024-12-30"


def test_cli_rejects_changed_sec_bytes_without_emitting_source_rows(tmp_path: Path):
    directory = _directory_capture(tmp_path / "directory")
    sec = _sec_capture(tmp_path / "sec")
    (sec / "company_tickers_exchange.json").write_bytes(b"changed")

    run = _run(directory, sec)
    report = json.loads(run.stdout)

    assert run.returncode == 2
    assert report["status"] == "invalid"
    assert report["safe_to_import"] is False
    assert "FICTA" not in run.stdout
    assert "Traceback" not in run.stderr
