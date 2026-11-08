"""Explicit company receipt actions, shared by company records and Monitor."""
from html import escape
from pathlib import Path
import os
from src.sec_exact_filing import get_company_filing_preview
from src.online_company_identity import _mode_reason
from src.sec_research_review import (
    MAX_BYTES, attach_operating_income_check, capture_review, compare_reviews, encode_review, list_reviews, load_review, save_review,
    review_queue, _ticker,
)
from src.company_sec_online_preview import _utc_timestamp
from src.sec_review_disposition import (
    MAX_REASON_LENGTH, SUPPORTED_DISPOSITION_COMPANIES, load_disposition, resolve_pair, save_disposition,
)

PROJECT_ROOT=Path(__file__).resolve().parent.parent


def saved_review_route_available(ticker,profile_key):
    """Saved evidence permits offline inspection, never current listing eligibility."""
    if not _ticker(ticker) or not isinstance(profile_key,str):return False
    try:return bool(list_reviews(PROJECT_ROOT,profile_key,ticker))
    except (ValueError,OSError):return False


LABELS={'revenue':'Revenue','operating_income':'Operating income','cash_from_operations':'Cash from operations',
        'capital_expenditures':'Capital expenditures','all':'Entire evidence package'}
REASONS={'source_evidence_unreviewed':'Direct source evidence needs review. Check the exact filing field.',
    'direct_field_missing':'No direct field for the same filing and period. Check the original filing.',
    'prior_direct_field_missing':'The earlier evidence lacks this direct field.', 'baseline_missing':'A second comparable saved observation is required.',
    'duration_mismatch':'Duration or period dates differ.', 'period_end_mismatch':'Reporting periods differ.',
    'concept_mismatch':'Financial definitions differ', 'unit_mismatch':'Units or currencies differ.',
    'rights_policy_changed':'The source rights registry changed. Review permissions again.', 'profile_key_mismatch':'Research profiles differ.',
    'same_source_digest_conflict':'The same source checksum has conflicting fields. Check evidence consistency.',
    'rights_mismatch':'Field permissions differ.', 'raw_source_conflict':'The original source has conflicting values. Check the filing context.',
    'raw_source_value_invalid':'The original source value failed validation.'}
REASONS.update({
    'matching_direct_native_unit_fact_unavailable':'No matching direct standard operating income fact in this filing. Pretax income, segment measures and EBITDA have different definitions.',
    'conflicting_direct_facts':'Conflicting direct operating income facts in this filing. Value withheld.',
    'exact_direct_fact_rights_held':'A direct fact exists, but archive field rights are unregistered. Value withheld.',
    'exact_direct_fact_unusable':'The direct filing fact failed value or source validation. Value withheld.'})
STATUS={'unchanged':'No change','changed':'Changed, review required','withheld':'Comparison basis differs, gaps retained',
        'gaps_changed':'Evidence gaps changed, review required','baseline_missing':'Saved, awaiting a comparison baseline'}
STATUS['review_changed']='Source review changed, financial values unchanged'
DISPOSITIONS = {'reviewed': 'Reviewed', 'still_open': 'Still open'}
PAIR_UNAVAILABLE = 'This saved evidence pair is unavailable. Check the research profile and full evidence IDs.'
REASONS.update({'ticker_mismatch':'The evidence belongs to different companies. A same-company comparison is required.',
    'sec_cik_mismatch':'Issuer identities differ. Their relationship requires independent review.'})


def _label(packet):
    stamp=_utc_timestamp(packet['saved_at']).strftime('%m/%d %H:%M')
    return f"{packet['period_end']} · {stamp} · {packet['receipt_id'][:6]}"


def _gaps_html(result):
    rows=''.join('<li><strong>'+escape(LABELS.get(g['field'],g['field']))+'</strong> · '+
        escape(REASONS.get(g['reason'],g['reason'].replace('_',' ').capitalize()))+'</li>' for g in result['gaps'])
    return '<ul>'+rows+'</ul>' if rows else '<p>These four direct fields have no open evidence gaps. Full valuation and investment decisions require additional evidence.</p>'


