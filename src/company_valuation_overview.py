"""A primary peer-valuation explanation with independent per-metric evidence gates."""
from collections.abc import Mapping
from datetime import date,datetime,timezone
from html import escape
import math
import re
from statistics import median
from urllib.parse import urlsplit

from src.company_research_scope import research_scope
from src.online_company_identity import _mode_reason
from src.quant_interpretation_eligibility import QuantEvidenceAssessment,evaluate_quant_interpretation

METRICS={'pe':'P/E','ps':'P/S','p_fcf':'P/FCF','ev_ebitda':'EV/EBITDA'}
MIN_PEERS=3


def _mapping(value):return value if isinstance(value,Mapping) else {}


def _date(value):
 try:return date.fromisoformat(value) if isinstance(value,str) else None
 except ValueError:return None


def _time(value):
 try:
  dt=datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else None
  return dt.astimezone(timezone.utc) if dt is not None and dt.utcoffset() is not None else None
 except (ValueError,OverflowError):return None


def _url(value):
 if not isinstance(value,str) or not 1<=len(value)<=2048:return False
 try:
  u=urlsplit(value);return u.scheme=='https' and bool(u.hostname) and u.username is None and u.password is None
 except ValueError:return False


def _symbol(value):return isinstance(value,str) and re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',value) is not None


def _observation_valid(row,metric,as_of):
 if not isinstance(row,Mapping):return False
 value=row.get('multiple');cik=row.get('sec_cik')
 if (not _symbol(row.get('ticker')) or not isinstance(cik,str) or not re.fullmatch(r'\d{10}',cik) or int(cik)==0
     or row.get('metric')!=metric or type(value) not in {int,float} or not 0<value<=1e6 or not math.isfinite(value)
     or row.get('identity_verified') is not True or row.get('rights_permitted') is not True or not _url(row.get('source_ref'))
     or row.get('basis') not in ('annual','TTM') or not isinstance(row.get('currency'),str) or not re.fullmatch(r'[A-Z]{3}',row['currency'])
     or not isinstance(row.get('denominator_definition'),str) or not 1<=len(row['denominator_definition'].strip())<=240):return False
 start,end,price,published=(_date(row.get(k))for k in ('period_start','period_end','price_date','published_at'));observed=_time(row.get('observed_at'))
 return bool(start and end and price and published and observed and 300<=(end-start).days<=430
  and end<=published<=price<=observed.date()<=as_of and 0<=(as_of-price).days<=7
  and (price-end).days<=(550 if row['basis']=='annual' else 180))


def _empty_metric(reason):
 return dict(status='withheld',subject_multiple=None,peer_median=None,premium_fraction=None,peer_count=0,peer_tickers=[],excluded=[],reason=reason,source_observations=[])


def _compare(metric,inputs,ticker,as_of,evidence_date):
 result=_empty_metric('Comparable company and peer observations are missing.')
 subject=_mapping(inputs).get('subject');peers=_mapping(inputs).get('peers')
 if (not _observation_valid(subject,metric,as_of) or subject['ticker']!=ticker or subject['price_date']!=evidence_date
     or not isinstance(peers,list) or len(peers)>100):return result
 result['reason']='At least three distinct reviewed and compatible peer companies are needed.'
 signature=tuple(subject[k]for k in ('basis','currency','period_start','period_end','price_date','denominator_definition'))
 accepted=[];seen_ciks=set();seen_symbols=set()
 for row in peers:
  r=_mapping(row);name=r.get('ticker') if _symbol(r.get('ticker')) else 'Unknown peer';reason=None
  if not _observation_valid(r,metric,as_of):reason='Identity, source rights, dates or positive multiple not verified.'
  elif r['sec_cik']==subject['sec_cik'] or r['ticker'].replace('.','-')==ticker.replace('.','-'):reason='The company cannot be its own peer.'
  elif r['sec_cik'] in seen_ciks or r['ticker'].replace('.','-') in seen_symbols:reason='Duplicate company or share class.'
  elif tuple(r[k]for k in ('basis','currency','period_start','period_end','price_date','denominator_definition'))!=signature:reason='Financial definition, period, currency or price date differs.'
  elif (r.get('relationship_reviewed') is not True or not isinstance(r.get('relationship_rationale'),str)
        or not 1<=len(r['relationship_rationale'].strip())<=500 or not _url(r.get('relationship_source_ref'))):reason='Comparable relationship and rationale have not been reviewed.'
  if reason:result['excluded'].append(dict(ticker=name,reason=reason));continue
  accepted.append(r);seen_ciks.add(r['sec_cik']);seen_symbols.add(r['ticker'].replace('.','-'))
 result.update(peer_count=len(accepted),peer_tickers=sorted(r['ticker']for r in accepted),
  price_date=subject['price_date'],basis=subject['basis'],currency=subject['currency'],period_start=subject['period_start'],period_end=subject['period_end'],
  denominator_definition=subject['denominator_definition'],source_observations=[dict(subject),*(dict(r)for r in accepted)])
 if len(accepted)<MIN_PEERS:return result
 peer_median=float(median(r['multiple']for r in accepted));premium=subject['multiple']/peer_median-1
 if not math.isfinite(premium) or abs(premium)>1e6:
  result['reason']='The relative multiple is outside the supported numeric range.';return result
 result.update(status='supported',subject_multiple=subject['multiple'],peer_median=peer_median,premium_fraction=premium,
  reason='Descriptive comparison of the compatible reported multiples; no overall valuation verdict.',
  price_date=subject['price_date'],basis=subject['basis'],currency=subject['currency'],period_start=subject['period_start'],period_end=subject['period_end'],
  denominator_definition=subject['denominator_definition'],source_observations=[dict(subject),*(dict(r)for r in accepted)])
 return result


