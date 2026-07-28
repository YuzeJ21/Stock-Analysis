from types import SimpleNamespace

import pytest

from src import research_workspace
from src.research_workspace import (
    RESEARCH_ROUTING_STATES,
    advanced_evidence_links,
    advanced_evidence_links_html,
    cash_generation_preview_cards,
    cash_generation_preview_rows,
    company_workbench_section_contract,
    company_change_answer,
    company_next_research_task,
    focused_cohort_cards,
    focused_cohort_coverage_cards,
    focused_ticker_coverage_cards,
    quarterly_trend_cards,
    research_desk_cards,
    research_desk_cards_html,
    research_evidence_return_link,
    research_monitor_frame,
    research_workspace_header_html,
    weekly_summary_cards,
)
from src.company_workbench_cash_generation_preview import (
    CashGenerationPreviewComponent,
    CashGenerationPreviewMetric,
    CompanyWorkbenchCashGenerationPreview,
    blocked_company_workbench_cash_generation_preview,
)
from src.focused_cohort_coverage import FocusedCohortCoverage, FocusedCohortCoverageRow
from src.focused_research_cohort import FocusedCohort, FocusedCohortMember
from src.earnings_nowcast_contract import QuarterlyActual
from src.quarterly_business_trend import build_quarterly_trend_packet
from src.quarterly_cash_generation import QuarterlyBusinessObservation
from src.weekly_research_summary import WeeklyResearchSummary


def _quarterly_actual(period: str, revenue: float, eps: float) -> QuarterlyActual:
    year = int(period[:4])
    quarter = int(period[-1])
    period_end = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    return QuarterlyActual(
        ticker="SYN1",
        fiscal_period=period,
        period_end_date=f"{year}-{period_end}",
        reported_at=f"{year + (quarter == 4)}-05-15T12:00:00+00:00",
        revenue_actual=revenue,
        eps_actual=eps,
        source="synthetic_test_fixture",
        source_ref=f"fixture:{period}:actuals",
        retrieved_at="2026-07-18T12:00:00+00:00",
        revenue_currency="USD",
        revenue_unit_scale=1.0,
        revenue_basis="reported",
        eps_currency="USD",
        eps_basis="gaap",
        eps_share_basis="diluted",
        eps_operations_basis="reported",
        split_adjustment_basis="as_reported",
    )


def _quarterly_business_observation(
    period: str,
    metric: str,
    value: float,
) -> QuarterlyBusinessObservation:
    year = int(period[:4])
    quarter = int(period[-1])
    period_end = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    return QuarterlyBusinessObservation(
        ticker="SYN1",
        fiscal_period=period,
        period_end_date=f"{year}-{period_end}",
        metric=metric,
        value=value,
        currency="USD",
        unit_scale=1.0,
        accounting_basis="reported",
        duration_basis="three_months",
        source="synthetic_test_fixture",
        source_ref=f"fixture:{period}:{metric}",
        published_at=f"{year + (quarter == 4)}-05-15T12:00:00+00:00",
        retrieved_at="2026-07-18T12:00:00+00:00",
        q4_evidence_state="explicit_filed_quarter" if quarter == 4 else "not_q4",
    )


def test_company_next_research_task_prioritizes_unresolved_source_change():
    task = company_next_research_task(
        {
            "state": "review_now",
            "next_task": "Review the filed evidence.",
            "source_backed_eligible": True,
        },
        [{"title": "Add peer mappings", "body": "Peer context is partial.", "state": "wait_for_evidence", "badges": ["peers"]}],
    )
    assert task == {
        "title": "Review the filed evidence.",
        "body": "Complete this source-backed evidence review before starting another research task.",
        "state": "review_now",
        "badges": ["source-backed change", "research-only"],
    }


