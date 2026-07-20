from datetime import datetime, timezone

import pytest

from src.price_lineage_temporal import review_daily_price_retrieval


def test_daily_price_temporal_review_normalizes_explicit_offsets_to_utc():
    review = review_daily_price_retrieval(
        "2026-01-02",
        "2026-01-03T18:00:00-05:00",
        review_cutoff="2026-01-04T00:00:00Z",
    )

    assert review.status == "temporal_complete"
    assert review.availability_at == "2026-01-03T00:00:00+00:00"
    assert review.retrieved_at == "2026-01-03T23:00:00+00:00"
    assert review.review_cutoff == "2026-01-04T00:00:00+00:00"
    assert review.blockers == ()


@pytest.mark.parametrize(
    ("retrieved_at", "cutoff", "blocker"),
    [
        ("", "2026-01-04T00:00:00Z", "missing_retrieved_at"),
        ("not-a-time", "2026-01-04T00:00:00Z", "invalid_retrieved_at"),
        ("2026-01-03T23:00:00", "2026-01-04T00:00:00Z", "retrieved_at_timezone_required"),
        ("2026-01-02T23:59:59Z", "2026-01-04T00:00:00Z", "retrieved_before_observation_available"),
        ("2026-01-04T00:00:01Z", "2026-01-04T00:00:00Z", "retrieved_after_review_cutoff"),
        ("2026-01-03T23:00:00Z", "", "review_cutoff_required"),
        ("2026-01-03T23:00:00Z", "2026-01-04T00:00:00", "review_cutoff_timezone_required"),
    ],
)
def test_daily_price_temporal_review_fails_closed(retrieved_at: str, cutoff: str, blocker: str):
    review = review_daily_price_retrieval(
        "2026-01-02",
        retrieved_at,
        review_cutoff=cutoff,
    )

    assert review.status == "temporal_review_required"
    assert blocker in review.blockers


def test_daily_price_temporal_review_rejects_invalid_observation_date():
    review = review_daily_price_retrieval(
        "not-a-date",
        "2026-01-03T23:00:00Z",
        review_cutoff="2026-01-04T00:00:00Z",
    )

    assert review.blockers == ("invalid_observation_date",)


def test_daily_price_temporal_review_accepts_aware_datetime_cutoff():
    review = review_daily_price_retrieval(
        "2026-01-02",
        "2026-01-03T23:00:00Z",
        review_cutoff=datetime(2026, 1, 4, tzinfo=timezone.utc),
    )

    assert review.status == "temporal_complete"
