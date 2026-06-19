from src.public_home_workflow import (
    public_home_first_30_second_cards,
    public_home_loop_cards,
    public_home_visitor_path_cards,
)


def test_public_home_first_30_second_cards_explain_product_without_operator_detail():
    cards = public_home_first_30_second_cards(
        {
            "master_universe": 3538,
            "price_ready": 3538,
            "dcf_ready": 59,
            "peer_ready": 26,
            "blocked_by_data": 3479,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["WHAT THIS IS", "HOW TO READ IT", "WHEN TO STOP"]
    assert "a readiness-first research workflow" in rendered
    assert "ready, blocked, partial, and excluded states stay visible" in rendered
    assert "3,538/3,538 price-ready" in rendered
    assert "59 names are dcf-ready and 26 are peer-ready today" in rendered
    assert "single-stock report for one ticker" in rendered
    assert "data health for source-proof gaps" in rendered
    assert "3,479 blocked states remain withheld" in rendered
    assert "keeps the conclusion unavailable" in rendered
    assert "make " not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_public_home_loop_cards_connect_public_workflow_without_commands_or_advice():
    cards = public_home_loop_cards(
        {
            "master_universe": 3538,
            "price_ready": 3538,
            "dcf_ready": 59,
            "peer_ready": 26,
            "blocked_by_data": 3479,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["READ THIS FIRST", "CONNECTED PATH", "STOP RULE"]
    assert "3,538/3,538 tracked names have price coverage" in rendered
    assert "59 are dcf-ready and 26 are peer-ready" in rendered
    assert "home -> one ticker -> data health -> proof history" in rendered
    assert "proof history is checked before trusting a changed state" in rendered
    assert "blocked states remain visible" in rendered
    assert "blocked or excluded instead of filling the gap" in rendered
    assert "make " not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_public_home_visitor_path_cards_show_four_step_public_loop_without_operator_detail():
    cards = public_home_visitor_path_cards(
        {
            "master_universe": 3538,
            "price_ready": 3538,
            "dcf_ready": 59,
            "peer_ready": 26,
            "blocked_by_data": 3479,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["STEP 1", "STEP 2", "STEP 3", "STEP 4"]
    assert [card["title"] for card in cards] == [
        "Start with readiness",
        "Open one ticker",
        "Route locks to Data Health",
        "Trust only after proof",
    ]
    assert "3,538/3,538 tracked names have price coverage" in rendered
    assert "what the local data can support today" in rendered
    assert "selected ticker" in rendered
    assert "where data health fits next" in rendered
    assert "3,479 blocked states stay visible" in rendered
    assert "without making visitors read raw csv tables first" in rendered
    assert "59 dcf-ready and 26 peer-ready" in rendered
    assert "changed states need rebuilt readiness and proof history before interpretation" in rendered
    assert "make " not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