def _review_change_item(
    *,
    evidence_status: str,
    review_status: str,
    wait_condition: str = "",
):
    event = SimpleNamespace(
        event_id=f"evt-{evidence_status}-{review_status}",
        ticker="NVDA",
        source_ref="sec:accession" if evidence_status == "source_backed" else "snapshot:readiness",
        evidence_status=evidence_status,
        suggested_research_task="NVDA: Review the changed evidence.",
    )
    return SimpleNamespace(
        event=event,
        review_status=review_status,
        wait_condition=wait_condition,
    )


def test_company_change_answer_maps_source_backed_open_change_to_eligible_review():
    answer = company_change_answer(
        "NVDA",
        [_review_change_item(evidence_status="source_backed", review_status="open")],
    )

    assert answer["state"] == "review_now"
    assert answer["next_task"] == "NVDA: Review the changed evidence."
    assert answer["source_backed_eligible"] is True
    assert answer["change_context_kind"] == "source_backed"


def test_snapshot_only_open_change_never_outranks_conclusion_priority():
    answer = company_change_answer(
        "NVDA",
        [_review_change_item(evidence_status="snapshot_evidence", review_status="open")],
    )
    task = company_next_research_task(
        answer,
        [{"title": "Add peer mappings", "body": "Peer context is partial.", "badges": ["peers"]}],
    )

    assert answer["source_backed_eligible"] is False
    assert answer["change_context_kind"] == "snapshot_only"
    assert task["title"] == "Add peer mappings"
    assert "source-backed change" not in task["badges"]


def test_source_backed_still_blocked_change_preserves_wait_routing():
    wait_condition = "Wait for the amended filing to become available."
    answer = company_change_answer(
        "NVDA",
        [
            _review_change_item(
                evidence_status="source_backed",
                review_status="still_blocked",
                wait_condition=wait_condition,
            )
        ],
    )
    task = company_next_research_task(answer, [{"title": "Add peer mappings", "badges": ["peers"]}])

    assert answer["source_backed_eligible"] is True
    assert answer["state"] == "wait_for_evidence"
    assert answer["next_task"] == wait_condition
    assert task["title"] == wait_condition
    assert task["state"] == "wait_for_evidence"


def test_source_backed_intentionally_deferred_change_preserves_wait_routing():
    wait_condition = "Resume after the quarterly review window opens."
    answer = company_change_answer(
        "NVDA",
        [
            _review_change_item(
                evidence_status="source_backed",
                review_status="intentionally_deferred",
                wait_condition=wait_condition,
            )
        ],
    )
    task = company_next_research_task(answer, [{"title": "Add peer mappings", "badges": ["peers"]}])

    assert answer["source_backed_eligible"] is True
    assert answer["state"] == "monitor"
    assert answer["next_task"] == wait_condition
    assert task["title"] == wait_condition
    assert task["state"] == "monitor"


@pytest.mark.parametrize(
    ("change_answer", "conclusion_cards"),
    [
        ("not-a-mapping", []),
        ({}, "not-a-card-collection"),
        ({}, 7),
        ({}, ["not-a-card", {"title": "Do not select this later card", "badges": []}]),
        ({}, [{"title": "Malformed badges", "badges": "peers"}]),
        ({}, [{"title": "Malformed badges", "badges": 7}]),
    ],
)
def test_company_next_research_task_fails_closed_on_malformed_input(
    change_answer,
    conclusion_cards,
):
    neutral_task = {
        "title": "Wait for reviewed evidence or choose another company",
        "body": "No source-backed change or executable company task is available. Do not infer one from missing data.",
        "state": "wait_for_evidence",
        "badges": ["monitor", "research-only"],
    }

    assert company_next_research_task(change_answer, conclusion_cards) == neutral_task


def test_company_next_research_task_uses_ordered_conclusion_priority_without_change():
    task = company_next_research_task(
        {"state": "monitor", "next_task": "Continue the current review or wait."},
        [{"title": "Add peer mappings", "body": "Peer context is partial.", "badges": ["peers"]}],
    )
    assert task["title"] == "Add peer mappings"
    assert task["body"] == "Peer context is partial."
    assert task["state"] == "wait_for_evidence"
    assert task["badges"] == ["peers", "research-only"]


