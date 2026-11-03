"""Explicit company receipt actions, shared by company records and Monitor."""
from html import escape
from pathlib import Path
import os
from src.sec_exact_filing import get_company_filing_preview
from src.online_company_identity import _mode_reason
from src.sec_research_review import (
    MAX_BYTES, attach_operating_income_check, capture_review, compare_reviews, encode_review, list_reviews, load_review, save_review,
    review_queue, _ticker,
)
from src.company_sec_online_preview import _utc_timestamp

PROJECT_ROOT=Path(__file__).resolve().parent.parent


def saved_review_route_available(ticker,profile_key):
    """Saved evidence permits offline inspection, never current listing eligibility."""
    if not _ticker(ticker) or not isinstance(profile_key,str):return False
    try:return bool(list_reviews(PROJECT_ROOT,profile_key,ticker))
    except (ValueError,OSError):return False


LABELS={'revenue':'收入','operating_income':'营业利润','cash_from_operations':'经营现金流',
        'capital_expenditures':'资本支出','all':'整个证据包'}
REASONS={'source_evidence_unreviewed':'直接来源证据尚未通过核查，需检查具体申报字段',
    'direct_field_missing':'没有同一申报、同一期间的直接字段，需核对原文',
    'prior_direct_field_missing':'上一份证据缺少直接字段', 'baseline_missing':'尚缺第二份可比较的保存证据',
    'duration_mismatch':'期间长度或起止日期不一致', 'period_end_mismatch':'报告期不同',
    'concept_mismatch':'财务定义不同', 'unit_mismatch':'单位或币种不同',
    'rights_policy_changed':'来源权限登记已变化，需重新核查', 'profile_key_mismatch':'研究集合不同',
    'same_source_digest_conflict':'相同来源摘要对应不同字段，需核查证据一致性',
    'rights_mismatch':'字段权限不一致', 'raw_source_conflict':'原始来源包含冲突值，需核查申报语境',
    'raw_source_value_invalid':'原始来源数值无法通过核查'}
REASONS.update({
    'matching_direct_native_unit_fact_unavailable':'具体申报中没有匹配的标准营业利润直接事实；税前收益、分部指标和 EBITDA 不能代替',
    'conflicting_direct_facts':'具体申报中有冲突的营业利润直接事实，暂不取值',
    'exact_direct_fact_rights_held':'原文存在直接字段，但该档案来源的字段权限尚未登记，暂不取值',
    'exact_direct_fact_unusable':'原文直接字段未通过数值或来源核验，暂不取值'})
STATUS={'unchanged':'未变化','changed':'发现变化，需核查','withheld':'口径不一致，保留缺口',
        'gaps_changed':'缺口状态变化，需核查','baseline_missing':'已保存，等待比较基线'}
STATUS['review_changed']='核查依据变化，财务数值未变'
REASONS.update({'ticker_mismatch':'公司不同，不能作为同公司财报变化比较',
    'sec_cik_mismatch':'发行人身份不同，需独立核对衔接关系'})


def _label(packet):
    stamp=_utc_timestamp(packet['saved_at']).strftime('%m/%d %H:%M')
    return f"{packet['period_end']} · {stamp} · {packet['receipt_id'][:6]}"


def _gaps_html(result):
    rows=''.join('<li><strong>'+escape(LABELS.get(g['field'],g['field']))+'</strong> · '+
        escape(REASONS.get(g['reason'],g['reason']))+'</li>' for g in result['gaps'])
    return '<ul>'+rows+'</ul>' if rows else '<p>这四个直接字段没有待核查缺口。完整估值及投资判断仍需其他证据。</p>'


def _render_comparison(st,result):
    label=STATUS[result['status']]
    if result['status']=='unchanged':st.success(label+' · 已保存的字段数值与口径一致。')
    elif result['status']=='changed':st.warning(label)
    else:st.info(label)
    if result.get('review_changes'):st.caption('来源核查依据已更新；这本身不是财务数值修订。')
    for change in result['changes']:
        left,right=change['before'],change['after']
        st.markdown('**'+LABELS[change['field']]+'**')
        st.write(f"{left['value']:,} → {right['value']:,} {right['unit']}")
        st.caption('变化维度：'+', '.join(change['changed_dimensions'])+
            ' · 原申报 '+left['accession']+' · 当前申报 '+right['accession'])
    st.markdown(_gaps_html(result),unsafe_allow_html=True)


