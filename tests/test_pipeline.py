from pathlib import Path

import pandas as pd

from src.config import AppConfig
from src.report_generator import printable_warnings, run


def _write_compact_pipeline_project(base_dir: Path) -> None:
    data_dir = base_dir / "data"
    outputs_dir = base_dir / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (base_dir / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (data_dir / "universe.csv").write_text(
        "ticker,theme,sector_etf,default_purpose,market_cap_bucket,notes,is_etf\n"
        "NVDA,AI Infrastructure,SMH,Momentum Leader,Large,fixture,False\n"
        "META,Platform Software,QQQ,Core Compounder,Large,fixture,False\n"
        "SMH,AI Semiconductors,,ETF / Defensive / Hedge,ETF,fixture,True\n",
        encoding="utf-8",
    )
    (data_dir / "holdings.csv").write_text(
        "Ticker,Shares,CostBasis,PositionPercent,PrimaryPurpose,SecondaryTags,OriginalThesis,MaxPositionPercent,InvalidationOverride\n"
        "NVDA,1,100,5,Momentum Leader,Core Compounder,fixture thesis,10,\n"
        "META,1,100,5,Core Compounder,,fixture thesis,10,\n",
        encoding="utf-8",
    )
    (data_dir / "theme_map.csv").write_text(
        "Theme,ETF,Description\n"
        "AI Infrastructure,SMH,Semiconductor and AI infrastructure context\n"
        "Platform Software,QQQ,Large-cap platform software context\n",
        encoding="utf-8",
    )
    (data_dir / "fundamentals.csv").write_text(
        "ticker,theme,sector,pe_ratio,revenue_growth,profit_margin,debt_to_equity,revenue,eps,free_cash_flow,fcf_margin,shares_outstanding,source,as_of_date\n"
        "NVDA,AI Infrastructure,Technology,34,0.30,0.45,0.20,100000000,4.9,30000000,0.30,1000000,fixture,2026-01-01\n"
        "META,Platform Software,Technology,24,0.12,0.35,0.10,90000000,8.1,25000000,0.28,1000000,fixture,2026-01-01\n",
        encoding="utf-8",
    )
    dates = pd.date_range("2026-01-01", periods=90, freq="D")
    rows = []
    for ticker, start_price in {
        "NVDA": 100.0,
        "META": 80.0,
        "SMH": 70.0,
        "SPY": 50.0,
        "QQQ": 60.0,
    }.items():
        for index, date in enumerate(dates):
            close = start_price + index * 0.5
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "open": close - 0.2,
                    "high": close + 0.4,
                    "low": close - 0.5,
                    "close": close,
                    "adj_close": close,
                    "volume": 1_000_000 + index,
                }
            )
    pd.DataFrame(rows).to_csv(data_dir / "prices.csv", index=False)


