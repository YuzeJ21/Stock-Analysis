"""Compact, source-dated capability study; separate from universe coverage."""
from html import escape

from src.online_peer_valuation_ui import _link, _reason
from src.online_research_tools_ui import sec_request_identification
from src.self_service_research_coverage import (
    CAPABILITY_LABELS, SAMPLE, SAMPLE_GROUPS, get_self_service_coverage, validated_coverage_view,
)

STYLE = '''<style>
.self-service-coverage{min-width:0;overflow-wrap:anywhere;color:#18372b}
.self-service-coverage .coverage-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.6rem;margin:1rem 0}
.self-service-coverage .coverage-metrics>div{padding:.85rem;border:1px solid #d3e0d7;border-radius:.6rem;background:#fff;min-width:0}
.self-service-coverage .coverage-metrics strong{display:block;font-size:1.35rem;margin-top:.4rem}
.self-service-coverage .coverage-table-scroll{max-width:100%;overflow-x:auto}
.self-service-coverage table{border-collapse:collapse;width:100%;font-size:.85rem}
.self-service-coverage th,.self-service-coverage td{text-align:left;padding:.7rem .5rem;border-bottom:1px solid #d3e0d7}
.self-service-coverage .coverage-group-table{min-width:36rem}
.self-service-coverage.coverage-dated{background:#fff;border:1px solid #d3e0d7;border-radius:.6rem;padding:1rem;margin:1rem 0}
.self-service-coverage.coverage-dated h3,.self-service-coverage.coverage-dated h4,.self-service-coverage.coverage-dated p,
.self-service-coverage.coverage-dated th,.self-service-coverage.coverage-dated td,.self-service-coverage.coverage-dated li,
.self-service-coverage.coverage-dated summary{color:#18372b!important}
.self-service-coverage .coverage-dated-table{min-width:30rem}
.self-service-coverage .coverage-dated-table small{display:block;margin-top:.25rem}
.self-service-coverage details{margin:.7rem 0}.self-service-coverage summary{min-height:44px;align-content:center;cursor:pointer}
.self-service-coverage a{color:#144c3d;text-decoration:underline}
[data-peer-source-storage]{padding:1rem;border:1px solid #d3e0d7;border-radius:.6rem;background:#fff!important;color:#18372b!important;overflow-wrap:anywhere}
[data-peer-source-storage] dt,[data-peer-source-storage] dd,[data-peer-source-storage] code{color:#18372b!important}
[data-peer-source-storage] dt{font-weight:600;margin-top:.6rem}[data-peer-source-storage] dd{margin:0}
[data-peer-source-storage] code{background:#edf4ef!important;white-space:normal;overflow-wrap:anywhere}
@media(max-width:700px){.self-service-coverage .coverage-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>'''


def _label(value):
    return str(value or 'Not available').replace('_',' ')


def _explain(reason):
    if reason == 'exact_ibn_annual_table_and_filing':
        return 'Workbench has qualified bank annual facts. The study requires revenue in the general period table for this count.'
    if reason == 'exact_ibn_interim_table_and_filing':
        return 'Workbench has qualified bank interim facts. The study requires revenue in the general period table for this count.'
    translated = _reason(reason)
    if translated == 'Source, identity, or field evidence could not be verified. This input is withheld.':
        return _label(reason)
    return translated


