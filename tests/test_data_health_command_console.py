import pandas as pd

from src import data_health_command_console as command_console


def _render(cards: list[dict[str, object]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_command_bundle_cards_surface_bundle_commands_safely():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 2,
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "bundle_shortcut_command": "make bundle-prices",
                "primary_command": "python3 -m src.data_update --tickers AMD,AVGO",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = command_console.command_bundle_cards(bundles)
    rendered = _render(cards)

    assert cards[0]["kicker"] == "PRICES"
    assert cards[0]["command"] == "make bundle-prices"
    assert "holdings first" in rendered
    assert "unlock monthly picks" in rendered
    assert "21 target rows" in rendered
    assert "start by 2025-12-01" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_command_bundle_cards_use_staged_follow_through_when_summary_is_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "runbook_shortcut_command": "make runbook-fundamentals",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = command_console.command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_command_bundle_runbook_cards_normalize_and_keep_review_gates_visible():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "python3 -m src.data_update --tickers META",
                "target_file": "data/imports/prices.csv",
                "tickers": "META",
                "goal_summary": "",
                "safe_next_step": "",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Review import file",
                "command": "make price-validate",
                "target_file": "data/imports/prices.csv",
                "tickers": "META",
                "goal_summary": "",
                "safe_next_step": "",
            },
        ]
    )

    cards = command_console.command_bundle_runbook_cards(runbook)
    rendered = _render(cards)

    assert cards[0]["kicker"] == "PRICES STEPS"
    assert cards[0]["command"] == "make price-refresh TICKERS=META"
    assert "make price-refresh tickers=meta" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered


def test_overview_command_bundle_cards_use_lane_runbook_fallback():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "ticker_count": 1,
                "tickers": "TSLA",
                "goal_summary": "",
                "why_it_matters": "",
            }
        ]
    )

    cards = command_console.overview_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-peers-broader"
    assert "guided data batch" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_bundle_runbook_cards_surface_compact_lane_steps():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "python3 -m src.data_update --tickers META",
                "tickers": "META",
                "goal_summary": "Unlock Monthly Picks for 1 ticker; 21 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "If refresh fails, normalize first CSV",
                "command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
                "tickers": "META",
                "goal_summary": "Unlock Monthly Picks for 1 ticker; 21 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
            },
        ]
    )

    cards = command_console.overview_bundle_runbook_cards(runbook)
    rendered = _render(cards)

    assert cards[0]["kicker"] == "PRICES LANE"
    assert cards[0]["command"] == "make price-refresh TICKERS=META"
    assert "21 target rows" in rendered
    assert "start by 2025-12-01" in rendered
    assert "make price-normalize input=data/raw/prices/meta.csv ticker=meta source=yahoo_manual" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_bundle_handoff_cards_keep_staged_follow_through_visible():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "follow_up_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = command_console.overview_bundle_handoff_cards(bundles, None, None)
    rendered = _render(cards)

    assert cards[0]["command"] == "make sec-stage TICKERS=META,NVDA,TSLA"
    assert cards[1]["command"] == "make imports-validate"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered


def test_overview_bundle_handoff_cards_use_runbook_follow_through_and_refresh():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "follow_up_command": "",
            }
        ]
    )
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Review follow-up output",
                "command": "make imports-validate",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "Refresh status outputs",
                "command": "make status",
            },
        ]
    )

    cards = command_console.overview_bundle_handoff_cards(bundles, None, runbook)

    assert cards[1]["command"] == "make imports-validate"
    assert cards[2]["title"] == "Refresh status outputs"
    assert cards[2]["command"] == "make status-check TOP_N=5"


def test_overview_bundle_handoff_cards_route_monthly_price_refresh():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 57 verified rows still needed across this bundle",
                "primary_command": "make bundle-prices",
                "follow_up_command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )
    details = pd.DataFrame([{"bundle_name": "Price Coverage Bundle", "ticker": "META"}])

    cards = command_console.overview_bundle_handoff_cards(bundles, details, None)
    rendered = _render(cards)

    assert cards[2]["title"] == "Refresh monthly context"
    assert cards[2]["command"] == "make monthly"
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered


def test_overview_bundle_handoff_cards_surface_peer_manual_follow_through():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
                "primary_command": "make templates",
                "follow_up_command": "data/imports/peers.csv",
                "target_file": "data/imports/peers.csv",
                "safe_next_step": "Fill only manually researched peers for the listed tickers, then run make imports-validate, make imports-preview, and make imports-apply before make status refreshes readiness and action outputs.",
            }
        ]
    )
    details = pd.DataFrame([{"bundle_name": "Peer Mapping Bundle", "ticker": "META"}])

    cards = command_console.overview_bundle_handoff_cards(bundles, details, None)
    rendered = _render(cards)

    assert cards[0]["kicker"] == "PEERS HANDOFF"
    assert cards[1]["command"] == "data/imports/peers.csv"
    assert "make templates" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
