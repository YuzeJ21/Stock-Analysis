"""Readable online comparison and source disclosure; no transport or state writes."""
from collections.abc import Mapping
from html import escape
import math
import re
from urllib.parse import urlsplit

from src.online_peer_valuation import FISCAL_WINDOW_DAYS, MIN_PEERS, QCOM_SIC_BASIS

REASONS = {
    'reported_annual_pe_industry_reference_only':'已取得通过规则核对的年度 P/E 行业参照，仅描述倍数差异。',
    'annual_filing_missing':'未取得本方法支持的年度 10-K / 20-F 申报。',
    'latest_annual_eps_missing_including_amendment':'最新年度或修订申报没有匹配的稀释每股收益，保留缺口。',
    'annual_filing_tie_unresolved':'同日有多份年度申报，缺少可区分版本顺序的证据。',
    'annual_eps_nonpositive_or_invalid':'年度稀释每股收益为零、负值或无效；P/E 不适用。',
    'annual_eps_confirmed_loss':'10-K 与 Companyfacts 均确认年度摊薄 EPS 为负，P/E 不适用。',
    'annual_eps_confirmed_zero':'10-K 与 Companyfacts 均确认年度摊薄 EPS 为零，P/E 不适用。',
    'annual_eps_confirmed_positive':'10-K 与 Companyfacts 均确认年度摊薄 EPS 为正。',
    'annual_eps_filing_version_unreviewed':'当前年度申报或修订版本尚未完成原文核对。',
    'annual_eps_exact_filing_unavailable':'核对年度摊薄 EPS 所需的 SEC 申报暂不可用。',
    'annual_eps_exact_filing_unverified':'年度申报原文未通过核对，EPS 仍待确认。',
    'annual_eps_companyfacts_not_matched':'已核对申报版本，缺少与同一财年和申报匹配的有效 Companyfacts EPS。',
    'annual_eps_exact_filing_conflict':'10-K 与 Companyfacts 的年度摊薄 EPS 口径或数值不一致。',
    'annual_diluted_eps_usd_missing':'没有取得 USD/shares 口径的已披露年度稀释每股收益。',
    'annual_eps_conflict':'相同年度申报存在冲突的收益字段。',
    'annual_eps_filing_mismatch':'收益字段与选定申报的类型或发布日期不一致。',
    'annual_eps_unit_conflict':'同一年度收益字段存在币种或单位冲突。',
    'annual_period_or_publication_not_current_for_price':'年度期间过旧，或申报尚未在所用价格日期发布。',
    'peer_fiscal_window_differs':'实际财年起止日期差异超过 35 天。',
    'peer_candidate_scope_unverified':'QCOM 的 CIK 或 SEC SIC 3663 候选范围未通过核对。',
    'peer_candidate_cik_mismatch':'候选公司的当前 SEC CIK 与已核对名单不同。',
    'provider_industry_differs':'供应商行业分类不同。',
    'sec_industry_differs':'SEC 行业代码不同。',
    'post_period_split_requires_share_basis_review':'财报期间后发生拆股，缺少可核对的收益调整口径。',
    'split_history_does_not_cover_period_end':'拆股观察范围未覆盖收益期间末，股数口径暂不能核对。',
    'split_evidence_invalid':'拆股记录的日期或比例未通过核对。',
    'peer_price_date_differs':'所用收盘价格日期与本公司不同。',
    'quote_not_same_recent_completed_day':'报价不是同一已完成交易日的近期价格。',
    'quote_and_daily_close_differ':'供应商报价与日线收盘值无法核对一致。',
    'price_quote_chronology_invalid':'价格来源的观察时间早于对应报价，暂不能采用。',
    'price_source_digest_missing':'缺少价格来源摘要。',
    'source_observation_stale_or_future':'来源观察已超过 24 小时或时间在未来，请重新更新。',
    'vendor_filing_not_matched_to_sec':'供应商申报链接未能与 SEC 申报元数据核对。',
    'vendor_cofiling_scope_unverified':'SO 的指定联报 10-Q 未通过来源核对。',
    'vendor_cofiling_source_unavailable':'SO 的指定联报 10-Q 来源暂不可用。',
    'vendor_filing_issuer_conflict':'供应商申报链接的发行人身份存在冲突。',
    'quote_identity_or_type_mismatch':'供应商代码或证券类型不一致。',
    'quote_exchange_mismatch':'供应商交易所与独立上市来源不一致。',
    'unsupported_quote_or_financial_currency':'价格与财务币种不是已支持的 USD 口径。',
    'peer_listing_or_share_basis_unverified':'未核对到独立、明确的普通股上市身份。',
    'selected_listing_or_cik_unverified':'本公司的上市身份、CIK 或普通股类型尚未核对。',
    'multiple_issuer_share_classes_unresolved':'同一发行人有多个关联代码，所选证券的每股收益口径尚未核对。',
    'selected_common_other_security_basis_unresolved':'所选普通股已有文件依据，其他关联证券的收益口径仍未核对。',
    'depositary_security_requires_separate_method':'纽约交易的是 ADS，须单独核对每 ADS 收益、币种及转换口径。',
    'successor_annual_basis_unverified':'已见发行人连续性依据，当前发行人的年度收益分母仍未建立。',
    'selected_security_scope_unverified':'所选证券的具体文件或当前版本尚未通过核对。',
    'selected_security_eps_conflict':'具体文件中的普通股 EPS 与年度财报字段不一致。',
    'selected_security_source_unavailable':'所选证券依据所需的具体 SEC 文件暂未取得。',
    'vendor_history_source_unavailable':'供应商身份核对所需的 SEC 历史索引暂未取得。',
    'ordinary_share_basis_unverified':'该证券缺少明确普通股依据，须采用适合其类型的方法。',
    'operating_issuer_required':'该发行人尚未通过经营性公司口径核对。',
    'investment_company_requires_separate_method':'投资公司需独立研究方法，不能直接采用这组 P/E。',
    'industry_or_operating_scope_unverified':'行业或经营性公司范围尚未核对。',
    'at_least_three_compatible_industry_references_required':'通过同口径筛选的参照公司不足，至少 3 家才显示差异。',
    'vendor_context_source_unavailable':'暂未取得供应商报价与申报身份资料。',
    'industry_candidate_source_unavailable':'暂未取得供应商行业候选列表。',
    'industry_metadata_missing':'本公司的行业分类缺失。',
    'listing_classification_unavailable':'独立上市与证券类型来源暂不可用。',
    'issuer_source_unavailable':'该公司的申报或价格来源暂不可用。',
    'listing_venue_source_unavailable':'核对交易所所需的 SEC 申报暂不可用。',
    'peer_not_collected':'尚未采集；先处理本公司来源缺口。',
    'source_paused_after_repeated_failures':'连续来源失败后暂停后续请求，保留未完成项。',
    'cached_observation_changed':'缓存内容与来源摘要不一致，请重新更新。',
    'normalized_sec_observation_changed':'财报字段与保存的来源摘要不一致。',
    'normalized_observation_changed':'供应商字段与保存的来源摘要不一致。',
    'peer_source_unavailable':'本次在线来源未完成，旧结论已撤下。',
    'commercial_identity_rights_unreviewed':'当前商业模式的来源权限尚未通过核对。',
    'invalid_commercial_mode_configuration':'运行模式配置无法核对，保留来源限制。',
    'comparative_eps_missing':'同一申报缺少相邻上年度 EPS。',
    'comparative_eps_base_nonpositive':'基期 EPS 为零或负值，百分比不适合解释本次变化。',
    'comparative_eps_metadata_mismatch':'上年度 EPS 与选定申报的类型或发布日期不一致。',
    'comparative_eps_period_invalid':'上年度 EPS 的实际期间不是已支持的完整年度。',
    'comparative_eps_conflict':'同一申报中的上年度 EPS 或期间存在冲突。',
    'comparative_eps_unit_conflict':'上年度 EPS 存在币种或单位冲突。',
    'comparative_eps_value_invalid':'上年度 EPS 数值未通过核对。',
    'comparative_eps_growth_outside_range':'EPS 变化超出本方法支持的范围。',
    'comparative_eps_input_invalid':'尚未取得可核对的同一申报年度 EPS 背景。',
    'amendment_source_unavailable':'修订范围核对所需的具体 SEC 文件暂未取得。',
    'amendment_scope_unverified':'修订范围或精确文件未通过核对，继续保留 EPS 缺口。',
    'amendment_original_eps_conflict':'原始文件 EPS 与 Companyfacts 记录不一致，暂不采用。',
}

