from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_onboarding import build_onboarding_payload
from src.data_onboarding import write_onboarding_outputs
from src.data_update import enrich_price_update_status_frame, refresh_price_update_status_output
from src.data_sources import build_data_source_payload, write_data_source_outputs
from src.action_queue import write_action_queue_output
from src.paths import resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.purpose_evaluation import PURPOSE_EVALUATION_SUMMARY_CSV, write_purpose_evaluation_summary
from src.research_health import run as run_research_health


PROBLEM_SOURCE_STATUSES = {"partial", "missing_file", "source_unavailable", "manual_only"}
PROJECT_STATUS_JSON = "project_status.json"
PROJECT_STATUS_SUMMARY_CSV = "project_status_summary.csv"
PROJECT_STATUS_TOP_ACTIONS_CSV = "project_status_top_actions.csv"
PROJECT_STATUS_NEXT_STEPS_CSV = "project_status_next_steps.csv"
TRUSTED_DATA_PILOT_CANDIDATES_COMMAND = "make trusted-data-pilot-candidates TOP_N=10"
LEGACY_TRUSTED_DATA_PILOT_COMMAND = "make trusted-data-pilot TOP_N=10"


def _friendly_cli_guidance(text: object) -> str:
    """Make generated action text easier to scan in terminal output."""
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(r"\bRun make\b", "Use make", value)
    value = re.sub(r"\brun make\b", "use make", value)
    value = value.replace(
        "normalize verified downloaded OHLCV files into",
        "normalize verified OHLCV files into",
    )
    return value


def _load_purpose_evaluation_summary(output_path: Path, top_n: int) -> list[dict[str, Any]]:
    path = output_path / PURPOSE_EVALUATION_SUMMARY_CSV
    if not path.exists():
        return []
    try:
        frame = pd.read_csv(path)
    except Exception:
        return []
    if frame.empty:
        return []
    return frame.head(top_n).fillna("").to_dict("records")


