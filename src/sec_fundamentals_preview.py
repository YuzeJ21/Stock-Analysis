"""Official-SEC, no-write annual fundamentals comparison."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import pandas as pd

from src.commercial_source_rights import (
    DEFAULT_REGISTRY_PATH,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.providers.sec_companyfacts import (
    SEC_ANNUAL_FORMS,
    SEC_COMPANYFACTS_URL,
    extract_fundamentals_from_companyfacts,
    fetch_companyfacts,
    load_sec_ticker_map,
    resolve_ticker_to_cik,
)


MAX_PREVIEW_TICKERS = 5
PREVIEW_FIELDS = (
    "revenue",
    "revenue_growth",
    "eps",
    "free_cash_flow",
    "fcf_margin",
    "profit_margin",
    "operating_margin",
    "ebitda",
    "cash",
    "debt",
    "shares_outstanding",
)
DIRECT_RIGHTS_FIELDS = {
    "revenue": "revenue",
    "shares_outstanding": "shares_outstanding",
}
CANDIDATE_COMPONENT_FIELDS = (
    "net_income",
    "cash_from_operations",
    "capital_expenditures",
    "operating_income",
)
_TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]*$")


def parse_preview_tickers(value: str | Iterable[str]) -> list[str]:
    raw_values = value.split(",") if isinstance(value, str) else list(value)
    tickers: list[str] = []
    for raw in raw_values:
        ticker = str(raw or "").strip().upper()
        if not ticker:
            continue
        if not _TICKER_PATTERN.fullmatch(ticker):
            raise ValueError(f"invalid ticker: {ticker!r}")
        if ticker not in tickers:
            tickers.append(ticker)
    if not tickers:
        raise ValueError("explicit ticker input is required")
    if len(tickers) > MAX_PREVIEW_TICKERS:
        raise ValueError("SEC fundamentals preview accepts at most five unique tickers")
    return tickers


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _values_equal(left: Any, right: Any) -> bool:
    left = _json_value(left)
    right = _json_value(right)
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=0.0)
    return left == right


def _read_canonical(path: Path) -> tuple[pd.DataFrame, list[str]]:
    if not path.is_file():
        raise ValueError(f"canonical fundamentals file is unavailable: {path}")
    frame = pd.read_csv(path)
    if "ticker" not in frame.columns:
        raise ValueError("canonical fundamentals file requires a ticker column")
    frame = frame.copy()
    frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    return frame.set_index("ticker", drop=False), list(frame.columns)


def _read_header(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return list(pd.read_csv(path, nrows=0).columns)


def _valid_companyfacts_payload(payload: Any) -> bool:
    if not isinstance(payload, Mapping):
        return False
    facts = payload.get("facts")
    if not isinstance(facts, Mapping):
        return False
    for taxonomy in facts.values():
        if not isinstance(taxonomy, Mapping):
            return False
        for fact in taxonomy.values():
            if not isinstance(fact, Mapping):
                return False
            units = fact.get("units")
            if not isinstance(units, Mapping):
                return False
            for items in units.values():
                if not isinstance(items, list) or not all(
                    isinstance(item, Mapping) for item in items
                ):
                    return False
    return True


def _valid_annual_anchor(record: Mapping[str, Any]) -> bool:
    return bool(
        record.get("period_start")
        and record.get("period_end")
        and record.get("filed")
        and record.get("accession")
        and record.get("form") in SEC_ANNUAL_FORMS
        and _has_annual_duration(record)
    )


def _has_annual_duration(record: Mapping[str, Any]) -> bool:
    period_start = pd.to_datetime(record.get("period_start"), errors="coerce")
    period_end = pd.to_datetime(record.get("period_end"), errors="coerce")
    if pd.isna(period_start) or pd.isna(period_end) or period_start >= period_end:
        return False
    return 300 <= (period_end - period_start).days <= 430


def _field_context(
    field: str,
    provenance: Mapping[str, Any],
    *,
    anchor_period_start: str | None,
    anchor_period_end: str | None,
    anchor_accession: str | None,
) -> tuple[str | None, str | None]:
    records = provenance.get("records")
    if not isinstance(records, list) or not records:
        return None, None
    normalized = [record for record in records if isinstance(record, Mapping)]
    if not normalized:
        return None, "source context is unavailable"

    for record in normalized:
        if record.get("period_start") and record.get("form") not in SEC_ANNUAL_FORMS:
            return "period_conflict", (
                f"flow fact form {record.get('form') or 'unavailable'} is not an annual filing"
            )
        if record.get("period_start") and not _has_annual_duration(record):
            return "period_conflict", (
                "Flow fact does not have a valid annual duration and date order."
            )

    if field == "revenue_growth":
        if len(normalized) != 2:
            return "source_context_ambiguous", (
                "Revenue growth requires exactly two complete annual records."
            )
        if any(
            not record.get(key)
            for record in normalized
            for key in ("period_end", "filed", "accession", "fiscal_year")
        ):
            return "source_context_ambiguous", (
                "Revenue growth requires two complete annual filing contexts."
            )
        latest_start = normalized[0].get("period_start")
        latest_end = normalized[0].get("period_end")
        if (
            not anchor_period_start
            or not anchor_period_end
            or latest_start != anchor_period_start
            or latest_end != anchor_period_end
        ):
            return "period_conflict", (
                "latest revenue-growth component does not match annual anchor "
                f"{anchor_period_start or 'unavailable'} to {anchor_period_end or 'unavailable'}"
            )
        latest_period_end = pd.to_datetime(
            normalized[0]["period_end"], errors="coerce"
        )
        prior_period_end = pd.to_datetime(
            normalized[1]["period_end"], errors="coerce"
        )
        if pd.isna(latest_period_end) or pd.isna(prior_period_end):
            return "source_context_ambiguous", (
                "Revenue growth period-end context is unavailable."
            )
        period_gap_days = (latest_period_end - prior_period_end).days
        if not 300 <= period_gap_days <= 430:
            return "period_conflict", (
                "Revenue growth requires the immediately adjacent prior annual period."
            )
        return None, None

    for record in normalized:
        period_end = record.get("period_end")
        accession = record.get("accession")
        period_start = record.get("period_start")
        if period_start:
            if not anchor_period_start or period_start != anchor_period_start:
                return "period_conflict", (
                    f"field period start {period_start or 'unavailable'} does not match annual anchor "
                    f"{anchor_period_start or 'unavailable'}"
                )
            if not anchor_period_end or period_end != anchor_period_end:
                return "period_conflict", (
                    f"field period {period_end or 'unavailable'} does not match annual anchor {anchor_period_end or 'unavailable'}"
                )
        elif not (
            anchor_period_end
            and period_end == anchor_period_end
            or anchor_accession
            and accession == anchor_accession
        ):
            return "source_context_ambiguous", (
                "instant fact is not tied to the annual anchor by period end or accession"
            )
        if not record.get("filed") or not accession or not period_end:
            return "source_context_ambiguous", "filing context is incomplete"
    return None, None


def _source_refs(records: list[Mapping[str, Any]], source_url: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for record in records:
        refs.append(
            {
                "source_url": source_url,
                "taxonomy": record.get("taxonomy"),
                "concept": record.get("concept"),
                "unit": record.get("unit"),
                "period_start": record.get("period_start"),
                "period_end": record.get("period_end"),
                "filed": record.get("filed"),
                "form": record.get("form"),
                "accession": record.get("accession"),
                "fiscal_year": record.get("fiscal_year"),
                "fiscal_period": record.get("fiscal_period"),
            }
        )
    return refs


def _compare_field(
    field: str,
    *,
    canonical_value: Any,
    candidate_value: Any,
    provenance: Mapping[str, Any],
    anchor_period_start: str | None,
    anchor_period_end: str | None,
    anchor_accession: str | None,
    source_url: str,
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    canonical_value = _json_value(canonical_value)
    candidate_value = _json_value(candidate_value)
    value_kind = str(provenance.get("value_kind") or "direct")
    records = [
        record
        for record in provenance.get("records", [])
        if isinstance(record, Mapping)
    ]
    refs = _source_refs(records, source_url)

    if candidate_value is None:
        value_status = "missing"
        classification = "missing"
        blocker = "No supported SEC fact was selected; the value remains unavailable."
    else:
        value_status = "unchanged" if _values_equal(canonical_value, candidate_value) else "changed"
        context_classification, context_blocker = _field_context(
            field,
            provenance,
            anchor_period_start=anchor_period_start,
            anchor_period_end=anchor_period_end,
            anchor_accession=anchor_accession,
        )
        if context_classification:
            classification = context_classification
            blocker = context_blocker or "Filing context requires review."
        elif value_kind == "derived":
            classification = "derived_scope_review_required"
            blocker = "Calculated value is not an SEC-reported fact and its exact field scope is not approved."
        else:
            required_field = DIRECT_RIGHTS_FIELDS.get(field, field)
            review = review_commercial_field_scope(
                registry,
                "sec_companyfacts",
                [required_field],
            )
            if review.commercial_evidence_ready:
                classification = "approved_direct"
                blocker = "none"
            else:
                classification = "unsupported"
                blocker = f"Direct SEC field {required_field} is outside the registered commercial field scope."

    first_ref = refs[0] if refs else {}
    return {
        "field": field,
        "canonical_value": canonical_value,
        "candidate_value": candidate_value,
        "value_status": value_status,
        "value_kind": value_kind,
        "classification": classification,
        "publishability_blocker": blocker,
        "period_start": first_ref.get("period_start"),
        "period_end": first_ref.get("period_end"),
        "filing_date": first_ref.get("filed"),
        "accession": first_ref.get("accession"),
        "form": first_ref.get("form"),
        "source_refs": refs,
    }


def _compare_source_component(
    field: str,
    *,
    component: Mapping[str, Any],
    anchor_period_start: str | None,
    anchor_period_end: str | None,
    anchor_accession: str | None,
    source_url: str,
    registry: Mapping[str, Any],
    canonical_columns: set[str],
) -> dict[str, Any]:
    row = _compare_field(
        field,
        canonical_value=None,
        candidate_value=component.get("value"),
        provenance=component,
        anchor_period_start=anchor_period_start,
        anchor_period_end=anchor_period_end,
        anchor_accession=anchor_accession,
        source_url=source_url,
        registry=registry,
    )
    row["value_status"] = "not_canonical"
    row["schema_status"] = (
        "existing_canonical_not_produced"
        if field in canonical_columns
        else "candidate_component_not_canonical"
    )
    if row["classification"] == "approved_direct":
        row["publishability_blocker"] = (
            "Direct SEC field is approved, but adding a canonical column requires a separate schema decision."
        )
    return row


def _ticker_failure(ticker: str, status: str, blocker: str) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "status": status,
        "blocker": blocker,
        "canonical_period_end": None,
        "candidate_period_end": None,
        "canonical_period_status": "unavailable",
        "fields": [],
    }


def build_sec_fundamentals_preview(
    tickers: str | Iterable[str],
    *,
    canonical_path: str | Path = "data/fundamentals.csv",
    staged_path: str | Path = "data/imports/fundamentals.csv",
    rights_path: str | Path = DEFAULT_REGISTRY_PATH,
    user_agent: str | None = None,
    cache_dir: str | Path = "data/cache/sec",
    sleep_seconds: float = 0.2,
    ticker_map_fetcher: Callable[[str, str, float], Any] | None = None,
    companyfacts_fetcher: Callable[[str, str, float], Any] | None = None,
) -> dict[str, Any]:
    requested = parse_preview_tickers(tickers)
    canonical, canonical_columns = _read_canonical(Path(canonical_path))
    staged_columns = _read_header(Path(staged_path))
    registry = load_source_rights_registry(Path(rights_path))
    ticker_map = load_sec_ticker_map(
        cache_dir=cache_dir,
        user_agent=user_agent,
        sleep_seconds=sleep_seconds,
        fetcher=ticker_map_fetcher,
        cache=False,
    )

    results: list[dict[str, Any]] = []
    for ticker in requested:
        canonical_present = ticker in canonical.index
        cik = resolve_ticker_to_cik(ticker, ticker_map)
        if cik is None:
            results.append(
                _ticker_failure(
                    ticker,
                    "cik_unresolved",
                    "No official SEC ticker-to-CIK mapping was found.",
                )
            )
            continue
        source_url = SEC_COMPANYFACTS_URL.format(cik=cik)
        try:
            payload = fetch_companyfacts(
                cik,
                user_agent,
                cache=False,
                cache_dir=cache_dir,
                sleep_seconds=sleep_seconds,
                fetcher=companyfacts_fetcher,
            )
        except (RuntimeError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            results.append(_ticker_failure(ticker, "fetch_failed", str(exc)))
            continue
        if not _valid_companyfacts_payload(payload):
            results.append(
                _ticker_failure(
                    ticker,
                    "invalid_payload",
                    "SEC Companyfacts payload was malformed or missing its facts mapping.",
                )
            )
            continue
        payload_cik = str(payload.get("cik", "")).strip()
        normalized_payload_cik = (
            str(int(payload_cik)).zfill(10) if payload_cik.isdigit() else payload_cik
        )
        if normalized_payload_cik != str(cik).zfill(10):
            results.append(
                _ticker_failure(
                    ticker,
                    "source_context_ambiguous",
                    "SEC Companyfacts CIK does not match the official ticker-map CIK.",
                )
            )
            continue

        try:
            extracted = extract_fundamentals_from_companyfacts(dict(payload))
        except (AttributeError, KeyError, TypeError, ValueError):
            results.append(
                _ticker_failure(
                    ticker,
                    "invalid_payload",
                    "SEC Companyfacts payload could not be interpreted safely.",
                )
            )
            continue
        provenance = extracted.get("_field_provenance", {})
        source_components = extracted.get("_source_components", {})
        revenue_records = provenance.get("revenue", {}).get("records", [])
        anchor_record = revenue_records[0] if revenue_records else {}
        anchor_valid = bool(
            extracted.get("revenue") is not None
            and isinstance(anchor_record, Mapping)
            and _valid_annual_anchor(anchor_record)
        )
        anchor_period_end = (
            _json_value(anchor_record.get("period_end"))
            if anchor_valid
            else None
        )
        anchor_period_start = (
            _json_value(anchor_record.get("period_start"))
            if anchor_valid
            else None
        )
        anchor_filing_date = (
            _json_value(anchor_record.get("filed")) if anchor_period_end else None
        )
        anchor_accession = (
            _json_value(anchor_record.get("accession")) if anchor_period_end else None
        )
        canonical_row = canonical.loc[ticker] if canonical_present else None
        if isinstance(canonical_row, pd.DataFrame):
            results.append(
                _ticker_failure(
                    ticker,
                    "canonical_row_ambiguous",
                    "Canonical fundamentals contains duplicate ticker rows.",
                )
            )
            continue
        canonical_period_end = (
            _json_value(canonical_row.get("as_of_date"))
            if canonical_row is not None
            else None
        )
        field_rows = [
            _compare_field(
                field,
                canonical_value=(
                    canonical_row.get(field) if canonical_row is not None else None
                ),
                candidate_value=(
                    extracted.get(field)
                    if field in extracted
                    else source_components.get(field, {}).get("value")
                ),
                provenance=(
                    provenance.get(field, {})
                    if field in provenance
                    else source_components.get(field, {})
                ),
                anchor_period_start=anchor_period_start,
                anchor_period_end=anchor_period_end,
                anchor_accession=anchor_accession,
                source_url=source_url,
                registry=registry,
            )
            for field in PREVIEW_FIELDS
        ]
        source_component_rows = [
            _compare_source_component(
                field,
                component=source_components.get(field, {}),
                anchor_period_start=anchor_period_start,
                anchor_period_end=anchor_period_end,
                anchor_accession=anchor_accession,
                source_url=source_url,
                registry=registry,
                canonical_columns=set(canonical_columns),
            )
            for field in CANDIDATE_COMPONENT_FIELDS
        ]
        future_apply_candidate_fields = [
            row["field"]
            for row in field_rows
            if row["classification"] == "approved_direct"
            and row["value_status"] == "changed"
        ]
        future_apply_proposal_status = (
            "owner_review_required"
            if canonical_present and future_apply_candidate_fields
            else "blocked"
        )
        results.append(
            {
                "ticker": ticker,
                "status": (
                    "compared" if canonical_present else "compared_canonical_missing"
                ),
                "blocker": (
                    "Canonical apply and source-rights decisions remain separately gated."
                    if canonical_present
                    else "Canonical fundamentals row is unavailable; a row-level apply proposal is blocked."
                ),
                "canonical_period_end": canonical_period_end,
                "candidate_period_end": anchor_period_end,
                "candidate_filing_date": anchor_filing_date,
                "candidate_accession": anchor_accession,
                "candidate_source_url": source_url,
                "canonical_period_status": (
                    "aligned"
                    if canonical_period_end and canonical_period_end == anchor_period_end
                    else "period_mismatch"
                    if canonical_period_end
                    else "unavailable"
                ),
                "future_apply_candidate_fields": future_apply_candidate_fields,
                "future_apply_proposal_status": future_apply_proposal_status,
                "source_components": source_component_rows,
                "fields": field_rows,
            }
        )

    staged_extra = sorted(set(staged_columns) - set(canonical_columns))
    component_extra = sorted(
        set(CANDIDATE_COMPONENT_FIELDS) - set(canonical_columns)
    )
    canonical_not_produced = sorted(
        set(canonical_columns)
        - set(PREVIEW_FIELDS)
        - {
            "ticker",
            "source",
            "as_of_date",
            "sec_cik",
            "sec_form",
            "sec_filed_date",
            "sec_accession",
            "sec_fact_warnings",
            "sec_entity_name",
        }
    )
    return {
        "status": "inspection_only",
        "requested_tickers": requested,
        "source": "sec_companyfacts",
        "source_rights_mutated": False,
        "canonical_apply_authorized": False,
        "repository_writes": [],
        "schema_delta": {
            "staged_extra_columns": staged_extra,
            "candidate_component_extra_columns": component_extra,
            "canonical_columns_not_produced": canonical_not_produced,
            "full_row_rewrite_risk": bool(staged_extra or canonical_not_produced),
        },
        "tickers": results,
    }


def render_sec_fundamentals_preview(result: Mapping[str, Any]) -> str:
    return json.dumps(result, indent=2, sort_keys=True, allow_nan=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare official SEC annual fundamentals in memory without writes."
    )
    parser.add_argument("--tickers", required=True)
    parser.add_argument("--canonical-path", type=Path, default=Path("data/fundamentals.csv"))
    parser.add_argument(
        "--staged-path",
        type=Path,
        default=Path("data/imports/fundamentals.csv"),
    )
    parser.add_argument("--rights-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--sec-user-agent")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = build_sec_fundamentals_preview(
            args.tickers,
            canonical_path=args.canonical_path,
            staged_path=args.staged_path,
            rights_path=args.rights_path,
            user_agent=args.sec_user_agent,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(render_sec_fundamentals_preview(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
