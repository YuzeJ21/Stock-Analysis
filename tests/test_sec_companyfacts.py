import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.providers.local_importer import preview_import_merge, validate_imports
from src.providers.sec_companyfacts import (
    SECUserAgentError,
    build_sec_fundamentals_rows,
    extract_fundamentals_from_companyfacts,
    fetch_companyfacts,
    load_sec_ticker_map,
    resolve_ticker_to_cik,
    write_sec_fundamentals_import,
)
from src.stock_report import main


def _sample_ticker_map_payload():
    return {
        "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    }


def _sample_companyfacts_payload():
    return {
        "cik": 1045810,
        "entityName": "NVIDIA CORP",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "val": 1000,
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            },
                            {
                                "val": 800,
                                "start": "2024-01-01",
                                "end": "2024-12-31",
                                "fy": 2024,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2025-02-20",
                                "accn": "0001045810-25-000001",
                            },
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "val": 200,
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            {
                                "val": 5,
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            {
                                "val": 250,
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USD": [
                            {
                                "val": 50,
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "val": 250,
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "CashAndCashEquivalentsAtCarryingValue": {
                    "units": {
                        "USD": [
                            {
                                "val": 300,
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "ShortTermBorrowings": {
                    "units": {
                        "USD": [
                            {
                                "val": 30,
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "LongTermDebtCurrent": {
                    "units": {
                        "USD": [
                            {
                                "val": 20,
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
                "LongTermDebtNoncurrent": {
                    "units": {
                        "USD": [
                            {
                                "val": 100,
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                },
            },
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {
                                "val": 100,
                                "end": "2025-12-31",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2026-02-20",
                                "accn": "0001045810-26-000001",
                            }
                        ]
                    }
                }
            },
        },
    }


def test_resolve_ticker_to_cik(tmp_path: Path):
    ticker_map = load_sec_ticker_map(
        cache_dir=tmp_path / "cache",
        fetcher=lambda *_: _sample_ticker_map_payload(),
        user_agent="Test test@example.com",
        refresh=True,
    )

    assert resolve_ticker_to_cik("NVDA", ticker_map) == "0001045810"
    assert resolve_ticker_to_cik("BRK.B", {"BRK-B": {"ticker": "BRK-B", "cik": "0001067983"}}) == "0001067983"
    assert resolve_ticker_to_cik("MISSING", ticker_map) is None


def test_extract_fundamentals_from_companyfacts_maps_supported_fields():
    row = extract_fundamentals_from_companyfacts(_sample_companyfacts_payload())

    assert row["revenue"] == 1000
    assert row["revenue_growth"] == pytest.approx(0.25)
    assert row["eps"] == 5
    assert row["free_cash_flow"] == 200
    assert row["fcf_margin"] == pytest.approx(0.2)
    assert row["profit_margin"] == pytest.approx(0.2)
    assert row["operating_margin"] == pytest.approx(0.25)
    assert row["cash"] == 300
    assert row["debt"] == 150
    assert row["shares_outstanding"] == 100
    assert row["sec_form"] == "10-K"
    assert row["as_of_date"] == "2025-12-31"
    assert any("EBITDA" in warning for warning in row["_warnings"])


def test_extract_fundamentals_maps_contract_revenue_concept():
    payload = _sample_companyfacts_payload()
    revenue_facts = payload["facts"]["us-gaap"].pop("Revenues")
    payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"] = revenue_facts

    row = extract_fundamentals_from_companyfacts(payload)

    assert row["revenue"] == 1000
    assert row["revenue_growth"] == pytest.approx(0.25)
    assert row["fcf_margin"] == pytest.approx(0.2)
    assert not any("Revenue was unavailable" in warning for warning in row["_warnings"])


def test_extract_fundamentals_warns_when_missing_facts():
    payload = {"cik": 1, "entityName": "Test", "facts": {"us-gaap": {"Revenues": {"units": {"USD": [{"val": 10, "end": "2025-12-31", "start": "2025-01-01", "fp": "FY", "fy": 2025, "form": "10-K", "filed": "2026-02-20", "accn": "1"}]}}}}}

    row = extract_fundamentals_from_companyfacts(payload)

    assert row["eps"] is None
    assert row["free_cash_flow"] is None
    assert any("EPS was unavailable" in warning for warning in row["_warnings"])
    assert any("Debt was unavailable" in warning for warning in row["_warnings"])


def test_missing_sec_user_agent_fails_clearly(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(SECUserAgentError):
        build_sec_fundamentals_rows(["NVDA"], user_agent=None, ticker_map=_sample_ticker_map_payload())


def test_cache_behavior_avoids_refetch(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    ticker_cache = cache_dir / "company_tickers.json"
    ticker_cache.parent.mkdir(parents=True, exist_ok=True)
    ticker_cache.write_text(json.dumps(_sample_ticker_map_payload()), encoding="utf-8")

    def should_not_fetch(*_args, **_kwargs):
        raise AssertionError("fetcher should not be called when cache exists")

    ticker_map = load_sec_ticker_map(cache_dir=cache_dir, user_agent="Test test@example.com", fetcher=should_not_fetch)
    assert ticker_map["NVDA"]["cik"] == "0001045810"

    companyfacts_cache = cache_dir / "companyfacts" / "CIK0001045810.json"
    companyfacts_cache.parent.mkdir(parents=True, exist_ok=True)
    companyfacts_cache.write_text(json.dumps(_sample_companyfacts_payload()), encoding="utf-8")

    payload = fetch_companyfacts("0001045810", "Test test@example.com", cache_dir=cache_dir, fetcher=should_not_fetch)
    assert payload["entityName"] == "NVIDIA CORP"


def test_no_cache_sec_requests_do_not_create_cache_paths(tmp_path: Path):
    cache_dir = tmp_path / "must-not-exist"
    requested_urls: list[str] = []

    def fake_ticker_fetch(url, *_args):
        requested_urls.append(url)
        return _sample_ticker_map_payload()

    def fake_companyfacts_fetch(url, *_args):
        requested_urls.append(url)
        return _sample_companyfacts_payload()

    ticker_map = load_sec_ticker_map(
        cache_dir=cache_dir,
        user_agent="Test test@example.com",
        cache=False,
        fetcher=fake_ticker_fetch,
    )
    payload = fetch_companyfacts(
        "0001045810",
        "Test test@example.com",
        cache=False,
        cache_dir=cache_dir,
        fetcher=fake_companyfacts_fetch,
    )

    assert ticker_map["NVDA"]["cik"] == "0001045810"
    assert payload["entityName"] == "NVIDIA CORP"
    assert requested_urls == [
        "https://www.sec.gov/files/company_tickers.json",
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
    ]
    assert not cache_dir.exists()


def test_extractor_records_direct_and_derived_field_provenance():
    row = extract_fundamentals_from_companyfacts(_sample_companyfacts_payload())
    provenance = row["_field_provenance"]

    assert provenance["revenue"]["value_kind"] == "direct"
    assert provenance["revenue"]["records"] == [
        {
            "taxonomy": "us-gaap",
            "concept": "Revenues",
            "unit": "USD",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "filed": "2026-02-20",
                "form": "10-K",
                "accession": "0001045810-26-000001",
                "fiscal_year": 2025,
                "fiscal_period": "FY",
            }
        ]
    assert provenance["free_cash_flow"]["value_kind"] == "derived"
    assert {record["concept"] for record in provenance["free_cash_flow"]["records"]} == {
        "NetCashProvidedByUsedInOperatingActivities",
        "PaymentsToAcquirePropertyPlantAndEquipment",
    }
    assert provenance["fcf_margin"]["value_kind"] == "derived"
    assert provenance["shares_outstanding"]["value_kind"] == "direct"
    assert provenance["debt"]["value_kind"] == "derived"
    assert len(provenance["debt"]["records"]) == 3
    components = row["_source_components"]
    assert components["cash_from_operations"]["value"] == 250
    assert components["capital_expenditures"]["value"] == 50
    assert components["operating_income"]["value"] == 250
    assert components["net_income"]["value"] == 200
    assert all(component["value_kind"] == "direct" for component in components.values())


def test_extractor_keeps_single_reported_total_debt_direct():
    payload = _sample_companyfacts_payload()
    gaap = payload["facts"]["us-gaap"]
    for concept in (
        "ShortTermBorrowings",
        "LongTermDebtCurrent",
        "LongTermDebtNoncurrent",
    ):
        gaap.pop(concept)
    gaap["LongTermDebt"] = {
        "units": {
            "USD": [
                {
                    "val": 150,
                    "end": "2025-12-31",
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-02-20",
                    "accn": "0001045810-26-000001",
                }
            ]
        }
    }

    row = extract_fundamentals_from_companyfacts(payload)

    assert row["debt"] == 150
    assert row["_field_provenance"]["debt"]["value_kind"] == "direct"
    assert len(row["_field_provenance"]["debt"]["records"]) == 1


def test_extractor_keeps_single_debt_component_derived_and_incomplete():
    payload = _sample_companyfacts_payload()
    gaap = payload["facts"]["us-gaap"]
    gaap.pop("ShortTermBorrowings")
    gaap.pop("LongTermDebtNoncurrent")

    row = extract_fundamentals_from_companyfacts(payload)

    assert row["debt"] == 20
    assert row["_field_provenance"]["debt"]["value_kind"] == "derived"
    assert len(row["_field_provenance"]["debt"]["records"]) == 1


def test_staging_rows_omit_private_field_provenance(tmp_path: Path):
    result = build_sec_fundamentals_rows(
        ["NVDA"],
        user_agent="Test test@example.com",
        cache_dir=tmp_path / "cache",
        ticker_map={"NVDA": {"ticker": "NVDA", "cik": "0001045810"}},
        companyfacts_fetcher=lambda *_: _sample_companyfacts_payload(),
    )

    assert "_field_provenance" not in result["rows"][0]
    assert "_source_components" not in result["rows"][0]


def test_tiny_sec_ticker_map_cache_refreshes(monkeypatch, tmp_path: Path):
    cache_dir = tmp_path / "cache"
    ticker_cache = cache_dir / "company_tickers.json"
    ticker_cache.parent.mkdir(parents=True, exist_ok=True)
    ticker_cache.write_text(json.dumps({"0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"}}), encoding="utf-8")

    def fake_fetch(*_args, **_kwargs):
        rows = {
            str(index): {"cik_str": 1000000 + index, "ticker": f"T{index}", "title": f"Company {index}"}
            for index in range(120)
        }
        rows["121"] = {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"}
        return rows

    monkeypatch.setattr("src.providers.sec_companyfacts._fetch_json", fake_fetch)
    ticker_map = load_sec_ticker_map(cache_dir=cache_dir, user_agent="Test test@example.com")

    assert ticker_map["MSFT"]["cik"] == "0000789019"
    assert len(json.loads(ticker_cache.read_text(encoding="utf-8"))) > 100


def test_tiny_companyfacts_cache_refreshes(monkeypatch, tmp_path: Path):
    cache_dir = tmp_path / "cache"
    facts_cache = cache_dir / "companyfacts" / "CIK0001045810.json"
    facts_cache.parent.mkdir(parents=True, exist_ok=True)
    facts_cache.write_text(json.dumps({"entityName": "Fixture Corp", "facts": {}}), encoding="utf-8")

    def fake_fetch(*_args, **_kwargs):
        return {"entityName": "Refreshed Corp", "facts": {"us-gaap": {}}}

    monkeypatch.setattr("src.providers.sec_companyfacts._fetch_json", fake_fetch)
    payload = fetch_companyfacts("0001045810", "Test test@example.com", cache_dir=cache_dir)

    assert payload["entityName"] == "Refreshed Corp"
    assert json.loads(facts_cache.read_text(encoding="utf-8"))["entityName"] == "Refreshed Corp"


def test_build_sec_fundamentals_rows_and_write_import_file(tmp_path: Path):
    result = build_sec_fundamentals_rows(
        ["NVDA"],
        user_agent="Test test@example.com",
        cache_dir=tmp_path / "cache",
        ticker_map={"NVDA": {"ticker": "NVDA", "cik": "0001045810"}},
        companyfacts_fetcher=lambda *_: _sample_companyfacts_payload(),
    )
    output_path = tmp_path / "data" / "imports" / "fundamentals.csv"
    write_result = write_sec_fundamentals_import(result["rows"], output_path=output_path)

    assert result["resolved_tickers"] == ["NVDA"]
    assert write_result["status"] == "written"
    assert output_path.exists()

    validation = validate_imports(base_dir=tmp_path)
    preview = preview_import_merge(base_dir=tmp_path)
    assert validation["status"] in {"valid", "valid_with_warnings"}
    assert preview["preview"][0]["new_rows"] == 1


def test_build_sec_fundamentals_rows_resolves_dot_class_alias_but_preserves_requested_ticker(tmp_path: Path):
    result = build_sec_fundamentals_rows(
        ["BRK.B"],
        user_agent="Test test@example.com",
        cache_dir=tmp_path / "cache",
        ticker_map={"BRK-B": {"ticker": "BRK-B", "cik": "0001067983"}},
        companyfacts_fetcher=lambda *_: _sample_companyfacts_payload(),
    )

    assert result["resolved_tickers"] == ["BRK.B"]
    assert result["unresolved_tickers"] == []
    assert result["rows"][0]["ticker"] == "BRK.B"
    assert result["row_summaries"][0]["sec_cik"] == "0001067983"


def test_write_sec_fundamentals_import_updates_existing_float_rows_with_missing_values(tmp_path: Path):
    output_path = tmp_path / "data" / "imports" / "fundamentals.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "ticker,revenue,free_cash_flow,shares_outstanding,source,as_of_date\n"
        "NVDA,1000,250,24000000000,manual_import,2025-12-31\n",
        encoding="utf-8",
    )

    write_result = write_sec_fundamentals_import(
        [
            {
                "ticker": "NVDA",
                "revenue": 1200,
                "source": "sec_companyfacts",
                "as_of_date": "2026-01-31",
            }
        ],
        output_path=output_path,
    )

    staged = pd.read_csv(output_path)
    nvda = staged.set_index("ticker").loc["NVDA"]
    assert write_result["status"] == "written"
    assert nvda["revenue"] == 1200
    assert nvda["source"] == "sec_companyfacts"
    assert pd.isna(nvda["free_cash_flow"])


def test_write_sec_fundamentals_import_refuses_canonical_data_path(tmp_path: Path):
    with pytest.raises(ValueError):
        write_sec_fundamentals_import(
            [{"ticker": "NVDA", "revenue": 1000, "source": "sec_companyfacts"}],
            output_path=tmp_path / "data" / "fundamentals.csv",
        )


def test_stock_report_cli_sec_stage_fundamentals_json(tmp_path: Path, monkeypatch, capsys):
    def fake_build(tickers, **_kwargs):
        return {
            "requested_tickers": tickers,
            "resolved_tickers": ["NVDA"],
            "unresolved_tickers": [],
            "rows": [{"ticker": "NVDA", "revenue": 1000, "source": "sec_companyfacts", "as_of_date": "2025-12-31"}],
            "row_summaries": [
                {"ticker": "NVDA", "sec_cik": "0001045810", "populated_fields": ["revenue"], "missing_fields": ["eps"], "warnings": []}
            ],
            "warnings": [],
        }

    monkeypatch.setattr("src.stock_report.build_sec_fundamentals_rows", fake_build)
    previous_cwd = Path.cwd()
    previous_argv = sys.argv[:]
    os.chdir(tmp_path)
    sys.argv = [
        "python",
        "--project-root",
        str(tmp_path),
        "--sec-stage-fundamentals",
        "--tickers",
        "NVDA",
        "--sec-user-agent",
        "Test test@example.com",
        "--json",
    ]
    try:
        main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["resolved_tickers"] == ["NVDA"]
        assert payload["rows_written"] == 1
        assert (tmp_path / "data" / "imports" / "fundamentals.csv").exists()
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)
