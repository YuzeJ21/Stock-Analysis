"""Read-only saved-versus-proposed readiness impact preview."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

import pandas as pd

from src.commercial_source_rights import (
    SourceRights,
    commercial_eligibility,
    load_source_rights_registry,
)
from src.company_analysis_scope import company_dcf_exclusion_reasons
from src.dcf_price_lineage import DcfPriceLineageReview, review_dcf_price_lineage
from src.loader import normalize_columns
from src.paths import resolve_data_dir, resolve_project_root
from src.readiness_engine import build_ticker_readiness_report


STABLE_READINESS_FIELDS = (
    "overall_readiness_state",
    "price_ready",
    "momentum_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "earnings_ready",
    "analyst_estimates_ready",
    "ready_features",
    "partial_features",
    "blocked_features",
    "excluded_features",
)

BOOLEAN_READINESS_FIELDS = (
    "price_ready",
    "momentum_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "earnings_ready",
    "analyst_estimates_ready",
)

OVERALL_STATES = ("ready", "partial", "blocked", "excluded")
PROMOTION_FIELDS = ("fundamentals_ready", "dcf_ready")
REQUIRED_FUNDAMENTALS_FIELDS = (
    "revenue",
    "free_cash_flow",
    "fcf_margin",
    "shares_outstanding",
)


@dataclass(frozen=True)
class ReadinessTickerChange:
    ticker: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessPromotionEvidence:
    ticker: str
    promoted_fields: tuple[str, ...]
    source_id: str
    as_of_date: str
    source_reference: str
    rights_status: str
    missing_provenance_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessPromotionReview:
    status: str
    promotion_count: int
    fundamentals_promotion_count: int
    dcf_promotion_count: int
    rights_approved_count: int
    rights_review_required_count: int
    provenance_complete_count: int
    provenance_review_required_count: int
    field_scope_complete_count: int
    field_scope_review_required_count: int
    source_counts: tuple[tuple[str, int], ...]
    rights_status_counts: tuple[tuple[str, int], ...]
    evidence_rows: tuple[ReadinessPromotionEvidence, ...]
    top_n: int


@dataclass(frozen=True)
class ReadinessChangeReview:
    status: str
    added_ticker_count: int
    removed_ticker_count: int
    newly_ready_counts: tuple[tuple[str, int], ...]
    newly_partial_counts: tuple[tuple[str, int], ...]
    newly_excluded_counts: tuple[tuple[str, int], ...]
    dcf_exclusion_reason_counts: tuple[tuple[str, int], ...]
    unexplained_dcf_exclusion_count: int
    unexplained_dcf_exclusion_tickers: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessImpactPreview:
    status: str
    saved_ticker_count: int
    proposed_ticker_count: int
    saved_counts: tuple[tuple[str, int], ...]
    proposed_counts: tuple[tuple[str, int], ...]
    changed_ticker_count: int
    changed_tickers: tuple[ReadinessTickerChange, ...]
    top_n: int
    saved_path: str
    promotion_review: ReadinessPromotionReview | None = None
    change_review: ReadinessChangeReview | None = None
    dcf_price_lineage_review: DcfPriceLineageReview | None = None


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _stable_value(row: pd.Series, field: str) -> bool | str:
    if field in BOOLEAN_READINESS_FIELDS:
        return _truthy(row.get(field))
    return _text(row.get(field))


def _index_readiness(frame: pd.DataFrame) -> dict[str, pd.Series]:
    if frame.empty or "ticker" not in frame.columns:
        return {}
    rows: dict[str, pd.Series] = {}
    for _, row in frame.iterrows():
        ticker = _text(row.get("ticker")).upper()
        if ticker:
            rows[ticker] = row
    return rows


def _count_summary(frame: pd.DataFrame) -> tuple[tuple[str, int], ...]:
    indexed = _index_readiness(frame)
    rows = list(indexed.values())
    counts: list[tuple[str, int]] = []
    for state in OVERALL_STATES:
        counts.append(
            (
                f"overall_{state}",
                sum(_text(row.get("overall_readiness_state")).lower() == state for row in rows),
            )
        )
    for field in BOOLEAN_READINESS_FIELDS:
        counts.append((field, sum(_truthy(row.get(field)) for row in rows)))
    return tuple(counts)


def _promotion_map(saved: pd.DataFrame, proposed: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    saved_rows = _index_readiness(saved)
    proposed_rows = _index_readiness(proposed)
    promotions: dict[str, tuple[str, ...]] = {}
    for ticker in sorted(set(proposed_rows)):
        proposed_row = proposed_rows[ticker]
        saved_row = saved_rows.get(ticker, pd.Series(dtype=object))
        fields = tuple(
            field
            for field in PROMOTION_FIELDS
            if not _truthy(saved_row.get(field)) and _truthy(proposed_row.get(field))
        )
        if fields:
            promotions[ticker] = fields
    return promotions


def _fundamentals_rows_by_ticker(frame: pd.DataFrame) -> dict[str, list[pd.Series]]:
    if frame.empty or "ticker" not in frame.columns:
        return {}
    rows: dict[str, list[pd.Series]] = {}
    for _, row in frame.iterrows():
        ticker = _text(row.get("ticker")).upper()
        if ticker:
            rows.setdefault(ticker, []).append(row)
    return rows


def _count_values(values: list[str]) -> tuple[tuple[str, int], ...]:
    if not values:
        return ()
    counts = pd.Series(values, dtype="string").value_counts()
    ordered = sorted(
        ((str(name), int(value)) for name, value in counts.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return tuple(ordered)


def _feature_set(value: object) -> set[str]:
    text = _text(value)
    return {part.strip() for part in text.split(",") if part.strip()}


def review_readiness_changes(
    saved: pd.DataFrame,
    proposed: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> ReadinessChangeReview:
    """Summarize semantic feature transitions without changing readiness decisions."""

    saved_rows = _index_readiness(saved)
    proposed_rows = _index_readiness(proposed)
    fundamentals_rows = _fundamentals_rows_by_ticker(fundamentals)
    newly_ready: list[str] = []
    newly_partial: list[str] = []
    newly_excluded: list[str] = []
    dcf_reasons: list[str] = []
    unexplained_dcf: list[str] = []

    for ticker in sorted(set(saved_rows) & set(proposed_rows)):
        saved_row = saved_rows[ticker]
        proposed_row = proposed_rows[ticker]
        newly_ready.extend(_feature_set(proposed_row.get("ready_features")) - _feature_set(saved_row.get("ready_features")))
        newly_partial.extend(
            _feature_set(proposed_row.get("partial_features")) - _feature_set(saved_row.get("partial_features"))
        )
        ticker_newly_excluded = _feature_set(proposed_row.get("excluded_features")) - _feature_set(
            saved_row.get("excluded_features")
        )
        newly_excluded.extend(ticker_newly_excluded)
        if "dcf" not in ticker_newly_excluded:
            continue
        candidates = fundamentals_rows.get(ticker, [])
        fundamentals_row = candidates[0] if len(candidates) == 1 else pd.Series(dtype=object)
        reasons = company_dcf_exclusion_reasons(
            proposed_row.get("asset_type"),
            proposed_row,
            fundamentals_row,
        )
        if reasons:
            dcf_reasons.append(reasons[0])
        else:
            unexplained_dcf.append(ticker)

    has_changes = bool(
        set(saved_rows) ^ set(proposed_rows)
        or newly_ready
        or newly_partial
        or newly_excluded
    )
    status = "unexplained_changes" if unexplained_dcf else "changes_explained" if has_changes else "no_changes"
    return ReadinessChangeReview(
        status=status,
        added_ticker_count=len(set(proposed_rows) - set(saved_rows)),
        removed_ticker_count=len(set(saved_rows) - set(proposed_rows)),
        newly_ready_counts=_count_values(newly_ready),
        newly_partial_counts=_count_values(newly_partial),
        newly_excluded_counts=_count_values(newly_excluded),
        dcf_exclusion_reason_counts=_count_values(dcf_reasons),
        unexplained_dcf_exclusion_count=len(unexplained_dcf),
        unexplained_dcf_exclusion_tickers=tuple(unexplained_dcf),
    )


def review_readiness_promotions(
    saved: pd.DataFrame,
    proposed: pd.DataFrame,
    fundamentals: pd.DataFrame,
    *,
    rights_registry: Mapping[str, SourceRights],
    top_n: int = 20,
) -> ReadinessPromotionReview:
    """Review proposed technical promotions without changing either readiness frame."""

    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    promotions = _promotion_map(saved, proposed)
    if not promotions:
        return ReadinessPromotionReview(
            status="no_promotions",
            promotion_count=0,
            fundamentals_promotion_count=0,
            dcf_promotion_count=0,
            rights_approved_count=0,
            rights_review_required_count=0,
            provenance_complete_count=0,
            provenance_review_required_count=0,
            field_scope_complete_count=0,
            field_scope_review_required_count=0,
            source_counts=(),
            rights_status_counts=(),
            evidence_rows=(),
            top_n=top_n,
        )

    fundamentals_rows = _fundamentals_rows_by_ticker(fundamentals)
    evidence: list[ReadinessPromotionEvidence] = []
    for ticker, promoted_fields in promotions.items():
        candidates = fundamentals_rows.get(ticker, [])
        if len(candidates) != 1:
            blocker = "missing_fundamentals_row" if not candidates else "duplicate_fundamentals_rows"
            evidence.append(
                ReadinessPromotionEvidence(
                    ticker=ticker,
                    promoted_fields=promoted_fields,
                    source_id="<missing>" if not candidates else "<ambiguous>",
                    as_of_date="",
                    source_reference="",
                    rights_status="not_evaluated_missing_evidence" if not candidates else "not_evaluated_ambiguous_evidence",
                    missing_provenance_fields=("source", "as_of_date", "source_reference"),
                    missing_supported_fields=REQUIRED_FUNDAMENTALS_FIELDS,
                    blockers=(blocker,),
                )
            )
            continue

        row = candidates[0]
        source_id = _text(row.get("source"))
        as_of_date = _text(row.get("as_of_date"))
        source_reference = _text(row.get("source_ref")) or _text(row.get("sec_accession"))
        missing_provenance = tuple(
            field
            for field, value in (
                ("source", source_id),
                ("as_of_date", as_of_date),
                ("source_reference", source_reference),
            )
            if not value
        )
        rights = commercial_eligibility(rights_registry, source_id)
        rights_record = rights_registry.get(source_id)
        supported = set(rights_record.supported_fields) if rights_record is not None else set()
        missing_supported = tuple(field for field in REQUIRED_FUNDAMENTALS_FIELDS if field not in supported)
        blockers: list[str] = []
        blockers.extend(f"missing_provenance:{field}" for field in missing_provenance)
        if not rights.allowed:
            blockers.append(f"commercial_rights:{rights.status}")
        if missing_supported:
            blockers.append("registered_field_scope_incomplete")
        evidence.append(
            ReadinessPromotionEvidence(
                ticker=ticker,
                promoted_fields=promoted_fields,
                source_id=source_id or "<missing>",
                as_of_date=as_of_date,
                source_reference=source_reference,
                rights_status=rights.status,
                missing_provenance_fields=missing_provenance,
                missing_supported_fields=missing_supported,
                blockers=tuple(blockers),
            )
        )

    rights_approved = sum(item.rights_status == "approved" for item in evidence)
    provenance_complete = sum(not item.missing_provenance_fields for item in evidence)
    field_scope_complete = sum(not item.missing_supported_fields for item in evidence)
    review_complete = all(
        item.rights_status == "approved"
        and not item.missing_provenance_fields
        and not item.missing_supported_fields
        for item in evidence
    )
    return ReadinessPromotionReview(
        status="evidence_review_complete" if review_complete else "evidence_review_required",
        promotion_count=len(evidence),
        fundamentals_promotion_count=sum("fundamentals_ready" in fields for fields in promotions.values()),
        dcf_promotion_count=sum("dcf_ready" in fields for fields in promotions.values()),
        rights_approved_count=rights_approved,
        rights_review_required_count=len(evidence) - rights_approved,
        provenance_complete_count=provenance_complete,
        provenance_review_required_count=len(evidence) - provenance_complete,
        field_scope_complete_count=field_scope_complete,
        field_scope_review_required_count=len(evidence) - field_scope_complete,
        source_counts=_count_values([item.source_id for item in evidence]),
        rights_status_counts=_count_values([item.rights_status for item in evidence]),
        evidence_rows=tuple(evidence[:top_n]),
        top_n=top_n,
    )


def compare_readiness_frames(
    saved: pd.DataFrame,
    proposed: pd.DataFrame,
    *,
    top_n: int = 20,
    saved_path: str = "data/reports/ticker_readiness_report.csv",
) -> ReadinessImpactPreview:
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    saved_rows = _index_readiness(saved)
    proposed_rows = _index_readiness(proposed)
    changes: list[ReadinessTickerChange] = []
    for ticker in sorted(set(saved_rows) | set(proposed_rows)):
        if ticker not in saved_rows or ticker not in proposed_rows:
            fields = ("row_presence",)
        else:
            fields = tuple(
                field
                for field in STABLE_READINESS_FIELDS
                if _stable_value(saved_rows[ticker], field) != _stable_value(proposed_rows[ticker], field)
            )
        if fields:
            changes.append(ReadinessTickerChange(ticker=ticker, fields=fields))
    return ReadinessImpactPreview(
        status="changes_detected" if changes else "no_readiness_changes",
        saved_ticker_count=len(saved_rows),
        proposed_ticker_count=len(proposed_rows),
        saved_counts=_count_summary(saved),
        proposed_counts=_count_summary(proposed),
        changed_ticker_count=len(changes),
        changed_tickers=tuple(changes[:top_n]),
        top_n=top_n,
        saved_path=saved_path,
    )


def build_readiness_impact_preview(
    root: Path | str,
    *,
    data_dir: Path | str | None = None,
    top_n: int = 20,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> ReadinessImpactPreview:
    project_root = resolve_project_root(root)
    data_path = resolve_data_dir(data_dir, project_root)
    saved_path = data_path / "reports" / "ticker_readiness_report.csv"
    if not saved_path.exists():
        return ReadinessImpactPreview(
            status="missing_saved_snapshot",
            saved_ticker_count=0,
            proposed_ticker_count=0,
            saved_counts=(),
            proposed_counts=(),
            changed_ticker_count=0,
            changed_tickers=(),
            top_n=top_n,
            saved_path=str(saved_path),
        )
    saved = pd.read_csv(saved_path)
    reports = build_ticker_readiness_report(
        project_root,
        data_dir=data_path,
        write_outputs=False,
    )
    proposed = reports["ticker_readiness_report"]
    preview = compare_readiness_frames(
        saved,
        proposed,
        top_n=top_n,
        saved_path=str(saved_path),
    )
    fundamentals_path = data_path / "fundamentals.csv"
    fundamentals = pd.read_csv(fundamentals_path) if fundamentals_path.exists() else pd.DataFrame()
    if not fundamentals.empty:
        fundamentals.columns = normalize_columns(list(fundamentals.columns))
    registry = (
        rights_registry
        if rights_registry is not None
        else load_source_rights_registry(project_root / "config" / "source_rights.yml")
    )
    promotion_review = review_readiness_promotions(
        saved,
        proposed,
        fundamentals,
        rights_registry=registry,
        top_n=top_n,
    )
    change_review = review_readiness_changes(saved, proposed, fundamentals)
    prices_path = data_path / "prices.csv"
    prices = pd.read_csv(prices_path) if prices_path.exists() else pd.DataFrame()
    if not prices.empty:
        prices.columns = normalize_columns(list(prices.columns))
    dcf_price_lineage_review = review_dcf_price_lineage(
        saved,
        proposed,
        prices,
        rights_registry=registry,
        top_n=top_n,
    )
    return replace(
        preview,
        promotion_review=promotion_review,
        change_review=change_review,
        dcf_price_lineage_review=dcf_price_lineage_review,
    )


def _format_counts(counts: tuple[tuple[str, int], ...]) -> str:
    return ", ".join(f"{name}={value}" for name, value in counts) or "unavailable"


def render_readiness_impact_preview(preview: ReadinessImpactPreview) -> str:
    lines = ["Readiness Impact Preview", ""]
    if preview.status == "missing_saved_snapshot":
        lines.extend(
            [
                "Status: missing_saved_snapshot",
                f"Saved snapshot: {preview.saved_path}",
                "Comparison is unavailable because the saved readiness snapshot is missing.",
            ]
        )
    else:
        lines.extend(
            [
                f"Status: {preview.status}",
                f"Ticker rows: saved={preview.saved_ticker_count}, proposed={preview.proposed_ticker_count}",
                f"Saved counts: {_format_counts(preview.saved_counts)}",
                f"Proposed counts: {_format_counts(preview.proposed_counts)}",
                f"Changed tickers: {preview.changed_ticker_count}",
            ]
        )
        for change in preview.changed_tickers:
            lines.append(f"- {change.ticker}: {', '.join(change.fields)}")
        hidden = preview.changed_ticker_count - len(preview.changed_tickers)
        if hidden > 0:
            lines.append(f"- ... {hidden} additional changed ticker(s) hidden by TOP_N={preview.top_n}")
        change_review = preview.change_review
        if change_review is not None:
            lines.extend(
                [
                    "",
                    "Readiness Change Cause Review",
                    f"Status: {change_review.status}",
                    (
                        "Ticker rows: "
                        f"added={change_review.added_ticker_count}, removed={change_review.removed_ticker_count}"
                    ),
                    f"Newly ready features: {_format_counts(change_review.newly_ready_counts)}",
                    f"Newly partial features: {_format_counts(change_review.newly_partial_counts)}",
                    f"Newly excluded features: {_format_counts(change_review.newly_excluded_counts)}",
                    f"Primary DCF exclusion reasons: {_format_counts(change_review.dcf_exclusion_reason_counts)}",
                    (
                        "Unexplained new DCF exclusions: "
                        f"{change_review.unexplained_dcf_exclusion_count}"
                    ),
                    "Transition counts are independent and can overlap for one ticker; they are not current readiness totals.",
                    "A DCF exclusion is a method-fit state, not a negative company signal or investment conclusion.",
                ]
            )
            if change_review.unexplained_dcf_exclusion_tickers:
                lines.append(
                    "- Unexplained DCF exclusions: "
                    + ", ".join(change_review.unexplained_dcf_exclusion_tickers[: preview.top_n])
                )
        review = preview.promotion_review
        if review is not None:
            lines.extend(
                [
                    "",
                    "Promotion Evidence Review",
                    f"Status: {review.status}",
                    (
                        "Technical promotions: "
                        f"unique={review.promotion_count}, fundamentals={review.fundamentals_promotion_count}, "
                        f"DCF={review.dcf_promotion_count}"
                    ),
                    (
                        "Commercial rights: "
                        f"approved={review.rights_approved_count}, review_required={review.rights_review_required_count}"
                    ),
                    (
                        "Provenance: "
                        f"complete={review.provenance_complete_count}, "
                        f"review_required={review.provenance_review_required_count}"
                    ),
                    (
                        "Registered field scope: "
                        f"complete={review.field_scope_complete_count}, "
                        f"review_required={review.field_scope_review_required_count}"
                    ),
                    f"Exact source values: {_format_counts(review.source_counts)}",
                    f"Rights statuses: {_format_counts(review.rights_status_counts)}",
                ]
            )
            for item in review.evidence_rows:
                missing_provenance = ",".join(item.missing_provenance_fields) or "none"
                missing_scope = ",".join(item.missing_supported_fields) or "none"
                lines.append(
                    f"- {item.ticker}: promotes={','.join(item.promoted_fields)}; source={item.source_id!r}; "
                    f"rights={item.rights_status}; missing_provenance={missing_provenance}; "
                    f"missing_registered_fields={missing_scope}"
                )
            hidden_evidence = review.promotion_count - len(review.evidence_rows)
            if hidden_evidence > 0:
                lines.append(
                    f"- ... {hidden_evidence} additional promotion evidence row(s) hidden by TOP_N={review.top_n}"
                )
            lines.extend(
                [
                    "Technical readiness movement is not source-rights or provenance approval.",
                    "DCF price-source provenance is outside this fundamentals review; see the independent price-lineage review.",
                    "Even a complete promotion evidence review would not authorize the separate readiness rebuild.",
                ]
            )
        price_review = preview.dcf_price_lineage_review
        if price_review is not None:
            lines.extend(
                [
                    "",
                    "DCF Price Lineage Review",
                    f"Status: {price_review.status}",
                    f"Technical DCF promotions: {price_review.promotion_count}",
                    (
                        "Latest price rows: "
                        f"usable={price_review.usable_latest_row_count}, "
                        f"missing={price_review.missing_latest_row_count}, "
                        f"ambiguous={price_review.ambiguous_latest_row_count}"
                    ),
                    (
                        "Price lineage: "
                        f"complete={price_review.lineage_complete_count}, "
                        f"review_required={price_review.lineage_review_required_count}"
                    ),
                    (
                        "Commercial price rights: "
                        f"approved={price_review.rights_approved_count}, "
                        f"review_required={price_review.rights_review_required_count}"
                    ),
                    (
                        "Registered price scope: "
                        f"complete={price_review.field_scope_complete_count}, "
                        f"review_required={price_review.field_scope_review_required_count}"
                    ),
                    f"Exact price source values: {_format_counts(price_review.source_counts)}",
                    f"Price rights statuses: {_format_counts(price_review.rights_status_counts)}",
                ]
            )
            for item in price_review.evidence_rows:
                missing_provenance = ",".join(item.missing_provenance_fields) or "none"
                missing_scope = ",".join(item.missing_supported_fields) or "none"
                blockers = ",".join(item.blockers) or "none"
                lines.append(
                    f"- {item.ticker}: observation_date={item.observation_date or '<missing>'}; "
                    f"valid_rows={item.valid_row_count}; latest_rows={item.latest_row_count}; "
                    f"source={item.source_id!r}; rights={item.rights_status}; "
                    f"missing_provenance={missing_provenance}; "
                    f"missing_registered_fields={missing_scope}; blockers={blockers}"
                )
            hidden_price_evidence = price_review.promotion_count - len(price_review.evidence_rows)
            if hidden_price_evidence > 0:
                lines.append(
                    f"- ... {hidden_price_evidence} additional DCF price evidence row(s) hidden by "
                    f"TOP_N={price_review.top_n}"
                )
            lines.extend(
                [
                    "File origin, observation date, and adapter availability are not provider provenance.",
                    "Missing or composite source identifiers are not split, inferred, or granted borrowed rights.",
                    "This price review changes no readiness state and does not authorize the separate rebuild.",
                ]
            )
    lines.extend(
        [
            "",
            "Read-only: no files were created, modified, or deleted.",
            "This preview does not make saved readiness current.",
            "An intentional reviewed make readiness run remains the separate rebuild boundary.",
            "Research workflow evidence only; not investment advice or a recommendation.",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview stable readiness impact without writing files.")
    parser.add_argument("--project-root", default=".", help="Project root. Defaults to the current directory.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--top-n", type=int, default=20, help="Maximum changed ticker details to print.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.top_n < 1:
        print("Readiness preview failed: --top-n must be at least 1.")
        return 1
    try:
        preview = build_readiness_impact_preview(
            Path(args.project_root),
            data_dir=args.data_dir,
            top_n=args.top_n,
        )
    except (KeyError, OSError, ValueError) as exc:
        print(f"Readiness preview failed: {exc}")
        print("Read-only: no readiness output was written.")
        return 1
    print(render_readiness_impact_preview(preview))
    return 2 if preview.status == "missing_saved_snapshot" else 0


if __name__ == "__main__":
    raise SystemExit(main())
