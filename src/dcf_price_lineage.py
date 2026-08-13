"""Fail-closed, read-only price-lineage review for proposed DCF promotions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from src.commercial_source_rights import SourceRights, commercial_eligibility
from src.loader import normalize_columns
from src.price_lineage_temporal import review_daily_price_retrieval


REQUIRED_PRICE_PROVENANCE_FIELDS = ("source", "source_ref", "retrieved_at")
REQUIRED_PRICE_SCOPE_FIELDS = ("prices",)


@dataclass(frozen=True)
class DcfPriceLineageEvidence:
    ticker: str
    observation_date: str
    valid_row_count: int
    latest_row_count: int
    source_id: str
    source_reference: str
    retrieved_at: str
    availability_at: str
    review_cutoff: str
    temporal_status: str
    rights_status: str
    missing_provenance_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class DcfPriceLineageReview:
    status: str
    promotion_count: int
    usable_latest_row_count: int
    missing_latest_row_count: int
    ambiguous_latest_row_count: int
    lineage_complete_count: int
    lineage_review_required_count: int
    temporal_complete_count: int
    temporal_review_required_count: int
    rights_approved_count: int
    rights_review_required_count: int
    field_scope_complete_count: int
    field_scope_review_required_count: int
    source_counts: tuple[tuple[str, int], ...]
    rights_status_counts: tuple[tuple[str, int], ...]
    evidence_rows: tuple[DcfPriceLineageEvidence, ...]
    top_n: int


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _text(value: object) -> str:
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    return str(value).strip()


def _readiness_index(frame: pd.DataFrame) -> dict[str, pd.Series]:
    if frame.empty or "ticker" not in frame.columns:
        return {}
    rows: dict[str, pd.Series] = {}
    for _, row in frame.iterrows():
        ticker = _text(row.get("ticker")).upper()
        if ticker:
            rows[ticker] = row
    return rows


def _dcf_promotions(saved: pd.DataFrame, proposed: pd.DataFrame) -> tuple[str, ...]:
    saved_rows = _readiness_index(saved)
    proposed_rows = _readiness_index(proposed)
    return tuple(
        ticker
        for ticker in sorted(proposed_rows)
        if not _truthy(saved_rows.get(ticker, pd.Series(dtype=object)).get("dcf_ready"))
        and _truthy(proposed_rows[ticker].get("dcf_ready"))
    )


def _normalized_price_rows(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame()
    frame = prices.copy()
    frame.columns = normalize_columns(list(frame.columns))
    if not {"ticker", "date", "close"}.issubset(frame.columns):
        return pd.DataFrame()
    frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    frame["_lineage_date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed")
    frame["_lineage_close"] = pd.to_numeric(frame["close"], errors="coerce")
    return frame.loc[
        frame["ticker"].notna()
        & frame["ticker"].ne("")
        & frame["_lineage_date"].notna()
        & frame["_lineage_close"].notna()
        & frame["_lineage_close"].gt(0)
    ].copy()


def _count_values(values: list[str]) -> tuple[tuple[str, int], ...]:
    if not values:
        return ()
    counts = pd.Series(values, dtype="string").value_counts()
    return tuple(
        sorted(
            ((str(name), int(value)) for name, value in counts.items()),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _selection_failure(
    ticker: str,
    *,
    valid_row_count: int,
    latest_row_count: int,
    observation_date: str,
) -> DcfPriceLineageEvidence:
    ambiguous = latest_row_count > 1
    return DcfPriceLineageEvidence(
        ticker=ticker,
        observation_date=observation_date,
        valid_row_count=valid_row_count,
        latest_row_count=latest_row_count,
        source_id="<ambiguous>" if ambiguous else "<missing>",
        source_reference="",
        retrieved_at="",
        availability_at="",
        review_cutoff="",
        temporal_status="not_evaluated_missing_or_ambiguous_evidence",
        rights_status=(
            "not_evaluated_ambiguous_evidence" if ambiguous else "not_evaluated_missing_evidence"
        ),
        missing_provenance_fields=REQUIRED_PRICE_PROVENANCE_FIELDS,
        missing_supported_fields=REQUIRED_PRICE_SCOPE_FIELDS,
        blockers=("ambiguous_latest_price_row" if ambiguous else "missing_latest_price_row",),
    )


def review_dcf_price_lineage(
    saved: pd.DataFrame,
    proposed: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    rights_registry: Mapping[str, SourceRights],
    review_cutoff: str | None = None,
    top_n: int = 20,
) -> DcfPriceLineageReview:
    """Review the selected latest price row without changing technical readiness."""

    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    promotions = _dcf_promotions(saved, proposed)
    if not promotions:
        return DcfPriceLineageReview(
            status="no_dcf_promotions",
            promotion_count=0,
            usable_latest_row_count=0,
            missing_latest_row_count=0,
            ambiguous_latest_row_count=0,
            lineage_complete_count=0,
            lineage_review_required_count=0,
            temporal_complete_count=0,
            temporal_review_required_count=0,
            rights_approved_count=0,
            rights_review_required_count=0,
            field_scope_complete_count=0,
            field_scope_review_required_count=0,
            source_counts=(),
            rights_status_counts=(),
            evidence_rows=(),
            top_n=top_n,
        )

    normalized_prices = _normalized_price_rows(prices)
    evidence: list[DcfPriceLineageEvidence] = []
    for ticker in promotions:
        ticker_rows = (
            normalized_prices.loc[normalized_prices["ticker"] == ticker].copy()
            if not normalized_prices.empty
            else pd.DataFrame()
        )
        if ticker_rows.empty:
            evidence.append(
                _selection_failure(
                    ticker,
                    valid_row_count=0,
                    latest_row_count=0,
                    observation_date="",
                )
            )
            continue

        latest_date = ticker_rows["_lineage_date"].max()
        latest_rows = ticker_rows.loc[ticker_rows["_lineage_date"] == latest_date]
        observation_date = latest_date.date().isoformat()
        if len(latest_rows) != 1:
            evidence.append(
                _selection_failure(
                    ticker,
                    valid_row_count=len(ticker_rows),
                    latest_row_count=len(latest_rows),
                    observation_date=observation_date,
                )
            )
            continue

        row = latest_rows.iloc[0]
        source_id = _text(row.get("source"))
        source_reference = _text(row.get("source_ref"))
        temporal = review_daily_price_retrieval(
            observation_date,
            row.get("retrieved_at"),
            review_cutoff=review_cutoff,
        )
        retrieved_at = temporal.retrieved_at
        missing_provenance = tuple(
            field
            for field, value in (
                ("source", source_id),
                ("source_ref", source_reference),
                ("retrieved_at", retrieved_at),
            )
            if not value
        )
        rights = commercial_eligibility(rights_registry, source_id)
        rights_record = rights_registry.get(source_id)
        supported_fields = set(rights_record.supported_fields) if rights_record is not None else set()
        missing_supported = tuple(
            field for field in REQUIRED_PRICE_SCOPE_FIELDS if field not in supported_fields
        )
        blockers: list[str] = []
        blockers.extend(f"missing_provenance:{field}" for field in missing_provenance)
        blockers.extend(temporal.blockers)
        if not rights.allowed:
            blockers.append(f"commercial_rights:{rights.status}")
        if missing_supported:
            blockers.append("registered_price_scope_incomplete")
        evidence.append(
            DcfPriceLineageEvidence(
                ticker=ticker,
                observation_date=observation_date,
                valid_row_count=len(ticker_rows),
                latest_row_count=1,
                source_id=source_id or "<missing>",
                source_reference=source_reference,
                retrieved_at=retrieved_at,
                availability_at=temporal.availability_at,
                review_cutoff=temporal.review_cutoff,
                temporal_status=temporal.status,
                rights_status=rights.status,
                missing_provenance_fields=missing_provenance,
                missing_supported_fields=missing_supported,
                blockers=tuple(blockers),
            )
        )

    usable_latest = sum(item.latest_row_count == 1 for item in evidence)
    missing_latest = sum(item.latest_row_count == 0 for item in evidence)
    ambiguous_latest = sum(item.latest_row_count > 1 for item in evidence)
    lineage_complete = sum(not item.missing_provenance_fields for item in evidence)
    temporal_complete = sum(item.temporal_status == "temporal_complete" for item in evidence)
    rights_approved = sum(item.rights_status == "approved" for item in evidence)
    field_scope_complete = sum(not item.missing_supported_fields for item in evidence)
    complete = all(not item.blockers for item in evidence)
    return DcfPriceLineageReview(
        status="price_lineage_review_complete" if complete else "price_lineage_review_required",
        promotion_count=len(evidence),
        usable_latest_row_count=usable_latest,
        missing_latest_row_count=missing_latest,
        ambiguous_latest_row_count=ambiguous_latest,
        lineage_complete_count=lineage_complete,
        lineage_review_required_count=len(evidence) - lineage_complete,
        temporal_complete_count=temporal_complete,
        temporal_review_required_count=len(evidence) - temporal_complete,
        rights_approved_count=rights_approved,
        rights_review_required_count=len(evidence) - rights_approved,
        field_scope_complete_count=field_scope_complete,
        field_scope_review_required_count=len(evidence) - field_scope_complete,
        source_counts=_count_values([item.source_id for item in evidence]),
        rights_status_counts=_count_values([item.rights_status for item in evidence]),
        evidence_rows=tuple(evidence[:top_n]),
        top_n=top_n,
    )
