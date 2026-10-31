"""Read-only source-labelled listing types and independent issuer profiles."""
from collections.abc import Mapping
from html import escape
from src.online_company_identity import _mode_reason
from src.security_classification import fetch_classification,validated_classification,validated_company_context

SESSION_KEY='listing_classification_v1'
LABELS={'etf':'ETF · declared flag','common_shares':'Common / ordinary shares','depositary_receipt':'Depositary receipt','preferred':'Preferred','debt':'Debt / note','unit':'Unit','warrant':'Warrant','right':'Right','unknown':'Unknown'}
STYLE='<style>.security-classification,.security-context{margin:16px 0;padding:16px;border:1px solid #d9e0dc;border-radius:8px;box-sizing:border-box;min-width:0;overflow-wrap:anywhere}.security-type-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr));gap:8px}.security-type-grid div{padding:8px;border:1px solid #d9e0dc;border-radius:6px;min-width:0}.security-classification ul,.security-context ul{padding-left:20px}</style>'

def _refs(refs):return '<ul>'+''.join('<li><a href="'+escape(r['source_url'],quote=True)+'" target="_blank" rel="noopener noreferrer">Official source</a> · observed '+escape(r['observed_at'])+' · SHA-256 '+escape(r['payload_sha256'])+'</li>' for r in refs)+'</ul>'

def get_listing_classification(session_state,*,refresh_requested,user_agent,fetcher=None,observed_at=None):
 if _mode_reason('research'):return dict(status='withheld',reason='personal_inspection_only')
 if refresh_requested:session_state[SESSION_KEY]=fetch_classification(user_agent=user_agent,fetcher=fetcher,observed_at=observed_at)
 cached=session_state.get(SESSION_KEY)
 if cached is None:return dict(status='not_requested')
 return validated_classification(cached) or dict(status='withheld',reason='classification_source_or_schema_unverified')

def classification_html(packet,query=''):
 if _mode_reason('research'):return '<p>Classification inspection is available only in Personal Research.</p>'
 if not isinstance(packet,Mapping) or packet.get('status')=='not_requested':return '<p>Classify the observed official listings online. Source labels and unresolved types remain separate from financial coverage.</p>'
 p=validated_classification(packet)
 if p is None:return '<p>Classification withheld · source or schema unverified.</p>'
 counts=''.join('<div>'+LABELS[k]+'<br><strong>'+str(p['counts'].get(k,0))+'</strong></div>' for k in LABELS)
 matches=[r for r in p['rows'] if not query or query.casefold() in (r['symbol']+' '+(r['description'] or '')).casefold()]
 rows=''.join('<li><strong>'+escape(r['symbol'])+'</strong> · '+LABELS[r['security_type']]+' · '+escape(r['description'] or 'No security description in SEC-only record')+' · '+escape(r['basis'].replace('_',' '))+((' · '+escape(r['reason'].replace('_',' '))) if r['reason'] else '')+'</li>' for r in matches[:50])
 return (STYLE+'<section class="security-classification" aria-label="Security types"><h3>Security types · observed listings</h3><p>'+str(len(p['rows']))+' listing records · observed '+escape(p['inventory']['observed_from'])+'.</p><div class="security-type-grid">'+counts+'</div><p>Types use a declared ETF flag or a directory description rule. Unknown and composite labels remain visible. Legal security type is not independently verified; depositary receipts may carry an underlying common-share directory label. These labels do not establish financial eligibility, issuer domicile, active status or point-in-time membership.</p><details><summary>Matching listing observations ('+str(len(matches))+')</summary><p>Showing '+str(min(50,len(matches)))+' matches; filter by symbol or description for another record.</p><ul>'+rows+'</ul></details><details><summary>Source dates, digests and rights</summary>'+_refs(p['inventory']['source_receipts'])+'<p>Unregistered personal inspection only. This independently dated snapshot does not change the saved coverage denominator or financial counters.</p></details></section>')

def company_security_html(context,ticker):
 if _mode_reason('research'):return '<p>Security context is available only in Personal Research.</p>'
 if not isinstance(context,Mapping) or context.get('status')=='not_requested':return '<p>Check the selected listing description and SEC issuer reporting profile online. No source request occurs until this action.</p>'
 p=validated_company_context(context,ticker)
 if p is None:return '<p>Security context withheld · identity, source or schema unverified.</p>'
 rows=''.join('<li>'+escape(r['symbol'])+' · '+LABELS[r['security_type']]+' · '+escape(r['description'] or 'SEC-only security type unknown')+' · '+escape(r['basis'].replace('_',' '))+'</li>' for r in p['listing_rows']) or '<li>No exact classified listing row; security type remains unknown.</li>'
 profile=p['issuer_profile'];body='<p>Issuer reporting profile withheld.</p>';refs=[];forms=''
 if profile['status']=='inspection_only':
  body='<p>Reporting profile: <strong>'+escape(profile['reporting_profile'].replace('_',' '))+'</strong> · SEC industry '+escape(profile['sic'] or 'unknown')+'.</p>'
  forms='<p>Observed forms: '+escape(', '.join(sorted(profile['form_counts'])))+'.</p>'
  refs=[profile['source_receipt']]
 return (STYLE+'<section class="security-context" aria-label="Listing and issuer type"><h3>Listing and issuer type · '+escape(ticker)+'</h3><p>SEC CIK '+escape(p['sec_cik'])+'</p><ul>'+rows+'</ul>'+body+'<p>Legal security type is not independently verified; a depositary receipt may carry a common-share directory label. Reporting forms and instrument descriptions remain separate. Issuer domicile, active status, operating-company classification, financial eligibility and point-in-time coverage remain unresolved.</p><details><summary>Source dates and rights</summary>'+forms+_refs([*p['classification']['inventory']['source_receipts'],*refs])+'<p>Listing and submissions metadata: unregistered personal inspection only. Financial evidence and saved readiness remain separate.</p></details></section>')
