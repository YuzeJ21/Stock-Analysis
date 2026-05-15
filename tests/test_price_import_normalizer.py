from pathlib import Path

import pandas as pd

from src.price_import_normalizer import normalize_price_imports


def test_yahoo_style_csv_normalizes_with_ticker(tmp_path: Path):
    raw = tmp_path / "data" / "raw" / "prices" / "NVDA.csv"
    output = tmp_path / "data" / "imports" / "prices.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text(
        "Date,Open,High,Low,Close,Adj Close,Volume\n"
        "2026-01-02,100,105,99,104,103.5,123456\n",
        encoding="utf-8",
    )

    result = normalize_price_imports(
        input_path=raw,
        output_path=output,
        ticker="NVDA",
        source="yahoo_manual",
        as_of_date="2026-01-03",
    )
    staged = pd.read_csv(output)

    assert result.rows_read == 1
    assert result.rows_written == 1
    assert staged.iloc[0]["ticker"] == "NVDA"
    assert staged.iloc[0]["adjusted_close"] == 103.5
    assert staged.iloc[0]["source"] == "yahoo_manual"


def test_generic_csv_with_ticker_column_normalizes(tmp_path: Path):
    raw = tmp_path / "data" / "raw" / "prices" / "prices.csv"
    output = tmp_path / "data" / "imports" / "prices.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text(
        "date,ticker,open,high,low,close,volume,adjusted_close,source\n"
        "2026-01-02,msft,200,202,199,201,200000,200.5,manual_export\n",
        encoding="utf-8",
    )

    result = normalize_price_imports(input_path=raw, output_path=output, source="generic_manual", as_of_date="2026-01-03")
    staged = pd.read_csv(output)

    assert result.affected_tickers == ["MSFT"]
    assert staged.iloc[0]["ticker"] == "MSFT"


def test_configurable_column_mapping_works(tmp_path: Path):
    raw = tmp_path / "raw.csv"
    output = tmp_path / "imports" / "prices.csv"
    raw.write_text(
        "when,symbol,o,h,l,c,v,adj\n"
        "2026-01-02,avgo,10,11,9,10.5,1000,10.4\n",
        encoding="utf-8",
    )

    normalize_price_imports(
        input_path=raw,
        output_path=output,
        source="mapped_manual",
        as_of_date="2026-01-03",
        column_mapping={
            "date": "when",
            "ticker": "symbol",
            "open": "o",
            "high": "h",
            "low": "l",
            "close": "c",
            "volume": "v",
            "adjusted_close": "adj",
        },
    )
    staged = pd.read_csv(output)

    assert staged.iloc[0]["ticker"] == "AVGO"
    assert staged.iloc[0]["adjusted_close"] == 10.4


def test_duplicate_date_ticker_rows_keep_last(tmp_path: Path):
    raw = tmp_path / "NVDA.csv"
    output = tmp_path / "imports" / "prices.csv"
    raw.write_text(
        "Date,Open,High,Low,Close,Adj Close,Volume\n"
        "2026-01-02,100,105,99,104,103,1000\n"
        "2026-01-02,101,106,100,105,104,1100\n",
        encoding="utf-8",
    )

    result = normalize_price_imports(input_path=raw, output_path=output, ticker="NVDA", source="manual", as_of_date="2026-01-03")
    staged = pd.read_csv(output)

    assert result.duplicate_rows == 1
    assert len(staged) == 1
    assert staged.iloc[0]["close"] == 105


def test_invalid_price_rows_are_skipped_and_reported(tmp_path: Path):
    raw = tmp_path / "NVDA.csv"
    output = tmp_path / "imports" / "prices.csv"
    raw.write_text(
        "Date,Open,High,Low,Close,Adj Close,Volume\n"
        "2026-01-02,100,99,101,104,103,1000\n"
        "2026-01-03,100,105,99,0,0,1000\n"
        "2026-01-04,100,105,99,104,103,1000\n",
        encoding="utf-8",
    )

    result = normalize_price_imports(input_path=raw, output_path=output, ticker="NVDA", source="manual", as_of_date="2026-01-05")
    staged = pd.read_csv(output)

    assert result.invalid_rows == 2
    assert len(staged) == 1
    assert staged.iloc[0]["date"] == "2026-01-04"


def test_normalizer_does_not_mutate_canonical_prices(tmp_path: Path):
    data_dir = tmp_path / "data"
    raw = data_dir / "raw" / "prices" / "NVDA.csv"
    output = data_dir / "imports" / "prices.csv"
    canonical = data_dir / "prices.csv"
    raw.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text("date,ticker,adj_close,volume\n2026-01-01,NVDA,100,1000\n", encoding="utf-8")
    before = canonical.read_text(encoding="utf-8")
    raw.write_text("Date,Open,High,Low,Close,Volume\n2026-01-02,100,105,99,104,123456\n", encoding="utf-8")

    normalize_price_imports(input_path=raw, output_path=output, ticker="NVDA", source="manual", as_of_date="2026-01-03")

    assert canonical.read_text(encoding="utf-8") == before
    assert output.exists()
