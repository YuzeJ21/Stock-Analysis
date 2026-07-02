import json

from src.source_activation_guide import (
    build_provider_setup_checklist,
    build_source_activation_guide,
    render_provider_setup_checklist,
    render_source_activation_guide,
)


def test_source_activation_guide_lists_public_sources_without_secrets(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "secret-fmp-key")
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "")
    monkeypatch.setenv("FINNHUB_API_KEY", "")
    monkeypatch.setenv("IBKR_HOST", "")
    monkeypatch.setenv("IBKR_PORT", "")
    monkeypatch.setenv("IBKR_CLIENT_ID", "")

    guide = build_source_activation_guide()
    rendered = render_source_activation_guide(guide)

    providers = {row["provider"]: row for row in guide["providers"]}
    assert providers["SEC Companyfacts"]["category"] == "free_public_available"
    assert providers["SEC submissions"]["usage"] == "metadata_evidence_only"
    assert providers["FMP free tier"]["category"] == "keyed_free_tier_available"
    assert providers["Alpha Vantage free tier"]["category"] == "keyed_free_tier_missing"
    assert providers["IBKR read-only"]["category"] == "optional_broker_disabled"
    assert providers["FMP free tier"]["batch_policy"] == "small_batch_only; recommended <=250 requests/day and <=25 tickers/run"
    assert providers["Alpha Vantage free tier"]["batch_policy"] == "small_batch_only; recommended <=25 requests/day and <=5 tickers/run"
    assert providers["Finnhub free tier"]["batch_policy"] == "small_batch_only; recommended <=60 requests/day and <=10 tickers/run"
    assert providers["FMP free tier"]["post_setup_smoke_command"] == (
        "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
        "&& make imports-preview IMPORT_TICKERS=<ticker>"
    )
    assert providers["Stooq"]["post_setup_smoke_command"] == (
        "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=stooq"
    )
    assert "broad unlimited refresh" not in rendered
    assert "small_batch_only" in rendered
    assert "secret-fmp-key" not in json.dumps(guide)
    assert "secret-fmp-key" not in rendered
    assert "No provider key values are printed or stored by this guide." in rendered
    assert "Do not apply data directly from source setup." in rendered


def test_source_activation_guide_prints_exact_next_commands(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)

    guide = build_source_activation_guide()

    assert guide["setup_commands"][0] == "cp config/provider_keys.env.example config/provider_keys.env"
    assert guide["activation_plan"] == [
        "Run make project-status first; if it says queues are exhausted, do not reopen broad proof loops.",
        "Configure at most one missing keyed free-tier provider locally, then rerun make session-source-preflight.",
        "Run that provider's reviewed one-ticker smoke command only; do not start a broad batch from setup.",
        "Continue only through validate, preview, rejected-row review, and source-provenance checks.",
        "If no source-backed row is staged, record still_blocked/skipped/excluded and pivot.",
    ]
    assert "make session-source-preflight" in guide["next_commands"]
    assert "make coverage-frontier TOP_N=10" in guide["next_commands"]
    assert "make imports-validate IMPORT_TICKERS=<ticker>" in guide["apply_gate"]
    assert guide["non_retry_rule"] == (
        "Record unavailable source paths once, then pivot to the next executable lane in this session."
    )


