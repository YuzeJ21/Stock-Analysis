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
    assert rows["SEC submissions"]["cannot_unlock"] == (
        "DCF, valuation, earnings, analyst estimates, or share count unless a filing document has an explicit fact."
    )
    assert checklist["secret_policy"] == "Real key values are never printed."
    assert "secret-fmp-key" not in json.dumps(checklist)
    assert "secret-fmp-key" not in rendered
    assert "Local setup commands:" in rendered
    assert "- cp config/provider_keys.env.example config/provider_keys.env" in rendered
    assert "- chmod 600 config/provider_keys.env" in rendered
    assert "- edit config/provider_keys.env locally; do not commit real keys" in rendered
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
