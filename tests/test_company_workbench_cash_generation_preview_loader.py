from __future__ import annotations

import inspect
import json
from pathlib import Path

from src.company_workbench_cash_generation_preview_loader import (
    PREVIEW_ACCESSION,
    PREVIEW_AS_OF,
    PREVIEW_CIK,
    PREVIEW_FISCAL_PERIOD,
    PREVIEW_PERIOD_END,
    PREVIEW_PERIOD_START,
    PREVIEW_PRIMARY_DOCUMENT,
    load_company_workbench_cash_generation_preview,
)


START = "2026-01-26"
END = "2026-04-26"
ACCESSION = "0001045810-26-000052"


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


def test_loader_uses_only_reviewed_nvidia_identity_and_composes_in_memory():
    calls: list[tuple[str, str]] = []

    result = load_company_workbench_cash_generation_preview(
        "NVDA",
        user_agent="Researcher research@example.com",
        fetcher=_fetcher(calls),
        retrieved_at="2026-07-20T23:00:00+00:00",
    )

    assert PREVIEW_CIK == "0001045810"
    assert PREVIEW_ACCESSION == "0001045810-26-000052"
    assert PREVIEW_PRIMARY_DOCUMENT == "nvda-20260426.htm"
    assert PREVIEW_FISCAL_PERIOD == "2027-Q1"
    assert PREVIEW_PERIOD_START == "2026-01-26"
    assert PREVIEW_PERIOD_END == "2026-04-26"
    assert PREVIEW_AS_OF == "2026-07-20T23:59:59-04:00"
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


def test_non_nvidia_ticker_is_withheld_without_fetching():
    def unexpected_fetch(_url: str, _user_agent: str) -> bytes:
        raise AssertionError("unsupported ticker must not fetch")

    result = load_company_workbench_cash_generation_preview(
        "OTHER",
        user_agent="Researcher research@example.com",
        fetcher=unexpected_fetch,
    )

    assert result.status == "withheld"
    assert result.blockers == ("unsupported_preview_ticker:OTHER",)
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
