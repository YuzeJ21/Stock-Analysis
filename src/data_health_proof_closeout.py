from __future__ import annotations

import re

import pandas as pd


FINAL_CLOSEOUT_STATES = {"supported", "still_blocked", "skipped", "excluded"}
OPEN_GATE_PATTERN = re.compile(r"blocked|missing|deferred|warning|needs|not_loaded|no_source")


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


def proof_closeout_frame_from_outcome(
    outcome: pd.DataFrame | None,
    *,
    latest_step: str,
    empty_evidence: str,
    empty_action: str,
    empty_boundary: str,
    fallback_action: str,
    complete_action: str,
    record_action: str,
    record_evidence: str,
    boundary: str,
) -> pd.DataFrame:
    columns = [
        "Closeout Status",
        "Latest Outcome",
        "Comparison Status",
        "Evidence Remaining",
        "Next Safest Action",
        "Closeout Boundary",
    ]
    if outcome is None or outcome.empty:
        return pd.DataFrame(
            [
                {
                    "Closeout Status": "not_loaded",
                    "Latest Outcome": "not_recorded",
                    "Comparison Status": "not_loaded",
                    "Evidence Remaining": empty_evidence,
                    "Next Safest Action": empty_action,
                    "Closeout Boundary": empty_boundary,
                }
            ],
            columns=columns,
        )

    latest_rows = outcome.loc[outcome["Proof Loop Step"].eq(latest_step)]
    comparison_rows = outcome.loc[outcome["Proof Loop Step"].eq("Before / after readiness comparison")]
    latest_status = (
        _format_missing(latest_rows.iloc[0].get("Status"), "not_recorded").lower()
        if not latest_rows.empty
        else "not_recorded"
    )
    comparison_status = (
        _format_missing(comparison_rows.iloc[0].get("Status"), "deferred").lower()
        if not comparison_rows.empty
        else "deferred"
    )
    gate_mask = outcome["Proof Loop Step"].ne(latest_step) & outcome["Status"].fillna("").astype(str).str.lower().str.contains(
        OPEN_GATE_PATTERN,
        regex=True,
    )
    open_gates = outcome.loc[gate_mask]
    if latest_status in FINAL_CLOSEOUT_STATES:
        closeout_status = latest_status
    elif latest_status in {"not_recorded", "not available", ""}:
        closeout_status = "not_recorded"
    else:
        closeout_status = f"review_{latest_status}"

    if not open_gates.empty:
        evidence = "; ".join(
            f"{row.get('Proof Loop Step')}: {_compact_fragment(row.get('Detail'), max_chars=110)}"
            for _, row in open_gates.head(3).iterrows()
        )
        next_action = _format_missing(open_gates.iloc[0].get("Next Safe Action"), fallback_action)
    elif latest_status in FINAL_CLOSEOUT_STATES:
        evidence = "No open source, comparison, or proof-record gates in this closeout view."
        next_action = complete_action
    else:
        evidence = record_evidence
        next_action = record_action

    return pd.DataFrame(
        [
            {
                "Closeout Status": closeout_status,
                "Latest Outcome": latest_status,
                "Comparison Status": comparison_status,
                "Evidence Remaining": evidence,
                "Next Safest Action": next_action,
                "Closeout Boundary": boundary,
            }
        ],
        columns=columns,
    )


def proof_closeout_cards_from_frame(
    closeout: pd.DataFrame | None,
    *,
    kicker: str,
    empty_title: str,
    empty_body: str,
    empty_badges: list[str],
    empty_command: str,
    fallback_command: str,
) -> list[dict[str, object]]:
    if closeout is None or closeout.empty:
        return [
            {
                "kicker": kicker,
                "title": empty_title,
                "body": empty_body,
                "badges": empty_badges,
                "command": empty_command,
            }
        ]
    row = closeout.iloc[0]
    status = _format_missing(row.get("Closeout Status"), "not_recorded")
    return [
        {
            "kicker": kicker,
            "title": f"Closeout status: {status}",
            "body": (
                f"{_card_sentence('Latest outcome', row.get('Latest Outcome'))} "
                f"{_card_sentence('Comparison', row.get('Comparison Status'))} "
                f"{_card_sentence('Evidence remaining', _compact_fragment(row.get('Evidence Remaining'), max_chars=200))} "
                "Closeout describes proof state only."
            ),
            "badges": ["proof state", "no advice"],
            "command": _format_missing(row.get("Next Safest Action"), fallback_command),
        }
    ]
