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


@dataclass(frozen=True)
class PilotLaneRunbook:
    lane: str
    label: str
    status: str
    what_proves_lane: str
    needed_rows_files: str
    rejected_row_reports: str
    readiness_proof_command: str
    remains_blocked_when: str
    ordered_steps: tuple[str, ...]
    next_safe_command: str
    locked_manual_note: str = ""


PILOT_EVIDENCE_COLUMNS = (
    "ticker",
    "pilot_lane",
    "scope",
    "before_mode",
    "after_mode",
    "outcome_state",
    "current_outcome",
    "changed_inputs",
    "review_command",
    "validation_commands",
    "proof_command",
    "report_path",
    "trusted_row_target",
    "rejected_row_report",
    "still_blocked_reason",
    "source_boundary",
    "local_file_status",
)


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


def _report_mode(root: Path, ticker: str) -> str:
    path = root / "outputs" / "stock_reports" / f"{ticker.lower()}.md"
    if not path.exists():
        return "before report missing; run make stock-report-md first"
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text.startswith("- Mode:"):
            value = text.replace("- Mode:", "", 1).strip().rstrip(".")
            return value.strip("`")
    return "before report generated; mode not found"


def _readiness_row(root: Path, ticker: str, *, previous: bool = False) -> dict[str, str] | None:
    filename = "ticker_readiness_report.previous.csv" if previous else "ticker_readiness_report.csv"
    rows = _read_csv(root / "data" / "reports" / filename)
    lookup = _readiness_lookup(rows)
    return lookup.get(ticker.strip().upper())


def _readiness_mode(row: dict[str, str] | None) -> str:
    if not row:
        return "baseline snapshot missing; run make readiness-snapshot first"
    if _truthy(row.get("dcf_ready")) and _truthy(row.get("peer_ready")):
        return "DCF-ready review"
    if _truthy(row.get("dcf_ready")):
        return "Standalone DCF review"
    if _truthy(row.get("price_ready")) or _truthy(row.get("momentum_ready")):
        return "Price/setup review only"
    return "Data needed before analysis"


