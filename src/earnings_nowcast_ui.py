from __future__ import annotations

from typing import Any, Mapping


_STATE_LABELS = {
    "baseline_ready": "Forecast range ready",
    "signal_context_ready": "Evidence context ready",
    "backtest_ready": "Backtest ready; probability withheld",
    "calibrated": "Calibrated probability ready",
    "blocked": "Source evidence required",
    "excluded": "Not eligible",
}


def nowcast_state_label(state: object) -> str:
    normalized = str(state or "blocked").strip().lower()
    return _STATE_LABELS.get(normalized, normalized.replace("_", " ").capitalize())


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


def nowcast_public_answers(
    packet: Mapping[str, Any] | None,
    *,
    ticker: str,
) -> dict[str, dict[str, str]]:
    normalized_ticker = str(ticker or "").strip().upper() or "Selected ticker"
    readiness = packet.get("readiness", {}) if packet else {}
    state = str(readiness.get("state", "blocked"))
    excluded = state == "excluded"
    forecast = packet.get("forecast", {}) if packet else {}
    baseline_ready = bool(packet and isinstance(forecast, Mapping) and state not in {"blocked", "excluded"})

    if baseline_ready:
        ranges = (
            f"Revenue range: {_range_text(forecast, 'revenue')}. "
            f"EPS range: {_range_text(forecast, 'eps')}."
        )
        classification = str(forecast.get("relative_classification", "withheld")).replace("_", " ")
        consensus = f"The available forecast range is {classification} relative to the point-in-time consensus snapshot."
        evidence_scope = str(packet.get("evidence_scope", "unverified_evidence"))
        if evidence_scope == "synthetic_test_evidence_only":
            context = "Synthetic test evidence (test-only) demonstrates the workflow; it is not real-company or freshness proof."
        else:
            context = "Reviewed evidence provides context only and does not change the deterministic forecast numbers."
        withheld = (
            "Numerical surprise probability is withheld until leakage-safe calibration passes."
            if not bool(packet.get("calibration", {}).get("probability_available"))
            else "No calibrated output is withheld by the probability gate."
        )
        next_action = "Review the range, then open Advanced evidence only if needed"
    else:
        ranges = "No numerical Revenue or EPS forecast is shown until the baseline evidence gate passes."
        consensus = "Consensus comparison is unavailable because no source-backed baseline is ready."
        context = "Candidate peer or news context cannot unlock or modify a numerical baseline."
        withheld = "Revenue, EPS, and numerical Beat/Miss probability remain analytically withheld."
        next_action = "Open Data Health"

    return {
        "eligibility": {
            "question": "Is this ticker eligible?",
            "status": "excluded" if excluded else "eligible",
            "answer": "Not eligible for this operating-company pilot." if excluded else f"{normalized_ticker} is eligible for evidence review.",
        },
        "baseline": {
            "question": "Is a real source-backed baseline available?",
            "status": "ready" if baseline_ready else "blocked",
            "answer": nowcast_state_label(state),
        },
        "ranges": {
            "question": "What Revenue/EPS range can be reviewed?",
            "status": "ready" if baseline_ready else "withheld",
            "answer": ranges,
        },
        "consensus": {
            "question": "How does the range compare with consensus?",
            "status": "ready" if baseline_ready else "withheld",
            "answer": consensus,
        },
        "evidence_context": {
            "question": "What evidence explains the context?",
            "status": "context_only" if baseline_ready else "blocked",
            "answer": context,
        },
        "withheld": {
            "question": "What is still withheld?",
            "status": "withheld" if "withheld" in withheld else "ready",
            "answer": withheld,
        },
        "next_action": {
            "question": "What should I do next?",
            "status": "action",
            "answer": next_action,
        },
    }


def _public_answers_body(answers: Mapping[str, Mapping[str, str]]) -> str:
    labels = (
        ("eligibility", "Eligibility"),
        ("baseline", "Baseline"),
        ("ranges", "Range"),
        ("consensus", "Consensus"),
        ("evidence_context", "Context"),
        ("withheld", "Withheld"),
        ("next_action", "Next"),
    )
    return "\n".join(f"{label}: {answers[key]['answer']}" for key, label in labels)


def nowcast_summary_cards(
    packet: Mapping[str, Any] | None,
    *,
    ticker: str,
) -> list[dict[str, object]]:
    normalized_ticker = str(ticker or "").strip().upper() or "Selected ticker"
    if not packet or not isinstance(packet.get("forecast"), Mapping):
        answers = nowcast_public_answers(None, ticker=normalized_ticker)
        return [
            {
                "kicker": "EARNINGS OUTLOOK",
                "title": "Earnings Outlook",
                "state": "blocked",
                "body": _public_answers_body(answers),
                "badges": ["blocked", "no forecast shown", "research-only"],
                "primary_action": "Open Data Health",
                "advanced_default_open": False,
                "state_label": nowcast_state_label("blocked"),
                "answers": answers,
            }
        ]

    forecast = packet["forecast"]
    readiness = packet.get("readiness", {})
    calibration = packet.get("calibration", {})
    evidence_scope = str(packet.get("evidence_scope", "unverified_evidence")).replace("_", " ")
    state = str(readiness.get("state", "blocked"))
    answers = nowcast_public_answers(packet, ticker=normalized_ticker)
    return [
        {
            "kicker": "EARNINGS OUTLOOK",
            "title": "Earnings Outlook",
            "state": state,
            "state_label": nowcast_state_label(state),
            "answers": answers,
            "body": _public_answers_body(answers),
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
    answers = card.get("answers", nowcast_public_answers(packet, ticker=ticker))
    for answer in answers.values():
        streamlit_module.markdown(f"**{answer['question']}**")
        streamlit_module.write(answer["answer"])
    with streamlit_module.expander("Advanced: nowcast evidence", expanded=False):
        streamlit_module.json(nowcast_advanced_evidence(packet))
