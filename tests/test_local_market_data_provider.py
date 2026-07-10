from pathlib import Path

import pandas as pd
import pytest

from src.providers.local_market_data import LocalCSVMarketDataProvider

RICH_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "rich_local_data"


def _copy_rich_fixture(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for path in RICH_FIXTURE_DIR.glob("*.csv"):
        (data_dir / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_local_provider_returns_quote_for_known_ticker(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n"
        "2026-01-03,SPY,101,1200\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    quote = provider.get_quote("SPY")

    assert quote.ticker == "SPY"
    assert quote.price == 101.0
    assert quote.previous_close == 100.0
    assert quote.source.provider == "local:prices.csv"


def test_local_provider_handles_missing_ticker_gracefully(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    with pytest.raises(LookupError, match="No local price rows were found for AAPL"):
        provider.get_quote("AAPL")


def test_local_provider_handles_sparse_csv_with_missing_optional_fields(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,900,2000\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    quote = provider.get_quote("NVDA")
    history = provider.get_price_history("NVDA", period="1y", interval="1d")

    assert quote.open is None
    assert quote.day_high is None
    assert quote.day_low is None
    assert list(history.columns) == ["date", "open", "high", "low", "close", "volume"]


def test_local_provider_returns_short_history_without_fabricating_lookback(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-05-01,QQQ,100,1000\n"
        "2026-05-02,QQQ,101,1000\n"
        "2026-05-03,QQQ,102,1000\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    history = provider.get_price_history("QQQ", period="1y", interval="1d")

    assert len(history) == 3
    assert history["close"].iloc[-1] == 102


def test_local_provider_date_parsing_is_consistent(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "Date,Ticker,Adj Close,Volume\n"
        "2026-01-02,SPY,100,1000\n"
        "2026/01/03,SPY,101,1001\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    history = provider.get_price_history("SPY", period="1y", interval="1d")

    assert len(history) == 2
    assert pd.api.types.is_datetime64_any_dtype(history["date"])


def test_local_provider_reuses_prepared_price_frame(tmp_path: Path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n"
        "2026-01-03,SPY,101,1200\n"
        "2026-01-02,QQQ,200,1000\n"
        "2026-01-03,QQQ,202,1200\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)
    original = provider.catalog.load_dataframe
    price_loads = []

    def wrapped_load_dataframe(dataset_name: str):
        if dataset_name == "prices":
            price_loads.append(dataset_name)
        return original(dataset_name)

    monkeypatch.setattr(provider.catalog, "load_dataframe", wrapped_load_dataframe)

    assert provider.get_quote("SPY").price == 101.0
    assert provider.get_price_history("SPY", period="1y", interval="1d").iloc[-1]["close"] == 101.0
    assert provider.get_quote("QQQ").price == 202.0

    assert price_loads == ["prices"]


def test_local_provider_reuses_financial_and_peer_lookups(tmp_path: Path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,ALFA,150,1000\n"
        "2026-01-02,BETA,90,1000\n"
        "2026-01-02,GAMMA,80,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,revenue,eps,free_cash_flow,shares_outstanding,market_cap\n"
        "ALFA,1000,5,100,10,1500\n"
        "BETA,800,4,90,12,1080\n"
        "GAMMA,700,3,80,11,880\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "peers.csv").write_text(
        "ticker,peer_ticker,peer_group\n"
        "ALFA,BETA,test_group\n"
        "ALFA,GAMMA,test_group\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)
    original = provider.catalog.load_dataframe
    loads = []

    def wrapped_load_dataframe(dataset_name: str):
        loads.append(dataset_name)
        return original(dataset_name)

    monkeypatch.setattr(provider.catalog, "load_dataframe", wrapped_load_dataframe)

    summary = provider.get_peer_summary("ALFA")
    inputs = provider.get_peer_valuation_inputs("ALFA")
    financials = provider.get_financials("BETA")

    assert summary["peer_count"] == 2
    assert {item["ticker"] for item in inputs} == {"BETA", "GAMMA"}
    assert financials.revenue == 800.0
    assert loads.count("fundamentals") == 1
    assert loads.count("peers") == 1
    assert loads.count("prices") == 1


def test_local_provider_loads_fundamentals_fixture_when_available(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,revenue,eps,free_cash_flow,pe_ratio,profit_margin\n"
        "NVDA,1000,4.5,250,30,0.35\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    financials = provider.get_financials("NVDA")

    assert financials.revenue == 1000.0
    assert financials.eps == 4.5
    assert financials.free_cash_flow == 250.0
    assert financials.trailing_pe == 30.0


def test_local_provider_loads_earnings_fixture_when_available(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "earnings.csv").write_text(
        "ticker,next_earnings_date,last_earnings_date,fiscal_period,eps_estimate,eps_actual,surprise_pct\n"
        "NVDA,2026-05-30,2026-02-25,Q2-2026,1.2,1.3,0.08\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    earnings = provider.get_earnings("NVDA")

    assert earnings.next_earnings_date == "2026-05-30"
    assert earnings.fiscal_period == "Q2-2026"
    assert earnings.eps_estimate == 1.2
    assert earnings.surprise_pct == 0.08


def test_local_provider_handles_sparse_earnings_row_without_crashing(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "earnings.csv").write_text(
        "ticker,source,as_of_date\n"
        "NVDA,manual,2026-05-01\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    earnings = provider.get_earnings("NVDA")

    assert earnings.ticker == "NVDA"
    assert earnings.next_earnings_date is None
    assert earnings.source is not None
    assert "Dataset row source: manual" in " ".join(earnings.source.notes)


def test_local_provider_loads_analyst_estimate_fixture_when_available(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "analyst_estimates.csv").write_text(
        "ticker,current_quarter_eps,next_quarter_eps,current_quarter_revenue,target_mean_price,target_high_price,target_low_price,recommendation,revision_trend\n"
        "NVDA,1.2,1.4,34000,220,250,180,hold,stable\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    estimates = provider.get_analyst_estimates("NVDA")

    assert estimates.current_quarter_eps == 1.2
    assert estimates.next_quarter_eps == 1.4
    assert estimates.current_quarter_revenue == 34000.0
    assert estimates.target_mean_price == 220.0
    assert estimates.target_high_price == 250.0
    assert estimates.target_low_price == 180.0
    assert estimates.recommendation == "hold"
    assert estimates.revision_trend == "stable"


def test_local_provider_handles_sparse_analyst_estimate_row_without_crashing(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "analyst_estimates.csv").write_text(
        "ticker,source,as_of_date\n"
        "NVDA,manual,2026-05-01\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    estimates = provider.get_analyst_estimates("NVDA")

    assert estimates.ticker == "NVDA"
    assert estimates.target_mean_price is None
    assert estimates.source is not None
    assert "Dataset row source: manual" in " ".join(estimates.source.notes)


def test_local_provider_handles_missing_optional_dataset_files(tmp_path: Path):
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    financials = provider.get_financials("NVDA")
    earnings = provider.get_earnings("NVDA")
    estimates = provider.get_analyst_estimates("NVDA")

    assert financials.revenue is None
    assert "No trusted earnings CSV has been added yet" in earnings.notes[0]
    assert "No trusted analyst-estimate CSV has been added yet" in estimates.notes[0]


def test_local_provider_surfaces_existing_screener_context(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "final_watchlist.csv").write_text(
        "Ticker,FinalState,Reason\n"
        "NVDA,Watch,Fixture row\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    context = provider.get_screener_context("NVDA")

    assert context["final_watchlist"]["finalstate"] == "Watch"
    assert context["final_watchlist"]["reason"] == "Fixture row"


def test_local_provider_preserves_source_and_as_of_date_from_rich_fixture(tmp_path: Path):
    provider = LocalCSVMarketDataProvider(base_dir=_copy_rich_fixture(tmp_path))

    financials = provider.get_financials("ALFA")
    quote = provider.get_quote("ALFA")
    earnings = provider.get_earnings("ALFA")
    estimates = provider.get_analyst_estimates("ALFA")

    assert financials.as_of_date == "2026-05-01"
    assert financials.reporting_period == "FY2026"
    assert financials.currency == "USD"
    assert quote.currency == "USD"
    assert "fixture_fundamentals" in " ".join(financials.source.notes)
    assert earnings.fiscal_period == "Q2-2026"
    assert "fixture_earnings" in " ".join(earnings.source.notes)
    assert estimates.target_high_price == 180.0
    assert estimates.target_low_price == 145.0
    assert estimates.revision_trend == "stable"
    assert "fixture_estimates" in " ".join(estimates.source.notes)


def test_local_provider_loads_peer_fixture_when_available(tmp_path: Path):
    provider = LocalCSVMarketDataProvider(base_dir=_copy_rich_fixture(tmp_path))

    peer_tickers = provider.get_peer_tickers("ALFA")
    peer_inputs = provider.get_peer_valuation_inputs("ALFA")

    assert peer_tickers == ["BETA", "GAMMA"]
    assert {item["ticker"] for item in peer_inputs} == {"BETA", "GAMMA"}


def test_local_provider_peer_summary_reports_group_and_availability(tmp_path: Path):
    provider = LocalCSVMarketDataProvider(base_dir=_copy_rich_fixture(tmp_path))

    summary = provider.get_peer_summary("ALFA")

    assert summary["peer_dataset_present"] is True
    assert summary["peer_group"] == "fixture_group"
    assert summary["peer_count"] == 2
    assert summary["peer_fundamentals_available"] == 2


def test_local_provider_peer_summary_distinguishes_candidate_and_trusted_layers(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-05-01,ALFA,150,1000\n"
        "2026-05-01,BETA,90,1000\n"
        "2026-05-01,GAMMA,80,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,revenue,free_cash_flow,fcf_margin,shares_outstanding,source\n"
        "ALFA,1000,100,0.1,10,fixture\n"
        "BETA,800,90,0.11,12,fixture\n"
        "GAMMA,700,80,0.09,11,fixture\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "peers.csv").write_text(
        "ticker,peer_ticker,peer_group,source\n"
        "ALFA,BETA,trusted_group,fixture\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "peer_candidates.csv").write_text(
        "ticker,peer_ticker,candidate_state,peer_group,source\n"
        "ALFA,BETA,candidate,candidate_group,fixture\n"
        "ALFA,GAMMA,research_only,candidate_group,fixture\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    summary = provider.get_peer_summary("ALFA")

    assert summary["peer_count"] == 1
    assert summary["peer_group"] == "trusted_group"
    assert summary["candidate_dataset_present"] is True
    assert summary["candidate_peer_count"] == 2
    assert summary["candidate_peer_group"] == "candidate_group"
    assert summary["candidate_mapping_status"] == "candidate_available"
    assert summary["candidate_states"] == ["candidate", "research_only"]
    assert summary["candidate_peer_tickers"] == ["BETA", "GAMMA"]


def test_local_provider_ignores_self_peers_and_duplicate_rows(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-05-01,ALFA,150,1000\n"
        "2026-05-01,BETA,90,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,revenue,eps,free_cash_flow,shares_outstanding,market_cap\n"
        "ALFA,1000,5,100,10,1500\n"
        "BETA,800,4,90,12,1080\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "peers.csv").write_text(
        "ticker,peer_ticker,peer_group\n"
        "ALFA,ALFA,test_group\n"
        "ALFA,BETA,test_group\n"
        "ALFA,BETA,test_group\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    summary = provider.get_peer_summary("ALFA")
    peer_tickers = provider.get_peer_tickers("ALFA")

    assert peer_tickers == ["BETA"]
    assert any("self-peer" in warning.lower() for warning in summary["warnings"])
    assert any("duplicate" in warning.lower() for warning in summary["warnings"])


def test_local_provider_exposes_validation_metadata(tmp_path: Path):
    provider = LocalCSVMarketDataProvider(base_dir=_copy_rich_fixture(tmp_path))

    validation = provider.get_local_data_validation()

    fundamentals = next(item for item in validation if item["name"] == "fundamentals")
    assert fundamentals["validation_status"] == "valid"
    assert "revenue" in fundamentals["available_optional_columns"]
