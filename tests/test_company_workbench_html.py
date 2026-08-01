from dataclasses import replace
from pathlib import Path

import pytest

from src.catalyst_evidence_timeline import CatalystEvent, CatalystTimeline
from src.company_workbench_html import (
    CompanyWorkbenchHtmlInputs,
    build_company_workbench_html_snapshot,
    company_workbench_html_filename,
    normalize_html_brief_state,
    safe_html_brief_reference,
    safe_html_brief_text,
)
from src.forward_view import ForwardViewPacket, ForwardViewSection
from src.historical_valuation_regime import ValuationRegimePacket
from src.observation_recency import ObservationRecency, ObservationRecencySet
from src.profile_context import CoverageCounts, ProfileContext
from src.quarterly_business_trend import QuarterlyMetricTrend, QuarterlyTrendPacket
from src.research_decision_lab import DecisionLabLane, ResearchDecisionLabState
from src.research_thesis_journal import JournalEntry, JournalState
from src.scenario_lab import ScenarioLabResult, ScenarioParameters
from src.valuation import DCFResult, SensitivityTable, ValuationInput, build_valuation_result


def _profile() -> ProfileContext:
    return ProfileContext(
        profile_key="demo",
        profile_label="Demo research profile",
        data_dir=Path("/private/input"),
        outputs_dir=Path("/private/output"),
        source_as_of="2026-07-28T12:00:00Z",
        readiness_built_at="2026-07-28T12:00:00Z",
        snapshot_identity="private-identity",
        snapshot_identity_short="private",
        freshness_state="current",
        freshness_message="Saved profile observation is current.",
        refresh_command="private command",
        coverage=CoverageCounts(),
        lane_source_dates=(),
        snapshot_inputs=("/private/source.csv",),
    )


def _trend(metric: str, value: float | None = 10.0) -> QuarterlyMetricTrend:
    return QuarterlyMetricTrend(metric, "ready", value, "2026-Q2", "https://sec.example/filing", 0.1, 0.2, ("2026-Q2",), (), "")


def _quarterly(ticker: str = "NVDA") -> QuarterlyTrendPacket:
    return QuarterlyTrendPacket(ticker, "ready", "2026-Q2", ("2026-Q2",), _trend("Revenue", 100.0), _trend("EPS", 2.0), _trend("Operating margin", 0.3), _trend("FCF", 20.0), _trend("FCF margin", 0.2), (), (), 0, "supported", "Q4 explicit only", "Quarterly evidence", ())


def _section(name: str, state: str = "ready", answer: str = "Reviewed context") -> ForwardViewSection:
    return ForwardViewSection(name, state, answer, ({"safe": "fact"},), "Research context only")


def _forward(ticker: str = "NVDA") -> ForwardViewPacket:
    return ForwardViewPacket(ticker, "ready", "2026-07-30T12:00:00Z", "current", "forward-v1", _section("Historical"), _section("Valuation"), _section("Peers"), _section("Thesis"), _section("Earnings"), (), "Review the evidence boundary.", "No recommendation")


def _decision(ticker: str = "NVDA", profile_key: str = "demo") -> ResearchDecisionLabState:
    lanes = tuple(DecisionLabLane(key, label, "documented", f"{label} documented", "Evidence recorded", "Review later") for key, label in (("plan", "Plan"), ("evidence", "Evidence"), ("invalidation", "Invalidation"), ("scenario", "Scenario"), ("review_trigger", "Review trigger"), ("learning", "Learning")))
    return ResearchDecisionLabState(profile_key, ticker, "ready", lanes, "Review later", "Process only", "decision-identity")


def _regime(ticker: str = "NVDA") -> ValuationRegimePacket:
    return ValuationRegimePacket(ticker, "pe", "insufficient_history", "", 0, 0, 0, None, None, None, None, None, "stale_or_unknown", (), (), 0, (), "Historical only")


def _catalysts(ticker: str = "NVDA", profile_key: str = "demo") -> CatalystTimeline:
    event = CatalystEvent("catalyst-evidence-v1", "event-1", profile_key, ticker, "earnings", "Earnings date", "2026-08-15T12:00:00Z", "2026-07-20T12:00:00Z", "2026-07-21T12:00:00Z", "SEC", "https://sec.example/event", "supported", "reviewer", "Reviewed event")
    return CatalystTimeline(ticker, "supported", (event,), (), 0, 0, (), "Evidence only")