def _read_csv_records(path: Path, *, top_n: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        frame = pd.read_csv(path, nrows=top_n)
    except Exception:
        return []
    if frame.empty:
        return []
    return frame.fillna("").to_dict("records")


def _read_csv_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _count_true(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if bool(row.get(field)))


def _first_non_empty(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass
        text = str(value or "").strip()
        if text.lower() == "nan":
            continue
        if text:
            return text
    return ""


def _price_recommended_action(ticker: str) -> str:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return (
            "Run make status-check TOP_N=5 first. For batch planning, preview make price-refresh-loop DRY_RUN=1; "
            "if you choose to refresh specific tickers, run make price-refresh TICKERS=<ticker>; if the free refresh "
            "path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv."
        )
    return (
        f"Run make focus-price TICKER={ticker} first. For batch planning, preview make price-refresh-loop DRY_RUN=1; "
        f"if you choose to refresh this ticker, run make price-refresh TICKERS={ticker}; if the free refresh path fails, "
        "normalize verified downloaded OHLCV files into data/imports/prices.csv."
    )


def _normalize_price_action_row(row: dict[str, Any]) -> dict[str, Any]:
    """Keep read-only status views current even when generated CSV text is stale."""
    if str(row.get("dataset") or "").strip().lower() != "prices":
        return row
    ticker = str(row.get("ticker") or "").strip().upper()
    text = str(row.get("recommended_action") or "").strip().lower()
    if (
        "make price-refresh-loop dry_run=1" not in text
        or "python3 -m src.data_update" in text
        or "or run make price-refresh" in text
    ):
        row["recommended_action"] = _price_recommended_action(ticker)
    return row


def _normalize_command_row(row: dict[str, Any]) -> dict[str, Any]:
    step = str(row.get("Step") or "")
    reason = str(row.get("Reason") or "")
    freshness = str(row.get("FreshnessContext") or "")
    if step:
        row["Step"] = (
            step.replace("Review import drafts", "Review import files")
            .replace("Review fundamentals import draft", "Review fundamentals import file")
            .replace("Review peer import draft", "Review peer import file")
            .replace("Review price import draft", "Review price import file")
            .replace("Refresh next capped missing-price batch", "Preview next capped missing-price batch")
        )
        step = str(row.get("Step") or "")
    if reason:
        row["Reason"] = (
            reason.replace("manual import draft fallback", "manual import file fallback")
            .replace("Manual import draft fallback", "Manual import file fallback")
            .replace("import draft workflow", "import file workflow")
            .replace("import drafts", "import files")
            .replace("import draft", "import file")
            .replace("Staged rows are already present", "Local import files already have rows")
        )
    if freshness:
        row["FreshnessContext"] = (
            freshness.replace(
                "verify source/freshness and generated CSV churn after any refresh",
                "verify source readiness notes and local CSV changes after any refresh",
            )
            .replace("local import draft workflow rows present", "local import files present; preview before apply")
            .replace("import draft workflow", "import file workflow")
            .replace("import drafts", "import files")
            .replace("import draft", "import file")
        )
        freshness = str(row.get("FreshnessContext") or "")
    if "Bundle" in step or "bundle" in freshness or "runbook" in step.lower():
        step = step.replace("Price Coverage Bundle", "Price Coverage Guided Data Batch")
        step = step.replace("SEC Fundamentals Bundle", "SEC Fundamentals Guided Data Batch")
        step = step.replace("Peer Mapping Bundle", "Peer Mapping Guided Data Batch")
        step = step.replace("Open Top bundle runbook", "Open Top guided data batch")
        step = step.replace(" bundle runbook", " guided data batch")
        step = step.replace(" Bundle runbook", " Guided Data Batch")
        step = step.replace(" runbook", "")
        row["Step"] = step
        if freshness:
            row["FreshnessContext"] = freshness.replace(
                "bundle generated from current onboarding outputs",
                "guided batch generated from current onboarding outputs",
            )
        reason = str(row.get("Reason") or "")
        if reason:
            row["Reason"] = reason.replace("across this bundle", "across this guided data batch").replace(
                "current bundle", "current guided data batch"
            )
    return row


def _load_price_status_lookup(output_path: Path) -> dict[str, dict[str, Any]]:
    path = output_path / "price_update_status.csv"
    if not path.exists():
        return {}
    frame = enrich_price_update_status_frame(pd.read_csv(path))
    if frame.empty or "ticker" not in frame.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            lookup[ticker] = row.to_dict()
    return lookup


def _count_readiness_true(data_path: Path, field: str) -> int | None:
    path = data_path / "reports" / "ticker_readiness_report.csv"
    if not path.exists():
        return None
    try:
        frame = pd.read_csv(path)
    except Exception:
        return None
    if frame.empty or field not in frame.columns:
        return None
    values = frame[field]
    if pd.api.types.is_bool_dtype(values):
        return int(values.fillna(False).sum())
    return int(values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes"}).sum())


def _truthy_series(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def _stale_generated_artifact_warnings(data_path: Path, output_path: Path) -> list[str]:
    generated_paths = [
        data_path / "reports" / "ticker_readiness_report.csv",
        output_path / "data_onboarding_actions.csv",
        output_path / PROJECT_STATUS_NEXT_STEPS_CSV,
    ]
    existing_generated = [path for path in generated_paths if path.exists()]
    if not existing_generated:
        return []
    oldest_generated_mtime = min(path.stat().st_mtime for path in existing_generated)
    source_paths = [
        data_path / "prices.csv",
        data_path / "fundamentals.csv",
        data_path / "peers.csv",
        data_path / "earnings.csv",
        data_path / "analyst_estimates.csv",
        data_path / "universe_master.csv",
        data_path / "universe_active.csv",
        data_path / "holdings.csv",
    ]
    newer_sources = [
        path.relative_to(data_path.parent).as_posix()
        for path in source_paths
        if path.exists() and path.stat().st_mtime > oldest_generated_mtime
    ]
    if not newer_sources:
        return []
    sample = ", ".join(newer_sources[:4])
    if len(newer_sources) > 4:
        sample = f"{sample}, +{len(newer_sources) - 4} more"
    return [
        (
            "Generated status artifacts may be stale because source CSVs changed after the last generated report "
            f"({sample}). Run make readiness or make status to refresh before relying on exact counts."
        )
    ]


def _fast_status_payload_from_outputs(
    project_root: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> dict[str, Any] | None:
    """Build a read-only operator snapshot from generated artifacts.

    The full project-status payload intentionally recomputes onboarding/source
    state. `make status-check` should stay fast on large local CSVs, so this
    path reuses existing generated reports and only falls back to recomputation
    when the minimal artifacts are missing.
    """
    root = resolve_project_root(project_root)
    data_path = resolve_data_dir(data_dir, root)
    output_path = resolve_outputs_dir(output_dir, root)
    readiness_path = data_path / "reports" / "ticker_readiness_report.csv"
    source_path = output_path / "data_source_status.csv"
    gaps_path = output_path / "data_gap_report.csv"
    actions_path = output_path / "data_onboarding_actions.csv"

    if not readiness_path.exists() or not source_path.exists() or not gaps_path.exists() or not actions_path.exists():
        return None

    readiness = _read_csv_frame(readiness_path)
    sources = _read_csv_records(source_path)
    gaps = _read_csv_records(gaps_path)
    actions = _read_csv_records(actions_path)
    bundles = _read_csv_records(output_path / "command_bundles.csv")
    if readiness.empty or not sources or not actions:
        return None

    allowed: set[str] | None = None
    if tickers:
        allowed = {str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()}
        if "ticker" in readiness.columns:
            readiness = readiness.loc[readiness["ticker"].astype(str).str.upper().str.strip().isin(allowed)].copy()
        gaps = [
            row for row in gaps
            if str(row.get("ticker", "")).upper().strip() in allowed
        ]
        actions = [
            row for row in actions
            if str(row.get("ticker", "")).upper().strip() in allowed
        ]

    normalized_actions = [_normalize_price_action_row(dict(row)) for row in actions]
    sorted_actions = sorted(normalized_actions, key=_action_rank)
    problem_sources = [row for row in sources if str(row.get("availability_status")) in PROBLEM_SOURCE_STATUSES]
    purpose_evaluation_rows = [] if allowed else _load_purpose_evaluation_summary(output_path, top_n)

    def readiness_count(field: str) -> int:
        if readiness.empty or field not in readiness.columns:
            return 0
        return int(_truthy_series(readiness[field]).sum())

    summary = {
        "data_sources_total": len(sources),
        "data_sources_available": sum(1 for row in sources if row.get("availability_status") == "available"),
        "data_sources_needing_attention": len(problem_sources),
        "data_gaps": len(gaps),
        "tickers_total": len(readiness),
        "tickers_with_prices": readiness_count("price_ready"),
        "tickers_usable_for_momentum": readiness_count("momentum_ready"),
        "tickers_dcf_ready": readiness_count("dcf_ready"),
        "tickers_peer_ready": readiness_count("peer_ready"),
        "onboarding_actions": len(sorted_actions),
        "critical_actions": sum(1 for row in sorted_actions if int(row.get("priority") or 999) <= 1),
        "purpose_evaluation_groups": len(purpose_evaluation_rows),
        "purpose_evaluation_active_groups": sum(
            1 for row in purpose_evaluation_rows if int(row.get("active_universe_count") or 0) > 0
        ),
    }
    command_rows = [_normalize_command_row(dict(row)) for row in _read_csv_records(output_path / PROJECT_STATUS_NEXT_STEPS_CSV)]
    if allowed:
        command_rows = _recommended_next_command_rows(sorted_actions, bundles, [])
    if not command_rows:
        command_rows = _recommended_next_command_rows(sorted_actions, bundles, [] if allowed else problem_sources)
    elif not allowed and not any(
        str(row.get("Command") or "").strip() == TRUSTED_DATA_PILOT_CANDIDATES_COMMAND
        for row in command_rows
    ):
        command_rows.append(_trusted_data_pilot_command_row())
    command_rows = _prioritize_public_command_rows(command_rows)

    return {
        "project_root": str(root),
        "data_dir": str(data_path),
        "outputs_dir": str(output_path),
        "summary": summary,
        "data_sources_needing_attention": problem_sources[:top_n],
        "top_data_gaps": gaps[:top_n],
        "top_onboarding_actions": sorted_actions[:top_n],
        "recommended_next_command_rows": command_rows,
        "recommended_next_commands": [row["Command"] for row in command_rows if row.get("Command")],
        "purpose_evaluation_summary": purpose_evaluation_rows,
        "warnings": _stale_generated_artifact_warnings(data_path, output_path),
        "status_source": "generated_artifacts",
    }


def _enrich_top_actions(onboarding_payload: dict[str, Any], price_status_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    actions = [dict(row) for row in onboarding_payload.get("onboarding_actions", [])]
    price_worklist = {
        str(row.get("ticker") or "").strip().upper(): row
        for row in onboarding_payload.get("price_import_worklist", [])
        if str(row.get("ticker") or "").strip()
    }
    sec_stage_queue = {
        str(row.get("ticker") or "").strip().upper(): row
        for row in onboarding_payload.get("sec_stage_queue", [])
        if str(row.get("ticker") or "").strip()
    }
    peer_mapping_queue = {
        str(row.get("ticker") or "").strip().upper(): row
        for row in onboarding_payload.get("peer_mapping_queue", [])
        if str(row.get("ticker") or "").strip()
    }
    holdings_first_price_tickers: set[str] = set()
    for row in onboarding_payload.get("command_bundles", []):
        if str(row.get("lane") or "").strip().lower() != "prices":
            continue
        if str(row.get("scope") or "").strip().lower() != "holdings_first":
            continue
        holdings_first_price_tickers.update(
            {
                ticker.strip().upper()
                for ticker in str(row.get("tickers") or "").split(",")
                if ticker.strip()
            }
        )

    enriched: list[dict[str, Any]] = []
    for row in actions:
        dataset = str(row.get("dataset") or "").strip().lower()
        ticker = str(row.get("ticker") or "").strip().upper()
        source_row: dict[str, Any] | None = None
        if dataset == "prices":
            source_row = price_worklist.get(ticker)
        elif dataset == "fundamentals":
            source_row = sec_stage_queue.get(ticker)
        elif dataset == "peers":
            source_row = peer_mapping_queue.get(ticker)

        if source_row:
            for field in ("reason", "recommended_action", "focus_command", "example_command"):
                value = _first_non_empty(source_row.get(field), row.get(field))
                if value:
                    row[field] = value
            if dataset == "prices" and ticker:
                row["is_holding"] = ticker in holdings_first_price_tickers
            elif "is_holding" in source_row:
                row["is_holding"] = bool(source_row.get("is_holding"))
        elif dataset == "prices" and ticker:
            row["is_holding"] = ticker in holdings_first_price_tickers

        if dataset == "prices" and ticker:
            price_status_row = price_status_lookup.get(ticker)
            if price_status_row:
                status = str(price_status_row.get("status") or "").strip().lower()
                for field in (
                    "status",
                    "recommended_action",
                    "focus_command",
                    "example_command",
                    "target_file",
                    "provider",
                    "requested_end",
                    "run_timestamp",
                ):
                    if source_row and status in {"fetched", "skipped_fresh"} and field != "status":
                        continue
                    value = _first_non_empty(price_status_row.get(field), row.get(field))
                    if value:
                        row[field] = value
                if not (source_row and status in {"fetched", "skipped_fresh"}):
                    row["reason"] = _first_non_empty(price_status_row.get("error_message"), row.get("reason"))
            row = _normalize_price_action_row(row)
        enriched.append(row)
    return enriched


def _action_rank(row: dict[str, Any]) -> tuple[int, int, str, str]:
    return (
        int(row.get("priority") or 999),
        0 if bool(row.get("is_holding")) else 1,
        str(row.get("ticker") or ""),
        str(row.get("dataset") or ""),
    )


def _bundle_rank(bundle: dict[str, Any]) -> tuple[int, int, str]:
    scope = str(bundle.get("scope") or "").strip().lower()
    ticker_count = int(bundle.get("ticker_count") or 0)
    scope_rank = 0 if scope == "broader_queue" else 1 if scope == "holdings_first" else 2
    return (scope_rank, -ticker_count, str(bundle.get("bundle_name") or ""))


def _guided_batch_name(raw_name: object, scope: str) -> str:
    name = _first_non_empty(raw_name, "Top guided data batch")
    name = name.replace(" Bundle", " Guided Data Batch").replace(" bundle", " guided data batch")
    if "Guided Data Batch" not in name:
        name = f"{name} Guided Data Batch"
    if scope == "broader_queue" and "(Broader Queue)" not in name:
        name = f"{name} (Broader Queue)"
    return name


def _source_context(*rows: dict[str, Any] | None, fallback: str = "") -> str:
    for row in rows:
        if not row:
            continue
        context = _first_non_empty(
            row.get("source_file"),
            row.get("target_file"),
            row.get("local_file"),
            row.get("source_artifact"),
            row.get("source_name"),
            row.get("provider"),
        )
        if context:
            return context
    return fallback


def _freshness_context(*rows: dict[str, Any] | None, fallback: str = "") -> str:
    for row in rows:
        if not row:
            continue
        context = _first_non_empty(
            row.get("updated_at"),
            row.get("last_price_date"),
            row.get("as_of_date"),
            row.get("requested_end"),
            row.get("status"),
            row.get("availability_status"),
        )
        if context:
            return context
    return fallback


def _command_row(
    step: str,
    command: str,
    reason: str,
    *,
    source_context: str = "",
    freshness_context: str = "",
) -> dict[str, str]:
    return {
        "Step": step,
        "Command": command,
        "Reason": reason,
        "SourceContext": source_context,
        "FreshnessContext": freshness_context,
    }


def _select_top_bundle(actions: list[dict[str, Any]], bundles: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not bundles:
        return None
    if not actions:
        return min(bundles, key=_bundle_rank)

    top_action = actions[0]
    dataset = str(top_action.get("dataset") or "").strip().lower()
    ticker = str(top_action.get("ticker") or "").strip().upper()

    lane_matches = [
        bundle for bundle in bundles if str(bundle.get("lane") or "").strip().lower() == dataset
    ]
    if not lane_matches:
        return min(bundles, key=_bundle_rank)

    if ticker:
        ticker_matches: list[dict[str, Any]] = []
        for bundle in lane_matches:
            tickers = {
                part.strip().upper()
                for part in str(bundle.get("tickers") or "").split(",")
                if part.strip()
            }
            if ticker in tickers:
                ticker_matches.append(bundle)
        if ticker_matches:
            return min(ticker_matches, key=_bundle_rank)

    return min(lane_matches, key=_bundle_rank)


def _recommended_source_command_rows(problem_sources: list[dict[str, Any]]) -> list[dict[str, str]]:
    grouped_rows: dict[str, list[dict[str, Any]]] = {}
    command_order: list[str] = []
    for row in problem_sources:
        command = _first_non_empty(row.get("focus_command"))
        if not command or command == "make status":
            continue
        if command not in grouped_rows:
            grouped_rows[command] = []
            command_order.append(command)
        grouped_rows[command].append(row)

    rows: list[dict[str, str]] = []
    for command in command_order:
        grouped = grouped_rows[command]
        if command == "make imports-validate" and len(grouped) > 1:
            datasets = [str(row.get("dataset") or "data").replace("_", " ") for row in grouped]
            target_files = [
                _first_non_empty(row.get("target_file"), row.get("local_file"))
                for row in grouped
                if _first_non_empty(row.get("target_file"), row.get("local_file"))
            ]
            dataset_text = " and ".join(datasets[:-1] + [datasets[-1]]) if len(datasets) <= 2 else ", ".join(datasets[:-1]) + f", and {datasets[-1]}"
            file_text = " and ".join(target_files[:-1] + [target_files[-1]]) if len(target_files) <= 2 else ", ".join(target_files[:-1]) + f", and {target_files[-1]}"
            reason = (
                f"Local import files already have rows in {file_text}. "
                "Run make imports-validate, then make imports-preview, then make imports-apply, then make status "
                f"to confirm the live local {dataset_text} inputs."
            )
            rows.append(
                _command_row(
                    "Review import files",
                    command,
                    reason,
                    source_context=file_text,
                    freshness_context="local import files present; preview before apply",
                )
            )
            continue

        row = grouped[0]
        dataset = str(row.get("dataset") or "data").replace("_", " ")
        status = str(row.get("availability_status") or "").strip().lower()
        if command == "make imports-validate":
            step = f"Review {dataset} import file"
        elif status == "manual_only":
            step = f"Prepare {dataset} input"
        else:
            step = f"Advance {dataset} source"
        reason = _first_non_empty(row.get("fallback_action"), row.get("validation_warnings"), row.get("notes"))
        rows.append(
            _command_row(
                step,
                command,
                reason,
                source_context=_source_context(row),
                freshness_context=_freshness_context(row),
            )
        )
    return rows


def _trusted_data_pilot_command_row() -> dict[str, str]:
    return _command_row(
        "Rank trusted data pilot candidates",
        TRUSTED_DATA_PILOT_CANDIDATES_COMMAND,
        (
            "Rank current operating-company blockers first, inspect one company with "
            "make trusted-data-pilot-packet TICKER=<ticker>, then use selected names for the trusted-data "
            "evidence loop instead of trying to unlock the full universe at once."
        ),
        source_context="trusted local CSVs plus SEC/manual review paths",
        freshness_context="read-only ranking; run before importing trusted fundamentals or peer rows",
    )


def _prioritize_public_command_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the public next-step order aligned with the product roadmap."""
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        command = str(row.get("Command") or "").strip()
        if command == LEGACY_TRUSTED_DATA_PILOT_COMMAND:
            continue
        if not command or command in seen:
            continue
        seen.add(command)
        deduped.append(row)

    if len(deduped) <= 2:
        return deduped

    first = deduped[0]
    rest = deduped[1:]
    pilot_rows = [row for row in rest if str(row.get("Command") or "").strip() == TRUSTED_DATA_PILOT_CANDIDATES_COMMAND]
    if not pilot_rows or str(first.get("Command") or "").strip() == TRUSTED_DATA_PILOT_CANDIDATES_COMMAND:
        return deduped

    without_pilot = [row for row in rest if str(row.get("Command") or "").strip() != TRUSTED_DATA_PILOT_CANDIDATES_COMMAND]
    return [first, pilot_rows[0], *without_pilot]


def _recommended_next_command_rows(
    actions: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
    problem_sources: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    if actions:
        top_action = actions[0]
        dataset_key = str(top_action.get("dataset") or "").strip().lower()
        if dataset_key == "prices" and not bool(top_action.get("is_holding")):
            rows.append(
                _command_row(
                    "Preview next capped missing-price batch",
                    "make price-refresh-loop DRY_RUN=1",
                    (
                        "Preview the broad-universe price frontier first, then run several capped batches "
                        "if you choose; Yahoo rows are research-grade and the manual import file fallback remains available."
                    ),
                    source_context="data/imports/prices.csv fallback plus optional Yahoo refresh",
                    freshness_context="dry-run first; verify source readiness notes and local CSV changes after any refresh",
                )
            )
        command = _first_non_empty(top_action.get("focus_command"), top_action.get("example_command"))
        if command:
            dataset = str(top_action.get("dataset") or "data").replace("_", " ")
            ticker = _first_non_empty(top_action.get("ticker"))
            step = f"Fix top {dataset} blocker" + (f" ({ticker})" if ticker else "")
            reason = _first_non_empty(top_action.get("reason"), top_action.get("recommended_action"))
            rows.append(
                _command_row(
                    step,
                    command,
                    reason,
                    source_context=_source_context(top_action),
                    freshness_context=_freshness_context(top_action),
                )
            )
            if dataset_key in {"fundamentals", "peers"} and not os.environ.get("SEC_USER_AGENT", "").strip():
                rows.append(
                    _command_row(
                        "Choose fundamentals input path",
                        "make templates",
                        (
                            "SEC_USER_AGENT is not configured, so SEC staging workflow is unavailable. "
                            "Either export SEC_USER_AGENT before make sec-stage, or prepare trusted manual "
                            "fundamentals in data/imports/fundamentals.csv and run make imports-validate, "
                            "make imports-preview, and make imports-apply."
                        ),
                        source_context="SEC_USER_AGENT or data/imports/fundamentals.csv",
                        freshness_context="credential/manual import state controls availability",
                    )
                )

    top_bundle = _select_top_bundle(actions, bundles)
    if top_bundle:
        command = _first_non_empty(
            top_bundle.get("runbook_shortcut_command"),
            top_bundle.get("detail_shortcut_command"),
            top_bundle.get("bundle_shortcut_command"),
            top_bundle.get("primary_command"),
        )
        if command:
            scope = str(top_bundle.get("scope") or "").strip().lower()
            bundle_name = _guided_batch_name(top_bundle.get("bundle_name"), scope)
            reason = _first_non_empty(top_bundle.get("goal_summary"), top_bundle.get("why_it_matters"))
            if command.startswith("make runbook-"):
                step = f"Open {bundle_name}"
            elif command.startswith("make detail-"):
                step = f"Open {bundle_name} details"
            elif command.startswith("make bundle-"):
                step = f"Run {bundle_name}"
            else:
                step = f"Run {bundle_name}"
            rows.append(
                _command_row(
                    step,
                    command,
                    reason,
                    source_context=_source_context(top_bundle),
                    freshness_context=_freshness_context(top_bundle, fallback="guided batch generated from current onboarding outputs"),
                )
            )

    rows.append(_trusted_data_pilot_command_row())

    problem_source_rows = _recommended_source_command_rows(problem_sources)
    if problem_source_rows:
        rows.append(problem_source_rows[0])

    rows.extend(
        [
            _command_row(
                "Deterministic verification",
                "make verify",
                "Confirm the local CSV outputs and dashboard helpers still pass deterministic checks.",
                source_context="tests and generated local CSV outputs",
                freshness_context="run after data refresh/import or code changes",
            ),
            _command_row(
                "Dashboard smoke check",
                "make dashboard-smoke",
                "Confirm the Streamlit surface still boots cleanly after the local data and workflow updates.",
                source_context="Streamlit dashboard",
                freshness_context="run after dashboard or environment changes",
            ),
        ]
    )

    return _prioritize_public_command_rows(rows)


def build_project_status_payload(
    project_root: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root)
    data_path = resolve_data_dir(data_dir, root)
    output_path = resolve_outputs_dir(output_dir, root)
    source_payload = build_data_source_payload(root, data_dir=data_path, output_dir=output_path)
    onboarding_payload = build_onboarding_payload(root, data_dir=data_path, output_dir=output_path)
    price_status_lookup = _load_price_status_lookup(output_path)
    sources = source_payload["data_sources"]
    gaps = source_payload["data_gaps"]
    coverage = onboarding_payload["ticker_coverage"]
    if tickers:
        allowed = {str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()}
        coverage = [row for row in coverage if str(row.get("ticker", "")).upper().strip() in allowed]
        gaps = [row for row in gaps if str(row.get("ticker", "")).upper().strip() in allowed]
    enriched_actions = _enrich_top_actions(onboarding_payload, price_status_lookup)
    if tickers:
        enriched_actions = [row for row in enriched_actions if str(row.get("ticker", "")).upper().strip() in allowed]
    actions = sorted(enriched_actions, key=_action_rank)
    problem_sources = [row for row in sources if str(row.get("availability_status")) in PROBLEM_SOURCE_STATUSES]
    command_problem_sources = [] if tickers else problem_sources
    readiness_dcf_ready = None if tickers else _count_readiness_true(data_path, "dcf_ready")
    purpose_evaluation_rows = [] if tickers else _load_purpose_evaluation_summary(output_path, top_n)
    summary = {
        "data_sources_total": len(sources),
        "data_sources_available": sum(1 for row in sources if row.get("availability_status") == "available"),
        "data_sources_needing_attention": len(problem_sources),
        "data_gaps": len(gaps),
        "tickers_total": len(coverage),
        "tickers_with_prices": _count_true(coverage, "has_prices"),
        "tickers_usable_for_momentum": _count_true(coverage, "usable_for_momentum"),
        "tickers_dcf_ready": readiness_dcf_ready if readiness_dcf_ready is not None else _count_true(coverage, "dcf_ready"),
        "tickers_peer_ready": _count_true(coverage, "peer_ready"),
        "onboarding_actions": len(actions),
        "critical_actions": sum(1 for row in actions if int(row.get("priority") or 999) <= 1),
        "purpose_evaluation_groups": len(purpose_evaluation_rows),
        "purpose_evaluation_active_groups": sum(
            1 for row in purpose_evaluation_rows if int(row.get("active_universe_count") or 0) > 0
        ),
    }
    command_rows = _recommended_next_command_rows(
        actions,
        onboarding_payload.get("command_bundles", []),
        command_problem_sources,
    )
    return {
        "project_root": str(root),
        "data_dir": str(data_path),
        "outputs_dir": str(output_path),
        "summary": summary,
        "data_sources_needing_attention": problem_sources[:top_n],
        "top_data_gaps": gaps[:top_n],
        "top_onboarding_actions": actions[:top_n],
        "recommended_next_command_rows": command_rows,
        "recommended_next_commands": [row["Command"] for row in command_rows],
        "purpose_evaluation_summary": purpose_evaluation_rows,
    }


def write_project_status_output(
    project_root: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    top_n: int = 10,
    refresh_supporting_outputs: bool = False,
) -> dict[str, Any]:
    root = resolve_project_root(project_root)
    data_path = resolve_data_dir(data_dir, root)
    output_path = resolve_outputs_dir(output_dir, root)
    if refresh_supporting_outputs:
        refresh_price_update_status_output(root, output_dir=output_path)
        write_data_source_outputs(root, data_dir=data_path, output_dir=output_path)
        write_onboarding_outputs(root, data_dir=data_path, output_dir=output_path)
        run_research_health(root, data_dir=data_path, output_dir=output_path)
        write_action_queue_output(root, data_dir=data_path, output_dir=output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    write_purpose_evaluation_summary(root, data_dir=data_path, output_dir=output_path)
    payload = build_project_status_payload(root, data_dir=data_path, output_dir=output_path, top_n=top_n)

    json_path = output_path / PROJECT_STATUS_JSON
    summary_path = output_path / PROJECT_STATUS_SUMMARY_CSV
    top_actions_path = output_path / PROJECT_STATUS_TOP_ACTIONS_CSV
    next_steps_path = output_path / PROJECT_STATUS_NEXT_STEPS_CSV
    purpose_summary_path = output_path / PURPOSE_EVALUATION_SUMMARY_CSV

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame([payload["summary"]]).to_csv(summary_path, index=False)
    pd.DataFrame(payload["top_onboarding_actions"]).to_csv(top_actions_path, index=False)
    pd.DataFrame(payload["recommended_next_command_rows"]).to_csv(next_steps_path, index=False)

    return {
        **payload,
        "written_files": {
            "project_status_json": str(json_path),
            "project_status_summary": str(summary_path),
            "project_status_top_actions": str(top_actions_path),
            "project_status_next_steps": str(next_steps_path),
            "purpose_evaluation_summary": str(purpose_summary_path),
        },
    }


def _print_human(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    print("Read-only project snapshot.")
    print("Commands below are copy-only local research helpers; this status view does not run them.")
    print("Project status summary:")
    print(f"- Data sources: {summary['data_sources_available']}/{summary['data_sources_total']} available")
    print(f"- Data sources needing attention: {summary['data_sources_needing_attention']}")
    print(f"- Locked input rows: {summary['data_gaps']}")
    print(f"- Tickers with prices: {summary['tickers_with_prices']}/{summary['tickers_total']}")
    print(f"- Tickers usable for momentum: {summary['tickers_usable_for_momentum']}/{summary['tickers_total']}")
    print(f"- DCF-ready tickers: {summary['tickers_dcf_ready']}/{summary['tickers_total']}")
    print(f"- Peer-ready tickers: {summary['tickers_peer_ready']}/{summary['tickers_total']}")
    print(f"- Data-unlock steps: {summary['onboarding_actions']} ({summary['critical_actions']} urgent)")
    print(f"- Research-purpose groups: {summary.get('purpose_evaluation_groups', 0)} ({summary.get('purpose_evaluation_active_groups', 0)} active-universe groups)")
    for warning in payload.get("warnings", []):
        print(f"Warning: {warning}")
    print("Top locked inputs to review:")
    for row in payload["top_onboarding_actions"]:
        ticker = f" {row['ticker']}" if row.get("ticker") else ""
        print(f"- P{row['priority']} {row['dataset']}{ticker}")
        if row.get("focus_command"):
            print(f"  suggested check: {row['focus_command']}")
        if row.get("recommended_action"):
            print(f"  guidance: {_friendly_cli_guidance(row['recommended_action'])}")
        if row.get("example_command"):
            print(f"  trusted import/fallback: {row['example_command']}")
        if row.get("credential_required"):
            present = "present" if bool(row.get("credential_present")) else "missing"
            print(f"  credential: {row['credential_required']} ({present})")
        if row.get("manual_fallback_command"):
            print(f"  fallback: {row['manual_fallback_command']}")
    print("Recommended next local steps:")
    command_rows = payload.get("recommended_next_command_rows") or [
        {"Step": f"Next {index}", "Command": command}
        for index, command in enumerate(payload.get("recommended_next_commands", []), start=1)
    ]
    for row in command_rows:
        print(f"- {row.get('Step', 'Next')}: {row.get('Command', '')}")
        if row.get("Reason"):
            print(f"  why it matters: {_friendly_cli_guidance(row['Reason'])}")
        if row.get("SourceContext"):
            print(f"  source: {row['SourceContext']}")
        if row.get("FreshnessContext"):
            print(f"  source readiness: {row['FreshnessContext']}")


def _format_operator_path_context(root: Path, data_path: Path, output_path: Path) -> str:
    def display(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)

    return (
        "Local folders:\n"
        f"- project: current repository root\n"
        f"- data: {display(data_path)}\n"
        f"- outputs: {display(output_path)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a read-only local project status snapshot.")
    parser.add_argument("--check", action="store_true", help="Print the current read-only local project status.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--write-output", action="store_true", help="Write machine-readable project status outputs.")
    parser.add_argument(
        "--refresh-artifacts",
        action="store_true",
        help="Refresh supporting read-only status files before printing status.",
    )
    parser.add_argument("--project-root", help="Project root for default data/output directories.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--output-dir", help="Optional output directory. Relative paths resolve from project root.")
    parser.add_argument("--tickers", help="Optional comma-separated ticker filter for read-only project status views.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of gaps/actions to show.")
    args = parser.parse_args()
    explicit_tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()] if args.tickers else None

    root = resolve_project_root(args.project_root)
    data_path = resolve_data_dir(args.data_dir, root)
    output_path = resolve_outputs_dir(args.output_dir, root)
    should_write_output = args.write_output or args.refresh_artifacts
    if args.check and should_write_output:
        parser.error("--check cannot be combined with --write-output or --refresh-artifacts")
    if should_write_output and explicit_tickers:
        parser.error("--tickers is only supported for read-only project status views")
    if should_write_output:
        payload = write_project_status_output(
            root,
            data_dir=data_path,
            output_dir=output_path,
            top_n=args.top_n,
            refresh_supporting_outputs=args.refresh_artifacts,
        )
    elif args.check:
        payload = _fast_status_payload_from_outputs(
            root,
            data_dir=data_path,
            output_dir=output_path,
            top_n=args.top_n,
            tickers=explicit_tickers,
        )
        if payload is None:
            payload = build_project_status_payload(
                root,
                data_dir=data_path,
                output_dir=output_path,
                top_n=args.top_n,
                tickers=explicit_tickers,
            )
    else:
        payload = build_project_status_payload(
            root,
            data_dir=data_path,
            output_dir=output_path,
            top_n=args.top_n,
            tickers=explicit_tickers,
        )

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print(_format_operator_path_context(root, data_path, output_path))
    _print_human(payload)
    if args.write_output:
        print("Wrote:")
        for path in payload.get("written_files", {}).values():
            print(f"- {path}")


if __name__ == "__main__":
    main()
