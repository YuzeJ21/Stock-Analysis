"""Read-only proof queue for short local price-history blockers.

This queue separates broad price coverage from history-depth readiness. A
ticker can have local prices and still be blocked for momentum, track-record,
or review-metric workflows when the verified local history is too short.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.data_onboarding import build_onboarding_payload
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root


PROOF_QUEUE_COLUMNS = [
    "priority",
    "ticker",
    "state",
    "current_history_rows",
    "next_goal",
    "target_history_rows",
    "rows_needed",
    "first_local_date",
    "latest_local_date",
    "next_safe_command",
    "dry_run_batch_command",
    "validate_preview_apply_gate",
    "post_run_proof_command",
    "stop_rule",
    "source_note",
]


@dataclass(frozen=True)
class PriceHistoryProofRow:
    priority: int
    ticker: str
    state: str
    current_history_rows: int
    next_goal: str
    target_history_rows: int
    rows_needed: int
    first_local_date: str
    latest_local_date: str
    next_safe_command: str
    dry_run_batch_command: str
    validate_preview_apply_gate: str
    post_run_proof_command: str
    stop_rule: str
    source_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes"}


def _state(row: dict[str, Any]) -> str:
    if not _truthy(row.get("has_prices")) or int(row.get("current_history_rows") or 0) <= 0:
        return "blocked"
    if int(row.get("rows_needed") or 0) > 0:
        return "partial"
    return "ready"


def _clean_goal(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "Maintain Coverage"
    return text


def _parse_tickers(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip().upper() for part in value.split(",") if part.strip()]


def _reviewed_non_actionable_price_tickers(root: Path, possible_tickers: set[str]) -> set[str]:
    path = root / "data" / "reviewed_batch_proofs.csv"
    if not path.exists() or not possible_tickers:
        return set()

    reviewed: set[str] = set()
    price_lanes = {"prices", "price_coverage", "price_history"}
    non_actionable_outcomes = {"still_blocked", "skipped", "excluded"}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            lane = str(row.get("lane") or "").strip().lower()
            outcome = str(row.get("final_outcome") or "").strip().lower()
            if lane not in price_lanes or outcome not in non_actionable_outcomes:
                continue

            fields = " ".join(
                str(row.get(name) or "")
                for name in ("tickers", "changed_tickers", "notes")
            ).upper()
            for token in re.findall(r"\b[A-Z][A-Z0-9.]{0,9}\b", fields):
                normalized = token.replace(".", "-")
                if normalized in possible_tickers:
                    reviewed.add(normalized)
    return reviewed


def build_price_history_proof_queue_from_payload(
    payload: dict[str, Any],
    *,
    top_n: int = 10,
    tickers: list[str] | None = None,
    reviewed_non_actionable_tickers: set[str] | None = None,
) -> list[PriceHistoryProofRow]:
    """Build proof rows from the existing onboarding price worklist."""
    wanted = {ticker.upper().strip() for ticker in tickers or [] if ticker.strip()}
    reviewed_non_actionable_tickers = reviewed_non_actionable_tickers or set()
    rows: list[PriceHistoryProofRow] = []
    dry_run_command = f"make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N={max(top_n, 1)} PROVIDER=auto"
    for raw in payload.get("price_import_worklist", []):
        ticker = str(raw.get("ticker") or "").strip().upper()
        if not ticker or (wanted and ticker not in wanted):
            continue
        rows_needed = int(raw.get("rows_needed_for_next_goal") or 0)
        if rows_needed <= 0:
            continue
        current_rows = int(raw.get("price_history_days") or 0)
        row_data = {
            "has_prices": raw.get("has_prices"),
            "current_history_rows": current_rows,
            "rows_needed": rows_needed,
        }
        state = _state(row_data)
        source_note = (
            "Uses local price worklist thresholds. Price coverage can be complete while momentum, track-record, "
            "or review-metric history depth remains partial."
        )
        next_safe_command = str(raw.get("focus_command") or f"make focus-price TICKER={ticker}").strip()
        if ticker in reviewed_non_actionable_tickers:
            source_note = (
                "Reviewed proof ledger already records this short-history source path as non-actionable; "
                "do not repeat it unless new provider data, a verified manual OHLCV file, or changed source behavior appears. "
                + source_note
            )
            next_safe_command = "wait for new verified OHLCV source or changed provider behavior"
        rows.append(
            PriceHistoryProofRow(
                priority=len(rows) + 1,
                ticker=ticker,
                state=state,
                current_history_rows=current_rows,
                next_goal=_clean_goal(raw.get("next_price_goal")),
                target_history_rows=int(raw.get("next_target_history_rows") or 0),
                rows_needed=rows_needed,
                first_local_date=str(raw.get("first_local_date") or "").strip(),
                latest_local_date=str(raw.get("latest_local_date") or "").strip(),
                next_safe_command=next_safe_command,
                dry_run_batch_command=dry_run_command,
                validate_preview_apply_gate="make price-validate -> make price-preview -> make price-apply only after reviewed source rows",
                post_run_proof_command=f"make readiness && make status-check TOP_N={max(top_n, 1)} && make focus-price TICKER={ticker}",
                stop_rule=(
                    "Stop if the provider/manual source cannot verify enough OHLCV history; keep the short-history "
                    "state visible and do not infer missing dates or prices."
                ),
                source_note=source_note,
            )
        )
    rows.sort(key=lambda row: ("reviewed proof ledger already records" in row.source_note.lower(), row.priority))
    rows = [
        PriceHistoryProofRow(
            priority=index,
            ticker=row.ticker,
            state=row.state,
            current_history_rows=row.current_history_rows,
            next_goal=row.next_goal,
            target_history_rows=row.target_history_rows,
            rows_needed=row.rows_needed,
            first_local_date=row.first_local_date,
            latest_local_date=row.latest_local_date,
            next_safe_command=row.next_safe_command,
            dry_run_batch_command=row.dry_run_batch_command,
            validate_preview_apply_gate=row.validate_preview_apply_gate,
            post_run_proof_command=row.post_run_proof_command,
            stop_rule=row.stop_rule,
            source_note=row.source_note,
        )
        for index, row in enumerate(rows, start=1)
    ]
    return rows[: max(top_n, 0)]


def build_price_history_proof_queue_from_files(
    root: Path,
    *,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> list[PriceHistoryProofRow]:
    payload = build_onboarding_payload(root, data_dir=data_dir, output_dir=output_dir, tickers=tickers)
    possible_tickers = {
        str(row.get("ticker") or "").strip().upper()
        for row in payload.get("price_import_worklist", [])
        if str(row.get("ticker") or "").strip()
    }
    reviewed_tickers = _reviewed_non_actionable_price_tickers(root, possible_tickers)
    return build_price_history_proof_queue_from_payload(
        payload,
        top_n=top_n,
        tickers=tickers,
        reviewed_non_actionable_tickers=reviewed_tickers,
    )


def _coverage_note(payload: dict[str, Any]) -> str:
    coverage = payload.get("ticker_coverage", [])
    total = len(coverage)
    price_ready = sum(1 for row in coverage if _truthy(row.get("has_prices")))
    momentum_ready = sum(1 for row in coverage if _truthy(row.get("usable_for_momentum")))
    return (
        f"Coverage context: {price_ready}/{total} tickers have local prices; "
        f"{momentum_ready}/{total} are momentum-ready from local history."
    )


def _price_rows_complete(payload: dict[str, Any]) -> bool:
    coverage = payload.get("ticker_coverage", [])
    if not coverage:
        return False
    return all(_truthy(row.get("has_prices")) for row in coverage)


def render_price_history_proof_queue(rows: list[PriceHistoryProofRow], payload: dict[str, Any]) -> str:
    lines = [
        "Short Price-History Proof Queue",
        "Read-only: this queue does not refresh prices, apply imports, or write canonical data.",
        "Research-only: short-history proof is a data-readiness gate, not a ranking or execution workflow.",
        "Data rule: do not fabricate missing dates, prices, volume, or adjusted close rows.",
        "Readiness note: price coverage can be complete while momentum, track-record, or review metrics remain partial.",
        _coverage_note(payload),
    ]
    if not rows:
        lines.append("No short price-history blockers found for the selected scope.")
        return "\n".join(lines)

    blocked = sum(1 for row in rows if row.state == "blocked")
    partial = sum(1 for row in rows if row.state == "partial")
    lines.append(f"Rows shown: {len(rows)}; blocked: {blocked}; partial: {partial}.")
    all_reviewed_non_actionable = all("reviewed proof ledger already records" in row.source_note.lower() for row in rows)
    focused_single_ticker = len(rows) == 1
    price_rows_complete = _price_rows_complete(payload)
    targeted_history_command = f"make price-refresh TICKERS={rows[0].ticker} PROVIDER=auto"
    if all_reviewed_non_actionable:
        lines.append(
            "Next safest action: No unreviewed executable price-history blockers are shown; "
            "do not repeat these source paths unless new provider data, a verified manual OHLCV file, or changed source behavior appears."
        )
    elif focused_single_ticker and price_rows_complete:
        lines.append(f"Next safest action: {targeted_history_command}.")
    elif focused_single_ticker:
        lines.append(f"Next safest action: {rows[0].dry_run_batch_command}.")
    else:
        lines.append(f"Next safest action: {rows[0].next_safe_command}.")
    if price_rows_complete:
        lines.append(
            "History source path: price rows are already present for every ticker; use focused review or "
            "verified manual OHLCV history for short-history names, not missing-price refresh."
        )
    else:
        lines.append(f"Dry-run batch plan: {rows[0].dry_run_batch_command}.")
    lines.append("")
    lines.append("Priority | Ticker | State | Local rows | Next goal | Rows needed | Next proof command")
    lines.append("---: | --- | --- | ---: | --- | ---: | ---")
    for row in rows:
        next_command = row.next_safe_command
        if focused_single_ticker and price_rows_complete and next_command.startswith("make focus-price"):
            next_command = targeted_history_command
        elif focused_single_ticker and next_command.startswith("make focus-price"):
            next_command = row.dry_run_batch_command
        lines.append(
            " | ".join(
                [
                    str(row.priority),
                    row.ticker,
                    row.state,
                    str(row.current_history_rows),
                    row.next_goal,
                    str(row.rows_needed),
                    next_command,
                ]
            )
        )
    if len(rows) == 1:
        row = rows[0]
        lines.append("")
        lines.append("Focused proof detail:")
        lines.append(f"- Source note: {row.source_note}")
        if "reviewed proof ledger already records" in row.source_note.lower():
            lines.append(f"- Follow-up: {row.next_safe_command}.")
        elif price_rows_complete:
            lines.append(f"- Targeted provider history check: {targeted_history_command} after make readiness-snapshot.")
            lines.append("- This is not the missing-price batch loop; inspect the source result before relying on added history.")
            lines.append(f"- Import gate: {row.validate_preview_apply_gate}.")
            lines.append(f"- Rebuild proof: {row.post_run_proof_command}.")
        else:
            lines.append(f"- Dry-run before refresh: {row.dry_run_batch_command}.")
            lines.append(f"- Import gate: {row.validate_preview_apply_gate}.")
            lines.append(f"- Rebuild proof: {row.post_run_proof_command}.")
        lines.append(f"- Stop rule: {row.stop_rule}")
    lines.append("")
    lines.append("Review checklist:")
    lines.append("- Inspect the ticker first with the focus command before planning a capped batch.")
    lines.append("- Use the dry-run batch command before any provider refresh.")
    lines.append("- For manual files, normalize verified OHLCV rows, then run validate and preview before apply.")
    lines.append("- Rebuild readiness and keep generated CSV/report churn excluded unless deliberately reviewed.")
    lines.append("- Keep the lane blocked or partial if source proof cannot verify enough history.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a read-only short price-history proof queue.")
    parser.add_argument("--project-root")
    parser.add_argument("--data-dir")
    parser.add_argument("--outputs-dir")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--tickers")
    args = parser.parse_args()

    root = resolve_project_root(Path(args.project_root) if args.project_root else None)
    data_path = resolve_data_dir(Path(args.data_dir) if args.data_dir else None, root)
    output_path = resolve_outputs_dir(Path(args.outputs_dir) if args.outputs_dir else None, root)
    tickers = _parse_tickers(args.tickers)
    payload = build_onboarding_payload(root, data_dir=data_path, output_dir=output_path, tickers=tickers)
    possible_tickers = {
        str(row.get("ticker") or "").strip().upper()
        for row in payload.get("price_import_worklist", [])
        if str(row.get("ticker") or "").strip()
    }
    reviewed_tickers = _reviewed_non_actionable_price_tickers(root, possible_tickers)
    rows = build_price_history_proof_queue_from_payload(
        payload,
        top_n=args.top_n,
        tickers=tickers,
        reviewed_non_actionable_tickers=reviewed_tickers,
    )
    print(format_path_context(root, data_path, output_path))
    print(render_price_history_proof_queue(rows, payload))


if __name__ == "__main__":
    main()
