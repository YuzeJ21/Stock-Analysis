from src.single_stock_workflow import (
    single_stock_data_health_handoff_cards,
    single_stock_next_command,
    single_stock_pre_report_contract_cards,
    single_stock_report_data_health_route,
    single_stock_workflow_command_rows,
    single_stock_workflow_fit_cards,
    single_stock_workflow_loop_cards,
)

import pandas as pd


def _render(cards: list[dict[str, object]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_single_stock_workflow_fit_cards_connect_review_scope_handoff_and_stop_rule():
    snapshot = {
        "ticker": "NVDA",
        "status": "partial",
        "asset_type": "company",
        "decision_bucket": "Research Now",
        "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "missing_data": "peers: needs source-backed mappings",
    }

    cards = single_stock_workflow_fit_cards(snapshot)
    rendered = _render(cards)

    assert [card["kicker"] for card in cards] == [
        "ANSWER FIRST",
        "REVIEW NOW",
        "BLOCKED / EXCLUDED",
        "NEXT SAFE STEP",
        "STOP RULE",
    ]
    assert cards[0]["title"] == "NVDA - partial"
    assert "use now:" in rendered
    assert "blocked/context:" in rendered
    assert "data health only if blocked/freshness:" in rendered
    assert "manual review boundary:" in rendered
    assert "next safe action:" not in rendered
    assert "read this first before detailed review" in rendered
    assert "previous proof comes from the saved readiness checks" in rendered
    assert "standalone dcf assumptions and source readiness can be reviewed" in rendered
    assert "peer-relative valuation remains locked" in rendered
    assert "open data health peer lane" in rendered
    assert "open peers source-proof lane only for the blocked or freshness question" in rendered
    assert "stop if peer mappings or peer valuation inputs lack source-backed rows" in rendered
    assert "commands stay in operator details" in rendered
    assert "copy-only" not in rendered
    assert "do not treat locked, partial, or excluded sections as conclusions" in rendered
    assert "make focus-peers ticker=nvda" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_data_health_handoff_cards_route_locked_inputs_to_matching_lane():
    snapshot = {
        "ticker": "MU",
        "status": "partial",
        "asset_type": "company",
        "decision_bucket": "Research Now",
        "decision_subtype": "Standalone DCF ready; peers gated",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "missing_data": "peer valuation inputs",
    }

    cards = single_stock_data_health_handoff_cards(snapshot)
    rendered = _render(cards)

    assert [card["kicker"] for card in cards] == [
        "ANSWER FIRST",
        "CURRENT REPORT",
        "LOCKED INPUTS",
        "OPEN DATA HEALTH",
        "STOP RULE",
    ]
    assert cards[0]["title"] == "Use this report first"
    assert "use now: standalone dcf context can be reviewed from trusted local inputs" in rendered
    assert "blocked: peer-relative context stays blocked until mappings and peer valuation inputs are source-backed" in rendered
    assert "next proof: open data health only for peers source-proof lane" in rendered
    assert "open data health only for peers source-proof lane" in rendered
    assert "proof history is evidence review, not a second report" in rendered
    assert cards[1]["title"] == "MU: partial"
    assert "what can be reviewed now: standalone dcf context can be reviewed" in rendered
    assert "peer-relative context stays blocked" in rendered
    assert "peers source-proof lane" in rendered
    assert "?mode=operator&page=data-health&lane=peers&drawer=source-proof" in rendered
    assert "dashboard does not write canonical data" in rendered
    assert "make focus-peers ticker=mu" in rendered
    assert "do not turn missing, partial, locked, or excluded inputs into conclusions" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_data_health_handoff_cards_cover_missing_price_and_monitor_states():
    missing = {
        "ticker": "ZZZ",
        "status": "missing",
        "next_action": "Stage or refresh universe metadata, then run make universe-report and make readiness.",
    }
    price_blocked = {
        "ticker": "APLD",
        "status": "blocked",
        "asset_type": "company",
        "price_ready": False,
        "dcf_status": "blocked",
    }
    monitor = {
        "ticker": "QQQ",
        "status": "partial",
        "asset_type": "etf",
        "price_ready": True,
        "dcf_status": "excluded",
    }

    missing_rendered = _render(single_stock_data_health_handoff_cards(missing))
    price_rendered = _render(single_stock_data_health_handoff_cards(price_blocked))
    monitor_rendered = _render(single_stock_data_health_handoff_cards(monitor))
    rendered = missing_rendered + price_rendered + monitor_rendered

    assert "universe and readiness refresh" in missing_rendered
    assert "stop until the ticker appears in local readiness outputs" in missing_rendered
    assert "prices lane" in price_rendered
    assert "?mode=operator&page=data-health&lane=prices&drawer=queue" in price_rendered
    assert "trusted price history exists" in price_rendered
    assert "monitor context can be read" in monitor_rendered
    assert "operating-company dcf and peer valuation are excluded" in monitor_rendered
    assert "proof history" in monitor_rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_workflow_command_rows_are_collapsed_copy_only_rows():
    cards = [
        {"kicker": "WHERE AM I", "command": "make stock-report-md TICKER=NVDA"},
        {"kicker": "REVIEW NOW", "command": ""},
        {"kicker": "NEXT SAFE STEP", "command": "make focus-peers TICKER=NVDA"},
        {"kicker": "NEXT SAFE STEP", "command": "make focus-peers TICKER=NVDA"},
    ]

    rows = single_stock_workflow_command_rows(cards)
    rendered = " ".join(" ".join(row.values()) for row in rows).lower()

    assert rows == [
        {
            "Step": "WHERE AM I",
            "Command": "make stock-report-md TICKER=NVDA",
            "Boundary": "Copy-only; the dashboard does not run imports, refreshes, or proof writes.",
        },
        {
            "Step": "NEXT SAFE STEP",
            "Command": "make focus-peers TICKER=NVDA",
            "Boundary": "Copy-only; the dashboard does not run imports, refreshes, or proof writes.",
        },
    ]
    assert "copy-only" in rendered
    assert "dashboard does not run imports" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_workflow_loop_cards_keep_current_step_next_action_and_stop_rule_visible():
    cards = single_stock_workflow_loop_cards(
        {
            "ticker": "MU",
            "status": "partial",
            "asset_type": "company",
            "decision_bucket": "Research Now",
            "decision_subtype": "Standalone DCF ready; peers gated",
            "price_ready": True,
            "dcf_status": "ready",
            "peer_ready": False,
            "earnings_ready": False,
            "analyst_estimates_ready": False,
            "missing_data": "peer valuation inputs",
        }
    )
    rendered = _render(cards)

    assert [card["kicker"] for card in cards] == ["CURRENT STEP", "NEXT SAFE ACTION", "STOP RULE"]
    assert cards[0]["title"] == "MU: Single-stock review"
    assert "previous proof: saved readiness row" in rendered
    assert "current state: partial" in rendered
    assert "review standalone dcf now; route peer-relative context to the peers lane" in rendered
    assert "navigation and copy-only command context" in rendered
    assert "no trusted input, no conclusion" in rendered
    assert "locked, partial, and excluded sections stay visible" in rendered
    assert "make focus-peers ticker=mu" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_workflow_fit_cards_cover_missing_and_monitor_states():
    missing = {
        "ticker": "ZZZ",
        "status": "missing",
        "next_action": "Stage or refresh universe metadata, then run make universe-report and make readiness.",
    }
    monitor = {
        "ticker": "QQQ",
        "status": "partial",
        "asset_type": "etf",
        "decision_bucket": "Monitor",
        "decision_subtype": "Monitor - ETF Market Proxy",
        "price_ready": True,
        "dcf_status": "excluded",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }

    missing_rendered = _render(single_stock_workflow_fit_cards(missing))
    monitor_rendered = _render(single_stock_workflow_fit_cards(monitor))

    assert "no local row, no interpretation" in missing_rendered
    assert "refresh universe and readiness outputs" in missing_rendered
    assert "monitor context can be reviewed from local price, liquidity, and risk outputs" in monitor_rendered
    assert "operating-company dcf and peer valuation are excluded" in monitor_rendered
    assert "use data health only if source freshness or proof history needs review" in monitor_rendered
    assert "make stock-report-md ticker=qqq" in monitor_rendered
    rendered = missing_rendered + monitor_rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_next_command_preserves_readiness_first_routes():
    assert single_stock_next_command({"ticker": "QQQ", "asset_type": "etf", "dcf_status": "excluded"}) == (
        "make stock-report-md TICKER=QQQ"
    )
    assert single_stock_next_command({"ticker": "APLD", "price_ready": False, "dcf_status": "blocked"}) == (
        "make focus-price TICKER=APLD"
    )
    assert single_stock_next_command({"ticker": "MU", "price_ready": True, "dcf_status": "blocked"}) == (
        "make focus-fundamentals TICKER=MU"
    )
    assert single_stock_next_command(
        {
            "ticker": "NVDA",
            "price_ready": True,
            "dcf_status": "ready",
            "peer_ready": False,
            "missing_data": "peer inputs",
        }
    ) == "make focus-peers TICKER=NVDA"
    assert single_stock_next_command(
        {
            "ticker": "CRDO",
            "price_ready": True,
            "dcf_status": "ready",
            "peer_ready": True,
            "earnings_ready": False,
            "analyst_estimates_ready": False,
        }
    ) == "make optional-context-worklist TOP_N=25"


def test_single_stock_report_data_health_route_covers_readiness_gates():
    monitor = single_stock_report_data_health_route(
        asset_type="etf",
        valuation_status="excluded",
        price_ready=True,
        dcf_ready=False,
        peer_ready=False,
        earnings_ready=False,
        estimates_ready=False,
    )
    price = single_stock_report_data_health_route(
        asset_type="company",
        valuation_status="insufficient_data",
        price_ready=False,
        dcf_ready=False,
        peer_ready=False,
        earnings_ready=False,
        estimates_ready=False,
    )
    fundamentals = single_stock_report_data_health_route(
        asset_type="company",
        valuation_status="insufficient_data",
        price_ready=True,
        dcf_ready=False,
        peer_ready=False,
        earnings_ready=False,
        estimates_ready=False,
    )
    peers = single_stock_report_data_health_route(
        asset_type="company",
        valuation_status="calculated",
        price_ready=True,
        dcf_ready=True,
        peer_ready=False,
        earnings_ready=False,
        estimates_ready=False,
    )
    optional = single_stock_report_data_health_route(
        asset_type="company",
        valuation_status="calculated",
        price_ready=True,
        dcf_ready=True,
        peer_ready=True,
        earnings_ready=False,
        estimates_ready=True,
    )
    proof = single_stock_report_data_health_route(
        asset_type="company",
        valuation_status="calculated",
        price_ready=True,
        dcf_ready=True,
        peer_ready=True,
        earnings_ready=True,
        estimates_ready=True,
    )
    rendered = " ".join(str(value) for route in (monitor, price, fundamentals, peers, optional, proof) for value in route.values()).lower()

    assert monitor["route_label"] == "Proof History"
    assert price["route"] == "?mode=operator&page=data-health&lane=prices&drawer=queue"
    assert fundamentals["route_label"] == "Fundamentals / DCF source-proof lane"
    assert peers["route"] == "?mode=operator&page=data-health&lane=peers&drawer=source-proof"
    assert optional["route_label"] == "Optional context lane"
    assert proof["stop_rule"] == "Stop if readiness changed since the report was generated; rebuild proof first."
    assert "placeholder-backed" in rendered
    assert "source-backed rows" in rendered
    assert "trusted local rows" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_single_stock_pre_report_contract_cards_show_readiness_before_clicking_report():
    coverage = pd.DataFrame(
        [
            {
                "dataset": "prices",
                "ticker": "META",
                "ticker_present": True,
                "focus_command": "make focus-price TICKER=META",
            },
            {
                "dataset": "fundamentals",
                "ticker": "META",
                "ticker_present": False,
                "focus_command": "make focus-fundamentals TICKER=META",
            },
            {
                "dataset": "peers",
                "ticker": "META",
                "ticker_present": False,
                "focus_command": "make focus-peers TICKER=META",
            },
        ]
    )

    cards = single_stock_pre_report_contract_cards("META", coverage, {"peer_dataset_present": False, "peer_count": 0})
    rendered = _render(cards)

    assert [card["kicker"] for card in cards] == [
        "RESEARCH LOOP",
        "SELECTED TICKER",
        "REVIEW NOW",
        "BLOCKED / EXCLUDED",
        "REPORT HANDOFF",
        "NEXT SAFE ACTION",
        "STOP RULE",
    ]
    assert "meta: review starting point" in rendered
    assert "previous proof: home readiness snapshot plus selected-ticker data coverage" in rendered
    assert "current step: decide what the selected ticker can support before opening the review" in rendered
    assert "next safe action: data health fundamentals lane" in rendered
    assert "meta: price context ready; fundamentals gated" in rendered
    assert "local price context can be reviewed" in rendered
    assert "trusted fundamentals, shares, fcf, market cap, and valuation inputs remain source-proof work" in rendered
    assert "open the review, then follow the locks" in rendered
    assert "loop: select ticker, open the review, read supported sections" in rendered
    assert "route any locked input to data health fundamentals lane" in rendered
    assert "data health fundamentals lane" in rendered
    assert "make focus-fundamentals ticker=meta" in rendered
    assert "does not run imports, refreshes, or proof writes" in rendered
    assert "no trusted input, no conclusion" in rendered
    assert "fundamentals, shares, market cap, fcf, or valuation inputs would be inferred" in rendered
    assert "not a recommendation or ranking" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_pre_report_contract_cards_route_price_peer_and_ready_states():
    price_blocked = single_stock_pre_report_contract_cards(
        "APLD",
        pd.DataFrame(
            [
                {"dataset": "prices", "ticker": "APLD", "ticker_present": False},
                {"dataset": "fundamentals", "ticker": "APLD", "ticker_present": False},
            ]
        ),
        {},
    )
    peer_blocked = single_stock_pre_report_contract_cards(
        "NVDA",
        pd.DataFrame(
            [
                {"dataset": "prices", "ticker": "NVDA", "ticker_present": True},
                {"dataset": "fundamentals", "ticker": "NVDA", "ticker_present": True},
                {"dataset": "peers", "ticker": "NVDA", "ticker_present": False},
            ]
        ),
        {"peer_dataset_present": False, "peer_count": 0},
    )
    ready = single_stock_pre_report_contract_cards(
        "CRDO",
        pd.DataFrame(
            [
                {"dataset": "prices", "ticker": "CRDO", "ticker_present": True},
                {"dataset": "fundamentals", "ticker": "CRDO", "ticker_present": True},
                {"dataset": "peers", "ticker": "CRDO", "ticker_present": True},
            ]
        ),
        {"peer_dataset_present": True, "peer_count": 4},
    )

    price_rendered = _render(price_blocked)
    peer_rendered = _render(peer_blocked)
    ready_rendered = _render(ready)

    assert "apld: price proof comes first" in price_rendered
    assert "next safe action: data health price lane" in price_rendered
    assert "make focus-price ticker=apld" in price_rendered
    assert "setup, trend, dcf, peer, optional context, and review metrics stay locked" in price_rendered
    assert "price rows are missing, stale, rejected, or not tied to the selected ticker" in price_rendered
    assert "nvda: core inputs present; peer context gated" in peer_rendered
    assert "next safe action: data health peers lane" in peer_rendered
    assert "data health peers lane" in peer_rendered
    assert "make focus-peers ticker=nvda" in peer_rendered
    assert "peer mappings or peer valuation inputs lack source-backed rows" in peer_rendered
    assert "crdo: ready to open the review" in ready_rendered
    assert "next safe action: single-stock report" in ready_rendered
    assert "make stock-report-md ticker=crdo" in ready_rendered
    assert "readiness changed after a local import, refresh, or proof update" in ready_rendered
