from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
import re

import pytest

import src.company_workbench_html as html_brief
import src.data_update as data_update
import src.loader as input_loader
import src.readiness_engine as readiness_engine
import src.stock_report as stock_report
from scripts.public_wording_check import find_forbidden_matches
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


def _change(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "state": "review_now",
        "answer": "1 unresolved source-backed change needs review.",
        "next_task": "Review the changed filing evidence.",
        "source_refs": ("https://sec.example/change",),
        "source_backed_eligible": True,
        "change_context_kind": "source_backed",
    }
    row.update(changes)
    return row


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
    values = dict(report_payload=default_report if report is None else report, profile_context=_profile(), observation_recency=recency, selected_answer=selected, authoritative_task={"title": "Review evidence", "body": "Confirm source scope.", "state": "blocked", "badges": ("Research",)}, scenario_lab_result=None, nowcast_packet=None, decision_lab_state=_decision(), quarterly_trend=_quarterly(), forward_view=_forward(), journal_state=None, valuation_regime=_regime(), catalyst_timeline=_catalysts(), change_answer=_change(), change_ticker="NVDA", change_profile_key="demo")
    values.update(changes)
    return CompanyWorkbenchHtmlInputs(**values)


def test_snapshot_freezes_four_scoped_answers_without_promoting_source_backed_change():
    snapshot = build_company_workbench_html_snapshot(_inputs())

    assert [answer.label for answer in snapshot.answers] == [
        "Use now",
        "Still withheld",
        "What changed",
        "Next research task",
    ]
    changed = snapshot.answers[2]
    assert changed.state == "partial"
    assert changed.title == "1 unresolved source-backed change needs review."
    assert changed.body == "Review the changed filing evidence."
    assert [reference.href for reference in changed.source_refs] == [
        "https://sec.example/change"
    ]
    assert any("portable publication" in blocker.lower() for blocker in changed.blockers)


@pytest.mark.parametrize(
    ("kind", "eligible", "expected"),
    (
        ("none", False, "not_recorded"),
        ("snapshot_only", False, "partial"),
        ("source_backed", True, "partial"),
        ("unknown", True, "withheld"),
    ),
)
def test_snapshot_maps_change_context_without_inheriting_workflow_state(kind, eligible, expected):
    inputs = _inputs(change_answer=_change(change_context_kind=kind, source_backed_eligible=eligible))
    assert build_company_workbench_html_snapshot(inputs).answers[2].state == expected


@pytest.mark.parametrize("kind", ("none", "unknown"))
def test_snapshot_clears_claim_and_references_for_none_or_unknown_context(kind):
    changed = build_company_workbench_html_snapshot(
        _inputs(change_answer=_change(change_context_kind=kind))
    ).answers[2]
    assert changed.title == "No portable change answer."
    assert changed.body == "No scoped saved change answer is available."
    assert changed.source_refs == ()
    assert "unresolved source-backed" not in repr(changed).lower()


@pytest.mark.parametrize(
    ("ticker", "profile"),
    (("AMD", "demo"), ("NVDA", "other"), ("", "demo")),
)
def test_snapshot_rejects_unscoped_or_mismatched_change_answer(ticker, profile):
    snapshot = build_company_workbench_html_snapshot(
        _inputs(change_ticker=ticker, change_profile_key=profile)
    )
    changed = snapshot.answers[2]
    assert changed.state == "not_recorded"
    assert changed.source_refs == ()
    assert "changed filing" not in repr(changed).lower()


def test_snapshot_sanitizes_change_copy_state_and_references():
    snapshot = build_company_workbench_html_snapshot(
        _inputs(
            change_answer=_change(
                state="invented-state<script>",
                answer="<script>alert(1)</script>",
                next_task="buy this stock now",
                source_refs=(
                    "javascript:alert(1)",
                    "https://sec.example/change",
                ),
            )
        )
    )
    changed = snapshot.answers[2]
    assert changed.state == "withheld"
    assert changed.badges == ()
    assert "<script" not in repr(changed).lower()
    assert "buy this stock" not in repr(changed).lower()
    assert changed.source_refs == ()
    assert changed.title == "No portable change answer."


@pytest.mark.parametrize(
    "source_ref",
    (
        "sec:accession",
        "sec-accession:0001045810-26-000021",
        "consensus://nvda/fy2027-q2/2026-07-15",
        "sec_companyfacts",
        "sec_companyfacts; sec_filing_document",
        "yfinance_research_grade; sec_filing_document",
    ),
)
def test_snapshot_keeps_real_opaque_source_ref_partial_but_does_not_expose_it(
    source_ref,
):
    changed = build_company_workbench_html_snapshot(
        _inputs(change_answer=_change(source_refs=(source_ref,)))
    ).answers[2]
    assert changed.state == "partial"
    assert changed.source_refs == ()
    assert any("reference is incomplete" in blocker.lower() for blocker in changed.blockers)


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "http://example.com/change",
        "/etc/passwd",
        "src/private-change.txt",
        "file:///tmp/change",
        "consensus://nvda/../../private",
    ),
)
def test_snapshot_withholds_mixed_valid_and_unsafe_change_references(unsafe_ref):
    changed = build_company_workbench_html_snapshot(
        _inputs(
            change_answer=_change(
                source_refs=("https://sec.example/change", unsafe_ref)
            )
        )
    ).answers[2]
    assert changed.state == "withheld"
    assert changed.source_refs == ()
    assert changed.title == "No portable change answer."


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


@pytest.mark.parametrize("field, value", (("profile_key", "other"), ("ticker", "AMD")))
def test_matching_journal_container_does_not_emit_a_mismatched_entry(field, value):
    journal = _journal()
    entry = replace(journal.entries[0], **{field: value})

    snapshot = build_company_workbench_html_snapshot(_inputs(journal_state=replace(journal, entries=(entry,))))

    assert not any(row.section == "journal" for row in snapshot.evidence_rows)


@pytest.mark.parametrize("unsafe", ("docs/brief.md", "scripts/tool.py", ".git/config", "folder\\file.txt", "../escape", "control\x7f", "control\x85"))
def test_sanitizer_rejects_full_control_range_and_repository_relative_paths(unsafe):
    assert safe_html_brief_text(unsafe) == ""


def test_validated_https_reference_remains_usable_while_its_label_is_sanitized():
    reference = safe_html_brief_reference({"source": "SEC-0000123456-26-000001", "source_ref": "https://www.sec.gov/Archives/edgar/data/1"})

    assert reference.label == "SEC-0000123456-26-000001"
    assert reference.href == "https://www.sec.gov/Archives/edgar/data/1"


_BROAD_REVIEW_POLICY_LEAKS = (
    "Shares should be bought now.",
    "Shares should definitely be bought now.",
    "Shares should probably be bought now.",
    "Shares should ultimately be bought now.",
    "Shares should promptly be bought now.",
    "Shares should gradually be bought now.",
    "Shares should aggressively be bought now.",
    "Shares definitely should be bought now.",
    "Shares probably should be bought now.",
    "Shares ultimately should be bought now.",
    "Shares promptly should be bought now.",
    "Shares gradually should be bought now.",
    "Shares aggressively should be bought now.",
    "Shares reviewwise should planwise be bought now.",
    "Shares outstanding should be bought now.",
    "Shares based on review should be bought now.",
    "The share count should be purchased now.",
    "Shares data should be bought now.",
    "Shares should be purchased, dataset quality permitting.",
    "Shares should be purchased, source dataset quality permitting.",
    "The share count should be normalized using the most recently purchased dataset and then sold.",
    "The share count should be normalized using the most recently purchased source dataset and then sold.",
    "Shares should reviewwise planwise slowly carefully deliberately eventually be bought now.",
    "Shares reviewwise planwise slowly carefully deliberately eventually should be bought now.",
    "Increase exposure now.",
    "Reduce exposure now.",
    "Build exposure now.",
    "Initiate exposure now.",
    "Increase the current direct strategic gross net total aggregate absolute adjusted exposure now.",
    "Increase the model detail using the reviewed historical assumptions and document the resulting shares now.",
    "Increase the model detail using the reviewed historical assumptions and increase the resulting exposure now.",
    "Purchase the entire share count now.",
    "Sell the selected share count now.",
    "Buy the full share count now.",
    "Acquire the resulting share count now.",
    "The share count should be normalized using the most recently purchased, vendor dataset.",
    "The share count should be normalized using the dataset most recently purchased, from the vendor.",
    "The share count should be normalized using the recently sold vendor dataset.",
    "The share count should be normalized using the recently purchased and then dataset.",
    "The share count should be normalized using the most recently purchased vendor dataset and then sold.",
    "The share count should be normalized using the dataset most recently purchased from the vendor and then sold.",
    "Increase as the model directs and document the resulting share count.",
    "Increase it per model and document the resulting position estimate.",
    "Increase model-directed quantity and document the resulting share count.",
    "Reduce model-directed quantity and document the resulting position estimate.",
    "Increase the model detail using reviewed historical assumptions and document the resulting position.",
    "Reduce the model detail using reviewed historical assumptions and document the resulting exposure.",
    "Build the model detail using reviewed historical assumptions and document the resulting shares.",
    "Initiate the model review using reviewed historical assumptions and document the resulting position.",
    "Shares cannot be bought now.",
    "Shares mustn't be bought now.",
    "Shares shouldn't be bought now.",
    "Shares can't be bought now.",
    "Shares couldn't be bought now.",
    "Shares mayn't be bought now.",
    "Shares mightn't be bought now.",
    "Shares won't be bought now.",
    "Shares wouldn't be bought now.",
    "Shares shan't be bought now.",
    "Shares mustn’t be bought now.",
    "Shares shouldn’t be bought now.",
    "Shares can’t be bought now.",
    "Shares couldn’t be bought now.",
    "Shares mayn’t be bought now.",
    "Shares mightn’t be bought now.",
    "Shares won’t be bought now.",
    "Shares wouldn’t be bought now.",
    "Shares shan’t be bought now.",
)


