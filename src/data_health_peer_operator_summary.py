from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment
from src.peer_mapping_source_review import PeerMappingSourceReviewPacket


SUMMARY_COLUMNS = ["Question", "Status", "Answer", "Next Safe Action", "Boundary"]


def peer_operator_summary_frame(
    packet: PeerMappingSourceReviewPacket | None,
    checklist: pd.DataFrame | None,
    outcome: pd.DataFrame | None,
) -> pd.DataFrame:
    if packet is None:
        return pd.DataFrame(
            [
                {
                    "Question": "Where am I?",
                    "Status": "missing_packet",
                    "Answer": "Peer source-review packet is not loaded.",
                    "Next Safe Action": "make readiness && make peer-mapping-source-review TOP_N=10",
                    "Boundary": "Rebuild readiness and source-review rows before planning peer proof.",
                }
            ],
            columns=SUMMARY_COLUMNS,
        )

    checklist_frame = checklist if checklist is not None else pd.DataFrame()
    outcome_frame = outcome if outcome is not None else pd.DataFrame()
    blocking = checklist_frame.loc[
        ~_column(checklist_frame, "Status").astype(str).str.lower().isin(
            {"current", "fresh", "ready_for_validate_preview", "copy_only_gate", "ready_for_review_fields", "supported"}
        )
    ] if not checklist_frame.empty else pd.DataFrame()
    current = blocking.iloc[0] if not blocking.empty else (
        checklist_frame.iloc[-1] if not checklist_frame.empty else pd.Series(dtype=object)
    )
    latest_rows = (
        outcome_frame.loc[_column(outcome_frame, "Proof Loop Step").eq("Latest peer ledger outcome")]
        if not outcome_frame.empty
        else pd.DataFrame()
    )
    latest = latest_rows.iloc[0] if not latest_rows.empty else pd.Series(dtype=object)
    tickers = ", ".join(packet.tickers[:10]) if packet.tickers else "no selected peer tickers"
    source_rows = len(packet.rows)
    return pd.DataFrame(
        [
            {
                "Question": "What is selected?",
                "Status": _text(packet.freshness.status, "unknown"),
                "Answer": f"{source_rows:,} peer source-review slot(s); tickers: {compact_card_fragment(tickers, max_chars=180)}.",
                "Next Safe Action": f"DRY_RUN=1 make peer-mapping-source-review TOP_N={packet.top_n}",
                "Boundary": "Peer source review plans reviewed rows only; it does not infer comparable companies.",
            },
            {
                "Question": "What is the current gate?",
                "Status": _text(current.get("Status"), "blocked"),
                "Answer": (
                    f"{_text(current.get('Checklist Item'), 'Finish peer proof')}: "
                    f"{compact_card_fragment(current.get('Need Before Proceeding'), max_chars=210)}"
                ),
                "Next Safe Action": _text(current.get("Next Safest Action"), "make peer-mapping-source-review TOP_N=10"),
                "Boundary": _text(current.get("Stop Rule"), "Keep peer valuation blocked until source-backed proof is reviewed."),
            },
            {
                "Question": "What proof exists?",
                "Status": _text(latest.get("Status"), "not_recorded"),
                "Answer": compact_card_fragment(
                    latest.get("Detail"),
                    fallback="No peer reviewed batch proof row recorded yet.",
                    max_chars=220,
                ),
                "Next Safe Action": _text(latest.get("Next Safe Action"), "make reviewed-batch-proof"),
                "Boundary": "Latest ledger outcome is readiness proof only; it is not a ranking, recommendation, or trading instruction.",
            },
            {
                "Question": "When must I stop?",
                "Status": "stop_rule",
                "Answer": "Stop if source proof, write-back guard, validation, preview, explicit apply/skip decision, rebuilt readiness, source files, changed counts, or generated-artifact review is missing.",
                "Next Safe Action": "Keep peer mapping still_blocked or skipped until reviewed proof exists.",
                "Boundary": "No peer-relative valuation unlock and no supported proof outcome without source-backed review.",
            },
        ],
        columns=SUMMARY_COLUMNS,
    )


def peer_operator_summary_cards(summary: pd.DataFrame | None) -> list[dict[str, object]]:
    if summary is None or summary.empty:
        return [
            {
                "kicker": "PEER OPERATOR SUMMARY",
                "title": "No peer proof summary loaded",
                "body": "Build the peer source-review packet before opening source-review, guard, validation, proof-record, or ledger details.",
                "badges": ["blocked visible", "no inferred peers"],
                "command": "make peer-mapping-source-review TOP_N=10",
            }
        ]
    current_rows = summary.loc[summary["Question"].astype(str).eq("What is the current gate?")]
    stop_rows = summary.loc[summary["Question"].astype(str).eq("When must I stop?")]
    current = current_rows.iloc[0] if not current_rows.empty else summary.iloc[0]
    stop = stop_rows.iloc[0] if not stop_rows.empty else summary.iloc[-1]
    return [
        {
            "kicker": "PEER OPERATOR SUMMARY",
            "title": f"Current gate: {_text(current.get('Status'), 'blocked')}",
            "body": (
                f"{card_sentence('Need', compact_card_fragment(current.get('Answer'), max_chars=210))} "
                f"{card_sentence('Boundary', compact_card_fragment(current.get('Boundary'), max_chars=190))} "
                "Use this first-read summary before lower peer source tables."
            ),
            "badges": ["first read", "source-backed only"],
            "command": _text(current.get("Next Safe Action"), "make peer-mapping-source-review TOP_N=10"),
        },
        {
            "kicker": "STOP RULE",
            "title": "Keep peer valuation locked",
            "body": compact_card_fragment(stop.get("Answer"), max_chars=260),
            "badges": ["no inferred peers", "research-only"],
            "command": _text(stop.get("Next Safe Action"), "Keep peer mapping still_blocked until proof is reviewed."),
        },
    ]


def _text(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        return pd.Series("", index=frame.index)
    return frame[name].fillna("")
