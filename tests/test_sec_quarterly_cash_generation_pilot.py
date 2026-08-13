from copy import deepcopy

import pytest

from src.commercial_source_rights import build_source_rights_registry
from src.sec_quarterly_cash_generation_pilot import (
    extract_sec_quarterly_cash_generation,
    preview_sec_quarterly_cash_generation,
)


ACCESSION = "0001045810-26-000052"
START = "2026-01-26"
END = "2026-04-26"


def _fact(value: float, *, filed: str = "2026-05-20") -> dict[str, object]:
    return {
        "start": START,
        "end": END,
        "val": value,
        "accn": ACCESSION,
        "fy": 2027,
        "fp": "Q1",
        "form": "10-Q",
        "filed": filed,
    }


def _companyfacts_fixture() -> dict[str, object]:
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


def _submissions_fixture() -> dict[str, object]:
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


def _filing_fixture() -> str:
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


def _extract(
    *,
    companyfacts_payload: dict[str, object] | None = None,
    submissions_payload: dict[str, object] | None = None,
    filing_html: str | None = None,
    as_of: str = "2026-07-20T15:00:00+00:00",
    fiscal_period: str = "2027-Q1",
    period_start_date: str = START,
    period_end_date: str = END,
):
    return extract_sec_quarterly_cash_generation(
        ticker="NVDA",
        cik="0001045810",
        fiscal_period=fiscal_period,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        accession=ACCESSION,
        companyfacts_payload=companyfacts_payload or _companyfacts_fixture(),
        submissions_payload=submissions_payload or _submissions_fixture(),
        filing_html=filing_html or _filing_fixture(),
        retrieved_at="2026-07-20T15:00:00+00:00",
        as_of=as_of,
    )


def _rights_registry(*, include_cash_fields: bool):
    supported_fields = ["revenue", "filing_dates"]
    if include_cash_fields:
        supported_fields.extend(
            ["operating_income", "cash_from_operations", "capital_expenditures"]
        )
    return build_source_rights_registry(
        [
            {
                "source_id": "sec_companyfacts",
                "display_name": "SEC Companyfacts test record",
                "permitted_use": "source_backed_company_facts",
                "commercial_use": "approved",
                "redistribution": "derived_data_only",
                "storage_limits": "in_memory_test_only",
                "attribution": "SEC EDGAR test fixture",
                "rate_limits": "not_applicable_test_only",
                "authentication": "SEC_USER_AGENT",
                "expected_freshness": "filing_driven",
                "supported_fields": supported_fields,
                "fallback_priority": 1,
            }
        ]
    )


def test_exact_q1_payload_builds_source_backed_components_and_revenue():
    result = _extract()

    assert result.blockers == ()
    assert result.accepted_at == "2026-05-20T20:35:52+00:00"
    assert [row.metric for row in result.observations] == [
        "operating_income",
        "cash_from_operations",
        "capital_expenditures",
    ]
    assert [row.value for row in result.observations] == [
        53_536_000_000.0,
        50_344_000_000.0,
        -1_757_000_000.0,
    ]
    assert result.revenue_actuals[0].revenue_actual == 81_615_000_000.0
    assert result.capex_sign_evidence == "explicit_filed_table_outflow"
    assert result.source_url.endswith("/nvda-20260426.htm")


def test_unsigned_capex_is_blocked_instead_of_inferred():
    result = _extract(filing_html=_filing_fixture().replace("<td>(</td>", "<td></td>").replace("<td>)</td>", "<td></td>"))

    assert result.blockers == (
        "capital_expenditures:explicit_outflow_evidence_missing",
    )
    assert result.observations == ()
    assert result.revenue_actuals == ()


def test_wrong_inline_context_is_distinct_from_missing_outflow_presentation():
    filing = _filing_fixture().replace(
        'id="f-capex" name="us-gaap:PaymentsToAcquireProductiveAssets" contextRef="c-q1"',
        'id="f-capex" name="us-gaap:PaymentsToAcquireProductiveAssets" contextRef="c-other"',
    )

    result = _extract(filing_html=filing)

    assert result.blockers == ("capital_expenditures:inline_fact_missing",)


def test_conflicting_exact_companyfacts_values_are_ambiguous():
    payload = deepcopy(_companyfacts_fixture())
    rows = payload["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"]
    rows.append(_fact(50_000_000_000))

    result = _extract(companyfacts_payload=payload)

    assert result.blockers == ("cash_from_operations:fact_ambiguous",)


