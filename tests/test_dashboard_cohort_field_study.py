"""Research-route checks for the read-only six-company field study."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pandas as pd

from src import dashboard
from src.cohort_field_evidence import DEFAULT_TICKERS, FIELDS
from src.cohort_field_study import BoundedFieldStudy
from src.weekly_research_summary import WeeklyResearchSummary


def _study() -> BoundedFieldStudy:
    rows = tuple({
        "ticker": ticker, "field": field, "value": "", "period_end": "",
        "withheld_reasons": ["saved_field_missing"], "source": "",
        "source_ref": "", "source_published_at": "", "observation_date": "",
        "rights_status": "source_unidentified",
    } for ticker in DEFAULT_TICKERS for field in FIELDS)
    return BoundedFieldStudy(
        status="unchanged",
        message="No field difference; two saved inspections of the same underlying inputs.",
        fields=rows,
        prior_as_of="2026-10-26",
        current_as_of="2026-10-27",
        snapshot_identity="a" * 64,
        same_input_digest=True,
        field_count=54,
        withheld_count=54,
    )


def test_discover_places_six_company_study_after_saved_company_results():
    source = inspect.getsource(dashboard.render_stock_selector)
    assert source.index("stock_selector_result_table_html(filtered") < source.index(
        "study_discover_html(field_study)"
    )


def test_discover_study_markup_keeps_qcom_blocked_and_all_six_company_links():
    rendered = dashboard.study_discover_html(_study())
    assert all(f"ticker={ticker}" in rendered for ticker in DEFAULT_TICKERS)
    assert "QCOM" in rendered and "blocked" in rendered


def test_company_workbench_shows_qcom_reasons_and_keeps_raw_proof_advanced(monkeypatch):
    from tests.test_research_mode_dashboard_contract import _capture_integrated_company_route
    query, context, captured, reports, calls = _capture_integrated_company_route(monkeypatch)
    rendered=[]
    monkeypatch.setattr(dashboard.st,'markdown',lambda value,**kwargs:rendered.append(str(value)))
    monkeypatch.setattr(dashboard,'load_dashboard_bounded_field_study',lambda context:_study())
    dashboard.st.query_params['ticker']='QCOM'
    dashboard.render_company_workbench(SimpleNamespace(list_local_tickers=lambda:['QCOM']),
        SimpleNamespace(profile_key='default',freshness_state='stale'),{},object())
    assert rendered==[] and reports==[]
    captured['render_sources']({'financial':{'status':'not_requested'},'prices':{'status':'not_requested'}})
    copy=' '.join(rendered)
    assert 'QCOM saved-field evidence' in copy
    assert copy.count('No saved value')==9
    assert 'Raw saved field references' in copy and 'Input digest:' in copy


def test_monitor_study_comparison_is_separate_from_follow_up_queue(monkeypatch):
    rendered: list[str] = []

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dashboard, "load_dashboard_bounded_field_study", lambda context: _study())
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "load_dashboard_research_discipline_rows", lambda *args, **kwargs: ())
    monkeypatch.setattr(dashboard, "load_dashboard_nowcast_cohort", lambda: ())
    monkeypatch.setattr(dashboard, "cohort_readiness_cards", lambda rows: [])
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: rendered.append(str(value)))
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    dashboard.render_research_monitor(
        {"queue": ()},
        SimpleNamespace(freshness_state="current", freshness_message="Current"),
        WeeklyResearchSummary("no_changes", "2026-10-27T00:00:00+00:00", 0, 0, (), "No changes"),
        object(),
    )

    copy = " ".join(rendered)
    assert rendered.count("## Follow-up Queue") == 1
    assert "Six-company saved-field comparison" in copy
    assert "No field difference" in copy
    assert "adds no Monitor follow-up event" in copy
