"""Synthetic, read-only checks for the held release baseline audit."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_COLUMNS = (
    "path",
    "sha256",
    "bytes",
    "csv_rows",
    "content_class",
    "source_content",
    "rights_status",
    "referenced_by",
)
DISPOSITION_COLUMNS = (
    "path",
    "sha256",
    "inherited_rights_status",
    "local_disposition",
    "decision_gap",
)
REVIEWED_HISTORY_COLUMNS = ("path", "blob_oid", "review_class", "review_note")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


def _write_tsv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _base_files(tmp_path: Path, *, extra_tracked: bool = False) -> tuple[Path, Path, Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "data").mkdir()
    (root / "data/universe_master.csv").write_text(
        "ticker,source\nTEST,synthetic\n", encoding="utf-8"
    )
    (root / "config").mkdir()
    (root / "config/source_rights.yml").write_text("sources: []\n", encoding="utf-8")
    if extra_tracked:
        (root / "data/extra.csv").write_text("ticker\nEXTRA\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Synthetic Test")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "add", "data", "config/source_rights.yml")
    _git(root, "commit", "-qm", "Synthetic baseline")
    base = _git(root, "rev-parse", "HEAD")
    inventory = tmp_path / "inventory.tsv"
    disposition = tmp_path / "disposition.tsv"
    source = (root / "data/universe_master.csv").read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    _write_tsv(
        inventory,
        INVENTORY_COLUMNS,
        [
            {
                "path": "data/universe_master.csv",
                "sha256": digest,
                "bytes": str(len(source)),
                "csv_rows": "1",
                "content_class": "canonical_identity_or_derived",
                "source_content": "synthetic",
                "rights_status": "unreviewed_source_scope",
                "referenced_by": "-",
            }
        ],
    )
    _write_tsv(
        disposition,
        DISPOSITION_COLUMNS,
        [
            {
                "path": "data/universe_master.csv",
                "sha256": digest,
                "inherited_rights_status": "unreviewed_source_scope",
                "local_disposition": "hold_for_exact_source_rights",
                "decision_gap": "source_channel_field_date_storage_display_redistribution",
            }
        ],
    )
    _write_tsv(tmp_path / "reviewed_history.tsv", REVIEWED_HISTORY_COLUMNS, [])
    return root, inventory, disposition, base


def _audit(root: Path, inventory: Path, disposition: Path, base: str) -> dict[str, object]:
    from src.release_baseline_audit import build_release_baseline_audit

    return build_release_baseline_audit(
        root, inventory, disposition, base, root.parent / "reviewed_history.tsv"
    )


def _review_history(root: Path, rows: list[dict[str, str]]) -> None:
    _write_tsv(root.parent / "reviewed_history.tsv", REVIEWED_HISTORY_COLUMNS, rows)


def _codes(payload: dict[str, object]) -> set[str]:
    return {str(item["code"]) for item in payload["failures"]}


def test_matching_baseline_is_integrity_verified_but_distribution_held(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "verified"
    assert result["distribution_status"] == "held"
    assert result["path_count"] == 1
    assert result["hold_counts"] == {"hold_for_exact_source_rights": 1}
    assert result["sensitive_history_paths"] == []
    assert result["failures"] == []


def test_changed_file_hash_fails_integrity(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    (root / "data/universe_master.csv").write_text(
        "ticker,source\nCHANGED,synthetic\n", encoding="utf-8"
    )

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "hash_mismatch" in _codes(result)
    assert result["distribution_status"] == "held"


def test_staged_sensitive_change_fails_even_when_worktree_bytes_match_inventory(
    tmp_path: Path,
) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    target = root / "data/universe_master.csv"
    original = target.read_bytes()
    target.write_text("ticker,source\nSTAGED,synthetic\n", encoding="utf-8")
    _git(root, "add", "data/universe_master.csv")
    target.write_bytes(original)

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "staged_sensitive_change" in _codes(result)
    assert result["staged_sensitive_paths"] == ["data/universe_master.csv"]


def test_tracked_path_set_drift_fails_integrity(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path, extra_tracked=True)

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "tracked_path_set_mismatch" in _codes(result)


def test_non_ascii_numeric_manifest_count_returns_failed_verdict(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    with inventory.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    rows[0]["bytes"] = "²"
    _write_tsv(inventory, INVENTORY_COLUMNS, rows)

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "invalid_inventory_counts" in _codes(result)


def test_duplicate_inventory_path_fails_integrity(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    lines = inventory.read_text(encoding="utf-8").splitlines()
    inventory.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")

    result = _audit(root, inventory, disposition, base)

    assert "duplicate_inventory_path" in _codes(result)


def test_traversing_inventory_path_is_rejected_before_reading_file(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    lines = inventory.read_text(encoding="utf-8").splitlines()
    traversal = lines[1].replace("data/universe_master.csv", "data/../../outside.csv")
    inventory.write_text("\n".join([lines[0], traversal]) + "\n", encoding="utf-8")

    result = _audit(root, inventory, disposition, base)

    assert "invalid_inventory_path" in _codes(result)
    assert "hash_mismatch" not in _codes(result)


@pytest.mark.parametrize(
    ("field", "replacement", "expected_code"),
    [
        ("sha256", "0" * 64, "disposition_mismatch"),
        ("inherited_rights_status", "no_source_payload", "disposition_mismatch"),
        ("local_disposition", "approved", "invalid_disposition"),
    ],
)
def test_disposition_mismatch_or_approval_claim_fails_closed(
    tmp_path: Path, field: str, replacement: str, expected_code: str
) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    with disposition.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    rows[0][field] = replacement
    _write_tsv(disposition, DISPOSITION_COLUMNS, rows)

    result = _audit(root, inventory, disposition, base)

    assert expected_code in _codes(result)
    assert result["distribution_status"] == "held"


def test_missing_disposition_row_fails_integrity(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    _write_tsv(disposition, DISPOSITION_COLUMNS, [])

    result = _audit(root, inventory, disposition, base)

    assert "disposition_path_set_mismatch" in _codes(result)


def test_added_then_deleted_sensitive_blob_remains_detected(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    sensitive = root / "outputs/private_capture.csv"
    sensitive.parent.mkdir()
    sensitive.write_text("synthetic,value\n", encoding="utf-8")
    _git(root, "add", "outputs/private_capture.csv")
    _git(root, "commit", "-qm", "Add synthetic capture")
    _git(root, "rm", "-q", "outputs/private_capture.csv")
    _git(root, "commit", "-qm", "Remove synthetic capture")

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "sensitive_history" in _codes(result)
    assert result["sensitive_history_paths"] == ["outputs/private_capture.csv"]


def test_added_then_deleted_docs_internal_capture_is_unreviewed_history(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    capture = root / "docs/internal/raw_sec_capture.json"
    capture.parent.mkdir(parents=True)
    capture.write_text('{"synthetic_source_payload": true}\n', encoding="utf-8")
    _git(root, "add", "docs/internal/raw_sec_capture.json")
    _git(root, "commit", "-qm", "Add synthetic capture")
    _git(root, "rm", "-q", "docs/internal/raw_sec_capture.json")
    _git(root, "commit", "-qm", "Remove synthetic capture")

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "reviewed_history_mismatch" in _codes(result)
    assert "docs/internal/raw_sec_capture.json" in result["unreviewed_history_paths"]


def test_copied_inherited_blob_then_deleted_still_requires_history_review(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    copied = root / "docs/internal/raw_copy.json"
    copied.parent.mkdir(parents=True)
    copied.write_bytes((root / "data/universe_master.csv").read_bytes())
    _git(root, "add", "docs/internal/raw_copy.json")
    _git(root, "commit", "-qm", "Copy inherited bytes into source capture path")
    _git(root, "rm", "-q", "docs/internal/raw_copy.json")
    _git(root, "commit", "-qm", "Remove copied bytes")

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "reviewed_history_mismatch" in _codes(result)
    assert "docs/internal/raw_copy.json" in result["unreviewed_history_paths"]


def test_unlisted_new_code_blob_fails_integrity(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    code = root / "src/example.py"
    code.parent.mkdir()
    code.write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "src/example.py")
    _git(root, "commit", "-qm", "Add reviewed-scope code")

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert "reviewed_history_mismatch" in _codes(result)
    assert result["unreviewed_history_paths"] == ["src/example.py"]


def test_matching_reviewed_code_blob_verifies_integrity_but_holds_distribution(
    tmp_path: Path,
) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    code = root / "src/example.py"
    code.parent.mkdir()
    code.write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "src/example.py")
    _git(root, "commit", "-qm", "Add reviewed-scope code")
    oid = _git(root, "rev-parse", "HEAD:src/example.py")
    _review_history(
        root,
        [
            {
                "path": "src/example.py",
                "blob_oid": oid,
                "review_class": "code",
                "review_note": "synthetic module reviewed for source material",
            }
        ],
    )

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "verified"
    assert result["distribution_status"] == "held"
    assert result["reviewed_history_tuple_count"] == 1
    assert result["unreviewed_history_paths"] == []


@pytest.mark.parametrize(
    ("field", "replacement", "expected_code"),
    [
        ("path", "src/../example.py", "invalid_reviewed_history_path"),
        ("blob_oid", "not-an-oid", "invalid_reviewed_history_oid"),
        ("review_class", "approved", "invalid_review_class"),
    ],
)
def test_malformed_history_manifest_fails_closed(
    tmp_path: Path, field: str, replacement: str, expected_code: str
) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    code = root / "src/example.py"
    code.parent.mkdir()
    code.write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "src/example.py")
    _git(root, "commit", "-qm", "Add reviewed-scope code")
    row = {
        "path": "src/example.py",
        "blob_oid": _git(root, "rev-parse", "HEAD:src/example.py"),
        "review_class": "code",
        "review_note": "source reviewed",
    }
    row[field] = replacement
    _review_history(root, [row])

    result = _audit(root, inventory, disposition, base)

    assert result["integrity_status"] == "failed"
    assert expected_code in _codes(result)


def test_reviewed_history_extra_blob_tuple_fails(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    _review_history(
        root,
        [
            {
                "path": "src/never_committed.py",
                "blob_oid": "1" * 40,
                "review_class": "code",
                "review_note": "unmatched row",
            }
        ],
    )

    result = _audit(root, inventory, disposition, base)

    assert "reviewed_history_mismatch" in _codes(result)


def test_misclassified_docs_internal_json_is_not_neutral_docs(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    capture = root / "docs/internal/raw_sec_capture.json"
    capture.parent.mkdir(parents=True)
    capture.write_text('{"synthetic_source_payload": true}\n', encoding="utf-8")
    _git(root, "add", "docs/internal/raw_sec_capture.json")
    _git(root, "commit", "-qm", "Add synthetic capture")
    _review_history(
        root,
        [
            {
                "path": "docs/internal/raw_sec_capture.json",
                "blob_oid": _git(root, "rev-parse", "HEAD:docs/internal/raw_sec_capture.json"),
                "review_class": "neutral_docs",
                "review_note": "misclassified source capture",
            }
        ],
    )

    result = _audit(root, inventory, disposition, base)

    assert "review_class_path_mismatch" in _codes(result)


def test_dirty_rights_registry_fails_even_with_valid_history_manifest(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    (root / "config/source_rights.yml").write_text("sources: [changed]\n", encoding="utf-8")

    result = _audit(root, inventory, disposition, base)

    assert "rights_registry_dirty" in _codes(result)


def test_committed_rights_registry_change_fails_even_if_reviewed(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    (root / "config/source_rights.yml").write_text("sources: [changed]\n", encoding="utf-8")
    _git(root, "add", "config/source_rights.yml")
    _git(root, "commit", "-qm", "Change rights registry")
    _review_history(
        root,
        [
            {
                "path": "config/source_rights.yml",
                "blob_oid": _git(root, "rev-parse", "HEAD:config/source_rights.yml"),
                "review_class": "code",
                "review_note": "registry change reviewed but not permitted",
            }
        ],
    )

    result = _audit(root, inventory, disposition, base)

    assert "rights_registry_history" in _codes(result)


def test_symlinked_baseline_file_is_rejected(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    original = root / "data/universe_master.csv"
    moved = root / "data/original.csv"
    original.rename(moved)
    original.symlink_to(moved)

    result = _audit(root, inventory, disposition, base)

    assert "symlink_path" in _codes(result)


def test_symlinked_manifest_parent_is_rejected(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    actual_dir = tmp_path / "manifest_store"
    actual_dir.mkdir()
    moved_inventory = actual_dir / inventory.name
    inventory.rename(moved_inventory)
    linked_dir = tmp_path / "linked_manifests"
    linked_dir.symlink_to(actual_dir, target_is_directory=True)

    result = _audit(root, linked_dir / inventory.name, disposition, base)

    assert "symlink_manifest" in _codes(result)


def test_cli_exits_zero_only_for_verified_integrity_with_hold(tmp_path: Path) -> None:
    root, inventory, disposition, base = _base_files(tmp_path)
    command = [
        sys.executable,
        "-m",
        "src.release_baseline_audit",
        "--repo-root",
        str(root),
        "--inventory",
        str(inventory),
        "--disposition",
        str(disposition),
        "--reviewed-history",
        str(root.parent / "reviewed_history.tsv"),
        "--base-ref",
        base,
    ]

    valid = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    assert valid.returncode == 0
    assert json.loads(valid.stdout)["distribution_status"] == "held"

    (root / "data/universe_master.csv").write_text("ticker\nBAD\n", encoding="utf-8")
    invalid = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["integrity_status"] == "failed"
