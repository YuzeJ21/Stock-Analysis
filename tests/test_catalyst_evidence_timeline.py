from pathlib import Path

import pytest

from src.catalyst_evidence_timeline import (
    CatalystEvent,
    append_reviewed_event,
    build_catalyst_timeline,
    load_catalyst_events,
    preview_event,
)


def _event(**overrides) -> CatalystEvent:
    values = {
        "schema_version": "catalyst-evidence-v1",
        "event_id": "event-001",
        "profile_key": "default",
        "ticker": "NVDA",
        "event_type": "earnings",
        "title": "Quarterly results expected",
        "effective_at": "2026-08-20T21:00:00Z",
        "published_at": "2026-07-17T20:00:00Z",
        "retrieved_at": "2026-07-18T05:00:00Z",
        "source": "company_ir",
        "source_ref": "https://example.invalid/nvda-event",
        "evidence_state": "supported",
        "reviewer": "owner",
        "summary": "Scheduled reporting date from reviewed source evidence.",
    }
    values.update(overrides)
    return CatalystEvent(**values)


def test_timeline_separates_upcoming_and_recent_source_backed_events():
    upcoming = _event()
    recent = _event(
        event_id="event-002",
        event_type="product",
        effective_at="2026-07-10T13:00:00Z",
        source_ref="https://example.invalid/nvda-product",
    )
    timeline = build_catalyst_timeline(
        (upcoming, recent),
        profile_key="default",
        ticker="NVDA",
        as_of="2026-07-18T06:00:00Z",
    )

    assert timeline.state == "supported"
    assert [row.event_id for row in timeline.upcoming] == ["event-001"]
    assert [row.event_id for row in timeline.recent] == ["event-002"]
    assert "cannot change forecasts" in timeline.boundary


def test_candidate_event_remains_context_only_and_post_cutoff_evidence_is_rejected():
    candidate = preview_event(_event(evidence_state="candidate_context_only"), existing=())
    post_cutoff = build_catalyst_timeline(
        (_event(published_at="2026-07-19T00:00:00Z"),),
        profile_key="default",
        ticker="NVDA",
        as_of="2026-07-18T06:00:00Z",
    )

    assert candidate.state == "candidate_context_only"
    assert post_cutoff.state == "blocked"
    assert post_cutoff.rejected_count == 1


def test_event_append_requires_review_and_rejects_duplicate(tmp_path: Path):
    ledger = tmp_path / "catalysts.csv"
    with pytest.raises(ValueError, match="confirm_reviewed"):
        append_reviewed_event(ledger, _event(), confirm_reviewed=False)

    append_reviewed_event(ledger, _event(), confirm_reviewed=True)
    with pytest.raises(ValueError, match="already exists"):
        append_reviewed_event(ledger, _event(), confirm_reviewed=True)

    assert load_catalyst_events(ledger) == (_event(),)


def test_event_type_must_be_from_reviewed_contract():
    preview = preview_event(_event(event_type="social_media_sentiment"), existing=())
    assert preview.state == "rejected"
    assert "event_type" in preview.reason


def test_same_underlying_event_cannot_be_duplicated_under_a_new_id():
    duplicate = preview_event(_event(event_id="event-002"), existing=(_event(),))
    assert duplicate.state == "rejected"
    assert "duplicate catalyst evidence" in duplicate.reason
