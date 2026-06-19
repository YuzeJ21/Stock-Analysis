import pandas as pd

from src.dashboard import (
    data_health_pilot_packet_cards,
    data_health_pilot_readiness_cards,
    data_health_pilot_reviewer_walkthrough_cards,
    data_health_pilot_reviewer_walkthrough_frame,
    data_health_pilot_reviewer_walkthrough_strip_html,
)


def test_data_health_pilot_readiness_cards_surface_verdict_and_priority_gates():
    frame = pd.DataFrame(
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
                "Status": "blocked",
                "Gate": "Readiness artifacts are stale",
                "Detail": "Run make readiness before relying on final counts.",
                "Command": "make readiness",
                "Stop Rule": "Stop before quoting final counts.",
            },
        ]
    )

    cards = data_health_pilot_readiness_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert cards[0]["title"] == "Blocked before pilot"
    assert "1 green gate" in cards[0]["body"]
    assert "1 manual gate" in cards[0]["body"]
    assert "1 blocked gate" in cards[0]["body"]
    assert cards[1]["title"] == "Readiness freshness"
    assert "make readiness" in rendered
    assert "generated artifact hygiene" in rendered
    assert "recommendation" not in rendered


def test_data_health_pilot_readiness_cards_empty_state_is_copy_only():
    cards = data_health_pilot_readiness_cards(pd.DataFrame())
    rendered = " ".join(str(card) for card in cards).lower()

    assert cards[0]["command"] == "make pilot-readiness-check TOP_N=10"
    assert "read-only" in rendered
    assert "pilot gate" in rendered


def test_data_health_pilot_packet_cards_are_copy_only_and_show_packet_path():
    frame = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "manual"},
            {"Area": "Research guardrails", "Status": "green"},
        ]
    )

    cards = data_health_pilot_packet_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert cards[0]["command"] == "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md"
    assert "outputs/pilot_readiness_packet.md" in rendered
    assert "does not refresh data or apply rows" in rendered
    assert "manual gates visible" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_pilot_reviewer_walkthrough_wraps_compact_path():
    pilot = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "green", "Detail": "main is synced.", "Command": "git status --short --branch", "Stop Rule": "Stop if branch diverges."},
            {"Area": "Generated artifact hygiene", "Status": "manual", "Detail": "Generated churn is excluded.", "Command": "make diff-hygiene-summary", "Stop Rule": "Do not stage broad generated churn."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 100,
                "Blocked": 90,
                "Top Blockers": "fundamentals_bundle_plus_shares: 90",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
                "Stop Rule": "Stop if source proof is unavailable.",
            }
        ]
    )

    frame = data_health_pilot_reviewer_walkthrough_frame(pilot, queues)
    cards = data_health_pilot_reviewer_walkthrough_cards(frame)
    strip = data_health_pilot_reviewer_walkthrough_strip_html(frame)
    rendered = " ".join(str(card) for card in cards).lower()
    rendered_strip = strip.lower()

    assert "one compact path before raw tables" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "make public-check" in rendered
    assert "copy-only" in rendered
    assert "pilot-flow" in rendered_strip
    assert "trusted fundamentals proof queue" in rendered_strip
    assert "make dcf-input-source-command-plan" in rendered_strip