def _render_exact_check(st, packet, *, show_reason=True):
    check=packet.get('operating_income_check')
    if not check:return
    st.markdown('**营业利润 · 原始申报已核查，缺口保留**')
    if show_reason:st.markdown(REASONS[check['reason']])
    st.markdown('[查看已核查的 SEC 原始申报]('+check['source_url']+')')
    st.caption(check['form']+' · '+check['accession']+' · '+check['period_start']+' 至 '+check['period_end']+
        ' · '+check['taxonomy']+':'+check['concept']+' · '+check['unit'])
    st.caption('申报日 '+check['filed']+' · 接收时间 '+check['accepted_at']+' · 核查观察 '+check['observed_at'])
    st.caption('原文仅供个人研究核查；本包只保存核查元数据，不纳入档案数值，也未扩大来源权限。')
    with st.expander('原始申报核查摘要',expanded=False):
        st.code(check['payload_sha256'],language=None)
        st.caption('来源权限：'+check['rights_status'])


def _check_candidate(st, candidate, scope):
    eligible=candidate is not None and any(g['field']=='operating_income' for g in candidate['gaps'])
    key='sec-review-exact-result:'+scope
    # Bind the action to this Companyfacts observation, not just a ticker or year.
    anchor={k:v for k,v in candidate.items() if k not in {'saved_at','receipt_id'}} if eligible else None
    if st.button('核查营业利润原始申报',key='sec-review-exact:'+scope,disabled=not eligible):
        st.session_state[key]={'anchor':anchor,'preview':{'status':'withheld'}}
        with st.spinner('正在核对 SEC 具体申报与当前财报口径…'):
            source=get_company_filing_preview('NEM',st.session_state,period_kind='annual',
                refresh_requested=True,user_agent=os.getenv('SEC_USER_AGENT'),expected_cik='0001164727')
        st.session_state[key]={'anchor':anchor,'preview':source}
    cached=st.session_state.get(key)
    if eligible and isinstance(cached,dict) and cached.get('anchor')==anchor:
        try:
            candidate=attach_operating_income_check(candidate,cached['preview'])
            st.info('原始申报核查已完成。点击下方保存，将本次核查随证据一起保留。')
            with st.expander('本次待保存的核查详情',expanded=False):
                _render_exact_check(st,candidate)
        except (ValueError,TypeError,KeyError):
            st.warning('本次原始申报核查未接入：来源不可用或申报、期间、单位不匹配。原缺口保留，请核对「数据来源」。')
    return candidate


CONTROL_STYLE='''<style>
.st-key-sec-review-panel [data-testid="stDownloadButton"] button,
.st-key-sec-review-panel [data-testid="stDownloadButton"] button p,
.st-key-sec-review-panel [data-testid="stDownloadButton"] button span,
.sec-review-link {background:#155e4b!important;color:#fff!important;}
.st-key-sec-review-panel [data-testid="stDownloadButton"] button {min-height:44px!important;}
.sec-review-link {display:inline-flex;align-items:center;min-height:44px;padding:8px 14px;
box-sizing:border-box;border-radius:7px;text-decoration:none!important;white-space:normal;}
.sec-review-link:focus-visible {outline:3px solid #b45309;outline-offset:3px;}
</style>'''


def render_company_review(st,ticker,view,*,profile_key):
    if not _ticker(ticker) or _mode_reason('research'):return
    st.markdown(CONTROL_STYLE,unsafe_allow_html=True)
    with st.container(key='sec-review-panel'):
        _render_company_review(st,ticker,view,profile_key=profile_key)


