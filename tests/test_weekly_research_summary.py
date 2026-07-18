from types import SimpleNamespace

from src.focused_research_cohort import FocusedCohort, FocusedCohortMember
from src.weekly_research_summary import build_weekly_research_summary, weekly_summary_rows


def _member(ticker: str) -> FocusedCohortMember:
    return FocusedCohortMember(
        ticker=ticker,
        company_name=f"{ticker} Company",
        sector="Technology",
        industry="Software",
        cohort_rationale="Operating company with source-backed evidence.",
        usable_lanes=("price",),
        blocked_lanes=("dcf",),
        freshness_state="current",
        last_review_date="",
        next_review_reason="Review source evidence for dcf.",
    )


def _cohort(*tickers: str) -> FocusedCohort:
    members = tuple(_member(ticker) for ticker in tickers)
    return FocusedCohort("ready", len(members), 1, len(members), members, "ready")


def _item(
    event_id: str,
    ticker: str,
    *,
    subtype: str = "sec_filing_arrived",
    family: str = "filing",
    prior: str = "old",
    current: str = "new",
    status: str = "open",
):
    event = SimpleNamespace(
        event_id=event_id,
        ticker=ticker,
        family=family,
        subtype=subtype,
        prior_value=prior,
        current_value=current,
        evidence_status="source_backed",
        source_ref=f"source:{event_id}",
        source_published_at="2026-07-16T12:00:00+00:00",
        detected_at="2026-07-17T12:00:00+00:00",
        suggested_research_task=f"{ticker}: Review source-backed evidence.",
    )
    return SimpleNamespace(
        event=event,
        review_status=status,
        wait_condition="Wait for changed source evidence." if status == "still_blocked" else "",
    )


def test_weekly_summary_groups_traceable_cohort_events_without_duplicate_or_recommendation_language():
    item = _item("evt-1", "AAA")
    summary = build_weekly_research_summary(
        _cohort("AAA", "BBB"),
        [item, item, _item("outside", "OUT")],
        as_of="2026-07-17T23:59:59+00:00",
    )

    assert summary.status == "review_required"
    assert summary.unique_event_count == 1
    assert [entry.ticker for entry in summary.items] == ["AAA", "AAA"]
    assert {entry.category for entry in summary.items} == {"new_evidence", "requires_review"}
    assert all(entry.source_ref == "source:evt-1" for entry in summary.items)
    rendered = weekly_summary_rows(summary).__str__().lower()
    for prohibited in ("buy", "sell", "top pick", "winner", "recommendation score"):
        assert prohibited not in rendered


def test_weekly_summary_classifies_newly_usable_newly_blocked_and_waiting_states():
    summary = build_weekly_research_summary(
        _cohort("AAA", "BBB"),
        [
            _item("usable", "AAA", subtype="dcf_readiness_changed", family="readiness", prior="false", current="true"),
            _item("blocked", "BBB", subtype="peer_readiness_changed", family="readiness", prior="true", current="false", status="still_blocked"),
        ],
        as_of="2026-07-17T23:59:59+00:00",
    )

    categories = {(item.ticker, item.category) for item in summary.items}
    assert ("AAA", "newly_usable") in categories
    assert ("BBB", "newly_blocked") in categories
    assert ("BBB", "waiting") in categories
    waiting = next(item for item in summary.items if item.category == "waiting")
    assert waiting.answer == "Wait for changed source evidence."


def test_weekly_summary_uses_only_reviewer_authored_stale_and_invalidation_rows():
    summary = build_weekly_research_summary(
        _cohort("AAA"),
        [],
        journal_rows=[
            {
                "ticker": "AAA",
                "review_due_date": "2026-07-01",
                "invalidation_triggered": True,
                "invalidation_condition": "Source-backed margin condition requires review.",
                "source_ref": "journal:aaa:3",
            },
            {
                "ticker": "OUT",
                "review_due_date": "2026-07-01",
                "invalidation_triggered": True,
                "invalidation_condition": "Outside cohort.",
                "source_ref": "journal:out:1",
            },
        ],
        as_of="2026-07-17T23:59:59+00:00",
    )

    assert {(item.category, item.ticker) for item in summary.items} == {
        ("stale_review", "AAA"),
        ("invalidation_condition", "AAA"),
    }
    assert all(item.source_ref == "journal:aaa:3" for item in summary.items)


def test_weekly_summary_empty_week_is_monitoring_not_fabricated_narrative():
    summary = build_weekly_research_summary(
        _cohort("AAA"),
        [],
        as_of="2026-07-17T23:59:59+00:00",
    )

    assert summary.status == "no_changes"
    assert summary.items == ()
    assert summary.message == "No traceable cohort evidence change requires review this week."
    assert weekly_summary_rows(summary) == []


def test_weekly_summary_excludes_events_outside_seven_day_window():
    old = _item("old", "AAA")
    old.event.detected_at = "2026-07-01T12:00:00+00:00"

    summary = build_weekly_research_summary(
        _cohort("AAA"),
        [old],
        as_of="2026-07-17T23:59:59+00:00",
    )

    assert summary.status == "no_changes"
    assert summary.unique_event_count == 0
