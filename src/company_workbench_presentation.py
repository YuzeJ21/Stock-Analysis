"""Composed, read-only company views over the existing validated observations."""
from collections.abc import Mapping
from html import escape
from math import isfinite

from src.company_answer_summary import company_answers_html
from src.company_sec_online_preview import _iso_date
from src.company_workbench_sections import workbench_projection
from src.online_company_identity import _mode_reason
from src.online_history_contract import validated_annual_history
from src.online_peer_valuation_ui import _link
from src.online_research_expansion_view import financial_field_label
from src.sec_foreign_financials import validated_foreign_financials
from src.sec_quarterly_history import validated_quarterly_history


METRICS = {'revenue':'Revenue', 'operating_income':'Operating income',
           'cash_from_operations':'Operating cash flow', 'capital_expenditures':'Capital spending'}

WORKBENCH_STYLE = '''<style>
.stApp:has(.st-key-company-workbench-layout){background:#f4f7f3!important;color:#152b24!important}
.stApp:has(.st-key-company-workbench-layout) [data-testid="stMainBlockContainer"]{max-width:84rem!important;padding:0 2rem 3rem!important}
.stApp:has(.st-key-company-workbench-layout) .research-workflow-navigation{background:#f4f7f3!important;margin-bottom:1.8rem!important}
.st-key-company-workbench-layout{min-width:0}
.st-key-company-workbench-layout p,.st-key-company-workbench-layout label{color:#496056}
.st-key-company-workbench-layout [data-testid="stCaptionContainer"]{opacity:1!important}
.st-key-company-workbench-layout h1,.st-key-company-workbench-layout h2,.st-key-company-workbench-layout h3{color:#152b24!important;letter-spacing:-.035em!important}
.st-key-company-workbench-layout [data-testid="stVerticalBlock"]{gap:.85rem}
.st-key-company-workbench-layout .company-integrated-header{padding:0!important}
.st-key-company-workbench-layout .company-integrated-header h1{font-size:clamp(2rem,3.4vw,3rem)!important;line-height:1.12!important;margin:0 0 .45rem!important}
.company-workspace-kicker{font-size:.74rem!important;letter-spacing:.11em!important;text-transform:uppercase;font-weight:750!important;color:#144c3d!important;margin:0 0 .8rem!important}
.company-workspace-intro{color:#496056;font-size:.95rem;margin:.25rem 0 .7rem}
.st-key-company-workbench-layout .company-coverage-details{font-size:.75rem!important}
.st-key-company-workbench-layout .company-coverage-details summary{min-height:2.75rem;align-content:center}
.st-key-company-workbench-rail{padding-top:.3rem}
.st-key-company-workbench-rail .company-rail-title{font-size:.74rem;letter-spacing:.1em;font-weight:750;color:#144c3d;text-transform:uppercase;margin:0 0 .5rem}
.st-key-company-section-navigation [role="radiogroup"]{display:flex!important;flex-direction:column!important;gap:.3rem!important}
.st-key-company-section-navigation [data-testid="stWidgetLabel"]{display:none!important}
.st-key-company-section-navigation label div:has(+ [data-testid="stMarkdownContainer"]){display:none!important}
.st-key-company-section-navigation label{display:flex!important;align-items:center!important;min-height:48px!important;padding:.6rem .7rem!important;border:1px solid transparent!important;border-radius:.6rem!important;background:transparent!important;width:100%!important}
.st-key-company-section-navigation label p{color:#18372b!important;font-size:.9rem!important;font-weight:650!important;line-height:1.3!important}
.st-key-company-section-navigation label:has(input:checked){background:#e8f3ed!important;border-color:#bbd6c7!important}
.st-key-company-section-navigation label>div:first-child{display:none!important}
.st-key-company-section-navigation label:focus-within{outline:3px solid #196853!important;outline-offset:2px}
.st-key-company-workbench-rail .st-key-company-update-actions{border-top:1px solid #d3e0d7;padding-top:1rem;margin-top:1rem}
.st-key-company-update-actions{gap:.45rem!important;flex-wrap:wrap!important}
.st-key-company-update-actions button{min-height:44px!important;padding:.45rem .6rem!important;border-radius:.5rem!important;box-shadow:none!important}
.st-key-company-update-actions button p{font-size:.78rem!important;line-height:1.3!important;color:#144c3d!important}
.st-key-company-workbench-layout .company-answer-summary{grid-template-columns:repeat(3,minmax(0,1fr)) minmax(0,1.4fr)!important;gap:.65rem;margin:.65rem 0 1.25rem!important}
.st-key-company-workbench-layout .company-answer-summary .company-answer{display:block!important;padding:1rem!important;border:1px solid #d3e0d7!important;border-radius:.65rem!important;background:#fff!important;box-shadow:none!important}
.st-key-company-workbench-layout .company-answer-summary .company-answer[data-company-answer="valuation"]{background:#e8f3ed!important;border-color:#bbd6c7!important}
.st-key-company-workbench-layout .company-answer-value{font-size:clamp(1.1rem,1.7vw,1.6rem)!important;letter-spacing:-.035em!important;line-height:1.22!important;color:#152b24!important;margin:.55rem 0!important}
.st-key-company-workbench-layout .company-answer-context{font-size:.8rem!important;line-height:1.45!important}
.st-key-company-workbench-layout .company-answer-summary summary{font-weight:650;min-height:44px}
.company-analysis-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.05fr);gap:.9rem;margin:.6rem 0 1rem}
.company-analysis-surface{min-width:0;padding:1.2rem;background:#fff;border:1px solid #d3e0d7;border-radius:.75rem;overflow-wrap:anywhere}
.company-analysis-surface h2{font-size:1.22rem!important;margin:0 0 .5rem!important;padding:0!important}
.company-analysis-surface p,.company-analysis-surface figcaption{font-size:.8rem;color:#496056;margin:.4rem 0}
.company-analysis-surface figure{margin:1rem 0 0}
.company-analysis-surface svg{display:block;width:100%;height:auto;max-height:275px}
.company-analysis-surface svg text{font:11px system-ui,sans-serif;fill:#496056}
.company-analysis-surface svg .company-bar-value{font-weight:750;fill:#152b24}
.company-table-scroll{max-width:100%;overflow-x:auto;overscroll-behavior-x:contain}
.company-analysis-surface table{width:100%;border-collapse:collapse;font-size:.76rem!important;margin:.6rem 0}
.company-analysis-surface caption{text-align:left;color:#496056;font-size:.74rem;padding-bottom:.5rem}
.company-analysis-surface td,.company-analysis-surface th{padding:.65rem .35rem!important;border-bottom:1px solid #d3e0d7!important;text-align:right!important;background:transparent!important}
.company-analysis-surface td{white-space:nowrap}
.company-analysis-surface tr>:first-child{text-align:left!important}
.company-analysis-surface th{font-size:.7rem!important;color:#496056;font-weight:700}
.company-analysis-surface details{font-size:.8rem;margin-top:.6rem}
.company-analysis-surface summary{min-height:44px;align-content:center;cursor:pointer;color:#144c3d;font-weight:650}
.company-analysis-surface a{color:#144c3d;text-decoration:underline}
.company-analysis-surface summary:focus-visible,.company-analysis-surface a:focus-visible{outline:3px solid #196853;outline-offset:2px}
.company-analysis-gap{padding:1.2rem;border:1px solid #d3e0d7;border-radius:.75rem;background:#fff;color:#496056}
.st-key-company-workbench-layout [data-testid="stExpander"]{border:1px solid #d3e0d7!important;border-radius:.6rem!important;background:#fff!important;box-shadow:none!important}
.st-key-company-workbench-layout .company-observation-context{border-bottom:1px solid #d3e0d7;padding-bottom:.65rem}
@media(min-width:768px){.st-key-company-workbench-rail{position:sticky;top:5.5rem}.st-key-company-workbench-layout>[data-testid="stHorizontalBlock"]{gap:2rem!important}}
@media(max-width:900px){.company-analysis-grid{grid-template-columns:minmax(0,1fr)}.st-key-company-workbench-layout .company-answer-summary{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
@media(max-width:767px){
 .stApp:has(.st-key-company-workbench-layout) [data-testid="stMainBlockContainer"]{padding:0 1rem 2rem!important}
 .stApp:has(.st-key-company-workbench-layout) .research-workflow-navigation{margin-bottom:.8rem!important}
 .st-key-company-workbench-layout>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]{flex-direction:column!important}
 .st-key-company-workbench-layout>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{width:100%!important;flex:1 1 auto!important;min-width:0!important}
 .st-key-company-workbench-layout [data-testid="stHorizontalBlock"]{row-gap:.75rem!important}
 .st-key-company-section-navigation{width:100%;max-width:100%;min-width:0;overflow:clip;padding:3px;box-sizing:border-box}
 .st-key-company-section-navigation [data-testid="stRadio"]{width:100%;max-width:100%;min-width:0}
 .st-key-company-section-navigation [role="radiogroup"]{flex-direction:row!important;flex-wrap:nowrap!important;gap:.3rem!important;overflow-x:auto!important;width:100%;max-width:100%;min-width:0;padding:3px;box-sizing:border-box}
 .st-key-company-section-navigation label{width:auto!important;flex:0 0 auto!important;min-height:44px!important;padding:.5rem .65rem!important}
 .st-key-company-section-navigation label p{font-size:.78rem!important}
 .st-key-company-workbench-rail .company-rail-title{display:none!important}
 .st-key-company-workbench-rail .st-key-company-update-actions{margin-top:0;padding-top:.6rem}
 .st-key-company-workbench-layout .company-answer-summary .company-answer{padding:.8rem!important}
 .st-key-company-workbench-layout .company-answer-summary .company-answer details{display:block!important}
 .st-key-company-workbench-layout .company-integrated-header h1{font-size:2rem!important}
 .company-analysis-surface{padding:1rem}.company-workspace-kicker{margin-bottom:.4rem!important}
}
@media(max-width:320px){.st-key-company-workbench-layout .company-answer-summary{grid-template-columns:minmax(0,1fr)!important}}
.company-answer-gaps{grid-column:1/-1;display:flex;flex-wrap:wrap;align-items:baseline;gap:.15rem .6rem;background:#fff8ea;color:#593c17;border:1px solid #e8d2ad;border-radius:.55rem;padding:.55rem .75rem;font-size:.8rem;line-height:1.45;overflow-wrap:anywhere}
@media(max-width:767px){
 .st-key-company-workbench-layout .company-answer-summary .company-answer[data-company-answer="financial"],
 .st-key-company-workbench-layout .company-answer-summary .company-answer[data-company-answer="valuation"]{order:-2}
 .st-key-company-workbench-layout .company-answer-summary .company-answer-gaps{order:-1}
 .st-key-company-workbench-layout .company-answer-summary .company-answer-value{font-size:1.05rem!important;margin:.35rem 0!important}
}
</style>'''


