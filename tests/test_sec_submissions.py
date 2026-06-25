from pathlib import Path

import pytest

from src.providers.sec_submissions import (
    SEC_SUBMISSIONS_URL_TEMPLATE,
    build_sec_submission_metadata,
    fetch_sec_submission,
    sec_submission_url,
)


def _sample_submission_payload() -> dict[str, object]:
    return {
        "cik": "1045810",
        "name": "NVIDIA CORP",
        "sic": "3674",
        "sicDescription": "Semiconductors and Related Devices",
        "fiscalYearEnd": "0128",
        "tickers": ["NVDA"],
        "exchanges": ["Nasdaq"],
        "filings": {
            "recent": {
                "accessionNumber": ["0001045810-26-000021", "0001045810-25-000023"],
                "filingDate": ["2026-02-25", "2025-02-26"],
                "reportDate": ["2026-01-25", "2025-01-26"],
                "form": ["10-K", "10-K"],
            }
        },
    }


def test_sec_submission_url_zero_pads_cik():
    assert sec_submission_url("1045810") == SEC_SUBMISSIONS_URL_TEMPLATE.format(cik="0001045810")


def test_build_sec_submission_metadata_maps_entity_industry_and_latest_filing():
    metadata = build_sec_submission_metadata(_sample_submission_payload())

    assert metadata["sec_cik"] == "0001045810"
    assert metadata["sec_entity_name"] == "NVIDIA CORP"
    assert metadata["sec_sic"] == "3674"
    assert metadata["sec_sic_description"] == "Semiconductors and Related Devices"
    assert metadata["sec_fiscal_year_end"] == "0128"
    assert metadata["sec_tickers"] == "NVDA"
    assert metadata["sec_exchanges"] == "Nasdaq"
    assert metadata["sec_latest_form"] == "10-K"
    assert metadata["sec_latest_filing_date"] == "2026-02-25"
    assert metadata["sec_latest_accession"] == "0001045810-26-000021"
    assert metadata["sec_recent_filing_count"] == 2
    assert metadata["source"] == "sec_submissions_metadata"
    assert metadata["source_usage"] == "metadata_evidence_only"


def test_fetch_sec_submission_uses_cache_when_available(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    first_payload = _sample_submission_payload()
    fetched_payload = {
        **first_payload,
        "name": "SHOULD NOT BE USED",
    }

    calls = []

    def fetcher(_url: str, _user_agent: str, _sleep_seconds: float):
        calls.append(_url)
        return first_payload

    payload = fetch_sec_submission(
        "1045810",
        "Research Tester test@example.com",
        cache_dir=cache_dir,
        fetcher=fetcher,
    )
    assert payload["name"] == "NVIDIA CORP"
    assert calls == [SEC_SUBMISSIONS_URL_TEMPLATE.format(cik="0001045810")]

    def should_not_fetch(*_args, **_kwargs):
        raise AssertionError(fetched_payload)

    cached = fetch_sec_submission(
        "1045810",
        "Research Tester test@example.com",
        cache_dir=cache_dir,
        fetcher=should_not_fetch,
    )
    assert cached["name"] == "NVIDIA CORP"


def test_fetch_sec_submission_requires_user_agent(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(ValueError, match="SEC requests require"):
        fetch_sec_submission("1045810", user_agent=None)
