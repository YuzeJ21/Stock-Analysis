import pandas as pd

from src import overview_workflow_console as workflow_console


def _render(cards: list[dict[str, object]] | list[dict[str, str]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_project_status_command_rows_prefer_structured_rows_and_normalize_commands():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Fix top prices blocker (NVDA)",
                "Command": "make focus-price TICKER=NVDA",
                "Reason": "Short local price history still blocks downstream work.",
                "SourceContext": "data/imports/prices.csv",
                "FreshnessContext": "2026-05-21",
            },
            {
                "Step": "Read-only status snapshot",
                "Command": "",
                "Reason": "Rebuild the local status snapshot before choosing a deeper workflow path.",
            },
        ],
        "recommended_next_commands": ["make onboarding", "make verify"],
    }

    rows = workflow_console.project_status_command_rows(payload)

    assert rows[0]["Step"] == "Fix top prices blocker (NVDA)"
    assert rows[0]["Command"] == "make focus-price TICKER=NVDA"
    assert rows[0]["SourceContext"] == "data/imports/prices.csv"
    assert rows[0]["FreshnessContext"] == "2026-05-21"
    assert rows[1]["Command"] == "make status-check TOP_N=5"


def test_project_status_command_rows_normalize_universe_preview_to_compact_summary():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Preview universe",
                "Command": "python3 -m src.universe_builder --preview --preset sp500_smh --max-tickers 50",
                "Reason": "Review source row counts before any apply step.",
            },
        ],
    }

    rows = workflow_console.project_status_command_rows(payload)

    assert rows[0]["Command"] == "make universe-preview-summary"


def test_top_priority_signals_keep_review_gates_visible():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            },
            {
                "priority": 2,
                "urgency": "high",
                "action_type": "prices",
                "ticker": "AMD",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make price-validate",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            },
        ]
    )

    signals = workflow_console.top_priority_signals(queue, limit=2)
    rendered = _render(signals)

    assert signals[0]["command"] == "make imports-validate"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert signals[1]["command"] == "make price-validate"
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "use local import draft workflows if the free refresh fails" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_workflow_path_cards_use_structured_steps_and_source_context():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Fix top prices blocker (META)",
                "Command": "make focus-price TICKER=META",
                "Reason": "Provider rows could not be parsed cleanly, so price coverage is still the top blocker.",
                "SourceContext": "data/imports/prices.csv",
                "FreshnessContext": "2026-05-21",
            },
            {
                "Step": "Review fundamentals import file",
                "Command": "make imports-validate",
                "Reason": "Fundamentals import file rows already exist and should be validated before preview/apply.",
            },
        ]
    }

    cards = workflow_console.overview_workflow_path_cards(payload, None)
    rendered = _render(cards)

    assert cards[0]["title"] == "make focus-price TICKER=META"
    assert cards[1]["title"] == "make imports-validate"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "source: data/imports/prices.csv" in rendered
    assert "source readiness: 2026-05-21" in rendered


def test_overview_workflow_path_cards_use_action_queue_then_verify_then_dashboard():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )

    cards = workflow_console.overview_workflow_path_cards(None, queue)

    assert cards[0]["title"] == "make runbook-peers"
    assert cards[1]["title"] == "make verify"
    assert cards[2]["title"] == "make dashboard-smoke"
    assert "guided data batch" in cards[0]["body"].lower()


def test_overview_workflow_reason_card_uses_queue_context_safely():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "NVDA update failed during remote refresh.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "example_command": "make price-worklist",
            }
        ]
    )

    card = workflow_console.overview_workflow_reason_card(None, queue)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make price-worklist"
    assert "nvda" in rendered
    assert "normalize verified downloaded ohlcv rows" in rendered
    assert "make price-preview" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
