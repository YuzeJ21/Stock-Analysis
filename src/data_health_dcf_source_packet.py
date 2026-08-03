from __future__ import annotations

import pandas as pd

from src.data_health_dcf_input_family import dcf_input_family_key, filter_dcf_input_queue_by_family
from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing


def dcf_source_route(row: pd.Series) -> str:
    family = format_missing(row.get("Missing Input Family"), "")
    mode = format_missing(row.get("Source Mode"), "").lower()
    if family == "price" or "price" in mode:
        return "Price dry-run path"
    if "sec-stageable" in mode:
        return "SEC-stageable"
    return "Trusted-local/manual"


def dcf_source_packet_frame(frame: pd.DataFrame | None, selection: object) -> pd.DataFrame:
    columns = [
        "Source Route",
        "Input Family",
        "Rows",
        "Tickers",
        "Blocking Inputs",
        "Source Target",
        "Stage Or Review Command",
        "Trusted Local Path",
        "Validation Gate",
        "Proof Packet Command",
        "Stop Rule",
    ]
    if frame is None or frame.empty:
        return pd.DataFrame(columns=columns)
    work = filter_dcf_input_queue_by_family(frame, selection)
    if work.empty:
        return pd.DataFrame(columns=columns)
    groups: dict[tuple[str, str], list[pd.Series]] = {}
    for _, row in work.iterrows():
        family = format_missing(row.get("Missing Input Family"), "DCF input")
        route = dcf_source_route(row)
        groups.setdefault((route, family), []).append(row)
    rows: list[dict[str, object]] = []
    for (route, family), items in groups.items():
        tickers = [format_missing(item.get("Ticker"), "").upper() for item in items if format_missing(item.get("Ticker"), "")]
        ticker_arg = ",".join(tickers[:10]) if tickers else "<reviewed_tickers>"
        first = items[0]
        if route == "Price dry-run path":
            stage_command = f"DRY_RUN=1 make reviewed-batch LANE=prices TICKERS={ticker_arg}"
            trusted_path = "data/imports/prices.csv after price validate/preview"
            source_target = "verified OHLCV rows or reviewed provider refresh"
        elif route == "SEC-stageable":
            stage_command = f"make sec-stage TICKERS={ticker_arg}"
            trusted_path = "data/imports/fundamentals.csv fallback after reviewed source rows"
            source_target = "SEC Companyfacts staging or reviewed company filing"
        else:
            stage_command = f"make dcf-input-source-review FAMILY={family} TOP_N=10"
            trusted_path = "data/imports/fundamentals.csv with reviewed local source rows"
            source_target = "trusted filing/report source supplied by reviewer"
        blocking_inputs = "; ".join(
            dict.fromkeys(compact_card_fragment(item.get("Missing DCF Fields"), max_chars=80) for item in items)
        )
        rows.append(
            {
                "Source Route": route,
                "Input Family": family,
                "Rows": len(items),
                "Tickers": ticker_arg,
                "Blocking Inputs": blocking_inputs,
                "Source Target": source_target,
                "Stage Or Review Command": stage_command,
                "Trusted Local Path": trusted_path,
                "Validation Gate": format_missing(first.get("Validation Sequence"), "make imports-validate -> make imports-preview"),
                "Proof Packet Command": format_missing(first.get("Proof Packet Command"), "DRY_RUN=1 make fundamentals-batch-proof"),
                "Stop Rule": format_missing(first.get("Stop Rule"), "Stop if source proof does not support the required DCF input."),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def dcf_source_packet_cards(frame: pd.DataFrame | None, selection: object) -> list[dict[str, object]]:
    packet = dcf_source_packet_frame(frame, selection)
    family = dcf_input_family_key(selection) or "selected DCF inputs"
    if packet.empty:
        return [
            {
                "kicker": "DCF SOURCE PACKET",
                "title": "No source route selected",
                "body": "Open the DCF input proof queue before choosing SEC staging or trusted-local source review.",
                "badges": ["source route", "blocked visible"],
                "command": "make dcf-input-proof-queue TOP_N=10",
            }
        ]
    routes = ", ".join(f"{row['Source Route']}: {row['Rows']}" for _, row in packet.iterrows())
    first = packet.iloc[0]
    return [
        {
            "kicker": "DCF SOURCE PACKET",
            "title": f"{family}: {routes}",
            "body": (
                f"{card_sentence('First route', first.get('Source Route'))} "
                f"{card_sentence('Tickers', first.get('Tickers'))} "
                f"{card_sentence('Source target', first.get('Source Target'))} "
                "Choose SEC staging only when configured and source-backed; otherwise use trusted-local review with validate, preview, rejected-row review, and proof after update."
            ),
            "badges": ["source first", "validate before apply"],
            "command": format_missing(first.get("Stage Or Review Command"), "make dcf-input-source-review TOP_N=10"),
        }
    ]


def batch_proof_record_scaffold(*, lane: str, tickers: list[str], command_run: str) -> str:
    ticker_text = ",".join(tickers) if tickers else "<reviewed_tickers>"
    assignments = {
        "BATCH_ID": "<reviewed_batch_id>",
        "LANE": lane,
        "REVIEW_DATE": "<yyyy-mm-dd>",
        "FINAL_OUTCOME": "<supported|candidate_context_only|still_blocked|skipped|excluded>",
        "TICKERS": ticker_text,
        "COMMAND_RUN": command_run,
        "VALIDATION_RESULT": "<reviewed_validation_result>",
        "PREVIEW_RESULT": "<reviewed_preview_result>",
        "APPLY_RESULT": "<reviewed_apply_result>",
        "CHANGED_READINESS_COUNTS": "<from_reviewed_batch_compare>",
        "CHANGED_TICKERS": "<from_reviewed_batch_compare>",
        "SOURCE_FILES": "<reviewed_source_files>",
        "GENERATED_ARTIFACTS_REVIEWED": "<kept_evidence_or_excluded_churn>",
    }
    values = " ".join(f"{name}='{value}'" for name, value in assignments.items())
    return f"DRY_RUN=1 make reviewed-batch-proof-record {values}"


def fundamentals_batch_review_queue_frame(
    frame: pd.DataFrame | None,
    selection: object,
    *,
    batch_size: int = 10,
) -> pd.DataFrame:
    columns = [
        "Batch Route",
        "Batch Scope",
        "Tickers",
        "Expected Source Fields",
        "Source Files",
        "Dry Run Or Stage Command",
        "Validation Gate",
        "Preview Gate",
        "Rejected Row Check",
        "Apply Boundary",
        "Post-Run Proof",
        "Proof Record Readiness",
        "Proof Record Scaffold",
        "Stop Rule",
    ]
    packet = dcf_source_packet_frame(frame, selection)
    if packet.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    cap = max(batch_size, 1)
    for _, item in packet.iterrows():
        route = format_missing(item.get("Source Route"), "Trusted-local/manual")
        family = format_missing(item.get("Input Family"), "fundamentals")
        ticker_text = format_missing(item.get("Tickers"), "")
        tickers = [ticker.strip().upper() for ticker in ticker_text.split(",") if ticker.strip()]
        selected = tickers[:cap] or ["<reviewed_ticker>"]
        selected_arg = ",".join(selected)
        lane = "share_count" if family == "shares_outstanding" else "prices" if route == "Price dry-run path" else "fundamentals"
        expected_fields = format_missing(item.get("Blocking Inputs"), family)
        if route == "Price dry-run path":
            source_files = "data/imports/prices.csv or reviewed provider refresh log"
            stage_command = f"DRY_RUN=1 make reviewed-batch LANE=prices TICKERS={selected_arg}"
            validation_gate = "make price-validate"
            preview_gate = "make price-preview"
            rejected_check = "review price rejected-row report if generated"
            apply_boundary = "Apply/import price rows only after dry-run scope, validation, preview, and artifact review."
            post_run = f"make readiness-snapshot PROFILE=<default|demo|local> && make price-validate && make price-preview && make price-apply && make reviewed-batch-compare PROFILE=<default|demo|local> LANE=prices BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd> && make stock-report-md TICKER={selected[0]}"
        elif route == "SEC-stageable":
            source_files = "data/staged/fundamentals/ plus data/imports/fundamentals.csv after review"
            stage_command = f"make sec-stage TICKERS={selected_arg}"
            validation_gate = f"make imports-validate IMPORT_TICKERS={selected_arg}"
            preview_gate = f"make imports-preview IMPORT_TICKERS={selected_arg}"
            rejected_check = "review data/rejected/fundamentals_import_rejected.csv"
            apply_boundary = "Apply only reviewed SEC/manual fundamentals rows after preview and rejected-row review."
            post_run = f"make readiness-snapshot PROFILE=<default|demo|local> && make imports-validate IMPORT_TICKERS={selected[0]} && make imports-preview IMPORT_TICKERS={selected[0]} && make imports-apply IMPORT_TICKERS={selected[0]} && make dcf-readiness && make reviewed-batch-compare PROFILE=<default|demo|local> LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd> && make stock-report-md TICKER={selected[0]}"
        else:
            source_files = "data/imports/fundamentals.csv with reviewer-provided filing/report source"
            stage_command = f"make dcf-input-source-review FAMILY={family} TOP_N={cap}"
            validation_gate = f"make imports-validate IMPORT_TICKERS={selected_arg}"
            preview_gate = f"make imports-preview IMPORT_TICKERS={selected_arg}"
            rejected_check = "review data/rejected/fundamentals_import_rejected.csv"
            apply_boundary = "Apply only source-backed trusted-local rows after preview and rejected-row review."
            post_run = f"make readiness-snapshot PROFILE=<default|demo|local> && make imports-validate IMPORT_TICKERS={selected[0]} && make imports-preview IMPORT_TICKERS={selected[0]} && make imports-apply IMPORT_TICKERS={selected[0]} && make dcf-readiness && make reviewed-batch-compare PROFILE=<default|demo|local> LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd> && make stock-report-md TICKER={selected[0]}"
        proof_scaffold = batch_proof_record_scaffold(
            lane=lane,
            tickers=selected,
            command_run=f"{stage_command} && {validation_gate} && {preview_gate}",
        )
        rows.append(
            {
                "Batch Route": route,
                "Batch Scope": f"{family}: {min(len(tickers) or 1, cap)} of {len(tickers) or 1}",
                "Tickers": selected_arg,
                "Expected Source Fields": expected_fields,
                "Source Files": source_files,
                "Dry Run Or Stage Command": stage_command,
                "Validation Gate": validation_gate,
                "Preview Gate": preview_gate,
                "Rejected Row Check": rejected_check,
                "Apply Boundary": apply_boundary,
                "Post-Run Proof": post_run,
                "Proof Record Readiness": "needs_reviewed_results",
                "Proof Record Scaffold": proof_scaffold,
                "Stop Rule": format_missing(item.get("Stop Rule"), "Stop if source proof does not support the required DCF input."),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def fundamentals_batch_review_queue_cards(frame: pd.DataFrame | None, selection: object) -> list[dict[str, object]]:
    queue = fundamentals_batch_review_queue_frame(frame, selection)
    if queue.empty:
        return [
            {
                "kicker": "FUNDAMENTALS BATCH REVIEW",
                "title": "No reviewed batch route selected",
                "body": "Select a DCF source packet before preparing SEC-stageable or trusted-local batch proof.",
                "badges": ["source first", "blocked visible"],
                "command": "make dcf-input-proof-queue TOP_N=10",
            }
        ]
    routes = ", ".join(f"{row['Batch Route']}: {row['Batch Scope']}" for _, row in queue.iterrows())
    first = queue.iloc[0]
    return [
        {
            "kicker": "FUNDAMENTALS BATCH REVIEW",
            "title": f"{len(queue):,} source route(s) ready for review",
            "body": (
                f"{compact_card_fragment(routes, max_chars=180)}. "
                f"{card_sentence('First batch', first.get('Tickers'))} "
                f"{card_sentence('Expected fields', first.get('Expected Source Fields'))} "
                "Record proof only after validation, preview, rejected-row review, apply decision, rebuilt readiness, and artifact hygiene."
            ),
            "badges": ["batch cap", "proof before unlock"],
            "command": format_missing(first.get("Dry Run Or Stage Command"), "make dcf-input-source-review TOP_N=10"),
        }
    ]


def dcf_planner_scope(frame: pd.DataFrame | None, selection: object) -> tuple[pd.DataFrame, str, str]:
    if frame is None or frame.empty:
        return pd.DataFrame(), "all families", "No DCF input families loaded"
    work = filter_dcf_input_queue_by_family(frame, selection)
    family = dcf_input_family_key(selection)
    if not family and not work.empty and "Missing Input Family" in work.columns:
        counts = work["Missing Input Family"].fillna("").astype(str).str.strip()
        counts = counts.loc[counts.ne("")].value_counts()
        if not counts.empty:
            family = str(counts.index[0])
            work = filter_dcf_input_queue_by_family(frame, family)
    family = family or "all families"
    if "Missing Input Family" in frame.columns:
        family_counts = frame["Missing Input Family"].fillna("").astype(str).str.strip()
        family_counts = family_counts.loc[family_counts.ne("")].value_counts()
        summary = "; ".join(f"{name}: {count}" for name, count in family_counts.head(4).items())
    else:
        summary = "Missing input family counts unavailable"
    return work, family, summary or "Missing input family counts unavailable"


def dcf_proof_batch_planner_frame(
    frame: pd.DataFrame | None,
    selection: object,
    *,
    batch_size: int = 10,
) -> pd.DataFrame:
    columns = ["Step", "Status", "Scope", "Copy-Ready Action", "Review Boundary"]
    work, family, family_summary = dcf_planner_scope(frame, selection)
    if work.empty:
        return pd.DataFrame(
            [
                {
                    "Step": "1. Choose DCF input family",
                    "Status": "blocked",
                    "Scope": family,
                    "Copy-Ready Action": "make dcf-input-proof-queue TOP_N=10",
                    "Review Boundary": "Refresh the DCF input proof queue before building a batch plan.",
                }
            ],
            columns=columns,
        )
    source_packet = dcf_source_packet_frame(work, family)
    batch_queue = fundamentals_batch_review_queue_frame(work, family, batch_size=batch_size)
    first_source = source_packet.iloc[0] if not source_packet.empty else pd.Series(dtype=object)
    first_batch = batch_queue.iloc[0] if not batch_queue.empty else pd.Series(dtype=object)
    tickers = format_missing(first_batch.get("Tickers"), format_missing(first_source.get("Tickers"), "<reviewed_tickers>"))
    route = format_missing(first_batch.get("Batch Route"), format_missing(first_source.get("Source Route"), "source route pending"))
    proof_packet = format_missing(first_source.get("Proof Packet Command"), "DRY_RUN=1 make fundamentals-batch-proof TOP_N=10")
    stage_or_review = format_missing(first_batch.get("Dry Run Or Stage Command"), format_missing(first_source.get("Stage Or Review Command"), "make dcf-input-source-review TOP_N=10"))
    validation = format_missing(first_batch.get("Validation Gate"), format_missing(first_source.get("Validation Gate"), "make imports-validate"))
    preview = format_missing(first_batch.get("Preview Gate"), "make imports-preview")
    proof_record = format_missing(first_batch.get("Proof Record Scaffold"), "DRY_RUN=1 make reviewed-batch-proof-record ...")
    stop_rule = format_missing(first_batch.get("Stop Rule"), format_missing(first_source.get("Stop Rule"), "Stop if source proof is missing."))
    rows = [
        {
            "Step": "1. Choose DCF input family",
            "Status": "ready",
            "Scope": f"{family}: {len(work):,} selected row(s)",
            "Copy-Ready Action": "make dcf-input-proof-queue TOP_N=10",
            "Review Boundary": f"Top blocker families: {family_summary}. Plan one family at a time.",
        },
        {
            "Step": "2. Review source route",
            "Status": route,
            "Scope": tickers,
            "Copy-Ready Action": stage_or_review,
            "Review Boundary": "Use SEC staging only when configured and source-backed; otherwise keep the lane trusted-local/manual.",
        },
        {
            "Step": "3. Preview reviewed batch packet",
            "Status": "dry_run_first",
            "Scope": tickers,
            "Copy-Ready Action": proof_packet,
            "Review Boundary": "Packet preview is copy-only and does not make DCF-ready claims.",
        },
        {
            "Step": "4. Validate and preview",
            "Status": "review_gate",
            "Scope": format_missing(first_batch.get("Expected Source Fields"), family),
            "Copy-Ready Action": f"{validation} && {preview}",
            "Review Boundary": "Validation, preview, and rejected-row review must be checked before any apply decision.",
        },
        {
            "Step": "5. Record proof only after review",
            "Status": format_missing(first_batch.get("Proof Record Readiness"), "needs_reviewed_results"),
            "Scope": tickers,
            "Copy-Ready Action": proof_record,
            "Review Boundary": "Fill changed counts, changed tickers, source files, and generated-artifact review before recording.",
        },
        {
            "Step": "6. Stop rule",
            "Status": "stop_if_missing_source_proof",
            "Scope": family,
            "Copy-Ready Action": "do not proceed",
            "Review Boundary": stop_rule,
        },
    ]
    return pd.DataFrame(rows, columns=columns)


def dcf_proof_batch_planner_cards(
    frame: pd.DataFrame | None,
    selection: object,
) -> list[dict[str, object]]:
    planner = dcf_proof_batch_planner_frame(frame, selection)
    if planner.empty:
        return [
            {
                "kicker": "DCF BATCH PLANNER",
                "title": "No DCF batch plan available",
                "body": "Refresh the DCF input proof queue before planning a capped proof batch.",
                "badges": ["blocked visible", "readiness first"],
                "command": "make dcf-input-proof-queue TOP_N=10",
            }
        ]
    choose = planner.iloc[0]
    packet = planner.iloc[2] if len(planner) > 2 else planner.iloc[0]
    stop = planner.iloc[-1]
    return [
        {
            "kicker": "SOURCE PROOF LOOP",
            "title": "Review source -> preview row -> decide -> record proof",
            "body": (
                "Use this order: source review, evidence intake, source guard, validate, preview, rejected-row review, "
                "apply/skip decision, rebuilt readiness, then proof-record dry run. Do not write canonical fundamentals by default."
            ),
            "badges": ["validate-preview-apply", "dry-run first"],
            "command": format_missing(choose.get("Copy-Ready Action"), "make dcf-input-proof-queue TOP_N=10"),
        },
        {
            "kicker": "DCF BATCH PLANNER",
            "title": format_missing(choose.get("Scope"), "DCF input family pending"),
            "body": (
                f"{card_sentence('Route', planner.iloc[1].get('Status') if len(planner) > 1 else 'source route pending')} "
                f"{card_sentence('Packet', packet.get('Copy-Ready Action'))} "
                f"{card_sentence('Stop rule', compact_card_fragment(stop.get('Review Boundary'), max_chars=180))}"
            ),
            "badges": ["capped proof", "copy-only"],
            "command": format_missing(packet.get("Copy-Ready Action"), "DRY_RUN=1 make fundamentals-batch-proof TOP_N=10"),
        }
    ]