def dated_coverage_comparison_html(report):
    """Compare dated measurements without mixing them into the current session."""
    before = report['baseline_available']
    rows = report['rows']
    pending = set(SAMPLE) - rows.keys()
    total = len(SAMPLE)
    available = {key: {ticker for ticker, cells in rows.items() if cells[key][0] == 'available'}
                 for key in CAPABILITY_LABELS}
    highlights = ''.join(
        f'<li>{CAPABILITY_LABELS[key]} · <strong>{len(before[key])} / {total} → {len(available[key])} / {total}</strong></li>'
        for key in ('direct_quarter', 'peer_comparison', 'snapshot_replay'))
    replay = available['snapshot_replay']
    additions = (set(report.get('same_source_replay_recheck', ())) & rows.keys()) - replay
    recheck = ''
    if additions:
        companies = ', '.join(ticker for ticker in SAMPLE if ticker in additions)
        recheck = ('<p><strong>Same-source replay recheck</strong> · '
                   f'{len(replay)} / {total} → {len(replay | additions)} / {total}. '
                   f'{escape(companies)} reopened unchanged using the retained study inputs. ADS valuation remains withheld.</p>')
    table_rows = []
    for key, label in CAPABILITY_LABELS.items():
        prior = set(before[key])
        current = available[key]
        changes = []
        for change, members in (
            ('Now available', current - prior),
            ('Previously available, now blocked', (prior - current) - pending),
            ('Unattempted', prior & pending),
        ):
            if members:
                changes.append(change + ' · ' + ', '.join(ticker for ticker in SAMPLE if ticker in members))
        change_html = ''.join('<small>' + escape(line) + '</small>' for line in changes)
        difference = len(current) - len(prior)
        delta = 'Incomplete' if pending else f'{difference:+d}' if difference else '0'
        table_rows.append(f'<tr><th scope="row">{escape(label)}</th><td>{len(prior)} / {total}</td>'
                          f'<td>{len(current)} / {total}</td><td>{delta}{change_html}</td></tr>')
    groups = []
    for group, tickers in SAMPLE_GROUPS:
        companies = []
        for ticker in tickers:
            if ticker not in rows:
                companies.append(f'<li><strong>{ticker}</strong> · Unattempted</li>')
                continue
            blockers = [f'<li>{escape(label)} · {escape(_label(status).title())} · {escape(_explain(reason))}</li>'
                        for key, label in CAPABILITY_LABELS.items()
                        for status, reason in (rows[ticker][key],) if status != 'available']
            detail = '<ul>' + ''.join(blockers) + '</ul>' if blockers else '<p>All ten capabilities available.</p>'
            companies.append(f'<li><details><summary>{ticker}</summary>{detail}</details></li>')
        groups.append(f'<h4>{escape(group)}</h4><ul>{"".join(companies)}</ul>')
    measured = escape(report['measured_date'])
    baseline = escape(report['baseline_date'])
    return (STYLE + '<section class="self-service-coverage coverage-dated" aria-label="Dated study results">'
            '<h3>Dated study results</h3>'
            f'<p><strong>{len(rows)} / {total} attempted</strong> · {measured}</p>'
            '<p>The fixed sample covers four research groups. Counts use the same twelve companies and reflect '
            'the sources and product behavior observed on each date. Your session results appear below.</p>'
            '<ul>' + highlights + '</ul>' + recheck + '<details><summary>Compare available capabilities</summary>'
            '<div class="coverage-table-scroll" role="region" aria-label="Dated capability comparison" tabindex="0">'
            '<table class="coverage-dated-table"><thead><tr><th scope="col">Capability</th>'
            f'<th scope="col">{baseline}</th><th scope="col">{measured}</th><th scope="col">Change</th>'
            '</tr></thead><tbody>' + ''.join(table_rows) + '</tbody></table></div></details>'
            '<details><summary>Remaining gaps by company</summary>' + ''.join(groups) + '</details>'
            '<p><a href="https://github.com/YuzeJ21/Stock-Analysis/blob/main/docs/CROSS_INDUSTRY_SELF_SERVICE.md#dated-rerun" '
            'target="_blank" rel="noopener noreferrer">Study method and dated results</a></p></section>')


