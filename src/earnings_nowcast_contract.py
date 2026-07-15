from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Iterable


_FISCAL_PERIOD_PATTERN = re.compile(r"^\d{4}-Q[1-4]$")
_HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NowcastState(StrEnum):
    BLOCKED = "blocked"
    BASELINE_READY = "baseline_ready"
    SIGNAL_CONTEXT_READY = "signal_context_ready"
    BACKTEST_READY = "backtest_ready"
    CALIBRATED = "calibrated"
    EXCLUDED = "excluded"


class FreshnessState(StrEnum):
    CURRENT = "current"
    REVIEW_DUE = "review_due"
    STALE_OR_UNKNOWN = "stale_or_unknown"


class SignalDirection(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNCLEAR = "unclear"


class SignalReviewState(StrEnum):
    CANDIDATE_CONTEXT_ONLY = "candidate_context_only"
    SUPPORTED = "supported"
    STILL_BLOCKED = "still_blocked"
    SKIPPED = "skipped"
    EXCLUDED = "excluded"


def _required_text(value: object, *, label: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{label} is required")
    return cleaned


def _ticker(value: object) -> str:
    return _required_text(value, label="ticker").upper()


def _fiscal_period(value: object) -> str:
    cleaned = _required_text(value, label="fiscal_period").upper()
    if not _FISCAL_PERIOD_PATTERN.fullmatch(cleaned):
        raise ValueError("fiscal_period must use YYYY-Q[1-4]")
    return cleaned


def _iso_date(value: object, *, label: str) -> str:
    cleaned = _required_text(value, label=label)
    try:
        return date.fromisoformat(cleaned).isoformat()
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD") from exc


def parse_utc_timestamp(value: object, *, label: str = "timestamp") -> datetime:
    cleaned = _required_text(value, label=label)
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _utc_string(value: object, *, label: str) -> str:
    return parse_utc_timestamp(value, label=label).isoformat()


def _optional_finite(value: object, *, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{label} must be finite")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def validate_cutoff(event_timestamp: object, cutoff: object, *, label: str) -> bool:
    event = parse_utc_timestamp(event_timestamp, label=f"{label} timestamp")
    boundary = parse_utc_timestamp(cutoff, label="forecast cutoff")
    if event > boundary:
        raise ValueError(f"{label} timestamp {event.isoformat()} is after forecast cutoff {boundary.isoformat()}")
    return True


@dataclass(frozen=True)
class QuarterlyActual:
    ticker: str
    fiscal_period: str
    period_end_date: str
    reported_at: str
    revenue_actual: float | None
    eps_actual: float | None
    source: str
    source_ref: str
    retrieved_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _ticker(self.ticker))
        object.__setattr__(self, "fiscal_period", _fiscal_period(self.fiscal_period))
        object.__setattr__(self, "period_end_date", _iso_date(self.period_end_date, label="period_end_date"))
        object.__setattr__(self, "reported_at", _utc_string(self.reported_at, label="reported_at"))
        object.__setattr__(self, "retrieved_at", _utc_string(self.retrieved_at, label="retrieved_at"))
        object.__setattr__(self, "revenue_actual", _optional_finite(self.revenue_actual, label="revenue_actual"))
        object.__setattr__(self, "eps_actual", _optional_finite(self.eps_actual, label="eps_actual"))
        object.__setattr__(self, "source", _required_text(self.source, label="source"))
        object.__setattr__(self, "source_ref", _required_text(self.source_ref, label="source_ref"))
        if self.revenue_actual is None and self.eps_actual is None:
            raise ValueError("at least one quarterly actual metric is required")

    def available_at(self, cutoff: object) -> bool:
        return validate_cutoff(self.reported_at, cutoff, label="quarterly actual")


@dataclass(frozen=True)
class ConsensusSnapshot:
    ticker: str
    fiscal_period: str
    snapshot_at: str
    revenue_consensus: float | None
    eps_consensus: float | None
    source: str
    retrieved_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _ticker(self.ticker))
        object.__setattr__(self, "fiscal_period", _fiscal_period(self.fiscal_period))
        object.__setattr__(self, "snapshot_at", _utc_string(self.snapshot_at, label="snapshot_at"))
        object.__setattr__(self, "retrieved_at", _utc_string(self.retrieved_at, label="retrieved_at"))
        object.__setattr__(self, "revenue_consensus", _optional_finite(self.revenue_consensus, label="revenue_consensus"))
        object.__setattr__(self, "eps_consensus", _optional_finite(self.eps_consensus, label="eps_consensus"))
        object.__setattr__(self, "source", _required_text(self.source, label="source"))
        if self.revenue_consensus is None and self.eps_consensus is None:
            raise ValueError("at least one consensus metric is required")

    def available_at(self, cutoff: object) -> bool:
        return validate_cutoff(self.snapshot_at, cutoff, label="consensus snapshot")


@dataclass(frozen=True)
class EvidenceSignal:
    signal_id: str
    target_ticker: str
    source_ticker: str | None
    fiscal_period: str
    as_of_timestamp: str
    signal_type: str
    direction: SignalDirection | str
    affected_metric: str
    confidence_band: str
    evidence_source: str
    evidence_published_at: str
    evidence_excerpt_hash: str
    peer_relationship_state: str
    review_state: SignalReviewState | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", _required_text(self.signal_id, label="signal_id"))
        object.__setattr__(self, "target_ticker", _ticker(self.target_ticker))
        object.__setattr__(self, "source_ticker", _ticker(self.source_ticker) if self.source_ticker else None)
        object.__setattr__(self, "fiscal_period", _fiscal_period(self.fiscal_period))
        object.__setattr__(self, "as_of_timestamp", _utc_string(self.as_of_timestamp, label="as_of_timestamp"))
        object.__setattr__(self, "signal_type", _required_text(self.signal_type, label="signal_type"))
        object.__setattr__(self, "direction", SignalDirection(str(self.direction)))
        metric = _required_text(self.affected_metric, label="affected_metric").lower()
        if metric not in {"revenue", "eps", "gross_margin", "bookings"}:
            raise ValueError("affected_metric is not supported")
        object.__setattr__(self, "affected_metric", metric)
        confidence = _required_text(self.confidence_band, label="confidence_band").lower()
        if confidence not in {"low", "medium", "high"}:
            raise ValueError("confidence_band must be low, medium, or high")
        object.__setattr__(self, "confidence_band", confidence)
        object.__setattr__(self, "evidence_source", _required_text(self.evidence_source, label="evidence_source"))
        object.__setattr__(
            self,
            "evidence_published_at",
            _utc_string(self.evidence_published_at, label="evidence_published_at"),
        )
        excerpt_hash = _required_text(self.evidence_excerpt_hash, label="evidence_excerpt_hash").lower()
        if not _HEX_64_PATTERN.fullmatch(excerpt_hash):
            raise ValueError("evidence_excerpt_hash must be a 64-character lowercase hex digest")
        object.__setattr__(self, "evidence_excerpt_hash", excerpt_hash)
        object.__setattr__(
            self,
            "peer_relationship_state",
            _required_text(self.peer_relationship_state, label="peer_relationship_state"),
        )
        object.__setattr__(self, "review_state", SignalReviewState(str(self.review_state)))
        validate_cutoff(self.evidence_published_at, self.as_of_timestamp, label="evidence signal")


@dataclass(frozen=True)
class ForecastSnapshot:
    forecast_id: str
    ticker: str
    fiscal_period: str
    as_of_timestamp: str
    model_version: str
    input_snapshot_hash: str
    revenue_midpoint: float | None
    revenue_low: float | None
    revenue_high: float | None
    eps_midpoint: float | None
    eps_low: float | None
    eps_high: float | None
    consensus_revenue: float | None
    consensus_eps: float | None
    revenue_gap_pct: float | None
    eps_gap_pct: float | None
    relative_classification: str
    confidence_band: str
    readiness_state: NowcastState | str
    freshness_state: FreshnessState | str
    source_ids: tuple[str, ...]
    created_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "forecast_id", _required_text(self.forecast_id, label="forecast_id"))
        object.__setattr__(self, "ticker", _ticker(self.ticker))
        object.__setattr__(self, "fiscal_period", _fiscal_period(self.fiscal_period))
        object.__setattr__(self, "as_of_timestamp", _utc_string(self.as_of_timestamp, label="as_of_timestamp"))
        object.__setattr__(self, "created_at", _utc_string(self.created_at, label="created_at"))
        object.__setattr__(self, "model_version", _required_text(self.model_version, label="model_version"))
        digest = _required_text(self.input_snapshot_hash, label="input_snapshot_hash").lower()
        if not _HEX_64_PATTERN.fullmatch(digest):
            raise ValueError("input_snapshot_hash must be a 64-character lowercase hex digest")
        object.__setattr__(self, "input_snapshot_hash", digest)
        for name in (
            "revenue_midpoint",
            "revenue_low",
            "revenue_high",
            "eps_midpoint",
            "eps_low",
            "eps_high",
            "consensus_revenue",
            "consensus_eps",
            "revenue_gap_pct",
            "eps_gap_pct",
        ):
            object.__setattr__(self, name, _optional_finite(getattr(self, name), label=name))
        self._validate_range("revenue")
        self._validate_range("eps")
        classification = _required_text(self.relative_classification, label="relative_classification").lower()
        if classification not in {"higher", "aligned", "lower", "withheld"}:
            raise ValueError("relative_classification must be higher, aligned, lower, or withheld")
        object.__setattr__(self, "relative_classification", classification)
        confidence = _required_text(self.confidence_band, label="confidence_band").lower()
        if confidence not in {"low", "medium", "high", "withheld"}:
            raise ValueError("confidence_band must be low, medium, high, or withheld")
        object.__setattr__(self, "confidence_band", confidence)
        object.__setattr__(self, "readiness_state", NowcastState(str(self.readiness_state)))
        object.__setattr__(self, "freshness_state", FreshnessState(str(self.freshness_state)))
        source_ids = tuple(sorted({_required_text(item, label="source_id") for item in self.source_ids}))
        object.__setattr__(self, "source_ids", source_ids)

    def _validate_range(self, prefix: str) -> None:
        midpoint = getattr(self, f"{prefix}_midpoint")
        low = getattr(self, f"{prefix}_low")
        high = getattr(self, f"{prefix}_high")
        values = (low, midpoint, high)
        if all(value is None for value in values):
            return
        if any(value is None for value in values) or not low <= midpoint <= high:
            raise ValueError(f"{prefix} range must satisfy low <= midpoint <= high")


def _canonicalize(value: Any) -> Any:
    if is_dataclass(value):
        return _canonicalize(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


def input_snapshot_hash(records: Iterable[object]) -> str:
    canonical_records = [
        json.dumps(_canonicalize(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        for record in records
    ]
    canonical = json.dumps(sorted(canonical_records), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