STYLE='''<style>
.online-peer-valuation{box-sizing:border-box;min-width:0;margin:12px 0 20px;padding:22px;border:1px solid #d7e1dc;border-radius:14px;background:#fff;color:#22372d;overflow-wrap:anywhere}
.online-peer-valuation h3{font-size:1.4rem;line-height:1.4;margin:.35rem 0 .7rem}.online-peer-valuation h4{font-size:1.05rem;margin:1rem 0 .5rem}.online-peer-valuation p{line-height:1.6;margin:.55rem 0}
.online-peer-valuation .peer-kicker{font-size:.85rem;color:#496253}.peer-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:18px 0}.peer-stats div{padding:14px;background:#f2f6f3;border:1px solid #dce5df;border-radius:10px;min-width:0}.peer-stats dt{font-size:.85rem;color:#496253}.peer-stats dd{font-size:1.35rem;font-weight:700;margin:.4rem 0 0}
.online-peer-valuation.peer-comparison h3{padding:0}.online-peer-valuation .peer-comparison-stats{gap:8px;margin:10px 0}.peer-comparison-stats div{padding:8px 10px}.peer-comparison-stats dd{font-size:1.1rem;line-height:1.35;margin:.2rem 0 0}
.online-peer-valuation details{border-top:1px solid #dce5df;margin-top:14px;padding-top:7px}.online-peer-valuation summary{cursor:pointer;min-height:44px;display:list-item;align-content:center;font-weight:650;line-height:1.5}.online-peer-valuation a{color:#245842;text-decoration:underline}.online-peer-valuation summary:focus-visible,.online-peer-valuation a:focus-visible{outline:2px solid #245842;outline-offset:3px}
.online-peer-valuation table{width:100%;table-layout:fixed;border-collapse:collapse;margin:12px 0}.online-peer-valuation th,.online-peer-valuation td{padding:9px 6px;text-align:left;vertical-align:top;border-bottom:1px solid #dce5df;font-size:.88rem;overflow-wrap:anywhere}.online-peer-valuation code{white-space:normal;word-break:break-all;font-size:.78rem}.online-peer-valuation ul{padding-left:20px}.online-peer-valuation li{margin:.5rem 0}
@media(max-width:640px){.online-peer-valuation{padding:15px}.peer-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.online-peer-valuation table,.online-peer-valuation tbody{display:block}.online-peer-valuation thead{display:none}.online-peer-valuation tr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border:1px solid #dce5df;border-radius:9px;margin:12px 0;padding:7px}.online-peer-valuation td{display:block;border:0;min-width:0}.online-peer-valuation td::before{content:attr(data-label);display:block;font-size:.78rem;color:#496253;margin-bottom:4px}.online-peer-valuation td:first-child,.online-peer-valuation td:last-child{grid-column:1/-1}}
</style>'''


