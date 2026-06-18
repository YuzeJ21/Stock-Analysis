from __future__ import annotations

import re

import pandas as pd


BLOCKING_STATUS_PATTERN = re.compile(r"blocked|missing|deferred|warning|needs|not_loaded|no_source")


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


def _compact_fragment(value: object, fallback: str = "Not available", *, max_chars: int = 180) -> str:
    text = _format_missing(value, fallback).replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "..."
    if text.endswith("..."):
        return text
    return text.rstrip(" .;:")


def _card_sentence(label: str, fragment: object) -> str:
    clean_label = label.strip().rstrip(":")
    clean_fragment = _format_missing(fragment, "Not available").strip()
    terminal = "" if clean_fragment.endswith((".", "?", "!", "...")) else "."
    return f"{clean_label}: {clean_fragment}{terminal}"


def proof_outcome_cards_from_frame(
    outcome: pd.DataFrame | None,
    *,
    kicker: str,
    empty_title: str,
    empty_body: str,
    empty_badges: list[str],
    empty_command: str,
    latest_title_prefix: str,
    decision_sentence: str,
    badges: list[str],
    fallback_command: str,
    status_max_chars: int = 220,
) -> list[dict[str, object]]:
    if outcome is None or outcome.empty:
        return [
            {
                "kicker": kicker,
                "title": empty_title,
                "body": empty_body,
                "badges": empty_badges,
                "command": empty_command,
            }
        ]

    statuses = ", ".join(f"{row['Proof Loop Step']}: {row['Status']}" for _, row in outcome.iterrows())
    latest = outcome.iloc[-1]
    blockers = outcome.loc[
        outcome["Status"].fillna("").astype(str).str.lower().str.contains(BLOCKING_STATUS_PATTERN, regex=True)
    ]
    focus = blockers.iloc[0] if not blockers.empty else latest
    return [
        {
            "kicker": kicker,
            "title": f"{latest_title_prefix}: {_format_missing(latest.get('Status'), 'not_recorded')}",
            "body": (
                f"{_compact_fragment(statuses, max_chars=status_max_chars)}. "
                f"{_card_sentence('Next proof gate', focus.get('Proof Loop Step'))} "
                f"{decision_sentence}"
            ),
            "badges": badges,
            "command": _format_missing(focus.get("Next Safe Action"), fallback_command),
        }
    ]
