"""Deterministic, inspection-only Golden Evidence Cohort packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd

from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.company_analysis_scope import company_dcf_exclusion_reasons
from src.dcf_price_lineage import DcfPriceLineageEvidence, review_dcf_price_lineage
from src.focused_research_cohort import build_focused_cohort
from src.paths import resolve_data_dir, resolve_project_root
from src.readiness_evidence_remediation import (
    INDEPENDENT_BLOCKER_ORDER,
    ReadinessEvidenceRemediation,
    ReadinessRemediationCandidate,
    build_remediation_from_preview,
)
from src.readiness_preview import (
    STABLE_READINESS_FIELDS,
    ReadinessImpactPreview,
    build_readiness_impact_preview,
)


OPERATING_ASSET_TYPES = {"company", "adr"}
METHOD_FIT_ASSET_TYPES = {"etf", "index", "index_proxy", "fund"}
FUNDAMENTAL_SCOPE_FIELDS = (
    "revenue",
    "free_cash_flow",
    "fcf_margin",
    "shares_outstanding",
    "filing_dates",
)
RESEARCH_ONLY_BOUNDARY = "Research workflow evidence only; no security action guidance."


@dataclass(frozen=True)
class GoldenEvidenceMember:
    ticker: str
    asset_type: str
    cohort_role: str
    selection_reason: str
    state: str
    saved_readiness_identity: str
    proposed_readiness_identity: str
    usable_evidence_lanes: tuple[str, ...]
    withheld_evidence_lanes: tuple[str, ...]
    source_identifiers: tuple[str, ...]
    source_rights_states: tuple[str, ...]
    missing_registered_fields: tuple[str, ...]
    provenance_omissions: tuple[str, ...]
    temporal_evidence_omissions: tuple[str, ...]
    price_lineage_omissions: tuple[str, ...]
    method_fit_exclusions: tuple[str, ...]
    independent_blockers: tuple[str, ...]
    owner_decision_required: bool
    next_evidence_review_action: str
    saved_research_loop_status: str
    research_only_boundary: str


@dataclass(frozen=True)
class GoldenEvidenceCohort:
    status: str
    saved_snapshot_identity: str
    proposed_snapshot_identity: str
    members: tuple[GoldenEvidenceMember, ...]
    top_n: int
    inspection_only: bool = True
    canonical_apply_authorized: bool = False
    readiness_materialization_authorized: bool = False
    source_rights_change_authorized: bool = False
    recommendation_authorized: bool = False
    repository_writes: tuple[str, ...] = ()
    research_only_boundary: str = RESEARCH_ONLY_BOUNDARY


def _text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _truthy(value: object) -> bool:
    return _text(value).lower() in {"true", "1", "yes", "y"}


def _ticker(value: object) -> str:
    return _text(value).upper()


def _feature_set(value: object) -> set[str]:
    return {part.strip().lower() for part in _text(value).split(",") if part.strip()}


def _normalized(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty or "ticker" not in frame.columns:
        return pd.DataFrame()
    result = frame.copy()
    result.columns = [str(column).strip().lower() for column in result.columns]
    result["ticker"] = result["ticker"].map(_ticker)
    return result.loc[result["ticker"].ne("")].copy()


def _row_index(frame: pd.DataFrame | None) -> dict[str, pd.Series]:
    normalized = _normalized(frame)
    if normalized.empty:
        return {}
    return {
        ticker: group.iloc[-1]
        for ticker, group in normalized.groupby("ticker", sort=False)
    }


def _rows_by_ticker(frame: pd.DataFrame | None) -> dict[str, tuple[pd.Series, ...]]:
    normalized = _normalized(frame)
    if normalized.empty:
        return {}
    return {
        ticker: tuple(group.iloc[index] for index in range(len(group)))
        for ticker, group in normalized.groupby("ticker", sort=False)
    }


def _readiness_identity(row: pd.Series | None) -> str:
    if row is None:
        return "unavailable"
    payload = {
        field: _text(row.get(field)) if field not in {"price_ready", "momentum_ready", "fundamentals_ready", "dcf_ready", "peer_ready", "earnings_ready", "analyst_estimates_ready"} else _truthy(row.get(field))
        for field in ("ticker", *STABLE_READINESS_FIELDS)
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _ordered_unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _asset_type(ticker: str, saved: Mapping[str, pd.Series], proposed: Mapping[str, pd.Series], universe: Mapping[str, pd.Series]) -> str:
    for rows in (saved, proposed, universe):
        value = _text(rows.get(ticker, pd.Series(dtype=object)).get("asset_type")).lower()
        if value:
            return value
    return "unknown"


def _metadata(ticker: str, saved: Mapping[str, pd.Series], proposed: Mapping[str, pd.Series], universe: Mapping[str, pd.Series]) -> dict[str, object]:
    values: dict[str, object] = {}
    for column in ("name", "security_type", "industry"):
        for rows in (saved, proposed, universe):
            value = _text(rows.get(ticker, pd.Series(dtype=object)).get(column))
            if value:
                values[column] = value
                break
    return values


def _price_evidence(
    ticker: str,
    saved_row: pd.Series | None,
    prices: pd.DataFrame,
    *,
    rights_registry: Mapping[str, SourceRights],
    review_cutoff: str | None,
) -> DcfPriceLineageEvidence:
    """Reuse the existing DCF price-lineage reviewer without changing readiness."""

    baseline = pd.DataFrame([dict(saved_row) if saved_row is not None else {"ticker": ticker, "dcf_ready": False}])
    baseline["ticker"] = ticker
    baseline["dcf_ready"] = False
    proposed = baseline.copy()
    proposed["dcf_ready"] = True
    review = review_dcf_price_lineage(
        baseline,
        proposed,
        prices,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
        top_n=1,
    )
    return review.evidence_rows[0]


def _fundamental_evidence(
    ticker: str,
    rows_by_ticker: Mapping[str, tuple[pd.Series, ...]],
    rights_registry: Mapping[str, SourceRights],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return usable lanes, source ids, rights states, scope gaps, and provenance gaps."""

    rows = rows_by_ticker.get(ticker, ())
    if len(rows) != 1:
        return (), (), (), FUNDAMENTAL_SCOPE_FIELDS, ("fundamentals_row",)
    row = rows[0]
    source_id = _text(row.get("source"))
    source_ref = _text(row.get("source_ref")) or _text(row.get("sec_accession"))
    as_of_date = _text(row.get("as_of_date"))
    provenance = tuple(
        field
        for field, value in (("source", source_id), ("source_reference", source_ref), ("as_of_date", as_of_date))
        if not value
    )
    scope = review_commercial_field_scope(rights_registry, source_id, FUNDAMENTAL_SCOPE_FIELDS)
    usable: list[str] = []
    if not provenance and scope.commercial_rights_approved:
        if "revenue" not in scope.missing_supported_fields and _text(row.get("revenue")):
            usable.append("revenue")
        if "shares_outstanding" not in scope.missing_supported_fields and _text(row.get("shares_outstanding")):
            usable.append("shares_outstanding")
        if "free_cash_flow" not in scope.missing_supported_fields and _text(row.get("free_cash_flow")):
            usable.append("free_cash_flow")
        if "fcf_margin" not in scope.missing_supported_fields and _text(row.get("fcf_margin")):
            usable.append("fcf_margin")
        if (
            "filing_dates" not in scope.missing_supported_fields
            and (_text(row.get("sec_filed_date")) or _text(row.get("filed_date")))
        ):
            usable.append("filing_date")
    source_ids = (source_id,) if source_id else ()
    rights = (f"{source_id}:{scope.rights_status}",) if source_id else ("<missing>:unknown_source",)
    return tuple(usable), source_ids, rights, scope.missing_supported_fields, provenance


