"""Exact-source packet regression tests use synthetic SEC payloads only."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

import src.sec_cash_generation_evidence_packet as packet_module
from src.cohort_field_evidence import DEFAULT_TICKERS, FIELDS, SCHEMA_VERSION as COHORT_SCHEMA
from src.commercial_source_rights import load_source_rights_registry
from src.sec_cash_generation_evidence_packet import (
    PINNED_SOURCE_URLS,
    SCHEMA_VERSION,
    build_packet_from_bytes,
    capture_exact_sec_sources,
    load_exact_sec_capture,
)


ACCESSION = "0001045810-26-000052"
START = "2026-01-26"
END = "2026-04-26"
OBSERVED = "2026-10-27T02:30:00Z"


def _fact(value: int, *, filed: str = "2026-05-20", unit: str = "USD") -> dict:
    return {
        "start": START, "end": END, "val": value, "accn": ACCESSION,
        "fy": 2027, "fp": "Q1", "form": "10-Q", "filed": filed,
        "unit": unit,
    }


def _payloads() -> dict[str, bytes]:
    # Fabricated component values and HTML; never a saved SEC response.
    facts = {
        "cik": 1045810, "entityName": "NVIDIA CORP",
        "facts": {"us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"USD": [_fact(12_000_000_000)]}},
            "OperatingIncomeLoss": {"units": {"USD": [_fact(7_000_000_000)]}},
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {"USD": [_fact(6_000_000_000)]}},
            "PaymentsToAcquireProductiveAssets": {
                "units": {"USD": [_fact(1_000_000_000)]}},
        }},
    }
    submissions = {
        "cik": "0001045810", "tickers": ["NVDA"],
        "filings": {"recent": {
            "accessionNumber": [ACCESSION], "filingDate": ["2026-05-20"],
            "acceptanceDateTime": ["2026-05-20T20:35:52.000Z"],
            "form": ["10-Q"], "primaryDocument": ["nvda-20260426.htm"],
        }},
    }
    filing = f"""
    <html><body>
      <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
      <xbrli:context id="q1"><xbrli:period><xbrli:startDate>{START}</xbrli:startDate><xbrli:endDate>{END}</xbrli:endDate></xbrli:period></xbrli:context>
      <table>
        <tr><td>Revenue</td><td><ix:nonFraction id="f-revenue" name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="q1" unitRef="usd" scale="6">12,000</ix:nonFraction></td></tr>
        <tr><td>Operating income</td><td><ix:nonFraction id="f-operating" name="us-gaap:OperatingIncomeLoss" contextRef="q1" unitRef="usd" scale="6">7,000</ix:nonFraction></td></tr>
        <tr><td>Net cash provided by operating activities</td><td><ix:nonFraction id="f-cfo" name="us-gaap:NetCashProvidedByUsedInOperatingActivities" contextRef="q1" unitRef="usd" scale="6">6,000</ix:nonFraction></td></tr>
        <tr><td>Purchases related to property and equipment and intangible assets</td><td>(</td><td><ix:nonFraction id="f-capex" name="us-gaap:PaymentsToAcquireProductiveAssets" contextRef="q1" unitRef="usd" scale="6">1,000</ix:nonFraction></td><td>)</td></tr>
      </table>
    </body></html>
    """
    return {
        "companyfacts": json.dumps(facts).encode(),
        "submissions": json.dumps(submissions).encode(),
        "filing": filing.encode(),
    }


def _cohort() -> dict:
    rows = []
    for ticker in DEFAULT_TICKERS:
        for field in FIELDS:
            row = {
                "ticker": ticker, "field": field, "value": "", "source": "",
                "source_ref": "", "period_end": "", "source_published_at": "",
                "observation_date": "", "rights_status": "source_unidentified",
                "registered_field_scope": False,
                "withheld_reasons": ["saved_field_missing"],
                "interpretation_state": "withheld",
            }
            if ticker == "NVDA" and field in {
                "revenue", "operating_income", "cash_from_operations",
                "capital_expenditures", "free_cash_flow", "fcf_margin",
            }:
                row.update({
                    "value": "100000000.0" if field == "revenue" else "",
                    "source": "sec_companyfacts",
                    "source_ref": "0001045810-26-000021",
                    "period_end": "2026-01-25",
                    "source_published_at": "2026-02-25",
                    "withheld_reasons": ["field_specific_proof_missing"],
                })
            rows.append(row)
    return {
        "schema_version": COHORT_SCHEMA, "tickers": list(DEFAULT_TICKERS),
        "snapshot_identity": "a" * 64, "fields": rows,
        "inspection_only": True, "canonical_writes": False,
    }


def _build(*, payloads=None, cohort=None, rights=None, as_of="2026-10-27T23:59:59Z"):
    return build_packet_from_bytes(
        raw_sources=payloads if payloads is not None else _payloads(),
        observed_at_by_source={key: OBSERVED for key in PINNED_SOURCE_URLS},
        as_of=as_of,
        rights_registry=rights if rights is not None else load_source_rights_registry(),
        saved_cohort=cohort if cohort is not None else _cohort(),
    )


def test_packet_binds_three_byte_receipts_exact_components_and_separate_saved_period():
    raw = _payloads()
    packet = _build(payloads=raw)

    assert packet["schema_version"] == SCHEMA_VERSION
    assert packet["status"] == "accepted_for_review"
    assert packet["blockers"] == []
    assert packet["evidence_review_cutoff"] == "2026-10-27T23:59:59+00:00"
    assert packet["cutoff_basis"] == "SEC publication and source observations at or before review cutoff"
    assert packet["source_observed_after_cutoff"] is False
    assert packet["inspection_only"] is True
    assert packet["production_activation"] is False
    assert packet["readiness_promotions"] == []
    assert packet["identity"]["ticker"] == "NVDA"
    assert packet["identity"]["accession"] == ACCESSION
    assert packet["identity"]["period_start_date"] == START
    assert packet["identity"]["period_end_date"] == END
    assert packet["identity"]["filing_date"] == "2026-05-20"
    assert packet["identity"]["accepted_at"] == "2026-05-20T20:35:52+00:00"
    assert {row["name"] for row in packet["source_receipts"]} == set(PINNED_SOURCE_URLS)
    for receipt in packet["source_receipts"]:
        assert receipt["url"] == PINNED_SOURCE_URLS[receipt["name"]]
        assert receipt["sha256"] == hashlib.sha256(raw[receipt["name"]]).hexdigest()
        assert receipt["byte_length"] == len(raw[receipt["name"]])
        assert receipt["observed_at_utc"] == "2026-10-27T02:30:00+00:00"
    proofs = {row["field"]: row for row in packet["components"]}
    assert len(proofs) == 4
    assert proofs["revenue"]["concept"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert proofs["revenue"]["companyfacts_filed_date"] == "2026-05-20"
    assert proofs["revenue"]["inline_fact_id"] == "f-revenue"
    assert proofs["revenue"]["inline_unit"] == "USD"
    assert proofs["revenue"]["inline_scale"] == 6
    assert proofs["revenue"]["source_published_at"] == "2026-05-20T20:35:52+00:00"
    assert proofs["revenue"]["definition"] == ["USD", 1.0, "reported", "three_months"]
    assert proofs["capital_expenditures"]["raw_value"] == 1_000_000_000.0
    assert proofs["capital_expenditures"]["normalized_value"] == -1_000_000_000.0
    assert proofs["capital_expenditures"]["explicit_outflow"] is True
    assert all(row["registered_field_scope"] for row in packet["components"])
    assert {row["field"] for row in packet["derived_withheld"]} == {
        "free_cash_flow", "fcf_margin"
    }
    assert all(row["reason"] == "derived_field_not_registered" for row in packet["derived_withheld"])
    assert packet["saved_comparison"]["cohort_snapshot_identity"] == "a" * 64
    assert len(packet["saved_comparison"]["fields"]) == 6
    assert all(row["relationship"] == "different_period_and_accession" for row in packet["saved_comparison"]["fields"])
    assert all(row["saved_interpretation_state"] == "withheld" for row in packet["saved_comparison"]["fields"])


def test_capture_uses_only_three_pinned_urls_and_observes_each_exact_response():
    raw = _payloads()
    requested = []
    times = iter([
        "2026-10-27T02:30:00Z", "2026-10-27T02:30:01Z", "2026-10-27T02:30:02Z"
    ])

    def fetch(url, user_agent):
        requested.append((url, user_agent))
        name = next(name for name, candidate in PINNED_SOURCE_URLS.items() if candidate == url)
        return raw[name]

    captured = capture_exact_sec_sources(user_agent="Stock Research Test research@example.com", fetcher=fetch, clock=lambda: next(times))

    assert [url for url, _agent in requested] == list(PINNED_SOURCE_URLS.values())
    assert captured.raw_sources == raw
    assert captured.observed_at_by_source == {
        "companyfacts": "2026-10-27T02:30:00+00:00",
        "submissions": "2026-10-27T02:30:01+00:00",
        "filing": "2026-10-27T02:30:02+00:00",
    }


def test_saved_capture_replays_exact_bytes_and_rejects_digest_or_url_drift(tmp_path):
    local = tmp_path / "outputs" / "local"
    capture = local / "nvda"
    capture.mkdir(parents=True)
    raw = _payloads()
    names = {
        "companyfacts": "companyfacts.json", "submissions": "submissions.json",
        "filing": "primary_filing.html",
    }
    receipts = []
    for name, url in PINNED_SOURCE_URLS.items():
        (capture / names[name]).write_bytes(raw[name])
        receipts.append({
            "name": name, "url": url, "sha256": hashlib.sha256(raw[name]).hexdigest(),
            "byte_length": len(raw[name]), "observed_at_utc": OBSERVED,
        })
    (capture / "manifest.json").write_text(json.dumps({"source_receipts": receipts}))

    replay = load_exact_sec_capture(capture, allowed_root=local)
    assert replay.raw_sources == raw
    assert replay.observed_at_by_source == {
        name: "2026-10-27T02:30:00+00:00" for name in PINNED_SOURCE_URLS
    }
    assert build_packet_from_bytes(
        raw_sources=replay.raw_sources,
        observed_at_by_source=replay.observed_at_by_source,
        as_of="2026-10-27T23:59:59Z",
        rights_registry=load_source_rights_registry(),
        saved_cohort=_cohort(),
    )["status"] == "accepted_for_review"

    (capture / names["filing"]).write_bytes(raw["filing"] + b"tamper")
    with pytest.raises(ValueError, match="filing:receipt_digest_mismatch"):
        load_exact_sec_capture(capture, allowed_root=local)
    (capture / names["filing"]).write_bytes(raw["filing"])
    receipts[0]["url"] = "https://example.invalid/wrong"
    (capture / "manifest.json").write_text(json.dumps({"source_receipts": receipts}))
    with pytest.raises(ValueError, match="companyfacts:receipt_url_mismatch"):
        load_exact_sec_capture(capture, allowed_root=local)
    receipts[0]["url"] = PINNED_SOURCE_URLS["companyfacts"]
    receipts[0]["name"] = ["companyfacts"]
    (capture / "manifest.json").write_text(json.dumps({"source_receipts": receipts}))
    with pytest.raises(ValueError, match="source_receipt_scope_invalid"):
        load_exact_sec_capture(capture, allowed_root=local)
    with pytest.raises(ValueError, match="source_dir_must_be_under_ignored_outputs_local"):
        load_exact_sec_capture(tmp_path, allowed_root=local)


def test_packet_blocks_source_observed_after_review_cutoff():
    packet = _build(as_of="2026-10-27T02:29:59Z")

    assert packet["status"] == "blocked"
    assert packet["evidence_review_cutoff"] == "2026-10-27T02:29:59+00:00"
    assert packet["source_observed_after_cutoff"] is True
    assert "source_observed_after_cutoff" in packet["blockers"]


def test_cli_replays_verified_capture_without_live_fetch(tmp_path, monkeypatch, capsys):
    saved = tmp_path / "cohort.json"
    saved.write_text(json.dumps(_cohort()))
    captured = packet_module.CapturedSecSources(
        raw_sources=_payloads(),
        observed_at_by_source={name: OBSERVED for name in PINNED_SOURCE_URLS},
    )
    monkeypatch.setattr(packet_module, "load_exact_sec_capture", lambda _path: captured)

    def never_fetch(**_kwargs):
        raise AssertionError("live SEC fetch was attempted during replay")

    monkeypatch.setattr(packet_module, "capture_exact_sec_sources", never_fetch)
    result = packet_module.main([
        "--as-of", "2026-10-27T23:59:59Z",
        "--saved-cohort", str(saved),
        "--source-dir", str(tmp_path / "ignored-capture"),
    ])

    assert result == 0
    assert json.loads(capsys.readouterr().out)["status"] == "accepted_for_review"


@pytest.mark.parametrize("mutation,blocker", [
    ("wrong_companyfacts_cik", "companyfacts:cik_mismatch"),
    ("wrong_submissions_cik", "submissions:cik_mismatch"),
    ("wrong_ticker", "submissions:ticker_mismatch"),
    ("wrong_accession", "submissions:accession_missing"),
    ("wrong_period", "revenue:fact_missing"),
    ("conflicting_concept", "revenue:concept_conflict"),
    ("wrong_filed_date", "revenue:filing_date_mismatch"),
    ("wrong_companyfacts_unit", "revenue:unit_conflict"),
    ("wrong_inline_unit", "revenue:inline_unit_mismatch"),
    ("wrong_inline_value", "revenue:inline_fact_missing"),
    ("missing_outflow", "capital_expenditures:explicit_outflow_evidence_missing"),
])
def test_packet_rejects_source_conflicts(mutation, blocker):
    raw = _payloads()
    facts = json.loads(raw["companyfacts"])
    submissions = json.loads(raw["submissions"])
    filing = raw["filing"].decode()
    if mutation == "wrong_companyfacts_cik":
        facts["cik"] = 12345
    elif mutation == "wrong_submissions_cik":
        submissions["cik"] = "0000001234"
    elif mutation == "wrong_ticker":
        submissions["tickers"] = ["OTHER"]
    elif mutation == "wrong_accession":
        submissions["filings"]["recent"]["accessionNumber"] = ["0001045810-26-999999"]
    elif mutation == "wrong_period":
        facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"][0]["start"] = "2026-01-01"
    elif mutation == "conflicting_concept":
        facts["facts"]["us-gaap"]["Revenues"] = {"units": {"USD": [_fact(1)]}}
    elif mutation == "wrong_filed_date":
        facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"][0]["filed"] = "2026-05-21"
    elif mutation == "wrong_companyfacts_unit":
        item = facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]
        item["units"]["EUR"] = item["units"].pop("USD")
    elif mutation == "wrong_inline_unit":
        filing = filing.replace('id="f-revenue" name=', 'id="f-revenue" name=').replace('contextRef="q1" unitRef="usd" scale="6">12,000', 'contextRef="q1" unitRef="eur" scale="6">12,000')
    elif mutation == "wrong_inline_value":
        filing = filing.replace(">12,000</ix:nonFraction>", ">12,001</ix:nonFraction>")
    elif mutation == "missing_outflow":
        filing = filing.replace("<td>(</td>", "<td></td>").replace("<td>)</td>", "<td></td>")
    raw = {"companyfacts": json.dumps(facts).encode(), "submissions": json.dumps(submissions).encode(), "filing": filing.encode()}

    packet = _build(payloads=raw)

    assert packet["status"] == "blocked"
    assert blocker in packet["blockers"]
    assert packet["production_activation"] is False
    assert packet["readiness_promotions"] == []


def test_packet_rejects_cutoff_rights_and_invalid_saved_scope():
    cutoff = _build(as_of="2026-05-20T20:35:51Z")
    assert cutoff["status"] == "blocked"
    assert "acceptance_after_cutoff" in cutoff["blockers"]

    from src.commercial_source_rights import build_source_rights_registry

    registry = load_source_rights_registry()
    record = registry["sec_companyfacts"]
    removed = {"source_id": record.source_id, "display_name": record.display_name,
        "permitted_use": record.permitted_use, "commercial_use": record.commercial_use,
        "redistribution": record.redistribution, "storage_limits": record.storage_limits,
        "attribution": record.attribution, "rate_limits": record.rate_limits,
        "authentication": record.authentication, "expected_freshness": record.expected_freshness,
        "supported_fields": ["revenue"], "fallback_priority": record.fallback_priority}
    blocked_rights = _build(rights=build_source_rights_registry([removed]))
    assert blocked_rights["status"] == "blocked"
    assert any(item.startswith("source_fields_missing:") for item in blocked_rights["blockers"])

    cohort = _cohort()
    cohort["fields"].append(deepcopy(cohort["fields"][0]))
    blocked_scope = _build(cohort=cohort)
    assert blocked_scope["status"] == "blocked"
    assert "saved_cohort:scope_invalid" in blocked_scope["blockers"]

    malformed = _cohort()
    malformed["fields"][0]["field"] = ["revenue"]
    malformed_scope = _build(cohort=malformed)
    assert malformed_scope["status"] == "blocked"
    assert "saved_cohort:scope_invalid" in malformed_scope["blockers"]


@pytest.mark.parametrize("mutation", [
    "facts_list", "taxonomy_list", "concept_list", "units_list", "rows_mapping", "row_list",
])
def test_packet_blocks_malformed_companyfacts_nesting(mutation):
    raw = _payloads()
    facts = json.loads(raw["companyfacts"])
    if mutation == "facts_list":
        facts["facts"] = []
    elif mutation == "taxonomy_list":
        facts["facts"]["us-gaap"] = []
    else:
        concept = facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]
        if mutation == "concept_list":
            facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"] = []
        elif mutation == "units_list":
            concept["units"] = []
        elif mutation == "rows_mapping":
            concept["units"]["USD"] = {"unexpected": "row"}
        else:
            concept["units"]["USD"][0] = []
    raw["companyfacts"] = json.dumps(facts).encode()

    packet = _build(payloads=raw)

    assert packet["status"] == "blocked"
    assert "source_payload_invalid:ValueError" in packet["blockers"]
    assert packet["components"] == []


def test_packet_blocks_malformed_saved_withheld_reasons():
    cohort = _cohort()
    next(row for row in cohort["fields"] if row["ticker"] == "NVDA" and row["field"] == "revenue")["withheld_reasons"] = 1

    packet = _build(cohort=cohort)

    assert packet["status"] == "blocked"
    assert "saved_cohort:scope_invalid" in packet["blockers"]
    assert packet["saved_comparison"]["fields"] == []


@pytest.mark.parametrize("mutation", [
    "filings_list", "filings_null", "recent_list", "recent_null", "accessions_null",
])
def test_packet_blocks_malformed_submissions_nesting(mutation):
    raw = _payloads()
    submissions = json.loads(raw["submissions"])
    if mutation == "filings_list":
        submissions["filings"] = []
    elif mutation == "filings_null":
        submissions["filings"] = None
    elif mutation == "recent_list":
        submissions["filings"]["recent"] = []
    elif mutation == "recent_null":
        submissions["filings"]["recent"] = None
    else:
        submissions["filings"]["recent"]["accessionNumber"] = None
    raw["submissions"] = json.dumps(submissions).encode()

    packet = _build(payloads=raw)

    assert packet["status"] == "blocked"
    assert "submissions:accession_missing" in packet["blockers"]
    assert packet["production_activation"] is False
