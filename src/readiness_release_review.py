"""Evidence-bound review for the default-profile readiness artifact family."""

from __future__ import annotations

import hashlib
import csv
import io
import json
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping


MAX_EVIDENCE_FILE_BYTES = 64 * 1024 * 1024
MAX_EVIDENCE_CSV_ROWS = 500_000


class ReleaseReviewError(RuntimeError):
    """Raised when release evidence cannot be read safely."""


@dataclass(frozen=True)
class CandidatePathSpec:
    path: str
    category: str


@dataclass(frozen=True)
class FileEvidence:
    path: str
    category: str
    head_sha256: str
    working_sha256: str
    status: str


@dataclass(frozen=True)
class ReviewAxis:
    name: str
    status: str
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReleaseReviewPacket:
    overall_status: str
    preview_receipt: str
    git_head: str
    branch: str
    candidate_manifest_digest: str
    canonical_source_digest: str
    rights_registry_digest: str
    proof_ledger_digest: str
    candidate_paths: tuple[FileEvidence, ...]
    axes: tuple[ReviewAxis, ...]
    blockers: tuple[str, ...]
    top_n: int

    def axis(self, name: str) -> ReviewAxis:
        for axis in self.axes:
            if axis.name == name:
                return axis
        raise KeyError(name)


CANDIDATE_PATHS = (
    CandidatePathSpec("data/analyst_estimates_readiness.csv", "compatibility_copy"),
    CandidatePathSpec("data/dcf_readiness.csv", "compatibility_copy"),
    CandidatePathSpec("data/earnings_readiness.csv", "compatibility_copy"),
    CandidatePathSpec("data/price_coverage_report.csv", "compatibility_copy"),
    CandidatePathSpec("data/reports/analyst_estimates_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/data_source_status.csv", "source_status_metadata"),
    CandidatePathSpec("data/reports/dcf_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/earnings_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/feature_readiness_summary.csv", "derived_summary"),
    CandidatePathSpec("data/reports/fundamentals_coverage_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/peer_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/peer_unlock_worklist.csv", "derived_worklist"),
    CandidatePathSpec("data/reports/price_coverage_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/ticker_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/universe_coverage_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/universe_master.csv", "canonical_readiness_input"),
    CandidatePathSpec("outputs/feature_readiness_summary.csv", "derived_summary"),
    CandidatePathSpec("outputs/peer_unlock_worklist.csv", "derived_worklist"),
)

READINESS_SOURCE_PATHS = (
    "config/readiness.yml",
    "data/universe.csv",
    "data/universe_active.csv",
    "data/holdings.csv",
    "data/prices.csv",
    "data/fundamentals.csv",
    "data/peers.csv",
    "data/peer_candidates.csv",
    "data/earnings.csv",
    "data/analyst_estimates.csv",
)
RIGHTS_REGISTRY_PATH = "config/source_rights.yml"
PROOF_LEDGER_PATHS = (
    "data/reviewed_batch_proofs.csv",
    "data/reviewed_data_proofs.csv",
)
REVIEW_RECORD_PATH = "data/readiness_release_reviews.csv"

AXIS_NAMES = (
    "candidate_integrity",
    "technical_transition_review",
    "provenance_review",
    "commercial_rights_review",
    "registered_field_scope_review",
    "price_lineage_review",
    "historical_proof_binding_review",
    "distribution_review",
    "staging_hygiene_review",
)


