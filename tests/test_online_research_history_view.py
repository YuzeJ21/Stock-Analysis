from datetime import datetime, timezone

from test_sec_annual_history import _payload, _view
from test_online_company_prices import _fetch, OBSERVED


def test_history_view_displays_reported_values_direction_and_restatement_basis():
    from src.sec_annual_history import build_sec_annual_history
    from src.online_research_history_view import annual_history_html

    view = _view(); view["annual_history"] = build_sec_annual_history(view, _payload())
    result = annual_history_html(view)
    assert "Historical annual financials" in result
    assert "Revenue increased" in result
    assert "2026-03-01" in result
    assert "not point-in-time" in result
    assert "Percentage growth remains withheld" in result
    assert '<svg' in result


def test_history_renderer_rejects_a_different_company_or_changed_source_value():
    from src.sec_annual_history import build_sec_annual_history
    from src.online_research_history_view import annual_history_html

    view = _view(); view["annual_history"] = build_sec_annual_history(view, _payload())
    view["annual_history"]["ticker"] = "OTHER"
    assert "Revenue increased" not in annual_history_html(view)
    view["annual_history"]["ticker"] = "FICT"
    view["annual_history"]["periods"][0]["revenue"] = 999999
    assert "999,999" not in annual_history_html(view)


def test_unused_malformed_field_cannot_crash_history_rendering():
    from src.sec_annual_history import build_sec_annual_history
    from src.online_research_history_view import annual_history_html
    view = _view(); view["annual_history"] = build_sec_annual_history(view, _payload())
    fields = view["annual_history"]["periods"][0]["fields"]
    fields[:] = [f for f in fields if f["field"] != "filing_dates"] + [{"field": "filing_dates"}]
    assert "Revenue increased" not in annual_history_html(view)


def test_malformed_withheld_period_start_is_rejected_before_rendering():
    from src.sec_annual_history import build_sec_annual_history
    from src.online_research_history_view import annual_history_html
    view = _view(); view["annual_history"] = build_sec_annual_history(view, _payload())
    view["annual_history"]["periods"][0].update({
        "status": "withheld", "fields": [], "revenue": None, "reason": "ambiguous_filing_context",
        "period_start": {"unexpected": "source"},
    })
    assert "Revenue increased" not in annual_history_html(view)


def test_historical_continuing_operations_cash_is_qualified_beside_the_value():
    from src.sec_annual_history import build_sec_annual_history
    from src.online_research_history_view import annual_history_html
    p = _payload(); facts = p["facts"]["us-gaap"]
    facts["NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"] = facts.pop("NetCashProvidedByUsedInOperatingActivities")
    view = _view(p); view["annual_history"] = build_sec_annual_history(view, p)
    assert "Operating cash flow · continuing operations" in annual_history_html(view)


def test_history_and_price_sections_survive_streamlit_markdown_on_desktop_and_phone(tmp_path):
    import pytest
    from src.sec_annual_history import build_sec_annual_history
    from src.online_company_prices import fetch_online_company_prices
    from src.online_research_history_view import annual_history_html, online_price_history_html
    from src.online_company_analysis import build_online_company_analysis, online_company_analysis_html
    from src.company_sec_online_preview import company_sec_annual_preview_html
    from src.public_performance_gate import _local_demo_server
    runtime = pytest.importorskip("playwright.sync_api")
    view = _view(); view["annual_history"] = build_sec_annual_history(view, _payload())
    prices = fetch_online_company_prices("FICT", observed_at=OBSERVED, fetcher=_fetch())
    html = online_company_analysis_html(build_online_company_analysis(view)) + annual_history_html(view) + company_sec_annual_preview_html(view)
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'dashboard.py').write_text('import streamlit as st\nst.markdown(' + repr(html) + ', unsafe_allow_html=True)\nst.markdown(' + repr(online_price_history_html(prices)) + ', unsafe_allow_html=True)\n')
    with _local_demo_server(tmp_path, timeout_seconds=30) as base:
        with runtime.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(base, wait_until="domcontentloaded")
            page.get_by_role('region', name='Historical annual financials').wait_for(timeout=15000)
            page.get_by_role('region', name='Daily price history').wait_for(timeout=15000)
            for width, height in [(1280,900),(390,844),(195,422)]:
                page.set_viewport_size({"width":width,"height":height})
                assert page.get_by_role('heading',name='Historical annual financials').count()==1
                assert 'not point-in-time' in page.locator('.online-history').inner_text()
                assert page.locator('.online-history article').count()==3
                dims=page.evaluate("() => [...document.querySelectorAll('.online-history,.online-history article,.online-price-inspection')].map(x=>[x.clientWidth,x.scrollWidth])")
                assert all(a==b for a,b in dims)
            browser.close()


def test_price_view_discloses_dates_identity_and_unreviewed_adjustment_rights():
    from src.online_company_prices import fetch_online_company_prices
    from src.online_research_history_view import online_price_history_html

    result = fetch_online_company_prices("FICT", observed_at=OBSERVED, fetcher=_fetch())
    rendered = online_price_history_html(result)
    assert "2026-10-29" in rendered
    assert "personal research" in rendered.lower()
    assert "Adjustment basis is unverified" in rendered
    assert "issuer link" in rendered
    assert "commercial" in rendered.lower()
    assert '<svg' in rendered


def test_history_model_can_mark_comparable_direction_available_without_releasing_percentages():
    from src.sec_annual_history import build_sec_annual_history
    from src.online_company_analysis import build_online_company_analysis

    view = _view(); view["annual_history"] = build_sec_annual_history(view, _payload())
    result = build_online_company_analysis(view)
    assert result["findings"][0]["title"] == "Historical revenue comparison available"
    assert result["derived_numeric_values"] == {}


def test_workbench_price_action_passes_explicit_request_and_displays_its_source_scope(monkeypatch):
    from types import SimpleNamespace
    from src import dashboard
    from src.online_company_prices import fetch_online_company_prices

    class Container:
        def __enter__(self): return self
        def __exit__(self, *_a): return False
    calls = []; html = []
    result = fetch_online_company_prices("FICT", observed_at=OBSERVED, fetcher=_fetch())
    monkeypatch.setattr(dashboard, "st", SimpleNamespace(
        container=lambda **kw: Container(), button=lambda *a, **kw: True, session_state={},
        markdown=lambda value, **kw: html.append(value),
    ))
    monkeypatch.setattr(dashboard, "get_online_company_prices", lambda ticker, session, **kw: calls.append(kw["refresh_requested"]) or result)
    dashboard.render_company_online_prices("FICT")
    assert calls == [True]
    assert "Adjustment basis is unverified" in " ".join(html)