def _render_comparison(st,result):
    label=STATUS[result['status']]
    if result['status']=='unchanged':st.success(label+' · Saved field values and reporting basis match.')
    elif result['status']=='changed':st.warning(label)
    else:st.info(label)
    if result.get('review_changes'):st.caption('Source review evidence changed. Financial value changes are shown separately.')
    for change in result['changes']:
        left,right=change['before'],change['after']
        st.markdown('**'+LABELS[change['field']]+'**')
        st.write(f"{left['value']:,} → {right['value']:,} {right['unit']}")
        st.caption('Changed dimensions · '+', '.join(change['changed_dimensions'])+
            ' · Earlier filing '+left['accession']+' · Later filing '+right['accession'])
    st.markdown(_gaps_html(result),unsafe_allow_html=True)


def _render_exact_check(st, packet, *, show_reason=True):
    check=packet.get('operating_income_check')
    if not check:return
    st.markdown('**Operating income · original filing checked, gap retained**')
    if show_reason:st.markdown(REASONS[check['reason']])
    st.markdown('[View the reviewed SEC filing]('+check['source_url']+')')
    st.caption(check['form']+' · '+check['accession']+' · '+check['period_start']+' to '+check['period_end']+
        ' · '+check['taxonomy']+':'+check['concept']+' · '+check['unit'])
    st.caption('Filed '+check['filed']+' · Accepted '+check['accepted_at']+' · Review observed '+check['observed_at'])
    st.caption('Archive inspection is for personal research. This filing check retains review metadata only. Archive values and additional source rights require separate approval.')
    with st.expander('Original filing check checksum',expanded=False):
        st.code(check['payload_sha256'],language=None)
        st.caption('Source rights · '+check['rights_status'])


def _check_candidate(st, candidate, scope):
    eligible=candidate is not None and any(g['field']=='operating_income' for g in candidate['gaps'])
    key='sec-review-exact-result:'+scope
    # Bind the action to this Companyfacts observation, not just a ticker or year.
    anchor={k:v for k,v in candidate.items() if k not in {'saved_at','receipt_id'}} if eligible else None
    if st.button('Check the operating income filing',key='sec-review-exact:'+scope,disabled=not eligible):
        st.session_state[key]={'anchor':anchor,'preview':{'status':'withheld'}}
        with st.spinner('Checking the exact SEC filing against the current financial basis…'):
            source=get_company_filing_preview('NEM',st.session_state,period_kind='annual',
                refresh_requested=True,user_agent=os.getenv('SEC_USER_AGENT'),expected_cik='0001164727')
        st.session_state[key]={'anchor':anchor,'preview':source}
    cached=st.session_state.get(key)
    if eligible and isinstance(cached,dict) and cached.get('anchor')==anchor:
        try:
            candidate=attach_operating_income_check(candidate,cached['preview'])
            st.info('Original filing check complete. Save below to retain this check with the evidence.')
            with st.expander('Filing check ready to save',expanded=False):
                _render_exact_check(st,candidate)
        except (ValueError,TypeError,KeyError):
            st.warning('The filing check could not be attached. Source access, filing, period or unit validation failed. The gap remains open. Check Data Sources.')
    return candidate


CONTROL_STYLE='''<style>
.st-key-sec-review-panel [data-testid="stDownloadButton"] button,
.st-key-sec-review-panel [data-testid="stDownloadButton"] button p,
.st-key-sec-review-panel [data-testid="stDownloadButton"] button span,
.sec-review-link {background:#155e4b!important;color:#fff!important;}
.st-key-sec-review-panel [data-testid="stDownloadButton"] button {min-height:44px!important;}
.sec-review-link {display:inline-flex;align-items:center;min-height:44px;padding:8px 14px;
box-sizing:border-box;border-radius:7px;text-decoration:none!important;white-space:normal;}
.sec-review-link:focus-visible {outline:3px solid #b45309;outline-offset:3px;}
.st-key-sec-review-panel [data-testid="stCaptionContainer"] {overflow-wrap:anywhere;}
</style>'''


def _selected_cik_valid(cik):
    return isinstance(cik,str) and len(cik)==10 and cik.isascii() and cik.isdigit() and cik!='0000000000'


