import json
from pathlib import Path

import pandas as pd

from src.dcf_readiness import build_dcf_readiness_frame
from src.providers.local_importer import preview_import_merge, validate_imports
from src.sec_filing_share_stage import stage_sec_filing_share_count_rows


def _submission_payload() -> dict[str, object]:
    return {
        "cik": "1783879",
        "name": "Robinhood Markets, Inc.",
        "tickers": ["HOOD"],
        "exchanges": ["Nasdaq"],
        "filings": {
            "recent": {
                "accessionNumber": ["0001783879-26-000077", "0001783879-26-000062"],
                "filingDate": ["2026-06-25", "2026-04-29"],
                "reportDate": ["2026-06-22", "2026-04-06"],
                "primaryDocument": ["hood-20260622.htm", "hood-20260331.htm"],
                "form": ["8-K", "10-Q"],
            }
        },
    }


def _write_base_files(root: Path) -> None:
    data = root / "data"
    (data / "imports").mkdir(parents=True, exist_ok=True)
    (data / "fundamentals.csv").write_text(
        "ticker,revenue,free_cash_flow,fcf_margin,cash,debt,shares_outstanding,source,as_of_date,sec_cik,sec_form,sec_filed_date,sec_accession,sec_fact_warnings,sec_entity_name\n"
        "HOOD,4473000000,1610000000,0.3599,5012000000,,,"
        "sec_companyfacts,2025-12-31,1783879,10-K/A,2026-02-20,0001783879-26-000029,"
        "\"Shares outstanding was unavailable from SEC Companyfacts.\",\"Robinhood Markets, Inc.\"\n",
        encoding="utf-8",
    )
    (data / "imports" / "fundamentals.csv").write_text(
        "ticker,revenue,free_cash_flow,fcf_margin,cash,debt,shares_outstanding,source,as_of_date,sec_cik,sec_form,sec_filed_date,sec_accession,sec_fact_warnings,sec_entity_name\n"
        "HOOD,4473000000,1610000000,0.3599,5012000000,,,"
        "sec_companyfacts,2025-12-31,0001783879,10-K/A,2026-02-20,0001783879-26-000029,"
        "\"Shares outstanding was unavailable from SEC Companyfacts.\",\"Robinhood Markets, Inc.\"\n",
        encoding="utf-8",
    )


def test_stage_sec_filing_share_count_preserves_existing_fundamentals_and_sets_preview_gate(tmp_path: Path):
    _write_base_files(tmp_path)

    result = stage_sec_filing_share_count_rows(
        ["HOOD"],
        root=tmp_path,
        user_agent="Test test@example.com",
        ticker_map={"HOOD": {"ticker": "HOOD", "cik": "0001783879"}},
        submission_fetcher=lambda *_: _submission_payload(),
        document_fetcher=lambda *_: (
            '<ix:nonFraction name="dei:EntityCommonStockSharesOutstanding" '
            'contextRef="c-2" unitRef="shares" scale="0">791,184,698</ix:nonFraction>'
        ),
    )

    staged = pd.read_csv(tmp_path / "data" / "imports" / "fundamentals.csv")
    hood = staged.set_index("ticker").loc["HOOD"]
    validation = validate_imports(base_dir=tmp_path, tickers="HOOD")
    preview = preview_import_merge(base_dir=tmp_path, tickers="HOOD")

    assert result["resolved_tickers"] == ["HOOD"]
    assert result["rows_written"] == 1
    assert int(hood["shares_outstanding"]) == 791184698
    assert hood["revenue"] == 4473000000
    assert hood["source"] == "sec_companyfacts; sec_filing_document"
    assert hood["as_of_date"] == "2026-04-06"
    assert str(hood["sec_cik"]).zfill(10) == "0001783879"
    assert hood["sec_form"] == "10-Q"
    assert hood["sec_filed_date"] == "2026-04-29"
    assert hood["sec_accession"] == "0001783879-26-000062"
    assert "explicit SEC filing document fact" in hood["sec_fact_warnings"]
    assert validation["status"] == "valid"
    assert preview["preview"][0]["updated_rows"] == 1
    assert preview["preview"][0]["new_rows"] == 0


