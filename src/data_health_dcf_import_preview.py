from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing
from src.dcf_input_proof_queue import build_dcf_input_source_guard


def dcf_import_preview_frame(source_frame: pd.DataFrame | None, input_family: object = "") -> pd.DataFrame:
    if source_frame is None or source_frame.empty:
        guard = build_dcf_input_source_guard(ticker="", input_family=format_missing(input_family, ""))
    else:
        first = source_frame.iloc[0]
        guard = build_dcf_input_source_guard(
            ticker=format_missing(first.get("Ticker"), ""),
            input_family=format_missing(first.get("Input Family"), ""),
            missing_dcf_fields=format_missing(first.get("Missing DCF Fields"), ""),
            period=format_missing(first.get("Period"), ""),
            revenue=format_missing(first.get("Revenue"), ""),
            free_cash_flow=format_missing(first.get("Free Cash Flow"), ""),
            fcf_margin=format_missing(first.get("FCF Margin"), ""),
            shares_outstanding=format_missing(first.get("Shares Outstanding"), ""),
            source_type=format_missing(first.get("Source Type"), ""),
            source_file_or_url=format_missing(first.get("Source File Or URL"), ""),
            source_as_of_date=format_missing(first.get("Source As Of Date"), ""),
            reviewer=format_missing(first.get("Reviewer"), ""),
            review_date=format_missing(first.get("Review Date"), ""),
            source_proof_status=format_missing(first.get("Source Proof Status"), ""),
            validation_result=format_missing(first.get("Validation Result"), ""),
            preview_result=format_missing(first.get("Preview Result"), ""),
            apply_decision=format_missing(first.get("Apply Decision"), ""),
        )
    return pd.DataFrame(
        [
            {
                "Step": "1. Guard status",
                "Status": guard.status,
                "Command Or Value": "make dcf-input-source-guard ...",
                "Review Boundary": ", ".join(guard.blocking_reasons) if guard.blocking_reasons else "reviewed fields complete",
            },
            {
                "Step": "2. Import header",
                "Status": "preview",
                "Command Or Value": guard.csv_header,
                "Review Boundary": "Header only; do not edit canonical data from this preview.",
            },
            {
                "Step": "3. Import row",
                "Status": "ready" if guard.csv_row else "blocked",
                "Command Or Value": guard.csv_row or "blocked until reviewed fields are complete",
                "Review Boundary": "Use only after reviewed source fields and guard status are ready.",
            },
            {
                "Step": "4. Validate",
                "Status": "copy-only",
                "Command Or Value": guard.validation_command,
                "Review Boundary": "Validation must pass before preview or apply decisions count as proof.",
            },
            {
                "Step": "5. Preview",
                "Status": "copy-only",
                "Command Or Value": guard.preview_command,
                "Review Boundary": "Preview and rejected-row reports must be reviewed before any apply step.",
            },
            {
                "Step": "6. Apply boundary",
                "Status": "manual reviewed boundary",
                "Command Or Value": guard.apply_boundary,
                "Review Boundary": "No automatic imports; missing DCF inputs stay blocked until reviewed.",
            },
            {
                "Step": "7. Post-apply proof",
                "Status": "copy-only",
                "Command Or Value": guard.post_apply_proof,
                "Review Boundary": "Rebuild readiness and report before any supported proof outcome.",
            },
        ]
    )


def dcf_import_preview_cards(preview: pd.DataFrame | None) -> list[dict[str, object]]:
    if preview is None or preview.empty:
        return [
            {
                "kicker": "DCF IMPORT PREVIEW",
                "title": "No import preview available",
                "body": "Open the DCF source-review intake before previewing any fundamentals import row.",
                "badges": ["copy-only", "blocked visible"],
                "command": "make dcf-input-source-review TOP_N=10",
            }
        ]
    status = format_missing(preview.iloc[0].get("Status"), "blocked")
    blockers = compact_card_fragment(preview.iloc[0].get("Review Boundary"), max_chars=190)
    row_status = format_missing(preview.iloc[2].get("Status"), "blocked") if len(preview) > 2 else "blocked"
    return [
        {
            "kicker": "DCF IMPORT PREVIEW",
            "title": f"Fundamentals row preview: {row_status}",
            "body": (
                f"Guard status: {status}. "
                f"{card_sentence('Blocking fields', blockers)} "
                "Header, row, validate, preview, apply boundary, and post-apply proof stay together here."
            ),
            "badges": ["validate", "preview before apply"],
            "command": "make dcf-input-source-guard ...",
        }
    ]
