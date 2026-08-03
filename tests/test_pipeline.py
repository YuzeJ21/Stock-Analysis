from pathlib import Path

import pandas as pd

import src.report_generator as report_generator
from src.config import AppConfig
from src.indicators import build_indicator_snapshot
from src.report_generator import printable_warnings, run


def _write_compact_pipeline_project(base_dir: Path) -> None:
    data_dir = base_dir / "data"
    data_dir.mkdir()
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


def test_indicator_snapshot_labels_atr_source_when_high_low_are_available():
    config = AppConfig.load(Path("config.yaml"))
    dates = pd.date_range("2026-01-01", periods=20, freq="D")
    prices = pd.DataFrame(
        {
            "date": dates,
            "ticker": ["NVDA"] * len(dates),
            "high": [101 + index for index in range(len(dates))],
            "low": [99 + index for index in range(len(dates))],
            "close": [100 + index for index in range(len(dates))],
            "volume": [1_000_000] * len(dates),
        }
    )
    universe = pd.DataFrame({"ticker": ["NVDA"], "theme": ["AI"], "sector_etf": ["SMH"]})

    snapshot, warnings = build_indicator_snapshot(prices, universe, pd.DataFrame(), config)

    row = snapshot.loc[snapshot["ticker"] == "NVDA"].iloc[0]
    assert row["atr_or_volatility_source"] == "atr"
    assert not any("volatility proxy" in warning.lower() for warning in warnings)


def test_indicator_snapshot_labels_volatility_proxy_as_approximation_when_atr_missing():
    config = AppConfig.load(Path("config.yaml"))
    dates = pd.date_range("2026-01-01", periods=20, freq="D")
    prices = pd.DataFrame(
        {
            "date": dates,
            "ticker": ["NVDA"] * len(dates),
            "close": [100 + index for index in range(len(dates))],
            "volume": [1_000_000] * len(dates),
        }
    )
    universe = pd.DataFrame({"ticker": ["NVDA"], "theme": ["AI"], "sector_etf": ["SMH"]})

    snapshot, warnings = build_indicator_snapshot(prices, universe, pd.DataFrame(), config)

    row = snapshot.loc[snapshot["ticker"] == "NVDA"].iloc[0]
    assert row["atr_or_volatility_source"] == "volatility_proxy"
    assert any("close-to-close volatility proxy as an approximation" in warning for warning in warnings)


def _file_manifest(root: Path) -> dict[str, tuple[str, bytes]]:
    manifest: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative_path = path.relative_to(root).as_posix()
        if path.is_dir():
            manifest[relative_path] = ("directory", b"")
        elif path.is_file():
            manifest[relative_path] = ("file", path.read_bytes())
    return manifest


def test_report_generator_returns_complete_frames_without_writing(tmp_path: Path, monkeypatch):
    _write_compact_pipeline_project(tmp_path)
    before = _file_manifest(tmp_path)

    original_readiness_builder = report_generator.build_ticker_readiness_report

    def build_readiness_without_writing(*args, **kwargs):
        assert kwargs.get("write_outputs") is False
        return original_readiness_builder(*args, **kwargs)

    def fail_writer(*_args, **_kwargs):
        raise AssertionError("the in-memory pipeline must not invoke an artifact writer")

    monkeypatch.setattr(report_generator, "build_ticker_readiness_report", build_readiness_without_writing)
    monkeypatch.setattr(report_generator, "write_research_decisions", fail_writer)
    monkeypatch.setattr(report_generator, "write_purpose_evaluation_summary", fail_writer)
    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_writer)

    result = run(tmp_path)
    config = AppConfig.load(Path("config.yaml"))
    banned_phrases = ("buy now", "sell now", "strong buy", "guaranteed")
    allowed_purposes = {
        "Momentum Leader",
        "Pullback Review Candidate",
        "Core Compounder",
        "Re-rating / Undervalued",
        "Speculative Optionality",
        "ETF / Defensive / Hedge",
        "Broken / No Setup",
    }
    allowed_momentum_states = {
        "Watch",
        "Setup Forming",
        "Research Ready",
        "Extended",
        "Pullback Review Candidate",
        "Broken",
        "No Setup",
    }
    allowed_portfolio_states = {
        "Keep",
        "Constructive Review",
        "Hold Review Only",
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
        "research_decisions",
        "purpose_evaluation_summary",
        "data_quality_wizard",
        "liquidity_risk",
        "correlation_risk",
        "dcf_readiness",
        "earnings_readiness",
        "analyst_estimates_readiness",
        "universe_coverage_report",
        "price_coverage_report",
        "fundamentals_coverage_report",
        "dcf_readiness_report",
        "peer_readiness_report",
        "earnings_readiness_report",
        "analyst_estimates_readiness_report",
        "ticker_readiness_report",
        "feature_readiness_summary",
        "peer_unlock_worklist",
        "data_source_status",
    }
    assert set(result["frames"]) == expected
    assert set(result["row_counts"]) == expected
    assert set(result["path_labels"]) == expected
    assert all(result["row_counts"][name] == len(frame) for name, frame in result["frames"].items())
    assert _file_manifest(tmp_path) == before
    assert not (tmp_path / "outputs").exists()

    purpose = result["frames"]["purpose_classification"]
    market = result["frames"]["market_direction"]
    momentum = result["frames"]["momentum_leaders"]
    portfolio = result["frames"]["portfolio_review"]
    value = result["frames"]["undervalued_candidates"]
    final_watchlist = result["frames"]["final_watchlist"]
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
    assert "ATRorVolatilitySource" in momentum.columns
    assert set(momentum["ATRorVolatilitySource"].dropna()) <= {"atr", "volatility_proxy", "unavailable"}
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

    reason_frame_names = {
        "purpose_classification",
        "market_direction",
        "momentum_leaders",
        "portfolio_review",
        "undervalued_candidates",
        "final_watchlist",
        "research_decisions",
        "purpose_evaluation_summary",
        "data_quality_wizard",
        "liquidity_risk",
        "correlation_risk",
    }
    for output_name in reason_frame_names:
        frame = result["frames"][output_name]
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
        "Optional benchmark/proxy OHLCV context unavailable for ARKF; theme/sector comparison is unavailable, but the ticker's own readiness state is unchanged.",
    ]

    printable = printable_warnings(warnings, max_warnings=3)

    assert not any(warning == "Missing OHLCV data for ZZZ" for warning in printable)
    assert any("3 tickers are missing OHLCV coverage" in warning for warning in printable)
    assert any("3 tickers have no daily price history available" in warning for warning in printable)
    assert any("1 optional benchmark/proxy tickers are missing OHLCV context" in warning for warning in printable)
    assert any("each stock's own readiness state is unchanged" in warning for warning in printable)
    assert any("make price-history-proof-queue TOP_N=25" in warning for warning in printable)
    assert any("make price-refresh-loop DRY_RUN=1" in warning for warning in printable)
    price_guidance = "\n".join(printable)
    assert price_guidance.index("make price-history-proof-queue TOP_N=25") < price_guidance.index(
        "make price-refresh-loop DRY_RUN=1"
    )
    assert not any("make price-worklist TOP_N=25" in warning for warning in printable)
    assert not any("make price-refresh TOP_N=25" in warning for warning in printable)
    assert len(printable) <= 5


