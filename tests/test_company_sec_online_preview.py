"""Synthetic, no-network contracts for the Company Workbench SEC preview."""

from __future__ import annotations

import pytest

from src.company_sec_online_preview import (
    company_sec_annual_preview_html,
    get_company_sec_annual_preview,
    present_company_sec_annual_preview,
)


def _synthetic_preview() -> dict[str, object]:
    source_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json"
    accession = "0000001234-26-000001"
    source_ref = {
        "source_url": source_url,
        "retrieval_timestamp": "2026-10-29T19:00:00Z",
        "taxonomy": "us-gaap",
        "concept": "Revenues",
        "unit": "USD",
        "underlying_fact_unit": "USD",
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
        "filed": "2026-03-01",
        "form": "10-K",
        "accession": accession,
        "fiscal_year": 2025,
        "fiscal_period": "FY",
    }

    return {
        "status": "inspection_only",
        "source": "sec_companyfacts",
        "requested_tickers": ["FICT"],
        "retrieval_timestamp": "2026-10-29T19:00:00Z",
        "source_rights_mutated": False,
        "canonical_apply_authorized": False,
        "repository_writes": [],
        "tickers": [
            {
                "ticker": "FICT",
                "status": "compared",
                "sec_cik": "0000001234",
                "candidate_source_url": source_url,
                "candidate_accession": accession,
                "candidate_filing_date": "2026-03-01",
                "candidate_period_end": "2025-12-31",
                "fields": [
                    {
                        "field": "revenue",
                        "value_kind": "direct",
                        "classification": "approved_direct",
                        "schema_status": "existing_canonical",
                        "field_scope_status": "approved",
                        "source_rights_status": "approved",
                        "commercial_rights_approved": True,
                        "publishability_blocker": "none",
                        "candidate_value": 1000000,
                        "unit": "USD",
                        "form": "10-K",
                        "sec_cik": "0000001234",
                        "accession": accession,
                        "period_start": "2025-01-01",
                        "period_end": "2025-12-31",
                        "filing_date": "2026-03-01",
                        "source_url": source_url,
                        "retrieval_timestamp": "2026-10-29T19:00:00Z",
                        "source_refs": [source_ref],
                    },
                    {
                        "field": "free_cash_flow",
                        "classification": "derived_scope_review_required",
                        "field_scope_status": "review_required",
                        "source_rights_status": "approved",
                        "commercial_rights_approved": True,
                        "candidate_value": 250000,
                    },
                ],
            }
        ],
    }


def test_default_online_action_explicitly_disables_local_csv_comparison(monkeypatch):
    from src import sec_fundamentals_preview

    calls = []
    def build(ticker, **kwargs):
        calls.append((ticker, kwargs))
        return _synthetic_preview()
    monkeypatch.setattr(sec_fundamentals_preview, "build_sec_fundamentals_preview", build)
    view = get_company_sec_annual_preview(
        "FICT", {}, refresh_requested=True, user_agent="Research Contact"
    )
    assert view["status"] == "inspection_only"
    assert calls[0][1]["canonical_path"] is None
    assert calls[0][1]["staged_path"] is None


def test_incompatible_annual_anchor_explains_reporting_gap():
    rendered = company_sec_annual_preview_html({
        "status": "unavailable", "ticker": "FICT", "reason": "invalid_annual_source_anchor",
    })
    assert "compatible annual revenue anchor" in rendered


def _preview_with_operating_components() -> dict[str, object]:
    preview = _synthetic_preview()
    revenue = preview["tickers"][0]["fields"][0]
    for name, concept, value in (
        ("operating_income", "OperatingIncomeLoss", 180_000),
        ("cash_from_operations", "NetCashProvidedByUsedInOperatingActivities", 250_000),
        ("capital_expenditures", "PaymentsToAcquirePropertyPlantAndEquipment", 40_000),
    ):
        reference = dict(revenue["source_refs"][0], concept=concept)
        preview["tickers"][0].setdefault("source_components", []).append(
            {
                **revenue,
                "field": name,
                "candidate_value": value,
                "schema_status": "candidate_component_not_canonical",
                "publishability_blocker": (
                    "Direct SEC field is approved, but adding a canonical column "
                    "requires a separate schema decision."
                ),
                "source_refs": [reference],
            }
        )
    return preview


