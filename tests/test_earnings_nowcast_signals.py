from __future__ import annotations

from dataclasses import asdict

from src.earnings_nowcast_contract import EvidenceSignal, SignalReviewState
from src.earnings_nowcast_signals import review_evidence_signals, signal_context_payload


CUTOFF = "2026-01-31T23:59:59Z"


def _signal(
    signal_id: str,
    *,
    review_state: str = "candidate_context_only",
    peer_relationship_state: str = "candidate",
    published_at: str = "2026-01-20T12:00:00Z",
    signal_as_of: str = CUTOFF,
    signal_type: str = "peer_earnings_readthrough",
) -> EvidenceSignal:
    return EvidenceSignal(
        signal_id=signal_id,
        target_ticker="SYN1",
        source_ticker="SYN2",
        fiscal_period="2026-Q1",
        as_of_timestamp=signal_as_of,
        signal_type=signal_type,
        direction="positive",
        affected_metric="revenue",
        confidence_band="medium",
        evidence_source="synthetic_test_fixture",
        evidence_published_at=published_at,
        evidence_excerpt_hash="a" * 64,
        peer_relationship_state=peer_relationship_state,
        review_state=review_state,
    )


def test_candidate_peer_signal_cannot_become_supported_or_change_numbers():
    candidate = _signal("candidate-1")

    review = review_evidence_signals([candidate], CUTOFF, trusted_peer_ids=set())

    assert review.supported == ()
    assert review.candidate_context_only == (candidate,)
    assert not hasattr(review, "revenue_adjustment")
    assert not hasattr(review, "eps_adjustment")


def test_trusted_reviewed_peer_signal_can_be_supported_context():
    supported = _signal(
        "peer-1",
        review_state="supported",
        peer_relationship_state="trusted",
    )

    review = review_evidence_signals([supported], CUTOFF, trusted_peer_ids={"peer-1"})

    assert review.supported == (supported,)
    assert review.state.value == "signal_context_ready"


def test_post_cutoff_signal_is_still_blocked():
    late = _signal(
        "peer-1",
        review_state="supported",
        peer_relationship_state="trusted",
        published_at="2026-02-01T12:00:00Z",
        signal_as_of="2026-02-02T00:00:00Z",
    )

    review = review_evidence_signals([late], CUTOFF, trusted_peer_ids={"peer-1"})

    assert review.supported == ()
    assert review.still_blocked == (late,)
    assert "published_after_cutoff" in review.blockers


def test_unsupported_signal_type_is_skipped():
    signal = _signal("unsupported-1", signal_type="social_media_sentiment")

    review = review_evidence_signals([signal], CUTOFF, trusted_peer_ids=set())

    assert review.skipped == (signal,)
    assert "unsupported_signal_type" in review.blockers


def test_payload_is_directional_and_contains_no_numeric_adjustment_fields():
    candidate = _signal("candidate-1")

    payload = signal_context_payload(review_evidence_signals([candidate], CUTOFF, trusted_peer_ids=set()))
    rendered = str(payload).lower()

    assert payload["state"] == "baseline_ready"
    assert payload["candidate_context_only"][0]["direction"] == "positive"
    assert "adjustment" not in rendered
    assert "impact_bps" not in rendered
    assert "probability" not in rendered


def test_explicit_blocked_skipped_and_excluded_states_are_preserved():
    rows = [
        _signal("blocked-1", review_state=SignalReviewState.STILL_BLOCKED.value),
        _signal("skipped-1", review_state=SignalReviewState.SKIPPED.value),
        _signal("excluded-1", review_state=SignalReviewState.EXCLUDED.value),
    ]

    review = review_evidence_signals(rows, CUTOFF, trusted_peer_ids=set())

    assert tuple(row.signal_id for row in review.still_blocked) == ("blocked-1",)
    assert tuple(row.signal_id for row in review.skipped) == ("skipped-1",)
    assert tuple(row.signal_id for row in review.excluded) == ("excluded-1",)
    assert asdict(review)["supported"] == ()
