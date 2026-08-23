"""Read-only public price-lineage candidate review for the Golden Evidence Cohort."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol

import pandas as pd

from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.data_update import YahooChartDailyPriceSource
from src.golden_evidence_cohort import (
    RESEARCH_ONLY_BOUNDARY,
    GoldenEvidenceCohort,
    GoldenEvidenceMember,
    build_golden_evidence_cohort,
)
from src.paths import resolve_project_root
from src.price_lineage_temporal import review_daily_price_retrieval


OPERATING_COHORT_ROLES = {"saved_operating_company", "evidence_gap_control"}
METHOD_FIT_ROLE = "method_fit_exclusion"
PUBLIC_PRICE_SOURCE_ID = "yahoo"


class _CandidatePriceSource(Protocol):
    source_id: str
    last_source_reference: str
    last_retrieved_at: str

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ...


@dataclass(frozen=True)
class GoldenPriceLineageProofMember:
    ticker: str
    cohort_role: str
    collection_status: str
    observation_date: str
    close: float | None
    source_id: str
    source_reference: str
    retrieved_at: str
    availability_at: str
    review_cutoff: str
    temporal_status: str
    rights_status: str
    price_scope_status: str
    blockers: tuple[str, ...]
    owner_decision_required: bool
    collection_notes: tuple[str, ...]
    next_evidence_review_action: str


@dataclass(frozen=True)
class GoldenPriceLineageProof:
    status: str
    provider_source_id: str
    saved_snapshot_identity: str
    proposed_snapshot_identity: str
    review_cutoff: str
    members: tuple[GoldenPriceLineageProofMember, ...]
    method_fit_exclusions: tuple[str, ...]
    live_collection_performed: bool
    candidate_collected_count: int
    collection_incomplete_count: int
    rights_approved_count: int
    price_scope_complete_count: int
    inspection_only: bool = True
    activation_authorized: bool = False
    canonical_apply_authorized: bool = False
    readiness_materialization_authorized: bool = False
    source_rights_change_authorized: bool = False
    recommendation_authorized: bool = False
    repository_writes: tuple[str, ...] = ()
    research_only_boundary: str = RESEARCH_ONLY_BOUNDARY


@dataclass(frozen=True)
class _CollectedCandidate:
    member: GoldenEvidenceMember
    frame: pd.DataFrame
    source_reference: str
    retrieved_at: str
    notes: tuple[str, ...]
    fetch_failed: bool


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_cutoff(
    review_cutoff: str | None,
    clock: Callable[[], datetime],
) -> str:
    if review_cutoff:
        return review_cutoff
    current = clock()
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("review clock must be timezone-aware")
    return current.astimezone(timezone.utc).isoformat()


def _operating_members(cohort: GoldenEvidenceCohort) -> tuple[GoldenEvidenceMember, ...]:
    return tuple(
        member for member in cohort.members if member.cohort_role in OPERATING_COHORT_ROLES
    )


def _method_fit_exclusions(cohort: GoldenEvidenceCohort) -> tuple[str, ...]:
    return tuple(
        member.ticker for member in cohort.members if member.cohort_role == METHOD_FIT_ROLE
    )


def _selection(
    ticker: str,
    frame: pd.DataFrame,
) -> tuple[str, pd.Series | None, str]:
    if frame.empty or not {"ticker", "date", "close"}.issubset(frame.columns):
        return "fetch_failed", None, ""
    normalized = frame.copy()
    normalized["ticker"] = normalized["ticker"].astype("string").str.upper().str.strip()
    normalized["_proof_date"] = pd.to_datetime(
        normalized["date"], errors="coerce", format="mixed"
    )
    normalized["_proof_close"] = pd.to_numeric(normalized["close"], errors="coerce")
    normalized = normalized.loc[
        normalized["ticker"].eq(ticker)
        & normalized["_proof_date"].notna()
        & normalized["_proof_close"].notna()
        & normalized["_proof_close"].gt(0)
    ].copy()
    if normalized.empty:
        return "no_usable_candidate", None, ""
    latest_date = normalized["_proof_date"].max()
    latest = normalized.loc[normalized["_proof_date"] == latest_date]
    observation_date = pd.Timestamp(latest_date).date().isoformat()
    if len(latest) != 1:
        return "ambiguous_latest_candidate", None, observation_date
    return "candidate_collected", latest.iloc[0], observation_date


def _next_action(
    ticker: str,
    collection_status: str,
    blockers: tuple[str, ...],
) -> str:
    if collection_status == "not_requested":
        return (
            f"Run the explicit live candidate review for {ticker}; this cannot apply prices or rebuild readiness."
        )
    if collection_status != "candidate_collected":
        return f"Resolve the {collection_status} evidence gap for {ticker}; do not pad or infer a row."
    if any(blocker.startswith("missing_provenance:") for blocker in blockers):
        return f"Review exact row-level price provenance for {ticker}; do not infer missing evidence."
    if any(
        blocker
        in {
            "invalid_observation_date",
            "missing_retrieved_at",
            "invalid_retrieved_at",
            "retrieved_at_timezone_required",
            "review_cutoff_required",
            "invalid_review_cutoff",
            "review_cutoff_timezone_required",
            "retrieved_before_observation_available",
            "retrieved_after_review_cutoff",
        }
        for blocker in blockers
    ):
        return f"Review the exact retrieval timestamp and cutoff evidence for {ticker}."
    if any(blocker.startswith("commercial_rights:") for blocker in blockers):
        return (
            f"Owner decision required for exact source '{PUBLIC_PRICE_SOURCE_ID}' commercial rights; "
            "do not borrow the yfinance registry entry."
        )
    if "registered_price_scope_incomplete" in blockers:
        return (
            f"Owner review required for exact source '{PUBLIC_PRICE_SOURCE_ID}' registered prices scope."
        )
    return (
        f"Candidate evidence for {ticker} is reviewable; a separate reviewed apply and readiness decision remain required."
    )


def _not_requested_member(
    member: GoldenEvidenceMember,
    *,
    rights_status: str,
    price_scope_status: str,
) -> GoldenPriceLineageProofMember:
    blockers = ["live_candidate_collection_required"]
    if rights_status != "approved":
        blockers.append(f"commercial_rights:{rights_status}")
    if price_scope_status != "complete":
        blockers.append("registered_price_scope_incomplete")
    return GoldenPriceLineageProofMember(
        ticker=member.ticker,
        cohort_role=member.cohort_role,
        collection_status="not_requested",
        observation_date="",
        close=None,
        source_id=PUBLIC_PRICE_SOURCE_ID,
        source_reference="",
        retrieved_at="",
        availability_at="",
        review_cutoff="",
        temporal_status="not_evaluated",
        rights_status=rights_status,
        price_scope_status=price_scope_status,
        blockers=tuple(blockers),
        owner_decision_required=(
            rights_status != "approved" or price_scope_status != "complete"
        ),
        collection_notes=(),
        next_evidence_review_action=_next_action(
            member.ticker, "not_requested", tuple(blockers)
        ),
    )


def _review_collected_member(
    collected: _CollectedCandidate,
    *,
    review_cutoff: str,
    rights_status: str,
    price_scope_status: str,
) -> GoldenPriceLineageProofMember:
    member = collected.member
    if collected.fetch_failed:
        collection_status = "fetch_failed"
        blockers = ("candidate_fetch_failed",)
        return GoldenPriceLineageProofMember(
            ticker=member.ticker,
            cohort_role=member.cohort_role,
            collection_status=collection_status,
            observation_date="",
            close=None,
            source_id=PUBLIC_PRICE_SOURCE_ID,
            source_reference="",
            retrieved_at="",
            availability_at="",
            review_cutoff=review_cutoff,
            temporal_status="not_evaluated",
            rights_status=rights_status,
            price_scope_status=price_scope_status,
            blockers=blockers,
            owner_decision_required=False,
            collection_notes=collected.notes,
            next_evidence_review_action=_next_action(
                member.ticker, collection_status, blockers
            ),
        )

    collection_status, row, observation_date = _selection(
        member.ticker, collected.frame
    )
    if row is None:
        blocker = (
            "ambiguous_latest_candidate_row"
            if collection_status == "ambiguous_latest_candidate"
            else "no_usable_candidate_row"
        )
        blockers = (blocker,)
        return GoldenPriceLineageProofMember(
            ticker=member.ticker,
            cohort_role=member.cohort_role,
            collection_status=collection_status,
            observation_date=observation_date,
            close=None,
            source_id=PUBLIC_PRICE_SOURCE_ID,
            source_reference=collected.source_reference,
            retrieved_at=collected.retrieved_at,
            availability_at="",
            review_cutoff=review_cutoff,
            temporal_status="not_evaluated",
            rights_status=rights_status,
            price_scope_status=price_scope_status,
            blockers=blockers,
            owner_decision_required=False,
            collection_notes=collected.notes,
            next_evidence_review_action=_next_action(
                member.ticker, collection_status, blockers
            ),
        )

    temporal = review_daily_price_retrieval(
        observation_date,
        collected.retrieved_at,
        review_cutoff=review_cutoff,
    )
    blockers: list[str] = []
    if not collected.source_reference:
        blockers.append("missing_provenance:source_ref")
    if not collected.retrieved_at:
        blockers.append("missing_provenance:retrieved_at")
    blockers.extend(temporal.blockers)
    if rights_status != "approved":
        blockers.append(f"commercial_rights:{rights_status}")
    if price_scope_status != "complete":
        blockers.append("registered_price_scope_incomplete")
    blocker_tuple = tuple(dict.fromkeys(blockers))
    return GoldenPriceLineageProofMember(
        ticker=member.ticker,
        cohort_role=member.cohort_role,
        collection_status=collection_status,
        observation_date=observation_date,
        close=float(row["_proof_close"]),
        source_id=PUBLIC_PRICE_SOURCE_ID,
        source_reference=collected.source_reference,
        retrieved_at=temporal.retrieved_at,
        availability_at=temporal.availability_at,
        review_cutoff=temporal.review_cutoff,
        temporal_status=temporal.status,
        rights_status=rights_status,
        price_scope_status=price_scope_status,
        blockers=blocker_tuple,
        owner_decision_required=(
            rights_status != "approved" or price_scope_status != "complete"
        ),
        collection_notes=collected.notes,
        next_evidence_review_action=_next_action(
            member.ticker, collection_status, blocker_tuple
        ),
    )


def build_golden_price_lineage_proof(
    cohort: GoldenEvidenceCohort,
    *,
    rights_registry: Mapping[str, SourceRights],
    live: bool,
    source: _CandidatePriceSource | None = None,
    review_cutoff: str | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> GoldenPriceLineageProof:
    """Collect or preview exact public price evidence without mutating repository state."""

    operating = _operating_members(cohort)
    exclusions = _method_fit_exclusions(cohort)
    scope = review_commercial_field_scope(
        rights_registry, PUBLIC_PRICE_SOURCE_ID, ("prices",)
    )
    rights_status = scope.rights_status
    price_scope_status = "complete" if not scope.missing_supported_fields else "review_required"

    if not live:
        members = tuple(
            _not_requested_member(
                member,
                rights_status=rights_status,
                price_scope_status=price_scope_status,
            )
            for member in operating
        )
        return GoldenPriceLineageProof(
            status="collection_not_requested",
            provider_source_id=PUBLIC_PRICE_SOURCE_ID,
            saved_snapshot_identity=cohort.saved_snapshot_identity,
            proposed_snapshot_identity=cohort.proposed_snapshot_identity,
            review_cutoff="",
            members=members,
            method_fit_exclusions=exclusions,
            live_collection_performed=False,
            candidate_collected_count=0,
            collection_incomplete_count=len(members),
            rights_approved_count=0,
            price_scope_complete_count=0,
        )

    if source is None:
        raise ValueError("live collection requires an explicit candidate price source")
    if str(source.source_id).strip() != PUBLIC_PRICE_SOURCE_ID:
        raise ValueError(
            f"exact public price source must be '{PUBLIC_PRICE_SOURCE_ID}'"
        )

    collected_rows: list[_CollectedCandidate] = []
    for member in operating:
        try:
            frame, notes = source.fetch_history(member.ticker)
        except Exception as exc:  # pragma: no cover - defensive network boundary
            frame = pd.DataFrame()
            notes = [f"{member.ticker}: candidate collection failed ({exc})"]
        collected_rows.append(
            _CollectedCandidate(
                member=member,
                frame=frame,
                source_reference=str(
                    getattr(source, "last_source_reference", "") or ""
                ).strip(),
                retrieved_at=str(
                    getattr(source, "last_retrieved_at", "") or ""
                ).strip(),
                notes=tuple(str(note) for note in notes if str(note).strip()),
                fetch_failed=frame.empty,
            )
        )

    cutoff = _normalized_cutoff(review_cutoff, clock)
    members = tuple(
        _review_collected_member(
            collected,
            review_cutoff=cutoff,
            rights_status=rights_status,
            price_scope_status=price_scope_status,
        )
        for collected in collected_rows
    )
    incomplete_count = sum(
        member.collection_status != "candidate_collected" for member in members
    )
    candidate_count = len(members) - incomplete_count
    rights_approved_count = sum(
        member.collection_status == "candidate_collected"
        and member.rights_status == "approved"
        for member in members
    )
    scope_complete_count = sum(
        member.collection_status == "candidate_collected"
        and member.price_scope_status == "complete"
        for member in members
    )
    if incomplete_count:
        status = "candidate_collection_incomplete"
    elif any(member.rights_status != "approved" for member in members):
        status = "candidate_evidence_collected_rights_blocked"
    elif any(member.price_scope_status != "complete" for member in members):
        status = "candidate_evidence_collected_scope_blocked"
    elif any(member.blockers for member in members):
        status = "candidate_evidence_review_required"
    else:
        status = "candidate_evidence_reviewable"
    return GoldenPriceLineageProof(
        status=status,
        provider_source_id=PUBLIC_PRICE_SOURCE_ID,
        saved_snapshot_identity=cohort.saved_snapshot_identity,
        proposed_snapshot_identity=cohort.proposed_snapshot_identity,
        review_cutoff=cutoff,
        members=members,
        method_fit_exclusions=exclusions,
        live_collection_performed=True,
        candidate_collected_count=candidate_count,
        collection_incomplete_count=incomplete_count,
        rights_approved_count=rights_approved_count,
        price_scope_complete_count=scope_complete_count,
    )


def render_golden_price_lineage_proof_json(
    packet: GoldenPriceLineageProof,
) -> str:
    return json.dumps(
        asdict(packet), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def render_golden_price_lineage_proof(packet: GoldenPriceLineageProof) -> str:
    lines = [
        "Golden Cohort Price Lineage Proof",
        "",
        f"status={packet.status}",
        f"provider_source_id={packet.provider_source_id}",
        f"saved_snapshot_identity={packet.saved_snapshot_identity}",
        f"proposed_snapshot_identity={packet.proposed_snapshot_identity}",
        f"review_cutoff={packet.review_cutoff or '<not_evaluated>'}",
        f"members={len(packet.members)}",
        f"method_fit_exclusions={','.join(packet.method_fit_exclusions) or 'none'}",
    ]
    for member in packet.members:
        lines.extend(
            [
                f"- {member.ticker}: role={member.cohort_role}; collection_status={member.collection_status}",
                f"  observation_date={member.observation_date or '<unavailable>'}; close={member.close if member.close is not None else '<unavailable>'}",
                f"  source_id={member.source_id}",
                f"  source_reference={member.source_reference or '<missing>'}",
                f"  retrieved_at={member.retrieved_at or '<missing>'}",
                f"  availability_at={member.availability_at or '<not_evaluated>'}",
                f"  review_cutoff={member.review_cutoff or '<not_evaluated>'}",
                f"  temporal_status={member.temporal_status}",
                f"  rights_status={member.rights_status}",
                f"  price_scope_status={member.price_scope_status}",
                f"  blockers={','.join(member.blockers) or 'none'}",
                f"  owner_decision_required={str(member.owner_decision_required).lower()}",
                f"  collection_notes={' | '.join(member.collection_notes) or 'none'}",
                f"  next_evidence_review_action={member.next_evidence_review_action}",
            ]
        )
    lines.extend(
        [
            "",
            f"live_collection_performed={str(packet.live_collection_performed).lower()}",
            f"candidate_collected_count={packet.candidate_collected_count}",
            f"collection_incomplete_count={packet.collection_incomplete_count}",
            f"rights_approved_count={packet.rights_approved_count}",
            f"price_scope_complete_count={packet.price_scope_complete_count}",
            "inspection_only=true",
            "activation_authorized=false",
            "canonical_apply_authorized=false",
            "readiness_materialization_authorized=false",
            "source_rights_change_authorized=false",
            "recommendation_authorized=false",
            "repository_writes=[]",
            RESEARCH_ONLY_BOUNDARY,
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect or preview public price-lineage candidates for the Golden Evidence Cohort."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--data-dir")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--review-cutoff")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    project_root = resolve_project_root(args.project_root)
    registry = load_source_rights_registry(project_root / "config" / "source_rights.yml")
    cohort = build_golden_evidence_cohort(
        project_root,
        data_dir=Path(args.data_dir) if args.data_dir else None,
        top_n=5,
        rights_registry=registry,
        review_cutoff=args.review_cutoff,
    )
    source = YahooChartDailyPriceSource() if args.live else None
    packet = build_golden_price_lineage_proof(
        cohort,
        rights_registry=registry,
        live=args.live,
        source=source,
        review_cutoff=args.review_cutoff,
    )
    print(
        render_golden_price_lineage_proof_json(packet)
        if args.json
        else render_golden_price_lineage_proof(packet)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
