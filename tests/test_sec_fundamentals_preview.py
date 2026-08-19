from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.sec_fundamentals_preview import (
    build_sec_fundamentals_preview,
    parse_preview_tickers,
    render_sec_fundamentals_preview,
)


def _ticker_map_payload():
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "APPLE INC"},
        "1": {"cik_str": 1018724, "ticker": "AMZN", "title": "AMAZON COM INC"},
        "2": {"cik_str": 1652044, "ticker": "GOOG", "title": "ALPHABET INC"},
    }


def _record(
    value,
    *,
    concept_period="2025-09-27",
    start="2024-09-29",
    unit="USD",
    accession="0000320193-25-000079",
):
    return {
        "val": value,
        "start": start,
        "end": concept_period,
        "fy": 2025,
        "fp": "FY",
        "form": "10-K",
        "filed": "2025-10-31",
        "accn": accession,
        "_unit": unit,
    }


def _fact(record):
    unit = record.pop("_unit", "USD")
    return {"units": {unit: [record]}}


def _companyfacts_payload(
    *,
    include_shares=True,
    eps_period="2025-09-27",
    cik=320193,
    accession="0000320193-25-000079",
):
    revenue_latest = _record(416_161_000_000, accession=accession)
    revenue_prior = _record(
        391_035_000_000,
        concept_period="2024-09-28",
        start="2023-10-01",
        accession=accession,
    )
    facts = {
        "us-gaap": {
            "Revenues": {"units": {"USD": [revenue_latest, revenue_prior]}},
            "NetIncomeLoss": _fact(_record(112_010_000_000, accession=accession)),
            "EarningsPerShareDiluted": _fact(
                _record(
                    7.46,
                    concept_period=eps_period,
                    unit="USD/shares",
                    accession=accession,
                )
            ),
            "NetCashProvidedByUsedInOperatingActivities": _fact(
                _record(111_482_000_000, accession=accession)
            ),
            "PaymentsToAcquirePropertyPlantAndEquipment": _fact(
                _record(12_715_000_000, accession=accession)
            ),
            "OperatingIncomeLoss": _fact(
                _record(133_050_000_000, accession=accession)
            ),
            "CashAndCashEquivalentsAtCarryingValue": _fact(
                _record(35_934_000_000, start=None, accession=accession)
            ),
            "LongTermDebt": _fact(
                _record(82_714_000_000, start=None, accession=accession)
            ),
        },
        "dei": {},
    }
    if include_shares:
        facts["dei"]["EntityCommonStockSharesOutstanding"] = _fact(
            _record(
                14_687_356_000,
                start=None,
                unit="shares",
                accession=accession,
            )
        )
    return {"cik": cik, "entityName": "TEST COMPANY", "facts": facts}


def _canonical_file(path: Path):
    pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "revenue": 265_595_000_000,
                "net_income": 100_000_000_000,
                "eps": 7.46,
                "free_cash_flow": 98_767_000_000,
                "shares_outstanding": 14_687_356_000,
                "source": "sec_companyfacts",
                "as_of_date": "2018-09-29",
                "sec_filed_date": "2018-11-05",
            },
            {"ticker": "AMZN", "revenue": 1, "as_of_date": "2024-12-31"},
            {"ticker": "GOOG", "revenue": 1, "as_of_date": "2024-12-31"},
        ]
    ).to_csv(path, index=False)


def _build(
    tmp_path: Path,
    *,
    payload=None,
    staged=True,
    retrieval_timestamp=None,
):
    canonical = tmp_path / "fundamentals.csv"
    _canonical_file(canonical)
    staged_path = tmp_path / "staged.csv"
    if staged:
        staged_path.write_text("ticker,revenue,currency\nAAPL,1,USD\n", encoding="utf-8")
    requested_urls: list[str] = []

    def ticker_fetcher(url, *_args):
        requested_urls.append(url)
        return _ticker_map_payload()

    def facts_fetcher(url, *_args):
        requested_urls.append(url)
        return payload if payload is not None else _companyfacts_payload()

    kwargs = {}
    if retrieval_timestamp is not None:
        kwargs["retrieval_timestamp"] = retrieval_timestamp
    result = build_sec_fundamentals_preview(
        "AAPL",
        canonical_path=canonical,
        staged_path=staged_path,
        user_agent="Test test@example.com",
        ticker_map_fetcher=ticker_fetcher,
        companyfacts_fetcher=facts_fetcher,
        cache_dir=tmp_path / "must-not-exist",
        **kwargs,
    )
    return result, requested_urls


