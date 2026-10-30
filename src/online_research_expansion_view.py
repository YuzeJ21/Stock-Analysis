"""Compact, source-labelled quarterly, identity and coverage views."""

from html import escape
from collections.abc import Mapping

from src.online_company_identity import validated_price_filing_association
from src.online_research_coverage import METRICS, validated_coverage_summary
from src.online_research_history_view import STYLE, _amount, _line
from src.sec_quarterly_history import FIELDS, validated_quarterly_history
from src.company_sec_online_preview import _iso_date

_STYLE=STYLE+'<style>.online-quarterly,.online-identity,.online-coverage{margin:16px 0;padding:16px;border:1px solid #d9e0dc;border-radius:8px;min-width:0;overflow-wrap:anywhere;box-sizing:border-box}.online-quarterly article,.online-coverage article{padding:12px;border:1px solid #d9e0dc;border-radius:8px;background:white;min-width:0;box-sizing:border-box}.online-quarter-grid,.online-coverage-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,20rem),1fr));gap:12px}.online-quarterly dl div{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px}.online-quarterly dd{margin:0;font-weight:650}.cumulative-flow{border-top:1px dashed #b9c7c0;margin-top:12px;padding-top:8px}.online-quarterly small,.online-identity small,.online-coverage small{color:#52615c}</style>'
_LABELS={'revenue':'Revenue','operating_income':'Operating income','cash_from_operations':'Operating cash flow','capital_expenditures':'Capital spending'}


def _reason(value):
    return escape(value.replace('_',' ')) if isinstance(value,str) else 'Evidence validation required'


def _label(name,field):
    if name=='revenue' and field:
        return {'RevenueFromContractWithCustomerExcludingAssessedTax':'Revenue · customer contracts, excluding assessed tax',
                'SalesRevenueNet':'Revenue · net sales','SalesRevenueGoodsNet':'Revenue · goods sales'}.get(field.get('concept'),'Revenue')
    return _LABELS[name]+(' · continuing operations' if field and field.get('concept')=='NetCashProvidedByUsedInOperatingActivitiesContinuingOperations' else '')


def _receipts(refs):
    return '<ul>'+''.join(f'<li><a href="{escape(r["source_url"],quote=True)}" target="_blank" rel="noopener noreferrer">Source</a> · observed {escape(r["observed_at"])} · SHA-256 {escape(r["payload_sha256"])}</li>' for r in refs)+'</ul>'


def _revision_gaps(row):
    gaps=row.get('revision_gaps',{})
    if not gaps: return ''
    items=''.join('<li>'+escape(name.replace('_',' '))+' · competing publication '+escape(gap.get('filed') or 'date unresolved')+' · '+_reason(gap['reason'])+'</li>' for name,gap in gaps.items())
    return '<details><summary>Revision context holds</summary><ul>'+items+'</ul></details>'