def _valuation_payload() -> dict[str, object]:
    valuation = build_valuation_result(ValuationInput(ticker="NVDA", free_cash_flow=100.0, shares_outstanding=10.0, net_debt=0.0))
    return valuation.to_dict()


def _inputs(report: dict[str, object] | None = None, **changes: object) -> CompanyWorkbenchHtmlInputs:
    valuation = _valuation_payload()
    default_report = {
        "ticker": "NVDA",
        "generated_at": "2026-07-31T12:00:00Z",
        "method_version": "report-v1",
        "financial_summary": {"currency": "USD"},
        "earnings_summary": {"fiscal_period": "2026-Q3"},
        "valuation_snapshot": valuation,
        "provenance": {"source_records": []},
    }
    selected = {"Ticker": "NVDA", "Use Now": "Saved, source-backed context.", "Still Blocked": "No live consensus.", "state": "ready"}
    recency = ObservationRecencySet(ObservationRecency("NVDA", "2026-07-30", 1, "current", "Current"), ObservationRecency("profile", "2026-07-30", 1, "current", "Current"), (), 7, "/private/prices.csv", "2026-07-31")
    values = dict(report_payload=default_report if report is None else report, profile_context=_profile(), observation_recency=recency, selected_answer=selected, authoritative_task={"title": "Review evidence", "body": "Confirm source scope.", "state": "blocked", "badges": ("Research",)}, scenario_lab_result=None, nowcast_packet=None, decision_lab_state=_decision(), quarterly_trend=_quarterly(), forward_view=_forward(), journal_state=None, valuation_regime=_regime(), catalyst_timeline=_catalysts())
    values.update(changes)
    return CompanyWorkbenchHtmlInputs(**values)


def _base(snapshot):
    return next(row for row in snapshot.scenarios if row.name == "Base")


def _base_dcf(report):
    return report["valuation_snapshot"]["scenarios"][1]["dcf_result"]


def test_snapshot_copies_authoritative_dcf_values_and_canonical_sensitivity_without_recalculation():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    raw = _inputs().report_payload["valuation_snapshot"]
    dcf = raw["dcf_result"]

    assert [row.name for row in snapshot.scenarios] == ["Bear", "Base", "Bull"]
    assert _base(snapshot).bridge.projected_fcfs == tuple(dcf["projected_fcfs"])
    assert _base(snapshot).bridge.discounted_fcfs == tuple(dcf["discounted_fcfs"])
    assert _base(snapshot).bridge.discounted_explicit_total == dcf["discounted_explicit_total"]
    assert _base(snapshot).bridge.terminal_value == dcf["terminal_value"]
    assert _base(snapshot).bridge.discounted_terminal_value == dcf["discounted_terminal_value"]
    assert _base(snapshot).bridge.enterprise_value == dcf["enterprise_value"]
    assert _base(snapshot).bridge.equity_value == dcf["equity_value"]
    assert _base(snapshot).bridge.scenario_value_per_share == dcf["fair_value_per_share"]
    assert snapshot.sensitivity.value_grid == tuple(tuple(row) for row in raw["sensitivity_table"]["fair_value_grid"])
    assert snapshot.sensitivity.wacc_values == tuple(raw["sensitivity_table"]["wacc_values"])
    assert snapshot.sensitivity.terminal_growth_values == tuple(raw["sensitivity_table"]["terminal_growth_values"])


def test_snapshot_keeps_enterprise_visible_when_equity_and_per_share_are_withheld():
    report = _inputs().report_payload
    dcf = _base_dcf(report)
    dcf["assumptions"].pop("net_debt", None)
    dcf["assumptions"].pop("cash", None)
    dcf["assumptions"].pop("debt", None)

    bridge = _base(build_company_workbench_html_snapshot(_inputs(report))).bridge

    assert bridge.state == "partial"
    assert bridge.enterprise_state == "available"
    assert bridge.equity_state == "withheld"
    assert bridge.per_share_state == "withheld"