@pytest.mark.parametrize("unsafe", _BROAD_REVIEW_POLICY_LEAKS)
def test_real_sanitizer_withholds_broad_review_modal_and_exposure_leaks(unsafe):
    assert safe_html_brief_text(unsafe) == (
        "Withheld: reviewer-authored action language is not portable research evidence."
    )


def _snapshot_with_portable_field_text(field_name: str, text: str):
    inputs = _inputs()
    report = inputs.report_payload
    changes = {}
    if field_name == "profile_label":
        changes["profile_context"] = replace(inputs.profile_context, profile_label=text)
    elif field_name == "source_as_of":
        changes["profile_context"] = replace(inputs.profile_context, source_as_of=text)
        changes["forward_view"] = replace(inputs.forward_view, source_cutoff="")
        report["generated_at"] = ""
    elif field_name == "model_version":
        report["method_version"] = text
    elif field_name == "currency":
        report["financial_summary"]["currency"] = text
    elif field_name in {"use_now", "still_blocked"}:
        selected = dict(inputs.selected_answer)
        selected["Use Now" if field_name == "use_now" else "Still Blocked"] = text
        changes["selected_answer"] = selected
    elif field_name.startswith("task_"):
        task = dict(inputs.authoritative_task)
        if field_name == "task_title":
            task["title"] = text
        elif field_name == "task_body":
            task["body"] = text
        else:
            task["badges"] = (text,)
        changes["authoritative_task"] = task
    elif field_name.startswith("recency_"):
        recency = inputs.observation_recency
        selected = replace(
            recency.selected_ticker,
            **({"message": text} if field_name == "recency_message" else {"through_date": text}),
        )
        changes["observation_recency"] = replace(recency, selected_ticker=selected)
    elif field_name in {"quarterly_message", "revenue_reason", "eps_reason"}:
        quarterly = inputs.quarterly_trend
        if field_name == "quarterly_message":
            quarterly = replace(quarterly, message=text)
        elif field_name == "revenue_reason":
            quarterly = replace(quarterly, revenue=replace(quarterly.revenue, withheld_reason=text))
        else:
            quarterly = replace(quarterly, eps=replace(quarterly.eps, withheld_reason=text))
        changes["quarterly_trend"] = quarterly
    elif field_name in {"peer_answer", "thesis_answer"}:
        forward = inputs.forward_view
        section_name = "peer_context" if field_name == "peer_answer" else "thesis_context"
        changes["forward_view"] = replace(
            forward,
            **{section_name: replace(getattr(forward, section_name), answer=text)},
        )
    elif field_name == "risk_summary":
        report["risk_summary"] = {"state": "ready", "summary": text}
    elif field_name == "catalyst_boundary":
        changes["catalyst_timeline"] = replace(inputs.catalyst_timeline, boundary=text)
    elif field_name == "regime_boundary":
        changes["valuation_regime"] = replace(inputs.valuation_regime, boundary=text)
    elif field_name == "decision_answer":
        lanes = (replace(inputs.decision_lab_state.lanes[0], answer=text),) + inputs.decision_lab_state.lanes[1:]
        changes["decision_lab_state"] = replace(inputs.decision_lab_state, lanes=lanes)
    elif field_name == "scenario_method":
        report["valuation_snapshot"]["scenarios"][1]["dcf_result"]["method_name"] = text
    elif field_name in {"evidence_source_id", "evidence_model_identity"}:
        source = _source_record()
        source["source_id" if field_name == "evidence_source_id" else "model_identity"] = text
        report["provenance"]["source_records"] = [source]
    elif field_name == "evidence_input_identity":
        changes["scenario_lab_result"] = _modified_scenario_result(
            input_identity=text,
            source_metadata=(_source_record(),),
        )
    elif field_name == "reference_label":
        report["provenance"]["source_records"] = [_source_record(label=text)]
    elif field_name == "nowcast_verdict":
        changes["nowcast_packet"] = {
            "ticker": "NVDA",
            "fiscal_period": "2026-Q3",
            "as_of_timestamp": "2026-07-30T12:00:00Z",
            "evidence_scope": "source_backed_preview_only",
            "readiness": {"consensus_ready": True},
            "backtest_verdict": text,
            "backtest_count": 4,
            "calibration_state": "reviewable",
            "event_count": 4,
            "gates": (),
        }
    else:
        raise AssertionError(f"unhandled portable field: {field_name}")

    return build_company_workbench_html_snapshot(_inputs(report, **changes))


@pytest.mark.parametrize(
    "safe",
    (
        "The share count should be normalized using the most recently purchased dataset.",
        "The share count should be normalized using the most recently purchased source dataset.",
        "The share count should be normalized using the most recently purchased vendor dataset.",
        "The share count should be normalized using the purchased external source dataset.",
        "The share count should be normalized using the dataset most recently purchased from the vendor.",
        "The share count should be normalized using the recently purchased third-party dataset.",
        "Increase the model detail using the reviewed historical assumptions and document the resulting share count.",
        "Increase the model detail using reviewed historical assumptions and document the resulting position estimate.",
    ),
)
def test_broad_review_reference_methodology_remains_portable_on_real_surfaces(safe):
    snapshot = _snapshot_with_portable_field_text("use_now", safe)
    fragment = html_brief.render_company_workbench_html_fragment(snapshot)
    document = html_brief.render_company_workbench_html_document(snapshot)
    download = html_brief.company_workbench_html_bytes(snapshot)

    assert safe_html_brief_text(safe) == safe
    assert snapshot.answers[0].body == safe
    assert safe in fragment
    assert safe in document
    assert safe.encode("utf-8") in download


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("profile_label", "recommend this security"),
        ("source_as_of", "execute a trade"),
        ("model_version", "purchase shares"),
        ("currency", "go long"),
        ("use_now", "recommend this security"),
        ("still_blocked", "execute a trade"),
        ("task_title", "purchase shares"),
        ("task_body", "go long"),
        ("task_badge", "recommend this security"),
        ("recency_message", "execute a trade"),
        ("recency_through_date", "purchase shares"),
        ("quarterly_message", "go long"),
        ("revenue_reason", "recommend this security"),
        ("eps_reason", "execute a trade"),
        ("peer_answer", "purchase shares"),
        ("thesis_answer", "go long"),
        ("risk_summary", "recommend this security"),
        ("catalyst_boundary", "execute a trade"),
        ("regime_boundary", "purchase shares"),
        ("decision_answer", "go long"),
        ("scenario_method", "recommend this security"),
        ("evidence_source_id", "execute a trade"),
        ("evidence_model_identity", "purchase shares"),
        ("evidence_input_identity", "go long"),
    ),
)
def test_each_portable_dynamic_research_text_field_withholds_recommendation_or_transaction_equivalents(
    field_name, unsafe
):
    snapshot = _snapshot_with_portable_field_text(field_name, unsafe)

    assert unsafe not in repr(snapshot)
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


