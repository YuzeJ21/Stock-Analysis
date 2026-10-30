"""Read-only view model for an explicitly requested SEC annual-facts preview."""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date, datetime, timedelta
from html import escape
from typing import Any, Callable, Mapping, MutableMapping


SESSION_KEY = "company_sec_annual_preview_v1"
ALLOWED_DIRECT_FIELDS = frozenset({
    "revenue", "shares_outstanding", "filing_dates",
    "operating_income", "cash_from_operations", "capital_expenditures",
})
ANNUAL_FORMS = frozenset({"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"})
EXPECTED_UNITS = {
    "revenue": "USD", "shares_outstanding": "shares", "filing_dates": "date",
    "operating_income": "USD", "cash_from_operations": "USD",
    "capital_expenditures": "USD",
}
REVENUE_CONCEPTS = frozenset({
    ("us-gaap", "Revenues"),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
    ("us-gaap", "SalesRevenueNet"),
    ("us-gaap", "SalesRevenueGoodsNet"),
})
OPERATING_COMPONENT_CONCEPTS = {
    "operating_income": frozenset({("us-gaap", "OperatingIncomeLoss")}),
    "cash_from_operations": frozenset({
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
    }),
    "capital_expenditures": frozenset({
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
        ("us-gaap", "PaymentsToAcquireProductiveAssets"),
    }),
}
SCHEMA_REVIEW_BLOCKER = (
    "Direct SEC field is approved, but adding a canonical column "
    "requires a separate schema decision."
)


def _unavailable(ticker: str, reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "ticker": ticker,
        "reason": reason,
        "approved_direct_fields": [],
        "withheld_fields": [],
        "safe_to_apply": False,
    }


def _iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0) else None


def _finite_direct_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and abs(value) <= 1e20
    except OverflowError:
        return False


def _source_reference(
    field: Mapping[str, Any], *, field_name: str, source_url: str,
    retrieval_timestamp: str, anchor_start: str | None, anchor_end: str,
    anchor_filed: str, anchor_accession: str, anchor_form: str | None,
    anchor_concept: tuple[str, str] | None,
) -> tuple[str | None, Mapping[str, Any] | None]:
    refs = field.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1 or not isinstance(refs[0], Mapping):
        return "source_reference_missing", None
    ref = refs[0]
    taxonomy, concept = ref.get("taxonomy"), ref.get("concept")
    if not isinstance(taxonomy, str) or not taxonomy or not isinstance(concept, str) or not concept:
        return "source_reference_missing", None
    if ref.get("form") not in ANNUAL_FORMS:
        return "nonannual_source", None
    if ref.get("unit") != EXPECTED_UNITS.get(field_name):
        return "field_unit_mismatch", None
    if (
        ref.get("period_end") != anchor_end
        or field.get("period_end") != ref.get("period_end")
    ):
        return "field_period_mismatch", None
    if field_name == "revenue" or field_name in OPERATING_COMPONENT_CONCEPTS:
        start = ref.get("period_start")
        start_date = _iso_date(start)
        end_date = _iso_date(anchor_end)
        if (
            start_date is None or end_date is None
            or not 300 <= (end_date - start_date).days <= 430
            or field.get("period_start") != start
            or (anchor_start is not None and start != anchor_start)
        ):
            return "field_period_mismatch", None
    concept_key = (taxonomy, concept)
    if (
        field_name == "revenue" and concept_key not in REVENUE_CONCEPTS
        or field_name == "shares_outstanding"
        and concept_key != ("dei", "EntityCommonStockSharesOutstanding")
        or field_name == "filing_dates"
        and (anchor_concept is None or concept_key != anchor_concept)
        or field_name in OPERATING_COMPONENT_CONCEPTS
        and concept_key not in OPERATING_COMPONENT_CONCEPTS[field_name]
    ):
        return "field_concept_mismatch", None
    if field_name == "filing_dates" and (
        ref.get("underlying_fact_unit") != "USD"
        or anchor_start is None
        or ref.get("period_start") != anchor_start
        or field.get("period_start") != anchor_start
    ):
        return "field_period_mismatch", None
    if (
        ref.get("source_url") != source_url
        or ref.get("retrieval_timestamp") != retrieval_timestamp
        or ref.get("filed") != anchor_filed
        or ref.get("accession") != anchor_accession
        or (anchor_form is not None and ref.get("form") != anchor_form)
        or field.get("form") != ref.get("form")
    ):
        return "field_source_mismatch", None
    return None, ref