def self_service_coverage_html(view):
    checked = validated_coverage_view(view)
    if checked is None:
        return '<section class="self-service-coverage" aria-label="Self-service research coverage"><h3>Self-service research coverage</h3><p>The saved study could not be verified. Restart this sample to inspect sources again.</p></section>'
    n = checked['requested_count']
    html = STYLE + '<section class="self-service-coverage" aria-label="Self-service research coverage"><h3>Self-service research coverage</h3>'
    html += '<p>Twelve declared companies in four research groups; this is not market-wide coverage. Every failed, excluded and unattempted company remains in its group denominator.</p>'
    html += '<div class="coverage-metrics">'
    for label,key in (('Inspected','attempted'),('Current annual facts','current_annual'),('Dated closes','dated_price'),('Peer comparisons','peer_comparison')):
        html += '<div>'+label+'<strong>'+str(checked['counts'][key])+' / '+str(n)+'</strong></div>'
    html += '</div><div class="coverage-table-scroll" role="region" aria-label="Research group capability counts" tabindex="0"><table class="coverage-group-table"><thead><tr>'
    columns = (('Inspected','attempted'),('Annual facts','current_annual'),('Direct quarter','direct_quarter'),('Dated close','dated_price'),('Peer P/E','peer_comparison'))
    html += '<th scope="col">Research group</th>'+''.join('<th scope="col">'+label+'</th>' for label,_ in columns)+'</tr></thead><tbody>'
    for row in checked['by_group']:
        html += '<tr><th scope="row">'+escape(row['group'])+'</th>'+''.join('<td>'+str(row['counts'][key])+' / '+str(row['requested_count'])+'</td>' for _,key in columns)+'</tr>'
    html += '</tbody></table></div><p>Unattempted: '+str(checked['pending_count'])+' / '+str(n)+'. A dated close is not proof of share-class identity or valuation eligibility. Annual and quarter counts describe supported, source-matched facts, not a complete statement model.</p>'
    html += '<details><summary>All tool counts and method exclusions</summary><ul>'
    for key,label in CAPABILITY_LABELS.items():
        states = checked.get('capability_status_counts',{}).get(key,{})
        held = ', '.join(str(count)+' '+status for status,count in states.items() if count and status!='available')
        html += '<li>'+escape(label)+': '+str(checked['counts'][key])+' / '+str(n)+(' · '+escape(held) if held else '')+'</li>'
    html += '</ul><p>Bank FCFF scenarios stay excluded. Industry P/E still requires same-day completed closes, a compatible annual diluted EPS basis, the 35-day fiscal window and at least three qualified references. Native-currency statements do not qualify an ADS or FX valuation join.</p></details>'
    if checked.get('paused'):
        html += '<p><strong>Source access paused.</strong> Remaining companies have not been inspected. Recheck an attempted company explicitly to resume when access is available. No automatic retries or paid data are used.</p>'
    html += '<p>Personal research inspection. Source permissions, canonical data and saved model readiness are unchanged. This study does not write to your company notes or evidence stores.</p></section>'
    return html


