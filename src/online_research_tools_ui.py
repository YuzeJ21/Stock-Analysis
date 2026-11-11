"""Self-service tools over one issuer's online observations and private notes."""
from collections.abc import Mapping
from html import escape
import os
from pathlib import Path

from src.company_research_notes import CompanyNotesScope, load_company_notes
from src.online_peer_sources import SESSION_KEY as PEER_SESSION_KEY
from src.online_research_tools import build_online_research_context, run_online_scenario
from src.online_company_identity import _mode_reason

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEC_AGENT_KEY = 'company-research-sec-identification'


def sec_request_identification(st, *, show_input=False):
    configured = os.getenv('SEC_USER_AGENT')
    if configured:
        return configured
    if show_input:
        st.session_state[SEC_AGENT_KEY] = st.text_input(
            'SEC request identification (name and contact)',
            value=st.session_state.get(SEC_AGENT_KEY, ''), key=SEC_AGENT_KEY + ':entry',
            help='Used for SEC requests in this app session. No credential or environment setting is changed.')
    return st.session_state.get(SEC_AGENT_KEY)


def _label(value):
    return str(value or 'Not available').replace('_', ' ')


def _scope(context):
    return {key: context[key] for key in ('profile_key', 'ticker', 'sec_cik')}


def _scenario_key(profile, ticker, cik):
    return f'online-scenario:{profile}:{ticker}:{cik or "unverified"}'


def prepare_online_tools(ticker, bundle, state, *, profile_key, expected_cik=None):
    """Read qualified local notes; never call transport or adopt legacy model rows."""
    financial = bundle['financial']
    identity = financial.get('companyfacts_identity', {})
    cik = expected_cik or identity.get('sec_cik')
    notes = None
    note_gap = None
    if cik:
        try:
            notes = load_company_notes(CompanyNotesScope(profile_key, ticker, cik))
        except (OSError, ValueError, UnicodeError):
            note_gap = 'Saved issuer notes could not be verified.'
    prefix = _scenario_key(profile_key, ticker, cik)
    for key in list(state):
        if key.startswith(prefix + ':input:'):
            state[key] = state[key]
    options = dict(ticker=ticker, profile_key=profile_key, expected_cik=cik, notes=notes)
    peers = state.get(PEER_SESSION_KEY)
    context = build_online_research_context(financial, bundle['prices'], peers,
                                            bundle['association'], **options)
    result = state.get(prefix + ':result')
    if isinstance(result, Mapping) and result.get('source_revision') == context['source_revision']:
        context = build_online_research_context(financial, bundle['prices'], peers,
                                                bundle['association'], scenario=result, **options)
    if note_gap:
        context['gaps'].append(note_gap)
    bundle['research_context'] = context
    bundle['online_scenario_key'] = prefix
    return context


def filing_status_html(context):
    coverage = context.get('filing_coverage', {})
    current = coverage.get('current', {})
    inventory = context.get('filing_inventory') or {}
    latest = inventory.get('latest') or {}
    rows = []
    for kind in ('annual', 'quarterly', 'interim'):
        state = current.get(kind) or {}
        anchor = state.get('anchor') or latest.get(kind)
        if anchor:
            label = ('Year to date' if kind == 'interim' else 'Direct quarter') if anchor.get('period_basis') == 'exact_native_quarter_table' else kind.title()
            rows.append(f"{label} {anchor.get('period_end') or 'period unverified'}: {_label(state.get('status'))}")
    if not rows:
        return '<p class="company-scope-note">Latest filing status has not been verified. Use Research company to check SEC reports and structured facts.</p>'
    return '<p class="company-scope-note" data-online-filing-status="1">' + escape(' · '.join(rows)) + '</p>'


def qualify_current_answers(answers, context):
    """Do not present older facts as the response to a known new report."""
    pending = {kind: state for kind, state in (context.get('filing_coverage') or {}).get('current', {}).items()
               if isinstance(state, Mapping) and state.get('status') in {'facts_pending', 'amendment_unresolved'}}
    if not pending:
        return answers
    qualified = []
    for answer in answers:
        if answer['key'] != 'financial':
            qualified.append(answer)
            continue
        if answer.get('native_archive_annual'):
            latest = pending.get('annual')
            if not latest:
                qualified.append(answer)
                continue
        else:
            latest = max(pending.values(), key=lambda state: (state.get('anchor') or {}).get('period_end') or '')
        anchor = latest.get('anchor') or {}
        if answer.get('native_quarter_end') and (anchor.get('period_end') or '') <= answer['native_quarter_end']:
            qualified.append(answer)
            continue
        qualified.append({**answer, 'value': 'New filing · financial facts pending',
                          'context': f"Period ended {anchor.get('period_end')} · {_label(latest.get('reason'))}",
                          'evidence': ('Older observations remain dated history. Review the latest filing for the current period.',),
                          'links': (('Latest SEC filing', anchor['source_url']),) if anchor.get('source_url') else (),
                          'headline': None, 'headline_context': None, 'gap': None})
    return tuple(qualified)


