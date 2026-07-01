import pandas as pd

from src.universe_scope_workflow import (
    _print_plan,
    universe_scope_risk_handoff_cards,
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
    ready_only = plan.loc[plan["scope"].eq("ready_only")].iloc[0]
    assert ready_only["copy_only_command"] == "make project-status"
    assert "project-status first so exhausted proof queues do not reopen stale trusted-data candidate loops" in str(
        ready_only["stop_rule"]
    ).lower()
    assert "make trusted-data-pilot-candidates top_n=12" not in rendered
    assert "make coverage-frontier top_n=12" in rendered
    assert "copy-only" in rendered
    assert "does not refresh, import, apply, or infer missing values" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_universe_scope_print_plan_starts_with_recommended_scope(capsys):
    plan = pd.DataFrame(
        [
            {
                "scope": "active_universe",
                "matching_rows": 2,
                "what_it_answers": "Which focused rows first?",
                "copy_only_command": "make readiness-queue TOP_N=10",
                "scope_boundary": "copy-only",
                "stop_rule": "Use active rows first.",
            },
            {
                "scope": "missing_data",
                "matching_rows": 5,
                "what_it_answers": "Which rows route to proof?",
                "copy_only_command": "make coverage-frontier TOP_N=10",
                "scope_boundary": "copy-only",
                "stop_rule": "Widen only after proof gates.",
            },
        ]
    )

    _print_plan(plan)
    output = capsys.readouterr().out.lower()

    assert "recommended first scope: active_universe" in output
    assert "make readiness-queue top_n=10" in output
    assert "do not treat master-universe coverage as analysis readiness" in output
    assert output.index("recommended first scope") < output.index("- active_universe")
    assert "buy" not in output
    assert "sell" not in output
    assert "broker" not in output


def test_universe_scope_risk_handoff_cards_keep_scope_before_risk_context():
    cards = universe_scope_risk_handoff_cards(
        {"master_universe": 3538, "active_universe": 12, "price_ready": 3538, "dcf_ready": 2691, "peer_ready": 29},
        pd.DataFrame(),
    )
    rendered = _render(cards)

    assert [card["kicker"] for card in cards] == [
        "SCOPE BEFORE RISK",
        "RISK CONTEXT BOUNDARY",
        "NEXT SAFE REVIEW",
    ]
    assert "12 active-review rows before the 3538-row master universe" in rendered
    assert "risk context is not a research conclusion" in rendered
    assert "liquidity and correlation after scope selection" in rendered
    assert "blocked rows route back to price history or source proof" in rendered
    assert cards[0]["command"] == "make universe-scope TOP_N=10"
    assert cards[1]["command"] == "make risk-context"
    assert cards[2]["command"] == "make coverage-frontier TOP_N=10"
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