def test_registered_operating_components_appear_only_as_read_only_source_facts() -> None:
    preview = _preview_with_operating_components()

    view = present_company_sec_annual_preview("FICT", preview)

    assert [row["field"] for row in view["approved_direct_fields"]] == [
        "revenue", "operating_income", "cash_from_operations", "capital_expenditures"
    ]
    assert [row["value"] for row in view["approved_direct_fields"][1:]] == [
        180_000, 250_000, 40_000
    ]
    assert all(row["canonical_schema_status"] == "review_required" for row in view["approved_direct_fields"][1:])
    assert view["safe_to_apply"] is False


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("missing_reference", "source_reference_missing"),
        ("wrong_concept", "field_concept_mismatch"),
        ("wrong_start", "field_period_mismatch"),
        ("wrong_end", "field_period_mismatch"),
        ("wrong_accession", "field_source_mismatch"),
        ("wrong_filed", "field_source_mismatch"),
        ("wrong_form", "nonannual_source"),
        ("wrong_unit", "field_unit_mismatch"),
        ("wrong_source_url", "field_source_mismatch"),
        ("wrong_observation", "field_source_mismatch"),
    ],
)
def test_operating_component_with_mismatched_source_reference_is_withheld(
    change: str, reason: str
) -> None:
    preview = _preview_with_operating_components()
    component = preview["tickers"][0]["source_components"][0]
    reference = component["source_refs"][0]
    if change == "missing_reference":
        component["source_refs"] = []
    elif change == "wrong_concept":
        reference["concept"] = "NetIncomeLoss"
    elif change == "wrong_start":
        reference["period_start"] = "2025-02-01"
    elif change == "wrong_end":
        reference["period_end"] = "2025-11-30"
    elif change == "wrong_accession":
        reference["accession"] = "0000001234-26-000002"
    elif change == "wrong_filed":
        reference["filed"] = "2026-03-02"
    elif change == "wrong_form":
        reference["form"] = "10-Q"
    elif change == "wrong_unit":
        reference["unit"] = "shares"
    elif change == "wrong_source_url":
        reference["source_url"] = "https://example.invalid/other.json"
    else:
        reference["retrieval_timestamp"] = "2026-10-28T19:00:00Z"

    view = present_company_sec_annual_preview("FICT", preview)

    assert "operating_income" not in {row["field"] for row in view["approved_direct_fields"]}
    assert {"field": "operating_income", "reason": reason} in view["withheld_fields"]
    assert "180,000" not in company_sec_annual_preview_html(view)


def test_missing_revenue_source_reference_blocks_operating_component_alignment() -> None:
    preview = _preview_with_operating_components()
    preview["tickers"][0]["fields"][0]["source_refs"] = []

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["approved_direct_fields"] == []
    assert {"field": "revenue", "reason": "source_reference_missing"} in view["withheld_fields"]
    assert all(
        {"field": field, "reason": "annual_anchor_reference_missing"} in view["withheld_fields"]
        for field in ("operating_income", "cash_from_operations", "capital_expenditures")
    )


def test_revenue_anchor_identity_failure_withholds_operating_components() -> None:
    preview = _preview_with_operating_components()
    preview["tickers"][0]["fields"][0]["sec_cik"] = "0000009999"

    view = present_company_sec_annual_preview("FICT", preview)

    assert {"field": "revenue", "reason": "field_source_mismatch"} in view["withheld_fields"]
    assert all(
        {"field": field, "reason": "annual_anchor_reference_missing"} in view["withheld_fields"]
        for field in ("operating_income", "cash_from_operations", "capital_expenditures")
    )


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("wrong_concept", "field_concept_mismatch"),
        ("derived_kind", "derived_field_scope_unreviewed"),
    ],
)
def test_untrusted_revenue_anchor_cannot_approve_direct_value_or_components(
    change: str, reason: str
) -> None:
    preview = _preview_with_operating_components()
    revenue = preview["tickers"][0]["fields"][0]
    if change == "wrong_concept":
        revenue["source_refs"][0]["concept"] = "NetIncomeLoss"
    else:
        revenue["value_kind"] = "derived"

    view = present_company_sec_annual_preview("FICT", preview)

    assert {"field": "revenue", "reason": reason} in view["withheld_fields"]
    assert all(
        {"field": field, "reason": "annual_anchor_reference_missing"} in view["withheld_fields"]
        for field in ("operating_income", "cash_from_operations", "capital_expenditures")
    )