def test_company_next_research_task_fails_closed_to_neutral_wait():
    task = company_next_research_task({}, [])
    assert task["title"] == "Wait for reviewed evidence or choose another company"
    assert task["state"] == "wait_for_evidence"
    assert task["badges"] == ["monitor", "research-only"]


def _cash_preview() -> CompanyWorkbenchCashGenerationPreview:
    source_url = "https://www.sec.gov/Archives/edgar/data/1045810/filing.htm"
    return CompanyWorkbenchCashGenerationPreview(
        ticker="NVDA",
        fiscal_period="2027-Q1",
        status="accepted_for_review",
        message="Accepted SEC evidence supports a cash-generation review preview.",
        operating_margin=CashGenerationPreviewMetric(
            "operating_margin",
            "preview_available",
            53_536_000_000 / 81_615_000_000,
            "2027-Q1",
            (f"{source_url}#operating", f"{source_url}#revenue"),
            "",
        ),
        free_cash_flow=CashGenerationPreviewMetric(
            "free_cash_flow",
            "preview_available",
            48_587_000_000,
            "2027-Q1",
            (f"{source_url}#cfo", f"{source_url}#capex"),
            "",
        ),
        fcf_margin=CashGenerationPreviewMetric(
            "fcf_margin",
            "preview_available",
            48_587_000_000 / 81_615_000_000,
            "2027-Q1",
            (f"{source_url}#cfo", f"{source_url}#capex", f"{source_url}#revenue"),
            "",
        ),
        blockers=(),
        withheld_metrics=(),
        accession="0001045810-26-000052",
        source_url=source_url,
        accepted_at="2026-05-20T20:35:52+00:00",
        cutoff="2026-07-21T03:59:59+00:00",
        capex_sign_evidence="explicit_filed_table_outflow",
        components=(
            CashGenerationPreviewComponent(
                metric="capital_expenditures",
                value=-1_757_000_000,
                currency="USD",
                fiscal_period="2027-Q1",
                source_ref=f"{source_url}#capex",
                published_at="2026-05-20T20:35:52+00:00",
                retrieved_at="2026-07-20T23:00:00+00:00",
                accounting_basis="reported",
                duration_basis="three_months",
                q4_evidence_state="not_q4",
            ),
        ),
    )


def test_cash_generation_preview_cards_are_answer_first_and_non_production():
    cards = cash_generation_preview_cards(_cash_preview())

    assert [card["kicker"] for card in cards] == [
        "CASH-GENERATION REVIEW PREVIEW",
        "OPERATING MARGIN",
        "FREE CASH FLOW",
        "FCF MARGIN",
    ]
    assert cards[0]["title"] == (
        "Cash-generation review preview — not production evidence"
    )
    assert cards[1]["title"] == "65.6%"
    assert cards[2]["title"] == "48,587,000,000"
    assert cards[3]["title"] == "59.5%"
    assert all(card["command"] == "" for card in cards)
    assert all("preview" in " ".join(card["badges"]).lower() for card in cards)
    rendered = str(cards)
    assert "0001045810-26-000052" not in rendered
    assert "sec.gov" not in rendered


def test_cash_generation_preview_rows_keep_lineage_under_advanced():
    rows = cash_generation_preview_rows(_cash_preview())

    assert any(
        row["Evidence"] == "Accession"
        and row["Value"] == "0001045810-26-000052"
        for row in rows
    )
    assert any(
        row["Evidence"] == "Capex sign"
        and row["Value"] == "explicit_filed_table_outflow"
        for row in rows
    )
    assert any(
        row["Evidence"] == "Component"
        and "capital_expenditures" in row["Value"]
        and row["Source Reference"].endswith("#capex")
        for row in rows
    )
    assert any(
        row["Evidence"] == "Boundary"
        and "production activation false" in row["Value"]
        and "readiness promotions none" in row["Value"]
        and "no persistence" in row["Value"]
        for row in rows
    )


