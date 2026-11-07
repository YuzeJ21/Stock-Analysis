"""Compact sample coverage with explicit actions and source-only session progress."""
from collections.abc import Mapping
from html import escape
import os
from urllib.parse import urlencode

from src.online_peer_coverage import get_peer_coverage,SESSION_KEY,DEFAULT_SAMPLE
from src.online_peer_valuation import _symbol
from src.online_peer_valuation_ui import STYLE,_text,_reason,_link

_INDUSTRIES={'semiconductors':'Semiconductors','software-infrastructure':'Infrastructure software','drug-manufacturers-general':'General drug manufacturers',
 'household-personal-products':'Household and personal products','restaurants':'Restaurants','farm-heavy-construction-machinery':'Farm and heavy construction machinery',
 'utilities-regulated-electric':'Regulated electric utilities','reit-retail':'Retail REITs','telecom-services':'Telecom services','banks-diversified':'Diversified banks',
 'oil-gas-integrated':'Integrated oil and gas','gold':'Gold'}


def _industry(row):
    key=row.get('industry_key')
    return _INDUSTRIES.get(key,row.get('industry_label') or key.replace('-',' ') if isinstance(key,str) else 'Industry unverified')


def _fraction(number,total):return str(number)+' / '+str(total)


def peer_coverage_html(view):
    if not isinstance(view,Mapping) or view.get('status')!='inspection_only':
        return '<section class="online-peer-valuation" aria-label="Industry peer coverage"><h3>Industry peer valuation coverage</h3><p>Session progress or the current source could not be verified. Restart the sample. Sources are not fetched automatically.</p></section>'
    n=view['requested_count']
    html=STYLE+'<section class="online-peer-valuation" aria-label="Industry peer coverage"><h3>Industry peer valuation coverage</h3><p>This sample has '+str(n)+' specified companies. Counts describe this sample, not the full US market or complete industries.</p>'
    stats=[('Inspected',view['attempted_count']),('Selected-company annual P/E available',view['subject_pe_count']),('Reference comparison available',view['comparison_count']),('Pending',view['pending_count'])]
    html+='<dl class="peer-stats">'+''.join('<div><dt>'+k+'</dt><dd>'+_fraction(v,n)+'</dd></div>' for k,v in stats)+'</dl>'
    html+='<p>References assessed: '+_fraction(view['reference_assessed_count'],n)+'. A selected-company P/E does not establish a reference comparison. At least 3 compatible references must fully qualify before a multiple difference is shown.</p>'
    html+='<p>Progress continues within this session only. Restarting clears this sample. Sources are rechecked at their original observation times. Stale evidence leaves a gap and is not refreshed automatically.</p>'
    if view['paused']:html+='<p><strong>Source failures for two consecutive companies paused further queries. Explicitly retry an inspected company to continue.</strong></p>'
    html+='<table aria-label="Industry sample coverage"><thead><tr>'+''.join('<th scope="col">'+s+'</th>' for s in ('Industry / SIC','Specified companies','Inspected','Selected-company P/E','Reference comparison'))+'</tr></thead><tbody>'
    for group in view['by_industry']:
        cells=[('Industry / SIC',_text(_industry(group))+' · '+_text(group.get('sic'))),('Specified companies',str(group['requested_count'])),
               ('Inspected',_fraction(group['attempted_count'],group['requested_count'])),('Selected-company P/E',_fraction(group['subject_pe_count'],group['requested_count'])),
               ('Reference comparison',_fraction(group['comparison_count'],group['requested_count']))]
        html+='<tr>'+''.join('<td data-label="'+k+'">'+v+'</td>' for k,v in cells)+'</tr>'
    html+='</tbody></table><details><summary>View company status, gaps, and sources</summary>'
    for row in view['rows']:
        state='Reference comparison available' if row['comparison_state']=='available' else 'Selected-company P/E available; references pending' if row['subject_pe_state']=='available' else 'Selected-company P/E unavailable' if row['attempted'] else 'Pending'
        html+='<details><summary>'+_text(row['ticker'])+' · '+state+'</summary><p>'+_text(_industry(row))+' · provider industry '+_text(row.get('industry_key'))+' · SEC SIC '+_text(row.get('sic'))+' · observed '+_text(row.get('attempted_at'))+'</p>'
        if not row['attempted']:html+='<p>Source queries have not started for this company. References remain unassessed.</p>'
        elif row['reference_state']=='not_assessed_subject_blocked':html+='<p>References remain unassessed while the selected-company source or identity gap is open. Unassessed does not mean zero eligible references.</p>'
        else:html+='<p>Qualified references '+str(row['accepted_reference_count'])+'. '+('Reference review is incomplete, and paused items remain open.' if row['reference_state']=='partially_assessed' else 'The bounded candidate set was inspected in this attempt.')+'</p>'
        if row['comparison_state']!='available':html+='<p>First blocker: '+('Not yet inspected.' if not row['attempted'] else _text(_reason(row['primary_reason'])))+'</p>'
        if row.get('selected_security_state') in {'supported_common','inspection_only'}:
            html+='<p>Selected-security evidence: '+('The selected common share and annual EPS basis were checked. Valuation eligibility remains a separate gate.' if row['selected_security_state']=='supported_common' else _text(_reason(row.get('selected_security_reason'))))+'</p>'
        url='?'+urlencode(dict(mode='research',page='company-workbench',ticker=row['ticker'],online='1',section='valuation'))
        html+='<p><a href="'+escape(url,quote=True)+'" target="_self">Open online company valuation</a></p>'
        for ref in row['source_refs']:
            html+='<p>'+_link(ref.get('source_url'),'Source observation')+' · '+_text(ref.get('observed_at'))+' · SHA-256 <code>'+_text(ref.get('payload_sha256') or ref.get('normalized_sha256'))+'</code></p>'
            if ref.get('body_sha256'):html+='<p>Verified filing-body SHA-256 <code>'+_text(ref['body_sha256'])+'</code></p>'
        html+='</details>'
    html+='</details><details><summary>Main gaps and candidate exclusions</summary><h4>Main gaps</h4><p>Only the first blocker is counted for each company. Later rules may remain unchecked.</p><ul>'
    html+=''.join('<li>'+_text(_reason(reason))+' · '+str(count)+' companies</li>' for reason,count in view['primary_reason_counts'].items()) or '<li>No main gaps have been recorded.</li>'
    html+='</ul><h4>Candidate exclusions</h4><p>These are candidate checks across companies. The same reference may be checked more than once, so this is not a unique-issuer count.</p><ul>'
    html+=''.join('<li>'+_text(_reason(reason))+' · '+str(count)+' checks</li>' for reason,count in view['excluded_reason_counts'].items()) or '<li>No candidate exclusions have been recorded.</li>'
    html+='</ul><p>Adapter operations '+str(view['adapter_operation_count'])+'. This counts component calls, not HTTP requests. Each attempt checks at most 12 other candidates and does not cover an entire industry.</p></details><p>Personal research only. Commercial and redistribution rights remain unapproved. This sample does not update canonical data, saved valuation, or the issuer-coverage checkpoint.</p></section>'
    return html


