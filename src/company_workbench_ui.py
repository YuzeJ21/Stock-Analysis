"""Lazy Personal Research compositor over existing, separately qualified evidence."""
from collections.abc import Mapping
from html import escape
import os
from urllib.parse import urlencode

from src.company_answer_summary import build_company_answers, company_answers_html
from src.company_sec_online_preview import get_company_sec_annual_preview
from src.online_company_prices import get_online_company_prices
from src.online_company_identity import get_price_filing_association, _mode_reason
from src.company_workbench_sections import (
    SECTIONS, section_key, workbench_projection, workbench_header_html, workbench_facts_html,
)
from src.online_research_history_view import annual_history_html, online_price_history_html
from src.online_research_expansion_view import quarterly_history_html, price_filing_association_html
from src.online_company_analysis import build_online_company_analysis, online_company_analysis_html
from src.online_us_universe_view import foreign_financials_html
from src.sec_foreign_financials import validated_foreign_financials
from src.company_valuation_overview import build_valuation_overview, valuation_overview_html
from src.security_classification import get_company_security_context
from src.scenario_lab_session import scenario_lab_widget_keys
from src.research_record_authoring_ui import FIELD_CONTRACTS, authoring_session_key
from src.online_peer_sources import get_online_peer_valuation
from src.online_peer_valuation_ui import online_peer_valuation_html
from src.company_workbench_presentation import (
    WORKBENCH_STYLE, METRICS, financial_workspace_html, workbench_metrics_html,
)


def retain_saved_tool_inputs(state,profile_scope,ticker,*,identity_scope=None):
    """Keep scoped editable inputs across lazy panes, never action or consent state."""
    keys=list(scenario_lab_widget_keys(profile_scope,ticker).values()) if identity_scope is None else []
    keys.append(authoring_session_key(profile_scope,ticker,'kind',identity_scope=identity_scope))
    keys.extend(authoring_session_key(profile_scope,ticker,f'field:{kind}:{name}',identity_scope=identity_scope)
                for kind,fields in FIELD_CONTRACTS.items() for name in fields)
    for key in keys:
        if key in state:state[key]=state[key]


def load_workbench_observations(ticker, state, *, refresh_financials=False, refresh_prices=False,
                                expected_cik=None, user_agent=None):
    """Only explicit actions reach transport; ordinary section reruns reuse attempts."""
    user_agent=user_agent if user_agent is not None else os.getenv('SEC_USER_AGENT')
    reason=_mode_reason('research')
    if reason:
        financial=prices={'ticker':ticker,'status':'unavailable','reason':reason}
    else:
        financial=get_company_sec_annual_preview(ticker,state,refresh_requested=refresh_financials,user_agent=user_agent)
        prices=get_online_company_prices(ticker,state,refresh_requested=refresh_prices,
            include_verified_session_close=True)
    projection=workbench_projection(ticker,financial,prices,expected_cik=expected_cik)
    if projection['identity_conflict']:
        financial={'ticker':ticker,'status':'unavailable','reason':'sec_identity_mismatch','safe_to_apply':False}
        prices={'ticker':ticker,'status':'unavailable','reason':'sec_identity_mismatch'}
    identity=financial.get('companyfacts_identity',{}) if isinstance(financial,Mapping) else {}
    association=get_price_filing_association(ticker,identity,prices,state,
        refresh_requested=bool(refresh_financials or refresh_prices) and not projection['identity_conflict'],
        user_agent=user_agent)
    return dict(financial=financial,prices=prices,association=association,projection=projection)


def _separate_saved_link(ticker):
    url='?'+urlencode({'mode':'research','page':'company-workbench','ticker':ticker,'open':'1'})
    return '<p><a href="'+escape(url,quote=True)+'" target="_self">Open the saved research workspace</a></p>'