def test_provider_setup_checklist_summarizes_unlocks_without_secrets(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "secret-fmp-key")
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("IBKR_HOST", raising=False)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    monkeypatch.delenv("IBKR_CLIENT_ID", raising=False)

    checklist = build_provider_setup_checklist()
    rendered = render_provider_setup_checklist(checklist)

    rows = {row["provider"]: row for row in checklist["rows"]}
    assert checklist["source_answer"] == {
        "free_public_now": "SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance",
        "needs_key": "Alpha Vantage free tier, Finnhub free tier",
        "configured_keyed": "FMP free tier",
        "optional_broker": "IBKR read-only (disabled unless explicitly configured)",
        "answer": (
            "Use the free/public baseline first; configure at most one keyed free-tier fallback only when "
            "project-status says source-proof queues are exhausted. Optional broker data remains disabled unless "
            "explicitly configured for read-only daily OHLCV."
        ),
    }
    assert checklist["first_answer"] == {
        "question": "What source can I use next?",
        "free_source_now": "SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance",
        "missing_key": "Alpha Vantage free tier, Finnhub free tier",
        "do_not_retry": "Do not retry exhausted proof queues until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist.",
        "setup_prerequisite": "FMP free tier is configured; choose one reviewed ticker before running the reviewed one-ticker smoke command.",
        "ticker_scope_rule": "Choose one reviewed ticker from make project-status or a current proof packet before replacing <ticker>; do not run the reviewed one-ticker smoke command across a broad list.",
        "reviewed_one_ticker_smoke": (
            "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
            "&& make imports-preview IMPORT_TICKERS=<ticker>"
        ),
        "one_safe_smoke": (
            "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
            "&& make imports-preview IMPORT_TICKERS=<ticker>"
        ),
        "boundary": "Provider setup only makes a source executable; readiness changes still require validate/preview/apply gates.",
    }
    assert rows["FMP free tier"]["setup_state"] == "configured"
    assert rows["Alpha Vantage free tier"]["setup_state"] == "needs_key"
    assert rows["Finnhub free tier"]["setup_state"] == "needs_key"
    assert rows["IBKR read-only"]["setup_state"] == "optional_disabled"
    assert rows["FMP free tier"]["unlock_lanes"] == "price, fundamentals, share_count"
    assert rows["FMP free tier"]["safe_next_step"] == "Run make session-source-preflight, then dry-run the matching source ladder."
    assert rows["FMP free tier"]["post_setup_smoke_command"] == (
        "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
        "&& make imports-preview IMPORT_TICKERS=<ticker>"
    )
    assert rows["Alpha Vantage free tier"]["safe_next_step"] == (
        "Set ALPHA_VANTAGE_API_KEY in config/provider_keys.env, then rerun make session-source-preflight."
    )
    assert rows["IBKR read-only"]["safe_next_step"] == (
        "Leave disabled unless intentionally using read-only daily OHLCV."
    )
    assert checklist["setup_commands"] == [
        "cp config/provider_keys.env.example config/provider_keys.env",
        "chmod 600 config/provider_keys.env",
        "edit config/provider_keys.env locally; do not commit real keys",
    ]
    assert checklist["activation_plan"][0].startswith("Run make project-status first")
    assert "Configure at most one missing keyed free-tier provider locally" in checklist["activation_plan"][1]
    assert checklist["workflow_pivot"] == [
        {
            "command": "make project-status",
            "purpose": "Confirm whether proof queues have executable company candidates before opening broad proof tables.",
            "boundary": "Read-only status; does not refresh, stage, apply, or unlock blocked inputs.",
        },
        {
            "command": "make provider-setup-checklist",
            "purpose": "Review missing keyed providers and reviewed one-ticker smoke commands when proof queues are exhausted.",
            "boundary": "Setup evidence only; do not apply data directly from provider setup.",
        },
        {
            "command": "make universe-scope TOP_N=10",
            "purpose": "Choose active-universe, ticker-list, sector/theme, ready-only, or missing-data scope before deeper review.",
            "boundary": "Scope selection only; does not infer missing fundamentals, peers, earnings, or estimates.",
        },
        {
            "command": "make risk-context",
            "purpose": "Review liquidity, correlation, and proxy-risk readiness after scope is chosen.",
            "boundary": "Historical context only; not a recommendation or source-proof unlock.",
        },
        {
            "command": "make universe-preview-summary",
            "purpose": "Preview capped S&P 500 / SMH universe metadata and source warnings before any row-scope stage or apply step.",
            "boundary": "Universe membership is metadata only; it does not unlock fundamentals, share count, DCF, peers, earnings, estimates, or recommendations.",
        },
    ]
    assert rows["SEC submissions"]["cannot_unlock"] == (
        "DCF, valuation, earnings, analyst estimates, or share count unless a filing document has an explicit fact."
    )
    assert checklist["secret_policy"] == "Real key values are never printed."
    assert "secret-fmp-key" not in json.dumps(checklist)
    assert "secret-fmp-key" not in rendered
    assert "Local setup commands:" in rendered
    assert "First provider answer:" in rendered
    assert "- question: What source can I use next?" in rendered
    assert "- free_source_now: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance" in rendered
    assert "- missing_key: Alpha Vantage free tier, Finnhub free tier" in rendered
    assert "- setup_prerequisite: FMP free tier is configured; choose one reviewed ticker before running the reviewed one-ticker smoke command." in rendered
    assert "- ticker_scope_rule: Choose one reviewed ticker from make project-status or a current proof packet before replacing <ticker>; do not run the reviewed one-ticker smoke command across a broad list." in rendered
    assert "- reviewed_one_ticker_smoke: make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>" in rendered
    assert "one_safe_smoke" not in rendered
    assert rendered.index("First provider answer:") < rendered.index("Coverage unlock decision:")
    assert rendered.index("First provider answer:") < rendered.index("Local setup commands:")
    assert "What can run now?" in rendered
    assert "Free public sources: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance" in rendered
    assert "Keyed free-tier fallbacks: configured FMP free tier; needs key Alpha Vantage free tier, Finnhub free tier" in rendered
    assert "Optional broker boundary: IBKR read-only (disabled unless explicitly configured)" in rendered
    assert "Apply gate: validate, preview, rejected-row review, source provenance, and explicit apply/skip decision are still required." in rendered
    assert "free_public_now: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance" in rendered
    assert "configured_keyed: FMP free tier" in rendered
    assert "needs_key: Alpha Vantage free tier, Finnhub free tier" in rendered
    assert "optional_broker: IBKR read-only (disabled unless explicitly configured)" in rendered
    assert "Use the free/public baseline first" in rendered
    assert "- cp config/provider_keys.env.example config/provider_keys.env" in rendered
    assert "- chmod 600 config/provider_keys.env" in rendered
    assert "- edit config/provider_keys.env locally; do not commit real keys" in rendered
    assert "Activation plan:" in rendered
    assert "- Configure at most one missing keyed free-tier provider locally, then rerun make session-source-preflight." in rendered
    assert "- Run that provider's reviewed one-ticker smoke command only; do not start a broad batch from setup." in rendered
    assert "Workflow pivot when proof queues are exhausted:" in rendered
    assert "make project-status | Confirm whether proof queues have executable company candidates before opening broad proof tables." in rendered
    assert "make provider-setup-checklist | Review missing keyed providers and reviewed one-ticker smoke commands when proof queues are exhausted." in rendered
    assert "make universe-scope TOP_N=10 | Choose active-universe, ticker-list, sector/theme, ready-only, or missing-data scope before deeper review." in rendered
    assert "make risk-context | Review liquidity, correlation, and proxy-risk readiness after scope is chosen." in rendered
    assert "make universe-preview-summary | Preview capped S&P 500 / SMH universe metadata and source warnings before any row-scope stage or apply step." in rendered
    assert rendered.index("make project-status | Confirm whether") < rendered.index(
        "make provider-setup-checklist | Review missing keyed providers"
    )
    assert rendered.index("make provider-setup-checklist | Review missing keyed providers") < rendered.index(
        "make universe-scope TOP_N=10 | Choose active-universe"
    )
    assert rendered.index("make universe-scope TOP_N=10 | Choose active-universe") < rendered.index(
        "make risk-context | Review liquidity"
    )
    assert rendered.index("make risk-context | Review liquidity") < rendered.index(
        "make universe-preview-summary | Preview capped S&P 500 / SMH universe metadata"
    )
    assert "FMP free tier | configured | price, fundamentals, share_count" in rendered
    assert "Alpha Vantage free tier | needs_key" in rendered
    assert "Provider | Setup state | Unlock lanes | Usage | Batch policy | Smoke command | Cannot unlock | Safe next step" in rendered
    assert "SEC submissions | available | metadata | metadata_evidence_only | not_applicable | not_applicable | DCF, valuation, earnings, analyst estimates, or share count unless a filing document has an explicit fact." in rendered
    assert "FMP free tier | configured | price, fundamentals, share_count | keyed_free_tier_fallback | small_batch_only; recommended <=250 requests/day and <=25 tickers/run" in rendered
    assert "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>" in rendered
    assert "Alpha Vantage free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | small_batch_only; recommended <=25 requests/day and <=5 tickers/run" in rendered
    assert "Finnhub free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | small_batch_only; recommended <=60 requests/day and <=10 tickers/run" in rendered
    assert "IBKR read-only | optional_disabled | price" in rendered
    assert "No investment advice" in rendered
    assert "direct buy/sell instructions" in rendered