def _fields(row):
    fields = row.get('fields', {})
    return {field['field']:field for field in fields} if isinstance(fields,list) else fields


def _value(row, key):
    field = _fields(row).get(key) if row['status']=='available' else None
    return field['value'] if field else None


def _millions(value):
    return 'Gap' if value is None else f'{value / 1e6:,.2f}'


def _bars(rows, metric, title):
    values = [_value(row,metric) for row in rows]
    valid = [value for value in values if value is not None]
    if not valid:
        return '<p>No directly reported values for this selection. Missing cash flow is never derived from cumulative values.</p>'
    definitions = {(field.get('taxonomy'),field.get('concept'),field.get('unit'))
                   for row in rows if row['status']=='available' and (field:=_fields(row).get(metric))}
    if len(definitions)>1:
        return '<p>Different reported definitions; trend withheld. Inspect each period in the table and source evidence.</p>'
    low, high = min(0,*valid), max(0,*valid)
    span = high-low or 1
    y = lambda value: 178-(value-low)/span*137
    zero = y(0)
    width = 380/max(1,len(rows))
    drawing = [f'<path d="M10 {zero:.1f} H410" stroke="#bbcdc2"/>']
    for index,(row,value) in enumerate(zip(rows,values)):
        x = 22 + index*width
        label = row['period_end'][2:7]
        if value is None:
            drawing.append(f'<text x="{x+width*.3:.1f}" y="165" text-anchor="middle">Gap</text>')
        else:
            top = min(zero,y(value)); height = max(1,abs(zero-y(value)))
            fill = '#28634f' if index==len(rows)-1 else '#80b29b'
            drawing.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{width*.6:.1f}" height="{height:.1f}" rx="4" fill="{fill}"><title>{escape(row["period_end"])}: {_millions(value)} million</title></rect>')
            chart_value=f'{value/1e6:,.0f}' if abs(value)>=1e8 else _millions(value)
            drawing.append(f'<text class="company-bar-value" x="{x+width*.3:.1f}" y="{max(15,top-7):.1f}" text-anchor="middle">{chart_value}</text>')
        drawing.append(f'<text x="{x+width*.3:.1f}" y="205" text-anchor="middle">{escape(label)}</text>')
    return '<figure><svg viewBox="0 0 430 220" role="img" aria-label="'+escape(title,quote=True)+'"><title>'+escape(title)+'</title>'+''.join(drawing)+'</svg><figcaption>Period ends · latest reported values as observed; gaps remain gaps.</figcaption></figure>'


