"""Explicit NEM receipt actions, shared by company records and Monitor."""
from html import escape
from pathlib import Path
from src.online_company_identity import _mode_reason
from src.sec_research_review import (
    MAX_BYTES, capture_review, compare_reviews, encode_review, list_reviews, load_review, save_review,
)

PROJECT_ROOT=Path(__file__).resolve().parent.parent
LABELS={'revenue':'收入','operating_income':'营业利润','cash_from_operations':'经营现金流',
        'capital_expenditures':'资本支出','all':'整个证据包'}
REASONS={'direct_field_missing':'没有同一申报、同一期间的直接字段，需核对原文',
    'prior_direct_field_missing':'上一份证据缺少直接字段', 'baseline_missing':'尚缺第二份可比较的保存证据',
    'duration_mismatch':'期间长度或起止日期不一致', 'period_end_mismatch':'报告期不同',
    'concept_mismatch':'财务定义不同', 'unit_mismatch':'单位或币种不同',
    'rights_policy_changed':'来源权限登记已变化，需重新核查', 'profile_key_mismatch':'研究集合不同',
    'same_source_digest_conflict':'相同来源摘要对应不同字段，需核查证据一致性',
    'rights_mismatch':'字段权限不一致', 'raw_source_conflict':'原始来源包含冲突值，需核查申报语境',
    'raw_source_value_invalid':'原始来源数值无法通过核查'}
STATUS={'unchanged':'未变化','changed':'发现变化，需核查','withheld':'口径不一致，保留缺口',
        'gaps_changed':'缺口状态变化，需核查','baseline_missing':'已保存，等待比较基线'}


def _label(packet):
    return f"{packet['saved_at']} · {packet['period_end']} · {packet['receipt_id'][:8]}"


def _gaps_html(result):
    rows=''.join('<li><strong>'+escape(LABELS.get(g['field'],g['field']))+'</strong> · '+
        escape(REASONS.get(g['reason'],g['reason']))+'</li>' for g in result['gaps'])
    return '<ul>'+rows+'</ul>' if rows else '<p>这四个直接字段没有待核查缺口。完整估值及投资判断仍需其他证据。</p>'


def _render_comparison(st,result):
    label=STATUS[result['status']]
    if result['status']=='unchanged':st.success(label+' · 已保存的字段数值与口径一致。')
    elif result['status']=='changed':st.warning(label)
    else:st.info(label)
    for change in result['changes']:
        left,right=change['before'],change['after']
        st.markdown('**'+LABELS[change['field']]+'**')
        st.write(f"{left['value']:,} → {right['value']:,} {right['unit']}")
        st.caption('变化维度：'+', '.join(change['changed_dimensions'])+
            ' · 原申报 '+left['accession']+' · 当前申报 '+right['accession'])
    st.markdown(_gaps_html(result),unsafe_allow_html=True)


def render_company_review(st,ticker,view,*,profile_key):
    if ticker!='NEM' or _mode_reason('research'):return
    st.markdown('### SEC 财报证据复核')
    st.caption('NEM 年度直接字段试点。显式保存后可以离线重放与比较；不会修改正式财务、来源权限或研究日志。')
    scope=f'{profile_key}:NEM'
    try:
        candidate=capture_review(view,profile_key=profile_key)
    except (ValueError,TypeError,OSError):candidate=None
    if st.button('保存当前 SEC 证据',key='sec-review-save:'+scope,disabled=candidate is None):
        try:save_review(candidate,PROJECT_ROOT);st.success('已保存本次观察。')
        except (ValueError,OSError):st.error('证据未保存。请检查来源口径、保存目录或历史数量。')
    if candidate is None:st.caption('先使用上方「只更新财报」取得合格的 NEM SEC 观察。已有证据仍可重放。')
    with st.expander('导入证据包',expanded=False):
        st.caption('只接受本研究集合的 NEM 证据 JSON，内容上限 64 KB。文件校验确认内容一致性，不能证明文件未经他人重新生成；导入不会向 SEC 重新认证。')
        upload=st.file_uploader('选择已导出的证据包',type=['json'],max_upload_size=1,key='sec-review-upload:'+scope)
        if st.button('导入并保存证据包',key='sec-review-import:'+scope,disabled=upload is None):
            try:
                upload.seek(0);packet=load_review(upload.read(MAX_BYTES+1))
                if packet['profile_key']!=profile_key:raise ValueError('profile_mismatch')
                save_review(packet,PROJECT_ROOT);st.success('证据包已导入，以下内容由保存文件重放。')
            except (ValueError,OSError):st.error('导入未完成。文件损坏、研究集合不符或保存目录不可用；原文件未更改。')
    try:packets=list_reviews(PROJECT_ROOT,profile_key)
    except (ValueError,OSError):st.error('已保存证据无法完整核验，比较暂停。请保留文件并检查保存目录。');return
    if not packets:st.info('尚未保存证据。保存第一次观察后，可再次保存或导入另一份证据进行比较。');return
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
    _render_comparison(st,result)
    st.caption('当前显示来自已保存证据，没有重新查询网络。保存时间与 SEC 观察时间分开记录；新的保存时间不表示财报变化。')
    st.download_button('下载当前证据包',data=encode_review(current),file_name='NEM-SEC-'+current['receipt_id'][:12]+'.json',
        mime='application/json',key='sec-review-download:'+scope)
    st.link_button('在 Monitor 查看待核查事项','?mode=research&page=monitor&ticker=NEM')
    with st.expander('证据来源与字段口径',expanded=False):
        st.write('报告期截至 '+current['period_end']+' · '+current['form'])
        st.write('申报发布日期 '+current['filing_date']+'（日期精度）')
        st.write('SEC 观察时间 '+current['source_observed_at'])
        st.write('保存时间 '+current['saved_at'])
        st.markdown('[SEC Companyfacts 原始来源]('+current['source_url']+')')
        st.caption('申报编号 '+current['accession']+' · CIK '+current['sec_cik'])
        st.caption('原始响应 SHA-256 '+current['raw_payload_sha256'])
        st.caption('来源权限登记 SHA-256 '+current['rights_registry_sha256'])
        st.caption('权限仅涵盖登记的规范化字段；原始响应、价格、派生自由现金流和分发许可未随此包开放。')
        for row in current['fields']:
            st.markdown('**'+LABELS[row['field']]+'** · '+format(row['value'],',')+' '+row['unit'])
            st.caption(row['taxonomy']+':'+row['concept']+' · '+row['period_start']+' 至 '+row['period_end'])


def render_review_monitor(st,*,profile_key):
    if _mode_reason('research'):return
    try:packets=list_reviews(PROJECT_ROOT,profile_key)
    except (ValueError,OSError):
        st.warning('NEM SEC 证据保存文件无法核验，待核查事项暂不可读。');return
    if not packets:return
    result=compare_reviews(packets[-2] if len(packets)>1 else None,packets[-1])
    st.markdown('### NEM SEC 证据待核查')
    st.markdown('**'+STATUS[result['status']]+'** · 最近两次保存的年度财报复核')
    st.caption('独立的数据核查事项，不计入研究日志、流程事件或投资信号。最新保存时间 '+packets[-1]['saved_at'])
    st.markdown(_gaps_html(result),unsafe_allow_html=True)
    for change in result['changes']:st.markdown('- '+LABELS[change['field']]+' · 已保存字段有变化，请核对两份申报来源。')
    st.link_button('返回 NEM 证据复核','?mode=research&page=company-workbench&ticker=NEM&section=notes')
