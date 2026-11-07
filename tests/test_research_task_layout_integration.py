"""The online search entry is concise and only fetches after its explicit submit."""
from streamlit.testing.v1 import AppTest


def _search_app():
    from src.dashboard import render_online_company_search
    render_online_company_search(saved_tickers=('AMD',))


def test_company_search_exposes_one_clear_action_and_never_fetches_on_render(monkeypatch):
    from src import dashboard
    calls=[]
    monkeypatch.setattr(dashboard,'search_sec_company_candidates',lambda query,**kw:
        calls.append(query) or {'status':'unavailable','reason':'source_unavailable'})
    at=AppTest.from_function(_search_app,default_timeout=30).run()
    assert not at.exception
    assert [field.label for field in at.text_input]==['Company name or ticker']
    assert [button.label for button in at.button]==['Search company']
    assert calls==[]
    at.text_input[0].set_value('AMD')
    at.button[0].click().run()
    assert not at.exception and calls==['AMD']
    at.run()
    assert calls==['AMD']
    assert 'SEC online company search is unavailable' in '\n'.join(m.value for m in at.markdown)


def test_desk_search_uses_registered_companies_beyond_the_focused_cohort(monkeypatch,tmp_path):
    from datetime import date
    from types import SimpleNamespace
    from src import dashboard
    captured=[]
    monkeypatch.setattr(dashboard,'load_observation_recency',lambda *a,**kw:None)
    monkeypatch.setattr(dashboard,'render_research_desk',lambda *a,**kw:captured.append(kw))
    context=SimpleNamespace(data_dir=tmp_path)
    provider=SimpleNamespace(list_local_tickers=lambda:['AMD','AAPL'])
    cohort=SimpleNamespace(members=[SimpleNamespace(ticker='AMD')])
    assert dashboard.render_personal_research_route(selected_page='Research Desk',provider=provider,
        context=context,state={},cohort=cohort,coverage=None,weekly_summary=None,ticker='',review_date=date(2026,11,7))
    assert captured[0]['registered_tickers']==('AMD','AAPL')
