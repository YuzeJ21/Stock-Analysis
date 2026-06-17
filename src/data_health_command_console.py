"""Pure Data Health command-bundle card helpers.

The dashboard renders the cards; this module owns the copy-only guided batch
card decisions for Data Health and Overview surfaces.
"""

from __future__ import annotations

import re

import pandas as pd


GUIDED_BATCH_WORKFLOW_COPY = (
    "Use the guided data batch as the local import file workflow next so validation and preview safeguards stay in place."
)
GUIDED_BATCH_FIRST_COPY = (
    "Use the highest-leverage guided data batch first so price, fundamentals, or peer follow-through stays coordinated."
)

_IMPORT_TARGETS = {"data/imports/fundamentals.csv", "data/imports/peers.csv", "data/imports/prices.csv"}


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


def _format_value(value: object, fallback: str = "Not available") -> str:
    text = _format_missing(value, fallback=fallback)
    if text == fallback:
        return text
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return text
    if abs(float(number)) >= 1_000_000:
        return f"{float(number) / 1_000_000:.1f}M"
    if abs(float(number)) >= 1_000:
        return f"{float(number):,.0f}"
    return f"{float(number):.2f}".rstrip("0").rstrip(".")


def _normalize_operator_copy(value: object) -> str:
    text = _format_missing(value)
    if text == "Not available":
        return text
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
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"\bmake status\b(?!-check)", "make status-check TOP_N=5", text)


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