def qualify_peer_view(view, context):
    """Carry current-context holds into every headline and valuation disclosure."""
    qualified = context.get('peer_read_through') or {}
    reason = qualified.get('reason') or ''
    if qualified.get('status') == 'withheld' and (
        reason == 'latest_annual_filing_not_corroborated' or reason.startswith('peer_subject_')
    ):
        return {**view, 'status':'withheld', 'reason':reason, 'subject':None,
                'peers':[], 'peer_count':0, 'peer_median':None, 'premium_fraction':None}
    return view


def _evidence(st, refs):
    if refs:
        st.json(refs, expanded=False)


def _business_trend(st, context):
    trend = context.get('business_trend') or {}
    with st.expander('Business Trend · online reported periods', expanded=False):
        narrative = trend.get('narrative') or []
        if isinstance(narrative, str):
            st.write(narrative)
        else:
            for line in narrative:
                st.write(line)
        metrics = trend.get('metrics') or []
        kinds = tuple(dict.fromkeys(row.get('period_kind') for row in metrics))
        selected = st.selectbox('Trend analysis basis', kinds,
            format_func=lambda value: {'annual':'Annual','quarterly':'Direct quarter','cumulative':'Year to date'}.get(value,value),
            key='online-trend-basis:' + context['profile_key'] + ':' + context['ticker'] + ':' + str(context.get('sec_cik'))) if kinds else None
        subset = [row for row in metrics if row.get('period_kind') == selected]
        latest_end = max((row['period_end'] for row in subset),default=None)
        for row in [row for row in subset if row['period_end'] == latest_end]:
            label = row.get('label') or _label(row.get('key'))
            value = row.get('value')
            if value is None:
                st.caption(f"{label}: {_label(row.get('reason'))}")
                continue
            unit = row.get('unit')
            shown = f'{value * 100:,.1f}%' if unit == 'ratio' else f'{value:,.2f} {_label(unit)}'
            st.write(f"**{label}: {shown}**")
            st.caption(f"{row.get('period_start')} to {row.get('period_end')} · {_label(row.get('basis'))}")
        if not metrics:
            st.caption('Reported periods are needed before trend calculations are available.')
        st.caption('Cash from operations less PP&E spending is descriptive cash generation, not issuer-defined free cash flow or FCFF for valuation. Year-to-date cash flow stays separate from direct quarters.')
        with st.expander('Trend definitions, sources and gaps', expanded=False):
            _evidence(st, metrics)
            for gap in trend.get('gaps') or []:
                st.write(_label(gap))
    components = context.get('earnings_components') or {}
    with st.expander('Earnings quality · reported annual components', expanded=False):
        st.caption('Direct standard SEC concepts from the selected annual filing. Missing adjustments, taxes and issuer-defined reconciliations remain gaps.')
        _evidence(st, components)


def _scenario_result(st, result):
    if result.get('status') != 'calculated':
        st.info('Scenario unavailable: ' + _label(result.get('reason')))
        return
    st.metric('Hypothetical enterprise value', f"{result.get('currency')} {result['enterprise_value']:,.0f}")
    per_share = result.get('value_per_assumed_share')
    if per_share is not None:
        st.metric('Hypothetical value per assumed share', f"{result.get('currency')} {per_share:,.2f}")
    st.caption('An assumption exercise, not a price target. Enterprise value does not establish value for the selected traded share class.')
    with st.expander('Scenario assumptions, projected cash flows and sensitivity', expanded=False):
        _evidence(st, {key: result.get(key) for key in ('assumptions', 'projected_fcfs', 'discounted_fcfs', 'sensitivity', 'gaps', 'input_identity')})


