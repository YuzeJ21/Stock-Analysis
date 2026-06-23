from types import SimpleNamespace

import pandas as pd

from src import data_health_overview_console as overview_console


def test_overview_orientation_cards_frame_proof_workflow_without_advice_language():
    cards = overview_console.orientation_cards(
        {
            "price_ready": 586,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT THIS MEANS",
        "WHAT YOU CAN ANALYZE NOW",
        "WHAT IS STILL LOCKED",
    ]
    assert "not an error page" in rendered
    assert "586 price-ready / 23 fundamentals-ready / 23 dcf-ready" in rendered
    assert "the app does not infer these inputs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_quick_read_cards_prioritize_first_unlocked_lane():
    cards = overview_console.quick_read_cards(
        {
            "price_ready": 240,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["FIRST READ", "ANALYZE NOW", "STILL LOCKED"]
    assert cards[0]["title"] == "Prove fundamentals before valuation"
    assert cards[0]["command"] == "make sec-stage-queue TOP_N=25"
    assert "217 price-ready row(s) still need trusted fundamentals" in rendered
    assert "not a negative company signal" in rendered
    assert "do not read locked sections as weak conclusions" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_public_visitor_path_cards_are_plain_language():
    cards = overview_console.public_visitor_path_cards(
        {
            "price_ready": 3536,
            "dcf_ready": 27,
            "peer_ready": 26,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card).lower()

    assert [card[0] for card in cards] == ["Review one stock", "Check data coverage", "Inspect proof"]
    assert [card[2] for card in cards] == ["Single-Stock Report", "Data Health", "Proof History"]
    assert "3,536 price-ready" in rendered
    assert "stop if source rows, freshness, or proof history are missing" in rendered
    assert "operator detail stays behind deeper drawers by default" in rendered
    assert "make " not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_public_first_30_second_cards_summarize_ready_blocked_and_proof_boundary():
    cards = overview_console.public_first_30_second_cards(
        {
            "price_ready": 3538,
            "fundamentals_ready": 59,
            "dcf_ready": 59,
            "peer_ready": 26,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["READY NOW", "STILL BLOCKED", "PROOF BOUNDARY"]
    assert "3,538 price / 59 dcf / 26 peer-ready" in rendered
    assert "3,479 names need trusted fundamentals" in rendered
    assert "blocked rows are not weak conclusions" in rendered
    assert "operator mode keeps validate, preview, apply" in rendered
    assert "research-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_operations_cockpit_cards_keep_stale_and_proof_hygiene_visible():
    ops = pd.DataFrame(
        [
            {"Lane": "Price coverage", "Workflow Mode": "safe_to_batch_dry_run"},
            {"Lane": "Fundamentals / DCF proof", "Workflow Mode": "review_only"},
            {"Lane": "Earnings locked lane", "Workflow Mode": "locked_manual"},
        ]
    )
    frontier = pd.DataFrame(
        [
            {
                "Lane": "Price coverage",
                "Unlock Impact": 3273,
                "Possible State Move": "blocked -> partial after verified local price rows",
                "Next Safe Command": "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo",
            }
        ]
    )
    earnings = pd.DataFrame([{"ticker": "NVDA", "has_trusted_earnings": False}, {"ticker": "A", "has_trusted_earnings": True}])
    estimates = pd.DataFrame(
        [{"ticker": "NVDA", "has_trusted_analyst_estimates": False}, {"ticker": "A", "has_trusted_analyst_estimates": False}]
    )

    cards = overview_console.operations_cockpit_cards(
        {"price_ready": 265, "dcf_ready": 23, "peer_ready": 9},
        ops,
        frontier,
        earnings,
        estimates,
        SimpleNamespace(
            status="stale",
            message="Readiness artifacts may be stale because source file(s) changed.",
            refresh_command="make readiness",
        ),
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "READINESS FRESHNESS",
        "OPS COCKPIT",
        "NEXT FRONTIER",
        "OPTIONAL CONTEXT",
        "PROOF HYGIENE",
    ]
    assert cards[0]["title"] == "Stale"
    assert cards[2]["command"] == "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo"
    assert "top data-lane opportunity has unlock impact 3273" in rendered
    assert "treat stale or missing readiness artifacts as a stop sign" in rendered
    assert "validate, preview, apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_freshness_routine_cards_are_dry_run_first():
    cards = overview_console.freshness_routine_cards({"master_universe": 3538, "price_ready": 265})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "READ-ONLY ROUTINE",
        "PRICE FRESHNESS",
        "REVIEW-REQUIRED LANES",
    ]
    assert cards[1]["command"] == "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3300 TOP_N=100 PROVIDER=yahoo"
    assert "without changing files" in rendered
    assert "run a real loop only after reviewing the dry-run plan" in rendered
    assert "validation, preview, rejected-row checks, and readiness rebuilds" in rendered
    assert "broker" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
