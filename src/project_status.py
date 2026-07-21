from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.artifact_freshness import generated_artifact_stale_warning
from src.continuation_gate import ContinuationGate, build_continuation_gate
from src.data_onboarding import build_onboarding_payload
from src.data_onboarding import write_onboarding_outputs
from src.data_update import enrich_price_update_status_frame, refresh_price_update_status_output
from src.data_sources import build_data_source_payload, write_data_source_outputs
from src.action_queue import write_action_queue_output
from src.dcf_input_proof_queue import build_dcf_input_proof_queue_from_files
from src.dcf_input_proof_queue import _reviewed_non_actionable_tickers as _reviewed_non_actionable_dcf_tickers
from src.hosted_demo_readiness import read_hosted_demo_url
from src.paths import resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.profile_context import build_profile_context, render_profile_context_text
from src.price_history_proof_queue import _reviewed_non_actionable_price_tickers
from src.public_ux_review_checklist import SUCCESSFUL_REVIEW_CLASSIFICATIONS, public_ux_review_notes_status
from src.purpose_evaluation import PURPOSE_EVALUATION_SUMMARY_CSV, write_purpose_evaluation_summary
from src.readiness_ops import build_reviewed_batch_ledger_summaries
from src.research_health import research_health_outputs_current
from src.research_health import run as run_research_health
from src.trusted_data_pilot import load_trusted_data_pilot_candidates


PROBLEM_SOURCE_STATUSES = {"partial", "missing_file", "source_unavailable", "manual_only"}
PROJECT_STATUS_JSON = "project_status.json"
PROJECT_STATUS_SUMMARY_CSV = "project_status_summary.csv"
PROJECT_STATUS_TOP_ACTIONS_CSV = "project_status_top_actions.csv"
PROJECT_STATUS_NEXT_STEPS_CSV = "project_status_next_steps.csv"
PROJECT_STATUS_REMAINING_STAGES_CSV = "project_status_remaining_stages.csv"
TRUSTED_DATA_PILOT_CANDIDATES_COMMAND = "make trusted-data-pilot-candidates TOP_N=10"
LEGACY_TRUSTED_DATA_PILOT_COMMAND = "make trusted-data-pilot TOP_N=10"


def _truthy_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"true", "1", "yes"}


def _source_needs_required_attention(row: dict[str, Any]) -> bool:
    status = str(row.get("availability_status") or "").strip()
    if status not in PROBLEM_SOURCE_STATUSES:
        return False
    return _truthy_value(row.get("is_required"))


def _source_is_optional_locked(row: dict[str, Any]) -> bool:
    status = str(row.get("availability_status") or "").strip()
    if status not in PROBLEM_SOURCE_STATUSES:
        return False
    return not _source_needs_required_attention(row)


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
    value = value.replace("coverage_workflow_evidence", "workflow evidence only; current source-proof queues are exhausted")
    value = value.replace("fundamentals_share_count_source_ladder", "fundamentals/share-count source ladder")
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


def _normalize_price_reason_text(text: object) -> str:
    """Clarify ticker-level price-history blockers in public status output."""
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(
        r"^Only (\d+) verified local price rows are present;",
        r"This ticker has only \1 verified local price rows;",
        value,
    )
    value = re.sub(
        r"^Only (\d+) verified local price rows are present\.$",
        r"This ticker has only \1 verified local price rows.",
        value,
    )
    return value


def _price_recommended_action(ticker: str) -> str:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return (
            "Run make status-check TOP_N=5 first. For batch planning, preview make price-refresh-loop DRY_RUN=1; "
            "if you choose to refresh specific tickers, run make price-refresh TICKERS=<ticker> PROVIDER=auto so "
            "Stooq, Yahoo, optional IBKR read-only, and configured FMP/Alpha Vantage/Finnhub fallbacks are tried automatically; only if every provider "
            "path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv."
        )
    return (
        f"Run make focus-price TICKER={ticker} first. For batch planning, preview make price-refresh-loop DRY_RUN=1; "
        f"if you choose to refresh this ticker, run make price-refresh TICKERS={ticker} PROVIDER=auto so Stooq, Yahoo, "
        "and configured FMP/Alpha Vantage/Finnhub fallbacks are tried automatically; only if every provider path fails, "
        "normalize verified downloaded OHLCV files into data/imports/prices.csv."
    )


def _normalize_price_action_row(row: dict[str, Any]) -> dict[str, Any]:
    """Keep read-only status views current even when generated CSV text is stale."""
    if str(row.get("dataset") or "").strip().lower() != "prices":
        return row
    ticker = str(row.get("ticker") or "").strip().upper()
    row["reason"] = _normalize_price_reason_text(row.get("reason"))
    text = str(row.get("recommended_action") or "").strip().lower()
    if (
        "make price-refresh-loop dry_run=1" not in text
        or "python3 -m src.data_update" in text
        or "or run make price-refresh" in text
        or "free refresh path fails" in text
        or "provider=auto" not in text
        or "configured fmp/alpha vantage" not in text
    ):
        row["recommended_action"] = _price_recommended_action(ticker)
    return row


def _normalize_command_row(row: dict[str, Any]) -> dict[str, Any]:
    step = str(row.get("Step") or "")
    reason = str(row.get("Reason") or "")
    freshness = str(row.get("FreshnessContext") or "")
    command = str(row.get("Command") or "").strip()
    if command == "make project-status" and "workflow evidence" in step.lower():
        row.update(_workflow_evidence_command_row())
        return row
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
            _normalize_price_reason_text(reason)
            .replace("manual import draft fallback", "manual import file fallback")
            .replace("Manual import draft fallback", "Manual import file fallback")
            .replace("import draft workflow", "import file workflow")
            .replace("import drafts", "import files")
            .replace("import draft", "import file")
            .replace("Staged rows are already present", "Local import files already have rows")
        )
        if str(row.get("Command") or "").strip() == "make imports-validate":
            row["Reason"] = re.sub(
                r";\s*run make imports-apply after previewing import files\.?",
                "; apply only after validation passes, preview scope is intended, and rejected rows are zero.",
                str(row["Reason"]),
                flags=re.IGNORECASE,
            )
            row["Reason"] = re.sub(
                r"(?:Use|Run) make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local ([^.]+?) inputs\.?",
                r"Run make imports-validate, then make imports-preview; apply only after validation passes, preview scope is intended, and rejected rows are zero. Then make status to confirm the live local \1 inputs.",
                str(row["Reason"]),
                flags=re.IGNORECASE,
            )
        if str(row.get("Command") or "").strip().startswith("make price-refresh-loop"):
            row["Reason"] = (
                "Preview the broad-universe price frontier first; PROVIDER=auto tries Stooq, Yahoo, "
                "and configured FMP/Alpha Vantage/Finnhub before the manual import file fallback."
            )
    source_context = str(row.get("SourceContext") or "")
    if source_context:
        row["SourceContext"] = (
            source_context.replace(
                "data/imports/prices.csv fallback plus optional Yahoo refresh",
                "PROVIDER=auto price ladder with Stooq, Yahoo, optional IBKR read-only, and configured FMP/Alpha Vantage/Finnhub fallbacks; data/imports/prices.csv remains the last manual fallback",
            )
            .replace(
                "data/imports/prices.csv fallback plus optional auto price ladder",
                "PROVIDER=auto price ladder with Stooq, Yahoo, optional IBKR read-only, and configured FMP/Alpha Vantage/Finnhub fallbacks; data/imports/prices.csv remains the last manual fallback",
            )
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
            ).replace("Unlock Monthly Picks", "Make Monthly Picks available")
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


def _count_tickers_with_price_rows(data_path: Path, allowed: set[str] | None = None) -> int | None:
    path = data_path / "price_coverage_report.csv"
    if not path.exists():
        return None
    try:
        frame = pd.read_csv(path)
    except Exception:
        return None
    if frame.empty or "ticker" not in frame.columns or "price_rows" not in frame.columns:
        return None
    if allowed is not None:
        tickers = frame["ticker"].fillna("").astype(str).str.upper().str.strip()
        frame = frame.loc[tickers.isin(allowed)].copy()
    price_rows = pd.to_numeric(frame["price_rows"], errors="coerce").fillna(0)
    return int(price_rows.gt(0).sum())


