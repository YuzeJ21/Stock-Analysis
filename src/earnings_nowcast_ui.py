from __future__ import annotations

from typing import Any, Mapping


def _number(value: object, *, decimals: int = 2) -> str:
    if value is None:
        return "withheld"
    return f"{float(value):,.{decimals}f}"


def _range_text(forecast: Mapping[str, object], prefix: str) -> str:
    low = forecast.get(f"{prefix}_low")
    midpoint = forecast.get(f"{prefix}_midpoint")
    high = forecast.get(f"{prefix}_high")
    if any(value is None for value in (low, midpoint, high)):
        return "withheld"
    return f"{_number(low)} to {_number(high)} (midpoint {_number(midpoint)})"


def nowcast_summary_cards(
    packet: Mapping[str, Any] | None,
    *,
    ticker: str,
) -> list[dict[str, object]]:
    normalized_ticker = str(ticker or "").strip().upper() or "Selected ticker"
    if not packet or not isinstance(packet.get("forecast"), Mapping):
        return [
            {
                "kicker": "EARNINGS OUTLOOK",
                "title": "Earnings Outlook",
                "state": "blocked",
                "body": (
                    f"{normalized_ticker} has no source-backed point-in-time nowcast packet. "
                    "Open Data Health to review missing quarterly actuals and exact-period consensus evidence."
                ),
                "badges": ["blocked", "no forecast shown", "research-only"],
                "primary_action": "Open Data Health",
                "advanced_default_open": False,
            }
        ]

    forecast = packet["forecast"]
    readiness = packet.get("readiness", {})
    calibration = packet.get("calibration", {})
    evidence_scope = str(packet.get("evidence_scope", "unverified_evidence")).replace("_", " ")
    state = str(readiness.get("state", "blocked"))
    body_parts = [
        f"Period {packet.get('fiscal_period', 'not available')} as of {packet.get('as_of_timestamp', 'not available')}.",
        f"Revenue range: {_range_text(forecast, 'revenue')}.",
        f"EPS range: {_range_text(forecast, 'eps')}.",
        f"Consensus-relative classification: {str(forecast.get('relative_classification', 'withheld')).replace('_', ' ')}.",
        f"Evidence scope: {evidence_scope}.",
    ]
    if not bool(calibration.get("probability_available")):
        body_parts.append("Numerical surprise probability is withheld until leakage-safe calibration passes.")
    return [
        {
            "kicker": "EARNINGS OUTLOOK",
            "title": "Earnings Outlook",
            "state": state,
            "body": " ".join(body_parts),
            "badges": [state, str(readiness.get("freshness_state", "unknown")), "research-only"],
            "primary_action": "Review the range, then open Advanced evidence only if needed",
            "advanced_default_open": False,
        }
    ]


def nowcast_blocked_card(*, ticker: str, missing_evidence: list[str] | tuple[str, ...] = ()) -> dict[str, object]:
    card = nowcast_summary_cards(None, ticker=ticker)[0]
    if missing_evidence:
        card = dict(card)
        card["body"] = f"{card['body']} Missing evidence: {', '.join(missing_evidence)}."
    return card


def nowcast_data_health_card(
    packet: Mapping[str, Any] | None,
    *,
    ticker: str,
) -> dict[str, object]:
    normalized_ticker = str(ticker or "").strip().upper() or "Selected ticker"
    if not packet:
        return {
            "kicker": "OPTIONAL EARNINGS LANE",
            "title": "Earnings Nowcast",
            "state": "blocked",
            "body": (
                f"{normalized_ticker}: infrastructure is available, but real output requires source-backed quarterly actuals "
                "and an exact-period point-in-time consensus snapshot. Candidate peer/news context cannot unlock the baseline."
            ),
            "badges": ["blocked", "point-in-time evidence required"],
            "primary_action": "Add reviewed evidence; otherwise keep the forecast withheld",
            "advanced_default_open": False,
        }
    readiness = packet.get("readiness", {})
    state = str(readiness.get("state", "blocked"))
    return {
        "kicker": "OPTIONAL EARNINGS LANE",
        "title": "Earnings Nowcast",
        "state": state,
        "body": (
            f"{normalized_ticker}: {state.replace('_', ' ')}. Deterministic ranges may be reviewed when ready; "
            "signals remain evidence-only and numerical probability remains withheld until calibrated."
        ),
        "badges": [state, "signals do not change numbers"],
        "primary_action": "Open the selected ticker report",
        "advanced_default_open": False,
    }


def nowcast_advanced_evidence(packet: Mapping[str, Any] | None) -> dict[str, object]:
    if not packet:
        return {"available": False, "reason": "No source-backed nowcast packet is available."}
    forecast = packet.get("forecast", {})
    return {
        "available": True,
        "model_version": forecast.get("model_version"),
        "input_snapshot_hash": forecast.get("input_snapshot_hash"),
        "source_ids": forecast.get("source_ids", []),
        "signals": packet.get("signals", {}),
        "backtest": packet.get("backtest", {}),
        "calibration": packet.get("calibration", {}),
    }


def render_earnings_nowcast_section(
    streamlit_module: Any,
    packet: Mapping[str, Any] | None,
    *,
    ticker: str,
) -> None:
    card = nowcast_summary_cards(packet, ticker=ticker)[0]
    streamlit_module.markdown("#### Earnings Outlook")
    streamlit_module.write(card["body"])
    with streamlit_module.expander("Advanced: nowcast evidence", expanded=False):
        streamlit_module.json(nowcast_advanced_evidence(packet))