@pytest.mark.parametrize("field_name", ["shares_outstanding", "filing_dates"])
def test_direct_instant_and_filing_date_reject_unrelated_concepts(field_name: str) -> None:
    preview = _synthetic_preview()
    revenue = preview["tickers"][0]["fields"][0]
    field = dict(revenue, field=field_name)
    if field_name == "shares_outstanding":
        field.update(candidate_value=1_000, unit="shares", period_start=None)
        field["source_refs"] = [
            dict(revenue["source_refs"][0], taxonomy="dei", concept="NetIncomeLoss",
                 unit="shares", period_start=None)
        ]
    else:
        field.update(candidate_value="2026-03-01", unit="date")
        field["source_refs"] = [
            dict(revenue["source_refs"][0], concept="NetIncomeLoss", unit="date",
                 underlying_fact_unit="USD")
        ]
    preview["tickers"][0]["fields"].append(field)

    view = present_company_sec_annual_preview("FICT", preview)

    assert {"field": field_name, "reason": "field_concept_mismatch"} in view["withheld_fields"]
    assert field_name not in {row["field"] for row in view["approved_direct_fields"]}


def test_direct_field_with_missing_canonical_column_keeps_schema_review_open() -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["fields"][0]["schema_status"] = "canonical_column_missing"

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["approved_direct_fields"][0]["canonical_schema_status"] == "review_required"
    assert view["safe_to_apply"] is False


@pytest.mark.parametrize("observed", [None, "2026-10-28T19:00:00Z"])
def test_field_observation_must_match_top_level_source_capture(observed: str | None) -> None:
    preview = _preview_with_operating_components()
    preview["tickers"][0]["fields"][0]["retrieval_timestamp"] = observed

    view = present_company_sec_annual_preview("FICT", preview)

    assert {"field": "revenue", "reason": "field_source_mismatch"} in view["withheld_fields"]
    assert all(
        {"field": field, "reason": "annual_anchor_reference_missing"} in view["withheld_fields"]
        for field in ("operating_income", "cash_from_operations", "capital_expenditures")
    )


def test_operating_field_moved_to_fields_cannot_bypass_missing_revenue_anchor() -> None:
    preview = _preview_with_operating_components()
    row = preview["tickers"][0]
    component = row["source_components"].pop(0)
    component.update(schema_status="existing_canonical", publishability_blocker="none")
    row["fields"].append(component)
    row["fields"][0]["source_refs"] = []

    view = present_company_sec_annual_preview("FICT", preview)

    assert {"field": "operating_income", "reason": "annual_anchor_reference_missing"} in view["withheld_fields"]
    assert "operating_income" not in {field["field"] for field in view["approved_direct_fields"]}


def test_operating_field_moved_out_of_source_components_is_not_approved() -> None:
    preview = _preview_with_operating_components()
    row = preview["tickers"][0]
    component = row["source_components"].pop(0)
    component.update(schema_status="existing_canonical", publishability_blocker="none")
    row["fields"].append(component)

    view = present_company_sec_annual_preview("FICT", preview)

    assert {"field": "operating_income", "reason": "unsupported_online_field"} in view["withheld_fields"]
    assert "operating_income" not in {field["field"] for field in view["approved_direct_fields"]}