def _render_company_review(st,ticker,view,*,profile_key):
    st.markdown('### SEC 财报证据复核')
    st.caption(f'{ticker} · 支持 US-GAAP / USD 年度 10-K、10-K/A 直接字段。显式保存后可离线重放；不会修改正式财务、来源权限或研究日志。')
    scope=f'{profile_key}:{ticker}'
    try:
        candidate=capture_review(view,profile_key=profile_key)
        if candidate['ticker']!=ticker:candidate=None
    except (ValueError,TypeError,OSError):candidate=None
    if ticker=='NEM':candidate=_check_candidate(st,candidate,scope)
    if st.button('保存当前 SEC 证据',key='sec-review-save:'+scope,disabled=candidate is None):
        try:save_review(candidate,PROJECT_ROOT);st.success('已保存本次观察。')
        except (ValueError,OSError):st.error('证据未保存。请检查来源口径或保存目录；每家公司最多 100 份、每个研究集合最多 100 家公司。')
    if candidate is None:st.caption(f'先使用上方「只更新财报」取得合格的 {ticker} SEC 观察。其他申报形式、币种或缺少直接收入基准时保留缺口；已有证据仍可重放。')
    with st.expander('导入证据包',expanded=False):
        st.caption(f'只接受本研究集合的 {ticker} 证据 JSON，内容上限 64 KB。文件校验确认内容一致性，不能证明文件未经他人重新生成；导入不会向 SEC 重新认证。')
        upload=st.file_uploader('选择已导出的证据包',type=['json'],max_upload_size=1,key='sec-review-upload:'+scope)
        if st.button('导入并保存证据包',key='sec-review-import:'+scope,disabled=upload is None):
            try:
                upload.seek(0);packet=load_review(upload.read(MAX_BYTES+1))
                if packet['profile_key']!=profile_key or packet['ticker']!=ticker:raise ValueError('selected_scope_mismatch')
                save_review(packet,PROJECT_ROOT);st.success('证据包已导入，以下内容由保存文件重放。')
            except (ValueError,OSError):st.error('导入未完成。文件损坏、公司或研究集合不符、目录不可用或保存数量已达上限；原文件未更改。')
    try:packets=list_reviews(PROJECT_ROOT,profile_key,ticker)
    except (ValueError,OSError):st.error('已保存证据无法完整核验，比较暂停。请保留文件并检查保存目录。');return
    if not packets:st.info('尚未保存证据。保存第一次观察后，可再次保存或导入另一份证据进行比较。');return
    st.markdown('#### 已保存证据重放')
    st.caption('选择项显示报告期、保存时间（UTC）和证据编号；完整时间在下方来源详情中。')
    options=list(range(len(packets)))
    current_index=st.selectbox('重放哪份证据',options,index=len(packets)-1,
        format_func=lambda i:_label(packets[i]),key=f'sec-review-current:{scope}:{len(packets)}')
    current=packets[current_index]
    baseline_options=[None]+options
    prior_index=st.selectbox('与哪份已保存证据比较',baseline_options,index=(current_index if current_index else 0),
        format_func=lambda i:'尚未选择基线' if i is None else _label(packets[i]),
        key=f'sec-review-before:{scope}:{len(packets)}:{current_index}')
    before=None if prior_index is None else packets[prior_index]
    result=compare_reviews(before,current)
    st.caption(f"本份证据：{len(current['fields'])}/4 个直接字段 · {len(current['gaps'])} 个字段缺口；不代表完整财报或估值资格。")
    _render_comparison(st,result)
    _render_exact_check(st,current,show_reason=False)
    st.caption('当前显示来自已保存证据，没有重新查询网络。保存时间与 SEC 观察时间分开记录；新的保存时间不表示财报变化。')
    st.download_button('下载当前证据包',data=encode_review(current),file_name=ticker+'-SEC-'+current['receipt_id'][:12]+'.json',
        mime='application/json',key='sec-review-download:'+scope)
    st.markdown('<a class="sec-review-link" href="?mode=research&amp;page=monitor&amp;return_ticker='+ticker+'" target="_self">在 Monitor 查看待核查事项</a>',unsafe_allow_html=True)
    with st.expander('证据来源与字段口径',expanded=False):
        st.write('报告期截至 '+current['period_end']+' · '+current['form'])
        st.write('申报发布日期 '+current['filing_date']+'（日期精度）')
        st.write('SEC 观察时间 '+current['source_observed_at'])
        st.write('保存时间 '+current['saved_at'])
        st.markdown('[SEC Companyfacts 原始来源]('+current['source_url']+')')
        st.caption('申报编号 '+current['accession']+' · CIK '+current['sec_cik'])
        st.caption('原始响应 SHA-256 '+current['raw_payload_sha256'])
        st.caption('来源权限登记 SHA-256 '+current['rights_registry_sha256'])
        if current.get('companyfacts_identity'):
            identity=current['companyfacts_identity']
            st.markdown('[SEC 公司与 CIK 关联来源]('+identity['association_source_url']+')')
            st.caption('关联观察 '+identity['association_observed_at']+' · SHA-256 '+identity['association_payload_sha256'])
        st.caption('这里记录发行人财报事实；不证明证券类别、发行人住所、上市状态、股价匹配或时间点覆盖。')
        st.caption('权限仅涵盖登记的规范化字段；原始响应、价格、派生自由现金流和分发许可未随此包开放。')
        for row in current['fields']:
            st.markdown('**'+LABELS[row['field']]+'** · '+format(row['value'],',')+' '+row['unit'])
            st.caption(row['taxonomy']+':'+row['concept']+' · '+row['period_start']+' 至 '+row['period_end'])


