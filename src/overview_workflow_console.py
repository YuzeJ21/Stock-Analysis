"""Pure Overview workflow card helpers.

These helpers decide the read-only command path shown on the Overview page.
The Streamlit dashboard keeps rendering concerns; this module owns command
normalization, action-queue priority cards, and workflow reason cards.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


GUIDED_BATCH_WORKFLOW_COPY = (
    "Use the guided data batch as the local import file workflow next so validation and preview safeguards stay in place."
)
GUIDED_BATCH_FIRST_COPY = (
    "Use the highest-leverage guided data batch first so price, fundamentals, or peer follow-through stays coordinated."
)


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


def _normalize_operator_command(command: object) -> str:
    command_text = _format_missing(command, "")
    if command_text == "make status":
        return "make status-check TOP_N=5"
    if command_text == "make onboarding":
        return "make status-check TOP_N=5"
    if command_text == "make dashboard":
        return "make dashboard-smoke"
    sec_stage_match = re.fullmatch(
        r"SEC_USER_AGENT=(?:'[^']*'|\"[^\"]*\"|\S+)\s+make sec-stage TICKERS=(.+)",
        command_text,
    )
    if sec_stage_match:
        tickers = ",".join(part.strip().upper() for part in sec_stage_match.group(1).split(",") if part.strip())
        if tickers:
            return f"make sec-stage TICKERS={tickers}"
    price_match = re.fullmatch(r"python3 -m src\.data_update --tickers (.+)", command_text)
    if price_match:
        tickers = ",".join(part.strip().upper() for part in price_match.group(1).split(",") if part.strip())
        if tickers:
            return f"make price-refresh TICKERS={tickers}"
    if re.fullmatch(r"python3 -m src\.universe_builder --preview --preset .+", command_text):
        return "make universe-preview"
    if re.fullmatch(r"python3 -m src\.universe_builder --preview --sources .+", command_text):
        return "make universe-preview"
    if re.fullmatch(r"python3 -m src\.universe_builder --write-import .+", command_text):
        return "make universe-apply"
    if command_text == "python3 -m src.universe_builder --apply-import":
        return "make universe-apply"
    return command_text


def _normalize_operator_copy(text: object) -> str:
    normalized = _format_missing(text)
    if normalized == "Not available":
        return normalized
    replacements = [
        (r"\bfundamentals import drafts\b", "fundamentals import file rows"),
        (r"\bfundamentals import draft\b", "fundamentals import file"),
        (r"\bpeer mapping import drafts\b", "peer mapping import file rows"),
        (r"\bpeer import drafts\b", "peer import file rows"),
        (r"\bpeer import draft\b", "peer import file"),
        (r"\blocal import draft rows\b", "local import file rows"),
        (r"\blocal import draft workflows\b", "local import files"),
        (r"\bSEC import draft workflow\b", "SEC staging workflow"),
        (r"\bSEC fundamentals import draft workflow\b", "SEC fundamentals staging workflow"),
        (r"\bSEC Companyfacts import draft workflow\b", "SEC Companyfacts staging workflow"),
    ]
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return re.sub(r"\bmake status\b(?!-check)", "make status-check TOP_N=5", normalized)


def _compact_reason(value: object, max_sentences: int = 2, max_chars: int = 260) -> str:
    text = _normalize_operator_copy(value)
    if text == "Not available":
        return text
    sentences = [part.strip() for part in text.replace("\n", " ").split(". ") if part.strip()]
    compact = ". ".join(sentences[:max_sentences])
    if compact and not compact.endswith((".", "?", "!")):
        compact += "."
    if len(compact) > max_chars:
        compact = compact[: max_chars - 1].rstrip() + "..."
    return compact


def _ticker_focus_command(lane: object, ticker: object, fallback: str = "") -> str:
    ticker_text = _format_missing(ticker, fallback="").upper()
    if not ticker_text:
        return fallback
    lane_key = _format_missing(lane, fallback="").strip().lower()
    command_map = {
        "prices": f"make focus-price TICKER={ticker_text}",
        "fundamentals": f"make focus-fundamentals TICKER={ticker_text}",
        "peers": f"make focus-peers TICKER={ticker_text}",
    }
    return command_map.get(lane_key, fallback)


def _preferred_row_command(row: pd.Series | dict[str, object], fallback: str = "") -> str:
    focus_command = ""
    if hasattr(row, "get"):
        focus_command = _normalize_operator_command(_format_missing(row.get("focus_command"), fallback=""))
    example_command = _normalize_operator_command(_format_missing(row.get("example_command") if hasattr(row, "get") else "", fallback=""))
    return focus_command or example_command or _normalize_operator_command(fallback)


def _review_path_fallback(dataset: object) -> str:
    lowered = _format_missing(dataset, fallback="").strip().lower()
    if lowered in {"fundamentals", "dcf", "sec"}:
        return "Review fundamentals path."
    if lowered in {"peers", "peer", "peer_relative"}:
        return "Review peer path."
    if lowered in {"prices", "price", "price_history"}:
        return "Review price path."
    if lowered in {"optional_context", "context"}:
        return "Review optional context path."
    return "Review local data coverage."


def _command_family_fallback(command: object, default: str) -> str:
    lowered = _format_missing(command, fallback="").strip().lower()
    if "imports-" in lowered or "runbook-" in lowered:
        return GUIDED_BATCH_WORKFLOW_COPY
    if "bundle-" in lowered:
        return GUIDED_BATCH_FIRST_COPY
    return default


def _project_status_context_lines(row: dict[str, object]) -> list[str]:
    lines: list[str] = []
    source_context = _format_missing(row.get("SourceContext"), "")
    freshness_context = _format_missing(row.get("FreshnessContext"), "")
    if source_context and source_context != "Not available":
        lines.append(f"Source: {source_context}")
    if freshness_context and freshness_context != "Not available":
        lines.append(f"Source readiness: {freshness_context}")
    return lines


def project_status_command_rows(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    if not payload:
        return []

    command_rows = payload.get("recommended_next_command_rows", [])
    if command_rows:
        rows: list[dict[str, str]] = []
        for row in command_rows:
            command = _normalize_operator_command(row.get("Command"))
            if not command:
                command = "make status-check TOP_N=5"
            rows.append(
                {
                    "Step": _format_missing(row.get("Step"), "Next"),
                    "Command": command,
                    "Reason": _format_missing(row.get("Reason"), ""),
                    "SourceContext": _format_missing(row.get("SourceContext"), ""),
                    "FreshnessContext": _format_missing(row.get("FreshnessContext"), ""),
                }
            )
        if rows:
            return rows

    commands = payload.get("recommended_next_commands", [])
    normalized: list[dict[str, str]] = []
    for index, command in enumerate(commands, start=1):
        command_text = _normalize_operator_command(command)
        normalized.append({"Step": f"Next {index}", "Command": command_text})
    return normalized


def top_priority_signals(action_queue: pd.DataFrame | None, limit: int = 3) -> list[dict[str, object]]:
    if action_queue is None or action_queue.empty:
        return []
    rows = []
    ordered = action_queue.sort_values(["priority", "ticker", "action_type"], na_position="last").head(limit)
    for _, row in ordered.iterrows():
        command = _preferred_row_command(
            row,
            _ticker_focus_command(
                row.get("action_type"),
                row.get("ticker"),
                "make action-queue-check TOP_N=10",
            ),
        )
        lowered_command = command.lower()
        reason = _normalize_operator_copy(row.get("reason"))
        recommended_action = _normalize_operator_copy(row.get("recommended_action"))
        target_file = _format_missing(row.get("target_file"), "")
        body_source = _command_family_fallback(command, _review_path_fallback(row.get("action_type")))
        if "runbook-" in command.lower():
            body_source = GUIDED_BATCH_WORKFLOW_COPY
        if recommended_action and recommended_action != reason:
            body_source = f"{reason} {recommended_action}".strip() if reason else recommended_action
        elif reason and reason != "Not available":
            body_source = reason
        if lowered_command == "make imports-validate":
            normalized_body = body_source.lower()
            if "make imports-preview" not in normalized_body or "make imports-apply" not in normalized_body:
                body_source = (
                    f"{reason} Run make imports-validate, then make imports-preview, then make imports-apply so local import files are reviewed before apply."
                    if reason and reason != "Not available"
                    else "Run make imports-validate, then make imports-preview, then make imports-apply so local import files are reviewed before apply."
                )
        elif lowered_command == "make price-validate":
            normalized_body = body_source.lower()
            if "make price-preview" not in normalized_body or "make price-apply" not in normalized_body:
                body_source = (
                    f"{reason} Run make price-validate, then make price-preview, then make price-apply so price import files are reviewed before apply."
                    if reason and reason != "Not available"
                    else "Run make price-validate, then make price-preview, then make price-apply so price import files are reviewed before apply."
                )
        staged_follow_through = ""
        if target_file == "data/imports/fundamentals.csv":
            staged_follow_through = "Run make imports-validate, then make imports-preview, then make imports-apply for the fundamentals import file."
        elif target_file == "data/imports/peers.csv":
            staged_follow_through = "Run make imports-validate, then make imports-preview, then make imports-apply for the peer import file."
        elif target_file == "data/imports/prices.csv":
            staged_follow_through = "Run make price-validate, then make price-preview, then make price-apply for the price import file."
        if staged_follow_through:
            normalized_body = body_source.lower()
            if target_file == "data/imports/prices.csv":
                needs_staged_upgrade = (
                    "make price-validate" not in normalized_body
                    or "make price-preview" not in normalized_body
                    or "make price-apply" not in normalized_body
                )
            else:
                needs_staged_upgrade = (
                    "make imports-validate" not in normalized_body
                    or "make imports-preview" not in normalized_body
                    or "make imports-apply" not in normalized_body
                )
            if needs_staged_upgrade:
                body_source = (
                    f"{reason} {staged_follow_through}".strip()
                    if reason and reason != "Not available"
                    else staged_follow_through
                )
        rows.append(
            {
                "kicker": str(row.get("urgency", "Action")).upper(),
                "title": command,
                "body": _compact_reason(body_source, max_sentences=2, max_chars=240),
                "badges": [
                    f"P{_format_missing(row.get('priority'), '-')}",
                    _format_missing(row.get("action_type"), "action"),
                    _format_missing(row.get("ticker"), "portfolio-wide"),
                ],
                "command": command,
            }
        )
    return rows


def overview_workflow_path_cards(
    project_status_payload: dict[str, Any] | None,
    action_queue: pd.DataFrame | None,
) -> list[dict[str, object]]:
    command_rows = project_status_command_rows(project_status_payload)
    top_signal: list[dict[str, object]] = []
    structured_rows = bool(project_status_payload and project_status_payload.get("recommended_next_command_rows"))
    if structured_rows and command_rows:
        cards: list[dict[str, object]] = []
        for index, row in enumerate(command_rows[:3], start=1):
            command = _format_missing(row.get("Command"), "make status-check TOP_N=5")
            reason = _compact_reason(row.get("Reason"), max_sentences=2, max_chars=220)
            context_lines = _project_status_context_lines(row)
            has_reason = bool(reason and reason != "Not available")
            lower_reason = reason.lower() if has_reason else ""
            body = reason or "Project next step from the current local workflow snapshot."
            badges = ["today", "data first"] if index == 1 else ["workflow", "command"]
            lowered = command.lower()
            if "verify" in lowered:
                badges = ["verify", "safe"]
                body = reason if has_reason else "Run deterministic verification so the current dashboard state is trustworthy."
            elif "dashboard-smoke" in lowered:
                badges = ["ui", "workflow"]
                body = reason if has_reason else "Open or smoke-check the dashboard after the data and verification steps are complete."
            elif "focus-" in lowered:
                badges = ["today", "single name"] if index == 1 else ["single name", "workflow"]
                body = reason if has_reason else "Use the current single-name shortcut first to unblock the highest-leverage local data gap."
            elif "bundle-" in lowered:
                badges = ["today", "guided batch"] if index == 1 else ["guided batch", "workflow"]
                body = reason if has_reason else GUIDED_BATCH_FIRST_COPY
            elif "imports-" in lowered:
                badges = ["today", "review first"] if index == 1 else ["review first", "import file"]
                if has_reason and "make imports-preview" in lower_reason and "make imports-apply" in lower_reason:
                    body = reason
                else:
                    body = "Run make imports-validate, then make imports-preview, then make imports-apply so local import files are reviewed before apply."
            elif lowered == "make price-validate":
                badges = ["today", "review first"] if index == 1 else ["review first", "import file"]
                if has_reason and "make price-preview" in lower_reason and "make price-apply" in lower_reason:
                    body = reason
                else:
                    body = "Run make price-validate, then make price-preview, then make price-apply so price import files are reviewed before apply."
            elif "runbook-" in lowered:
                badges = ["today", "guided batch"] if index == 1 else ["guided batch", "workflow"]
                body = reason if has_reason else GUIDED_BATCH_WORKFLOW_COPY
            if context_lines:
                body = "\n".join([body, *context_lines])
            cards.append({"kicker": f"STEP {index}", "title": command, "body": body, "badges": badges, "command": command})
        if cards:
            return cards

    commands = [row.get("Command", "") for row in command_rows]
    first_command = "make status-check TOP_N=5"
    if action_queue is not None and not action_queue.empty:
        top_signal = top_priority_signals(action_queue, limit=1)
        if top_signal:
            candidate = _format_missing(top_signal[0].get("command"), "")
            if candidate and candidate != "Not available":
                first_command = candidate
    elif commands:
        first_command = str(commands[0])

    second_command = "make verify"
    third_command = "make dashboard-smoke"
    if any("dashboard-smoke" in str(command) for command in commands):
        third_command = "make dashboard-smoke"

    first_body = "Start with the highest-value local data or workflow blocker before interpreting downstream research outputs."
    first_badges = ["today", "data first"]
    lowered_first = first_command.lower()
    if "focus-" in lowered_first:
        first_body = "Use the current single-name shortcut first to unblock the highest-leverage local data gap."
        first_badges = ["today", "single name"]
    elif "bundle-" in lowered_first:
        first_body = GUIDED_BATCH_FIRST_COPY
        first_badges = ["today", "guided batch"]
    elif "imports-" in lowered_first:
        first_body = "Run make imports-validate, then make imports-preview, then make imports-apply so local import files are reviewed before apply."
        first_badges = ["today", "review first"]
    elif "runbook-" in lowered_first:
        first_body = GUIDED_BATCH_WORKFLOW_COPY
        first_badges = ["today", "guided batch"]
    if top_signal:
        signal_body = _compact_reason(top_signal[0].get("body"), max_sentences=2, max_chars=240)
        if signal_body and signal_body != "Not available":
            first_body = signal_body

    return [
        {"kicker": "STEP 1", "title": first_command, "body": first_body, "badges": first_badges, "command": first_command},
        {
            "kicker": "STEP 2",
            "title": second_command,
            "body": "Run deterministic verification so the current dashboard state is trustworthy.",
            "badges": ["verify", "safe"],
            "command": second_command,
        },
        {
            "kicker": "STEP 3",
            "title": third_command,
            "body": "Open or smoke-check the dashboard after the data and verification steps are complete.",
            "badges": ["ui", "workflow"],
            "command": third_command,
        },
    ]


def overview_workflow_reason_card(
    project_status_payload: dict[str, Any] | None,
    action_queue: pd.DataFrame | None,
) -> dict[str, object]:
    first_card = overview_workflow_path_cards(project_status_payload, action_queue)[0]
    first_command = first_card["title"]
    reason = f"Run {first_command} first to refresh local blocker triage before verification and UI review."
    badges = ["why now", "research only"]

    if action_queue is not None and not action_queue.empty:
        top_row = action_queue.sort_values(["priority", "ticker", "action_type"], na_position="last").iloc[0]
        dataset = _format_missing(top_row.get("action_type"), "data")
        ticker = _format_missing(top_row.get("ticker"), "")
        signal = top_priority_signals(action_queue, limit=1)
        signal_command = _format_missing(signal[0].get("command"), "") if signal else _preferred_row_command(
            top_row,
            _ticker_focus_command(top_row.get("action_type"), top_row.get("ticker"), "make action-queue-check TOP_N=10"),
        )
        row_reason = _compact_reason(top_row.get("reason"), max_sentences=1, max_chars=170)
        signal_reason = _compact_reason(signal[0].get("body"), max_sentences=2, max_chars=240) if signal else row_reason
        if not signal_reason or signal_reason == "Not available":
            signal_reason = _command_family_fallback(signal_command, _review_path_fallback(top_row.get("action_type")))
        if ticker and ticker != "Not available":
            reason = f"{dataset.title()} pressure is currently led by {ticker}. {signal_reason}"
        else:
            reason = f"{dataset.title()} pressure is currently the top local blocker. {signal_reason}"
        badges = [f"P{_format_missing(top_row.get('priority'), '-')}", dataset]
    elif project_status_payload:
        summary = project_status_payload.get("summary", {})
        data_gaps = int(summary.get("data_gaps") or 0)
        critical_actions = int(summary.get("critical_actions") or 0)
        if first_command == "make status":
            first_command = "make status-check TOP_N=5"
        if project_status_payload.get("recommended_next_command_rows") and critical_actions == 0 and data_gaps == 0:
            structured_reason = _compact_reason(first_card.get("body"), max_sentences=2, max_chars=240)
            if structured_reason and structured_reason != "Not available":
                reason = structured_reason
                badges = [str(item) for item in first_card.get("badges", [])][:2] or ["workflow", "command"]
            else:
                reason = (
                    f"{critical_actions} critical actions and {data_gaps} visible data gaps are in the current read-only status snapshot, "
                    "so the workflow starts with local coverage before interpretation."
                )
                badges = ["status snapshot", "data first"]
        else:
            reason = (
                f"{critical_actions} critical actions and {data_gaps} visible data gaps are in the current read-only status snapshot, "
                "so the workflow starts with local coverage before interpretation."
            )
            badges = ["status snapshot", "data first"]

    return {
        "kicker": "WHY THIS STEP NOW",
        "title": str(first_command),
        "body": reason,
        "badges": badges,
        "command": str(first_command),
    }
