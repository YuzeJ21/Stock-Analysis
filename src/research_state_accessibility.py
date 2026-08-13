"""Accessible, visible messages for user-triggered research-state transitions."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html import escape


_STATE_SEMANTICS = {
    "validation_rejected": ("alert", "assertive"),
    "preview_ready": ("status", "polite"),
    "draft_changed": ("status", "polite"),
    "save_reloaded": ("status", "polite"),
    "save_reload_unverified": ("alert", "assertive"),
}


@dataclass(frozen=True)
class ResearchStateMessage:
    state: str
    title: str
    detail: str
    role: str
    live: str
    message_id: str


def _required_text(value: object, *, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "scope"


def research_state_message(
    state: str,
    *,
    scope: str,
    title: str,
    detail: str,
    identity: str,
) -> ResearchStateMessage:
    """Build one deterministic message from the closed transition contract."""

    normalized_state = _required_text(state, name="state").lower()
    try:
        role, live = _STATE_SEMANTICS[normalized_state]
    except KeyError as exc:
        raise ValueError(f"Unsupported research transition state: {normalized_state!r}") from exc

    normalized_scope = _required_text(scope, name="scope")
    normalized_title = _required_text(title, name="title")
    normalized_identity = _required_text(identity, name="identity")
    identity_digest = hashlib.sha256(normalized_identity.encode("utf-8")).hexdigest()[:16]
    message_id = (
        f"research-state-{_slug(normalized_scope)}-"
        f"{normalized_state.replace('_', '-')}-{identity_digest}"
    )
    return ResearchStateMessage(
        state=normalized_state,
        title=normalized_title,
        detail=str(detail or "").strip(),
        role=role,
        live=live,
        message_id=message_id,
    )


def research_state_message_html(
    message: ResearchStateMessage,
    *,
    announce: bool = True,
) -> str:
    """Render one visible message, optionally as an atomic live region."""

    message_id = escape(message.message_id, quote=True)
    title = escape(message.title, quote=True)
    detail = escape(message.detail, quote=True)
    if announce:
        semantics = (
            f"role='{escape(message.role, quote=True)}' "
            f"aria-live='{escape(message.live, quote=True)}' aria-atomic='true'"
        )
    else:
        semantics = "role='group'"
    return (
        f"<div id='{message_id}' class='research-state-message' {semantics}>"
        f"<strong class='research-state-message__title'>{title}</strong>"
        f"<div class='research-state-message__detail'>{detail}</div>"
        "</div>"
    )


def research_state_transition_key(message: ResearchStateMessage) -> str:
    """Return the stable deduplication key for an exact transition identity."""

    return message.message_id
