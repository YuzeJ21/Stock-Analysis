from __future__ import annotations

import pandas as pd

from src.data_health_coverage_delta import build_readiness_change_frame


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


def _bool_series(frame: pd.DataFrame | None, column: str) -> pd.Series:
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(dtype=bool)
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def _latest_frame_timestamp(frame: pd.DataFrame | None) -> str:
    if frame is None or frame.empty:
        return ""
    for column in ("updated_at", "generated_at", "last_success_at", "last_attempted_at"):
        if column not in frame.columns:
            continue
        values = frame[column].dropna().astype(str).str.strip()
        values = values.loc[~values.str.lower().isin({"", "nan", "none", "null", "not available"})]
        if not values.empty:
            return str(values.max())
    return ""


def readiness_recent_progress_cards(
    current_frame: pd.DataFrame | None,
    previous_frame: pd.DataFrame | None = None,
    feature_summary_frame: pd.DataFrame | None = None,
    previous_snapshot_label: str = "",
) -> list[dict[str, object]]:
    if current_frame is None or current_frame.empty:
        return [
            {
                "kicker": "WHAT CHANGED",
                "title": "Readiness report missing",
                "body": "Refresh readiness before comparing current and prior product status. Open operator details for the copy-only command.",
                "badges": ["blocked"],
                "command": "make readiness",
            }
        ]

    current = current_frame.copy()
    total = int(len(current))
    active = int(_bool_series(current, "in_active_universe").reindex(current.index, fill_value=False).sum()) if "in_active_universe" in current.columns else 0
    state_counts = (
        current.get("overall_readiness_state", pd.Series(dtype=object))
        .fillna("unknown")
        .astype(str)
        .str.lower()
        .value_counts()
    )
    change_frame = build_readiness_change_frame(current, previous_frame)
    latest = _latest_frame_timestamp(current)
    prior_latest = _latest_frame_timestamp(previous_frame)
    prior_label = "saved prior readiness snapshot" if previous_snapshot_label else "prior readiness snapshot"
    price_ready = int(change_frame.loc[change_frame["feature"].eq("Price"), "current_ready"].max() or 0)
    dcf_ready = int(change_frame.loc[change_frame["feature"].eq("DCF"), "current_ready"].max() or 0)
    peer_ready = int(change_frame.loc[change_frame["feature"].eq("Peers"), "current_ready"].max() or 0)
    cards = [
        {
            "kicker": "READINESS NOW",
            "title": f"{price_ready}/{total} price-ready",
            "body": (
                f"Active universe: {active}. DCF-ready: {dcf_ready}. Peer-ready: {peer_ready}. "
                f"Blocked: {int(state_counts.get('blocked', 0))}. Partial: {int(state_counts.get('partial', 0))}. "
                f"Latest refresh timestamp: {_format_missing(latest)}."
            ),
            "badges": ["current counts", "readiness first"],
            "command": "make readiness",
        }
    ]

    has_previous = previous_frame is not None and not previous_frame.empty
    if has_previous:
        changed = change_frame.dropna(subset=["delta_ready"]).copy()
        changed["abs_delta"] = pd.to_numeric(changed["delta_ready"], errors="coerce").abs()
        changed = changed.sort_values(["abs_delta", "feature"], ascending=[False, True], kind="stable")
        top_changed = changed.loc[changed["abs_delta"].gt(0)].head(4)
        changed_text = ", ".join(
            f"{row.feature} {'+' if int(row.delta_ready) >= 0 else ''}{int(row.delta_ready)}"
            for row in top_changed.itertuples(index=False)
        )
        newly_ready = next(
            (
                str(value)
                for value in changed["newly_ready_tickers"].dropna().astype(str)
                if value.strip()
            ),
            "",
        )
        cards.append(
            {
                "kicker": "WHAT CHANGED",
                "title": changed_text or "No ready-count change",
                "body": (
                    f"Compared with {prior_label}; prior refresh timestamp: {_format_missing(prior_latest)}. "
                    f"Newly ready tickers: {newly_ready or 'none detected'}. "
                    "This is a count comparison only; review source readiness before interpreting analysis."
                ),
                "badges": ["previous vs current", "no fabricated deltas"],
                "command": "make readiness",
            }
        )
    else:
        cards.append(
            {
                "kicker": "WHAT CHANGED",
                "title": "Current-only baseline",
                "body": (
                    "No prior readiness snapshot was found, so the dashboard shows current counts without pretending a delta exists. "
                    "Save a baseline snapshot before the next targeted refresh or import, then refresh readiness to compare real before/after counts."
                ),
                "badges": ["no prior snapshot", "data-honest"],
                "command": "make readiness-snapshot",
            }
        )

    cards.append(
        {
            "kicker": "SNAPSHOT WORKFLOW",
            "title": "Snapshot -> targeted update -> compare",
            "body": (
                "Use one saved baseline, then one targeted refresh/import workflow, then refresh readiness. "
                "The dashboard compares only saved local snapshots and never invents progress."
            ),
            "badges": ["review workflow", "copy only"],
            "command": "make readiness-snapshot",
        }
    )

    blocked_rows: list[str] = []
    if feature_summary_frame is not None and not feature_summary_frame.empty:
        summary = feature_summary_frame.copy()
        if "blocked_count" in summary.columns:
            summary["blocked_count"] = pd.to_numeric(summary["blocked_count"], errors="coerce").fillna(0).astype(int)
            summary = summary.sort_values(["blocked_count", "feature"], ascending=[False, True], kind="stable")
            for row in summary.head(4).itertuples(index=False):
                feature = _format_missing(getattr(row, "feature", ""), "feature")
                blocked = int(getattr(row, "blocked_count", 0) or 0)
                blocked_rows.append(f"{feature}: {blocked}")
    if not blocked_rows and not change_frame.empty:
        blocked = change_frame.sort_values(["current_blocked", "feature"], ascending=[False, True], kind="stable").head(4)
        blocked_rows = [f"{row.feature}: {int(row.current_blocked)}" for row in blocked.itertuples(index=False)]
    cards.append(
        {
            "kicker": "STILL BLOCKED",
            "title": ", ".join(blocked_rows[:2]) or "No blockers reported",
            "body": (
                (", ".join(blocked_rows) if blocked_rows else "No current blocker summary is available.")
                + " Use capped, feature-specific worklists instead of rendering or refreshing all master rows."
            ),
            "badges": ["top blocked features", "row-limited"],
            "command": "make onboarding TOP_N=10",
        }
    )
    cards.append(
        {
            "kicker": "SOURCE / FRESHNESS",
            "title": "Copyable commands only",
            "body": (
                "Dashboard cards display local commands and paths only; they do not run imports, refreshes, or external account actions. "
                "Earnings and analyst estimates remain unavailable until trusted local CSV rows validate."
            ),
            "badges": ["copy only", "research-only"],
            "command": "make imports-validate",
        }
    )
    return cards
