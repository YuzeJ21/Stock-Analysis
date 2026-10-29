"""Read-only view model for an explicitly requested SEC annual-facts preview."""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date, datetime, timedelta
from html import escape
from typing import Any, Callable, Mapping, MutableMapping


SESSION_KEY = "company_sec_annual_preview_v1"
ALLOWED_DIRECT_FIELDS = frozenset({"revenue", "shares_outstanding", "filing_dates"})
ANNUAL_FORMS = frozenset({"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"})
EXPECTED_UNITS = {"revenue": "USD", "shares_outstanding": "shares", "filing_dates": "date"}


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
        row.get("status") not in {"compared", "compared_canonical_missing"}
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
    approved: list[dict[str, Any]] = []
    withheld: list[dict[str, str]] = []
    approved_forms: set[str] = set()
    for field in fields:
        field_name = str(field.get("field") or "unknown")
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
        )
        if same_source and (
            field_name in ALLOWED_DIRECT_FIELDS
            and field.get("form") in ANNUAL_FORMS
            and unit_ok
            and value_ok
            and field.get("classification") == "approved_direct"
            and field.get("field_scope_status") == "approved"
            and field.get("source_rights_status") == "approved"
            and field.get("commercial_rights_approved") is True
            and field.get("publishability_blocker") == "none"
        ):
            approved_forms.add(str(field.get("form")))
            approved.append(
                {
                    "field": field_name,
                    "value": field.get("candidate_value"),
                    "unit": field.get("unit"),
                    "period_end": field.get("period_end"),
                }
            )
        else:
            withheld.append(
                {
                    "field": field_name,
                    "reason": (
                        "derived_field_scope_unreviewed"
                        if field.get("classification") == "derived_scope_review_required"
                        else "unsupported_online_field"
                        if field_name not in ALLOWED_DIRECT_FIELDS
                        else "nonannual_source"
                        if field.get("classification") == "approved_direct" and field.get("form") not in ANNUAL_FORMS
                        else "field_source_mismatch"
                        if field.get("classification") == "approved_direct" and not same_source
                        else "field_unit_mismatch"
                        if field.get("classification") == "approved_direct" and not unit_ok
                        else "invalid_direct_value"
                        if field.get("classification") == "approved_direct" and not value_ok
                        else "source_evidence_unreviewed"
                    ),
                }
            )
    field_counts = Counter(str(field.get("field") or "unknown") for field in fields)
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
    if preview_builder is None:
        from src.sec_fundamentals_preview import build_sec_fundamentals_preview

        preview_builder = build_sec_fundamentals_preview
    try:
        preview = preview_builder(normalized, user_agent=user_agent)
    except (RuntimeError, ValueError, TypeError, OSError, TimeoutError):
        view = _unavailable(normalized, "sec_fetch_unavailable")
        session_state[SESSION_KEY] = {"ticker": normalized, "view": view}
        return view
    view = present_company_sec_annual_preview(normalized, preview)
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
            field_rows.append(
                '<tr class="sec-annual-field-row is-available">'
                + '<th scope="row"><span class="sec-annual-field-name">'
                + f"{escape(field_label)}</span><code>{escape(field_name)}</code></th>"
                + f'<td class="sec-annual-field-value">{escape(display_value)}</td>'
                + f'<td>{escape(str(row.get("unit") or "unknown")[:16])}</td>'
                + f'<td>{escape(str(row.get("period_end") or "unknown")[:20])}</td>'
                + "</tr>"
            )
        approved_count = len(field_rows)
        reason_labels = {
            "derived_field_scope_unreviewed": "Derived field scope needs review",
            "unsupported_online_field": "This field is outside the SEC annual-facts scope",
            "field_source_mismatch": "Source identity or period does not match",
            "nonannual_source": "The fact is not from an annual filing",
            "field_unit_mismatch": "The reported unit does not match this field",
            "invalid_direct_value": "A valid direct value was not available",
            "source_evidence_unreviewed": "Source evidence needs review",
            "duplicate_direct_field": "Conflicting or duplicate source facts need review",
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
