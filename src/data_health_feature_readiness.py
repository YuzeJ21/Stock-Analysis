from __future__ import annotations

import pandas as pd


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


def feature_readiness_cards(feature_summary_frame: pd.DataFrame | None, *, limit: int = 6) -> list[dict[str, object]]:
    if feature_summary_frame is None or feature_summary_frame.empty:
        return [
            {
                "kicker": "FEATURE READINESS",
                "title": "Feature readiness not ready yet",
                "body": "Build feature readiness proof before reviewing which analysis areas are ready, partial, blocked, or excluded. Open operator details for read-only proof steps.",
                "badges": ["blocked"],
                "command": "make readiness",
            }
        ]
    frame = feature_summary_frame.copy()
    for column in ["ready_count", "partial_count", "blocked_count", "excluded_count", "total_count"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)
    if "blocked_count" in frame.columns:
        frame = frame.sort_values(["blocked_count", "ready_count"], ascending=[False, True]).copy()
    cards: list[dict[str, object]] = []
    for _, row in frame.head(limit).iterrows():
        feature = _format_missing(row.get("feature"), "Feature")
        feature_key = feature.lower().replace(" ", "_")
        ready = int(row.get("ready_count") or 0)
        partial = int(row.get("partial_count") or 0)
        blocked = int(row.get("blocked_count") or 0)
        excluded = int(row.get("excluded_count") or 0)
        total = int(row.get("total_count") or 0)
        blocker = _format_missing(row.get("top_blocker"), "No dominant blocker")
        section = _format_missing(row.get("dashboard_section"), "Dashboard")
        command = str(row.get("next_action") or "make readiness")
        body = f"Partial: {partial}. Blocked: {blocked}. Excluded: {excluded}. Top blocker: {blocker}."
        if feature_key == "earnings":
            body = (
                f"{body} Optional context is intentionally locked until trusted local rows exist. "
                "Use schema-only templates, place files in data/staged/earnings/, import to data/imports/earnings.csv, "
                "then run make imports-validate IMPORT_TICKERS=<ticker> -> make imports-preview IMPORT_TICKERS=<ticker> -> make imports-apply IMPORT_TICKERS=<ticker>."
            )
            command = "make templates"
        elif feature_key == "analyst_estimates":
            body = (
                f"{body} Optional context is intentionally locked until trusted local rows exist. "
                "Use schema-only templates, place files in data/staged/analyst_estimates/, import to data/imports/analyst_estimates.csv, "
                "then run make imports-validate IMPORT_TICKERS=<ticker> -> make imports-preview IMPORT_TICKERS=<ticker> -> make imports-apply IMPORT_TICKERS=<ticker>."
            )
            command = "make templates"
        elif feature_key == "price":
            body = (
                f"{body} For broad coverage, dry-run the capped refresh loop first; this avoids repeating small "
                "worklists manually and previews local CSV churn before any provider-backed update."
            )
            command = "make price-refresh-loop DRY_RUN=1"
        cards.append(
            {
                "kicker": section.upper(),
                "title": f"{feature}: {ready}/{total} ready",
                "body": body,
                "badges": ["feature readiness", "product status"],
                "command": command,
            }
        )
    return cards
