"""Deterministic, stdout-only remediation queue for proposed readiness evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from src.commercial_source_rights import SourceRights
from src.dcf_price_lineage import DcfPriceLineageEvidence
from src.readiness_preview import (
    ReadinessImpactPreview,
    ReadinessPromotionEvidence,
    build_readiness_impact_preview,
)


INDEPENDENT_BLOCKER_ORDER = (
    "provenance",
    "price_lineage",
    "temporal_evidence",
    "exact_source_rights",
    "registered_field_scope",
    "unclassified_evidence_blocker",
)
FEATURE_ORDER = {"fundamentals": 0, "dcf": 1}
TEMPORAL_BLOCKERS = {
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


@dataclass(frozen=True)
class ReadinessRemediationCandidate:
    ticker: str
    feature: str
    status: str
    independent_blockers: tuple[str, ...]
    blocker_details: tuple[str, ...]
    fundamentals_source: str
    rights_status: str
    missing_provenance_fields: tuple[str, ...]
    missing_registered_fields: tuple[str, ...]
    price_source: str
    price_rights_status: str
    price_temporal_status: str
    price_missing_provenance_fields: tuple[str, ...]
    price_missing_registered_fields: tuple[str, ...]
    next_review_instruction: str


@dataclass(frozen=True)
class ReadinessEvidenceRemediation:
    status: str
    preview_status: str
    saved_snapshot_identity: str
    proposed_snapshot_identity: str
    saved_ticker_count: int
    proposed_ticker_count: int
    changed_ticker_count: int
    added_ticker_count: int
    removed_ticker_count: int
    method_fit_exclusion_counts: tuple[tuple[str, int], ...]
    fundamentals_promotion_count: int
    dcf_promotion_count: int
    independent_blocker_counts: tuple[tuple[str, int], ...]
    candidate_count: int
    candidates: tuple[ReadinessRemediationCandidate, ...]
    top_n: int
    canonical_apply_authorized: bool = False
    readiness_materialization_authorized: bool = False
    source_rights_change_authorized: bool = False
    repository_writes: tuple[str, ...] = ()


def _independent_blockers(
    fundamentals: ReadinessPromotionEvidence,
    price: DcfPriceLineageEvidence | None,
) -> tuple[str, ...]:
    blockers: set[str] = set()
    if fundamentals.missing_provenance_fields:
        blockers.add("provenance")
    if fundamentals.missing_supported_fields:
        blockers.add("registered_field_scope")
    for blocker in fundamentals.blockers:
        if blocker.startswith("missing_provenance:") or blocker in {
            "missing_fundamentals_row",
            "duplicate_fundamentals_rows",
        }:
            blockers.add("provenance")
        elif blocker.startswith("commercial_rights:"):
            blockers.add("exact_source_rights")
        elif blocker == "registered_field_scope_incomplete":
            blockers.add("registered_field_scope")
        else:
            blockers.add("unclassified_evidence_blocker")

    if price is not None:
        if price.latest_row_count != 1 or price.missing_provenance_fields:
            blockers.add("price_lineage")
        if price.latest_row_count == 1 and price.temporal_status != "temporal_complete":
            blockers.add("temporal_evidence")
        if price.missing_supported_fields:
            blockers.add("registered_field_scope")
        for blocker in price.blockers:
            if blocker.startswith("missing_provenance:") or blocker in {
                "missing_latest_price_row",
                "ambiguous_latest_price_row",
            }:
                blockers.add("price_lineage")
            elif blocker in TEMPORAL_BLOCKERS:
                blockers.add("temporal_evidence")
            elif blocker.startswith("commercial_rights:"):
                blockers.add("exact_source_rights")
            elif blocker == "registered_price_scope_incomplete":
                blockers.add("registered_field_scope")
            else:
                blockers.add("unclassified_evidence_blocker")
    return tuple(name for name in INDEPENDENT_BLOCKER_ORDER if name in blockers)


def _next_review_instruction(
    ticker: str,
    blockers: tuple[str, ...],
    fundamentals: ReadinessPromotionEvidence,
    price: DcfPriceLineageEvidence | None,
) -> str:
    if "unclassified_evidence_blocker" in blockers:
        details = list(fundamentals.blockers)
        if price is not None:
            details.extend(price.blockers)
        return f"Independent review must classify unexpected evidence blockers for {ticker}: {', '.join(details)}."
    if "provenance" in blockers:
        fields = ", ".join(fundamentals.missing_provenance_fields) or "one unambiguous fundamentals row"
        return f"Review exact fundamentals provenance for {ticker}: {fields}; keep missing evidence uninferred."
    if "price_lineage" in blockers:
        fields = ", ".join(price.missing_provenance_fields) if price is not None else "latest price evidence"
        return f"Review exact latest-price lineage for {ticker}: {fields or 'one unambiguous latest row'}; keep provider identity uninferred."
    if "temporal_evidence" in blockers:
        return f"Review the exact price retrieval timestamp and cutoff evidence for {ticker}."
    if "exact_source_rights" in blockers:
        sources: list[str] = []
        if fundamentals.rights_status != "approved":
            sources.append(fundamentals.source_id)
        if (
            price is not None
            and price.rights_status != "approved"
            and price.source_id not in {"", "<missing>", "<ambiguous>"}
        ):
            sources.append(price.source_id)
        return f"Owner decision required for exact-source commercial rights: {' | '.join(sources)}; keep identifiers intact."
    if "registered_field_scope" in blockers:
        fields = list(fundamentals.missing_supported_fields)
        if price is not None:
            fields.extend(price.missing_supported_fields)
        return f"Owner review required for registered field scope on {ticker}: {', '.join(dict.fromkeys(fields))}."
    return f"Evidence gates are complete for {ticker}; independent review is still required before a separate readiness decision."


def _candidate(
    fundamentals: ReadinessPromotionEvidence,
    feature: str,
    price: DcfPriceLineageEvidence | None,
) -> ReadinessRemediationCandidate:
    blockers = _independent_blockers(fundamentals, price)
    details = tuple(f"fundamentals:{item}" for item in fundamentals.blockers)
    if price is not None:
        details += tuple(f"price:{item}" for item in price.blockers)
    return ReadinessRemediationCandidate(
        ticker=fundamentals.ticker,
        feature=feature,
        status="withheld" if blockers else "evidence_reviewable",
        independent_blockers=blockers,
        blocker_details=details,
        fundamentals_source=fundamentals.source_id,
        rights_status=fundamentals.rights_status,
        missing_provenance_fields=fundamentals.missing_provenance_fields,
        missing_registered_fields=fundamentals.missing_supported_fields,
        price_source=price.source_id if price is not None else "not_applicable",
        price_rights_status=price.rights_status if price is not None else "not_applicable",
        price_temporal_status=price.temporal_status if price is not None else "not_applicable",
        price_missing_provenance_fields=(price.missing_provenance_fields if price is not None else ()),
        price_missing_registered_fields=(price.missing_supported_fields if price is not None else ()),
        next_review_instruction=_next_review_instruction(fundamentals.ticker, blockers, fundamentals, price),
    )


def build_remediation_from_preview(
    preview: ReadinessImpactPreview,
    *,
    top_n: int = 20,
) -> ReadinessEvidenceRemediation:
    """Project existing preview evidence into a closest-first, fail-closed queue."""

    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    promotion_review = preview.promotion_review
    change_review = preview.change_review
    price_review = preview.dcf_price_lineage_review
    promotion_rows = promotion_review.evidence_rows if promotion_review is not None else ()
    price_by_ticker = {
        item.ticker: item for item in (price_review.evidence_rows if price_review is not None else ())
    }
    all_candidates: list[ReadinessRemediationCandidate] = []
    for evidence in promotion_rows:
        for promoted_field in evidence.promoted_fields:
            feature = promoted_field.removesuffix("_ready")
            price = price_by_ticker.get(evidence.ticker) if feature == "dcf" else None
            all_candidates.append(_candidate(evidence, feature, price))
    all_candidates.sort(
        key=lambda item: (
            len(item.independent_blockers),
            len(item.blocker_details),
            item.ticker,
            FEATURE_ORDER.get(item.feature, 99),
        )
    )
    blocker_counts = tuple(
        (name, sum(name in item.independent_blockers for item in all_candidates))
        for name in INDEPENDENT_BLOCKER_ORDER
        if any(name in item.independent_blockers for item in all_candidates)
    )
    return ReadinessEvidenceRemediation(
        status="inspection_only",
        preview_status=preview.status,
        saved_snapshot_identity=preview.saved_snapshot_identity,
        proposed_snapshot_identity=preview.proposed_snapshot_identity,
        saved_ticker_count=preview.saved_ticker_count,
        proposed_ticker_count=preview.proposed_ticker_count,
        changed_ticker_count=preview.changed_ticker_count,
        added_ticker_count=change_review.added_ticker_count if change_review is not None else 0,
        removed_ticker_count=change_review.removed_ticker_count if change_review is not None else 0,
        method_fit_exclusion_counts=(change_review.newly_excluded_counts if change_review is not None else ()),
        fundamentals_promotion_count=(
            promotion_review.fundamentals_promotion_count if promotion_review is not None else 0
        ),
        dcf_promotion_count=promotion_review.dcf_promotion_count if promotion_review is not None else 0,
        independent_blocker_counts=blocker_counts,
        candidate_count=len(all_candidates),
        candidates=tuple(all_candidates[:top_n]),
        top_n=top_n,
    )


def build_readiness_evidence_remediation(
    root: Path | str,
    *,
    data_dir: Path | str | None = None,
    top_n: int = 20,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
) -> ReadinessEvidenceRemediation:
    preview = build_readiness_impact_preview(
        root,
        data_dir=data_dir,
        top_n=top_n,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
        include_all_evidence=True,
    )
    return build_remediation_from_preview(preview, top_n=top_n)


def render_readiness_evidence_remediation_json(packet: ReadinessEvidenceRemediation) -> str:
    return json.dumps(asdict(packet), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _format_counts(values: tuple[tuple[str, int], ...]) -> str:
    return ", ".join(f"{name}={count}" for name, count in values) or "none"


def render_readiness_evidence_remediation(packet: ReadinessEvidenceRemediation) -> str:
    lines = [
        "Readiness Evidence Remediation Queue",
        "",
        f"Status: {packet.status}",
        f"Preview status: {packet.preview_status}",
        f"Saved snapshot identity: {packet.saved_snapshot_identity or '<unavailable>'}",
        f"Proposed snapshot identity: {packet.proposed_snapshot_identity or '<unavailable>'}",
        f"Ticker rows: saved={packet.saved_ticker_count}, proposed={packet.proposed_ticker_count}",
        f"Changed tickers: {packet.changed_ticker_count}",
        f"Universe rows: added={packet.added_ticker_count}, removed={packet.removed_ticker_count}",
        f"Method-fit exclusions: {_format_counts(packet.method_fit_exclusion_counts)}",
        (
            "Technical promotions: "
            f"fundamentals={packet.fundamentals_promotion_count}, DCF={packet.dcf_promotion_count}"
        ),
        f"Independent blocker counts: {_format_counts(packet.independent_blocker_counts)}",
        f"Candidates: total={packet.candidate_count}, shown={len(packet.candidates)}, TOP_N={packet.top_n}",
    ]
    for item in packet.candidates:
        blockers = ",".join(item.independent_blockers) or "none"
        details = ",".join(item.blocker_details) or "none"
        missing_scope = ",".join(item.missing_registered_fields) or "none"
        missing_provenance = ",".join(item.missing_provenance_fields) or "none"
        price_missing_scope = ",".join(item.price_missing_registered_fields) or "none"
        price_missing_provenance = ",".join(item.price_missing_provenance_fields) or "none"
        lines.extend(
            [
                (
                    f"- {item.ticker} / {item.feature}: status={item.status}; blockers={blockers}; "
                    f"details={details}"
                ),
                (
                    f"  fundamentals_source={item.fundamentals_source!r}; rights={item.rights_status}; "
                    f"missing_provenance={missing_provenance}; missing_registered_fields={missing_scope}"
                ),
                (
                    f"  price_source={item.price_source!r}; price_rights={item.price_rights_status}; "
                    f"price_temporal={item.price_temporal_status}; "
                    f"price_missing_provenance={price_missing_provenance}; "
                    f"price_missing_registered_fields={price_missing_scope}"
                ),
                f"  next_review={item.next_review_instruction}",
            ]
        )
    lines.extend(
        [
            "",
            f"canonical_apply_authorized={str(packet.canonical_apply_authorized).lower()}",
            (
                "readiness_materialization_authorized="
                f"{str(packet.readiness_materialization_authorized).lower()}"
            ),
            f"source_rights_change_authorized={str(packet.source_rights_change_authorized).lower()}",
            "repository_writes=[]",
            "Numerical completeness never overrides an independent evidence blocker.",
            "Research workflow evidence only; not investment advice or a recommendation.",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a stdout-only readiness evidence remediation queue.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--data-dir")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--review-cutoff")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        packet = build_readiness_evidence_remediation(
            Path(args.project_root),
            data_dir=args.data_dir,
            top_n=args.top_n,
            review_cutoff=args.review_cutoff,
        )
    except (KeyError, OSError, ValueError) as exc:
        print(f"Readiness evidence remediation failed: {exc}")
        print("repository_writes=[]")
        return 1
    print(
        render_readiness_evidence_remediation_json(packet)
        if args.json
        else render_readiness_evidence_remediation(packet)
    )
    return 2 if packet.preview_status == "missing_saved_snapshot" else 0


if __name__ == "__main__":
    raise SystemExit(main())
