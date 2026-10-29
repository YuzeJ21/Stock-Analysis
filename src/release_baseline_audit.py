"""Read-only integrity audit for a held repository release baseline.

An intact inventory is evidence about bytes and Git history, not permission to
redistribute any inherited source material.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath


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
REVIEW_CLASSES = {"code", "neutral_docs", "test_code"}
CONSERVATIVE_DISPOSITIONS = {
    "no_source_payload": "retain_candidate_pending_code_review",
    "unreviewed_source_scope": "hold_for_exact_source_rights",
    "mixed_or_unreviewed_source_scope": "hold_for_component_rights",
    "inherits_unreviewed_upstream": "hold_for_upstream_review_or_synthetic_replacement",
    "internal_content_review": "hold_for_owner_content_review",
}
SENSITIVE_PATHS = ("data", "outputs", "docs/assets", "config/source_rights.yml")
MAX_DETAIL = 20


def _failure(failures: list[dict[str, object]], code: str, **details: object) -> None:
    failures.append({"code": code, **details})


def _is_inventory_path(value: str) -> bool:
    if not _is_repo_path(value):
        return False
    return value.startswith(("data/", "outputs/", "docs/assets/"))


def _is_repo_path(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        return False
    if "\n" in value or "\r" in value:
        return False
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return PurePosixPath(value).as_posix() == value


def _review_class_matches_path(review_class: str, path: str) -> bool:
    if review_class == "code":
        return path == "Makefile" or path.startswith("src/") and path.endswith(".py")
    if review_class == "neutral_docs":
        return path.endswith(".md") and (
            path.startswith("docs/") or path in {"README.md", "ROADMAP.md"}
        )
    if review_class == "test_code":
        return path.startswith("tests/") and path.endswith(".py")
    return False


def _has_symlink_component(path: Path) -> bool:
    current = path.absolute()
    while True:
        if current.is_symlink():
            return True
        if current.parent == current:
            return False
        current = current.parent


def _read_tsv(
    path: Path,
    columns: tuple[str, ...],
    kind: str,
    failures: list[dict[str, object]],
) -> list[dict[str, str]]:
    if _has_symlink_component(path):
        _failure(failures, "symlink_manifest", kind=kind)
        return []
    if not path.is_file():
        _failure(failures, "missing_manifest", kind=kind)
        return []
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream, delimiter="\t", strict=True)
            header = next(reader, None)
            if tuple(header or ()) != columns:
                _failure(failures, "invalid_manifest_schema", kind=kind)
                return []
            rows: list[dict[str, str]] = []
            for line_number, fields in enumerate(reader, start=2):
                if len(fields) != len(columns):
                    _failure(
                        failures,
                        "invalid_manifest_row",
                        kind=kind,
                        line=line_number,
                    )
                    continue
                rows.append(dict(zip(columns, fields, strict=True)))
            return rows
    except (OSError, UnicodeError, csv.Error):
        _failure(failures, "unreadable_manifest", kind=kind)
        return []


def _validated_rows(
    rows: list[dict[str, str]], kind: str, failures: list[dict[str, object]]
) -> dict[str, dict[str, str]]:
    validated: dict[str, dict[str, str]] = {}
    for line_number, row in enumerate(rows, start=2):
        value = row["path"]
        if not _is_inventory_path(value):
            _failure(failures, f"invalid_{kind}_path", line=line_number)
            continue
        if value in validated:
            _failure(failures, f"duplicate_{kind}_path", path=value)
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            _failure(failures, "invalid_hash", kind=kind, path=value)
            continue
        if kind == "inventory":
            if not re.fullmatch(r"[0-9]+", row["bytes"]) or (
                row["csv_rows"] and not re.fullmatch(r"[0-9]+", row["csv_rows"])
            ):
                _failure(failures, "invalid_inventory_counts", path=value)
                continue
            if any(
                not row[field]
                for field in ("content_class", "source_content", "rights_status", "referenced_by")
            ) or row["rights_status"] not in CONSERVATIVE_DISPOSITIONS:
                _failure(failures, "invalid_inventory_scope", path=value)
                continue
        else:
            if not row["decision_gap"]:
                _failure(failures, "invalid_disposition", path=value)
            expected = CONSERVATIVE_DISPOSITIONS.get(row["inherited_rights_status"])
            if row["local_disposition"] != expected or expected is None:
                _failure(failures, "invalid_disposition", path=value)
        validated[value] = row
    return validated


def _validated_reviewed_history(
    rows: list[dict[str, str]], failures: list[dict[str, object]]
) -> dict[tuple[str, str], dict[str, str]]:
    validated: dict[tuple[str, str], dict[str, str]] = {}
    for line_number, row in enumerate(rows, start=2):
        path = row["path"]
        oid = row["blob_oid"]
        if not _is_repo_path(path):
            _failure(failures, "invalid_reviewed_history_path", line=line_number)
            continue
        if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", oid):
            _failure(failures, "invalid_reviewed_history_oid", path=path)
            continue
        if row["review_class"] not in REVIEW_CLASSES:
            _failure(failures, "invalid_review_class", path=path)
            continue
        if not _review_class_matches_path(row["review_class"], path):
            _failure(failures, "review_class_path_mismatch", path=path)
            continue
        if not row["review_note"].strip():
            _failure(failures, "missing_review_note", path=path)
            continue
        key = (path, oid)
        if key in validated:
            _failure(failures, "duplicate_reviewed_history_tuple", path=path)
            continue
        validated[key] = row
    return validated


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if result.returncode != 0:
        raise ValueError("Git audit failed")
    return result.stdout


def _tracked_paths(root: Path) -> set[str]:
    payload = _git(root, "ls-files", "-z", "--", "data", "outputs", "docs/assets")
    return {os.fsdecode(item) for item in payload.split(b"\0") if item}


def _history_paths(root: Path, base: str) -> list[str]:
    payload = _git(
        root,
        "log",
        "--format=",
        "--name-only",
        "-z",
        f"{base}..HEAD",
        "--",
        *SENSITIVE_PATHS,
    )
    return sorted({os.fsdecode(item) for item in payload.split(b"\0") if item})


def _staged_sensitive_paths(root: Path) -> list[str]:
    payload = _git(
        root,
        "diff",
        "--cached",
        "--name-only",
        "-z",
        "--",
        "data",
        "outputs",
        "docs/assets",
    )
    return sorted({os.fsdecode(path) for path in payload.split(b"\0") if path})


def _changed_blob_pairs(root: Path, base: str) -> set[tuple[str, str]]:
    """Find introduced path/blob versions in every branch commit, including reused OIDs."""
    pairs: set[tuple[str, str]] = set()
    commits = _git(root, "rev-list", "--reverse", f"{base}..HEAD").splitlines()
    for commit_bytes in commits:
        commit = os.fsdecode(commit_bytes)
        parents = os.fsdecode(_git(root, "show", "-s", "--format=%P", commit)).split()
        if not parents:
            raise ValueError("Branch history includes a root commit after base")
        changed_paths: set[str] = set()
        for parent in parents:
            diff = _git(root, "diff", "--no-renames", "--name-only", "-z", parent, commit)
            changed_paths.update(os.fsdecode(path) for path in diff.split(b"\0") if path)
        if not changed_paths:
            continue
        tree_entries: dict[str, tuple[bytes, bytes]] = {}
        for record in _git(root, "ls-tree", "-r", "-z", commit).split(b"\0"):
            if not record:
                continue
            metadata, path = record.split(b"\t", 1)
            _mode, object_type, oid = metadata.split(b" ", 2)
            tree_entries[os.fsdecode(path)] = (object_type, oid)
        for path in changed_paths:
            entry = tree_entries.get(path)
            if entry is None:
                continue  # A deletion introduces no path/blob version.
            object_type, oid = entry
            if object_type != b"blob":
                raise ValueError("Changed history path is not a blob")
            pairs.add((path, os.fsdecode(oid)))
    return pairs


def _rights_registry_changed(root: Path, base: str) -> tuple[bool, bool]:
    dirty = bool(
        _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", "config/source_rights.yml")
    )
    history = bool(
        _git(
            root,
            "log",
            "--format=",
            "--name-only",
            "-z",
            f"{base}..HEAD",
            "--",
            "config/source_rights.yml",
        ).strip(b"\0\n")
    )
    return dirty, history


def _path_has_symlink(root: Path, relative_path: str) -> bool:
    current = root
    for part in relative_path.split("/"):
        current = current / part
        if current.is_symlink():
            return True
    return False


def build_release_baseline_audit(
    repo_root: Path,
    inventory_path: Path,
    disposition_path: Path,
    base_ref: str,
    reviewed_history_path: Path,
) -> dict[str, object]:
    """Check inventory integrity and sensitive branch history without writing."""
    root = Path(repo_root)
    failures: list[dict[str, object]] = []
    inventory_file = Path(inventory_path)
    disposition_file = Path(disposition_path)
    reviewed_history_file = Path(reviewed_history_path)
    if not inventory_file.is_absolute():
        inventory_file = root / inventory_file
    if not disposition_file.is_absolute():
        disposition_file = root / disposition_file
    if not reviewed_history_file.is_absolute():
        reviewed_history_file = root / reviewed_history_file

    inventory = _validated_rows(
        _read_tsv(inventory_file, INVENTORY_COLUMNS, "inventory", failures),
        "inventory",
        failures,
    )
    dispositions = _validated_rows(
        _read_tsv(disposition_file, DISPOSITION_COLUMNS, "disposition", failures),
        "disposition",
        failures,
    )
    reviewed_history = _validated_reviewed_history(
        _read_tsv(
            reviewed_history_file,
            REVIEWED_HISTORY_COLUMNS,
            "reviewed_history",
            failures,
        ),
        failures,
    )

    tracked: set[str] = set()
    history_paths: list[str] = []
    staged_sensitive_paths: list[str] = []
    changed_blob_pairs: set[tuple[str, str]] = set()
    rights_dirty = False
    rights_history = False
    head = "unavailable"
    base_commit = "unavailable"
    try:
        if _has_symlink_component(root) or not root.is_dir():
            raise ValueError("Invalid repository root")
        top = Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel")).strip())
        if top.resolve() != root.resolve():
            raise ValueError("Repository root does not match worktree top")
        if not base_ref or base_ref.startswith("-") or any(c.isspace() for c in base_ref):
            raise ValueError("Invalid base ref")
        base_commit = os.fsdecode(
            _git(root, "rev-parse", "--verify", f"{base_ref}^{{commit}}")
        ).strip()
        head = os.fsdecode(_git(root, "rev-parse", "HEAD")).strip()
        _git(root, "merge-base", "--is-ancestor", base_commit, head)
        tracked = _tracked_paths(root)
        history_paths = _history_paths(root, base_commit)
        staged_sensitive_paths = _staged_sensitive_paths(root)
        changed_blob_pairs = _changed_blob_pairs(root, base_commit)
        rights_dirty, rights_history = _rights_registry_changed(root, base_commit)
    except (OSError, ValueError):
        _failure(failures, "git_verification_failed")

    inventory_paths = set(inventory)
    if tracked != inventory_paths:
        _failure(
            failures,
            "tracked_path_set_mismatch",
            inventory_only_count=len(inventory_paths - tracked),
            tracked_only_count=len(tracked - inventory_paths),
        )
    if set(dispositions) != inventory_paths:
        _failure(
            failures,
            "disposition_path_set_mismatch",
            inventory_only_count=len(inventory_paths - set(dispositions)),
            disposition_only_count=len(set(dispositions) - inventory_paths),
        )

    for path, row in inventory.items():
        disposition = dispositions.get(path)
        if disposition and (
            disposition["sha256"] != row["sha256"]
            or disposition["inherited_rights_status"] != row["rights_status"]
        ):
            _failure(failures, "disposition_mismatch", path=path)
        if path not in tracked:
            continue
        if _path_has_symlink(root, path):
            _failure(failures, "symlink_path", path=path)
            continue
        target = root / path
        if not target.is_file():
            _failure(failures, "missing_tracked_file", path=path)
            continue
        try:
            payload = target.read_bytes()
        except OSError:
            _failure(failures, "unreadable_tracked_file", path=path)
            continue
        if hashlib.sha256(payload).hexdigest() != row["sha256"]:
            _failure(failures, "hash_mismatch", path=path)
        if len(payload) != int(row["bytes"]):
            _failure(failures, "byte_count_mismatch", path=path)

    if history_paths:
        _failure(
            failures,
            "sensitive_history",
            path_count=len(history_paths),
        )
    if staged_sensitive_paths:
        _failure(
            failures,
            "staged_sensitive_change",
            path_count=len(staged_sensitive_paths),
        )
    unreviewed_pairs = changed_blob_pairs - set(reviewed_history)
    extra_reviewed_pairs = set(reviewed_history) - changed_blob_pairs
    if unreviewed_pairs or extra_reviewed_pairs:
        _failure(
            failures,
            "reviewed_history_mismatch",
            unreviewed_tuple_count=len(unreviewed_pairs),
            extra_reviewed_tuple_count=len(extra_reviewed_pairs),
        )
    if rights_dirty:
        _failure(failures, "rights_registry_dirty")
    if rights_history:
        _failure(failures, "rights_registry_history")
    holds = Counter(
        row["local_disposition"]
        for row in dispositions.values()
        if row["path"] in inventory
        and row["local_disposition"] in CONSERVATIVE_DISPOSITIONS.values()
    )
    return {
        "integrity_status": "verified" if not failures else "failed",
        "distribution_status": "held",
        "base_commit": base_commit,
        "head_commit": head,
        "path_count": len(inventory),
        "tracked_path_count": len(tracked),
        "hold_counts": dict(sorted(holds.items())),
        "sensitive_history_path_count": len(history_paths),
        "sensitive_history_paths": history_paths[:MAX_DETAIL],
        "staged_sensitive_path_count": len(staged_sensitive_paths),
        "staged_sensitive_paths": staged_sensitive_paths[:MAX_DETAIL],
        "changed_blob_oid_count": len({oid for _, oid in changed_blob_pairs}),
        "changed_blob_path_tuple_count": len(changed_blob_pairs),
        "reviewed_history_tuple_count": len(reviewed_history),
        "unreviewed_history_tuple_count": len(unreviewed_pairs),
        "unreviewed_history_paths": sorted({path for path, _ in unreviewed_pairs})[:MAX_DETAIL],
        "extra_reviewed_history_tuple_count": len(extra_reviewed_pairs),
        "failure_count": len(failures),
        "failures": failures[:MAX_DETAIL],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--disposition", required=True, type=Path)
    parser.add_argument("--reviewed-history", required=True, type=Path)
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args(argv)
    payload = build_release_baseline_audit(
        args.repo_root,
        args.inventory,
        args.disposition,
        args.base_ref,
        args.reviewed_history,
    )
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["integrity_status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
