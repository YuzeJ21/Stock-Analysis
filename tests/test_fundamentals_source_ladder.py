from src.fundamentals_source_ladder import build_fundamentals_source_ladder_rows


def test_fundamentals_source_ladder_uses_fmp_after_sec_and_yfinance_fail(monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)

    def sec_builder(tickers, **_kwargs):
        return {
            "requested_tickers": list(tickers),
            "resolved_tickers": [],
            "unresolved_tickers": list(tickers),
            "rows": [],
            "row_summaries": [],
            "warnings": ["SEC unavailable"],
        }

    def yfinance_builder(tickers):
        return {
            "requested_tickers": list(tickers),
            "resolved_tickers": [],
            "unresolved_tickers": list(tickers),
            "rows": [],
            "row_summaries": [],
            "warnings": ["yfinance unavailable"],
        }

    def fmp_builder(tickers, **_kwargs):
        return {
            "requested_tickers": list(tickers),
            "resolved_tickers": ["BA"],
            "unresolved_tickers": [],
            "rows": [{"ticker": "BA", "revenue": 1000, "source": "fmp_research_api"}],
            "row_summaries": [
                {
                    "ticker": "BA",
                    "source": "fmp_research_api",
                    "populated_fields": ["revenue"],
                    "missing_fields": [],
                    "warnings": [],
                }
            ],
            "warnings": [],
        }

    result = build_fundamentals_source_ladder_rows(
        ["BA"],
        sec_user_agent=None,
        fmp_api_key="demo",
        alpha_vantage_api_key=None,
        sec_builder=sec_builder,
        yfinance_builder=yfinance_builder,
        fmp_builder=fmp_builder,
    )

    assert result["resolved_tickers"] == ["BA"]
    assert result["unresolved_tickers"] == []
    assert result["rows"] == [{"ticker": "BA", "revenue": 1000, "source": "fmp_research_api"}]
    assert [attempt["provider"] for attempt in result["provider_attempts"]] == ["sec", "yfinance", "fmp", "alpha_vantage", "finnhub"]
    assert result["provider_attempts"][2]["status"] == "resolved_rows"
    assert result["provider_attempts"][3]["status"] == "skipped"
    assert result["provider_attempts"][3]["reason_code"] == "provider_key_missing"
    assert result["provider_attempts"][4]["reason_code"] == "provider_key_missing"


def test_fundamentals_source_ladder_preserves_row_source_when_provider_summary_omits_it(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)

    def sec_builder(tickers, **_kwargs):
        return {
            "requested_tickers": list(tickers),
            "resolved_tickers": ["ARCT"],
            "unresolved_tickers": [],
            "rows": [{"ticker": "ARCT", "revenue": 82_031_000, "source": "sec_companyfacts"}],
            "row_summaries": [
                {
                    "ticker": "ARCT",
                    "populated_fields": ["revenue"],
                    "missing_fields": [],
                    "warnings": [],
                }
            ],
            "warnings": [],
        }

    result = build_fundamentals_source_ladder_rows(
        ["ARCT"],
        sec_user_agent="Analyst analyst@example.com",
        sec_builder=sec_builder,
    )

    assert result["row_summaries"] == [
        {
            "ticker": "ARCT",
            "source": "sec_companyfacts",
            "populated_fields": ["revenue"],
            "missing_fields": [],
            "warnings": [],
        }
    ]


def test_fundamentals_source_ladder_skips_session_blocked_sec_and_yfinance_before_fmp():
    called_providers = []

    def sec_builder(tickers, **_kwargs):
        called_providers.append("sec")
        raise AssertionError("SEC should be skipped by session preflight")

    def yfinance_builder(tickers):
        called_providers.append("yfinance")
        raise AssertionError("yfinance should be skipped by session preflight")

    def fmp_builder(tickers, **_kwargs):
        called_providers.append("fmp")
        return {
            "requested_tickers": list(tickers),
            "resolved_tickers": ["BA"],
            "unresolved_tickers": [],
            "rows": [{"ticker": "BA", "revenue": 1000, "source": "fmp_research_api"}],
            "row_summaries": [
                {
                    "ticker": "BA",
                    "source": "fmp_research_api",
                    "populated_fields": ["revenue"],
                    "missing_fields": [],
                    "warnings": [],
                }
            ],
            "warnings": [],
        }

    result = build_fundamentals_source_ladder_rows(
        ["BA"],
        sec_user_agent="Analyst analyst@example.com",
        fmp_api_key="demo",
        session_preflight={
            "sources": {
                "sec": {"status": "unavailable", "reason_code": "network_error"},
                "yfinance_stage": {"status": "unavailable", "reason_code": "probe_failed"},
                "fmp": {"status": "available", "reason_code": "configured"},
                "alpha_vantage": {"status": "unavailable", "reason_code": "provider_key_missing"},
            },
            "do_not_retry_paths": ["sec", "yfinance_fundamentals"],
        },
        sec_builder=sec_builder,
        yfinance_builder=yfinance_builder,
        fmp_builder=fmp_builder,
    )

    assert called_providers == ["fmp"]
    assert result["resolved_tickers"] == ["BA"]
    assert [attempt["provider"] for attempt in result["provider_attempts"]] == ["sec", "yfinance", "fmp", "alpha_vantage", "finnhub"]
    assert result["provider_attempts"][0]["reason_code"] == "session_preflight_unavailable"
    assert result["provider_attempts"][1]["reason_code"] == "session_preflight_unavailable"
    assert result["provider_attempts"][2]["status"] == "resolved_rows"


def test_fundamentals_source_ladder_uses_finnhub_after_other_sources_fail():
    def no_rows(tickers, **_kwargs):
        return {
            "requested_tickers": list(tickers),
            "resolved_tickers": [],
            "unresolved_tickers": list(tickers),
            "rows": [],
            "row_summaries": [],
            "warnings": ["no rows"],
        }

    def yfinance_builder(tickers):
        return no_rows(tickers)

    def finnhub_builder(tickers, **_kwargs):
        return {
            "requested_tickers": list(tickers),
            "resolved_tickers": ["BA"],
            "unresolved_tickers": [],
            "rows": [{"ticker": "BA", "shares_outstanding": 1000, "source": "finnhub_research_api"}],
            "row_summaries": [
                {
                    "ticker": "BA",
                    "source": "finnhub_research_api",
                    "populated_fields": ["shares_outstanding"],
                    "missing_fields": [],
                    "warnings": [],
                }
            ],
            "warnings": [],
        }

    result = build_fundamentals_source_ladder_rows(
        ["BA"],
        sec_user_agent=None,
        fmp_api_key="demo",
        alpha_vantage_api_key="demo",
        finnhub_api_key="demo",
        sec_builder=no_rows,
        yfinance_builder=yfinance_builder,
        fmp_builder=no_rows,
        alpha_vantage_builder=no_rows,
        finnhub_builder=finnhub_builder,
    )

    assert result["resolved_tickers"] == ["BA"]
    assert result["unresolved_tickers"] == []
    assert [attempt["provider"] for attempt in result["provider_attempts"]] == [
        "sec",
        "yfinance",
        "fmp",
        "alpha_vantage",
        "finnhub",
    ]
    assert result["provider_attempts"][4]["status"] == "resolved_rows"