def test_identical_inline_duplicates_collapse_to_first_document_fact():
    filing = _filing_fixture().replace(
        "</table>",
        (
            '<tr><td>Repeated Revenue disclosure</td><td><ix:nonFraction '
            'id="f-revenue-duplicate" '
            'name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" '
            'contextRef="c-q1" scale="6">81,615</ix:nonFraction></td></tr>'
            "</table>"
        ),
    )

    result = _extract(filing_html=filing)

    assert result.blockers == ()
    assert result.revenue_actuals[0].source_ref.endswith("#f-revenue")


@pytest.mark.parametrize(
    ("acceptance_time", "as_of", "blocker"),
    [
        ("", "2026-07-20T15:00:00+00:00", "submissions:acceptance_time_invalid"),
        ("2026-05-20T20:35:52", "2026-07-20T15:00:00+00:00", "submissions:acceptance_time_invalid"),
        ("2026-05-20T20:35:52.000Z", "2026-05-20T20:35:51+00:00", "acceptance_after_cutoff"),
    ],
)
def test_acceptance_timestamp_fails_closed(acceptance_time, as_of, blocker):
    submissions = deepcopy(_submissions_fixture())
    submissions["filings"]["recent"]["acceptanceDateTime"] = [acceptance_time]

    result = _extract(submissions_payload=submissions, as_of=as_of)

    assert blocker in result.blockers
    assert result.observations == ()


def test_missing_accession_in_submissions_blocks_all_values():
    submissions = deepcopy(_submissions_fixture())
    submissions["filings"]["recent"]["accessionNumber"] = ["different"]

    result = _extract(submissions_payload=submissions)

    assert result.blockers == ("submissions:accession_missing",)
    assert result.observations == ()


def test_submissions_primary_document_must_match_requested_filing():
    result = extract_sec_quarterly_cash_generation(
        ticker="NVDA",
        cik="0001045810",
        fiscal_period="2027-Q1",
        period_start_date=START,
        period_end_date=END,
        accession=ACCESSION,
        primary_document="different-filing.htm",
        companyfacts_payload=_companyfacts_fixture(),
        submissions_payload=_submissions_fixture(),
        filing_html=_filing_fixture(),
        retrieved_at="2026-07-20T15:00:00+00:00",
        as_of="2026-07-20T15:00:00+00:00",
    )

    assert result.blockers == ("filing:primary_document_mismatch",)
    assert result.observations == ()


def test_payload_cik_must_match_requested_company():
    payload = deepcopy(_companyfacts_fixture())
    payload["cik"] = 1234

    result = _extract(companyfacts_payload=payload)

    assert result.blockers == ("companyfacts:cik_mismatch",)


def test_q4_ytd_facts_cannot_become_a_derived_quarter():
    result = _extract(
        fiscal_period="2027-Q4",
        period_start_date="2026-01-26",
        period_end_date="2027-01-31",
    )

    assert "q4_explicit_three_month_filing_required" in result.blockers
    assert result.observations == ()


def test_preview_composes_existing_acceptance_without_activation():
    preview = preview_sec_quarterly_cash_generation(
        extraction=_extract(),
        rights_registry=_rights_registry(include_cash_fields=True),
        as_of="2026-07-20T15:00:00+00:00",
    )

    assert preview.status == "accepted_for_review"
    assert preview.blockers == ()
    assert preview.acceptance is not None
    assert preview.acceptance.accepted_observation_count == 3
    assert preview.production_activation is False
    assert preview.readiness_promotions == ()


def test_extraction_and_rights_blockers_never_activate_preview():
    blocked_extraction = _extract(filing_html="<html></html>")
    extraction_preview = preview_sec_quarterly_cash_generation(
        extraction=blocked_extraction,
        rights_registry=_rights_registry(include_cash_fields=True),
    )
    rights_preview = preview_sec_quarterly_cash_generation(
        extraction=_extract(),
        rights_registry=_rights_registry(include_cash_fields=False),
    )

    assert extraction_preview.status == "blocked"
    assert extraction_preview.acceptance is None
    assert rights_preview.status == "blocked"
    assert "source_fields_missing:" in " ".join(rights_preview.blockers)
    assert rights_preview.production_activation is False