def test_preview_requires_explicit_tickers_and_caps_unique_cohort_at_five():
    with pytest.raises(ValueError, match="explicit"):
        parse_preview_tickers("")
    assert parse_preview_tickers("aapl, AMZN,aapl,goog") == ["AAPL", "AMZN", "GOOG"]
    with pytest.raises(ValueError, match="five"):
        parse_preview_tickers("A,B,C,D,E,F")


def test_preview_uses_only_official_sec_endpoints_and_writes_no_cache(tmp_path: Path):
    result, urls = _build(tmp_path)

    assert result["status"] == "inspection_only"
    assert urls == [
        "https://www.sec.gov/files/company_tickers.json",
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
    ]
    assert all(url.startswith(("https://www.sec.gov/", "https://data.sec.gov/")) for url in urls)
    assert not (tmp_path / "must-not-exist").exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "fundamentals.csv",
        "staged.csv",
    ]


def test_preview_preserves_existing_cache_and_input_bytes(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    ticker_cache = cache_dir / "company_tickers.json"
    facts_cache = cache_dir / "companyfacts" / "CIK0000320193.json"
    facts_cache.parent.mkdir(parents=True)
    ticker_cache.write_bytes(b"user-owned-ticker-cache")
    facts_cache.write_bytes(b"user-owned-companyfacts-cache")
    canonical = tmp_path / "fundamentals.csv"
    staged = tmp_path / "staged.csv"
    _canonical_file(canonical)
    staged.write_text("ticker,revenue,currency\nAAPL,1,USD\n", encoding="utf-8")
    before = {
        path: path.read_bytes() for path in (ticker_cache, facts_cache, canonical, staged)
    }

    build_sec_fundamentals_preview(
        "AAPL",
        canonical_path=canonical,
        staged_path=staged,
        user_agent="Test test@example.com",
        ticker_map_fetcher=lambda *_: _ticker_map_payload(),
        companyfacts_fetcher=lambda *_: _companyfacts_payload(),
        cache_dir=cache_dir,
    )

    assert {path: path.read_bytes() for path in before} == before


def test_preview_exposes_aapl_mixed_canonical_period_and_field_classifications(tmp_path: Path):
    result, _ = _build(tmp_path)
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}

    assert ticker["ticker"] == "AAPL"
    assert ticker["candidate_period_end"] == "2025-09-27"
    assert ticker["canonical_period_end"] == "2018-09-29"
    assert ticker["canonical_period_status"] == "period_mismatch"
    assert fields["revenue"]["candidate_value"] == 416_161_000_000
    assert fields["revenue"]["value_status"] == "changed"
    assert fields["revenue"]["classification"] == "approved_direct"
    assert fields["revenue"]["value_kind"] == "direct"
    assert fields["revenue"]["accession"] == "0000320193-25-000079"
    assert fields["eps"]["value_status"] == "unchanged"
    assert fields["eps"]["classification"] == "unsupported"
    assert fields["free_cash_flow"]["classification"] == "derived_scope_review_required"
    assert fields["free_cash_flow"]["value_kind"] == "derived"
    assert fields["fcf_margin"]["classification"] == "derived_scope_review_required"
    assert fields["shares_outstanding"]["classification"] == "approved_direct"
    assert all(row["publishability_blocker"] for row in ticker["fields"] if row["classification"] != "approved_direct")
    components = {row["field"]: row for row in ticker["source_components"]}
    assert components["cash_from_operations"]["candidate_value"] == 111_482_000_000
    assert components["cash_from_operations"]["classification"] == "approved_direct"
    assert components["capital_expenditures"]["classification"] == "approved_direct"
    assert components["operating_income"]["classification"] == "approved_direct"
    assert components["net_income"]["classification"] == "unsupported"
    assert components["net_income"]["schema_status"] == "existing_canonical_not_produced"
    assert all(
        components[field]["schema_status"] == "candidate_component_not_canonical"
        for field in (
            "cash_from_operations",
            "capital_expenditures",
            "operating_income",
        )
    )
    assert "net_income" not in fields