def test_report_generator_creates_outputs(tmp_path: Path):
    _write_compact_pipeline_project(tmp_path)
    result = run(tmp_path)
    config = AppConfig.load(Path("config.yaml"))
    banned_phrases = ("buy now", "sell now", "strong buy", "guaranteed")
    allowed_purposes = {
        "Momentum Leader",
        "Pullback Add Candidate",
        "Core Compounder",
        "Re-rating / Undervalued",
        "Speculative Optionality",
        "ETF / Defensive / Hedge",
        "Broken / Avoid",
    }
    allowed_momentum_states = {
        "Watch",
        "Setup Forming",
        "Buyable Area",
        "Extended / No Chase",
        "Pullback Add Candidate",
        "Broken",
        "Avoid",
    }
    allowed_portfolio_states = {
        "Keep",
        "Add Candidate",
        "Hold but Do Not Add",
        "Risk Reduce",
        "Broken",
        "Review Thesis",
    }
    allowed_value_categories = {
        "Undervalued Quality",
        "Re-rating Candidate",
        "Cheap but No Momentum",
        "Possible Value Trap",
        "Avoid",
        "Insufficient Data",
    }
    allowed_market_states = {
        "Strong Rotation",
        "Early Rotation",
        "Overextended",
        "Weak",
        "Broken",
        "Insufficient Data",
    }
    expected = {
        "purpose_classification",
        "market_direction",
        "momentum_leaders",
        "portfolio_review",
        "undervalued_candidates",
        "final_watchlist",
    }
    assert expected.issubset(result["files"].keys())
    for path in result["files"].values():
        assert path.exists()

    purpose = pd.read_csv(result["files"]["purpose_classification"])
    market = pd.read_csv(result["files"]["market_direction"])
    momentum = pd.read_csv(result["files"]["momentum_leaders"])
    portfolio = pd.read_csv(result["files"]["portfolio_review"])
    value = pd.read_csv(result["files"]["undervalued_candidates"])
    final_watchlist = pd.read_csv(result["files"]["final_watchlist"])
    assert "SPY" not in purpose["Ticker"].tolist()
    assert "SPY" not in final_watchlist["Ticker"].tolist()
    assert purpose["Reason"].fillna("").str.len().gt(0).all()
    assert market["Reason"].fillna("").str.len().gt(0).all()
    assert momentum["Reason"].fillna("").str.len().gt(0).all()
    assert portfolio["Reason"].fillna("").str.len().gt(0).all()
    assert value["Reason"].fillna("").str.len().gt(0).all()
    assert final_watchlist["Reason"].fillna("").str.len().gt(0).all()

    assert set(purpose["FinalPrimaryPurpose"].dropna()) <= allowed_purposes
    conflict_rows = purpose.loc[purpose["ConflictFlag"].fillna(False).astype(bool)]
    assert conflict_rows["ConflictReasons"].fillna("").str.len().gt(0).all()
    assert "MissingDataFields" in market.columns
    assert "MacroNarrativeCaution" in market.columns
    assert market["MacroNarrativeCaution"].fillna("").str.contains("upstream", case=False).all()
    assert set(market["ThemeStatus"].dropna()) <= allowed_market_states
    assert set(momentum["SetupStatus"].dropna()) <= allowed_momentum_states
    assert set(portfolio["ReviewState"].dropna()) <= allowed_portfolio_states
    assert "MissingDataFields" in value.columns
    assert set(value["FinalValueCategory"].dropna()) <= allowed_value_categories
    assert "PeerRelativeStatus" in value.columns
    assert "RelativeOpportunityScore" in value.columns
    assert set(final_watchlist["FinalState"].dropna()) <= set(config.state_labels)
    assert "WatchlistScore" in final_watchlist.columns
    assert "WatchlistRank" in final_watchlist.columns
    ranked_rows = final_watchlist.loc[final_watchlist["WatchlistRank"].notna()]
    if not ranked_rows.empty:
        assert ranked_rows["WatchlistScore"].notna().all()
        assert ranked_rows["RankReason"].fillna("").str.len().gt(0).all()

    for output_name, output_path in result["files"].items():
        frame = pd.read_csv(output_path)
        assert "Reason" in frame.columns, f"{output_name} is missing a Reason column"
        assert frame["Reason"].fillna("").str.len().gt(0).all(), f"{output_name} contains blank reasons"
        string_columns = frame.select_dtypes(include=["object", "string"]).fillna("")
        for phrase in banned_phrases:
            assert not string_columns.apply(lambda column: column.str.contains(phrase, case=False, regex=False)).any().any()


def test_printable_warnings_summarizes_broad_universe_missing_prices():
    warnings = [
        "A: no daily price history was available.",
        "AA: no daily price history was available.",
        "AAA: no daily price history was available.",
        "Missing OHLCV data for A",
        "Missing OHLCV data for AA",
        "Missing OHLCV data for ZZZ",
    ]

    printable = printable_warnings(warnings, max_warnings=3)

    assert not any(warning == "Missing OHLCV data for ZZZ" for warning in printable)
    assert any("3 tickers are missing OHLCV coverage" in warning for warning in printable)
    assert any("3 tickers have no daily price history available" in warning for warning in printable)
    assert any("make price-worklist TOP_N=25" in warning for warning in printable)
    assert len(printable) <= 4


