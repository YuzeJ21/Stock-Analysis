import pandas as pd

from src.risk_context_workflow import (
    data_health_risk_context_cards,
    risk_context_summary_lines,
    split_risk_context_by_price_ready,
)


def test_split_risk_context_by_price_ready_status_keeps_supported_and_unavailable_separate():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD"],
            "LiquidityStatus": ["Liquid", "Insufficient Price Data"],
        }
    )

    ready, unavailable = split_risk_context_by_price_ready(frame, {"Insufficient Price Data"})

    assert ready["Ticker"].tolist() == ["NVDA"]
    assert unavailable["Ticker"].tolist() == ["AMD"]


def test_data_health_risk_context_cards_label_proxy_context_without_recommendations():
    liquidity = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD", "QQQ"],
            "LiquidityStatus": ["Liquid", "Insufficient Price Data", "Liquid"],
            "LiquidityInputsUsed": ["ATR inputs", "", "close-to-close volatility proxy approximation"],
            "Reason": ["Supported by local rows.", "Need volume rows.", "Proxy remains approximate."],
        }
    )
    correlation = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD", "QQQ"],
            "CorrelationStatus": ["Ready", "Insufficient Overlap", "Insufficient Data"],
            "Reason": ["Supported.", "Need overlap.", "Need local returns."],
        }
    )

    cards = data_health_risk_context_cards(liquidity, correlation)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "LIQUIDITY READINESS",
        "CORRELATION READINESS",
        "PROXY RISK NOTES",
    ]
    assert cards[0]["title"] == "2 ready / 3 rows"
    assert cards[1]["title"] == "1 ready / 3 rows"
    assert cards[2]["title"] == "1 approximation row(s)"
    assert "examples: amd" in rendered
    assert "examples: amd, qqq" in rendered
    assert "review context only" in rendered
    assert "concentration review signal, not a research conclusion" in rendered
    assert "volatility-proxy language must stay labeled as an approximation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_risk_context_summary_lines_are_terminal_safe_and_copy_only():
    liquidity = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD"],
            "LiquidityStatus": ["Liquid", "Insufficient Price Data"],
            "LiquidityInputsUsed": ["ATR inputs", ""],
        }
    )
    correlation = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD"],
            "CorrelationStatus": ["Ready", "Insufficient Overlap"],
        }
    )

    lines = risk_context_summary_lines(liquidity, correlation)
    rendered = " ".join(lines).lower()

    assert lines[0] == "Risk Context Summary"
    assert "read-only" in rendered
    assert "choose scope first" in rendered
    assert "make universe-scope top_n=10" in rendered
    assert "does not unlock missing fundamentals, peers, earnings, or estimates" in rendered
    assert "use the price-history proof queue before any capped provider refresh" in rendered
    assert "liquidity readiness: 1 ready / 2 rows" in rendered
    assert "correlation readiness: 1 ready / 2 rows" in rendered
    assert "examples: amd" in rendered
    assert "make price-history-proof-queue top_n=25" in rendered
    assert "make price-worklist top_n=25" not in rendered
    assert "make research-health-check top_n=10" in rendered
    assert "review context only" in rendered
    assert "not a research conclusion" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