def _text(value):
    return escape(str(value if value is not None else '未取得'))


def _number(value):
    try:return type(value) in {int,float} and abs(value)<=1e20 and math.isfinite(value)
    except (ValueError,OverflowError):return False


def _multiple(value):
    return (f'{value:,.1f}' if value>=.1 else f'{value:.3g}')+'×' if _number(value) and value>0 else '未取得'


def _link(url,label):
    try:
        p=urlsplit(url) if isinstance(url,str) and len(url)<=2048 else None
        if p and p.scheme=='https' and p.hostname in {'www.sec.gov','data.sec.gov','query1.finance.yahoo.com','finance.yahoo.com','cdn.yahoofinance.com','www.nasdaqtrader.com'} and p.username is None and p.password is None and p.port is None:
            return '<a href="'+escape(url,quote=True)+'" target="_blank" rel="noopener noreferrer">'+escape(label)+'</a>'
    except ValueError:pass
    return escape(label)+'（链接未通过核对）'


def _reason(value):
    return REASONS.get(value if isinstance(value,str) else None,'来源、身份或字段记录未通过核对，暂不采用。')


def _source_table(rows):
    body=''
    for row in rows:
        eps=f'{row["eps"]:,.6g}' if _number(row.get('eps')) else '未取得'
        price=f'{row["price"]:,.6g}' if _number(row.get('price')) else '未取得'
        cells=[('公司',_text(row.get('ticker'))),('年度 P/E',_multiple(row.get('multiple'))),
               ('年度稀释 EPS',_text(eps)+' USD/shares'),
               ('实际财报期间',_text(row.get('period_start'))+' → '+_text(row.get('period_end'))),
               ('价格及日期',_text(price)+' USD · '+_text(row.get('price_date'))),
               ('来源',_link(row.get('source_ref'),'SEC 收益')+' · '+_link(row.get('filing_ref'),'申报文件')+' · '+_link(row.get('price_source_ref'),'价格源'))]
        body+='<tr>'+''.join('<td data-label="'+escape(k,quote=True)+'">'+v+'</td>' for k,v in cells)+'</tr>'
    return '<table aria-label="年度 P/E 与实际期间"><thead><tr>'+''.join('<th scope="col">'+k+'</th>' for k in ('公司','年度 P/E','年度稀释 EPS','实际财报期间','价格及日期','来源'))+'</tr></thead><tbody>'+body+'</tbody></table>'


def _earnings_phrase(row):
    context=row.get('earnings_context') if isinstance(row.get('earnings_context'),Mapping) else {}
    growth=context.get('growth_fraction')
    if (context.get('status')=='supported' and _number(growth) and abs(growth)<=1e6
            and context.get('accession')==row.get('accession')):
        return '年度 EPS 同比 '+f'{growth*100:+.1f}%'
    return 'EPS 同比暂不计算：'+_reason(context.get('reason','comparative_eps_input_invalid'))


def _earnings_table(rows):
    body=''
    for row in rows:
        context=row.get('earnings_context') if isinstance(row.get('earnings_context'),Mapping) else {}
        def period(label):
            value=context.get(label+'_eps')
            if not _number(value):return '未取得'
            return _text(f'{value:,.6g}')+' USD/shares<br>'+_text(context.get(label+'_period_start'))+' → '+_text(context.get(label+'_period_end'))
        cells=[('公司',_text(row.get('ticker'))),('年度 EPS 变化',_text(_earnings_phrase(row))),
               ('上年度列示值',period('prior')),('本年度列示值',period('current')),
               ('同一申报来源',_link(row.get('source_ref'),'SEC 收益')+' · '+_link(row.get('filing_ref'),'对应申报'))]
        body+='<tr>'+''.join('<td data-label="'+escape(k,quote=True)+'">'+v+'</td>' for k,v in cells)+'</tr>'
    return '<h4>盈利变化背景</h4><p>同一年度申报的稀释 EPS 列示值；历史变化不代表未来增长，同行倍数未按增长调整。</p><table aria-label="同一年度申报的 EPS 变化"><thead><tr>'+''.join('<th scope="col">'+k+'</th>' for k in ('公司','年度 EPS 变化','上年度列示值','本年度列示值','同一申报来源'))+'</tr></thead><tbody>'+body+'</tbody></table>'