def test_provider_setup_checklist_starts_with_source_boundary_decision_table(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "secret-fmp-key")
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("IBKR_HOST", raising=False)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    monkeypatch.delenv("IBKR_CLIENT_ID", raising=False)

    checklist = build_provider_setup_checklist()
    rendered = render_provider_setup_checklist(checklist)

    assert checklist["source_boundary_decision"] == [
        {
            "source_group": "Free public sources",
            "use_for": "SEC facts, filing metadata, explicit filing-document shares, daily OHLCV, provider-assisted fundamentals",
            "status": "usable now",
            "setup_boundary": "Use preflight and one reviewed ticker before any validate/preview/apply path.",
            "next_safe_action": "make session-source-preflight",
        },
        {
            "source_group": "Keyed free-tier fallbacks",
            "use_for": "Small-batch price, fundamentals, and share-count fallback rows",
            "status": "configured: FMP free tier; missing: Alpha Vantage free tier, Finnhub free tier",
            "setup_boundary": "Configure at most one missing key; key setup is not data proof.",
            "next_safe_action": "make provider-setup-checklist",
        },
        {
            "source_group": "Metadata-only evidence",
            "use_for": "Ticker/entity, CIK, SIC, exchange, filing recency, source routing",
            "status": "context only",
            "setup_boundary": "Metadata never unlocks DCF, valuation, earnings, estimates, or share count unless an explicit filing fact is staged.",
            "next_safe_action": "make trusted-data-pilot-packet TICKER=<ticker>",
        },
        {
            "source_group": "Optional broker",
            "use_for": "Read-only daily OHLCV only when explicitly configured",
            "status": "disabled by default",
            "setup_boundary": "Do not use broker/account/order APIs; leave disabled unless intentionally configured.",
            "next_safe_action": "No action unless choosing IBKR read-only daily bars.",
        },
        {
            "source_group": "Paid or locked optional lanes",
            "use_for": "Earnings and analyst estimates only after trusted provider/manual rows exist",
            "status": "locked until source-backed rows exist",
            "setup_boundary": "Do not infer or publish optional context from missing provider data.",
            "next_safe_action": "make optional-context-source-ladder-queue TOP_N=10",
        },
    ]
    assert "Source boundary decision:" in rendered
    assert "Source group | Use for | Status | Setup boundary | Next safe action" in rendered
    assert "Free public sources | SEC facts, filing metadata, explicit filing-document shares, daily OHLCV, provider-assisted fundamentals | usable now" in rendered
    assert "Keyed free-tier fallbacks | Small-batch price, fundamentals, and share-count fallback rows | configured: FMP free tier; missing: Alpha Vantage free tier, Finnhub free tier" in rendered
    assert "Metadata-only evidence | Ticker/entity, CIK, SIC, exchange, filing recency, source routing | context only" in rendered
    assert "Optional broker | Read-only daily OHLCV only when explicitly configured | disabled by default" in rendered
    assert "Paid or locked optional lanes | Earnings and analyst estimates only after trusted provider/manual rows exist | locked until source-backed rows exist" in rendered
    assert rendered.index("Source boundary decision:") < rendered.index("Provider setup and boundaries:")
    assert "secret-fmp-key" not in rendered