def _company_details(st,row):
    st.markdown('#### '+row['ticker']+' · '+row['group'])
    st.caption('SEC CIK '+str(row.get('sec_cik') or 'unverified')+' · '+_label(row.get('status')))
    rows = []
    for key,label in CAPABILITY_LABELS.items():
        cap = row['capabilities'][key]
        rows.append('<tr><th scope="row">'+escape(label)+'</th><td>'+escape(_label(cap['status']).title())+'</td><td>'+escape(_explain(cap.get('reason')))+'</td></tr>')
    st.markdown('<section class="self-service-coverage"><div class="coverage-table-scroll" role="region" aria-label="Selected company capabilities" tabindex="0"><table><thead><tr><th scope="col">Capability</th><th scope="col">State</th><th scope="col">Evidence or gap</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>',unsafe_allow_html=True)
    if row.get('price_date'):
        st.caption('Completed closing-price date: '+row['price_date'])
    storage = row.get('peer_storage') or {}
    if storage.get('status')=='retained' and storage.get('source_evidence_unchanged') is True:
        st.markdown('<p class="company-scope-note" data-peer-evidence-retained="1">Full peer source evidence retained · exact restoration verified.</p>',unsafe_allow_html=True)
    with st.expander('Reporting periods and original source receipts',expanded=False):
        if storage:
            st.caption('Peer source retention. Storage does not establish valuation eligibility.')
            st.markdown(peer_storage_proof_html(storage),unsafe_allow_html=True)
        st.json(row.get('periods') or {},expanded=False)
        for ref in row.get('source_receipts') or []:
            st.markdown(_link(ref.get('source_url') or ref.get('source_ref'),'Original source'),unsafe_allow_html=True)
            st.caption('Observed '+str(ref.get('observed_at') or ref.get('retrieved_at_utc') or 'not recorded')+' · SHA-256 '+str(ref.get('payload_sha256') or ref.get('normalized_sha256') or 'not retained'))
        if not row.get('source_receipts'):
            st.caption('No verified source receipt for this attempt.')
        if row.get('peer_source_attempts'):
            st.caption('Peer listing-source attempts; a failed request is not unsupported security evidence.')
            st.json(row['peer_source_attempts'],expanded=False)
        if row.get('peer_exclusions'):
            st.caption('Industry references excluded from this observation')
            st.json(row['peer_exclusions'],expanded=False)
        st.json(row.get('snapshot_replay') or {},expanded=False)


def peer_storage_proof_html(storage):
    html = '<section data-peer-source-storage="1" aria-label="Peer source storage proof"><strong>Peer source retention</strong><dl>'
    fields = [('State',_label(storage.get('status'))),('Encoding',storage.get('encoding'))]
    for label,key in [('Restored source bytes','expanded_bytes'),('Stored packet bytes','stored_bytes')]:
        value = storage.get(key)
        if type(value) is int:
            fields.append((label,f'{value:,}'))
    fields.append(('Original packet digest',storage.get('packet_digest') or 'Not verified'))
    for label,value in fields:
        html += '<dt>'+escape(label)+'</dt><dd>'+escape(str(value or 'Not verified'))+'</dd>'
    html += '</dl><p>'+escape(_label(storage.get('reason')))+'</p></section>'
    return html


def render_self_service_coverage(st):
    from src.self_service_study_results import DATED_STUDY

    st.markdown(dated_coverage_comparison_html(DATED_STUDY),unsafe_allow_html=True)
    st.caption('Inspect the declared sample in this session using the same online tools as Company Workbench. Section changes do not request sources.')
    view = get_self_service_coverage(st.session_state,user_agent=sec_request_identification(st))
    checked = validated_coverage_view(view)
    by_ticker = {row['ticker']:row for row in checked['rows']} if checked else {}
    # Register this selection even on runs that stop at an explicit action's
    # rerun, so Streamlit's widget cleanup cannot reset it to the first ticker.
    selected = st.radio('Company evidence',tuple(by_ticker),horizontal=True,
        key='self-service-coverage-company') if by_ticker else None
    inspect = st.button('Inspect next company',key='self-service-coverage-next',
        disabled=bool(view.get('paused')) or view.get('pending_count',12)==0 or view.get('status')!='inspection_only')
    retry = None
    can_recheck = selected and by_ticker[selected]['attempted'] and view.get('status')=='inspection_only'
    if st.button('Recheck company',key='self-service-coverage-retry',disabled=not can_recheck):retry=selected
    reset = st.button('Restart study',key='self-service-coverage-reset')
    if inspect or retry or reset:
        with st.spinner('Checking online sources and research tools…'):
            view = get_self_service_coverage(st.session_state,inspect_requested=inspect,retry_ticker=retry,
                reset_requested=reset,user_agent=sec_request_identification(st))
        st.rerun()
    st.markdown(self_service_coverage_html(view),unsafe_allow_html=True)
    if selected:
        _company_details(st,by_ticker[selected])