def render_integrated_company(st_api, ticker, *, profile_scope, saved_available,
                              online_candidate=None, render_saved, render_sources,saved_receipt_only=False,
                              render_notes=None,saved_notes_cik=None):
    """Render one company section, keeping online and saved identities distinct."""
    candidate=online_candidate if isinstance(online_candidate,Mapping) else None
    expected_cik=candidate.get('cik') if candidate else saved_notes_cik
    scope='online:'+str(expected_cik) if candidate else 'notes:'+saved_notes_cik if saved_notes_cik else 'receipts' if saved_receipt_only else 'saved'
    retain_saved_tool_inputs(st_api.session_state,profile_scope,ticker,identity_scope=expected_cik if candidate or saved_notes_cik else None)
    st_api.html(WORKBENCH_STYLE)
    with st_api.container(key='company-workbench-layout'):
        rail,content=st_api.columns([1,4],gap='large')
        with rail,st_api.container(key='company-workbench-rail'):
            st_api.markdown('<p class="company-rail-title">Company research</p>',unsafe_allow_html=True)
            nav_key=f'company-section:{profile_scope}:{ticker}:{scope}'
            if st_api.session_state.get(nav_key) not in dict(SECTIONS):
                st_api.session_state[nav_key]=section_key(st_api.query_params.get('section'))
            with st_api.container(key='company-section-navigation'):
                selected=st_api.radio('Company research sections',tuple(dict(SECTIONS)),format_func=dict(SECTIONS).get,
                                      horizontal=False,label_visibility='collapsed',key=nav_key)
            with st_api.container(key='company-update-actions',horizontal=True,vertical_alignment='center'):
                update_all=st_api.button('Refresh financials and prices',key='company-refresh-all',type='secondary',width='content')
                with st_api.popover('Refresh options'):
                    update_financial=st_api.button('Financials only',key='company-refresh-financials',width='content')
                    update_prices=st_api.button('Prices only',key='company-refresh-prices',width='content')
        with content:
            return _render_company_content(st_api,ticker,profile_scope=profile_scope,scope=scope,
                candidate=candidate,expected_cik=expected_cik,selected=section_key(selected),
                update_all=update_all,update_financial=update_financial,update_prices=update_prices,
                saved_available=saved_available,saved_receipt_only=saved_receipt_only,
                render_saved=render_saved,render_sources=render_sources,render_notes=render_notes)


