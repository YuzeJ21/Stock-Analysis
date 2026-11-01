"""Lazy Personal Research compositor over existing, separately qualified evidence."""
from collections.abc import Mapping
from html import escape
import os
from urllib.parse import urlencode

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


def load_workbench_observations(ticker, state, *, refresh_financials=False, refresh_prices=False,
                                expected_cik=None, user_agent=None):
    """Only explicit actions reach transport; ordinary section reruns reuse attempts."""
    user_agent=user_agent if user_agent is not None else os.getenv('SEC_USER_AGENT')
    reason=_mode_reason('research')
    if reason:
        financial=prices={'ticker':ticker,'status':'unavailable','reason':reason}
    else:
        financial=get_company_sec_annual_preview(ticker,state,refresh_requested=refresh_financials,user_agent=user_agent)
        prices=get_online_company_prices(ticker,state,refresh_requested=refresh_prices)
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
    return '<p><a href="'+escape(url,quote=True)+'" target="_self">打开独立的已保存研究集合</a></p>'


def render_integrated_company(st_api, ticker, *, profile_scope, saved_available,
                              online_candidate=None, render_saved, render_sources):
    """Render one company section, keeping online and saved identities distinct."""
    candidate=online_candidate if isinstance(online_candidate,Mapping) else None
    expected_cik=candidate.get('cik') if candidate else None
    scope='online:'+str(expected_cik) if candidate else 'saved'
    header=st_api.empty()
    update_all=st_api.button('更新财报与价格',key='company-refresh-all',type='primary')
    with st_api.expander('分别更新',expanded=False):
        update_financial=st_api.button('只更新财报',key='company-refresh-financials')
        update_prices=st_api.button('只更新价格',key='company-refresh-prices')
    bundle=load_workbench_observations(ticker,st_api.session_state,
        refresh_financials=bool(update_all or update_financial),refresh_prices=bool(update_all or update_prices),
        expected_cik=expected_cik)
    financial,prices,projection=bundle['financial'],bundle['prices'],bundle['projection']
    header.markdown(workbench_header_html(ticker,projection,saved_scope=candidate is None,
        title=candidate.get('title') if candidate else None),unsafe_allow_html=True)
    nav_key=f'company-section:{profile_scope}:{ticker}:{scope}'
    if st_api.session_state.get(nav_key) not in dict(SECTIONS):
        st_api.session_state[nav_key]=section_key(st_api.query_params.get('section'))
    st_api.markdown('<div id="company-research-sections"></div>',unsafe_allow_html=True)
    with st_api.container(key='company-section-navigation'):
        selected=st_api.radio('公司研究分区',tuple(dict(SECTIONS)),format_func=dict(SECTIONS).get,
                              horizontal=True,label_visibility='collapsed',key=nav_key)
    selected=section_key(selected)
    st_api.query_params['section']=selected
    with st_api.container(key='company-section-body'):
        st_api.markdown('## '+dict(SECTIONS)[selected])
        if selected=='overview':
            st_api.markdown(workbench_facts_html(projection),unsafe_allow_html=True)
            if prices.get('status')!='not_requested':
                st_api.markdown(online_price_history_html(prices),unsafe_allow_html=True)
            else:
                st_api.caption('更新后在此查看有日期的价格图和可核对财报摘要。来源或模型缺口不会被填成零。')
            with st_api.expander('身份与模型使用范围',expanded=False):
                st_api.markdown(price_filing_association_html(bundle['association']),unsafe_allow_html=True)
                st_api.caption('当前上市关联不等于独立供应商发行人身份、历史连续性、证券类型或估值资格。')
        elif selected=='financials':
            st_api.caption('同一份在线财报结果供概览和财务页复用。直接报告事实与已保存模型输入分别判断。')
            if financial.get('status')=='not_requested':
                st_api.info('先使用上方更新操作取得财报；不需要为每家公司准备 CSV。')
            else:
                foreign=validated_foreign_financials(financial)
                if foreign:
                    st_api.markdown(foreign_financials_html(financial),unsafe_allow_html=True)
                else:
                    kind=st_api.radio('财报期间',('annual','quarterly'),format_func=lambda x:'年度' if x=='annual' else '季度',
                                      horizontal=True,key=f'company-financial-period:{profile_scope}:{ticker}:{scope}')
                    content=annual_history_html(financial,compact=True) if kind=='annual' else quarterly_history_html(financial,compact=True)
                    if content:st_api.markdown(content,unsafe_allow_html=True)
                    else:st_api.info('该期间的直接申报字段尚未取得或未通过核对；可在数据来源检查原始申报和原因。')
                with st_api.expander('财务观察与可用分析',expanded=False):
                    st_api.markdown(online_company_analysis_html(build_online_company_analysis(financial)),unsafe_allow_html=True)
        elif selected in ('valuation','notes'):
            if saved_available and candidate is None:
                render_saved(selected)
            elif selected=='valuation':
                research_context=get_company_security_context(ticker,st_api.session_state,
                    refresh_requested=False,user_agent=None,expected_cik=expected_cik)
                st_api.markdown(valuation_overview_html(build_valuation_overview(ticker,
                    research_context=research_context),compact=True),unsafe_allow_html=True)
                st_api.info('在线财报与价格仅供分别阅读。估值还需要核对股类、财务定义、价格日期、来源权限和同行依据。')
                if saved_available:st_api.markdown(_separate_saved_link(ticker),unsafe_allow_html=True)
            else:
                st_api.info('在线公司身份尚未与已保存研究集合核对，当前页面不会读取或写入同代码的已保存记录。')
                if saved_available:st_api.markdown(_separate_saved_link(ticker),unsafe_allow_html=True)
        else:
            st_api.caption('来源、期间、单位、观察日期与权限分别保留；在线查询不更新正式财务、readiness 或覆盖统计。')
            st_api.markdown(price_filing_association_html(bundle['association']),unsafe_allow_html=True)
            render_sources(bundle)
    return bundle
