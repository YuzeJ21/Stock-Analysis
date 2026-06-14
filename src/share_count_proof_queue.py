"""Share-count proof queue for DCF readiness.

This read-only queue separates the recurring shares-outstanding blocker from
the broader fundamentals lane. It does not infer share counts, refresh data,
apply imports, or create valuation conclusions.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.dcf_readiness import build_dcf_readiness_frame
from src.loader import normalize_columns
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root


QUEUE_COLUMNS = [
    "priority",
    "ticker",
    "scope",
    "missing_field",
    "dcf_input_status",
    "sec_stage_command",
    "manual_source_path",
    "validation_sequence",
    "proof_after_update",
    "stop_rule",
    "source_note",
]


@dataclass(frozen=True)
class ShareCountProofRow:
    priority: int
    ticker: str
    scope: str
    missing_field: str
    dcf_input_status: str
    sec_stage_command: str
    manual_source_path: str
    validation_sequence: str
    proof_after_update: str
    stop_rule: str
    source_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame.columns = normalize_columns(list(frame.columns))
    return frame


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"true", "1", "yes", "y"}


def _missing_fields(value: object) -> list[str]:
    return [part.strip() for part in str(value or "").replace("|", ",").replace(";", ",").split(",") if part.strip()]


def _universe_scope(universe: pd.DataFrame, ticker: str) -> str:
    if universe.empty or "ticker" not in universe.columns:
        return "master universe"
    frame = universe.copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    rows = frame.loc[frame["ticker"].eq(ticker)]
    if rows.empty:
        return "master universe"
    row = rows.iloc[-1]
    if _truthy(row.get("in_active_universe")):
        return "active universe"
    if _truthy(row.get("in_portfolio")):
        return "portfolio universe"
    return "master universe"


def _dcf_input_status(row: pd.Series) -> str:
    ready_fields = []
    missing_fields = []
    checks = [
        ("price", "has_price"),
        ("revenue", "has_revenue"),
        ("free cash flow", "has_free_cash_flow"),
        ("FCF margin", "has_fcf_margin"),
    ]
    for label, column in checks:
        if _truthy(row.get(column)):
            ready_fields.append(label)
        else:
            missing_fields.append(label)
    if not missing_fields:
        return "share-count-only blocker; price, revenue, free cash flow, and FCF margin are present"
    return f"shares plus missing {', '.join(missing_fields)}"


def _rank(row: pd.Series, universe: pd.DataFrame) -> tuple[int, int, str]:
    ticker = str(row.get("ticker", "")).upper()
    active_rank = 0 if _universe_scope(universe, ticker) == "active universe" else 1
    other_inputs_rank = 0 if _dcf_input_status(row).startswith("share-count-only") else 1
    return active_rank, other_inputs_rank, ticker


def build_share_count_proof_queue(
    *,
    universe: pd.DataFrame,
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> list[ShareCountProofRow]:
    dcf = build_dcf_readiness_frame(universe=universe, fundamentals=fundamentals, prices=prices)
    if dcf.empty:
        return []
    company = dcf.get("asset_type", pd.Series("", index=dcf.index)).astype(str).str.lower().eq("company")
    not_ready = ~dcf.get("is_dcf_ready", pd.Series(False, index=dcf.index)).astype(bool)
    has_share_gap = dcf.get("missing_dcf_fields", pd.Series("", index=dcf.index)).astype(str).str.contains(
        "shares_outstanding", na=False
    )
    queue = dcf.loc[company & not_ready & has_share_gap].copy()
    if tickers:
        wanted = {ticker.upper().strip() for ticker in tickers if ticker.strip()}
        queue = queue.loc[queue["ticker"].astype(str).str.upper().isin(wanted)]
    if queue.empty:
        return []
    ranked = sorted((row for _, row in queue.iterrows()), key=lambda row: _rank(row, universe))
    rows: list[ShareCountProofRow] = []
    for row in ranked[: max(top_n, 0)]:
        ticker = str(row.get("ticker", "")).upper().strip()
        missing = _missing_fields(row.get("missing_dcf_fields"))
        row_status = _dcf_input_status(row)
        rows.append(
            ShareCountProofRow(
                priority=len(rows) + 1,
                ticker=ticker,
                scope=_universe_scope(universe, ticker),
                missing_field="shares_outstanding",
                dcf_input_status=row_status,
                sec_stage_command=f"make sec-stage TICKERS={ticker}",
                manual_source_path="data/imports/fundamentals.csv",
                validation_sequence="make imports-validate -> make imports-preview -> make imports-apply",
                proof_after_update=f"make dcf-readiness && make readiness && make stock-report-md TICKER={ticker}",
                stop_rule=(
                    "Stop if SEC/manual source proof cannot verify shares_outstanding; keep DCF blocked and do not infer "
                    "share count from price, market cap, or placeholder rows."
                ),
                source_note=(
                    "SEC Companyfacts may not expose the needed share-count fact. Use a reviewed 10-K/10-Q/annual report "
                    f"or trusted local row only; remaining missing fields: {', '.join(missing)}."
                ),
            )
        )
    return rows


def build_share_count_proof_queue_from_files(
    root: Path,
    *,
    data_dir: Path | None = None,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> list[ShareCountProofRow]:
    data_path = resolve_data_dir(data_dir, root)
    return build_share_count_proof_queue(
        universe=_read_csv(data_path / "universe.csv"),
        fundamentals=_read_csv(data_path / "fundamentals.csv"),
        prices=_read_csv(data_path / "prices.csv"),
        top_n=top_n,
        tickers=tickers,
    )


def render_share_count_proof_queue(rows: list[ShareCountProofRow]) -> str:
    lines = [
        "Share Count Proof Queue",
        "Read-only: this queue does not refresh data, apply imports, or create valuation conclusions.",
        "Research-only: shares-outstanding proof is a DCF input gate, not investment advice or a buy/sell instruction.",
        "Do not infer share count from price, market cap, peer data, or placeholder rows.",
    ]
    if not rows:
        lines.append("No shares-outstanding DCF blockers found for the selected scope.")
        return "\n".join(lines)
    share_only = sum(1 for row in rows if row.dcf_input_status.startswith("share-count-only"))
    lines.append(f"Rows shown: {len(rows)}; share-count-only blockers: {share_only}")
    lines.append(f"Next safest action: {rows[0].sec_stage_command}, then review whether SEC/manual source proof includes shares_outstanding.")
    lines.append("")
    lines.append("Priority | Ticker | Scope | DCF input status | Source path | Proof after update")
    lines.append("---: | --- | --- | --- | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    str(row.priority),
                    row.ticker,
                    row.scope,
                    row.dcf_input_status,
                    row.manual_source_path,
                    row.proof_after_update,
                ]
            )
        )
    lines.append("")
    lines.append("Review checklist:")
    lines.append("- Stage SEC rows first when configured, but keep shares_outstanding blocked if SEC does not expose it.")
    lines.append("- For manual source rows, record the source document and date before validate / preview / apply.")
    lines.append("- Rebuild DCF readiness and the single-stock report before calling a lane supported.")
    return "\n".join(lines)


def _split_tickers(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a read-only shares-outstanding proof queue for DCF blockers.")
    parser.add_argument("--project-root")
    parser.add_argument("--data-dir")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--tickers")
    parser.add_argument("--output", help="Optional CSV output path.")
    args = parser.parse_args()

    root = resolve_project_root(Path(args.project_root) if args.project_root else None)
    data_path = resolve_data_dir(Path(args.data_dir) if args.data_dir else None, root)
    rows = build_share_count_proof_queue_from_files(
        root,
        data_dir=data_path,
        top_n=args.top_n,
        tickers=_split_tickers(args.tickers),
    )
    print(format_path_context(root, data_path, resolve_outputs_dir(None, root)))
    print(render_share_count_proof_queue(rows))
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([row.to_dict() for row in rows], columns=QUEUE_COLUMNS).to_csv(output, index=False)
        print(f"\nWrote share-count proof queue CSV: {output}")


if __name__ == "__main__":
    main()