def test_derived_operating_component_is_withheld_even_with_registered_field_name() -> None:
    preview = _preview_with_operating_components()
    preview["tickers"][0]["source_components"][0]["value_kind"] = "derived"

    view = present_company_sec_annual_preview("FICT", preview)

    assert "operating_income" not in {row["field"] for row in view["approved_direct_fields"]}
    assert {"field": "operating_income", "reason": "derived_field_scope_unreviewed"} in view["withheld_fields"]


def test_html_exposes_field_concept_period_rights_observation_and_schema_boundary() -> None:
    view = present_company_sec_annual_preview("FICT", _preview_with_operating_components())

    html = company_sec_annual_preview_html(view)

    assert "Source: us-gaap:OperatingIncomeLoss" in html
    assert "Period: 2025-01-01 to 2025-12-31" in html
    assert "Field scope: approved; raw redistribution held" in html
    assert "Observed: 2026-10-29T19:00:00Z" in html
    assert "Canonical schema: review required" in html
    assert "0000001234-26-000001" in html


@pytest.mark.parametrize(
    ("change", "label"),
    [
        ("missing_reference", "Exact SEC field reference is missing"),
        ("wrong_concept", "SEC concept does not match this field"),
        ("wrong_period", "Field period does not match the annual filing"),
        ("missing_anchor", "Revenue annual source anchor is missing"),
    ],
)
def test_html_names_source_proof_gaps_instead_of_generic_review_copy(
    change: str, label: str
) -> None:
    preview = _preview_with_operating_components()
    component = preview["tickers"][0]["source_components"][0]
    if change == "missing_reference":
        component["source_refs"] = []
    elif change == "wrong_concept":
        component["source_refs"][0]["concept"] = "NetIncomeLoss"
    elif change == "wrong_period":
        component["source_refs"][0]["period_start"] = "2025-02-01"
    else:
        preview["tickers"][0]["fields"][0]["source_refs"] = []

    html = company_sec_annual_preview_html(present_company_sec_annual_preview("FICT", preview))

    assert label in html
    assert "180,000" not in html


def test_presenter_shows_only_direct_approved_fields_and_withholds_derived_values() -> None:
    view = present_company_sec_annual_preview("FICT", _synthetic_preview())

    assert view["status"] == "inspection_only"
    assert view["ticker"] == "FICT"
    assert view["source_url"] == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json"
    assert view["sec_cik"] == "0000001234"
    assert view["retrieved_at_utc"] == "2026-10-29T19:00:00Z"
    assert view["filing_date"] == "2026-03-01"
    assert view["period_end"] == "2025-12-31"
    assert view["accession"] == "0000001234-26-000001"
    assert view["annual_form"] == "10-K"
    assert view["approved_direct_fields"] == [
        {
            "field": "revenue", "value": 1000000, "unit": "USD",
            "taxonomy": "us-gaap", "concept": "Revenues",
            "period_start": "2025-01-01", "period_end": "2025-12-31",
            "source_ref": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json",
            "accession": "0000001234-26-000001",
            "rights_status": "approved_field_scope_raw_redistribution_held",
            "observed_at_utc": "2026-10-29T19:00:00Z",
            "canonical_schema_status": "unchanged",
        }
    ]
    assert view["withheld_fields"] == [
        {"field": "free_cash_flow", "reason": "derived_field_scope_unreviewed"}
    ]
    assert "250000" not in str(view)
    assert view["safe_to_apply"] is False


def test_presenter_rejects_a_preview_for_another_company() -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["ticker"] = "OTHER"

    view = present_company_sec_annual_preview("FICT", preview)

    assert view == {
        "status": "unavailable",
        "ticker": "FICT",
        "reason": "source_identity_mismatch",
        "approved_direct_fields": [],
        "withheld_fields": [],
        "safe_to_apply": False,
    }


