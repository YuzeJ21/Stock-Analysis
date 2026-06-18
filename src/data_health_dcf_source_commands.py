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


def dcf_source_command_triage_frame(plan: pd.DataFrame | None) -> pd.DataFrame:
    columns = ["Triage Bucket", "Count", "Next Safe Action", "Review Boundary"]
    if plan is None or plan.empty:
        return pd.DataFrame(
            [
                {
                    "Triage Bucket": "blocked_no_plan",
                    "Count": 1,
                    "Next Safe Action": "make dcf-input-proof-queue TOP_N=10",
                    "Review Boundary": "Refresh the DCF input queue before source-review triage.",
                }
            ],
            columns=columns,
        )
    work = plan.copy()
    statuses = work.get("Status", pd.Series("", index=work.index)).fillna("").astype(str).str.lower()
    fields = work.get("Fields To Fill", pd.Series("", index=work.index)).fillna("").astype(str)
    buckets = [
        {
            "Triage Bucket": "needs_source_fields",
            "mask": statuses.str.contains("needs|blocked_until_reviewed_fields", regex=True),
            "Next Safe Action": _first_command(work, statuses.str.contains("needs|blocked_until_reviewed_fields", regex=True)),
            "Review Boundary": f"Fill exact source fields first: {_field_summary(fields.loc[statuses.str.contains('needs|blocked_until_reviewed_fields', regex=True)])}.",
        },
        {
            "Triage Bucket": "ready_for_guard_or_validate",
            "mask": statuses.str.contains("ready_for_guard|copy_only_after_guard|copy_only_after_validate", regex=True),
            "Next Safe Action": _first_command(work, statuses.str.contains("ready_for_guard|copy_only_after_guard|copy_only_after_validate", regex=True)),
            "Review Boundary": "Run guard, validate, and preview only after reviewed source fields replace placeholders.",
        },
        {
            "Triage Bucket": "manual_apply_boundary",
            "mask": statuses.str.contains("manual_review_boundary", regex=True),
            "Next Safe Action": _first_command(work, statuses.str.contains("manual_review_boundary", regex=True)),
            "Review Boundary": "Apply remains a reviewed/manual boundary; do not use it to fabricate DCF readiness.",
        },
        {
            "Triage Bucket": "proof_handoff_ready_after_review",
            "mask": statuses.str.contains("dry_run_first|copy_only_after_apply_or_skip", regex=True),
            "Next Safe Action": _first_command(work, statuses.str.contains("dry_run_first|copy_only_after_apply_or_skip", regex=True)),
            "Review Boundary": "Record proof only after rebuilt readiness, comparison, source files, and artifact review.",
        },
    ]
    rows = []
    for bucket in buckets:
        mask = bucket.pop("mask")
        count = int(mask.sum())
        if count:
            rows.append({"Count": count, **bucket})
    if not rows:
        rows.append(
            {
                "Triage Bucket": "review_required",
                "Count": len(work),
                "Next Safe Action": _first_command(work, pd.Series(True, index=work.index)),
                "Review Boundary": "Review source commands and keep missing inputs blocked unless proof exists.",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def dcf_source_command_triage_cards(triage: pd.DataFrame | None, family: str | None = None) -> list[dict[str, object]]:
    family_label = str(family or "top family").strip() or "top family"
    if triage is None or triage.empty:
        return [
            {
                "kicker": "DCF SOURCE TRIAGE",
                "title": "No DCF source triage available",
                "body": "Build the DCF source command plan before reviewing source outcomes.",
                "badges": ["blocked visible", "readiness first"],
                "command": "make dcf-input-source-command-plan TOP_N=10",
            }
        ]
    top = triage.iloc[0]
    bucket_summary = "; ".join(
        f"{str(row.get('Triage Bucket')).replace('_', ' ')}: {int(row.get('Count', 0))}"
        for _, row in triage.iterrows()
    )
    return [
        {
            "kicker": "DCF SOURCE TRIAGE",
            "title": f"{family_label}: {bucket_summary}",
            "body": (
                f"{card_sentence('Next safest action', top.get('Next Safe Action'))} "
                f"{card_sentence('Review boundary', compact_card_fragment(top.get('Review Boundary'), max_chars=190))} "
                "Use this summary to decide whether to fill fields, run the guard, validate/preview, or stop."
            ),
            "badges": ["source fields first", "no fabricated unlocks"],
            "command": str(top.get("Next Safe Action") or "make dcf-input-source-command-plan TOP_N=10"),
        }
    ]


def _first_command(frame: pd.DataFrame, mask: pd.Series) -> str:
    matches = frame.loc[mask]
    if matches.empty or "Command" not in matches.columns:
        return "make dcf-input-source-command-plan TOP_N=10"
    return str(matches.iloc[0].get("Command") or "make dcf-input-source-command-plan TOP_N=10")


def _field_summary(values: pd.Series) -> str:
    fields: list[str] = []
    for value in values:
        for part in str(value or "").replace("|", ",").replace(";", ",").split(","):
            field = part.strip()
            if field and field not in fields:
                fields.append(field)
    return ", ".join(fields[:8]) if fields else "reviewed source fields"