@pytest.mark.parametrize("shares", (None, 0.0, -1.0, float("nan"), float("inf")))
def test_snapshot_withholds_per_share_for_missing_or_nonpositive_or_nonfinite_shares(shares):
    report = _inputs().report_payload
    _base_dcf(report)["assumptions"]["shares_outstanding"] = shares
    bridge = _base(build_company_workbench_html_snapshot(_inputs(report))).bridge

    assert bridge.per_share_state == "withheld"
    assert bridge.scenario_value_per_share is None
    assert bridge.shares_label == "Shares outstanding used by existing model"
    assert bridge.share_basis_state == "unverified"


def test_non_calculated_dcf_with_populated_numbers_exposes_none_of_them():
    report = _inputs().report_payload
    _base_dcf(report)["status"] = "partial"

    bridge = _base(build_company_workbench_html_snapshot(_inputs(report))).bridge

    assert bridge.state == "withheld"
    assert bridge.projected_fcfs == ()
    assert bridge.discounted_fcfs == ()
    assert bridge.discounted_explicit_total is None
    assert bridge.enterprise_value is None
    assert bridge.equity_value is None
    assert bridge.scenario_value_per_share is None


def test_state_and_text_normalization_fail_closed_for_unknown_and_action_language():
    assert normalize_html_brief_state("ready") == "available"
    assert normalize_html_brief_state("candidate_context_only") == "excluded"
    assert normalize_html_brief_state("invented") == "withheld"
    assert safe_html_brief_text("buy this stock now") == "Withheld: reviewer-authored action language is not portable research evidence."
    assert safe_html_brief_text("SEC-0000123456-26-000001") == "SEC-0000123456-26-000001"
    assert safe_html_brief_reference("javascript:alert(1)").href == ""
    assert safe_html_brief_reference("https://example.com/source").href == "https://example.com/source"


def test_only_a_fresh_matching_changed_scenario_lab_can_modify_base_and_sensitivity():
    canonical = _inputs()
    raw_dcf = _base_dcf(canonical.report_payload)
    modified_dcf = DCFResult(**raw_dcf)
    modified = ScenarioLabResult("calculated", "Calculated", "demo", "NVDA", "input-identity", None, ScenarioParameters(0.1, 0.2, 0.09, 0.03, 5), ({"assumption": "wacc"},), None, modified_dcf, SensitivityTable("calculated", "dcf", [0.08], [0.03], [[123.0]], [], [], []), None, None, None, (), ())

    accepted = build_company_workbench_html_snapshot(_inputs(scenario_lab_result=modified))
    rejected = build_company_workbench_html_snapshot(_inputs(scenario_lab_result=replace(modified, ticker="AMD")))

    assert _base(accepted).modified is True
    assert accepted.sensitivity.value_grid == ((123.0,),)
    assert _base(rejected).modified is False
    assert rejected.sensitivity.value_grid != ((123.0,),)


def test_nowcast_requires_matching_scoped_packet_and_never_emits_probability():
    matching = {"ticker": "NVDA", "fiscal_period": "2026-Q3", "as_of_timestamp": "2026-07-30T12:00:00Z", "evidence_scope": "source_backed_preview_only", "readiness": {"consensus_ready": True}, "probability_available": True, "beat_probability": 0.99, "source_ids": ["SEC-1"]}
    snapshot = build_company_workbench_html_snapshot(_inputs(nowcast_packet=matching))
    lanes = {lane.key: lane for lane in snapshot.readiness_lanes}

    assert lanes["consensus"].state == "partial"
    assert "portable nowcast provenance incomplete" in lanes["consensus"].blockers
    assert "0.99" not in lanes["consensus"].answer
    assert lanes["outcomes"].state == "withheld"
    assert "portable outcome scope and provenance incomplete" in lanes["outcomes"].blockers