def test_preview_emits_complete_field_level_review_metadata(tmp_path: Path):
    result, _ = _build(
        tmp_path,
        retrieval_timestamp="2026-08-18T22:15:30Z",
    )
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}
    components = {row["field"]: row for row in ticker["source_components"]}

    assert result["retrieval_timestamp"] == "2026-08-18T22:15:30Z"
    assert ticker["sec_cik"] == "0000320193"
    assert ticker["changed_fields"] == [
        "revenue",
        "revenue_growth",
        "fcf_margin",
        "profit_margin",
        "operating_margin",
        "cash",
        "debt",
        "filing_dates",
    ]
    assert ticker["schema_review_required_fields"] == [
        "cash_from_operations",
        "capital_expenditures",
        "operating_income",
    ]
    assert "eps" in ticker["intentionally_withheld_fields"]
    assert "free_cash_flow" in ticker["intentionally_withheld_fields"]

    revenue = fields["revenue"]
    assert revenue == {
        **revenue,
        "ticker": "AAPL",
        "sec_cik": "0000320193",
        "canonical_column": "revenue",
        "unit": "USD",
        "source_units": ["USD"],
        "retrieval_timestamp": "2026-08-18T22:15:30Z",
        "source_rights_status": "approved",
        "commercial_rights_approved": True,
        "required_registered_field": "revenue",
        "field_scope_status": "approved",
        "missing_registered_fields": [],
        "proposed_delta": {
            "from": 265_595_000_000,
            "to": 416_161_000_000,
            "numeric_change": 150_566_000_000,
        },
        "required_owner_action": "review_field_delta_before_separate_apply_authorization",
    }
    assert revenue["source_refs"][0]["retrieval_timestamp"] == "2026-08-18T22:15:30Z"

    filing_date = fields["filing_dates"]
    assert filing_date["canonical_column"] == "sec_filed_date"
    assert filing_date["candidate_value"] == "2025-10-31"
    assert filing_date["unit"] == "date"
    assert filing_date["value_kind"] == "direct"
    assert filing_date["classification"] == "approved_direct"
    assert filing_date["field_scope_status"] == "approved"
    assert filing_date["source_units"] == ["date"]
    assert filing_date["source_refs"][0]["taxonomy"] == "us-gaap"
    assert filing_date["source_refs"][0]["concept"] == "Revenues"
    assert filing_date["source_refs"][0]["unit"] == "date"
    assert filing_date["source_refs"][0]["underlying_fact_unit"] == "USD"
    assert filing_date["proposed_delta"] == {
        "from": "2018-11-05",
        "to": "2025-10-31",
        "numeric_change": None,
    }
    assert "filing_dates" in ticker["future_apply_candidate_fields"]

    operating_income = components["operating_income"]
    assert operating_income["unit"] == "USD"
    assert operating_income["source_rights_status"] == "approved"
    assert operating_income["field_scope_status"] == "approved"
    assert operating_income["required_owner_action"] == (
        "approve_canonical_schema_before_any_apply"
    )

    shares = fields["shares_outstanding"]
    assert shares["basis_status"] == "reported_value_no_split_adjustment"
    assert shares["classification"] == "approved_direct"


def test_preview_blocks_cross_currency_derived_values(tmp_path: Path):
    payload = _companyfacts_payload()
    capex = payload["facts"]["us-gaap"][
        "PaymentsToAcquirePropertyPlantAndEquipment"
    ]["units"].pop("USD")[0]
    payload["facts"]["us-gaap"][
        "PaymentsToAcquirePropertyPlantAndEquipment"
    ]["units"]["EUR"] = [capex]

    result, _ = _build(tmp_path, payload=payload)
    fields = {row["field"]: row for row in result["tickers"][0]["fields"]}

    assert fields["free_cash_flow"]["source_units"] == ["EUR", "USD"]
    assert fields["free_cash_flow"]["unit"] == "mixed"
    assert fields["free_cash_flow"]["classification"] == "unit_conflict"
    assert "consistent source units" in fields["free_cash_flow"][
        "publishability_blocker"
    ]
    assert fields["fcf_margin"]["classification"] == "unit_conflict"


