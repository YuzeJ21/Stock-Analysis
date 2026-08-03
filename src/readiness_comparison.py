"""Compare one saved readiness baseline with a current in-memory row set.

The comparison is deterministic and read-only. It does not refresh data,
apply imports, materialize readiness, or infer that a readiness change is
supported without the operator's source review.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from src.readiness_engine import (
    READINESS_METHOD_VERSION,
    READINESS_SNAPSHOT_FILENAME,
    READINESS_SNAPSHOT_SCHEMA_VERSION,
    build_ticker_readiness_report,
)
from src.readiness_source_boundary import (
    ReadinessSourceBoundaryError,
    readiness_input_identity,
    validate_readiness_source_boundary,
)


DEFAULT_BEFORE = Path("data/reports") / READINESS_SNAPSHOT_FILENAME
# Compatibility label only. The default comparison never reads this path.
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
SNAPSHOT_METADATA_COLUMNS = (
    "snapshot_profile",
    "snapshot_input_identity",
    "snapshot_captured_at",
    "snapshot_schema_version",
    "snapshot_method_version",
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
    profile: str = "default"
    before_input_identity: str = ""
    after_input_identity: str = ""
    readiness_method_version: str = READINESS_METHOD_VERSION
    after_source: str = ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def _ticker_key(row: Mapping[str, object]) -> str:
    return _clean(row.get("ticker")).upper()


def _truthy(value: object) -> bool:
    return _clean(value).lower() in {"true", "1", "yes", "y", "ready"}


def _counts(rows: Iterable[Mapping[str, object]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {column: {} for column in COUNT_COLUMNS}
    for row in rows:
        for column in COUNT_COLUMNS:
            if column == "overall_readiness_state":
                value = _clean(row.get(column)).lower() or "missing"
            else:
                value = "ready" if _truthy(row.get(column)) else "not_ready"
            result[column][value] = result[column].get(value, 0) + 1
    return result


def _count_delta_summary(
    before: list[dict[str, str]],
    after: list[dict[str, str]],
) -> str:
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


def _row_signature(row: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(_clean(row.get(column)) for column in COMPARE_COLUMNS)


def _changed_tickers(
    before: list[dict[str, str]],
    after: list[dict[str, str]],
) -> list[str]:
    before_by_ticker = {_ticker_key(row): row for row in before if _ticker_key(row)}
    after_by_ticker = {_ticker_key(row): row for row in after if _ticker_key(row)}
    tickers = sorted(set(before_by_ticker) | set(after_by_ticker))
    return [
        ticker
        for ticker in tickers
        if _row_signature(before_by_ticker.get(ticker, {}))
        != _row_signature(after_by_ticker.get(ticker, {}))
    ]


def _path_from_root(root: Path, value: Path | str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _snapshot_metadata(
    rows: list[dict[str, str]],
    *,
    label: str,
    expected_profile: str,
) -> dict[str, str]:
    if not rows:
        raise ValueError(f"{label} readiness snapshot is empty.")
    missing = [column for column in SNAPSHOT_METADATA_COLUMNS if column not in rows[0]]
    if missing:
        raise ValueError(f"{label} snapshot is missing metadata columns: {', '.join(missing)}.")

    metadata: dict[str, str] = {}
    for column in SNAPSHOT_METADATA_COLUMNS:
        values = {_clean(row.get(column)) for row in rows}
        if "" in values:
            raise ValueError(f"{label} snapshot has empty {column} metadata.")
        if len(values) != 1:
            raise ValueError(f"{label} snapshot has inconsistent {column} metadata.")
        metadata[column] = next(iter(values))

    if metadata["snapshot_profile"] != expected_profile:
        raise ValueError(
            f"{label} snapshot_profile {metadata['snapshot_profile']!r} does not match selected profile "
            f"{expected_profile!r}."
        )
    if metadata["snapshot_schema_version"] != READINESS_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(
            f"{label} snapshot schema version {metadata['snapshot_schema_version']!r} is unsupported; "
            f"expected {READINESS_SNAPSHOT_SCHEMA_VERSION!r}."
        )
    if metadata["snapshot_method_version"] != READINESS_METHOD_VERSION:
        raise ValueError(
            f"{label} snapshot method version {metadata['snapshot_method_version']!r} does not match current "
            f"{READINESS_METHOD_VERSION!r}. Capture a new baseline for this profile."
        )
    return metadata


def _blocked_comparison(
    *,
    status: str,
    profile: str,
    before_path: Path,
    after_path: Path,
    after_source: str,
    message: str,
    before_rows: int = 0,
    after_rows: int = 0,
    before_input_identity: str = "",
    after_input_identity: str = "",
) -> ReadinessComparison:
    return ReadinessComparison(
        status=status,
        before_path=before_path,
        after_path=after_path,
        before_rows=before_rows,
        after_rows=after_rows,
        changed_tickers=(),
        changed_count=0,
        changed_readiness_counts="not available",
        freshness_status="not_applicable",
        freshness_message="Saved-artifact freshness is not used for profile-bound snapshot comparison.",
        blocking_message=message,
        profile=profile,
        before_input_identity=before_input_identity,
        after_input_identity=after_input_identity,
        readiness_method_version=READINESS_METHOD_VERSION,
        after_source=after_source,
    )


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, str]]:
    return [
        {str(key): _clean(value) for key, value in row.items()}
        for row in frame.fillna("").to_dict(orient="records")
    ]


def compare_readiness_snapshots(
    root: Path | str = ".",
    *,
    before: Path | str | None = None,
    after: Path | str | None = None,
    profile: str = "default",
    top_n: int = 25,
) -> ReadinessComparison:
    lexical_root = Path(root).expanduser().absolute()
    fallback_before = lexical_root / DEFAULT_BEFORE
    fallback_after = lexical_root / DEFAULT_AFTER
    try:
        selected = validate_readiness_source_boundary(lexical_root, profile)
    except (ReadinessSourceBoundaryError, OSError, ValueError) as error:
        return _blocked_comparison(
            status="source_boundary_blocked",
            profile=profile,
            before_path=fallback_before,
            after_path=fallback_after,
            after_source=f"in-memory readiness profile={profile}",
            message=f"Readiness source boundary refused comparison: {error}",
        )

    before_path = (
        selected.data_dir / "reports" / READINESS_SNAPSHOT_FILENAME
        if before is None
        else _path_from_root(lexical_root, before)
    )
    if after is None:
        after_source = f"in-memory readiness profile={selected.name}"
        after_path = Path(after_source)
    else:
        after_path = _path_from_root(lexical_root, after)
        after_source = str(after_path)

    if not before_path.is_file():
        return _blocked_comparison(
            status="missing_before",
            profile=selected.name,
            before_path=before_path,
            after_path=after_path,
            after_source=after_source,
            message=(
                "Missing prior readiness snapshot. Run "
                f"make readiness-snapshot PROFILE={selected.name} before this reviewed batch."
            ),
        )

    before_rows = _read_csv(before_path)
    try:
        before_metadata = _snapshot_metadata(
            before_rows,
            label="Prior",
            expected_profile=selected.name,
        )
    except (OSError, ValueError) as error:
        return _blocked_comparison(
            status="invalid_before",
            profile=selected.name,
            before_path=before_path,
            after_path=after_path,
            after_source=after_source,
            message=f"Prior readiness snapshot is invalid: {error}",
            before_rows=len(before_rows),
        )
    before_identity = before_metadata["snapshot_input_identity"]

    if after is not None:
        if not after_path.is_file():
            return _blocked_comparison(
                status="missing_after",
                profile=selected.name,
                before_path=before_path,
                after_path=after_path,
                after_source=after_source,
                message="Explicit current readiness fixture is missing.",
                before_rows=len(before_rows),
                before_input_identity=before_identity,
            )
        after_rows = _read_csv(after_path)
        try:
            after_metadata = _snapshot_metadata(
                after_rows,
                label="Explicit current",
                expected_profile=selected.name,
            )
        except (OSError, ValueError) as error:
            return _blocked_comparison(
                status="invalid_after",
                profile=selected.name,
                before_path=before_path,
                after_path=after_path,
                after_source=after_source,
                message=f"Explicit current readiness fixture is invalid: {error}",
                before_rows=len(before_rows),
                after_rows=len(after_rows),
                before_input_identity=before_identity,
            )
        after_identity = after_metadata["snapshot_input_identity"]
    else:
        try:
            identity_before_composition = readiness_input_identity(lexical_root, selected.name)
            reports = build_ticker_readiness_report(
                lexical_root.resolve(strict=True),
                data_dir=selected.data_dir,
                output_dir=selected.outputs_dir,
                write_outputs=False,
            )
            readiness = reports.get("ticker_readiness_report")
            if not isinstance(readiness, pd.DataFrame):
                raise ValueError("Readiness builder did not return a ticker readiness DataFrame.")
            if readiness.empty:
                raise ValueError("Current in-memory ticker readiness row set is empty.")
            after_identity = readiness_input_identity(lexical_root, selected.name)
            if after_identity != identity_before_composition:
                raise ValueError("Named readiness inputs changed during current composition.")
            after_rows = _frame_rows(readiness)
        except Exception as error:
            return _blocked_comparison(
                status="current_composition_blocked",
                profile=selected.name,
                before_path=before_path,
                after_path=after_path,
                after_source=after_source,
                message=f"Current in-memory readiness composition failed: {error}",
                before_rows=len(before_rows),
                before_input_identity=before_identity,
            )

    changed = _changed_tickers(before_rows, after_rows)
    return ReadinessComparison(
        status="ok",
        before_path=before_path,
        after_path=after_path,
        before_rows=len(before_rows),
        after_rows=len(after_rows),
        changed_tickers=tuple(changed[: max(top_n, 0)]),
        changed_count=len(changed),
        changed_readiness_counts=_count_delta_summary(before_rows, after_rows),
        freshness_status="not_applicable",
        freshness_message="Current readiness rows were composed in memory; saved-artifact freshness was not consulted.",
        profile=selected.name,
        before_input_identity=before_identity,
        after_input_identity=after_identity,
        readiness_method_version=READINESS_METHOD_VERSION,
        after_source=after_source,
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
    after_label = comparison.after_source or str(comparison.after_path)
    after_snapshot = f"{comparison.after_rows} rows from {after_label}"
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
    after_label = comparison.after_source or str(comparison.after_path)
    lines = [
        "Reviewed Batch Readiness Comparison",
        "Read-only: compares a saved profile-bound baseline with current readiness composed in memory; it does not refresh data, apply rows, or create recommendations.",
        "Research-only: changed counts are data-readiness evidence, not investment advice or trade instructions.",
        "",
        f"Status: {comparison.status}",
        f"Profile: {comparison.profile}",
        f"Before snapshot: {comparison.before_path}",
        f"After row set: {after_label}",
        f"Rows before -> after: {comparison.before_rows} -> {comparison.after_rows}",
        f"Before input identity: {comparison.before_input_identity or 'not available'}",
        f"After input identity: {comparison.after_input_identity or 'not available'}",
        f"Readiness method version: {comparison.readiness_method_version}",
        f"Freshness boundary: {comparison.freshness_status} - {comparison.freshness_message}",
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
            "Use `supported` only when source proof, validation, preview/apply decision, in-memory comparison, and artifact review all support it.",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare a profile-bound prior baseline with current readiness composed in memory."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--before")
    parser.add_argument("--after")
    parser.add_argument("--profile", choices=("default", "demo", "local"), default="default")
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
        profile=args.profile,
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
    return 0 if comparison.status == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