def render_company_review(st,ticker,view,*,profile_key,expected_cik=None):
    if not _ticker(ticker) or _mode_reason('research'):return
    st.markdown(CONTROL_STYLE,unsafe_allow_html=True)
    with st.container(key='sec-review-panel'):
        _render_company_review(st,ticker,view,profile_key=profile_key,expected_cik=expected_cik)


def _render_company_review(st,ticker,view,*,profile_key,expected_cik=None):
    st.markdown('### Saved SEC evidence review')
    st.caption(f'{ticker} · Supports direct US-GAAP / USD annual 10-K and 10-K/A fields. Save explicitly for offline replay. Canonical financials, source permissions and research journal updates require separate actions.')
    if expected_cik is not None:
        if not _selected_cik_valid(expected_cik):
            st.error('Saved SEC evidence is unavailable. The selected issuer requires a verified, nonzero 10-digit CIK.')
            return
        st.caption('Selected issuer CIK '+expected_cik+' · Only matching issuer evidence can be saved, imported or replayed here.')
    token = st.query_params.get('sec_pair')
    if ticker in SUPPORTED_DISPOSITION_COMPANIES and token:
        if st.query_params.get('online') == '1':
            st.warning(f'Open this evidence pair from Monitor on the saved {ticker} company page.')
        else:
            _render_pinned_pair(st, profile_key, ticker, token, expected_cik=expected_cik)
        return
    scope=f'{profile_key}:{ticker}'
    try:
        candidate=capture_review(view,profile_key=profile_key)
        if candidate['ticker']!=ticker:candidate=None
        if candidate is not None and expected_cik is not None and candidate['sec_cik']!=expected_cik:
            st.warning(f"Current evidence CIK {candidate['sec_cik']} differs from selected issuer CIK {expected_cik}. This observation cannot be saved here.")
            candidate=None
    except (ValueError,TypeError,OSError):candidate=None
    if ticker=='NEM':candidate=_check_candidate(st,candidate,scope)
    if st.button('Save current SEC evidence',key='sec-review-save:'+scope,disabled=candidate is None):
        try:save_review(candidate,PROJECT_ROOT);st.success('Observation saved.')
        except (ValueError,OSError):st.error('Evidence was not saved. Check the source basis or storage folder. Limits are 100 receipts per company and 100 companies per research profile.')
    if candidate is None:st.caption(f'Use Refresh financials above to obtain an eligible {ticker} SEC observation. Unsupported filing forms, currencies or a missing direct revenue anchor retain their gaps. Saved evidence remains available for replay.')
    with st.expander('Import evidence package',expanded=False):
        st.caption(f'Accepts {ticker} evidence JSON for this research profile, up to 64 KB. A checksum verifies content consistency. Imported evidence is user supplied and requires independent source authentication.')
        upload=st.file_uploader('Choose an exported evidence package',type=['json'],max_upload_size=1,key='sec-review-upload:'+scope)
        if st.button('Import and save evidence package',key='sec-review-import:'+scope,disabled=upload is None):
            try:
                upload.seek(0);packet=load_review(upload.read(MAX_BYTES+1))
                if packet['profile_key']!=profile_key or packet['ticker']!=ticker:raise ValueError('selected_scope_mismatch')
                if expected_cik is not None and packet['sec_cik']!=expected_cik:raise ValueError('selected_issuer_mismatch')
                save_review(packet,PROJECT_ROOT);st.success('Evidence package imported. The saved file is replayed below.')
            except (ValueError,OSError):
                issuer_reason='selected issuer CIK mismatch, ' if expected_cik is not None else ''
                st.error('Import failed. Check for a damaged file, company or research profile mismatch, '+issuer_reason+'unavailable storage or a full receipt history.')
    try:packets=list_reviews(PROJECT_ROOT,profile_key,ticker)
    except (ValueError,OSError):st.error('Saved evidence could not be fully verified. Comparison is paused. Retain the files and check the storage folder.');return
    if expected_cik is not None:
        excluded=[packet for packet in packets if packet['sec_cik']!=expected_cik]
        packets=[packet for packet in packets if packet['sec_cik']==expected_cik]
        if excluded:
            other_ciks=', '.join(sorted({packet['sec_cik'] for packet in excluded}))
            st.warning(f'Excluded {len(excluded)} saved evidence package(s) for other issuer CIKs ({other_ciks}). Only selected issuer CIK {expected_cik} is available for replay. The saved files are retained.')
        if excluded and not packets:
            st.info('No saved evidence matches selected issuer CIK '+expected_cik+'. Save or import a matching observation to replay it here.')
            return
    if not packets:st.info('No evidence saved yet. Save the first observation, then save or import another observation to compare.');return
    st.markdown('#### Replay saved evidence')
    st.caption('Each option shows the reporting period, UTC save time and evidence ID. Full timestamps appear in the source details below.')
    options=list(range(len(packets)))
    current_index=st.selectbox('Evidence to replay',options,index=len(packets)-1,
        format_func=lambda i:_label(packets[i]),key=f'sec-review-current:{scope}:{len(packets)}')
    current=packets[current_index]
    baseline_options=[None]+options
    prior_index=st.selectbox('Compare with saved evidence',baseline_options,index=(current_index if current_index else 0),
        format_func=lambda i:'No baseline selected' if i is None else _label(packets[i]),
        key=f'sec-review-before:{scope}:{len(packets)}:{current_index}')
    before=None if prior_index is None else packets[prior_index]
    result=compare_reviews(before,current)
    st.caption(f"This evidence · {len(current['fields'])}/4 direct fields · {len(current['gaps'])} field gaps. Complete financial coverage and valuation eligibility require further evidence.")
    _render_comparison(st,result)
    _render_exact_check(st,current,show_reason=False)
    st.caption('Replaying saved evidence offline. Save time and SEC observation time are recorded separately. A later save time alone carries no financial revision.')
    st.download_button('Download current evidence package',data=encode_review(current),file_name=ticker+'-SEC-'+current['receipt_id'][:12]+'.json',
        mime='application/json',key='sec-review-download:'+scope)
    _render_monitor_link(st, ticker)
    _render_receipt_sources(st, current, 'Evidence sources and field definitions')


