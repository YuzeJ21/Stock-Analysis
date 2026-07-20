"""Truthful lane coverage for the focused commercial-beta cohort."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.focused_research_cohort import FocusedCohort
from src.quarterly_business_trend import QuarterlyTrendPacket


COHORT_COVERAGE_LANES = (
    "adjusted_daily_price_history",
    "quarterly_revenue",
    "quarterly_eps",
    "margins",
    "free_cash_flow",
    "cash_and_debt",
    "shares_outstanding",
    "trusted_peers",
    "filing_dates",
    "earnings_dates",
    "point_in_time_consensus",
)

ALLOWED_COVERAGE_STATES = {
    "usable_now",
    "partial",
    "candidate_context_only",
    "blocked",
    "excluded",
}


@dataclass(frozen=True)
class FocusedCohortCoverageRow:
    ticker: str
    company_name: str
    lane: str
    state: str
    evidence: str
    boundary: str


@dataclass(frozen=True)
class FocusedCohortCoverage:
    status: str
    company_count: int
    rows: tuple[FocusedCohortCoverageRow, ...]
    message: str


@dataclass(frozen=True)
class CohortSavedFieldReview:
    technical_available: bool
    provenance_complete: bool
    commercial_rights_approved: bool
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    usable: bool


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


def _normalized_readiness(frame: pd.DataFrame | None) -> dict[str, pd.Series]:
    if frame is None or frame.empty or "ticker" not in frame.columns:
        return {}
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    normalized["ticker"] = normalized["ticker"].map(lambda value: _text(value).upper())
    normalized = normalized[normalized["ticker"].ne("")].drop_duplicates("ticker", keep="last")
    return {str(row["ticker"]): row for _, row in normalized.iterrows()}


def _row_map(frame: pd.DataFrame | None) -> dict[str, pd.Series]:
    return _normalized_readiness(frame)


def _has_value(row: pd.Series | None, *fields: str) -> bool:
    if row is None:
        return False
    for field in fields:
        if field not in row.index:
            continue
        value = row.get(field)
        if _text(value):
            return True
    return False


def _commercial_field_review(
    row: pd.Series | None,
    *,
    technical_available: bool,
    required_fields: tuple[str, ...],
    commercial_mode: bool = False,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> CohortSavedFieldReview:
    research_source_backed = bool(
        row is not None and _has_value(row, "source", "source_ref", "sec_accession")
    )
    provenance_complete = bool(
        row is not None
        and _has_value(row, "source")
        and _has_value(row, "source_ref", "sec_accession")
    )
    if not commercial_mode:
        return CohortSavedFieldReview(
            technical_available=technical_available,
            provenance_complete=research_source_backed,
            commercial_rights_approved=True,
            required_supported_fields=required_fields,
            missing_supported_fields=(),
            usable=technical_available and research_source_backed,
        )
    source_id = _text(row.get("source")) if row is not None else ""
    registry = rights_registry if rights_registry is not None else load_source_rights_registry()
    review = review_commercial_field_scope(registry, source_id, required_fields)
    return CohortSavedFieldReview(
        technical_available=technical_available,
        provenance_complete=provenance_complete,
        commercial_rights_approved=review.commercial_rights_approved,
        required_supported_fields=review.required_supported_fields,
        missing_supported_fields=review.missing_supported_fields,
        usable=(
            technical_available
            and provenance_complete
            and review.commercial_evidence_ready
        ),
    )


def _populated_fields(
    row: pd.Series | None,
    field_aliases: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[str, ...]:
    return tuple(
        field
        for field, aliases in field_aliases
        if _has_value(row, *aliases)
    )


def _alternative_field_review(
    row: pd.Series | None,
    field_aliases: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    commercial_mode: bool,
    rights_registry: Mapping[str, SourceRights] | None,
) -> CohortSavedFieldReview:
    populated = _populated_fields(row, field_aliases)
    if not populated:
        return _commercial_field_review(
            row,
            technical_available=False,
            required_fields=(),
            commercial_mode=commercial_mode,
            rights_registry=rights_registry,
        )
    reviews = tuple(
        _commercial_field_review(
            row,
            technical_available=True,
            required_fields=(field,),
            commercial_mode=commercial_mode,
            rights_registry=rights_registry,
        )
        for field in populated
    )
    if any(review.usable for review in reviews):
        selected = next(review for review in reviews if review.usable)
        return CohortSavedFieldReview(
            technical_available=True,
            provenance_complete=selected.provenance_complete,
            commercial_rights_approved=selected.commercial_rights_approved,
            required_supported_fields=populated,
            missing_supported_fields=(),
            usable=True,
        )
    return CohortSavedFieldReview(
        technical_available=True,
        provenance_complete=all(review.provenance_complete for review in reviews),
        commercial_rights_approved=all(
            review.commercial_rights_approved for review in reviews
        ),
        required_supported_fields=populated,
        missing_supported_fields=tuple(
            field
            for review in reviews
            for field in review.missing_supported_fields
        ),
        usable=False,
    )


def _commercial_blocked_evidence(
    review: CohortSavedFieldReview,
    *,
    available: str,
    missing: str,
) -> str:
    if review.usable:
        return available
    if not review.technical_available:
        return missing
    if not review.provenance_complete:
        return "A saved technical value exists, but source provenance is incomplete."
    if not review.commercial_rights_approved:
        return "A saved technical value and provenance exist, but exact-source commercial rights are not approved."
    fields = ", ".join(review.missing_supported_fields) or "required lane field"
    return (
        "A saved technical value and provenance exist, but registered field scope "
        f"is incomplete: {fields}."
    )


def _price_history_review(
    rows: tuple[pd.Series, ...],
    *,
    technical_available_hint: bool,
    lineage_columns_missing: tuple[str, ...],
    commercial_mode: bool,
    rights_registry: Mapping[str, SourceRights] | None,
) -> CohortSavedFieldReview:
    valid_rows: list[pd.Series] = []
    for row in rows:
        date = pd.to_datetime(row.get("date"), errors="coerce")
        close = pd.to_numeric(
            row.get("adj_close") if _has_value(row, "adj_close") else row.get("close"),
            errors="coerce",
        )
        if pd.notna(date) and pd.notna(close) and float(close) > 0:
            valid_rows.append(row)
    if not valid_rows and not (technical_available_hint and lineage_columns_missing):
        return CohortSavedFieldReview(False, False, False, ("prices",), (), False)
    if not commercial_mode:
        return CohortSavedFieldReview(True, True, True, ("prices",), (), True)

    if not valid_rows and lineage_columns_missing:
        return CohortSavedFieldReview(True, False, False, ("prices",), (), False)

    registry = rights_registry if rights_registry is not None else load_source_rights_registry()
    provenance_complete = all(
        _has_value(row, "source")
        and _has_value(row, "source_ref")
        and _has_value(row, "retrieved_at")
        for row in valid_rows
    )
    source_reviews = tuple(
        review_commercial_field_scope(
            registry, _text(row.get("source")), ("prices",)
        )
        for row in valid_rows
    )
    rights_approved = all(review.commercial_rights_approved for review in source_reviews)
    missing_scope = tuple(
        dict.fromkeys(
            field
            for review in source_reviews
            for field in review.missing_supported_fields
        )
    )
    return CohortSavedFieldReview(
        technical_available=True,
        provenance_complete=provenance_complete,
        commercial_rights_approved=rights_approved,
        required_supported_fields=("prices",),
        missing_supported_fields=missing_scope,
        usable=provenance_complete and rights_approved and not missing_scope,
    )


def _latest_consensus_by_cutoff(frame: pd.DataFrame | None, *, as_of: str | None) -> dict[str, pd.Series]:
    if frame is None or frame.empty or not as_of or "ticker" not in frame.columns:
        return {}
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    timestamp_column = next(
        (column for column in ("snapshot_at", "available_at", "retrieved_at", "published_at") if column in normalized.columns),
        "",
    )
    if not timestamp_column:
        return {}
    normalized["ticker"] = normalized["ticker"].map(lambda value: _text(value).upper())
    normalized["_snapshot_at"] = pd.to_datetime(normalized[timestamp_column], utc=True, errors="coerce")
    cutoff = pd.to_datetime(as_of, utc=True, errors="coerce")
    if pd.isna(cutoff):
        raise ValueError("as_of must be an ISO-8601 timestamp")
    normalized = normalized[
        normalized["ticker"].ne("")
        & normalized["_snapshot_at"].notna()
        & normalized["_snapshot_at"].le(cutoff)
    ].sort_values("_snapshot_at")
    normalized = normalized.drop_duplicates("ticker", keep="last")
    return {str(row["ticker"]): row for _, row in normalized.iterrows()}


def _grouped_rows(frame: pd.DataFrame | None) -> dict[str, tuple[pd.Series, ...]]:
    if frame is None or frame.empty or "ticker" not in frame.columns:
        return {}
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    normalized["ticker"] = normalized["ticker"].map(lambda value: _text(value).upper())
    return {
        ticker: tuple(row for _, row in group.iterrows())
        for ticker, group in normalized[normalized["ticker"].ne("")].groupby("ticker", sort=True)
    }


def derive_cohort_evidence(
    tickers: tuple[str, ...],
    *,
    fundamentals: pd.DataFrame | None = None,
    prices: pd.DataFrame | None = None,
    price_lineage_missing_fields: tuple[str, ...] = (),
    readiness: pd.DataFrame | None = None,
    universe: pd.DataFrame | None = None,
    consensus: pd.DataFrame | None = None,
    earnings: pd.DataFrame | None = None,
    peers: pd.DataFrame | None = None,
    peer_candidates: pd.DataFrame | None = None,
    as_of: str | None = None,
    commercial_mode: bool = False,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> dict[str, dict[str, object]]:
    """Derive display states only from saved rows that retain provenance."""

    fundamentals_rows = _row_map(fundamentals)
    price_rows = _grouped_rows(prices)
    readiness_rows = _row_map(readiness)
    universe_rows = _row_map(universe)
    consensus_rows = _latest_consensus_by_cutoff(consensus, as_of=as_of)
    earnings_rows = _row_map(earnings)
    peer_rows = _grouped_rows(peers)
    candidate_rows = _grouped_rows(peer_candidates)
    registry = (
        rights_registry
        if rights_registry is not None
        else load_source_rights_registry()
        if commercial_mode
        else None
    )
    result: dict[str, dict[str, object]] = {}
    for raw_ticker in tickers:
        ticker = _text(raw_ticker).upper()
        fundamental = fundamentals_rows.get(ticker)
        ready = readiness_rows.get(ticker)
        universe_row = universe_rows.get(ticker)
        consensus_row = consensus_rows.get(ticker)
        earnings_row = earnings_rows.get(ticker)
        saved_price_ready = bool(ready is not None and _truthy(ready.get("price_ready")))
        price_review = _price_history_review(
            price_rows.get(ticker, ()),
            technical_available_hint=saved_price_ready,
            lineage_columns_missing=price_lineage_missing_fields,
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        margin_review = _alternative_field_review(
            fundamental,
            (
                ("operating_margin", ("operating_margin",)),
                ("fcf_margin", ("fcf_margin",)),
                ("profit_margin", ("profit_margin",)),
            ),
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        fcf_review = _alternative_field_review(
            fundamental,
            (("free_cash_flow", ("free_cash_flow", "fcf")),),
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        cash_review = _commercial_field_review(
            fundamental,
            technical_available=_has_value(fundamental, "cash"),
            required_fields=("cash",),
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        debt_review = _commercial_field_review(
            fundamental,
            technical_available=_has_value(fundamental, "debt"),
            required_fields=("debt",),
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        shares_review = _commercial_field_review(
            fundamental,
            technical_available=_has_value(fundamental, "shares_outstanding"),
            required_fields=("shares_outstanding",),
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        filing_review = _commercial_field_review(
            fundamental,
            technical_available=_has_value(fundamental, "sec_filed_date", "filed_date"),
            required_fields=("filing_dates",),
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )

        margin_ready = margin_review.usable
        fcf_ready = fcf_review.usable
        cash_ready = cash_review.usable
        debt_ready = debt_review.usable
        shares_ready = shares_review.usable
        filing_ready = filing_review.usable
        saved_peer_ready = bool(ready is not None and _truthy(ready.get("peer_ready")))
        trusted_rows = peer_rows.get(ticker, ())
        trusted_reviews = tuple(
            _commercial_field_review(
                row,
                technical_available=True,
                required_fields=("trusted_peers",),
                commercial_mode=commercial_mode,
                rights_registry=registry,
            )
            for row in trusted_rows
        )
        trusted_source_ready = bool(trusted_reviews) and all(
            review.usable for review in trusted_reviews
        )
        peers_ready = saved_peer_ready and (trusted_source_ready if commercial_mode else True)
        candidate_count = len(candidate_rows.get(ticker, ()))
        consensus_metric_fields = _populated_fields(
            consensus_row,
            (
                ("revenue_consensus", ("revenue_consensus", "revenue_estimate")),
                ("eps_consensus", ("eps_consensus", "eps_estimate")),
            ),
        )
        consensus_base_ready = bool(
            consensus_row is not None
            and _has_value(consensus_row, "fiscal_period")
            and _has_value(consensus_row, "snapshot_at", "available_at", "retrieved_at", "published_at")
            and consensus_metric_fields
        )
        consensus_review = _commercial_field_review(
            consensus_row,
            technical_available=consensus_base_ready,
            required_fields=consensus_metric_fields,
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        consensus_ready = consensus_review.usable
        earnings_technical = bool(
            earnings_row is not None
            and _has_value(
                earnings_row,
                "earnings_date",
                "expected_report_date",
                "event_date",
                "next_earnings_date",
                "last_earnings_date",
                "report_date",
            )
        )
        earnings_review = _commercial_field_review(
            earnings_row,
            technical_available=earnings_technical,
            required_fields=("earnings_dates",),
            commercial_mode=commercial_mode,
            rights_registry=registry,
        )
        earnings_ready = earnings_review.usable
        result[ticker] = {
            "asset_type": _text(universe_row.get("asset_type")) if universe_row is not None else "company",
            "price_history_state": "usable_now" if price_review.usable else "blocked",
            "price_history_evidence": _commercial_blocked_evidence(
                price_review,
                available="Saved adjusted daily price history has complete commercial evidence.",
                missing="No technically usable adjusted daily price rows are available.",
            ),
            "margin_state": "usable_now" if margin_ready else "blocked",
            "margin_evidence": _commercial_blocked_evidence(
                margin_review,
                available="Saved source-backed margin input is available.",
                missing="No source-backed margin input is available.",
            ),
            "free_cash_flow_state": "usable_now" if fcf_ready else "blocked",
            "free_cash_flow_evidence": _commercial_blocked_evidence(
                fcf_review,
                available="Saved source-backed free cash flow is available.",
                missing="No source-backed free cash flow is available.",
            ),
            "cash_debt_state": "usable_now" if cash_ready and debt_ready else "partial" if cash_ready or debt_ready else "blocked",
            "cash_debt_evidence": (
                "Saved source-backed cash and debt are available."
                if cash_ready and debt_ready
                else "Cash and debt evidence is incomplete; "
                + "; ".join(
                    (
                        f"cash: {_commercial_blocked_evidence(cash_review, available='available', missing='missing')}",
                        f"debt: {_commercial_blocked_evidence(debt_review, available='available', missing='missing')}",
                    )
                )
            ),
            "shares_state": "usable_now" if shares_ready else "blocked",
            "shares_evidence": _commercial_blocked_evidence(
                shares_review,
                available="Saved source-backed shares outstanding are available.",
                missing="No source-backed shares-outstanding input is available.",
            ),
            "trusted_peers_state": "usable_now" if peers_ready else "candidate_context_only" if candidate_count else "blocked",
            "trusted_peers_evidence": (
                "Saved readiness and source rows confirm trusted peer inputs."
                if peers_ready
                else _commercial_blocked_evidence(
                    next(review for review in trusted_reviews if not review.usable),
                    available="Saved trusted peer evidence is available.",
                    missing="Trusted peer inputs are unavailable.",
                )
                if saved_peer_ready and trusted_reviews and not trusted_source_ready
                else f"{candidate_count} candidate peer relationship(s) are visible but not trusted."
                if candidate_count
                else "Trusted peer inputs are unavailable."
            ),
            "filing_dates_state": "usable_now" if filing_ready else "blocked",
            "filing_dates_evidence": _commercial_blocked_evidence(
                filing_review,
                available="A source-backed filing date is available.",
                missing="No source-backed filing date is available.",
            ),
            "earnings_dates_state": "usable_now" if earnings_ready else "blocked",
            "earnings_dates_evidence": _commercial_blocked_evidence(
                earnings_review,
                available="A source-backed earnings date is available.",
                missing="No permitted source-backed earnings date is available.",
            ),
            "point_in_time_consensus_state": "usable_now" if consensus_ready else "blocked",
            "point_in_time_consensus_evidence": _commercial_blocked_evidence(
                consensus_review,
                available="An exact-period point-in-time consensus snapshot is available.",
                missing=(
                    "No populated exact-period point-in-time consensus value is available."
                    if consensus_row is not None and not consensus_metric_fields
                    else "No exact-period point-in-time consensus snapshot is available."
                ),
            ),
        }
    return result


def _validated_state(value: object, *, default: str = "blocked") -> str:
    state = _text(value).lower() or default
    if state not in ALLOWED_COVERAGE_STATES:
        raise ValueError(f"unsupported coverage state: {state}")
    return state


def _quarterly_state(packet: QuarterlyTrendPacket | None, metric: str) -> tuple[str, str, str]:
    if packet is None:
        return "blocked", "No canonical quarterly actuals are available.", "Source-backed quarterly rows are required."
    trend = packet.revenue if metric == "revenue" else packet.eps
    state = {"ready": "usable_now", "partial": "partial", "blocked": "blocked"}.get(trend.status, "blocked")
    evidence = (
        f"{trend.latest_fiscal_period}: explicit quarterly {metric} from {trend.latest_source_ref}."
        if trend.latest_fiscal_period and trend.latest_source_ref
        else f"Quarterly {metric} evidence is unavailable."
    )
    boundary_parts = list(trend.missing_comparisons)
    if trend.withheld_reason:
        boundary_parts.append(trend.withheld_reason)
    boundary = "; ".join(boundary_parts) or "Comparable sequential and prior-year periods are source-backed."
    return state, evidence, boundary


def _explicit_lane(
    evidence: Mapping[str, object],
    state_key: str,
    *,
    missing: str,
    boundary: str,
) -> tuple[str, str, str]:
    state = _validated_state(evidence.get(state_key))
    evidence_text = _text(evidence.get(state_key.replace("_state", "_evidence"))) or missing
    if state == "candidate_context_only":
        boundary = f"{boundary} Candidate context is not trusted source proof."
    return state, evidence_text, boundary


def build_focused_cohort_coverage(
    cohort: FocusedCohort,
    ticker_readiness: pd.DataFrame | None,
    *,
    quarterly_packets: Mapping[str, QuarterlyTrendPacket] | None = None,
    evidence_by_ticker: Mapping[str, Mapping[str, object]] | None = None,
) -> FocusedCohortCoverage:
    """Compose saved evidence into lane states without inferring missing values."""

    if len(cohort.members) > 50:
        raise ValueError("commercial beta cohort cannot exceed 50 companies")
    readiness = _normalized_readiness(ticker_readiness)
    packets = {str(key).strip().upper(): value for key, value in (quarterly_packets or {}).items()}
    evidence_map = {str(key).strip().upper(): value for key, value in (evidence_by_ticker or {}).items()}
    rows: list[FocusedCohortCoverageRow] = []

    for member in cohort.members:
        ticker = member.ticker
        saved = readiness.get(ticker)
        evidence = evidence_map.get(ticker, {})
        asset_type = _text(evidence.get("asset_type")).lower()
        if asset_type and asset_type not in {"company", "adr"}:
            for lane in COHORT_COVERAGE_LANES:
                rows.append(
                    FocusedCohortCoverageRow(
                        ticker,
                        member.company_name,
                        lane,
                        "excluded",
                        f"{asset_type} is outside operating-company beta analysis.",
                        "Excluded means not applicable; no company valuation or forecast is produced.",
                    )
                )
            continue

        saved_price_ready = bool(saved is not None and _truthy(saved.get("price_ready")))
        reviewed_price_state = _text(evidence.get("price_history_state"))
        price_ready = saved_price_ready and (
            reviewed_price_state == "usable_now" if reviewed_price_state else True
        )
        price_state = "usable_now" if price_ready else "blocked"
        rows.append(
            FocusedCohortCoverageRow(
                ticker,
                member.company_name,
                "adjusted_daily_price_history",
                price_state,
                (
                    _text(evidence.get("price_history_evidence"))
                    if reviewed_price_state
                    else "Saved adjusted daily price history is readiness-backed."
                )
                if price_ready
                else _text(evidence.get("price_history_evidence"))
                or "Adjusted daily price history is unavailable.",
                "Price history supports trend context only; it does not create fundamentals or a recommendation.",
            )
        )

        for lane, metric in (("quarterly_revenue", "revenue"), ("quarterly_eps", "eps")):
            state, evidence_text, boundary = _quarterly_state(packets.get(ticker), metric)
            rows.append(FocusedCohortCoverageRow(ticker, member.company_name, lane, state, evidence_text, boundary))

        explicit_specs = (
            ("margins", "margin_state", "No versioned quarterly margin evidence is available.", "Margins require an explicit compatible quarterly source contract."),
            ("free_cash_flow", "free_cash_flow_state", "No versioned quarterly free-cash-flow evidence is available.", "Free cash flow is not derived from incomplete cash-flow rows."),
            ("cash_and_debt", "cash_debt_state", "Cash and debt proof is unavailable.", "Both values need source provenance and compatible effective dates."),
            ("shares_outstanding", "shares_state", "Shares-outstanding proof is unavailable.", "Shares are never inferred from price or market capitalization."),
            ("trusted_peers", "trusted_peers_state", "Trusted peer proof is unavailable.", "Candidate peers cannot unlock trusted peer analysis."),
            ("filing_dates", "filing_dates_state", "Source-backed filing dates are unavailable.", "Filing metadata is context and cannot supply missing financial facts."),
            ("earnings_dates", "earnings_dates_state", "Source-backed earnings dates are unavailable.", "Earnings dates require a permitted source and publication timestamp."),
            ("point_in_time_consensus", "point_in_time_consensus_state", "Point-in-time consensus is unavailable.", "Consensus must match the fiscal period and be available by the review cutoff."),
        )
        for lane, state_key, missing, boundary in explicit_specs:
            state, evidence_text, lane_boundary = _explicit_lane(
                evidence,
                state_key,
                missing=missing,
                boundary=boundary,
            )
            rows.append(FocusedCohortCoverageRow(ticker, member.company_name, lane, state, evidence_text, lane_boundary))

    states = {row.state for row in rows}
    status = "unavailable" if not rows else "excluded" if states == {"excluded"} else "ready" if states <= {"usable_now", "excluded"} else "partial"
    return FocusedCohortCoverage(
        status=status,
        company_count=len(cohort.members),
        rows=tuple(rows),
        message=(
            "Focused cohort lane evidence is fully usable for the supported scope."
            if status == "ready"
            else "Focused cohort coverage is mixed; blocked and context-only lanes remain explicit."
            if rows
            else "Focused cohort coverage is unavailable."
        ),
    )


def focused_cohort_coverage_frame(coverage: FocusedCohortCoverage) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": row.ticker,
                "Company": row.company_name,
                "Lane": row.lane.replace("_", " "),
                "State": row.state.replace("_", " "),
                "Evidence": row.evidence,
                "Boundary": row.boundary,
            }
            for row in coverage.rows
        ],
        columns=["Ticker", "Company", "Lane", "State", "Evidence", "Boundary"],
    )
