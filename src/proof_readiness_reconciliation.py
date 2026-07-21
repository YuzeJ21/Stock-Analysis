"""Reconcile historical proof outcomes with current saved readiness.

This module is read-only. It does not restore canonical data, promote readiness,
rewrite proof history, or infer source rights, provenance, or payload truth.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
import re
from typing import Sequence

import pandas as pd

from src.reviewed_batch_proof import ReviewedBatchProof, load_reviewed_batch_proofs


SUPPORTING_OUTCOMES = frozenset({"supported", "auto_supported", "human_reviewed_supported"})
PLACEHOLDER_TICKER_VALUES = frozenset({"-", "none", "n/a", "na", "not available", "unknown"})
CANONICAL_DCF_FIELDS = (
    "free_cash_flow",
    "shares_outstanding",
    "revenue",
    "fcf_margin",
    "price",
)
FUNDAMENTALS_FIELDS = CANONICAL_DCF_FIELDS[:-1]
HISTORICAL_EVIDENCE_LIMIT = (
    "Historical batch proof cannot distinguish payload removal, readiness-contract change, "
    "source-rights change, field-scope change, or another historical cause."
)

NEXT_SAFE_REVIEW = {
    "current_canonical_row_missing": (
        "Obtain and review a permitted source payload for the exact ticker before any import or readiness rebuild."
    ),
    "current_required_fields_missing": (
        "Review the named current fields through the existing source-review and preview-first workflow."
    ),
    "current_price_missing": (
        "Inspect the exact ticker's current price evidence without inferring a provider."
    ),
    "current_peer_mapping_missing": (
        "Review a source-backed relationship through the existing peer evidence contract."
    ),
    "current_peer_valuation_inputs_missing": (
        "Review current peer valuation inputs independently from mapping readiness."
    ),
    "current_readiness_input_unavailable": (
        "Restore or inspect the current saved input before drawing a conclusion."
    ),
    "none": "No current blocker is reported for this lane.",
}

LANE_MAPPINGS: dict[str, tuple[str, str, str]] = {
    "fundamentals": ("fundamentals", "ticker", "fundamentals_ready"),
    "fundamentals_dcf": ("dcf", "ticker", "dcf_ready"),
    "share_count": ("share_count", "dcf", "has_shares_outstanding"),
    "price": ("price", "ticker", "price_ready"),
    "prices": ("price", "ticker", "price_ready"),
    "price_coverage": ("price", "ticker", "price_ready"),
    "price_history": ("price", "ticker", "price_ready"),
    "peers": ("peer_mapping", "ticker", "peer_ready"),
    "peer_mapping": ("peer_mapping", "ticker", "peer_ready"),
    "peer_valuation_inputs": ("peer_valuation_inputs", "peer", "peer_valuation_ready"),
}

CANONICAL_LANES: tuple[tuple[str, str, str], ...] = (
    ("fundamentals", "ticker", "fundamentals_ready"),
    ("dcf", "ticker", "dcf_ready"),
    ("share_count", "dcf", "has_shares_outstanding"),
    ("price", "ticker", "price_ready"),
    ("peer_mapping", "ticker", "peer_ready"),
    ("peer_valuation_inputs", "peer", "peer_valuation_ready"),
)

INPUT_REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "ticker": ("ticker", "fundamentals_ready", "dcf_ready", "price_ready", "peer_ready"),
    "dcf": ("ticker", "has_shares_outstanding", "missing_dcf_fields"),
    "peer": ("ticker", "peer_valuation_ready"),
    "fundamentals": ("ticker",),
}

INPUT_LABELS = {
    "ticker": "ticker readiness",
    "dcf": "DCF readiness",
    "peer": "peer readiness",
    "fundamentals": "canonical fundamentals",
}

INPUT_READINESS_FIELDS: dict[str, tuple[str, ...]] = {
    "ticker": ("fundamentals_ready", "dcf_ready", "price_ready", "peer_ready"),
    "dcf": ("has_shares_outstanding",),
    "peer": ("peer_valuation_ready",),
}

STATE_PRIORITY = {
    "historical_supported_currently_blocked": 0,
    "current_ready_proof_not_supporting": 1,
    "currently_blocked_with_non_supporting_history": 2,
    "current_supported_with_matching_proof": 3,
    "no_proof_record": 4,
    "not_applicable": 5,
}


@dataclass(frozen=True)
class ProofReadinessReconciliationRow:
    ticker: str
    lane: str
    current_field: str
    current_ready: bool | None
    latest_batch_id: str
    latest_review_date: str
    latest_outcome: str
    review_date_valid: bool
    state: str
    reason: str
    proof_applicability: str
    current_blocker_code: str
    current_blocker_fields: tuple[str, ...]
    current_blocker_detail: str
    next_safe_review: str
    historical_payload_status: str
    historical_evidence_limit: str


@dataclass(frozen=True)
class ProofReadinessReconciliationSummary:
    rows: tuple[ProofReadinessReconciliationRow, ...]
    status_counts: tuple[tuple[str, int], ...]
    conflict_counts_by_lane: tuple[tuple[str, int], ...]
    input_status: str
    input_message: str
    proof_applicability_counts: tuple[tuple[str, int], ...]
    current_blocker_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class _LatestProof:
    proof: ReviewedBatchProof
    review_date_valid: bool
    sort_key: tuple[int, int, int]


@dataclass(frozen=True)
class _CurrentBlocker:
    code: str
    fields: tuple[str, ...]
    detail: str
    next_safe_review: str


@dataclass(frozen=True)
class _MissingDcfFields:
    fields: tuple[str, ...]
    unknown_tokens: tuple[str, ...]
    valid: bool


def _normalized_columns(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower().replace(" ", "_") for column in normalized.columns]
    return normalized


def _explicit_bool(value: object) -> bool | None:
    text = "" if value is None or pd.isna(value) else str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def _readiness_lookup(frame: pd.DataFrame, field: str) -> dict[str, bool | None]:
    if frame.empty or "ticker" not in frame.columns or field not in frame.columns:
        return {}
    return {
        str(row["ticker"]).strip().upper(): _explicit_bool(row[field])
        for _, row in frame.iterrows()
        if str(row["ticker"]).strip()
    }


def _valid_tickers(frame: pd.DataFrame) -> tuple[str, ...]:
    if frame.empty or "ticker" not in frame.columns:
        return ()
    values = {str(value).strip().upper() for value in frame["ticker"] if str(value).strip()}
    return tuple(sorted(values))


def _ticker_tokens(value: object, valid_tickers: set[str]) -> tuple[str, ...]:
    tokens = (token.strip().upper() for token in re.split(r"[,;]", str(value or "")))
    return tuple(
        dict.fromkeys(
            token
            for token in tokens
            if token
            and token.lower() not in PLACEHOLDER_TICKER_VALUES
            and token in valid_tickers
        )
    )


def _proof_applicability(
    latest_proof: _LatestProof | None,
    *,
    ticker: str,
    valid_tickers: set[str],
) -> str:
    if latest_proof is None:
        return "no_applicable_proof"
    if not latest_proof.review_date_valid:
        return "malformed_review_date"
    outcome = str(latest_proof.proof.final_outcome or "").strip().lower()
    if outcome not in SUPPORTING_OUTCOMES:
        return "non_supporting_outcome"
    changed = _ticker_tokens(latest_proof.proof.changed_tickers, valid_tickers)
    if ticker in changed:
        return "explicit_ticker_change"
    if not changed:
        return "missing_ticker_change_detail"
    return "scope_only_not_supported"


def _frame_has_columns(frame: pd.DataFrame, *columns: str) -> bool:
    return not frame.empty and all(column in frame.columns for column in columns)


def _missing_dcf_fields(value: object) -> _MissingDcfFields:
    text = "" if value is None or pd.isna(value) else str(value)
    tokens = tuple(
        dict.fromkeys(
            token.strip().lower()
            for token in re.split(r"[,;]", text)
            if token.strip()
        )
    )
    token_set = set(tokens)
    canonical = tuple(field for field in CANONICAL_DCF_FIELDS if field in token_set)
    unknown = tuple(token for token in tokens if token not in CANONICAL_DCF_FIELDS)
    return _MissingDcfFields(
        fields=canonical,
        unknown_tokens=unknown,
        valid=bool(canonical),
    )


def _missing_dcf_lookup(frame: pd.DataFrame) -> dict[str, _MissingDcfFields]:
    if not _frame_has_columns(frame, "ticker", "missing_dcf_fields"):
        return {}
    return {
        str(row["ticker"]).strip().upper(): _missing_dcf_fields(row["missing_dcf_fields"])
        for _, row in frame.iterrows()
        if str(row["ticker"]).strip()
    }


def _schema_issues(frames: dict[str, pd.DataFrame]) -> tuple[list[str], dict[str, bool]]:
    issues: list[str] = []
    schema_valid: dict[str, bool] = {}
    for source, required_columns in INPUT_REQUIRED_COLUMNS.items():
        frame = frames[source]
        label = INPUT_LABELS[source]
        if frame.empty:
            issues.append(f"{label} input is missing or empty")
            schema_valid[source] = False
            continue
        missing = tuple(column for column in required_columns if column not in frame.columns)
        if missing:
            issues.append(f"{label} is missing required column(s): {', '.join(missing)}")
            schema_valid[source] = False
            continue
        schema_valid[source] = True
    return issues, schema_valid


def _readiness_value_issues(
    frames: dict[str, pd.DataFrame],
    schema_valid: dict[str, bool],
) -> list[str]:
    issues: list[str] = []
    for source, readiness_fields in INPUT_READINESS_FIELDS.items():
        if not schema_valid[source]:
            continue
        frame = frames[source]
        malformed = tuple(
            field
            for field in readiness_fields
            if any(_explicit_bool(value) is None for value in frame[field])
        )
        if malformed:
            issues.append(
                f"{INPUT_LABELS[source]} has malformed readiness field(s): {', '.join(malformed)}"
            )
    return issues


def _lookup_coverage_issues(
    *,
    valid_tickers: set[str],
    current_lookups: dict[tuple[str, str], dict[str, bool | None]],
    schema_valid: dict[str, bool],
) -> list[str]:
    issues: list[str] = []
    for _, source, field in CANONICAL_LANES:
        if not schema_valid[source]:
            continue
        lookup = current_lookups[(source, field)]
        unavailable = sum(1 for ticker in valid_tickers if lookup.get(ticker) is None)
        if unavailable:
            issues.append(
                f"{INPUT_LABELS[source]} has unavailable {field} value(s) for {unavailable} ticker(s)"
            )
    return issues


def _missing_field_parse_issues(
    *,
    valid_tickers: set[str],
    current_lookups: dict[tuple[str, str], dict[str, bool | None]],
    missing_dcf: dict[str, _MissingDcfFields],
    dcf_schema_valid: bool,
) -> list[str]:
    if not dcf_schema_valid:
        return []
    inconsistent = 0
    unknown = 0
    for ticker in valid_tickers:
        parse = missing_dcf.get(ticker)
        required_by_lane = (
            (
                "fundamentals",
                current_lookups[("ticker", "fundamentals_ready")].get(ticker),
                FUNDAMENTALS_FIELDS,
            ),
            (
                "dcf",
                current_lookups[("ticker", "dcf_ready")].get(ticker),
                CANONICAL_DCF_FIELDS,
            ),
            (
                "share_count",
                current_lookups[("dcf", "has_shares_outstanding")].get(ticker),
                ("shares_outstanding",),
            ),
        )
        for _, current_ready, required_fields in required_by_lane:
            if current_ready is not False:
                continue
            if parse is None or not parse.valid or not any(field in parse.fields for field in required_fields):
                inconsistent += 1
            if parse is not None and parse.unknown_tokens:
                unknown += 1
    issues: list[str] = []
    if inconsistent:
        issues.append(
            "DCF readiness has unavailable or lane-inconsistent missing_dcf_fields "
            f"for {inconsistent} ticker-lane value(s)"
        )
    if unknown:
        issues.append(
            "DCF readiness has unrecognized missing_dcf_fields tokens in "
            f"{unknown} blocked ticker-lane value(s)"
        )
    return issues


def _blocker(code: str, fields: tuple[str, ...] = (), detail: str = "") -> _CurrentBlocker:
    return _CurrentBlocker(
        code=code,
        fields=fields,
        detail=detail,
        next_safe_review=NEXT_SAFE_REVIEW[code],
    )


def _unknown_missing_field_detail(parse: _MissingDcfFields) -> str:
    if not parse.unknown_tokens:
        return ""
    return (
        " Unrecognized missing-field token(s): "
        f"{', '.join(parse.unknown_tokens)}; they are not reported as canonical blocker fields."
    )


def _current_blocker(
    *,
    ticker: str,
    lane: str,
    current_ready: bool | None,
    missing_dcf: dict[str, _MissingDcfFields],
    dcf_schema_valid: bool,
    canonical_tickers: set[str],
    fundamentals_schema_valid: bool,
) -> _CurrentBlocker:
    if current_ready is None:
        return _blocker(
            "current_readiness_input_unavailable",
            detail="The authoritative current readiness input is unavailable or malformed.",
        )
    if current_ready:
        return _blocker("none", detail="No current blocker is reported for this lane.")
    if lane == "price":
        return _blocker("current_price_missing", detail="Current saved price readiness is false.")
    if lane == "peer_mapping":
        return _blocker("current_peer_mapping_missing", detail="Current saved peer mapping readiness is false.")
    if lane == "peer_valuation_inputs":
        return _blocker(
            "current_peer_valuation_inputs_missing",
            detail="Current saved peer valuation-input readiness is false.",
        )

    if not dcf_schema_valid:
        return _blocker(
            "current_readiness_input_unavailable",
            detail="The current DCF readiness input is unavailable or malformed.",
        )
    missing = missing_dcf.get(ticker)
    if missing is None:
        return _blocker(
            "current_readiness_input_unavailable",
            detail="The current DCF readiness row for this ticker is unavailable.",
        )
    unknown_detail = _unknown_missing_field_detail(missing)
    if lane == "share_count":
        if not missing.valid or "shares_outstanding" not in missing.fields:
            return _blocker(
                "current_readiness_input_unavailable",
                detail=(
                    "Current saved share-count readiness is false, but missing_dcf_fields does not name "
                    f"shares_outstanding.{unknown_detail}"
                ),
            )
        return _blocker(
            "current_required_fields_missing",
            ("shares_outstanding",),
            "Current DCF readiness reports missing required fields." + unknown_detail,
        )

    fields = missing.fields if lane == "dcf" else tuple(
        field for field in missing.fields if field in FUNDAMENTALS_FIELDS
    )
    if not missing.valid or not fields:
        lane_label = "DCF" if lane == "dcf" else "fundamentals"
        return _blocker(
            "current_readiness_input_unavailable",
            detail=(
                f"Current saved {lane_label} readiness is false, but missing_dcf_fields has no "
                f"recognized field for this lane.{unknown_detail}"
            ),
        )
    if not fundamentals_schema_valid:
        return _blocker(
            "current_readiness_input_unavailable",
            detail="The current canonical fundamentals input is unavailable or malformed.",
        )
    if ticker not in canonical_tickers:
        return _blocker(
            "current_canonical_row_missing",
            fields,
            "No current canonical fundamentals row is present." + unknown_detail,
        )
    return _blocker(
        "current_required_fields_missing",
        fields,
        "Current DCF readiness reports missing required fields." + unknown_detail,
    )


def _review_date_key(value: object, append_index: int) -> tuple[bool, tuple[int, int, int]]:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return False, (0, -1, append_index)
    return True, (1, parsed.toordinal(), append_index)


def _reconciliation_state(*, current_ready: bool | None, proof_exists: bool, supporting: bool) -> str:
    if current_ready is None:
        return "not_applicable"
    if current_ready and supporting:
        return "current_supported_with_matching_proof"
    if not current_ready and supporting:
        return "historical_supported_currently_blocked"
    if current_ready:
        return "current_ready_proof_not_supporting"
    if proof_exists:
        return "currently_blocked_with_non_supporting_history"
    return "no_proof_record"


def _state_reason(state: str) -> str:
    reasons = {
        "current_supported_with_matching_proof": (
            "Current saved readiness is true and the latest applicable dated proof outcome is explicitly supporting."
        ),
        "historical_supported_currently_blocked": (
            "Historical supporting proof conflicts with current saved readiness; current readiness remains authoritative."
        ),
        "current_ready_proof_not_supporting": (
            "Current saved readiness is true, but the latest applicable proof is absent, malformed, or non-supporting."
        ),
        "currently_blocked_with_non_supporting_history": (
            "Current saved readiness is blocked and the latest applicable proof is non-supporting."
        ),
        "no_proof_record": "Current saved readiness is blocked and no applicable proof row is recorded.",
        "not_applicable": "The authoritative current readiness field is missing or malformed; no state is inferred.",
    }
    return reasons[state]


def build_proof_readiness_reconciliation(
    *,
    proofs: Sequence[ReviewedBatchProof],
    ticker_readiness: pd.DataFrame,
    dcf_readiness: pd.DataFrame,
    peer_readiness: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> ProofReadinessReconciliationSummary:
    frames = {
        "ticker": _normalized_columns(ticker_readiness),
        "dcf": _normalized_columns(dcf_readiness),
        "peer": _normalized_columns(peer_readiness),
        "fundamentals": _normalized_columns(fundamentals),
    }
    tickers = _valid_tickers(frames["ticker"])
    if not tickers:
        return ProofReadinessReconciliationSummary(
            rows=(),
            status_counts=(),
            conflict_counts_by_lane=(),
            input_status="unavailable",
            input_message="Current ticker readiness is missing or has no valid ticker rows; reconciliation cannot infer state.",
            proof_applicability_counts=(),
            current_blocker_counts=(),
        )

    current_lookups = {
        (source, field): _readiness_lookup(frames[source], field)
        for _, source, field in CANONICAL_LANES
    }
    valid_set = set(tickers)
    input_issues, schema_valid = _schema_issues(frames)
    input_issues.extend(_readiness_value_issues(frames, schema_valid))
    input_issues.extend(
        _lookup_coverage_issues(
            valid_tickers=valid_set,
            current_lookups=current_lookups,
            schema_valid=schema_valid,
        )
    )
    missing_dcf = _missing_dcf_lookup(frames["dcf"])
    input_issues.extend(
        _missing_field_parse_issues(
            valid_tickers=valid_set,
            current_lookups=current_lookups,
            missing_dcf=missing_dcf,
            dcf_schema_valid=schema_valid["dcf"],
        )
    )
    canonical_tickers = set(_valid_tickers(frames["fundamentals"]))

    latest: dict[tuple[str, str], _LatestProof] = {}
    for append_index, proof in enumerate(proofs):
        mapping = LANE_MAPPINGS.get(str(proof.lane or "").strip().lower())
        if mapping is None:
            continue
        canonical_lane, _, _ = mapping
        review_date_valid, sort_key = _review_date_key(proof.review_date, append_index)
        candidate = _LatestProof(proof=proof, review_date_valid=review_date_valid, sort_key=sort_key)
        for ticker in _ticker_tokens(proof.tickers, valid_set):
            key = (ticker, canonical_lane)
            existing = latest.get(key)
            if existing is None or candidate.sort_key > existing.sort_key:
                latest[key] = candidate

    rows: list[ProofReadinessReconciliationRow] = []
    for ticker in tickers:
        for lane, source, field in CANONICAL_LANES:
            current_ready = current_lookups[(source, field)].get(ticker)
            latest_proof = latest.get((ticker, lane))
            proof_exists = latest_proof is not None
            latest_outcome = (
                str(latest_proof.proof.final_outcome or "").strip().lower() if latest_proof is not None else ""
            )
            proof_applicability = _proof_applicability(
                latest_proof,
                ticker=ticker,
                valid_tickers=valid_set,
            )
            supporting = proof_applicability == "explicit_ticker_change"
            state = _reconciliation_state(
                current_ready=current_ready,
                proof_exists=proof_exists,
                supporting=supporting,
            )
            blocker = _current_blocker(
                ticker=ticker,
                lane=lane,
                current_ready=current_ready,
                missing_dcf=missing_dcf,
                dcf_schema_valid=schema_valid["dcf"],
                canonical_tickers=canonical_tickers,
                fundamentals_schema_valid=schema_valid["fundamentals"],
            )
            next_safe_review = blocker.next_safe_review
            if proof_applicability in {"scope_only_not_supported", "missing_ticker_change_detail"}:
                next_safe_review = "Review the proof row; do not reuse it as ticker-level support. " + next_safe_review
            rows.append(
                ProofReadinessReconciliationRow(
                    ticker=ticker,
                    lane=lane,
                    current_field=field,
                    current_ready=current_ready,
                    latest_batch_id=latest_proof.proof.batch_id if latest_proof is not None else "",
                    latest_review_date=latest_proof.proof.review_date if latest_proof is not None else "",
                    latest_outcome=latest_outcome,
                    review_date_valid=latest_proof.review_date_valid if latest_proof is not None else False,
                    state=state,
                    reason=_state_reason(state),
                    proof_applicability=proof_applicability,
                    current_blocker_code=blocker.code,
                    current_blocker_fields=blocker.fields,
                    current_blocker_detail=blocker.detail,
                    next_safe_review=next_safe_review,
                    historical_payload_status=(
                        "structured_payload_not_recorded" if proof_exists else ""
                    ),
                    historical_evidence_limit=HISTORICAL_EVIDENCE_LIMIT if proof_exists else "",
                )
            )

    rows.sort(key=lambda row: (STATE_PRIORITY[row.state], row.lane, row.ticker))
    status_counts = Counter(row.state for row in rows)
    conflict_counts = Counter(
        row.lane for row in rows if row.state == "historical_supported_currently_blocked"
    )
    proof_applicability_counts = Counter(row.proof_applicability for row in rows)
    current_blocker_counts = Counter(row.current_blocker_code for row in rows)
    input_status = "partial" if input_issues else "ready"
    input_message = (
        f"Current input issue(s): {'; '.join(dict.fromkeys(input_issues))}. "
        "Affected lane diagnoses remain unavailable while independent lanes are preserved."
        if input_issues
        else (
            "Current ticker, DCF, peer, and canonical fundamentals inputs are available for read-only "
            "reconciliation."
        )
    )
    return ProofReadinessReconciliationSummary(
        rows=tuple(rows),
        status_counts=tuple(sorted(status_counts.items())),
        conflict_counts_by_lane=tuple(sorted(conflict_counts.items())),
        proof_applicability_counts=tuple(sorted(proof_applicability_counts.items())),
        current_blocker_counts=tuple(sorted(current_blocker_counts.items())),
        input_status=input_status,
        input_message=input_message,
    )


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, low_memory=False).fillna("")
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def load_proof_readiness_reconciliation(
    *,
    root: Path,
    data_dir: Path | None = None,
) -> ProofReadinessReconciliationSummary:
    resolved = Path(root).expanduser().resolve()
    data = Path(data_dir).expanduser().resolve() if data_dir is not None else resolved / "data"
    return build_proof_readiness_reconciliation(
        proofs=load_reviewed_batch_proofs(data / "reviewed_batch_proofs.csv"),
        ticker_readiness=_read_csv(data / "reports" / "ticker_readiness_report.csv"),
        dcf_readiness=_read_csv(data / "reports" / "dcf_readiness_report.csv"),
        peer_readiness=_read_csv(data / "reports" / "peer_readiness_report.csv"),
        fundamentals=_read_csv(data / "fundamentals.csv"),
    )


def filter_reconciliation_rows(
    summary: ProofReadinessReconciliationSummary,
    *,
    tickers: Sequence[str] = (),
    top_n: int = 20,
) -> tuple[ProofReadinessReconciliationRow, ...]:
    selected = {str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}
    rows = tuple(row for row in summary.rows if not selected or row.ticker in selected)
    return rows[: max(int(top_n), 0)]


def _parse_ticker_filter(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token.strip().upper() for token in str(value or "").split(",") if token.strip()))


def proof_readiness_reconciliation_payload(
    summary: ProofReadinessReconciliationSummary,
    *,
    tickers: Sequence[str] = (),
    top_n: int = 20,
) -> dict[str, object]:
    return {
        "input_status": summary.input_status,
        "input_message": summary.input_message,
        "total_rows": len(summary.rows),
        "status_counts": dict(summary.status_counts),
        "conflict_counts_by_lane": dict(summary.conflict_counts_by_lane),
        "proof_applicability_counts": dict(summary.proof_applicability_counts),
        "current_blocker_counts": dict(summary.current_blocker_counts),
        "displayed_tickers": [str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()],
        "rows": [
            asdict(row)
            for row in filter_reconciliation_rows(summary, tickers=tickers, top_n=top_n)
        ],
        "boundary": (
            "Current saved readiness remains authoritative; reconciliation does not restore data, promote readiness, "
            "or rewrite proof history. Current blocker diagnosis describes observable saved inputs and does not establish "
            "the historical cause."
        ),
    }


def render_proof_readiness_reconciliation(
    summary: ProofReadinessReconciliationSummary,
    *,
    tickers: Sequence[str] = (),
    top_n: int = 20,
) -> str:
    rows = filter_reconciliation_rows(summary, tickers=tickers, top_n=top_n)
    conflict_total = sum(dict(summary.conflict_counts_by_lane).values())
    lines = [
        "Proof-Readiness Reconciliation",
        "Read-only: compares append-only historical proof with current saved readiness; it writes no files.",
        "Research-only: this is evidence interpretation, not investment advice, a ranking, recommendation, or trade instruction.",
        "Current saved readiness remains authoritative; reconciliation does not restore data, promote readiness, or rewrite proof history.",
        "",
        f"Input status: {summary.input_status}",
        f"Input detail: {summary.input_message}",
        f"Reconciliation rows: {len(summary.rows):,}",
        f"Historical-support/current-readiness conflicts: {conflict_total:,}",
        "",
        "State counts:",
    ]
    for state, count in summary.status_counts:
        lines.append(f"- {state}: {count:,}")
    lines.extend(["", "Proof applicability counts:"])
    if summary.proof_applicability_counts:
        for applicability, count in summary.proof_applicability_counts:
            lines.append(f"- {applicability}: {count:,}")
    else:
        lines.append("- none")
    lines.extend(["", "Current blocker counts:"])
    if summary.current_blocker_counts:
        for blocker, count in summary.current_blocker_counts:
            lines.append(f"- {blocker}: {count:,}")
    else:
        lines.append("- none")
    lines.extend(["", "Conflict counts by lane:"])
    if summary.conflict_counts_by_lane:
        for lane, count in summary.conflict_counts_by_lane:
            lines.append(f"- {lane}: {count:,}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            f"Rows shown: {len(rows):,}",
            "Ticker | Lane | Current ready | Latest proof | Review date | Reconciliation state | Proof applicability | Current blocker | Next safe review",
            "--- | --- | --- | --- | --- | --- | --- | --- | ---",
        ]
    )
    for row in rows:
        current = "unavailable" if row.current_ready is None else str(row.current_ready).lower()
        latest = f"{row.latest_batch_id}: {row.latest_outcome}" if row.latest_batch_id else "not recorded"
        review_date = row.latest_review_date or "not recorded"
        blocker = row.current_blocker_code
        if row.current_blocker_fields:
            blocker += f" ({', '.join(row.current_blocker_fields)})"
        lines.append(
            f"{row.ticker} | {row.lane} | {current} | {latest} | {review_date} | {row.state} | "
            f"{row.proof_applicability} | {blocker} | {row.next_safe_review}"
        )
    if not rows:
        lines.append("No rows match the requested display filter.")
    lines.extend(
        [
            "",
            "Next safe command: make proof-readiness-reconciliation TOP_N=20",
            "Boundary: current blocker diagnosis describes observable saved inputs; it does not establish the historical cause, source rights, field scope, provenance, payload truth, or commercial use.",
        ]
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcile historical proof outcomes with current readiness.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--tickers", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = load_proof_readiness_reconciliation(root=Path(args.root))
    tickers = _parse_ticker_filter(args.tickers)
    if args.json:
        print(
            json.dumps(
                proof_readiness_reconciliation_payload(summary, tickers=tickers, top_n=args.top_n),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(render_proof_readiness_reconciliation(summary, tickers=tickers, top_n=args.top_n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