def test_withheld_cash_preview_shows_no_numeric_or_component_evidence():
    preview = blocked_company_workbench_cash_generation_preview(
        "NVDA",
        fiscal_period="2027-Q1",
        as_of="2026-07-21T03:59:59+00:00",
        blockers=("complete_cash_generation_preview_required",),
    )

    cards = cash_generation_preview_cards(preview)
    rows = cash_generation_preview_rows(preview)

    assert [card["title"] for card in cards[1:]] == [
        "Withheld",
        "Withheld",
        "Withheld",
    ]
    assert all(card["state"] == "withheld" for card in cards[1:])
    assert "complete_cash_generation_preview_required" in str(cards)
    assert not any(row["Evidence"] == "Component" for row in rows)
    assert any(
        row["Evidence"] == "Blocker"
        and row["Value"] == "complete_cash_generation_preview_required"
        for row in rows
    )


def test_research_desk_answers_changes_attention_blockers_and_next_action_without_recommendations():
    cards = research_desk_cards(
        change_status="changes_detected",
        review_items=[object(), object()],
        readiness_summary={
            "master_universe": 25,
            "price_ready": 24,
            "dcf_ready": 12,
            "peer_ready": 5,
        },
    )

    assert [card["question"] for card in cards] == [
        "What changed?",
        "Which companies need attention?",
        "What is blocked or stale?",
        "What should I review next?",
    ]
    assert all(card["routing_state"] in RESEARCH_ROUTING_STATES for card in cards)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    assert "2 unresolved evidence changes" in rendered
    assert "discover" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "recommend" not in rendered


def test_company_workbench_contract_keeps_evidence_last():
    sections = company_workbench_section_contract()

    assert [section["title"] for section in sections] == [
        "Selected Company",
        "What Changed",
        "Business Trend",
        "Valuation",
        "Forward View",
        "What Remains Withheld",
        "Research Conclusion",
        "Next Research Task",
        "Advanced Evidence",
    ]
    assert sections[-1]["expanded"] is False
    assert "Data Health" in sections[-1]["contents"]
    assert "Proof History" in sections[-1]["contents"]


def test_company_change_answer_is_ticker_scoped_and_does_not_invent_change():
    event = SimpleNamespace(
        event_id="evt-nvda",
        ticker="NVDA",
        subtype="sec_filing_arrived",
        source_ref="sec:accession",
        evidence_status="source_backed",
        suggested_research_task="NVDA: Review the filing.",
    )
    item = SimpleNamespace(event=event, review_status="open", wait_condition="")

    changed = company_change_answer("NVDA", [item])
    unchanged = company_change_answer("MSFT", [item])

    assert changed["state"] == "review_now"
    assert changed["answer"] == "1 unresolved source-backed change needs review."
    assert changed["source_refs"] == ("sec:accession",)
    assert changed["source_backed_eligible"] is True
    assert unchanged["state"] == "monitor"
    assert unchanged["answer"] == "No unresolved source-backed change is queued for this company."
    assert unchanged["source_backed_eligible"] is False
    assert unchanged["change_context_kind"] == "none"