def _diagnostic_html(d):
    if not isinstance(d,Mapping):return '<p>未取得可独立核对的观察。</p>'
    html='<p>以下是独立来源观察，不参与 P/E 或参照中位数。'+_link(d.get('candidate_source_ref'),'候选组来源')+'</p>'
    if d.get('sec_cik'):
        html+='<p>SEC 上市关联 CIK '+_text(d['sec_cik'])+' · '+_link(d.get('profile_source_ref'),'申报元数据查询地址')+' · '+_link(d.get('facts_query_ref'),'收益字段查询地址')+'。查询地址不代表字段已取得。</p>'
    for filing in d.get('annual_versions',[]):
        html+='<p>'+_text(filing.get('form'))+' · '+_text(filing.get('accession'))+' · 期间末 '+_text(filing.get('period_end'))+' · 发布 '+_text(filing.get('filed'))+' · '+_link(filing.get('source_ref'),'具体申报')+'</p>'
    html+=_selected_security_html(d.get('selected_security_scope'))
    html+=_vendor_filing_evidence_html(d.get('vendor_identity_observation'))
    html+=_listing_venue_evidence_html(d.get('listing_venue_evidence'))
    audit=d.get('annual_eps_audit')
    if isinstance(audit,Mapping):
        html+='<p>'+_text(_reason(audit.get('reason')))
        if audit.get('source_url'):
            html+=' '+_link(audit['source_url'],'10-K 年度摊薄 EPS 原文')
        html+='</p>'
    eps=d.get('annual_eps_observation')
    if isinstance(eps,Mapping) and _number(eps.get('eps')):
        html+='<p>申报稀释每股收益：'+_text(f'{eps["eps"]:,.6g}')+' USD/shares · '+_text(eps.get('period_start'))+' → '+_text(eps.get('period_end'))+' · 发布 '+_text(eps.get('filed'))+' · 观察 '+_text(eps.get('observed_at'))+' · '+_link(eps.get('source_ref'),'SEC 收益观察')+' · '+_link(eps.get('filing_ref'),'对应申报')+'</p>'
        html+=_earnings_table([{**eps,'ticker':d.get('ticker',d.get('sec_cik'))}])
        html+=_amendment_html(eps.get('amendment_scope'))
        digest=eps.get('facts_sha256')
        html+='<p>SEC 原始响应 SHA-256：<code>'+(_text(digest) if isinstance(digest,str) and re.fullmatch(r'[0-9a-f]{64}',digest) else '未取得')+'</code></p>'
    price=d.get('price_observation')
    if isinstance(price,Mapping):
        html+='<p>单独价格观察（未用于估值）：'+_text(price.get('provider_symbol'))+' · '+_text(price.get('price'))+' USD · '+_text(price.get('date'))+' · 观察 '+_text(price.get('observed_at'))+' · '+_link(price.get('source_ref'),'价格源')+'</p>'
        html+='<p>价格与拆股观察请求 '+_text(price.get('history_range'))+'；实际 '+_text(price.get('first_date'))+' → '+_text(price.get('last_date'))+'；请求范围不保证历史完整。</p>'
    else:html+='<p>价格来源尚未取得或未通过独立字段核对。</p>'
    for split in d.get('splits_observed',[]):
        html+='<p>观察到拆股：'+_text(split.get('date'))+' · '+_text(split.get('numerator'))+':'+_text(split.get('denominator'))+'；未推导调整后收益。</p>'
    observation=d.get('independent_observation_not_in_benchmark')
    if isinstance(observation,Mapping):html+='<p>本公司独立计算，但不纳入参照中位数：</p>'+_source_table([observation])
    return html


def _amendment_html(scope):
    if not isinstance(scope,Mapping) or scope.get('status')!='supported':return ''
    html='<details><summary>修订范围与原始年度申报 EPS 依据</summary><p>原始年度申报 EPS 已与具体文件及 Companyfacts 交叉核对。已知修订仅更正经营讨论中的百分比，并声明其他披露不变；继续采用原始 EPS 是有边界的技术证据解释，不是来源权限或模型批准。</p>'
    html+='<p>修订元数据为 10-K/A，文档记录 AmendmentFlag=false；通用财报解析仍保持受限，未修改其校验规则。</p>'
    receipts=scope.get('source_receipts',[])
    for index,(key,label) in enumerate([('original','原始申报'),('amendment','最新修订')]):
        filing=scope.get(key,{}) if isinstance(scope.get(key),Mapping) else {};ref=receipts[index] if isinstance(receipts,list) and len(receipts)>index else {}
        html+='<p>'+label+' · '+_text(filing.get('form'))+' · '+_text(filing.get('accessionNumber'))+' · 发布 '+_text(filing.get('filingDate'))+' · 接收 '+_text(filing.get('acceptanceDateTime'))+' · '+_link(ref.get('source_url'),'具体文件')+' · 观察 '+_text(ref.get('observed_at'))+'</p><p>SHA-256 <code>'+_text(ref.get('payload_sha256'))+'</code></p>'
        if ref.get('binding_normalization')=='sec-empty-tail-script-v1':
            html+='<p>正文 SHA-256 <code>'+_text(ref.get('body_sha256'))+'</code> · 仅排除 SEC 响应末尾的空外部脚本。</p>'
    return html+'</details>'


