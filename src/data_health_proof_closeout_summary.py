from __future__ import annotations

import re

import pandas as pd

from src.data_health_proof_ctas import data_health_operator_lane_url


COMPLETE_CLOSEOUT_STATES = {"supported", "still_blocked", "skipped", "excluded"}


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


def proof_closeout_summary_frame(
    dcf_closeout: pd.DataFrame | None,
    peer_closeout: pd.DataFrame | None,
) -> pd.DataFrame:
    columns = [
        "Proof Lane",
        "Closeout Status",
        "Latest Outcome",
        "Comparison Status",
        "Evidence Remaining",
        "Next Safest Action",
        "Lane URL",
        "Closeout Boundary",
    ]

    def _row(lane: str, lane_url: str, frame: pd.DataFrame | None, fallback_action: str) -> dict[str, object]:
        if frame is None or frame.empty:
            return {
                "Proof Lane": lane,
                "Closeout Status": "not_loaded",
                "Latest Outcome": "not_recorded",
                "Comparison Status": "not_loaded",
                "Evidence Remaining": "Open the lane drawer to build closeout evidence.",
                "Next Safest Action": fallback_action,
                "Lane URL": lane_url,
                "Closeout Boundary": "Closeout rows are data-readiness proof states only, not recommendations.",
            }
        first = frame.iloc[0]
        return {
            "Proof Lane": lane,
            "Closeout Status": _format_missing(first.get("Closeout Status"), "not_recorded"),
            "Latest Outcome": _format_missing(first.get("Latest Outcome"), "not_recorded"),
            "Comparison Status": _format_missing(first.get("Comparison Status"), "deferred"),
            "Evidence Remaining": _compact_fragment(
                first.get("Evidence Remaining"),
                fallback="Open the lane drawer to review evidence gates.",
                max_chars=220,
            ),
            "Next Safest Action": _format_missing(first.get("Next Safest Action"), fallback_action),
            "Lane URL": lane_url,
            "Closeout Boundary": _format_missing(
                first.get("Closeout Boundary"),
                "Closeout rows are data-readiness proof states only, not recommendations.",
            ),
        }

    return pd.DataFrame(
        [
            _row(
                "DCF proof closeout",
                data_health_operator_lane_url("fundamentals"),
                dcf_closeout,
                "make dcf-input-proof-queue TOP_N=10",
            ),
            _row(
                "Peer proof closeout",
                data_health_operator_lane_url("peers"),
                peer_closeout,
                "make peer-mapping-source-review TOP_N=10",
            ),
        ],
        columns=columns,
    )


def proof_closeout_summary_cards(
    dcf_closeout: pd.DataFrame | None,
    peer_closeout: pd.DataFrame | None,
) -> list[dict[str, object]]:
    summary = proof_closeout_summary_frame(dcf_closeout, peer_closeout)
    if summary.empty:
        return [
            {
                "kicker": "PROOF CLOSEOUT",
                "title": "No closeout lanes loaded",
                "body": "Open DCF or Peer drawers to review proof closeout status.",
                "badges": ["blocked visible", "research-only"],
                "command": data_health_operator_lane_url("fundamentals"),
            }
        ]
    status_series = summary["Closeout Status"].fillna("not_recorded").astype(str).str.lower()
    complete = status_series.isin(COMPLETE_CLOSEOUT_STATES)
    needs_review = summary.loc[~complete]
    focus = needs_review.iloc[0] if not needs_review.empty else summary.iloc[0]
    if needs_review.empty:
        title = "2 proof lane(s) have closeout states"
        badges = ["closeout visible", "proof states only"]
    else:
        title = f"{len(needs_review)} proof lane(s) need closeout review"
        badges = ["closeout review", "blocked visible"]
    ordered_statuses = list(dict.fromkeys(status_series.tolist()))
    counts = "; ".join(f"{status}: {int((status_series == status).sum())}" for status in ordered_statuses)
    return [
        {
            "kicker": "PROOF CLOSEOUT",
            "title": title,
            "body": (
                f"{_card_sentence('Closeout states', counts)} "
                f"{_card_sentence('Next lane', focus.get('Proof Lane'))} "
                f"{_card_sentence('Evidence remaining', _compact_fragment(focus.get('Evidence Remaining'), max_chars=190))} "
                "Closeout is data-readiness evidence, not analysis or recommendation output."
            ),
            "badges": badges,
            "command": _format_missing(focus.get("Lane URL"), data_health_operator_lane_url("fundamentals")),
        }
    ]
