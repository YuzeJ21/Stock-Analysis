"""Read-only trusted-data pilot candidate queue.

This module ranks current local blockers for a small company-focused pilot.
It does not refresh providers, import rows, write CSVs, or change readiness
outputs.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_TOP_N = 10
MONITOR_EXAMPLE_TICKERS = {"QQQ", "SMH"}
DEMO_COMPANY_ORDER = {
    ticker: index
    for index, ticker in enumerate(
        ("NVDA", "AVGO", "AMD", "MU", "CRDO", "COHR", "LITE", "HOOD", "TSLA", "META", "A", "APLD"),
        start=1,
    )
}


@dataclass(frozen=True)
class PilotCandidate:
    ticker: str
    lane: str
    priority: int
    why_it_matters: str
    missing_input: str
    next_command: str
    validation_path: str
    proof_after_unlock: str
    source_boundary: str
    active_universe: bool = False
    demo_rank: int = 999


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _clean(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def _int_value(value: object, fallback: int = 99) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return fallback


def _ticker_filter(tickers: str | Iterable[str] | None) -> set[str] | None:
    if not tickers:
        return None
    if isinstance(tickers, str):
        values = tickers.split(",")
    else:
        values = tickers
    selected = {str(value).strip().upper() for value in values if str(value).strip()}
    return selected or None


def _readiness_lookup(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {_clean(row.get("ticker"), "").upper(): row for row in rows if _clean(row.get("ticker"), "")}


def _is_company_candidate(ticker: str, readiness_row: dict[str, str] | None) -> bool:
    if ticker in MONITOR_EXAMPLE_TICKERS:
        return False
    if not readiness_row:
        return True
    asset_type = _clean(readiness_row.get("asset_type"), "company").lower()
    if asset_type != "company":
        return False
    name = _clean(readiness_row.get("name"), "").lower()
    non_operating_markers = ("acquisition", "spac", "blank check")
    return not any(marker in name for marker in non_operating_markers)


def _candidate_sort_key(candidate: PilotCandidate) -> tuple[int, int, int, int, str]:
    lane_rank = {
        "fundamentals_dcf": 1,
        "peer_valuation_inputs": 2,
        "peer_mapping": 3,
        "optional_context_locked": 4,
    }.get(candidate.lane, 9)
    active_rank = 0 if candidate.active_universe else 1
    return (active_rank, candidate.demo_rank, lane_rank, candidate.priority, candidate.ticker)


def pilot_lane_label(lane: str) -> str:
    """Return a visitor-facing lane name for internal pilot lane codes."""

    return {
        "fundamentals_dcf": "Fundamentals / DCF unlock",
        "peer_mapping": "Peer mapping unlock",
        "peer_valuation_inputs": "Peer valuation inputs unlock",
        "optional_context_locked": "Optional context unlock",
    }.get(str(lane or "").strip(), "Trusted-data unlock")


def pilot_review_path(validation_path: str) -> str:
    """Show lane diagnostics separately from validate/preview/apply commands."""

    steps = [step.strip() for step in str(validation_path or "").split("->") if step.strip()]
    review_steps = [
        step
        for step in steps
        if step
        not in {
            "make imports-validate",
            "make imports-preview",
            "make imports-apply",
        }
    ]
    return " -> ".join(review_steps or steps) or "make trusted-data-pilot-candidates TOP_N=10"


def pilot_trusted_row_path(candidate: PilotCandidate) -> str:
    """Return the trusted local file or staging folder for a pilot lane."""

    if candidate.lane == "fundamentals_dcf":
        return "data/staged/fundamentals/ or data/imports/fundamentals.csv"
    if candidate.lane in {"peer_mapping", "peer_valuation_inputs"}:
        return "data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed"
    if candidate.lane == "optional_context_locked":
        return "data/staged/earnings/ or data/staged/analyst_estimates/"
    return "trusted local CSV import files"


def pilot_rank_reason(candidate: PilotCandidate) -> str:
    """Explain why a candidate appears in the ranked pilot queue."""

    scope = "active-universe" if candidate.active_universe else "master-universe"
    demo_note = "public-demo name" if candidate.demo_rank < 999 else "current local blocker"
    lane = pilot_lane_label(candidate.lane).lower()
    return (
        f"{scope} {demo_note}; {lane}; priority {candidate.priority}; "
        f"missing {plain_pilot_input_copy(candidate.missing_input)}."
    )


def plain_pilot_input_copy(value: object) -> str:
    """Translate raw readiness field names into visitor-facing blocker copy."""

    text = _clean(value, "trusted local input")
    replacements = {
        "analyst_estimates": "analyst estimates",
        "shares_outstanding": "shares outstanding",
        "fcf_margin": "free-cash-flow margin",
        "free_cash_flow": "free cash flow",
        "peer_valuation_ready": "peer valuation readiness",
    }
    for raw, label in replacements.items():
        text = re.sub(rf"\b{re.escape(raw)}\b", label, text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def pilot_operator_decision(candidate: PilotCandidate) -> str:
    """Explain the plain next decision for a pilot candidate."""

    if candidate.lane == "fundamentals_dcf":
        return (
            "Choose this company only if you can review trusted SEC or manual fundamentals rows; "
            "otherwise leave DCF blocked and move to the next candidate."
        )
    if candidate.lane == "peer_mapping":
        return (
            "Choose this company only if you can document source-backed peer relationships; "
            "sector or industry similarity is research context, not trusted peer data."
        )
    if candidate.lane == "peer_valuation_inputs":
        return (
            "Choose this company only if mapped peers also have trusted peer valuation inputs; "
            "otherwise show peer trend only and keep peer valuation blocked."
        )
    if candidate.lane == "optional_context_locked":
        return (
            "Choose this company only if trusted earnings or analyst-estimate rows are available; "
            "otherwise keep optional context intentionally locked."
        )
    return "Choose this candidate only when trusted source rows can be reviewed; otherwise keep it data-blocked."


def pilot_evidence_expectation(candidate: PilotCandidate) -> str:
    """Return the evidence that should exist before claiming a pilot unlock."""

    return (
        "Evidence required: before report, lane review output, trusted source row or source note, "
        "validate/preview/apply result if rows are applied, rebuilt readiness, after report, and still-blocked reason if unchanged. "
        f"Do not call {candidate.ticker} unlocked until the rebuilt report proves the lane changed."
    )


def build_trusted_data_pilot_candidates(
    fundamentals_rows: Iterable[dict[str, str]],
    peer_rows: Iterable[dict[str, str]],
    readiness_rows: Iterable[dict[str, str]],
    *,
    tickers: str | Iterable[str] | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> list[PilotCandidate]:
    """Return read-only company pilot candidates from current local outputs."""

    selected = _ticker_filter(tickers)
    readiness = _readiness_lookup(readiness_rows)
    by_ticker: dict[str, PilotCandidate] = {}

    def selected_ok(ticker: str) -> bool:
        return selected is None or ticker in selected

    for row in fundamentals_rows:
        ticker = _clean(row.get("ticker"), "").upper()
        if not ticker or not selected_ok(ticker):
            continue
        readiness_row = readiness.get(ticker)
        if not _is_company_candidate(ticker, readiness_row):
            continue
        missing_dcf = _clean(row.get("missing_required_for_dcf"), "")
        has_dcf = _truthy(row.get("dcf_ready"))
        if not missing_dcf or has_dcf:
            continue
        candidate = PilotCandidate(
            ticker=ticker,
            lane="fundamentals_dcf",
            priority=_int_value(row.get("priority")),
            why_it_matters="Unlocks company fundamentals review and the DCF readiness gate.",
            missing_input=missing_dcf,
            next_command=_clean(row.get("focus_command"), f"make focus-fundamentals TICKER={ticker}"),
            validation_path=(
                "make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER="
                f"{ticker} -> make imports-validate -> make imports-preview -> make imports-apply"
            ),
            proof_after_unlock=f"make readiness && make dcf-readiness && make stock-report-md TICKER={ticker}",
            source_boundary="Use SEC staging or trusted manual rows only; leave blank fields blocked.",
            active_universe=_truthy((readiness_row or {}).get("in_active_universe")),
            demo_rank=DEMO_COMPANY_ORDER.get(ticker, 999),
        )
        by_ticker[ticker] = candidate

    for row in peer_rows:
        ticker = _clean(row.get("ticker"), "").upper()
        if not ticker or not selected_ok(ticker):
            continue
        readiness_row = readiness.get(ticker)
        if not _is_company_candidate(ticker, readiness_row):
            continue
        blocker = _clean(row.get("peer_blocker_type"), "").lower()
        if not blocker:
            continue
        lane = "peer_mapping" if blocker == "missing_peer_mapping" else "peer_valuation_inputs"
        missing_input = _clean(row.get("missing_peer_reason"), _clean(row.get("peer_valuation_status"), "peer inputs"))
        next_command = _clean(row.get("focus_command"), f"make focus-peers TICKER={ticker}")
        validation_path = _clean(
            row.get("validation_sequence"),
            f"make peer-mapping-queue TOP_N=25 -> {next_command} -> make imports-validate -> make imports-preview -> make imports-apply",
        )
        candidate = PilotCandidate(
            ticker=ticker,
            lane=lane,
            priority=_int_value(row.get("priority")),
            why_it_matters=_clean(
                row.get("next_action_summary"),
                "Unlocks peer context without implying peer valuation is ready.",
            ),
            missing_input=missing_input,
            next_command=next_command,
            validation_path=validation_path,
            proof_after_unlock=f"make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER={ticker}",
            source_boundary="Peer rows must be source-backed; sector or industry fallback is context only.",
            active_universe=_truthy((readiness_row or {}).get("in_active_universe")),
            demo_rank=DEMO_COMPANY_ORDER.get(ticker, 999),
        )
        current = by_ticker.get(ticker)
        if current is None or _candidate_sort_key(candidate) < _candidate_sort_key(current):
            by_ticker[ticker] = candidate

    for ticker, row in readiness.items():
        if not ticker or ticker in by_ticker or not selected_ok(ticker):
            continue
        if not _is_company_candidate(ticker, row):
            continue
        if _truthy(row.get("peer_ready")):
            continue
        missing_data = _clean(row.get("missing_data"), "")
        next_action = _clean(row.get("next_action"), "")
        if "peer" not in missing_data.lower() and "peer" not in next_action.lower():
            continue
        candidate = PilotCandidate(
            ticker=ticker,
            lane="peer_mapping",
            priority=2 if _truthy(row.get("in_active_universe")) else 3,
            why_it_matters="Unlocks source-backed peer trend or peer valuation context for a visible company report.",
            missing_input=missing_data or "peer inputs",
            next_command=f"make focus-peers TICKER={ticker}",
            validation_path=(
                "make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER="
                f"{ticker} -> make imports-validate -> make imports-preview -> make imports-apply"
            ),
            proof_after_unlock=f"make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER={ticker}",
            source_boundary="Peer rows must be source-backed; do not treat sector or industry fallback as trusted peer valuation.",
            active_universe=_truthy(row.get("in_active_universe")),
            demo_rank=DEMO_COMPANY_ORDER.get(ticker, 999),
        )
        by_ticker[ticker] = candidate

    candidates = sorted(by_ticker.values(), key=_candidate_sort_key)
    return candidates[: max(top_n, 0)]


def load_trusted_data_pilot_candidates(
    *,
    root: Path,
    tickers: str | Iterable[str] | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> list[PilotCandidate]:
    return build_trusted_data_pilot_candidates(
        _read_csv(root / "outputs" / "fundamentals_peer_worklist.csv"),
        _read_csv(root / "outputs" / "peer_unlock_worklist.csv"),
        _read_csv(root / "data" / "reports" / "ticker_readiness_report.csv"),
        tickers=tickers,
        top_n=top_n,
    )


def render_trusted_data_pilot_candidates(candidates: list[PilotCandidate], *, top_n: int = DEFAULT_TOP_N) -> str:
    lines = [
        "Trusted Data Pilot Candidates",
        "Read-only: this command ranks current local blockers and does not refresh, import, edit CSVs, or change readiness outputs.",
        "",
    ]
    if not candidates:
        lines.extend(
            [
                "No operating-company pilot candidates matched the current filters.",
                "ETF/index monitor examples such as QQQ and SMH remain useful demos, but they are not company DCF pilot targets.",
                "Try: make trusted-data-pilot-candidates TOP_N=10",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"Top {min(top_n, len(candidates))} operating-company candidates:",
            "ETF/index monitor examples such as QQQ and SMH are excluded from this company pilot queue.",
            "Pilot lanes are plain-English unlock paths; they do not mean the missing data is available yet.",
            "",
        ]
    )
    for index, candidate in enumerate(candidates, start=1):
        scope = "active universe" if candidate.active_universe else "master universe"
        lines.extend(
            [
                f"{index}. {candidate.ticker} - {pilot_lane_label(candidate.lane)} ({scope}, priority {candidate.priority})",
                f"   Why it matters: {candidate.why_it_matters}",
                f"   Rank reason: {pilot_rank_reason(candidate)}",
                f"   Missing input: {plain_pilot_input_copy(candidate.missing_input)}",
                f"   Operator decision: {pilot_operator_decision(candidate)}",
                f"   Next command: {candidate.next_command}",
                f"   Review path: {pilot_review_path(candidate.validation_path)}",
                f"   Trusted row target: {pilot_trusted_row_path(candidate)}",
                "   Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply",
                f"   Proof after unlock: {candidate.proof_after_unlock}",
                f"   Evidence expectation: {pilot_evidence_expectation(candidate)}",
                f"   Source boundary: {candidate.source_boundary}",
                "",
            ]
        )

    ticker_list = ",".join(candidate.ticker for candidate in candidates)
    first = candidates[0].ticker
    lines.extend(
        [
            "Suggested safe loop:",
            "1. make readiness-snapshot",
            f"2. make trusted-data-pilot-packet TICKER={first}",
            f"3. Review the lane blocker: {pilot_review_path(candidates[0].validation_path)}",
            f"4. Prepare trusted rows only if the source review passes: {pilot_trusted_row_path(candidates[0])}",
            "5. Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply",
            f"6. Rebuild lane proof: {candidates[0].proof_after_unlock}",
            f"7. If still blocked, keep the blocker visible and move to the next candidate: make trusted-data-pilot TICKERS={ticker_list} TOP_N={len(candidates)}",
            "",
            "Stop condition: if trusted source rows are unavailable, keep the ticker data-blocked and move to the next candidate.",
        ]
    )
    return "\n".join(lines)


def render_trusted_data_pilot_packet(candidate: PilotCandidate | None, *, requested_ticker: str) -> str:
    ticker = requested_ticker.strip().upper()
    lines = [
        "Trusted Data Pilot Evidence Packet",
        "Read-only: this command prints a one-company proof loop and does not refresh, import, edit CSVs, or change readiness outputs.",
        "",
    ]
    if candidate is None:
        lines.extend(
            [
                f"No operating-company pilot candidate matched {ticker}.",
                "Run `make trusted-data-pilot-candidates TOP_N=10` to choose from current local blockers.",
                "ETF/index monitor examples such as QQQ and SMH are not operating-company DCF pilot targets.",
            ]
        )
        return "\n".join(lines)

    scope = "active universe" if candidate.active_universe else "master universe"
    lines.extend(
        [
            f"Ticker: {candidate.ticker}",
            f"Pilot lane: {pilot_lane_label(candidate.lane)}",
            f"Scope: {scope}",
            f"Priority: {candidate.priority}",
            f"Rank reason: {pilot_rank_reason(candidate)}",
            f"Why this candidate matters: {candidate.why_it_matters}",
            f"Missing trusted input: {plain_pilot_input_copy(candidate.missing_input)}",
            f"Operator decision: {pilot_operator_decision(candidate)}",
            f"Source boundary: {candidate.source_boundary}",
            f"Trusted row target: {pilot_trusted_row_path(candidate)}",
            "",
            "One-company evidence packet:",
            "1. Baseline readiness: make readiness-snapshot",
            f"2. Before report: make stock-report-md TICKER={candidate.ticker}",
            f"3. Focused blocker check: {candidate.next_command}",
            f"4. Prepare or stage trusted rows only if source review passes: {pilot_trusted_row_path(candidate)}",
            "5. Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply",
            f"6. Rebuild proof and after report: {candidate.proof_after_unlock}",
            "7. Record the evidence row and keep any remaining blocker visible.",
            "",
            pilot_evidence_expectation(candidate),
            "",
            "Evidence table row to record:",
            "ticker | before_mode | after_mode | changed_inputs | validation_commands | report_path | still_blocked_reason",
            "",
            "Stop condition: if trusted source rows are unavailable, keep this ticker data-blocked and move to the next candidate.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank read-only trusted-data pilot candidates.")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--tickers", default="")
    parser.add_argument("--packet", default="", help="Print a one-company evidence packet for the requested ticker.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.packet:
        ticker = args.packet.strip().upper()
        candidates = load_trusted_data_pilot_candidates(root=Path.cwd(), tickers=ticker, top_n=1)
        print(render_trusted_data_pilot_packet(candidates[0] if candidates else None, requested_ticker=ticker))
        return
    candidates = load_trusted_data_pilot_candidates(root=Path.cwd(), tickers=args.tickers, top_n=args.top_n)
    print(render_trusted_data_pilot_candidates(candidates, top_n=args.top_n))


if __name__ == "__main__":
    main()