def _render_company_content(st_api,ticker,*,profile_scope,scope,candidate,expected_cik,selected,
                            update_all,update_financial,update_prices,saved_available,
                            saved_receipt_only,render_saved,render_sources,render_notes=None):
    """The main column stays focused on the selected company's analysis."""
    header=st_api.empty()
    bundle=load_workbench_observations(ticker,st_api.session_state,
        refresh_financials=bool(update_all or update_financial),refresh_prices=bool(update_all or update_prices),
        expected_cik=expected_cik)
    financial,prices,projection=bundle['financial'],bundle['prices'],bundle['projection']
    if selected!='overview' or 'section' in st_api.query_params:
        st_api.query_params['section']=selected
    with st_api.container(key='company-section-body'):
        st_api.markdown('<div id="company-research-sections" data-company-section="'+selected+'"></div>',unsafe_allow_html=True)
        if selected!='overview':
            st_api.markdown('## '+dict(SECTIONS)[selected])
            st_api.caption({
            'financials':'Compare directly reported periods and inspect the drivers.',
            'valuation':'Check the multiple, price date, and qualifying industry references.',
            'notes':'Review saved evidence and record the next research question.',
            'sources':'Inspect company identity, reporting periods, units, and source permissions.',
            }[selected])
        refresh_peers = selected=='valuation' and st_api.button(
            'Refresh peer valuation',key=f'company-refresh-peers:{ticker}:{scope}')
        if refresh_peers:
            with st_api.spinner('Checking company identity, annual earnings, and industry sources…'):
                peer_view=get_online_peer_valuation(ticker,st_api.session_state,
                    refresh_requested=True,expected_cik=expected_cik)
        else:
            peer_view=get_online_peer_valuation(ticker,st_api.session_state,
                refresh_requested=False,expected_cik=expected_cik)

        # The header placeholder precedes the controls, but receives the result of this rerun.
        answers=build_company_answers(ticker,projection,financial,prices,bundle['association'],peer_view)
        attempted={key for key,source in (('financial',financial),('price',prices),('valuation',peer_view))
                   if source.get('status') not in (None,'not_requested')}
        if projection['identity_conflict']:
            answers_html=''
        elif not attempted:
            answers_html='<p class="company-load-prompt">Refresh financials and prices to load company observations.</p>'
        elif selected=='overview':
            answers_html=workbench_metrics_html(ticker,answers,peer_view)
        else:
            answers_html=company_answers_html(tuple(answer for answer in answers if answer['key'] in attempted),compact=True)
        header.markdown(workbench_header_html(ticker,projection,saved_scope=candidate is None,
            title=candidate.get('title') if candidate else None,saved_receipt_only=saved_receipt_only,
            answers_html=answers_html),
            unsafe_allow_html=True)
        if selected=='overview':
            if projection['attempted'] or projection['facts']:
                foreign=validated_foreign_financials(financial)
                if foreign:
                    st_api.markdown(foreign_financials_html(financial),unsafe_allow_html=True)
                else:
                    kind='quarterly' if projection['quarter_count'] else 'annual'
                    st_api.markdown(financial_workspace_html(ticker,financial,period_kind=kind),unsafe_allow_html=True)
            if prices.get('status')!='not_requested':
                with st_api.expander('Price history',expanded=False):
                    st_api.markdown(online_price_history_html(prices),unsafe_allow_html=True)
            with st_api.expander('Identity and model scope',expanded=False):
                st_api.markdown(price_filing_association_html(bundle['association']),unsafe_allow_html=True)
                st_api.caption('Vendor issuer identity, historical continuity, security type, and model eligibility each require their own evidence.')
        elif selected=='financials':
            if financial.get('status')=='not_requested':
                st_api.info('Refresh financials and prices to load reported periods.')
            else:
                foreign=validated_foreign_financials(financial)
                if foreign:
                    st_api.markdown(foreign_financials_html(financial),unsafe_allow_html=True)
                else:
                    kind=st_api.radio('Reporting period',('annual','quarterly'),format_func=lambda x:'Annual' if x=='annual' else 'Quarterly',
                                      horizontal=True,key=f'company-financial-period:{profile_scope}:{ticker}:{scope}')
                    metric=st_api.selectbox('Chart metric',tuple(METRICS),format_func=METRICS.get,
                        key=f'company-financial-metric:{profile_scope}:{ticker}:{scope}')
                    st_api.markdown(financial_workspace_html(ticker,financial,period_kind=kind,metric=metric,limit=8),unsafe_allow_html=True)
                with st_api.expander('Financial observations and available analysis',expanded=False):
                    st_api.markdown(online_company_analysis_html(build_online_company_analysis(financial)),unsafe_allow_html=True)
                with st_api.expander('Full period evidence',expanded=False):
                    st_api.markdown(annual_history_html(financial,compact=True)+quarterly_history_html(financial,compact=True),unsafe_allow_html=True)
            if saved_available and scope=='saved':
                render_saved(selected)
        elif selected in ('valuation','notes'):
            if selected=='notes':
                from src.sec_research_review_ui import render_company_review
                if render_notes is not None:
                    render_notes(bundle)
                    with st_api.expander('Saved SEC evidence',expanded=bool(st_api.query_params.get('sec_pair') or saved_receipt_only)):
                        kwargs={'expected_cik':expected_cik} if expected_cik else {}
                        render_company_review(st_api,ticker,financial,profile_key=profile_scope,**kwargs)
                    return bundle
                if saved_available and candidate is None and not saved_receipt_only and not st_api.query_params.get('sec_pair'):
                    render_saved(selected)
                    with st_api.expander('Saved SEC evidence',expanded=False):
                        render_company_review(st_api,ticker,financial,profile_key=profile_scope)
                    return bundle
                render_company_review(st_api,ticker,financial,profile_key=profile_scope)
            if selected=='valuation':
                if peer_view['status']!='not_requested':
                    st_api.markdown(online_peer_valuation_html(peer_view,compact=True),unsafe_allow_html=True)
                else:
                    st_api.caption('Refresh to compare reported annual diluted P/E with qualifying industry references.')
                with st_api.expander('Listing source continuity', expanded=False):
                    st_api.caption('A complete listing observation from this session can be reused for up to 24 hours with its original dates. Financials and prices are checked independently.')
            if saved_available and scope=='saved':
                render_saved(selected)
            elif selected=='valuation':
                if peer_view['status']=='not_requested':
                    research_context=get_company_security_context(ticker,st_api.session_state,
                        refresh_requested=False,user_agent=None,expected_cik=expected_cik)
                    st_api.markdown(valuation_overview_html(build_valuation_overview(ticker,
                        research_context=research_context),compact=True),unsafe_allow_html=True)
                    st_api.info('Valuation requires a matched share class, financial definition, price date, source rights, and comparison basis.')
                if saved_available:st_api.markdown(_separate_saved_link(ticker),unsafe_allow_html=True)
            else:
                st_api.info('This page replays saved SEC facts. Local models, research journals, and current listing identity require separate qualification.' if saved_receipt_only else
                    'Saved models and journals require a separately matched research identity. SEC evidence can be saved independently.')
                if saved_available:st_api.markdown(_separate_saved_link(ticker),unsafe_allow_html=True)
        else:
            st_api.caption('Each source retains its period, unit, observation date, and permission scope. Saved financials, readiness, and coverage keep their own review process.')
            st_api.markdown(price_filing_association_html(bundle['association']),unsafe_allow_html=True)
            if peer_view['status']!='not_requested':
                st_api.markdown(online_peer_valuation_html(peer_view,sources_only=True),unsafe_allow_html=True)
            render_sources(bundle)
    return bundle