def _scenario(st, context, prefix):
    with st.expander('Scenario Lab · explicit assumptions', expanded=False):
        base = context.get('scenario_base') or {}
        st.caption('Use reported annual revenue as a starting point. Growth and the FCFF margin below are hypothetical assumptions; reported operating cash flow is not treated as FCFF.')
        st.caption('Results use the last calculated assumptions. Recalculate after editing the controls.')
        st.caption(f"Revenue basis: {base['period_start']} to {base['period_end']} · {base['currency']}" if base.get('status') == 'available'
            else 'Revenue basis unavailable: ' + _label(base.get('reason')))
        parameters = {}
        controls = (
            ('revenue_growth', 'Revenue growth assumption (%)', -50., 40., 8.),
            ('fcf_margin', 'FCFF margin assumption (%)', -50., 45., 15.),
            ('wacc', 'Discount rate / WACC (%)', 5., 20., 10.),
            ('terminal_growth', 'Terminal growth assumption (%)', -2., 5., 2.),
        )
        for key, label, low, high, default in controls:
            widget_key = prefix + ':input:' + key
            default_args = {} if widget_key in st.session_state else {'value':default}
            parameters[key] = st.number_input(label, min_value=low, max_value=high,
                step=0.5, key=widget_key, **default_args) / 100
        year_key = prefix + ':input:forecast_years'
        parameters['forecast_years'] = st.number_input('Forecast years', min_value=1, max_value=10,
            step=1, key=year_key, **({} if year_key in st.session_state else {'value':5}))
        debt = shares = basis = None
        if st.checkbox('Add explicit capital structure assumptions', key=prefix + ':input:capital'):
            debt = st.number_input('Assumed net debt (source currency; negative means net cash)',
                value=0., step=1e6, key=prefix + ':input:net_debt')
            shares = st.number_input('Assumed common shares', min_value=0., value=0.,
                step=1e6, key=prefix + ':input:shares')
            basis = st.text_input('Capital structure assumption and share basis', key=prefix + ':input:basis')
            st.caption('These entries are your assumptions, not verified current common-share inputs.')
        if st.button('Calculate hypothetical enterprise value', key=prefix + ':run'):
            st.session_state[prefix + ':result'] = run_online_scenario(
                context, parameters, assumed_net_debt=debt, assumed_shares=shares,
                capital_structure_basis=basis,
            )
            st.rerun()
        result = st.session_state.get(prefix + ':result')
        if isinstance(result, Mapping):
            if result.get('source_revision') != context.get('source_revision'):
                st.warning('Online inputs changed. Rerun the scenario using the new source evidence; your draft assumptions are retained.')
            else:
                _scenario_result(st, result)
        elif base.get('reason'):
            st.info('Scenario base gap: ' + _label(base['reason']))
    peers = context.get('peer_read_through') or {}
    with st.expander('Peer read-through · observed industry references', expanded=False):
        st.caption('Observed annual P/E references and exclusions. Shared industry classification does not prove an economic transmission relationship or future performance.')
        _evidence(st, peers)


def _forward_decision(st, context):
    with st.expander('Forward View and Decision Lab', expanded=False):
        st.caption('Reported trends, explicit hypotheses and your issuer-scoped research records. Filing detections are review triggers, not reviewed catalysts or earnings forecasts.')
        forward = context.get('forward_view') or {}
        decision = context.get('decision_lab') or {}
        if decision.get('next_process_step'):
            st.write('**Next research action:** ' + str(decision['next_process_step']))
        for lane in decision.get('lanes') or []:
            st.write('**' + str(lane.get('label') or _label(lane.get('key'))) + '**')
            st.write(lane.get('answer') or _label(lane.get('state')))
            if lane.get('next_step'):
                st.caption(lane['next_step'])
        st.json({'forward_view': forward, 'research_process': decision}, expanded=False)


