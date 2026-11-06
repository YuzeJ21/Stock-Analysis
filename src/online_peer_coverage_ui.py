"""Compact sample coverage with explicit actions and source-only session progress."""
from collections.abc import Mapping
from html import escape
import os
from urllib.parse import urlencode

from src.online_peer_coverage import DEFAULT_SAMPLE, DISCOVER_SAMPLE, _coverage_session, get_peer_coverage
from src.online_peer_valuation import QCOM_SIC_BASIS, _symbol
from src.online_peer_valuation_ui import STYLE,_text,_reason,_link,online_peer_valuation_html

_INDUSTRIES={'semiconductors':'半导体','software-infrastructure':'基础软件','drug-manufacturers-general':'综合制药',
 'household-personal-products':'家庭与个人用品','restaurants':'餐饮','farm-heavy-construction-machinery':'农业与工程机械',
 'utilities-regulated-electric':'受监管电力','reit-retail':'零售 REIT','telecom-services':'电信服务','banks-diversified':'多元化银行',
 'oil-gas-integrated':'综合油气','gold':'黄金'}
_QCOM_PENDING = {
    'peer_not_collected': '待核查 · 尚未取得此候选的来源。',
    'source_paused_after_repeated_failures': '待核查 · 连续来源失败，候选核查已暂停。',
}


def qcom_candidate_display(row):
    """Share the counts and reason labels across the two Discover views."""
    if row.get('ticker') != 'QCOM' or row.get('candidate_basis') != QCOM_SIC_BASIS:
        return None
    total, checked, pending = (row.get(key) for key in (
        'candidate_count', 'checked_candidate_count', 'pending_candidate_count',
    ))
    if any(type(value) is not int or value < 0 for value in (total, checked, pending)) or checked + pending != total:
        return None
    progress = f'SEC SIC 3663 候选 · 候选已核查 {checked} / {total}'
    if pending:
        progress += f' · 候选待核查 {pending} 家'
    outcomes = []
    for item in row.get('excluded') or ():
        if isinstance(item, Mapping) and _symbol(item.get('ticker')) and isinstance(item.get('reason'), str):
            reason = item['reason']
            text = _QCOM_PENDING.get(reason)
            description = text or f'未通过 · {_reason(reason)}'
            audit = item.get('annual_eps_audit')
            if isinstance(audit, Mapping) and audit.get('reason') and audit['reason'] != reason:
                description += f' · {_reason(audit["reason"])}'
            links = []
            for key, label in (('listing_venue_evidence', 'NYSE American 交易所核对'),
                               ('annual_eps_audit', '10-K 年度摊薄 EPS 原文')):
                evidence = item.get(key)
                if isinstance(evidence, Mapping) and evidence.get('source_url'):
                    links.append((evidence['source_url'], label))
            outcomes.append((item['ticker'], description, links))
    return progress, outcomes


def _qcom_candidate_detail_html(display):
    progress, outcomes = display
    html = ('<section aria-label="QCOM SEC SIC 3663 候选"><p><strong>'+escape(progress)+'</strong></p>'
            '<p>候选仍须通过相同供应商行业、同日收盘价和财年起止日期核对。至少 3 家通过后才显示比较。</p>')
    if outcomes:
        html += '<ul>'+''.join(
            f'<li><strong>{escape(ticker)}</strong> · {escape(text)}'
            + ''.join(' · '+_link(url,label) for url, label in links)+'</li>'
            for ticker, text, links in outcomes)+'</ul>'
    return html+'</section>'


def _industry(row):
    key=row.get('industry_key')
    return _INDUSTRIES.get(key,row.get('industry_label') or key.replace('-',' ') if isinstance(key,str) else '行业待核对')


def _fraction(number,total):return str(number)+' / '+str(total)


