import json

from src.providers.alternative_fundamentals import (
    build_alpha_vantage_fundamentals_rows,
    build_fmp_fundamentals_rows,
    build_finnhub_fundamentals_rows,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_build_fmp_fundamentals_rows_maps_statement_payloads():
    def opener(request, timeout=20):
        url = request.full_url
        if "/profile/NVDA" in url:
            return _Response([{"sector": "Technology", "mktCap": 3000, "sharesOutstanding": 100}])
        if "/income-statement/NVDA" in url:
            return _Response(
                [
                    {
                        "date": "2025-01-31",
                        "revenue": 1200,
                        "netIncome": 400,
                        "eps": 4.0,
                        "operatingIncome": 500,
                        "grossProfitRatio": 0.65,
                        "operatingIncomeRatio": 0.41,
                        "netIncomeRatio": 0.33,
                        "ebitda": 550,
                    }
                ]
            )
        if "/cash-flow-statement/NVDA" in url:
            return _Response([{"freeCashFlow": 300}])
        if "/balance-sheet-statement/NVDA" in url:
            return _Response([{"cashAndCashEquivalents": 200, "totalDebt": 50}])
        if "/key-metrics-ttm/NVDA" in url:
            return _Response([{"peRatioTTM": 30, "enterpriseValueTTM": 3100, "debtToEquityTTM": 0.2}])
        raise AssertionError(url)

    result = build_fmp_fundamentals_rows(["NVDA"], api_key="demo", opener=opener)

    assert result["resolved_tickers"] == ["NVDA"]
    row = result["rows"][0]
    assert row["ticker"] == "NVDA"
    assert row["source"] == "fmp_research_api"
    assert row["revenue"] == 1200.0
    assert row["free_cash_flow"] == 300.0
    assert row["fcf_margin"] == 0.25
    assert row["shares_outstanding"] == 100.0
    assert row["as_of_date"] == "2025-01-31"


def test_build_alpha_vantage_fundamentals_rows_maps_statement_payloads():
    def opener(request, timeout=20):
        url = request.full_url
        if "function=OVERVIEW" in url:
            return _Response(
                {
                    "Sector": "Industrials",
                    "MarketCapitalization": "9000",
                    "SharesOutstanding": "300",
                    "PERatio": "20",
                    "ProfitMargin": "0.11",
                    "OperatingMarginTTM": "0.22",
                    "GrossMarginTTM": "0.33",
                    "EBITDA": "700",
                    "EPS": "5.5",
                    "LatestQuarter": "2025-03-31",
                }
            )
        if "function=INCOME_STATEMENT" in url:
            return _Response({"annualReports": [{"fiscalDateEnding": "2024-12-31", "totalRevenue": "1500", "netIncome": "250"}]})
        if "function=CASH_FLOW" in url:
            return _Response({"annualReports": [{"operatingCashflow": "500", "capitalExpenditures": "100"}]})
        if "function=BALANCE_SHEET" in url:
            return _Response({"annualReports": [{"cashAndCashEquivalentsAtCarryingValue": "80", "shortLongTermDebtTotal": "30"}]})
        raise AssertionError(url)

    result = build_alpha_vantage_fundamentals_rows(["BA"], api_key="demo", opener=opener)

    assert result["resolved_tickers"] == ["BA"]
    row = result["rows"][0]
    assert row["source"] == "alpha_vantage_research_api"
    assert row["revenue"] == 1500.0
    assert row["free_cash_flow"] == 400.0
    assert row["fcf_margin"] == 400.0 / 1500.0
    assert row["shares_outstanding"] == 300.0
    assert row["cash"] == 80.0
    assert row["debt"] == 30.0


def test_build_finnhub_fundamentals_rows_maps_profile_and_metric_payloads():
    def opener(request, timeout=20):
        url = request.full_url
        if "stock/profile2" in url:
            return _Response(
                {
                    "finnhubIndustry": "Semiconductors",
                    "marketCapitalization": 9000,
                    "shareOutstanding": 300,
                }
            )
        if "stock/metric" in url:
            return _Response(
                {
                    "metric": {
                        "revenueTTM": 1500,
                        "netIncomeEmployeeAnnual": None,
                        "epsTTM": 5.5,
                        "fcfMarginTTM": 0.2,
                        "freeCashFlowTTM": 300,
                        "netProfitMarginTTM": 0.11,
                        "operatingMarginTTM": 0.22,
                        "grossMarginTTM": 0.33,
                        "ebitdaTTM": 700,
                        "peTTM": 20,
                        "pbAnnual": 3.1,
                        "totalDebt/totalEquityAnnual": 0.4,
                        "cashRatioAnnual": 0.8,
                    }
                }
            )
        raise AssertionError(url)

    result = build_finnhub_fundamentals_rows(["BA"], api_key="demo", opener=opener)

    assert result["resolved_tickers"] == ["BA"]
    row = result["rows"][0]
    assert row["source"] == "finnhub_research_api"
    assert row["sector"] == "Semiconductors"
    assert row["revenue"] == 1500.0
    assert row["free_cash_flow"] == 300.0
    assert row["fcf_margin"] == 0.2
    assert row["shares_outstanding"] == 300_000_000.0
    assert row["market_cap"] == 9_000_000_000.0
    assert row["eps"] == 5.5
    assert row["trailing_pe"] == 20.0