def test_cohort_trend_and_weekly_cards_keep_truthful_boundaries():
    member = FocusedCohortMember(
        "AAA", "A Co", "Technology", "Software", "Source-backed evidence.",
        ("price", "dcf"), ("peers",), "stale", "", "Review peer evidence.",
    )
    cohort = FocusedCohort("awaiting_reviewed_source", 25, 25, 1, (member,), "Only one eligible company.")
    trend = build_quarterly_trend_packet("AAA", [])
    weekly = WeeklyResearchSummary(
        "no_changes", "2026-07-17T00:00:00+00:00", 1, 0, (),
        "No traceable cohort evidence change requires review this week.",
    )

    cohort_cards = focused_cohort_cards(cohort)
    trend_cards = quarterly_trend_cards(trend)
    summary_cards = weekly_summary_cards(weekly)

    assert "1 of 25" in cohort_cards[0]["title"]
    assert cohort_cards[0]["state"] == "awaiting_reviewed_source"
    assert trend_cards[0]["state"] == "blocked"
    assert "No source-backed quarterly actual" in trend_cards[0]["body"]
    assert summary_cards[0]["state"] == "monitor"
    rendered = str(cohort_cards + trend_cards + summary_cards).lower()
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_quarterly_trend_cards_keep_cash_generation_withheld_without_reviewed_observations():
    packet = build_quarterly_trend_packet(
        "SYN1",
        [_quarterly_actual("2025-Q1", 120.0, 1.2)],
    )

    cards = quarterly_trend_cards(packet)
    by_kicker = {card["kicker"]: card for card in cards}

    assert by_kicker["OPERATING MARGIN"]["title"] == "Withheld"
    assert by_kicker["FREE CASH FLOW"]["title"] == "Withheld"
    assert by_kicker["FCF MARGIN"]["title"] == "Withheld"
    assert all(
        "reviewed" in by_kicker[kicker]["body"].lower()
        and "source adapter" in by_kicker[kicker]["body"].lower()
        for kicker in ("OPERATING MARGIN", "FREE CASH FLOW", "FCF MARGIN")
    )


def test_quarterly_trend_cards_show_cash_conversion_answer_without_raw_formula_or_sources():
    actuals = [
        _quarterly_actual("2024-Q1", 80.0, 0.8),
        _quarterly_actual("2024-Q4", 100.0, 1.0),
        _quarterly_actual("2025-Q1", 120.0, 1.2),
    ]
    values = {
        "2024-Q1": {"operating_income": 20.0, "cash_from_operations": 24.0, "capital_expenditures": -8.0},
        "2024-Q4": {"operating_income": 20.0, "cash_from_operations": 30.0, "capital_expenditures": -10.0},
        "2025-Q1": {"operating_income": 30.0, "cash_from_operations": 36.0, "capital_expenditures": -12.0},
    }
    observations = [
        _quarterly_business_observation(period, metric, value)
        for period, metrics in values.items()
        for metric, value in metrics.items()
    ]

    cards = quarterly_trend_cards(
        build_quarterly_trend_packet(
            "SYN1",
            actuals,
            business_observations=observations,
        )
    )
    by_kicker = {card["kicker"]: card for card in cards}

    assert by_kicker["OPERATING MARGIN"]["title"] == "25.0%"
    assert by_kicker["FREE CASH FLOW"]["title"] == "24"
    assert by_kicker["FCF MARGIN"]["title"] == "20.0%"
    assert "sequential +25.0%" in by_kicker["OPERATING MARGIN"]["body"]
    primary_text = str(cards).lower()
    assert "fixture:" not in primary_text
    assert "cash_from_operations" not in primary_text
    assert "capital_expenditures" not in primary_text
    assert "cfo +" not in primary_text


def test_focused_cohort_coverage_cards_answer_what_is_usable_without_overclaiming():
    coverage = FocusedCohortCoverage(
        status="partial",
        company_count=1,
        rows=(
            FocusedCohortCoverageRow("AAA", "Alpha", "adjusted_daily_price_history", "usable_now", "price", "boundary"),
            FocusedCohortCoverageRow("AAA", "Alpha", "quarterly_revenue", "blocked", "missing", "boundary"),
            FocusedCohortCoverageRow("AAA", "Alpha", "trusted_peers", "candidate_context_only", "candidate", "not trusted"),
        ),
        message="Mixed coverage.",
    )

    cards = focused_cohort_coverage_cards(coverage)

    assert cards[0]["title"] == "1 usable lane"
    assert cards[1]["title"] == "2 gated lanes"
    rendered = str(cards).lower()
    assert "candidate context" in rendered
    assert "research-only" in rendered