def _render_monitor_link(st, ticker, *, token=''):
    from src.research_workspace import research_monitor_handoff_href
    monitor_href = research_monitor_handoff_href(ticker, online=st.query_params.get('online') == '1', sec_pair=token,
        **({'notes_cik':st.query_params.get('notes_cik')} if st.query_params.get('notes_cik') else {}))
    label = 'Return to this review in Monitor' if token else 'View review items in Monitor'
    st.markdown(
        '<a class="sec-review-link" data-research-session-route="monitor" '
        f'href="{escape(monitor_href, quote=True)}" target="_self">{label}</a>',
        unsafe_allow_html=True,
    )


def _render_receipt_sources(st, current, title, *, show_values=True):
    with st.expander(title, expanded=False):
        st.write('Period ended '+current['period_end']+' · '+current['form'])
        st.write('Filing publication date '+current['filing_date']+' (day precision)')
        st.write('SEC observation time '+current['source_observed_at'])
        st.write('Saved at '+current['saved_at'])
        st.markdown('[SEC Companyfacts source]('+current['source_url']+')')
        st.caption('Accession '+current['accession']+' · CIK '+current['sec_cik'])
        st.caption('Raw response SHA-256 '+current['raw_payload_sha256'])
        st.caption('Source rights registry SHA-256 '+current['rights_registry_sha256'])
        if current.get('companyfacts_identity'):
            identity=current['companyfacts_identity']
            st.markdown('[SEC issuer-to-CIK association source]('+identity['association_source_url']+')')
            st.caption('Association observed '+identity['association_observed_at']+' · SHA-256 '+identity['association_payload_sha256'])
        st.caption('Scope is issuer financial facts. Security class, domicile, listing status, price matching and point-in-time coverage each require separate evidence.')
        st.caption('Permissions cover the registered normalized fields. Raw responses, prices, derived free cash flow and redistribution require separate permission.')
        if show_values:
            for row in current['fields']:
                st.markdown('**'+LABELS[row['field']]+'** · '+format(row['value'],',')+' '+row['unit'])
                st.caption(row['taxonomy']+':'+row['concept']+' · '+row['period_start']+' to '+row['period_end'])


