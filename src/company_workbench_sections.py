"""Read-only company-page projection; reported facts never promote saved models."""
from collections.abc import Mapping
from html import escape
import re

from src.online_company_identity import _mode_reason
from src.online_history_contract import validated_annual_history
from src.sec_quarterly_history import validated_quarterly_history
from src.sec_foreign_financials import validated_foreign_financials
from src.online_research_history_view import validated_online_price_history
from src.online_research_expansion_view import financial_field_label

SECTIONS = (
    ('overview', '概览'), ('financials', '财务趋势'), ('valuation', '估值与同行'),
    ('notes', '研究记录'), ('sources', '数据来源'),
)
FIELD_LABELS = {'revenue':'营收', 'operating_income':'经营利润',
                'cash_from_operations':'经营现金流', 'capital_expenditures':'资本支出'}


def section_key(value):
    return value if isinstance(value,str) and value in dict(SECTIONS) else 'overview'


def workbench_projection(ticker, financial_view, prices, expected_cik=None):
    view=financial_view if isinstance(financial_view,Mapping) else {}
    result=dict(ticker=ticker, annual_count=0, quarter_count=0, price_count=0,
                facts={}, period_end=None, period_start=None, period_kind=None,
                unit=None, identity_conflict=False, model_eligibility='independent',
                readiness_promoted=False, withheld_periods=[], attempted=any(
                    isinstance(item,Mapping) and item.get('status') not in (None,'not_requested')
                    for item in (financial_view,prices)))
    if _mode_reason('research'):
        return result
    identities=[view.get('sec_cik')]
    for key in ('companyfacts_identity','annual_history','quarterly_history','foreign_financials'):
        item=view.get(key)
        if isinstance(item,Mapping):identities.append(item.get('sec_cik'))
    known=[c for c in identities if c is not None]
    if (any(not isinstance(c,str) or re.fullmatch(r'\d{10}',c) is None or int(c)==0 for c in known)
        or len(set(known))>1 or expected_cik is not None and any(c!=expected_cik for c in known)):
        result['identity_conflict']=True
        return result
    price=validated_online_price_history(prices,ticker=ticker)
    result['price_count']=len(price['bars']) if price else 0
    if view.get('ticker')!=ticker:
        return result
    annual=validated_annual_history(view) if view.get('status')=='inspection_only' else None
    quarter=validated_quarterly_history(view)
    foreign=validated_foreign_financials(view)
    candidates=[]
    def inspect_latest(kind,rows,history):
        if not rows:return
        row=rows[-1]
        if row['status']=='available':
            candidates.append((kind,row,history['unit']))
        else:
            result['withheld_periods'].append(dict(kind=kind,period_end=row['period_end'],
                reason=row['reason'],filed=row.get('filed'),source_ref=history.get('source_url'),
                observed_at=history.get('observed_at')))
    for kind,history in (('annual',annual),('quarterly',quarter)):
        if history is None:continue
        rows=history['periods'];available=[r for r in rows if r['status']=='available']
        result['annual_count' if kind=='annual' else 'quarter_count']=len(available)
        inspect_latest(kind,rows,history)
    if foreign is not None:
        for kind,key in (('annual','annual_count'),('quarterly','quarter_count')):
            rows=foreign[kind]
            result[key]=len([r for r in rows if r['status']=='available'])
            inspect_latest(kind,rows,foreign)
    if candidates:
        kind,row,unit=max(candidates,key=lambda item:item[1]['period_end'])
        fields=row['fields'];fields={f['field']:f for f in fields} if isinstance(fields,list) else fields
        result.update(facts={k:dict(v) for k,v in fields.items() if k in FIELD_LABELS},
                      period_start=row['period_start'],period_end=row['period_end'],period_kind=kind,unit=unit,
                      filed=row.get('filed'))
    result['withheld_periods']=[row for row in result['withheld_periods']
                               if result['period_end'] is None or row['period_end']>result['period_end']]
    return result


STYLE='''<style>
.company-integrated{min-width:0}.company-integrated-header{padding:16px 0 12px!important;border:0!important;background:transparent!important;box-shadow:none!important;border-radius:0!important;margin:0!important}
.company-integrated-header .company-coverage-details{margin:5px 0;color:#52615c;font-size:.8rem}.company-coverage-details summary{cursor:pointer}.company-coverage-details summary:focus-visible{outline:3px solid #245842;outline-offset:2px}
.company-integrated-header h1{font-size:2rem!important;line-height:1.2!important;margin:0 0 8px!important;padding:0!important}.company-integrated-header p{margin:5px 0;font-size:.9rem}.company-integrated-header .public-primary-action{display:inline-flex;align-items:center;min-height:44px;padding:0 12px;border:1px solid #b8c9be;border-radius:7px;color:#173e30!important;background:#f1f6f3;text-decoration:none}
.company-fact-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr));gap:10px;margin:12px 0}.company-fact-grid div{background:#fff;border:1px solid #dce3de;padding:14px;border-radius:8px;min-width:0;overflow-wrap:anywhere}.company-fact-grid dt{font-size:.85rem;color:#52615c}.company-fact-grid dd{font-weight:700;margin:6px 0 0;font-size:1.15rem}.company-fact-grid small{display:block;color:#52615c;font-size:.78rem;margin-top:6px}.company-scope-note{font-size:.86rem;color:#52615c;overflow-wrap:anywhere}
.st-key-company-section-navigation [role="radiogroup"]{display:flex;flex-wrap:wrap;gap:6px}.st-key-company-section-navigation label{min-height:44px;padding:8px 12px!important;border:1px solid #dce3de;border-radius:7px;background:#fff;box-sizing:border-box}.st-key-company-section-navigation label:has(input:checked){background:#e6f0e9;border-color:#426a55}.st-key-company-section-navigation label p{color:#173e30!important;margin:0!important}.st-key-company-section-navigation input{accent-color:#155e4b}
@media(max-width:640px){.company-integrated-header h1{font-size:1.55rem!important}.st-key-company-section-navigation label{flex:1 1 25%;justify-content:center;padding:8px 5px!important}.company-fact-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:260px){.company-fact-grid{grid-template-columns:1fr}.st-key-company-section-navigation label{flex-basis:40%}}
</style>'''


