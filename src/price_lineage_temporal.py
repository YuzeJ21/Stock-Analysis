"""Shared fail-closed temporal review for daily price lineage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
@dataclass(frozen=True)
class PriceTemporalReview:
    status: str
    observation_date: str
    availability_at: str
    retrieved_at: str
    review_cutoff: str
    blockers: tuple[str, ...]


def _observation_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _aware_timestamp(value: object, *, label: str) -> tuple[datetime | None, str | None]:
    if value is None or not str(value).strip():
        return None, "missing_retrieved_at" if label == "retrieved_at" else f"{label}_required"
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None, f"invalid_{label}"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, f"{label}_timezone_required"
    return parsed.astimezone(timezone.utc), None


def review_daily_price_retrieval(
    observation_date: object,
    retrieved_at: object,
    *,
    review_cutoff: object,
) -> PriceTemporalReview:
    """Review daily OHLCV availability without inferring provider publication time."""

    observed = _observation_date(observation_date)
    if observed is None:
        return PriceTemporalReview(
            status="temporal_review_required",
            observation_date="",
            availability_at="",
            retrieved_at="",
            review_cutoff="",
            blockers=("invalid_observation_date",),
        )

    availability = datetime.combine(observed + timedelta(days=1), time.min, timezone.utc)
    retrieved, retrieved_error = _aware_timestamp(retrieved_at, label="retrieved_at")
    if retrieved_error:
        return PriceTemporalReview(
            status="temporal_review_required",
            observation_date=observed.isoformat(),
            availability_at=availability.isoformat(),
            retrieved_at="",
            review_cutoff="",
            blockers=(retrieved_error,),
        )

    cutoff, cutoff_error = _aware_timestamp(review_cutoff, label="review_cutoff")
    if cutoff_error:
        return PriceTemporalReview(
            status="temporal_review_required",
            observation_date=observed.isoformat(),
            availability_at=availability.isoformat(),
            retrieved_at=retrieved.isoformat(),
            review_cutoff="",
            blockers=(cutoff_error,),
        )

    blockers: list[str] = []
    if retrieved < availability:
        blockers.append("retrieved_before_observation_available")
    if retrieved > cutoff:
        blockers.append("retrieved_after_review_cutoff")
    return PriceTemporalReview(
        status="temporal_complete" if not blockers else "temporal_review_required",
        observation_date=observed.isoformat(),
        availability_at=availability.isoformat(),
        retrieved_at=retrieved.isoformat(),
        review_cutoff=cutoff.isoformat(),
        blockers=tuple(blockers),
    )
