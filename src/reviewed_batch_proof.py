"""Reviewed batch proof ledger.

This ledger records reviewed batch execution outcomes separately from broad
generated readiness reports. The command is append-only by design: it does not
refresh providers, import rows, apply data, or produce research conclusions.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_BATCH_PROOF_LEDGER = Path("data/reviewed_batch_proofs.csv")
BATCH_OUTCOMES = {"supported", "still_blocked", "skipped", "excluded"}
BATCH_PROOF_COLUMNS = (
    "batch_id",
    "review_date",
    "reviewer",
    "lane",
    "scope",
    "tickers",
    "command_run",
    "validation_result",
    "preview_result",
    "apply_result",
    "pre_run_readiness_snapshot",
    "post_run_readiness_snapshot",
    "changed_readiness_counts",
    "changed_tickers",
    "source_files",
    "generated_artifacts_reviewed",
    "final_outcome",
    "notes",
)


@dataclass(frozen=True)
class ReviewedBatchProof:
    batch_id: str
    review_date: str
    reviewer: str
    lane: str
    scope: str
    tickers: str
    command_run: str
    validation_result: str
    preview_result: str
    apply_result: str
    pre_run_readiness_snapshot: str
    post_run_readiness_snapshot: str
    changed_readiness_counts: str
    changed_tickers: str
    source_files: str
    generated_artifacts_reviewed: str
    final_outcome: str
    notes: str


def _clean(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def batch_proof_from_row(row: dict[str, str]) -> ReviewedBatchProof:
    values = {column: _clean(row.get(column)) for column in BATCH_PROOF_COLUMNS}
    values["final_outcome"] = values["final_outcome"].lower()
    return ReviewedBatchProof(**values)


def load_reviewed_batch_proofs(path: Path = DEFAULT_BATCH_PROOF_LEDGER) -> list[ReviewedBatchProof]:
    return [batch_proof_from_row(row) for row in _read_csv(path)]


def write_reviewed_batch_proofs(
    rows: Iterable[ReviewedBatchProof],
    path: Path = DEFAULT_BATCH_PROOF_LEDGER,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BATCH_PROOF_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in BATCH_PROOF_COLUMNS})
    return path


def append_reviewed_batch_proof(
    row: ReviewedBatchProof,
    path: Path = DEFAULT_BATCH_PROOF_LEDGER,
) -> Path:
    existing = load_reviewed_batch_proofs(path)
    existing.append(row)
    return write_reviewed_batch_proofs(existing, path)


def latest_reviewed_batch_proof(rows: list[ReviewedBatchProof]) -> ReviewedBatchProof | None:
    if not rows:
        return None
    return sorted(rows, key=lambda row: (row.review_date, row.batch_id))[-1]


def render_reviewed_batch_proofs(rows: list[ReviewedBatchProof]) -> str:
    lines = [
        "Reviewed Batch Proof Ledger",
        "Durable: this ledger records reviewed batch outcomes; it is not broad generated CSV/JSON churn.",
        "Research-only: proof rows do not provide investment advice, broker actions, auto-trading, order routing, or direct buy/sell instructions.",
        "",
    ]
    if not rows:
        lines.extend(
            [
                "No reviewed batch proof rows are recorded yet.",
                "Use reviewed-batch-proof-record after a copy-only packet, dry-run or reviewed scope, validation, preview, apply decision, readiness proof, and churn review.",
            ]
        )
        return "\n".join(lines)
    for row in sorted(rows, key=lambda item: (item.review_date, item.batch_id), reverse=True):
        lines.extend(
            [
                f"- {row.batch_id} | {row.review_date} | {row.lane} | {row.final_outcome}",
                f"  scope: {row.scope}; tickers: {row.tickers}",
                f"  command_run: {row.command_run}",
                f"  validate/preview/apply: {row.validation_result} / {row.preview_result} / {row.apply_result}",
                f"  readiness before -> after: {row.pre_run_readiness_snapshot} -> {row.post_run_readiness_snapshot}",
                f"  changed_readiness_counts: {row.changed_readiness_counts}",
                f"  changed_tickers: {row.changed_tickers}",
                f"  source_files: {row.source_files}",
                f"  generated_artifacts_reviewed: {row.generated_artifacts_reviewed}",
                f"  reviewer: {row.reviewer}",
                f"  notes: {row.notes}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_batch_proof_from_args(args: argparse.Namespace) -> ReviewedBatchProof:
    final_outcome = _clean(args.final_outcome).lower()
    if final_outcome not in BATCH_OUTCOMES:
        raise SystemExit("FINAL_OUTCOME must be one of supported, still_blocked, skipped, excluded.")
    return ReviewedBatchProof(
        batch_id=_clean(args.batch_id),
        review_date=_clean(args.review_date),
        reviewer=_clean(args.reviewer),
        lane=_clean(args.lane),
        scope=_clean(args.scope),
        tickers=_clean(args.tickers),
        command_run=_clean(args.command_run),
        validation_result=_clean(args.validation_result),
        preview_result=_clean(args.preview_result),
        apply_result=_clean(args.apply_result),
        pre_run_readiness_snapshot=_clean(args.pre_run_readiness_snapshot),
        post_run_readiness_snapshot=_clean(args.post_run_readiness_snapshot),
        changed_readiness_counts=_clean(args.changed_readiness_counts),
        changed_tickers=_clean(args.changed_tickers),
        source_files=_clean(args.source_files),
        generated_artifacts_reviewed=_clean(args.generated_artifacts_reviewed),
        final_outcome=final_outcome,
        notes=_clean(args.notes),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reviewed batch proof ledger tools.")
    parser.add_argument("--ledger", default=str(DEFAULT_BATCH_PROOF_LEDGER))
    parser.add_argument("--record", action="store_true")
    for column in BATCH_PROOF_COLUMNS:
        parser.add_argument(f"--{column.replace('_', '-')}", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ledger_path = Path(args.ledger)
    if args.record:
        row = build_batch_proof_from_args(args)
        written = append_reviewed_batch_proof(row, ledger_path)
        print("Reviewed Batch Proof Record")
        print(f"Wrote: {written}")
        print(f"Batch: {row.batch_id} | {row.lane} | {row.final_outcome}")
        return 0
    print(render_reviewed_batch_proofs(load_reviewed_batch_proofs(ledger_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
