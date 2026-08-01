"""Pure, fail-closed portable snapshot for the Company Workbench HTML brief."""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Mapping
from urllib.parse import urlparse

from src.catalyst_evidence_timeline import CatalystTimeline
from src.forward_view import ForwardViewPacket
from src.historical_valuation_regime import ValuationRegimePacket
from src.observation_recency import ObservationRecencySet
from src.profile_context import ProfileContext
from src.quarterly_business_trend import QuarterlyTrendPacket
from src.research_decision_lab import ResearchDecisionLabState
from src.research_thesis_journal import JournalState
from src.scenario_lab import ScenarioLabResult


_AVAILABLE = frozenset({"available", "ready", "calculated", "current", "supported", "complete", "usable_now", "documented", "reviewable", "reviewed", "review_current", "evidence_recorded", "process_documented", "thesis_documented", "invalidation_documented", "baseline_ready", "backtest_ready", "signal_context_ready", "probability_available"})
_PARTIAL = frozenset({"partial", "incomplete", "conflict_review_needed", "overdue_review", "scheduled_review", "review_now"})
_STALE = frozenset({"stale", "stale_review_only", "stale_or_unknown"})
_NOT_RECORDED = frozenset({"not_recorded", "not recorded", "not_started", "empty", "missing"})
_EXCLUDED = frozenset({"excluded", "not_applicable", "candidate_context_only"})
_WITHHELD = frozenset({"withheld", "blocked", "still_blocked", "commercial_evidence_blocked", "unavailable", "insufficient_data", "insufficient_history", "not_supported", "unverified", "rejected"})
_ACTION_PATTERN = re.compile(r"\b(buy|sell|short|hold|position\s*size|allocation|stop[-\s]?loss|take[-\s]?profit|order|broker|rank(?:ing)?|target[-\s]?price|expected[-\s]?return|upside|downside|margin[-\s]?of[-\s]?safety)\b", re.I)
_SECRET_PATTERN = re.compile(r"(?:api[_-]?key|secret|token|cookie|password|authorization|bearer)\s*(?:=|:)|\b(?:sk|ghp|xox)[A-Za-z0-9_-]{8,}\b", re.I)
_PATH_PATTERN = re.compile(r"(?:^~[/\\]|^/|^[A-Za-z]:[\\/]|(?:^|\s)\.{1,2}(?:[/\\]|$)|/Users/|/private/|/tmp/|\\\\)")
_WITHHELD_ACTION = "Withheld: reviewer-authored action language is not portable research evidence."


@dataclass(frozen=True)
class HtmlBriefSafeReference:
    label: str
    href: str


@dataclass(frozen=True)
class HtmlBriefAnswer:
    label: str
    title: str
    body: str
    state: str
    badges: tuple[str, ...]


@dataclass(frozen=True)
class HtmlBriefDcfBridge:
    state: str
    enterprise_state: str
    equity_state: str
    per_share_state: str
    explicit_total_state: str
    projected_fcfs: tuple[float, ...]
    discounted_fcfs: tuple[float, ...]
    discounted_explicit_total: float | None
    terminal_value: float | None
    discounted_terminal_value: float | None
    enterprise_value: float | None
    cash: float | None
    debt: float | None
    net_debt: float | None
    equity_value: float | None
    shares_outstanding: float | None
    shares_label: str
    share_basis_state: str
    scenario_value_per_share: float | None
    currency: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class HtmlBriefScenario:
    name: str
    state: str
    modified: bool
    method_name: str
    revenue_growth: float | None
    fcf_margin: float | None
    wacc: float | None
    terminal_growth: float | None
    forecast_years: int | None
    bridge: HtmlBriefDcfBridge


