"""Evidence-gated peer relationship and result context for stock reports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from src.peer_evidence_quality import assess_peer_evidence

@dataclass(frozen=True)
class PeerReadThroughEdge:
    subject_ticker: str
    peer_ticker: str
    relationship_state: str
    peer_group: str
    peer_role: str
    comparability_state: str
    valuation_anchor_state: str
    evidence_quality_blockers: tuple[str, ...]
    business_overlap: str
    fiscal_timing: str
    result_evidence: str
    relationship_source: str
    relationship_as_of: str
    result_source: str
    result_date: str
    read_through_state: str
    missing_proof: str
    boundary: str


@dataclass(frozen=True)
class PeerReadThroughMap:
    ticker: str
    profile_key: str
    status: str
    map_identity: str
    edges: tuple[PeerReadThroughEdge, ...]
    trusted_count: int
    candidate_count: int
    reviewable_count: int
    withheld_count: int
    valuation_anchor_count: int
    comparability_withheld_count: int
    boundary: str


def _text(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def _source_text(value: object) -> str:
    if isinstance(value, Mapping):
        return _text(value.get("provider") or value.get("source") or value.get("url"))
    return _text(value)


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(_text(value))
    return True


def _result_evidence(result: Mapping[str, object]) -> tuple[str, bool]:
    available: list[str] = []
    if _has_value(result.get("revenue_actual")):
        available.append("Revenue actual")
    if _has_value(result.get("eps_actual")):
        available.append("EPS actual")
    result_date = _text(result.get("last_earnings_date") or result.get("report_date"))
    source = _source_text(result.get("source"))
    source_backed = bool(available and result_date and source)
    return (" and ".join(available) if source_backed else "No source-backed actual result", source_backed)


def _business_overlap(row: Mapping[str, object]) -> str:
    return _text(
        row.get("relationship_rationale")
        or row.get("industry")
        or row.get("peer_group")
    ) or "Not documented"


def _relationship_source_ready(row: Mapping[str, object]) -> bool:
    return bool(_source_text(row.get("source")) and _text(row.get("as_of_date")))


def _trusted_edge(
    *,
    ticker: str,
    row: Mapping[str, object],
    target_period: str,
) -> PeerReadThroughEdge:
    peer = _text(row.get("peer_ticker")).upper()
    overlap = _business_overlap(row)
    quality = assess_peer_evidence(row)
    relationship_ready = _relationship_source_ready(row)
    result = row.get("peer_result") if isinstance(row.get("peer_result"), Mapping) else {}
    result = result or {}
    result_label, result_ready = _result_evidence(result)
    peer_period = _text(result.get("fiscal_period"))
    timing_ready = bool(target_period and peer_period)
    fiscal_timing = f"{ticker} {target_period} / {peer} {peer_period}" if timing_ready else "Not established"

    if not relationship_ready:
        relationship_state = "awaiting_relationship_proof"
        read_through_state = "awaiting_relationship_proof"
        missing = "Relationship source and as-of date"
    elif overlap == "Not documented":
        relationship_state = "trusted_peer_ready"
        read_through_state = "relationship_context_only"
        missing = "Explicit business-overlap evidence"
    elif not result_ready:
        relationship_state = "trusted_peer_ready"
        read_through_state = "awaiting_peer_result"
        missing = "Source-backed peer Revenue or EPS actual"
    elif not timing_ready:
        relationship_state = "trusted_peer_ready"
        read_through_state = "awaiting_fiscal_timing"
        missing = "Target and peer fiscal periods"
    else:
        relationship_state = "trusted_peer_ready"
        read_through_state = "reviewable_context"
        missing = "None for contextual review"

    return PeerReadThroughEdge(
        subject_ticker=ticker,
        peer_ticker=peer,
        relationship_state=relationship_state,
        peer_group=_text(row.get("peer_group")) or "Not documented",
        peer_role=quality.peer_role,
        comparability_state=quality.comparability_state,
        valuation_anchor_state=quality.valuation_anchor_state,
        evidence_quality_blockers=quality.blockers,
        business_overlap=overlap,
        fiscal_timing=fiscal_timing,
        result_evidence=result_label,
        relationship_source=_source_text(row.get("source")) or "Not available",
        relationship_as_of=_text(row.get("as_of_date")) or "Not available",
        result_source=_source_text(result.get("source")) or "Not available",
        result_date=_text(result.get("last_earnings_date") or result.get("report_date")) or "Not available",
        read_through_state=read_through_state,
        missing_proof=missing,
        boundary="Context only; this peer evidence does not change a forecast, valuation, readiness state, or action.",
    )


def _candidate_edge(*, ticker: str, row: Mapping[str, object]) -> PeerReadThroughEdge:
    quality = assess_peer_evidence(row)
    return PeerReadThroughEdge(
        subject_ticker=ticker,
        peer_ticker=_text(row.get("peer_ticker")).upper(),
        relationship_state="candidate_context_only",
        peer_group=_text(row.get("peer_group")) or "Not documented",
        peer_role=quality.peer_role,
        comparability_state=quality.comparability_state,
        valuation_anchor_state=quality.valuation_anchor_state,
        evidence_quality_blockers=quality.blockers,
        business_overlap=_business_overlap(row),
        fiscal_timing="Not established",
        result_evidence="Not reviewed",
        relationship_source=_source_text(row.get("source")) or "Not available",
        relationship_as_of=_text(row.get("as_of_date")) or "Not available",
        result_source="Not available",
        result_date="Not available",
        read_through_state="candidate_context_only",
        missing_proof="Reviewed source-backed relationship, peer result, and fiscal timing",
        boundary="Candidate context can route review only; it cannot become trusted peer evidence or change analysis.",
    )


def build_peer_read_through_map(
    report_payload: Mapping[str, object],
    *,
    profile_key: str,
) -> PeerReadThroughMap:
    """Build a deterministic map without inferring relationships or timing."""

    ticker = _text(report_payload.get("ticker")).upper() or "UNKNOWN"
    asset_type = _text(report_payload.get("asset_type")).lower()
    common_boundary = "Peer read-through is evidence context only and never changes forecast or valuation numbers."
    if asset_type in {"etf", "index_proxy", "fund"}:
        identity_payload = {"ticker": ticker, "profile_key": profile_key, "status": "excluded", "edges": []}
        identity = hashlib.sha256(json.dumps(identity_payload, sort_keys=True).encode("utf-8")).hexdigest()
        return PeerReadThroughMap(
            ticker=ticker,
            profile_key=profile_key,
            status="excluded",
            map_identity=identity,
            edges=(),
            trusted_count=0,
            candidate_count=0,
            reviewable_count=0,
            withheld_count=0,
            valuation_anchor_count=0,
            comparability_withheld_count=0,
            boundary=common_boundary,
        )

    earnings = report_payload.get("earnings_summary") if isinstance(report_payload.get("earnings_summary"), Mapping) else {}
    target_period = _text((earnings or {}).get("fiscal_period"))
    readiness = report_payload.get("valuation_readiness") if isinstance(report_payload.get("valuation_readiness"), Mapping) else {}
    peer_summary = (readiness or {}).get("peer_summary") if isinstance((readiness or {}).get("peer_summary"), Mapping) else {}
    trusted_rows = tuple((peer_summary or {}).get("trusted_relationships") or ())
    candidate_rows = tuple((peer_summary or {}).get("candidate_relationships") or ())

    edges: list[PeerReadThroughEdge] = []
    trusted_peers: set[str] = set()
    for row in trusted_rows:
        if not isinstance(row, Mapping) or not _text(row.get("peer_ticker")):
            continue
        edge = _trusted_edge(ticker=ticker, row=row, target_period=target_period)
        edges.append(edge)
        trusted_peers.add(edge.peer_ticker)
    for row in candidate_rows:
        if not isinstance(row, Mapping) or not _text(row.get("peer_ticker")):
            continue
        if _text(row.get("peer_ticker")).upper() in trusted_peers:
            continue
        edges.append(_candidate_edge(ticker=ticker, row=row))

    edges.sort(key=lambda edge: (edge.relationship_state == "candidate_context_only", edge.peer_ticker))
    identity_payload = {
        "ticker": ticker,
        "profile_key": profile_key,
        "edges": [asdict(edge) for edge in edges],
    }
    identity = hashlib.sha256(json.dumps(identity_payload, sort_keys=True).encode("utf-8")).hexdigest()
    trusted_count = sum(edge.relationship_state == "trusted_peer_ready" for edge in edges)
    candidate_count = sum(edge.relationship_state == "candidate_context_only" for edge in edges)
    reviewable_count = sum(edge.read_through_state == "reviewable_context" for edge in edges)
    valuation_anchor_count = sum(
        edge.relationship_state == "trusted_peer_ready" and edge.valuation_anchor_state == "eligible"
        for edge in edges
    )
    comparability_withheld_count = sum(
        edge.relationship_state == "trusted_peer_ready" and edge.valuation_anchor_state != "eligible"
        for edge in edges
    )
    status = "ready_for_context_review" if reviewable_count else "evidence_withheld" if edges else "no_relationship_evidence"
    return PeerReadThroughMap(
        ticker=ticker,
        profile_key=profile_key,
        status=status,
        map_identity=identity,
        edges=tuple(edges),
        trusted_count=trusted_count,
        candidate_count=candidate_count,
        reviewable_count=reviewable_count,
        withheld_count=len(edges) - reviewable_count,
        valuation_anchor_count=valuation_anchor_count,
        comparability_withheld_count=comparability_withheld_count,
        boundary=common_boundary,
    )


def peer_read_through_rows(read_through: PeerReadThroughMap) -> list[dict[str, str]]:
    state_labels = {
        "reviewable_context": "Reviewable context",
        "candidate_context_only": "Candidate context only",
        "awaiting_relationship_proof": "Awaiting relationship proof",
        "relationship_context_only": "Relationship context only",
        "awaiting_peer_result": "Awaiting peer result",
        "awaiting_fiscal_timing": "Awaiting fiscal timing",
    }
    role_labels = {
        "core_peer": "Core peer",
        "secondary_peer": "Secondary peer",
        "aspirational_peer": "Aspirational peer",
        "negative_peer": "Negative peer",
        "excluded_close_peer": "Excluded close peer",
        "not_clean_comp": "Not clean comp",
        "unreviewed": "Unreviewed",
    }
    comparability_labels = {
        "reviewed_comparable": "Reviewed comparable",
        "context_only": "Context only",
        "unreviewed": "Unreviewed",
    }
    anchor_labels = {"eligible": "Eligible", "withheld": "Withheld"}
    rows: list[dict[str, str]] = []
    for edge in read_through.edges:
        rows.append(
            {
                "Peer": edge.peer_ticker,
                "Relationship": "Trusted peer" if edge.relationship_state == "trusted_peer_ready" else state_labels.get(edge.relationship_state, edge.relationship_state),
                "Peer Role": role_labels.get(edge.peer_role, edge.peer_role),
                "Comparability": comparability_labels.get(edge.comparability_state, edge.comparability_state),
                "Valuation Anchor": anchor_labels.get(edge.valuation_anchor_state, edge.valuation_anchor_state),
                "Business Overlap": edge.business_overlap,
                "Fiscal Timing": edge.fiscal_timing,
                "Peer Result": edge.result_evidence,
                "Read-Through State": state_labels.get(edge.read_through_state, edge.read_through_state),
                "Missing Proof": edge.missing_proof,
            }
        )
    return rows