def test_explicit_refresh_fetches_once_and_rerenders_use_the_session_view() -> None:
    calls: list[tuple[str, str]] = []
    session: dict[str, object] = {}

    def fetch(ticker: str, *, user_agent: str) -> dict[str, object]:
        calls.append((ticker, user_agent))
        return _synthetic_preview()

    idle = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=False, user_agent="Research Contact", preview_builder=fetch
    )
    assert idle["status"] == "not_requested"
    assert calls == []

    first = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=True, user_agent="Research Contact", preview_builder=fetch
    )
    replay = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=False, user_agent="Research Contact", preview_builder=fetch
    )
    switched = get_company_sec_annual_preview(
        "OTHER", session, refresh_requested=False, user_agent="Research Contact", preview_builder=fetch
    )

    assert calls == [("FICT", "Research Contact")]
    assert first == replay
    assert switched["status"] == "not_requested"
    assert "1000000" not in str(switched)


def test_missing_identifying_user_agent_blocks_online_fetch() -> None:
    session: dict[str, object] = {}

    def unexpected_fetch(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("SEC fetch must not run without an identifying User-Agent")

    view = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=True, user_agent=None, preview_builder=unexpected_fetch
    )

    assert view["status"] == "configuration_required"
    assert view["reason"] == "sec_user_agent_required"
    assert view["approved_direct_fields"] == []
    assert get_company_sec_annual_preview(
        "FICT", session, refresh_requested=False, user_agent=None, preview_builder=unexpected_fetch
    ) == view


@pytest.mark.parametrize("failure", [RuntimeError, TypeError])
def test_online_failure_returns_bounded_error_without_leaking_transport_details(
    failure: type[Exception],
) -> None:
    session: dict[str, object] = {}

    def failed_fetch(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise failure("HTTP 500 with private transport detail")

    view = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=True, user_agent="Research Contact", preview_builder=failed_fetch
    )

    assert view["status"] == "unavailable"
    assert view["reason"] == "sec_fetch_unavailable"
    assert "private transport detail" not in str(view)
    assert get_company_sec_annual_preview(
        "FICT", session, refresh_requested=False, user_agent="Research Contact", preview_builder=failed_fetch
    ) == view


def test_malformed_session_cache_fails_closed_without_a_key_error() -> None:
    session: dict[str, object] = {"company_sec_annual_preview_v1": {"ticker": "FICT"}}

    view = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=False, user_agent="Research Contact"
    )

    assert view["status"] == "not_requested"
    assert view["safe_to_apply"] is False


def test_presenter_rejects_an_unverified_companyfacts_source_url() -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["candidate_source_url"] = "https://example.invalid/facts.json"

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["status"] == "unavailable"
    assert view["reason"] == "source_identity_mismatch"
    assert view["approved_direct_fields"] == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("canonical_apply_authorized", True),
        ("repository_writes", ["data/fundamentals.csv"]),
    ],
)
def test_presenter_rejects_a_preview_that_could_write_or_apply(key: str, value: object) -> None:
    preview = _synthetic_preview()
    preview[key] = value

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["status"] == "unavailable"
    assert view["reason"] == "preview_not_read_only"
    assert view["approved_direct_fields"] == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("sec_cik", "0000009999"),
        ("accession", "0000001234-26-999999"),
        ("period_end", "2024-12-31"),
        ("source_url", "https://example.invalid/other.json"),
    ],
)
def test_direct_field_with_mixed_source_identity_is_withheld(key: str, value: object) -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["fields"][0][key] = value

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["approved_direct_fields"] == []
    assert {"field": "revenue", "reason": "field_source_mismatch"} in view["withheld_fields"]
    assert "1000000" not in str(view)


@pytest.mark.parametrize(
    "case",
    ["no_ticker_rows", "missing_fields", "wrong_preview_source", "wrong_requested_ticker", "blocked_row"],
)
def test_malformed_or_blocked_preview_fails_closed_without_exception(case: str) -> None:
    preview = _synthetic_preview()
    if case == "no_ticker_rows":
        preview["tickers"] = []
    elif case == "missing_fields":
        del preview["tickers"][0]["fields"]
    elif case == "wrong_preview_source":
        preview["source"] = "unreviewed_provider"
    elif case == "wrong_requested_ticker":
        preview["requested_tickers"] = ["OTHER"]
    else:
        preview["tickers"][0]["status"] = "fetch_failed"

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["status"] == "unavailable"
    assert view["approved_direct_fields"] == []
    assert view["safe_to_apply"] is False