def _quant_current(report,ticker,as_of):
 entry=_mapping(_mapping(report.get('quant_interpretation')).get('valuation'))
 if entry.get('family')!='valuation' or entry.get('scope')!=ticker+':valuation_snapshot' or entry.get('interpretation_state')!='current_context_eligible':return False
 try:
  assessment=QuantEvidenceAssessment(**{k:entry.get(k)for k in ('family','scope','calculation_state','observation_state','observation_through_date','provenance_state','rights_state','field_scope_state')},evidence_notes=())
  decision=evaluate_quant_interpretation(assessment);through=_date(assessment.observation_through_date)
  return decision.interpretation_state=='current_context_eligible' and through is not None and 0<=(as_of-through).days<=7
 except (ValueError,TypeError):return False


def build_valuation_overview(ticker,report_payload=None,*,as_of_date=None,research_context=None):
 as_of=as_of_date if type(as_of_date) is date else date.today()
 result=dict(ticker=ticker,status='withheld',reason='Current comparable valuation evidence has not been established.',
  metrics={k:_empty_metric('Source-bound company and peer inputs are needed.')for k in METRICS},as_of_date=as_of.isoformat())
 if _mode_reason('research') or not _symbol(ticker):return result
 path=research_scope(research_context,ticker)['path']
 report=_mapping(report_payload);ready={**_mapping(report.get('readiness')),**_mapping(report.get('valuation_readiness'))}
 asset=report.get('asset_type',ready.get('asset_type'))
 if path in {'investment_company','security_wrapper','blank_check'} or asset in ('etf','fund','index_proxy'):
  result.update(status='separate_research_path',reason='This instrument needs its own research path before ordinary operating-company peer valuation.');return result
 if report.get('ticker')!=ticker or ready.get('peer_ready') is not True or not _quant_current(report,ticker,as_of):return result
 inputs=_mapping(_mapping(_mapping(report.get('valuation_snapshot')).get('relative_valuation')).get('comparison_inputs'))
 for metric in METRICS:
  if path=='bank' and metric!='pe':
   result['metrics'][metric]=_empty_metric('A bank-specific valuation definition and capital context are needed.');continue
  result['metrics'][metric]=_compare(metric,inputs.get(metric),ticker,as_of,_mapping(_mapping(report.get('quant_interpretation')).get('valuation')).get('observation_through_date'))
 if any(r['status']=='supported'for r in result['metrics'].values()):result.update(status='supported',reason='Compare each metric separately; a higher multiple is not proof of overvaluation.')
 return result


STYLE='''<style>.company-valuation{margin:16px 0;padding:20px;background:#fff;border:1px solid #d9e0dc;border-radius:12px;min-width:0;box-sizing:border-box;overflow-wrap:anywhere}.company-valuation h2{font-size:1.25rem;margin:0 0 .5rem}.company-valuation h3{font-size:1.1rem;line-height:1.35;margin:.65rem 0}.company-valuation p{margin:.5rem 0}.valuation-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr));gap:10px;margin:14px 0}.valuation-grid div{background:#f4f7f5;border:1px solid #dfe6e1;border-radius:8px;padding:12px;min-width:0}.valuation-grid dt{font-size:.85rem;color:#44584e}.valuation-grid dd{margin:.4rem 0 0;font-size:1.15rem;font-weight:700}.company-valuation details{padding:9px 0;border-top:1px solid #e4e9e5}.company-valuation summary{font-weight:650;cursor:pointer}.company-valuation li{margin:.4rem 0}.company-valuation ul{padding-left:20px}.valuation-kicker{font-size:.8rem;font-weight:650;color:#52675c}.company-valuation table{width:100%;table-layout:fixed;border-collapse:collapse}.company-valuation th,.company-valuation td{text-align:left;padding:8px 4px;overflow-wrap:anywhere;border-bottom:1px solid #e4e9e5}</style>'''