def financial_workspace_html(ticker, financial, *, period_kind='annual', metric='revenue', limit=6):
    """One chart/table selection; validators retain period, identity and rights gates."""
    if period_kind not in {'annual','quarterly'} or metric not in METRICS:
        raise ValueError('Unsupported financial selection')
    if type(limit) is not int or not 1<=limit<=12:
        raise ValueError('Unsupported financial window')
    if _mode_reason('research'):
        return '<div class="company-analysis-gap">Financial trend needs verification in this workspace. Personal research observations remain unavailable.</div>'
    view = financial if isinstance(financial,Mapping) else {}
    projection = workbench_projection(ticker,view,{})
    history = None
    if view.get('ticker')==ticker and not projection['identity_conflict']:
        history = (validated_annual_history(view) if view.get('status')=='inspection_only' else None) if period_kind=='annual' else validated_quarterly_history(view)
        annual_archive = projection.get('annual_archive')
        foreign = validated_foreign_financials(view) if annual_archive else None
        if period_kind == 'annual' and annual_archive:
            from src.sec_native_annual_history import native_archive_annual_rows
            history = dict(unit=annual_archive['unit'],
                           periods=native_archive_annual_rows(foreign, annual_archive),
                           source_url=annual_archive['source_url'], observed_at=annual_archive['observed_at'],
                           source_label='Exact SEC annual filing')
        elif period_kind=='quarterly':
            from src.sec_online_quarter_evidence import validated_archive_quarter
            from src.sec_online_quarter_view import merge_archive_quarter
            archive=validated_archive_quarter(view)
            if foreign and foreign['unit'] != 'USD' and foreign['quarterly']:
                history = dict(foreign, periods=foreign['quarterly'])
            elif archive:
                history=dict(history or {},unit=archive['unit'],
                             periods=merge_archive_quarter(history['periods'] if history else [],archive),
                             source_url=archive['source_url'],observed_at=archive['observed_at'],source_label='Exact SEC filing · separate archive scope')
    if not history:
        return '<div class="company-analysis-gap">Financial trend needs verification. Refresh the source or inspect Data Sources for the specific gap.</div>'
    rows = history['periods'][-limit:]
    kind = 'Annual' if period_kind=='annual' else 'Quarterly'
    # Preserve industry revenue and continuing-operations cash definitions in the display label.
    metric_field = next((_fields(row).get(metric) for row in reversed(rows) if _fields(row).get(metric)),None)
    definition = financial_field_label(metric,metric_field)
    label = 'Net revenue' if metric=='revenue' and metric_field and metric_field.get('concept')=='RevenuesNetOfInterestExpense' else METRICS[metric]
    title = kind+' '+label.lower()+' trend'
    unit = history['unit']+' millions'
    columns = ['revenue','operating_income',metric if metric in {'cash_from_operations','capital_expenditures'} else 'cash_from_operations']
    concepts={key:{_fields(row)[key].get('concept') for row in rows if row['status']=='available' and key in _fields(row)} for key in columns}
    continuing='NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'
    def heading(key):
        if key=='revenue' and concepts[key]=={'RevenuesNetOfInterestExpense'}:
            return 'Net revenue'
        if key=='cash_from_operations' and continuing in concepts[key]:
            return 'Operating cash flow · '+('continuing operations' if len(concepts[key])==1 else 'basis varies')
        return METRICS[key]
    headings = ''.join('<th scope="col">'+escape(heading(key))+'</th>' for key in columns)
    def cell(row,key):
        value=_value(row,key)
        scope=''
        if value is not None and key=='cash_from_operations' and len(concepts[key])>1:
            scope='<br><small>'+('Continuing operations' if _fields(row)[key]['concept']==continuing else 'Total operations')+'</small>'
        return '<td>'+_millions(value)+scope+'</td>'
    body = ''.join('<tr><th scope="row">'+escape(row['period_end'])+'</th>'+''.join(cell(row,key) for key in columns)+'</tr>' for row in reversed(rows))
    receipts = []
    cumulative = []
    for row in reversed(rows):
        reason = ' · Gap: '+str(row.get('reason','')).replace('_',' ') if row['status']!='available' else ''
        receipts.append('<li>'+escape(str(row.get('period_start') or 'Unresolved start')+' → '+row['period_end']+' · '+str(row.get('form') or '')+' · Filed '+str(row.get('filed') or 'Unavailable')+' · '+str(row.get('accession') or 'Unavailable')+reason)+'</li>')
        for key,field in _fields(row).items():
            receipts.append('<li>'+escape(financial_field_label(key,field)+' · '+field.get('concept','')+' · '+str(field.get('unit',history['unit'])))+'</li>')
        source_field=next(iter(_fields(row).values()),{})
        if source_field.get('source_ref'):
            receipts.append('<li>'+_link(source_field['source_ref'],'This period’s source')+'</li>')
        for key,reason in row.get('withheld_fields',{}).items():
            receipts.append('<li>'+escape(row['period_end']+' · '+METRICS.get(key,key)+' gap: '+reason.replace('_',' '))+'</li>')
        if row.get('cumulative_fields'):
            anchor=row['cumulative_anchor']
            cumulative.append('<li>'+escape(anchor['period_start']+' → '+row['period_end'])+' · '+escape(history['unit'])+' millions · '+escape('; '.join(financial_field_label(key,field)+' '+_millions(field['value']) for key,field in row['cumulative_fields'].items()))+'</li>')
        if row.get('revision_gaps'):
            receipts.append('<li>'+escape(row['period_end']+' · Revision context holds: '+', '.join(row['revision_gaps']))+'</li>')
    gaps = ''.join('<p>Newer '+escape(row['kind'])+' period '+escape(row['period_end'])+' needs verification. Earlier values retain their own dates.</p>' for row in projection['withheld_periods'])
    return ('<div class="company-analysis-grid">'
        '<section class="company-analysis-surface" aria-label="'+escape(title,quote=True)+'"><h2>'+escape(kind+' '+label.lower())+'</h2><p>'+escape(unit)+' · directly reported periods</p>'
        +_bars(rows,metric,title)+gaps+'</section>'
        '<section class="company-analysis-surface" aria-label="Reported '+period_kind+' financials"><h2>Reported financials</h2>'
        '<div class="company-table-scroll" tabindex="0" role="region" aria-label="Financial table"><table><caption>'+escape(unit)+' · period ends</caption><thead><tr><th scope="col">Period</th>'+headings+'</tr></thead><tbody>'+body+'</tbody></table></div>'
        '<details><summary>Period evidence and gaps</summary><p>'+escape(definition)+'. '+_link(history['source_url'],history.get('source_label','SEC Companyfacts'))+' · Observed '+escape(history['observed_at'])+'. Latest reported observations, including revisions; not point-in-time history. Each period retains its own source; raw redistribution held.</p><ul>'+''.join(receipts)+'</ul></details>'
        +('<details><summary>Cumulative cash flow · not single-quarter</summary><ul>'+''.join(cumulative)+'</ul></details>' if cumulative else '')+'</section></div>')


