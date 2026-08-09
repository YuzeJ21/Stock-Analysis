from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src import readiness_release_review as release


EXPECTED_CANDIDATE_PATHS = (
    "data/analyst_estimates_readiness.csv",
    "data/dcf_readiness.csv",
    "data/earnings_readiness.csv",
    "data/price_coverage_report.csv",
    "data/reports/analyst_estimates_readiness_report.csv",
    "data/reports/data_source_status.csv",
    "data/reports/dcf_readiness_report.csv",
    "data/reports/earnings_readiness_report.csv",
    "data/reports/feature_readiness_summary.csv",
    "data/reports/fundamentals_coverage_report.csv",
    "data/reports/peer_readiness_report.csv",
    "data/reports/peer_unlock_worklist.csv",
    "data/reports/price_coverage_report.csv",
    "data/reports/ticker_readiness_report.csv",
    "data/reports/universe_coverage_report.csv",
    "data/universe_master.csv",
    "outputs/feature_readiness_summary.csv",
    "outputs/peer_unlock_worklist.csv",
)


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _write(root: Path, relative: str, payload: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _release_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "tests@example.com")
    _run_git(root, "config", "user.name", "Release Tests")
    for relative in EXPECTED_CANDIDATE_PATHS:
        _write(root, relative, "ticker,status\nAAA,head\n")
    for relative in release.READINESS_SOURCE_PATHS:
        _write(root, relative, "ticker,value\nAAA,1\n")
    _write(root, release.RIGHTS_REGISTRY_PATH, "sources: []\n")
    for relative in release.PROOF_LEDGER_PATHS:
        _write(root, relative, "id,status\nproof-1,reviewed\n")
    _run_git(root, "add", "--", ".")
    _run_git(root, "commit", "-qm", "seed release fixture")
    for relative in EXPECTED_CANDIDATE_PATHS:
        _write(root, relative, "ticker,status\nAAA,working\n")
    return root


def test_candidate_manifest_is_exact_ordered_and_digest_is_deterministic(tmp_path: Path):
    root = _release_repo(tmp_path)

    first = release.build_release_review(root, top_n=1)
    second = release.build_release_review(root, top_n=50)

    assert tuple(item.path for item in first.candidate_paths) == EXPECTED_CANDIDATE_PATHS
    assert first.candidate_manifest_digest == second.candidate_manifest_digest
    assert first.preview_receipt == second.preview_receipt
    assert len(first.preview_receipt) == 64


def test_review_rejects_unexpected_modified_and_staged_paths(tmp_path: Path):
    root = _release_repo(tmp_path)
    _write(root, "data/reports/unexpected.csv", "value\n1\n")
    _run_git(root, "add", "--", "data/reports/unexpected.csv")

    packet = release.build_release_review(root)

    assert "unexpected_changed_path:data/reports/unexpected.csv" in packet.blockers
    assert "staged_path:data/reports/unexpected.csv" in packet.blockers
    assert packet.axis("staging_hygiene_review").status == "blocked"


def test_review_rejects_a_staged_candidate_without_changing_its_digest(tmp_path: Path):
    root = _release_repo(tmp_path)
    path = EXPECTED_CANDIDATE_PATHS[0]
    before = release.build_release_review(root).candidate_paths[0].working_sha256
    _run_git(root, "add", "--", path)

    packet = release.build_release_review(root)

    assert f"staged_path:{path}" in packet.blockers
    assert packet.candidate_paths[0].working_sha256 == before


def test_canonical_receipt_is_key_order_independent_and_value_sensitive():
    first = release.canonical_receipt({"b": [2, 3], "a": {"x": True}})
    reordered = release.canonical_receipt({"a": {"x": True}, "b": [2, 3]})
    changed = release.canonical_receipt({"a": {"x": False}, "b": [2, 3]})

    assert first == reordered
    assert changed != first


def test_review_rejects_candidate_symlink(tmp_path: Path):
    root = _release_repo(tmp_path)
    relative = EXPECTED_CANDIDATE_PATHS[0]
    target = root / "target.csv"
    target.write_text("ticker,status\nAAA,working\n", encoding="utf-8")
    (root / relative).unlink()
    (root / relative).symlink_to(target)

    with pytest.raises(release.ReleaseReviewError, match=f"symlink_rejected:{relative}"):
        release.build_release_review(root)


def test_review_rejects_oversized_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _release_repo(tmp_path)
    relative = EXPECTED_CANDIDATE_PATHS[0]
    monkeypatch.setattr(release, "MAX_EVIDENCE_FILE_BYTES", 64)
    _write(root, relative, "ticker,status\nAAA," + ("x" * 80) + "\n")

    with pytest.raises(release.ReleaseReviewError, match=f"file_too_large:{relative}"):
        release.build_release_review(root)


def test_review_rejects_candidate_over_row_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _release_repo(tmp_path)
    relative = EXPECTED_CANDIDATE_PATHS[0]
    monkeypatch.setattr(release, "MAX_EVIDENCE_CSV_ROWS", 2)
    _write(root, relative, "ticker,status\nAAA,one\nBBB,two\nCCC,three\n")

    with pytest.raises(release.ReleaseReviewError, match=f"csv_row_limit_exceeded:{relative}"):
        release.build_release_review(root)


def test_review_rejects_duplicate_columns_and_duplicate_tickers(tmp_path: Path):
    duplicate_columns = _release_repo(tmp_path / "columns")
    relative = EXPECTED_CANDIDATE_PATHS[0]
    _write(duplicate_columns, relative, "ticker,ticker\nAAA,AAA\n")

    with pytest.raises(release.ReleaseReviewError, match=f"duplicate_csv_column:{relative}:ticker"):
        release.build_release_review(duplicate_columns)

    duplicate_tickers = _release_repo(tmp_path / "tickers")
    _write(duplicate_tickers, relative, "ticker,status\nAAA,one\nAAA,two\n")

    with pytest.raises(release.ReleaseReviewError, match=f"duplicate_ticker:{relative}:AAA"):
        release.build_release_review(duplicate_tickers)