def test_provider_setup_checklist_names_one_missing_keyed_provider_to_configure_first(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("IBKR_HOST", raising=False)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    monkeypatch.delenv("IBKR_CLIENT_ID", raising=False)

    checklist = build_provider_setup_checklist()
    rendered = render_provider_setup_checklist(checklist)

    assert checklist["first_answer"]["setup_prerequisite"] == (
        "Configure FMP free tier with FMP_API_KEY before running its reviewed one-ticker smoke command."
    )
    assert checklist["one_provider_setup_order"] == [
        {
            "provider": "FMP free tier",
            "why_first": "Broadest keyed fallback here: price, fundamentals, share count, and the largest stated free-tier daily cap.",
            "setup_env": "FMP_API_KEY",
            "smoke_command": (
                "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
                "&& make imports-preview IMPORT_TICKERS=<ticker>"
            ),
        },
        {
            "provider": "Finnhub free tier",
            "why_first": "Second fallback after FMP; use only if FMP is unavailable or insufficient for the reviewed ticker.",
            "setup_env": "FINNHUB_API_KEY",
            "smoke_command": (
                "make finnhub-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
                "&& make imports-preview IMPORT_TICKERS=<ticker>"
            ),
        },
        {
            "provider": "Alpha Vantage free tier",
            "why_first": "Smallest stated free-tier cap; keep as a final small-batch fallback.",
            "setup_env": "ALPHA_VANTAGE_API_KEY",
            "smoke_command": (
                "make alpha-vantage-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
                "&& make imports-preview IMPORT_TICKERS=<ticker>"
            ),
        },
    ]
    assert "Configure first: FMP free tier" in rendered
    assert "- setup_prerequisite: Configure FMP free tier with FMP_API_KEY before running its reviewed one-ticker smoke command." in rendered
    assert "- reviewed_smoke_command: make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>" in rendered
    assert "rerun preflight, run a reviewed one-ticker smoke command, then validate/preview before any apply" in rendered
    assert "- smoke_command:" not in rendered
    assert "Do not configure all missing providers at once" in rendered
    assert rendered.index("Configure first: FMP free tier") < rendered.index("Provider setup and boundaries:")


def test_provider_setup_checklist_starts_with_coverage_unlock_decision(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("IBKR_HOST", raising=False)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    monkeypatch.delenv("IBKR_CLIENT_ID", raising=False)
    current_preflight = {
        "source_activation_console_v2": {
            "operator_summary": {
                "can_run_now": ["coverage_workflow_evidence"],
                "needs_setup": ["fmp", "alpha_vantage", "finnhub"],
                "avoid_repeating": ["fundamentals_share_count_source_ladder"],
                "next_step": "make project-status",
                "next_step_reason": "Current proof queues are exhausted.",
            },
        },
    }

    checklist = build_provider_setup_checklist(current_preflight)
    rendered = render_provider_setup_checklist(checklist)

    assert checklist["coverage_unlock_decision"] == {
        "answer": "No broad coverage batch should run from setup alone.",
        "can_use_now": "Use free/public sources for already executable proof paths; current gate says coverage_workflow_evidence.",
            "configure_first": "Configure FMP free tier first only if you want a keyed fallback, then run a reviewed one-ticker smoke command.",
        "do_not_retry": "Do not retry fundamentals_share_count_source_ladder until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist.",
        "proof_boundary": "Provider setup only makes a source executable; readiness changes still require validate, preview, rejected-row review, source provenance, apply/skip decision, rebuilt readiness, and proof ledger evidence.",
    }
    assert "Coverage unlock decision:" in rendered
    assert "- answer: No broad coverage batch should run from setup alone." in rendered
    assert (
        "- can_use_now: Use free/public sources for already executable proof paths; "
        "current gate says workflow evidence only; current source-proof queues are exhausted."
    ) in rendered
    assert "- configure_first: Configure FMP free tier first only if you want a keyed fallback, then run a reviewed one-ticker smoke command." in rendered
    assert (
        "- do_not_retry: Do not retry fundamentals/share-count source ladder until new source-backed rows, "
        "keyed provider data, reviewed manual rows, or changed blockers exist."
    ) in rendered
    assert "- proof_boundary: Provider setup only makes a source executable; readiness changes still require validate, preview, rejected-row review, source provenance, apply/skip decision, rebuilt readiness, and proof ledger evidence." in rendered
    assert checklist["first_answer"]["do_not_retry"] == (
        "Do not retry fundamentals_share_count_source_ladder until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist."
    )
    assert checklist["first_answer"]["ticker_scope_rule"] == (
        "Choose one reviewed ticker from make project-status or a current proof packet before replacing <ticker>; do not run the reviewed one-ticker smoke command across a broad list."
    )
    assert rendered.index("First provider answer:") < rendered.index("Coverage unlock decision:")
    assert rendered.index("Coverage unlock decision:") < rendered.index("Local setup commands:")


def test_provider_setup_checklist_includes_current_gate_without_fetching_sources(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    current_preflight = {
        "source_activation": {
            "status": "not_required",
            "reason_code": "workflow_evidence_only",
            "detail": "Sources are reachable, but current blockers already have reviewed non-actionable proof.",
            "next_action": "Use project-status or provider setup evidence until new data appears.",
        },
        "source_activation_console_v2": {
            "next_executable_lane": "coverage_workflow_evidence",
            "next_executable_command": "make project-status",
            "operator_summary": {
                "can_run_now": ["coverage_workflow_evidence"],
                "needs_setup": ["fmp", "alpha_vantage", "finnhub"],
                "avoid_repeating": ["fundamentals_share_count_source_ladder"],
                "next_step": "make project-status",
                "next_step_reason": "Wait for new provider data before repeating the source ladder.",
            },
        },
    }

    checklist = build_provider_setup_checklist(current_preflight)
    rendered = render_provider_setup_checklist(checklist)

    assert checklist["current_gate"] == {
        "can_run_now": "coverage_workflow_evidence",
        "needs_setup": "fmp, alpha_vantage, finnhub",
        "avoid_repeating": "fundamentals_share_count_source_ladder",
        "next_step": "make project-status",
        "next_step_reason": "Wait for new provider data before repeating the source ladder.",
        "source_activation_reason": "workflow_evidence_only",
        "source_activation_detail": "Sources are reachable, but current blockers already have reviewed non-actionable proof.",
        "source_activation_next_action": "Use project-status or provider setup evidence until new data appears.",
    }
    assert "Current source gate:" in rendered
    assert "source_activation_reason: workflow evidence only" in rendered
    assert "source_activation_reason: workflow_evidence_only" not in rendered
    assert "source_activation_detail: Sources are reachable, but current blockers already have reviewed non-actionable proof." in rendered
    assert "can_run_now: workflow evidence only; current source-proof queues are exhausted" in rendered
    assert "needs_setup: fmp, alpha_vantage, finnhub" in rendered
    assert "avoid_repeating: fundamentals/share-count source ladder" in rendered
    assert "next_step: make project-status" in rendered
    assert "secret-fmp-key" not in json.dumps(checklist)
