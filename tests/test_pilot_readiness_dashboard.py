import pandas as pd

from src.dashboard import data_health_pilot_readiness_cards


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