def test_snapshot_is_immutable_sanitized_and_deterministic_with_fixed_section_orders():
    inputs = _inputs()
    first = build_company_workbench_html_snapshot(inputs)
    inputs.report_payload["ticker"] = "AMD"
    inputs.selected_answer["Use Now"] = "buy now"
    second = build_company_workbench_html_snapshot(_inputs())

    assert first.ticker == "NVDA"
    assert first.identity == build_company_workbench_html_snapshot(_inputs()).identity
    assert first.identity == second.identity
    assert "/private" not in repr(first)
    assert [row.key for row in first.research_sections] == ["business-trend", "key-drivers", "risks", "catalysts", "evidence-gaps", "valuation-regime"]
    assert [row.key for row in first.decision_lanes] == ["plan", "evidence", "invalidation", "scenario", "review-trigger", "learning"]
    assert company_workbench_html_filename(first) == "NVDA-2026-07-30-research-brief.html"


def _source_record(**changes):
    row = {
        "source_id": "SEC-0000123456-26-000001",
        "source_ref": "https://sec.example/filing",
        "as_of": "2026-07-30T12:00:00Z",
        "retrieved_at": "2026-07-30T12:30:00Z",
        "rights_state": "permitted",
        "field_scope_state": "permitted",
    }
    row.update(changes)
    return row


def test_mismatched_selected_answer_withholds_both_answer_bodies():
    selected = {"Ticker": "AMD", "Use Now": "AMD-only research", "Still Blocked": "AMD-only blocker", "state": "ready"}

    snapshot = build_company_workbench_html_snapshot(_inputs(selected_answer=selected))

    assert snapshot.answers[0].state == "withheld"
    assert snapshot.answers[0].body == "No portable answer."
    assert snapshot.answers[1].body == "No portable blocker."
    assert "AMD" not in repr(snapshot.answers[:2])


def test_incomplete_evidence_row_withholds_rights_rollup_even_when_another_row_is_permitted():
    report = _inputs().report_payload
    report["provenance"]["source_records"] = [_source_record(), _source_record(source_id="SEC-INCOMPLETE", retrieved_at="")]

    snapshot = build_company_workbench_html_snapshot(_inputs(report, catalyst_timeline=replace(_catalysts(), upcoming=())))

    assert snapshot.rights_state == "withheld"
    report_rows = [row for row in snapshot.evidence_rows if row.section == "report"]
    assert len(report_rows) == 2
    assert report_rows[1].state == "withheld"


def test_excluded_rights_rollup_requires_both_rights_and_field_scope_to_be_not_applicable():
    report = _inputs().report_payload
    report["provenance"]["source_records"] = [_source_record(rights_state="not_applicable", field_scope_state="not_applicable")]
    empty_catalysts = replace(_catalysts(), upcoming=())
    assert build_company_workbench_html_snapshot(_inputs(report, catalyst_timeline=empty_catalysts)).rights_state == "excluded"

    report["provenance"]["source_records"] = [_source_record(rights_state="not_applicable", field_scope_state="permitted")]
    assert build_company_workbench_html_snapshot(_inputs(report, catalyst_timeline=empty_catalysts)).rights_state == "withheld"


def test_nowcast_withholds_missing_backtest_and_calibration_diagnostics_independently():
    packet = {"ticker": "NVDA", "fiscal_period": "2026-Q3", "as_of_timestamp": "2026-07-30T12:00:00Z", "evidence_scope": "source_backed_preview_only", "readiness": {"consensus_ready": True}}

    lanes = {row.key: row for row in build_company_workbench_html_snapshot(_inputs(nowcast_packet=packet)).readiness_lanes}

    assert lanes["consensus"].state == "partial"
    assert lanes["backtesting"].state == "withheld"
    assert lanes["calibration"].state == "withheld"


def test_nowcast_exposes_backtest_and_calibration_only_when_their_own_diagnostics_exist():
    packet = {
        "ticker": "NVDA", "fiscal_period": "2026-Q3", "as_of_timestamp": "2026-07-30T12:00:00Z",
        "evidence_scope": "source_backed_preview_only", "readiness": {"consensus_ready": True},
        "backtest_verdict": "reviewable", "backtest_count": 4,
        "calibration_state": "reviewable", "event_count": 4, "gates": (),
    }

    lanes = {row.key: row for row in build_company_workbench_html_snapshot(_inputs(nowcast_packet=packet)).readiness_lanes}

    assert lanes["backtesting"].state == "partial"
    assert lanes["calibration"].state == "partial"
    assert "portable nowcast provenance incomplete" in lanes["backtesting"].blockers
    assert "portable nowcast provenance incomplete" in lanes["calibration"].blockers