def test_stage_sec_filing_share_count_does_not_make_dcf_ready_before_apply(tmp_path: Path):
    _write_base_files(tmp_path)
    prices = pd.DataFrame([{"ticker": "HOOD", "date": "2026-04-30", "close": 10.0}])
    universe = pd.DataFrame([{"ticker": "HOOD", "asset_type": "company"}])

    stage_sec_filing_share_count_rows(
        ["HOOD"],
        root=tmp_path,
        user_agent="Test test@example.com",
        ticker_map={"HOOD": {"ticker": "HOOD", "cik": "0001783879"}},
        submission_fetcher=lambda *_: _submission_payload(),
        document_fetcher=lambda *_: (
            '<ix:nonFraction name="dei:EntityCommonStockSharesOutstanding" '
            'contextRef="c-2" unitRef="shares">791184698</ix:nonFraction>'
        ),
    )

    readiness = build_dcf_readiness_frame(
        universe=universe,
        fundamentals=pd.read_csv(tmp_path / "data" / "fundamentals.csv"),
        prices=prices,
    )

    assert bool(readiness.loc[readiness["ticker"].eq("HOOD"), "is_dcf_ready"].iloc[0]) is False
    assert "shares_outstanding" in readiness.loc[readiness["ticker"].eq("HOOD"), "missing_dcf_fields"].iloc[0]


def test_stage_sec_filing_share_count_reports_missing_document_without_writing(tmp_path: Path):
    _write_base_files(tmp_path)

    result = stage_sec_filing_share_count_rows(
        ["HOOD"],
        root=tmp_path,
        allow_network=False,
        ticker_map={"HOOD": {"ticker": "HOOD", "cik": "0001783879"}},
    )

    assert result["resolved_tickers"] == []
    assert result["unresolved_tickers"] == ["HOOD"]
    assert result["rows_written"] == 0
    assert "cached_submission_missing" in result["warnings"][0]


def test_stage_sec_filing_share_count_reports_missing_explicit_fact(tmp_path: Path):
    _write_base_files(tmp_path)

    result = stage_sec_filing_share_count_rows(
        ["HOOD"],
        root=tmp_path,
        user_agent="Test test@example.com",
        ticker_map={"HOOD": {"ticker": "HOOD", "cik": "0001783879"}},
        submission_fetcher=lambda *_: _submission_payload(),
        document_fetcher=lambda *_: "<html>No share fact.</html>",
    )

    assert result["resolved_tickers"] == []
    assert result["unresolved_tickers"] == ["HOOD"]
    assert result["rows_written"] == 0
    assert "explicit_share_count_fact_missing" in result["warnings"][0]


def test_stage_sec_filing_share_count_json_shape(tmp_path: Path):
    _write_base_files(tmp_path)

    result = stage_sec_filing_share_count_rows(
        ["HOOD"],
        root=tmp_path,
        user_agent="Test test@example.com",
        ticker_map={"HOOD": {"ticker": "HOOD", "cik": "0001783879"}},
        submission_fetcher=lambda *_: _submission_payload(),
        document_fetcher=lambda *_: (
            '<ix:nonFraction name="dei:EntityCommonStockSharesOutstanding" '
            'contextRef="c-2" unitRef="shares">791184698</ix:nonFraction>'
        ),
    )

    json.dumps(result)
    assert result["recommended_next_commands"] == [
        "make imports-validate IMPORT_TICKERS=<resolved_tickers>",
        "make imports-preview IMPORT_TICKERS=<resolved_tickers>",
        "make imports-apply IMPORT_TICKERS=<resolved_tickers>",
    ]
