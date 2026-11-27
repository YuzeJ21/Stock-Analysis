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
from src.mrvl_earnings_review_ui import mrvl_earnings_review_html, mrvl_earnings_caution_html
from src.company_workbench_presentation import (
    WORKBENCH_STYLE, METRICS, financial_workspace_html, workbench_metrics_html,
)


def retain_saved_tool_inputs(state,profile_scope,ticker,*,identity_scope=None):
    """Keep scoped editable inputs across lazy panes, never action or consent state."""
    keys=list(scenario_lab_widget_keys(profile_scope,ticker).values()) if identity_scope is None else []
    online_prefix=f'online-scenario:{profile_scope}:{ticker}:' + (str(identity_scope)+':' if identity_scope else '')
    keys.extend(key for key in state if key.startswith(online_prefix) and ':input:' in key)
    keys.append(authoring_session_key(profile_scope,ticker,'kind',identity_scope=identity_scope))
    keys.extend(authoring_session_key(profile_scope,ticker,f'field:{kind}:{name}',identity_scope=identity_scope)
                for kind,fields in FIELD_CONTRACTS.items() for name in fields)
    for key in keys:
        if key in state:state[key]=state[key]


def load_workbench_observations(ticker, state, *, refresh_financials=False, refresh_prices=False,
                                exact_quarter_requested=False, expected_cik=None, user_agent=None):
    """Only explicit actions reach transport; ordinary section reruns reuse attempts."""
    user_agent=user_agent if user_agent is not None else os.getenv('SEC_USER_AGENT')
    reason=_mode_reason('research')
    if reason:
        financial=prices={'ticker':ticker,'status':'unavailable','reason':reason}
    else:
        financial=get_company_sec_annual_preview(ticker,state,
            refresh_requested=refresh_financials or exact_quarter_requested,user_agent=user_agent,
            exact_quarter_requested=exact_quarter_requested,expected_cik=expected_cik)
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