def present_company_sec_annual_preview(ticker: str, preview: Mapping[str, Any]) -> dict[str, Any]:
    normalized = str(ticker or "").strip().upper()
    if not isinstance(preview, Mapping):
        return _unavailable(normalized, "invalid_preview")
    if (
        preview.get("status") != "inspection_only"
        or preview.get("canonical_apply_authorized") is not False
        or preview.get("source_rights_mutated") is not False
        or preview.get("repository_writes") != []
    ):
        return _unavailable(normalized, "preview_not_read_only")
    rows = preview.get("tickers")
    if (
        preview.get("source") != "sec_companyfacts"
        or preview.get("requested_tickers") != [normalized]
        or not isinstance(rows, list)
        or len(rows) != 1
        or not isinstance(rows[0], Mapping)
    ):
        return _unavailable(normalized, "invalid_preview")
    row = rows[0]
    fields = row.get("fields")
    if (
        row.get("status") not in {"compared", "compared_canonical_missing", "online_only"}
        or not isinstance(fields, list)
        or len(fields) > 32
        or any(not isinstance(field, Mapping) for field in fields)
    ):
        return _unavailable(normalized, "invalid_preview")
    if row.get("ticker") != normalized:
        return _unavailable(normalized, "source_identity_mismatch")
    cik = str(row.get("sec_cik") or "")
    expected_source_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    if not re.fullmatch(r"\d{10}", cik) or row.get("candidate_source_url") != expected_source_url:
        return _unavailable(normalized, "source_identity_mismatch")
    period_end = _iso_date(row.get("candidate_period_end"))
    filing_date = _iso_date(row.get("candidate_filing_date"))
    retrieved_at = _utc_timestamp(preview.get("retrieval_timestamp"))
    accession = row.get("candidate_accession")
    if (
        period_end is None
        or filing_date is None
        or retrieved_at is None
        or filing_date < period_end
        or retrieved_at.date() < filing_date
        or not isinstance(accession, str)
        or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession)
    ):
        return _unavailable(normalized, "invalid_annual_source_anchor")
    components = row.get("source_components", [])
    if (
        not isinstance(components, list) or len(fields) + len(components) > 32
        or any(not isinstance(component, Mapping) for component in components)
    ):
        return _unavailable(normalized, "invalid_preview")
    source_rows = [(field, False) for field in fields] + [
        (component, True) for component in components
    ]
    revenue_rows = [field for field in fields if field.get("field") == "revenue"]
    anchor_start: str | None = None
    anchor_form: str | None = None
    anchor_concept: tuple[str, str] | None = None
    revenue = revenue_rows[0] if len(revenue_rows) == 1 else {}
    revenue_anchor_ready = bool(
        revenue.get("classification") == "approved_direct"
        and revenue.get("value_kind") == "direct"
        and _finite_direct_number(revenue.get("candidate_value"))
        and revenue.get("sec_cik") == cik
        and revenue.get("accession") == accession
        and revenue.get("period_end") == row["candidate_period_end"]
        and revenue.get("filing_date") == row["candidate_filing_date"]
        and revenue.get("source_url") == expected_source_url
        and revenue.get("retrieval_timestamp") == preview["retrieval_timestamp"]
        and revenue.get("form") in ANNUAL_FORMS
        and revenue.get("unit") == "USD"
        and revenue.get("field_scope_status") == "approved"
        and revenue.get("source_rights_status") == "approved"
        and revenue.get("commercial_rights_approved") is True
        and revenue.get("publishability_blocker") == "none"
    )
    if revenue_anchor_ready:
        anchor_reason, anchor_ref = _source_reference(
            revenue, field_name="revenue", source_url=expected_source_url,
            retrieval_timestamp=str(preview["retrieval_timestamp"]),
            anchor_start=None, anchor_end=str(row["candidate_period_end"]),
            anchor_filed=str(row["candidate_filing_date"]),
            anchor_accession=accession, anchor_form=None, anchor_concept=None,
        )
        if anchor_reason is None and anchor_ref is not None:
            anchor_start = str(anchor_ref["period_start"])
            anchor_form = str(anchor_ref["form"])
            anchor_concept = (str(anchor_ref["taxonomy"]), str(anchor_ref["concept"]))

    approved: list[dict[str, Any]] = []
    withheld: list[dict[str, str]] = []
    approved_forms: set[str] = set()
    for field, is_component in source_rows:
        field_name = str(field.get("field") or "unknown")
        schema_hold = bool(
            is_component
            and field.get("schema_status") == "candidate_component_not_canonical"
            and field.get("publishability_blocker") == SCHEMA_REVIEW_BLOCKER
        )
        unit_ok = field.get("unit") == EXPECTED_UNITS.get(field_name)
        value = field.get("candidate_value")
        value_ok = (
            _iso_date(value) == filing_date
            if field_name == "filing_dates"
            else _finite_direct_number(value)
        )
        same_source = (
            field.get("sec_cik") == cik
            and field.get("accession") == row.get("candidate_accession")
            and field.get("period_end") == row.get("candidate_period_end")
            and field.get("filing_date") == row.get("candidate_filing_date")
            and field.get("source_url") == expected_source_url
            and field.get("retrieval_timestamp") == preview["retrieval_timestamp"]
        )
        reference_reason: str | None = None
        source_ref: Mapping[str, Any] | None = None
        if field_name in ALLOWED_DIRECT_FIELDS:
            reference_reason, source_ref = _source_reference(
                field, field_name=field_name, source_url=expected_source_url,
                retrieval_timestamp=str(preview["retrieval_timestamp"]),
                anchor_start=anchor_start, anchor_end=str(row["candidate_period_end"]),
                anchor_filed=str(row["candidate_filing_date"]),
                anchor_accession=accession, anchor_form=anchor_form,
                anchor_concept=anchor_concept,
            )
        reason = (
            str(field["classification"])
            if field.get("classification") in {"raw_source_value_invalid", "raw_source_conflict"}
            else "derived_field_scope_unreviewed"
            if field.get("classification") == "derived_scope_review_required"
            or field_name in ALLOWED_DIRECT_FIELDS and field.get("value_kind") != "direct"
            else "unsupported_online_field"
            if field_name not in ALLOWED_DIRECT_FIELDS
            or is_component and field_name not in OPERATING_COMPONENT_CONCEPTS
            or not is_component and field_name in OPERATING_COMPONENT_CONCEPTS and anchor_start is not None
            else "nonannual_source"
            if field.get("classification") == "approved_direct" and field.get("form") not in ANNUAL_FORMS
            else "field_source_mismatch"
            if field.get("classification") == "approved_direct" and not same_source
            else "field_unit_mismatch"
            if field.get("classification") == "approved_direct" and not unit_ok
            else "invalid_direct_value"
            if field.get("classification") == "approved_direct" and not value_ok
            else "annual_anchor_reference_missing"
            if field_name in OPERATING_COMPONENT_CONCEPTS and anchor_start is None
            else reference_reason
            if field.get("classification") == "approved_direct" and reference_reason
            else "source_evidence_unreviewed"
            if field.get("classification") != "approved_direct"
            or field.get("field_scope_status") != "approved"
            or field.get("source_rights_status") != "approved"
            or field.get("commercial_rights_approved") is not True
            or not (
                schema_hold if is_component else field.get("publishability_blocker") == "none"
            )
            else None
        )
        if reason is None and source_ref is not None:
            approved_forms.add(str(field.get("form")))
            approved.append(
                {
                    "field": field_name,
                    "value": field.get("candidate_value"),
                    "unit": field.get("unit"),
                    "taxonomy": source_ref["taxonomy"],
                    "concept": source_ref["concept"],
                    "period_start": source_ref.get("period_start"),
                    "period_end": field.get("period_end"),
                    "source_ref": expected_source_url,
                    "accession": accession,
                    "rights_status": "approved_field_scope_raw_redistribution_held",
                    "observed_at_utc": preview["retrieval_timestamp"],
                    "canonical_schema_status": (
                        "unchanged"
                        if not is_component and field.get("schema_status") == "existing_canonical"
                        else "review_required"
                    ),
                }
            )
        else:
            withheld.append({"field": field_name, "reason": reason or "source_evidence_unreviewed"})
    field_counts = Counter(
        str(field.get("field") or "unknown") for field, _is_component in source_rows
    )
    duplicate_direct = {
        name for name, count in field_counts.items() if name in ALLOWED_DIRECT_FIELDS and count > 1
    }
    if duplicate_direct:
        approved = [row for row in approved if row["field"] not in duplicate_direct]
        withheld = [row for row in withheld if row["field"] not in duplicate_direct]
        withheld.extend(
            {"field": name, "reason": "duplicate_direct_field"}
            for name in sorted(duplicate_direct)
        )
    return {
        "status": "inspection_only",
        "ticker": normalized,
        "source_url": expected_source_url,
        "sec_cik": cik,
        "retrieved_at_utc": preview.get("retrieval_timestamp"),
        "filing_date": row.get("candidate_filing_date"),
        "period_end": row.get("candidate_period_end"),
        "accession": row.get("candidate_accession"),
        "annual_form": next(iter(approved_forms)) if len(approved_forms) == 1 else None,
        "approved_direct_fields": approved,
        "withheld_fields": withheld,
        "safe_to_apply": False,
    }