def _truthy_series(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def _stale_generated_artifact_warnings(data_path: Path, output_path: Path) -> list[str]:
    root = data_path.parent
    generated_paths = [
        data_path / "reports" / "ticker_readiness_report.csv",
        output_path / "data_onboarding_actions.csv",
        output_path / PROJECT_STATUS_NEXT_STEPS_CSV,
    ]
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
    warning = generated_artifact_stale_warning(
        root=root,
        generated_paths=generated_paths,
        source_paths=source_paths,
        display_root=root,
        refresh_command="make readiness or make status",
    )
    if not warning:
        return []
    return [warning]


def _load_source_operator_summary(output_path: Path) -> dict[str, Any]:
    path = output_path / "session_source_preflight.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    console = payload.get("source_activation_console_v2", {})
    if not isinstance(console, dict):
        return {}
    summary = console.get("operator_summary", {})
    if not isinstance(summary, dict):
        return {}
    enriched = dict(summary)
    limits = console.get("free_tier_batch_limits", {})
    if isinstance(limits, dict):
        enriched["free_tier_batch_limits"] = limits
    return enriched


def _source_operator_free_tier_limit_summary(source_operator_summary: dict[str, Any]) -> str:
    limits = source_operator_summary.get("free_tier_batch_limits", {})
    if not isinstance(limits, dict):
        return ""
    pieces: list[str] = []
    for provider in ("fmp", "alpha_vantage", "finnhub"):
        policy = limits.get(provider)
        if not isinstance(policy, dict):
            continue
        daily = policy.get("recommended_daily_request_limit")
        batch = policy.get("recommended_batch_size")
        if daily in (None, "") or batch in (None, ""):
            continue
        pieces.append(f"{provider}<={daily}/day and <={batch}/run")
    return ", ".join(pieces)


_KEYED_PROVIDER_OPERATOR_GUIDANCE: dict[str, dict[str, str]] = {
    "fmp": {
        "setup_env": "FMP_API_KEY",
        "smoke_command": "make fmp-smoke TICKER=<ticker>",
    },
    "finnhub": {
        "setup_env": "FINNHUB_API_KEY",
        "smoke_command": "make finnhub-smoke TICKER=<ticker>",
    },
    "alpha_vantage": {
        "setup_env": "ALPHA_VANTAGE_API_KEY",
        "smoke_command": "make alpha-vantage-smoke TICKER=<ticker>",
    },
}

_KEYED_PROVIDER_SETUP_ORDER = ("fmp", "finnhub", "alpha_vantage")


def _source_operator_first_setup_guidance(source_operator_summary: dict[str, Any]) -> dict[str, str]:
    needs_setup = [
        str(item).strip().lower()
        for item in source_operator_summary.get("needs_setup", [])
        if str(item).strip()
    ]
    for provider in _KEYED_PROVIDER_SETUP_ORDER:
        if provider in needs_setup:
            guidance = _KEYED_PROVIDER_OPERATOR_GUIDANCE[provider]
            return {
                "provider": provider,
                "setup_env": guidance["setup_env"],
                "smoke_command": guidance["smoke_command"],
            }
    return {}


def _git_status_line(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch", "--untracked-files=no"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return (result.stdout.splitlines() or [""])[0].strip()


def _linkedin_stage_from_git_status(git_status_line: str | None) -> dict[str, str]:
    line = str(git_status_line or "").strip()
    lowered = line.lower()
    if "behind" in lowered or "diverged" in lowered:
        return {
            "State": "needs_git_sync_review",
            "Evidence": f"Public share gates may pass, but git status is {line}; sync from origin before sharing.",
            "Next Action": "Run git status --short --branch, resolve remote sync, then rerun public-check before posting.",
            "Completion Gate": "GitHub branch is synced and public gates pass.",
        }
    if "ahead" in lowered:
        return {
            "State": "needs_github_sync",
            "Evidence": f"Public share gates may pass, but git status is {line}; push reviewed local commits before sharing the GitHub link.",
            "Next Action": "Run git push origin main after confirming no generated churn is staged, then rerun public-check.",
            "Completion Gate": "GitHub includes the latest reviewed local commit and public gates pass.",
        }
    return {
        "State": "ready_for_manual_share",
        "Evidence": "Public share gates pass; GitHub is synced; use GitHub link and curated screenshot.",
        "Next Action": "Post or update LinkedIn manually using docs/LINKEDIN_PROJECT_BRIEF.md.",
        "Completion Gate": "LinkedIn profile/card is updated by the account owner.",
    }


def _public_ux_review_status_for_root(project_root: Path) -> dict[str, Any] | None:
    """Read local UX notes only for the active checkout, not temp test fixtures."""
    try:
        if project_root.resolve() != Path.cwd().resolve():
            return None
        return public_ux_review_notes_status()
    except Exception:
        return None


def _public_ux_stage_from_status(status: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(status, dict):
        return {
            "State": "ready_for_live_review",
            "Evidence": (
                "Browser QA evidence is ready; public workflow is Home -> Stock Selector -> "
                "Single-Stock Report -> Data Health -> Proof History."
            ),
            "Next Action": (
                "Run make public-ux-review-checklist-json for the machine-readable five-page contract "
                "and make public-ux-review-notes-check for pending note rows, then run a live "
                "desktop/mobile review and polish first viewport spacing or unclear Data Health wording only."
            ),
        }
    gate = str(status.get("share_review_gate") or "").strip()
    if gate == "share_review_ready":
        counts = status.get("classification_counts") if isinstance(status.get("classification_counts"), dict) else {}
        resolved = sum(
            int(counts.get(classification) or 0) for classification in SUCCESSFUL_REVIEW_CLASSIFICATIONS
        )
        total = int(status.get("expected_rows") or resolved)
        return {
            "State": "share_review_ready",
            "Evidence": f"{resolved}/{total} public desktop/mobile review rows resolved; public UX notes gate is share_review_ready.",
            "Next Action": "Rerun make public-ux-review-notes-check after UI copy, layout, or route changes.",
        }
    if gate == "review_limited":
        return {
            "State": "review_limited",
            "Evidence": "Public UX review notes have no pending rows, but at least one row is environment-limited or deferred.",
            "Next Action": str(status.get("next_limited_command") or "make public-ux-review-notes-check"),
        }
    pending = int(status.get("pending_rows") or 0)
    return {
        "State": "ready_for_live_review",
        "Evidence": f"Public UX review notes still have {pending} pending desktop/mobile route row(s).",
        "Next Action": str(status.get("next_safe_command") or "make public-ux-review-notes-check"),
    }


def _hosted_demo_url_for_root(root: Path) -> str:
    return read_hosted_demo_url(root)


def _workflow_continuation_from_stage_rows(rows: list[dict[str, str]]) -> dict[str, str]:
    """Keep external dependencies visible without treating the roadmap as terminal."""
    pending_states = {
        "awaiting_external_setup",
        "awaiting_reviewed_source",
        "awaiting_source_change",
    }
    pending_rows = [row for row in rows if str(row.get("State") or "").strip() in pending_states]
    if pending_rows:
        stages = ", ".join(str(row.get("Stage") or "Next stage") for row in pending_rows)
        return {
            "State": "continue_with_pending_dependencies",
            "Evidence": f"{len(pending_rows)} dependency-backed stage(s) are pending: {stages}.",
            "Next Action": "Continue any executable product/share work; resume each pending stage only when its external setup, reviewed source, or source change arrives.",
        }
    return {
        "State": "continue_with_current_stage_map",
        "Evidence": "Current stages are classified without a pending external setup or source-change dependency.",
        "Next Action": "Use the first applicable stage action and keep the existing source-proof gates intact.",
    }


def _remaining_public_stage_rows(
    summary: dict[str, Any],
    *,
    source_operator_summary: dict[str, Any] | None = None,
    trusted_data_pilot_has_candidates: bool | None = None,
    price_coverage_complete: bool = False,
    git_status_line: str | None = None,
    public_ux_review_status: dict[str, Any] | None = None,
    hosted_demo_url: str | None = None,
) -> list[dict[str, str]]:
    """Classify the remaining public/product stages without unlocking data."""
    source_operator_summary = source_operator_summary if isinstance(source_operator_summary, dict) else {}
    needs_setup = [
        str(item).strip().lower()
        for item in source_operator_summary.get("needs_setup", [])
        if str(item).strip()
    ]
    avoid_repeating = [
        str(item).strip().lower()
        for item in source_operator_summary.get("avoid_repeating", [])
        if str(item).strip()
    ]
    first_setup = _source_operator_first_setup_guidance(source_operator_summary)
    total = int(summary.get("tickers_total") or 0)
    with_prices = int(summary.get("tickers_with_prices") or 0)
    price_ready = int(summary.get("tickers_price_ready") or with_prices)
    momentum_ready = int(summary.get("tickers_usable_for_momentum") or 0)
    fundamentals_ready = int(summary.get("tickers_fundamentals_ready") or 0)
    dcf_ready = int(summary.get("tickers_dcf_ready") or 0)
    peer_ready = int(summary.get("tickers_peer_ready") or 0)
    locked_inputs = int(summary.get("data_gaps") or 0)
    optional_locked = int(summary.get("data_sources_optional_locked") or 0)

    fmp_missing = "fmp" in needs_setup
    first_provider = first_setup.get("setup_env") or "FMP_API_KEY"
    source_queues_exhausted = trusted_data_pilot_has_candidates is False and price_coverage_complete
    avoid_source_ladder = "fundamentals_share_count_source_ladder" in avoid_repeating
    linkedin_stage = _linkedin_stage_from_git_status(git_status_line)
    public_ux_stage = _public_ux_stage_from_status(public_ux_review_status)
    hosted_demo_url = str(hosted_demo_url or "").strip()
    hosted_stage = {
        "State": "manual_verify_required" if hosted_demo_url else "awaiting_external_setup",
        "Diagnostic State": "manual_verify_required" if hosted_demo_url else "external_account_required",
        "Evidence": (
            f"Hosted URL marker is configured: {hosted_demo_url}. It still needs live public-flow verification."
            if hosted_demo_url
            else "No public hosted Streamlit URL is configured in this repository."
        ),
        "Next Action": (
            "Open the hosted public URL, verify Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History, then rerun public gates."
            if hosted_demo_url
            else "Deploy only after an external host/account is chosen and docs/HOSTED_DEMO_DEPLOYMENT.md is followed."
        ),
        "Completion Gate": (
            "Hosted URL opens, public-check and browser QA evidence pass, and README/LinkedIn wording is updated."
            if hosted_demo_url
            else "Hosted URL opens, public gates pass against that route, and README/LinkedIn wording is updated."
        ),
    }

    rows: list[dict[str, str]] = [
        {
            "Stage": "LinkedIn publish",
            "State": linkedin_stage["State"],
            "Evidence": linkedin_stage["Evidence"],
            "Next Action": linkedin_stage["Next Action"],
            "Completion Gate": linkedin_stage["Completion Gate"],
            "Boundary": "Manual LinkedIn action only; repo cannot edit the external profile.",
        },
        {
            "Stage": "Hosted Streamlit demo",
            "State": hosted_stage["State"],
            "Diagnostic State": hosted_stage["Diagnostic State"],
            "Evidence": hosted_stage["Evidence"],
            "Next Action": hosted_stage["Next Action"],
            "Completion Gate": hosted_stage["Completion Gate"],
            "Boundary": "Do not claim a hosted app exists until the URL is deployed and verified.",
        },
        {
            "Stage": "FMP provider activation",
            "State": "awaiting_external_setup" if fmp_missing else "configured_smoke_required",
            "Diagnostic State": "external_key_required" if fmp_missing else "configured_smoke_required",
            "Evidence": (
                "FMP_API_KEY is not configured."
                if fmp_missing
                else "FMP_API_KEY appears configured; provider setup still needs a reviewed one-ticker smoke."
            ),
            "Next Action": (
                "Set FMP_API_KEY outside the repo, then run one reviewed ticker smoke."
                if fmp_missing
                else "Run make fmp-smoke TICKER=<ticker>."
            ),
            "Completion Gate": (
                f"{first_provider} is configured locally; one ticker validates, previews narrowly, has zero rejected rows, and source provenance is present."
            ),
            "Boundary": "Provider setup is not data proof and must not start a broad batch by itself.",
        },
        {
            "Stage": "Peer readiness upgrade",
            "State": "awaiting_reviewed_source" if peer_ready < max(dcf_ready, 1) else "ready",
            "Diagnostic State": "source_gated" if peer_ready < max(dcf_ready, 1) else "ready",
            "Evidence": f"{peer_ready}/{total} peer-ready; source-backed peer mappings remain the biggest analysis-depth gap.",
            "Next Action": "Use source-backed peer mapping rows only; keep candidate peers as context until reviewed.",
            "Completion Gate": "Trusted peer rows validate, preview, apply intentionally, rebuild readiness, and update proof history.",
            "Boundary": "Do not infer trusted peers from sector labels, market cap, price, or model guesses.",
        },
        {
            "Stage": "Optional earnings and estimates",
            "State": "awaiting_reviewed_source" if optional_locked or locked_inputs else "ready",
            "Diagnostic State": "locked_until_trusted_rows" if optional_locked or locked_inputs else "ready",
            "Evidence": f"{optional_locked} optional/manual lane(s) locked; {locked_inputs} locked input row(s) visible.",
            "Next Action": "Use optional-context source ladder or reviewed local rows; date-only or target-only rows stay candidate context.",
            "Completion Gate": "Supported earnings or estimate fields pass validate, preview, apply, readiness rebuild, and proof recording.",
            "Boundary": "Do not infer earnings, analyst estimates, targets, or recommendations.",
        },
        {
            "Stage": "Source-proof queues",
            "State": "awaiting_source_change" if source_queues_exhausted or avoid_source_ladder else "check_project_status",
            "Diagnostic State": "exhausted_do_not_retry" if source_queues_exhausted or avoid_source_ladder else "check_project_status",
            "Evidence": (
                "Current proof queues have no unreviewed executable company candidates."
                if source_queues_exhausted or avoid_source_ladder
                else "Project status decides whether current proof candidates are executable."
            ),
            "Next Action": "Use provider setup or changed source-backed rows before reopening broad proof loops.",
            "Completion Gate": "New provider data, reviewed manual rows, changed blockers, or executable company candidates appear.",
            "Boundary": "Do not repeat broad fundamentals/share-count loops just because sources are reachable.",
        },
        {
            "Stage": "Coverage depth",
            "State": "ready_with_known_gaps" if price_coverage_complete else "price_gap_remaining",
            "Evidence": (
                f"price rows {with_prices}/{total}; setup-ready prices {price_ready}/{total}; momentum {momentum_ready}/{total}; "
                f"fundamentals {fundamentals_ready}/{total}; DCF {dcf_ready}/{total}; peer {peer_ready}/{total}."
            ),
            "Next Action": "Prioritize provider activation and peer/optional proof; do not rerun broad price coverage unless it regresses.",
            "Completion Gate": "Every lane is ready or truthfully supported, still_blocked, skipped, excluded, or candidate_context_only.",
            "Boundary": "Coverage counts are readiness evidence, not investment conclusions.",
        },
        {
            "Stage": "Public UX polish",
            "State": public_ux_stage["State"],
            "Evidence": public_ux_stage["Evidence"],
            "Next Action": public_ux_stage["Next Action"],
            "Completion Gate": "Five public pages remain clear, mobile-safe, and raw operations stay behind Advanced.",
            "Boundary": "Do not expand data coverage or add providers during UX polish.",
        },
        {
            "Stage": "Generated artifacts",
            "State": "excluded_by_default",
            "Evidence": "Generated CSV/report/sample-report churn is local working data unless individually reviewed.",
            "Next Action": "Keep broad generated churn unstaged; stage only exact reviewed evidence artifacts.",
            "Completion Gate": "make diff-hygiene-summary shows product package clean or only intentional reviewed files staged.",
            "Boundary": "Do not use git add -A for this repo.",
        },
    ]
    return rows


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
    had_actions_before_review_filter = bool(normalized_actions)
    reviewed_non_actionable_price_tickers = _reviewed_non_actionable_price_tickers(
        root,
        _price_action_tickers(normalized_actions),
    )
    reviewed_non_actionable_fundamentals_tickers = _reviewed_non_actionable_dcf_tickers(root).intersection(
        _fundamentals_action_tickers(normalized_actions)
    )
    reviewed_non_actionable_peer_tickers = _reviewed_non_actionable_peer_tickers(
        root,
        _peer_action_tickers(normalized_actions),
    )
    dcf_source_ladder_has_unreviewed = _dcf_source_ladder_has_unreviewed_rows(root, data_path)
    trusted_data_pilot_has_candidates = _trusted_data_pilot_has_candidates(root, top_n=top_n)
    optional_context_covered = _optional_context_ledger_covers_current_universe(root, len(readiness))
    normalized_actions = _drop_reviewed_non_actionable_price_actions(root, normalized_actions)
    normalized_actions = _drop_reviewed_non_actionable_fundamentals_actions(root, normalized_actions)
    normalized_actions = _drop_reviewed_non_actionable_peer_actions(root, normalized_actions)
    if dcf_source_ladder_has_unreviewed is False:
        normalized_actions = _drop_all_fundamentals_actions(normalized_actions)
    if optional_context_covered:
        normalized_actions = _drop_optional_context_actions(normalized_actions)
    normalized_actions = _drop_preview_available_source_actions(normalized_actions)
    sorted_actions = sorted(normalized_actions, key=_action_rank)
    problem_sources = [row for row in sources if str(row.get("availability_status")) in PROBLEM_SOURCE_STATUSES]
    required_problem_sources = [row for row in problem_sources if _source_needs_required_attention(row)]
    optional_locked_sources = [row for row in problem_sources if _source_is_optional_locked(row)]
    purpose_evaluation_rows = [] if allowed else _load_purpose_evaluation_summary(output_path, top_n)

    def readiness_count(field: str) -> int:
        if readiness.empty or field not in readiness.columns:
            return 0
        return int(_truthy_series(readiness[field]).sum())

    summary = {
        "data_sources_total": len(sources),
        "data_sources_available": sum(1 for row in sources if row.get("availability_status") == "available"),
        "data_sources_needing_attention": len(required_problem_sources),
        "data_sources_optional_locked": len(optional_locked_sources),
        "data_gaps": len(gaps),
        "tickers_total": len(readiness),
        "tickers_with_prices": _count_tickers_with_price_rows(data_path, allowed) or readiness_count("price_ready"),
        "tickers_price_ready": readiness_count("price_ready"),
        "tickers_usable_for_momentum": readiness_count("momentum_ready"),
        "tickers_fundamentals_ready": readiness_count("fundamentals_ready"),
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
    price_complete = _price_coverage_complete(summary)
    command_rows = _drop_stale_missing_price_batch_rows(
        command_rows,
        price_coverage_complete=price_complete,
    )
    command_rows = _drop_reviewed_non_actionable_price_rows(
        command_rows,
        reviewed_non_actionable_price_tickers,
    )
    command_rows = _drop_reviewed_non_actionable_fundamentals_rows(
        command_rows,
        reviewed_non_actionable_fundamentals_tickers,
    )
    command_rows = _drop_reviewed_non_actionable_peer_rows(
        command_rows,
        reviewed_non_actionable_peer_tickers,
    )
    if dcf_source_ladder_has_unreviewed is False:
        command_rows = _drop_all_fundamentals_actions(command_rows)
    if optional_context_covered:
        command_rows = _drop_optional_context_actions(command_rows)
    if allowed:
        command_rows = _recommended_next_command_rows(
            sorted_actions,
            bundles,
            [],
            price_coverage_complete=price_complete,
            include_guided_batches=_include_guided_batches(
                sorted_actions,
                had_actions_before_review_filter=had_actions_before_review_filter,
                dcf_source_ladder_has_unreviewed=dcf_source_ladder_has_unreviewed,
            ),
            include_trusted_data_pilot=(
                trusted_data_pilot_has_candidates is not False
                and (bool(sorted_actions) or dcf_source_ladder_has_unreviewed is not False)
            ),
        )
    if not command_rows:
        command_rows = _recommended_next_command_rows(
            sorted_actions,
            bundles,
            [] if allowed else problem_sources,
            price_coverage_complete=price_complete,
            include_guided_batches=_include_guided_batches(
                sorted_actions,
                had_actions_before_review_filter=had_actions_before_review_filter,
                dcf_source_ladder_has_unreviewed=dcf_source_ladder_has_unreviewed,
            ),
            include_trusted_data_pilot=(
                trusted_data_pilot_has_candidates is not False
                and (bool(sorted_actions) or dcf_source_ladder_has_unreviewed is not False)
            ),
        )
    elif not allowed and not any(
        str(row.get("Command") or "").strip() == TRUSTED_DATA_PILOT_CANDIDATES_COMMAND
        for row in command_rows
    ) and trusted_data_pilot_has_candidates is not False and (
        bool(sorted_actions) or dcf_source_ladder_has_unreviewed is not False
    ):
        command_rows.append(_trusted_data_pilot_command_row())
    if dcf_source_ladder_has_unreviewed is False:
        command_rows = _ensure_exhausted_source_scope_rows(command_rows)
    command_rows = _prioritize_public_command_rows(command_rows)
    command_rows = _pivot_to_provider_setup_when_trusted_candidates_empty(
        command_rows,
        trusted_data_pilot_has_candidates=trusted_data_pilot_has_candidates,
        price_coverage_complete=price_complete,
    )

    remaining_stage_rows = _remaining_public_stage_rows(
        summary,
        source_operator_summary=_load_source_operator_summary(output_path),
        trusted_data_pilot_has_candidates=trusted_data_pilot_has_candidates,
        price_coverage_complete=price_complete,
        git_status_line=_git_status_line(root),
        public_ux_review_status=_public_ux_review_status_for_root(root),
        hosted_demo_url=_hosted_demo_url_for_root(root),
    )
    workflow_continuation = _workflow_continuation_from_stage_rows(remaining_stage_rows)
    return {
        "project_root": str(root),
        "data_dir": str(data_path),
        "outputs_dir": str(output_path),
        "summary": summary,
        "data_sources_needing_attention": required_problem_sources[:top_n],
        "data_sources_optional_locked": optional_locked_sources[:top_n],
        "top_data_gaps": gaps[:top_n],
        "top_onboarding_actions": sorted_actions[:top_n],
        "recommended_next_command_rows": command_rows,
        "recommended_next_commands": [row["Command"] for row in command_rows if row.get("Command")],
        "remaining_public_stage_rows": remaining_stage_rows,
        "workflow_continuation": workflow_continuation,
        "purpose_evaluation_summary": purpose_evaluation_rows,
        "source_operator_summary": _load_source_operator_summary(output_path),
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
        command = str(row.get("focus_command") or row.get("example_command") or row.get("Command") or "").strip()
        dataset = str(row.get("dataset") or "").strip().lower()
        if dataset == "smh_holdings" and command in {"make universe-preview", "make universe-preview-summary"}:
            return "preview available; apply only if canonical preview shows new or updated rows"
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


def _dataset_display_name(value: object) -> str:
    dataset = str(value or "data").strip()
    names = {
        "smh_holdings": "SMH holdings",
        "sp500_constituents": "S&P 500 constituents",
        "nasdaq_symbols": "Nasdaq symbols",
    }
    return names.get(dataset.lower(), dataset.replace("_", " "))


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


def _import_review_reason(file_text: str, dataset_text: str) -> str:
    """Describe import-file review without making apply sound automatic."""

    return (
        f"Local import files already have rows in {file_text}. "
        "Run make imports-validate, then make imports-preview; apply only after validation passes, "
        "preview scope is intended, and rejected rows are zero. Then make status to confirm the live local "
        f"{dataset_text} inputs."
    )


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
            datasets = [_dataset_display_name(row.get("dataset")) for row in grouped]
            target_files = [
                _first_non_empty(row.get("target_file"), row.get("local_file"))
                for row in grouped
                if _first_non_empty(row.get("target_file"), row.get("local_file"))
            ]
            dataset_text = " and ".join(datasets[:-1] + [datasets[-1]]) if len(datasets) <= 2 else ", ".join(datasets[:-1]) + f", and {datasets[-1]}"
            file_text = " and ".join(target_files[:-1] + [target_files[-1]]) if len(target_files) <= 2 else ", ".join(target_files[:-1]) + f", and {target_files[-1]}"
            reason = _import_review_reason(file_text, dataset_text)
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
        dataset = _dataset_display_name(row.get("dataset"))
        status = str(row.get("availability_status") or "").strip().lower()
        if command == "make imports-validate":
            step = f"Review {dataset} import file"
        elif status == "manual_only":
            step = f"Prepare {dataset} input"
        else:
            step = f"Advance {dataset} source"
        reason = _first_non_empty(row.get("fallback_action"), row.get("validation_warnings"), row.get("notes"))
        if command == "make imports-validate":
            reason = _import_review_reason(_source_context(row), dataset)
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
            "evidence loop instead of trying to make the full universe analysis-ready at once."
        ),
        source_context="trusted local CSVs plus SEC/manual review paths",
        freshness_context="read-only ranking; run before importing trusted fundamentals or peer rows",
    )


def _workflow_evidence_command_row() -> dict[str, str]:
    return _command_row(
        "Review provider setup checklist",
        "make provider-setup-checklist",
        (
            "Current source-proof queues have no unreviewed executable company candidates. "
            "Review provider setup states, source boundaries, and validate/preview/apply gates before repeating "
            "the trusted-data pilot loop."
        ),
        source_context="source activation guide, project status, proof ledger, and source preflight",
        freshness_context=(
            "source setup evidence only; no import/apply step is available from the current queue"
        ),
    )


def _trusted_data_pilot_has_candidates(root: Path, *, top_n: int = 10) -> bool | None:
    required_paths = [
        root / "outputs" / "fundamentals_peer_worklist.csv",
        root / "outputs" / "peer_unlock_worklist.csv",
        root / "data" / "reports" / "ticker_readiness_report.csv",
    ]
    if not all(path.exists() for path in required_paths):
        return None
    try:
        return bool(load_trusted_data_pilot_candidates(root=root, top_n=top_n))
    except Exception:
        return None


def _scope_and_risk_context_command_rows() -> list[dict[str, str]]:
    return [
        _command_row(
            "Choose safe universe scope",
            "make universe-scope TOP_N=10",
            (
                "When source-proof queues are exhausted, choose active-universe, ticker-list, sector/theme, "
                "ready-only, or missing-data scope before opening broad tables or risk context."
            ),
            source_context="ticker readiness report and universe scope runbook",
            freshness_context="copy-only scope guide; does not refresh, import, apply, or infer missing values",
        ),
        _command_row(
            "Review risk context readiness",
            "make risk-context",
            (
                "Choose scope before treating liquidity, correlation, or proxy-risk rows as usable context. "
                "Risk context is not a research conclusion and does not unlock missing fundamentals, peers, earnings, or estimates."
            ),
            source_context="outputs/liquidity_risk.csv and outputs/correlation_risk.csv",
            freshness_context="read-only risk context; not a research conclusion or source-proof unlock",
        ),
    ]


def _ensure_exhausted_source_scope_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return rows
    commands = [str(row.get("Command") or "").strip() for row in rows]
    if "make provider-setup-checklist" not in commands:
        return rows
    wanted = _scope_and_risk_context_command_rows()
    wanted_commands = {str(row.get("Command") or "").strip() for row in wanted}
    filtered = [
        row
        for row in rows
        if str(row.get("Command") or "").strip() not in wanted_commands
    ]
    insert_at = next(
        (
            index + 1
            for index, row in enumerate(filtered)
            if str(row.get("Command") or "").strip() == "make provider-setup-checklist"
        ),
        1,
    )
    return [*filtered[:insert_at], *wanted, *filtered[insert_at:]]


def _pivot_to_provider_setup_when_trusted_candidates_empty(
    rows: list[dict[str, str]],
    *,
    trusted_data_pilot_has_candidates: bool | None,
    price_coverage_complete: bool,
) -> list[dict[str, str]]:
    if trusted_data_pilot_has_candidates is not False or not price_coverage_complete:
        return rows
    workflow_row = _workflow_evidence_command_row()
    scope_rows = _scope_and_risk_context_command_rows()
    suppressed_commands = {
        TRUSTED_DATA_PILOT_CANDIDATES_COMMAND,
        "make provider-setup-checklist",
        *{row["Command"] for row in scope_rows},
    }
    remaining = [
        row
        for row in rows
        if str(row.get("Command") or "").strip() not in suppressed_commands
    ]
    return [workflow_row, *scope_rows, *remaining]


def _price_coverage_complete(summary: dict[str, Any]) -> bool:
    total = int(summary.get("tickers_total") or 0)
    with_prices = int(summary.get("tickers_with_prices") or 0)
    return total > 0 and with_prices >= total


def _drop_stale_missing_price_batch_rows(
    rows: list[dict[str, str]],
    *,
    price_coverage_complete: bool,
) -> list[dict[str, str]]:
    if not price_coverage_complete:
        return rows
    return [
        row
        for row in rows
        if str(row.get("Command") or "").strip() != "make price-refresh-loop DRY_RUN=1"
    ]


def _price_action_tickers(actions: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("ticker") or "").strip().upper()
        for row in actions
        if str(row.get("dataset") or "").strip().lower() == "prices"
        and str(row.get("ticker") or "").strip()
    }


def _command_row_ticker(row: dict[str, Any]) -> str:
    for value in (row.get("Command"), row.get("Step"), row.get("Reason")):
        match = re.search(r"\bTICKER=([A-Z][A-Z0-9.-]{0,9})\b", str(value or "").upper())
        if match:
            return match.group(1).replace(".", "-")
    return ""


def _drop_reviewed_non_actionable_price_rows(
    rows: list[dict[str, str]],
    reviewed_tickers: set[str],
) -> list[dict[str, str]]:
    if not reviewed_tickers:
        return rows
    filtered: list[dict[str, str]] = []
    for row in rows:
        command = str(row.get("Command") or "").strip()
        ticker = _command_row_ticker(row)
        if command.startswith("make focus-price") and ticker in reviewed_tickers:
            continue
        filtered.append(row)
    return filtered


def _drop_reviewed_non_actionable_price_actions(
    root: Path,
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    possible_tickers = _price_action_tickers(actions)
    reviewed_tickers = _reviewed_non_actionable_price_tickers(root, possible_tickers)
    if not reviewed_tickers:
        return actions
    return [
        row
        for row in actions
        if not (
            str(row.get("dataset") or "").strip().lower() == "prices"
            and str(row.get("ticker") or "").strip().upper() in reviewed_tickers
        )
    ]


def _fundamentals_action_tickers(actions: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("ticker") or "").strip().upper()
        for row in actions
        if str(row.get("dataset") or "").strip().lower() in {"fundamentals", "share_count", "shares_outstanding"}
        and str(row.get("ticker") or "").strip()
    }


def _drop_reviewed_non_actionable_fundamentals_rows(
    rows: list[dict[str, str]],
    reviewed_tickers: set[str],
) -> list[dict[str, str]]:
    if not reviewed_tickers:
        return rows
    filtered: list[dict[str, str]] = []
    for row in rows:
        command = str(row.get("Command") or "").strip()
        ticker = _command_row_ticker(row)
        if command.startswith("make focus-fundamentals") and ticker in reviewed_tickers:
            continue
        filtered.append(row)
    return filtered


def _drop_reviewed_non_actionable_fundamentals_actions(
    root: Path,
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    possible_tickers = _fundamentals_action_tickers(actions)
    if not possible_tickers:
        return actions
    reviewed_tickers = _reviewed_non_actionable_dcf_tickers(root).intersection(possible_tickers)
    if not reviewed_tickers:
        return actions
    return [
        row
        for row in actions
        if not (
            str(row.get("dataset") or "").strip().lower() in {"fundamentals", "share_count", "shares_outstanding"}
            and str(row.get("ticker") or "").strip().upper() in reviewed_tickers
        )
    ]


def _drop_all_fundamentals_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        command = str(row.get("Command") or row.get("focus_command") or row.get("example_command") or "").strip()
        dataset = str(row.get("dataset") or "").strip().lower()
        if dataset in {"fundamentals", "share_count", "shares_outstanding"}:
            continue
        if command.startswith("make focus-fundamentals"):
            continue
        filtered.append(row)
    return filtered


def _peer_action_tickers(actions: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("ticker") or "").strip().upper().replace(".", "-")
        for row in actions
        if str(row.get("dataset") or "").strip().lower() == "peers"
        and str(row.get("ticker") or "").strip()
    }


def _reviewed_non_actionable_peer_tickers(root: Path, possible_tickers: set[str]) -> set[str]:
    path = root / "data" / "reviewed_batch_proofs.csv"
    if not path.exists() or not possible_tickers:
        return set()
    reviewed: set[str] = set()
    rows = _read_csv_records(path)
    lanes = {"peers", "peer_mapping"}
    outcomes = {"candidate_context_only", "still_blocked", "skipped", "excluded"}
    for row in rows:
        if str(row.get("lane") or "").strip().lower() not in lanes:
            continue
        if str(row.get("final_outcome") or "").strip().lower() not in outcomes:
            continue
        text = " ".join(str(row.get(name) or "") for name in ("tickers", "changed_tickers", "notes")).upper()
        for token in re.findall(r"\b[A-Z][A-Z0-9.]{0,9}\b", text):
            ticker = token.replace(".", "-")
            if ticker in possible_tickers:
                reviewed.add(ticker)
    return reviewed


def _drop_reviewed_non_actionable_peer_rows(
    rows: list[dict[str, str]],
    reviewed_tickers: set[str],
) -> list[dict[str, str]]:
    if not reviewed_tickers:
        return rows
    filtered: list[dict[str, str]] = []
    for row in rows:
        command = str(row.get("Command") or "").strip()
        ticker = _command_row_ticker(row)
        if command.startswith("make focus-peers") and ticker in reviewed_tickers:
            continue
        filtered.append(row)
    return filtered


def _drop_reviewed_non_actionable_peer_actions(
    root: Path,
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    possible_tickers = _peer_action_tickers(actions)
    reviewed_tickers = _reviewed_non_actionable_peer_tickers(root, possible_tickers)
    if not reviewed_tickers:
        return actions
    return [
        row
        for row in actions
        if not (
            str(row.get("dataset") or "").strip().lower() == "peers"
            and str(row.get("ticker") or "").strip().upper().replace(".", "-") in reviewed_tickers
        )
    ]


def _optional_context_ledger_covers_current_universe(root: Path, expected_count: int) -> bool:
    if expected_count <= 0:
        return False
    summary = build_reviewed_batch_ledger_summaries(root).get("optional_context")
    if summary is None:
        return False
    return summary.unique_ticker_count >= expected_count


def _is_optional_context_action(row: dict[str, Any]) -> bool:
    dataset = str(row.get("dataset") or "").strip().lower()
    if dataset in {"earnings", "analyst_estimates", "analyst estimates", "optional_context"}:
        return True
    command = str(row.get("Command") or row.get("focus_command") or row.get("example_command") or "").strip()
    step = str(row.get("Step") or "").strip().lower()
    return command == "make templates" and any(token in step for token in ("earnings", "analyst", "optional"))


def _drop_optional_context_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not _is_optional_context_action(row)]


def _is_preview_available_source_action(row: dict[str, Any]) -> bool:
    dataset = str(row.get("dataset") or "").strip().lower()
    status = str(row.get("status") or "").strip().lower()
    command = str(row.get("focus_command") or row.get("example_command") or row.get("Command") or "").strip()
    return dataset == "smh_holdings" and status == "preview_available" and command in {
        "make universe-preview",
        "make universe-preview-summary",
    }


def _drop_preview_available_source_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not _is_preview_available_source_action(row)]


def _drop_optional_context_problem_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row.get("dataset") or "").strip().lower()
        not in {"earnings", "analyst_estimates", "analyst estimates", "optional_context"}
    ]