def render_saved_company_replay(st, snapshot, *, baseline=None):
    """Render a validated historical context without consulting current observations."""
    from src.online_research_tools_ui import (
        _business_trend, _forward_decision, _scenario, _scenario_key, _scenario_result,
        filing_status_html, render_saved_online_snapshot,
    )
    from src.research_workspace import open_research_monitor

    if _mode_reason('research'):
        st.info('Personal online research replay is unavailable in this workspace.')
        return
    context = snapshot['context']
    ticker, profile, cik = (snapshot[key] for key in ('ticker', 'profile_key', 'sec_cik'))
    peer_view = context.get('peer_read_through') or {}
    scope = (peer_view.get('subject_source_context') or {}).get('selected_security_scope')
    invalid_sap_peer = False
    if ticker == 'SAP' and isinstance(scope, dict):
        from src.sec_sap_snapshot_evidence import saved_sap_numeric_observation_indices

        invalid_sap_peer = saved_sap_numeric_observation_indices(scope, context=context) is None
        if invalid_sap_peer:
            from src.online_peer_valuation import _empty

            peer_view = _empty(ticker, 'selected_security_scope_unverified')
    selected = section_key(st.query_params.get('section', 'notes'))
    nav_key = f'company-section:{profile}:{ticker}:notes:{cik}'
    retain_saved_tool_inputs(st.session_state, profile, ticker, identity_scope=cik)

    def select_section():
        st.query_params['section'] = st.session_state[nav_key]

    st.html(WORKBENCH_STYLE)
    with st.container(key='company-workbench-layout'):
        rail, content = st.columns([1, 4], gap='large')
        with rail, st.container(key='company-workbench-rail'):
            st.markdown('<p class="company-rail-title">Company research</p>', unsafe_allow_html=True)
            st.session_state[nav_key] = selected
            with st.container(key='company-section-navigation'):
                st.radio('Company research sections', tuple(dict(SECTIONS)), format_func=dict(SECTIONS).get,
                         label_visibility='collapsed', key=nav_key, on_change=select_section)
            current_url = '?' + urlencode(dict(mode='research', page='company-workbench',
                                                ticker=ticker, online='1', section=selected))
            st.markdown(f'<p><a href="{escape(current_url, quote=True)}" target="_self">Open current research</a></p>',
                        unsafe_allow_html=True)
        with content, st.container(key='company-section-body'):
            st.markdown(f'<div id="company-research-sections" data-company-section="{selected}"></div>',
                        unsafe_allow_html=True)
            st.markdown(f'# {escape(ticker)}')
            st.markdown('## ' + dict(SECTIONS)[selected])
            with st.expander('Saved online research · replay and compare', expanded=True):
                st.info('Historical replay · ' + snapshot['observed_at'])
                st.caption('Snapshot ' + snapshot['snapshot_id'][:12] + ' · SEC CIK ' + cik)
                if invalid_sap_peer:
                    st.warning('Saved SAP peer evidence could not be verified. Other filing fields keep their own evidence checks.')
                if selected in {'overview', 'valuation'}:
                    if peer_view.get('status') in {None, 'not_requested'}:
                        st.caption('Peer valuation was not captured in this snapshot.')
                    else:
                        st.markdown(online_peer_valuation_html(peer_view, compact=True), unsafe_allow_html=True)
                if selected in {'overview', 'financials'}:
                    st.markdown(filing_status_html(context), unsafe_allow_html=True)
                    _business_trend(st, context)
                if selected == 'valuation':
                    from src.online_peer_valuation_ui import sap_price_basis_html

                    basis = sap_price_basis_html(context)
                    if basis:
                        st.markdown(basis, unsafe_allow_html=True)
                    from src.sap_fx_review_ui import render_sap_fx_review

                    render_sap_fx_review(st, context)
                    if context.get('scenario'):
                        with st.expander('Saved Scenario Lab result', expanded=False):
                            _scenario_result(st, context['scenario'])
                    st.caption('Scenario Lab drafts use the saved annual revenue basis. Edits are separate from the saved result.')
                    _scenario(st, context, _scenario_key(profile, ticker, cik))
                if selected == 'notes':
                    from src.company_research_notes import saved_company_notes_scope

                    thesis = (context.get('notes_summary') or {}).get('current_thesis')
                    if thesis:
                        st.text(thesis)
                    if saved_company_notes_scope(ticker, profile, sec_cik=cik) is not None:
                        notes_url = '?' + urlencode(dict(mode='research', page='company-workbench',
                                                        ticker=ticker, section='notes', notes_cik=cik))
                        st.markdown(f'<p><a href="{escape(notes_url, quote=True)}" target="_self">Open issuer notes</a></p>',
                                    unsafe_allow_html=True)
                    _forward_decision(st, context)
                if selected == 'sources':
                    if ticker == 'SAP':
                        from src.online_peer_valuation_ui import saved_depositary_security_html

                        security = saved_depositary_security_html(context)
                        if security:
                            st.markdown(security, unsafe_allow_html=True)
                        from src.sap_fx_review_ui import render_sap_fx_review

                        render_sap_fx_review(st, context)
                    st.json(context.get('source_receipts') or [], expanded=False)
                if selected == 'notes' or baseline is not None:
                    render_saved_online_snapshot(st, snapshot, baseline=baseline)
                else:
                    with st.expander('Exact saved evidence', expanded=False):
                        st.json(context, expanded=False)
                st.button('Return to this filing pair in Monitor' if baseline is not None else 'Open Monitor',
                          key='online-research-replay-monitor', on_click=open_research_monitor,
                          args=(st, ticker, profile))


def render_integrated_company(st_api, ticker, *, profile_scope, saved_available,
                              online_candidate=None, render_saved, render_sources,saved_receipt_only=False,
                              render_notes=None,saved_notes_cik=None,enable_online_tools=False):
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
                update_all=st_api.button('Research company' if enable_online_tools else 'Refresh financials and prices',key='company-refresh-all',type='secondary',width='content')
                with st_api.popover('Refresh options'):
                    update_financial=st_api.button('Financials only',key='company-refresh-financials',width='content')
                    update_exact_quarter=enable_online_tools and st_api.button(
                        'Refresh exact SEC quarter',key='company-refresh-exact-quarter',width='content')
                    update_prices=st_api.button('Prices only',key='company-refresh-prices',width='content')
                    if enable_online_tools and not os.getenv('SEC_USER_AGENT'):
                        from src.online_research_tools_ui import sec_request_identification
                        sec_request_identification(st_api,show_input=True)
        with content:
            return _render_company_content(st_api,ticker,profile_scope=profile_scope,scope=scope,
                candidate=candidate,expected_cik=expected_cik,selected=section_key(selected),
                update_all=update_all,update_financial=update_financial,update_prices=update_prices,
                update_exact_quarter=update_exact_quarter,
                saved_available=saved_available,saved_receipt_only=saved_receipt_only,
                render_saved=render_saved,render_sources=render_sources,render_notes=render_notes,
                enable_online_tools=enable_online_tools)


