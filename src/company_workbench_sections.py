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
    ('overview', 'Overview'), ('financials', 'Financial Trends'), ('valuation', 'Valuation & Peers'),
    ('notes', 'Research Notes'), ('sources', 'Data Sources'),
)
FIELD_LABELS = {'revenue':'Revenue', 'operating_income':'Operating income',
                'cash_from_operations':'Operating cash flow', 'capital_expenditures':'Capital expenditures'}


def section_key(value):
    return value if isinstance(value,str) and value in dict(SECTIONS) else 'overview'


def workbench_projection(ticker, financial_view, prices, expected_cik=None, *, as_of=None):
    view=financial_view if isinstance(financial_view,Mapping) else {}
    result=dict(ticker=ticker, annual_count=0, quarter_count=0, price_count=0,
                facts={}, period_end=None, period_start=None, period_kind=None,
                unit=None, identity_conflict=False, model_eligibility='independent',
                readiness_promoted=False, withheld_periods=[], annual_archive=None, native_quarter_archive=None,
                native_quarter_selected=False, native_ytd_missing=False, comparative=None,
                withheld_fields={}, attempted=any(
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
    from src.sec_online_quarter_evidence import validated_archive_quarter
    from src.sec_online_quarter_view import merge_archive_quarter
    archive=validated_archive_quarter(view)
    if archive:
        quarter=dict(unit=archive['unit'],source_url=archive['source_url'],observed_at=archive['observed_at'],
                     periods=merge_archive_quarter(quarter['periods'] if quarter else [],archive))
    foreign=validated_foreign_financials(view)
    from src.sec_online_annual_evidence import validated_archive_annual
    from src.sec_native_annual_history import native_archive_annual_rows, native_annual_comparison
    from src.sec_online_native_quarter_evidence import validated_native_quarter
    from src.online_filing_context import corroborate_online_financials, selected_native_quarter_periods
    native_annual=validated_archive_annual(view, as_of=as_of)
    native_quarter=validated_native_quarter(view,ticker=ticker,expected_cik=expected_cik,as_of=as_of)
    coverage=corroborate_online_financials(view,view['filing_inventory'],as_of=as_of) if native_annual or native_quarter else {}
    if not coverage.get('structured_annual'):
        native_annual=None
    native_rows=dict(selected_native_quarter_periods(native_quarter,coverage))
    native_current=native_rows.get('quarterly')
    if native_rows:
        selected=list(native_rows.values())
        result['native_quarter_archive']=dict(native_quarter,periods=selected,
            comparative_periods=native_quarter.get('comparative_periods', []) if native_current else [],
            excluded_kinds=[row['kind'] for row in native_quarter['periods'] if row not in selected])
    result['annual_archive']=native_annual
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
        if history is None or kind=='annual' and native_annual or kind=='quarterly' and native_current:continue
        rows=history['periods'];available=[r for r in rows if r['status']=='available']
        result['annual_count' if kind=='annual' else 'quarter_count']=len(available)
        inspect_latest(kind,rows,history)
    if foreign is not None:
        for kind,key in (('annual','annual_count'),('quarterly','quarter_count')):
            if kind=='annual' and native_annual or kind=='quarterly' and native_current:continue
            rows=foreign[kind]
            if rows and foreign['unit'] != 'USD':
                candidates=[candidate for candidate in candidates if candidate[0] != kind]
            result[key]=len([r for r in rows if r['status']=='available'])
            inspect_latest(kind,rows,foreign)
    if native_annual:
        annual_rows=native_archive_annual_rows(foreign,native_annual)
        result['annual_count']=sum(r['status']=='available' for r in annual_rows)
        inspect_latest('annual',annual_rows,native_annual)
    if native_current:
        history=foreign['quarterly'] if foreign and foreign['unit']==native_current['unit'] else []
        result['quarter_count']=1+sum(r['status']=='available' and r['period_end']<native_current['period_end'] for r in history)
        inspect_latest('quarterly',[native_current],native_quarter)
    if candidates:
        kind,row,unit=max(candidates,key=lambda item:item[1]['period_end'])
        fields=row['fields'];fields={f['field']:f for f in fields} if isinstance(fields,list) else fields
        result.update(facts={k:dict(v) for k,v in fields.items() if k in FIELD_LABELS},
                      period_start=row['period_start'],period_end=row['period_end'],period_kind=kind,unit=unit,
                      filed=row.get('filed'))
        if native_annual and row is native_annual['periods'][0]:
            result['withheld_fields']=dict(row['withheld_fields'])
            result['comparative']=native_annual_comparison(row,annual_rows,coverage)
        if row is native_current:
            ytd_state=coverage['current']['interim']
            ytd_anchor=ytd_state.get('anchor') or {}
            result.update(withheld_fields=dict(row['withheld_fields']), native_quarter_selected=True,
                          native_ytd_missing=not (ytd_state['status']=='corroborated'
                                                  and ytd_anchor.get('period_end')==row['period_end']))
    result['withheld_periods']=[row for row in result['withheld_periods']
                               if result['period_end'] is None or row['period_end']>result['period_end']]
    return result


STYLE='''<style>
.company-integrated{min-width:0}.company-integrated-header{padding:16px 0 12px!important;border:0!important;background:transparent!important;box-shadow:none!important;border-radius:0!important;margin:0!important}
.company-integrated-header .company-coverage-details{margin:5px 0;color:#52615c;font-size:.8rem}.company-coverage-details summary{cursor:pointer}.company-coverage-details summary:focus-visible{outline:3px solid #245842;outline-offset:2px}
.company-integrated-header h1{font-size:2rem!important;line-height:1.2!important;margin:0 0 8px!important;padding:0!important}.company-integrated-header p{margin:5px 0;font-size:.9rem}.company-integrated-header .public-primary-action{display:inline-flex;align-items:center;min-height:44px;padding:0 12px;border:1px solid #b8c9be;border-radius:7px;color:#173e30!important;background:#f1f6f3;text-decoration:none}
.company-fact-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr));gap:10px;margin:12px 0}.company-fact-grid div{background:#fff;border:1px solid #dce3de;padding:14px;border-radius:8px;min-width:0;overflow-wrap:anywhere}.company-fact-grid dt{font-size:.85rem;color:#52615c}.company-fact-grid dd{font-weight:700;margin:6px 0 0;font-size:1.15rem}.company-fact-grid small{display:block;color:#52615c;font-size:.78rem;margin-top:6px}.company-scope-note{font-size:.86rem;color:#52615c;overflow-wrap:anywhere}
.st-key-company-section-navigation [role="radiogroup"]{display:flex;flex-wrap:wrap;gap:6px}.st-key-company-section-navigation label{min-height:44px;padding:8px 12px!important;border:1px solid #dce3de;border-radius:7px;background:#fff;box-sizing:border-box}.st-key-company-section-navigation label:has(input:checked){background:#e6f0e9;border-color:#426a55}.st-key-company-section-navigation label p{color:#173e30!important;margin:0!important}.st-key-company-section-navigation input{accent-color:#155e4b}
.st-key-company-update-actions{margin-bottom:8px}.st-key-company-update-actions button{min-height:44px}.st-key-company-section-navigation label{min-width:0}.st-key-company-section-navigation label p{white-space:normal;line-height:1.3!important}
.st-key-company-update-actions [data-testid="stPopoverButton"]{min-width:8.75rem;background:#f1f6f3!important;color:#173e30!important;border-color:#b8c9be!important}
.st-key-company-update-actions [data-testid="stPopoverButton"] p,.st-key-company-update-actions [data-testid="stPopoverButton"] span{color:#173e30!important}
.st-key-company-update-actions [data-testid="stPopoverButton"]:hover{background:#e6f0e9!important}
.company-load-prompt{margin:8px 0!important;font-size:.95rem!important}
@media(max-width:640px){.company-integrated-header h1{font-size:1.55rem!important}.st-key-company-section-navigation label{flex:1 1 40%;justify-content:center;padding:8px 6px!important}.company-fact-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:260px){.company-fact-grid{grid-template-columns:1fr}.st-key-company-section-navigation label{flex-basis:100%}}
</style>'''


def workbench_header_html(ticker, projection, saved_scope, title=None,saved_receipt_only=False,*,answers_html=''):
    p=projection
    scope='Saved research with separate online observations' if saved_scope else 'Online company candidate; saved research identity needs its own check'
    if saved_receipt_only:scope='Saved SEC evidence; current listing identity and local model eligibility need their own checks'
    scope+=' · Research-only'
    stylesheet=STYLE
    if answers_html:
        from src.company_answer_summary import COMPANY_ANSWERS_STYLE
        # Streamlit's Markdown renderer needs one uninterrupted style block before the header.
        stylesheet=STYLE.removesuffix('</style>')+COMPANY_ANSWERS_STYLE+'</style>'
    heading=(stylesheet+'<section class="company-workbench-primary-brief company-integrated-header" aria-label="Company Brief">'
            '<h1>'+escape(ticker)+' Company Brief</h1>'
            +('<p>'+escape(str(title)[:140])+'</p>' if title else '')
            +answers_html)
    status=(f"Available observations: {p['annual_count']} annual / {p['quarter_count']} quarterly periods · {p['price_count']} daily prices"
            if any(p[k] for k in ('annual_count','quarter_count','price_count')) else 'Financials and prices have not been requested')
    if p.get('attempted') and not any(p[k] for k in ('annual_count','quarter_count','price_count')):
        status='No verified financial trend or daily price history is available. Check Data Sources for the reason or refresh explicitly.'
    if p['identity_conflict']:status='Company identity conflicts across sources. Values are withheld.'
    status_html='<p>'+escape(status)+'</p>'
    if p['identity_conflict']:
        heading+=status_html
    return (heading+'<details class="company-coverage-details"><summary>Evidence scope</summary>'
            +'<p>'+escape(scope)+'</p>'+status_html
            +'<p class="company-scope-note">Online observations and saved models have separate eligibility. Saved financials, model inputs, and research records retain their original sources.</p>'
            '</details></section>')


def workbench_facts_html(projection):
    p=projection
    reasons={'latest_reported_quarter_revenue_unavailable':'Verified revenue is unavailable for this reported quarter',
             'raw_source_conflict':'Source facts conflict',
             'matching_direct_fact_unavailable':'A matching directly reported fact is unavailable',
             'ambiguous_quarter_context':'The reporting period or context is ambiguous'}
    gaps=''.join('<p class="company-scope-note" data-withheld-reason="'+escape(row['reason'],quote=True)
        +'">Newer reported period · '+('Quarter' if row['kind']=='quarterly' else 'Annual')+' '+escape(row['period_end'])
        +' · Gap: '+escape(reasons.get(row['reason'],row['reason'].replace('_',' ')))
        +'. Earlier available values apply to their own periods. Check Data Sources for details.</p>' for row in p.get('withheld_periods',[]))
    if not p['facts']:
        return gaps+'<p class="company-scope-note">Verified financial facts are unavailable. Refresh financials and prices, then check Data Sources for field-level reasons.</p>'
    cards=[]
    for key,label in FIELD_LABELS.items():
        field=p['facts'].get(key)
        amount=format(field['value'],',.0f') if field else 'Unavailable'
        scope=financial_field_label(key,field) if field else 'No verified directly reported fact for this period'
        definition=scope+(' · '+field.get('concept','') if field else '')
        cards.append('<div><dt>'+label+'</dt><dd>'+escape(amount)+'</dd><small>'+escape(definition)+'</small></div>')
    kind='Directly reported quarter' if p['period_kind']=='quarterly' else 'Reported annual period'
    return (gaps+'<h3>Reported financial summary</h3><p class="company-scope-note">'+escape(kind+' · '+p['period_start']+' → '+p['period_end']+' · '+p['unit'])
            +' · Available verified period. Newer filings and point-in-time coverage require separate evidence.</p><dl class="company-fact-grid">'+''.join(cards)+'</dl>')