def _overview_gaps(financial, projection, research_context):
    gaps = [financial['gap']] if financial.get('gap') else []
    if not gaps:
        gaps.extend(financial.get('native_comparison_gaps') or ())
    if (projection or {}).get('native_ytd_missing'):
        gaps.append('Year-to-date evidence needs verification')
    if (projection or {}).get('bank_annual'):
        gaps.extend(('Quarterly and year-to-date results need verification', 'Traded ADS earnings need verification'))
    withheld = (projection or {}).get('withheld_fields') or {}
    for field, label in METRICS.items():
        if field in withheld:
            gaps.append(f'{label} needs verification')
    current = (research_context or {}).get('filing_coverage', {}).get('current', {})
    for kind, label in (('annual', 'Annual filing evidence'), ('quarterly', 'Direct-quarter evidence')):
        state = current.get(kind, {})
        if (state.get('status') not in {'withheld', 'facts_pending', 'amendment_unresolved'}
                or state.get('reason') == 'ibn_6k_reporting_basis_unqualified'):
            continue
        reason = {
            'supported_filing_form_unavailable': 'no supported filing form',
            'filing_document_metadata_unavailable': 'filing document unavailable',
            'new_filing_structured_facts_pending': 'structured facts pending',
            'amended_filing_structured_facts_unresolved': 'amendment unresolved',
            'ambiguous_filing_version': 'filing version unresolved',
        }.get(state.get('reason'))
        gaps.append(f'{label} needs verification' + (f' ({reason})' if reason else ''))
    return gaps