def render_review_monitor(st,*,profile_key):
    if _mode_reason('research'):return
    try:queue=review_queue(PROJECT_ROOT,profile_key)
    except (ValueError,OSError):
        st.warning('SEC 证据目录无法核验或超过 100 家公司的保存上限，数据复核队列暂不可读。');return
    if not queue['items']:return
    st.markdown('### SEC 财报证据复核队列')
    st.caption(f"已保存 {queue['companies']} 家公司 · 字段缺口 {queue['field_gap_companies']} 家 · 等待基线 {queue['baseline_companies']} 家 · 发现变化 {queue['changed_companies']} 家 · 不可读 {queue['unreadable_companies']} 家")
    st.caption('仅统计本研究集合主动保存的 SEC 证据；不是全市场覆盖率，也不计入下方研究流程事项或投资信号。')
    items={i['ticker']:i for i in queue['items']};symbols=list(items)
    requested=st.query_params.get('return_ticker') or st.query_params.get('ticker')
    selected=st.selectbox('选择要复核的公司',symbols,index=symbols.index(requested) if requested in symbols else 0,
        format_func=lambda t:t+' · '+('保存文件待核验' if items[t]['error'] else STATUS[items[t]['comparison']['status']]),
        key='sec-review-monitor-company:'+profile_key)
    item=items[selected]
    st.markdown('#### '+selected+' SEC 证据复核')
    if item['error']:
        st.warning(selected+' 的保存文件无法核验。请保留文件并检查目录；其他公司的记录仍可查看。')
        return
    result=item['comparison'];current=item['latest']
    context='最近两次保存的年度财报复核' if item['previous'] else '首次保存的年度财报'
    st.markdown('**'+STATUS[result['status']]+'** · '+context)
    st.caption('最新保存时间 '+current['saved_at']+' · 报告期 '+current['period_end'])
    st.markdown(_gaps_html(result),unsafe_allow_html=True)
    _render_exact_check(st,current,show_reason=False)
    if result.get('review_changes'):st.caption('来源核查依据发生变化；不表示财务数值修订。')
    for change in result['changes']:st.markdown('- '+LABELS[change['field']]+' · 已保存字段有变化，请核对两份申报来源。')
    if result['status']=='baseline_missing':st.caption('下一步：回到公司页，保存另一份同公司、同期间的独立观察。重复保存只验证重放稳定性。')
    elif result['gaps']:st.caption('下一步：按字段缺失原因核对来源或口径；相同输入未变化，不表示缺口已补齐。')
    elif result['changes'] or result.get('review_changes'):st.caption('下一步：回到公司页检查前后两份证据及变化来源。')
    else:st.caption('当前保存范围无需因重复观察重开核查；出现新申报或新证据时再复核。')
    st.markdown(CONTROL_STYLE+'<a class="sec-review-link" href="?mode=research&amp;page=company-workbench&amp;ticker='+selected+'&amp;section=notes" target="_self">返回 '+selected+' 证据复核</a>',unsafe_allow_html=True)