def _snapshots(st, context, bundle):
    if _mode_reason('research'):
        st.info('Personal online research replay is unavailable in this workspace.')
        return
    from src.online_research_context_store import save_research_context, list_research_contexts, load_research_context, compare_research_contexts
    with st.expander('Saved online research · replay and compare', expanded=bool(st.query_params.get('research_snapshot'))):
        st.caption('Private normalized observations, assumptions and notes. Replay is dated history; refresh explicitly for current online research. Source permissions remain unchanged.')
        cik = context.get('sec_cik')
        if not cik:
            st.caption('A matched issuer identity is required to save and replay research.')
            st.button('Save research snapshot', key='online-research-save', disabled=True)
            return
        scope = _scope(context)
        matched = bundle['financial'].get('companyfacts_identity', {}).get('status') == 'source_matched'
        try:
            if st.button('Save research snapshot', key='online-research-save', disabled=not matched):
                saved = save_research_context(context, **scope, project_root=PROJECT_ROOT)
                st.success('Research snapshot saved: ' + saved['snapshot_id'][:12])
            snapshots = list_research_contexts(**scope, project_root=PROJECT_ROOT)
            requested = st.query_params.get('research_snapshot')
            if requested:
                historical = load_research_context(requested, **scope, project_root=PROJECT_ROOT)
                st.info('Historical replay · ' + historical['observed_at'])
                trend = historical['context'].get('business_trend') or {}
                comparisons = trend.get('comparative_periods') or []
                if comparisons:
                    from src.sec_online_quarter_view import native_quarter_comparisons_html
                    current_quarter = next(row for row in trend['periods']
                        if row.get('current') is True and row.get('period_basis') == 'direct_quarter')
                    st.markdown(native_quarter_comparisons_html(current_quarter, comparisons,
                                trend.get('comparative_gaps')), unsafe_allow_html=True)
                _evidence(st, historical['context'])
            if not snapshots:
                st.caption('No saved online research in this exact company scope.')
                return
            labels = {r['snapshot_id']: f"{r['observed_at']} · {r['snapshot_id'][:12]}" for r in snapshots}
            selected = st.selectbox('Replay saved research', tuple(labels), format_func=labels.get,
                key='online-research-replay:' + scope['profile_key'] + ':' + scope['ticker'] + ':' + cik)
            if st.button('Open historical research snapshot', key='online-research-replay-open'):
                st.query_params['research_snapshot'] = selected
                st.query_params['research_cik'] = cik
                st.rerun()
            if len(snapshots) >= 2:
                comparison = compare_research_contexts(snapshots[1], snapshots[0])
                st.write('**Latest saved comparison:** ' + _label(comparison.get('status')))
                _evidence(st, comparison)
            current = compare_research_contexts(snapshots[0], context)
            st.caption('Current versus latest saved: ' + _label(current.get('status')))
            _evidence(st, current)
            from src.research_workspace import open_research_monitor
            st.button('Open Monitor', key='online-research-open-monitor',
                on_click=open_research_monitor,args=(st,scope['ticker'],scope['profile_key']))
        except (OSError, ValueError, TypeError, UnicodeError):
            st.warning('Saved research could not be verified in this exact profile and issuer scope. No other company snapshot was substituted.')


def render_online_tools(st, section, bundle):
    if _mode_reason('research'):
        st.info('Personal online research tools are unavailable in this workspace.')
        return
    context = bundle['research_context']
    if section == 'financials':
        _business_trend(st, context)
    elif section == 'valuation':
        _scenario(st, context, bundle['online_scenario_key'])
    elif section == 'notes':
        _forward_decision(st, context)
        _snapshots(st, context, bundle)
    elif section == 'sources':
        with st.expander('Latest SEC filings and structured-data coverage', expanded=True):
            st.json({key: context.get(key) for key in ('filing_inventory', 'filing_coverage', 'source_receipts', 'gaps')}, expanded=False)


def render_online_research_monitor(st, *, profile_key):
    if _mode_reason('research'):
        st.info('Personal online research snapshots are unavailable in this workspace.')
        return
    from src.online_research_context_store import list_research_context_scopes, list_research_contexts, compare_research_contexts
    st.markdown('### Saved online research updates')
    st.caption('Private company-context snapshots, separate from the saved SEC evidence review counts. Monitor checks saved observations; use Research company for new online filings.')
    try:
        index = list_research_context_scopes(profile_key, project_root=PROJECT_ROOT)
        if index.get('errors'):
            st.warning('Some saved research could not be verified; those records are excluded.')
        scopes = index.get('scopes') or []
        if not scopes:
            st.caption('No online research snapshots saved in this profile.')
            return
        labels = {f"{r['ticker']} · CIK {r['sec_cik']}": r for r in scopes}
        choice = st.selectbox('Saved online research company', tuple(labels), key='online-research-monitor:' + profile_key)
        scope = labels[choice]
        snapshots = list_research_contexts(profile_key=profile_key, ticker=scope['ticker'],
            sec_cik=scope['sec_cik'], project_root=PROJECT_ROOT)
        latest = snapshots[0]
        st.caption('Latest observation: ' + latest['observed_at'])
        if len(snapshots) >= 2:
            st.write('Latest pair: ' + _label(compare_research_contexts(snapshots[1], latest)['status']))
        for gap in latest['context'].get('gaps') or []:
            st.write(_label(gap))
        query = dict(mode='research', page='company-workbench', ticker=scope['ticker'],
            section='notes', research_cik=scope['sec_cik'], research_snapshot=latest['snapshot_id'])
        st.button('Reopen exact saved research', key='online-research-monitor-open:' + profile_key,
            on_click=st.query_params.from_dict, args=(query,))
    except (OSError, ValueError, TypeError, UnicodeError, IndexError):
        st.warning('Online research snapshots could not be verified. Existing SEC review and company notes remain separate.')