def _candidate_groups(packet: ReadinessEvidenceRemediation) -> dict[str, tuple[ReadinessRemediationCandidate, ...]]:
    groups: dict[str, list[ReadinessRemediationCandidate]] = {}
    for candidate in packet.candidates:
        groups.setdefault(candidate.ticker, []).append(candidate)
    return {ticker: tuple(items) for ticker, items in groups.items()}


def _merged_candidate_blockers(candidates: tuple[ReadinessRemediationCandidate, ...]) -> tuple[str, ...]:
    seen = {blocker for candidate in candidates for blocker in candidate.independent_blockers}
    return tuple(blocker for blocker in INDEPENDENT_BLOCKER_ORDER if blocker in seen)


def _state_from_blockers(blockers: tuple[str, ...]) -> str:
    mapping = {
        "provenance": "withheld_provenance",
        "price_lineage": "withheld_price_lineage",
        "temporal_evidence": "withheld_temporal_evidence",
        "exact_source_rights": "withheld_exact_source_rights",
        "registered_field_scope": "withheld_registered_field_scope",
    }
    return next((mapping[blocker] for blocker in blockers if blocker in mapping), "insufficient_evidence")


def _withheld_lanes(
    usable: tuple[str, ...],
    *,
    method_fit: tuple[str, ...],
) -> tuple[str, ...]:
    lanes = [
        lane
        for lane in (
            "revenue",
            "price_lineage",
            "free_cash_flow",
            "fcf_margin",
            "shares_outstanding",
            "filing_date",
            "dcf",
            "peers",
            "earnings_dates",
            "point_in_time_consensus",
        )
        if lane not in usable
    ]
    if method_fit:
        lanes = [lane for lane in lanes if lane != "dcf"]
    return tuple(lanes)