def peer_coverage_html(view):
    if not isinstance(view,Mapping) or view.get('status')!='inspection_only':
        return '<section class="online-peer-valuation" aria-label="Industry peer coverage"><h3>行业同行估值覆盖</h3><p>会话记录或当前来源未通过核对，请重新开始样本；没有自动补取来源。</p></section>'
    n=view['requested_count']
    html=STYLE+'<section class="online-peer-valuation" aria-label="Industry peer coverage"><h3>行业同行估值覆盖</h3><p>本次 '+str(n)+' 个指定查询对象；数字只描述本样本，不代表完整美国市场或完整行业。</p>'
    stats=[('已核查',view['attempted_count']),('本公司年度 P/E 可用',view['subject_pe_count']),('同行比较可用',view['comparison_count']),('待核查',view['pending_count'])]
    html+='<dl class="peer-stats">'+''.join('<div><dt>'+k+'</dt><dd>'+_fraction(v,n)+'</dd></div>' for k,v in stats)+'</dl>'
    html+='<p>已完成参照核查：'+_fraction(view['reference_assessed_count'],n)+'。本公司 P/E 可用不等于同行比较可用；至少 3 家完整通过同口径规则才给出倍数差异。</p>'
    html+='<p>进度仅在会话内继续，重新开始会清空本样本进度。来源按原观察时间重新核对；过期后保留缺口，不会自动刷新。</p>'
    if view['paused']:html+='<p><strong>连续两家公司来源失败，已暂停后续查询。可明确重试已核查公司后继续。</strong></p>'
    html+='<table aria-label="行业样本覆盖"><thead><tr>'+''.join('<th scope="col">'+s+'</th>' for s in ('行业 / SIC','指定对象','已核查','本公司 P/E','同行比较'))+'</tr></thead><tbody>'
    for group in view['by_industry']:
        cells=[('行业 / SIC',_text(_industry(group))+' · '+_text(group.get('sic'))),('指定对象',str(group['requested_count'])),
               ('已核查',_fraction(group['attempted_count'],group['requested_count'])),('本公司 P/E',_fraction(group['subject_pe_count'],group['requested_count'])),
               ('同行比较',_fraction(group['comparison_count'],group['requested_count']))]
        html+='<tr>'+''.join('<td data-label="'+k+'">'+v+'</td>' for k,v in cells)+'</tr>'
    html+='</tbody></table><details><summary>逐家公司查看状态、缺失原因与来源</summary>'
    for row in view['rows']:
        state='同行比较可用' if row['comparison_state']=='available' else '本公司 P/E 可用，同行比较暂缺' if row['subject_pe_state']=='available' else '暂缺本公司 P/E' if row['attempted'] else '待核查'
        html+='<details><summary>'+_text(row['ticker'])+' · '+state+'</summary><p>'+_text(_industry(row))+' · 供应商行业 '+_text(row.get('industry_key'))+' · SEC SIC '+_text(row.get('sic'))+' · 观察 '+_text(row.get('attempted_at'))+'</p>'
        if not row['attempted']:html+='<p>尚未发起该对象的来源查询，同行尚未核查。</p>'
        elif row['reference_state']=='not_assessed_subject_blocked':html+='<p>同行尚未核查；先处理本公司来源或身份缺口，不能把未核查写成零家同行。</p>'
        else:html+='<p>通过的参照 '+str(row['accepted_reference_count'])+' 家；'+('参照核查未完成，保留暂停项。' if row['reference_state']=='partially_assessed' else '本次已检查有上限的参照候选。')+'</p>'
        if candidates := qcom_candidate_display(row):
            html += '<p>'+escape(candidates[0])+'</p>'
        if row['comparison_state']!='available':html+='<p>第一项阻碍：'+('尚未核查。' if not row['attempted'] else _text(_reason(row['primary_reason'])))+'</p>'
        if row.get('selected_security_state') in {'supported_common','inspection_only'}:
            html+='<p>所选证券依据：'+('已核对所选普通股与年度收益口径，估值资格仍分别检查。' if row['selected_security_state']=='supported_common' else _text(_reason(row.get('selected_security_reason'))))+'</p>'
        url='?'+urlencode(dict(mode='research',page='company-workbench',ticker=row['ticker'],online='1',section='valuation'))
        html+='<p><a href="'+escape(url,quote=True)+'" target="_self">在线打开公司估值页</a></p>'
        for ref in row['source_refs']:
            html+='<p>'+_link(ref.get('source_url'),'来源观察')+' · '+_text(ref.get('observed_at'))+' · SHA-256 <code>'+_text(ref.get('payload_sha256') or ref.get('normalized_sha256'))+'</code></p>'
            if ref.get('body_sha256'):html+='<p>已核对正文 SHA-256 <code>'+_text(ref['body_sha256'])+'</code></p>'
        html+='</details>'
    html+='</details><details><summary>主要缺口与候选参照排除原因</summary><h4>主要缺口</h4><p>每个目标只计第一项阻碍；不表示后续所有规则已经核查。</p><ul>'
    html+=''.join('<li>'+_text(_reason(reason))+' · '+str(count)+' 个目标</li>' for reason,count in view['primary_reason_counts'].items()) or '<li>目前没有已记录的主要缺口。</li>'
    html+='</ul><h4>候选参照排除原因</h4><p>这是各目标的候选检查次数，可能重复核查同一参照，不是唯一发行人数量。</p><ul>'
    html+=''.join('<li>'+_text(_reason(reason))+' · '+str(count)+' 次</li>' for reason,count in view['excluded_reason_counts'].items()) or '<li>尚无候选排除记录。</li>'
    html+='</ul><p>适配器调用 '+str(view['adapter_operation_count'])+' 次；这是组件调用次数，不是 HTTP 请求数。每次最多 12 家其他候选，列表不是完整行业。</p></details><p>仅个人研究；商业与再分发权限未核准。此样本不更新正式数据、已保存估值或发行人覆盖检查点。</p></section>'
    return html