def canonical_receipt(payload: Mapping[str, object] | list[object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=text,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReleaseReviewError(f"git_read_failed:{args[0] if args else 'unknown'}") from exc
    return result.stdout


def _git_status(root: Path) -> dict[str, str]:
    raw = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", text=False)
    assert isinstance(raw, bytes)
    entries = raw.split(b"\0")
    statuses: dict[str, str] = {}
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4:
            raise ReleaseReviewError("git_status_malformed")
        code = entry[:2].decode("ascii", errors="strict")
        path = entry[3:].decode("utf-8", errors="strict")
        statuses[path] = code
        if code[0] in {"R", "C"} and index < len(entries):
            prior = entries[index]
            index += 1
            if prior:
                statuses[prior.decode("utf-8", errors="strict")] = code
    return statuses


def _read_regular_file(path: Path, relative: str) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise ReleaseReviewError(f"missing_file:{relative}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ReleaseReviewError(f"symlink_rejected:{relative}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ReleaseReviewError(f"non_regular_file:{relative}")
    if metadata.st_size > MAX_EVIDENCE_FILE_BYTES:
        raise ReleaseReviewError(f"file_too_large:{relative}")
    return path.read_bytes()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validate_csv_payload(payload: bytes, relative: str) -> None:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReleaseReviewError(f"csv_not_utf8:{relative}") from exc
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader, None)
        if header is None:
            raise ReleaseReviewError(f"csv_missing_header:{relative}")
        normalized_header = [column.strip() for column in header]
        seen_columns: set[str] = set()
        for column in normalized_header:
            if not column:
                raise ReleaseReviewError(f"empty_csv_column:{relative}")
            if column in seen_columns:
                raise ReleaseReviewError(f"duplicate_csv_column:{relative}:{column}")
            seen_columns.add(column)
        ticker_index = normalized_header.index("ticker") if "ticker" in normalized_header else None
        seen_tickers: set[str] = set()
        row_count = 0
        for row in reader:
            row_count += 1
            if row_count > MAX_EVIDENCE_CSV_ROWS:
                raise ReleaseReviewError(f"csv_row_limit_exceeded:{relative}")
            if len(row) != len(normalized_header):
                raise ReleaseReviewError(f"csv_column_count_mismatch:{relative}:{row_count + 1}")
            if ticker_index is None:
                continue
            ticker = row[ticker_index].strip().upper()
            if not ticker:
                continue
            if ticker in seen_tickers:
                raise ReleaseReviewError(f"duplicate_ticker:{relative}:{ticker}")
            seen_tickers.add(ticker)
    except csv.Error as exc:
        raise ReleaseReviewError(f"csv_malformed:{relative}") from exc


def _head_bytes(root: Path, relative: str) -> bytes:
    payload = _git(root, "show", f"HEAD:{relative}", text=False)
    assert isinstance(payload, bytes)
    if len(payload) > MAX_EVIDENCE_FILE_BYTES:
        raise ReleaseReviewError(f"head_file_too_large:{relative}")
    return payload


def _named_digest(root: Path, paths: tuple[str, ...]) -> str:
    rows: list[dict[str, str]] = []
    for relative in paths:
        path = root / relative
        if not path.exists():
            rows.append({"path": relative, "sha256": "<missing>"})
            continue
        rows.append({"path": relative, "sha256": _sha256(_read_regular_file(path, relative))})
    return canonical_receipt(rows)


def _single_file_digest(root: Path, relative: str) -> str:
    path = root / relative
    if not path.exists():
        return "<missing>"
    return _sha256(_read_regular_file(path, relative))


def build_release_review(
    project_root: Path | str,
    *,
    top_n: int = 20,
    allow_record_path_change: bool = False,
) -> ReleaseReviewPacket:
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    root = Path(project_root).expanduser().resolve()
    git_head = str(_git(root, "rev-parse", "HEAD")).strip()
    branch = str(_git(root, "branch", "--show-current")).strip()
    statuses = _git_status(root)
    candidate_names = {item.path for item in CANDIDATE_PATHS}
    allowed_changed = set(candidate_names)
    if allow_record_path_change:
        allowed_changed.add(REVIEW_RECORD_PATH)

    candidate_evidence: list[FileEvidence] = []
    integrity_blockers: list[str] = []
    staging_blockers: list[str] = []
    for spec in CANDIDATE_PATHS:
        working = _read_regular_file(root / spec.path, spec.path)
        _validate_csv_payload(working, spec.path)
        head = _head_bytes(root, spec.path)
        status = statuses.get(spec.path, "  ")
        if status == "  ":
            integrity_blockers.append(f"candidate_not_modified:{spec.path}")
        if status[0] not in {" ", "?"}:
            staging_blockers.append(f"staged_path:{spec.path}")
        candidate_evidence.append(
            FileEvidence(
                path=spec.path,
                category=spec.category,
                head_sha256=_sha256(head),
                working_sha256=_sha256(working),
                status=status,
            )
        )

    for relative, status in sorted(statuses.items()):
        if relative not in allowed_changed:
            staging_blockers.append(f"unexpected_changed_path:{relative}")
        if status[0] not in {" ", "?"}:
            staging_blockers.append(f"staged_path:{relative}")

    integrity_blockers = sorted(set(integrity_blockers))
    staging_blockers = sorted(set(staging_blockers))
    blockers = tuple(sorted(set(integrity_blockers + staging_blockers)))
    axes = (
        ReviewAxis(
            "candidate_integrity",
            "blocked" if integrity_blockers else "passed",
            tuple(integrity_blockers),
        ),
        ReviewAxis("technical_transition_review", "not_evaluated"),
        ReviewAxis("provenance_review", "not_evaluated"),
        ReviewAxis("commercial_rights_review", "not_evaluated"),
        ReviewAxis("registered_field_scope_review", "not_evaluated"),
        ReviewAxis("price_lineage_review", "not_evaluated"),
        ReviewAxis("historical_proof_binding_review", "not_evaluated"),
        ReviewAxis("distribution_review", "review_required", ("distribution_review_required",)),
        ReviewAxis(
            "staging_hygiene_review",
            "blocked" if staging_blockers else "passed",
            tuple(staging_blockers),
        ),
    )
    candidate_manifest_digest = canonical_receipt([asdict(item) for item in CANDIDATE_PATHS])
    canonical_source_digest = _named_digest(root, READINESS_SOURCE_PATHS)
    rights_registry_digest = _single_file_digest(root, RIGHTS_REGISTRY_PATH)
    proof_ledger_digest = _named_digest(root, PROOF_LEDGER_PATHS)
    receipt_payload: dict[str, object] = {
        "git_head": git_head,
        "branch": branch,
        "candidate_manifest_digest": candidate_manifest_digest,
        "canonical_source_digest": canonical_source_digest,
        "rights_registry_digest": rights_registry_digest,
        "proof_ledger_digest": proof_ledger_digest,
        "candidate_paths": [asdict(item) for item in candidate_evidence],
        "axes": [asdict(item) for item in axes],
        "blockers": blockers,
    }
    return ReleaseReviewPacket(
        overall_status="blocked" if blockers else "technical_snapshot_reviewable_commercial_claims_withheld",
        preview_receipt=canonical_receipt(receipt_payload),
        git_head=git_head,
        branch=branch,
        candidate_manifest_digest=candidate_manifest_digest,
        canonical_source_digest=canonical_source_digest,
        rights_registry_digest=rights_registry_digest,
        proof_ledger_digest=proof_ledger_digest,
        candidate_paths=tuple(candidate_evidence),
        axes=axes,
        blockers=blockers,
        top_n=top_n,
    )
