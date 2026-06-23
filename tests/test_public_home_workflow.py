from src.public_home_workflow import (
    public_home_current_data_coverage_cards,
    public_home_first_30_second_cards,
    public_home_loop_cards,
    public_home_next_step_cards,
    public_home_real_workflow_cards,
    public_home_review_map_cards,
    public_home_route_choice_cards,
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
    assert "home -> stock selector -> one ticker -> data health -> proof history" in rendered
    assert "stock selector filters readiness-backed candidates" in rendered
    assert "proof history is checked before trusting a changed state" in rendered
    assert "blocked states remain visible" in rendered
    assert "blocked or excluded instead of filling the gap" in rendered
    assert "make " not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_public_home_real_workflow_cards_connect_pages_without_demo_framing():
    cards = public_home_real_workflow_cards(
        {
            "price_ready": 3538,
            "dcf_ready": 59,
            "peer_ready": 26,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["WORKFLOW 1", "WORKFLOW 2", "WORKFLOW 3", "WORKFLOW 4"]
    assert "start with the live readiness snapshot" in rendered
    assert "3,538 price-ready, 59 dcf-ready, and 26 peer-ready" in rendered
    assert "review one ticker from the current state" in rendered
    assert "workflow also works for any local ticker" in rendered
    assert "route locked sections to data health" in rendered
    assert "3,479 price-ready names still need trusted fundamentals" in rendered
    assert "33 dcf-ready names still need peer inputs" in rendered
    assert "record proof before trusting a changed state" in rendered
    assert "demo" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_public_home_next_step_cards_are_copyable_and_readiness_gated():
    price_gap_cards = public_home_next_step_cards(
        {
            "master_universe": 100,
            "price_ready": 20,
            "dcf_ready": 2,
            "peer_ready": 1,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    fundamentals_cards = public_home_next_step_cards(
        {
            "master_universe": 100,
            "price_ready": 100,
            "dcf_ready": 1,
            "peer_ready": 1,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    peer_cards = public_home_next_step_cards(
        {
            "master_universe": 100,
            "price_ready": 100,
            "dcf_ready": 10,
            "peer_ready": 1,
            "earnings_ready": 1,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(
        str(value)
        for card in price_gap_cards + fundamentals_cards + peer_cards
        for value in card.values()
    ).lower()

    assert price_gap_cards[0]["command"] == "make price-refresh-loop DRY_RUN=1"
    assert fundamentals_cards[0]["command"] == "make sec-stage-queue TOP_N=25"
    assert peer_cards[0]["command"] == "make peer-mapping-queue TOP_N=25"
    assert price_gap_cards[1]["command"] == "make stock-report-md TICKER=NVDA"
    assert price_gap_cards[2]["command"] == "make data-wizard TOP_N=10"
    assert price_gap_cards[3]["command"] == "make optional-context-worklist TOP_N=25"
    assert price_gap_cards[4]["command"] == "make readiness && make status-check TOP_N=5"
    assert price_gap_cards[5]["command"] == "make trusted-data-pilot-candidates TOP_N=10"
    assert price_gap_cards[5]["title"] == "Improve 5-10 companies first"
    assert "read-only candidate list" in price_gap_cards[5]["body"]
    assert "Inspect one company packet before applying rows" in price_gap_cards[5]["body"]
    assert "keep the ticker visibly blocked" in price_gap_cards[5]["body"]
    assert "make trusted-data-pilot-candidates TOP_N=10" not in price_gap_cards[5]["body"]
    assert "make trusted-data-pilot-packet TICKER=CRDO" not in price_gap_cards[5]["body"]
    assert "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10" not in price_gap_cards[5]["body"]
    assert "scalable dry run" in rendered
    assert "instead of repeating 25-ticker refreshes manually" in rendered
    assert "blocked rows are useful, but they are a missing-data list, not a conclusion list" in rendered
    assert "no data, no conclusion" in rendered
    assert "earnings and analyst estimates are not broken" in rendered
    assert "optional context is available" in rendered
    assert "prove the new state before reading conclusions" in rendered
    assert "rerun readiness before interpreting changed cards" in rendered
    assert "review the local status snapshot and reopen home" in rendered
    assert "do not try to make the full universe analysis-ready at once" in rendered
    assert "small trusted-data pilot" in rendered
    assert "source proof is missing" in rendered
    assert "move to the next candidate" in rendered
    assert "use make readiness" not in rendered
    assert "run make readiness" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_public_home_current_data_coverage_cards_show_public_snapshot_and_unlock_paths():
    cards = public_home_current_data_coverage_cards(
        {
            "master_universe": 3538,
            "active_universe": 12,
            "price_ready": 240,
            "momentum_ready": 237,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 9,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
            "blocked_by_data": 3298,
            "partial": 240,
            "updated_at": "2026-06-06T00:00:00+00:00",
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "CURRENT SNAPSHOT",
        "BREADTH",
        "DEPTH",
        "RELATIVE CONTEXT",
        "OPTIONAL CONTEXT",
    ]
    assert "3,538 tracked / 12 active" in rendered
    assert "240 tickers have partial coverage and 3,298 are blocked by data" in rendered
    assert "price: 240/3,538 ready (6.8%)" in rendered
    assert "momentum: 237/3,538 ready (6.7%)" in rendered
    assert "fundamentals: 23/3,538 ready (0.7%)" in rendered
    assert "dcf: 23/3,538 ready (0.7%)" in rendered
    assert "peers: 9/3,538 ready (0.3%)" in rendered
    assert "earnings: 0/3,538 ready (0.0%)" in rendered
    assert "analyst estimates: 0/3,538 ready (0.0%)" in rendered
    assert "zero ready rows means intentionally locked" in rendered
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make optional-context-worklist top_n=25" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_public_home_current_data_coverage_cards_show_timestamp_fallback():
    cards = public_home_current_data_coverage_cards({"master_universe": 10, "updated_at": None})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "snapshot timestamp: run make readiness for the latest timestamp" in rendered


def test_public_home_review_map_cards_show_current_step_next_action_and_stop_rule():
    cards = public_home_review_map_cards(
        {
            "master_universe": 3538,
            "price_ready": 3538,
            "dcf_ready": 59,
            "peer_ready": 26,
            "blocked_by_data": 3479,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "CURRENT STEP",
        "REVIEW NOW",
        "NEXT SAFE ACTION",
        "STOP RULE",
    ]
    assert "start from the readiness snapshot" in rendered
    assert "3,538/3,538 tracked names have price coverage" in rendered
    assert "59 names are dcf-ready and 26 are peer-ready" in rendered
    assert "single-stock report starts with what can be reviewed now" in rendered
    assert "3,479 blocked states remain source-proof work" in rendered
    assert "manual gate, proof packet, and stop rule together" in rendered
    assert "do not conclude from missing inputs" in rendered
    assert "stays blocked or excluded until reviewed proof exists" in rendered
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
        "Choose a candidate, then open one ticker",
        "Route locks to Data Health",
        "Trust only after proof",
    ]
    assert "3,538/3,538 tracked names have price coverage" in rendered
    assert "what the local data can support today" in rendered
    assert "stock selector narrows readiness-backed candidates" in rendered
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


def test_public_home_route_choice_cards_warn_when_candidate_pages_should_stay_empty():
    cards = public_home_route_choice_cards(
        {
            "master_universe": 25,
            "price_ready": 0,
            "dcf_ready": 0,
            "peer_ready": 0,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card).lower()

    assert cards[0][0] == "Review one stock"
    assert cards[1][0] == "Explore ready names"
    assert cards[1][3] == "warning"
    assert cards[2][0] == "Check data coverage"
    assert cards[2][3] == "warning"
    assert "choose any local ticker" in rendered
    assert "ready, blocked, excluded, or monitor-only" in rendered
    assert "open proof history first" in rendered
    assert "candidate pages should stay empty when local data cannot support them" in rendered
    assert "25 ticker(s) still need price coverage" in rendered
    assert "make " not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
