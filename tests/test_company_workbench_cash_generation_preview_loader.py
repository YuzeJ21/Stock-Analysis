from __future__ import annotations

import inspect
import json
from pathlib import Path

from src.company_workbench_cash_generation_preview_loader import (
    CASH_GENERATION_PREVIEW_FILINGS,
    load_company_workbench_cash_generation_preview,
)


START = "2026-01-26"
END = "2026-04-26"
ACCESSION = "0001045810-26-000052"
AMD_START = "2025-12-28"
AMD_END = "2026-03-28"
AMD_ACCESSION = "0000002488-26-000076"


def _fact(value: float) -> dict[str, object]:
    return {
        "start": START,
        "end": END,
        "val": value,
        "accn": ACCESSION,
        "fy": 2027,
        "fp": "Q1",
        "form": "10-Q",
        "filed": "2026-05-20",
    }


def _companyfacts() -> dict[str, object]:
    return {
        "cik": 1045810,
        "entityName": "NVIDIA CORP",
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [_fact(81_615_000_000)]}
                },
                "OperatingIncomeLoss": {
                    "units": {"USD": [_fact(53_536_000_000)]}
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {"USD": [_fact(50_344_000_000)]}
                },
                "PaymentsToAcquireProductiveAssets": {
                    "units": {"USD": [_fact(1_757_000_000)]}
                },
            }
        },
    }


def _submissions() -> dict[str, object]:
    return {
        "cik": "0001045810",
        "filings": {
            "recent": {
                "accessionNumber": [ACCESSION],
                "filingDate": ["2026-05-20"],
                "acceptanceDateTime": ["2026-05-20T20:35:52.000Z"],
                "form": ["10-Q"],
                "primaryDocument": ["nvda-20260426.htm"],
            }
        },
    }


def _filing() -> str:
    return f"""
    <html><body>
      <xbrli:context id="c-q1">
        <xbrli:period>
          <xbrli:startDate>{START}</xbrli:startDate>
          <xbrli:endDate>{END}</xbrli:endDate>
        </xbrli:period>
      </xbrli:context>
      <table>
        <tr><td>Revenue</td><td><ix:nonFraction id="f-revenue" name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="c-q1" scale="6">81,615</ix:nonFraction></td></tr>
        <tr><td>Operating income</td><td><ix:nonFraction id="f-operating" name="us-gaap:OperatingIncomeLoss" contextRef="c-q1" scale="6">53,536</ix:nonFraction></td></tr>
        <tr><td>Net cash provided by operating activities</td><td><ix:nonFraction id="f-cfo" name="us-gaap:NetCashProvidedByUsedInOperatingActivities" contextRef="c-q1" scale="6">50,344</ix:nonFraction></td></tr>
        <tr><td>Purchases related to property and equipment and intangible assets</td><td>(</td><td><ix:nonFraction id="f-capex" name="us-gaap:PaymentsToAcquireProductiveAssets" contextRef="c-q1" scale="6">1,757</ix:nonFraction></td><td>)</td></tr>
      </table>
    </body></html>
    """


def _fetcher(calls: list[tuple[str, str]]):
    def fetch(url: str, user_agent: str) -> bytes:
        calls.append((url, user_agent))
        if "companyfacts" in url:
            return json.dumps(_companyfacts()).encode("utf-8")
        if "submissions" in url:
            return json.dumps(_submissions()).encode("utf-8")
        return _filing().encode("utf-8")

    return fetch


def _amd_fact(value: float) -> dict[str, object]:
    return {
        "start": AMD_START,
        "end": AMD_END,
        "val": value,
        "accn": AMD_ACCESSION,
        "fy": 2026,
        "fp": "Q1",
        "form": "10-Q",
        "filed": "2026-05-06",
    }


def _amd_companyfacts() -> dict[str, object]:
    return {
        "cik": 2488,
        "entityName": "ADVANCED MICRO DEVICES INC",
        "facts": {"us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"USD": [_amd_fact(10_253_000_000)]}
            },
            "OperatingIncomeLoss": {"units": {"USD": [_amd_fact(1_476_000_000)]}},
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {"USD": [_amd_fact(2_955_000_000)]}
            },
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {"USD": [_amd_fact(389_000_000)]}
            },
        }},
    }