def test_quarterly_and_valuation_regime_available_states_are_capped_without_portable_provenance():
    trend = _quarterly()
    regime = replace(_regime(), state="ready")

    snapshot = build_company_workbench_html_snapshot(_inputs(quarterly_trend=trend, valuation_regime=regime))
    lanes = {row.key: row for row in snapshot.readiness_lanes}
    sections = {row.key: row for row in snapshot.research_sections}

    assert lanes["actuals"].state == "partial"
    assert lanes["revenue"].state == "partial"
    assert lanes["eps"].state == "partial"
    assert lanes["historical-valuation"].state == "partial"
    assert sections["valuation-regime"].state == "partial"
    assert all("portable provenance incomplete" in row.blockers for row in (lanes["actuals"], lanes["revenue"], lanes["eps"], lanes["historical-valuation"], sections["valuation-regime"]))


def _journal(profile_key="demo", ticker="NVDA"):
    entry = JournalEntry("research-thesis-journal-v1", "entry-1", profile_key, ticker, "thesis-1", "evidence", "2026-07-20T12:00:00Z", "2026-07-20T12:00:00Z", "reviewer", "Reviewed evidence", "supporting", "SEC", "https://sec.example/journal", "2026-07-19T12:00:00Z", "", "", "")
    return JournalState(profile_key, ticker, "2026-07-30T12:00:00Z", "ready", (entry,), None, 0, (), (entry,), (), (), (), (), (), "", "", False)


def test_matching_journal_and_catalyst_evidence_rows_are_retained_as_fail_closed_provenance_rows():
    snapshot = build_company_workbench_html_snapshot(_inputs(journal_state=_journal()))

    sections = [row.section for row in snapshot.evidence_rows]
    assert "journal" in sections
    assert "catalyst" in sections
    assert all(row.state == "withheld" for row in snapshot.evidence_rows if row.section in {"journal", "catalyst"})


def test_mismatched_journal_or_catalyst_evidence_is_not_emitted():
    wrong_event_timeline = _catalysts(profile_key="other")
    snapshot = build_company_workbench_html_snapshot(_inputs(journal_state=_journal(profile_key="other"), catalyst_timeline=wrong_event_timeline))

    assert not any(row.section in {"journal", "catalyst"} for row in snapshot.evidence_rows)


def test_missing_canonical_scenario_is_withheld_instead_of_cloning_top_level_dcf():
    report = _inputs().report_payload
    report["valuation_snapshot"]["scenarios"] = report["valuation_snapshot"]["scenarios"][1:]

    bear = next(row for row in build_company_workbench_html_snapshot(_inputs(report)).scenarios if row.name == "Bear")

    assert bear.state == "withheld"
    assert bear.bridge.enterprise_value is None
    assert bear.bridge.projected_fcfs == ()


@pytest.mark.parametrize("unsafe", ("line one\nline two", "src/valuation.py", "./tests/test_valuation.py", "NVDA\x00AMD"))
def test_sanitizer_rejects_control_and_repository_relative_paths(unsafe):
    assert safe_html_brief_text(unsafe) == ""


def test_unsafe_ticker_is_withheld_from_snapshot_and_filename():
    report = _inputs().report_payload
    report["ticker"] = "NVDA\nAMD"

    snapshot = build_company_workbench_html_snapshot(_inputs(report))

    assert snapshot.ticker == ""
    assert "NVDA" not in repr(snapshot)
    assert company_workbench_html_filename(snapshot) == "UNKNOWN-2026-07-31-research-brief.html"


def test_snapshot_isolated_from_source_metadata_mutation_after_construction():
    report = _inputs().report_payload
    source = _source_record()
    report["provenance"]["source_records"] = [source]

    snapshot = build_company_workbench_html_snapshot(_inputs(report))
    identity = snapshot.identity
    source["source_id"] = "MUTATED"
    source["source_ref"] = "https://example.invalid/mutated"

    assert snapshot.evidence_rows[0].source_id == "SEC-0000123456-26-000001"
    assert snapshot.identity == identity
