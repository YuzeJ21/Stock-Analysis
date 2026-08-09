"""Evidence-bound review for the default-profile readiness artifact family."""

from __future__ import annotations

import hashlib
import csv
import io
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

from src.commercial_source_rights import SourceRights, load_source_rights_registry
from src.dcf_price_lineage import review_dcf_price_lineage
from src.readiness_engine import build_ticker_readiness_report
from src.readiness_preview import (
    ReadinessImpactPreview,
    compare_readiness_frames,
    review_readiness_changes,
    review_readiness_promotions,
)
from src.research_ledger_lock import ledger_write_lock


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
class TransitionEvidence:
    ticker: str
    fields: tuple[str, ...]
    source_id: str
    source_reference: str
    as_of_date: str
    changed_input_identity: str
    review_cutoff: str
    before_snapshot_identity: str
    after_snapshot_identity: str


@dataclass(frozen=True)
class ReleaseEvidenceReview:
    head_to_working: ReadinessImpactPreview
    working_to_proposed: ReadinessImpactPreview
    transitions: tuple[TransitionEvidence, ...]
    axes: tuple[ReviewAxis, ...]
    blockers: tuple[str, ...]

    def axis(self, name: str) -> ReviewAxis:
        for axis in self.axes:
            if axis.name == name:
                return axis
        raise KeyError(name)


@dataclass(frozen=True)
class RecordedDecision:
    record_id: str
    preview_receipt: str
    git_head: str
    candidate_manifest_digest: str
    canonical_source_digest: str
    rights_registry_digest: str
    proof_ledger_digest: str
    technical_transition_summary: str
    candidate_integrity: str
    technical_transition_review: str
    provenance_review: str
    commercial_rights_review: str
    registered_field_scope_review: str
    price_lineage_review: str
    historical_proof_binding_review: str
    distribution_review: str
    staging_hygiene_review: str
    technical_decision: str
    distribution_decision: str
    reviewer: str
    review_date: str
    blocker_codes: str
    research_only_boundary: str
    recorded_at: str


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
    head_to_working: ReadinessImpactPreview
    working_to_proposed: ReadinessImpactPreview
    transitions: tuple[TransitionEvidence, ...]
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

REVIEW_RECORD_COLUMNS = (
    "record_id",
    "preview_receipt",
    "git_head",
    "candidate_manifest_digest",
    "canonical_source_digest",
    "rights_registry_digest",
    "proof_ledger_digest",
    "technical_transition_summary",
    "candidate_integrity",
    "technical_transition_review",
    "provenance_review",
    "commercial_rights_review",
    "registered_field_scope_review",
    "price_lineage_review",
    "historical_proof_binding_review",
    "distribution_review",
    "staging_hygiene_review",
    "technical_decision",
    "distribution_decision",
    "reviewer",
    "review_date",
    "blocker_codes",
    "research_only_boundary",
    "recorded_at",
)

TECHNICAL_DECISIONS = {"approved", "rejected"}
DISTRIBUTION_DECISIONS = {"approved", "rejected", "external_review_required"}
RESEARCH_ONLY_BOUNDARY = "research_only_no_investment_or_execution_action"

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

MIRROR_PAIRS = (
    (
        "analyst_estimates_readiness",
        "data/analyst_estimates_readiness.csv",
        "data/reports/analyst_estimates_readiness_report.csv",
    ),
    (
        "earnings_readiness",
        "data/earnings_readiness.csv",
        "data/reports/earnings_readiness_report.csv",
    ),
    (
        "price_coverage_report",
        "data/price_coverage_report.csv",
        "data/reports/price_coverage_report.csv",
    ),
    (
        "feature_readiness_summary",
        "data/reports/feature_readiness_summary.csv",
        "outputs/feature_readiness_summary.csv",
    ),
    (
        "peer_unlock_worklist",
        "data/reports/peer_unlock_worklist.csv",
        "outputs/peer_unlock_worklist.csv",
    ),
)