def valuation_overview_html(view):
 v=_mapping(view);ticker=str(v.get('ticker')or'Selected company');metrics=_mapping(v.get('metrics'))
 supported=[(k,_mapping(metrics.get(k)))for k in METRICS if _mapping(metrics.get(k)).get('status')=='supported']
 headline='No supported peer comparison yet';values=['Needs dated inputs','Needs comparable peers','Not established','0 verified'];label='P/E'
 if not supported:
  for key in METRICS:
   m=_mapping(metrics.get(key))
   if m.get('peer_count',0)>0:label=METRICS[key];values[3]=str(m['peer_count'])+' verified';break
 if supported:
  key,m=supported[0];label=METRICS[key];p=m['premium_fraction'];direction='above'if p>0 else 'below'if p<0 else 'at'
  headline=f'{abs(p):.0%} {direction} the peer median on {label}' if p else f'At the peer median on {label}'
  values=[f"{m['subject_multiple']:.1f}×",f"{m['peer_median']:.1f}×",f'{p:+.1%}',str(m['peer_count'])]
 if v.get('status')=='separate_research_path':headline='Use the instrument-specific research path first'
 cards=''.join('<div><dt>'+escape(title)+'</dt><dd>'+escape(value)+'</dd></div>'for title,value in zip((ticker+' · '+label,'Peer median','Premium / discount','Comparable peers'),values))
 rows=''.join('<tr><th scope="row">'+name+' · '+str(_mapping(metrics.get(k)).get('peer_count',0))+' comparable peers</th><td>'+escape(str(_mapping(metrics.get(k)).get('reason')or'Data needed'))+'</td></tr>'for k,name in METRICS.items())
 sources=''
 for key in METRICS:
  m=_mapping(metrics.get(key))
  if not m.get('source_observations') and not m.get('excluded'):continue
  sources+='<h4>'+METRICS[key]+'</h4><p>'+escape(m['basis']+' · '+m['period_start']+' to '+m['period_end']+' · '+m['currency']+' · price date '+m['price_date'])+'</p><p>Definition: '+escape(m['denominator_definition'])+'</p><ul>'
  for row in m['source_observations']:
   sources+='<li>'+escape(row['ticker'])+' · observed '+escape(row['observed_at'])+' · published '+escape(row['published_at'])+' · <a href="'+escape(row['source_ref'],quote=True)+'" target="_blank" rel="noopener noreferrer">Source</a>'
   if row['ticker']!=ticker:sources+=' · '+escape(row['relationship_rationale'])+' · <a href="'+escape(row['relationship_source_ref'],quote=True)+'" target="_blank" rel="noopener noreferrer">Peer rationale</a>'
   sources+='</li>'
  sources+='</ul>'
  if m['excluded']:sources+='<p>Excluded observations:</p><ul>'+''.join('<li>'+escape(r['ticker']+': '+r['reason'])+'</li>'for r in m['excluded'])+'</ul>'
 evidence=sources or '<p>A dated price, compatible financial definition and period, permitted source fields, and at least three reviewed peers are needed. A shared industry code alone does not establish comparable peers.</p>'
 evidence+='<p>Declared recency guards: prices within seven calendar days; annual periods within 550 days of the price date, or 180 days for TTM. This does not prove that a later filing is absent.</p>'
 return (STYLE+'<section class="company-valuation" aria-label="Valuation and peers"><p class="valuation-kicker">COMPANY VALUATION</p><h2>Valuation and peers</h2><h3>'+escape(headline)+'</h3><p>'+escape(str(v.get('reason')or''))+'</p><dl class="valuation-grid">'+cards+'</dl>'
  '<p>A premium is a higher reported multiple, not proof of overvaluation. Compare business mix, growth, profitability, capital needs and risk before interpreting the difference.</p>'
  '<details><summary>Other valuation measures and gaps</summary><table><thead><tr><th>Measure</th><th>What can be established</th></tr></thead><tbody>'+rows+'</tbody></table></details>'
  '<details><summary>Source dates and comparability</summary>'+evidence+'</details>'
  '<details class="valuation-example"><summary>Illustrative example · synthetic companies only</summary><p><strong>ExampleCo: 30× P/E. Three example peers: 20×, 25×, 40×.</strong> Their median is 25×. The calculation is 30 ÷ 25 − 1 = +20% premium.</p><p>This explains the calculation only. It is not data for '+escape(ticker)+' and cannot change its research status.</p></details></section>')
