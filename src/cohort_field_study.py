"""Read-only view of two saved six-company field inspections."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

from src.cohort_field_evidence import DEFAULT_TICKERS, FIELDS, SCHEMA_VERSION, compare_reports


REQUIRED_ROW_KEYS = (
    "value", "source", "source_ref", "period_end", "source_published_at",
    "observation_date", "observation_date_basis", "rights_status", "registered_field_scope",
    "withheld_reasons", "interpretation_state",
)
FIELD_LABELS = {
    "cash_from_operations": "Cash from operations",
    "capital_expenditures": "Capital expenditures",
    "free_cash_flow": "Free cash flow",
    "fcf_margin": "Free cash flow margin",
    "shares_outstanding": "Shares outstanding",
    "latest_close": "Latest saved close",
}
REASON_LABELS = {
    "saved_field_missing": "Saved evidence missing",
    "field_specific_proof_missing": "Exact field source proof missing",
    "field_not_registered": "Field not in the rights registry",
    "source_rights_unverified": "Source rights unverified",
    "price_source_missing": "Price source missing",
    "source_missing": "Source missing",
    "source_reference_missing": "Source reference missing",
    "period_end_missing": "Period end missing",
    "publication_date_missing": "Publication date missing",
    "observation_date_missing": "Observation date missing",
    "stale_observation": "Saved observation is old",
    "old_period_end": "Saved period is old",
}
DIMENSION_LABELS = {
    "value": "Value", "source": "Source", "source_ref": "Source reference",
    "period_end": "Period end", "source_published_at": "Publication date",
    "observation_date": "Observation date", "observation_date_basis": "Observation date basis",
    "rights_status": "Rights status",
    "registered_field_scope": "Registered field scope",
    "withheld_reasons": "Reasons withheld", "interpretation_state": "Interpretation state",
}
SAVED_NAMES = ("cohort_field_evidence_2026-10-26.json", "cohort_field_evidence_2026-10-27.json")


@dataclass(frozen=True)
class BoundedFieldStudy:
    status: str
    message: str
    fields: tuple[dict, ...] = ()
    changes: tuple[dict, ...] = ()
    prior_as_of: str = ""
    current_as_of: str = ""
    snapshot_identity: str = ""
    same_input_digest: bool = False
    field_count: int = 0
    withheld_count: int = 0


def _valid_report(report: object) -> bool:
    if not isinstance(report, dict):
        return False
    if (report.get("schema_version") != SCHEMA_VERSION
            or report.get("tickers") != list(DEFAULT_TICKERS)
            or report.get("inspection_only") is not True
            or report.get("canonical_writes") is not False):
        return False
    stamp, digest, rows = report.get("as_of"), report.get("snapshot_identity"), report.get("fields")
    if not isinstance(stamp, str) or not isinstance(digest, str) or not isinstance(rows, list):
        return False
    try:
        if date.fromisoformat(stamp).isoformat() != stamp:
            return False
    except ValueError:
        return False
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None or len(rows) != len(DEFAULT_TICKERS) * len(FIELDS):
        return False
    expected = {(ticker, field) for ticker in DEFAULT_TICKERS for field in FIELDS}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or any(key not in row for key in ("ticker", "field", *REQUIRED_ROW_KEYS)):
            return False
        if (any(not isinstance(row[key], str) for key in (
                "ticker", "field", "value", "source", "source_ref", "period_end",
                "source_published_at", "observation_date", "observation_date_basis",
                "rights_status", "interpretation_state"))
                or not isinstance(row["registered_field_scope"], bool)):
            return False
        key = (row["ticker"], row["field"])
        if key not in expected or key in seen:
            return False
        if (not isinstance(row["withheld_reasons"], list)
                or any(not isinstance(reason, str) for reason in row["withheld_reasons"])):
            return False
        if row["interpretation_state"] not in {"withheld", "inspect_only"}:
            return False
        seen.add(key)
    return seen == expected


def _unavailable(message: str) -> BoundedFieldStudy:
    return BoundedFieldStudy("unavailable", message)


def load_bounded_field_study(root: Path | str, *, profile_key: str, data_dir: Path | str) -> BoundedFieldStudy:
    """Read the pinned local reports only for their default-profile scope."""

    selected_root = Path(root).resolve()
    if profile_key != "default" or Path(data_dir).resolve() != (selected_root / "data").resolve():
        return _unavailable("This saved study is available only in the default local profile.")
    paths = tuple(selected_root / "outputs" / "local" / name for name in SAVED_NAMES)
    try:
        before, after = (json.loads(path.read_text(encoding="utf-8")) for path in paths)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _unavailable("Comparable saved field reports are unavailable locally.")
    if not _valid_report(before) or not _valid_report(after):
        return _unavailable("The saved field reports could not be verified.")
    comparison = compare_reports(before, after)
    if comparison["status"] == "incompatible_scope":
        return _unavailable("The saved field reports could not be compared safely.")
    status = comparison["status"]
    same_inputs = bool(comparison["same_input_digest"])
    if status == "unchanged" and same_inputs:
        message = "No field difference; two saved inspections of the same underlying inputs."
    elif status == "review_date_reevaluation":
        message = "The review date changed an aging reason; the same underlying inputs contain no new source observation."
    elif status == "unchanged":
        message = "No selected field difference across the saved inspections."
    else:
        message = "Saved field differences need inspection before any conclusion changes."
    fields = tuple(after["fields"])
    return BoundedFieldStudy(
        status, message, fields, tuple(comparison["changes"]), before["as_of"], after["as_of"],
        after["snapshot_identity"], same_inputs, len(fields),
        sum(row["interpretation_state"] == "withheld" for row in fields),
    )


def _safe(value: object) -> str:
    if isinstance(value, list):
        value = ", ".join(str(part) for part in value)
    return html.escape(str(value if value is not None else ""), quote=True)


def _label(value: str, known: dict[str, str]) -> str:
    return known.get(value, value.replace("_", " ").capitalize())


def _display_change_value(dimension: str, value: object) -> str:
    if dimension == "source_ref":
        return "See Advanced Evidence" if value else "No saved reference"
    if dimension == "observation_date_basis":
        return _label(str(value or ""), {})
    if dimension == "withheld_reasons" and isinstance(value, list):
        return "; ".join(_label(str(reason), REASON_LABELS) for reason in value)
    if dimension == "rights_status":
        return _label(str(value or ""), {})
    return str(value if value is not None else "")


def _company_rows(study: BoundedFieldStudy, ticker: str) -> list[dict]:
    return [row for row in study.fields if row["ticker"] == ticker]


def study_discover_html(study: BoundedFieldStudy) -> str:
    if study.status == "unavailable":
        return f"<section aria-label='Six-company evidence study'><h3>Six-company evidence study</h3><p>Unavailable: {_safe(study.message)}</p></section>"
    links = []
    for ticker in DEFAULT_TICKERS:
        rows = _company_rows(study, ticker)
        present = sum(bool(row["value"]) for row in rows)
        state = "blocked: no saved field values" if present == 0 else f"{present} saved values; interpretation withheld"
        links.append(
            f"<li><a href='?mode=research&amp;page=company-workbench&amp;ticker={quote(ticker, safe='')}&amp;open=1'>"
            f"Open {_safe(ticker)} Company Workbench</a> — {_safe(state)}</li>"
        )
    return (
        "<section aria-label='Six-company evidence study'><h3>Six-company evidence study</h3>"
        "<p>These saved examples are for evidence review. Inclusion does not change the focused cohort or screening eligibility.</p>"
        f"<ul>{''.join(links)}</ul></section>"
    )


def study_company_html(study: BoundedFieldStudy, ticker: str) -> str:
    symbol = str(ticker or "").strip().upper()
    if symbol not in DEFAULT_TICKERS:
        return ""
    if study.status == "unavailable":
        return f"<section aria-label='Saved field evidence'><h3>Saved field evidence</h3><p>Unavailable: {_safe(study.message)}</p></section>"
    company_fields = _company_rows(study, symbol)
    field_rows = "".join(
        f"<tr><th scope='row'>{_safe(_label(row['field'], FIELD_LABELS))}</th>"
        f"<td>{_safe(row['value'] or 'No saved value')}</td>"
        f"<td>{_safe(row['period_end'] or 'No saved period')}</td>"
        f"<td>{_safe('; '.join(_label(reason, REASON_LABELS) for reason in row['withheld_reasons']))}</td></tr>"
        for row in company_fields
    )
    blocked_notice = (
        "<p>Evidence review blocked: no saved field values for this company.</p>"
        if all(not row["value"] for row in company_fields) else ""
    )
    changes = [change for change in study.changes if change["ticker"] == symbol]
    change_rows = "".join(
        f"<tr><th scope='row'>{_safe(_label(change['field'], FIELD_LABELS))}</th>"
        f"<td>{_safe(_label(dimension, DIMENSION_LABELS))}</td>"
        f"<td>{_safe(_display_change_value(dimension, change['before'][dimension]))}</td>"
        f"<td>{_safe(_display_change_value(dimension, change['after'][dimension]))}</td></tr>"
        for change in changes for dimension in change["changed_dimensions"]
    )
    change_view = (
        "<p>No field difference between the saved captures.</p>" if not changes else
        "<table><caption>Saved field differences</caption><thead><tr>"
        "<th>Field</th><th>Changed dimension</th><th>Before</th><th>After</th></tr></thead>"
        f"<tbody>{change_rows}</tbody></table>"
    )
    return (
        f"<section aria-label='{_safe(symbol)} saved field evidence'><h3>{_safe(symbol)} saved-field evidence</h3>"
        f"<p>{_safe(study.message)} This inspection does not change readiness or listing status.</p>{blocked_notice}{change_view}"
        "<table><caption>Saved values and reasons they remain withheld</caption><thead><tr>"
        "<th>Field</th><th>Saved value</th><th>Period end</th><th>Reasons withheld</th></tr></thead>"
        f"<tbody>{field_rows}</tbody></table></section>"
    )


def study_company_detail_html(study: BoundedFieldStudy, ticker: str) -> str:
    """Return raw references for an explicitly opened Advanced Evidence expander."""

    symbol = str(ticker or "").strip().upper()
    if study.status == "unavailable" or symbol not in DEFAULT_TICKERS:
        return ""
    rows = "".join(
        f"<tr><th scope='row'>{_safe(row['field'])}</th><td>{_safe(row['source'])}</td>"
        f"<td>{_safe(row['source_ref'])}</td><td>{_safe(row['source_published_at'])}</td>"
        f"<td>{_safe(row['observation_date'])}</td><td>{_safe(row['rights_status'])}</td>"
        f"<td>{_safe(row['withheld_reasons'])}</td></tr>"
        for row in _company_rows(study, symbol)
    )
    return (
        "<section aria-label='Raw saved field references'>"
        f"<p>Input digest: {_safe(study.snapshot_identity)}. Captures: {_safe(study.prior_as_of)} and {_safe(study.current_as_of)}.</p>"
        "<table><caption>Raw saved field references</caption><thead><tr>"
        "<th>Field</th><th>Source</th><th>Reference</th><th>Publication</th>"
        "<th>Observation</th><th>Rights</th><th>Withheld codes</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></section>"
    )


def study_monitor_html(study: BoundedFieldStudy) -> str:
    if study.status == "unavailable":
        return f"<section aria-label='Six-company saved-field comparison'><h3>Six-company saved-field comparison</h3><p>Unavailable: {_safe(study.message)}</p></section>"
    rows = []
    for ticker in DEFAULT_TICKERS:
        count = sum(change["ticker"] == ticker for change in study.changes)
        missing = sum(not row["value"] for row in _company_rows(study, ticker))
        rows.append(f"<li>{_safe(ticker)}: {count} field difference{'s' if count != 1 else ''}; {missing} saved values missing</li>")
    return (
        "<section aria-label='Six-company saved-field comparison'><h3>Six-company saved-field comparison</h3>"
        f"<p>{_safe(study.message)} This is inspection only and adds no Monitor follow-up event.</p>"
        f"<ul>{''.join(rows)}</ul></section>"
    )