def get_company_sec_annual_preview(
    ticker: str,
    session_state: MutableMapping[str, Any],
    *,
    refresh_requested: bool,
    user_agent: str | None,
    preview_builder: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized = str(ticker or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}", normalized):
        return _unavailable(normalized[:24], "invalid_ticker")
    cached = session_state.get(SESSION_KEY)
    if not refresh_requested:
        if isinstance(cached, Mapping) and cached.get("ticker") == normalized:
            cached_view = cached.get("view")
            if (
                isinstance(cached_view, Mapping)
                and cached_view.get("ticker") == normalized
                and cached_view.get("safe_to_apply") is False
                and cached_view.get("status") in {
                    "inspection_only", "unavailable", "configuration_required"
                }
            ):
                return dict(cached_view)
        return {"status": "not_requested", "ticker": normalized, "safe_to_apply": False}
    if not isinstance(user_agent, str) or not user_agent.strip():
        view = {
            "status": "configuration_required",
            "ticker": normalized,
            "reason": "sec_user_agent_required",
            "approved_direct_fields": [],
            "withheld_fields": [],
            "safe_to_apply": False,
        }
        session_state[SESSION_KEY] = {"ticker": normalized, "view": view}
        return view
    try:
        if preview_builder is None:
            from src.sec_annual_history import fetch_sec_online_research_view

            view = fetch_sec_online_research_view(normalized, user_agent=user_agent)
        else:
            preview = preview_builder(normalized, user_agent=user_agent)
            view = present_company_sec_annual_preview(normalized, preview)
    except (RuntimeError, ValueError, TypeError, OSError, TimeoutError):
        view = _unavailable(normalized, "sec_fetch_unavailable")
        session_state[SESSION_KEY] = {"ticker": normalized, "view": view}
        return view
    session_state[SESSION_KEY] = {"ticker": normalized, "view": view}
    return view


def company_sec_annual_preview_html(view: Mapping[str, Any]) -> str:
    """Render only bounded, escaped inspection copy for a Workbench disclosure."""
    status = view.get("status") if isinstance(view, Mapping) else None
    ticker = escape(str(view.get("ticker") or "")[:24]) if isinstance(view, Mapping) else ""
    boundary = (
        '<p class="sec-annual-boundary">No live prices or analyst estimates. '
        "Saved readiness is unchanged. Research evidence only.</p>"
    )
    if status == "not_requested":
        body = "<p>Check SEC annual facts to request filing evidence for this company.</p>"
    elif status == "configuration_required":
        body = "<p>SEC identifying User-Agent is required before an online check.</p>"
    elif status == "unavailable" and view.get("reason") == "sec_identity_mismatch":
        body = "<p>SEC ticker identity did not match the selected online candidate. Annual facts are withheld.</p>"
    elif status == "unavailable" and view.get("reason") == "invalid_annual_source_anchor":
        body = "<p>SEC annual facts are unavailable: a compatible annual revenue anchor was not established under the current reporting definitions. Review the source filing; this is a field-coverage gap.</p>"
    elif status != "inspection_only":
        body = "<p>SEC annual facts are unavailable. No field was promoted.</p>"
    else:
        source_url = str(view.get("source_url") or "")
        cik = str(view.get("sec_cik") or "")
        expected = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        source_link = (
            f'<a href="{escape(source_url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            "SEC Companyfacts source</a>"
            if re.fullmatch(r"\d{10}", cik) and source_url == expected
            else "Source link unavailable"
        )
        details = (
            '<div class="sec-annual-source-meta">'
            f"<span>Retrieved {escape(str(view.get('retrieved_at_utc') or 'unknown')[:40])}</span>"
            f"<span>form {escape(str(view.get('annual_form') or 'unverified')[:12])}</span>"
            f"<span>filed {escape(str(view.get('filing_date') or 'unknown')[:20])}</span>"
            f"<span>period ended {escape(str(view.get('period_end') or 'unknown')[:20])}</span>"
            f"{source_link}</div>"
            '<p class="sec-annual-identity">'
            f"Candidate SEC CIK {escape(cik)}; accession "
            f"{escape(str(view.get('accession') or 'unavailable')[:24])}. "
            "Ticker association still requires separate identity review.</p>"
        )
        field_rows: list[str] = []
        approved_input = view.get("approved_direct_fields")
        if not isinstance(approved_input, (list, tuple)):
            approved_input = []
        for row in approved_input[:32]:
            if not isinstance(row, Mapping):
                continue
            value = row.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                display_value = "Unavailable"
            elif isinstance(value, float) and value.is_integer():
                display_value = format(int(value), ",")
            elif isinstance(value, (int, float)):
                display_value = format(value, ",")
            else:
                display_value = value[:80]
            field_name = str(row.get("field") or "unknown")[:40]
            field_label = "Filing date" if field_name == "filing_dates" else field_name.replace("_", " ").title()
            proof = (
                '<div class="sec-annual-field-proof">'
                f'<div>Source: {escape(str(row.get("taxonomy") or "unknown")[:32])}:'
                f'{escape(str(row.get("concept") or "unknown")[:96])}; accession '
                f'{escape(str(row.get("accession") or "unavailable")[:24])}</div>'
                f'<div>Period: {escape(str(row.get("period_start") or "not stated")[:20])} to '
                f'{escape(str(row.get("period_end") or "unknown")[:20])}</div>'
                '<div>Field scope: approved; raw redistribution held</div>'
                f'<div>Observed: {escape(str(row.get("observed_at_utc") or "unknown")[:40])}</div>'
                + (
                    '<div>Canonical schema: review required</div>'
                    if row.get("canonical_schema_status") == "review_required"
                    else ""
                )
                + '</div>'
            )
            field_rows.append(
                '<tr class="sec-annual-field-row is-available">'
                + '<th scope="row"><span class="sec-annual-field-name">'
                + f"{escape(field_label)}</span><code>{escape(field_name)}</code></th>"
                + f'<td class="sec-annual-field-value">{escape(display_value)}{proof}</td>'
                + f'<td>{escape(str(row.get("unit") or "unknown")[:16])}</td>'
                + f'<td>{escape(str(row.get("period_end") or "unknown")[:20])}</td>'
                + "</tr>"
            )
        approved_count = len(field_rows)
        reason_labels = {
            "raw_source_value_invalid": "Raw SEC amount is malformed or nonnumeric",
            "raw_source_conflict": "Raw SEC records conflict for this exact filing context",
            "derived_field_scope_unreviewed": "Derived field scope needs review",
            "unsupported_online_field": "This field is outside the SEC annual-facts scope",
            "field_source_mismatch": "Source identity or period does not match",
            "nonannual_source": "The fact is not from an annual filing",
            "field_unit_mismatch": "The reported unit does not match this field",
            "invalid_direct_value": "A valid direct value was not available",
            "source_evidence_unreviewed": "Source evidence needs review",
            "duplicate_direct_field": "Conflicting or duplicate source facts need review",
            "source_reference_missing": "Exact SEC field reference is missing",
            "field_concept_mismatch": "SEC concept does not match this field",
            "field_period_mismatch": "Field period does not match the annual filing",
            "annual_anchor_reference_missing": "Revenue annual source anchor is missing",
        }
        withheld_input = view.get("withheld_fields")
        if not isinstance(withheld_input, (list, tuple)):
            withheld_input = []
        withheld_count = 0
        for row in withheld_input[: max(32 - approved_count, 0)]:
            if not isinstance(row, Mapping):
                continue
            field_name = str(row.get("field") or "unknown")[:40]
            withheld_count += 1
            field_rows.append(
                '<tr class="sec-annual-field-row is-withheld">'
                + '<th scope="row"><span class="sec-annual-field-name">'
                + f'{escape(field_name.replace("_", " ").title())}</span>'
                + f"<code>{escape(field_name)}</code></th>"
                + '<td class="sec-annual-field-reason">Withheld · '
                + f'{escape(reason_labels.get(row.get("reason"), "Evidence needs review"))}</td>'
                + '<td aria-label="Unit not verified">—</td>'
                + '<td aria-label="Field period not verified">—</td>'
                + "</tr>"
            )
        empty_approved = (
            "<p>No direct-approved annual facts are available.</p>"
            if approved_count == 0
            else ""
        )
        field_table = (
            '<div class="sec-annual-table-scroll" role="region" '
            'aria-label="Annual filing fields" tabindex="0">'
            '<table class="sec-annual-field-table">'
            f'<caption>Annual fields · {approved_count} direct · {withheld_count} withheld</caption>'
            '<thead><tr><th scope="col">Field</th><th scope="col">Value or reason</th>'
            '<th scope="col">Unit</th><th scope="col">Period end</th></tr></thead>'
            '<tbody>' + "".join(field_rows) + '</tbody></table></div>'
        )
        body = (
            details
            + "<h4>Annual filing field evidence</h4>"
            + empty_approved
            + field_table
        )
    return (
        '<section class="company-sec-annual-preview" aria-label="SEC annual facts">'
        '<span class="sec-annual-kicker">Online filing evidence</span>'
        f"<h3>SEC annual facts {ticker}</h3>"
        + body
        + boundary
        + "</section>"
    )