def _amd_submissions() -> dict[str, object]:
    return {"cik": "0000002488", "filings": {"recent": {
        "accessionNumber": [AMD_ACCESSION],
        "filingDate": ["2026-05-06"],
        "acceptanceDateTime": ["2026-05-05T18:06:27.000-04:00"],
        "form": ["10-Q"],
        "primaryDocument": ["amd-20260328.htm"],
    }}}


def _amd_filing() -> str:
    return f"""
    <html><body><xbrli:context id="amd-q1"><xbrli:period>
      <xbrli:startDate>{AMD_START}</xbrli:startDate>
      <xbrli:endDate>{AMD_END}</xbrli:endDate>
    </xbrli:period></xbrli:context><table>
      <tr><td>Net revenue</td><td><ix:nonFraction id="amd-revenue" name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="amd-q1" scale="6">10,253</ix:nonFraction></td></tr>
      <tr><td>Operating income</td><td><ix:nonFraction id="amd-operating" name="us-gaap:OperatingIncomeLoss" contextRef="amd-q1" scale="6">1,476</ix:nonFraction></td></tr>
      <tr><td>Net cash provided by operating activities</td><td><ix:nonFraction id="amd-cfo" name="us-gaap:NetCashProvidedByUsedInOperatingActivities" contextRef="amd-q1" scale="6">2,955</ix:nonFraction></td></tr>
      <tr><td>Purchases of property and equipment</td><td>(</td><td><ix:nonFraction id="amd-capex" name="us-gaap:PaymentsToAcquirePropertyPlantAndEquipment" contextRef="amd-q1" scale="6">389</ix:nonFraction></td><td>)</td></tr>
    </table></body></html>
    """


def _amd_fetcher(calls: list[tuple[str, str]]):
    def fetch(url: str, user_agent: str) -> bytes:
        calls.append((url, user_agent))
        if "companyfacts" in url:
            return json.dumps(_amd_companyfacts()).encode("utf-8")
        if "submissions" in url:
            return json.dumps(_amd_submissions()).encode("utf-8")
        return _amd_filing().encode("utf-8")

    return fetch


def test_registry_contains_only_two_exact_reviewed_filings():
    assert tuple(CASH_GENERATION_PREVIEW_FILINGS) == ("NVDA", "AMD")
    nvda = CASH_GENERATION_PREVIEW_FILINGS["NVDA"]
    amd = CASH_GENERATION_PREVIEW_FILINGS["AMD"]
    assert (nvda.cik, nvda.accession, nvda.primary_document) == (
        "0001045810", "0001045810-26-000052", "nvda-20260426.htm"
    )
    assert (amd.cik, amd.fiscal_period, amd.period_start, amd.period_end) == (
        "0000002488", "2026-Q1", "2025-12-28", "2026-03-28"
    )
    assert (amd.accession, amd.primary_document, amd.as_of) == (
        "0000002488-26-000076", "amd-20260328.htm", "2026-07-20T23:59:59-04:00"
    )


def test_loader_uses_only_reviewed_nvidia_identity_and_composes_in_memory():
    calls: list[tuple[str, str]] = []

    result = load_company_workbench_cash_generation_preview(
        "NVDA",
        user_agent="Researcher research@example.com",
        fetcher=_fetcher(calls),
        retrieved_at="2026-07-20T23:00:00+00:00",
    )

    assert len(calls) == 3
    assert calls[0][0].endswith("/CIK0001045810.json")
    assert calls[1][0].endswith("/CIK0001045810.json")
    assert calls[2][0].endswith(
        "/1045810/000104581026000052/nvda-20260426.htm"
    )
    assert {user_agent for _url, user_agent in calls} == {
        "Researcher research@example.com"
    }
    assert result.status == "accepted_for_review"
    assert result.fiscal_period == "2027-Q1"
    assert result.free_cash_flow.value == 48_587_000_000
    assert result.production_activation is False
    assert result.readiness_promotions == ()
    assert result.persistence is False


def test_amd_loader_uses_exact_reviewed_identity_and_composes_in_memory():
    calls: list[tuple[str, str]] = []
    result = load_company_workbench_cash_generation_preview(
        "AMD",
        user_agent="Researcher research@example.com",
        fetcher=_amd_fetcher(calls),
        retrieved_at="2026-07-20T23:00:00+00:00",
    )
    assert [url for url, _agent in calls] == [
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000002488.json",
        "https://data.sec.gov/submissions/CIK0000002488.json",
        "https://www.sec.gov/Archives/edgar/data/2488/000000248826000076/amd-20260328.htm",
    ]
    assert result.status == "accepted_for_review"
    assert result.fiscal_period == "2026-Q1"
    assert result.free_cash_flow.value == 2_566_000_000
    assert result.operating_margin.status == "preview_available"
    assert result.fcf_margin.status == "preview_available"
    assert result.production_activation is False
    assert result.readiness_promotions == ()
    assert result.persistence is False