def _portable_state_signature(snapshot):
    return (
        snapshot.freshness_state,
        snapshot.rights_state,
        tuple(row.state for row in snapshot.answers),
        snapshot.recency.state,
        tuple(row.state for row in snapshot.readiness_lanes),
        tuple(row.state for row in snapshot.scenarios),
        tuple(row.state for row in snapshot.research_sections),
        tuple(row.state for row in snapshot.decision_lanes),
        tuple(row.state for row in snapshot.evidence_rows),
    )


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        (field_name, unsafe)
        for field_name in (
            "profile_label",
            "source_as_of",
            "model_version",
            "currency",
            "use_now",
            "still_blocked",
            "task_title",
            "task_body",
            "task_badge",
            "recency_message",
            "recency_through_date",
            "quarterly_message",
            "revenue_reason",
            "eps_reason",
            "peer_answer",
            "thesis_answer",
            "risk_summary",
            "catalyst_boundary",
            "regime_boundary",
            "decision_answer",
            "scenario_method",
            "evidence_source_id",
            "evidence_model_identity",
            "evidence_input_identity",
            "reference_label",
        )
        for unsafe in (
            "Shares should be bought now.",
            "Shares reviewwise should planwise be bought now.",
            "Shares should reviewwise planwise slowly carefully deliberately eventually be bought now.",
            "Shares reviewwise planwise slowly carefully deliberately eventually should be bought now.",
            "Shares shouldn’t be bought now.",
            "Shares cannot be bought now.",
            "Shares should be purchased, dataset quality permitting.",
            "The share count should be purchased now.",
            "Increase the current direct strategic gross net total aggregate absolute adjusted exposure now.",
            "Increase the model detail using the reviewed historical assumptions and document the resulting shares now.",
            "Purchase the entire share count now.",
            "The share count should be normalized using the most recently purchased, vendor dataset.",
            "Increase as the model directs and document the resulting share count.",
            "Increase model-directed quantity and document the resulting share count.",
            "Increase the model detail using reviewed historical assumptions and document the resulting position.",
            "Increase exposure now.",
        )
    ),
)
def test_broad_review_action_language_is_withheld_from_every_portable_field_surface(field_name, unsafe):
    baseline = _snapshot_with_portable_field_text(field_name, "Reviewed historical evidence.")
    snapshot = _snapshot_with_portable_field_text(field_name, unsafe)
    fragment = html_brief.render_company_workbench_html_fragment(snapshot)
    document = html_brief.render_company_workbench_html_document(snapshot)
    download = html_brief.company_workbench_html_bytes(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in fragment
    assert unsafe not in document
    assert unsafe.encode("utf-8") not in download
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)
    assert _portable_state_signature(snapshot) == _portable_state_signature(baseline)


@pytest.mark.parametrize("unsafe", _BROAD_REVIEW_POLICY_LEAKS)
def test_broad_review_nowcast_verdict_is_not_emitted_and_cannot_promote_eligible_lane(unsafe):
    absent = _snapshot_with_portable_field_text("nowcast_verdict", "")
    snapshot = _snapshot_with_portable_field_text("nowcast_verdict", unsafe)
    fragment = html_brief.render_company_workbench_html_fragment(snapshot)
    document = html_brief.render_company_workbench_html_document(snapshot)
    download = html_brief.company_workbench_html_bytes(snapshot)
    absent_lanes = {row.key: row for row in absent.readiness_lanes}
    lanes = {row.key: row for row in snapshot.readiness_lanes}

    assert unsafe not in repr(snapshot)
    assert unsafe not in fragment
    assert unsafe not in document
    assert unsafe.encode("utf-8") not in download
    assert lanes["backtesting"].state == absent_lanes["backtesting"].state == "withheld"
    assert _portable_state_signature(snapshot) == _portable_state_signature(absent)


@pytest.mark.parametrize(
    "approved",
    ("no recommendation", "no buy/sell instruction", "no broker integration", "not investment advice"),
)
def test_approved_negated_research_boundaries_remain_visible(approved):
    inputs = _inputs()
    selected = dict(inputs.selected_answer)
    selected["Use Now"] = approved

    snapshot = build_company_workbench_html_snapshot(_inputs(selected_answer=selected))
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert approved in rendered


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "recommendations are provided"),
        ("task_body", "executing a transaction"),
        ("quarterly_message", "executed a trade"),
        ("decision_answer", "purchased shares"),
        ("evidence_model_identity", "going long"),
    ),
)
def test_portable_field_values_withhold_common_action_inflections(field_name, unsafe):
    inputs = _inputs()
    report = inputs.report_payload
    changes = {}
    if field_name == "use_now":
        selected = dict(inputs.selected_answer)
        selected["Use Now"] = unsafe
        changes["selected_answer"] = selected
    elif field_name == "task_body":
        task = dict(inputs.authoritative_task)
        task["body"] = unsafe
        changes["authoritative_task"] = task
    elif field_name == "quarterly_message":
        changes["quarterly_trend"] = replace(inputs.quarterly_trend, message=unsafe)
    elif field_name == "decision_answer":
        lanes = (replace(inputs.decision_lab_state.lanes[0], answer=unsafe),) + inputs.decision_lab_state.lanes[1:]
        changes["decision_lab_state"] = replace(inputs.decision_lab_state, lanes=lanes)
    else:
        report["provenance"]["source_records"] = [
            _source_record(model_identity=unsafe)
        ]

    snapshot = build_company_workbench_html_snapshot(_inputs(report, **changes))
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