def _target_rows_hint(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return ""
    return str(int(numeric))


def normalize_operator_command(command: object) -> str:
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


def _unlock_stage_command(stage: object, fallback: str = "") -> str:
    stage_text = _format_missing(stage, "").strip().lower()
    command_map = {
        "prices": "make runbook-prices-broader",
        "fundamentals": "make runbook-fundamentals-broader",
        "peers": "make runbook-peers-broader",
        "optional_context": "make onboarding",
        "ready": "make status-check TOP_N=5",
    }
    return command_map.get(stage_text, fallback)


def preferred_bundle_command(row: pd.Series | dict[str, object], fallback: str = "") -> str:
    if hasattr(row, "get"):
        for key in ("bundle_shortcut_command", "primary_command", "runbook_shortcut_command", "detail_shortcut_command"):
            command = normalize_operator_command(_format_missing(row.get(key), fallback=""))
            if command:
                return command
        lane_fallback = _unlock_stage_command(_format_missing(row.get("lane"), ""), "")
        if lane_fallback:
            return lane_fallback
    return normalize_operator_command(fallback)


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


def _staged_summary(row: pd.Series | dict[str, object]) -> str:
    target_file = _format_missing(row.get("target_file") if hasattr(row, "get") else "", "")
    if target_file not in _IMPORT_TARGETS:
        return ""
    summary = _compact_reason(row.get("safe_next_step") if hasattr(row, "get") else "", max_sentences=1, max_chars=150)
    if target_file == "data/imports/fundamentals.csv":
        default = "Run make imports-validate, make imports-preview, and make imports-apply for the fundamentals import file."
    elif target_file == "data/imports/peers.csv":
        default = "Run make imports-validate, make imports-preview, and make imports-apply for the peer import file."
    else:
        default = "Run make price-validate, make price-preview, and make price-apply for the price import file."
    if summary == "Not available":
        return default
    if target_file == "data/imports/prices.csv" and (
        "make price-validate" not in summary or "make price-preview" not in summary or "make price-apply" not in summary
    ):
        return default
    return summary


def _fallback_first_command(target_file: str) -> str:
    if target_file in {"data/imports/fundamentals.csv", "data/imports/peers.csv"}:
        return "make imports-validate"
    if target_file == "data/imports/prices.csv":
        return "make price-validate"
    return ""


def _bundle_hint(row: pd.Series | dict[str, object]) -> str:
    target_history_rows = _target_rows_hint(row.get("target_history_rows") if hasattr(row, "get") else "")
    suggested_start_date = _format_missing(row.get("suggested_start_date") if hasattr(row, "get") else "", "")
    hints: list[str] = []
    if target_history_rows not in {"", "-"}:
        hints.append(f"{target_history_rows} target rows")
    if suggested_start_date not in {"", "-"}:
        hints.append(f"start by {suggested_start_date}")
    return f" ({'; '.join(hints)})" if hints else ""


def _bundle_body_summary(row: pd.Series | dict[str, object], command: str) -> str:
    goal_summary = _compact_reason(row.get("goal_summary") if hasattr(row, "get") else "", max_sentences=1, max_chars=110)
    lane_summary = _command_family_fallback(command, _review_path_fallback(row.get("lane") if hasattr(row, "get") else ""))
    if "runbook-" in command.lower():
        lane_summary = GUIDED_BATCH_WORKFLOW_COPY
    staged_summary = _staged_summary(row)
    return (
        goal_summary
        if goal_summary != "Not available"
        else _compact_reason(
            (row.get("why_it_matters") if hasattr(row, "get") else "") or staged_summary or lane_summary,
            max_sentences=1,
            max_chars=150,
        )
    )


def command_bundle_cards(bundle_frame: pd.DataFrame | None, limit: int = 3) -> list[dict[str, object]]:
    if bundle_frame is None or bundle_frame.empty:
        return [
            {
                "kicker": "DATA BATCHES",
                "title": "No guided data batches yet",
                "body": "Build holdings-first guided data batches for prices, SEC staging workflow, and peer mapping.",
                "badges": ["read-only"],
                "command": "make onboarding",
            }
        ]

    ordered = bundle_frame.copy()
    if "ticker_count" in ordered.columns:
        ordered["ticker_count"] = pd.to_numeric(ordered["ticker_count"], errors="coerce").fillna(0)

    cards: list[dict[str, object]] = []
    for _, row in ordered.head(limit).iterrows():
        command = preferred_bundle_command(row, "")
        body_summary = _bundle_body_summary(row, command)
        cards.append(
            {
                "kicker": _format_missing(row.get("lane"), "bundle").upper(),
                "title": _format_missing(row.get("bundle_name"), "Local bundle"),
                "body": (
                    f"{_format_missing(row.get('tickers'), 'No tickers')}: "
                    f"{body_summary}"
                    f"{_bundle_hint(row)}"
                ),
                "badges": [
                    _format_missing(row.get("scope"), "scope").replace("_", " "),
                    f"{_format_value(row.get('ticker_count'), fallback='0')} tickers",
                ],
                "command": command,
            }
        )
    return cards


def command_bundle_runbook_cards(runbook_frame: pd.DataFrame | None, limit: int = 3) -> list[dict[str, object]]:
    if runbook_frame is None or runbook_frame.empty:
        return [
            {
                "kicker": "GUIDED STEPS",
                "title": "No guided data batch plan yet",
                "body": "Build ordered guided steps for prices, SEC staging workflow, and peer mapping before using this plan.",
                "badges": ["read-only"],
                "command": "make onboarding",
            }
        ]
    return _runbook_lane_cards(
        runbook_frame,
        limit=limit,
        kicker_suffix="STEPS",
        body_prefix_tickers=False,
        fallback_card={
            "kicker": "GUIDED STEPS",
            "title": "No guided data batch plan yet",
            "body": "Build ordered guided steps for prices, SEC staging workflow, and peer mapping before using this plan.",
            "badges": ["read-only"],
            "command": "make onboarding",
        },
        max_steps_by_lane={"prices": 7, "fundamentals": 5, "peers": 5},
    )


def overview_command_bundle_cards(bundle_frame: pd.DataFrame | None, limit: int = 2) -> list[dict[str, object]]:
    if bundle_frame is None or bundle_frame.empty:
        return [
            {
                "kicker": "DATA BUNDLE",
                "title": "No guided data batches yet",
                "body": "Build holdings-first guided data batches for prices, SEC staging workflow, and peer mapping.",
                "badges": ["read-only", "data moat"],
                "command": "make onboarding",
            }
        ]

    cards: list[dict[str, object]] = []
    for _, row in bundle_frame.head(limit).iterrows():
        command = preferred_bundle_command(row, "")
        lane = _format_missing(row.get("lane"), "bundle").replace("_", " ")
        scope = _format_missing(row.get("scope"), "scope").replace("_", " ")
        body_summary = _bundle_body_summary(row, command)
        cards.append(
            {
                "kicker": f"{lane.upper()} BUNDLE",
                "title": _format_missing(row.get("bundle_name"), "Local bundle"),
                "body": (
                    f"{_format_missing(row.get('tickers'), 'No tickers')}: "
                    f"{body_summary}"
                    f"{_bundle_hint(row)}"
                ),
                "badges": [scope, f"{_format_value(row.get('ticker_count'), fallback='0')} tickers"],
                "command": command,
            }
        )
    return cards


def overview_bundle_runbook_cards(runbook_frame: pd.DataFrame | None, limit: int = 3) -> list[dict[str, object]]:
    if runbook_frame is None or runbook_frame.empty:
        return [
            {
                "kicker": "GUIDED BATCH",
                "title": "No guided data batch plan yet",
                "body": "Build ordered price, SEC fundamentals, and peer-mapping steps before using this guided batch plan.",
                "badges": ["read-only", "data moat"],
                "command": "make onboarding",
            }
        ]
    return _runbook_lane_cards(
        runbook_frame,
        limit=limit,
        kicker_suffix="LANE",
        body_prefix_tickers=True,
        fallback_card={
            "kicker": "GUIDED BATCH",
            "title": "No guided data batch plan yet",
            "body": "Build ordered price, SEC fundamentals, and peer-mapping steps before using this guided batch plan.",
            "badges": ["read-only", "data moat"],
            "command": "make onboarding",
        },
        max_steps_by_lane={"prices": 2, "fundamentals": 2, "peers": 2},
        badge_second="runbook",
    )


def _runbook_lane_cards(
    runbook_frame: pd.DataFrame,
    *,
    limit: int,
    kicker_suffix: str,
    body_prefix_tickers: bool,
    fallback_card: dict[str, object],
    max_steps_by_lane: dict[str, int],
    badge_second: str | None = None,
) -> list[dict[str, object]]:
    ordered = runbook_frame.copy()
    ordered["lane"] = ordered.get("lane", pd.Series(dtype=str)).astype(str)
    if "step_order" in ordered.columns:
        ordered["step_order"] = pd.to_numeric(ordered["step_order"], errors="coerce")
        ordered = ordered.sort_values(["lane", "step_order", "bundle_name"], kind="stable")

    cards: list[dict[str, object]] = []
    for lane in ("prices", "fundamentals", "peers"):
        lane_rows = ordered.loc[ordered["lane"].eq(lane)]
        if lane_rows.empty:
            continue
        first = lane_rows.iloc[0]
        target_file = _format_missing(first.get("target_file"), "")
        fallback_first_command = _fallback_first_command(target_file)
        max_steps = max_steps_by_lane.get(lane, 5)
        steps: list[str] = []
        first_command = ""
        for _, row in lane_rows.head(max_steps).iterrows():
            step_label = _format_missing(row.get("step_label"), "Step")
            command = _format_missing(row.get("command"), "")
            step_command = normalize_operator_command(command) or command
            if not step_command and fallback_first_command and not first_command:
                step_command = fallback_first_command
            if step_command:
                first_command = first_command or step_command
                steps.append(f"{step_label}: {step_command}")

        surfaced_command = first_command or fallback_first_command
        lane_summary = _command_family_fallback(surfaced_command, _review_path_fallback(lane))
        if "runbook-" in surfaced_command.lower():
            lane_summary = GUIDED_BATCH_WORKFLOW_COPY
        goal_summary = _compact_reason(first.get("goal_summary"), max_sentences=1, max_chars=110)
        body_summary = (
            goal_summary
            if goal_summary not in {"", "Not available"}
            else _compact_reason(first.get("why_it_matters") or _staged_summary(first) or lane_summary, max_sentences=1, max_chars=150)
        )
        lead = f"{body_summary}{_bundle_hint(first)}. " if body_summary not in {"", "Not available"} else ""
        if body_prefix_tickers:
            tickers = _format_missing(first.get("tickers"), "No tickers")
            body = lead + f"{tickers}. " + " | ".join(steps)
        else:
            body = lead + (" | ".join(steps) if steps else "No guided steps available.")
        badges = [
            _format_missing(first.get("scope"), "scope").replace("_", " "),
            badge_second or _format_missing(first.get("tickers"), "No tickers"),
        ]
        cards.append(
            {
                "kicker": f"{lane.upper()} {kicker_suffix}",
                "title": _format_missing(first.get("bundle_name"), "Local bundle"),
                "body": body,
                "badges": badges,
                "command": first_command or fallback_first_command,
            }
        )
        if len(cards) >= limit:
            break
    return cards or [fallback_card]
