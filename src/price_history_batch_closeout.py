"""Render a copy-only closeout scaffold for reviewed price-history blockers."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.price_history_proof_queue import PriceHistoryProofRow, build_price_history_proof_queue_from_files


def _parse_tickers(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [ticker.strip().upper() for ticker in value.split(",") if ticker.strip()]


def _is_reviewed_source_limited(row: PriceHistoryProofRow) -> bool:
    return "reviewed proof ledger already records" in row.source_note.lower()


def _grouped_tickers(rows: list[PriceHistoryProofRow], top_n: int) -> list[str]:
    return sorted({row.ticker for row in rows if _is_reviewed_source_limited(row)})[: max(top_n, 0)]


def render_price_history_batch_closeout(rows: list[PriceHistoryProofRow], *, top_n: int = 10) -> str:
    """Render one deterministic, non-writing proof-record scaffold."""
    tickers = _grouped_tickers(rows, top_n)
    lines = [
        "Reviewed Price-History Batch Closeout",
        "Read-only: this command groups reviewed source-limited price-history outcomes only.",
        "It does not refresh, write data, record proof rows, stage, commit, push, or expose secrets.",
        "Copy-only: inspect the grouped outcome, then copy and complete the scaffold only when an intentional proof record is warranted.",
    ]
    if not tickers:
        lines.append("No reviewed source-limited price-history outcomes found for the selected scope.")
        return "\n".join(lines)

    ticker_list = ",".join(tickers)
    lines.extend(
        [
            f"Grouped tickers: {', '.join(tickers)}",
            "Copy-only proof-record scaffold (DRY_RUN=1):",
            (
                "DRY_RUN=1 make reviewed-batch-proof-record "
                "BATCH_ID=RB-PRICE-HISTORY-YYYYMMDD-001 "
                "REVIEW_DATE=YYYY-MM-DD "
                "LANE=price_history "
                f"TICKERS={ticker_list} "
                "FINAL_OUTCOME=still_blocked "
                'SCOPE="reviewed source-limited price-history closeout"'
            ),
            "The scaffold remains a dry run and does not record a proof row.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a read-only reviewed price-history batch closeout scaffold.")
    parser.add_argument("--project-root")
    parser.add_argument("--data-dir")
    parser.add_argument("--outputs-dir")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--tickers")
    args = parser.parse_args(argv)

    root = resolve_project_root(Path(args.project_root) if args.project_root else None)
    data_path = resolve_data_dir(Path(args.data_dir) if args.data_dir else None, root)
    output_path = resolve_outputs_dir(Path(args.outputs_dir) if args.outputs_dir else None, root)
    rows = build_price_history_proof_queue_from_files(
        root,
        data_dir=data_path,
        output_dir=output_path,
        top_n=None,
        tickers=_parse_tickers(args.tickers),
        include_reviewed=True,
    )
    print(format_path_context(root, data_path, output_path))
    print(render_price_history_batch_closeout(rows, top_n=args.top_n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
