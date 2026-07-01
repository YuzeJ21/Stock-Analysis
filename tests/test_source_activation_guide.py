import json

from src.source_activation_guide import build_source_activation_guide, render_source_activation_guide


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
