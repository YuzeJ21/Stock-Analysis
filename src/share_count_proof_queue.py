"""Share-count proof queue for DCF readiness.

This read-only queue separates the recurring shares-outstanding blocker from
the broader fundamentals lane. It does not infer share counts, refresh data,
apply imports, or create valuation conclusions.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.dcf_readiness import build_dcf_readiness_frame
from src.loader import normalize_columns
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.session_source_preflight import load_session_source_preflight


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


def _universe_scope_lookup(universe: pd.DataFrame) -> dict[str, str]:
    if universe.empty or "ticker" not in universe.columns:
        return {}
    frame = universe.copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    scopes: dict[str, str] = {}
    for _, row in frame.iterrows():
        ticker = str(row.get("ticker", "")).upper().strip()
        if not ticker:
            continue
        if _truthy(row.get("in_active_universe")):
            scope = "active universe"
        elif _truthy(row.get("in_portfolio")):
            scope = "portfolio universe"
        else:
            scope = "master universe"
        scopes[ticker] = scope
    return scopes


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


def _rank(row: pd.Series, scope_lookup: dict[str, str]) -> tuple[int, int, str]:
    ticker = str(row.get("ticker", "")).upper()
    active_rank = 0 if scope_lookup.get(ticker, "master universe") == "active universe" else 1
    other_inputs_rank = 0 if _dcf_input_status(row).startswith("share-count-only") else 1
    return active_rank, other_inputs_rank, ticker


def _source_action_for_share_count(
    ticker: str,
    missing: list[str],
    session_preflight: dict[str, Any] | None,
) -> tuple[str, str]:
    default_note = (
        "SEC Companyfacts may not expose the needed share-count fact. Use a reviewed 10-K/10-Q/annual report "
        f"or trusted local row only; remaining missing fields: {', '.join(missing)}."
    )
    if not isinstance(session_preflight, dict):
        return f"make sec-stage TICKERS={ticker}", default_note
    sources = session_preflight.get("sources", {})
    if not isinstance(sources, dict):
        return f"make sec-stage TICKERS={ticker}", default_note
    sec = sources.get("sec", {})
    if not isinstance(sec, dict) or sec.get("status") != "unavailable":
        return f"make sec-stage TICKERS={ticker}", default_note

    reason = str(sec.get("reason_code") or "").strip()
    source_context = f"Session preflight marks SEC unavailable{f' ({reason})' if reason else ''}"
    ladder_available = any(
        isinstance(sources.get(key), dict) and sources[key].get("status") == "available"
        for key in ("yfinance_stage", "fmp", "alpha_vantage")
    )
    if ladder_available:
        return (
            f"make fundamentals-source-ladder TICKERS={ticker}",
            (
                f"{source_context}. Use the fundamentals source ladder or reviewed local fundamentals rows for "
                f"shares_outstanding; do not retry SEC in this session. Remaining missing fields: {', '.join(missing)}."
            ),
        )
    return (
        f"make focus-fundamentals TICKER={ticker}",
        (
            f"{source_context}. Use reviewed local fundamentals rows in data/imports/fundamentals.csv for "
            f"shares_outstanding; do not retry SEC in this session. Remaining missing fields: {', '.join(missing)}."
        ),
    )


def _reviewed_non_actionable_share_tickers(root: Path, possible_tickers: set[str]) -> set[str]:
    path = root / "data" / "reviewed_batch_proofs.csv"
    if not path.exists() or not possible_tickers:
        return set()

    reviewed: set[str] = set()
    lanes = {"share_count", "fundamentals"}
    outcomes = {"still_blocked", "skipped", "excluded"}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            lane = str(row.get("lane") or "").strip().lower()
            outcome = str(row.get("final_outcome") or "").strip().lower()
            if lane not in lanes or outcome not in outcomes:
                continue
            text = " ".join(
                str(row.get(name) or "")
                for name in ("tickers", "changed_tickers", "notes")
            ).upper()
            for token in re.findall(r"\b[A-Z][A-Z0-9.]{0,9}\b", text):
                normalized = token.replace(".", "-")
                if normalized in possible_tickers:
                    reviewed.add(normalized)
    return reviewed


def build_share_count_proof_queue(
    *,
    universe: pd.DataFrame,
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
    top_n: int = 10,
    tickers: list[str] | None = None,
    session_preflight: dict[str, Any] | None = None,
    reviewed_non_actionable_tickers: set[str] | None = None,
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
    scope_lookup = _universe_scope_lookup(universe)
    ranked = sorted((row for _, row in queue.iterrows()), key=lambda row: _rank(row, scope_lookup))
    reviewed_non_actionable_tickers = reviewed_non_actionable_tickers or set()
    rows: list[ShareCountProofRow] = []
    for row in ranked[: max(top_n, 0)]:
        ticker = str(row.get("ticker", "")).upper().strip()
        missing = _missing_fields(row.get("missing_dcf_fields"))
        row_status = _dcf_input_status(row)
        source_command, source_note = _source_action_for_share_count(ticker, missing, session_preflight)
        if ticker in reviewed_non_actionable_tickers:
            source_command = "wait for new SEC facts, keyed provider data, or reviewed manual source rows"
            source_note = (
                "Reviewed proof ledger already records this share-count/DCF source path as non-actionable; "
                "do not repeat it unless new SEC facts, keyed provider data, reviewed manual source rows, "
                f"or changed blockers appear. {source_note}"
            )
        rows.append(
            ShareCountProofRow(
                priority=len(rows) + 1,
                ticker=ticker,
                scope=scope_lookup.get(ticker, "master universe"),
                missing_field="shares_outstanding",
                dcf_input_status=row_status,
                sec_stage_command=source_command,
                manual_source_path="data/imports/fundamentals.csv",
                validation_sequence=(
                    f"make imports-validate IMPORT_TICKERS={ticker} -> "
                    f"make imports-preview IMPORT_TICKERS={ticker} -> "
                    f"make imports-apply IMPORT_TICKERS={ticker}"
                ),
                proof_after_update=f"make dcf-readiness && make readiness && make stock-report-md TICKER={ticker}",
                stop_rule=(
                    "Stop if SEC/manual source proof cannot verify shares_outstanding; keep DCF blocked and do not infer "
                    "share count from price, market cap, or placeholder rows."
                ),
                source_note=source_note,
            )
        )
    rows.sort(key=lambda row: ("reviewed proof ledger already records" in row.source_note.lower(), row.priority))
    rows = [
        ShareCountProofRow(
            priority=index,
            ticker=row.ticker,
            scope=row.scope,
            missing_field=row.missing_field,
            dcf_input_status=row.dcf_input_status,
            sec_stage_command=row.sec_stage_command,
            manual_source_path=row.manual_source_path,
            validation_sequence=row.validation_sequence,
            proof_after_update=row.proof_after_update,
            stop_rule=row.stop_rule,
            source_note=row.source_note,
        )
        for index, row in enumerate(rows, start=1)
    ]
    return rows


def build_share_count_proof_queue_from_files(
    root: Path,
    *,
    data_dir: Path | None = None,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> list[ShareCountProofRow]:
    data_path = resolve_data_dir(data_dir, root)
    universe = _read_csv(data_path / "universe.csv")
    fundamentals = _read_csv(data_path / "fundamentals.csv")
    prices = _read_csv(data_path / "prices.csv")
    dcf = build_dcf_readiness_frame(universe=universe, fundamentals=fundamentals, prices=prices)
    possible_tickers = {
        str(row.get("ticker") or "").strip().upper()
        for _, row in dcf.iterrows()
        if str(row.get("ticker") or "").strip()
    }
    reviewed_tickers = _reviewed_non_actionable_share_tickers(root, possible_tickers)
    return build_share_count_proof_queue(
        universe=universe,
        fundamentals=fundamentals,
        prices=prices,
        top_n=top_n,
        tickers=tickers,
        session_preflight=load_session_source_preflight(root),
        reviewed_non_actionable_tickers=reviewed_tickers,
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
    all_reviewed_non_actionable = all("reviewed proof ledger already records" in row.source_note.lower() for row in rows)
    if all_reviewed_non_actionable:
        lines.append(
            "Next safest action: No unreviewed executable share-count blockers are shown; "
            "do not repeat these source paths unless new SEC facts, keyed provider data, reviewed manual source rows, or changed blockers appear."
        )
    elif rows[0].sec_stage_command.startswith("make sec-stage"):
        lines.append(
            f"Next safest action: {rows[0].sec_stage_command}, then review whether SEC/manual source proof includes shares_outstanding."
        )
    else:
        lines.append(
            f"Next safest action: {rows[0].sec_stage_command}, then validate and preview any reviewed source-backed share-count row."
        )
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
    if all_reviewed_non_actionable:
        lines.append(
            "- Do not repeat reviewed share-count source paths unless new SEC facts, keyed provider data, "
            "reviewed manual source rows, or changed blockers appear."
        )
    elif any(row.sec_stage_command.startswith("make sec-stage") for row in rows):
        lines.append("- Stage SEC rows first when configured, but keep shares_outstanding blocked if SEC does not expose it.")
    else:
        lines.append("- Do not retry SEC in this session; use source-ladder output or reviewed local rows only.")
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
