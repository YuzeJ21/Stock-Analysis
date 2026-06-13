"""Compare before/after readiness snapshots for reviewed batch proof.

The comparison is deterministic and read-only. It does not refresh data,
apply imports, or infer that a readiness change is supported without the
operator's source review.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.reviewed_batch import readiness_freshness_status


DEFAULT_BEFORE = Path("data/reports/ticker_readiness_report.previous.csv")
DEFAULT_AFTER = Path("data/reports/ticker_readiness_report.csv")
COUNT_COLUMNS = (
    "overall_readiness_state",
    "price_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "earnings_ready",
    "analyst_estimates_ready",
)
COMPARE_COLUMNS = (
    "overall_readiness_state",
    "price_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "peer_trend_comparison_ready",
    "peer_valuation_comparison_ready",
    "earnings_ready",
    "analyst_estimates_ready",
    "blocked_features",
    "excluded_features",
    "missing_data",
)


@dataclass(frozen=True)
class ReadinessComparison:
    status: str
    before_path: Path
    after_path: Path
    before_rows: int
    after_rows: int
    changed_tickers: tuple[str, ...]
    changed_count: int
    changed_readiness_counts: str
    freshness_status: str
    freshness_message: str
    blocking_message: str = ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _ticker_key(row: dict[str, str]) -> str:
    return _clean(row.get("ticker")).upper()


def _truthy(value: object) -> bool:
    return _clean(value).lower() in {"true", "1", "yes", "y", "ready"}


def _counts(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {column: {} for column in COUNT_COLUMNS}
    for row in rows:
        for column in COUNT_COLUMNS:
            if column == "overall_readiness_state":
                value = _clean(row.get(column)).lower() or "missing"
            else:
                value = "ready" if _truthy(row.get(column)) else "not_ready"
            result[column][value] = result[column].get(value, 0) + 1
    return result


def _count_delta_summary(before: list[dict[str, str]], after: list[dict[str, str]]) -> str:
    before_counts = _counts(before)
    after_counts = _counts(after)
    parts: list[str] = []
    for column in COUNT_COLUMNS:
        keys = sorted(set(before_counts[column]) | set(after_counts[column]))
        deltas = []
        for key in keys:
            before_value = before_counts[column].get(key, 0)
            after_value = after_counts[column].get(key, 0)
            if before_value != after_value:
                deltas.append(f"{key}: {before_value}->{after_value}")
        if deltas:
            parts.append(f"{column} ({'; '.join(deltas)})")
    return "; ".join(parts) if parts else "none; no readiness count changes"


def _row_signature(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(_clean(row.get(column)) for column in COMPARE_COLUMNS)


def _changed_tickers(before: list[dict[str, str]], after: list[dict[str, str]]) -> list[str]:
    before_by_ticker = {_ticker_key(row): row for row in before if _ticker_key(row)}
    after_by_ticker = {_ticker_key(row): row for row in after if _ticker_key(row)}
    tickers = sorted(set(before_by_ticker) | set(after_by_ticker))
    changed = []
    for ticker in tickers:
        if _row_signature(before_by_ticker.get(ticker, {})) != _row_signature(after_by_ticker.get(ticker, {})):
            changed.append(ticker)
    return changed


def compare_readiness_snapshots(
    root: Path | str = ".",
    *,
    before: Path | str = DEFAULT_BEFORE,
    after: Path | str = DEFAULT_AFTER,
    top_n: int = 25,
) -> ReadinessComparison:
    root = Path(root)
    before_path = root / before
    after_path = root / after
    freshness = readiness_freshness_status(root)
    if not before_path.exists():
        after_rows = _read_csv(after_path)
        return ReadinessComparison(
            "missing_before",
            before_path,
            after_path,
            0,
            len(after_rows),
            (),
            0,
            "not available",
            freshness.status,
            freshness.message,
            "Missing prior readiness snapshot. Run make readiness-snapshot before a reviewed batch.",
        )
    if not after_path.exists():
        return ReadinessComparison(
            "missing_after",
            before_path,
            after_path,
            0,
            0,
            (),
            0,
            "not available",
            freshness.status,
            freshness.message,
            "Missing current readiness report. Run make readiness after a reviewed batch.",
        )
    before_rows = _read_csv(before_path)
    after_rows = _read_csv(after_path)
    changed = _changed_tickers(before_rows, after_rows)
    return ReadinessComparison(
        "ok",
        before_path,
        after_path,
        len(before_rows),
        len(after_rows),
        tuple(changed[: max(top_n, 0)]),
        len(changed),
        _count_delta_summary(before_rows, after_rows),
        freshness.status,
        freshness.message,
        "Run make readiness before relying on final counts." if freshness.status in {"missing", "stale"} else "",
    )


def proof_record_command(
    comparison: ReadinessComparison,
    *,
    batch_id: str,
    lane: str,
    review_date: str,
    final_outcome: str = "skipped",
) -> str:
    changed_tickers = ",".join(comparison.changed_tickers) if comparison.changed_tickers else "none"
    changed_counts = comparison.changed_readiness_counts.replace('"', "'")
    before_snapshot = f"{comparison.before_rows} rows from {comparison.before_path}"
    after_snapshot = f"{comparison.after_rows} rows from {comparison.after_path}"
    return (
        "make reviewed-batch-proof-record "
        f'BATCH_ID="{batch_id}" '
        f'LANE="{lane}" '
        f'REVIEW_DATE="{review_date}" '
        f'FINAL_OUTCOME="{final_outcome}" '
        f'PRE_RUN_READINESS_SNAPSHOT="{before_snapshot}" '
        f'POST_RUN_READINESS_SNAPSHOT="{after_snapshot}" '
        f'CHANGED_READINESS_COUNTS="{changed_counts}" '
        f'CHANGED_TICKERS="{changed_tickers}"'
    )


def render_readiness_comparison(
    comparison: ReadinessComparison,
    *,
    batch_id: str = "<batch_id>",
    lane: str = "<lane>",
    review_date: str = "<yyyy-mm-dd>",
) -> str:
    lines = [
        "Reviewed Batch Readiness Comparison",
        "Read-only: compares saved readiness snapshots for proof rows; it does not refresh data, apply rows, or create recommendations.",
        "Research-only: changed counts are data-readiness evidence, not investment advice or trade instructions.",
        "",
        f"Status: {comparison.status}",
        f"Before snapshot: {comparison.before_path}",
        f"After snapshot: {comparison.after_path}",
        f"Rows before -> after: {comparison.before_rows} -> {comparison.after_rows}",
        f"Freshness: {comparison.freshness_status} - {comparison.freshness_message}",
    ]
    if comparison.blocking_message:
        lines.append(f"Blocking note: {comparison.blocking_message}")
    lines.extend(
        [
            f"Changed readiness counts: {comparison.changed_readiness_counts}",
            f"Changed tickers ({comparison.changed_count}): {', '.join(comparison.changed_tickers) if comparison.changed_tickers else 'none'}",
            "",
            "Proof-ledger command scaffold:",
            proof_record_command(
                comparison,
                batch_id=batch_id,
                lane=lane,
                review_date=review_date,
                final_outcome="skipped",
            ),
            "",
            "Use `supported` only when source proof, validation, preview/apply decision, rebuilt readiness, and artifact review all support it.",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare reviewed batch readiness snapshots.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--before", default=str(DEFAULT_BEFORE))
    parser.add_argument("--after", default=str(DEFAULT_AFTER))
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--batch-id", default="<batch_id>")
    parser.add_argument("--lane", default="<lane>")
    parser.add_argument("--review-date", default="<yyyy-mm-dd>")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    comparison = compare_readiness_snapshots(
        args.root,
        before=args.before,
        after=args.after,
        top_n=args.top_n,
    )
    print(
        render_readiness_comparison(
            comparison,
            batch_id=args.batch_id,
            lane=args.lane,
            review_date=args.review_date,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
