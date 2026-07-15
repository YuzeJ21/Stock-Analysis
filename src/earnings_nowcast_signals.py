from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from src.earnings_nowcast_contract import (
    EvidenceSignal,
    NowcastState,
    SignalReviewState,
    parse_utc_timestamp,
)


ALLOWED_SIGNAL_TYPES = frozenset(
    {
        "company_news_event",
        "company_guidance_context",
        "industry_indicator",
        "macro_indicator",
        "peer_earnings_readthrough",
    }
)


@dataclass(frozen=True)
class SignalReview:
    state: NowcastState
    supported: tuple[EvidenceSignal, ...]
    candidate_context_only: tuple[EvidenceSignal, ...]
    still_blocked: tuple[EvidenceSignal, ...]
    skipped: tuple[EvidenceSignal, ...]
    excluded: tuple[EvidenceSignal, ...]
    blockers: tuple[str, ...]


def _ordered(rows: Iterable[EvidenceSignal]) -> tuple[EvidenceSignal, ...]:
    return tuple(sorted(rows, key=lambda row: (row.evidence_published_at, row.signal_id)))


def review_evidence_signals(
    signals: Sequence[EvidenceSignal],
    cutoff: str,
    *,
    trusted_peer_ids: set[str] | frozenset[str],
) -> SignalReview:
    boundary = parse_utc_timestamp(cutoff, label="forecast cutoff")
    supported: list[EvidenceSignal] = []
    candidates: list[EvidenceSignal] = []
    blocked: list[EvidenceSignal] = []
    skipped: list[EvidenceSignal] = []
    excluded: list[EvidenceSignal] = []
    blockers: list[str] = []

    for signal in _ordered(signals):
        if signal.review_state == SignalReviewState.EXCLUDED:
            excluded.append(signal)
            continue
        if signal.review_state == SignalReviewState.SKIPPED:
            skipped.append(signal)
            continue
        if signal.review_state == SignalReviewState.STILL_BLOCKED:
            blocked.append(signal)
            continue
        if parse_utc_timestamp(signal.evidence_published_at) > boundary:
            blocked.append(signal)
            blockers.append("published_after_cutoff")
            continue
        if signal.signal_type not in ALLOWED_SIGNAL_TYPES:
            skipped.append(signal)
            blockers.append("unsupported_signal_type")
            continue

        is_peer_signal = signal.signal_type == "peer_earnings_readthrough"
        trusted_peer = (
            not is_peer_signal
            or (
                signal.signal_id in trusted_peer_ids
                and signal.peer_relationship_state == "trusted"
            )
        )
        if signal.review_state == SignalReviewState.SUPPORTED and trusted_peer:
            supported.append(signal)
        else:
            candidates.append(signal)

    return SignalReview(
        state=NowcastState.SIGNAL_CONTEXT_READY if supported else NowcastState.BASELINE_READY,
        supported=_ordered(supported),
        candidate_context_only=_ordered(candidates),
        still_blocked=_ordered(blocked),
        skipped=_ordered(skipped),
        excluded=_ordered(excluded),
        blockers=tuple(dict.fromkeys(blockers)),
    )


def _signal_payload(signal: EvidenceSignal) -> dict[str, object]:
    payload = asdict(signal)
    payload["direction"] = signal.direction.value
    payload["review_state"] = signal.review_state.value
    return payload


def signal_context_payload(review: SignalReview) -> dict[str, object]:
    return {
        "state": review.state.value,
        "supported": [_signal_payload(signal) for signal in review.supported],
        "candidate_context_only": [_signal_payload(signal) for signal in review.candidate_context_only],
        "still_blocked": [_signal_payload(signal) for signal in review.still_blocked],
        "skipped": [_signal_payload(signal) for signal in review.skipped],
        "excluded": [_signal_payload(signal) for signal in review.excluded],
        "blockers": list(review.blockers),
        "boundary": "Evidence signals are directional context only and never change forecast numbers.",
    }
