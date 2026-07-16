"""Readiness-first, non-ranking comparison for selected research rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd


PROHIBITED_TERMS = (
    "buy",
    "sell",
    "hold",
    "order",
    "recommendation",
    "expected return",
)


@dataclass(frozen=True)
class ComparisonCompany:
    ticker: str
    asset_type: str
    research_state: str
    overall_readiness: str
    price_state: str
    fundamentals_state: str
    dcf_state: str
    trusted_peer_state: str
    supported_now: str
    blocked_or_missing: str
    next_proof_step: str
    proof_freshness: str
    catalysts: str
    risks: str


@dataclass(frozen=True)
class ResearchComparison:
    companies: tuple[ComparisonCompany, ...]
    status: str
    boundary: str


def _safe_text(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return fallback
    lowered = text.lower()
    if any(term in lowered for term in PROHIBITED_TERMS):
        return "Review the source evidence for this field."
    return text


def _boolean_state(value: object) -> str:
    if value is True or str(value).strip().lower() in {"true", "1", "yes"}:
        return "Ready"
    if value is False or str(value).strip().lower() in {"false", "0", "no"}:
        return "Blocked"
    return "Not available"


def _journal_summary(state: object, field: str, empty: str) -> str:
    if state is None:
        return empty
    entries = tuple(getattr(state, field, ()) or ())
    summaries = [_safe_text(getattr(entry, "summary", ""), "") for entry in entries]
    summaries = [summary for summary in summaries if summary]
    return " | ".join(summaries[:3]) if summaries else empty


def build_research_comparison(
    selected_rows: pd.DataFrame,
    *,
    journal_states: Mapping[str, object],
) -> ResearchComparison:
    """Build an evidence matrix in selection order without scoring companies."""

    if selected_rows is None or "Ticker" not in selected_rows.columns:
        raise ValueError("Research comparison requires two or three selected ticker rows.")
    tickers = [str(value or "").strip().upper() for value in selected_rows["Ticker"].tolist()]
    if len(tickers) not in {2, 3}:
        raise ValueError("Research comparison requires two or three selected ticker rows.")
    if any(not ticker for ticker in tickers) or len(set(tickers)) != len(tickers):
        raise ValueError("Research comparison requires unique non-empty tickers.")

    companies: list[ComparisonCompany] = []
    for (_, row), ticker in zip(selected_rows.iterrows(), tickers):
        journal_state = journal_states.get(ticker)
        companies.append(
            ComparisonCompany(
                ticker=ticker,
                asset_type=_safe_text(row.get("Asset Type"), "Not available"),
                research_state=_safe_text(row.get("Research State"), "Not available"),
                overall_readiness=_safe_text(row.get("Readiness"), "Not available"),
                price_state=_boolean_state(row.get("Price Ready")),
                fundamentals_state=_boolean_state(row.get("Fundamentals Ready")),
                dcf_state=_boolean_state(row.get("DCF Ready")),
                trusted_peer_state=_boolean_state(row.get("Trusted Peer Ready")),
                supported_now=_safe_text(row.get("Supported Now"), "No supported analysis listed."),
                blocked_or_missing=_safe_text(row.get("Blocked / Missing"), "No missing input listed."),
                next_proof_step=_safe_text(row.get("Next Proof Step"), "Review Data Health evidence."),
                proof_freshness=_safe_text(row.get("Proof Freshness"), "Not available"),
                catalysts=_journal_summary(journal_state, "catalysts", "No reviewed catalyst evidence."),
                risks=_journal_summary(journal_state, "risks", "No reviewed risk evidence."),
            )
        )
    return ResearchComparison(
        companies=tuple(companies),
        status="ready_for_evidence_review",
        boundary="Compare evidence availability and research context only; no score, winner, or action is produced.",
    )


def comparison_matrix_rows(comparison: ResearchComparison) -> list[dict[str, Any]]:
    """Return a row-oriented matrix with tickers as columns."""

    fields = (
        ("Asset type", "asset_type"),
        ("Research state", "research_state"),
        ("Overall readiness", "overall_readiness"),
        ("Price context", "price_state"),
        ("Fundamentals", "fundamentals_state"),
        ("DCF scenario", "dcf_state"),
        ("Trusted peers", "trusted_peer_state"),
        ("Supported now", "supported_now"),
        ("Blocked or missing", "blocked_or_missing"),
        ("Next proof step", "next_proof_step"),
        ("Proof freshness", "proof_freshness"),
        ("Reviewed catalysts", "catalysts"),
        ("Reviewed risks", "risks"),
    )
    rows: list[dict[str, Any]] = []
    for label, field in fields:
        row: dict[str, Any] = {"Research evidence": label}
        row.update({company.ticker: getattr(company, field) for company in comparison.companies})
        rows.append(row)
    return rows
