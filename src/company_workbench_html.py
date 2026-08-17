"""Pure, fail-closed portable snapshot for the Company Workbench HTML brief."""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import unicodedata
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from datetime import datetime, timezone
from typing import Mapping
from urllib.parse import unquote, urlparse, urlsplit

from src.catalyst_evidence_timeline import CatalystTimeline
from src.forward_view import ForwardViewPacket
from src.historical_valuation_regime import ValuationRegimePacket
from src.observation_recency import ObservationRecencySet
from src.profile_context import ProfileContext
from src.quarterly_business_trend import QuarterlyTrendPacket
from src.research_decision_lab import ResearchDecisionLabState
from src.research_thesis_journal import JournalState
from src.scenario_lab import ScenarioLabResult
from src.portable_research_action_policy import contains_portable_action_language


_AVAILABLE = frozenset({"available", "ready", "calculated", "current", "supported", "complete", "usable_now", "documented", "reviewable", "reviewed", "review_current", "evidence_recorded", "process_documented", "thesis_documented", "invalidation_documented", "baseline_ready", "backtest_ready", "signal_context_ready", "probability_available"})
_PARTIAL = frozenset({"partial", "incomplete", "conflict_review_needed", "overdue_review", "scheduled_review", "review_now"})
_STALE = frozenset({"stale", "stale_review_only", "stale_or_unknown"})
_NOT_RECORDED = frozenset({"not_recorded", "not recorded", "not_started", "empty", "missing"})
_EXCLUDED = frozenset({"excluded", "not_applicable", "candidate_context_only"})
_WITHHELD = frozenset({"withheld", "blocked", "still_blocked", "commercial_evidence_blocked", "unavailable", "insufficient_data", "insufficient_history", "not_supported", "unverified", "rejected"})
_SECRET_PATTERN = re.compile(
    r"(?:\b(?:api[_-]?key|secret|token|cookie|password|authorization)\b\s*(?:=|:|\s+)\s*"
    r"(?:bearer\s+)?\S+|\bbearer\s+\S+|\b(?:sk|ghp|xox)[A-Za-z0-9_-]{8,}\b)",
    re.I,
)
_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9/])(?:~[/\\]|/[^\s]*|[A-Za-z]:[\\/][^\s]*)|"
    r"(?:^|[/\\])\.{1,2}(?:[/\\]|$)|"
    r"(?<![A-Za-z0-9])(?:src|tests|data|outputs|docs|scripts|\.git|\.superpowers)(?:[/\\]|$)|\\"
)
_SENSITIVE_PATH_SEGMENTS = frozenset(
    {"api-key", "api_key", "apikey", "authorization", "bearer", "cookie", "password", "secret", "token"}
)
_TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]+$")
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
    source_refs: tuple[HtmlBriefSafeReference, ...] = ()
    blockers: tuple[str, ...] = ()


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
    change_answer: Mapping[str, object] = field(default_factory=dict)
    change_ticker: str = ""
    change_profile_key: str = ""


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
    text = str(value)
    if not text or any(unicodedata.category(char) == "Cc" for char in text):
        return ""
    text = text.strip()
    if _PATH_PATTERN.search(text) or _SECRET_PATTERN.search(text):
        return ""
    parsed = urlparse(text)
    if parsed.scheme or text.startswith("//"):
        return ""
    if contains_portable_action_language(text):
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
    if isinstance(candidate, str) and not any(unicodedata.category(char) == "Cc" for char in candidate) and not _SECRET_PATTERN.search(candidate):
        try:
            parsed = urlparse(candidate.strip())
            parsed_port = parsed.port
            authority_is_safe = (
                (parsed_port is None or parsed_port > 0)
                and not any(char.isspace() for char in parsed.netloc)
                and "%" not in parsed.netloc
            )
            decoded_path = parsed.path
            for _ in range(2):
                decoded_path = unquote(decoded_path)
            path_segments = tuple(segment.strip().lower() for segment in decoded_path.split("/") if segment.strip())
            sensitive_pair = any(
                segment in _SENSITIVE_PATH_SEGMENTS and index + 1 < len(path_segments)
                for index, segment in enumerate(path_segments)
            )
            unsafe_path = decoded_path.startswith(("/Users/", "/private/", "/tmp/")) or ".." in decoded_path or "\\" in decoded_path or sensitive_pair
            if parsed.scheme == "https" and parsed.hostname and authority_is_safe and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and not unsafe_path:
                href = candidate.strip()
        except ValueError:
            href = ""
    return HtmlBriefSafeReference(label, href)


def _neutral_change_answer(*, state: str, blocker: str) -> HtmlBriefAnswer:
    return HtmlBriefAnswer(
        "What changed",
        "No portable change answer.",
        "No scoped saved change answer is available.",
        state,
        (),
        (),
        (blocker,),
    )


def _portable_change_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    raw = value.strip()
    if not raw or "<" in raw or ">" in raw:
        return ""
    safe = safe_html_brief_text(raw)
    return "" if not safe or safe == _WITHHELD_ACTION else safe


def _benign_incomplete_change_reference(raw: str) -> bool:
    if len(raw) > 512:
        return False
    if re.fullmatch(r"sec:[A-Za-z0-9][A-Za-z0-9._-]{0,127}", raw):
        return True
    if re.fullmatch(
        r"sec-accession:[A-Za-z0-9][A-Za-z0-9._-]{0,127}", raw
    ):
        return True
    source_tokens = tuple(part.strip() for part in raw.split(";"))
    if 1 <= len(source_tokens) <= 8 and all(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", part)
        for part in source_tokens
    ):
        return True
    try:
        parsed = urlsplit(raw)
        path_parts = tuple(part for part in parsed.path.split("/") if part)
        return bool(
            parsed.scheme == "consensus"
            and parsed.hostname
            and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9.-]{0,127}", parsed.hostname
            )
            and not parsed.username
            and not parsed.password
            and parsed.port is None
            and not parsed.query
            and not parsed.fragment
            and path_parts
            and all(
                part not in {".", ".."}
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", part)
                for part in path_parts
            )
        )
    except ValueError:
        return False


def _change_reference_is_unsafe(value: object) -> bool:
    if not isinstance(value, str):
        return True
    raw = value.strip()
    if not raw or "<" in raw or ">" in raw or "\\" in raw:
        return True
    if any(unicodedata.category(char) == "Cc" for char in raw):
        return True
    if _SECRET_PATTERN.search(raw):
        return True
    if _benign_incomplete_change_reference(raw):
        return False
    return not bool(
        safe_html_brief_reference(
            {"label": "Change source", "href": raw}
        ).href
    )


def _portable_change_answer(
    inputs: CompanyWorkbenchHtmlInputs,
    ticker: str,
) -> HtmlBriefAnswer:
    scoped = _ticker_matches(inputs.change_ticker, ticker) and _profile_matches(
        inputs.change_profile_key,
        inputs.profile_context.profile_key,
    )
    change = _mapping(inputs.change_answer)
    if not scoped or not change:
        return _neutral_change_answer(
            state="not_recorded",
            blocker="Portable change scope is absent or mismatched.",
        )

    raw_context_kind = str(change.get("change_context_kind") or "").strip().lower()
    if raw_context_kind == "none":
        return _neutral_change_answer(
            state="not_recorded",
            blocker="No source-backed or snapshot-only change is recorded.",
        )
    if raw_context_kind not in {"snapshot_only", "source_backed"}:
        return _neutral_change_answer(
            state="withheld",
            blocker="Portable change context is unsupported.",
        )

    raw_workflow_state = str(change.get("state") or "").strip().lower()
    title = _portable_change_text(change.get("answer"))
    body = _portable_change_text(change.get("next_task"))
    refs: list[HtmlBriefSafeReference] = []
    refs_incomplete = False
    raw_refs = change.get("source_refs")
    refs_unsafe = raw_refs is not None and not isinstance(raw_refs, (list, tuple))
    for index, raw in enumerate(
        raw_refs if isinstance(raw_refs, (list, tuple)) else ()
    ):
        if _change_reference_is_unsafe(raw):
            refs_unsafe = True
            continue
        safe = safe_html_brief_reference(
            {"label": f"Change source {index + 1}", "href": raw}
        )
        if safe.href and safe not in refs:
            refs.append(safe)
        elif not safe.href:
            refs_incomplete = True

    content_safe = (
        raw_workflow_state in {"monitor", "review_now", "wait_for_evidence"}
        and bool(title)
        and bool(body)
        and not refs_unsafe
    )
    if not content_safe:
        return _neutral_change_answer(
            state="withheld",
            blocker="Portable change content, workflow state, or reference is unsafe.",
        )

    if raw_context_kind == "snapshot_only":
        state = "partial"
        refs = []
        blockers = ("Change context is snapshot-only.",)
    else:
        state = "partial"
        blockers = (
            "Portable publication and retrieval dates, rights, field scope, and cutoff proof are not frozen."
            if (
                change.get("source_backed_eligible") is True
                and refs
                and not refs_incomplete
            )
            else "Portable source-backed change eligibility or reference is incomplete.",
        )

    return HtmlBriefAnswer(
        "What changed",
        title,
        body,
        state,
        tuple(
            safe_html_brief_text(item)
            for item in (raw_workflow_state, raw_context_kind)
            if safe_html_brief_text(item)
        ),
        tuple(refs),
        blockers,
    )


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _record_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return asdict(value) if is_dataclass(value) else {}