def workbench_metrics_html(ticker, answers, peer_view, *, projection=None, research_context=None):
    """Retain existing answer evidence; EPS is separately qualified, never inferred."""
    view = peer_view if isinstance(peer_view,Mapping) else {}
    subject = view.get('subject') if view.get('ticker')==ticker and not _mode_reason('research') else None
    eps = dict(key='eps',title='Annual diluted EPS',value='Needs verification',
               context='Open Valuation & Peers to check annual earnings.',
               evidence=('Annual earnings retain their own filing, security and currency checks. No EPS is inferred from revenue.',),links=())
    if (isinstance(subject,Mapping) and subject.get('ticker')==ticker
        and subject.get('unit')=='USD/shares' and subject.get('concept')=='EarningsPerShareDiluted'
        and type(subject.get('eps')) in (int,float) and isfinite(subject['eps'])
        and _iso_date(subject.get('period_start')) and _iso_date(subject.get('period_end'))
        and subject.get('filing_ref') and subject.get('source_ref')):
        eps.update(value=f"USD {subject['eps']:,.2f}",context='Year ended '+subject['period_end']+' · reported',
            evidence=(subject['period_start']+' → '+subject['period_end']+' · USD/shares',
                      'Reported annual diluted EPS. This is separate from the latest quarter shown alongside.',),
            links=(('SEC annual filing',subject['filing_ref']),('SEC EPS fact',subject['source_ref'])))
    by_key={answer['key']:dict(answer) for answer in answers}
    financial = by_key['financial']
    financial['title'] = 'What changed'
    if financial.get('headline'):
        financial['value'] = financial['headline']
    if financial.get('headline_context'):
        financial['context'] = financial['headline_context']
    valuation=by_key['valuation']
    if valuation['value'].startswith('Annual P/E '):
        valuation.update(title='Annual P/E vs peers',value=valuation['value'].removeprefix('Annual P/E ').replace('industry references','references'))
    return company_answers_html((financial, valuation, by_key['price'], eps),
                                gaps=_overview_gaps(financial, projection, research_context))
