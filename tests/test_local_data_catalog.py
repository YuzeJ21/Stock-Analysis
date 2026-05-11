from pathlib import Path

from src.providers.local_data_catalog import LocalDataCatalog


def test_local_data_catalog_discovers_existing_datasets(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,profit_margin,pe_ratio\n"
        "SPY,0.20,22\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "momentum_leaders.csv").write_text(
        "Ticker,SetupStatus,Reason\n"
        "SPY,Watch,Local fixture\n",
        encoding="utf-8",
    )

    catalog = LocalDataCatalog(tmp_path)
    discovered = {entry.name: entry for entry in catalog.discover()}

    assert "prices" in discovered
    assert discovered["prices"].row_count == 1
    assert discovered["prices"].date_column == "date"
    assert discovered["prices"].ticker_column == "ticker"
    assert discovered["prices"].latest_data_timestamp.startswith("2026-01-02")
    assert discovered["prices"].validation_status == "valid"
    assert "momentum_leaders" in discovered
    assert discovered["earnings"].validation_status == "missing_file"


def test_local_data_catalog_lists_and_describes_tickers(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n"
        "2026-01-03,QQQ,101,1100\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,profit_margin\n"
        "SPY,0.20\n",
        encoding="utf-8",
    )

    catalog = LocalDataCatalog(tmp_path)

    assert catalog.list_tickers(["prices", "fundamentals"]) == ["QQQ", "SPY"]
    coverage = catalog.describe_ticker("SPY", ["prices", "fundamentals", "earnings"])

    assert coverage[0].ticker_present is True
    assert coverage[1].ticker_present is True
    assert coverage[2].ticker_present is False
    assert coverage[2].validation_status == "missing_file"


def test_local_data_catalog_uses_as_of_date_for_latest_timestamp(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "analyst_estimates.csv").write_text(
        "ticker,current_quarter_eps,as_of_date\n"
        "SPY,1.0,2026-05-01\n",
        encoding="utf-8",
    )
    catalog = LocalDataCatalog(tmp_path)

    metadata = catalog.dataset_metadata("analyst_estimates")

    assert metadata.latest_data_timestamp.startswith("2026-05-01")