def _member(
    *,
    ticker: str,
    asset_type: str,
    role: str,
    reason: str,
    saved_row: pd.Series | None,
    proposed_row: pd.Series | None,
    fundamentals: Mapping[str, tuple[pd.Series, ...]],
    prices: pd.DataFrame,
    rights_registry: Mapping[str, SourceRights],
    review_cutoff: str | None,
    candidate_rows: tuple[ReadinessRemediationCandidate, ...] = (),
    method_fit: tuple[str, ...] = (),
) -> GoldenEvidenceMember:
    usable, sources, rights, missing_scope, provenance = _fundamental_evidence(
        ticker, fundamentals, rights_registry
    )
    price = _price_evidence(
        ticker,
        saved_row,
        prices,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
    )
    price_blockers = tuple(price.blockers)
    price_lineage = _ordered_unique(list(price.missing_provenance_fields) + [blocker for blocker in price_blockers if blocker in {"missing_latest_price_row", "ambiguous_latest_price_row"}])
    temporal = tuple(
        blocker
        for blocker in price_blockers
        if blocker in {
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
    )
    blockers = list(_merged_candidate_blockers(candidate_rows))
    if price_lineage:
        blockers.append("price_lineage")
    if temporal:
        blockers.append("temporal_evidence")
    if price.rights_status != "approved":
        blockers.append("exact_source_rights")
    if price.missing_supported_fields:
        blockers.append("registered_field_scope")
    if missing_scope:
        blockers.append("registered_field_scope")
    if provenance:
        blockers.append("provenance")
    blockers = tuple(blocker for blocker in INDEPENDENT_BLOCKER_ORDER if blocker in set(blockers))
    if (
        price.latest_row_count == 1
        and not price.missing_provenance_fields
        and price.temporal_status == "temporal_complete"
        and price.rights_status == "approved"
        and not price.missing_supported_fields
    ):
        usable = _ordered_unique(list(usable) + ["price_lineage"])
    if (
        saved_row is not None
        and _truthy(saved_row.get("dcf_ready"))
        and not method_fit
        and {"price_lineage", "revenue", "free_cash_flow", "fcf_margin", "shares_outstanding"}
        <= set(usable)
    ):
        usable = _ordered_unique(list(usable) + ["dcf"])
    price_rights = (f"{price.source_id}:{price.rights_status}",)
    sources = _ordered_unique(list(sources) + [price.source_id])
    rights = _ordered_unique(list(rights) + list(price_rights))
    withheld = _withheld_lanes(usable, method_fit=method_fit)
    if method_fit:
        state = "method_fit_excluded"
    elif role == "saved_operating_company" and usable:
        state = "reviewable_saved_evidence"
    else:
        state = _state_from_blockers(blockers)
    if role == "method_fit_exclusion":
        next_action = "Use a method appropriate to the saved fund or index evidence; keep company DCF excluded."
    elif blockers and blockers[0] == "price_lineage":
        omissions = ", ".join(price_lineage) or "one unambiguous latest-price row"
        next_action = (
            f"Review exact latest-price lineage for {ticker}: {omissions}; "
            "keep source or provider identity uninferred."
        )
    elif blockers and blockers[0] == "temporal_evidence":
        next_action = f"Review the exact price retrieval timestamp and cutoff evidence for {ticker}."
    elif blockers and blockers[0] == "exact_source_rights":
        unresolved_sources = tuple(
            source for source in sources if f"{source}:approved" not in rights
        )
        next_action = (
            f"Owner decision required for exact-source commercial rights on {ticker}: "
            f"{' | '.join(unresolved_sources) or '<missing>'}; keep identifiers intact."
        )
    elif blockers and blockers[0] == "registered_field_scope":
        next_action = (
            f"Owner review required for registered field scope on {ticker}: "
            f"{', '.join(_ordered_unique(list(missing_scope) + list(price.missing_supported_fields))) or 'required fields'}."
        )
    elif blockers and blockers[0] == "provenance":
        next_action = (
            f"Review exact fundamentals provenance for {ticker}: "
            f"{', '.join(provenance) or 'one unambiguous fundamentals row'}; keep missing evidence uninferred."
        )
    elif blockers:
        next_action = f"Independent review must classify the primary evidence blocker for {ticker}."
    else:
        next_action = "Review saved evidence before any separate owner decision."
    return GoldenEvidenceMember(
        ticker=ticker,
        asset_type=asset_type,
        cohort_role=role,
        selection_reason=reason,
        state=state,
        saved_readiness_identity=_readiness_identity(saved_row),
        proposed_readiness_identity=_readiness_identity(proposed_row),
        usable_evidence_lanes=usable,
        withheld_evidence_lanes=withheld,
        source_identifiers=sources,
        source_rights_states=rights,
        missing_registered_fields=_ordered_unique(list(missing_scope) + list(price.missing_supported_fields)),
        provenance_omissions=provenance,
        temporal_evidence_omissions=temporal,
        price_lineage_omissions=price_lineage,
        method_fit_exclusions=method_fit,
        independent_blockers=blockers,
        owner_decision_required=bool(
            {"exact_source_rights", "registered_field_scope"} & set(blockers)
        ),
        next_evidence_review_action=next_action,
        saved_research_loop_status="partial_saved_evidence_only",
        research_only_boundary=RESEARCH_ONLY_BOUNDARY,
    )


def build_golden_evidence_cohort_from_evidence(
    saved_readiness: pd.DataFrame,
    proposed_readiness: pd.DataFrame,
    universe_master: pd.DataFrame,
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    preview: ReadinessImpactPreview,
    rights_registry: Mapping[str, SourceRights],
    top_n: int = 5,
    review_cutoff: str | None = None,
) -> GoldenEvidenceCohort:
    """Compose saved cohort, remediation, rights, and method-fit evidence without writing."""

    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    saved = _normalized(saved_readiness)
    proposed = _normalized(proposed_readiness)
    universe = _normalized(universe_master)
    saved_by_ticker = _row_index(saved)
    proposed_by_ticker = _row_index(proposed)
    universe_by_ticker = _row_index(universe)
    fundamental_rows = _rows_by_ticker(fundamentals)

    full_remediation = build_remediation_from_preview(
        preview,
        top_n=max(1, len(preview.promotion_review.evidence_rows if preview.promotion_review else ()) * 2),
    )
    candidate_groups = _candidate_groups(full_remediation)
    focused = build_focused_cohort(
        saved,
        universe,
        target_size=3,
        minimum_size=1,
        profile_freshness="stale_saved_evidence",
    )
    members: list[GoldenEvidenceMember] = []
    selected = set()
    for focused_member in focused.members[:3]:
        ticker = focused_member.ticker
        selected.add(ticker)
        members.append(
            _member(
                ticker=ticker,
                asset_type=_asset_type(ticker, saved_by_ticker, proposed_by_ticker, universe_by_ticker),
                role="saved_operating_company",
                reason="Selected from the existing saved focused-cohort order; saved evidence remains separately gated.",
                saved_row=saved_by_ticker.get(ticker),
                proposed_row=proposed_by_ticker.get(ticker),
                fundamentals=fundamental_rows,
                prices=prices,
                rights_registry=rights_registry,
                review_cutoff=review_cutoff,
            )
        )

    control_ticker = next(
        (
            ticker
            for ticker in candidate_groups
            if ticker not in selected
            and _asset_type(ticker, saved_by_ticker, proposed_by_ticker, universe_by_ticker) in OPERATING_ASSET_TYPES
        ),
        "",
    )
    if control_ticker:
        selected.add(control_ticker)
        members.append(
            _member(
                ticker=control_ticker,
                asset_type=_asset_type(control_ticker, saved_by_ticker, proposed_by_ticker, universe_by_ticker),
                role="evidence_gap_control",
                reason="First distinct operating-company control in the existing remediation order; same-ticker feature evidence is aggregated.",
                saved_row=saved_by_ticker.get(control_ticker),
                proposed_row=proposed_by_ticker.get(control_ticker),
                fundamentals=fundamental_rows,
                prices=prices,
                rights_registry=rights_registry,
                review_cutoff=review_cutoff,
                candidate_rows=candidate_groups[control_ticker],
            )
        )

    method_tickers = sorted(
        ticker
        for ticker, row in saved_by_ticker.items()
        if ticker not in selected
        and _asset_type(ticker, saved_by_ticker, proposed_by_ticker, universe_by_ticker) in METHOD_FIT_ASSET_TYPES
        and "dcf" in _feature_set(row.get("excluded_features"))
    )
    if method_tickers:
        ticker = method_tickers[0]
        metadata = _metadata(ticker, saved_by_ticker, proposed_by_ticker, universe_by_ticker)
        method_asset_type = _asset_type(ticker, saved_by_ticker, proposed_by_ticker, universe_by_ticker)
        method_fit = company_dcf_exclusion_reasons(
            "index_proxy" if method_asset_type == "index" else method_asset_type,
            metadata,
            None,
        )
        if method_fit:
            members.append(
                _member(
                    ticker=ticker,
                    asset_type=_asset_type(ticker, saved_by_ticker, proposed_by_ticker, universe_by_ticker),
                    role="method_fit_exclusion",
                    reason="Distinct saved ETF, index, or fund with an explicit company-DCF method-fit exclusion.",
                    saved_row=saved_by_ticker.get(ticker),
                    proposed_row=proposed_by_ticker.get(ticker),
                    fundamentals=fundamental_rows,
                    prices=prices,
                    rights_registry=rights_registry,
                    review_cutoff=review_cutoff,
                    method_fit=method_fit,
                )
            )
    emitted = tuple(members[: min(top_n, 5)])
    return GoldenEvidenceCohort(
        status="inspection_only",
        saved_snapshot_identity=preview.saved_snapshot_identity,
        proposed_snapshot_identity=preview.proposed_snapshot_identity,
        members=emitted,
        top_n=top_n,
    )


def build_golden_evidence_cohort(
    root: Path | str,
    *,
    data_dir: Path | str | None = None,
    top_n: int = 5,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
) -> GoldenEvidenceCohort:
    project_root = resolve_project_root(root)
    data_path = resolve_data_dir(data_dir, project_root)
    saved_path = data_path / "reports" / "ticker_readiness_report.csv"
    saved = pd.read_csv(saved_path) if saved_path.exists() else pd.DataFrame()
    preview = build_readiness_impact_preview(
        project_root,
        data_dir=data_path,
        top_n=max(top_n, 5),
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
        include_all_evidence=True,
    )
    proposed = pd.DataFrame()
    if preview.status != "missing_saved_snapshot":
        from src.readiness_engine import build_ticker_readiness_report

        proposed = build_ticker_readiness_report(
            project_root, data_dir=data_path, write_outputs=False
        )["ticker_readiness_report"]
    universe_path = data_path / "universe_master.csv"
    fundamentals_path = data_path / "fundamentals.csv"
    prices_path = data_path / "prices.csv"
    registry = (
        rights_registry
        if rights_registry is not None
        else load_source_rights_registry(project_root / "config" / "source_rights.yml")
    )
    return build_golden_evidence_cohort_from_evidence(
        saved,
        proposed,
        pd.read_csv(universe_path) if universe_path.exists() else pd.DataFrame(),
        pd.read_csv(fundamentals_path) if fundamentals_path.exists() else pd.DataFrame(),
        pd.read_csv(prices_path) if prices_path.exists() else pd.DataFrame(),
        preview=preview,
        rights_registry=registry,
        top_n=top_n,
        review_cutoff=review_cutoff,
    )


def render_golden_evidence_cohort_json(packet: GoldenEvidenceCohort) -> str:
    return json.dumps(asdict(packet), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def render_golden_evidence_cohort(packet: GoldenEvidenceCohort) -> str:
    lines = [
        "Golden Evidence Cohort",
        "",
        f"status={packet.status}",
        f"saved_snapshot_identity={packet.saved_snapshot_identity or '<unavailable>'}",
        f"proposed_snapshot_identity={packet.proposed_snapshot_identity or '<unavailable>'}",
        f"members={len(packet.members)}; TOP_N={packet.top_n}",
    ]
    for member in packet.members:
        lines.extend(
            [
                f"- {member.ticker}: role={member.cohort_role}; state={member.state}",
                f"  asset_type={member.asset_type}",
                f"  reason={member.selection_reason}",
                f"  saved_readiness_identity={member.saved_readiness_identity}",
                f"  proposed_readiness_identity={member.proposed_readiness_identity}",
                f"  usable_evidence_lanes={','.join(member.usable_evidence_lanes) or 'none'}",
                f"  withheld_evidence_lanes={','.join(member.withheld_evidence_lanes) or 'none'}",
                f"  independent_blockers={','.join(member.independent_blockers) or 'none'}",
                f"  source_identifiers={','.join(member.source_identifiers) or 'none'}",
                f"  source_rights_states={','.join(member.source_rights_states) or 'none'}",
                f"  missing_registered_fields={','.join(member.missing_registered_fields) or 'none'}",
                f"  provenance_omissions={','.join(member.provenance_omissions) or 'none'}",
                f"  temporal_evidence_omissions={','.join(member.temporal_evidence_omissions) or 'none'}",
                f"  price_lineage_omissions={','.join(member.price_lineage_omissions) or 'none'}",
                f"  method_fit_exclusions={','.join(member.method_fit_exclusions) or 'none'}",
                f"  owner_decision_required={str(member.owner_decision_required).lower()}",
                f"  next_evidence_review_action={member.next_evidence_review_action}",
                f"  saved_research_loop_status={member.saved_research_loop_status}",
                f"  research_only_boundary={member.research_only_boundary}",
            ]
        )
    lines.extend(
        [
            "",
            "inspection_only=true",
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
    parser = argparse.ArgumentParser(description="Build a deterministic, inspection-only Golden Evidence Cohort packet.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--data-dir")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--review-cutoff")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        packet = build_golden_evidence_cohort(
            Path(args.project_root),
            data_dir=args.data_dir,
            top_n=args.top_n,
            review_cutoff=args.review_cutoff,
        )
    except (KeyError, OSError, ValueError) as exc:
        print(f"Golden evidence cohort failed: {exc}")
        print("repository_writes=[]")
        return 1
    print(render_golden_evidence_cohort_json(packet) if args.json else render_golden_evidence_cohort(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