def test_preview_does_not_make_missing_canonical_columns_apply_candidates(
    tmp_path: Path,
):
    canonical = tmp_path / "fundamentals.csv"
    pd.DataFrame(
        [{"ticker": "AAPL", "revenue": 1, "as_of_date": "2024-01-01"}]
    ).to_csv(canonical, index=False)
    result = build_sec_fundamentals_preview(
        "AAPL",
        retrieval_timestamp="2026-08-18T22:15:30Z",
        canonical_path=canonical,
        staged_path=tmp_path / "missing.csv",
        user_agent="Test test@example.com",
        ticker_map_fetcher=lambda *_: _ticker_map_payload(),
        companyfacts_fetcher=lambda *_: _companyfacts_payload(),
        cache_dir=tmp_path / "must-not-exist",
    )
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}

    assert fields["filing_dates"]["classification"] == "approved_direct"
    assert fields["filing_dates"]["schema_status"] == "canonical_column_missing"
    assert fields["filing_dates"]["required_owner_action"] == (
        "approve_canonical_schema_before_any_apply"
    )
    assert "filing_dates" not in ticker["future_apply_candidate_fields"]


def test_preview_blocks_mixed_candidate_periods(tmp_path: Path):
    payload = _companyfacts_payload(eps_period="2024-09-28")
    payload["facts"]["us-gaap"]["EarningsPerShareDiluted"]["units"][
        "USD/shares"
    ][0]["start"] = "2023-10-01"
    result, _ = _build(tmp_path, payload=payload)
    fields = {row["field"]: row for row in result["tickers"][0]["fields"]}

    assert fields["eps"]["classification"] == "period_conflict"
    assert fields["eps"]["candidate_value"] == 7.46
    assert "annual anchor" in fields["eps"]["publishability_blocker"]
    assert "2024-09-29" in fields["eps"]["publishability_blocker"]


def test_preview_labels_aggregated_debt_derived_but_single_total_direct(
    tmp_path: Path,
):
    direct_result, _ = _build(tmp_path)
    direct_fields = {
        row["field"]: row for row in direct_result["tickers"][0]["fields"]
    }
    assert direct_fields["debt"]["value_kind"] == "direct"
    assert direct_fields["debt"]["classification"] == "unsupported"

    payload = _companyfacts_payload()
    gaap = payload["facts"]["us-gaap"]
    gaap.pop("LongTermDebt")
    gaap["ShortTermBorrowings"] = _fact(_record(10_000_000_000, start=None))
    gaap["LongTermDebtNoncurrent"] = _fact(
        _record(72_714_000_000, start=None)
    )
    aggregated_result, _ = _build(tmp_path, payload=payload)
    aggregated_fields = {
        row["field"]: row for row in aggregated_result["tickers"][0]["fields"]
    }

    assert aggregated_fields["debt"]["candidate_value"] == 82_714_000_000
    assert aggregated_fields["debt"]["value_kind"] == "derived"
    assert (
        aggregated_fields["debt"]["classification"]
        == "derived_scope_review_required"
    )


def test_preview_rejects_long_duration_quarterly_fact_as_annual_anchor(
    tmp_path: Path,
):
    payload = _companyfacts_payload()
    revenue_records = payload["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    revenue_records[0]["form"] = "10-Q"
    revenue_records[0]["start"] = "2024-01-01"
    shares = payload["facts"]["dei"]["EntityCommonStockSharesOutstanding"]
    shares["units"]["shares"][0]["val"] = 14_000_000_000

    result, _ = _build(tmp_path, payload=payload)
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}

    assert fields["revenue"]["classification"] == "period_conflict"
    assert fields["shares_outstanding"]["classification"] == "source_context_ambiguous"
    assert "annual filing" in fields["revenue"]["publishability_blocker"]
    assert ticker["future_apply_candidate_fields"] == []
    assert ticker["future_apply_proposal_status"] == "blocked"


