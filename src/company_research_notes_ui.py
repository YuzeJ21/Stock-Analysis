"""Saved user research notes and follow-ups independent of company model inputs."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from src.catalyst_evidence_timeline import load_catalyst_events
from src.company_research_notes import (
    CompanyNotesScope,
    load_company_notes,
    notes_index,
    notes_paths,
    notes_query,
    legacy_note_tickers,
)
from src.research_outcome_review import load_outcomes
from src.research_record_authoring import AuthoringPaths
from src.research_record_authoring_ui import render_research_record_authoring
from src.research_thesis_journal import derive_journal_state, load_journal_entries


_READ_ERRORS = (OSError, ValueError, UnicodeError, csv.Error)
_STORE_GAP = (
    "Saved company notes could not be verified. Retain the saved files and check the "
    "notes folder before adding another record."
)


def _legacy_records(paths, profile_key, ticker):
    if not isinstance(paths, AuthoringPaths):
        raise ValueError("Invalid legacy research paths")
    for value in paths.all():
        path = Path(value)
        if path.is_symlink() or (
            path.exists() and not path.is_file()
        ):
            raise ValueError("Legacy research file could not be verified")
    return tuple(
        tuple(row for row in loader(path) if row.profile_key == profile_key and row.ticker.upper() == ticker)
        for loader, path in (
            (load_journal_entries, paths.journal),
            (load_catalyst_events, paths.catalysts),
            (load_outcomes, paths.outcomes),
        )
    )


def _note_state(journal, profile_key, ticker):
    return derive_journal_state(
        journal, profile_key=profile_key, ticker=ticker,
        as_of=datetime.now(UTC).isoformat(),
    )


def _render_summary(st, state):
    if state.current_thesis is None:
        st.caption("No thesis saved for this company note scope.")
    else:
        st.markdown("**Latest thesis**")
        st.text(state.current_thesis.summary)
    st.caption("Review due: " + (state.review_due_date or "Not recorded"))


def _render_history(st, journal, catalysts, outcomes):
    with st.expander("Note history", expanded=False):
        if not journal:
            st.caption("No thesis or evidence history saved.")
        for row in journal:
            st.caption(f"{row.entry_type.title()} · {row.recorded_at} · {row.entry_id}")
            st.text(row.summary)
            if row.source_ref:
                st.text(f"Source: {row.source} · {row.source_ref}")
    with st.expander("Catalyst notes", expanded=False):
        if not catalysts:
            st.caption("No catalyst notes saved.")
        for row in catalysts:
            st.text(row.title)
            st.caption(f"{row.effective_at} · User-recorded evidence state: {row.evidence_state}")
            st.text(row.summary)
            st.text(f"Source: {row.source} · {row.source_ref}")
    with st.expander("Outcome notes", expanded=False):
        if not outcomes:
            st.caption("No outcome notes saved.")
        for row in outcomes:
            st.caption(f"{row.reviewed_at} · User-recorded outcome: {row.outcome_state}")
            st.text(row.summary)
            st.text(row.learning)
            st.text(f"Source: {row.source} · {row.source_ref}")


def render_company_notes(
    st, *, profile_key, ticker, scope=None, legacy_paths=None,
):
    """Read an exact saved note scope and retain explicit preview/confirm authoring."""

    symbol = str(ticker or "").strip().upper()
    if (
        (scope is None) == (legacy_paths is None)
        or scope is not None and (
            not isinstance(scope, CompanyNotesScope)
            or scope.profile_key != profile_key or scope.ticker != symbol
        )
    ):
        st.warning("The requested company note scope does not match this profile and ticker.")
        return
    try:
        if scope is not None:
            loaded = load_company_notes(scope)
            paths = notes_paths(scope)
            journal, catalysts, outcomes = loaded.journal, loaded.catalysts, loaded.outcomes
        else:
            paths = legacy_paths
            journal, catalysts, outcomes = _legacy_records(paths, profile_key, symbol)
        state = _note_state(journal, profile_key, symbol)
    except _READ_ERRORS:
        st.warning(_STORE_GAP)
        return

    st.markdown("### Your company notes")
    if scope is not None:
        st.caption(
            f"{symbol} · CIK {scope.sec_cik} · Profile: {profile_key}. "
            "This is a saved note identity, not proof of a current listing."
        )
    else:
        st.caption(f"{symbol} · Profile: {profile_key} · Existing saved research journal.")
    st.caption(
        "User-authored research records. Notes do not verify source evidence, "
        "change source permissions, or complete company model inputs."
    )
    _render_summary(st, state)
    _render_history(st, journal, catalysts, outcomes)
    render_research_record_authoring(
        st_api=st, profile_key=profile_key, ticker=symbol, paths=paths,
        **({"identity_scope": scope.sec_cik} if scope is not None else {}),
    )


def render_company_notes_monitor(st, *, profile_key, monitor_origin=None,legacy_paths=None):
    """Show user-authored follow-ups separately from saved SEC evidence counts."""

    st.markdown("### User-authored follow-ups")
    st.caption(
        "Saved company notes in this profile. These are user records, "
        "separate from saved SEC evidence and its company counts."
    )
    try:
        index = notes_index(profile_key)
    except _READ_ERRORS:
        st.warning(_STORE_GAP)
        return
    if index.errors:
        st.warning(
            "Some saved company notes could not be verified and are excluded from "
            "this list. Other saved notes remain available."
        )
    scopes = {
        f"{scope.ticker} · CIK {scope.sec_cik}": scope
        for scope in index.scopes if scope.profile_key == profile_key
    }
    legacy_symbols={}
    if legacy_paths is not None:
        try:
            legacy_symbols={f'{ticker} · saved workspace':ticker for ticker in legacy_note_tickers(legacy_paths,profile_key)}
        except _READ_ERRORS:
            st.warning('Existing saved-workspace notes could not be verified. Online issuer notes remain separate.')
    options=tuple(scopes)+tuple(legacy_symbols)
    if not options:
        st.caption("No saved company notes in this profile.")
        return
    label = st.selectbox(
        "Saved company notes", options, key="company-notes-monitor:" + profile_key,
    )
    scope = scopes.get(label)
    ticker=scope.ticker if scope else legacy_symbols[label]
    try:
        journal=(load_company_notes(scope).journal if scope else _legacy_records(legacy_paths,profile_key,ticker)[0])
        state = _note_state(journal, profile_key, ticker)
    except _READ_ERRORS:
        st.warning(_STORE_GAP)
        return
    _render_summary(st, state)
    st.caption((f"CIK {scope.sec_cik} identifies these saved notes. " if scope else
        'These are ticker-scoped saved-workspace records, without a verified current issuer association. ')+
        'Opening them does not refresh listing information or load a company model.')
    query=notes_query(scope) if scope else dict(mode='research',page='company-workbench',ticker=ticker,section='notes')
    st.button(
        f"Open {ticker} notes", key="company-notes-monitor-open:" + profile_key,
        on_click=st.query_params.from_dict, args=(query,),
    )
