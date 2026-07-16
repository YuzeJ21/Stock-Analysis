from src.source_freshness_timeline import build_source_freshness_timeline


def _payload() -> dict[str, object]:
    return {
        "ticker": "SYN1",
        "generated_at": "2026-07-15T20:00:00Z",
        "price_snapshot": {"market_time": "2026-07-15T16:00:00Z"},
        "financial_summary": {
            "as_of_date": "2026-06-30",
            "reporting_period": "2026-Q2",
        },
        "data_freshness": [
            {
                "provider": "local:prices.csv",
                "freshness": "current",
                "retrieved_at": "2026-07-15T17:00:00Z",
                "official": False,
                "notes": ["Saved daily bars."],
            },
            {
                "provider": "sec_companyfacts",
                "freshness": "stale",
                "retrieved_at": "2026-07-10T12:00:00Z",
                "official": True,
                "notes": ["Latest reviewed filing input."],
            },
        ],
    }


def test_timeline_orders_known_events_newest_first_and_preserves_timestamp_kind():
    timeline = build_source_freshness_timeline(_payload(), profile_key="demo")

    assert timeline.ticker == "SYN1"
    assert timeline.profile_key == "demo"
    assert [event.timestamp_kind for event in timeline.events[:3]] == [
        "report_generated",
        "source_retrieved",
        "market_observed",
    ]
    assert timeline.events[-1].timestamp_kind == "financial_effective"


def test_timeline_identity_is_deterministic_and_profile_specific():
    first = build_source_freshness_timeline(_payload(), profile_key="demo")
    repeat = build_source_freshness_timeline(_payload(), profile_key="demo")
    local = build_source_freshness_timeline(_payload(), profile_key="local")

    assert first.timeline_identity == repeat.timeline_identity
    assert len(first.timeline_identity) == 64
    assert first.timeline_identity != local.timeline_identity
    assert [event.event_id for event in first.events] == [event.event_id for event in repeat.events]


def test_timeline_deduplicates_exact_source_records_and_keeps_stale_state():
    payload = _payload()
    payload["data_freshness"].append(dict(payload["data_freshness"][1]))

    timeline = build_source_freshness_timeline(payload, profile_key="demo")
    sec_events = [event for event in timeline.events if event.source == "sec_companyfacts"]

    assert len(sec_events) == 1
    assert sec_events[0].freshness_state == "stale"
    assert sum(event.freshness_state == "stale" for event in timeline.events) == 1
    assert timeline.stale_or_unknown_count == 2


def test_timeline_keeps_missing_and_invalid_retrieval_times_unknown_without_inference():
    payload = _payload()
    payload["data_freshness"].extend(
        [
            {"provider": "manual_peer_review", "freshness": "current", "retrieved_at": ""},
            {"provider": "optional_estimates", "freshness": "current", "retrieved_at": "not-a-date"},
        ]
    )

    timeline = build_source_freshness_timeline(payload, profile_key="demo")
    unknown = [event for event in timeline.events if event.source in {"manual_peer_review", "optional_estimates"}]

    assert len(unknown) == 2
    assert all(event.timestamp is None for event in unknown)
    assert all(event.freshness_state == "missing_timestamp" for event in unknown)
    assert timeline.unknown_timestamp_count == 2
    assert timeline.events[-1].timestamp is None


def test_timeline_does_not_invent_publication_cutoff_or_revision_events():
    timeline = build_source_freshness_timeline(_payload(), profile_key="demo")
    kinds = {event.timestamp_kind for event in timeline.events}

    assert "source_published" not in kinds
    assert "forecast_cutoff" not in kinds
    assert "revision_recorded" not in kinds
