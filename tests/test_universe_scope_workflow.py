import pandas as pd

from src.universe_scope_workflow import (
    universe_scope_counts,
    universe_scope_review_plan,
    universe_scope_workflow_cards,
)


def _render(cards: list[dict[str, object]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_universe_scope_counts_fall_back_to_readiness_frame_without_rendering_full_table():
    frame = pd.DataFrame(
        [
            {"ticker": "META", "in_active_universe": True, "price_ready": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "NVDA", "in_active_universe": True, "price_ready": True, "dcf_ready": True, "peer_ready": True},
            {"ticker": "BROAD", "in_active_universe": False, "price_ready": True, "dcf_ready": False, "peer_ready": False},
        ]
    )

    counts = universe_scope_counts({}, frame)

    assert counts == {
        "master": 3,
        "active": 2,
        "price_ready": 3,
        "dcf_ready": 2,
        "peer_ready": 1,
    }


def test_universe_scope_workflow_cards_explain_scope_filters_and_stop_rule():
    cards = universe_scope_workflow_cards(
        {"master_universe": 3538, "active_universe": 12, "price_ready": 3538, "dcf_ready": 59, "peer_ready": 26},
        pd.DataFrame(),
    )
    rendered = _render(cards)

    assert [card["kicker"] for card in cards] == ["SCOPE MAP", "SAFE FILTER PATH", "STOP RULE"]
    assert "3538 master rows; 12 active-review rows" in rendered
    assert "master universe is coverage planning" in rendered
    assert "single-stock lookup can inspect known master-universe tickers one at a time" in rendered
    assert "without forcing full-market analysis" in rendered
    assert "keep missing fundamentals, shares, peers, earnings, analyst estimates, valuation inputs, and review metrics blocked" in rendered
    assert "make status-check top_n=5" in rendered
    assert "make data-coverage-proof-queues top_n=10" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_universe_scope_review_plan_gives_lazy_copy_only_scope_commands():
    frame = pd.DataFrame(
        [
            {
                "ticker": "META",
                "in_active_universe": True,
                "sector": "Communication Services",
                "theme": "AI Applications",
                "price_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
                "blocked_features": "peer, earnings, analyst_estimates",
            },
            {
                "ticker": "BROAD",
                "in_active_universe": False,
                "sector": "Technology",
                "theme": "Broad Universe",
                "price_ready": True,
                "dcf_ready": False,
                "peer_ready": False,
                "blocked_features": "fundamentals, dcf, peer",
            },
        ]
    )

    plan = universe_scope_review_plan(
        {},
        frame,
        tickers="META,BROAD",
        sector="Technology",
        theme="AI Applications",
        top_n=12,
    )
    rendered = " ".join(str(value) for value in plan.to_numpy().ravel()).lower()

    assert list(plan["scope"]) == [
        "active_universe",
        "ticker_list",
        "sector_theme",
        "ready_only",
        "missing_data",
    ]
    assert plan.loc[plan["scope"].eq("active_universe"), "matching_rows"].iloc[0] == 1
    assert plan.loc[plan["scope"].eq("ticker_list"), "matching_rows"].iloc[0] == 2
    assert plan.loc[plan["scope"].eq("sector_theme"), "matching_rows"].iloc[0] == 2
    assert "make status-check tickers=meta,broad top_n=12" in rendered
    assert "make trusted-data-pilot-candidates top_n=12" in rendered
    assert "make coverage-frontier top_n=12" in rendered
    assert "copy-only" in rendered
    assert "does not refresh, import, apply, or infer missing values" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
