"""Online discovery is separate from saved research evidence."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src import dashboard
from src.online_company_search import (
    ONLINE_COMPANY_SESSION_KEY,
    online_company_candidate_for_route,
    online_company_results_html,
)


def _result(*, candidates=None):
    return {
        "status": "ready",
        "query": "FICT",
        "source_url": "https://www.sec.gov/files/company_tickers_exchange.json",
        "observed_at": "2026-10-30T14:00:00Z",
        "source_last_modified": "2026-10-30T10:00:00Z",
        "payload_sha256": "a" * 64,
        "candidates": candidates if candidates is not None else [
            {"ticker": "FICT", "cik": "0000001234", "title": "Fictional <Research>", "exchange": "Nasdaq", "ambiguous": False},
        ],
    }


def test_online_result_links_unambiguous_unsaved_company_without_claiming_readiness():
    rendered = online_company_results_html(_result(), saved_tickers={"AMD"})

    assert "Fictional &lt;Research&gt;" in rendered
    assert "page=company-workbench&amp;ticker=FICT&amp;online=1" in rendered
    assert "No local ticker row" in rendered
    assert "2026-10-30T14:00:00Z" in rendered
    assert "active listing" in rendered.lower()
    assert "analysis eligibility" in rendered.lower()
    assert "<Research>" not in rendered


def test_ambiguous_sec_ticker_is_visible_but_has_no_workbench_link():
    result = _result(candidates=[
        {"ticker": "DUP", "cik": "0000001234", "title": "Issuer One", "exchange": "NYSE", "ambiguous": True},
        {"ticker": "DUP", "cik": "0000005678", "title": "Issuer Two", "exchange": "Nasdaq", "ambiguous": True},
    ])

    rendered = online_company_results_html(result, saved_tickers=set())

    assert rendered.count("Ambiguous SEC association") == 2
    assert "page=company-workbench" not in rendered
    assert online_company_candidate_for_route("DUP", {ONLINE_COMPANY_SESSION_KEY: result}) is None


def test_online_route_requires_valid_session_candidate_and_never_guesses_identity():
    result = _result()
    session = {ONLINE_COMPANY_SESSION_KEY: result}

    assert online_company_candidate_for_route("FICT", session)["cik"] == "0000001234"
    assert online_company_candidate_for_route("OTHER", session) is None
    assert online_company_candidate_for_route(
        "FICT", {ONLINE_COMPANY_SESSION_KEY: {**result, "source_url": "https://example.invalid/map"}}
    ) is None


@pytest.mark.parametrize("registered", [("AMD",), ("AMD", "FICT")])
def test_online_only_workbench_opens_sec_check_without_saved_analysis(monkeypatch, registered):
    from tests.test_research_mode_dashboard_contract import _capture_integrated_company_route
    query, context, captured, reports, calls = _capture_integrated_company_route(monkeypatch)
    monkeypatch.setattr(dashboard,"render_company_sec_filing_check",lambda ticker,expected_cik=None:calls.append(("filing",ticker,expected_cik)))
    monkeypatch.setattr(dashboard,"render_company_security_check",lambda ticker,expected_cik=None:calls.append(("security",ticker,expected_cik)))
    dashboard.st.query_params.update(ticker="FICT",online="1")
    dashboard.st.session_state.clear()
    monkeypatch.setattr(dashboard,"search_sec_company_candidates",lambda *a,**k:_result())
    dashboard.render_company_workbench(
        SimpleNamespace(list_local_tickers=lambda:list(registered)),
        SimpleNamespace(profile_key="default",freshness_state="stale"),{},object())
    assert captured['online_candidate']['cik']=="0000001234"
    assert captured['saved_available']==("FICT" in registered)
    assert reports==[] and calls==[]
    captured['render_sources']({'financial':{'status':'not_requested'},'prices':{'status':'not_requested'}})
    assert ('filing',"FICT","0000001234") in calls
    assert ('security',"FICT","0000001234") in calls
    assert reports==[]


def test_online_search_runs_only_on_explicit_submit_and_survives_zero_saved_rows(monkeypatch):
    class Form:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    calls: list[str] = []
    rendered: list[str] = []
    session: dict[str, object] = {}
    submitted = [False, True]
    monkeypatch.setattr(
        dashboard,
        "st",
        SimpleNamespace(
            session_state=session,
            form=lambda *_args, **_kwargs: Form(),
            text_input=lambda *_args, **_kwargs: "FICT",
            form_submit_button=lambda *_args, **_kwargs: submitted.pop(0),
            markdown=lambda value, **kwargs: rendered.append(str(value)),
        ),
    )
    monkeypatch.setattr(
        dashboard,
        "search_sec_company_candidates",
        lambda query, *, user_agent: calls.append(query) or _result(),
    )

    dashboard.render_online_company_search(saved_tickers=())
    assert calls == []
    dashboard.render_online_company_search(saved_tickers=())
    assert calls == ["FICT"]
    assert session[ONLINE_COMPANY_SESSION_KEY]["status"] == "ready"
    assert any("page=company-workbench&amp;ticker=FICT&amp;online=1" in value for value in rendered)


def test_online_workbench_route_retains_explicit_online_flag():
    from src.dashboard_navigation import canonical_workspace_query

    assert canonical_workspace_query(
        "research", "Company Workbench",
        {"ticker": "IONQ", "online": "1"},
    ) == {
        "mode": "research", "page": "company-workbench", "ticker": "IONQ", "online": "1"
    }


@pytest.mark.parametrize("registered", [(), ("FICT",)])
def test_unavailable_online_route_does_not_repeat_sec_fetch_on_rerender(monkeypatch, registered):
    session: dict[str, object] = {}
    calls: list[str] = []
    rendered: list[str] = []
    monkeypatch.setattr(
        dashboard,
        "st",
        SimpleNamespace(
            query_params={"ticker": "FICT", "online": "1"},
            session_state=session,
            markdown=lambda value, **_kwargs: rendered.append(str(value)),
        ),
    )
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "search_sec_company_candidates",
        lambda query, *, user_agent: calls.append(query) or {
            "status": "unavailable", "query": query, "reason": "sec_fetch_unavailable",
            "candidates": [],
        },
    )

    for _ in range(2):
        dashboard.render_company_workbench(
            SimpleNamespace(list_local_tickers=lambda: list(registered)),
            SimpleNamespace(), {}, object(),
        )

    assert calls == ["FICT"]
    assert "Online SEC identity is unavailable for FICT" in " ".join(rendered)


def test_online_candidate_sec_facts_withhold_mismatched_cik(monkeypatch):
    class Container:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    rendered: list[str] = []
    monkeypatch.setattr(
        dashboard,
        "st",
        SimpleNamespace(
            session_state={},
            container=lambda **kwargs: Container(),
            button=lambda *_args, **_kwargs: True,
            empty=lambda: SimpleNamespace(markdown=lambda value, **kwargs: rendered.append(value)),
        ),
    )
    monkeypatch.setattr(
        dashboard,
        "get_company_sec_annual_preview",
        lambda *args, **kwargs: {
            "status": "inspection_only", "ticker": "FICT", "sec_cik": "0000009999",
            "approved_direct_fields": [{"field": "revenue", "value": 123456789}],
            "safe_to_apply": False,
        },
    )

    dashboard.render_company_sec_annual_check("FICT", expected_cik="0000001234")

    assert "123456789" not in " ".join(rendered)
    assert "identity" in " ".join(rendered).lower()
