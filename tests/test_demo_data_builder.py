import json

import pandas as pd
import pytest

from src.demo_data_builder import build_demo_data_profile, verify_demo_data_profile


def _write_source_data(root):
    data_dir = root / "data"
    data_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "name": "NVIDIA Corp.",
                "exchange": "NASDAQ",
                "asset_type": "company",
                "security_type": "common_stock",
                "sector": "Technology",
                "industry": "Semiconductors",
                "country": "US",
                "currency": "USD",
                "is_active_listing": True,
                "source": "fixture",
                "source_updated_at": "2026-07-01",
                "created_at": "2026-07-01T00:00:00+00:00",
                "updated_at": "2026-07-01T00:00:00+00:00",
            },
            {
                "ticker": "QQQ",
                "name": "Invesco QQQ Trust",
                "exchange": "NASDAQ",
                "asset_type": "etf",
                "security_type": "etf",
                "sector": "",
                "industry": "",
                "country": "US",
                "currency": "USD",
                "is_active_listing": True,
                "source": "fixture",
                "source_updated_at": "2026-07-01",
                "created_at": "2026-07-01T00:00:00+00:00",
                "updated_at": "2026-07-01T00:00:00+00:00",
            },
            {
                "ticker": "OTHER",
                "name": "Excluded Corp.",
                "exchange": "NYSE",
                "asset_type": "company",
                "security_type": "common_stock",
                "sector": "Other",
                "industry": "Other",
                "country": "US",
                "currency": "USD",
                "is_active_listing": True,
                "source": "fixture",
                "source_updated_at": "2026-07-01",
                "created_at": "2026-07-01T00:00:00+00:00",
                "updated_at": "2026-07-01T00:00:00+00:00",
            },
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "scope": "active_research", "priority": 1, "theme": "AI", "research_status": "active", "user_notes": "", "added_at": "2026-07-01", "updated_at": "2026-07-01"},
            {"ticker": "QQQ", "scope": "active_research", "priority": 2, "theme": "Benchmark", "research_status": "active", "user_notes": "", "added_at": "2026-07-01", "updated_at": "2026-07-01"},
        ]
    ).to_csv(data_dir / "universe_active.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "theme": "AI", "sector_etf": "Technology", "default_purpose": "research", "market_cap_bucket": "large", "notes": "", "company_name": "NVIDIA Corp.", "universe_source": "fixture", "source_detail": "", "index_membership": "", "etf_membership": "", "exchange": "NASDAQ", "is_etf": False, "as_of_date": "2026-07-01", "in_local_sample": True, "in_sp500": True, "in_nasdaq": True, "in_smh": True, "in_holdings": False, "in_custom": False},
            {"ticker": "QQQ", "theme": "Benchmark", "sector_etf": "ETF", "default_purpose": "ETF", "market_cap_bucket": "ETF", "notes": "", "company_name": "Invesco QQQ Trust", "universe_source": "fixture", "source_detail": "", "index_membership": "", "etf_membership": "", "exchange": "NASDAQ", "is_etf": True, "as_of_date": "2026-07-01", "in_local_sample": True, "in_sp500": False, "in_nasdaq": True, "in_smh": False, "in_holdings": False, "in_custom": False},
        ]
    ).to_csv(data_dir / "universe.csv", index=False)
    price_rows = []
    for ticker, close in (("NVDA", 100.0), ("QQQ", 500.0), ("SPY", 600.0), ("OTHER", 10.0)):
        for day in range(1, 7):
            price_rows.append({"date": f"2026-07-0{day}", "ticker": ticker, "open": close, "high": close + 1, "low": close - 1, "close": close, "adj_close": close, "volume": 1000})
    pd.DataFrame(price_rows).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "revenue": 100.0, "free_cash_flow": 20.0, "fcf_margin": 0.2, "shares_outstanding": 10.0, "source": "fixture", "as_of_date": "2026-07-01"},
            {"ticker": "OTHER", "revenue": 10.0, "free_cash_flow": 1.0, "fcf_margin": 0.1, "shares_outstanding": 3.0, "source": "fixture", "as_of_date": "2026-07-01"},
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "peer_ticker": "OTHER", "peer_group": "fixture", "sector": "Technology", "industry": "Semiconductors", "source": "fixture", "as_of_date": "2026-07-01"},
            {"ticker": "OTHER", "peer_ticker": "NVDA", "peer_group": "fixture", "sector": "Other", "industry": "Other", "source": "fixture", "as_of_date": "2026-07-01"},
        ]
    ).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(
        [{"Ticker": "NVDA", "Shares": 0, "CostBasis": 0, "PositionPercent": 0, "PrimaryPurpose": "Example", "SecondaryTags": "", "OriginalThesis": "Example only", "MaxPositionPercent": 0, "InvalidationOverride": ""}]
    ).to_csv(data_dir / "holdings.csv", index=False)
    pd.DataFrame([{"Theme": "AI", "ETF": "SMH", "Description": "Fixture"}]).to_csv(data_dir / "theme_map.csv", index=False)