def test_preview_rejects_short_duration_fact_even_when_labelled_annual(
    tmp_path: Path,
):
    payload = _companyfacts_payload()
    revenue = payload["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]
    revenue["start"] = "2025-07-01"
    shares = payload["facts"]["dei"]["EntityCommonStockSharesOutstanding"]
    shares["units"]["shares"][0]["val"] = 14_000_000_000

    result, _ = _build(tmp_path, payload=payload)
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}

    assert ticker["candidate_period_end"] is None
    assert fields["revenue"]["classification"] == "period_conflict"
    assert "annual duration" in fields["revenue"]["publishability_blocker"]
    assert fields["shares_outstanding"]["classification"] == "source_context_ambiguous"
    assert ticker["future_apply_candidate_fields"] == []


def test_preview_rejects_same_end_but_different_annual_period_start(
    tmp_path: Path,
):
    payload = _companyfacts_payload()
    operating_income = payload["facts"]["us-gaap"]["OperatingIncomeLoss"][
        "units"
    ]["USD"][0]
    operating_income["start"] = "2024-08-01"

    result, _ = _build(tmp_path, payload=payload)
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}
    components = {row["field"]: row for row in ticker["source_components"]}

    assert fields["operating_margin"]["classification"] == "period_conflict"
    assert "period start" in fields["operating_margin"]["publishability_blocker"]
    assert components["operating_income"]["classification"] == "period_conflict"
    assert "period start" in components["operating_income"]["publishability_blocker"]


def test_revenue_growth_requires_adjacent_complete_annual_records(tmp_path: Path):
    gap_payload = _companyfacts_payload()
    gap_prior = gap_payload["facts"]["us-gaap"]["Revenues"]["units"]["USD"][1]
    gap_prior.update(
        {
            "start": "2022-01-01",
            "end": "2022-12-31",
            "fy": 2022,
            "filed": "2023-02-01",
            "accn": "0000320193-23-000001",
        }
    )
    gap_result, _ = _build(tmp_path, payload=gap_payload)
    gap_growth = {
        row["field"]: row for row in gap_result["tickers"][0]["fields"]
    }["revenue_growth"]

    assert gap_growth["classification"] == "period_conflict"
    assert "adjacent" in gap_growth["publishability_blocker"]

    incomplete_payload = _companyfacts_payload()
    incomplete_prior = incomplete_payload["facts"]["us-gaap"]["Revenues"]["units"]["USD"][1]
    incomplete_prior["accn"] = None
    incomplete_result, _ = _build(tmp_path, payload=incomplete_payload)
    incomplete_growth = {
        row["field"]: row
        for row in incomplete_result["tickers"][0]["fields"]
    }["revenue_growth"]

    assert incomplete_growth["classification"] == "source_context_ambiguous"
    assert "complete" in incomplete_growth["publishability_blocker"]


def test_preview_does_not_substitute_another_fact_for_missing_revenue_anchor(
    tmp_path: Path,
):
    payload = _companyfacts_payload()
    payload["facts"]["us-gaap"].pop("Revenues")

    result, _ = _build(tmp_path, payload=payload)
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}
    components = {row["field"]: row for row in ticker["source_components"]}

    assert ticker["candidate_period_end"] is None
    assert ticker["candidate_accession"] is None
    assert fields["revenue"]["classification"] == "missing"
    assert components["net_income"]["classification"] == "period_conflict"
    assert ticker["future_apply_candidate_fields"] == []


def test_preview_keeps_missing_goog_shares_unavailable(tmp_path: Path):
    canonical = tmp_path / "fundamentals.csv"
    _canonical_file(canonical)
    result = build_sec_fundamentals_preview(
        "GOOG",
        canonical_path=canonical,
        staged_path=tmp_path / "missing-staged.csv",
        user_agent="Test test@example.com",
        ticker_map_fetcher=lambda *_: _ticker_map_payload(),
        companyfacts_fetcher=lambda *_: _companyfacts_payload(
            include_shares=False,
            cik=1652044,
            accession="0001652044-25-000100",
        ),
        cache_dir=tmp_path / "must-not-exist",
    )
    fields = {row["field"]: row for row in result["tickers"][0]["fields"]}

    assert fields["shares_outstanding"]["candidate_value"] is None
    assert fields["shares_outstanding"]["classification"] == "missing"
    assert fields["shares_outstanding"]["value_status"] == "missing"


