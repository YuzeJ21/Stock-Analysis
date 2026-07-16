import re

import pytest

from src.research_change_monitor import compare_optional_snapshots, compare_research_snapshots
from src.research_change_snapshot import ResearchChangeSnapshot, TickerResearchState


def _snapshot(
    *,
    profile: str = "local",
    identity: str = "before",
    ticker: str = "NVDA",
    readiness: dict[str, str] | None = None,
    fundamentals: dict[str, str] | None = None,
    accession: str = "A1",
    filing_date: str = "2026-01-01",
    price_date: str = "2026-07-14",
    consensus_ids: tuple[str, ...] = (),
) -> ResearchChangeSnapshot:
    fundamental_values = {"source": "sec_companyfacts", "as_of_date": "2026-01-01"}
    fundamental_values.update(fundamentals or {})
    return ResearchChangeSnapshot(
        schema_version="research-change-snapshot-v1",
        profile_key=profile,
        snapshot_identity=identity,
        captured_at="2026-07-15T20:00:00+00:00" if identity == "before" else "2026-07-16T20:00:00+00:00",
        source_as_of="2026-07-14",
        tickers=(
            TickerResearchState(
                ticker=ticker,
                readiness=tuple(sorted((readiness or {}).items())),
                fundamentals=tuple(sorted(fundamental_values.items())),
                latest_price_date=price_date,
                latest_filing_accession=accession,
                latest_filing_date=filing_date,
                nowcast_consensus_ids=consensus_ids,
                source_refs=(f"sec-accession:{accession}",),
            ),
        ),
    )


def _event(events, subtype):
    return next(row for row in events if row.subtype == subtype)


def test_monitor_detects_readiness_loss_and_gain():
    before = _snapshot(readiness={"dcf_ready": "true", "peer_ready": "false"})
    after = _snapshot(identity="after", readiness={"dcf_ready": "false", "peer_ready": "true"})

    events = compare_research_snapshots(before, after)

    assert _event(events, "dcf_readiness_changed").current_value == "false"
    assert _event(events, "peer_readiness_changed").current_value == "true"
    assert _event(events, "dcf_readiness_changed").materiality == "high"


def test_monitor_detects_filing_and_source_field_revisions():
    before = _snapshot(fundamentals={"shares_outstanding": "100"}, accession="A1")
    after = _snapshot(
        identity="after",
        fundamentals={"shares_outstanding": "105"},
        accession="A2",
        filing_date="2026-07-15",
    )

    events = compare_research_snapshots(before, after)

    assert {row.subtype for row in events} >= {"sec_filing_arrived", "shares_outstanding_revised"}


def test_monitor_detects_price_and_nowcast_context_changes():
    before = _snapshot(price_date="2026-07-14")
    after = _snapshot(
        identity="after",
        price_date="2026-07-15",
        consensus_ids=("NVDA|FY2027-Q2|2026-07-15T20:00:00Z",),
    )

    events = compare_research_snapshots(before, after)

    assert {row.subtype for row in events} >= {"price_history_advanced", "nowcast_consensus_changed"}


def test_monitor_rejects_cross_profile_comparison():
    with pytest.raises(ValueError, match="same selected profile"):
        compare_research_snapshots(_snapshot(profile="demo"), _snapshot(profile="local", identity="after"))


def test_monitor_returns_baseline_missing_without_fabricating_events():
    result = compare_optional_snapshots(None, _snapshot(identity="after"))

    assert result.status == "baseline_missing"
    assert result.events == ()


def test_event_ids_are_stable_and_unique():
    before = _snapshot(readiness={"dcf_ready": "true"}, fundamentals={"shares_outstanding": "100"})
    after = _snapshot(
        identity="after",
        readiness={"dcf_ready": "false"},
        fundamentals={"shares_outstanding": "105"},
        accession="A2",
    )

    first = compare_research_snapshots(before, after)
    second = compare_research_snapshots(before, after)

    assert [row.event_id for row in first] == [row.event_id for row in second]
    assert len({row.event_id for row in first}) == len(first)


def test_suggested_tasks_contain_no_investment_or_execution_language():
    before = _snapshot(readiness={"dcf_ready": "true"}, fundamentals={"shares_outstanding": "100"})
    after = _snapshot(
        identity="after",
        readiness={"dcf_ready": "false"},
        fundamentals={"shares_outstanding": "105"},
        accession="A2",
        consensus_ids=("NVDA|FY2027-Q2|2026-07-15T20:00:00Z",),
    )

    rendered = " ".join(row.suggested_research_task for row in compare_research_snapshots(before, after)).lower()

    assert not re.search(r"\b(buy|sell|hold|outperform|underperform|order|trade)\b", rendered)