def _snapshot_with_portable_action_text(field_name, text):
    return _snapshot_with_portable_field_text(field_name, text)


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "buying shares now"),
        ("task_body", "bought this stock"),
        ("quarterly_message", "selling shares now"),
        ("decision_answer", "sold the security"),
        ("evidence_model_identity", "purchasing shares"),
        ("use_now", "shorting shares"),
        ("task_body", "shorted the stock"),
        ("quarterly_message", "holding shares"),
        ("decision_answer", "held a position"),
        ("evidence_model_identity", "placing a trade"),
        ("use_now", "placed an order"),
        ("task_body", "submitting a transaction"),
        ("quarterly_message", "submitted a trade"),
        ("decision_answer", "went long"),
        ("evidence_model_identity", "go short"),
        ("use_now", "entering a position"),
        ("task_body", "opened the position"),
        ("quarterly_message", "closing a position"),
        ("decision_answer", "exited the position"),
    ),
)
def test_portable_fields_withhold_bounded_semantic_action_families(field_name, unsafe):
    snapshot = _snapshot_with_portable_action_text(field_name, unsafe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


@pytest.mark.parametrize(
    "safe",
    (
        "Long-term revenue evidence remains under review.",
        "Short history limits calibration evidence.",
        "Historical evidence shows shares were purchased by the issuer in 2024.",
        "Historical evidence records a closed reporting period.",
    ),
)
def test_portable_fields_preserve_safe_non_action_research_language(safe):
    snapshot = _snapshot_with_portable_action_text("use_now", safe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert snapshot.answers[0].body == safe
    assert safe in rendered


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "buy more shares"),
        ("task_body", "bought several securities"),
        ("quarterly_message", "sell some stock"),
        ("decision_answer", "sold all equities"),
        ("evidence_model_identity", "purchase additional shares"),
        ("use_now", "sale of more shares"),
        ("task_body", "acquire another security"),
        ("quarterly_message", "disposed of those stocks"),
        ("decision_answer", "short several equities"),
        ("evidence_model_identity", "holding multiple shares"),
        ("use_now", "execute this trade"),
        ("task_body", "executed multiple orders"),
        ("quarterly_message", "placing our trade"),
        ("decision_answer", "submit our transaction"),
        ("evidence_model_identity", "routed several orders"),
        ("use_now", "open another position"),
        ("task_body", "closed all positions"),
        ("quarterly_message", "exiting our remaining positions"),
        ("decision_answer", "add to the position"),
        ("evidence_model_identity", "added more to our positions"),
        ("use_now", "trim the position"),
        ("task_body", "trimmed several positions"),
        ("quarterly_message", "increase the position"),
        ("decision_answer", "reduced multiple positions"),
        ("evidence_model_identity", "build a position"),
        ("use_now", "built up the position"),
        ("task_body", "initiating another position"),
        ("quarterly_message", "liquidated all positions"),
    ),
)
def test_portable_fields_withhold_action_objects_across_bounded_modifier_windows(field_name, unsafe):
    snapshot = _snapshot_with_portable_action_text(field_name, unsafe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "buy common shares"),
        ("task_body", "sell restricted stock"),
        ("quarterly_message", "purchase preferred shares"),
        ("decision_answer", "execute a block trade"),
        ("evidence_model_identity", "place a limit order"),
        ("use_now", "submit a market order"),
        ("task_body", "build a long position"),
        ("quarterly_message", "reduce the stock position"),
        ("decision_answer", "trim our equity position"),
        ("evidence_model_identity", "go net long"),
        ("use_now", "buy non-voting Class B common shares"),
        ("task_body", "sell a newly issued restricted stock"),
        ("quarterly_message", "purchase five thinly traded preferred securities"),
        ("decision_answer", "execute one large off-market block trade"),
        ("evidence_model_identity", "place the next good-til-cancelled limit order"),
        ("use_now", "submit one immediate-or-cancel market order"),
        ("task_body", "build a materially larger long position"),
        ("quarterly_message", "reduce the highly concentrated stock position"),
        ("decision_answer", "trim our current preferred equity position"),
        ("evidence_model_identity", "go strategically net long"),
        ("use_now", "buy 10.5 common shares"),
        ("task_body", "sell 25% of restricted stock"),
        ("quarterly_message", "buy restricted_class common shares"),
    ),
)
def test_portable_fields_withhold_structural_action_grammar_with_unseen_qualifiers(field_name, unsafe):
    snapshot = _snapshot_with_portable_action_text(field_name, unsafe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


@pytest.mark.parametrize(
    "safe",
    (
        "Long-term view remains evidence-led.",
        "Short history limits calibration evidence.",
        "Revenue increased 12% year over year.",
        "Debt was reduced during the quarter.",
        "The company increased revenue and reduced debt.",
        "Company historical evidence records a closed reporting period.",
        "The company opened another distribution center.",
        "Higher-order historical evidence remains unavailable.",
    ),
)
def test_portable_fields_preserve_non_action_text_near_action_family_words(safe):
    snapshot = _snapshot_with_portable_action_text("use_now", safe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert snapshot.answers[0].body == safe
    assert safe in rendered


@pytest.mark.parametrize(
    "safe",
    (
        "Higher-order evidence remains unavailable.",
        "Long-term revenue evidence remains under review.",
        "Short history limits calibration evidence.",
        "Revenue increased 12% year over year.",
        "Debt reduced during the quarter.",
        "Common shares outstanding were unchanged.",
        "Preferred stock terms remain under review.",
        "Market order statistics describe historical liquidity.",
        "The historical position remained net long throughout 2024.",
    ),
)
def test_portable_fields_preserve_safe_endpoint_terms_without_action_start(safe):
    snapshot = _snapshot_with_portable_action_text("use_now", safe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert snapshot.answers[0].body == safe
    assert safe in rendered


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "buy common, voting shares"),
        ("task_body", "buy common & preferred shares"),
        ("quarterly_message", "buy 1,000 shares"),
        ("decision_answer", "buy $500 of stock"),
        ("evidence_model_identity", "buy 1/2 of stock"),
        ("use_now", "place a good‑til‑cancelled limit order"),
        ("task_body", "go net-long"),
        ("quarterly_message", "BUY common/preferred SHARES"),
        ("decision_answer", "sell €750.00 of restricted stock"),
        ("evidence_model_identity", "purchase 2⁄3 of preferred securities"),
        ("use_now", "execute a same/day block trade"),
        ("task_body", "place a good—til—cancelled market order"),
        ("quarterly_message", "go market/neutral short"),
        ("decision_answer", "ＢＵＹ common／preferred shares"),
        ("evidence_model_identity", "buy side shares"),
        ("use_now", "sell side stocks"),
        ("task_body", "short term stock now"),
        ("quarterly_message", "short interest securities now"),
    ),
)
def test_portable_fields_withhold_normalized_action_token_variants(field_name, unsafe):
    snapshot = _snapshot_with_portable_action_text(field_name, unsafe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "buy shares"),
        ("task_body", "execute a trade"),
        ("quarterly_message", "open a position"),
        ("decision_answer", "hold the position"),
        ("evidence_model_identity", "size the position"),
        ("use_now", "cover the short"),
        ("task_body", "cover common shares"),
        ("quarterly_message", "go long"),
    ),
)
def test_portable_fields_withhold_direct_actions_from_each_semantic_family(field_name, unsafe):
    snapshot = _snapshot_with_portable_action_text(field_name, unsafe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "buy equity"),
        ("task_body", "sell common equity"),
        ("quarterly_message", "purchase private equity"),
        ("decision_answer", "cover equity"),
        ("evidence_model_identity", "buy the position"),
        ("use_now", "sell the position"),
        ("task_body", "short the position"),
        ("quarterly_message", "cover the position"),
        ("decision_answer", "open a trade"),
        ("evidence_model_identity", "close the trade"),
        ("use_now", "enter a trade"),
        ("task_body", "exit the trade"),
        ("quarterly_message", "add shares"),
        ("decision_answer", "trim common shares"),
        ("evidence_model_identity", "reduce equity"),
        ("use_now", "open long"),
        ("task_body", "close the short"),
        ("quarterly_message", "The report says the strategy buys shares."),
        ("decision_answer", "The report says the portfolio opens a position."),
        ("evidence_model_identity", "The note says the strategy goes long."),
        ("use_now", "The research says the strategy executes trades."),
        ("task_body", "place an immediate-or-cancel good-til-cancelled limit order"),
        ("quarterly_message", "buy $1,000,000,000.00 of common shares"),
        ("decision_answer", "b\u200buy shares"),
        ("evidence_model_identity", "buy sh\u2060ares"),
        ("use_now", "go lo\u200bng"),
        ("task_body", "open a pos\u200bition"),
        ("quarterly_message", "Buy shares—report the fill later."),
        ("decision_answer", "Execute the trade—record the result later."),
        ("evidence_model_identity", "Open a position—report it later."),
        ("use_now", "Go long—report the result later."),
        ("task_body", "Buy shares - report the fill later."),
        ("quarterly_message", "Execute the trade--record the result later."),
        ("decision_answer", "The model buys shares."),
        ("evidence_model_identity", "The analyst sells stock."),
        ("use_now", "The model opens positions."),
        ("task_body", "The analysis executes trades."),
        ("quarterly_message", "The model goes long."),
        ("decision_answer", "The report holds equities."),
        ("evidence_model_identity", "bu\ufe0fy shares"),
        ("use_now", "buy sh\ufe0fares"),
        ("task_body", "go lo\ufe0fng"),
        ("quarterly_message", "open a pos\ufe0fition"),
        ("decision_answer", "Buy stock data for review and shares for the portfolio."),
        ("evidence_model_identity", "liquidate common shares"),
        ("use_now", "liquidate the stock"),
        ("task_body", "liquidate equity"),
        ("quarterly_message", "size common shares"),
        ("decision_answer", "close the stock"),
        ("evidence_model_identity", "exit common shares"),
        ("use_now", "initiate common shares"),
        ("task_body", "The model covers the short."),
        ("quarterly_message", "The model orders trades."),
        ("decision_answer", "The report orders shares."),
        ("evidence_model_identity", "The analyst orders transactions."),
        ("use_now", "bu\u034fy shares"),
        ("task_body", "buy sh\u034fares"),
        ("quarterly_message", "go lo\u034fng"),
        ("decision_answer", "bu\u180by shares"),
        ("evidence_model_identity", "buy sh\u180cares"),
        ("use_now", "Buy stock data plus shares for the portfolio."),
        ("task_body", "Buy stock data & shares for the portfolio."),
        ("quarterly_message", "Buy stock data, shares for the portfolio."),
        ("decision_answer", "Buy stock data along with shares for the portfolio."),
        ("evidence_model_identity", "Buy total equity."),
        ("use_now", "Purchase tangible equity."),
        ("task_body", "Sell book equity."),
        ("quarterly_message", "Buy the shares outstanding."),
        ("decision_answer", "Buy shares by date 2026-08-05."),
        ("evidence_model_identity", "The model covers the position with shares."),
        ("use_now", "Buy stock data as well as shares for the portfolio."),
        ("task_body", "Buy stock data alongside shares for the portfolio."),
        ("quarterly_message", "bu\u3164y shares"),
        ("decision_answer", "buy sh\u115fares"),
        ("evidence_model_identity", "Order shares by date 2026-08-05."),
        ("use_now", "Hold the shares outstanding."),
        ("task_body", "Hold total equity."),
        ("quarterly_message", "Increase book equity."),
        ("decision_answer", "The model covers the trade with shares."),
        ("evidence_model_identity", "The model covers the exposure with shares."),
        ("use_now", "bu\u2800y shares"),
        ("task_body", "buy sh\u2800ares"),
        ("quarterly_message", "The company is stable, so increase equity."),
        ("decision_answer", "Review the company, then increase equity."),
        ("evidence_model_identity", "The model covers the risk with shares."),
        ("use_now", "The model covers market risk with common stock."),
    ),
)
def test_portable_fields_withhold_adversarial_action_state_transitions(field_name, unsafe):
    snapshot = _snapshot_with_portable_action_text(field_name, unsafe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


@pytest.mark.parametrize(
    "safe",
    (
        "The filing covers the current position disclosure.",
        "The model builds a current position estimate.",
        "Hold the current equity method constant.",
        "The report covers common and preferred share disclosures.",
        "The valuation model builds a net-long position estimate.",
        "The analysis orders trade records by date.",
        "The table routes transaction evidence to the appendix.",
        "The note covers the short-interest disclosure.",
        "Hold the historical cost equity method constant.",
        "Build an equity model for the accounting review.",
        "Buy-side research covers securities.",
        "Sell-side analysts cover common stocks.",
        "Short-term stock performance remains under review.",
        "Held-to-maturity securities remain unchanged.",
        "Available-for-sale securities remain unchanged.",
        "Order transaction records by date.",
        "Place trade records in chronological order.",
        "Cover short-interest disclosures in the appendix.",
        "Build position estimates from reviewed evidence.",
        "The filing covered common shares outstanding.",
        "The model built a current position bridge.",
        "The company increased shareholder equity.",
        "Add stock-based compensation to the model.",
        "Reduce stock-based compensation expense in the forecast.",
        "The analysis ordered trade rows by date.",
        "Open the trade blotter for review.",
        "Open long-duration asset schedules.",
        "The company increased total equity.",
        "The bank increased tangible common equity.",
        "Add stock–based compensation to the model.",
        "Open the trade-ledger for review.",
        "Open long–duration asset schedules.",
        "The analyst covers private equity.",
        "The analyst initiates stock coverage.",
        "Initiate coverage of the stock.",
        "The model builds stock coverage.",
        "Open the equity research workbook.",
        "Add stock−based compensation to the model.",
        "The bank increased common equity.",
        "Add stock⁃based compensation to the model.",
        "Open long⁃duration asset schedules.",
    ),
)
def test_portable_fields_preserve_safe_reference_research_and_accounting_semantics(safe):
    snapshot = _snapshot_with_portable_action_text("use_now", safe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert snapshot.answers[0].body == safe
    assert safe in rendered


@pytest.mark.parametrize(
    "unsafe",
    (
        "buy one two three four five six seven eight nine shares",
        "execute one two three four five six seven eight nine trades",
        "open one two three four five six seven eight nine position",
        "cover one two three four five six seven eight nine shares",
        "go one two three four five six seven eight nine long",
    ),
)
def test_portable_action_scanner_uses_clause_boundary_instead_of_token_count(unsafe):
    snapshot = _snapshot_with_portable_action_text("use_now", unsafe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered
    assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)


@pytest.mark.parametrize(
    "safe",
    (
        "Buy assumptions are documented. Common shares remain unchanged.",
        "The instruction says buy; common shares outstanding are unchanged.",
        "Buy assumptions are documented。 Common shares remain unchanged.",
        "Buy assumptions are documented\u2028Common shares remain unchanged.",
        "Buy assumptions are documented؟ Common shares remain unchanged.",
        "Buy assumptions are documented। Common shares remain unchanged.",
        "Buy assumptions are documented։ Common shares remain unchanged.",
        "Buy assumptions are documented۔ Common shares remain unchanged.",
        "Buy assumptions are documented። Common shares remain unchanged.",
        "Buy assumptions are documented‽ Common shares remain unchanged.",
    ),
)
def test_portable_action_scanner_stops_at_clause_boundary(safe):
    snapshot = _snapshot_with_portable_action_text("use_now", safe)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert snapshot.answers[0].body == safe
    assert safe in rendered


@pytest.mark.parametrize(
    "approved",
    (
        "NO RECOMMENDATION",
        "No buy—sell instruction",
        "No broker-integration",
        "Not investment advice",
    ),
)
def test_portable_fields_preserve_normalized_approved_negated_boundaries(approved):
    snapshot = _snapshot_with_portable_action_text("use_now", approved)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert snapshot.answers[0].body == approved
    assert approved in rendered


@pytest.mark.parametrize("credential", ("password hunter2", "api_key hunter2", "Authorization Bearer hunter2"))
def test_portable_document_bytes_reject_whitespace_and_bearer_credentials(credential):
    inputs = _inputs()
    selected = dict(inputs.selected_answer)
    selected["Use Now"] = credential

    data = html_brief.company_workbench_html_bytes(
        build_company_workbench_html_snapshot(_inputs(selected_answer=selected))
    )

    assert credential.encode() not in data
    assert b"hunter2" not in data


@pytest.mark.parametrize(
    "unsafe_url",
    (
        "https://example.com/token/hunter2",
        "https://example.com/api_key/hunter2",
        "https://example.com/%74%6f%6b%65%6e/hunter2",
        "https://example.com/api%5Fkey/hunter2",
    ),
)
def test_https_references_reject_sensitive_plain_and_url_decoded_path_pairs(unsafe_url):
    assert safe_html_brief_reference(unsafe_url).href == ""


def test_safe_ordinary_https_reference_remains_clickable_without_fetching(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("reference validation must not fetch")

    monkeypatch.setattr("socket.socket", fail)

    assert safe_html_brief_reference("https://example.com/research/filing").href == (
        "https://example.com/research/filing"
    )


def _complete_nowcast(as_of_timestamp):
    return {
        "ticker": "NVDA",
        "fiscal_period": "2026-Q3",
        "as_of_timestamp": as_of_timestamp,
        "evidence_scope": "source_backed_preview_only",
        "readiness": {"consensus_ready": True},
        "backtest_verdict": "reviewable",
        "backtest_count": 4,
        "calibration_state": "reviewable",
        "event_count": 4,
        "gates": (),
    }


def test_nowcast_datetime_comparison_handles_fractional_seconds_and_equivalent_offsets():
    report = _inputs().report_payload
    report["generated_at"] = "2026-07-30T12:00:00Z"
    forward = replace(_forward(), source_cutoff="2026-07-30T08:00:00-04:00")

    at_cutoff = build_company_workbench_html_snapshot(
        _inputs(report, forward_view=forward, nowcast_packet=_complete_nowcast("2026-07-30T12:00:00.000Z"))
    )
    half_second_late = build_company_workbench_html_snapshot(
        _inputs(report, forward_view=forward, nowcast_packet=_complete_nowcast("2026-07-30T08:00:00.500-04:00"))
    )

    at_cutoff_lanes = {row.key: row.state for row in at_cutoff.readiness_lanes}
    late_lanes = {row.key: row.state for row in half_second_late.readiness_lanes}
    assert [at_cutoff_lanes[key] for key in ("consensus", "backtesting", "calibration")] == [
        "partial",
        "partial",
        "partial",
    ]
    assert [late_lanes[key] for key in ("consensus", "backtesting", "calibration")] == [
        "withheld",
        "withheld",
        "withheld",
    ]


@pytest.mark.parametrize("invalid_cutoff", ("not-a-cutoff", "2026-07-30T12:00:00"))
def test_nowcast_withholds_when_all_applicable_cutoffs_are_malformed_or_naive(invalid_cutoff):
    report = _inputs().report_payload
    report["generated_at"] = invalid_cutoff
    profile = replace(_profile(), source_as_of=invalid_cutoff)
    forward = replace(_forward(), source_cutoff=invalid_cutoff)

    snapshot = build_company_workbench_html_snapshot(
        _inputs(
            report,
            profile_context=profile,
            forward_view=forward,
            nowcast_packet=_complete_nowcast("2026-07-30T11:59:59Z"),
        )
    )
    lanes = {row.key: row for row in snapshot.readiness_lanes}

    assert snapshot.generated_at == "not recorded"
    assert snapshot.review_cutoff == "not recorded"
    assert [lanes[key].state for key in ("consensus", "backtesting", "calibration")] == [
        "withheld",
        "withheld",
        "withheld",
    ]


def test_nowcast_accepts_valid_profile_cutoff_fallback_when_higher_precedence_cutoffs_are_invalid():
    report = _inputs().report_payload
    report["generated_at"] = "not-a-cutoff"
    profile = replace(_profile(), source_as_of="2026-07-30T12:00:00Z")
    forward = replace(_forward(), source_cutoff="2026-07-30T12:00:00")

    snapshot = build_company_workbench_html_snapshot(
        _inputs(
            report,
            profile_context=profile,
            forward_view=forward,
            nowcast_packet=_complete_nowcast("2026-07-30T11:59:59Z"),
        )
    )
    lanes = {row.key: row for row in snapshot.readiness_lanes}

    assert snapshot.generated_at == "not recorded"
    assert snapshot.review_cutoff == "2026-07-30T12:00:00Z"
    assert [lanes[key].state for key in ("consensus", "backtesting", "calibration")] == [
        "partial",
        "partial",
        "partial",
    ]


def test_empty_supported_catalyst_timeline_is_withheld_in_readiness_and_research_sections():
    empty = replace(_catalysts(), state="supported", upcoming=(), recent=())

    snapshot = build_company_workbench_html_snapshot(_inputs(catalyst_timeline=empty))
    readiness = {row.key: row for row in snapshot.readiness_lanes}
    research = {row.key: row for row in snapshot.research_sections}

    for row in (readiness["catalysts"], research["catalysts"]):
        assert row.state == "withheld"
        assert row.answer == "No matching catalyst evidence."
        assert row.blockers == ("Catalyst event scope does not match report scope.",)


def test_renderer_shows_supplied_scenario_assumptions_values_and_modified_base_cue():
    snapshot = build_company_workbench_html_snapshot(
        _inputs(scenario_lab_result=_modified_scenario_result())
    )
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert "<th>Scenario value/share</th>" in rendered
    assert "<th>Modified state</th>" in rendered
    assert "Modified Base" in rendered
    assert "Forecast years" in rendered
    for scenario in snapshot.scenarios:
        value = html_brief.format_html_brief_number(
            scenario.bridge.scenario_value_per_share,
            currency=scenario.bridge.currency,
        )
        assert value in rendered


def test_renderer_keeps_each_scenario_bridge_blockers_with_its_own_row_and_escapes_them():
    report = _inputs().report_payload
    report["valuation_snapshot"]["scenarios"][0]["dcf_result"]["status"] = "partial"
    snapshot = build_company_workbench_html_snapshot(_inputs(report))
    bear = next(scenario for scenario in snapshot.scenarios if scenario.name == "Bear")
    escaped_bear = replace(
        bear,
        bridge=replace(
            bear.bridge,
            blockers=bear.bridge.blockers + ("Bear <bridge> blocker.",),
        ),
    )
    scenarios = (escaped_bear,) + snapshot.scenarios[1:]

    rendered = html_brief.render_company_workbench_html_document(
        replace(snapshot, scenarios=scenarios)
    )
    bear_row = rendered.split('<th scope="row">Bear</th>', 1)[1].split("</tr>", 1)[0]
    base_row = rendered.split('<th scope="row">Base</th>', 1)[1].split("</tr>", 1)[0]

    assert escaped_bear.state == "withheld"
    assert "DCF result is not calculated." in bear_row
    assert "Bear &lt;bridge&gt; blocker." in bear_row
    assert "Bear <bridge> blocker." not in rendered
    assert "DCF result is not calculated." not in base_row


def test_renderer_shows_stored_projected_and_discounted_fcf_schedules_in_order():
    snapshot = _render_snapshot()
    base = _base(snapshot)

    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert "<caption>Supplied Base projected and discounted FCF schedule</caption>" in rendered
    assert "Projected FCF" in rendered
    assert "Discounted FCF" in rendered
    projected = [
        html_brief.format_html_brief_number(value, currency=base.bridge.currency)
        for value in base.bridge.projected_fcfs
    ]
    discounted = [
        html_brief.format_html_brief_number(value, currency=base.bridge.currency)
        for value in base.bridge.discounted_fcfs
    ]
    assert [rendered.index(value) for value in projected] == sorted(rendered.index(value) for value in projected)
    assert [rendered.index(value) for value in discounted] == sorted(rendered.index(value) for value in discounted)


def test_advanced_evidence_renders_model_input_identities_and_row_blockers_escaped():
    snapshot = _render_snapshot()
    row = replace(
        snapshot.evidence_rows[0],
        model_identity="model<identity>",
        input_identity="input&identity",
        blockers=("scope <blocked>",),
    )

    rendered = html_brief.render_company_workbench_html_document(
        replace(snapshot, evidence_rows=(row,))
    )

    assert "<th>Model identity</th>" in rendered
    assert "<th>Input identity</th>" in rendered
    assert "<th>Row blockers</th>" in rendered
    assert "model&lt;identity&gt;" in rendered
    assert "input&amp;identity" in rendered
    assert "scope &lt;blocked&gt;" in rendered
    assert "model<identity>" not in rendered


@pytest.mark.parametrize("safe", ("Revenue/EPS", "cash/debt", "Q/C Technologies"))
def test_sanitizer_preserves_safe_slash_delimited_research_phrases(safe):
    assert safe_html_brief_text(safe) == safe


@pytest.mark.parametrize(
    "unsafe",
    (
        "/etc/passwd",
        "../../escape",
        "folder/../escape",
        "~/private.txt",
        "C:\\private\\secret.txt",
        "/Users/research/private.txt",
        "/private/research.txt",
        "src/company_workbench_html.py",
        "data/report.csv",
        "archive/data/report.csv",
        "outputs/brief.html",
    ),
)
def test_sanitizer_still_rejects_absolute_traversal_private_repository_and_known_output_paths(unsafe):
    assert safe_html_brief_text(unsafe) == ""


@pytest.mark.parametrize(
    "field_name, unsafe",
    (
        ("use_now", "file=/Users/research/private.txt"),
        ("task_body", "path=/tmp/secret.txt"),
        ("quarterly_message", "archive=src/company_workbench_html.py"),
    ),
)
def test_portable_field_values_withhold_paths_preceded_by_punctuation(field_name, unsafe):
    inputs = _inputs()
    changes = {}
    if field_name == "use_now":
        selected = dict(inputs.selected_answer)
        selected["Use Now"] = unsafe
        changes["selected_answer"] = selected
    elif field_name == "task_body":
        task = dict(inputs.authoritative_task)
        task["body"] = unsafe
        changes["authoritative_task"] = task
    else:
        changes["quarterly_trend"] = replace(inputs.quarterly_trend, message=unsafe)

    snapshot = build_company_workbench_html_snapshot(_inputs(**changes))
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert unsafe not in repr(snapshot)
    assert unsafe not in rendered


def test_empty_or_invalid_report_ticker_never_matches_empty_scoped_objects():
    report = _inputs().report_payload
    report["ticker"] = "BAD/TICKER"
    recency = _inputs().observation_recency
    empty_recency = replace(recency, selected_ticker=replace(recency.selected_ticker, scope=""))
    empty_decision = replace(_decision(), ticker="")
    selected = {"Ticker": "", "Use Now": "leaked answer", "Still Blocked": "leaked blocker", "state": "ready"}

    snapshot = build_company_workbench_html_snapshot(_inputs(report, selected_answer=selected, observation_recency=empty_recency, decision_lab_state=empty_decision))

    assert snapshot.ticker == ""
    assert snapshot.answers[0].state == "withheld"
    assert snapshot.answers[0].body == "No portable answer."
    assert snapshot.recency.state == "withheld"
    assert all(row.state == "withheld" for row in snapshot.decision_lanes)
    assert snapshot.evidence_rows == ()


@pytest.mark.parametrize(
    "changed, lane_key",
    (
        (lambda inputs: {"observation_recency": replace(inputs.observation_recency, selected_ticker=replace(inputs.observation_recency.selected_ticker, scope="AMD"))}, "recency"),
        (lambda inputs: {"decision_lab_state": replace(inputs.decision_lab_state, ticker="AMD")}, "decision"),
        (lambda inputs: {"quarterly_trend": replace(inputs.quarterly_trend, ticker="AMD")}, "actuals"),
        (lambda inputs: {"forward_view": replace(inputs.forward_view, ticker="AMD")}, "peers"),
        (lambda inputs: {"valuation_regime": replace(inputs.valuation_regime, ticker="AMD")}, "historical-valuation"),
        (lambda inputs: {"nowcast_packet": {"ticker": "AMD", "fiscal_period": "2026-Q3", "as_of_timestamp": "2026-07-30T12:00:00Z", "evidence_scope": "source_backed_preview_only", "readiness": {"consensus_ready": True}}}, "consensus"),
    ),
)
def test_each_ticker_scoped_input_is_withheld_independently_on_mismatch(changed, lane_key):
    base = _inputs()
    snapshot = build_company_workbench_html_snapshot(_inputs(**changed(base)))

    if lane_key == "recency":
        assert snapshot.recency.state == "withheld"
    elif lane_key == "decision":
        assert all(row.state == "withheld" for row in snapshot.decision_lanes)
    else:
        lanes = {row.key: row for row in snapshot.readiness_lanes}
        assert lanes[lane_key].state == "withheld"


def test_real_snapshot_builder_does_not_call_file_network_or_calculation_collaborators(monkeypatch):
    inputs = _inputs()

    def fail(*args, **kwargs):
        raise AssertionError("snapshot builder must remain pure")

    monkeypatch.setattr("builtins.open", fail)
    monkeypatch.setattr("socket.socket", fail)
    monkeypatch.setattr("src.valuation.calculate_dcf", fail)
    monkeypatch.setattr("src.valuation.build_sensitivity_table", fail)

    snapshot = html_brief.build_company_workbench_html_snapshot(inputs)

    assert snapshot.ticker == "NVDA"


def _modified_scenario_result(**changes):
    raw = _base_dcf(_inputs().report_payload)
    result = ScenarioLabResult("calculated", "Calculated", "demo", "NVDA", "input-identity", None, ScenarioParameters(0.1, 0.2, 0.09, 0.03, 5), ({"assumption": "wacc"},), None, DCFResult(**raw), SensitivityTable("calculated", "dcf", [0.08], [0.03], [[123.0]], [], [], []), None, None, None, (), ())
    return replace(result, **changes)


@pytest.mark.parametrize("changed", ({"ticker": "AMD"}, {"profile_key": "other"}, {"input_identity": ""}, {"changed_assumptions": ()}))
def test_scenario_lab_rejects_each_independent_acceptance_gate(changed):
    snapshot = build_company_workbench_html_snapshot(_inputs(scenario_lab_result=_modified_scenario_result(**changed)))

    assert _base(snapshot).modified is False
    assert snapshot.sensitivity.value_grid != ((123.0,),)


def test_scenario_lab_rejects_non_calculated_outer_status_with_all_other_gates_valid():
    calculated = _modified_scenario_result()
    scenario_dcf = replace(
        calculated.scenario_result,
        enterprise_value=987654.0,
        fair_value_per_share=87654.0,
    )
    rejected = replace(
        calculated,
        status="partial",
        scenario_result=scenario_dcf,
        source_metadata=(_source_record(source_id="SCENARIO-ONLY"),),
    )

    snapshot = build_company_workbench_html_snapshot(_inputs(scenario_lab_result=rejected))

    assert _base(snapshot).modified is False
    assert _base(snapshot).bridge.enterprise_value != 987654.0
    assert _base(snapshot).bridge.scenario_value_per_share != 87654.0
    assert snapshot.sensitivity.value_grid != ((123.0,),)
    assert all(row.modified is False for row in snapshot.scenarios)
    assert not any(row.section == "scenario" for row in snapshot.evidence_rows)
    assert {row.name: row.state for row in snapshot.scenarios} == {
        "Bear": "available",
        "Base": "available",
        "Bull": "available",
    }
    assert "Scenario Lab result is not an accepted matching changed calculation." in snapshot.blockers


@pytest.mark.parametrize("field, value", (("ticker", "AMD"), ("profile_key", "other")))
def test_decision_lab_rejects_each_independent_scope_mismatch(field, value):
    snapshot = build_company_workbench_html_snapshot(_inputs(decision_lab_state=replace(_decision(), **{field: value})))

    assert all(row.state == "withheld" for row in snapshot.decision_lanes)


@pytest.mark.parametrize("field, value", (("ticker", "AMD"), ("profile_key", "other")))
def test_journal_state_rejects_each_independent_scope_mismatch(field, value):
    snapshot = build_company_workbench_html_snapshot(_inputs(journal_state=_journal(**{field: value})))

    assert not any(row.section == "journal" for row in snapshot.evidence_rows)


@pytest.mark.parametrize("field, value", (("ticker", "AMD"), ("profile_key", "other")))
def test_each_catalyst_event_rejects_each_independent_scope_mismatch(field, value):
    timeline = _catalysts()
    event = replace(timeline.upcoming[0], **{field: value})
    snapshot = build_company_workbench_html_snapshot(_inputs(catalyst_timeline=replace(timeline, upcoming=(event,))))

    assert not any(row.section == "catalyst" for row in snapshot.evidence_rows)


def test_catalyst_timeline_rejects_outer_ticker_mismatch_when_events_match():
    matching_events = _catalysts()
    mismatched_timeline = replace(matching_events, ticker="AMD")

    snapshot = build_company_workbench_html_snapshot(_inputs(catalyst_timeline=mismatched_timeline))
    lanes = {row.key: row for row in snapshot.readiness_lanes}
    sections = {row.key: row for row in snapshot.research_sections}

    assert matching_events.upcoming[0].ticker == "NVDA"
    assert matching_events.upcoming[0].profile_key == "demo"
    assert lanes["catalysts"].state == "withheld"
    assert lanes["catalysts"].answer == "No matching catalyst evidence."
    assert sections["catalysts"].state == "withheld"
    assert sections["catalysts"].answer == "No matching catalyst evidence."
    assert not any(row.section == "catalyst" for row in snapshot.evidence_rows)
    assert lanes["actuals"].answer == "Quarterly evidence"
    assert sections["key-drivers"].answer == "Reviewed context"


def test_nowcast_rejects_fiscal_period_mismatch_with_all_other_gates_valid():
    packet = {
        "ticker": "NVDA",
        "fiscal_period": "2026-Q4",
        "as_of_timestamp": "2026-07-30T12:00:00Z",
        "evidence_scope": "source_backed_preview_only",
        "readiness": {"consensus_ready": True},
        "backtest_verdict": "reviewable",
        "backtest_count": 4,
        "calibration_state": "reviewable",
        "event_count": 4,
        "gates": (),
    }

    snapshot = build_company_workbench_html_snapshot(_inputs(nowcast_packet=packet))
    lanes = {row.key: row for row in snapshot.readiness_lanes}

    assert [lanes[key].state for key in ("consensus", "backtesting", "calibration")] == [
        "withheld",
        "withheld",
        "withheld",
    ]
    assert [lanes[key].answer for key in ("consensus", "backtesting", "calibration")] == [
        "No portable nowcast evidence.",
        "No portable nowcast evidence.",
        "No portable nowcast evidence.",
    ]
    assert lanes["actuals"].answer == "Quarterly evidence"
    assert lanes["valuation"].answer == "Authoritative DCF bridge."


def test_nowcast_rejects_invalid_as_of_timestamp_with_all_other_gates_valid():
    packet = {
        "ticker": "NVDA",
        "fiscal_period": "2026-Q3",
        "as_of_timestamp": "not-a-timestamp",
        "evidence_scope": "source_backed_preview_only",
        "readiness": {"consensus_ready": True},
        "backtest_verdict": "reviewable",
        "backtest_count": 4,
        "calibration_state": "reviewable",
        "event_count": 4,
        "gates": (),
    }

    snapshot = build_company_workbench_html_snapshot(_inputs(nowcast_packet=packet))
    lanes = {row.key: row for row in snapshot.readiness_lanes}

    assert [lanes[key].state for key in ("consensus", "backtesting", "calibration")] == [
        "withheld",
        "withheld",
        "withheld",
    ]
    assert [lanes[key].answer for key in ("consensus", "backtesting", "calibration")] == [
        "No portable nowcast evidence.",
        "No portable nowcast evidence.",
        "No portable nowcast evidence.",
    ]
    assert lanes["actuals"].answer == "Quarterly evidence"
    assert lanes["valuation"].answer == "Authoritative DCF bridge."


def test_nowcast_rejects_as_of_after_report_generated_at_when_review_cutoff_is_later():
    report = _inputs().report_payload
    report["generated_at"] = "2026-07-31T12:00:00Z"
    forward = replace(_forward(), source_cutoff="2026-08-01T12:00:00Z")
    packet = {
        "ticker": "NVDA",
        "fiscal_period": "2026-Q3",
        "as_of_timestamp": "2026-07-31T12:00:01Z",
        "evidence_scope": "source_backed_preview_only",
        "readiness": {"consensus_ready": True},
        "backtest_verdict": "reviewable",
        "backtest_count": 4,
        "calibration_state": "reviewable",
        "event_count": 4,
        "gates": (),
    }

    snapshot = build_company_workbench_html_snapshot(
        _inputs(report, forward_view=forward, nowcast_packet=packet)
    )
    lanes = {row.key: row for row in snapshot.readiness_lanes}

    assert snapshot.generated_at == "2026-07-31T12:00:00Z"
    assert snapshot.review_cutoff == "2026-08-01T12:00:00Z"
    assert [lanes[key].state for key in ("consensus", "backtesting", "calibration")] == [
        "withheld",
        "withheld",
        "withheld",
    ]
    assert lanes["actuals"].answer == "Quarterly evidence"
    assert lanes["valuation"].answer == "Authoritative DCF bridge."


def test_nowcast_rejects_as_of_after_review_cutoff_when_report_generated_at_is_later():
    report = _inputs().report_payload
    report["generated_at"] = "2026-07-31T12:00:00Z"
    forward = replace(_forward(), source_cutoff="2026-07-30T12:00:00Z")
    packet = {
        "ticker": "NVDA",
        "fiscal_period": "2026-Q3",
        "as_of_timestamp": "2026-07-30T12:00:01Z",
        "evidence_scope": "source_backed_preview_only",
        "readiness": {"consensus_ready": True},
        "backtest_verdict": "reviewable",
        "backtest_count": 4,
        "calibration_state": "reviewable",
        "event_count": 4,
        "gates": (),
    }

    snapshot = build_company_workbench_html_snapshot(
        _inputs(report, forward_view=forward, nowcast_packet=packet)
    )
    lanes = {row.key: row for row in snapshot.readiness_lanes}

    assert snapshot.generated_at == "2026-07-31T12:00:00Z"
    assert snapshot.review_cutoff == "2026-07-30T12:00:00Z"
    assert [lanes[key].state for key in ("consensus", "backtesting", "calibration")] == [
        "withheld",
        "withheld",
        "withheld",
    ]
    assert lanes["actuals"].answer == "Quarterly evidence"
    assert lanes["valuation"].answer == "Authoritative DCF bridge."


def test_invalid_or_empty_profile_keys_never_authorize_decision_journal_catalyst_or_scenario_content():
    profile = replace(_profile(), profile_key="")
    journal = _journal(profile_key="")
    timeline = _catalysts(profile_key="")
    decision = _decision(profile_key="")
    scenario = _modified_scenario_result(profile_key="")

    snapshot = build_company_workbench_html_snapshot(_inputs(profile_context=profile, journal_state=journal, catalyst_timeline=timeline, decision_lab_state=decision, scenario_lab_result=scenario))

    assert _base(snapshot).modified is False
    assert all(row.state == "withheld" for row in snapshot.decision_lanes)
    assert not any(row.section in {"journal", "catalyst", "scenario"} for row in snapshot.evidence_rows)


def test_real_snapshot_builder_does_not_call_available_loader_refresh_readiness_report_or_ledger_collaborators(monkeypatch):
    inputs = _inputs()

    def fail(*args, **kwargs):
        raise AssertionError("snapshot builder must remain pure")

    monkeypatch.setattr("builtins.open", fail)
    monkeypatch.setattr("socket.socket", fail)
    monkeypatch.setattr(input_loader, "load_inputs", fail)
    monkeypatch.setattr(data_update, "refresh_price_update_status_output", fail)
    monkeypatch.setattr(readiness_engine, "build_ticker_readiness_report", fail)
    monkeypatch.setattr(stock_report, "build_stock_report_markdown", fail)
    monkeypatch.setattr("src.research_thesis_journal.append_journal_entry", fail)
    monkeypatch.setattr("src.catalyst_evidence_timeline.append_reviewed_event", fail)
    monkeypatch.setattr("src.valuation.calculate_dcf", fail)
    monkeypatch.setattr("src.valuation.build_sensitivity_table", fail)

    snapshot = build_company_workbench_html_snapshot(inputs)

    assert snapshot.ticker == "NVDA"


class _BriefHtmlParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attrs = []
        self.headings = []
        self._heading = None

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)
        if tag in {"h1", "h2", "h3"}:
            self._heading = tag

    def handle_endtag(self, tag):
        if tag == self._heading:
            self._heading = None

    def handle_data(self, data):
        if self._heading:
            self.headings.append((self._heading, data.strip()))


def _render_snapshot():
    report = _inputs().report_payload
    report["provenance"]["source_records"] = [_source_record()]
    return build_company_workbench_html_snapshot(_inputs(report))


def test_renderer_has_fixed_research_section_order_and_uses_only_snapshot_values():
    snapshot = _render_snapshot()

    rendered = html_brief.render_company_workbench_html_document(snapshot)

    expected = (
        "Overview",
        "Answers",
        "Scenarios",
        "DCF bridge",
        "Sensitivity",
        "Business / forward view",
        "Decision Lab",
        "Advanced evidence",
    )
    positions = [rendered.index(f'data-section="{title.lower().replace(" / ", "-").replace(" ", "-")}"') for title in expected]
    assert positions == sorted(positions)
    assert "net debt" not in rendered.lower() or str(next(row for row in snapshot.scenarios if row.name == "Base").bridge.net_debt) in rendered


def test_document_and_fragment_have_distinct_semantic_wrappers():
    snapshot = _render_snapshot()
    document = html_brief.render_company_workbench_html_document(snapshot)
    fragment = html_brief.render_company_workbench_html_fragment(snapshot)
    full = _BriefHtmlParser()
    embedded = _BriefHtmlParser()
    full.feed(document)
    embedded.feed(fragment)

    assert document.startswith("<!doctype html>")
    assert full.tags.count("h1") == 1
    assert {"html", "head", "body", "header", "main", "section", "table", "caption", "footer"} <= set(full.tags)
    assert ('id', 'research-brief-main') in full.attrs
    assert ('tabindex', '-1') in full.attrs
    assert "Skip to research brief" in document
    assert fragment.count('<article class="srcc-html-brief"') == 1
    assert ("h2", "NVDA research brief") in embedded.headings
    assert not {"html", "head", "body", "header", "main", "footer", "script"} & set(embedded.tags)
    assert "Skip to research brief" not in fragment
    assert "Content-Security-Policy" not in fragment


def test_renderer_escapes_content_allows_only_validated_https_references_and_has_no_active_markup():
    snapshot = _render_snapshot()
    unsafe_answer = replace(snapshot.answers[0], body='<img src=x onerror="alert(1)">')
    unsafe_row = replace(snapshot.evidence_rows[0], source_ref=html_brief.HtmlBriefSafeReference("Unsafe source", "javascript:alert(1)"))
    rendered = html_brief.render_company_workbench_html_document(replace(snapshot, answers=(unsafe_answer,) + snapshot.answers[1:], evidence_rows=(unsafe_row,)))
    safe_rendered = html_brief.render_company_workbench_html_document(snapshot)

    parser = _BriefHtmlParser()
    parser.feed(rendered)
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in rendered
    assert "javascript:" not in rendered
    assert not {"script", "form", "iframe", "img"} & set(parser.tags)
    assert not any(name.lower().startswith("on") for name, _ in parser.attrs)
    assert 'href="https://sec.example/filing"' in safe_rendered
    assert 'rel="noreferrer noopener"' in safe_rendered
    assert "SEC-0000123456-26-000001" in safe_rendered
    assert "url(" not in rendered.lower()
    assert "/private/" not in rendered


def test_renderer_states_numbers_and_dcf_values_are_explicit_without_recalculation():
    snapshot = _render_snapshot()
    base = next(row for row in snapshot.scenarios if row.name == "Base")
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert html_brief.format_html_brief_number(None) == "not recorded"
    assert html_brief.format_html_brief_number(0, currency="USD") == "USD 0.00"
    assert html_brief.format_html_brief_number(-2.5, percent=True) == "-250.0%"
    assert html_brief.format_html_brief_number("") == "not recorded"
    with pytest.raises(ValueError):
        html_brief.format_html_brief_number(float("nan"))
    assert "not recorded" in rendered
    for state in ("complete", "partial", "withheld", "stale", "not recorded", "excluded"):
        assert state in rendered
    assert "State: withheld" in rendered
    assert html_brief.format_html_brief_number(base.bridge.enterprise_value, currency=base.bridge.currency) in rendered
    assert html_brief.format_html_brief_number(snapshot.sensitivity.value_grid[0][0], currency=base.bridge.currency) in rendered


def test_renderer_css_is_scoped_and_contains_offline_accessibility_and_print_contracts():
    snapshot = _render_snapshot()
    fragment = html_brief.render_company_workbench_html_fragment(snapshot)
    document = html_brief.render_company_workbench_html_document(snapshot)

    fragment_css = fragment.split("<style>", 1)[1].split("</style>", 1)[0]
    document_css = document.split("<style>", 1)[1].split("</style>", 1)[0]
    for css, root in ((fragment_css, ".srcc-html-brief"), (document_css, ".srcc-html-document")):
        selectors = [selector.strip() for selector in re.findall(r"(?m)^\s*(?!@)([^{}]+)\{", css)]
        assert all(root in selector for selector in selectors)
        assert not re.search(r"(?m)^\s*(?:table|th|td|\*)\s*\{", css)
        assert ":focus-visible" in css
        assert "@media print" in css
        assert "@media (forced-colors: active)" in css
        assert "@media (prefers-reduced-motion: reduce)" in css
        assert "@media (max-width: 700px)" in css
        assert "table-scroll" in css
        assert "srcc-boundary" in css
    assert "Research-only" in document
    assert "body {" not in fragment_css
    assert "body {" not in document_css


def test_document_bytes_and_download_spec_are_deterministic_and_pathless():
    snapshot = _render_snapshot()

    first = html_brief.company_workbench_html_bytes(snapshot)
    second = html_brief.company_workbench_html_bytes(snapshot)
    spec = html_brief.company_workbench_html_download_spec(snapshot)

    assert first == second
    assert first == html_brief.render_company_workbench_html_document(snapshot).encode("utf-8")
    assert spec.data == first
    assert spec.file_name == "NVDA-2026-07-30-research-brief.html"
    assert spec.mime == "text/html; charset=utf-8"
    assert not hasattr(spec, "path")
    assert "default-src 'none'; script-src 'none'; connect-src 'none'; img-src 'none'; style-src 'unsafe-inline'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'" in html_brief.render_company_workbench_html_document(snapshot)
    assert "frame-ancestors" not in html_brief.render_company_workbench_html_document(snapshot)


def test_complete_partial_and_withheld_documents_keep_research_only_wording_non_actionable():
    snapshot = _render_snapshot()
    approved_boundary = (
        "Research-only, fail-closed portable brief; no recommendation, "
        "probability, or transaction action."
    )
    affirmative_or_instructional = tuple(
        re.compile(pattern, re.IGNORECASE)
        for pattern in (
            r"\b(?:buy|sell|short|hold)\s+(?:now|today|this\s+(?:stock|ticker)|shares?)\b",
            r"\b(?:set|use|raise|lower)\s+(?:a\s+)?target[- ]price\b",
            r"\btarget[- ]price\s+(?:is|of|at|:)\b",
            r"\b(?:we|the\s+(?:brief|system))\s+recommend(?:s|ed|ing)?\b",
            r"\brecommendation\s*:\s*(?:buy|sell|short|hold)\b",
            r"\b(?:rank|ranking)\s+(?:the|this|companies|stocks|securities)\b",
            r"\b(?:place|execute|route|submit)\s+(?:an?\s+)?(?:transaction|trade|order)\b",
            r"\b(?:open|close|size|increase|reduce)\s+(?:a\s+|the\s+|your\s+)?position\b",
            r"\ballocate\s+(?:capital|cash|portfolio)\b",
            r"\ballocation\s+(?:is|of|at|:)\s*\d",
            r"\bexpected[- ]return\s+(?:is|of|at|:)\b",
            r"\b(?:take|execute|recommended)\s+(?:an?\s+)?action\b",
            r"\baction\s*:\s*(?:buy|sell|short|hold)\b",
        )
    )

    for state, visible_label in (
        ("available", "complete"),
        ("partial", "partial"),
        ("withheld", "withheld"),
    ):
        state_snapshot = replace(
            snapshot,
            freshness_state=state,
            rights_state=state,
            answers=tuple(replace(answer, state=state) for answer in snapshot.answers),
            recency=replace(snapshot.recency, state=state),
            readiness_lanes=tuple(replace(lane, state=state) for lane in snapshot.readiness_lanes),
            research_sections=tuple(replace(section, state=state) for section in snapshot.research_sections),
            decision_lanes=tuple(replace(lane, state=state) for lane in snapshot.decision_lanes),
        )
        rendered = html_brief.render_company_workbench_html_document(state_snapshot)

        assert f"State: {visible_label}" in rendered
        assert approved_boundary in rendered
        assert find_forbidden_matches(rendered, path=f"{visible_label}-research-brief.html") == []
        assert not any(pattern.search(rendered) for pattern in affirmative_or_instructional)