def _observations_html(scope,*,compact=False):
    observations=scope.get('evidence_observations',[])
    if not isinstance(observations,list) or not observations:return ''
    html='<h4>已核对的证券与收益观察</h4><p>以下观察不参与 P/E、同行中位数或已保存模型。</p>'
    if scope.get('reason')=='depositary_security_requires_separate_method':
        html+='<p>ADS 与普通股分别列示。美元便利折算不等于按交易日汇率换算的收益；不从四舍五入后的普通股 EPS 计算 ADS EPS。</p>'
    has_numbers=any(isinstance(o,Mapping) and o.get('kind')=='numeric' for o in observations)
    for o in observations:
        if not isinstance(o,Mapping):continue
        if compact and has_numbers and (o.get('kind')!='numeric' or o.get('security_basis')!='ADS'):continue
        html+='<p><strong>'+_text(o.get('label'))+'</strong>'
        if _number(o.get('value')):
            unit=o.get('unit','')
            display_unit=unit.replace('/shares','/ADS' if o.get('security_basis')=='ADS' else '/普通股')
            html+='：'+_text(f'{o["value"]:,.6g}')+' '+_text(display_unit)
        html+='</p>'
        if compact:
            if not has_numbers:html+='<p>'+_link(o.get('source_ref'),'已核对的原始依据')+'</p>'
            continue
        if o.get('kind')=='numeric':
            html+='<p>'+_text(o.get('period_start'))+' → '+_text(o.get('period_end'))+' · 原始单位 '+_text(o.get('unit'))+' · '+_text(o.get('concept'))+' · '+_text(o.get('namespace_uri'))+'</p>'
        if o.get('entity_cik'):
            html+='<p>申报 CIK '+_text(o.get('filing_cik'))+' · 事实上下文实体 CIK '+_text(o.get('entity_cik'))+'</p>'
        html+='<p>'+_link(o.get('source_ref'),'原始观察来源')
        for key,label in [('context_source_ref','实体与期间上下文'),('unit_source_ref','原始单位定义')]:
            if o.get(key):html+=' · '+_link(o[key],label)
        html+='</p>'
        if o.get('source_refs'):html+='<p>完整附注链：'+' · '.join(_link(ref,'附注原文') for ref in o['source_refs'])+'</p>'
        if o.get('location'):html+='<p>正文内位置 '+_text(o['location'])+'；使用整份文件链接，原文没有可用的片段锚点。</p>'
        html+='<p>发布 '+_text(o.get('publication_date'))+' · 观察 '+_text(o.get('observed_at'))+'</p>'
    return html


def _selected_security_html(scope):
    if not isinstance(scope,Mapping) or scope.get('status') not in {'supported_common','inspection_only'}:return ''
    html='<details><summary>所选证券与其他关联代码</summary>'
    if scope['status']=='supported_common':html+='<p>所选普通股与已披露年度 EPS 的口径已按具体文件核对；完整估值资格和同行可比性仍分别检查。这是有边界的技术证据解释。</p>'
    else:html+='<p>'+_text(_reason(scope.get('reason')))+'</p>'
    if scope.get('reason')=='successor_annual_basis_unverified':html+='<p>已见新旧发行人的证券与报告连续性依据；当前发行人年度收益分母仍缺失。不将旧 CIK 的 EPS 拼接为当前年度分母，供应商身份冲突也不会自动消失。</p>'
    if scope.get('reason')=='depositary_security_requires_separate_method':html+='<p>封面普通股标题还带有不直接交易的限制，不能把它当成纽约交易的 ADS 本身。</p>'
    symbols=scope.get('issuer_symbols',[])
    html+='<p>SEC 关联代码：'+_text('、'.join(str(s) for s in symbols))+'。不代表这些代码已逐一完成证券映射；下列封面原始代码作为独立观察保留。</p>'
    if scope.get('unassigned_issuer_symbols'):html+='<p>尚未逐一建立证券映射：'+_text('、'.join(scope['unassigned_issuer_symbols']))+'。本次仅核对所选证券，不授予关联代码相同的价格或估值资格。</p>'
    labels={'annual':'年度财报','cover':'已核对的 8-K 封面','successor':'继承发行人申报','quarter':'季度财报','annual_companion':'年度财报的同次申报附件','cover_companion':'8-K 的同次申报附件'}
    for doc in scope.get('documents',[]):
        html+='<p>'+_text(labels.get(doc.get('role'),doc.get('role')))+' · '+_text(doc.get('form'))+' · '+_text(doc.get('accessionNumber'))+' · 期间末 '+_text(doc.get('reportDate'))+' · 发布 '+_text(doc.get('filingDate'))+' · 接收 '+_text(doc.get('acceptanceDateTime'))+' · 观察 '+_text(doc.get('observed_at'))+' · '+_link(doc.get('source_ref'),'具体文件')+'</p>'
        selected=doc.get('selected_common')
        if doc.get('parent_source_ref'):
            html+='<p>'+_text(doc.get('parent_form'))+' '+_link(doc.get('parent_source_ref'),'主文件引用')+'：'+_text(doc.get('parent_href'))+'。上列期间、发布与接收日期属于同次主申报，附件类型单独列示。</p>'
        if isinstance(selected,Mapping):
            html+='<p>所选证券：'+_text(selected.get('ticker'))+' · '+_text(selected.get('title'))+' · '+_text(selected.get('exchange'))+'</p>'
            html+='<p>'+ ' · '.join(_link(ref,label) for ref,label in zip(selected.get('fact_refs',[]),('封面证券标题','封面交易代码','封面交易所')))+'</p>'
            if selected.get('context_source_ref'):html+='<p>'+_link(selected['context_source_ref'],'证券上下文来源')+'</p>'
            if selected.get('consistent_duplicate_refs'):html+='<p>已核对的一致交易所列示：'+' · '.join(_link(ref,'原始事实') for ref in selected['consistent_duplicate_refs'])+'</p>'
        observations=doc.get('raw_cover_observations',[])
        if observations:html+='<ul>'+''.join('<li>'+_text(r.get('raw_symbol'))+' · '+_text(r.get('title'))+'</li>' for r in observations if isinstance(r,Mapping))+'</ul>'
        html+='<p>原始响应 SHA-256 <code>'+_text(doc.get('payload_sha256'))+'</code><br>已核对正文 SHA-256 <code>'+_text(doc.get('body_sha256'))+'</code></p>'
    for ref in scope.get('basis_refs',[]):html+='<p>'+_link(ref.get('source_ref'),'普通股资本与收益定义')+' · '+_text(ref.get('concept'))+'</p>'
    html+=_observations_html(scope)
    eps=scope.get('original_eps')
    if isinstance(eps,Mapping):
        html+='<p>事实期间与单位：'+_text(eps.get('period_start'))+' → '+_text(eps.get('period_end'))+' · USD/shares。直接年度稀释 EPS 与 Companyfacts 同次申报记录另行核对。</p>'
        for proof in eps.get('proofs',[]):
            if not isinstance(proof,Mapping):continue
            html+='<p>'+_link(proof.get('source_ref'),'EPS 原始事实')
            if proof.get('context_source_ref'):html+=' · '+_link(proof['context_source_ref'],'EPS 期间与实体上下文')
            if proof.get('unit_source_ref'):html+=' · '+_link(proof['unit_source_ref'],'EPS 单位定义')
            html+='</p>'
    if any(d.get('binding_normalization')=='sec-empty-tail-script-v1' for d in scope.get('documents',[])):
        html+='<p>正文核对仅排除 SEC 响应末尾已声明的空外部脚本；每次响应的原始摘要仍完整保留，财务正文变更继续受限。</p>'
    return html+'<p>仅个人研究，不授予法律证券分类、来源商业权限或正式数据资格。</p></details>'