def test_demo_builder_creates_profile_local_readiness_and_auditable_manifest(tmp_path):
    _write_source_data(tmp_path)

    result = build_demo_data_profile(tmp_path, tickers=("NVDA", "QQQ"), snapshot_date="2026-07-01")

    demo_data = tmp_path / "data" / "demo"
    manifest = json.loads((demo_data / "manifest.json").read_text(encoding="utf-8"))
    assert result.tickers == ("NVDA", "QQQ")
    assert set(pd.read_csv(demo_data / "prices.csv")["ticker"]) == {"NVDA", "QQQ"}
    assert set(pd.read_csv(demo_data / "reports" / "ticker_readiness_report.csv")["ticker"]) == {"NVDA", "QQQ"}
    assert manifest["profile"] == "demo"
    assert manifest["snapshot_date"] == "2026-07-01"
    assert manifest["scenario_roles"]["dcf_ready_company"] == ["NVDA"]
    assert manifest["scenario_roles"]["excluded_asset_context"] == ["QQQ"]
    assert manifest["known_limitations"]
    assert manifest["files"]["prices.csv"]["sha256"]
    assert not (tmp_path / "outputs" / "demo" / "research_decisions.csv").exists()


def test_demo_builder_refuses_to_overwrite_an_existing_demo_profile(tmp_path):
    _write_source_data(tmp_path)
    build_demo_data_profile(tmp_path, tickers=("NVDA",), snapshot_date="2026-07-01")

    with pytest.raises(FileExistsError, match="already exists"):
        build_demo_data_profile(tmp_path, tickers=("NVDA",), snapshot_date="2026-07-01")


def test_demo_builder_keeps_a_price_backed_benchmark_metadata_only(tmp_path):
    _write_source_data(tmp_path)

    build_demo_data_profile(tmp_path, tickers=("NVDA", "SPY"), snapshot_date="2026-07-01")

    master = pd.read_csv(tmp_path / "data" / "demo" / "universe_master.csv").set_index("ticker")
    manifest = json.loads((tmp_path / "data" / "demo" / "manifest.json").read_text(encoding="utf-8"))
    assert master.loc["SPY", "asset_type"] == "index_proxy"
    assert master.loc["SPY", "source"] == "demo_profile_price_history"
    assert manifest["derived_metadata_tickers"] == ["SPY"]


def test_demo_builder_verifies_manifest_checksums_without_rebuilding(tmp_path):
    _write_source_data(tmp_path)
    build_demo_data_profile(tmp_path, tickers=("NVDA",), snapshot_date="2026-07-01")

    verification = verify_demo_data_profile(tmp_path)

    assert verification["status"] == "valid"
    assert verification["files_checked"] > 0
