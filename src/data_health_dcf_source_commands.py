from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment
from src.dcf_input_proof_queue import DcfInputProofRow, build_dcf_input_source_command_plan


def dcf_source_command_plan_frame(rows: list[DcfInputProofRow], family: str | None = None) -> pd.DataFrame:
    plan = build_dcf_input_source_command_plan(rows, family=family)
    return pd.DataFrame(
        [
            {
                "Step": row.step,
                "Status": row.status,
                "Command": row.command,
                "Fields To Fill": row.fields_to_fill,
                "Review Boundary": row.review_boundary,
            }
            for row in plan
        ]
    )


def dcf_source_command_plan_cards(plan: pd.DataFrame | None, family: str | None = None) -> list[dict[str, object]]:
    family_label = str(family or "top family").strip() or "top family"
    if plan is None or plan.empty:
        return [
            {
                "kicker": "DCF COMMAND PLAN",
                "title": "No DCF source command plan available",
                "body": "Refresh the DCF input queue before building source-review, guard, validation, and proof commands.",
                "badges": ["copy-only", "blocked visible"],
                "command": "make dcf-input-proof-queue TOP_N=10",
            }
        ]
    first_blocker = plan.loc[
        plan["Status"].fillna("").astype(str).str.lower().str.contains("blocked|needs", regex=True)
    ]
    focus = first_blocker.iloc[0] if not first_blocker.empty else plan.iloc[0]
    source_command = (
        f"make dcf-input-source-command-plan FAMILY={family_label} TOP_N=10"
        if family_label != "top family"
        else "make dcf-input-source-command-plan TOP_N=10"
    )
    return [
        {
            "kicker": "DCF COMMAND PLAN",
            "title": f"{family_label}: source review to proof handoff",
            "body": (
                f"{len(plan):,} copy-only step(s). "
                f"{card_sentence('Next blocked step', focus.get('Step'))} "
                f"{card_sentence('Fields to fill', compact_card_fragment(focus.get('Fields To Fill'), max_chars=180))} "
                "Use this command path before opening raw source-review or import-preview tables."
            ),
            "badges": ["copy-only", "validate then preview"],
            "command": source_command,
        }
    ]
