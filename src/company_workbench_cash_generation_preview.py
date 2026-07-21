"""Pure Company Workbench composition for non-production cash previews."""

from __future__ import annotations

from dataclasses import dataclass

from src.earnings_nowcast_contract import parse_utc_timestamp
from src.quarterly_business_trend import build_quarterly_trend_packet
from src.sec_quarterly_cash_generation_pilot import SecQuarterlyPilotPreview


@dataclass(frozen=True)
class CashGenerationPreviewMetric:
    metric: str
    status: str
    value: float | None
    fiscal_period: str
    source_refs: tuple[str, ...]
    withheld_reason: str


@dataclass(frozen=True)
class CashGenerationPreviewComponent:
    metric: str
    value: float
    currency: str
    fiscal_period: str
    source_ref: str
    published_at: str
    retrieved_at: str
    accounting_basis: str
    duration_basis: str
    q4_evidence_state: str


@dataclass(frozen=True)
class CompanyWorkbenchCashGenerationPreview:
    ticker: str
    fiscal_period: str
    status: str
    message: str
    operating_margin: CashGenerationPreviewMetric
    free_cash_flow: CashGenerationPreviewMetric
    fcf_margin: CashGenerationPreviewMetric
    blockers: tuple[str, ...]
    withheld_metrics: tuple[str, ...]
    accession: str
    source_url: str
    accepted_at: str
    cutoff: str
    capex_sign_evidence: str
    components: tuple[CashGenerationPreviewComponent, ...]
    production_activation: bool = False
    readiness_promotions: tuple[str, ...] = ()
    persistence: bool = False


def company_workbench_cash_preview_requested(value: object) -> bool:
    """Enable the bounded preview only for the exact opt-in query value."""

    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value or "").strip() == "1"


def _withheld_metric(metric: str, reason: str) -> CashGenerationPreviewMetric:
    return CashGenerationPreviewMetric(
        metric=metric,
        status="withheld",
        value=None,
        fiscal_period="",
        source_refs=(),
        withheld_reason=reason,
    )


def blocked_company_workbench_cash_generation_preview(
    ticker: str,
    *,
    fiscal_period: str = "",
    as_of: str = "",
    blockers: tuple[str, ...] = (),
    accession: str = "",
    source_url: str = "",
    accepted_at: str = "",
    capex_sign_evidence: str = "",
) -> CompanyWorkbenchCashGenerationPreview:
    """Return an all-or-nothing withheld preview with no numeric leakage."""

    stable_blockers = tuple(dict.fromkeys(str(item) for item in blockers if str(item)))
    reason = "; ".join(stable_blockers) or "cash_generation_preview_unavailable"
    return CompanyWorkbenchCashGenerationPreview(
        ticker=str(ticker or "").strip().upper(),
        fiscal_period=str(fiscal_period or "").strip().upper(),
        status="withheld",
        message="Cash-generation review preview is withheld until complete evidence passes.",
        operating_margin=_withheld_metric("operating_margin", reason),
        free_cash_flow=_withheld_metric("free_cash_flow", reason),
        fcf_margin=_withheld_metric("fcf_margin", reason),
        blockers=stable_blockers,
        withheld_metrics=("operating_margin", "free_cash_flow", "fcf_margin"),
        accession=str(accession or "").strip(),
        source_url=str(source_url or "").strip(),
        accepted_at=str(accepted_at or "").strip(),
        cutoff=str(as_of or "").strip(),
        capex_sign_evidence=str(capex_sign_evidence or "").strip(),
        components=(),
    )


def _metric(metric: str, trend) -> CashGenerationPreviewMetric:
    return CashGenerationPreviewMetric(
        metric=metric,
        status="preview_available",
        value=trend.latest_value,
        fiscal_period=trend.latest_fiscal_period,
        source_refs=tuple(
            source_ref
            for source_ref in str(trend.latest_source_ref or "").split(";")
            if source_ref
        ),
        withheld_reason=trend.withheld_reason,
    )


