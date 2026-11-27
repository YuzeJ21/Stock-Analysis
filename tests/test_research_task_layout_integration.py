"""The online search entry is concise and only fetches after its explicit submit."""
import pytest

from streamlit.testing.v1 import AppTest


def _search_app():
    from src.dashboard import render_online_company_search
    render_online_company_search(saved_tickers=('AMD',))


@pytest.mark.parametrize('configured_agent', [False, True])
def test_company_search_exposes_one_clear_action_and_never_fetches_on_render(monkeypatch, configured_agent):
    from src import dashboard
    from src.online_research_tools_ui import SEC_AGENT_KEY
    identification = 'Synthetic research contact@example.invalid'
    if configured_agent:
        monkeypatch.setenv('SEC_USER_AGENT', identification)
    else:
        monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    calls=[]
    monkeypatch.setattr(dashboard,'search_sec_company_candidates',lambda query,**kw:
        calls.append((query, kw['user_agent'])) or {'status':'unavailable','reason':'source_unavailable'})
    at=AppTest.from_function(_search_app,default_timeout=30).run()
    assert not at.exception
    if configured_agent:
        assert [field.label for field in at.text_input]==['Company name or ticker']
    else:
        assert [field.label for field in at.text_input]==[
            'SEC request identification (name and contact)', 'Company name or ticker',
        ]
        assert len(at.expander)==1 and at.expander[0].label=='SEC access'
        assert at.expander[0].proto.expanded is False
        at.text_input(key=SEC_AGENT_KEY + ':entry').set_value(identification).run()
        assert not at.exception and calls==[]
    assert [button.label for button in at.button]==['Search company']
    assert calls==[]
    at.text_input(key='online-company-query').set_value('AMD')
    at.button[0].click().run()
    assert not at.exception and calls==[('AMD', identification)]
    at.run()
    assert calls==[('AMD', identification)]
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