def quarterly_history_html(view):
    if 'quarterly_history' not in view: return ''
    h=validated_quarterly_history(view)
    annual_gap=''
    markers=view.get('reported_period_anchors',{})
    annual=markers.get('annual') if isinstance(markers,Mapping) else None
    if isinstance(annual,Mapping) and _iso_date(annual.get('period_end')) and _iso_date(view.get('period_end')) and view['period_end']<annual['period_end']:
        annual_gap='<p><strong>Annual coverage gap:</strong> the supported annual concept ends '+escape(view['period_end'])+'; the source contains a later annual reporting period '+escape(annual['period_end'])+'. Older values do not establish latest-period coverage.</p>'
    if h is None:
        raw=view.get('quarterly_history',{})
        reason=raw.get('reason') if isinstance(raw,Mapping) else None
        return _STYLE+'<section class="online-quarterly" aria-label="Reported quarterly financials"><h3>Reported quarterly financials</h3>'+annual_gap+'<p>Quarterly evidence withheld · '+_reason(reason)+'. No missing quarter is inferred.</p></section>'
    points=[]; previous=None; cards=[]
    for row in h['periods']:
        if previous and (row['status']!='available' or previous['status']!='available' or row['period_start']!=_day_after(previous['period_end'])):
            points.append((row['period_end'],None))
        revenue=row['fields'].get('revenue')
        points.append((row['period_end'],revenue['value'] if revenue else None)); previous=row
    for row in reversed(h['periods']):
        if row['status']!='available':
            cards.append('<article><h4>Quarter ended '+escape(row['period_end'])+'</h4><p>Withheld · '+_reason(row['reason'])+'</p>'+_revision_gaps(row)+'</article>'); continue
        values=''.join('<div><dt>'+_label(name,row['fields'].get(name))+'</dt><dd>'+(_amount(row['fields'][name]['value']) if name in row['fields'] else 'Withheld')+'</dd></div>' for name in FIELDS)
        missing='; '.join(_LABELS[name]+': '+reason.replace('_',' ') for name,reason in row['withheld_fields'].items())
        cumulative=''
        if row['cumulative_fields'] or row.get('cumulative_withheld_fields') and row.get('cumulative_anchor'):
            anchor=row['cumulative_anchor']
            amounts=''.join('<div><dt>'+_label(name,field)+'</dt><dd>'+_amount(field['value'])+'</dd></div>' for name,field in row['cumulative_fields'].items())
            cumulative='<div class="cumulative-flow"><strong>Cumulative cash flow · not single-quarter</strong><p>'+escape(anchor['period_start'])+' to '+escape(row['period_end'])+' · USD</p><dl>'+amounts+'</dl></div>'
        cumulative_missing='; '.join('cumulative '+_LABELS[name]+': '+reason.replace('_',' ') for name,reason in row.get('cumulative_withheld_fields',{}).items())
        definitions='; '.join(f'{name}: {f["taxonomy"]}:{f["concept"]}' for name,f in row['fields'].items())
        definitions+='; '+'; '.join(f'cumulative {name}: {f["taxonomy"]}:{f["concept"]}' for name,f in row['cumulative_fields'].items())
        cards.append('<article><h4>Quarter ended '+escape(row['period_end'])+'</h4><small>'+escape(row['period_start'])+' to '+escape(row['period_end'])+' · USD</small><dl>'+values+'</dl>'+cumulative
            +'<details><summary>Quarter evidence and gaps</summary><p>Filed '+escape(row['filed'])+' · '+escape(row['form'])+' · accession '+escape(row['accession'])+'</p><p>'+escape(definitions)+'</p><p>'+escape(missing)+'</p><p>'+escape(cumulative_missing)+'</p></details>'+_revision_gaps(row)+'</article>')
    latest='<div class="online-quarter-grid">'+''.join(cards[:4])+'</div>'
    earlier='<details><summary>Earlier reported quarters ('+str(len(cards)-4)+')</summary><div class="online-quarter-grid">'+''.join(cards[4:])+'</div></details>' if len(cards)>4 else ''
    return (_STYLE+'<section class="online-quarterly" aria-label="Reported quarterly financials"><h3>Reported quarterly financials</h3>'
        '<p>Latest reported values as observed, including revisions; not point-in-time history. Only directly reported quarter-length periods are shown. No missing quarter is inferred.</p>'+annual_gap
        +_line(points,'Direct reported quarterly revenue in USD; reporting gaps break the line')+latest+earlier
        +'<p>Reported revenue concept: '+escape(h['taxonomy']+':'+h['concept'])+'. Source: <a href="'+escape(h['source_url'],quote=True)+'" target="_blank" rel="noopener noreferrer">SEC Companyfacts</a> · observed '+escape(h['observed_at'])+' · SHA-256 '+escape(h['payload_sha256'])+'. Direct-field scope inspected; raw redistribution held.</p></section>')


def _day_after(value):
    from datetime import date,timedelta
    return (date.fromisoformat(value)+timedelta(days=1)).isoformat()