def render_peer_coverage(st_api):
    """Callbacks finish before the rerender; ordinary rendering never requests sources."""
    def act(kind):
        with st_api.spinner('Checking one company and its industry references…'):
            get_peer_coverage(st_api.session_state,inspect_requested=kind=='next',reset_requested=kind=='reset',
                retry_ticker=st_api.session_state.get('peer-coverage-retry') if kind=='retry' else None,
                user_agent=os.getenv('SEC_USER_AGENT'))
    st_api.markdown('<div id="peer-coverage-sample"></div>',unsafe_allow_html=True)
    with st_api.expander('Peer valuation coverage · industry sample',expanded=False):
        st_api.caption('Inspect annual P/E and reference comparability one company at a time. Missing sources and unassessed companies remain visible.')
        raw=st_api.session_state.get(SESSION_KEY,{});raw=raw if isinstance(raw,Mapping) else {}
        requested=raw.get('requested_tickers',DEFAULT_SAMPLE);requested=requested if isinstance(requested,(list,tuple)) else DEFAULT_SAMPLE
        packets=raw.get('packets',{});packets=packets if isinstance(packets,Mapping) else {}
        attempted=[t for t in requested if _symbol(t) and t in packets]
        paused=type(raw.get('source_failure_streak')) is int and raw['source_failure_streak']>=2
        st_api.button('Inspect next company',key='peer-coverage-next',disabled=paused or len(attempted)==len(requested),on_click=act,args=('next',))
        if attempted:
            st_api.selectbox('Company to retry',attempted,key='peer-coverage-retry')
            st_api.button('Retry selected company',key='peer-coverage-retry-action',on_click=act,args=('retry',))
        st_api.button('Restart sample',key='peer-coverage-reset',on_click=act,args=('reset',))
        result=get_peer_coverage(st_api.session_state,user_agent=os.getenv('SEC_USER_AGENT'))
        st_api.markdown(peer_coverage_html(result),unsafe_allow_html=True)
        return result
