"""Reconcile historical proof outcomes with current saved readiness.

This module is read-only. It does not restore canonical data, promote readiness,
rewrite proof history, or infer source rights, provenance, or payload truth.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Sequence

import pandas as pd

from src.reviewed_batch_proof import ReviewedBatchProof, load_reviewed_batch_proofs


SUPPORTING_OUTCOMES = frozenset({"supported", "auto_supported", "human_reviewed_supported"})

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


@dataclass(frozen=True)
class ProofReadinessReconciliationSummary:
    rows: tuple[ProofReadinessReconciliationRow, ...]
    status_counts: tuple[tuple[str, int], ...]
    conflict_counts_by_lane: tuple[tuple[str, int], ...]
    input_status: str
    input_message: str


@dataclass(frozen=True)
class _LatestProof:
    proof: ReviewedBatchProof
    review_date_valid: bool
    sort_key: tuple[int, int, int]


def _normalized_columns(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower().replace(" ", "_") for column in normalized.columns]
    return normalized


def _explicit_bool(value: object) -> bool | None:
    text = str(value or "").strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def _readiness_lookup(frame: pd.DataFrame | None, field: str) -> dict[str, bool | None]:
    normalized = _normalized_columns(frame)
    if normalized.empty or "ticker" not in normalized.columns or field not in normalized.columns:
        return {}
    return {
        str(row["ticker"]).strip().upper(): _explicit_bool(row[field])
        for _, row in normalized.iterrows()
        if str(row["ticker"]).strip()
    }


def _valid_tickers(frame: pd.DataFrame | None) -> tuple[str, ...]:
    normalized = _normalized_columns(frame)
    if normalized.empty or "ticker" not in normalized.columns:
        return ()
    values = {str(value).strip().upper() for value in normalized["ticker"] if str(value).strip()}
    return tuple(sorted(values))


def _proof_tickers(value: object, valid_tickers: set[str]) -> tuple[str, ...]:
    tokens = (token.strip().upper() for token in re.split(r"[,;]", str(value or "")))
    return tuple(dict.fromkeys(token for token in tokens if token and token in valid_tickers))


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
) -> ProofReadinessReconciliationSummary:
    tickers = _valid_tickers(ticker_readiness)
    if not tickers:
        return ProofReadinessReconciliationSummary(
            rows=(),
            status_counts=(),
            conflict_counts_by_lane=(),
            input_status="unavailable",
            input_message="Current ticker readiness is missing or has no valid ticker rows; reconciliation cannot infer state.",
        )

    frames = {
        "ticker": ticker_readiness,
        "dcf": dcf_readiness,
        "peer": peer_readiness,
    }
    current_lookups = {
        (source, field): _readiness_lookup(frames[source], field)
        for _, source, field in CANONICAL_LANES
    }
    missing_inputs = [
        label
        for label, frame in (("DCF readiness", dcf_readiness), ("peer readiness", peer_readiness))
        if frame is None or frame.empty
    ]

    valid_set = set(tickers)
    latest: dict[tuple[str, str], _LatestProof] = {}
    for append_index, proof in enumerate(proofs):
        mapping = LANE_MAPPINGS.get(str(proof.lane or "").strip().lower())
        if mapping is None:
            continue
        canonical_lane, _, _ = mapping
        review_date_valid, sort_key = _review_date_key(proof.review_date, append_index)
        candidate = _LatestProof(proof=proof, review_date_valid=review_date_valid, sort_key=sort_key)
        for ticker in _proof_tickers(proof.tickers, valid_set):
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
            supporting = bool(
                latest_proof is not None
                and latest_proof.review_date_valid
                and latest_outcome in SUPPORTING_OUTCOMES
            )
            state = _reconciliation_state(
                current_ready=current_ready,
                proof_exists=proof_exists,
                supporting=supporting,
            )
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
                )
            )

    rows.sort(key=lambda row: (STATE_PRIORITY[row.state], row.lane, row.ticker))
    status_counts = Counter(row.state for row in rows)
    conflict_counts = Counter(
        row.lane for row in rows if row.state == "historical_supported_currently_blocked"
    )
    input_status = "partial" if missing_inputs else "ready"
    input_message = (
        f"Missing current input(s): {', '.join(missing_inputs)}; affected lanes remain not_applicable."
        if missing_inputs
        else "Current ticker, DCF, and peer readiness inputs are available for read-only reconciliation."
    )
    return ProofReadinessReconciliationSummary(
        rows=tuple(rows),
        status_counts=tuple(sorted(status_counts.items())),
        conflict_counts_by_lane=tuple(sorted(conflict_counts.items())),
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


def load_proof_readiness_reconciliation(*, root: Path) -> ProofReadinessReconciliationSummary:
    resolved = Path(root).expanduser().resolve()
    data = resolved / "data"
    return build_proof_readiness_reconciliation(
        proofs=load_reviewed_batch_proofs(data / "reviewed_batch_proofs.csv"),
        ticker_readiness=_read_csv(data / "reports" / "ticker_readiness_report.csv"),
        dcf_readiness=_read_csv(data / "reports" / "dcf_readiness_report.csv"),
        peer_readiness=_read_csv(data / "reports" / "peer_readiness_report.csv"),
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
