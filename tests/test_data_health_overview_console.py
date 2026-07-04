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

    assert [card[0] for card in cards] == ["Single-Stock Report", "Data Health", "Proof History"]
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


def test_overview_public_first_30_second_cards_route_blocked_rows_through_source_gate():
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

    assert cards[1]["kicker"] == "STILL BLOCKED"
    assert cards[1]["command"] == "make project-status"
    assert "source gate" in rendered
    assert "provider setup" in rendered
    assert "make data-coverage-proof-queues" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_overview_operations_cockpit_cards_keep_stale_and_proof_hygiene_visible():
    ops = pd.DataFrame(
        [
            {
                "Lane": "Price coverage",
                "State": "partial",
                "Ready": 264,
                "Partial": 1,
                "Blocked": 0,
                "Excluded": 0,
                "Workflow Mode": "safe_to_batch_dry_run",
                "Next Safe Command": "make price-refresh-loop DRY_RUN=1",
            },
            {
                "Lane": "Fundamentals / DCF proof",
                "State": "partial",
                "Ready": 23,
                "Partial": 217,
                "Blocked": 25,
                "Excluded": 0,
                "Workflow Mode": "review_only",
                "Next Safe Command": "make project-status",
            },
            {
                "Lane": "Earnings locked lane",
                "State": "blocked",
                "Ready": 0,
                "Partial": 0,
                "Blocked": 265,
                "Excluded": 0,
                "Workflow Mode": "locked_manual",
                "Next Safe Command": "make optional-context-source-ladder-queue TOP_N=10",
            },
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
        "LANE ANSWER",
        "OPS COCKPIT",
        "NEXT FRONTIER",
        "OPTIONAL CONTEXT",
        "PROOF HYGIENE",
    ]
    assert cards[0]["title"] == "Stale"
    assert cards[1]["title"] == "What can I use now?"
    assert cards[1]["command"] == "make readiness-ops-center"
    assert cards[3]["command"] == "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto"
    assert "one answer per lane:" in rendered
    assert "price coverage -> use ready price rows now; review 1 partial row only if freshness depth matters" in rendered
    assert "fundamentals / dcf proof -> use 23 ready row(s); review 217 partial row(s); keep 25 blocked row(s) locked" in rendered
    assert "earnings locked lane -> do not use as analysis input yet; locked optional context needs trusted rows" in rendered
    assert "use now: price coverage has 264 ready row(s)" in rendered
    assert "partly usable: price coverage has 1 partial row(s); fundamentals / dcf proof has 217 partial row(s)" in rendered
    assert "blocked: fundamentals / dcf proof has 25 blocked row(s); earnings locked lane has 265 blocked row(s)" in rendered
    assert "context only: earnings locked lane is locked/manual until trusted optional rows exist" in rendered
    assert "excluded/not applicable: no excluded lane reported" in rendered
    assert "next safe action: price coverage -> inspect the partial price row only if freshness depth matters" in rendered
    assert "fundamentals / dcf proof -> open details for the source-backed next step" in rendered
    assert "earnings locked lane -> keep optional context locked until trusted rows exist" in rendered
    assert "top data-lane opportunity has unlock impact 3273" in rendered
    assert "treat stale or missing readiness artifacts as a stop sign" in rendered
    assert "validate, preview, apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_lane_answer_frame_gives_one_clear_row_per_lane():
    ops = pd.DataFrame(
        [
            {
                "Lane": "Price Coverage",
                "State": "partial",
                "Ready": 3537,
                "Partial": 1,
                "Blocked": 0,
                "Excluded": 0,
                "Workflow Mode": "dry_run_first",
                "Next Safe Command": "make price-history-proof-queue TOP_N=25",
            },
            {
                "Lane": "Peer Mapping Proof",
                "State": "partial",
                "Ready": 29,
                "Partial": 0,
                "Blocked": 3507,
                "Excluded": 2,
                "Workflow Mode": "preview_first_reviewed_apply",
                "Next Safe Command": "make project-status",
            },
            {
                "Lane": "Earnings Locked Lane",
                "State": "blocked",
                "Ready": 0,
                "Partial": 0,
                "Blocked": 3538,
                "Excluded": 0,
                "Workflow Mode": "optional_source_ladder",
                "Next Safe Command": "make optional-context-source-ladder-queue TOP_N=10",
            },
        ]
    )

    frame = overview_console.lane_answer_frame(ops)

    assert list(frame.columns) == [
        "Lane",
        "Primary Answer",
        "Use Now",
        "Partial",
        "Blocked",
        "Context Only",
        "Excluded / Not Applicable",
        "Next Safe Action",
        "Review Boundary",
    ]
    assert frame.to_dict("records") == [
        {
            "Lane": "Price Coverage",
            "Primary Answer": "Use ready price rows now; review 1 partial row only if freshness depth matters.",
            "Use Now": "3,537 ready row(s)",
            "Partial": "1 partial row(s)",
            "Blocked": "-",
            "Context Only": "-",
            "Excluded / Not Applicable": "-",
            "Next Safe Action": "Inspect the partial price row only if freshness depth matters.",
            "Review Boundary": "Use the ready price evidence now; inspect the one partial row only if freshness depth matters.",
        },
        {
            "Lane": "Peer Mapping Proof",
            "Primary Answer": "Use 29 ready row(s); keep 3,507 blocked row(s) locked until source proof exists.",
            "Use Now": "29 ready row(s)",
            "Partial": "-",
            "Blocked": "3,507 blocked row(s)",
            "Context Only": "-",
            "Excluded / Not Applicable": "2 excluded/not applicable",
            "Next Safe Action": "Use provider setup before reopening broad proof queues.",
            "Review Boundary": "Treat ready peer rows as usable and blocked rows as locked until trusted source proof exists.",
        },
        {
            "Lane": "Earnings Locked Lane",
            "Primary Answer": "Do not use as analysis input yet; locked optional context needs trusted rows.",
            "Use Now": "-",
            "Partial": "-",
            "Blocked": "3,538 blocked row(s)",
            "Context Only": "locked/manual or candidate context",
            "Excluded / Not Applicable": "-",
            "Next Safe Action": "Keep optional context locked until trusted rows exist.",
            "Review Boundary": "Use as optional context only; keep raw provider/manual setup in collapsed operator drawers.",
        },
    ]
    rendered = " ".join(str(value) for value in frame.to_numpy().ravel()).lower()
    assert "make " not in rendered


def test_overview_lane_answer_card_keeps_raw_commands_out_of_lane_answers():
    ops = pd.DataFrame(
        [
            {
                "Lane": "Price Coverage",
                "State": "partial",
                "Ready": 3537,
                "Partial": 1,
                "Blocked": 0,
                "Excluded": 0,
                "Workflow Mode": "dry_run_first",
                "Next Safe Command": "make price-history-proof-queue TOP_N=25",
            },
            {
                "Lane": "Fundamentals / DCF Proof",
                "State": "partial",
                "Ready": 2691,
                "Partial": 243,
                "Blocked": 90,
                "Excluded": 514,
                "Workflow Mode": "preview_first_reviewed_apply",
                "Next Safe Command": "make project-status",
            },
        ]
    )

    card = overview_console.lane_answer_card(ops)
    body = str(card["body"]).lower()
    lane_answer_text = body.split("next safe action:", maxsplit=1)[0]

    assert "one answer per lane:" in body
    assert "price coverage -> use ready price rows now; review 1 partial row only if freshness depth matters" in body
    assert "fundamentals / dcf proof -> use 2,691 ready row(s); review 243 partial row(s); keep 90 blocked row(s) locked" in body
    assert "make " not in lane_answer_text
    assert "make " not in body
    assert body.count("next safe action:") == 1
    assert (
        "next safe action: price coverage -> inspect the partial price row only if freshness depth matters; "
        "fundamentals / dcf proof -> open details for the source-backed next step."
    ) in body
    assert card["command"] == "make readiness-ops-center"


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
    assert "can run now: workflow evidence only; current source-proof queues are exhausted" in rendered
    assert "avoid repeating: fundamentals/share-count source ladder" in rendered
    assert "coverage_workflow_evidence" not in rendered
    assert "fundamentals_share_count_source_ladder" not in rendered
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
                "Run that provider's reviewed one-ticker smoke command only; do not start a broad batch from setup.",
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
    assert "reviewed one-ticker smoke command only" in rendered
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
            "source_answer": {
                "free_public_now": "SEC Companyfacts, SEC submissions, Stooq",
                "configured_keyed": "FMP free tier",
                "needs_key": "Alpha Vantage free tier",
                "optional_broker": "IBKR read-only",
                "answer": "Use the free/public baseline first; configure at most one keyed free-tier fallback only when project-status says source-proof queues are exhausted.",
            },
            "coverage_unlock_decision": {
                "answer": "No broad coverage batch should run from setup alone.",
                "can_use_now": "Use free/public sources for already executable proof paths; current gate says coverage_workflow_evidence.",
                "configure_first": "Configure FMP free tier first only if you want a keyed fallback, then run a reviewed one-ticker smoke command.",
                "do_not_retry": "Do not retry fundamentals_share_count_source_ladder until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist.",
                "proof_boundary": "Provider setup only makes a source executable; readiness changes still require validate, preview, rejected-row review, source provenance, apply/skip decision, rebuilt readiness, and proof ledger evidence.",
            },
            "rows": [
                {
                    "provider": "SEC Companyfacts",
                    "category": "free_public_available",
                    "setup_state": "available",
                    "unlock_lanes": "fundamentals, share_count",
                    "usage": "source_backed_companyfacts",
                    "safe_next_step": "Use SEC through source ladders only when a ticker still has unreviewed actionable blockers.",
                },
                {
                    "provider": "Stooq daily prices",
                    "category": "free_public_available",
                    "setup_state": "available",
                    "unlock_lanes": "price",
                    "usage": "free_public_daily_ohlcv",
                    "safe_next_step": "Use PROVIDER=auto dry-run before any capped price refresh.",
                },
                {
                    "provider": "FMP free tier",
                    "category": "keyed_free_tier_available",
                    "setup_state": "configured",
                    "unlock_lanes": "price, fundamentals, share_count",
                    "usage": "keyed_free_tier_fallback",
                    "safe_next_step": "Run make session-source-preflight, then dry-run the matching source ladder.",
                    "post_setup_smoke_command": "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>",
                },
                {
                    "provider": "Alpha Vantage free tier",
                    "category": "keyed_free_tier_missing",
                    "setup_state": "needs_key",
                    "unlock_lanes": "price, fundamentals, share_count",
                    "usage": "keyed_free_tier_fallback",
                    "safe_next_step": "Set ALPHA_VANTAGE_API_KEY in config/provider_keys.env, then rerun make session-source-preflight.",
                },
                {
                    "provider": "IBKR read-only",
                    "category": "optional_broker_disabled",
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
        "PROVIDER RUN DECISION",
        "PROVIDER FIRST ANSWER",
        "COVERAGE UNLOCK DECISION",
        "PROVIDER SETUP CHECKLIST",
        "WORKFLOW PIVOT",
        "SAFE SETUP PATH",
        "FREE PUBLIC BASELINE",
        "KEYED FALLBACKS",
        "OPTIONAL BROKER",
        "NEXT SAFE STEP",
    ]
    assert cards[0]["title"] == "Do I run coverage now?"
    assert cards[0]["command"] == "make project-status"
    assert cards[1]["title"] == "What source can I use next?"
    assert cards[1]["command"] == "make provider-setup-checklist"
    assert cards[2]["command"] == "make project-status"
    assert cards[3]["command"] == "make provider-setup-checklist"
    assert cards[4]["command"] == "make universe-scope TOP_N=10 && make risk-context"
    assert cards[5]["command"] == "make project-status"
    assert "do not run broad coverage from setup alone" in rendered
    assert "reopen one reviewed ticker only after new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers appear" in rendered
    assert "what free source can run now" in rendered
    assert "what key is missing" in rendered
    assert "what should not be retried" in rendered
    assert "review boundary" in rendered
    assert "one safe smoke test" not in rendered
    assert "no broad coverage batch should run from setup alone" in rendered
    assert "provider setup only makes a source executable" in rendered
    assert "do not retry fundamentals/share-count source ladder" in rendered
    assert "fundamentals_share_count_source_ladder" not in rendered
    assert "coverage_workflow_evidence" not in rendered
    assert "project-status -> provider setup -> reviewed one-ticker smoke command -> validate/preview" in rendered
    assert "when proof queues are exhausted, pivot to source setup and scoped review" in rendered
    assert "make universe-scope top_n=10" in rendered
    assert "make risk-context" in rendered
    assert "make universe-preview-summary" in rendered
    assert "universe membership is source metadata only" in rendered
    assert "does not unlock fundamentals, share count, dcf, peer valuation, earnings, or estimates" in rendered
    assert "do not reopen trusted-data candidates until project-status shows executable company candidates" in rendered
    assert "do not reopen broad proof loops from setup" in rendered
    assert "use the free/public baseline first" in rendered
    assert "free public sources: sec companyfacts, sec submissions, stooq" in rendered
    assert "keyed free-tier fallbacks: configured fmp free tier; needs key alpha vantage free tier" in rendered
    assert "optional broker boundary: ibkr read-only" in rendered
    assert "free now: sec companyfacts, sec submissions, stooq" in rendered
    assert "configured keyed: fmp free tier" in rendered
    assert "needs key: alpha vantage free tier" in rendered
    assert "optional broker: ibkr read-only" in rendered
    assert "free/public baseline works before keys" in rendered
    assert "sec companyfacts: available" in rendered
    assert "stooq daily prices: available" in rendered
    assert "keyed fallbacks expand coverage; they are not required for pilot/demo sharing" in rendered
    assert "fmp free tier: configured" in rendered
    assert "alpha vantage free tier: needs_key" in rendered
    assert "ibkr read-only: optional_disabled" in rendered
    assert "real key values are never printed" in rendered
    assert "dry-run the matching source ladder" in rendered
    assert "reviewed smoke command: make fmp-stage tickers=<ticker>" in rendered
    assert "smoke test:" not in rendered
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