def workbench_header_html(ticker, projection, saved_scope, title=None,saved_receipt_only=False,*,answers_html=''):
    p=projection
    scope='已保存研究；在线查询结果独立展示' if saved_scope else '在线公司候选；与已保存研究的身份仍需核对'
    if saved_receipt_only:scope='已保存 SEC 证据；当前上市身份与本地模型资格仍需独立核对'
    scope+=' · Research-only'
    stylesheet=STYLE
    if answers_html:
        from src.company_answer_summary import COMPANY_ANSWERS_STYLE
        # Streamlit's Markdown renderer needs one uninterrupted style block before the header.
        stylesheet=STYLE.removesuffix('</style>')+COMPANY_ANSWERS_STYLE+'</style>'
    heading=(stylesheet+'<section class="company-workbench-primary-brief company-integrated-header" aria-label="Company Brief">'
            '<h1>'+escape(ticker)+' Company Brief</h1>'
            +('<p>'+escape(str(title)[:140])+'</p>' if title else '')
            +answers_html+'<p>'+escape(scope)+'</p>')
    status=(f"可阅读财报：{p['annual_count']} 个年度 / {p['quarter_count']} 个季度 · 价格：{p['price_count']} 个日线观察"
            if any(p[k] for k in ('annual_count','quarter_count','price_count')) else '财报与价格尚未查询')
    if p.get('attempted') and not any(p[k] for k in ('annual_count','quarter_count','price_count')):
        status='暂无通过核对的财报趋势或日线历史；请在数据来源查看原因，或明确重试更新'
    if p['identity_conflict']:status='来源公司身份冲突；数值暂不展示'
    status_html='<p>'+escape(status)+'</p>'
    if answers_html and not p['identity_conflict']:
        status_html=('<details class="company-coverage-details"><summary>财报与价格核对范围</summary>'
                     +status_html+'</details>')
    return (heading+status_html
            +'<p class="company-scope-note">模型资格独立：在线事实不更新已保存数据、已保存估值输入或研究记录。</p>'
            '<a class="public-primary-action" href="#company-research-sections" target="_self">选择研究分区</a></section>')


def workbench_facts_html(projection):
    p=projection
    reasons={'latest_reported_quarter_revenue_unavailable':'该报告季度缺少可核对的收入字段',
             'raw_source_conflict':'来源字段存在冲突',
             'matching_direct_fact_unavailable':'缺少期间匹配的直接申报字段',
             'ambiguous_quarter_context':'申报期间或上下文仍有歧义'}
    gaps=''.join('<p class="company-scope-note" data-withheld-reason="'+escape(row['reason'],quote=True)
        +'">较新申报期间 · '+('季度' if row['kind']=='quarterly' else '年度')+' '+escape(row['period_end'])
        +' 仍待补充：'+escape(reasons.get(row['reason'],row['reason'].replace('_',' ')))
        +'。较早的可读数值不代表该期间已覆盖；来源与原因见数据来源。</p>' for row in p.get('withheld_periods',[]))
    if not p['facts']:
        return gaps+'<p class="company-scope-note">财报事实尚未取得或来源未通过核对。使用上方更新操作；逐字段原因可在数据来源查看。</p>'
    cards=[]
    for key,label in FIELD_LABELS.items():
        field=p['facts'].get(key)
        amount=format(field['value'],',.0f') if field else '待补充'
        scope=financial_field_label(key,field) if field else '该期间没有可核对的直接字段'
        definition=scope+(' · '+field.get('concept','') if field else '')
        cards.append('<div><dt>'+label+'</dt><dd>'+escape(amount)+'</dd><small>'+escape(definition)+'</small></div>')
    kind='直接报告季度' if p['period_kind']=='quarterly' else '报告年度'
    return (gaps+'<h3>可核对财报摘要</h3><p class="company-scope-note">'+escape(kind+' · '+p['period_start']+' → '+p['period_end']+' · '+p['unit'])
            +' · 当前可核对期间，不代表最新申报已覆盖，也不是点时历史。</p><dl class="company-fact-grid">'+''.join(cards)+'</dl>')
