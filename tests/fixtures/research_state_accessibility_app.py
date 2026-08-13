import streamlit as st

from src.research_state_accessibility import (
    research_state_message,
    research_state_message_html,
    research_state_transition_key,
)


STATIC_STATES = (
    (
        "loading",
        "Loading saved TEST1 research state. No data is being refreshed or changed.",
        " aria-busy='true'",
    ),
    ("empty", "No reviewed TEST1 evidence is recorded.", ""),
    ("withheld", "TEST1 output is withheld until its evidence gate passes.", ""),
    ("stale", "TEST1 remains historical or review-only because its saved evidence is stale.", ""),
    ("failure", "TEST1 evidence could not be verified; inspect the saved source before continuing.", ""),
    ("validation", "TEST1 validation has not run.", ""),
)

TRANSITIONS = (
    (
        "validation_rejected",
        "Validation rejected",
        "TEST1 required evidence is missing.",
    ),
    (
        "preview_ready",
        "Preview ready",
        "This exact TEST1 record is ready for review and is not saved.",
    ),
    (
        "draft_changed",
        "Draft changed",
        "Validate and preview the edited TEST1 draft again before saving.",
    ),
    (
        "save_reloaded",
        "Record saved",
        "Saved TEST1-record. Corrections require a new append-only record.",
    ),
    (
        "save_reload_unverified",
        "Save verification incomplete",
        "TEST1 could not be reloaded; inspect the ledger before another save.",
    ),
)


st.title("Synthetic research-state accessibility harness")
for state, detail, attributes in STATIC_STATES:
    st.html(
        f"<div id='state-{state}' data-research-static-state='{state}' "
        f"role='group'{attributes}><strong>TEST1 {state}</strong>"
        f"<div>{detail}</div></div>"
    )

for state, title, detail in TRANSITIONS:
    if st.button(
        title,
        key=f"transition-{state.replace('_', '-')}",
    ):
        st.session_state["selected-transition"] = state

selected_state = st.session_state.get("selected-transition")
if selected_state:
    title, detail = next(
        (title, detail)
        for state, title, detail in TRANSITIONS
        if state == selected_state
    )
    message = research_state_message(
        selected_state,
        scope="fixture:TEST1:research-state",
        title=title,
        detail=detail,
        identity=f"fixture-{selected_state}-1",
    )
    transition_key = research_state_transition_key(message)
    last_key = st.session_state.get("last-transition-key")
    st.html(
        research_state_message_html(
            message,
            announce=last_key != transition_key,
        )
    )
    st.session_state["last-transition-key"] = transition_key