def test_presenter_never_promotes_a_price_from_an_sec_annual_preview() -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["fields"][0]["field"] = "price"

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["approved_direct_fields"] == []
    assert {"field": "price", "reason": "unsupported_online_field"} in view["withheld_fields"]
    assert "1000000" not in str(view)


@pytest.mark.parametrize("key", ["candidate_period_end", "candidate_filing_date", "candidate_accession"])
def test_missing_annual_source_anchor_fails_closed(key: str) -> None:
    preview = _synthetic_preview()
    preview["tickers"][0][key] = None

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["status"] == "unavailable"
    assert view["approved_direct_fields"] == []


def test_nonannual_direct_fact_is_withheld() -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["fields"][0]["form"] = "10-Q"

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["approved_direct_fields"] == []
    assert {"field": "revenue", "reason": "nonannual_source"} in view["withheld_fields"]


def test_duplicate_direct_fact_is_withheld_even_when_each_row_is_individually_approved() -> None:
    preview = _synthetic_preview()
    second_revenue = dict(preview["tickers"][0]["fields"][0])
    second_revenue["candidate_value"] = 2000000
    preview["tickers"][0]["fields"].append(second_revenue)

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["approved_direct_fields"] == []
    assert {"field": "revenue", "reason": "duplicate_direct_field"} in view["withheld_fields"]
    assert "1000000" not in str(view)
    assert "2000000" not in str(view)


def test_html_idle_state_prompts_explicit_fetch_and_keeps_market_boundary() -> None:
    html = company_sec_annual_preview_html({"status": "not_requested", "ticker": "FICT"})

    assert "Check SEC annual facts" in html
    assert "No live prices or analyst estimates" in html
    assert "Saved readiness is unchanged" in html


def test_html_inspection_shows_approved_and_withheld_with_escaped_text() -> None:
    view = present_company_sec_annual_preview("FICT", _synthetic_preview())
    view["withheld_fields"].append(
        {"field": "<script>alert(1)</script>", "reason": "source_evidence_unreviewed"}
    )

    html = company_sec_annual_preview_html(view)

    assert "FICT" in html
    assert "2026-03-01" in html
    assert "2025-12-31" in html
    assert "10-K" in html
    assert "Candidate SEC CIK 0000001234" in html
    assert "0000001234-26-000001" in html
    assert "1,000,000" in html
    assert "free_cash_flow" in html
    assert "Derived field scope needs review" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html
    assert 'href="https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json"' in html


def test_html_inspection_shows_every_approved_and_withheld_field_in_one_visible_table() -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["fields"][0]["candidate_value"] = 1000000.0
    filing_date = dict(preview["tickers"][0]["fields"][0])
    filing_date.update(field="filing_dates", candidate_value="2026-03-01", unit="date")
    filing_date["source_refs"] = [
        dict(filing_date["source_refs"][0], unit="date", underlying_fact_unit="USD")
    ]
    preview["tickers"][0]["fields"].append(filing_date)
    view = present_company_sec_annual_preview("FICT", preview)

    html = company_sec_annual_preview_html(view)

    assert (
        'class="sec-annual-table-scroll" role="region" '
        'aria-label="Annual filing fields" tabindex="0"'
    ) in html
    assert '<table class="sec-annual-field-table">' in html
    assert '<th scope="col">Field</th>' in html
    assert '<th scope="col">Value or reason</th>' in html
    assert '<th scope="row">' in html
    assert html.count('<tr class="sec-annual-field-row') == 3
    assert "1,000,000" in html
    assert "1,000,000.0" not in html
    assert "USD" in html
    assert "2025-12-31" in html
    assert "Filing date" in html
    assert "2026-03-01 date" not in html
    assert '<details class="sec-annual-gaps">' not in html
    assert "free_cash_flow" in html
    assert "Derived field scope needs review" in html
    assert "250000" not in html
    assert "Saved readiness is unchanged" in html