def canonical_receipt(payload: Mapping[str, object] | list[object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def review_candidate_mirrors(payloads: Mapping[str, bytes]) -> ReviewAxis:
    blockers = tuple(
        f"mirror_mismatch:{name}"
        for name, first, second in MIRROR_PAIRS
        if payloads.get(first) != payloads.get(second)
    )
    dcf_compat = payloads.get("data/dcf_readiness.csv")
    dcf_report = payloads.get("data/reports/dcf_readiness_report.csv")
    if dcf_compat is None or dcf_report is None:
        blockers += ("mirror_mismatch:dcf_readiness",)
    elif _normalized_dcf_rows(dcf_compat) != _normalized_dcf_rows(dcf_report):
        blockers += ("mirror_mismatch:dcf_readiness",)
    return ReviewAxis(
        name="candidate_integrity",
        status="blocked" if blockers else "passed",
        blockers=blockers,
    )


def _normalized_dcf_rows(payload: bytes) -> tuple[tuple[tuple[str, str], ...], ...]:
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
        rows: list[tuple[tuple[str, str], ...]] = []
        for row in reader:
            normalized = {
                ("dcf_ready" if key == "is_dcf_ready" else str(key)): str(value or "")
                for key, value in row.items()
            }
            rows.append(tuple(sorted(normalized.items())))
        return tuple(rows)
    except (UnicodeDecodeError, csv.Error):
        return (("<invalid>", "<invalid>"),)


def _text(value: object) -> str:
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    return str(value).strip()


def _fundamentals_by_ticker(frame: pd.DataFrame) -> dict[str, list[pd.Series]]:
    rows: dict[str, list[pd.Series]] = {}
    if frame.empty or "ticker" not in frame.columns:
        return rows
    for _, row in frame.iterrows():
        ticker = _text(row.get("ticker")).upper()
        if ticker:
            rows.setdefault(ticker, []).append(row)
    return rows


def _transition_identity(row: pd.Series) -> str:
    payload = {
        str(key): _text(value)
        for key, value in sorted(row.to_dict().items(), key=lambda item: str(item[0]))
    }
    return canonical_receipt(payload)


def _proof_tickers(row: Mapping[str, str]) -> set[str]:
    raw = str(row.get("tickers") or row.get("tickers_or_dependencies") or "")
    normalized = raw.replace(";", ",")
    return {part.strip().upper() for part in normalized.split(",") if part.strip()}


def _lane_matches(transition: TransitionEvidence, lane: str) -> bool:
    normalized = str(lane or "").strip().lower()
    if "dcf_ready" in transition.fields:
        return normalized in {"dcf", "fundamentals_dcf"}
    return normalized == "fundamentals"


def review_historical_binding(
    transitions: Sequence[TransitionEvidence],
    batch_rows: Sequence[Mapping[str, str]],
    data_rows: Sequence[Mapping[str, str]],
) -> ReviewAxis:
    blockers: list[str] = []
    proof_rows = tuple(batch_rows) + tuple(data_rows)
    for transition in transitions:
        matched = any(
            _lane_matches(transition, str(row.get("lane") or ""))
            and transition.ticker in _proof_tickers(row)
            and str(row.get("source_id") or "").strip() == transition.source_id
            and str(row.get("changed_input_identity") or "").strip() == transition.changed_input_identity
            and str(row.get("review_cutoff") or "").strip() == transition.review_cutoff
            and str(row.get("pre_run_readiness_snapshot") or row.get("readiness_before") or "").strip()
            == transition.before_snapshot_identity
            and str(row.get("post_run_readiness_snapshot") or row.get("readiness_after") or "").strip()
            == transition.after_snapshot_identity
            for row in proof_rows
        )
        if not matched:
            blockers.append(f"historical_proof_binding_missing:{transition.ticker}")
    return ReviewAxis(
        name="historical_proof_binding_review",
        status="blocked" if blockers else "passed",
        blockers=tuple(blockers),
    )


def _axis(name: str, blockers: Sequence[str]) -> ReviewAxis:
    stable = tuple(sorted(set(blockers)))
    return ReviewAxis(name=name, status="blocked" if stable else "passed", blockers=stable)


def review_release_axes(
    head: pd.DataFrame,
    working: pd.DataFrame,
    proposed: pd.DataFrame,
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    rights_registry: Mapping[str, SourceRights],
    batch_rows: Sequence[Mapping[str, str]] = (),
    data_rows: Sequence[Mapping[str, str]] = (),
    review_cutoff: str | None = None,
    before_snapshot_identity: str,
    after_snapshot_identity: str,
    top_n: int = 20,
) -> ReleaseEvidenceReview:
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    full_detail_limit = max(len(head), len(working), len(proposed), 1)
    head_to_working = compare_readiness_frames(head, working, top_n=top_n, saved_path="HEAD")
    head_to_working = replace(
        head_to_working,
        change_review=review_readiness_changes(head, working, fundamentals),
    )
    working_to_proposed = compare_readiness_frames(
        working,
        proposed,
        top_n=top_n,
        saved_path="working_candidate",
    )
    promotion = review_readiness_promotions(
        head,
        working,
        fundamentals,
        rights_registry=rights_registry,
        top_n=full_detail_limit,
    )
    price_lineage = review_dcf_price_lineage(
        head,
        working,
        prices,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
        top_n=full_detail_limit,
    )

    fundamentals_rows = _fundamentals_by_ticker(fundamentals)
    transitions: list[TransitionEvidence] = []
    for evidence in promotion.evidence_rows:
        candidates = fundamentals_rows.get(evidence.ticker, [])
        changed_identity = _transition_identity(candidates[0]) if len(candidates) == 1 else "<unavailable>"
        transitions.append(
            TransitionEvidence(
                ticker=evidence.ticker,
                fields=evidence.promoted_fields,
                source_id=evidence.source_id,
                source_reference=evidence.source_reference,
                as_of_date=evidence.as_of_date,
                changed_input_identity=changed_identity,
                review_cutoff=str(review_cutoff or ""),
                before_snapshot_identity=before_snapshot_identity,
                after_snapshot_identity=after_snapshot_identity,
            )
        )

    technical_blockers: list[str] = []
    if working_to_proposed.changed_ticker_count:
        technical_blockers.append("working_candidate_differs_from_in_memory_readiness")
    if head_to_working.change_review and head_to_working.change_review.status == "unexplained_changes":
        technical_blockers.append("unexplained_technical_transition")

    provenance_blockers: list[str] = []
    commercial_blockers: list[str] = []
    scope_blockers: list[str] = []
    for evidence in promotion.evidence_rows:
        provenance_blockers.extend(
            f"missing_provenance:{field}:{evidence.ticker}"
            for field in evidence.missing_provenance_fields
        )
        if evidence.rights_status != "approved":
            commercial_blockers.append(f"commercial_rights:{evidence.rights_status}:{evidence.ticker}")
        if evidence.missing_supported_fields:
            scope_blockers.append(f"registered_field_scope_incomplete:{evidence.ticker}")
    for evidence in price_lineage.evidence_rows:
        if evidence.rights_status != "approved":
            commercial_blockers.append(f"commercial_rights:{evidence.rights_status}:{evidence.ticker}:price")
        if evidence.missing_supported_fields:
            scope_blockers.append(f"registered_price_scope_incomplete:{evidence.ticker}")

    price_blockers = (
        []
        if price_lineage.status in {"no_dcf_promotions", "price_lineage_review_complete"}
        else ["price_lineage_review_required"]
    )
    history_axis = review_historical_binding(tuple(transitions), batch_rows, data_rows)
    axes = (
        _axis("technical_transition_review", technical_blockers),
        _axis("provenance_review", provenance_blockers),
        _axis("commercial_rights_review", commercial_blockers),
        _axis("registered_field_scope_review", scope_blockers),
        _axis("price_lineage_review", price_blockers),
        history_axis,
        ReviewAxis("distribution_review", "review_required", ("distribution_review_required",)),
    )
    blockers = tuple(
        sorted(
            {
                blocker
                for axis in axes
                for blocker in axis.blockers
            }
        )
    )
    return ReleaseEvidenceReview(
        head_to_working=head_to_working,
        working_to_proposed=working_to_proposed,
        transitions=tuple(transitions),
        axes=axes,
        blockers=blockers,
    )


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


def _read_csv_payload(payload: bytes, relative: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(payload))
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise ReleaseReviewError(f"csv_malformed:{relative}") from exc


def _read_csv_rows(root: Path, relative: str) -> tuple[dict[str, str], ...]:
    path = root / relative
    if not path.exists():
        return ()
    payload = _read_regular_file(path, relative)
    _validate_csv_payload(payload, relative)
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
        return tuple({str(key): str(value or "") for key, value in row.items()} for row in reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ReleaseReviewError(f"csv_malformed:{relative}") from exc


def load_review_records(path: Path | str) -> tuple[RecordedDecision, ...]:
    destination = Path(path)
    if not destination.exists():
        return ()
    payload = _read_regular_file(destination, str(destination))
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
        if tuple(reader.fieldnames or ()) != REVIEW_RECORD_COLUMNS:
            raise ReleaseReviewError("review_ledger_header_mismatch")
        records: list[RecordedDecision] = []
        seen_ids: set[str] = set()
        seen_receipts: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            values = {column: str(row.get(column) or "") for column in REVIEW_RECORD_COLUMNS}
            record_id = values["record_id"]
            receipt = values["preview_receipt"]
            if record_id in seen_ids:
                raise ReleaseReviewError(f"duplicate_record_id:{record_id}:row_{row_number}")
            if receipt in seen_receipts:
                raise ReleaseReviewError(f"duplicate_preview_receipt:{receipt}:row_{row_number}")
            seen_ids.add(record_id)
            seen_receipts.add(receipt)
            records.append(RecordedDecision(**values))
        return tuple(records)
    except UnicodeDecodeError as exc:
        raise ReleaseReviewError("review_ledger_not_utf8") from exc
    except csv.Error as exc:
        raise ReleaseReviewError("review_ledger_malformed") from exc


def _validate_reviewer(value: object) -> str:
    reviewer = str(value or "").strip()
    lowered = reviewer.casefold()
    placeholder = (
        not reviewer
        or lowered in {"-", "unknown", "n/a", "na", "reviewer", "local reviewer"}
        or ("<" in reviewer and ">" in reviewer)
    )
    if placeholder or any(ord(character) < 32 for character in reviewer):
        raise ReleaseReviewError("invalid_reviewer")
    return reviewer


def _validate_review_date(value: object) -> str:
    review_date = str(value or "").strip()
    try:
        parsed = date.fromisoformat(review_date)
    except ValueError as exc:
        raise ReleaseReviewError("invalid_review_date") from exc
    if parsed.isoformat() != review_date:
        raise ReleaseReviewError("invalid_review_date")
    return review_date


def _validate_receipt(value: object) -> str:
    receipt = str(value or "").strip()
    if re.fullmatch(r"[0-9a-f]{64}", receipt) is None:
        raise ReleaseReviewError("invalid_preview_receipt")
    return receipt


def _atomic_write_records(destination: Path, records: Sequence[RecordedDecision]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=REVIEW_RECORD_COLUMNS, lineterminator="\n")
            writer.writeheader()
            for record in records:
                writer.writerow({column: getattr(record, column) for column in REVIEW_RECORD_COLUMNS})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        directory_descriptor = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def record_review(
    project_root: Path | str,
    *,
    preview_receipt: str,
    reviewer: str,
    review_date: str,
    technical_decision: str,
    distribution_decision: str,
    confirm_reviewed: bool,
    ledger_path: Path | str | None = None,
    proposed_readiness: pd.DataFrame | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
) -> RecordedDecision:
    if not confirm_reviewed:
        raise ReleaseReviewError("confirm_reviewed_required")
    receipt = _validate_receipt(preview_receipt)
    reviewer_name = _validate_reviewer(reviewer)
    reviewed_on = _validate_review_date(review_date)
    technical = str(technical_decision or "").strip().lower()
    if technical not in TECHNICAL_DECISIONS:
        raise ReleaseReviewError("invalid_technical_decision")
    distribution = str(distribution_decision or "").strip().lower()
    if distribution not in DISTRIBUTION_DECISIONS:
        raise ReleaseReviewError("invalid_distribution_decision")

    root = Path(project_root).expanduser().resolve()
    destination = (
        Path(ledger_path).expanduser().resolve()
        if ledger_path is not None
        else root / REVIEW_RECORD_PATH
    )
    with ledger_write_lock(destination):
        packet = build_release_review(
            root,
            allow_record_path_change=True,
            proposed_readiness=proposed_readiness,
            rights_registry=rights_registry,
            review_cutoff=review_cutoff,
        )
        if packet.preview_receipt != receipt:
            raise ReleaseReviewError(
                f"preview_receipt_mismatch:expected_{receipt}:current_{packet.preview_receipt}"
            )
        existing = load_review_records(destination)
        if any(record.preview_receipt == receipt for record in existing):
            raise ReleaseReviewError(f"duplicate_preview_receipt:{receipt}")
        record_id = f"RRR-{reviewed_on.replace('-', '')}-{receipt[:12]}"
        if any(record.record_id == record_id for record in existing):
            raise ReleaseReviewError(f"duplicate_record_id:{record_id}")
        axes = {axis.name: axis.status for axis in packet.axes}
        record = RecordedDecision(
            record_id=record_id,
            preview_receipt=receipt,
            git_head=packet.git_head,
            candidate_manifest_digest=packet.candidate_manifest_digest,
            canonical_source_digest=packet.canonical_source_digest,
            rights_registry_digest=packet.rights_registry_digest,
            proof_ledger_digest=packet.proof_ledger_digest,
            technical_transition_summary=(
                f"head_to_working={packet.head_to_working.changed_ticker_count};"
                f"working_to_proposed={packet.working_to_proposed.changed_ticker_count};"
                f"transitions={len(packet.transitions)}"
            ),
            candidate_integrity=axes["candidate_integrity"],
            technical_transition_review=axes["technical_transition_review"],
            provenance_review=axes["provenance_review"],
            commercial_rights_review=axes["commercial_rights_review"],
            registered_field_scope_review=axes["registered_field_scope_review"],
            price_lineage_review=axes["price_lineage_review"],
            historical_proof_binding_review=axes["historical_proof_binding_review"],
            distribution_review=axes["distribution_review"],
            staging_hygiene_review=axes["staging_hygiene_review"],
            technical_decision=technical,
            distribution_decision=distribution,
            reviewer=reviewer_name,
            review_date=reviewed_on,
            blocker_codes=";".join(packet.blockers),
            research_only_boundary=RESEARCH_ONLY_BOUNDARY,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        _atomic_write_records(destination, (*existing, record))
        try:
            reloaded = load_review_records(destination)
        except Exception as exc:
            raise ReleaseReviewError(
                f"record_write_outcome_uncertain:{record_id}:reload_by_record_id"
            ) from exc
        confirmed = next((row for row in reloaded if row.record_id == record_id), None)
        if confirmed != record:
            raise ReleaseReviewError(
                f"record_write_outcome_uncertain:{record_id}:reload_by_record_id"
            )
        return record


def build_release_review(
    project_root: Path | str,
    *,
    top_n: int = 20,
    allow_record_path_change: bool = False,
    proposed_readiness: pd.DataFrame | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
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
    candidate_payloads: dict[str, bytes] = {}
    integrity_blockers: list[str] = []
    staging_blockers: list[str] = []
    for spec in CANDIDATE_PATHS:
        working = _read_regular_file(root / spec.path, spec.path)
        _validate_csv_payload(working, spec.path)
        candidate_payloads[spec.path] = working
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

    mirror_axis = review_candidate_mirrors(candidate_payloads)
    integrity_blockers.extend(mirror_axis.blockers)
    integrity_blockers = sorted(set(integrity_blockers))
    staging_blockers = sorted(set(staging_blockers))
    ticker_relative = "data/reports/ticker_readiness_report.csv"
    head_ticker_payload = _head_bytes(root, ticker_relative)
    working_ticker_payload = candidate_payloads[ticker_relative]
    head_ticker = _read_csv_payload(head_ticker_payload, f"HEAD:{ticker_relative}")
    working_ticker = _read_csv_payload(working_ticker_payload, ticker_relative)
    if proposed_readiness is None:
        reports = build_ticker_readiness_report(root, write_outputs=False)
        proposed = reports["ticker_readiness_report"]
    else:
        proposed = proposed_readiness.copy()
    fundamentals_payload = _read_regular_file(root / "data/fundamentals.csv", "data/fundamentals.csv")
    prices_payload = _read_regular_file(root / "data/prices.csv", "data/prices.csv")
    fundamentals = _read_csv_payload(fundamentals_payload, "data/fundamentals.csv")
    prices = _read_csv_payload(prices_payload, "data/prices.csv")
    registry = (
        rights_registry
        if rights_registry is not None
        else load_source_rights_registry(root / RIGHTS_REGISTRY_PATH)
    )
    evidence_review = review_release_axes(
        head_ticker,
        working_ticker,
        proposed,
        fundamentals,
        prices,
        rights_registry=registry,
        batch_rows=_read_csv_rows(root, PROOF_LEDGER_PATHS[0]),
        data_rows=_read_csv_rows(root, PROOF_LEDGER_PATHS[1]),
        review_cutoff=review_cutoff,
        before_snapshot_identity=_sha256(head_ticker_payload),
        after_snapshot_identity=_sha256(working_ticker_payload),
        top_n=max(len(head_ticker), len(working_ticker), len(proposed), 1),
    )
    evidence_axes = {axis.name: axis for axis in evidence_review.axes}
    axes_by_name = {
        "candidate_integrity": ReviewAxis(
            "candidate_integrity",
            "blocked" if integrity_blockers else "passed",
            tuple(integrity_blockers),
        ),
        **evidence_axes,
        "staging_hygiene_review": ReviewAxis(
            "staging_hygiene_review",
            "blocked" if staging_blockers else "passed",
            tuple(staging_blockers),
        ),
    }
    axes = tuple(axes_by_name[name] for name in AXIS_NAMES)
    blockers = tuple(sorted({blocker for axis in axes for blocker in axis.blockers}))
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
        "head_to_working": asdict(evidence_review.head_to_working),
        "working_to_proposed": asdict(evidence_review.working_to_proposed),
        "transitions": [asdict(item) for item in evidence_review.transitions],
        "axes": [asdict(item) for item in axes],
        "blockers": blockers,
    }
    technical_axes = {
        "candidate_integrity",
        "technical_transition_review",
        "staging_hygiene_review",
    }
    if any(axes_by_name[name].status == "blocked" for name in technical_axes):
        overall_status = "invalid" if axes_by_name["candidate_integrity"].status == "blocked" else "blocked"
    elif all(
        axis.status == "passed"
        for axis in axes
        if axis.name != "distribution_review"
    ):
        overall_status = "release_reviewable"
    else:
        overall_status = "technical_snapshot_reviewable_commercial_claims_withheld"
    return ReleaseReviewPacket(
        overall_status=overall_status,
        preview_receipt=canonical_receipt(receipt_payload),
        git_head=git_head,
        branch=branch,
        candidate_manifest_digest=candidate_manifest_digest,
        canonical_source_digest=canonical_source_digest,
        rights_registry_digest=rights_registry_digest,
        proof_ledger_digest=proof_ledger_digest,
        candidate_paths=tuple(candidate_evidence),
        head_to_working=evidence_review.head_to_working,
        working_to_proposed=evidence_review.working_to_proposed,
        transitions=evidence_review.transitions,
        axes=axes,
        blockers=blockers,
        top_n=top_n,
    )
