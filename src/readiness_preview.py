"""Read-only saved-versus-proposed readiness impact preview."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.paths import resolve_data_dir, resolve_project_root
from src.readiness_engine import build_ticker_readiness_report


STABLE_READINESS_FIELDS = (
    "overall_readiness_state",
    "price_ready",
    "momentum_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "earnings_ready",
    "analyst_estimates_ready",
    "ready_features",
    "partial_features",
    "blocked_features",
    "excluded_features",
)

BOOLEAN_READINESS_FIELDS = (
    "price_ready",
    "momentum_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "earnings_ready",
    "analyst_estimates_ready",
)

OVERALL_STATES = ("ready", "partial", "blocked", "excluded")


@dataclass(frozen=True)
class ReadinessTickerChange:
    ticker: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessImpactPreview:
    status: str
    saved_ticker_count: int
    proposed_ticker_count: int
    saved_counts: tuple[tuple[str, int], ...]
    proposed_counts: tuple[tuple[str, int], ...]
    changed_ticker_count: int
    changed_tickers: tuple[ReadinessTickerChange, ...]
    top_n: int
    saved_path: str


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _stable_value(row: pd.Series, field: str) -> bool | str:
    if field in BOOLEAN_READINESS_FIELDS:
        return _truthy(row.get(field))
    return _text(row.get(field))


def _index_readiness(frame: pd.DataFrame) -> dict[str, pd.Series]:
    if frame.empty or "ticker" not in frame.columns:
        return {}
    rows: dict[str, pd.Series] = {}
    for _, row in frame.iterrows():
        ticker = _text(row.get("ticker")).upper()
        if ticker:
            rows[ticker] = row
    return rows


def _count_summary(frame: pd.DataFrame) -> tuple[tuple[str, int], ...]:
    indexed = _index_readiness(frame)
    rows = list(indexed.values())
    counts: list[tuple[str, int]] = []
    for state in OVERALL_STATES:
        counts.append(
            (
                f"overall_{state}",
                sum(_text(row.get("overall_readiness_state")).lower() == state for row in rows),
            )
        )
    for field in BOOLEAN_READINESS_FIELDS:
        counts.append((field, sum(_truthy(row.get(field)) for row in rows)))
    return tuple(counts)


def compare_readiness_frames(
    saved: pd.DataFrame,
    proposed: pd.DataFrame,
    *,
    top_n: int = 20,
    saved_path: str = "data/reports/ticker_readiness_report.csv",
) -> ReadinessImpactPreview:
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    saved_rows = _index_readiness(saved)
    proposed_rows = _index_readiness(proposed)
    changes: list[ReadinessTickerChange] = []
    for ticker in sorted(set(saved_rows) | set(proposed_rows)):
        if ticker not in saved_rows or ticker not in proposed_rows:
            fields = ("row_presence",)
        else:
            fields = tuple(
                field
                for field in STABLE_READINESS_FIELDS
                if _stable_value(saved_rows[ticker], field) != _stable_value(proposed_rows[ticker], field)
            )
        if fields:
            changes.append(ReadinessTickerChange(ticker=ticker, fields=fields))
    return ReadinessImpactPreview(
        status="changes_detected" if changes else "no_readiness_changes",
        saved_ticker_count=len(saved_rows),
        proposed_ticker_count=len(proposed_rows),
        saved_counts=_count_summary(saved),
        proposed_counts=_count_summary(proposed),
        changed_ticker_count=len(changes),
        changed_tickers=tuple(changes[:top_n]),
        top_n=top_n,
        saved_path=saved_path,
    )


def build_readiness_impact_preview(
    root: Path | str,
    *,
    data_dir: Path | str | None = None,
    top_n: int = 20,
) -> ReadinessImpactPreview:
    project_root = resolve_project_root(root)
    data_path = resolve_data_dir(data_dir, project_root)
    saved_path = data_path / "reports" / "ticker_readiness_report.csv"
    if not saved_path.exists():
        return ReadinessImpactPreview(
            status="missing_saved_snapshot",
            saved_ticker_count=0,
            proposed_ticker_count=0,
            saved_counts=(),
            proposed_counts=(),
            changed_ticker_count=0,
            changed_tickers=(),
            top_n=top_n,
            saved_path=str(saved_path),
        )
    saved = pd.read_csv(saved_path)
    reports = build_ticker_readiness_report(
        project_root,
        data_dir=data_path,
        write_outputs=False,
    )
    proposed = reports["ticker_readiness_report"]
    return compare_readiness_frames(
        saved,
        proposed,
        top_n=top_n,
        saved_path=str(saved_path),
    )


def _format_counts(counts: tuple[tuple[str, int], ...]) -> str:
    return ", ".join(f"{name}={value}" for name, value in counts) or "unavailable"


def render_readiness_impact_preview(preview: ReadinessImpactPreview) -> str:
    lines = ["Readiness Impact Preview", ""]
    if preview.status == "missing_saved_snapshot":
        lines.extend(
            [
                "Status: missing_saved_snapshot",
                f"Saved snapshot: {preview.saved_path}",
                "Comparison is unavailable because the saved readiness snapshot is missing.",
            ]
        )
    else:
        lines.extend(
            [
                f"Status: {preview.status}",
                f"Ticker rows: saved={preview.saved_ticker_count}, proposed={preview.proposed_ticker_count}",
                f"Saved counts: {_format_counts(preview.saved_counts)}",
                f"Proposed counts: {_format_counts(preview.proposed_counts)}",
                f"Changed tickers: {preview.changed_ticker_count}",
            ]
        )
        for change in preview.changed_tickers:
            lines.append(f"- {change.ticker}: {', '.join(change.fields)}")
        hidden = preview.changed_ticker_count - len(preview.changed_tickers)
        if hidden > 0:
            lines.append(f"- ... {hidden} additional changed ticker(s) hidden by TOP_N={preview.top_n}")
    lines.extend(
        [
            "",
            "Read-only: no files were created, modified, or deleted.",
            "This preview does not make saved readiness current.",
            "An intentional reviewed make readiness run remains the separate rebuild boundary.",
            "Research workflow evidence only; not investment advice or a recommendation.",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview stable readiness impact without writing files.")
    parser.add_argument("--project-root", default=".", help="Project root. Defaults to the current directory.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--top-n", type=int, default=20, help="Maximum changed ticker details to print.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.top_n < 1:
        print("Readiness preview failed: --top-n must be at least 1.")
        return 1
    try:
        preview = build_readiness_impact_preview(
            Path(args.project_root),
            data_dir=args.data_dir,
            top_n=args.top_n,
        )
    except (KeyError, OSError, ValueError) as exc:
        print(f"Readiness preview failed: {exc}")
        print("Read-only: no readiness output was written.")
        return 1
    print(render_readiness_impact_preview(preview))
    return 2 if preview.status == "missing_saved_snapshot" else 0


if __name__ == "__main__":
    raise SystemExit(main())