def test_preview_inspects_sec_candidate_but_blocks_apply_when_canonical_row_is_missing(
    tmp_path: Path,
):
    canonical = tmp_path / "fundamentals.csv"
    pd.DataFrame(
        [{"ticker": "AAPL", "revenue": 1, "as_of_date": "2024-01-01"}]
    ).to_csv(canonical, index=False)
    result = build_sec_fundamentals_preview(
        "GOOG",
        canonical_path=canonical,
        staged_path=tmp_path / "missing.csv",
        user_agent="Test test@example.com",
        ticker_map_fetcher=lambda *_: _ticker_map_payload(),
        companyfacts_fetcher=lambda *_: _companyfacts_payload(
            include_shares=False,
            cik=1652044,
            accession="0001652044-25-000100",
        ),
        cache_dir=tmp_path / "must-not-exist",
    )
    ticker = result["tickers"][0]
    fields = {row["field"]: row for row in ticker["fields"]}

    assert ticker["status"] == "compared_canonical_missing"
    assert ticker["canonical_period_status"] == "unavailable"
    assert ticker["future_apply_proposal_status"] == "blocked"
    assert fields["revenue"]["candidate_value"] == 416_161_000_000
    assert fields["revenue"]["canonical_value"] is None
    assert fields["shares_outstanding"]["classification"] == "missing"


def test_preview_rejects_companyfacts_from_a_different_cik(tmp_path: Path):
    result, _ = _build(
        tmp_path,
        payload=_companyfacts_payload(cik=1652044),
    )

    assert result["tickers"][0]["status"] == "source_context_ambiguous"
    assert result["tickers"][0]["fields"] == []
    assert "CIK" in result["tickers"][0]["blocker"]


def test_preview_fails_closed_for_malformed_companyfacts(tmp_path: Path):
    result, _ = _build(tmp_path, payload={"facts": []})

    assert result["tickers"][0]["status"] == "invalid_payload"
    assert result["tickers"][0]["fields"] == []
    assert "malformed" in result["tickers"][0]["blocker"].lower()


def test_malformed_first_ticker_does_not_abort_later_valid_ticker(tmp_path: Path):
    canonical = tmp_path / "fundamentals.csv"
    _canonical_file(canonical)

    def facts_fetcher(url, *_args):
        if "CIK0000320193" in url:
            return {
                "cik": 320193,
                "facts": {
                    "us-gaap": {
                        "Revenues": {"units": {"USD": "malformed"}}
                    }
                },
            }
        return _companyfacts_payload(
            cik=1018724,
            accession="0001018724-25-000100",
        )

    result = build_sec_fundamentals_preview(
        "AAPL,AMZN",
        canonical_path=canonical,
        staged_path=tmp_path / "missing.csv",
        user_agent="Test test@example.com",
        ticker_map_fetcher=lambda *_: _ticker_map_payload(),
        companyfacts_fetcher=facts_fetcher,
        cache_dir=tmp_path / "must-not-exist",
    )

    assert [ticker["ticker"] for ticker in result["tickers"]] == ["AAPL", "AMZN"]
    assert result["tickers"][0]["status"] == "invalid_payload"
    assert result["tickers"][0]["fields"] == []
    assert result["tickers"][1]["status"] == "compared"
    assert result["tickers"][1]["fields"]


def test_preview_reports_staged_schema_expansion_and_is_deterministic(tmp_path: Path):
    retrieval_timestamp = "2026-08-18T22:15:30Z"
    result, _ = _build(tmp_path, retrieval_timestamp=retrieval_timestamp)
    rebuilt, _ = _build(tmp_path, retrieval_timestamp=retrieval_timestamp)

    assert result["schema_delta"]["staged_extra_columns"] == ["currency"]
    assert "cash_from_operations" in result["schema_delta"]["candidate_component_extra_columns"]
    assert "net_income" not in result["schema_delta"]["candidate_component_extra_columns"]
    assert "net_income" in result["schema_delta"]["canonical_columns_not_produced"]
    rendered = render_sec_fundamentals_preview(result)
    assert json.loads(rendered) == result
    assert rendered == render_sec_fundamentals_preview(rebuilt)