def test_focused_ticker_coverage_cards_keep_one_company_answer_concise():
    coverage = FocusedCohortCoverage(
        status="partial",
        company_count=1,
        rows=(
            FocusedCohortCoverageRow("AAA", "Alpha", "adjusted_daily_price_history", "usable_now", "price", "boundary"),
            FocusedCohortCoverageRow("AAA", "Alpha", "quarterly_revenue", "blocked", "missing", "boundary"),
            FocusedCohortCoverageRow("BBB", "Beta", "adjusted_daily_price_history", "usable_now", "price", "boundary"),
        ),
        message="Mixed coverage.",
    )

    cards = focused_ticker_coverage_cards(coverage, "AAA")

    assert cards[0]["title"] == "1 usable lane"
    assert cards[1]["title"] == "1 blocked lane"
    assert "BBB" not in str(cards)


def test_research_monitor_uses_review_queue_without_ranking_or_inventing_changes():
    event = SimpleNamespace(
        event_id="evt-1",
        ticker="NVDA",
        family="filing",
        subtype="sec_filing_arrived",
        materiality="medium",
        prior_value="000-old",
        current_value="000-new",
        source_published_at="2026-07-16T12:00:00Z",
        detected_at="2026-07-17T12:00:00Z",
        suggested_research_task="NVDA: Review the new SEC filing.",
        evidence_status="source_backed",
    )
    item = SimpleNamespace(
        event=event,
        priority=20,
        review_status="open",
        wait_condition="",
    )

    frame = research_monitor_frame([item])

    assert frame.to_dict("records") == [
        {
            "Ticker": "NVDA",
            "Change": "Sec Filing Arrived",
            "Previous state": "000-old",
            "Current state": "000-new",
            "Evidence": "source backed",
            "Affected section": "Filing",
            "Review state": "review_now",
            "Effective date": "2026-07-16T12:00:00Z",
            "Detected": "2026-07-17T12:00:00Z",
            "Next research task": "NVDA: Review the new SEC filing.",
            "Wait condition": "",
        }
    ]
    assert "Score" not in frame.columns
    assert "Rank" not in frame.columns


def test_research_monitor_deduplicates_identical_event_identity_and_preserves_wait_condition():
    event = SimpleNamespace(
        event_id="same-event",
        ticker="BLOCK",
        family="readiness",
        subtype="dcf_readiness_changed",
        materiality="high",
        prior_value="true",
        current_value="false",
        source_published_at="2026-07-16T00:00:00Z",
        detected_at="2026-07-17T00:00:00Z",
        suggested_research_task="BLOCK: Review DCF evidence.",
        evidence_status="source_backed",
    )
    item = SimpleNamespace(
        event=event,
        priority=10,
        review_status="still_blocked",
        wait_condition="Wait for a new source-backed filing.",
    )

    frame = research_monitor_frame([item, item])

    assert len(frame) == 1
    assert frame.iloc[0]["Review state"] == "wait_for_evidence"
    assert frame.iloc[0]["Wait condition"] == "Wait for a new source-backed filing."


def test_advanced_evidence_links_preserve_personal_research_mode_and_ticker():
    links = advanced_evidence_links("NVDA")

    assert links == [
        {
            "label": "Open Data Health",
            "href": "?mode=research&page=data-health&ticker=NVDA",
            "purpose": "Inspect blocked inputs and source-proof paths.",
        },
        {
            "label": "Open Proof History",
            "href": "?mode=research&page=proof-history&ticker=NVDA",
            "purpose": "Review evidence that changed a readiness state.",
        },
    ]


def test_research_evidence_links_encode_ticker_and_return_to_workbench_or_desk():
    assert advanced_evidence_links("BRK/B")[0]["href"].endswith("ticker=BRK%2FB")
    assert research_evidence_return_link("BRK/B") == {
        "label": "Return to Company Workbench",
        "href": "?mode=research&page=company-workbench&ticker=BRK%2FB&open=1",
        "purpose": "Continue the selected-company review without changing evidence state.",
    }
    assert research_evidence_return_link("") == {
        "label": "Return to Research Desk",
        "href": "?mode=research&page=research-desk",
        "purpose": "Return to the primary research workflow without changing evidence state.",
    }


