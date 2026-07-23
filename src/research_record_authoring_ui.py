"""Streamlit composer for append-only reviewed research records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.research_record_authoring import (
    AuthoringPaths,
    AuthoringPreview,
    authoring_draft_digest,
    build_authoring_draft,
    confirm_authoring_preview,
    preview_authoring_record,
)
from src.catalyst_evidence_timeline import load_catalyst_events
from src.research_outcome_review import load_outcomes
from src.research_thesis_journal import load_journal_entries


FIELD_CONTRACTS = {
    "thesis": (
        "thesis_id",
        "summary",
        "effective_at",
        "reviewer",
        "confidence",
        "review_due_date",
        "supersedes_entry_id",
    ),
    "evidence": (
        "thesis_id",
        "summary",
        "effective_at",
        "reviewer",
        "evidence_direction",
        "source",
        "source_ref",
        "source_published_at",
    ),
    "catalyst": (
        "event_type",
        "title",
        "summary",
        "effective_at",
        "published_at",
        "retrieved_at",
        "source",
        "source_ref",
        "evidence_state",
        "reviewer",
    ),
    "outcome": (
        "thesis_id",
        "original_thesis_entry_id",
        "reviewed_at",
        "observation_start",
        "observation_end",
        "reviewer",
        "outcome_state",
        "summary",
        "source",
        "source_ref",
        "source_published_at",
        "learning",
    ),
}

SELECT_OPTIONS = {
    "evidence_direction": ("supporting", "conflicting", "context"),
    "event_type": (
        "earnings",
        "product",
        "regulatory",
        "customer",
        "industry",
        "capital_allocation",
        "management",
        "macro",
    ),
    "evidence_state": (
        "candidate_context_only",
        "supported",
        "still_blocked",
        "skipped",
        "excluded",
    ),
    "outcome_state": ("supported", "mixed", "not_supported", "inconclusive"),
}


def authoring_field_contract(record_kind: str) -> tuple[str, ...]:
    """Return the immutable input fields for one persisted record kind."""

    try:
        return FIELD_CONTRACTS[record_kind]
    except KeyError as exc:
        raise ValueError(f"Unsupported record kind: {record_kind!r}") from exc


def authoring_session_key(profile_key: str, ticker: str, suffix: str) -> str:
    """Namespace transient widgets by their locked Company Workbench scope."""

    return f"research-authoring:{profile_key}:{ticker.upper()}:{suffix}"


def _generated_id(kind: str) -> str:
    return f"{kind}-{uuid4().hex}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _scoped_thesis_options(
    paths: AuthoringPaths, profile_key: str, ticker: str
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (row.thesis_id, row.entry_id)
        for row in load_journal_entries(paths.journal)
        if row.entry_type == "thesis"
        and row.profile_key == profile_key
        and row.ticker.upper() == ticker.upper()
    )


def _field_label(name: str) -> str:
    return name.replace("_", " ").title()


def _render_field(
    st_api: Any,
    *,
    name: str,
    kind: str,
    profile_key: str,
    ticker: str,
    thesis_options: tuple[tuple[str, str], ...],
    current_fields: dict[str, str],
) -> str:
    key = authoring_session_key(profile_key, ticker, f"field:{kind}:{name}")
    label = _field_label(name)
    if name == "thesis_id" and kind in {"evidence", "outcome"}:
        return st_api.selectbox(
            label,
            tuple(dict.fromkeys(thesis_id for thesis_id, _ in thesis_options)),
            key=key,
        )
    if name == "original_thesis_entry_id":
        selected_thesis_id = current_fields.get("thesis_id", "")
        return st_api.selectbox(
            label,
            tuple(entry_id for thesis_id, entry_id in thesis_options if thesis_id == selected_thesis_id),
            key=key,
        )
    if name == "supersedes_entry_id":
        return st_api.selectbox(
            label,
            ("", *(entry_id for _, entry_id in thesis_options)),
            key=key,
        )
    if name in SELECT_OPTIONS:
        return st_api.selectbox(label, SELECT_OPTIONS[name], key=key)
    if name in {"summary", "learning"}:
        return st_api.text_area(label, key=key)
    return st_api.text_input(label, key=key)


def _render_preview(st_api: Any, preview: AuthoringPreview) -> None:
    st_api.markdown("#### Exact append-only preview")
    st_api.caption(
        f"Destination: {preview.destination_label} | Previewed at: {preview.previewed_at}"
    )
    st_api.dataframe(
        [{"Field": name, "Value": value} for name, value in preview.persisted_fields],
        width="stretch",
        hide_index=True,
    )
    st_api.caption(
        "Research-only record. Corrections require a new append-only record; history is never edited or deleted."
    )


def _show_reloaded_save_receipt(
    st_api: Any, *, profile_key: str, ticker: str, paths: AuthoringPaths
) -> None:
    """Show one save receipt only after its persisted record is read back."""

    symbol = ticker.upper()
    receipt_key = authoring_session_key(profile_key, symbol, "pending-reload-receipt")
    receipt = st_api.session_state.get(receipt_key)
    if receipt is None:
        return
    del st_api.session_state[receipt_key]
    if not isinstance(receipt, dict):
        st_api.warning("Saved record could not be reloaded; review the ledger")
        return
    record_kind = str(receipt.get("record_kind") or "").strip().lower()
    record_id = str(receipt.get("record_id") or "").strip()
    try:
        if record_kind in {"thesis", "evidence"}:
            record_reloaded = any(
                entry.entry_id == record_id
                and entry.profile_key == profile_key
                and entry.ticker.upper() == symbol
                for entry in load_journal_entries(paths.journal)
            )
        elif record_kind == "catalyst":
            record_reloaded = any(
                event.event_id == record_id
                and event.profile_key == profile_key
                and event.ticker.upper() == symbol
                for event in load_catalyst_events(paths.catalysts)
            )
        elif record_kind == "outcome":
            record_reloaded = any(
                outcome.outcome_id == record_id
                and outcome.profile_key == profile_key
                and outcome.ticker.upper() == symbol
                for outcome in load_outcomes(paths.outcomes)
            )
        else:
            record_reloaded = False
    except (OSError, UnicodeError, ValueError):
        record_reloaded = False
    if record_reloaded:
        st_api.success(
            f"Saved {record_id}. Corrections require a new append-only record; history is never edited or deleted."
        )
    else:
        st_api.warning("Saved record could not be reloaded; review the ledger")


def render_research_record_authoring(
    *, st_api: Any, profile_key: str, ticker: str, paths: AuthoringPaths
) -> None:
    """Render a locked-scope, preview-first authoring composer without direct writes."""

    symbol = ticker.upper()
    _show_reloaded_save_receipt(
        st_api,
        profile_key=profile_key,
        ticker=symbol,
        paths=paths,
    )
    with st_api.expander("Add a reviewed research record", expanded=False):
        st_api.markdown(
            f"Profile: {profile_key} | Ticker: {symbol} — locked to this Company Workbench."
        )
        kind = st_api.selectbox(
            "Record type",
            tuple(FIELD_CONTRACTS),
            format_func=str.title,
            key=authoring_session_key(profile_key, symbol, "kind"),
        )
        thesis_options: tuple[tuple[str, str], ...] = ()
        if kind in {"thesis", "evidence", "outcome"}:
            try:
                thesis_options = _scoped_thesis_options(paths, profile_key, symbol)
            except (OSError, ValueError) as exc:
                st_api.error(f"Thesis references could not be loaded; no record can be saved: {exc}")
                return
        if kind in {"evidence", "outcome"} and not thesis_options:
            st_api.warning(
                "This record type requires an existing thesis in this locked profile and ticker. "
                "Add and confirm a thesis first."
            )
            return

        fields: dict[str, str] = {}
        for name in authoring_field_contract(kind):
            fields[name] = _render_field(
                st_api,
                name=name,
                kind=kind,
                profile_key=profile_key,
                ticker=symbol,
                thesis_options=thesis_options,
                current_fields=fields,
            )
        draft = build_authoring_draft(
            kind, profile_key=profile_key, ticker=symbol, fields=fields
        )
        preview_key = authoring_session_key(profile_key, symbol, "preview")
        if st_api.button(
            "Validate and preview",
            key=authoring_session_key(profile_key, symbol, "validate"),
            use_container_width=True,
        ):
            st_api.session_state[preview_key] = preview_authoring_record(
                draft,
                paths=paths,
                previewed_at=_utc_now(),
                generated_id=_generated_id(kind),
            )
        preview: AuthoringPreview | None = st_api.session_state.get(preview_key)
        if preview is None:
            st_api.caption(
                "No record is saved until this draft passes preview and you confirm the exact reviewed source evidence."
            )
            return
        if preview.draft_digest != authoring_draft_digest(draft):
            st_api.warning(
                "Draft changed after preview. Validate and preview again before saving."
            )
            return
        if preview.state == "rejected":
            st_api.error(preview.reason)
            return

        _render_preview(st_api, preview)
        confirmed = st_api.checkbox(
            "I reviewed this exact record and its source evidence",
            key=authoring_session_key(profile_key, symbol, "confirmed"),
        )
        if st_api.button(
            "Confirm and save",
            key=authoring_session_key(profile_key, symbol, "save"),
            use_container_width=True,
        ):
            result = confirm_authoring_preview(
                preview,
                current_draft=draft,
                paths=paths,
                active_profile_key=profile_key,
                active_ticker=symbol,
                active_kind=kind,
                confirm_reviewed=confirmed,
            )
            if result.state == "saved":
                del st_api.session_state[preview_key]
                st_api.session_state[
                    authoring_session_key(profile_key, symbol, "pending-reload-receipt")
                ] = {"record_kind": result.record_kind, "record_id": result.record_id}
                st_api.rerun()
            else:
                st_api.error(result.reason)