def _vendor_filing_evidence_html(identity):
    if not isinstance(identity, Mapping):
        return ''
    if identity.get('history_source_ref'):
        return '<p>历史 SEC 索引仅用于供应商身份核对；年度 EPS 仍使用当前选定的年度申报。'+_link(identity.get('history_source_ref'),'官方历史索引')+' · 观察 '+_text(identity.get('history_observed_at'))+' · SHA-256 <code>'+_text(identity.get('history_sha256'))+'</code></p>'
    documents = identity.get('cofiling_documents')
    if not isinstance(documents, list) or len(documents) != 2:
        return ''
    html = '<p>联报 10-Q 仅用于报价来源身份核对。年度摊薄 EPS 仍取自 10-K。申报编号 '+_text(identity.get('accession'))+'。</p>'
    for document, label in zip(documents, ('SEC 母公司副本', 'SEC 联报公司副本'), strict=True):
        html += ('<p>'+_link(document.get('source_url'),label)+' · 观察 '+_text(document.get('observed_at'))
                 +' · 原始 SHA-256 <code>'+_text(document.get('payload_sha256'))+'</code></p>')
    html += '<p>'+_link(identity.get('co_registrant_source_ref'),'联报公司 SEC 申报索引')+' · 已核对正文 SHA-256 <code>'+_text(documents[0].get('body_sha256'))+'</code></p>'
    return html


def _listing_venue_evidence_html(evidence):
    if not isinstance(evidence, Mapping):
        return ''
    return ('<p>SEC 摘要标为 '+_text(evidence.get('reported_exchange'))
            +'。申报可见封面、上市目录及报价均核对为 '+_text(evidence.get('confirmed_exchange'))+'。'
            +_link(evidence.get('source_url'),'NYSE American 交易所核对')+' · 提交 '+_text(evidence.get('filed'))
            +' · 观察 '+_text(evidence.get('observed_at'))+' · 已核对正文 SHA-256 <code>'
            +_text(evidence.get('body_sha256'))+'</code></p>')


def _listing_html(v):
    context=v.get('listing_context')
    if not isinstance(context,Mapping):return ''
    selection=context.get('selection')
    if selection=='recent_session':
        answer='上市来源本次暂不可用；沿用本会话 24 小时内的完整上市观察。原始日期未续期，财报与价格仍独立核查。'
    elif selection=='returned_receipt':
        answer='上市证据采用本次返回的完整来源回执；以下为来源原始观察日期，未续期。'
    else:answer='没有可用的近期完整上市观察，本次财报与价格核查未继续；请稍后重试。'
    html='<div class="peer-listing-context"><p><strong>'+answer+'</strong></p>'
    if context.get('observed_from'):
        html+='<p>上市观察：'+_text(context['observed_from'])+' → '+_text(context.get('observed_to'))+'。</p>'
    html+='<details><summary>上市来源日期、摘要与本次获取记录</summary>'
    html+='<p>上市获取尝试：'+_text(context.get('attempted_at'))+' → '+_text(context.get('completed_at'))+'。</p>'
    for ref in context.get('source_receipts',[])[:4]:
        html+='<p>'+_link(ref.get('source_url'),'上市或 SEC 关联来源')+' · 原始观察 '+_text(ref.get('observed_at'))
        if ref.get('source_created_at'):html+=' · 目录创建 '+_text(ref['source_created_at'])+'（纽约时间）'
        html+=' · SHA-256 <code>'+_text(ref.get('payload_sha256'))+'</code></p>'
    failures={'directory_incomplete':'目录内容不完整','source_access_limited':'来源限制访问，未自动重试',
              'source_transport_unavailable':'来源暂不可访问','source_response_unverified':'响应地址或内容未核对',
              'directory_schema_invalid':'目录结构未通过核对','directory_date_invalid':'目录创建日期过旧或在未来'}
    for attempt in context.get('source_attempts',[])[:4]:
        message=failures.get(attempt.get('reason'),'仅收到响应；不代表整套上市证据已通过核对')
        html+='<p>本次获取 '+_text(attempt.get('observed_at',context.get('attempted_at')))+' · '+_link(attempt.get('source_url'),'查询来源')+' · '+message
        if type(attempt.get('byte_count')) is int:html+=' · '+str(attempt['byte_count'])+' bytes'
        if attempt.get('payload_sha256'):html+=' · SHA-256 <code>'+_text(attempt['payload_sha256'])+'</code>'
        html+='</p>'
    return html+'</details></div>'


