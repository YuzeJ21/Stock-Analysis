"""Read-only trusted-data pilot candidate list.

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
        "fundamentals_dcf": "Fundamentals / DCF proof path",
        "peer_mapping": "Peer mapping proof path",
        "peer_valuation_inputs": "Peer valuation inputs proof path",
        "optional_context_locked": "Optional context proof path",
    }.get(str(lane or "").strip(), "Trusted-data proof path")


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


def pilot_rejected_report_path(candidate: PilotCandidate) -> str:
    """Return the rejected-row report that must be checked for a pilot lane."""

    if candidate.lane == "fundamentals_dcf":
        return "data/rejected/fundamentals_import_rejected.csv"
    if candidate.lane in {"peer_mapping", "peer_valuation_inputs"}:
        return "data/rejected/peers_import_rejected.csv"
    if candidate.lane == "optional_context_locked":
        return "data/rejected/earnings_import_rejected.csv and data/rejected/analyst_estimates_import_rejected.csv"
    return "data/rejected/<dataset>_import_rejected.csv"


def _csv_data_row_count(path: Path) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    return max(len(rows) - 1, 0)


def _staged_file_count(path: Path) -> int | None:
    if not path.exists() or not path.is_dir():
        return None
    files = [
        item
        for item in path.iterdir()
        if item.is_file() and item.name != ".gitkeep"
    ]
    return len(files)


def pilot_local_file_status(candidate: PilotCandidate, *, root: Path) -> str:
    """Return read-only local file state for the lane without validating rows."""

    if candidate.lane == "fundamentals_dcf":
        import_rows = _csv_data_row_count(root / "data" / "imports" / "fundamentals.csv")
        staged_files = _staged_file_count(root / "data" / "staged" / "fundamentals")
        rejected_exists = (root / "data" / "rejected" / "fundamentals_import_rejected.csv").exists()
        return (
            "Local file status: fundamentals import "
            f"{'missing' if import_rows is None else f'{import_rows} data row(s)'}; "
            f"staged fundamentals {'missing' if staged_files is None else f'{staged_files} file(s)'}; "
            f"rejected-row report {'present' if rejected_exists else 'missing'}. "
            "Rows still require source review, validate, preview, apply, and readiness proof."
        )
    if candidate.lane in {"peer_mapping", "peer_valuation_inputs"}:
        import_rows = _csv_data_row_count(root / "data" / "imports" / "peers.csv")
        rejected_exists = (root / "data" / "rejected" / "peers_import_rejected.csv").exists()
        return (
            "Local file status: peer import "
            f"{'missing' if import_rows is None else f'{import_rows} data row(s)'}; "
            f"rejected-row report {'present' if rejected_exists else 'missing'}. "
            "Peer rows still require source-backed relationship review and readiness proof."
        )
    if candidate.lane == "optional_context_locked":
        earnings_rows = _csv_data_row_count(root / "data" / "imports" / "earnings.csv")
        estimate_rows = _csv_data_row_count(root / "data" / "imports" / "analyst_estimates.csv")
        staged_earnings = _staged_file_count(root / "data" / "staged" / "earnings")
        staged_estimates = _staged_file_count(root / "data" / "staged" / "analyst_estimates")
        staged_total = (0 if staged_earnings is None else staged_earnings) + (0 if staged_estimates is None else staged_estimates)
        return (
            "Local file status: earnings import "
            f"{'missing' if earnings_rows is None else f'{earnings_rows} data row(s)'}; "
            "analyst-estimates import "
            f"{'missing' if estimate_rows is None else f'{estimate_rows} data row(s)'}; "
            f"staged optional files {staged_total}. "
            "Optional rows remain locked until trusted local rows validate and readiness proves availability."
        )
    return "Local file status: not checked for this trusted-data lane."


def pilot_rank_reason(candidate: PilotCandidate) -> str:
    """Explain why a candidate appears in the ranked pilot list."""

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
    return "Choose this candidate only when trusted source rows can be reviewed; otherwise keep it visibly blocked by missing data."


def pilot_evidence_expectation(candidate: PilotCandidate) -> str:
    """Return the evidence that should exist before claiming a pilot lane is available."""

    return (
        "Evidence required: before report, lane review output, trusted source row or source note, "
        "validate/preview/apply result if rows are applied, rebuilt readiness, after report, and still-blocked reason if unchanged. "
        f"Do not call {candidate.ticker} available until the rebuilt report proves the lane changed."
    )


def pilot_skip_condition(candidate: PilotCandidate) -> str:
    """Return the condition that should stop work on this candidate."""

    if candidate.lane == "fundamentals_dcf":
        return "Skip for now if trusted SEC or manual fundamentals rows are not reviewable."
    if candidate.lane == "peer_mapping":
        return "Skip for now if peer relationships cannot be supported by a source note."
    if candidate.lane == "peer_valuation_inputs":
        return "Skip for now if mapped peers do not have trusted valuation inputs."
    if candidate.lane == "optional_context_locked":
        return "Skip for now if trusted earnings or analyst-estimate rows are unavailable."
    return "Skip for now if the trusted source proof is not available."


def pilot_evidence_row_template(candidate: PilotCandidate) -> str:
    """Return a copyable evidence row template for the selected pilot ticker."""

    report_path = f"outputs/stock_reports/{candidate.ticker.lower()}.md"
    return (
        f"{candidate.ticker} | before: run report | after: rerun report | "
        f"{plain_pilot_input_copy(candidate.missing_input)} | "
        "make imports-validate && make imports-preview && make imports-apply | "
        f"{report_path} | keep visible if source proof is unavailable or readiness remains blocked"
    )


def pilot_review_board_row(candidate: PilotCandidate) -> str:
    """Return a compact choose/skip/prove line for CLI review boards."""

    return (
        f"{candidate.ticker}: continue if source proof exists; {pilot_skip_condition(candidate)} "
        f"Packet: make trusted-data-pilot-packet TICKER={candidate.ticker}; "
        f"evidence row: {pilot_evidence_row_template(candidate)}"
    )


def pilot_public_shortlist(candidates: list[PilotCandidate], *, limit: int = 10) -> list[PilotCandidate]:
    """Prefer active or public-demo names for the small trusted-data pilot."""

    public_candidates = [candidate for candidate in candidates if candidate.active_universe or candidate.demo_rank < 999]
    selected = public_candidates or candidates
    return selected[: max(limit, 0)]


def pilot_decision_gate(candidate: PilotCandidate) -> str:
    """Return the plain-language go/no-go gate for a one-company pilot packet."""

    if candidate.lane == "fundamentals_dcf":
        proof = "trusted SEC or manual fundamentals rows for the missing DCF fields"
        stop = "leave fundamentals and DCF blocked"
    elif candidate.lane == "peer_mapping":
        proof = "source-backed peer relationships, not sector or industry similarity alone"
        stop = "leave peer valuation blocked and show peer context only when supported"
    elif candidate.lane == "peer_valuation_inputs":
        proof = "mapped peers plus trusted peer valuation inputs"
        stop = "show peer trend only and leave peer valuation blocked"
    elif candidate.lane == "optional_context_locked":
        proof = "trusted earnings or analyst-estimate rows"
        stop = "leave optional context intentionally locked"
    else:
        proof = "trusted source rows for the missing input"
        stop = "keep the ticker visibly blocked by missing data"
    return (
        f"Decision gate: continue only if you have {proof}. "
        f"If not, {stop}; do not apply placeholder rows just to make the report look complete."
    )


def pilot_selection_brief(candidates: list[PilotCandidate]) -> list[str]:
    """Return concise operator guidance for choosing a small trusted-data pilot."""

    if not candidates:
        return [
            "Pilot selection rule: no company candidates matched the current filters, so do not force a pilot.",
            "Next move: rebuild readiness outputs or choose a different company filter before importing rows.",
        ]

    active_count = sum(1 for candidate in candidates if candidate.active_universe)
    lane_counts: dict[str, int] = {}
    for candidate in candidates:
        lane_counts[candidate.lane] = lane_counts.get(candidate.lane, 0) + 1
    lane_summary = ", ".join(
        f"{pilot_lane_label(lane)}: {count}" for lane, count in sorted(lane_counts.items())
    )
    suggested_candidates = pilot_public_shortlist(candidates, limit=10)
    suggested = ",".join(candidate.ticker for candidate in suggested_candidates)
    overflow = [candidate.ticker for candidate in candidates if candidate not in suggested_candidates]
    overflow_line = (
        f"Optional broad-universe overflow: {', '.join(overflow[:5])}; use only after source proof exists."
        if overflow
        else "No broad-universe overflow is needed for the first pilot shortlist."
    )
    return [
        "Pilot selection rule: choose 5-10 operating companies only when you can review source proof for the missing input.",
        f"Current short list: {active_count} active-universe candidate(s); lane mix: {lane_summary}.",
        f"Suggested pilot command after choosing active/demo names: make trusted-data-pilot TICKERS={suggested} TOP_N={len(suggested_candidates)}",
        overflow_line,
        "Useful pilot win: before report, lane review, trusted source row, validate/preview/apply if rows change, rebuilt readiness, after report, and any still-blocked reason.",
        "If source proof is unavailable, keep that ticker blocked and move to the next candidate rather than filling placeholder data.",
    ]


def pilot_quick_path_lines(candidates: list[PilotCandidate]) -> list[str]:
    """Return the shortest visitor-facing path before detailed evidence rows."""

    if not candidates:
        return [
            "Quick path: no company pilot is available from the current filters.",
            "Next command: make trusted-data-pilot-candidates TOP_N=10 after rebuilding readiness outputs.",
        ]
    shortlist = pilot_public_shortlist(candidates, limit=10)
    first = shortlist[0]
    return [
        f"Shortlist: {', '.join(candidate.ticker for candidate in shortlist)}.",
        f"Start with one packet: make trusted-data-pilot-packet TICKER={first.ticker}",
        f"Review its lane: {pilot_review_path(first.validation_path)}",
        f"Trusted input target: {pilot_trusted_row_path(first)}",
        f"Stop if source proof is unavailable: keep {first.ticker} visibly blocked and move to the next shortlisted company.",
    ]


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
            why_it_matters="Proves whether company fundamentals review and the DCF readiness gate can become available.",
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
                "Proves whether peer context can become available without implying peer valuation is ready.",
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
            why_it_matters="Proves whether source-backed peer trend or peer valuation context can become available for a visible company report.",
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


def render_trusted_data_pilot_candidates(
    candidates: list[PilotCandidate],
    *,
    top_n: int = DEFAULT_TOP_N,
    root: Path | None = None,
    verbose: bool = False,
) -> str:
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
            "ETF/index monitor examples such as QQQ and SMH are excluded from this company pilot list.",
            "Pilot lanes are plain-English proof paths; they do not mean the missing data is available yet.",
            "",
            "How to choose the pilot:",
            *[f"- {line}" for line in pilot_selection_brief(candidates)],
            "",
            "Quick path:",
            *[f"- {line}" for line in pilot_quick_path_lines(candidates)],
            "",
            "Compact review board:",
            *[f"- {pilot_review_board_row(candidate)}" for candidate in candidates[: min(top_n, len(candidates))]],
            "",
        ]
    )
    if verbose:
        lines.append("Verbose candidate details:")
        for index, candidate in enumerate(candidates, start=1):
            scope = "active universe" if candidate.active_universe else "master universe"
            lines.extend(
                [
                    f"{index}. {candidate.ticker} - {pilot_lane_label(candidate.lane)} ({scope}, priority {candidate.priority})",
                    f"   Why it matters: {candidate.why_it_matters}",
                    f"   Rank reason: {pilot_rank_reason(candidate)}",
                    f"   Missing input: {plain_pilot_input_copy(candidate.missing_input)}",
                    f"   Next decision: {pilot_operator_decision(candidate)}",
                    f"   {pilot_decision_gate(candidate)}",
                    f"   Packet command: make trusted-data-pilot-packet TICKER={candidate.ticker}",
                    f"   Lane check: {candidate.next_command}",
                    f"   Review path: {pilot_review_path(candidate.validation_path)}",
                    f"   Trusted row target: {pilot_trusted_row_path(candidate)}",
                    f"   {pilot_local_file_status(candidate, root=root) if root is not None else 'Local file status: not checked in this render.'}",
                    f"   Skip if: {pilot_skip_condition(candidate)}",
                    "   Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply",
                    f"   Rejected-row report to review: {pilot_rejected_report_path(candidate)}",
                    f"   Proof after data changes: {candidate.proof_after_unlock}",
                    f"   Evidence expectation: {pilot_evidence_expectation(candidate)}",
                    f"   Source boundary: {candidate.source_boundary}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "Need full candidate detail? Rerun with `make trusted-data-pilot-candidates VERBOSE=1`.",
                "",
            ]
        )

    safe_loop_candidates = pilot_public_shortlist(candidates, limit=10)
    ticker_list = ",".join(candidate.ticker for candidate in safe_loop_candidates)
    first = candidates[0].ticker
    lines.extend(
        [
            "Suggested safe loop:",
            "1. make readiness-snapshot",
            f"2. make trusted-data-pilot-packet TICKER={first}",
            f"3. Review the lane blocker: {pilot_review_path(candidates[0].validation_path)}",
            f"4. Prepare trusted rows only if the source review passes: {pilot_trusted_row_path(candidates[0])}",
            "5. Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply",
            f"6. Check rejected-row report: {pilot_rejected_report_path(candidates[0])}",
            f"7. Rebuild lane proof: {candidates[0].proof_after_unlock}",
            f"8. If still blocked, keep the blocker visible and move to the next active/demo candidate: make trusted-data-pilot TICKERS={ticker_list} TOP_N={len(safe_loop_candidates)}",
            "",
            "Stop condition: if trusted source rows are unavailable, keep the ticker visibly blocked by missing data and move to the next candidate.",
        ]
    )
    return "\n".join(lines)


def render_trusted_data_pilot_packet(
    candidate: PilotCandidate | None,
    *,
    requested_ticker: str,
    root: Path | None = None,
) -> str:
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
            f"Next decision: {pilot_operator_decision(candidate)}",
            pilot_decision_gate(candidate),
            f"Source boundary: {candidate.source_boundary}",
            f"Trusted row target: {pilot_trusted_row_path(candidate)}",
            pilot_local_file_status(candidate, root=root) if root is not None else "Local file status: not checked in this render.",
            f"Skip if: {pilot_skip_condition(candidate)}",
            "",
            "One-company evidence packet:",
            "1. Baseline readiness: make readiness-snapshot",
            f"2. Before report: make stock-report-md TICKER={candidate.ticker}",
            f"3. Focused blocker check: {candidate.next_command}",
            f"4. Prepare or stage trusted rows only if source review passes: {pilot_trusted_row_path(candidate)}",
            "5. Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply",
            f"6. Check rejected-row report: {pilot_rejected_report_path(candidate)}",
            f"7. Rebuild proof and after report: {candidate.proof_after_unlock}",
            "8. Record the evidence row and keep any remaining blocker visible.",
            "",
            pilot_evidence_expectation(candidate),
            "",
            "Evidence table row to record:",
            "ticker | before_mode | after_mode | changed_inputs | validation_commands | report_path | still_blocked_reason",
            pilot_evidence_row_template(candidate),
            "",
            "Stop condition: if trusted source rows are unavailable, keep this ticker visibly blocked by missing data and move to the next candidate.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank read-only trusted-data pilot candidates.")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--tickers", default="")
    parser.add_argument("--packet", default="", help="Print a one-company evidence packet for the requested ticker.")
    parser.add_argument("--verbose", action="store_true", help="Print full per-candidate evidence details.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.packet:
        ticker = args.packet.strip().upper()
        candidates = load_trusted_data_pilot_candidates(root=Path.cwd(), tickers=ticker, top_n=1)
        print(render_trusted_data_pilot_packet(candidates[0] if candidates else None, requested_ticker=ticker, root=Path.cwd()))
        return
    candidates = load_trusted_data_pilot_candidates(root=Path.cwd(), tickers=args.tickers, top_n=args.top_n)
    print(render_trusted_data_pilot_candidates(candidates, top_n=args.top_n, root=Path.cwd(), verbose=args.verbose))


if __name__ == "__main__":
    main()
