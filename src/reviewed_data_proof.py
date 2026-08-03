"""Reviewed data proof ledger and lane history helpers.

This module keeps reviewed data proof separate from generated readiness churn.
The default ledger is a small source-controlled CSV that records lane-level
operator evidence and final outcomes.
"""

from __future__ import annotations

from src.reviewed_batch_proof import resolve_readiness_proof_profile

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_LEDGER_PATH = Path("data/reviewed_data_proofs.csv")
DEFAULT_PUBLIC_DEMO_PACK_PATH = Path("docs/PUBLIC_DEMO_READINESS_PACK.md")
PROOF_OUTCOMES = {"supported", "candidate_context_only", "still_blocked", "skipped", "excluded"}

PROOF_LEDGER_COLUMNS = (
    "proof_id",
    "proof_date",
    "lane",
    "lane_label",
    "scope",
    "tickers_or_dependencies",
    "source_proof_status",
    "reviewer_outcome",
    "validate_result",
    "preview_result",
    "apply_result",
    "rejected_row_status",
    "readiness_before",
    "readiness_after",
    "final_outcome",
    "changed_inputs",
    "what_changed",
    "still_blocked",
    "review_command",
    "proof_command",
    "artifact_paths",
    "generated_churn_policy",
)


def _env_status(*names: str) -> str:
    return "present" if any(os.environ.get(name, "").strip() for name in names) else "missing"


@dataclass(frozen=True)
class ReviewedProof:
    proof_id: str
    proof_date: str
    lane: str
    lane_label: str
    scope: str
    tickers_or_dependencies: str
    source_proof_status: str
    reviewer_outcome: str
    validate_result: str
    preview_result: str
    apply_result: str
    rejected_row_status: str
    readiness_before: str
    readiness_after: str
    final_outcome: str
    changed_inputs: str
    what_changed: str
    still_blocked: str
    review_command: str
    proof_command: str
    artifact_paths: str
    generated_churn_policy: str


def _clean(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def reviewed_proof_from_row(row: dict[str, str]) -> ReviewedProof:
    values = {column: _clean(row.get(column)) for column in PROOF_LEDGER_COLUMNS}
    return ReviewedProof(**values)


def load_reviewed_proofs(path: Path = DEFAULT_LEDGER_PATH) -> list[ReviewedProof]:
    return [reviewed_proof_from_row(row) for row in _read_csv(path)]


def write_reviewed_proofs(rows: Iterable[ReviewedProof], path: Path = DEFAULT_LEDGER_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROOF_LEDGER_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in PROOF_LEDGER_COLUMNS})
    return path


def append_reviewed_proof(row: ReviewedProof, path: Path = DEFAULT_LEDGER_PATH) -> Path:
    existing = load_reviewed_proofs(path)
    existing.append(row)
    return write_reviewed_proofs(existing, path)


def latest_reviewed_proof(rows: list[ReviewedProof]) -> ReviewedProof | None:
    if not rows:
        return None
    return sorted(rows, key=lambda row: (row.proof_date, row.proof_id))[-1]


def lane_history_rows(rows: list[ReviewedProof]) -> list[dict[str, str]]:
    lanes: dict[str, list[ReviewedProof]] = {}
    for row in rows:
        lanes.setdefault(row.lane, []).append(row)
    history = []
    for lane, lane_rows in sorted(lanes.items()):
        ordered = sorted(lane_rows, key=lambda row: (row.proof_date, row.proof_id))
        latest = ordered[-1]
        outcomes: dict[str, int] = {}
        for row in ordered:
            outcomes[row.final_outcome] = outcomes.get(row.final_outcome, 0) + 1
        history.append(
            {
                "lane": lane,
                "lane_label": latest.lane_label,
                "proof_count": str(len(ordered)),
                "latest_proof_date": latest.proof_date,
                "latest_outcome": latest.final_outcome,
                "latest_changed_inputs": latest.changed_inputs,
                "latest_still_blocked": latest.still_blocked,
                "outcome_mix": ", ".join(f"{key}: {value}" for key, value in sorted(outcomes.items())),
                "latest_proof_command": latest.proof_command,
            }
        )
    return history


