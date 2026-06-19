from src.single_stock_workflow import single_stock_next_command, single_stock_workflow_fit_cards


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
        "WHERE AM I",
        "REVIEW NOW",
        "BLOCKED / EXCLUDED",
        "NEXT SAFE STEP",
        "STOP RULE",
    ]
    assert cards[0]["title"] == "NVDA - partial"
    assert "previous proof comes from the saved readiness row and report payload" in rendered
    assert "standalone dcf assumptions and source readiness can be reviewed" in rendered
    assert "peer-relative valuation remains locked" in rendered
    assert "open data health peer lane" in rendered
    assert "copy-only" in rendered
    assert "do not treat locked, partial, or excluded sections as conclusions" in rendered
    assert "make focus-peers ticker=nvda" in rendered
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