def test_research_workspace_header_keeps_scope_freshness_action_and_boundary_visible():
    rendered = research_workspace_header_html(
        "Company Workbench",
        ticker="NVDA",
        profile_label="Local Research",
        freshness="Current through 2026-07-16",
        primary_action="Review source-backed sections",
    )

    assert "Company Workbench" in rendered
    assert "NVDA" in rendered
    assert "Local Research" in rendered
    assert "Current through 2026-07-16" in rendered
    assert "Review source-backed sections" in rendered
    assert "class='research-workspace-meta-item research-workspace-freshness'" in rendered
    assert "class='research-workspace-meta-item research-workspace-action'" in rendered
    assert "Research-only" in rendered
    assert "investment advice" in rendered


@pytest.mark.parametrize(
    "active_page",
    ("research-desk", "discover", "company-workbench", "monitor"),
)
def test_mobile_workflow_navigation_is_labelled_and_has_one_current_page(active_page):
    rendered = research_workspace.research_workflow_navigation_html(active_page=active_page, ticker="AVGO")

    assert "aria-label='Personal research workflow'" in rendered
    assert rendered.count("aria-current='page'") == 1
    assert all(label in rendered for label in ("Research Desk", "Discover", "Company Workbench", "Monitor"))
    assert "ticker=AVGO" in rendered
    assert "Company Workbench" not in research_workspace.research_workflow_navigation_html(
        active_page="discover",
    )


@pytest.mark.parametrize("active_page", ("data-health", "proof-history"))
def test_workflow_navigation_has_no_current_link_for_secondary_research_pages(active_page):
    rendered = research_workspace.research_workflow_navigation_html(active_page=active_page, ticker="AVGO")

    assert rendered.count("aria-current='page'") == 0


def test_research_workspace_header_labels_saved_readiness_without_changing_its_argument():
    rendered = research_workspace_header_html(
        "Research Desk",
        profile_label="Local Research",
        freshness="Current",
        primary_action="Open Discover",
    )

    assert "<dt>Saved readiness</dt>" in rendered
    assert "<dt>Freshness</dt>" not in rendered


def test_compact_research_workspace_header_keeps_identity_scope_and_boundary_without_duplicate_meta():
    rendered = research_workspace_header_html(
        "Company Workbench",
        ticker="NVDA",
        profile_label="Local Research",
        freshness="Current through 2026-07-16",
        primary_action="Review source-backed sections",
        compact=True,
    )

    assert "research-workspace-header compact" in rendered
    assert "<h1>Company Workbench</h1>" in rendered
    assert "NVDA" in rendered
    assert "Local Research" in rendered
    assert "Research-only" in rendered
    assert "investment advice" in rendered
    assert "Current through 2026-07-16" not in rendered
    assert "Review source-backed sections" not in rendered
    assert "research-workspace-meta" not in rendered


def test_research_desk_and_advanced_evidence_html_stay_answer_first_and_command_free():
    cards = research_desk_cards(
        change_status="no_changes",
        review_items=[],
        readiness_summary={"master_universe": 25, "price_ready": 24, "dcf_ready": 12, "peer_ready": 5},
    )
    desk_html = research_desk_cards_html(cards)
    evidence_html = advanced_evidence_links_html("NVDA")

    assert desk_html.count("research-desk-answer") == 4
    assert "What changed?" in desk_html
    assert "Open Discover" in desk_html
    assert "Open Data Health" in evidence_html
    assert "Open Proof History" in evidence_html
    assert "make " not in (desk_html + evidence_html).lower()
    assert "provider" not in (desk_html + evidence_html).lower()