def _dcf_source_ladder_has_unreviewed_rows(root: Path, data_path: Path) -> bool | None:
    universe_path = data_path / "universe_master.csv"
    if not universe_path.exists():
        universe_path = data_path / "universe.csv"
    if not universe_path.exists() or not (data_path / "fundamentals.csv").exists() or not (data_path / "prices.csv").exists():
        return None
    try:
        rows = build_dcf_input_proof_queue_from_files(root, data_dir=data_path, top_n=10)
    except Exception:
        return None
    return any(
        "reviewed proof ledger already records" not in str(getattr(row, "source_note", "") or "").lower()
        for row in rows
    )


def _include_guided_batches(
    actions: list[dict[str, Any]],
    *,
    had_actions_before_review_filter: bool,
    dcf_source_ladder_has_unreviewed: bool | None,
) -> bool:
    if dcf_source_ladder_has_unreviewed is False:
        return False
    return bool(actions) or not had_actions_before_review_filter


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
    *,
    price_coverage_complete: bool = False,
    include_guided_batches: bool = True,
    include_trusted_data_pilot: bool = True,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    if actions:
        top_action = actions[0]
        dataset_key = str(top_action.get("dataset") or "").strip().lower()
        if dataset_key == "prices" and not bool(top_action.get("is_holding")) and not price_coverage_complete:
            rows.append(
                _command_row(
                    "Preview next capped missing-price batch",
                    "make price-refresh-loop DRY_RUN=1",
                    (
                        "Preview the broad-universe price frontier first; PROVIDER=auto tries Stooq, Yahoo, "
                        "and configured FMP/Alpha Vantage/Finnhub before the manual import file fallback."
                    ),
                    source_context=(
                        "PROVIDER=auto price ladder with Stooq, Yahoo, optional IBKR read-only, and configured FMP/Alpha Vantage/Finnhub fallbacks; "
                        "data/imports/prices.csv remains the last manual fallback"
                    ),
                    freshness_context="dry-run first; verify source readiness notes and local CSV changes after any refresh",
                )
            )
        command = _first_non_empty(top_action.get("focus_command"), top_action.get("example_command"))
        if command:
            dataset = str(top_action.get("dataset") or "data").replace("_", " ")
            ticker = _first_non_empty(top_action.get("ticker"))
            if dataset_key == "prices" and price_coverage_complete:
                step = "Review short price-history blocker" + (f" ({ticker})" if ticker else "")
            elif dataset_key in {"earnings", "analyst_estimates"}:
                step = "Dry-run optional context source ladder" + (f" ({ticker})" if ticker else "")
                command = "make optional-context-source-ladder-queue TOP_N=10"
            else:
                step = f"Fix top {dataset} blocker" + (f" ({ticker})" if ticker else "")
            reason = _first_non_empty(top_action.get("reason"), top_action.get("recommended_action"))
            source_context = _source_context(top_action)
            freshness_context = _freshness_context(top_action)
            if dataset_key in {"earnings", "analyst_estimates"}:
                reason = (
                    f"{reason} Use the optional source ladder before templates; provider-assisted date-only or "
                    "target-only rows can be candidate context but do not unlock optional readiness without "
                    "supported fields and validate/preview/apply gates."
                ).strip()
                source_context = (
                    "optional context source ladder with yfinance and configured FMP/Alpha Vantage/Finnhub fallbacks; "
                    "local import templates only after a trusted source row exists"
                )
                freshness_context = (
                    "dry-run first; candidate_context_only rows remain locked until supported fields validate, "
                    "preview cleanly, and are intentionally applied"
                )
            rows.append(
                _command_row(
                    step,
                    command,
                    reason,
                    source_context=source_context,
                    freshness_context=freshness_context,
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

    top_bundle = _select_top_bundle(actions, bundles) if include_guided_batches else None
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

    if include_trusted_data_pilot:
        rows.append(_trusted_data_pilot_command_row())
    elif not rows:
        rows.append(_workflow_evidence_command_row())
    if not include_trusted_data_pilot:
        rows.extend(_scope_and_risk_context_command_rows())

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
    source_payload: dict[str, Any] | None = None,
    onboarding_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root)
    data_path = resolve_data_dir(data_dir, root)
    output_path = resolve_outputs_dir(output_dir, root)
    source_payload = source_payload or build_data_source_payload(root, data_dir=data_path, output_dir=output_path)
    onboarding_payload = onboarding_payload or build_onboarding_payload(root, data_dir=data_path, output_dir=output_path)
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
    had_actions_before_review_filter = bool(enriched_actions)
    dcf_source_ladder_has_unreviewed = _dcf_source_ladder_has_unreviewed_rows(root, data_path)
    trusted_data_pilot_has_candidates = _trusted_data_pilot_has_candidates(root, top_n=top_n)
    optional_context_covered = _optional_context_ledger_covers_current_universe(root, len(coverage))
    filtered_actions = _drop_reviewed_non_actionable_price_actions(root, enriched_actions)
    filtered_actions = _drop_reviewed_non_actionable_fundamentals_actions(root, filtered_actions)
    filtered_actions = _drop_reviewed_non_actionable_peer_actions(root, filtered_actions)
    if dcf_source_ladder_has_unreviewed is False:
        filtered_actions = _drop_all_fundamentals_actions(filtered_actions)
    if optional_context_covered:
        filtered_actions = _drop_optional_context_actions(filtered_actions)
    filtered_actions = _drop_preview_available_source_actions(filtered_actions)
    actions = sorted(filtered_actions, key=_action_rank)
    problem_sources = [row for row in sources if str(row.get("availability_status")) in PROBLEM_SOURCE_STATUSES]
    required_problem_sources = [row for row in problem_sources if _source_needs_required_attention(row)]
    optional_locked_sources = [row for row in problem_sources if _source_is_optional_locked(row)]
    command_problem_sources = [] if tickers else problem_sources
    if optional_context_covered:
        command_problem_sources = _drop_optional_context_problem_sources(command_problem_sources)
    readiness_fundamentals_ready = None if tickers else _count_readiness_true(data_path, "fundamentals_ready")
    readiness_dcf_ready = None if tickers else _count_readiness_true(data_path, "dcf_ready")
    readiness_price_ready = None if tickers else _count_readiness_true(data_path, "price_ready")
    purpose_evaluation_rows = [] if tickers else _load_purpose_evaluation_summary(output_path, top_n)
    summary = {
        "data_sources_total": len(sources),
        "data_sources_available": sum(1 for row in sources if row.get("availability_status") == "available"),
        "data_sources_needing_attention": len(required_problem_sources),
        "data_sources_optional_locked": len(optional_locked_sources),
        "data_gaps": len(gaps),
        "tickers_total": len(coverage),
        "tickers_with_prices": _count_true(coverage, "has_prices"),
        "tickers_price_ready": readiness_price_ready if readiness_price_ready is not None else _count_true(coverage, "price_ready"),
        "tickers_usable_for_momentum": _count_true(coverage, "usable_for_momentum"),
        "tickers_fundamentals_ready": (
            readiness_fundamentals_ready
            if readiness_fundamentals_ready is not None
            else _count_true(coverage, "fundamentals_ready")
        ),
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
        price_coverage_complete=_price_coverage_complete(summary),
        include_guided_batches=_include_guided_batches(
            actions,
            had_actions_before_review_filter=had_actions_before_review_filter,
            dcf_source_ladder_has_unreviewed=dcf_source_ladder_has_unreviewed,
        ),
        include_trusted_data_pilot=(
            trusted_data_pilot_has_candidates is not False
            and (bool(actions) or dcf_source_ladder_has_unreviewed is not False)
        ),
    )
    command_rows = _pivot_to_provider_setup_when_trusted_candidates_empty(
        command_rows,
        trusted_data_pilot_has_candidates=trusted_data_pilot_has_candidates,
        price_coverage_complete=_price_coverage_complete(summary),
    )
    source_operator_summary = _load_source_operator_summary(output_path)
    remaining_stage_rows = _remaining_public_stage_rows(
        summary,
        source_operator_summary=source_operator_summary,
        trusted_data_pilot_has_candidates=trusted_data_pilot_has_candidates,
        price_coverage_complete=_price_coverage_complete(summary),
        git_status_line=_git_status_line(root),
        public_ux_review_status=_public_ux_review_status_for_root(root),
        hosted_demo_url=_hosted_demo_url_for_root(root),
    )
    workflow_continuation = _workflow_continuation_from_stage_rows(remaining_stage_rows)
    return {
        "project_root": str(root),
        "data_dir": str(data_path),
        "outputs_dir": str(output_path),
        "summary": summary,
        "data_sources_needing_attention": required_problem_sources[:top_n],
        "data_sources_optional_locked": optional_locked_sources[:top_n],
        "top_data_gaps": gaps[:top_n],
        "top_onboarding_actions": actions[:top_n],
        "recommended_next_command_rows": command_rows,
        "recommended_next_commands": [row["Command"] for row in command_rows],
        "remaining_public_stage_rows": remaining_stage_rows,
        "workflow_continuation": workflow_continuation,
        "purpose_evaluation_summary": purpose_evaluation_rows,
        "source_operator_summary": source_operator_summary,
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
    source_payload = None
    onboarding_payload = None
    if refresh_supporting_outputs:
        refresh_price_update_status_output(root, output_dir=output_path)
        source_payload = write_data_source_outputs(root, data_dir=data_path, output_dir=output_path)
        onboarding_payload = write_onboarding_outputs(root, data_dir=data_path, output_dir=output_path)
        if not research_health_outputs_current(root, data_dir=data_path, output_dir=output_path):
            run_research_health(root, data_dir=data_path, output_dir=output_path)
        write_action_queue_output(
            root,
            data_dir=data_path,
            output_dir=output_path,
            refresh_research_health=False,
            source_payload=source_payload,
            onboarding_payload=onboarding_payload,
        )
    output_path.mkdir(parents=True, exist_ok=True)
    write_purpose_evaluation_summary(root, data_dir=data_path, output_dir=output_path)
    payload = build_project_status_payload(
        root,
        data_dir=data_path,
        output_dir=output_path,
        top_n=top_n,
        source_payload=source_payload,
        onboarding_payload=onboarding_payload,
    )

    json_path = output_path / PROJECT_STATUS_JSON
    summary_path = output_path / PROJECT_STATUS_SUMMARY_CSV
    top_actions_path = output_path / PROJECT_STATUS_TOP_ACTIONS_CSV
    next_steps_path = output_path / PROJECT_STATUS_NEXT_STEPS_CSV
    remaining_stages_path = output_path / PROJECT_STATUS_REMAINING_STAGES_CSV
    purpose_summary_path = output_path / PURPOSE_EVALUATION_SUMMARY_CSV

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame([payload["summary"]]).to_csv(summary_path, index=False)
    pd.DataFrame(payload["top_onboarding_actions"]).to_csv(top_actions_path, index=False)
    pd.DataFrame(payload["recommended_next_command_rows"]).to_csv(next_steps_path, index=False)
    pd.DataFrame(payload["remaining_public_stage_rows"]).to_csv(remaining_stages_path, index=False)

    return {
        **payload,
        "written_files": {
            "project_status_json": str(json_path),
            "project_status_summary": str(summary_path),
            "project_status_top_actions": str(top_actions_path),
            "project_status_next_steps": str(next_steps_path),
            "project_status_remaining_stages": str(remaining_stages_path),
            "purpose_evaluation_summary": str(purpose_summary_path),
        },
    }


def _print_human(
    payload: dict[str, Any],
    *,
    continuation_gate: ContinuationGate | None = None,
) -> None:
    summary = payload["summary"]
    warnings = list(payload.get("warnings", []))
    has_stale_snapshot_warning = any(
        "generated status artifacts may be stale" in str(warning).strip().lower()
        for warning in warnings
    )
    print("Read-only project snapshot.")
    print("Commands below are copy-only local research helpers; this status view does not run them.")
    suppress_execution = bool(continuation_gate and continuation_gate.suppress_execution)
    if continuation_gate is not None:
        print(f"Continuation gate: {continuation_gate.state}")
        if continuation_gate.next_safe_command:
            print(f"- Continuation-safe next action: {continuation_gate.next_safe_command}")
        if continuation_gate.reason:
            print(f"- Reason: {continuation_gate.reason}")
        if continuation_gate.rebuild_command:
            print(
                f"- Rebuild boundary: {continuation_gate.rebuild_command} requires an intentional reviewed write."
            )
        if continuation_gate.stop_rule:
            print(f"- Stop rule: {continuation_gate.stop_rule}")
    if has_stale_snapshot_warning:
        print("Snapshot freshness: generated snapshot may be stale; refresh before relying on exact counts.")
    for warning in warnings:
        print(f"Warning: {warning}")
    summary_label = "Project status summary"
    if has_stale_snapshot_warning:
        summary_label = f"{summary_label} (stale generated snapshot)"
    print(f"{summary_label}:")
    print(f"- Data sources: {summary['data_sources_available']}/{summary['data_sources_total']} available")
    print(f"- Required data sources needing attention: {summary['data_sources_needing_attention']}")
    source_operator_summary = payload.get("source_operator_summary", {})
    source_needs_setup = (
        [str(item).strip() for item in source_operator_summary.get("needs_setup", []) if str(item).strip()]
        if isinstance(source_operator_summary, dict)
        else []
    )
    if source_needs_setup:
        print(f"- Optional provider setup gaps: {len(source_needs_setup)} ({', '.join(source_needs_setup)})")
    print(f"- Optional/manual lanes locked: {summary.get('data_sources_optional_locked', 0)}")
    print(f"- Locked input rows: {summary['data_gaps']}")
    print(f"- Tickers with prices: {summary['tickers_with_prices']}/{summary['tickers_total']}")
    print(f"- Tickers usable for momentum: {summary['tickers_usable_for_momentum']}/{summary['tickers_total']}")
    print(f"- Fundamentals/input-ready tickers: {summary.get('tickers_fundamentals_ready', 0)}/{summary['tickers_total']}")
    print(f"- Operating-company DCF-ready tickers: {summary['tickers_dcf_ready']}/{summary['tickers_total']}")
    print(f"- Peer-ready tickers: {summary['tickers_peer_ready']}/{summary['tickers_total']}")
    print(f"- Missing-data steps: {summary['onboarding_actions']} ({summary['critical_actions']} urgent)")
    print(f"- Research-purpose groups: {summary.get('purpose_evaluation_groups', 0)} ({summary.get('purpose_evaluation_active_groups', 0)} active-universe groups)")
    command_rows = payload.get("recommended_next_command_rows") or [
        {"Step": f"Next {index}", "Command": command}
        for index, command in enumerate(payload.get("recommended_next_commands", []), start=1)
    ]
    if suppress_execution:
        command_rows = [
            {
                "Step": "Inspect stale readiness impact",
                "Command": continuation_gate.next_safe_command,
                "Reason": "Compare saved and proposed stable readiness states in memory before any reviewed rebuild decision.",
                "FreshnessContext": "Inspection only; this does not make saved readiness current.",
            }
        ]
    first_command = str(command_rows[0].get("Command") or "").strip() if command_rows else ""
    print("First read:")
    ready_label = "Ready now"
    if has_stale_snapshot_warning or suppress_execution:
        ready_label = "Ready in saved snapshot"
    print(
        f"- {ready_label}: {summary['tickers_with_prices']} with price rows, "
        f"{summary.get('tickers_fundamentals_ready', 0)} fundamentals/input-ready, "
        f"{summary['tickers_dcf_ready']} operating-company DCF-ready, "
        f"{summary['tickers_peer_ready']} peer-ready."
    )
    if has_stale_snapshot_warning:
        print("- Refresh needed: run make readiness or make status before using exact readiness counts.")
    print(
        "- Still blocked: trusted fundamentals, peer mappings, earnings, and analyst estimates "
        "stay locked where source-backed rows are missing."
    )
    if suppress_execution:
        print(
            f"- Best next proof: {continuation_gate.next_safe_command} for no-write readiness impact inspection; "
            "source and coverage execution stays paused until readiness is current or a separate reviewed rebuild is authorized."
        )
    elif first_command == "make provider-setup-checklist":
        print(
            "- Best next proof: make provider-setup-checklist for provider setup and source-boundary evidence; "
            "current source-proof queues have no unreviewed executable company candidates, so wait for new "
            "provider data, keyed sources, reviewed manual rows, or changed blockers before repeating the "
            "trusted-data pilot loop."
        )
    elif first_command == "make project-status":
        print(
            "- Best next proof: make project-status for workflow evidence; current source-proof queues have "
            "no unreviewed executable company candidates, so wait for new provider data, keyed sources, "
            "reviewed manual rows, or changed blockers before repeating the trusted-data pilot loop."
        )
    elif first_command.startswith("make focus-peers"):
        print(
            f"- Best next proof: {first_command} for the top peer-mapping blocker; "
            "add only source-backed peer rows and keep candidate peers as context until validated."
        )
    elif _price_coverage_complete(summary):
        print(
            f"- Best next proof: {TRUSTED_DATA_PILOT_CANDIDATES_COMMAND} for company-depth work; "
            "price coverage is complete, so remaining price work is short-history review, not missing-price batch planning."
        )
    else:
        print(
            f"- Best next proof: {TRUSTED_DATA_PILOT_CANDIDATES_COMMAND} for company-depth work, "
            "or make price-refresh-loop DRY_RUN=1 for price coverage planning."
        )
    if isinstance(source_operator_summary, dict) and source_operator_summary:
        needs_setup = source_needs_setup
        avoid_repeating = [
            str(item).strip()
            for item in source_operator_summary.get("avoid_repeating", [])
            if str(item).strip()
        ]
        if needs_setup:
            print(f"- Source setup to unlock more: {', '.join(needs_setup)}.")
        free_tier_limits = _source_operator_free_tier_limit_summary(source_operator_summary)
        if free_tier_limits:
            print(f"- Free-tier limits: {free_tier_limits}.")
        first_setup = _source_operator_first_setup_guidance(source_operator_summary)
        if first_setup:
            print(f"- Configure first provider: {first_setup['setup_env']}.")
            print(f"- Reviewed one-ticker smoke after setup: {first_setup['smoke_command']}.")
        if avoid_repeating:
            print(f"- Avoid repeating now: {_friendly_cli_guidance(', '.join(avoid_repeating))}.")
    print("- Details below are capped and copy-only.")
    stage_rows = payload.get("remaining_public_stage_rows") or []
    if stage_rows:
        print("Remaining public/product stages:")
        for row in stage_rows:
            stage = str(row.get("Stage") or "Next stage").strip()
            state = str(row.get("State") or "unknown").strip()
            diagnostic_state = str(row.get("Diagnostic State") or "").strip()
            next_action = str(row.get("Next Action") or "").strip()
            evidence = str(row.get("Evidence") or "").strip()
            print(f"- {stage}: {state}")
            if diagnostic_state and diagnostic_state != state:
                print(f"  diagnostic: {diagnostic_state}")
            if evidence:
                print(f"  evidence: {evidence}")
            if next_action:
                print(f"  next: {next_action}")
    workflow_continuation = payload.get("workflow_continuation") or {}
    if isinstance(workflow_continuation, dict):
        state = str(workflow_continuation.get("State") or "").strip()
        evidence = str(workflow_continuation.get("Evidence") or "").strip()
        next_action = str(workflow_continuation.get("Next Action") or "").strip()
        if state:
            print(f"Overall workflow: {state}")
        if evidence:
            print(f"  evidence: {evidence}")
        if next_action:
            print(f"  next: {next_action}")
    if not suppress_execution:
        print("Top locked inputs to review:")
        price_complete = _price_coverage_complete(summary)
        for row in payload["top_onboarding_actions"]:
            ticker = f" {row['ticker']}" if row.get("ticker") else ""
            raw_dataset_label = str(row.get("dataset") or "data")
            dataset_label = raw_dataset_label
            if dataset_label == "prices" and price_complete:
                dataset_label = "price history"
            print(f"- P{row['priority']} {dataset_label}{ticker}")
            if row.get("focus_command"):
                print(f"  suggested check: {row['focus_command']}")
            if row.get("recommended_action"):
                print(f"  guidance: {_friendly_cli_guidance(row['recommended_action'])}")
            if row.get("example_command"):
                example_label = "last manual fallback" if raw_dataset_label == "prices" else "trusted import/fallback"
                print(f"  {example_label}: {row['example_command']}")
            if row.get("credential_required"):
                present = "present" if bool(row.get("credential_present")) else "missing"
                print(f"  credential: {row['credential_required']} ({present})")
            if row.get("manual_fallback_command"):
                print(f"  fallback: {row['manual_fallback_command']}")
    print("Recommended next local steps:")
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


def main(argv: list[str] | None = None) -> None:
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
    args = parser.parse_args(argv)
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

    profile_context = build_profile_context(
        project_root=root,
        data_dir=data_path,
        output_dir=output_path,
    )
    continuation_gate = build_continuation_gate(profile_context)
    payload["continuation_gate"] = asdict(continuation_gate)
    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print(render_profile_context_text(profile_context))
    print(_format_operator_path_context(root, data_path, output_path))
    _print_human(payload, continuation_gate=continuation_gate)
    if args.write_output:
        print("Wrote:")
        for path in payload.get("written_files", {}).values():
            print(f"- {path}")


if __name__ == "__main__":
    main()