def test_report_generator_classifies_missing_sector_etf_as_optional_proxy_context(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (data_dir / "universe.csv").write_text(
        "ticker,theme,sector_etf,default_purpose,market_cap_bucket\n"
        "HOOD,Fintech,ARKF,Core Compounder,Large\n",
        encoding="utf-8",
    )
    (data_dir / "holdings.csv").write_text(
        "Ticker,Shares,CostBasis,PositionPercent,PrimaryPurpose,SecondaryTags,OriginalThesis,MaxPositionPercent,InvalidationOverride\n",
        encoding="utf-8",
    )
    (data_dir / "theme_map.csv").write_text(
        "Theme,ETF,Description\n"
        "Fintech,ARKF,Financial technology context\n",
        encoding="utf-8",
    )
    (data_dir / "fundamentals.csv").write_text("ticker\n", encoding="utf-8")
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    rows = []
    for ticker, start_price in {"HOOD": 20.0, "SPY": 100.0, "QQQ": 120.0}.items():
        for index, date in enumerate(dates):
            close = start_price + index * 0.1
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "open": close - 0.1,
                    "high": close + 0.2,
                    "low": close - 0.2,
                    "close": close,
                    "volume": 1_000_000,
                }
            )
    pd.DataFrame(rows).to_csv(data_dir / "prices.csv", index=False)

    result = run(tmp_path)

    assert not any(warning == "Missing OHLCV data for ARKF" for warning in result["warnings"])
    assert any(
        warning.startswith("Optional benchmark/proxy OHLCV context unavailable for ARKF")
        for warning in result["warnings"]
    )
    printable = printable_warnings(result["warnings"])
    assert any("optional benchmark/proxy tickers are missing OHLCV context" in warning for warning in printable)


def test_report_generator_handles_missing_price_file_gracefully(tmp_path: Path):
    _write_compact_pipeline_project(tmp_path)
    (tmp_path / "data" / "prices.csv").unlink()

    result = run(tmp_path)

    assert any("Price file not found" in warning for warning in result["warnings"])
    assert any("No price data loaded." in warning for warning in result["warnings"])
    for output_name in (
        "purpose_classification",
        "market_direction",
        "momentum_leaders",
        "portfolio_review",
        "undervalued_candidates",
        "final_watchlist",
        "research_decisions",
        "purpose_evaluation_summary",
        "data_quality_wizard",
        "liquidity_risk",
        "correlation_risk",
    ):
        frame = result["frames"][output_name]
        assert "Reason" in frame.columns


def test_report_generator_handles_missing_fundamentals_file_gracefully(tmp_path: Path):
    _write_compact_pipeline_project(tmp_path)
    (tmp_path / "data" / "fundamentals.csv").unlink()

    result = run(tmp_path)

    assert any("Missing file: fundamentals.csv" in warning for warning in result["warnings"])
    value_frame = result["frames"]["undervalued_candidates"]
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
    for output_name in (
        "purpose_classification",
        "market_direction",
        "momentum_leaders",
        "portfolio_review",
        "undervalued_candidates",
        "final_watchlist",
        "research_decisions",
        "purpose_evaluation_summary",
        "data_quality_wizard",
        "liquidity_risk",
        "correlation_risk",
    ):
        frame = result["frames"][output_name]
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

    purpose_frame = result["frames"]["purpose_classification"]
    final_watchlist_frame = result["frames"]["final_watchlist"]

    assert "ZZZ" in purpose_frame["Ticker"].tolist()
    assert "ZZZ" in final_watchlist_frame["Ticker"].tolist()

    zzz_purpose = purpose_frame.loc[purpose_frame["Ticker"] == "ZZZ"].iloc[0]
    zzz_final = final_watchlist_frame.loc[final_watchlist_frame["Ticker"] == "ZZZ"].iloc[0]

    assert zzz_purpose["IsHolding"] is True or bool(zzz_purpose["IsHolding"]) is True
    assert "Price data is missing" in zzz_purpose["Reason"]
    assert zzz_final["FinalState"] == "Review Thesis"
    assert "Price data is missing" in zzz_final["Reason"]