def _pinned_pair(profile_key, ticker, token, *, expected_cik=None):
    before_id, _, after_id = token.partition('.')
    pair=resolve_pair(list_reviews(PROJECT_ROOT, profile_key, ticker), before_id, after_id, ticker=ticker)
    if expected_cik is not None and (not _selected_cik_valid(expected_cik) or any(packet['sec_cik']!=expected_cik for packet in pair)):
        raise ValueError('selected_issuer_mismatch')
    return pair


def _render_pinned_pair(st, profile_key, ticker, token, *, expected_cik=None):
    try:
        before, after = _pinned_pair(profile_key, ticker, token, expected_cik=expected_cik)
    except (ValueError, OSError):
        st.warning(PAIR_UNAVAILABLE)
        if expected_cik is not None:
            st.warning('Selected issuer CIK '+expected_cik+' is required. Evidence for other issuer CIKs is excluded from this comparison.')
        _render_monitor_link(st, ticker)
        return
    st.markdown('#### Pinned SEC evidence comparison')
    st.caption('This comparison replays the selected saved pair offline. Later observations have their own evidence IDs and comparisons.')
    st.caption('Earlier evidence '+before['receipt_id'])
    st.caption('Later evidence '+after['receipt_id'])
    result = compare_reviews(before, after)
    _render_comparison(st, result)
    _render_monitor_link(st, ticker, token=token)
    show_values = not any(gap['reason'] == 'rights_policy_changed' for gap in result['gaps'])
    for title, packet in (('Earlier evidence', before), ('Later evidence', after)):
        _render_exact_check(st, packet)
        _render_receipt_sources(st, packet, title+' source · '+_label(packet), show_values=show_values)


def _render_pair_disposition(st, profile_key, ticker, before, after):
    before_id, after_id = before['receipt_id'], after['receipt_id']
    try:
        resolve_pair((before, after), before_id, after_id, ticker=ticker)
    except ValueError:
        st.warning(PAIR_UNAVAILABLE)
        return
    token = before_id+'.'+after_id
    query = {'mode': 'research', 'page': 'company-workbench', 'ticker': ticker, 'open': '1',
             'section': 'notes', 'sec_pair': token}
    st.caption('Earlier evidence '+_label(before)+' → Later evidence '+_label(after))
    st.button('Open this evidence pair', key='sec-review-open-pair', on_click=st.query_params.from_dict, args=(query,))
    try:
        decision = load_disposition(PROJECT_ROOT, profile_key, before_id, after_id, ticker=ticker)
    except (ValueError, OSError):
        st.warning('The review status for this pair cannot be read. Check the local review record.')
        return
    st.caption('The review status applies only to this pair. Reviewed records that you examined the evidence. Reported gaps remain visible.')
    form_key = 'sec-review-disposition:'+profile_key+':'+ticker+':'+token
    with st.form(form_key):
        status = st.radio('Review status', tuple(DISPOSITIONS), format_func=DISPOSITIONS.get,
                          index=tuple(DISPOSITIONS).index(decision['status']) if decision else None,
                          key=form_key+':status')
        reason = st.text_area('Review reason', value=decision['reason'] if decision else '',
                              max_chars=MAX_REASON_LENGTH, key=form_key+':reason')
        submitted = st.form_submit_button('Save review status')
    if submitted:
        if status is None or not reason.strip():
            st.error('Choose a review status and enter a reason.')
        else:
            try:
                decision = save_disposition(PROJECT_ROOT, profile_key, before_id, after_id, status, reason, ticker=ticker)
            except (ValueError, OSError):
                st.error('Review status was not saved. Check the reason or local evidence.')
            else:
                st.success('Review status saved.')
    if decision:
        st.markdown('**'+DISPOSITIONS[decision['status']]+'**')
        st.text(decision['reason'])
        st.caption('Reviewed at '+decision['reviewed_at'])
    else:
        st.caption('Pending review')