def render_peer_coverage(st_api, *, tickers=DEFAULT_SAMPLE):
    """Callbacks finish before the rerender; ordinary rendering never requests sources."""
    def act(kind):
        with st_api.spinner('正在核对一个查询对象及其同行来源…'):
            get_peer_coverage(st_api.session_state,inspect_requested=kind=='next',reset_requested=kind=='reset',
                inspect_ticker=st_api.session_state.get('peer-coverage-pending') if kind=='selected' else None,
                retry_ticker=st_api.session_state.get('peer-coverage-retry') if kind=='retry' else None,
                tickers=tickers,user_agent=os.getenv('SEC_USER_AGENT'))
    st_api.markdown('<div id="peer-coverage-sample"></div>',unsafe_allow_html=True)
    with st_api.expander('同行估值覆盖 · 行业样本',expanded=False):
        st_api.caption('按公司逐项核查年度 P/E 与同行可比性；来源缺失、未核查对象都会保留。')
        _,raw=_coverage_session(st_api.session_state,list(tickers));raw=raw if isinstance(raw,Mapping) else {}
        requested=raw.get('requested_tickers',tickers);requested=requested if isinstance(requested,(list,tuple)) else tickers
        packets=raw.get('packets',{});packets=packets if isinstance(packets,Mapping) else {}
        attempted=[t for t in requested if _symbol(t) and t in packets]
        paused=type(raw.get('source_failure_streak')) is int and raw['source_failure_streak']>=2
        st_api.button('核查下一家公司',key='peer-coverage-next',disabled=paused or len(attempted)==len(requested),on_click=act,args=('next',))
        if tuple(tickers) == DISCOVER_SAMPLE:
            pending = [ticker for ticker in tickers if ticker not in attempted]
            if pending:
                choice = st_api.selectbox('待核查公司',pending,index=None,key='peer-coverage-pending',
                    placeholder='选择一个待核查的代码',disabled=paused)
                st_api.button('核查所选公司',key='peer-coverage-inspect-selected',disabled=paused or choice is None,
                    on_click=act,args=('selected',))
        if attempted:
            st_api.selectbox('重新核查公司',attempted,key='peer-coverage-retry')
            st_api.button('重试所选公司',key='peer-coverage-retry-action',on_click=act,args=('retry',))
        st_api.button('重新开始样本',key='peer-coverage-reset',on_click=act,args=('reset',))
        selected = st_api.selectbox(
            '查看本次核查详情', attempted, index=None, key='peer-coverage-detail',
            placeholder='选择已核查公司',
        ) if attempted else None
        result=get_peer_coverage(st_api.session_state,tickers=tickers,user_agent=os.getenv('SEC_USER_AGENT'),detail_ticker=selected)
        if detail := result.get('selected_detail'):
            st_api.caption(f"{detail['ticker']} · 本会话核查详情。按原观察时间重新校验。")
            selected_row = next((row for row in result.get('rows', ()) if row.get('ticker') == detail['ticker']), None)
            if selected_row and (candidates := qcom_candidate_display(selected_row)):
                st_api.markdown(_qcom_candidate_detail_html(candidates), unsafe_allow_html=True)
            st_api.markdown(online_peer_valuation_html(detail, show_coverage_link=False),unsafe_allow_html=True)
        st_api.markdown(peer_coverage_html(result),unsafe_allow_html=True)
        return result