def test_report_generator_handles_missing_price_file_gracefully(tmp_path: Path):
    _write_compact_pipeline_project(tmp_path)
    (tmp_path / "data" / "prices.csv").unlink()

    result = run(tmp_path)

    assert any("Price file not found" in warning for warning in result["warnings"])
    assert any("No price data loaded." in warning for warning in result["warnings"])
    for output_name, output_path in result["files"].items():
        assert output_path.exists(), f"{output_name} should still be written even without prices"
        frame = pd.read_csv(output_path)
        assert "Reason" in frame.columns


def test_report_generator_handles_missing_fundamentals_file_gracefully(tmp_path: Path):
    _write_compact_pipeline_project(tmp_path)
    (tmp_path / "data" / "fundamentals.csv").unlink()

    result = run(tmp_path)

    assert any("Missing file: fundamentals.csv" in warning for warning in result["warnings"])
    assert result["files"]["undervalued_candidates"].exists()

    value_frame = pd.read_csv(result["files"]["undervalued_candidates"])
    assert "Reason" in value_frame.columns
    assert "MissingDataFields" in value_frame.columns
    assert value_frame["Reason"].fillna("").str.len().gt(0).all()
    assert value_frame["FinalValueCategory"].isin(["Insufficient Data", "Avoid"]).all()
    assert value_frame["MissingDataFields"].fillna("").str.contains("fundamentals unavailable").all()


def test_report_generator_handles_missing_theme_map_file_gracefully(tmp_path: Path):
    _write_compact_pipeline_project(tmp_path)
    (tmp_path / "data" / "theme_map.csv").unlink()

    result = run(tmp_path)

    assert any("Missing file: theme_map.csv" in warning for warning in result["warnings"])
    for output_name, output_path in result["files"].items():
        assert output_path.exists(), f"{output_name} should still be written without theme_map.csv"
        frame = pd.read_csv(output_path)
        assert "Reason" in frame.columns
        assert frame["Reason"].fillna("").str.len().gt(0).all()


def test_report_generator_keeps_holdings_only_tickers_without_price_history(tmp_path: Path):
    _write_compact_pipeline_project(tmp_path)
    (tmp_path / "data" / "universe.csv").write_text("Ticker,Theme,SectorETF,DefaultPurpose,MarketCapBucket\n", encoding="utf-8")
    (tmp_path / "data" / "holdings.csv").write_text(
        "Ticker,Shares,CostBasis,PositionPercent,PrimaryPurpose,SecondaryTags,OriginalThesis,MaxPositionPercent,InvalidationOverride\n"
        "ZZZ,0,0,10,Core Compounder,,,15,\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "theme_map.csv").write_text("Theme,ETF,Description\n", encoding="utf-8")
    (tmp_path / "data" / "fundamentals.csv").write_text("Ticker\n", encoding="utf-8")

    result = run(tmp_path)

    assert any("Missing OHLCV data for ZZZ" in warning for warning in result["warnings"])
    assert any("ZZZ: no daily price history was available." in warning for warning in result["warnings"])

    purpose_frame = pd.read_csv(result["files"]["purpose_classification"])
    final_watchlist_frame = pd.read_csv(result["files"]["final_watchlist"])

    assert "ZZZ" in purpose_frame["Ticker"].tolist()
    assert "ZZZ" in final_watchlist_frame["Ticker"].tolist()

    zzz_purpose = purpose_frame.loc[purpose_frame["Ticker"] == "ZZZ"].iloc[0]
    zzz_final = final_watchlist_frame.loc[final_watchlist_frame["Ticker"] == "ZZZ"].iloc[0]

    assert zzz_purpose["IsHolding"] is True or bool(zzz_purpose["IsHolding"]) is True
    assert "Price data is missing" in zzz_purpose["Reason"]
    assert zzz_final["FinalState"] == "Review Thesis"
    assert "Price data is missing" in zzz_final["Reason"]
