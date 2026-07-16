import csv
from pathlib import Path

from src.research_change_monitor import ResearchChangeEvent
from src.research_review_queue import (
    REVIEW_LEDGER_COLUMNS,
    ReviewResolution,
    append_review_resolution,
    build_research_review_queue,
    load_review_resolutions,
)


def _event(
    *,
    event_id: str,
    subtype: str,
    prior_value: str = "",
    current_value: str = "",
    materiality: str = "context",
    ticker: str = "NVDA",
) -> ResearchChangeEvent:
    return ResearchChangeEvent(
        event_id=event_id,
        ticker=ticker,
        family="readiness",
        subtype=subtype,
        prior_value=prior_value,
        current_value=current_value,
        source="selected_profile_readiness",
        source_ref=f"source:{event_id}",
        source_published_at="2026-07-15T12:00:00Z",
        retrieved_at="2026-07-15T13:00:00Z",
        detected_at="2026-07-15T13:00:00Z",
        profile_key="local",
        prior_snapshot_identity="before",
        current_snapshot_identity="after",
        evidence_status="source_backed",
        materiality=materiality,
        suggested_research_task=f"{ticker}: Review the changed research evidence.",
    )


def _resolution(event_id: str, status: str, *, reviewed_at: str = "2026-07-15T20:00:00Z") -> ReviewResolution:
    return ReviewResolution(
        schema_version="research-event-review-v1",
        event_id=event_id,
        profile_key="local",
        ticker="NVDA",
        review_status=status,
        reviewed_at=reviewed_at,
        reviewer="codex-review",
        resolution_note="Reviewed source evidence without mutating readiness.",
        source_ref=f"source:{event_id}",
        prior_snapshot_identity="before",
        current_snapshot_identity="after",
    )


def test_review_ledger_header_matches_contract():
    with Path("data/reviewed_research_events.csv").open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == list(REVIEW_LEDGER_COLUMNS)


def test_queue_prioritizes_lost_readiness_before_new_context():
    queue = build_research_review_queue(
        [
            _event(event_id="momentum", subtype="momentum_readiness_changed"),
            _event(
                event_id="dcf-loss",
                subtype="dcf_readiness_changed",
                prior_value="true",
                current_value="false",
                materiality="high",
            ),
            _event(event_id="filing", subtype="sec_filing_arrived", materiality="medium"),
        ],
        resolutions=[],
    )

    assert [row.event.subtype for row in queue] == [
        "dcf_readiness_changed",
        "sec_filing_arrived",
        "momentum_readiness_changed",
    ]


def test_review_resolution_appends_and_does_not_mutate_source_files(tmp_path):
    source = tmp_path / "data" / "local" / "fundamentals.csv"
    source.parent.mkdir(parents=True)
    source.write_text("ticker,revenue\nNVDA,1\n", encoding="utf-8")
    before = source.read_bytes()
    ledger = tmp_path / "data" / "reviewed_research_events.csv"

    append_review_resolution(ledger, _resolution("event-1", "reviewed_supported"))
    append_review_resolution(
        ledger,
        _resolution("event-1", "still_blocked", reviewed_at="2026-07-16T00:00:00Z"),
    )

    assert source.read_bytes() == before
    assert len(list(csv.DictReader(ledger.open(encoding="utf-8")))) == 2
    assert load_review_resolutions(ledger)[-1].review_status == "still_blocked"


def test_latest_resolution_controls_queue_without_erasing_history(tmp_path):
    ledger = tmp_path / "reviewed_research_events.csv"
    append_review_resolution(ledger, _resolution("event-1", "still_blocked"))
    append_review_resolution(
        ledger,
        _resolution("event-1", "reviewed_no_change", reviewed_at="2026-07-16T00:00:00Z"),
    )
    resolutions = load_review_resolutions(ledger)

    queue = build_research_review_queue(
        [_event(event_id="event-1", subtype="sec_filing_arrived")],
        resolutions=resolutions,
    )

    assert len(resolutions) == 2
    assert queue == ()


def test_still_blocked_resolution_remains_visible_with_wait_condition():
    event = _event(event_id="event-1", subtype="sec_filing_arrived")

    queue = build_research_review_queue(
        [event],
        resolutions=[_resolution("event-1", "still_blocked")],
    )

    assert len(queue) == 1
    assert queue[0].review_status == "still_blocked"
    assert queue[0].wait_condition == "Reviewed evidence remains blocked; wait for new source evidence."
