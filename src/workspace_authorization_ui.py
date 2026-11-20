"""Compose protected research routes after server-side workspace authorization."""
from dataclasses import replace
from hashlib import sha256

from src.workspace_authorization import WorkspaceAccessDenied, selected_workspace_session


def render_workspace_route(st, *, page, mode):
    from src import dashboard
    from src.profile_context import build_profile_context
    from src.research_workspace import (
        research_monitor_origin, resolve_saved_monitor_origin,
        research_monitor_return_link, return_to_research_workbench,
    )

    if not st.query_params.get('mode') and not st.query_params.get('page'):
        page, mode = 'Research Desk', 'research'
        st.query_params.from_dict({'mode': mode, 'page': 'research-desk'})
    try:
        session = selected_workspace_session()
        if mode != 'research' or page not in {'Research Desk', 'Discover', 'Company Workbench', 'Monitor'}:
            raise WorkspaceAccessDenied('workspace_route_unavailable')
    except WorkspaceAccessDenied:
        st.session_state.clear()
        st.markdown('## Workspace access unavailable')
        st.caption('Sign in with an active membership for this workspace.')
        st.button('Sign in', on_click=st.login)
        return

    binding = (session.principal_id, session.workspace_id, session.profile_key)
    if st.session_state.get('authorized-workspace-binding') != binding:
        st.session_state.clear()
        st.session_state['authorized-workspace-binding'] = binding
    workspace = session.storage_root / 'workspaces' / sha256(session.workspace_id.encode()).hexdigest()
    # Workspace model paths and private research records have independent roots.
    # No shared personal model, journal or event ledger is adopted here.
    context = replace(build_profile_context(project_root=dashboard.BASE_DIR,
        data_dir=workspace / 'data', output_dir=workspace / 'outputs'),
        profile_key=session.profile_key, profile_label='Workspace')
    origin = None
    ticker = str(st.query_params.get('ticker') or '').strip().upper()
    if page == 'Monitor':
        ticker = str(st.query_params.get('return_ticker') or '').strip().upper()
        pinned = any(key.startswith('return_research_') for key in st.query_params)
        if pinned:
            origin = resolve_saved_monitor_origin(st.query_params, session.profile_key, ticker,
                previous=st.session_state.get('research_monitor_origin'))
        else:
            origin = research_monitor_origin(st.session_state, session.profile_key, ticker)
        if origin is not None:
            st.session_state['research_monitor_origin'] = origin
        else:
            for key in tuple(st.query_params):
                if key.startswith('return_'):
                    del st.query_params[key]
            st.session_state.pop('research_monitor_origin', None)
            ticker = ''
    dashboard.render_research_workspace_styles()
    dashboard.render_research_workflow_navigation(page, ticker=ticker,
        monitor_profile_key=session.profile_key if page == 'Company Workbench' else '',
        monitor_origin=origin)
    if page == 'Company Workbench':
        dashboard.render_company_workbench(None, context, {}, None)
    elif page == 'Monitor':
        st.markdown('## Monitor')
        if origin is not None:
            st.button(research_monitor_return_link(ticker, origin=origin)['label'],
                key='monitor-return-to-workbench', on_click=return_to_research_workbench, args=(st, origin))
        from src.company_research_notes_ui import render_company_notes_monitor
        from src.online_research_tools_ui import render_online_research_monitor
        from src.sec_research_review_ui import render_review_monitor

        render_review_monitor(st, profile_key=session.profile_key, monitor_origin=origin)
        render_company_notes_monitor(st, profile_key=session.profile_key, monitor_origin=origin)
        render_online_research_monitor(st, profile_key=session.profile_key, monitor_origin=origin)
    else:
        st.markdown('## ' + page)
        dashboard.render_online_company_search(saved_tickers=())
        st.caption('Open Monitor to review saved workspace research.')
