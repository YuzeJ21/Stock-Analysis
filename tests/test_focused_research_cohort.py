import pandas as pd

from src.focused_research_cohort import build_focused_cohort, focused_cohort_frame


def _readiness(*rows):
    return pd.DataFrame(rows)


def _universe(*rows):
    return pd.DataFrame(rows)


def test_focused_cohort_is_deterministic_and_prioritizes_reviewability_without_ranking_language():
    readiness = _readiness(
        {"ticker": "CCC", "name": "C Co", "price_ready": True, "fundamentals_ready": False, "dcf_ready": False, "peer_ready": False, "in_active_universe": False},
        {"ticker": "AAA", "name": "A Co", "price_ready": True, "fundamentals_ready": True, "dcf_ready": True, "peer_ready": True, "in_active_universe": True},
        {"ticker": "BBB", "name": "B Co", "price_ready": True, "fundamentals_ready": True, "dcf_ready": True, "peer_ready": False, "in_active_universe": False},
    )
    universe = _universe(
        {"ticker": "BBB", "asset_type": "company", "is_active_listing": True, "sector": "Industrials", "industry": "Tools"},
        {"ticker": "CCC", "asset_type": "company", "is_active_listing": True, "sector": "Health Care", "industry": "Devices"},
        {"ticker": "AAA", "asset_type": "company", "is_active_listing": True, "sector": "Technology", "industry": "Software"},
    )

    first = build_focused_cohort(readiness, universe, target_size=3, minimum_size=2, profile_freshness="current")
    second = build_focused_cohort(readiness.sample(frac=1, random_state=3), universe.sample(frac=1, random_state=4), target_size=3, minimum_size=2, profile_freshness="current")

    assert [member.ticker for member in first.members] == ["AAA", "BBB", "CCC"]
    assert first == second
    assert first.status == "ready"
    rendered = focused_cohort_frame(first).to_string(index=False).lower()
    for prohibited in ("buy", "sell", "winner", "recommendation score", "rank"):
        assert prohibited not in rendered


def test_focused_cohort_excludes_non_companies_inactive_rows_and_non_price_ready_rows():
    readiness = _readiness(
        {"ticker": "KEEP", "name": "Keep Co", "price_ready": True},
        {"ticker": "ETF", "name": "Fund", "price_ready": True},
        {"ticker": "OLD", "name": "Old Co", "price_ready": True},
        {"ticker": "MISS", "name": "Missing Price", "price_ready": False},
    )
    universe = _universe(
        {"ticker": "KEEP", "asset_type": "company", "is_active_listing": True},
        {"ticker": "ETF", "asset_type": "etf", "is_active_listing": True},
        {"ticker": "OLD", "asset_type": "company", "is_active_listing": False},
        {"ticker": "MISS", "asset_type": "company", "is_active_listing": True},
    )

    cohort = build_focused_cohort(readiness, universe, target_size=25, minimum_size=25)

    assert [member.ticker for member in cohort.members] == ["KEEP"]
    assert cohort.status == "awaiting_reviewed_source"
    assert cohort.eligible_count == 1
    assert cohort.requested_size == 25


def test_focused_cohort_deduplicates_tickers_and_preserves_source_backed_context():
    readiness = _readiness(
        {"ticker": "DUP", "name": "Duplicate Co", "price_ready": True, "fundamentals_ready": False, "dcf_ready": False, "blocked_features": "fundamentals, dcf", "updated_at": "2026-07-01"},
        {"ticker": "DUP", "name": "Duplicate Co", "price_ready": True, "fundamentals_ready": True, "dcf_ready": True, "blocked_features": "peers", "updated_at": "2026-07-02"},
    )
    universe = _universe(
        {"ticker": "DUP", "asset_type": "company", "is_active_listing": True, "sector": "Technology", "industry": "Hardware"},
    )

    cohort = build_focused_cohort(
        readiness,
        universe,
        target_size=25,
        minimum_size=25,
        profile_freshness="stale",
        last_review_dates={"DUP": "2026-06-30"},
    )

    assert len(cohort.members) == 1
    member = cohort.members[0]
    assert member.ticker == "DUP"
    assert member.sector == "Technology"
    assert member.industry == "Hardware"
    assert member.usable_lanes == ("price", "fundamentals", "dcf")
    assert member.blocked_lanes == ("peers",)
    assert member.freshness_state == "stale"
    assert member.last_review_date == "2026-06-30"


def test_focused_cohort_missing_inputs_fail_closed():
    cohort = build_focused_cohort(pd.DataFrame(), pd.DataFrame(), target_size=25, minimum_size=25)

    assert cohort.status == "unavailable"
    assert cohort.members == ()
    assert cohort.eligible_count == 0
    assert cohort.message == "Focused cohort inputs are unavailable."
