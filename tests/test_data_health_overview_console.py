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
    assert "trusted fundamentals provide company-level valuation support" in rendered
    assert "make company-level" not in rendered
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
    assert cards[0]["command"] == "make fundamentals-source-ladder-queue TOP_N=25"
    assert "217 price-ready row(s) still need trusted fundamentals" in rendered
    assert "not a negative company signal" in rendered
    assert "detailed proof steps only when source rows are ready" in rendered
    assert "detailed proof commands" not in rendered
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
                "Next Safe Command": "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto",
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
    assert cards[2]["command"] == "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto"
    assert "top data-lane opportunity has unlock impact 3273" in rendered
    assert "treat stale or missing readiness artifacts as a stop sign" in rendered
    assert "validate, preview, apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_auto_refresh_status_cards_show_scheduler_next_step():
    cards = overview_console.auto_refresh_status_cards(
        {
            "source_activation": "not_required",
            "can_run_now": "coverage_workflow_evidence",
            "needs_setup": "fmp, alpha_vantage, finnhub",
            "avoid_repeating": "fundamentals_share_count_source_ladder",
            "next_executable_command": "make project-status",
            "next_runbook": "make auto-refresh-runbook SCHEDULE=daily",
            "source_categories": {
                "free_public_available": "stooq, yahoo, sec",
                "paid_or_locked": "fmp, alpha_vantage, finnhub",
            },
            "free_tier_batch_limits": "fmp<=250/day and <=25/run; alpha_vantage<=25/day and <=5/run; finnhub<=60/day and <=10/run",
            "artifact_policy": "generated CSV/JSON/report churn stays excluded unless intentionally reviewed evidence.",
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "AUTO REFRESH STATUS",
        "SOURCE SETUP",
        "NEXT SCHEDULER STEP",
    ]
    assert cards[0]["command"] == "make auto-refresh-status SCHEDULE=daily"
    assert cards[2]["command"] == "make auto-refresh-runbook SCHEDULE=daily"
    assert "can run now: coverage_workflow_evidence" in rendered
    assert "avoid repeating: fundamentals_share_count_source_ladder" in rendered
    assert "needs setup: fmp, alpha vantage, finnhub" in rendered
    assert "generated csv/json/report churn stays excluded" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_source_activation_setup_cards_show_provider_boundaries():
    cards = overview_console.source_activation_setup_cards(
        {
            "setup_commands": [
                "cp config/provider_keys.env.example config/provider_keys.env",
                "chmod 600 config/provider_keys.env",
                "edit config/provider_keys.env locally; do not commit real keys",
            ],
            "activation_plan": [
                "Run make project-status first; if it says queues are exhausted, do not reopen broad proof loops.",
                "Configure at most one missing keyed free-tier provider locally, then rerun make session-source-preflight.",
                "Run that provider's one-ticker smoke command only; do not start a broad batch from setup.",
            ],
            "providers": [
                {
                    "provider": "SEC Companyfacts",
                    "category": "free_public_available",
                    "env_vars": ["SEC_USER_AGENT"],
                    "can_cover": ["fundamentals", "share_count"],
                    "usage": "source_backed_companyfacts",
                    "cannot_unlock": "Peers, earnings estimates, recommendations, or inferred missing values.",
                    "setup": "Set SEC_USER_AGENT in config/provider_keys.env or the shell.",
                },
                {
                    "provider": "FMP free tier",
                    "category": "keyed_free_tier_missing",
                    "env_vars": ["FMP_API_KEY"],
                    "can_cover": ["price", "fundamentals", "share_count"],
                    "usage": "keyed_free_tier_fallback",
                    "cannot_unlock": "Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.",
                    "setup": "Set FMP_API_KEY in config/provider_keys.env, then rerun make session-source-preflight.",
                    "batch_policy": "small_batch_only; recommended <=250 requests/day and <=25 tickers/run",
                },
                {
                    "provider": "IBKR read-only",
                    "category": "optional_broker_disabled",
                    "env_vars": ["IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID"],
                    "can_cover": ["price"],
                    "usage": "read_only_daily_ohlcv",
                    "cannot_unlock": "Broker actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates.",
                    "setup": "Leave disabled unless IBKR Gateway/TWS is intentionally running for read-only daily bars.",
                },
            ],
            "apply_gate": [
                "make imports-validate IMPORT_TICKERS=<ticker>",
                "make imports-preview IMPORT_TICKERS=<ticker>",
                "make imports-apply IMPORT_TICKERS=<ticker> only when validation passes, preview scope is intended, rejected rows are zero, and source provenance exists",
            ],
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "ACTIVATION PLAN",
        "FREE PUBLIC SOURCES",
        "KEYED FREE-TIER SETUP",
        "BROKER DATA BOUNDARY",
        "APPLY GATE",
    ]
    assert cards[0]["command"] == "make project-status"
    assert cards[1]["command"] == "make source-activation-guide"
    assert cards[2]["command"] == "cp config/provider_keys.env.example config/provider_keys.env"
    assert "do not reopen broad proof loops" in rendered
    assert "one-ticker smoke command only" in rendered
    assert "sec companyfacts" in rendered
    assert "fmp free tier" in rendered
    assert "small_batch_only" in rendered
    assert "ibkr read-only stays disabled" in rendered
    assert "validate" in rendered
    assert "preview" in rendered
    assert "rejected rows are zero" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_provider_setup_checklist_cards_show_setup_states():
    cards = overview_console.provider_setup_checklist_cards(
        {
            "secret_policy": "Real key values are never printed.",
            "rows": [
                {
                    "provider": "FMP free tier",
                    "setup_state": "configured",
                    "unlock_lanes": "price, fundamentals, share_count",
                    "usage": "keyed_free_tier_fallback",
                    "safe_next_step": "Run make session-source-preflight, then dry-run the matching source ladder.",
                    "post_setup_smoke_command": "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>",
                },
                {
                    "provider": "Alpha Vantage free tier",
                    "setup_state": "needs_key",
                    "unlock_lanes": "price, fundamentals, share_count",
                    "usage": "keyed_free_tier_fallback",
                    "safe_next_step": "Set ALPHA_VANTAGE_API_KEY in config/provider_keys.env, then rerun make session-source-preflight.",
                },
                {
                    "provider": "IBKR read-only",
                    "setup_state": "optional_disabled",
                    "unlock_lanes": "price",
                    "usage": "read_only_daily_ohlcv",
                    "safe_next_step": "Leave disabled unless intentionally using read-only daily OHLCV.",
                },
            ],
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "PROVIDER SETUP CHECKLIST",
        "KEYED FALLBACKS",
        "OPTIONAL BROKER",
        "NEXT SAFE STEP",
    ]
    assert cards[0]["command"] == "make provider-setup-checklist"
    assert "fmp free tier: configured" in rendered
    assert "alpha vantage free tier: needs_key" in rendered
    assert "ibkr read-only: optional_disabled" in rendered
    assert "real key values are never printed" in rendered
    assert "dry-run the matching source ladder" in rendered
    assert "smoke test: make fmp-stage tickers=<ticker>" in rendered
    assert "imports-preview import_tickers=<ticker>" in rendered
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
    assert cards[1]["command"] == "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3300 TOP_N=100 PROVIDER=auto"
    assert "without changing files" in rendered
    assert "run a real loop only after reviewing the dry-run plan" in rendered
    assert "validation, preview, rejected-row checks, and readiness rebuilds" in rendered
    assert "broker" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