def _value(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _ticker(value: object) -> str:
    if not isinstance(value, str):
        return ""
    if any(unicodedata.category(char) == "Cc" for char in value):
        return ""
    ticker = value.strip().upper()
    return ticker if _TICKER_PATTERN.fullmatch(ticker) else ""


def _ticker_matches(value: object, ticker: str) -> bool:
    scoped = _ticker(value)
    return bool(ticker and scoped and scoped == ticker)


def _profile_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    return normalized if normalized and safe_html_brief_text(normalized) else ""


def _profile_matches(value: object, profile_key: object) -> bool:
    scoped = _profile_key(value)
    expected = _profile_key(profile_key)
    return bool(scoped and expected and scoped == expected)


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


def _iso_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso(value: object) -> str:
    parsed = _iso_datetime(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else ""


def _date_part(value: str) -> str:
    return value[:10] if len(value) >= 10 and _iso(value) else ""


def _clean_text(value: object, fallback: str = "not recorded") -> str:
    return safe_html_brief_text(value) or fallback


def _bridge(dcf_result: object, currency: str) -> HtmlBriefDcfBridge:
    status = str(_value(dcf_result, "status", "")).strip().lower()
    blockers: list[str] = []
    if status != "calculated":
        return HtmlBriefDcfBridge("withheld", "withheld", "withheld", "withheld", "withheld", (), (), None, None, None, None, None, None, None, None, None, "Shares outstanding used by existing model", "unverified", None, currency, ("DCF result is not calculated.",))
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
    if enterprise_state != "available":
        blockers.append("Enterprise value is unavailable.")
    if explicit_state != "available":
        blockers.append("Authoritative discounted explicit total is unavailable.")
    if not eligible_equity:
        blockers.append("Equity bridge requires finite net debt or both finite cash and debt.")
    elif equity is None:
        blockers.append("Equity value is unavailable.")
    if per_share_state != "available":
        blockers.append("Per-share bridge requires available equity, positive finite shares outstanding, and a supplied per-share value.")
    displayed_projected = projected if projected else ()
    displayed_discounted = discounted if discounted else ()
    state = "available" if enterprise_state == equity_state == per_share_state == "available" else ("partial" if "available" in {enterprise_state, equity_state, per_share_state} else "withheld")
    return HtmlBriefDcfBridge(state, enterprise_state, equity_state, per_share_state, explicit_state, displayed_projected, displayed_discounted, explicit, terminal, discounted_terminal, enterprise, cash, debt, net_debt, equity if equity_state == "available" else None, shares if per_share_state == "available" else None, "Shares outstanding used by existing model", "unverified", per_share if per_share_state == "available" else None, currency, tuple(blockers))


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
    return {key: found.get(key, _scenario_from_raw(key.title(), {}, currency)) for key in ("bear", "base", "bull")}


def _accepted_scenario(result: ScenarioLabResult | None, ticker: str, profile_key: str) -> bool:
    return bool(result and ticker and result.status == "calculated" and _ticker_matches(result.ticker, ticker) and _profile_matches(result.profile_key, profile_key) and str(result.input_identity or "").strip() and result.changed_assumptions and result.scenario_result is not None)


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
    if record is None or not _ticker_matches(record.scope, ticker):
        return _section("recency", "Recency", "withheld", "No matching selected-ticker observation.", blockers=("Selected-ticker observation is unavailable or mismatched.",))
    return _section("recency", "Recency", record.state, record.message, (("Through date", record.through_date), ("Age days", record.age_days), ("Policy days", inputs.observation_recency.policy_days), ("Evaluation as of", inputs.observation_recency.as_of)))


def _nowcast_lanes(packet: Mapping[str, object] | None, report: Mapping[str, object], ticker: str, generated_at: str, review_cutoff: str) -> tuple[HtmlBriefSection, HtmlBriefSection, HtmlBriefSection]:
    withheld = ("Matching source-backed point-in-time nowcast evidence is unavailable.",)
    if not packet or not _ticker_matches(packet.get("ticker"), ticker) or str(packet.get("fiscal_period") or "") != str(_mapping(report.get("earnings_summary")).get("fiscal_period") or "") or not str(_mapping(report.get("earnings_summary")).get("fiscal_period") or "") or packet.get("evidence_scope") != "source_backed_preview_only":
        return tuple(_section(key, title, "withheld", "No portable nowcast evidence.", blockers=withheld) for key, title in (("consensus", "Consensus"), ("backtesting", "Backtesting"), ("calibration", "Calibration")))  # type: ignore[return-value]
    packet_at = _iso_datetime(packet.get("as_of_timestamp"))
    boundaries = tuple(
        parsed
        for value in (generated_at, review_cutoff)
        if (parsed := _iso_datetime(value)) is not None
    )
    if packet_at is None or not boundaries or any(packet_at > boundary for boundary in boundaries):
        return tuple(_section(key, title, "withheld", "No portable nowcast evidence.", blockers=withheld) for key, title in (("consensus", "Consensus"), ("backtesting", "Backtesting"), ("calibration", "Calibration")))  # type: ignore[return-value]
    readiness = _mapping(packet.get("readiness"))
    consensus_state = "partial" if readiness.get("consensus_ready") is True else "withheld"
    provenance = "portable nowcast provenance incomplete"
    backtest_verdict = safe_html_brief_text(packet.get("backtest_verdict"))
    backtest_count = _finite(packet.get("backtest_count"))
    calibration_state = normalize_html_brief_state(packet.get("calibration_state"))
    calibration_count = _finite(packet.get("event_count"))
    calibration_gates = packet.get("gates")
    backtest_state = (
        "partial"
        if backtest_verdict and backtest_verdict != _WITHHELD_ACTION and backtest_count is not None
        else "withheld"
    )
    calibration_lane_state = "partial" if calibration_state in {"available", "partial", "stale"} and calibration_count is not None and isinstance(calibration_gates, (tuple, list)) else "withheld"
    return (
        _section("consensus", "Consensus", consensus_state, "Source-backed preview is present; portable provenance remains incomplete.", blockers=(provenance,) if consensus_state == "partial" else ("Consensus readiness is not explicitly true.",)),
        _section("backtesting", "Backtesting", backtest_state, "Point-in-time preview verdict is not portable as complete evidence." if backtest_state == "partial" else "No portable backtesting diagnostics.", blockers=(provenance,) if backtest_state == "partial" else ("Backtesting verdict and count are required.",)),
        _section("calibration", "Calibration", calibration_lane_state, "Point-in-time preview calibration is not portable as complete evidence." if calibration_lane_state == "partial" else "No portable calibration diagnostics.", blockers=(provenance,) if calibration_lane_state == "partial" else ("Calibration state, event count, and gates are required.",)),
    )


def _readiness(inputs: CompanyWorkbenchHtmlInputs, ticker: str, bridge: HtmlBriefDcfBridge, generated_at: str, review_cutoff: str) -> tuple[HtmlBriefSection, ...]:
    trend = inputs.quarterly_trend if _ticker_matches(inputs.quarterly_trend.ticker, ticker) else None
    forward = inputs.forward_view if _ticker_matches(inputs.forward_view.ticker, ticker) else None
    quarterly_state = _portable_provenance_state(trend.status) if trend else "withheld"
    actual = _section("actuals", "Actuals", quarterly_state, trend.message if trend else "No matching quarterly evidence.", blockers=("portable provenance incomplete",) if trend else ("Quarterly ticker does not match report ticker.",))
    revenue_state = _portable_provenance_state(trend.revenue.status) if trend else "withheld"
    revenue = _section("revenue", "Revenue", revenue_state, trend.revenue.withheld_reason or "Quarterly revenue context." if trend else "No matching quarterly evidence.", blockers=("portable provenance incomplete", "Q4 requires explicit compatible quarterly evidence.") if trend else ("Quarterly ticker does not match report ticker.",))
    eps_state = _portable_provenance_state(trend.eps.status) if trend else "withheld"
    eps = _section("eps", "EPS", eps_state, trend.eps.withheld_reason or "Quarterly EPS context." if trend else "No matching quarterly evidence.", blockers=("portable provenance incomplete", "EPS split-basis proof is required.") if trend else ("Quarterly ticker does not match report ticker.",))
    valuation = _section("valuation", "Valuation", bridge.state, "Authoritative DCF bridge.", blockers=bridge.blockers)
    peers = _section("peers", "Peers", forward.peer_context.state if forward else "withheld", forward.peer_context.answer if forward else "No matching Forward View evidence.", blockers=() if forward else ("Forward View ticker does not match report ticker.",))
    historical = _section("historical-valuation", "Historical valuation", _portable_provenance_state(inputs.valuation_regime.state) if _ticker_matches(inputs.valuation_regime.ticker, ticker) else "withheld", inputs.valuation_regime.boundary if _ticker_matches(inputs.valuation_regime.ticker, ticker) else "No matching valuation regime.", blockers=("portable provenance incomplete",))
    catalyst_matches = _catalyst_matches(inputs.catalyst_timeline, ticker, inputs.profile_context.profile_key)
    catalysts = _section("catalysts", "Catalysts", inputs.catalyst_timeline.state if catalyst_matches else "withheld", inputs.catalyst_timeline.boundary if catalyst_matches else "No matching catalyst evidence.", blockers=() if catalyst_matches else ("Catalyst event scope does not match report scope.",))
    consensus, backtesting, calibration = _nowcast_lanes(inputs.nowcast_packet, inputs.report_payload, ticker, generated_at, review_cutoff)
    outcome = _section("outcomes", "Outcomes", "withheld", "No portable outcome evidence.", blockers=("portable outcome scope and provenance incomplete",))
    return (actual, consensus, revenue, eps, valuation, peers, historical, catalysts, outcome, backtesting, calibration)


def _research_sections(inputs: CompanyWorkbenchHtmlInputs, ticker: str) -> tuple[HtmlBriefSection, ...]:
    trend = inputs.quarterly_trend if _ticker_matches(inputs.quarterly_trend.ticker, ticker) else None
    forward = inputs.forward_view if _ticker_matches(inputs.forward_view.ticker, ticker) else None
    report = inputs.report_payload
    risks = _mapping(report.get("risk_summary"))
    catalyst_matches = _catalyst_matches(inputs.catalyst_timeline, ticker, inputs.profile_context.profile_key)
    return (
        _section("business-trend", "Business trend", _portable_provenance_state(trend.status) if trend else "withheld", trend.message if trend else "No matching quarterly business trend.", blockers=("portable provenance incomplete",)),
        _section("key-drivers", "Key drivers", forward.thesis_context.state if forward else "withheld", forward.thesis_context.answer if forward else "No matching Forward View evidence."),
        _section("risks", "Risks", risks.get("state", "withheld"), risks.get("summary", "No portable risk evidence.")),
        _section("catalysts", "Catalysts", inputs.catalyst_timeline.state if catalyst_matches else "withheld", inputs.catalyst_timeline.boundary if catalyst_matches else "No matching catalyst evidence.", blockers=() if catalyst_matches else ("Catalyst event scope does not match report scope.",)),
        _section("evidence-gaps", "Evidence gaps", "withheld", "Portable evidence remains incomplete."),
        _section("valuation-regime", "Valuation regime", _portable_provenance_state(inputs.valuation_regime.state) if _ticker_matches(inputs.valuation_regime.ticker, ticker) else "withheld", inputs.valuation_regime.boundary if _ticker_matches(inputs.valuation_regime.ticker, ticker) else "No matching valuation regime.", blockers=("portable provenance incomplete",)),
    )


def _portable_provenance_state(value: object) -> str:
    state = normalize_html_brief_state(value)
    return "partial" if state in {"available", "partial", "stale"} else "withheld"


def _catalyst_matches(timeline: CatalystTimeline, ticker: str, profile_key: str) -> bool:
    if not _ticker_matches(timeline.ticker, ticker):
        return False
    events = tuple(timeline.upcoming) + tuple(timeline.recent)
    return bool(events) and all(
        _ticker_matches(event.ticker, ticker) and _profile_matches(event.profile_key, profile_key)
        for event in events
    )


def _decision_lanes(state: ResearchDecisionLabState, ticker: str, profile_key: str) -> tuple[HtmlBriefSection, ...]:
    by_key = {lane.key: lane for lane in state.lanes} if _ticker_matches(state.ticker, ticker) and _profile_matches(state.profile_key, profile_key) else {}
    ordered = (("plan", "Plan"), ("evidence", "Evidence"), ("invalidation", "Invalidation"), ("scenario", "Scenario"), ("review-trigger", "Review trigger"), ("learning", "Learning"))
    output: list[HtmlBriefSection] = []
    for output_key, title in ordered:
        lane = by_key.get(output_key.replace("-", "_"))
        output.append(_section(output_key, title, lane.state if lane else "withheld", lane.answer if lane else "No matching Decision Lab evidence.", blockers=() if lane else ("Decision Lab scope does not match report scope.",)))
    return tuple(output)


def _evidence_rows(inputs: CompanyWorkbenchHtmlInputs, accepted_scenario: bool) -> tuple[HtmlBriefEvidenceRow, ...]:
    candidates: list[tuple[str, object, str]] = []
    ticker = _ticker(inputs.report_payload.get("ticker"))
    if not ticker:
        return ()
    provenance = _mapping(inputs.report_payload.get("provenance"))
    for row in provenance.get("source_records", ()) if isinstance(provenance.get("source_records"), (list, tuple)) else ():
        candidates.append(("report", row, ""))
    valuation = _mapping(inputs.report_payload.get("valuation_snapshot"))
    for row in valuation.get("source_metadata", ()) if isinstance(valuation.get("source_metadata"), (list, tuple)) else ():
        candidates.append(("valuation", row, ""))
    if accepted_scenario and inputs.scenario_lab_result:
        for row in inputs.scenario_lab_result.source_metadata:
            candidates.append(("scenario", row, inputs.scenario_lab_result.input_identity))
    journal = inputs.journal_state
    if journal and _profile_matches(journal.profile_key, inputs.profile_context.profile_key) and _ticker_matches(journal.ticker, ticker):
        for entry in journal.entries:
            if _profile_matches(entry.profile_key, inputs.profile_context.profile_key) and _ticker_matches(entry.ticker, ticker):
                candidates.append(("journal", entry, ""))
    timeline = inputs.catalyst_timeline
    if _catalyst_matches(timeline, ticker, inputs.profile_context.profile_key):
        for event in tuple(timeline.upcoming) + tuple(timeline.recent):
            candidates.append(("catalyst", event, ""))
    rows: list[HtmlBriefEvidenceRow] = []
    for section, raw, identity in candidates:
        item = _record_mapping(raw)
        source_id = safe_html_brief_text(item.get("source_id") or item.get("source") or "")
        ref = safe_html_brief_reference(item)
        as_of = _iso(item.get("as_of") or item.get("as_of_date") or item.get("published_at") or item.get("source_published_at"))
        retrieved = _iso(item.get("retrieved_at"))
        rights = str(item.get("rights_state") or "").strip().lower()
        scope = str(item.get("field_scope_state") or "").strip().lower()
        rights_state = "permitted" if rights == "permitted" else ("not_applicable" if rights == "not_applicable" else "unverified")
        scope_state = "permitted" if scope == "permitted" else ("not_applicable" if scope == "not_applicable" else "unverified")
        complete = bool(source_id and ref.href and as_of and retrieved)
        state = "available" if complete and rights_state == scope_state == "permitted" else "withheld"
        blockers = () if state == "available" else tuple(item for item in (
            "Portable source identity, reference, as-of timestamp, or retrieval timestamp is incomplete." if not complete else "",
            "Portable rights or field-scope provenance is incomplete." if rights_state != "permitted" or scope_state != "permitted" else "",
        ) if item)
        row = HtmlBriefEvidenceRow(section, state, source_id, ref, as_of, retrieved, rights_state, scope_state, _clean_text(item.get("model_identity"), "not recorded"), _clean_text(identity, "not recorded"), blockers)
        if row not in rows:
            rows.append(row)
    return tuple(rows)


def _rights_state(rows: tuple[HtmlBriefEvidenceRow, ...]) -> str:
    if not rows:
        return "withheld"
    if all(row.rights_state == "not_applicable" and row.field_scope_state == "not_applicable" for row in rows):
        return "excluded"
    return "available" if all(row.state == "available" and row.rights_state == "permitted" and row.field_scope_state == "permitted" for row in rows) else "withheld"


def build_company_workbench_html_snapshot(inputs: CompanyWorkbenchHtmlInputs) -> CompanyWorkbenchHtmlSnapshot:
    """Build only from supplied objects; this function performs no I/O or refresh work."""
    report = _mapping(inputs.report_payload)
    ticker = _ticker(report.get("ticker"))
    generated_at = _iso(report.get("generated_at")) or "not recorded"
    forward_cutoff = _iso(inputs.forward_view.source_cutoff) if _ticker_matches(inputs.forward_view.ticker, ticker) else ""
    review_cutoff = forward_cutoff or (_iso(generated_at) if generated_at != "not recorded" else "") or _iso(inputs.profile_context.source_as_of) or "not recorded"
    provenance = _mapping(report.get("provenance"))
    model_version = _clean_text(report.get("method_version") or provenance.get("method_version"), "not recorded")
    financial = _mapping(report.get("financial_summary"))
    currency = _clean_text(financial.get("currency") or _mapping(report.get("price_snapshot")).get("currency"), "not recorded")
    scope_blockers: list[str] = []
    selected_matches = _ticker_matches(inputs.selected_answer.get("Ticker"), ticker)
    if not selected_matches:
        scope_blockers.append("Selected answer ticker does not match report ticker.")
    canonical = _canonical_scenarios(_mapping(report.get("valuation_snapshot")) if ticker else {}, currency)
    accepted = _accepted_scenario(inputs.scenario_lab_result, ticker, inputs.profile_context.profile_key)
    if inputs.scenario_lab_result and not accepted:
        scope_blockers.append("Scenario Lab result is not an accepted matching changed calculation.")
    if accepted and inputs.scenario_lab_result:
        canonical["base"] = _scenario_from_raw("Base", inputs.scenario_lab_result.scenario_result, currency, modified=True, params=inputs.scenario_lab_result.scenario_parameters)
    scenarios = tuple(canonical[name] for name in ("bear", "base", "bull"))
    sensitivity_table = inputs.scenario_lab_result.sensitivity_table if accepted and inputs.scenario_lab_result else _mapping(report.get("valuation_snapshot")).get("sensitivity_table")
    sensitivity = _sensitivity(sensitivity_table, canonical["base"].bridge)
    selected_state = inputs.selected_answer.get("state", "withheld") if selected_matches else "withheld"
    selected_use_now = _clean_text(inputs.selected_answer.get("Use Now"), "No portable answer.") if selected_matches else "No portable answer."
    selected_blocked = _clean_text(inputs.selected_answer.get("Still Blocked"), "No portable blocker.") if selected_matches else "No portable blocker."
    answers = (
        HtmlBriefAnswer("Use now", "Use now", selected_use_now, normalize_html_brief_state(selected_state), ()),
        HtmlBriefAnswer("Still withheld", "Still withheld", selected_blocked, "withheld", ()),
        _portable_change_answer(inputs, ticker),
        HtmlBriefAnswer("Next research task", _clean_text(inputs.authoritative_task.get("title"), "Next research task"), _clean_text(inputs.authoritative_task.get("body"), "No portable task."), normalize_html_brief_state(inputs.authoritative_task.get("state")), tuple(safe_html_brief_text(item) for item in inputs.authoritative_task.get("badges", ()) if safe_html_brief_text(item)) if isinstance(inputs.authoritative_task.get("badges"), (list, tuple)) else ()),
    )
    evidence = _evidence_rows(inputs, accepted)
    freshness = normalize_html_brief_state(inputs.observation_recency.selected_ticker.state) if inputs.observation_recency and _ticker_matches(inputs.observation_recency.selected_ticker.scope, ticker) else normalize_html_brief_state(inputs.profile_context.freshness_state)
    snapshot = CompanyWorkbenchHtmlSnapshot(ticker, _clean_text(inputs.profile_context.profile_label), review_cutoff, _clean_text(inputs.profile_context.source_as_of), generated_at, model_version, freshness, _rights_state(evidence), "Research-only, fail-closed portable brief; no recommendation, probability, or transaction action.", answers, _recency(inputs, ticker), _readiness(inputs, ticker, canonical["base"].bridge, generated_at, review_cutoff), scenarios, sensitivity, _research_sections(inputs, ticker), _decision_lanes(inputs.decision_lab_state, ticker, inputs.profile_context.profile_key), evidence, tuple(scope_blockers), "")
    payload = json.dumps(asdict(snapshot), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return replace(snapshot, identity=hashlib.sha256(payload.encode("utf-8")).hexdigest())


def company_workbench_html_filename(snapshot: CompanyWorkbenchHtmlSnapshot) -> str:
    ticker = _ticker(snapshot.ticker) or "UNKNOWN"
    date = _date_part(snapshot.review_cutoff) or _date_part(snapshot.generated_at) or "undated"
    return f"{ticker}-{date}-research-brief.html"


@dataclass(frozen=True)
class HtmlBriefDownloadSpec:
    """Pure download metadata for an already-rendered offline research brief."""

    data: bytes
    file_name: str
    mime: str


_HTML_BRIEF_STATE_LABELS = {
    "available": "complete",
    "partial": "partial",
    "withheld": "withheld",
    "stale": "stale",
    "not_recorded": "not recorded",
    "excluded": "excluded",
}
_HTML_BRIEF_CSP = "default-src 'none'; script-src 'none'; connect-src 'none'; img-src 'none'; style-src 'unsafe-inline'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"


def _html_brief_text(value: object, fallback: str = "not recorded") -> str:
    """Canonicalize an already-sanitized snapshot value for a markup context."""
    if not isinstance(value, (str, int, float, bool)):
        return fallback
    # Snapshot construction stores escaped text. Unescaping before its final escape
    # preserves ordinary text while also safely handling a manually-constructed snapshot.
    return safe_html_brief_text(html.unescape(str(value))) or fallback


def _html_brief_state(value: object) -> tuple[str, str]:
    state = normalize_html_brief_state(value)
    return state, _HTML_BRIEF_STATE_LABELS[state]


def format_html_brief_number(value: object, *, currency: str = "", percent: bool = False) -> str:
    """Format a recorded finite value without deriving any valuation value."""
    if value is None or value == "":
        return "not recorded"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "not recorded"
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("HTML brief values must be finite before rendering")
    if percent:
        return f"{number * 100:.1f}%"
    rendered = f"{number:,.2f}"
    currency_label = _html_brief_text(currency, "") if currency else ""
    return f"{currency_label} {rendered}".strip()


def _html_brief_css(root: str) -> str:
    return f"""
{root} {{ color: #18222e; background: #ffffff; font-family: system-ui, sans-serif; line-height: 1.5; }}
{root} *, {root} *::before, {root} *::after {{ box-sizing: border-box; }}
{root} .srcc-brief-shell {{ max-width: 1120px; margin: 0 auto; padding: 1.5rem; }}
{root} .srcc-brief-title {{ margin: 0; font-size: 1.7rem; }}
{root} .srcc-brief-subtitle, {root} .srcc-boundary {{ margin: .45rem 0; }}
{root} .srcc-boundary {{ border-inline-start: .35rem solid #305f83; padding-inline-start: .75rem; font-weight: 650; }}
{root} .srcc-section {{ border: 1px solid #99a8b7; border-radius: .45rem; margin-top: 1rem; padding: 1rem; }}
{root} .srcc-section > h2, {root} .srcc-section > h3 {{ margin-top: 0; }}
{root} .srcc-card-grid {{ display: grid; gap: .75rem; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); }}
{root} .srcc-card {{ border: 1px solid #99a8b7; border-radius: .35rem; padding: .75rem; }}
{root} .srcc-state {{ border-inline-start: .35rem solid #495762; font-weight: 700; padding-inline-start: .45rem; text-transform: capitalize; }}
{root} .srcc-state-available {{ border-color: #176b46; }}
{root} .srcc-state-partial {{ border-color: #9a6700; }}
{root} .srcc-state-withheld {{ border-color: #9d2020; }}
{root} .srcc-state-stale {{ border-color: #6547a5; }}
{root} .srcc-state-not_recorded {{ border-color: #495762; }}
{root} .srcc-state-excluded {{ border-color: #396c91; }}
{root} .srcc-meta {{ display: grid; gap: .35rem; grid-template-columns: max-content 1fr; }}
{root} .srcc-meta dt {{ font-weight: 700; }}
{root} .srcc-meta dd {{ margin: 0; overflow-wrap: anywhere; }}
{root} .table-scroll {{ overflow-x: auto; }}
{root} .srcc-table {{ border-collapse: collapse; min-width: 38rem; width: 100%; }}
{root} .srcc-table th, {root} .srcc-table td {{ border: 1px solid #99a8b7; padding: .45rem; text-align: left; vertical-align: top; }}
{root} .srcc-table caption {{ caption-side: top; font-weight: 700; padding-bottom: .45rem; text-align: left; }}
{root} a {{ color: #075a9c; overflow-wrap: anywhere; }}
{root} :focus-visible {{ outline: .2rem solid #d04a00; outline-offset: .15rem; }}
{root} .srcc-blockers {{ margin-bottom: 0; }}
{root} .srcc-skip-link {{ background: #ffffff; left: .5rem; padding: .5rem; position: absolute; top: -4rem; }}
{root} .srcc-skip-link:focus-visible {{ top: .5rem; }}
@media (max-width: 700px) {{
  {root} .srcc-brief-shell {{ padding: .75rem; }}
  {root} .srcc-card-grid {{ grid-template-columns: 1fr; }}
  {root} .srcc-meta {{ grid-template-columns: 1fr; }}
  {root} .srcc-table {{ min-width: 32rem; }}
}}
@media (forced-colors: active) {{
  {root} .srcc-section, {root} .srcc-card, {root} .srcc-table th, {root} .srcc-table td {{ border-color: CanvasText; }}
  {root} .srcc-state, {root} .srcc-boundary {{ border-color: CanvasText; }}
}}
@media (prefers-reduced-motion: reduce) {{
  {root} *, {root} *::before, {root} *::after {{ animation-duration: .01ms !important; scroll-behavior: auto !important; transition-duration: .01ms !important; }}
}}
@media print {{
  {root} {{ background: #ffffff; color: #000000; }}
  {root} .srcc-skip-link {{ display: none; }}
  {root} .srcc-section, {root} .srcc-card {{ break-inside: avoid; }}
  {root} .srcc-advanced-evidence, {root} .srcc-boundary {{ display: block; }}
}}
{root} .srcc-one-pager {{
  color: #f8fafc !important;
  background: #0b1b2b;
  border-top: .35rem solid #f59e0b;
  padding: 1.25rem;
}}
{root} .srcc-one-pager * {{ color: #f8fafc !important; }}
{root} .srcc-one-pager-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: #64748b;
}}
{root} .srcc-one-pager-card {{
  min-width: 0;
  background: #0b1b2b;
  padding: 1rem;
}}
{root} .srcc-one-pager-scenarios {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
  list-style: none;
  margin: 0;
  padding: 0;
}}
{root} .srcc-one-pager a {{ color: #67e8f9 !important; }}
{root} .srcc-one-pager .srcc-boundary {{ border-color: #60a5fa; }}
{root} .srcc-one-pager .srcc-state-available {{ border-color: #34d399; }}
{root} .srcc-one-pager .srcc-state-partial {{ border-color: #fbbf24; }}
{root} .srcc-one-pager .srcc-state-withheld {{ border-color: #f87171; }}
{root} .srcc-one-pager .srcc-state-stale {{ border-color: #c4b5fd; }}
{root} .srcc-one-pager .srcc-state-not_recorded {{ border-color: #94a3b8; }}
{root} .srcc-one-pager .srcc-state-excluded {{ border-color: #7dd3fc; }}
{root} .srcc-one-pager .table-scroll {{ overflow: visible; }}
{root} .srcc-one-pager .srcc-table {{
  min-width: 0;
  table-layout: fixed;
  width: 100%;
}}
{root} .srcc-one-pager .srcc-table th,
{root} .srcc-one-pager .srcc-table td {{ overflow-wrap: anywhere; }}
@media (max-width: 640px) {{
  {root} .srcc-one-pager-grid,
  {root} .srcc-one-pager-scenarios {{ grid-template-columns: 1fr; }}
}}
@media (forced-colors: active) {{
  {root} .srcc-one-pager,
  {root} .srcc-one-pager-card {{ border: 1px solid CanvasText; }}
}}
@media print {{
  {root} .srcc-one-pager {{
    color: #000 !important;
    background: #fff !important;
    border-color: #000 !important;
    break-inside: auto;
  }}
  {root} .srcc-one-pager * {{ color: #000 !important; }}
  {root} .srcc-one-pager-grid {{ background: #000 !important; }}
  {root} .srcc-one-pager-card {{ background: #fff !important; }}
  {root} .srcc-one-pager .srcc-state,
  {root} .srcc-one-pager .srcc-boundary,
  {root} .srcc-one-pager [data-section='one-pager-provenance'],
  {root} .srcc-one-pager .srcc-table th,
  {root} .srcc-one-pager .srcc-table td,
  {root} .srcc-one-pager .srcc-card,
  {root} .srcc-one-pager-card {{
    border-color: #000 !important;
  }}
  {root} .srcc-one-pager a {{
    color: #000 !important;
    text-decoration: underline !important;
  }}
}}
""".strip()


def _html_brief_state_markup(state: object) -> str:
    normalized, label = _html_brief_state(state)
    return f'<p class="srcc-state srcc-state-{normalized}">State: {label}</p>'


def _html_brief_blockers(blockers: tuple[str, ...]) -> str:
    if not blockers:
        return ""
    rows = "".join(f"<li>{_html_brief_text(item)}</li>" for item in blockers)
    return f'<ul class="srcc-blockers"><li>Blockers</li><li><ul>{rows}</ul></li></ul>'


def _html_brief_section_card(section: HtmlBriefSection) -> str:
    facts = ""
    if section.facts:
        facts = '<dl class="srcc-meta">' + "".join(
            f"<dt>{_html_brief_text(label)}</dt><dd>{_html_brief_text(value)}</dd>" for label, value in section.facts
        ) + "</dl>"
    return (
        '<article class="srcc-card">'
        f"<h3>{_html_brief_text(section.title)}</h3>"
        f"{_html_brief_state_markup(section.state)}"
        f"<p>{_html_brief_text(section.answer, 'No portable evidence recorded.')}</p>"
        f"{facts}{_html_brief_blockers(section.blockers)}"
        "</article>"
    )


def _html_brief_section_cards(sections: tuple[HtmlBriefSection, ...]) -> str:
    return '<div class="srcc-card-grid">' + "".join(_html_brief_section_card(section) for section in sections) + "</div>"


def _html_brief_reference_markup(reference: HtmlBriefSafeReference) -> str:
    safe = safe_html_brief_reference({"label": html.unescape(str(reference.label)), "href": reference.href})
    label = safe.label or "not recorded"
    if safe.href:
        return f'<a href="{html.escape(safe.href, quote=True)}" rel="noreferrer noopener">{label}</a>'
    return label


def _section_by_key(
    sections: tuple[HtmlBriefSection, ...],
    key: str,
) -> HtmlBriefSection | None:
    return next((section for section in sections if section.key == key), None)


def _answer_by_label(
    answers: tuple[HtmlBriefAnswer, ...],
    label: str,
) -> HtmlBriefAnswer | None:
    return next((answer for answer in answers if answer.label == label), None)


def _html_one_pager_role(*parts: object) -> str:
    tokens = tuple(
        token
        for part in parts
        for token in re.findall(r"[a-z0-9]+", str(part or "").lower())
    )
    return "-".join(tokens)[:120] or "one-pager-unavailable"


def _html_one_pager_state_attributes(state: object, role: str) -> str:
    normalized, _ = _html_brief_state(state)
    return (
        f'data-state="{normalized}" '
        f'data-state-role="{html.escape(role, quote=True)}"'
    )


def _html_one_pager_references(
    references: tuple[HtmlBriefSafeReference, ...],
) -> str:
    if not references:
        return ""
    items = "".join(
        f"<li>{_html_brief_reference_markup(reference)}</li>"
        for reference in references
    )
    return f"<p>Source references</p><ul>{items}</ul>"


def _html_one_pager_unavailable_section() -> HtmlBriefSection:
    return HtmlBriefSection(
        key="unavailable",
        title="Not recorded",
        state="not_recorded",
        answer="No portable evidence is recorded for this section.",
        facts=(),
        blockers=("The frozen snapshot does not contain this section.",),
    )


def _html_one_pager_section_card(
    section: HtmlBriefSection | None,
    *,
    role: str,
    heading: str,
) -> str:
    selected = section or _html_one_pager_unavailable_section()
    facts = ""
    if selected.facts:
        facts = '<dl class="srcc-meta">' + "".join(
            f"<dt>{_html_brief_text(label)}</dt><dd>{_html_brief_text(value)}</dd>"
            for label, value in selected.facts
        ) + "</dl>"
    return (
        '<article class="srcc-one-pager-card srcc-card" '
        f'{_html_one_pager_state_attributes(selected.state, role)}>'
        f"<{heading}>{_html_brief_text(selected.title)}</{heading}>"
        f"{_html_brief_state_markup(selected.state)}"
        f"<p>{_html_brief_text(selected.answer, 'No portable evidence recorded.')}</p>"
        f"{facts}{_html_brief_blockers(selected.blockers)}"
        "</article>"
    )


def _html_one_pager_answer_card(
    answer: HtmlBriefAnswer,
    *,
    role: str,
    heading: str,
    answer_item: bool = False,
    container: str = "li",
) -> str:
    item_attribute = ' data-answer-item=""' if answer_item else ""
    return (
        f'<{container} class="srcc-one-pager-card srcc-card"'
        f'{item_attribute} {_html_one_pager_state_attributes(answer.state, role)}>'
        f"<{heading}>{_html_brief_text(answer.label)}</{heading}>"
        f"{_html_brief_state_markup(answer.state)}"
        f"<p>{_html_brief_text(answer.title, 'No portable answer.')}</p>"
        f"<p>{_html_brief_text(answer.body, 'No portable answer.')}</p>"
        f"{_html_one_pager_references(answer.source_refs)}"
        f"{_html_brief_blockers(answer.blockers)}"
        f"</{container}>"
    )


def _html_one_pager_numeric_display(
    value: object,
    state: object,
    *,
    currency: str = "",
) -> tuple[str, str | None]:
    normalized = normalize_html_brief_state(state)
    if normalized != "available":
        return normalized, None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "withheld", None
    if not math.isfinite(float(value)):
        return "withheld", None
    return normalized, format_html_brief_number(value, currency=currency)


def _html_one_pager_share_basis(
    state: object,
    *,
    role: str,
) -> str:
    supplied = _html_brief_text(state, "not recorded")
    return (
        '<p class="srcc-boundary" '
        f'data-share-basis-role="{html.escape(role, quote=True)}" '
        f'data-share-basis-state="{html.escape(html.unescape(supplied), quote=True)}">'
        f"Share basis state: {supplied}</p>"
    )


def _html_evidence_one_pager(
    snapshot: CompanyWorkbenchHtmlSnapshot,
    heading_level: int,
) -> str:
    """Project a summary from an already-frozen snapshot without side effects."""
    level = max(1, min(6, int(heading_level)))
    heading = f"h{level}"
    section_heading = f"h{min(6, level + 1)}"
    card_heading = f"h{min(6, level + 2)}"

    header_state_rows = "".join(
        '<div class="srcc-one-pager-card" '
        f'{_html_one_pager_state_attributes(state, _html_one_pager_role("header", field))}>'
        f"<p>{_html_brief_text(label)}</p>{_html_brief_state_markup(state)}</div>"
        for field, label, state in (
            ("freshness-state", "Freshness", snapshot.freshness_state),
            ("rights-state", "Rights", snapshot.rights_state),
        )
    )
    header = (
        '<header data-section="one-pager-header">'
        '<p>Saved evidence snapshot</p>'
        f'<{heading} id="evidence-one-pager-title">'
        f"{_html_brief_text(snapshot.ticker, 'Research')} Evidence One-Pager"
        f"</{heading}>"
        '<dl class="srcc-meta">'
        f"<dt>Ticker</dt><dd>{_html_brief_text(snapshot.ticker)}</dd>"
        f"<dt>Review cutoff</dt><dd>{_html_brief_text(snapshot.review_cutoff)}</dd>"
        f"<dt>Source as of</dt><dd>{_html_brief_text(snapshot.source_as_of)}</dd>"
        f"<dt>Model version</dt><dd>{_html_brief_text(snapshot.model_version)}</dd>"
        f"<dt>Snapshot identity</dt><dd>{_html_brief_text(snapshot.identity)}</dd>"
        "</dl>"
        f'<div class="srcc-one-pager-grid">{header_state_rows}</div>'
        f'<p class="srcc-boundary">{_html_brief_text(snapshot.boundary)}</p>'
        f"{_html_brief_blockers(snapshot.blockers)}"
        "</header>"
    )

    answer_items = "".join(
        _html_one_pager_answer_card(
            answer,
            role=_html_one_pager_role("answers", answer.label),
            heading=card_heading,
            answer_item=True,
        )
        for answer in snapshot.answers
    )
    answers = (
        '<section data-section="one-pager-answers">'
        f"<{section_heading}>Company Brief</{section_heading}>"
        f'<ol class="srcc-one-pager-grid">{answer_items}</ol>'
        "</section>"
    )

    scenario_items = []
    for scenario in snapshot.scenarios:
        scenario_role = _html_one_pager_role("scenarios", scenario.name)
        value_role = _html_one_pager_role("scenarios", scenario.name, "value-per-share")
        value_state, value = _html_one_pager_numeric_display(
            scenario.bridge.scenario_value_per_share,
            scenario.bridge.per_share_state,
            currency=scenario.bridge.currency,
        )
        value_copy = f"Scenario value: {value}" if value is not None else "Scenario value withheld"
        scenario_items.append(
            '<li class="srcc-one-pager-card srcc-card" data-scenario-item="" '
            f'{_html_one_pager_state_attributes(scenario.state, scenario_role)}>'
            f"<{card_heading}>{_html_brief_text(scenario.name)}</{card_heading}>"
            f"{_html_brief_state_markup(scenario.state)}"
            f"<p>{'Modified Base assumptions' if scenario.modified else 'Recorded assumptions'}</p>"
            '<dl class="srcc-meta">'
            f"<dt>Method</dt><dd>{_html_brief_text(scenario.method_name)}</dd>"
            f"<dt>Revenue growth</dt><dd>{format_html_brief_number(scenario.revenue_growth, percent=True)}</dd>"
            f"<dt>FCF margin</dt><dd>{format_html_brief_number(scenario.fcf_margin, percent=True)}</dd>"
            f"<dt>WACC</dt><dd>{format_html_brief_number(scenario.wacc, percent=True)}</dd>"
            f"<dt>Terminal growth</dt><dd>{format_html_brief_number(scenario.terminal_growth, percent=True)}</dd>"
            f"<dt>Forecast years</dt><dd>{format_html_brief_number(scenario.forecast_years)}</dd>"
            "</dl>"
            '<div class="srcc-card" '
            f'{_html_one_pager_state_attributes(value_state, value_role)}>'
            f"<p>{value_copy}</p>{_html_brief_state_markup(value_state)}</div>"
            f"{_html_one_pager_share_basis(scenario.bridge.share_basis_state, role=_html_one_pager_role('scenarios', scenario.name, 'share-basis'))}"
            f"{_html_brief_blockers(scenario.bridge.blockers)}"
            "</li>"
        )
    scenarios = (
        '<section data-section="one-pager-scenarios">'
        f"<{section_heading}>Scenarios under assumptions</{section_heading}>"
        f'<ol class="srcc-one-pager-scenarios">{"".join(scenario_items)}</ol>'
        "</section>"
    )

    research_case_sources = (
        ("decision", "plan", _section_by_key(snapshot.decision_lanes, "plan")),
        ("decision", "evidence", _section_by_key(snapshot.decision_lanes, "evidence")),
        ("research", "business-trend", _section_by_key(snapshot.research_sections, "business-trend")),
        ("research", "key-drivers", _section_by_key(snapshot.research_sections, "key-drivers")),
    )
    research_case_cards = "".join(
        _html_one_pager_section_card(
            section,
            role=_html_one_pager_role("research-case", source, key),
            heading=card_heading,
        )
        for source, key, section in research_case_sources
    )
    research_case = (
        '<section data-section="one-pager-research-case">'
        f"<{section_heading}>Research case</{section_heading}>"
        f'<div class="srcc-one-pager-grid">{research_case_cards}</div>'
        "</section>"
    )

    operating_sources = tuple(
        (key, _section_by_key(snapshot.research_sections, key))
        for key in ("business-trend", "key-drivers", "valuation-regime")
    )
    operating_cards = "".join(
        _html_one_pager_section_card(
            section,
            role=_html_one_pager_role("operating-valuation", "research", key),
            heading=card_heading,
        )
        for key, section in operating_sources
    )
    base = next((scenario for scenario in snapshot.scenarios if scenario.name == "Base"), None)
    if base is None:
        bridge_markup = _html_one_pager_section_card(
            None,
            role=_html_one_pager_role("operating-valuation", "base-bridge"),
            heading=card_heading,
        )
    else:
        bridge_values = (
            ("discounted-explicit-total", "Discounted explicit total", base.bridge.discounted_explicit_total, base.bridge.explicit_total_state),
            ("terminal-value", "Terminal value", base.bridge.terminal_value, base.bridge.enterprise_state),
            ("discounted-terminal-value", "Discounted terminal value", base.bridge.discounted_terminal_value, base.bridge.enterprise_state),
            ("enterprise-value", "Enterprise value", base.bridge.enterprise_value, base.bridge.enterprise_state),
            ("cash", "Cash", base.bridge.cash, base.bridge.equity_state),
            ("debt", "Debt", base.bridge.debt, base.bridge.equity_state),
            ("net-debt", "Net debt", base.bridge.net_debt, base.bridge.equity_state),
            ("equity-value", "Equity value", base.bridge.equity_value, base.bridge.equity_state),
            ("supplied-shares", base.bridge.shares_label, base.bridge.shares_outstanding, base.bridge.per_share_state),
            ("supplied-value-per-share", "Supplied value per share", base.bridge.scenario_value_per_share, base.bridge.per_share_state),
        )
        bridge_rows = []
        for key, label, value, state in bridge_values:
            value_state, displayed_value = _html_one_pager_numeric_display(
                value,
                state,
                currency="" if key == "supplied-shares" else base.bridge.currency,
            )
            bridge_rows.append(
                '<tr '
                f'{_html_one_pager_state_attributes(value_state, _html_one_pager_role("operating-valuation", "base-bridge", key))}>'
                f'<th scope="row">{_html_brief_text(label)}</th><td>'
                f"{displayed_value or 'withheld'}"
                f"{_html_brief_state_markup(value_state)}"
                f"{_html_brief_blockers(base.bridge.blockers)}</td></tr>"
            )
        bridge_markup = (
            '<div class="srcc-one-pager-card">'
            f"<{card_heading}>Supplied Base bridge values</{card_heading}>"
            '<div class="table-scroll"><table class="srcc-table">'
            "<caption>Supplied Base bridge values</caption>"
            "<thead><tr><th>Field</th><th>Recorded evidence</th></tr></thead>"
            f"<tbody>{''.join(bridge_rows)}</tbody></table></div>"
            f"{_html_one_pager_share_basis(base.bridge.share_basis_state, role=_html_one_pager_role('operating-valuation', 'base-bridge', 'share-basis'))}"
            "</div>"
        )
    operating = (
        '<section data-section="one-pager-operating-valuation">'
        f"<{section_heading}>Operating and valuation evidence</{section_heading}>"
        f'<div class="srcc-one-pager-grid">{operating_cards}</div>{bridge_markup}'
        "</section>"
    )

    break_sources = (
        ("research", "risks", _section_by_key(snapshot.research_sections, "risks")),
        ("decision", "invalidation", _section_by_key(snapshot.decision_lanes, "invalidation")),
    )
    break_cards = "".join(
        _html_one_pager_section_card(
            section,
            role=_html_one_pager_role("break-case", source, key),
            heading=card_heading,
        )
        for source, key, section in break_sources
    )
    break_case = (
        '<section data-section="one-pager-break-case">'
        f"<{section_heading}>What could break the research case</{section_heading}>"
        f'<div class="srcc-one-pager-grid">{break_cards}</div>'
        "</section>"
    )

    question_sections = (
        ("decision", "review-trigger", _section_by_key(snapshot.decision_lanes, "review-trigger")),
        ("research", "evidence-gaps", _section_by_key(snapshot.research_sections, "evidence-gaps")),
    )
    question_cards = "".join(
        _html_one_pager_section_card(
            section,
            role=_html_one_pager_role("questions", source, key),
            heading=card_heading,
        )
        for source, key, section in question_sections
    )
    next_task = _answer_by_label(snapshot.answers, "Next research task")
    if next_task is None:
        next_task = HtmlBriefAnswer(
            "Next research task",
            "Not recorded",
            "No portable evidence is recorded for this section.",
            "not_recorded",
            (),
            (),
            ("The frozen snapshot does not contain this section.",),
        )
    next_task_card = _html_one_pager_answer_card(
        next_task,
        role=_html_one_pager_role("questions", "answer", "next-research-task"),
        heading=card_heading,
        container="div",
    )
    questions = (
        '<section data-section="one-pager-questions">'
        f"<{section_heading}>Questions still requiring evidence</{section_heading}>"
        f'<div class="srcc-one-pager-grid">{question_cards}{next_task_card}</div>'
        "</section>"
    )

    provenance_top_states = "".join(
        '<div class="srcc-one-pager-card" '
        f'{_html_one_pager_state_attributes(state, _html_one_pager_role("provenance", field))}>'
        f"<p>{_html_brief_text(label)}</p>{_html_brief_state_markup(state)}</div>"
        for field, label, state in (
            ("freshness-state", "Freshness", snapshot.freshness_state),
            ("rights-state", "Rights", snapshot.rights_state),
        )
    )
    provenance_bodies = []
    for ordinal, row in enumerate(snapshot.evidence_rows, start=1):
        role = _html_one_pager_role(
            "provenance", "row", ordinal, row.section, row.source_id
        )
        fields = (
            ("State", _html_brief_state_markup(row.state)),
            ("Section", _html_brief_text(row.section)),
            ("Source ID", _html_brief_text(row.source_id)),
            ("Reference", _html_brief_reference_markup(row.source_ref)),
            ("As of", _html_brief_text(row.as_of)),
            ("Retrieved", _html_brief_text(row.retrieved_at)),
            ("Rights", _html_brief_text(row.rights_state)),
            ("Field scope", _html_brief_text(row.field_scope_state)),
            ("Model identity", _html_brief_text(row.model_identity)),
            ("Input identity", _html_brief_text(row.input_identity)),
            ("Blockers", _html_brief_blockers(row.blockers) or "None recorded"),
        )
        rows = "".join(
            f'<tr><th scope="row">{label}</th><td>{value}</td></tr>'
            for label, value in fields
        )
        provenance_bodies.append(
            f'<tbody {_html_one_pager_state_attributes(row.state, role)}>{rows}</tbody>'
        )
    if not provenance_bodies:
        unavailable = _html_one_pager_unavailable_section()
        provenance_bodies.append(
            '<tbody '
            f'{_html_one_pager_state_attributes(unavailable.state, _html_one_pager_role("provenance", "no-portable-evidence"))}>'
            '<tr><th scope="row">Evidence state</th><td>'
            f"{_html_brief_state_markup(unavailable.state)}"
            f"<p>{_html_brief_text(unavailable.answer)}</p>"
            f"{_html_brief_blockers(unavailable.blockers)}</td></tr></tbody>"
        )
    provenance = (
        '<aside class="srcc-one-pager-card" data-section="one-pager-provenance" '
        'aria-labelledby="evidence-one-pager-provenance-title">'
        f'<{section_heading} id="evidence-one-pager-provenance-title">'
        f"Provenance and boundaries</{section_heading}>"
        '<dl class="srcc-meta">'
        f"<dt>Model version</dt><dd>{_html_brief_text(snapshot.model_version)}</dd>"
        f"<dt>Snapshot identity</dt><dd>{_html_brief_text(snapshot.identity)}</dd>"
        f"<dt>Boundary</dt><dd>{_html_brief_text(snapshot.boundary)}</dd>"
        "</dl>"
        f'<div class="srcc-one-pager-grid">{provenance_top_states}</div>'
        '<div class="table-scroll"><table class="srcc-table">'
        "<caption>Portable evidence provenance</caption>"
        "<thead><tr><th>Field</th><th>Evidence</th></tr></thead>"
        f"{''.join(provenance_bodies)}</table></div>"
        "</aside>"
    )
    handoff = (
        '<section data-section="one-pager-handoff">'
        "<p>Continue to the full evidence report below.</p>"
        "</section>"
    )
    return (
        '<section class="srcc-one-pager" aria-labelledby="evidence-one-pager-title" '
        'data-section="evidence-one-pager">'
        f"{header}{answers}{scenarios}{research_case}{operating}{break_case}"
        f"{questions}{provenance}{handoff}</section>"
    )


def _evidence_one_pager_scope_valid(
    snapshot: CompanyWorkbenchHtmlSnapshot,
) -> bool:
    """Validate only the frozen identity and fields required by the summary."""
    if not isinstance(snapshot, CompanyWorkbenchHtmlSnapshot):
        return False
    profile_label = safe_html_brief_text(
        html.unescape(str(snapshot.profile_label))
    )
    expected_identity = hashlib.sha256(
        json.dumps(
            asdict(replace(snapshot, identity="")),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    return bool(
        _ticker(snapshot.ticker)
        and profile_label
        and profile_label.lower() != "not recorded"
        and profile_label != _WITHHELD_ACTION
        and _iso(snapshot.review_cutoff)
        and str(snapshot.identity or "") == expected_identity
    )


def _html_evidence_one_pager_or_unavailable(
    snapshot: CompanyWorkbenchHtmlSnapshot,
    *,
    heading_level: int,
) -> str:
    """Fail closed to an explicit summary state without affecting the full report."""
    try:
        if not _evidence_one_pager_scope_valid(snapshot):
            raise ValueError("one-pager scope is incomplete or unsafe")
        return _html_evidence_one_pager(snapshot, heading_level=heading_level)
    except (TypeError, ValueError):
        heading = f"h{heading_level}"
        return (
            '<section class="srcc-one-pager" '
            'data-section="evidence-one-pager-unavailable">'
            f"<{heading}>Evidence One-Pager unavailable</{heading}>"
            '<p class="srcc-boundary">The compact summary could not be formatted. '
            "Continue to the full evidence report below.</p></section>"
        )


def _html_brief_content(snapshot: CompanyWorkbenchHtmlSnapshot, *, heading_level: int) -> str:
    heading = f"h{heading_level}"
    base = next((scenario for scenario in snapshot.scenarios if scenario.name == "Base"), None)
    overview = (
        '<section class="srcc-section" data-section="overview">'
        f"<{heading}>Overview</{heading}>"
        f"{_html_brief_state_markup(snapshot.freshness_state)}"
        '<dl class="srcc-meta">'
        f"<dt>Ticker</dt><dd>{_html_brief_text(snapshot.ticker, 'not recorded')}</dd>"
        f"<dt>Profile</dt><dd>{_html_brief_text(snapshot.profile_label)}</dd>"
        f"<dt>Review cutoff</dt><dd>{_html_brief_text(snapshot.review_cutoff)}</dd>"
        f"<dt>Source as of</dt><dd>{_html_brief_text(snapshot.source_as_of)}</dd>"
        f"<dt>Generated at</dt><dd>{_html_brief_text(snapshot.generated_at)}</dd>"
        f"<dt>Model version</dt><dd>{_html_brief_text(snapshot.model_version)}</dd>"
        "</dl>"
        f"{_html_brief_blockers(snapshot.blockers)}"
        "</section>"
    )
    answers = '<section class="srcc-section" data-section="answers">' + f"<{heading}>Answers</{heading}>" + '<div class="srcc-card-grid">' + "".join(
        '<article class="srcc-card">'
        f"<h3>{_html_brief_text(answer.title)}</h3>{_html_brief_state_markup(answer.state)}"
        f"<p>{_html_brief_text(answer.body, 'No portable answer.')}</p>"
        "</article>" for answer in snapshot.answers
    ) + "</div></section>"
    scenario_rows = "".join(
        "<tr>"
        f"<th scope=\"row\">{_html_brief_text(scenario.name)}</th>"
        f"<td>{_html_brief_state_markup(scenario.state)}</td>"
        f"<td>{'Modified Base' if scenario.modified else 'Canonical'}</td>"
        f"<td>{_html_brief_text(scenario.method_name)}</td>"
        f"<td>{format_html_brief_number(scenario.revenue_growth, percent=True)}</td>"
        f"<td>{format_html_brief_number(scenario.fcf_margin, percent=True)}</td>"
        f"<td>{format_html_brief_number(scenario.wacc, percent=True)}</td>"
        f"<td>{format_html_brief_number(scenario.terminal_growth, percent=True)}</td>"
        f"<td>{format_html_brief_number(scenario.forecast_years)}</td>"
        f"<td>{format_html_brief_number(scenario.bridge.scenario_value_per_share, currency=scenario.bridge.currency)}"
        f"{_html_brief_state_markup(scenario.bridge.per_share_state)}</td>"
        f"<td>{_html_brief_blockers(scenario.bridge.blockers) or 'None recorded'}</td>"
        "</tr>" for scenario in snapshot.scenarios
    )
    scenarios = (
        '<section class="srcc-section" data-section="scenarios">'
        f"<{heading}>Scenarios</{heading}><div class=\"table-scroll\"><table class=\"srcc-table\"><caption>Supplied scenario assumptions</caption>"
        "<thead><tr><th>Scenario</th><th>State</th><th>Modified state</th><th>Method</th><th>Revenue growth</th><th>FCF margin</th><th>WACC</th><th>Terminal growth</th><th>Forecast years</th><th>Scenario value/share</th><th>Bridge blockers</th></tr></thead>"
        f"<tbody>{scenario_rows}</tbody></table></div></section>"
    )
    schedule_rows = ""
    if base is not None:
        schedule_length = max(len(base.bridge.projected_fcfs), len(base.bridge.discounted_fcfs))
        schedule_rows = "".join(
            "<tr>"
            f"<th scope=\"row\">{index + 1}</th>"
            f"<td>{format_html_brief_number(base.bridge.projected_fcfs[index], currency=base.bridge.currency) if index < len(base.bridge.projected_fcfs) else 'not recorded'}</td>"
            f"<td>{format_html_brief_number(base.bridge.discounted_fcfs[index], currency=base.bridge.currency) if index < len(base.bridge.discounted_fcfs) else 'not recorded'}</td>"
            "</tr>"
            for index in range(schedule_length)
        )
    schedule = (
        '<div class="table-scroll"><table class="srcc-table"><caption>Supplied Base projected and discounted FCF schedule</caption>'
        '<thead><tr><th>Forecast period</th><th>Projected FCF</th><th>Discounted FCF</th></tr></thead>'
        f"<tbody>{schedule_rows}</tbody></table></div>"
    )
    bridge_values = () if base is None else (
        ("Discounted explicit total", base.bridge.discounted_explicit_total, base.bridge.explicit_total_state),
        ("Terminal value", base.bridge.terminal_value, base.bridge.enterprise_state),
        ("Discounted terminal value", base.bridge.discounted_terminal_value, base.bridge.enterprise_state),
        ("Enterprise value", base.bridge.enterprise_value, base.bridge.enterprise_state),
        ("Cash", base.bridge.cash, base.bridge.equity_state),
        ("Debt", base.bridge.debt, base.bridge.equity_state),
        ("Net debt", base.bridge.net_debt, base.bridge.equity_state),
        ("Equity value", base.bridge.equity_value, base.bridge.equity_state),
        (base.bridge.shares_label, base.bridge.shares_outstanding, base.bridge.share_basis_state),
        ("Supplied value per share", base.bridge.scenario_value_per_share, base.bridge.per_share_state),
    )
    bridge_rows = "".join(
        f"<tr><th scope=\"row\">{_html_brief_text(label)}</th><td>{format_html_brief_number(value, currency=base.bridge.currency if base else '')}</td><td>{_html_brief_state_markup(state)}</td></tr>"
        for label, value, state in bridge_values
    )
    bridge = (
        '<section class="srcc-section" data-section="dcf-bridge">'
        f"<{heading}>DCF bridge</{heading}>{_html_brief_state_markup(base.bridge.state if base else 'withheld')}"
        f"{schedule}"
        '<div class="table-scroll"><table class="srcc-table"><caption>Supplied Base DCF bridge values</caption><thead><tr><th>Field</th><th>Recorded value</th><th>State</th></tr></thead>'
        f"<tbody>{bridge_rows}</tbody></table></div>{_html_brief_blockers(base.bridge.blockers if base else ('Base scenario is not recorded.',))}</section>"
    )
    sensitivity_headers = "".join(f"<th>{format_html_brief_number(value, percent=True)}</th>" for value in snapshot.sensitivity.terminal_growth_values)
    sensitivity_rows = "".join(
        f"<tr><th scope=\"row\">{format_html_brief_number(wacc, percent=True)}</th>" + "".join(
            f"<td>{format_html_brief_number(value, currency=base.bridge.currency if base else '')}</td>" for value in row
        ) + "</tr>" for wacc, row in zip(snapshot.sensitivity.wacc_values, snapshot.sensitivity.value_grid)
    )
    sensitivity = (
        '<section class="srcc-section" data-section="sensitivity">'
        f"<{heading}>Sensitivity</{heading}>{_html_brief_state_markup(snapshot.sensitivity.state)}"
        '<div class="table-scroll"><table class="srcc-table"><caption>Supplied sensitivity grid</caption><thead><tr><th>WACC / terminal growth</th>'
        f"{sensitivity_headers}</tr></thead><tbody>{sensitivity_rows}</tbody></table></div>{_html_brief_blockers(snapshot.sensitivity.blockers)}</section>"
    )
    business = (
        '<section class="srcc-section" data-section="business-forward-view">'
        f"<{heading}>Business / forward view</{heading}>"
        f"{_html_brief_section_cards((snapshot.recency,) + snapshot.readiness_lanes + snapshot.research_sections)}"
        "</section>"
    )
    decision = (
        '<section class="srcc-section" data-section="decision-lab">'
        f"<{heading}>Decision Lab</{heading}>{_html_brief_section_cards(snapshot.decision_lanes)}</section>"
    )
    evidence_rows = "".join(
        "<tr>"
        f"<td>{_html_brief_text(row.section)}</td><td>{_html_brief_state_markup(row.state)}</td>"
        f"<td>{_html_brief_text(row.source_id)}</td><td>{_html_brief_reference_markup(row.source_ref)}</td>"
        f"<td>{_html_brief_text(row.as_of)}</td><td>{_html_brief_text(row.retrieved_at)}</td>"
        f"<td>{_html_brief_text(row.rights_state)}</td><td>{_html_brief_text(row.field_scope_state)}</td>"
        f"<td>{_html_brief_text(row.model_identity)}</td><td>{_html_brief_text(row.input_identity)}</td>"
        f"<td>{_html_brief_blockers(row.blockers) or 'None recorded'}</td>"
        "</tr>" for row in snapshot.evidence_rows
    ) or "<tr><td colspan=\"11\">No portable evidence recorded.</td></tr>"
    evidence = (
        '<section class="srcc-section srcc-advanced-evidence" data-section="advanced-evidence">'
        f"<{heading}>Advanced evidence</{heading}>{_html_brief_state_markup(snapshot.rights_state)}"
        '<div class="table-scroll"><table class="srcc-table"><caption>Portable evidence provenance</caption><thead><tr><th>Section</th><th>State</th><th>Source ID</th><th>Reference</th><th>As of</th><th>Retrieved</th><th>Rights</th><th>Field scope</th><th>Model identity</th><th>Input identity</th><th>Row blockers</th></tr></thead>'
        f"<tbody>{evidence_rows}</tbody></table></div></section>"
    )
    return overview + answers + scenarios + bridge + sensitivity + business + decision + evidence


def render_company_workbench_html_fragment(snapshot: CompanyWorkbenchHtmlSnapshot) -> str:
    """Render a self-contained, scoped HTML fragment from a frozen snapshot only."""
    title = f"{_html_brief_text(snapshot.ticker, 'Research')} research brief"
    summary = _html_evidence_one_pager_or_unavailable(snapshot, heading_level=3)
    full_report = _html_brief_content(snapshot, heading_level=3)
    return (
        f"<style>{_html_brief_css('.srcc-html-brief')}</style>"
        '<article class="srcc-html-brief" aria-labelledby="srcc-brief-title"><div class="srcc-brief-shell">'
        f'<h2 id="srcc-brief-title" class="srcc-brief-title">{title}</h2>'
        f'<p class="srcc-boundary">{_html_brief_text(snapshot.boundary)}</p>'
        f"{summary}{full_report}"
        "</div></article>"
    )


def render_company_workbench_html_document(snapshot: CompanyWorkbenchHtmlSnapshot) -> str:
    """Render a deterministic, offline full document from a frozen snapshot only."""
    title = f"{_html_brief_text(snapshot.ticker, 'Research')} research brief"
    summary = _html_evidence_one_pager_or_unavailable(snapshot, heading_level=2)
    full_report = _html_brief_content(snapshot, heading_level=2)
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<meta http-equiv=\"Content-Security-Policy\" content=\"{_HTML_BRIEF_CSP}\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{title}</title><style>{_html_brief_css('.srcc-html-document')}</style></head>"
        '<body class="srcc-html-document"><a class="srcc-skip-link" href="#research-brief-main">Skip to research brief</a>'
        '<header class="srcc-brief-shell"><h1 class="srcc-brief-title">'
        f"{title}</h1><p class=\"srcc-boundary\">{_html_brief_text(snapshot.boundary)}</p></header>"
        f'<main id="research-brief-main" tabindex="-1" class="srcc-brief-shell">{summary}{full_report}</main>'
        '<footer class="srcc-brief-shell"><p>Portable offline research brief. Review source evidence and stated boundaries.</p></footer>'
        "</body></html>"
    )


def company_workbench_html_bytes(snapshot: CompanyWorkbenchHtmlSnapshot) -> bytes:
    """Return deterministic UTF-8 bytes for the full offline document."""
    return render_company_workbench_html_document(snapshot).encode("utf-8")


def company_workbench_html_download_spec(snapshot: CompanyWorkbenchHtmlSnapshot) -> HtmlBriefDownloadSpec:
    """Return download data only; callers own any user-initiated save operation."""
    return HtmlBriefDownloadSpec(
        data=company_workbench_html_bytes(snapshot),
        file_name=company_workbench_html_filename(snapshot),
        mime="text/html; charset=utf-8",
    )