def render_review_monitor(st, *, profile_key, monitor_origin=None):
    if _mode_reason('research'):return
    try:queue=review_queue(PROJECT_ROOT,profile_key)
    except (ValueError,OSError):
        st.warning('The SEC evidence folder cannot be verified or exceeds the 100-company limit. The review queue is unavailable.');return
    if queue['store_errors']:
        st.warning(f"Unverified entries in the SEC evidence folder · {len(queue['store_errors'])}. Check the folder. These entries are excluded from company counts. Valid company records remain available.")
    token = st.query_params.get('sec_pair')
    if not queue['items'] and not token:return
    st.markdown('### Saved SEC evidence review queue')
    st.caption(f"Saved companies {queue['companies']} · With field gaps {queue['field_gap_companies']} · Awaiting baseline {queue['baseline_companies']} · Changed {queue['changed_companies']} · Unreadable {queue['unreadable_companies']}")
    st.caption('Counts include explicitly saved SEC evidence in this research profile. Market coverage, research process items below and investment signals have separate scopes.')
    items={i['ticker']:i for i in queue['items']};symbols=list(items)
    if token:
        selected = st.query_params.get('sec_ticker', 'NEM')
        latest_query = {'mode': 'research', 'page': 'monitor'}
        if selected in SUPPORTED_DISPOSITION_COMPANIES:
            latest_query['return_ticker'] = selected
        st.button('View latest evidence pair', on_click=st.query_params.from_dict, args=(latest_query,))
        if selected not in SUPPORTED_DISPOSITION_COMPANIES or selected not in items:
            st.warning(PAIR_UNAVAILABLE)
            return
    else:
        requested=st.query_params.get('return_ticker') or st.query_params.get('ticker')
        selected=st.selectbox('Select a company to review',symbols,index=symbols.index(requested) if requested in symbols else 0,
            format_func=lambda t:t+' · '+('Saved files need verification' if items[t]['error'] else STATUS[items[t]['comparison']['status']]),
            key='sec-review-monitor-company:'+profile_key)
    item=items[selected]
    st.markdown('#### '+selected+' SEC evidence review')
    if item['error']:
        st.warning(selected+' saved files cannot be verified. Retain the files and check the folder. Other company records remain available.')
        return
    before, current = item['previous'], item['latest']
    result = item['comparison']
    context = 'Latest two saved annual observations' if before else 'First saved annual observation'
    if token:
        try:
            before, current = _pinned_pair(profile_key, selected, token)
        except (ValueError, OSError):
            st.warning(PAIR_UNAVAILABLE)
            return
        result = compare_reviews(before, current)
        context = 'Pinned pair of saved annual observations'
    st.markdown('**'+STATUS[result['status']]+'** · '+context)
    st.caption('Later evidence saved at '+current['saved_at']+' · Reporting period '+current['period_end'])
    st.markdown(_gaps_html(result),unsafe_allow_html=True)
    _render_exact_check(st,current,show_reason=False)
    if result.get('review_changes'):st.caption('Source review evidence changed. Financial value changes are shown separately.')
    for change in result['changes']:st.markdown('- '+LABELS[change['field']]+' · Saved field changed. Check both filing sources.')
    if result['status']=='baseline_missing':st.caption('Next, return to the company page and save an independent observation for the same issuer and period. Saving the same observation again tests replay stability.')
    elif result['gaps']:st.caption('Next, check the source and reporting basis for each field gap. Identical inputs retain their existing gaps.')
    elif result['changes'] or result.get('review_changes'):st.caption('Next, return to the company page to inspect both observations and the source of each change.')
    else:st.caption('The saved inputs are stable. Review again when a new filing or new evidence arrives.')
    if selected in SUPPORTED_DISPOSITION_COMPANIES and before is not None:
        _render_pair_disposition(st, profile_key, selected, before, current)
        return
    notes_href = f"?mode=research&page=company-workbench&ticker={selected}&section=notes"
    notes_label = f"View saved {selected} evidence"
    session_route = ""
    if monitor_origin is not None and monitor_origin.ticker == selected and monitor_origin.section == "notes":
        notes_label = f"Return to {selected} evidence review"
        session_route = ' data-research-session-route="workbench"'
        if monitor_origin.online_cik is not None:
            notes_href = "?mode=research&page=company-workbench"
    st.markdown(
        CONTROL_STYLE + f'<a class="sec-review-link"{session_route} href="{escape(notes_href, quote=True)}" '
        f'target="_self">{escape(notes_label)}</a>',
        unsafe_allow_html=True,
    )
