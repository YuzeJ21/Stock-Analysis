import json

from src.optional_context_sources import (
    build_alpha_vantage_optional_context_rows,
    build_fmp_optional_context_rows,
    build_optional_context_source_ladder_rows,
    write_optional_context_import,
)


class _Response:
    def __init__(self, payload, *, raw: bool = False):
        self.payload = payload
        self.raw = raw
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        if self.raw:
            return str(self.payload).encode("utf-8")
        return json.dumps(self.payload).encode("utf-8")


def test_alpha_vantage_optional_context_maps_earnings_history_to_staged_rows():
    def opener(request, timeout=20):
        assert timeout == 20
        assert "function=EARNINGS" in request.full_url
        assert "symbol=IBM" in request.full_url
        return _Response(
            {
                "quarterlyEarnings": [
                    {
                        "fiscalDateEnding": "2025-12-31",
                        "reportedDate": "2026-01-24",
                        "reportedEPS": "3.50",
                        "estimatedEPS": "3.40",
                        "surprisePercentage": "2.94",
                    }
                ]
            }
        )

    result = build_alpha_vantage_optional_context_rows(["IBM"], api_key="demo", opener=opener)

    assert result["resolved_tickers"] == ["IBM"]
    earnings = result["earnings_rows"][0]
    estimates = result["analyst_estimate_rows"][0]
    assert earnings["ticker"] == "IBM"
    assert earnings["source"] == "alpha_vantage_research_api"
    assert earnings["last_earnings_date"] == "2026-01-24"
    assert earnings["eps_actual"] == 3.5
    assert earnings["eps_estimate"] == 3.4
    assert earnings["surprise_pct"] == 2.94
    assert estimates["current_quarter_eps"] == 3.4
    assert estimates["source"] == "alpha_vantage_research_api"


def test_fmp_optional_context_maps_earnings_and_estimates_payloads():
    def opener(request, timeout=20):
        assert timeout == 20
        url = request.full_url
        if "/historical/earning_calendar/NVDA" in url:
            return _Response(
                [
                    {
                        "date": "2026-02-18",
                        "fiscalDateEnding": "2026-01-31",
                        "eps": 1.25,
                        "epsEstimated": 1.2,
                        "revenue": 32000000000,
                        "revenueEstimated": 31500000000,
                    }
                ]
            )
        if "/analyst-estimates/NVDA" in url:
            return _Response(
                [
                    {
                        "date": "2026-01-31",
                        "estimatedEpsAvg": 1.2,
                        "estimatedRevenueAvg": 31500000000,
                    }
                ]
            )
        raise AssertionError(url)

    result = build_fmp_optional_context_rows(["NVDA"], api_key="demo", opener=opener)

    assert result["resolved_tickers"] == ["NVDA"]
    earnings = result["earnings_rows"][0]
    estimates = result["analyst_estimate_rows"][0]
    assert earnings["ticker"] == "NVDA"
    assert earnings["source"] == "fmp_research_api"
    assert earnings["last_earnings_date"] == "2026-02-18"
    assert earnings["revenue_actual"] == 32000000000.0
    assert earnings["revenue_estimate"] == 31500000000.0
    assert estimates["period"] == "2026-01-31"
    assert estimates["current_quarter_eps"] == 1.2
    assert estimates["current_quarter_revenue"] == 31500000000.0


def test_optional_context_ladder_continues_until_each_dataset_has_rows(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "demo")

    def yfinance_builder(tickers):
        assert tickers == ["NVDA"]
        return {
            "requested_tickers": ["NVDA"],
            "resolved_tickers": ["NVDA"],
            "unresolved_tickers": [],
            "earnings_rows": [
                {
                    "ticker": "NVDA",
                    "last_earnings_date": "2026-02-18",
                    "eps_actual": 1.25,
                    "source": "yfinance_research_api",
                }
            ],
            "analyst_estimate_rows": [],
            "row_summaries": [],
            "warnings": [],
        }

    def fmp_builder(tickers, api_key):
        assert tickers == ["NVDA"]
        assert api_key == "demo"
        return {
            "requested_tickers": ["NVDA"],
            "resolved_tickers": ["NVDA"],
            "unresolved_tickers": [],
            "earnings_rows": [
                {
                    "ticker": "NVDA",
                    "last_earnings_date": "2026-02-18",
                    "eps_actual": 1.2,
                    "source": "fmp_research_api",
                }
            ],
            "analyst_estimate_rows": [
                {
                    "ticker": "NVDA",
                    "current_quarter_eps": 1.2,
                    "source": "fmp_research_api",
                }
            ],
            "row_summaries": [],
            "warnings": [],
        }

    result = build_optional_context_source_ladder_rows(
        ["NVDA"],
        yfinance_builder=yfinance_builder,
        fmp_builder=fmp_builder,
    )

    assert result["resolved_tickers"] == ["NVDA"]
    assert result["earnings_rows"] == [
        {
            "ticker": "NVDA",
            "last_earnings_date": "2026-02-18",
            "eps_actual": 1.25,
            "source": "yfinance_research_api",
        }
    ]
    assert result["analyst_estimate_rows"] == [
        {
            "ticker": "NVDA",
            "current_quarter_eps": 1.2,
            "source": "fmp_research_api",
        }
    ]
    assert result["provider_attempts"][0]["provider"] == "yfinance"
    assert result["provider_attempts"][0]["resolved_tickers"] == ["NVDA"]
    assert result["provider_attempts"][1]["provider"] == "fmp"
    assert result["provider_attempts"][1]["resolved_tickers"] == ["NVDA"]


def test_write_optional_context_import_preserves_existing_row_when_only_updated_at_changes(tmp_path):
    import_path = tmp_path / "data" / "imports" / "earnings.csv"

    first = write_optional_context_import(
        "earnings",
        [
            {
                "ticker": "NVDA",
                "next_earnings_date": "2026-08-26",
                "source": "yfinance_research_api",
                "updated_at": "2026-07-01T08:00:00+00:00",
            }
        ],
        import_path,
    )
    second = write_optional_context_import(
        "earnings",
        [
            {
                "ticker": "NVDA",
                "next_earnings_date": "2026-08-26",
                "source": "yfinance_research_api",
                "updated_at": "2026-07-01T09:00:00+00:00",
            }
        ],
        import_path,
    )

    assert first["status"] == "staged"
    assert second["status"] == "unchanged"
    assert "2026-07-01T08:00:00+00:00" in import_path.read_text()
    assert "2026-07-01T09:00:00+00:00" not in import_path.read_text()