def test_unsupported_ticker_is_withheld_without_fetching():
    def unexpected_fetch(_url: str, _user_agent: str) -> bytes:
        raise AssertionError("unsupported ticker must not fetch")

    result = load_company_workbench_cash_generation_preview(
        "OTHER",
        user_agent="Researcher research@example.com",
        fetcher=unexpected_fetch,
    )

    assert result.status == "withheld"
    assert result.blockers == ("unsupported_preview_ticker:OTHER",)
    assert result.fiscal_period == ""
    assert result.accession == ""
    assert result.source_url == ""
    assert result.cutoff == ""
    assert result.operating_margin.value is None
    assert result.components == ()


def test_missing_sec_user_agent_is_converted_to_withheld_preview(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    result = load_company_workbench_cash_generation_preview("NVDA")

    assert result.status == "withheld"
    assert result.blockers == ("preview_load_blocked:SECUserAgentError",)
    assert result.free_cash_flow.value is None


def test_fetch_failure_is_converted_without_exposing_error_text():
    def failed_fetch(_url: str, _user_agent: str) -> bytes:
        raise ValueError("secret-bearing failure text")

    result = load_company_workbench_cash_generation_preview(
        "NVDA",
        user_agent="Researcher research@example.com",
        fetcher=failed_fetch,
    )

    assert result.status == "withheld"
    assert result.blockers == ("preview_load_blocked:ValueError",)
    assert "secret-bearing" not in str(result)


def test_blocked_exact_filing_never_returns_partial_values():
    calls: list[tuple[str, str]] = []
    base_fetcher = _fetcher(calls)

    def unsigned_capex_fetch(url: str, user_agent: str) -> bytes:
        payload = base_fetcher(url, user_agent)
        if url.endswith("nvda-20260426.htm"):
            return payload.replace(b"<td>(</td>", b"<td></td>").replace(
                b"<td>)</td>", b"<td></td>"
            )
        return payload

    result = load_company_workbench_cash_generation_preview(
        "NVDA",
        user_agent="Researcher research@example.com",
        fetcher=unsigned_capex_fetch,
        retrieved_at="2026-07-20T23:00:00+00:00",
    )

    assert result.status == "withheld"
    assert "pilot_status:blocked" in result.blockers
    assert result.operating_margin.value is None
    assert result.free_cash_flow.value is None
    assert result.fcf_margin.value is None
    assert result.components == ()


def test_unsigned_amd_capex_withholds_complete_preview():
    calls: list[tuple[str, str]] = []
    base_fetcher = _amd_fetcher(calls)

    def unsigned_fetch(url: str, user_agent: str) -> bytes:
        payload = base_fetcher(url, user_agent)
        if url.endswith("amd-20260328.htm"):
            return payload.replace(b"<td>(</td>", b"<td></td>").replace(
                b"<td>)</td>", b"<td></td>"
            )
        return payload

    result = load_company_workbench_cash_generation_preview(
        "AMD",
        user_agent="Researcher research@example.com",
        fetcher=unsigned_fetch,
        retrieved_at="2026-07-20T23:00:00+00:00",
    )
    assert result.status == "withheld"
    assert result.operating_margin.value is None
    assert result.free_cash_flow.value is None
    assert result.fcf_margin.value is None
    assert result.components == ()


def test_loader_has_no_writer_broad_collection_or_apply_surface():
    parameters = inspect.signature(
        load_company_workbench_cash_generation_preview
    ).parameters
    source = Path(
        "src/company_workbench_cash_generation_preview_loader.py"
    ).read_text(encoding="utf-8")

    assert set(parameters) == {"ticker", "user_agent", "fetcher", "retrieved_at"}
    for forbidden_parameter in (
        "output",
        "apply",
        "refresh",
        "readiness",
        "accession",
        "cik",
        "filing",
        "cutoff",
    ):
        assert forbidden_parameter not in parameters
    for forbidden_source in (
        "argparse",
        "Path(",
        "open(",
        "to_csv",
        "to_json",
        "output_dir",
        "yfinance",
        "fixture",
    ):
        assert forbidden_source not in source