def _excluded_html(v):
    excluded = v.get('excluded')
    rows = [row for row in excluded if isinstance(row, Mapping)] if isinstance(excluded, list) else []
    if not rows:
        return ''
    items = ''.join(
        '<li><details><summary>'+_text(row.get('ticker'))+'：'+_text(_reason(row.get('reason')))
        +'</summary>'+_diagnostic_html(row.get('diagnostics'))+'</details></li>'
        for row in rows
    )
    label = '候选排除与待核查' if v.get('candidate_basis') == QCOM_SIC_BASIS else '未纳入参照的公司与原因'
    return '<details><summary>'+label+'（'+str(len(rows))+' 家）</summary><ul>'+items+'</ul></details>'


def _disclosure(v,rows,*,include_excluded=True):
    html='<p>本次来源查询：'+_text(v['attempted_at'])+'</p>' if v.get('attempted_at') else ''
    html+=_listing_html(v)+'<p>自动筛选的行业参照组：同供应商行业、同 SEC 行业代码、普通股、独立发行人、同一价格日期。每家实际财年起止日期与本公司相差不超过 '+str(FISCAL_WINDOW_DAYS)+' 天；这不是完全相同的期间，也不是分析师审核的经济可比组。</p>'
    html+='<p>至少 '+str(MIN_PEERS)+' 家参照公司通过同口径核对后才比较倍数。</p>'
    if v.get('candidate_basis') == QCOM_SIC_BASIS:
        html+='<p>SEC SIC 3663 候选已核查 '+_text(v.get('checked_candidate_count'))+' / '+_text(v.get('candidate_count'))
        html+=' · 待核查 '+_text(v.get('pending_candidate_count'))+'。这份名单来自已核对的有限样本；每家公司仍须通过供应商行业和其他比较条件。'+_link(v.get('candidate_source_ref'),'SEC SIC 分类')+'</p>'
    else:
        html+='<p>候选列表共 '+_text(v.get('industry_candidate_total'))+' 个记录，本次最多核查 12 家其他公司，按供应商列表顺序保留；不是完整行业覆盖。</p>'
        if v.get('industry_source_ref'):
            html+='<p>'+_link(v['industry_source_ref'],'候选组来源')+' · 观察 '+_text(v.get('industry_observed_at'))+'</p>'
    context=v.get('subject_source_context')
    if isinstance(context,Mapping) and context:
        html+='<h4>本公司申报元数据与收益字段线索</h4><p>CIK '+_text(context.get('sec_cik'))+' · '+_link(context.get('profile_source_ref'),'SEC 申报元数据')+' · '+_link(context.get('facts_query_ref'),'收益字段查询地址')+' · 观察 '+_text(context.get('profile_observed_at'))+'。列出元数据不代表对应收益字段已通过核对。</p><ul>'
        for filing in context.get('annual_versions',[]):
            html+='<li>'+_text(filing.get('form'))+' · '+_text(filing.get('accession'))+' · 期间末 '+_text(filing.get('period_end'))+' · 发布 '+_text(filing.get('filed'))+' · 接收 '+_text(filing.get('accepted_at'))+' · '+_link(filing.get('source_ref'),'具体申报')+'</li>'
        html+='</ul>'
        html+=_selected_security_html(context.get('selected_security_scope'))
        if not rows:
            html+=_vendor_filing_evidence_html(context.get('vendor_identity_observation'))
            html+=_listing_venue_evidence_html(context.get('listing_venue_evidence'))
    if rows:html+=_source_table(rows)+_earnings_table(rows)
    if include_excluded:html+=_excluded_html(v)
    html+='<details><summary>字段定义、观察日期与来源摘要</summary>'
    for row in rows:
        html+='<h4>'+_text(row.get('ticker'))+'</h4><p>us-gaap:EarningsPerShareDiluted · USD/shares · '+_text(row.get('form'))+' · accession '+_text(row.get('accession'))+' · 发布 '+_text(row.get('filed'))+'</p>'
        html+=_amendment_html(row.get('amendment_scope'))
        if row.get('ticker')!=v.get('ticker'):html+=_selected_security_html(row.get('selected_security_scope'))
        html+='<p>财报观察 '+_text(row.get('observed_at'))+'；价格观察 '+_text(row.get('price_observed_at'))+'；供应商身份观察 '+_text(row.get('vendor_observed_at'))+'。</p>'
        html+='<p>价格与拆股观察请求 '+_text(row.get('price_history_range'))+'；实际 '+_text(row.get('price_history_first_date'))+' → '+_text(row.get('price_history_last_date'))+'；请求范围不保证历史完整。</p>'
        identity=row.get('vendor_filing') if isinstance(row.get('vendor_filing'),Mapping) else {}
        html+='<p>CIK '+_text(row.get('sec_cik'))+' · '+_link(identity.get('source_ref'),'供应商申报身份依据')+'。当前匹配不证明历史证券连续性或发行人所在地。</p>'
        html+=_vendor_filing_evidence_html(identity)
        html+=_listing_venue_evidence_html(row.get('listing_venue_evidence'))
        for key,label in [('facts_sha256','SEC 原始响应 SHA-256'),('price_sha256','价格原始响应 SHA-256'),('vendor_normalized_sha256','供应商 normalized SHA-256')]:
            value=row.get(key)
            html+='<p>'+label+'：<code>'+(_text(value) if isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) else '未取得')+'</code></p>'
    html+='</details><p>来源权限：仅个人研究检查。价格与供应商资料的商业使用及再分发权限未通过核对；本字段不新增 SEC 商业字段批准，不更新已保存模型、记录或覆盖状态。</p>'
    return html


