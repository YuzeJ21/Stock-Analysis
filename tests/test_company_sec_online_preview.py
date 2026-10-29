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
                        "classification": "approved_direct",
                        "field_scope_status": "approved",
                        "source_rights_status": "approved",
                        "commercial_rights_approved": True,
                        "publishability_blocker": "none",
                        "candidate_value": 1000000,
                        "unit": "USD",
                        "form": "10-K",
                        "sec_cik": "0000001234",
                        "accession": accession,
                        "period_end": "2025-12-31",
                        "filing_date": "2026-03-01",
                        "source_url": source_url,
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
        {"field": "revenue", "value": 1000000, "unit": "USD", "period_end": "2025-12-31"}
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
