"""Pure coverage frontier and expansion-loop helpers for Data Health.

The dashboard should render these rows and cards, while this module owns the
read-only coverage operations copy: frontier ranking, expansion-loop gates,
proof boundaries, and generated-artifact hygiene language.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.readiness_ops import ReadinessLane, build_coverage_frontier


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


def _compact_fragment(
    value: object,
    fallback: str = "Not available",
    *,
    max_sentences: int = 1,
    max_chars: int = 180,
) -> str:
    text = _format_missing(value, fallback).replace("\n", " ").strip()
    if text == fallback:
        return text
    sentences = [part.strip() for part in text.split(". ") if part.strip()]
    compact = ". ".join(sentences[:max_sentences]) if sentences else text
    if compact and not compact.endswith((".", "?", "!")):
        compact += "."
    if len(compact) > max_chars:
        compact = compact[: max(0, max_chars - 1)].rstrip() + "..."
    if compact.endswith("..."):
        return compact
    return compact.rstrip(" .;:")


def _card_sentence(label: str, fragment: str) -> str:
    clean_label = label.strip().rstrip(":")
    clean_fragment = _format_missing(fragment, "Not available").strip()
    terminal = "" if clean_fragment.endswith((".", "?", "!", "...")) else "."
    return f"{clean_label}: {clean_fragment}{terminal}"


def coverage_frontier_frame_from_lanes(lanes: list[ReadinessLane], *, top_n: int = 10) -> pd.DataFrame:
    frontier = build_coverage_frontier(lanes, top_n=top_n)
    rows = [
        {
            "Rank": row.rank,
            "Lane": row.label,
            "Unlock Impact": row.unlock_impact,
            "Possible State Move": row.possible_state_move,
            "Source Lane": row.source_lane,
            "Workflow Mode": row.workflow_mode,
            "Next Safe Command": row.next_safe_command,
            "Proof Command": row.proof_command,
            "Generated Churn Policy": row.generated_churn_policy,
            "Guardrail": row.guardrail,
        }
        for row in frontier
    ]
    return pd.DataFrame(rows)


def coverage_frontier_cards(frontier_frame: pd.DataFrame | None, *, limit: int = 3) -> list[dict[str, object]]:
    if frontier_frame is None or frontier_frame.empty:
        return [
            {
                "kicker": "COVERAGE FRONTIER",
                "title": "No batch frontier rows yet",
                "body": (
                    "Refresh the coverage frontier after readiness outputs exist. "
                    "The frontier ranks data operations, not securities; open operator details for read-only proof steps."
                ),
                "badges": ["read-only", "not a ranking"],
                "command": "make coverage-frontier TOP_N=10",
            }
        ]
    cards: list[dict[str, object]] = []
    for _, row in frontier_frame.head(max(limit, 0)).iterrows():
        lane = _format_missing(row.get("Lane"), "Coverage lane")
        impact = _format_missing(row.get("Unlock Impact"), "0")
        move = _compact_fragment(row.get("Possible State Move"), max_chars=180).replace("->", "to")
        guardrail = _compact_fragment(row.get("Guardrail"), max_chars=170)
        command = _format_missing(row.get("Next Safe Command"), "make coverage-frontier TOP_N=10")
        cards.append(
            {
                "kicker": f"FRONTIER #{_format_missing(row.get('Rank'), '-')}",
                "title": lane,
                "body": (
                    f"Impact: {impact} coverage rows. "
                    f"{_card_sentence('Path', move)} "
                    f"{_card_sentence('Guardrail', guardrail)}"
                ),
                "badges": [_format_missing(row.get("Workflow Mode"), "review"), "batch lane"],
                "command": command,
            }
        )
    return cards


def coverage_expansion_loop_cards(loop: Any) -> list[dict[str, object]]:
    if loop.status == "blocked_missing_lane":
        return [
            {
                "kicker": "EXPANSION LOOP",
                "title": "Pick a planner lane first",
                "body": (
                    "The coverage planner did not return a matching lane. Rebuild readiness, open the planner, "
                    "then choose a listed lane before packet or dry-run work."
                ),
                "badges": ["planner first", "blocked"],
                "command": "make data-coverage-planner TOP_N=10",
            }
        ]
    if loop.status == "ready_for_reviewed_dry_run":
        title = "Coverage loop ready"
        badges = ["ready", "dry-run first"]
        command = loop.preflight.packet_command if loop.preflight is not None else "make coverage-expansion-loop TOP_N=10"
    else:
        title = "Coverage loop blocked by preflight"
        badges = ["preflight", "fix first"]
        command = (
            loop.preflight.snapshot_command
            if loop.preflight is not None and not loop.preflight.prior_snapshot_exists
            else "make coverage-expansion-loop TOP_N=10"
        )
    return [
        {
            "kicker": "EXPANSION LOOP",
            "title": title,
            "body": (
                f"{loop.selected_label}: {_compact_fragment(loop.next_safe_action, max_chars=210)} "
                "This is the compact planner -> preflight -> packet -> proof path; full copy-only steps stay in the review drawer."
            ),
            "badges": badges + [loop.reviewed_batch_lane],
            "command": command,
        }
    ]


def coverage_expansion_loop_frame(loop: Any) -> pd.DataFrame:
    planner_step = loop.planner_step
    preflight = loop.preflight
    return pd.DataFrame(
        [
            {
                "Step": "Status",
                "Value": loop.status,
                "Command": loop.copy_only_sequence[0] if loop.copy_only_sequence else "make coverage-expansion-loop TOP_N=10",
                "Stop If": "; ".join(loop.do_not_proceed_if[:3]),
            },
            {
                "Step": "Planner gate",
                "Value": planner_step.review_gate if planner_step is not None else "No matching planner lane",
                "Command": planner_step.next_safe_command if planner_step is not None else "make data-coverage-planner TOP_N=10",
                "Stop If": planner_step.stop_condition if planner_step is not None else "planner lane is missing",
            },
            {
                "Step": "Preflight gate",
                "Value": preflight.status if preflight is not None else "missing",
                "Command": preflight.packet_command if preflight is not None else "make reviewed-batch-preflight",
                "Stop If": preflight.do_not_proceed_if[0] if preflight is not None and preflight.do_not_proceed_if else "preflight unavailable",
            },
            {
                "Step": "Proof boundary",
                "Value": "Record supported only after source proof, validation, preview/apply decision, rebuilt readiness, comparison, and artifact review.",
                "Command": (
                    f"DRY_RUN=1 {preflight.proof_record_command}"
                    if preflight is not None
                    else "DRY_RUN=1 make reviewed-batch-proof-record"
                ),
                "Stop If": "generated CSV/JSON churn is not classified or source proof is missing",
            },
        ]
    )