def _render_company_content(st_api,ticker,*,profile_scope,scope,candidate,expected_cik,selected,
                            update_all,update_financial,update_prices,update_exact_quarter,saved_available,
                            saved_receipt_only,render_saved,render_sources,render_notes=None,enable_online_tools=False):
    """The main column stays focused on the selected company's analysis."""
    header=st_api.empty()
    user_agent = os.getenv('SEC_USER_AGENT')
    if enable_online_tools:
        from src.online_research_tools_ui import SEC_AGENT_KEY, prepare_online_tools, render_online_tools, filing_status_html, qualify_current_answers, qualify_peer_view
        user_agent = user_agent or st_api.session_state.get(SEC_AGENT_KEY)
    bundle=load_workbench_observations(ticker,st_api.session_state,
        refresh_financials=bool(update_all or update_financial),refresh_prices=bool(update_all or update_prices),
        exact_quarter_requested=bool(update_exact_quarter),
        expected_cik=expected_cik,user_agent=user_agent)
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
        if refresh_peers or (enable_online_tools and update_all):
            with st_api.spinner('Checking company identity, annual earnings, and industry sources…'):
                peer_view=get_online_peer_valuation(ticker,st_api.session_state,
                    refresh_requested=True,expected_cik=expected_cik,user_agent=user_agent)
        else:
            peer_view=get_online_peer_valuation(ticker,st_api.session_state,
                refresh_requested=False,expected_cik=expected_cik)

        if enable_online_tools:
            context = prepare_online_tools(ticker,bundle,st_api.session_state,
                profile_key=profile_scope,expected_cik=expected_cik)
            peer_view = qualify_peer_view(peer_view,context)
            bundle['peer_view'] = peer_view

        # The header placeholder precedes the controls, but receives the result of this rerun.
        answers=build_company_answers(ticker,projection,financial,prices,bundle['association'],peer_view)
        if enable_online_tools:answers=qualify_current_answers(answers,context)
        attempted={key for key,source in (('financial',financial),('price',prices),('valuation',peer_view))
                   if source.get('status') not in (None,'not_requested')}
        if projection['identity_conflict']:
            answers_html=''
        elif not attempted:
            answers_html='<p class="company-load-prompt">Refresh financials and prices to load company observations.</p>'
        elif selected=='overview':
            answers_html=workbench_metrics_html(ticker,answers,peer_view,projection=projection,
                                               research_context=context if enable_online_tools else None)
        else:
            answers_html=company_answers_html(tuple(answer for answer in answers if answer['key'] in attempted),compact=True)
        header.markdown(workbench_header_html(ticker,projection,saved_scope=candidate is None,
            title=candidate.get('title') if candidate else None,saved_receipt_only=saved_receipt_only,
            answers_html=answers_html),
            unsafe_allow_html=True)
        if enable_online_tools:
            st_api.markdown(filing_status_html(context),unsafe_allow_html=True)
            if financial.get('exact_quarter_requested') is True and selected not in {'financials', 'sources'}:
                st_api.caption('See Financial Trends for the exact SEC quarter and any filing gaps.')
        if selected=='overview':
            if projection['attempted'] or projection['facts']:
                foreign=validated_foreign_financials(financial)
                if projection.get('bank_interim'):
                    from src.sec_exact_filing_view import bank_interim_html
                    st_api.markdown(bank_interim_html(projection['bank_interim']),unsafe_allow_html=True)
                elif projection.get('bank_annual'):
                    from src.sec_exact_filing_view import bank_annual_html
                    st_api.markdown(bank_annual_html(projection['bank_annual'],show_history=False),unsafe_allow_html=True)
                elif projection['native_quarter_selected']:
                    from src.sec_online_quarter_view import native_quarter_html
                    st_api.markdown(native_quarter_html(projection['native_quarter_archive'],show_comparisons=False),unsafe_allow_html=True)
                elif foreign and not projection.get('annual_archive'):
                    st_api.markdown(foreign_financials_html(financial),unsafe_allow_html=True)
                else:
                    kind=projection['period_kind'] or ('quarterly' if projection['quarter_count'] else 'annual')
                    metric=(projection.get('comparative') or {}).get('field','revenue')
                    st_api.markdown(financial_workspace_html(ticker,financial,period_kind=kind,metric=metric),unsafe_allow_html=True)
            if prices.get('status')!='not_requested':
                with st_api.expander('Price history',expanded=False):
                    st_api.markdown(online_price_history_html(prices),unsafe_allow_html=True)
            with st_api.expander('Identity and model scope',expanded=False):
                st_api.markdown(price_filing_association_html(bundle['association']),unsafe_allow_html=True)
                st_api.caption('Vendor issuer identity, historical continuity, security type, and model eligibility each require their own evidence.')
        elif selected=='financials':
            if financial.get('status')=='not_requested':
                st_api.info('Refresh financials and prices to load reported periods.')
            elif projection.get('bank_annual'):
                from src.sec_exact_filing_view import bank_annual_html, bank_interim_html, bank_quarter_comparison_html
                interim=projection.get('bank_interim')
                if interim:
                    pair=projection.get('bank_interim_comparison')
                    if pair:
                        st_api.markdown(bank_quarter_comparison_html(interim,pair),unsafe_allow_html=True)
                    st_api.markdown(bank_interim_html(interim),unsafe_allow_html=True)
                st_api.markdown(bank_annual_html(projection['bank_annual'],show_interim_gap=not interim),unsafe_allow_html=True)
            else:
                from src.sec_online_quarter_view import archive_quarter_html, native_quarter_html
                st_api.markdown(archive_quarter_html(financial)+native_quarter_html(projection['native_quarter_archive']),unsafe_allow_html=True)
                foreign=validated_foreign_financials(financial)
                if projection.get('annual_archive'):
                    default_metric=(projection.get('comparative') or {}).get('field','revenue')
                    metric=st_api.selectbox('Chart metric',tuple(METRICS),format_func=METRICS.get,
                        index=tuple(METRICS).index(default_metric),key=f'company-financial-metric:{profile_scope}:{ticker}:{scope}')
                    st_api.markdown(financial_workspace_html(ticker,financial,period_kind='annual',metric=metric,limit=8),unsafe_allow_html=True)
                    if foreign:
                        with st_api.expander('Structured annual, quarter and interim history',expanded=False):
                            st_api.markdown(foreign_financials_html(financial),unsafe_allow_html=True)
                elif foreign:
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
            if enable_online_tools:render_online_tools(st_api,selected,bundle)
            if saved_available and scope=='saved':
                render_saved(selected)
        elif selected in ('valuation','notes'):
            if selected=='notes':
                from src.sec_research_review_ui import render_company_review
                if render_notes is not None:
                    render_notes(bundle)
                    if enable_online_tools:render_online_tools(st_api,selected,bundle)
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
                earnings_caution = mrvl_earnings_caution_html(financial, expected_cik=expected_cik)
                if earnings_caution:
                    st_api.markdown(earnings_caution, unsafe_allow_html=True)
                if peer_view['status']!='not_requested':
                    st_api.markdown(online_peer_valuation_html(peer_view,compact=True),unsafe_allow_html=True)
                else:
                    st_api.caption('Refresh to compare reported annual diluted P/E with qualifying industry references.')
                earnings_review = mrvl_earnings_review_html(financial, expected_cik=expected_cik)
                if earnings_review:
                    st_api.markdown(earnings_review, unsafe_allow_html=True)
                with st_api.expander('Listing source continuity', expanded=False):
                    st_api.caption('A complete listing observation from this session can be reused for up to 24 hours with its original dates. Financials and prices are checked independently.')
                if enable_online_tools:render_online_tools(st_api,selected,bundle)
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
            earnings_review = mrvl_earnings_review_html(financial, expected_cik=expected_cik, sources_only=True)
            if earnings_review:
                st_api.markdown(earnings_review, unsafe_allow_html=True)
            render_sources(bundle)
            if enable_online_tools:render_online_tools(st_api,selected,bundle)
    return bundle
