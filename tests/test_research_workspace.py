from types import SimpleNamespace

from src.research_workspace import (
    RESEARCH_ROUTING_STATES,
    advanced_evidence_links,
    advanced_evidence_links_html,
    company_workbench_section_contract,
    research_desk_cards,
    research_desk_cards_html,
    research_monitor_frame,
    research_workspace_header_html,
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
        "Business Trend",
        "Valuation",
        "Forward View",
        "Research Conclusion",
        "Advanced Evidence",
    ]
    assert sections[-1]["expanded"] is False
    assert "Data Health" in sections[-1]["contents"]
    assert "Proof History" in sections[-1]["contents"]


def test_research_monitor_uses_review_queue_without_ranking_or_inventing_changes():
    event = SimpleNamespace(
        ticker="NVDA",
        subtype="sec_filing_arrived",
        materiality="medium",
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
            "Evidence": "source backed",
            "Review state": "review_now",
            "Detected": "2026-07-17T12:00:00Z",
            "Next research task": "NVDA: Review the new SEC filing.",
        }
    ]
    assert "Score" not in frame.columns
    assert "Rank" not in frame.columns


def test_advanced_evidence_links_preserve_research_only_routing():
    links = advanced_evidence_links("NVDA")

    assert links == [
        {
            "label": "Open Data Health",
            "href": "?mode=operator&page=data-health&ticker=NVDA",
            "purpose": "Inspect blocked inputs and source-proof paths.",
        },
        {
            "label": "Open Proof History",
            "href": "?mode=public&page=proof-history&ticker=NVDA",
            "purpose": "Review evidence that changed a readiness state.",
        },
    ]


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
    assert "Research-only" in rendered
    assert "investment advice" in rendered


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