def compose_company_workbench_cash_generation_preview(
    pilot: SecQuarterlyPilotPreview,
    *,
    selected_ticker: str,
    as_of: str,
) -> CompanyWorkbenchCashGenerationPreview:
    """Compose one accepted pilot result without persistence or activation."""

    extraction = pilot.extraction
    try:
        cutoff = parse_utc_timestamp(
            as_of,
            label="cash preview cutoff",
        ).isoformat()
    except ValueError:
        return blocked_company_workbench_cash_generation_preview(
            extraction.ticker,
            fiscal_period=extraction.fiscal_period,
            as_of=str(as_of or ""),
            blockers=("cutoff_invalid",),
            accession=extraction.accession,
            source_url=extraction.source_url,
            accepted_at=extraction.accepted_at,
            capex_sign_evidence=extraction.capex_sign_evidence,
        )
    if pilot.status != "accepted_for_review":
        return blocked_company_workbench_cash_generation_preview(
            extraction.ticker,
            fiscal_period=extraction.fiscal_period,
            as_of=cutoff,
            blockers=(f"pilot_status:{pilot.status}", *pilot.blockers),
            accession=extraction.accession,
            source_url=extraction.source_url,
            accepted_at=extraction.accepted_at,
            capex_sign_evidence=extraction.capex_sign_evidence,
        )
    blockers: list[str] = []
    acceptance = pilot.acceptance
    selected_symbol = str(selected_ticker or "").strip().upper()
    if acceptance is None:
        blockers.append("adapter_acceptance_required")
    else:
        if acceptance.status != "accepted_for_review":
            blockers.append(f"adapter_status:{acceptance.status}")
        blockers.extend(f"adapter_blocker:{item}" for item in acceptance.blockers)
        if acceptance.source_id != "sec_companyfacts":
            blockers.append(f"adapter_source:{acceptance.source_id}")
        if acceptance.rights_status != "approved":
            blockers.append(f"source_rights:{acceptance.rights_status}")
        if not {
            "operating_income",
            "cash_from_operations",
            "capital_expenditures",
        }.issubset(acceptance.reviewed_metrics):
            blockers.append("adapter_reviewed_metrics_incomplete")
        if acceptance.derived_point_count < 3:
            blockers.append("adapter_derived_points_incomplete")
        if acceptance.ticker != extraction.ticker:
            blockers.append(f"adapter_ticker:{acceptance.ticker}")
        if acceptance.accepted_observation_count != len(extraction.observations):
            blockers.append("accepted_observation_count_mismatch")
        if acceptance.production_activation:
            blockers.append("production_activation_forbidden")
        if acceptance.readiness_promotions:
            blockers.append("readiness_promotions_forbidden")
    if pilot.production_activation:
        blockers.append("production_activation_forbidden")
    if pilot.readiness_promotions:
        blockers.append("readiness_promotions_forbidden")
    blockers.extend(f"pilot_blocker:{item}" for item in pilot.blockers)
    if selected_symbol != extraction.ticker:
        blockers.append(f"ticker_mismatch:{extraction.ticker}")
    blockers.extend(f"sec_extraction:{item}" for item in extraction.blockers)
    if not str(extraction.accession or "").strip():
        blockers.append("accession_required")
    if not str(extraction.source_url or "").strip():
        blockers.append("source_url_required")
    if extraction.capex_sign_evidence != "explicit_filed_table_outflow":
        blockers.append("capex_sign_evidence_required")
    try:
        accepted_at = parse_utc_timestamp(
            extraction.accepted_at,
            label="cash preview accepted_at",
        )
    except ValueError:
        blockers.append("accepted_at_invalid")
    else:
        if accepted_at > parse_utc_timestamp(cutoff):
            blockers.append("accepted_after_cutoff")
    if not extraction.observations:
        blockers.append("observations_required")
    if not extraction.revenue_actuals:
        blockers.append("revenue_actual_required")
    for row in extraction.observations:
        if row.ticker != extraction.ticker:
            blockers.append(f"observation_ticker:{row.ticker}")
        if row.source != "sec_companyfacts":
            blockers.append(f"observation_source:{row.source}")
        if parse_utc_timestamp(row.published_at) > parse_utc_timestamp(cutoff):
            blockers.append(f"observation_after_cutoff:{row.metric}")
        if row.metric == "capital_expenditures" and row.value >= 0:
            blockers.append("capital_expenditures_outflow_required")
    for row in extraction.revenue_actuals:
        if row.ticker != extraction.ticker:
            blockers.append(f"revenue_ticker:{row.ticker}")
        if row.source != "sec_companyfacts":
            blockers.append(f"revenue_source:{row.source}")
        if parse_utc_timestamp(row.reported_at) > parse_utc_timestamp(cutoff):
            blockers.append("revenue_after_cutoff")
    if (
        extraction.fiscal_period.endswith("-Q4")
        and (
            acceptance is None
            or extraction.fiscal_period not in acceptance.explicit_q4_periods
        )
    ):
        blockers.append("explicit_q4_evidence_required")
    if blockers:
        return blocked_company_workbench_cash_generation_preview(
            extraction.ticker,
            fiscal_period=extraction.fiscal_period,
            as_of=cutoff,
            blockers=tuple(blockers),
            accession=extraction.accession,
            source_url=extraction.source_url,
            accepted_at=extraction.accepted_at,
            capex_sign_evidence=extraction.capex_sign_evidence,
        )
    trend = build_quarterly_trend_packet(
        selected_ticker,
        extraction.revenue_actuals,
        as_of=cutoff,
        business_observations=extraction.observations,
    )
    metrics = (
        _metric("operating_margin", trend.operating_margin),
        _metric("free_cash_flow", trend.free_cash_flow),
        _metric("fcf_margin", trend.fcf_margin),
    )
    if any(
        metric.value is None or metric.fiscal_period != extraction.fiscal_period
        for metric in metrics
    ):
        return blocked_company_workbench_cash_generation_preview(
            extraction.ticker,
            fiscal_period=extraction.fiscal_period,
            as_of=cutoff,
            blockers=("complete_cash_generation_preview_required",),
            accession=extraction.accession,
            source_url=extraction.source_url,
            accepted_at=extraction.accepted_at,
            capex_sign_evidence=extraction.capex_sign_evidence,
        )
    revenue = extraction.revenue_actuals[0]
    components = (
        CashGenerationPreviewComponent(
            metric="revenue",
            value=float(revenue.revenue_actual),
            currency=revenue.revenue_currency,
            fiscal_period=revenue.fiscal_period,
            source_ref=revenue.source_ref,
            published_at=revenue.reported_at,
            retrieved_at=revenue.retrieved_at,
            accounting_basis=revenue.revenue_basis,
            duration_basis="three_months",
            q4_evidence_state=(
                "explicit_filed_quarter"
                if revenue.fiscal_period.endswith("-Q4")
                else "not_q4"
            ),
        ),
        *(
            CashGenerationPreviewComponent(
                metric=row.metric,
                value=row.value,
                currency=row.currency,
                fiscal_period=row.fiscal_period,
                source_ref=row.source_ref,
                published_at=row.published_at,
                retrieved_at=row.retrieved_at,
                accounting_basis=row.accounting_basis,
                duration_basis=row.duration_basis,
                q4_evidence_state=row.q4_evidence_state,
            )
            for row in extraction.observations
        ),
    )
    return CompanyWorkbenchCashGenerationPreview(
        ticker=extraction.ticker,
        fiscal_period=extraction.fiscal_period,
        status="accepted_for_review",
        message=(
            "Accepted SEC evidence supports a cash-generation review preview. "
            "Production evidence and readiness remain unchanged."
        ),
        operating_margin=metrics[0],
        free_cash_flow=metrics[1],
        fcf_margin=metrics[2],
        blockers=(),
        withheld_metrics=(),
        accession=extraction.accession,
        source_url=extraction.source_url,
        accepted_at=extraction.accepted_at,
        cutoff=cutoff,
        capex_sign_evidence=extraction.capex_sign_evidence,
        components=components,
    )