def price_filing_association_html(result):
    link=validated_price_filing_association(result)
    if link is None:
        reason=result.get('reason') if isinstance(result,Mapping) else None
        return _STYLE+'<section class="online-identity" aria-label="Price and filing identity"><h3>Price and filing identity</h3><p>Association withheld · '+_reason(reason)+'. Check both SEC financial evidence and prices to inspect the current listing context.</p></section>'
    alias=' Explicit share-class alias: '+escape(link['ticker'])+' → '+escape(link['provider_symbol'])+'.' if link['share_class_alias_applied'] else ''
    return (_STYLE+'<section class="online-identity" aria-label="Price and filing identity"><h3>Listing association matched</h3>'
        '<p>SEC CIK '+escape(link['sec_cik'])+' · ticker '+escape(link['sec_ticker'])+' · '+escape(link['exchange'])+'.'+alias+'</p>'
        '<p>The current SEC ticker/CIK context and the provider symbol/venue agree. An independent vendor issuer identifier is unavailable. This does not verify historical security continuity, issuer domicile, active status or valuation eligibility. Price adjustments and source-use rights retain their separate holds.</p>'
        '<details><summary>Identity source receipts</summary>'+_receipts(link['source_receipts'])+'</details></section>')


def coverage_study_html(result):
    if not isinstance(result,Mapping) or result.get('status')=='not_requested':
        return '<p>Run a bounded online SEC sample to inspect financial field coverage across industries. No source request occurs until you run it.</p>'
    study=validated_coverage_summary(result)
    if study is None: return '<p>Coverage sample unavailable · '+_reason(result.get('reason'))+'.</p>'
    n=study['requested_count']
    industries=''.join('<li>'+escape(group['sic'] or 'Unknown SIC')+' · '+escape(group['description'])+': '+str(group['requested_count'])+' requested; annual revenue '+str(group['counts']['annual_revenue'])+'/'+str(group['requested_count'])+'; quarterly revenue '+str(group['counts']['quarterly_revenue'])+'/'+str(group['requested_count'])+'</li>' for group in study['by_industry'])
    totals=''.join('<li>'+escape(name.replace('_',' '))+': '+str(study['counts'][name])+'/'+str(n)+'</li>' for name in METRICS)
    cards=[]
    for row in study['rows']:
        facts=''.join('<li>'+escape(name.replace('_',' '))+': '+('available' if row['fields'][name] else 'withheld')+'</li>' for name in METRICS)
        older='<p>Supported historical evidence ends: annual '+escape(row.get('annual_available_period') or 'unavailable')+'; quarter '+escape(row.get('quarterly_available_period') or 'unavailable')+'.</p>'
        cards.append('<article><h4>'+escape(row['ticker'])+'</h4><p>SIC '+escape(row['sic'] or 'unavailable')+' · annual '+escape(row['annual_period'] or 'unavailable')+' · quarter '+escape(row['quarterly_period'] or 'unavailable')+'</p><p>Industry: '+_reason(row['industry_reason'])+'; annual: '+_reason(row['annual_reason'])+'; quarterly: '+_reason(row['quarterly_reason'])+'</p>'+older+'<ul>'+facts+'</ul><details><summary>Source receipts</summary>'+_receipts(row['source_receipts'])+'</details></article>')
    return (_STYLE+'<section class="online-coverage" aria-label="Cross-industry coverage"><h3>Cross-industry coverage · online sample</h3>'
        '<p>'+str(n)+' requested · '+str(study['attempted_count'])+' attempted · '+str(study['resolved_issuer_count'])+' resolved issuers · '+str(study['source_failure_count'])+' source failures · '+str(study['unsupported_financial_count'])+' unsupported financial paths · '+str(study['unknown_industry_count'])+' unknown industry.</p>'
        '<p>This is not a market-wide or representative coverage estimate. Every requested ticker stays in the denominator. Counts inspect the latest observed annual or quarterly period; cumulative cash flows are counted separately. Prices are not queried by this study.</p>'
        '<ul>'+industries+'</ul><details><summary>All field counts</summary><ul>'+totals+'</ul></details><details><summary>Company coverage and gaps</summary><div class="online-coverage-grid">'+''.join(cards)+'</div></details>'
        '<p>Source observation span: '+escape(study['observed_from'] or 'unavailable')+' to '+escape(study['observed_to'] or 'unavailable')+'. SEC direct-field scope and personal-only submissions metadata remain separate; raw redistribution is held.</p></section>')