@dataclass(frozen=True)
class HtmlBriefSensitivity:
    state: str
    wacc_values: tuple[float, ...]
    terminal_growth_values: tuple[float, ...]
    value_grid: tuple[tuple[float | None, ...], ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class HtmlBriefSection:
    key: str
    title: str
    state: str
    answer: str
    facts: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class HtmlBriefEvidenceRow:
    section: str
    state: str
    source_id: str
    source_ref: HtmlBriefSafeReference
    as_of: str
    retrieved_at: str
    rights_state: str
    field_scope_state: str
    model_identity: str
    input_identity: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class CompanyWorkbenchHtmlInputs:
    report_payload: Mapping[str, object]
    profile_context: ProfileContext
    observation_recency: ObservationRecencySet | None
    selected_answer: Mapping[str, object]
    authoritative_task: Mapping[str, object]
    scenario_lab_result: ScenarioLabResult | None
    nowcast_packet: Mapping[str, object] | None
    decision_lab_state: ResearchDecisionLabState
    quarterly_trend: QuarterlyTrendPacket
    forward_view: ForwardViewPacket
    journal_state: JournalState | None
    valuation_regime: ValuationRegimePacket
    catalyst_timeline: CatalystTimeline


@dataclass(frozen=True)
class CompanyWorkbenchHtmlSnapshot:
    ticker: str
    profile_label: str
    review_cutoff: str
    source_as_of: str
    generated_at: str
    model_version: str
    freshness_state: str
    rights_state: str
    boundary: str
    answers: tuple[HtmlBriefAnswer, ...]
    recency: HtmlBriefSection
    readiness_lanes: tuple[HtmlBriefSection, ...]
    scenarios: tuple[HtmlBriefScenario, ...]
    sensitivity: HtmlBriefSensitivity
    research_sections: tuple[HtmlBriefSection, ...]
    decision_lanes: tuple[HtmlBriefSection, ...]
    evidence_rows: tuple[HtmlBriefEvidenceRow, ...]
    blockers: tuple[str, ...]
    identity: str


def normalize_html_brief_state(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in _AVAILABLE:
        return "available"
    if text in _PARTIAL:
        return "partial"
    if text in _STALE:
        return "stale"
    if text in _NOT_RECORDED:
        return "not_recorded"
    if text in _EXCLUDED:
        return "excluded"
    return "withheld"


def safe_html_brief_text(value: object) -> str:
    """Return escaped portable text, never paths, secrets, or action instructions."""
    if not isinstance(value, (str, int, float, bool)):
        return ""
    text = str(value).strip()
    if not text or any(ord(char) < 32 and char not in "\t\n" for char in text):
        return ""
    if _PATH_PATTERN.search(text) or _SECRET_PATTERN.search(text):
        return ""
    parsed = urlparse(text)
    if parsed.scheme or text.startswith("//"):
        return ""
    if _ACTION_PATTERN.search(text):
        return _WITHHELD_ACTION
    return html.escape(text, quote=True)


def safe_html_brief_reference(value: object) -> HtmlBriefSafeReference:
    if isinstance(value, Mapping):
        label = safe_html_brief_text(value.get("label") or value.get("source") or value.get("source_id") or "")
        candidate = value.get("href") or value.get("source_ref") or ""
    else:
        label = safe_html_brief_text(value)
        candidate = value
    href = ""
    if isinstance(candidate, str) and not any(ord(char) < 32 for char in candidate) and not _SECRET_PATTERN.search(candidate):
        parsed = urlparse(candidate.strip())
        unsafe_path = parsed.path.startswith(("/Users/", "/private/", "/tmp/")) or ".." in parsed.path or "\\" in parsed.path
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and not unsafe_path:
            href = candidate.strip()
    return HtmlBriefSafeReference(label, href)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _value(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _ticker(value: object) -> str:
    return str(value or "").strip().upper()


def _finite(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _finite_tuple(value: object) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    result = tuple(_finite(item) for item in value)
    return tuple(item for item in result if item is not None) if len(result) == len(value) else ()


def _iso(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return ""
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _date_part(value: str) -> str:
    return value[:10] if len(value) >= 10 and _iso(value) else ""


def _clean_text(value: object, fallback: str = "not recorded") -> str:
    return safe_html_brief_text(value) or fallback


def _bridge(dcf_result: object, currency: str) -> HtmlBriefDcfBridge:
    status = str(_value(dcf_result, "status", "")).strip().lower()
    blockers: list[str] = []
    if status != "calculated":
        return HtmlBriefDcfBridge("withheld", "withheld", "withheld", "withheld", "withheld", (), (), None, None, None, None, None, None, None, None, None, "Shares outstanding", "unverified", None, currency, ("DCF result is not calculated.",))
    assumptions = _mapping(_value(dcf_result, "assumptions", {}))
    projected = _finite_tuple(_value(dcf_result, "projected_fcfs", ()))
    discounted = _finite_tuple(_value(dcf_result, "discounted_fcfs", ()))
    explicit = _finite(_value(dcf_result, "discounted_explicit_total"))
    terminal = _finite(_value(dcf_result, "terminal_value"))
    discounted_terminal = _finite(_value(dcf_result, "discounted_terminal_value"))
    enterprise = _finite(_value(dcf_result, "enterprise_value"))
    cash, debt, net_debt = (_finite(assumptions.get(key)) for key in ("cash", "debt", "net_debt"))
    equity = _finite(_value(dcf_result, "equity_value"))
    shares = _finite(assumptions.get("shares_outstanding"))
    per_share = _finite(_value(dcf_result, "fair_value_per_share"))
    enterprise_state = "available" if enterprise is not None else "withheld"
    explicit_state = "available" if explicit is not None else "withheld"
    eligible_equity = net_debt is not None or (cash is not None and debt is not None)
    equity_state = "available" if eligible_equity and equity is not None else "withheld"
    per_share_state = "available" if equity_state == "available" and shares is not None and shares > 0 and per_share is not None else "withheld"
    if enterprise_state != "available": blockers.append("Enterprise value is unavailable.")
    if explicit_state != "available": blockers.append("Authoritative discounted explicit total is unavailable.")
    if not eligible_equity: blockers.append("Equity bridge requires finite net debt or both finite cash and debt.")
    elif equity is None: blockers.append("Equity value is unavailable.")
    if per_share_state != "available": blockers.append("Per-share bridge requires available equity, positive finite shares outstanding, and a supplied per-share value.")
    displayed_projected = projected if projected else ()
    displayed_discounted = discounted if discounted else ()
    state = "available" if enterprise_state == equity_state == per_share_state == "available" else ("partial" if "available" in {enterprise_state, equity_state, per_share_state} else "withheld")
    return HtmlBriefDcfBridge(state, enterprise_state, equity_state, per_share_state, explicit_state, displayed_projected, displayed_discounted, explicit, terminal, discounted_terminal, enterprise, cash, debt, net_debt, equity if equity_state == "available" else None, shares if per_share_state == "available" else None, "Shares outstanding", "unverified", per_share if per_share_state == "available" else None, currency, tuple(blockers))


def _scenario_from_raw(name: str, raw: object, currency: str, *, modified: bool = False, params: object = None) -> HtmlBriefScenario:
    dcf = _value(raw, "dcf_result", raw)
    assumptions = _mapping(_value(dcf, "assumptions", {}))
    def number(field: str) -> float | None:
        return _finite(_value(params, field, assumptions.get(field)))
    years = _value(params, "forecast_years", assumptions.get("forecast_years"))
    forecast_years = int(years) if isinstance(years, int) and not isinstance(years, bool) else None
    bridge = _bridge(dcf, currency)
    return HtmlBriefScenario(name, bridge.state, modified, _clean_text(_value(dcf, "method_name", "not recorded")), number("revenue_growth"), number("fcf_margin"), number("wacc"), number("terminal_growth"), forecast_years, bridge)


def _canonical_scenarios(valuation: Mapping[str, object], currency: str) -> dict[str, HtmlBriefScenario]:
    rows = _value(valuation, "scenarios", ())
    found: dict[str, HtmlBriefScenario] = {}
    if isinstance(rows, (list, tuple)):
        for row in rows:
            label = str(_value(row, "name", "")).strip().lower()
            if label in {"bear", "base", "bull"}:
                found[label] = _scenario_from_raw(label.title(), row, currency)
    fallback = _value(valuation, "dcf_result", {})
    return {key: found.get(key, _scenario_from_raw(key.title(), fallback, currency)) for key in ("bear", "base", "bull")}


def _accepted_scenario(result: ScenarioLabResult | None, ticker: str, profile_key: str) -> bool:
    return bool(result and result.status == "calculated" and _ticker(result.ticker) == ticker and result.profile_key == profile_key and str(result.input_identity or "").strip() and result.changed_assumptions and result.scenario_result is not None)


def _sensitivity(table: object, bridge: HtmlBriefDcfBridge) -> HtmlBriefSensitivity:
    if bridge.per_share_state != "available":
        return HtmlBriefSensitivity("withheld", (), (), (), ("Sensitivity is withheld because the owning Base bridge has no available per-share value.",))
    wacc = _finite_tuple(_value(table, "wacc_values", ()))
    terminal = _finite_tuple(_value(table, "terminal_growth_values", ()))
    raw_grid = _value(table, "fair_value_grid", ())
    grid: list[tuple[float | None, ...]] = []
    valid = bool(wacc and terminal and isinstance(raw_grid, (list, tuple)) and len(raw_grid) == len(wacc))
    if valid:
        for row in raw_grid:
            if not isinstance(row, (list, tuple)) or len(row) != len(terminal):
                valid = False
                break
            values = tuple(_finite(cell) for cell in row)
            if any(cell is None for cell in values):
                valid = False
                break
            grid.append(values)
    if not valid:
        return HtmlBriefSensitivity("withheld", (), (), (), ("Sensitivity grid is missing, malformed, or non-finite.",))
    return HtmlBriefSensitivity("available", wacc, terminal, tuple(grid), ())


def _section(key: str, title: str, state: object, answer: object, facts: tuple[tuple[object, object], ...] = (), blockers: tuple[object, ...] = ()) -> HtmlBriefSection:
    return HtmlBriefSection(key, title, normalize_html_brief_state(state), _clean_text(answer, "No portable evidence recorded."), tuple((_clean_text(k), _clean_text(v)) for k, v in facts if safe_html_brief_text(k) and safe_html_brief_text(v)), tuple(_clean_text(item) for item in blockers if safe_html_brief_text(item)))


def _recency(inputs: CompanyWorkbenchHtmlInputs, ticker: str) -> HtmlBriefSection:
    record = inputs.observation_recency.selected_ticker if inputs.observation_recency else None
    if record is None or _ticker(record.scope) != ticker:
        return _section("recency", "Recency", "withheld", "No matching selected-ticker observation.", blockers=("Selected-ticker observation is unavailable or mismatched.",))
    return _section("recency", "Recency", record.state, record.message, (("Through date", record.through_date), ("Age days", record.age_days), ("Policy days", inputs.observation_recency.policy_days), ("Evaluation as of", inputs.observation_recency.as_of)))


def _nowcast_lanes(packet: Mapping[str, object] | None, report: Mapping[str, object], ticker: str, generated_at: str, review_cutoff: str) -> tuple[HtmlBriefSection, HtmlBriefSection, HtmlBriefSection]:
    withheld = ("Matching source-backed point-in-time nowcast evidence is unavailable.",)
    if not packet or _ticker(packet.get("ticker")) != ticker or str(packet.get("fiscal_period") or "") != str(_mapping(report.get("earnings_summary")).get("fiscal_period") or "") or not str(_mapping(report.get("earnings_summary")).get("fiscal_period") or "") or packet.get("evidence_scope") != "source_backed_preview_only":
        return tuple(_section(key, title, "withheld", "No portable nowcast evidence.", blockers=withheld) for key, title in (("consensus", "Consensus"), ("backtesting", "Backtesting"), ("calibration", "Calibration")))  # type: ignore[return-value]
    packet_at = _iso(packet.get("as_of_timestamp"))
    boundaries = tuple(_iso(value) for value in (generated_at, review_cutoff) if _iso(value))
    if not packet_at or any(packet_at > boundary for boundary in boundaries):
        return tuple(_section(key, title, "withheld", "No portable nowcast evidence.", blockers=withheld) for key, title in (("consensus", "Consensus"), ("backtesting", "Backtesting"), ("calibration", "Calibration")))  # type: ignore[return-value]
    readiness = _mapping(packet.get("readiness"))
    consensus_state = "partial" if readiness.get("consensus_ready") is True else "withheld"
    provenance = "portable nowcast provenance incomplete"
    return (
        _section("consensus", "Consensus", consensus_state, "Source-backed preview is present; portable provenance remains incomplete.", blockers=(provenance,) if consensus_state == "partial" else ("Consensus readiness is not explicitly true.",)),
        _section("backtesting", "Backtesting", "partial", "Point-in-time preview verdict is not portable as complete evidence.", blockers=(provenance,)),
        _section("calibration", "Calibration", "partial", "Point-in-time preview calibration is not portable as complete evidence.", blockers=(provenance,)),
    )


def _readiness(inputs: CompanyWorkbenchHtmlInputs, ticker: str, bridge: HtmlBriefDcfBridge, generated_at: str, review_cutoff: str) -> tuple[HtmlBriefSection, ...]:
    trend = inputs.quarterly_trend if _ticker(inputs.quarterly_trend.ticker) == ticker else None
    forward = inputs.forward_view if _ticker(inputs.forward_view.ticker) == ticker else None
    actual = _section("actuals", "Actuals", trend.status if trend else "withheld", trend.message if trend else "No matching quarterly evidence.", blockers=() if trend else ("Quarterly ticker does not match report ticker.",))
    revenue = _section("revenue", "Revenue", trend.revenue.status if trend else "withheld", trend.revenue.withheld_reason or "Quarterly revenue context.", blockers=("Q4 requires explicit compatible quarterly evidence.",) if trend else ("Quarterly ticker does not match report ticker.",))
    eps = _section("eps", "EPS", trend.eps.status if trend else "withheld", trend.eps.withheld_reason or "Quarterly EPS context.", blockers=("EPS split-basis proof is required.",) if trend else ("Quarterly ticker does not match report ticker.",))
    valuation = _section("valuation", "Valuation", bridge.state, "Authoritative DCF bridge.", blockers=bridge.blockers)
    peers = _section("peers", "Peers", forward.peer_context.state if forward else "withheld", forward.peer_context.answer if forward else "No matching Forward View evidence.", blockers=() if forward else ("Forward View ticker does not match report ticker.",))
    historical = _section("historical-valuation", "Historical valuation", inputs.valuation_regime.state if _ticker(inputs.valuation_regime.ticker) == ticker else "withheld", inputs.valuation_regime.boundary if _ticker(inputs.valuation_regime.ticker) == ticker else "No matching valuation regime.", blockers=("portable provenance incomplete",))
    catalyst_matches = _catalyst_matches(inputs.catalyst_timeline, ticker, inputs.profile_context.profile_key)
    catalysts = _section("catalysts", "Catalysts", inputs.catalyst_timeline.state if catalyst_matches else "withheld", inputs.catalyst_timeline.boundary if catalyst_matches else "No matching catalyst evidence.", blockers=() if catalyst_matches else ("Catalyst event scope does not match report scope.",))
    consensus, backtesting, calibration = _nowcast_lanes(inputs.nowcast_packet, inputs.report_payload, ticker, generated_at, review_cutoff)
    outcome = _section("outcomes", "Outcomes", "withheld", "No portable outcome evidence.", blockers=("portable outcome scope and provenance incomplete",))
    return (actual, consensus, revenue, eps, valuation, peers, historical, catalysts, outcome, backtesting, calibration)


def _research_sections(inputs: CompanyWorkbenchHtmlInputs, ticker: str) -> tuple[HtmlBriefSection, ...]:
    trend = inputs.quarterly_trend if _ticker(inputs.quarterly_trend.ticker) == ticker else None
    forward = inputs.forward_view if _ticker(inputs.forward_view.ticker) == ticker else None
    report = inputs.report_payload
    risks = _mapping(report.get("risk_summary"))
    catalyst_matches = _catalyst_matches(inputs.catalyst_timeline, ticker, inputs.profile_context.profile_key)
    return (
        _section("business-trend", "Business trend", trend.status if trend else "withheld", trend.message if trend else "No matching quarterly business trend.", blockers=("portable provenance incomplete",)),
        _section("key-drivers", "Key drivers", forward.thesis_context.state if forward else "withheld", forward.thesis_context.answer if forward else "No matching Forward View evidence."),
        _section("risks", "Risks", risks.get("state", "withheld"), risks.get("summary", "No portable risk evidence.")),
        _section("catalysts", "Catalysts", inputs.catalyst_timeline.state if catalyst_matches else "withheld", inputs.catalyst_timeline.boundary if catalyst_matches else "No matching catalyst evidence.", blockers=() if catalyst_matches else ("Catalyst event scope does not match report scope.",)),
        _section("evidence-gaps", "Evidence gaps", "withheld", "Portable evidence remains incomplete."),
        _section("valuation-regime", "Valuation regime", inputs.valuation_regime.state if _ticker(inputs.valuation_regime.ticker) == ticker else "withheld", inputs.valuation_regime.boundary if _ticker(inputs.valuation_regime.ticker) == ticker else "No matching valuation regime.", blockers=("portable provenance incomplete",)),
    )


def _catalyst_matches(timeline: CatalystTimeline, ticker: str, profile_key: str) -> bool:
    if _ticker(timeline.ticker) != ticker:
        return False
    events = tuple(timeline.upcoming) + tuple(timeline.recent)
    return all(_ticker(event.ticker) == ticker and event.profile_key == profile_key for event in events)


def _decision_lanes(state: ResearchDecisionLabState, ticker: str, profile_key: str) -> tuple[HtmlBriefSection, ...]:
    by_key = {lane.key: lane for lane in state.lanes} if state.ticker.upper() == ticker and state.profile_key == profile_key else {}
    ordered = (("plan", "Plan"), ("evidence", "Evidence"), ("invalidation", "Invalidation"), ("scenario", "Scenario"), ("review-trigger", "Review trigger"), ("learning", "Learning"))
    output: list[HtmlBriefSection] = []
    for output_key, title in ordered:
        lane = by_key.get(output_key.replace("-", "_"))
        output.append(_section(output_key, title, lane.state if lane else "withheld", lane.answer if lane else "No matching Decision Lab evidence.", blockers=() if lane else ("Decision Lab scope does not match report scope.",)))
    return tuple(output)


def _evidence_rows(inputs: CompanyWorkbenchHtmlInputs, accepted_scenario: bool) -> tuple[HtmlBriefEvidenceRow, ...]:
    candidates: list[tuple[str, object, str]] = []
    provenance = _mapping(inputs.report_payload.get("provenance"))
    for row in provenance.get("source_records", ()) if isinstance(provenance.get("source_records"), (list, tuple)) else ():
        candidates.append(("report", row, ""))
    valuation = _mapping(inputs.report_payload.get("valuation_snapshot"))
    for row in valuation.get("source_metadata", ()) if isinstance(valuation.get("source_metadata"), (list, tuple)) else ():
        candidates.append(("valuation", row, ""))
    if accepted_scenario and inputs.scenario_lab_result:
        for row in inputs.scenario_lab_result.source_metadata:
            candidates.append(("scenario", row, inputs.scenario_lab_result.input_identity))
    rows: list[HtmlBriefEvidenceRow] = []
    for section, raw, identity in candidates:
        item = _mapping(raw)
        source_id = safe_html_brief_text(item.get("source_id") or item.get("source") or "")
        ref = safe_html_brief_reference(item)
        as_of = _iso(item.get("as_of") or item.get("as_of_date") or item.get("published_at"))
        retrieved = _iso(item.get("retrieved_at"))
        rights = str(item.get("rights_state") or "").strip().lower()
        scope = str(item.get("field_scope_state") or "").strip().lower()
        if not (source_id and ref.href and as_of and retrieved):
            continue
        rights_state = "permitted" if rights == "permitted" else ("not_applicable" if rights == "not_applicable" else "unverified")
        scope_state = "permitted" if scope == "permitted" else ("not_applicable" if scope == "not_applicable" else "unverified")
        state = "available" if rights_state == scope_state == "permitted" else "withheld"
        blockers = () if state == "available" else ("Portable rights or field-scope provenance is incomplete.",)
        row = HtmlBriefEvidenceRow(section, state, source_id, ref, as_of, retrieved, rights_state, scope_state, _clean_text(item.get("model_identity"), "not recorded"), _clean_text(identity, "not recorded"), blockers)
        if row not in rows:
            rows.append(row)
    return tuple(rows)


def _rights_state(rows: tuple[HtmlBriefEvidenceRow, ...]) -> str:
    if not rows:
        return "withheld"
    if all(row.rights_state == "not_applicable" for row in rows):
        return "excluded"
    return "available" if all(row.rights_state == "permitted" and row.field_scope_state == "permitted" for row in rows) else "withheld"


def build_company_workbench_html_snapshot(inputs: CompanyWorkbenchHtmlInputs) -> CompanyWorkbenchHtmlSnapshot:
    """Build only from supplied objects; this function performs no I/O or refresh work."""
    report = _mapping(inputs.report_payload)
    ticker = _ticker(report.get("ticker"))
    generated_at = _iso(report.get("generated_at")) or "not recorded"
    forward_cutoff = _iso(inputs.forward_view.source_cutoff) if _ticker(inputs.forward_view.ticker) == ticker else ""
    review_cutoff = forward_cutoff or (_iso(generated_at) if generated_at != "not recorded" else "") or _iso(inputs.profile_context.source_as_of) or "not recorded"
    provenance = _mapping(report.get("provenance"))
    model_version = _clean_text(report.get("method_version") or provenance.get("method_version"), "not recorded")
    financial = _mapping(report.get("financial_summary"))
    currency = _clean_text(financial.get("currency") or _mapping(report.get("price_snapshot")).get("currency"), "not recorded")
    scope_blockers: list[str] = []
    selected_matches = _ticker(inputs.selected_answer.get("Ticker")) == ticker
    if not selected_matches:
        scope_blockers.append("Selected answer ticker does not match report ticker.")
    canonical = _canonical_scenarios(_mapping(report.get("valuation_snapshot")), currency)
    accepted = _accepted_scenario(inputs.scenario_lab_result, ticker, inputs.profile_context.profile_key)
    if inputs.scenario_lab_result and not accepted:
        scope_blockers.append("Scenario Lab result is not an accepted matching changed calculation.")
    if accepted and inputs.scenario_lab_result:
        canonical["base"] = _scenario_from_raw("Base", inputs.scenario_lab_result.scenario_result, currency, modified=True, params=inputs.scenario_lab_result.scenario_parameters)
    scenarios = tuple(canonical[name] for name in ("bear", "base", "bull"))
    sensitivity_table = inputs.scenario_lab_result.sensitivity_table if accepted and inputs.scenario_lab_result else _mapping(report.get("valuation_snapshot")).get("sensitivity_table")
    sensitivity = _sensitivity(sensitivity_table, canonical["base"].bridge)
    selected_state = inputs.selected_answer.get("state", "withheld") if selected_matches else "withheld"
    answers = (
        HtmlBriefAnswer("Usable now", "Usable now", _clean_text(inputs.selected_answer.get("Use Now"), "No portable answer."), normalize_html_brief_state(selected_state), ()),
        HtmlBriefAnswer("Still withheld", "Still withheld", _clean_text(inputs.selected_answer.get("Still Blocked"), "No portable blocker."), "withheld", ()),
        HtmlBriefAnswer("Next research task", _clean_text(inputs.authoritative_task.get("title"), "Next research task"), _clean_text(inputs.authoritative_task.get("body"), "No portable task."), normalize_html_brief_state(inputs.authoritative_task.get("state")), tuple(safe_html_brief_text(item) for item in inputs.authoritative_task.get("badges", ()) if safe_html_brief_text(item)) if isinstance(inputs.authoritative_task.get("badges"), (list, tuple)) else ()),
    )
    evidence = _evidence_rows(inputs, accepted)
    freshness = normalize_html_brief_state(inputs.observation_recency.selected_ticker.state) if inputs.observation_recency and _ticker(inputs.observation_recency.selected_ticker.scope) == ticker else normalize_html_brief_state(inputs.profile_context.freshness_state)
    snapshot = CompanyWorkbenchHtmlSnapshot(ticker, _clean_text(inputs.profile_context.profile_label), review_cutoff, _clean_text(inputs.profile_context.source_as_of), generated_at, model_version, freshness, _rights_state(evidence), "Research-only, fail-closed portable brief; no recommendation, probability, or transaction action.", answers, _recency(inputs, ticker), _readiness(inputs, ticker, canonical["base"].bridge, generated_at, review_cutoff), scenarios, sensitivity, _research_sections(inputs, ticker), _decision_lanes(inputs.decision_lab_state, ticker, inputs.profile_context.profile_key), evidence, tuple(scope_blockers), "")
    payload = json.dumps(asdict(snapshot), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return replace(snapshot, identity=hashlib.sha256(payload.encode("utf-8")).hexdigest())


def company_workbench_html_filename(snapshot: CompanyWorkbenchHtmlSnapshot) -> str:
    ticker = re.sub(r"[^A-Z0-9.-]", "", snapshot.ticker.upper()) or "UNKNOWN"
    date = _date_part(snapshot.review_cutoff) or _date_part(snapshot.generated_at) or "undated"
    return f"{ticker}-{date}-research-brief.html"