def _prior_dcf_missing_input(row: dict[str, str] | None) -> str:
    if not row:
        return "trusted fundamentals / DCF inputs"
    missing_data = _clean(row.get("missing_data"), "")
    match = re.search(r"dcf:\s*([^;]+)", missing_data, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return _clean(row.get("blocked_features"), "trusted fundamentals / DCF inputs")


def _prior_peer_missing_input(row: dict[str, str] | None) -> str:
    if not row:
        return "peer fundamentals or peer price/market-cap context"
    missing_data = _clean(row.get("missing_data"), "")
    match = re.search(r"peers:\s*([^;]+)", missing_data, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "peer fundamentals or peer price/market-cap context"


def _completed_peer_input(root: Path, ticker: str, fallback: str) -> str:
    peer_rows = _read_csv(root / "data" / "reports" / "peer_readiness_report.csv")
    peer_lookup = _readiness_lookup(peer_rows)
    peer_row = peer_lookup.get(ticker.strip().upper())
    sample_peers = _clean((peer_row or {}).get("sample_peers"), "")
    if sample_peers:
        return f"verified mapped-peer price history and SEC fundamentals for {sample_peers}"
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


LANE_ALIASES = {
    "fundamentals": "fundamentals_dcf",
    "fundamental": "fundamentals_dcf",
    "fundamentals_dcf": "fundamentals_dcf",
    "dcf": "fundamentals_dcf",
    "peer_mapping": "peer_mapping",
    "peer_mappings": "peer_mapping",
    "peers": "peer_mapping",
    "peer": "peer_mapping",
    "peer_valuation": "peer_valuation_inputs",
    "peer_valuation_input": "peer_valuation_inputs",
    "peer_valuation_inputs": "peer_valuation_inputs",
    "mapped_peer_inputs": "peer_valuation_inputs",
    "optional": "optional_context_locked",
    "optional_context": "optional_context_locked",
    "optional_context_locked": "optional_context_locked",
    "earnings": "optional_context_locked",
    "analyst_estimates": "optional_context_locked",
    "analyst-estimates": "optional_context_locked",
    "price": "price_coverage",
    "prices": "price_coverage",
    "price_coverage": "price_coverage",
    "coverage": "price_coverage",
}


def normalize_pilot_lane(value: str) -> str:
    """Normalize a lane-group alias for CLI and dashboard use."""

    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if normalized in LANE_ALIASES:
        return LANE_ALIASES[normalized]
    raise ValueError(
        "Unknown trusted-data pilot lane. Use one of: fundamentals_dcf, peer_mapping, "
        "peer_valuation_inputs, optional_context_locked, price_coverage."
    )


def pilot_lane_label(lane: str) -> str:
    """Return a visitor-facing lane name for internal pilot lane codes."""

    return {
        "fundamentals_dcf": "Fundamentals / DCF proof path",
        "peer_mapping": "Peer mapping proof path",
        "peer_valuation_inputs": "Peer valuation inputs proof path",
        "optional_context_locked": "Optional context proof path",
        "price_coverage": "Price coverage dry-run path",
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
    if candidate.lane == "peer_mapping":
        return "data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed"
    if candidate.lane == "peer_valuation_inputs":
        return (
            "reviewed mapped-peer fundamentals in data/imports/fundamentals.csv or verified peer price history; "
            "use data/imports/peers.csv only if mappings change"
        )
    if candidate.lane == "optional_context_locked":
        return "data/staged/earnings/ or data/staged/analyst_estimates/"
    return "trusted local CSV import files"


def pilot_rejected_report_path(candidate: PilotCandidate) -> str:
    """Return the rejected-row report that must be checked for a pilot lane."""

    if candidate.lane == "fundamentals_dcf":
        return "data/rejected/fundamentals_import_rejected.csv"
    if candidate.lane == "peer_mapping":
        return "data/rejected/peers_import_rejected.csv"
    if candidate.lane == "peer_valuation_inputs":
        return "data/rejected/fundamentals_import_rejected.csv and data/rejected/price_import_rejected.csv when peer price rows change"
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
            "File presence is not proof. Rows still require source review, validate, preview, apply, and readiness proof."
        )
    if candidate.lane == "peer_mapping":
        import_rows = _csv_data_row_count(root / "data" / "imports" / "peers.csv")
        rejected_exists = (root / "data" / "rejected" / "peers_import_rejected.csv").exists()
        return (
            "Local file status: peer import "
            f"{'missing' if import_rows is None else f'{import_rows} data row(s)'}; "
            f"rejected-row report {'present' if rejected_exists else 'missing'}. "
            "File presence is not proof. Peer rows still require source-backed relationship review and readiness proof."
        )
    if candidate.lane == "peer_valuation_inputs":
        peer_rows = _csv_data_row_count(root / "data" / "imports" / "peers.csv")
        fundamentals_rows = _csv_data_row_count(root / "data" / "imports" / "fundamentals.csv")
        fundamentals_rejected = (root / "data" / "rejected" / "fundamentals_import_rejected.csv").exists()
        price_rejected = (root / "data" / "rejected" / "price_import_rejected.csv").exists()
        return (
            "Local file status: peer mapping import "
            f"{'missing' if peer_rows is None else f'{peer_rows} data row(s)'}; "
            "fundamentals import "
            f"{'missing' if fundamentals_rows is None else f'{fundamentals_rows} data row(s)'}; "
            "rejected-row reports "
            f"fundamentals {'present' if fundamentals_rejected else 'missing'}, "
            f"price {'present' if price_rejected else 'missing'}. "
            "File presence is not proof. Mapped peers still require trusted fundamentals or verified price-history proof before peer valuation appears."
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
            "File presence is not proof. Optional rows remain locked until trusted local rows validate and readiness proves availability."
        )
    return "Local file status: not checked for this trusted-data lane."


def pilot_rank_reason(candidate: PilotCandidate) -> str:
    """Explain why a candidate appears in the ranked pilot list."""

    scope = "active-universe" if candidate.active_universe else "master-universe"
    demo_note = "public-demo name" if candidate.demo_rank < 999 else "current local blocker"
    lane = pilot_lane_label(candidate.lane).lower()
    return (
        f"{scope} {demo_note}; {lane}; priority {candidate.priority}; "
        f"missing {pilot_primary_missing_input(candidate)}."
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


def pilot_primary_missing_input(candidate: PilotCandidate) -> str:
    """Return the lane-specific blocker before secondary optional-context locks."""

    parts = plain_pilot_input_copy(candidate.missing_input).split("; ")
    primary = parts[0]
    if (
        candidate.lane == "peer_valuation_inputs"
        and len(parts) > 1
        and "ready" in primary.lower()
    ):
        primary = parts[1]
    return re.sub(r"^peer valuation still requires\s+", "", primary, flags=re.IGNORECASE)


def pilot_secondary_locked_context(candidate: PilotCandidate) -> str:
    """Return secondary locked context that should stay visible but not drive the pilot lane."""

    missing_input = plain_pilot_input_copy(candidate.missing_input)
    if "; " not in missing_input:
        return ""
    secondary = missing_input.split("; ", 1)[1]
    if re.search(r"\b(earnings|analyst estimates|optional)\b", secondary, flags=re.IGNORECASE):
        return secondary
    return ""


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
        "outcome_state: supported/still_blocked/skipped/excluded | "
        f"{pilot_primary_missing_input(candidate)} | "
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


def pilot_compact_board_row(candidate: PilotCandidate) -> str:
    """Return a short visitor-facing candidate row without row-level diagnostics."""

    missing_input = pilot_primary_missing_input(candidate)
    if pilot_secondary_locked_context(candidate):
        missing_input = f"{missing_input}; optional context locked"
    return (
        f"{candidate.ticker}: {pilot_lane_label(candidate.lane)}; "
        f"missing input: {missing_input}; "
        f"packet make trusted-data-pilot-packet TICKER={candidate.ticker}; "
        "skip if source proof is unavailable."
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
    fundamentals_first = next(
        (candidate for candidate in shortlist if candidate.lane == "fundamentals_dcf"),
        None,
    )
    lines = [
        f"Shortlist: {', '.join(candidate.ticker for candidate in shortlist)}.",
        f"Start with one packet: make trusted-data-pilot-packet TICKER={first.ticker}",
        f"Review its lane: {pilot_review_path(first.validation_path)}",
        f"Trusted input target: {pilot_trusted_row_path(first)}",
        f"Stop if source proof is unavailable: keep {first.ticker} visibly blocked and move to the next shortlisted company.",
    ]
    if fundamentals_first and fundamentals_first.ticker != first.ticker:
        lines.insert(
            2,
            f"For a fundamentals/DCF proof demo, use make trusted-data-pilot-packet TICKER={fundamentals_first.ticker}",
        )
    return lines


def pilot_proof_story_lines(candidate: PilotCandidate | None = None) -> list[str]:
    """Explain the trusted-data proof loop without turning it into data claims."""

    ticker = candidate.ticker if candidate else "<ticker>"
    lane = pilot_lane_label(candidate.lane) if candidate else "the selected proof path"
    return [
        "Baseline: snapshot current readiness and generate a before report so the starting mode is visible.",
        f"Source proof: review {ticker} in the {lane} and add rows only when the source evidence is trusted.",
        "Validation: validate, preview, and check rejected rows before applying any local CSV change.",
        "Rebuild: rerun readiness and the stock report; only the rebuilt report can prove the lane changed.",
        "Stop rule: if source proof is missing or the rebuilt report is still blocked, keep the blocker visible and move to the next candidate.",
    ]


def pilot_outcome_checklist_lines(candidate: PilotCandidate | None = None) -> list[str]:
    """Explain how to read the result after the proof loop without overclaiming."""

    ticker = candidate.ticker if candidate else "<ticker>"
    primary_input = pilot_primary_missing_input(candidate) if candidate else "the primary lane input"
    return [
        f"Supported: {ticker} moves forward only if rebuilt readiness and the regenerated report show the lane is ready.",
        f"Still blocked: keep {primary_input} visible when validation fails, rejected rows appear, or the report remains locked.",
        "Skip: if source proof is unavailable, do not apply placeholder rows; move to the next shortlisted company.",
    ]


def pilot_outcome_state_guide(candidate: PilotCandidate | None = None) -> str:
    """Return the durable outcome-state contract for pilot evidence."""

    ticker = candidate.ticker if candidate else "<ticker>"
    return (
        "Outcome states: supported means rebuilt readiness and the regenerated report prove the lane changed; "
        "still_blocked means validation failed, rejected rows appeared, or readiness/report output stayed locked; "
        f"skipped means source proof was unavailable for {ticker}; "
        "excluded means the ticker is not an operating-company pilot target."
    )


def pilot_current_outcome_state(
    candidate: PilotCandidate,
    current_readiness: dict[str, str] | None,
    *,
    peer_readiness: dict[str, str] | None = None,
) -> str:
    """Classify current evidence without implying an unavailable data unlock."""

    current_row = current_readiness or {}
    asset_type = _clean(current_row.get("asset_type"), "company").lower()
    if asset_type and asset_type != "company":
        return "excluded"
    supported = (
        (
            candidate.lane == "fundamentals_dcf"
            and _truthy(current_row.get("fundamentals_ready"))
            and _truthy(current_row.get("dcf_ready"))
        )
        or (
            candidate.lane == "peer_mapping"
            and _truthy(current_row.get("peer_ready"))
        )
        or (
            candidate.lane == "peer_valuation_inputs"
            and (
                _truthy((peer_readiness or {}).get("peer_valuation_ready"))
                or _truthy((peer_readiness or {}).get("peer_valuation_comparison_ready"))
            )
        )
        or (
            candidate.lane == "optional_context_locked"
            and (
                _truthy(current_row.get("earnings_ready"))
                or _truthy(current_row.get("analyst_estimates_ready"))
            )
        )
    )
    return "supported" if supported else "still_blocked"


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
        if missing_dcf and not has_dcf:
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

        missing_peer_relative = _clean(row.get("missing_required_for_peer_relative"), "")
        peer_ready = _truthy(row.get("peer_ready"))
        if missing_peer_relative and not peer_ready:
            has_peer_mapping = _truthy(row.get("has_peer_mapping"))
            lane = "peer_valuation_inputs" if has_peer_mapping else "peer_mapping"
            peer_review_command = f"make focus-peers TICKER={ticker}"
            peer_metric_command = _clean(row.get("focus_command"), "")
            validation_path = (
                f"make peer-mapping-queue TOP_N=25 -> {peer_review_command}"
                + (f" -> {peer_metric_command}" if peer_metric_command and peer_metric_command != peer_review_command else "")
                + " -> make imports-validate -> make imports-preview -> make imports-apply"
            )
            candidate = PilotCandidate(
                ticker=ticker,
                lane=lane,
                priority=_int_value(row.get("priority")),
                why_it_matters=_clean(
                    row.get("recommended_action"),
                    "Proves whether source-backed peer context can become available for a DCF-ready company report.",
                ),
                missing_input=missing_peer_relative,
                next_command=peer_review_command,
                validation_path=validation_path,
                proof_after_unlock=f"make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER={ticker}",
                source_boundary="Peer rows must be source-backed; sector or industry fallback is context only.",
                active_universe=_truthy((readiness_row or {}).get("in_active_universe")),
                demo_rank=DEMO_COMPANY_ORDER.get(ticker, 999),
            )
            current = by_ticker.get(ticker)
            if current is None or _candidate_sort_key(candidate) < _candidate_sort_key(current):
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


def load_trusted_data_pilot_evidence_candidates(
    *,
    root: Path,
    tickers: str | Iterable[str] | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> list[PilotCandidate]:
    """Load candidates for evidence, preserving completed selected DCF pilots."""

    selected = _ticker_filter(tickers)
    current_candidates = load_trusted_data_pilot_candidates(root=root, tickers=tickers, top_n=top_n)
    if selected is None:
        return current_candidates

    current_readiness = _readiness_lookup(_read_csv(root / "data" / "reports" / "ticker_readiness_report.csv"))
    prior_readiness = _readiness_lookup(_read_csv(root / "data" / "reports" / "ticker_readiness_report.previous.csv"))
    by_ticker = {candidate.ticker: candidate for candidate in current_candidates}

    for ticker in sorted(selected):
        current_row = current_readiness.get(ticker)
        prior_row = prior_readiness.get(ticker)
        completed_fundamentals = (
            current_row is not None
            and prior_row is not None
            and not _truthy(prior_row.get("dcf_ready"))
            and _truthy(current_row.get("fundamentals_ready"))
            and _truthy(current_row.get("dcf_ready"))
        )
        completed_peer = (
            current_row is not None
            and prior_row is not None
            and not _truthy(prior_row.get("peer_ready"))
            and _truthy(current_row.get("peer_ready"))
        )
        if not completed_fundamentals:
            if completed_peer:
                by_ticker[ticker] = PilotCandidate(
                    ticker=ticker,
                    lane="peer_valuation_inputs",
                    priority=2,
                    why_it_matters="Records the completed source-backed peer valuation input proof path.",
                    missing_input=_completed_peer_input(root, ticker, _prior_peer_missing_input(prior_row)),
                    next_command=f"make focus-peers TICKER={ticker}",
                    validation_path=(
                        f"make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER={ticker} "
                        "-> make imports-validate -> make imports-preview -> make imports-apply"
                    ),
                    proof_after_unlock=f"make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER={ticker}",
                    source_boundary="Peer rows must be source-backed; sector or industry fallback is context only.",
                    active_universe=_truthy((current_row or {}).get("in_active_universe")),
                    demo_rank=DEMO_COMPANY_ORDER.get(ticker, 999),
                )
            continue
        by_ticker[ticker] = PilotCandidate(
            ticker=ticker,
            lane="fundamentals_dcf",
            priority=1,
            why_it_matters="Records the completed source-backed fundamentals and DCF proof path.",
            missing_input=_prior_dcf_missing_input(prior_row),
            next_command=f"make focus-fundamentals TICKER={ticker}",
            validation_path=(
                f"make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER={ticker} "
                "-> make imports-validate -> make imports-preview -> make imports-apply"
            ),
            proof_after_unlock=f"make readiness && make dcf-readiness && make stock-report-md TICKER={ticker}",
            source_boundary="Use SEC staging or trusted manual rows only; leave blank fields blocked.",
            active_universe=_truthy((current_row or {}).get("in_active_universe")),
            demo_rank=DEMO_COMPANY_ORDER.get(ticker, 999),
        )

    return sorted(by_ticker.values(), key=_candidate_sort_key)[: max(top_n, 0)]


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
            "What the proof loop proves:",
            *[f"- {line}" for line in pilot_proof_story_lines(candidates[0])],
            "",
            "How to read the outcome:",
            *[f"- {line}" for line in pilot_outcome_checklist_lines(candidates[0])],
            f"- {pilot_outcome_state_guide(candidates[0])}",
            "",
            "Compact review board:",
            *[f"- {pilot_compact_board_row(candidate)}" for candidate in candidates[: min(top_n, len(candidates))]],
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
                    f"   Primary lane input: {pilot_primary_missing_input(candidate)}",
                    *(
                        [f"   Secondary locked context: {pilot_secondary_locked_context(candidate)}"]
                        if pilot_secondary_locked_context(candidate)
                        else []
                    ),
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
                    f"   Evidence row: {pilot_evidence_row_template(candidate)}",
                    f"   Source boundary: {candidate.source_boundary}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                f"Need local proof detail? Rerun with `make trusted-data-pilot-candidates TOP_N={top_n} VERBOSE=1`.",
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
    secondary_context = pilot_secondary_locked_context(candidate)
    lines.extend(
        [
            f"Ticker: {candidate.ticker}",
            f"Pilot lane: {pilot_lane_label(candidate.lane)}",
            f"Scope: {scope}",
            f"Priority: {candidate.priority}",
            f"Rank reason: {pilot_rank_reason(candidate)}",
            f"Why this candidate matters: {candidate.why_it_matters}",
            f"Primary lane input: {pilot_primary_missing_input(candidate)}",
            *([f"Secondary locked context: {secondary_context}"] if secondary_context else []),
            f"Next decision: {pilot_operator_decision(candidate)}",
            pilot_decision_gate(candidate),
            f"Source boundary: {candidate.source_boundary}",
            f"Trusted row target: {pilot_trusted_row_path(candidate)}",
            pilot_local_file_status(candidate, root=root) if root is not None else "Local file status: not checked in this render.",
            f"Skip if: {pilot_skip_condition(candidate)}",
            "",
            "One-company evidence packet:",
            "What this proves before any conclusion changes:",
            *[f"- {line}" for line in pilot_proof_story_lines(candidate)],
            "How to read the outcome:",
            *[f"- {line}" for line in pilot_outcome_checklist_lines(candidate)],
            f"- {pilot_outcome_state_guide(candidate)}",
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
            "ticker | before_mode | after_mode | outcome_state | changed_inputs | validation_commands | report_path | still_blocked_reason",
            pilot_evidence_row_template(candidate),
            "",
            "Stop condition: if trusted source rows are unavailable, keep this ticker visibly blocked by missing data and move to the next candidate.",
        ]
    )
    return "\n".join(lines)


def build_trusted_data_pilot_evidence_rows(
    candidates: list[PilotCandidate],
    *,
    root: Path,
) -> list[dict[str, str]]:
    """Build a read-only pilot evidence ledger from current local artifacts."""

    rows: list[dict[str, str]] = []
    peer_readiness_lookup = _readiness_lookup(_read_csv(root / "data" / "reports" / "peer_readiness_report.csv"))
    for candidate in candidates:
        prior_readiness = _readiness_row(root, candidate.ticker, previous=True)
        current_readiness = _readiness_row(root, candidate.ticker)
        current_report_mode = _report_mode(root, candidate.ticker)
        before_mode = _readiness_mode(prior_readiness) if prior_readiness else current_report_mode
        outcome_state = pilot_current_outcome_state(
            candidate,
            current_readiness,
            peer_readiness=peer_readiness_lookup.get(candidate.ticker),
        )
        supported = outcome_state == "supported"
        excluded = outcome_state == "excluded"
        after_mode = current_report_mode if supported else "pending rebuilt report after trusted rows"
        current_outcome = (
            "supported by rebuilt readiness and regenerated report"
            if supported
            else "excluded from the operating-company pilot target list"
            if excluded
            else "still blocked or unproven until rebuilt readiness changes"
        )
        still_blocked_reason = (
            f"Resolved by source-backed rebuild: {pilot_primary_missing_input(candidate)}"
            if supported
            else "Excluded from this company pilot because the ticker is not an operating-company target."
            if excluded
            else (
                f"Keep visible if source proof is unavailable or readiness remains blocked: "
                f"{pilot_primary_missing_input(candidate)}"
            )
        )
        report_path = f"outputs/stock_reports/{candidate.ticker.lower()}.md"
        rows.append(
            {
                "ticker": candidate.ticker,
                "pilot_lane": pilot_lane_label(candidate.lane),
                "scope": "active universe" if candidate.active_universe else "master universe",
                "before_mode": before_mode,
                "after_mode": after_mode,
                "outcome_state": outcome_state,
                "current_outcome": current_outcome,
                "changed_inputs": pilot_primary_missing_input(candidate),
                "review_command": candidate.next_command,
                "validation_commands": "make imports-validate && make imports-preview && make imports-apply",
                "proof_command": candidate.proof_after_unlock,
                "report_path": report_path,
                "trusted_row_target": pilot_trusted_row_path(candidate),
                "rejected_row_report": pilot_rejected_report_path(candidate),
                "still_blocked_reason": still_blocked_reason,
                "source_boundary": candidate.source_boundary,
                "local_file_status": pilot_local_file_status(candidate, root=root),
            }
        )
    return rows


def write_trusted_data_pilot_evidence(
    candidates: list[PilotCandidate],
    *,
    root: Path,
    output_path: Path,
) -> Path:
    """Write a CSV evidence ledger without changing source data or readiness."""

    rows = build_trusted_data_pilot_evidence_rows(candidates, root=root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PILOT_EVIDENCE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def render_trusted_data_pilot_board(
    candidates: list[PilotCandidate],
    *,
    root: Path,
) -> str:
    """Render a multi-ticker evidence board without writing files."""

    lines = [
        "Trusted Data Pilot Board",
        "Read-only: this board summarizes selected pilot candidates without refreshing, importing, applying rows, writing CSVs, or changing readiness outputs.",
        "",
    ]
    if not candidates:
        lines.extend(
            [
                "No operating-company pilot candidates matched the current filters.",
                "Next command: make trusted-data-pilot-candidates TOP_N=10",
            ]
        )
        return "\n".join(lines)

    rows = build_trusted_data_pilot_evidence_rows(candidates, root=root)
    state_counts: dict[str, int] = {}
    lane_counts: dict[str, int] = {}
    for row in rows:
        state_counts[row["outcome_state"]] = state_counts.get(row["outcome_state"], 0) + 1
        lane_counts[row["pilot_lane"]] = lane_counts.get(row["pilot_lane"], 0) + 1

    state_summary = ", ".join(f"{state}: {count}" for state, count in sorted(state_counts.items()))
    lane_summary = ", ".join(f"{lane}: {count}" for lane, count in sorted(lane_counts.items()))
    tickers = ",".join(row["ticker"] for row in rows)

    lines.extend(
        [
            f"Tickers reviewed: {tickers}",
            f"Outcome mix: {state_summary}",
            f"Lane mix: {lane_summary}",
            "",
            "Lane-group workflows:",
        ]
    )
    lanes: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        lanes.setdefault(row["pilot_lane"], []).append(row)
    for lane, lane_rows in sorted(lanes.items()):
        lane_tickers = ",".join(row["ticker"] for row in lane_rows)
        blockers = sorted({row["changed_inputs"] for row in lane_rows})
        review_patterns = sorted({row["review_command"] for row in lane_rows})
        trusted_targets = sorted({row["trusted_row_target"] for row in lane_rows})
        rejected_reports = sorted({row["rejected_row_report"] for row in lane_rows})
        proof_patterns = sorted({row["proof_command"] for row in lane_rows})
        lines.extend(
            [
                f"- {lane}:",
                f"  candidate_count: {len(lane_rows)}",
                f"  tickers: {lane_tickers}",
                f"  shared_blocker_theme: {'; '.join(blockers)}",
                f"  shared_review_command_pattern: {'; '.join(review_patterns)}",
                f"  trusted_row_target: {'; '.join(trusted_targets)}",
                f"  rejected_row_report: {'; '.join(rejected_reports)}",
                f"  proof_command_pattern: {'; '.join(proof_patterns)}",
                "  stop_condition: stop if source proof is unavailable, validation fails, rejected rows appear, or rebuilt reports stay locked",
                f"  batch_status: {pilot_lane_batch_status(lane)}",
            ]
        )
    suggested_lane, suggested_lane_rows = max(
        lanes.items(),
        key=lambda item: (len(item[1]), item[0]),
    )
    suggested_lane_tickers = ",".join(row["ticker"] for row in suggested_lane_rows)
    suggested_review_pattern = "; ".join(sorted({row["review_command"] for row in suggested_lane_rows}))
    lines.extend(
        [
            "",
            "Batch board:",
        ]
    )
    for row in rows:
        lines.append(
            "- "
            f"{row['ticker']}: {row['outcome_state']}; {row['pilot_lane']}; "
            f"input={row['changed_inputs']}; review={row['review_command']}; proof={row['proof_command']}"
        )

    lines.extend(
        [
            "",
            "Batch decision rule:",
            "- Apply no rows from this board. Use it to choose the next lane group, then run validate/preview/apply only after source proof is reviewed.",
            "- Treat supported as proven only when rebuilt readiness and regenerated reports support the lane.",
            "- Treat still_blocked as the correct result when source proof is missing, rejected rows appear, or the report remains locked.",
            "",
            "Suggested batch next step:",
            f"- Start with lane group: {suggested_lane}",
            f"- Lane tickers: {suggested_lane_tickers}",
            f"- Review command pattern: {suggested_review_pattern}",
            f"- Evidence ledger command: make trusted-data-pilot-evidence TICKERS={tickers}",
            "- Keep generated CSV/JSON churn out of commits unless the evidence ledger is intentionally reviewed.",
        ]
    )
    return "\n".join(lines)


def pilot_lane_batch_status(lane_label: str) -> str:
    """Classify whether a lane can batch now or needs review."""

    normalized = lane_label.lower()
    if "price" in normalized:
        return "safe_to_batch_dry_run"
    if "optional" in normalized:
        return "locked"
    if "fundamentals" in normalized or "peer" in normalized:
        return "review_only"
    return "review_only"


def pilot_lane_runbook(lane: str) -> PilotLaneRunbook:
    """Return the read-only lane-group operating contract."""

    normalized = normalize_pilot_lane(lane)
    specs = {
        "fundamentals_dcf": PilotLaneRunbook(
            lane="fundamentals_dcf",
            label=pilot_lane_label("fundamentals_dcf"),
            status="review_only",
            what_proves_lane="Rebuilt readiness shows fundamentals_ready and dcf_ready, then the regenerated stock report exposes DCF review instead of a missing-field gate.",
            needed_rows_files="SEC-staged or reviewed manual rows in data/staged/fundamentals/ or data/imports/fundamentals.csv with required DCF fields and source.",
            rejected_row_reports="data/rejected/fundamentals_import_rejected.csv",
            readiness_proof_command="make readiness && make dcf-readiness && make stock-report-md TICKER=<ticker>",
            remains_blocked_when="trusted revenue, free-cash-flow margin or free cash flow, shares outstanding, cash, debt, date, or source rows are missing or rejected.",
            ordered_steps=(
                "Run make trusted-data-pilot-candidates TOP_N=10 and choose the fundamentals/DCF lane group only if source proof exists.",
                "Run make trusted-data-pilot-packet TICKER=<ticker> for the selected operating company.",
                "Run make sec-stage-queue TOP_N=25 or make focus-fundamentals TICKER=<ticker> to inspect missing fields.",
                "Add or stage fundamentals rows only when SEC or trusted manual source proof is reviewable.",
                "Run make imports-validate and make imports-preview; inspect rejected-row reports before any apply.",
                "Run make imports-apply only for reviewed trusted rows.",
                "Run make readiness, make dcf-readiness, and make stock-report-md TICKER=<ticker> to prove the lane changed or remains blocked.",
            ),
            next_safe_command="make trusted-data-pilot-lane LANE=fundamentals_dcf",
        ),
        "peer_mapping": PilotLaneRunbook(
            lane="peer_mapping",
            label=pilot_lane_label("peer_mapping"),
            status="review_only",
            what_proves_lane="Rebuilt readiness and the peer queue show source-backed peer context; sector or industry fallback alone does not prove peer valuation.",
            needed_rows_files="source-backed peer mappings in data/imports/peers.csv, plus peer price/fundamental inputs only when the queue asks for them.",
            rejected_row_reports="data/rejected/peers_import_rejected.csv",
            readiness_proof_command="make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER=<ticker>",
            remains_blocked_when="peer relationships cannot be supported by source notes or mapped peers still lack the required valuation inputs.",
            ordered_steps=(
                "Run make trusted-data-pilot-candidates TOP_N=10 and choose the peer mapping lane group only when peer relationship proof exists.",
                "Run make trusted-data-pilot-packet TICKER=<ticker> for one selected operating company.",
                "Run make peer-mapping-queue TOP_N=25 and make focus-peers TICKER=<ticker>.",
                "Add peer rows only with source-backed relationships; do not treat sector or industry fallback as trusted peer data.",
                "Run make imports-validate and make imports-preview; inspect data/rejected/peers_import_rejected.csv.",
                "Run make imports-apply only for reviewed trusted peer rows.",
                "Run make readiness, make peer-mapping-queue TOP_N=25, and make stock-report-md TICKER=<ticker> to prove the lane changed or remains blocked.",
            ),
            next_safe_command="make trusted-data-pilot-lane LANE=peer_mapping",
        ),
        "peer_valuation_inputs": PilotLaneRunbook(
            lane="peer_valuation_inputs",
            label=pilot_lane_label("peer_valuation_inputs"),
            status="review_only",
            what_proves_lane="Mapped peers have verified valuation inputs, such as trusted fundamentals or verified peer price/market-cap context, and the rebuilt report no longer withholds peer valuation.",
            needed_rows_files="reviewed mapped-peer fundamentals in data/imports/fundamentals.csv or verified peer price history; data/imports/peers.csv only if mappings change.",
            rejected_row_reports="data/rejected/fundamentals_import_rejected.csv and data/rejected/price_import_rejected.csv when peer price rows change",
            readiness_proof_command="make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER=<ticker>",
            remains_blocked_when="mapped peers lack trusted fundamentals, price history, market-cap context, or the rebuilt peer readiness report still withholds valuation comparison.",
            ordered_steps=(
                "Run make trusted-data-pilot-board TICKERS=MU,CRDO,HOOD,TSLA,META,A,APLD and choose the peer valuation inputs lane group, not a single name first.",
                "Run make focus-peers TICKER=<ticker> to see the mapped-peer dependency printed by the queue.",
                "Follow the peer dependency with make focus-fundamentals TICKER=<peer> or the printed peer price proof command.",
                "Add mapped-peer inputs only when source proof is reviewable.",
                "Run make imports-validate and make imports-preview; inspect fundamentals and price rejected-row reports if those rows changed.",
                "Run make imports-apply only for reviewed trusted rows.",
                "Run make readiness, make peer-mapping-queue TOP_N=25, and make stock-report-md TICKER=<ticker> to prove peer valuation changed or remains blocked.",
            ),
            next_safe_command="make trusted-data-pilot-lane LANE=peer_valuation_inputs",
        ),
        "optional_context_locked": PilotLaneRunbook(
            lane="optional_context_locked",
            label=pilot_lane_label("optional_context_locked"),
            status="locked",
            what_proves_lane="Only trusted local earnings or analyst-estimate rows can unlock optional context; this lane is optional and must not block core readiness.",
            needed_rows_files="trusted rows in data/staged/earnings/, data/staged/analyst_estimates/, data/imports/earnings.csv, or data/imports/analyst_estimates.csv.",
            rejected_row_reports="data/rejected/earnings_import_rejected.csv and data/rejected/analyst_estimates_import_rejected.csv",
            readiness_proof_command="make optional-context-readiness && make onboarding TOP_N=10 && make stock-report-md TICKER=<ticker>",
            remains_blocked_when="trusted earnings or analyst-estimate rows do not exist locally, validation rejects them, or optional readiness remains unavailable.",
            ordered_steps=(
                "Leave the lane locked unless trusted local earnings or analyst-estimate rows already exist.",
                "Run make optional-context-worklist TOP_N=10 to inspect optional/manual blockers.",
                "Add rows only from trusted local sources; do not infer future estimates or earnings values.",
                "Run make imports-validate and make imports-preview; inspect optional rejected-row reports.",
                "Run make imports-apply only for reviewed trusted optional rows.",
                "Run make optional-context-readiness and make stock-report-md TICKER=<ticker> to prove optional context changed or remains locked.",
            ),
            next_safe_command="make trusted-data-pilot-lane LANE=optional_context_locked",
            locked_manual_note="Manual/optional lane: keep earnings and analyst estimates locked unless trusted local rows exist.",
        ),
        "price_coverage": PilotLaneRunbook(
            lane="price_coverage",
            label=pilot_lane_label("price_coverage"),
            status="safe_to_batch_dry_run",
            what_proves_lane="Dry-run planning proves which price rows would be attempted; only reviewed applied price imports and rebuilt readiness prove coverage changed.",
            needed_rows_files="verified OHLCV rows staged through provider refresh or normalized into data/imports/prices.csv after review.",
            rejected_row_reports="data/rejected/price_import_rejected.csv",
            readiness_proof_command="make price-coverage && make readiness && make status-check TOP_N=5",
            remains_blocked_when="the dry run finds no safe provider path, downloaded rows cannot be verified, rejected rows appear, or readiness still shows missing price coverage.",
            ordered_steps=(
                "Run make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo.",
                "Review the dry-run plan before running any real refresh.",
                "If a real capped refresh is chosen later, inspect generated CSV diffs before keeping artifacts.",
                "For downloaded files, normalize verified OHLCV rows, then run make price-validate and make price-preview.",
                "Run make price-apply only for reviewed trusted price rows.",
                "Run make price-coverage, make readiness, and make status-check TOP_N=5 to prove coverage changed or remains blocked.",
            ),
            next_safe_command="make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo",
        ),
    }
    return specs[normalized]


def pilot_lane_summary_rows(candidates: list[PilotCandidate]) -> list[dict[str, str]]:
    """Return lane-group summary rows for CLI and dashboard views."""

    rows: list[dict[str, str]] = []
    for lane in (
        "fundamentals_dcf",
        "peer_mapping",
        "peer_valuation_inputs",
        "optional_context_locked",
        "price_coverage",
    ):
        runbook = pilot_lane_runbook(lane)
        lane_candidates = [candidate for candidate in candidates if candidate.lane == lane]
        blocker_themes = sorted({pilot_primary_missing_input(candidate) for candidate in lane_candidates})
        tickers = ",".join(candidate.ticker for candidate in lane_candidates) or "-"
        if lane == "price_coverage":
            blocker_theme = "missing or stale price coverage; dry-run-first batch planning"
        elif lane == "optional_context_locked" and not blocker_themes:
            blocker_theme = "earnings and analyst estimates remain locked unless trusted local rows exist"
        else:
            blocker_theme = "; ".join(blocker_themes) if blocker_themes else "no current candidate in selected scope"
        rows.append(
            {
                "lane": lane,
                "lane_label": runbook.label,
                "candidate_count": str(len(lane_candidates)),
                "tickers": tickers,
                "blocker_theme": blocker_theme,
                "status": runbook.status,
                "next_safe_command": runbook.next_safe_command,
                "what_proves_lane": runbook.what_proves_lane,
                "needed_rows_files": runbook.needed_rows_files,
                "rejected_row_reports": runbook.rejected_row_reports,
                "readiness_proof_command": runbook.readiness_proof_command,
                "remains_blocked_when": runbook.remains_blocked_when,
                "locked_manual_note": runbook.locked_manual_note,
            }
        )
    return rows


def render_trusted_data_pilot_lane(
    lane: str,
    candidates: list[PilotCandidate],
    *,
    root: Path | None = None,
) -> str:
    """Render one lane-group runbook without writing data."""

    runbook = pilot_lane_runbook(lane)
    normalized = runbook.lane
    rows = pilot_lane_summary_rows(candidates)
    summary = next(row for row in rows if row["lane"] == normalized)
    lane_candidates = [candidate for candidate in candidates if candidate.lane == normalized]
    lines = [
        "Trusted Data Pilot Lane Runbook",
        "Read-only: this command prints lane-specific steps and evidence requirements without refreshing, importing, applying rows, writing CSVs, or changing readiness outputs.",
        "",
        f"Lane: {runbook.label}",
        f"Lane key: {runbook.lane}",
        f"Batch status: {runbook.status}",
        f"Candidate count in selected scope: {summary['candidate_count']}",
        f"Candidate tickers: {summary['tickers']}",
        f"Current blocker theme: {summary['blocker_theme']}",
        f"Next safe command: {runbook.next_safe_command}",
        *([f"Locked/manual note: {runbook.locked_manual_note}"] if runbook.locked_manual_note else []),
        "",
        "Ordered lane steps:",
        *[f"{index}. {step}" for index, step in enumerate(runbook.ordered_steps, start=1)],
        "",
        "Lane evidence summary:",
        f"- What proves the lane: {runbook.what_proves_lane}",
        f"- Rows/files needed: {runbook.needed_rows_files}",
        f"- Rejected-row reports that matter: {runbook.rejected_row_reports}",
        f"- Command that confirms readiness changed: {runbook.readiness_proof_command}",
        f"- What remains blocked: {runbook.remains_blocked_when}",
        "",
        "Outcome contract:",
        "- supported: rebuilt readiness and regenerated reports prove the lane changed.",
        "- still_blocked: source proof is missing, validation fails, rejected rows appear, or rebuilt reports stay locked.",
        "- skipped: the lane is intentionally not advanced because source proof is unavailable.",
        "- excluded: the row is not an operating-company pilot target.",
    ]
    if lane_candidates:
        lines.extend(
            [
                "",
                "Current lane candidates:",
                *[
                    (
                        f"- {candidate.ticker}: missing {pilot_primary_missing_input(candidate)}; "
                        f"review {candidate.next_command}; proof {candidate.proof_after_unlock}"
                    )
                    for candidate in lane_candidates
                ],
            ]
        )
    if root is not None and lane_candidates:
        lines.extend(
            [
                "",
                "Read-only local file status:",
                *[f"- {candidate.ticker}: {pilot_local_file_status(candidate, root=root)}" for candidate in lane_candidates[:3]],
            ]
        )
    lines.extend(
        [
            "",
            "Guardrail: do not fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, recommendations, or unlocks.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank read-only trusted-data pilot candidates.")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--tickers", default="")
    parser.add_argument("--packet", default="", help="Print a one-company evidence packet for the requested ticker.")
    parser.add_argument("--verbose", action="store_true", help="Print full per-candidate evidence details.")
    parser.add_argument("--board", action="store_true", help="Print a read-only multi-ticker pilot evidence board.")
    parser.add_argument("--lane", default="", help="Print a lane-group runbook for fundamentals, peers, optional context, or price coverage.")
    parser.add_argument(
        "--write-evidence",
        default="",
        help="Write a read-only pilot evidence ledger CSV for selected candidates.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.packet:
        ticker = args.packet.strip().upper()
        candidates = load_trusted_data_pilot_candidates(root=Path.cwd(), tickers=ticker, top_n=1)
        print(render_trusted_data_pilot_packet(candidates[0] if candidates else None, requested_ticker=ticker, root=Path.cwd()))
        return
    if args.lane:
        try:
            normalize_pilot_lane(args.lane)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        candidates = load_trusted_data_pilot_evidence_candidates(root=Path.cwd(), tickers=args.tickers, top_n=args.top_n)
        print(render_trusted_data_pilot_lane(args.lane, candidates, root=Path.cwd()))
        return
    if args.write_evidence:
        candidates = load_trusted_data_pilot_evidence_candidates(root=Path.cwd(), tickers=args.tickers, top_n=args.top_n)
        output_path = Path(args.write_evidence)
        written = write_trusted_data_pilot_evidence(candidates, root=Path.cwd(), output_path=output_path)
        print("Trusted Data Pilot Evidence Ledger")
        print("Read-only: wrote pilot evidence rows from current reports and readiness snapshots; no source rows or readiness outputs were changed.")
        print(f"Rows: {len(candidates)}")
        print(f"Wrote: {written}")
        return
    if args.board:
        candidates = load_trusted_data_pilot_evidence_candidates(root=Path.cwd(), tickers=args.tickers, top_n=args.top_n)
        print(render_trusted_data_pilot_board(candidates, root=Path.cwd()))
        return
    candidates = load_trusted_data_pilot_candidates(root=Path.cwd(), tickers=args.tickers, top_n=args.top_n)
    print(render_trusted_data_pilot_candidates(candidates, top_n=args.top_n, root=Path.cwd(), verbose=args.verbose))


if __name__ == "__main__":
    main()