def render_reviewed_data_proofs(rows: list[ReviewedProof]) -> str:
    lines = [
        "Reviewed Data Proof Ledger",
        "Durable: this ledger records lane-level reviewed data changes; it is not a broad generated readiness report.",
        "Research-only: proof rows do not provide investment advice, broker actions, or direct buy/sell instructions.",
        "",
    ]
    if not rows:
        lines.extend(
            [
                "No reviewed proof rows are recorded yet.",
                "Use reviewed-data-proof-record only after source proof, validation, preview, rejected-row review, apply, and readiness proof are reviewed.",
            ]
        )
        return "\n".join(lines)
    for row in sorted(rows, key=lambda item: (item.proof_date, item.proof_id), reverse=True):
        lines.extend(
            [
                f"- {row.proof_id} | {row.proof_date} | {row.lane_label} | {row.final_outcome}",
                f"  scope: {row.scope}; tickers/dependencies: {row.tickers_or_dependencies}",
                f"  source_proof_status: {row.source_proof_status}; reviewer_outcome: {row.reviewer_outcome}",
                f"  validate/preview/apply: {row.validate_result} / {row.preview_result} / {row.apply_result}",
                f"  rejected_row_status: {row.rejected_row_status}",
                f"  readiness before -> after: {row.readiness_before} -> {row.readiness_after}",
                f"  changed_inputs: {row.changed_inputs}",
                f"  what_changed: {row.what_changed}",
                f"  still_blocked: {row.still_blocked}",
                f"  proof_command: {row.proof_command}",
                f"  artifacts: {row.artifact_paths}",
                f"  generated_churn_policy: {row.generated_churn_policy}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_lane_outcome_history(rows: list[ReviewedProof]) -> str:
    lines = [
        "Lane Outcome History",
        "Read-only: summarizes the durable reviewed proof ledger without reading generated readiness CSV churn.",
        "",
    ]
    history = lane_history_rows(rows)
    if not history:
        lines.append("No lane history is recorded yet.")
        return "\n".join(lines)
    for row in history:
        lines.extend(
            [
                f"- {row['lane_label']}:",
                f"  proof_count: {row['proof_count']}",
                f"  latest_proof_date: {row['latest_proof_date']}",
                f"  latest_outcome: {row['latest_outcome']}",
                f"  latest_changed_inputs: {row['latest_changed_inputs']}",
                f"  latest_still_blocked: {row['latest_still_blocked']}",
                f"  outcome_mix: {row['outcome_mix']}",
                f"  latest_proof_command: {row['latest_proof_command']}",
            ]
        )
    return "\n".join(lines)


def render_latest_proof_timeline(rows: list[ReviewedProof]) -> str:
    latest = latest_reviewed_proof(rows)
    lines = [
        "Data Health Proof Timeline",
        "Read-only: latest reviewed lane proof from the durable ledger.",
        "",
    ]
    if latest is None:
        lines.append("No reviewed proof has been recorded yet.")
        return "\n".join(lines)
    lines.extend(
        [
            f"Latest proof: {latest.proof_id} ({latest.proof_date})",
            f"Lane: {latest.lane_label}",
            f"Final outcome: {latest.final_outcome}",
            f"What changed: {latest.what_changed}",
            f"Still blocked: {latest.still_blocked}",
            f"Readiness before -> after: {latest.readiness_before} -> {latest.readiness_after}",
            f"Command that proves it: {latest.proof_command}",
            f"Artifacts: {latest.artifact_paths}",
        ]
    )
    return "\n".join(lines)


def render_price_reviewed_run_plan(
    *,
    max_candidates: int = 3500,
    top_n: int = 100,
    provider: str = "auto",
    sleep_seconds: int = 30,
) -> str:
    loop_command = (
        f"make price-refresh-loop MAX_CANDIDATES={max_candidates} TOP_N={top_n} "
        f"PROVIDER={provider} SLEEP_SECONDS={sleep_seconds}"
    )
    dry_run = (
        f"make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES={max_candidates} TOP_N={top_n} "
        f"PROVIDER={provider}"
    )
    stooq_status = _env_status("STOOQ_API_KEY", "STOQ_API_KEY")
    fmp_status = _env_status("FMP_API_KEY")
    alpha_status = _env_status("ALPHA_VANTAGE_API_KEY")
    finnhub_status = _env_status("FINNHUB_API_KEY")
    return "\n".join(
        [
            "Reviewed Price Coverage Run",
            "Copy-only: this command prints a controlled execution plan; it does not refresh prices by itself.",
            (
                "Provider credential visibility: "
                f"STOOQ_API_KEY {stooq_status}; FMP_API_KEY {fmp_status}; "
                f"ALPHA_VANTAGE_API_KEY {alpha_status}; FINNHUB_API_KEY {finnhub_status}."
            ),
            "",
            "Before the run:",
            "1. make status-check TOP_N=5",
            f"2. make readiness-snapshot PROFILE={resolve_readiness_proof_profile()}",
            f"3. {dry_run}",
            "4. Review provider boundary notes and expected generated CSV churn.",
            "",
            "Reviewed capped run:",
            f"5. {loop_command}",
            "",
            "After the run:",
            "6. make price-coverage TOP_N=25",
            f"7. make reviewed-batch-compare PROFILE={resolve_readiness_proof_profile()} LANE=prices BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            "8. make status-check TOP_N=5",
            "9. make diff-hygiene",
            "10. Record a reviewed proof row with final outcome supported/candidate_context_only/still_blocked/skipped/excluded.",
            "If no reviewed price rows are fetched or merged, record FINAL_OUTCOME=still_blocked with provider output as evidence and pivot to the next executable lane.",
            "",
            "Rollback notes:",
            "- If provider output is incomplete or suspicious, do not stage generated CSV churn.",
            "- Use the readiness snapshot and git diff to identify changed price and report files.",
            "- Restore unreviewed generated files before committing; keep only intentionally reviewed evidence.",
            "",
            "Guardrail: price rows can improve coverage only. They do not create fundamentals, peers, earnings, estimates, valuation inputs, or recommendations.",
        ]
    )


def render_public_demo_readiness_pack(rows: list[ReviewedProof]) -> str:
    return "\n".join(
        [
            "# Public Demo Readiness Pack",
            "",
            "This pack is research-only. It shows readiness states, blocked inputs, and proof commands; it is not investment advice and it does not connect to brokers or route orders.",
            "",
            "Start with the product flow before opening operator proof commands:",
            "",
            "```text",
            "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History",
            "```",
            "",
            "Use the table below as evidence after the visitor can already explain what is ready, what is blocked, what is excluded, and what proof changed a lane. Status, provider setup, and proof-ledger commands are operator evidence; they do not refresh data, unlock blocked inputs, or replace the public workflow.",
            "",
            "## Shareable Proof Set",
            "",
            "| Slot | Artifact / command | What it proves |",
            "| --- | --- | --- |",
            "| Visitor workflow | `make dashboard` then follow Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History | First-screen product path and readiness-first route sequence. |",
            "| Status gate | `make project-status-check` | Current safest proof path, provider setup boundary, and whether company candidates are executable. |",
            "| Provider setup | `make provider-setup-checklist` | Source setup steps when source-proof queues are exhausted; no imports or generated data are applied. |",
            "| Scope selection | `make universe-scope TOP_N=10` | Choose active-universe, ticker-list, sector/theme, ready-only, or missing-data scope before deeper review. |",
            "| Risk context | `make risk-context` | Read-only liquidity, correlation, and proxy-risk context after scope is chosen. |",
            "| Data Health lane board | `make readiness-ops-center`, `make coverage-frontier TOP_N=10`, or dashboard `Data Health` | Lane counts, blocker themes, next safe commands, and locked/manual lanes. |",
            "| Ready report | `make stock-report-md TICKER=NVDA` | Ready company report with local DCF review and source-readiness boundaries. |",
            "| Blocked report | `make stock-report-md TICKER=META` | Blocked/missing-input report that keeps valuation gated. |",
            "| Excluded / monitor example | `make stock-report-md TICKER=QQQ` | ETF/index monitor context where operating-company DCF is excluded, not failed. |",
            "",
            "## Current proof timeline",
            "",
            "Latest reviewed proof: run `make reviewed-data-proof` for the current ledger row.",
            "",
            "Use `make reviewed-data-proof` to show the latest durable lane-level proof rows.",
            "Use `make reviewed-batch-proof` to show the latest reviewed batch outcomes.",
            "Use `make lane-outcome-history` when you need the lane-level outcome history.",
            "",
            "This proof review does not refresh data, apply imports, stage files, or unlock blocked inputs. It keeps proof history separate from broad generated CSV churn and from browser screenshots, which remain product evidence only.",
            "",
            "## Source-boundary pivot",
            "",
            "If `make project-status-check` says current source-proof queues are exhausted, use `make provider-setup-checklist` before reopening broad proof loops. Configure at most one keyed free-tier provider, run that provider's reviewed one-ticker smoke command, then use validate, preview, rejected-row review, and source-provenance checks before any apply step.",
        ]
    )


def build_proof_from_args(args: argparse.Namespace) -> ReviewedProof:
    final_outcome = _clean(args.final_outcome).lower()
    if final_outcome not in PROOF_OUTCOMES:
        raise SystemExit("FINAL_OUTCOME must be one of supported, candidate_context_only, still_blocked, skipped, or excluded.")
    return ReviewedProof(
        proof_id=_clean(args.proof_id),
        proof_date=_clean(args.proof_date),
        lane=_clean(args.lane),
        lane_label=_clean(args.lane_label),
        scope=_clean(args.scope),
        tickers_or_dependencies=_clean(args.tickers_or_dependencies),
        source_proof_status=_clean(args.source_proof_status),
        reviewer_outcome=_clean(args.reviewer_outcome),
        validate_result=_clean(args.validate_result),
        preview_result=_clean(args.preview_result),
        apply_result=_clean(args.apply_result),
        rejected_row_status=_clean(args.rejected_row_status),
        readiness_before=_clean(args.readiness_before),
        readiness_after=_clean(args.readiness_after),
        final_outcome=final_outcome,
        changed_inputs=_clean(args.changed_inputs),
        what_changed=_clean(args.what_changed),
        still_blocked=_clean(args.still_blocked),
        review_command=_clean(args.review_command),
        proof_command=_clean(args.proof_command),
        artifact_paths=_clean(args.artifact_paths),
        generated_churn_policy=_clean(args.generated_churn_policy),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reviewed data proof ledger tools.")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--price-reviewed-run", action="store_true")
    parser.add_argument("--public-demo-pack", action="store_true")
    parser.add_argument("--write-public-demo-pack", default="")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=3500)
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--sleep-seconds", type=int, default=30)
    for column in PROOF_LEDGER_COLUMNS:
        parser.add_argument(f"--{column.replace('_', '-')}", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ledger_path = Path(args.ledger)
    if args.record:
        row = build_proof_from_args(args)
        written = append_reviewed_proof(row, ledger_path)
        print("Reviewed Data Proof Record")
        print(f"Wrote: {written}")
        print(f"Proof: {row.proof_id} | {row.lane_label} | {row.final_outcome}")
        return
    rows = load_reviewed_proofs(ledger_path)
    if args.price_reviewed_run:
        print(
            render_price_reviewed_run_plan(
                max_candidates=args.max_candidates,
                top_n=args.top_n,
                provider=args.provider,
                sleep_seconds=args.sleep_seconds,
            )
        )
        return
    if args.public_demo_pack or args.write_public_demo_pack:
        rendered = render_public_demo_readiness_pack(rows)
        if args.write_public_demo_pack:
            output_path = Path(args.write_public_demo_pack)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered + "\n", encoding="utf-8")
            print("Public Demo Readiness Pack")
            print(f"Wrote: {output_path}")
        else:
            print(rendered)
        return
    if args.history:
        print(render_lane_outcome_history(rows))
        return
    if args.latest:
        print(render_latest_proof_timeline(rows))
        return
    print(render_reviewed_data_proofs(rows))


if __name__ == "__main__":
    main()
