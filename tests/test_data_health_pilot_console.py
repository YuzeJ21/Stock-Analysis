from pathlib import Path

import pandas as pd

from src import data_health_pilot_console as pilot_console


def _pilot_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Area": "GitHub sync",
                "Status": "green",
                "Gate": "GitHub branch state",
                "Detail": "main is synced.",
                "Command": "git status --short --branch",
                "Stop Rule": "Stop if the branch diverges.",
            },
            {
                "Area": "Generated artifact hygiene",
                "Status": "manual",
                "Gate": "Dirty tree classification",
                "Detail": "25 generated CSV artifacts are dirty and excluded by default.",
                "Command": "make diff-hygiene-summary",
                "Stop Rule": "Do not stage broad generated churn.",
            },
            {
                "Area": "Readiness freshness",
                "Status": "green",
                "Gate": "Readiness artifacts are current",
                "Detail": "Readiness artifacts are current.",
                "Command": "make status-check TOP_N=5",
                "Stop Rule": "Stop before quoting stale counts.",
            },
        ]
    )


def _proof_queue_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 3472,
                "Ready": 59,
                "Partial": 21,
                "Blocked": 3458,
                "Top Blockers": "fundamentals_bundle_plus_shares: 3459",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
                "Stop Rule": "Stop if revenue, free cash flow, FCF margin, or share-count proof is unavailable.",
            },
            {
                "Queue": "Peer Valuation Input Proof Queue",
                "State": "partial",
                "Queued Rows": 19,
                "Ready": 7,
                "Partial": 0,
                "Blocked": 19,
                "Top Blockers": "peer fundamentals: 19",
                "Next Safe Command": "make peer-mapping-queue TOP_N=25",
                "Stop Rule": "Stop if mapped peers lack trusted valuation-input rows.",
            },
        ]
    )


def test_pilot_cards_remain_copy_only_and_research_safe():
    cards = pilot_console.pilot_readiness_cards(_pilot_frame())
    packet = pilot_console.pilot_packet_cards(_pilot_frame(), output_path=Path("outputs/pilot_readiness_packet.md"))
    rendered = " ".join(str(card) for card in cards + packet).lower()

    assert cards[0]["title"] == "Pilot-ready with manual gates"
    assert "generated artifact hygiene" in rendered
    assert "outputs/pilot_readiness_packet.md" in rendered
    assert "does not refresh data or apply rows" in rendered
    assert "research-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pilot_reviewer_walkthrough_uses_deferred_proof_queue_when_fast_view():
    frame = pilot_console.pilot_reviewer_walkthrough_frame(_pilot_frame(), pd.DataFrame())
    cards = pilot_console.pilot_reviewer_walkthrough_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Stage"]) == [
        "Pilot status",
        "Manual gate to clear",
        "Source-proof focus",
        "Reviewer packet",
        "Public boundary",
    ]
    assert frame.iloc[1]["What Reviewer Sees"] == "Generated artifact hygiene"
    assert frame.iloc[2]["What Reviewer Sees"] == "Load source-proof queues"
    assert "switch readiness queue detail level to review details" in rendered
    assert "raw csv rows" in rendered
    assert "recommendation" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pilot_reviewer_walkthrough_promotes_largest_source_proof_blocker():
    frame = pilot_console.pilot_reviewer_walkthrough_frame(_pilot_frame(), _proof_queue_frame())
    cards = pilot_console.pilot_reviewer_walkthrough_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    source_row = frame[frame["Stage"] == "Source-proof focus"].iloc[0]

    assert source_row["What Reviewer Sees"] == "Trusted Fundamentals Proof Queue"
    assert "3,458 blocked item" in source_row["Evidence"]
    assert "fundamentals_bundle_plus_shares" in source_row["Evidence"]
    assert source_row["Next Safe Action"] == "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10"
    assert "trusted fundamentals proof queue" in rendered
    assert "public-check" in rendered
    assert "broad generated churn stays excluded" in rendered


def test_pilot_reviewer_walkthrough_strip_is_compact_and_safe():
    frame = pilot_console.pilot_reviewer_walkthrough_frame(_pilot_frame(), _proof_queue_frame())
    html = pilot_console.pilot_reviewer_walkthrough_strip_html(frame)
    rendered = html.lower()

    assert "pilot-flow" in rendered
    assert "pilot workflow" in rendered
    assert "gate, proof focus, packet, and public-check before raw tables" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "make pilot-readiness-packet" in rendered
    assert "make public-check" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_operator_next_action_summary_answers_first_screen_questions():
    frame = pilot_console.operator_next_action_summary_frame(_pilot_frame(), _proof_queue_frame())
    cards = pilot_console.operator_next_action_summary_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Question"]) == [
        "Can this be piloted?",
        "What is the main manual gate?",
        "What blocks deeper analysis?",
        "What should stay hidden first?",
    ]
    assert frame.iloc[0]["Answer"] == "Pilot-ready with manual gates"
    assert frame.iloc[1]["Answer"] == "Generated artifact hygiene"
    assert frame.iloc[2]["Answer"] == "Trusted Fundamentals Proof Queue"
    assert frame.iloc[3]["Answer"] == "Raw tables and proof commands"
    assert "make dcf-input-source-command-plan" in rendered
    assert "validate, preview, rejected-row review" in rendered
    assert "copy-only" in rendered
    assert "research-only" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "advice" not in rendered


def test_operator_next_action_summary_deferred_state_stays_copy_only():
    frame = pilot_console.operator_next_action_summary_frame(_pilot_frame(), pd.DataFrame())
    cards = pilot_console.operator_next_action_summary_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert frame.iloc[2]["Answer"] == "Load source-proof queues"
    assert frame.iloc[2]["Status"] == "deferred"
    assert "review details before editing any data rows" in rendered
    assert "make data-coverage-proof-queues top_n=10" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