def online_peer_valuation_html(view,*,sources_only=False,show_coverage_link=True):
    v=view if isinstance(view,Mapping) else {}
    if v.get('status')=='not_requested':return ''
    subject=v.get('subject') if isinstance(v.get('subject'),Mapping) else None
    peers=[r for r in v.get('peers',[]) if isinstance(r,Mapping)] if isinstance(v.get('peers'),list) else []
    rows=([subject] if subject else [])+peers
    if sources_only:
        return STYLE+'<section class="online-peer-valuation" aria-label="Online peer valuation sources"><h3>在线同行估值来源</h3><p>'+_text(_reason(v.get('reason')))+'</p>'+_disclosure(v,rows)+'</section>'
    supported=(v.get('status')=='research_comparison' and subject is not None and subject.get('ticker')==v.get('ticker')
               and len(peers)>=MIN_PEERS and v.get('peer_count')==len(peers)
               and _number(v.get('premium_fraction')) and _number(v.get('peer_median')) and v['peer_median']>0)
    headline='暂不判断相对贵便宜'
    if supported:
        premium=v['premium_fraction'];amount=f'{abs(premium)*100:.1f}%' if abs(premium)>=.0005 else '<0.1%'
        headline=('年度 P/E 等于同行参照中位数' if premium==0 else '年度 P/E '+('高于' if premium>0 else '低于')+'同行参照 '+amount)
    kicker='在线来源 · 已披露年度稀释 P/E · 非 TTM / 非预测值'
    html=STYLE+'<section class="online-peer-valuation peer-comparison" aria-label="Online peer valuation"><h3>'+_text(headline)+'</h3>'
    stats=[('价格日期',_text(subject.get('price_date')) if subject else '未取得'),
           ('通过筛选的同行',str(len(peers))+' 家' if subject else '未核查'),
           ('本公司年度 P/E',_multiple(subject.get('multiple')) if subject else '未取得'),
           ('同行参照中位数',_multiple(v.get('peer_median')) if supported else '暂不显示')]
    html+='<dl class="peer-stats peer-comparison-stats">'+''.join('<div><dt>'+label+'</dt><dd>'+value+'</dd></div>' for label,value in stats)+'</dl>'
    if not supported:html+='<p>'+_text(_reason(v.get('reason')))+'</p>'
    html+='<p class="peer-kicker">'+kicker+'</p>'
    html+='<p>这是单一指标的相对比较，不是低估或高估结论。业务结构、增长、利润率、资本需求和风险差异尚未调整。</p>'
    if subject:
        html+='<details><summary>比较方法与盈利背景</summary>'
        html += '<p><strong>倍数怎么算</strong>　同日收盘价 ÷ 已披露年度稀释 EPS。</p>'
        if supported:
            html += ('<p><strong>差距怎么算</strong>　本公司 '+_multiple(subject.get('multiple'))
                     +' ÷ 同行中位数 '+_multiple(v['peer_median'])+' − 1。百分比按未四舍五入的倍数计算。</p>')
        if peers:
            members = '、'.join(_text(peer.get('ticker')) for peer in peers)
            html += ('<p><strong>为什么纳入这些公司</strong>　'+members
                     +'。供应商行业与 SEC 行业代码均匹配，均为独立发行人的普通股，使用同日价格，'
                     +'财年起止各相差不超过 '+str(FISCAL_WINDOW_DAYS)+' 天。</p>')
        html+='<h4>盈利变化背景</h4><p><strong>'+_text(_earnings_phrase(subject))+'</strong> · 同一年度申报列示值。</p><p>历史变化不代表未来增长；同行倍数未按增长调整。展开下方可核对每家公司的本年、上年 EPS 与实际期间。</p>'
        if subject.get('amendment_scope'):html+='<p>EPS 采用已交叉核对的原始年度申报；具体修订范围、来源与标记差异见下方依据。</p>'
        html+='</details>'+_excluded_html(v)
    scope=v.get('subject_source_context',{}).get('selected_security_scope',{}) if isinstance(v.get('subject_source_context'),Mapping) else {}
    if not subject and isinstance(scope,Mapping) and scope.get('status')=='inspection_only':html+=_observations_html(scope,compact=True)
    html+='<details><summary>查看实际财年、价格与来源</summary>'+_disclosure(v,rows,include_excluded=not subject)+'</details>'
    html+='<details><summary>其他估值口径为什么尚未显示</summary><p>TTM / 预测 P/E、P/S、P/FCF、EV/EBITDA 还需要分别核对期间、股数、企业价值与成分定义；本次不会从股票存在或其他倍数推断。</p></details>'
    if show_coverage_link:
        html+='<p><a href="?mode=research&amp;page=discover#peer-coverage-sample" target="_self">查看跨行业同行覆盖</a></p>'
    return html+'</section>'
