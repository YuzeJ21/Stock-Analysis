from pathlib import Path

import pytest

from src.providers.sec_submissions import (
    SEC_SUBMISSIONS_URL_TEMPLATE,
    build_sec_filing_share_count_evidence,
    build_sec_submission_metadata_packet,
    build_sec_submission_metadata,
    extract_filing_exhibits,
    extract_share_count_from_inline_xbrl,
    fetch_sec_submission,
    latest_filing_document,
    sec_filing_index_url,
    sec_filing_document_url,
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
                "primaryDocument": ["nvda-20260125.htm", "nvda-20250126.htm"],
                "form": ["10-K", "10-K"],
            }
        },
    }


def test_sec_submission_url_zero_pads_cik():
    assert sec_submission_url("1045810") == SEC_SUBMISSIONS_URL_TEMPLATE.format(cik="0001045810")


def test_sec_filing_index_url_uses_archive_accession_path():
    assert sec_filing_index_url("0001045810", "0001045810-26-000021") == (
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.html"
    )


def test_extract_filing_exhibits_discovers_explicit_ex_99_links():
    index_html = """
    <table>
      <tr><th>Document</th><th>Description</th><th>Type</th></tr>
      <tr><td><a href="nvda-ex991.htm">nvda-ex991.htm</a></td><td>Earnings release</td><td>EX-99.1</td></tr>
      <tr><td><a href="not-an-exhibit.htm">not-an-exhibit.htm</a></td><td>Primary</td><td>8-K</td></tr>
    </table>
    """

    exhibits = extract_filing_exhibits(index_html, cik="0001045810", accession="0001045810-26-000021")

    assert len(exhibits) == 1
    assert exhibits[0].document_type == "EX-99.1"
    assert exhibits[0].document_name == "nvda-ex991.htm"
    assert exhibits[0].source_ref == (
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-ex991.htm"
    )


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


def test_build_sec_submission_metadata_packet_uses_cached_submission_without_network(tmp_path: Path):
    cache_path = tmp_path / "cache" / "submissions" / "CIK0001045810.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(
        __import__("json").dumps(_sample_submission_payload()),
        encoding="utf-8",
    )

    packet = build_sec_submission_metadata_packet(
        "NVDA",
        ticker_map={"NVDA": {"ticker": "NVDA", "cik": "0001045810"}},
        cache_dir=tmp_path / "cache",
        allow_network=False,
    )

    assert packet["status"] == "available"
    assert packet["source"] == "sec_submissions_metadata"
    assert packet["source_usage"] == "metadata_evidence_only"
    assert packet["ticker"] == "NVDA"
    assert packet["sec_cik"] == "0001045810"
    assert packet["ticker_validation"] == "matched_sec_submission_tickers"
    assert packet["sec_entity_name"] == "NVIDIA CORP"
    assert packet["sec_sic_description"] == "Semiconductors and Related Devices"
    assert packet["sec_latest_form"] == "10-K"
    assert packet["sec_latest_filing_date"] == "2026-02-25"
    assert "does not unlock fundamentals" in packet["proof_boundary"]


def test_build_sec_submission_metadata_packet_resolves_dot_class_alias(tmp_path: Path):
    payload = {
        **_sample_submission_payload(),
        "cik": "1067983",
        "name": "BERKSHIRE HATHAWAY INC",
        "tickers": ["BRK-B"],
    }
    cache_path = tmp_path / "cache" / "submissions" / "CIK0001067983.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    packet = build_sec_submission_metadata_packet(
        "BRK.B",
        ticker_map={"BRK-B": {"ticker": "BRK-B", "cik": "0001067983"}},
        cache_dir=tmp_path / "cache",
        allow_network=False,
    )

    assert packet["status"] == "available"
    assert packet["ticker"] == "BRK.B"
    assert packet["sec_cik"] == "0001067983"
    assert packet["sec_tickers"] == "BRK-B"
    assert packet["ticker_validation"] == "matched_sec_submission_tickers"


def test_build_sec_submission_metadata_packet_reports_missing_cache_without_remote_retry(tmp_path: Path):
    packet = build_sec_submission_metadata_packet(
        "NVDA",
        ticker_map={"NVDA": {"ticker": "NVDA", "cik": "0001045810"}},
        cache_dir=tmp_path / "cache",
        allow_network=False,
    )

    assert packet["status"] == "unavailable"
    assert packet["reason_code"] == "cached_submission_missing"
    assert packet["source_usage"] == "metadata_evidence_only"
    assert "No cached SEC submissions metadata" in packet["detail"]


def test_latest_filing_document_builds_sec_archive_url():
    filing = latest_filing_document(_sample_submission_payload())

    assert filing["sec_cik"] == "0001045810"
    assert filing["form"] == "10-K"
    assert filing["filing_date"] == "2026-02-25"
    assert filing["accession"] == "0001045810-26-000021"
    assert filing["primary_document"] == "nvda-20260125.htm"
    assert filing["document_url"] == sec_filing_document_url(
        "0001045810",
        "0001045810-26-000021",
        "nvda-20260125.htm",
    )
    assert "/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm" in filing["document_url"]


def test_latest_filing_document_can_prefer_share_count_capable_forms():
    payload = _sample_submission_payload()
    payload["filings"]["recent"] = {
        "accessionNumber": ["0001045810-26-000077", "0001045810-26-000021"],
        "filingDate": ["2026-06-25", "2026-02-25"],
        "reportDate": ["2026-06-22", "2026-01-25"],
        "primaryDocument": ["nvda-20260622.htm", "nvda-20260125.htm"],
        "form": ["8-K", "10-K"],
    }

    latest_any = latest_filing_document(payload)
    latest_share_count_form = latest_filing_document(payload, preferred_forms=("10-K", "10-Q"))

    assert latest_any["form"] == "8-K"
    assert latest_share_count_form["form"] == "10-K"
    assert latest_share_count_form["primary_document"] == "nvda-20260125.htm"