@pytest.mark.parametrize(
    ("key", "value", "reason"),
    [
        ("unit", "shares", "field_unit_mismatch"),
        ("candidate_value", float("nan"), "invalid_direct_value"),
        ("candidate_value", None, "invalid_direct_value"),
        ("candidate_value", 10**1000, "invalid_direct_value"),
    ],
)
def test_direct_fact_with_wrong_unit_or_value_is_withheld(
    key: str, value: object, reason: str
) -> None:
    preview = _synthetic_preview()
    preview["tickers"][0]["fields"][0][key] = value

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["approved_direct_fields"] == []
    assert {"field": "revenue", "reason": reason} in view["withheld_fields"]


@pytest.mark.parametrize("retrieval", [None, "2025-01-01T00:00:00Z"])
def test_missing_or_pre_filing_retrieval_time_fails_closed(retrieval: object) -> None:
    preview = _synthetic_preview()
    preview["retrieval_timestamp"] = retrieval

    view = present_company_sec_annual_preview("FICT", preview)

    assert view["status"] == "unavailable"
    assert view["approved_direct_fields"] == []


def test_html_fails_closed_on_malformed_lists_and_unsafe_source_link() -> None:
    html = company_sec_annual_preview_html(
        {
            "status": "inspection_only",
            "ticker": "<img src=x onerror=alert(1)>",
            "sec_cik": "0000001234",
            "source_url": "javascript:alert(1)",
            "approved_direct_fields": {"unexpected": "shape"},
            "withheld_fields": {"unexpected": "shape"},
        }
    )

    assert "<img" not in html
    assert "&lt;img" in html
    assert "javascript:" not in html
    assert "Source link unavailable" in html
    assert "No direct-approved annual facts are available" in html


def test_html_explains_configuration_and_fetch_failure_without_source_values() -> None:
    configuration = company_sec_annual_preview_html(
        {"status": "configuration_required", "ticker": "FICT", "reason": "sec_user_agent_required"}
    )
    failure = company_sec_annual_preview_html(
        {"status": "unavailable", "ticker": "FICT", "reason": "sec_fetch_unavailable"}
    )

    assert "User-Agent is required" in configuration
    assert "annual facts are unavailable" in failure
    assert "Saved readiness is unchanged" in configuration
    assert "Saved readiness is unchanged" in failure
    assert "href=" not in configuration + failure


def test_html_shows_all_validated_size_field_rows_and_caps_untrusted_larger_views() -> None:
    view = present_company_sec_annual_preview("FICT", _synthetic_preview())
    view["withheld_fields"] = [
        {"field": f"gap{i:02d}", "reason": "source_evidence_unreviewed"}
        for i in range(35)
    ]

    html = company_sec_annual_preview_html(view)

    assert "gap30" in html
    assert "gap31" not in html
    assert html.count('<tr class="sec-annual-field-row') == 32


def test_loader_rejects_multi_ticker_input_before_online_fetch() -> None:
    session: dict[str, object] = {}

    def unexpected_fetch(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("one Workbench action must never fetch multiple tickers")

    view = get_company_sec_annual_preview(
        "FICT,OTHER",
        session,
        refresh_requested=True,
        user_agent="Research Contact",
        preview_builder=unexpected_fetch,
    )

    assert view["status"] == "unavailable"
    assert view["reason"] == "invalid_ticker"
    assert session == {}


def test_failed_refresh_does_not_replay_an_older_session_result() -> None:
    session: dict[str, object] = {}
    get_company_sec_annual_preview(
        "FICT",
        session,
        refresh_requested=True,
        user_agent="Research Contact",
        preview_builder=lambda *_args, **_kwargs: _synthetic_preview(),
    )

    blocked = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=True, user_agent=None
    )
    replay = get_company_sec_annual_preview(
        "FICT", session, refresh_requested=False, user_agent=None
    )

    assert blocked["status"] == "configuration_required"
    assert replay == blocked
    assert "1000000" not in str(replay)