def test_extract_share_count_from_inline_xbrl_requires_explicit_dei_fact():
    document = """
    <html>
      <ix:nonFraction name="dei:EntityCommonStockSharesOutstanding"
          contextRef="c1" unitRef="shares" decimals="0">136,414,409</ix:nonFraction>
    </html>
    """

    evidence = extract_share_count_from_inline_xbrl(document)

    assert evidence["status"] == "available"
    assert evidence["source"] == "sec_filing_document"
    assert evidence["source_usage"] == "share_count_evidence_only"
    assert evidence["shares_outstanding"] == 136414409
    assert evidence["sec_fact_name"] == "dei:EntityCommonStockSharesOutstanding"
    assert evidence["sec_fact_context"] == "c1"
    assert evidence["sec_fact_unit"] == "shares"
    assert "does not unlock DCF" in evidence["proof_boundary"]


def test_extract_share_count_from_inline_xbrl_applies_explicit_scale():
    document = """
    <ix:nonFraction name="dei:EntityCommonStockSharesOutstanding"
      contextRef="c1" unitRef="shares" scale="3">136,414</ix:nonFraction>
    """

    evidence = extract_share_count_from_inline_xbrl(document)

    assert evidence["shares_outstanding"] == 136414000
    assert evidence["sec_fact_scale"] == "3"


def test_extract_share_count_from_inline_xbrl_reports_missing_explicit_fact():
    evidence = extract_share_count_from_inline_xbrl("<html><body>No share-count fact here.</body></html>")

    assert evidence["status"] == "unavailable"
    assert evidence["reason_code"] == "explicit_share_count_fact_missing"
    assert "EntityCommonStockSharesOutstanding" in evidence["detail"]


def test_build_sec_filing_share_count_evidence_uses_cached_document(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    submission_path = cache_dir / "submissions" / "CIK0001045810.json"
    document_path = cache_dir / "filing_documents" / "CIK0001045810" / "000104581026000021" / "nvda-20260125.htm"
    submission_path.parent.mkdir(parents=True)
    document_path.parent.mkdir(parents=True)
    submission_path.write_text(__import__("json").dumps(_sample_submission_payload()), encoding="utf-8")
    document_path.write_text(
        '<ix:nonFraction name="dei:EntityCommonStockSharesOutstanding" contextRef="c1" unitRef="shares">100</ix:nonFraction>',
        encoding="utf-8",
    )

    evidence = build_sec_filing_share_count_evidence(
        "NVDA",
        ticker_map={"NVDA": {"ticker": "NVDA", "cik": "0001045810"}},
        cache_dir=cache_dir,
        allow_network=False,
    )

    assert evidence["status"] == "available"
    assert evidence["ticker"] == "NVDA"
    assert evidence["sec_cik"] == "0001045810"
    assert evidence["shares_outstanding"] == 100
    assert evidence["sec_form"] == "10-K"
    assert evidence["sec_filed_date"] == "2026-02-25"
    assert evidence["sec_accession"] == "0001045810-26-000021"
    assert evidence["sec_primary_document"] == "nvda-20260125.htm"
    assert evidence["source"] == "sec_filing_document"
    assert evidence["source_usage"] == "share_count_evidence_only"


def test_build_sec_filing_share_count_evidence_resolves_dot_class_alias(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    payload = {
        **_sample_submission_payload(),
        "cik": "1067983",
        "name": "BERKSHIRE HATHAWAY INC",
        "tickers": ["BRK-B"],
    }
    submission_path = cache_dir / "submissions" / "CIK0001067983.json"
    document_path = cache_dir / "filing_documents" / "CIK0001067983" / "000104581026000021" / "nvda-20260125.htm"
    submission_path.parent.mkdir(parents=True)
    document_path.parent.mkdir(parents=True)
    submission_path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    document_path.write_text(
        '<ix:nonFraction name="dei:EntityCommonStockSharesOutstanding" contextRef="c1" unitRef="shares">100</ix:nonFraction>',
        encoding="utf-8",
    )

    evidence = build_sec_filing_share_count_evidence(
        "BRK.B",
        ticker_map={"BRK-B": {"ticker": "BRK-B", "cik": "0001067983"}},
        cache_dir=cache_dir,
        allow_network=False,
    )

    assert evidence["status"] == "available"
    assert evidence["ticker"] == "BRK.B"
    assert evidence["sec_cik"] == "0001067983"
    assert evidence["shares_outstanding"] == 100


def test_build_sec_filing_share_count_evidence_reports_missing_document_without_retry(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    submission_path = cache_dir / "submissions" / "CIK0001045810.json"
    submission_path.parent.mkdir(parents=True)
    submission_path.write_text(__import__("json").dumps(_sample_submission_payload()), encoding="utf-8")

    evidence = build_sec_filing_share_count_evidence(
        "NVDA",
        ticker_map={"NVDA": {"ticker": "NVDA", "cik": "0001045810"}},
        cache_dir=cache_dir,
        allow_network=False,
    )

    assert evidence["status"] == "unavailable"
    assert evidence["reason_code"] == "cached_filing_document_missing"
    assert "remote retry disabled" in evidence["detail"]
