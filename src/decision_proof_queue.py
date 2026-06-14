"""Build a compact proof queue for readiness-aware research decisions.

The queue is a read-only translation layer. It does not refresh data, apply
imports, route orders, or turn decision buckets into investment advice.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.loader import normalize_columns
from src.paths import format_path_context, resolve_outputs_dir, resolve_project_root
from src.reviewed_batch import FreshnessStatus, readiness_freshness_status


DEFAULT_QUEUE_CSV = Path("outputs/decision_proof_queue.csv")
DEFAULT_QUEUE_MD = Path("outputs/decision_proof_queue.md")
RESEARCH_DECISIONS_CSV = Path("outputs/research_decisions.csv")
TICKER_READINESS_CSV = Path("data/reports/ticker_readiness_report.csv")

QUEUE_COLUMNS = [
    "priority",
    "ticker",
    "decision_bucket",
    "decision_subtype",
    "primary_blocker",
    "data_confidence",
    "what_can_be_reviewed_now",
    "what_stays_locked",
    "copy_only_command",
    "proof_after_unlock",
    "source_note",
]


@dataclass(frozen=True)
class DecisionProofQueueWriteResult:
    status: str
    message: str
    freshness: FreshnessStatus
    rows: int
    output_csv: Path
    output_md: Path
    refresh_command: str


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


def _compact_reason(value: object, max_sentences: int = 2, max_chars: int = 260) -> str:
    text = _format_missing(value)
    if text == "Not available":
        return text
    text = " ".join(text.replace("`", "").split())
    sentences = [part.strip() for part in text.split(". ") if part.strip()]
    compact = ". ".join(sentences[:max_sentences])
    if compact and not compact.endswith((".", "?", "!")):
        compact += "."
    if len(compact) > max_chars:
        compact = compact[: max_chars - 1].rstrip() + "..."
    return compact


def _bool_series(frame: pd.DataFrame | None, column: str) -> pd.Series:
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(False, index=frame.index if frame is not None else None)
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def _stock_report_md_command(ticker: object, fallback: str = "TICKER") -> str:
    return f"make stock-report-md TICKER={_format_missing(ticker, fallback).upper()}"


def _peer_mapping_unlock_action(ticker: object) -> str:
    symbol = _format_missing(ticker, "TICKER").upper()
    return (
        f"Add at least 2 source-backed peer mappings for {symbol} in data/imports/peers.csv; "
        "then run make imports-validate, make imports-preview, and make imports-apply."
    )


def _purpose_unlock_command(ticker: object, primary_blocker: object, exact_command: object) -> str:
    symbol = _format_missing(ticker, "").upper()
    blocker = _format_missing(primary_blocker, "").lower()
    if not symbol:
        return _format_missing(exact_command, "make project-status")
    if blocker == "price":
        return f"make focus-price TICKER={symbol}"
    if blocker in {"fundamentals", "dcf"}:
        return f"make focus-fundamentals TICKER={symbol}"
    if blocker in {"peer", "peers"}:
        return f"make focus-peers TICKER={symbol}"
    if blocker in {"earnings", "analyst_estimates", "analyst estimates", "optional_context"}:
        return "make templates"
    return _format_missing(exact_command, _stock_report_md_command(symbol))


def _decision_next_action_summary(row: pd.Series) -> str:
    ticker = _format_missing(row.get("ticker"), "Ticker")
    blocker = _format_missing(row.get("primary_blocker"), "").lower().replace(" ", "_")
    asset_type = _format_missing(row.get("asset_type"), row.get("asset_type_readiness", "")).lower()
    if asset_type in {"etf", "index_proxy", "fund"}:
        return f"Review {ticker} as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded."
    dcf_ready = str(row.get("dcf_ready", "")).strip().lower() in {"true", "1", "yes", "y"}
    peer_ready = str(row.get("peer_ready", "")).strip().lower() in {"true", "1", "yes", "y"}
    stale_peer_action = "peer mappings and peer metrics" in _format_missing(row.get("next_best_action"), "").lower()
    if blocker in {"peer", "peers"} and (dcf_ready or not peer_ready or stale_peer_action):
        return _peer_mapping_unlock_action(ticker)
    if blocker == "fundamentals":
        return f"Import trusted fundamentals for {ticker}; use SEC staging workflow when configured or data/imports/fundamentals.csv, then validate and preview."
    if blocker == "price":
        return "Refresh a capped price worklist before deeper analysis; start with make price-refresh-loop DRY_RUN=1, then review the planned batches."
    if blocker in {"earnings", "analyst_estimates", "optional_context"}:
        return f"Optional context for {ticker} stays unavailable until trusted local CSV rows are staged, validated, previewed, and applied."
    return _compact_reason(row.get("next_best_action"), max_sentences=1, max_chars=180)


def _decision_next_action_proof(row: pd.Series) -> str:
    ticker = _format_missing(row.get("ticker"), "").upper()
    blocker = _format_missing(row.get("primary_blocker"), "").lower().replace(" ", "_")
    asset_type = _format_missing(row.get("asset_type"), row.get("asset_type_readiness", "")).lower()
    report_command = _stock_report_md_command(ticker) if ticker else "make project-status"
    if asset_type in {"etf", "index_proxy", "fund"}:
        return f"Proof after review: run `{report_command}` and confirm operating-company DCF is excluded, not failed."
    if blocker == "price":
        return f"Proof after data changes: run `make price-coverage TOP_N=25`, `make readiness`, then `{report_command}`."
    if blocker in {"fundamentals", "dcf"}:
        return f"Proof after data changes: run `make dcf-readiness`, `make readiness`, then `{report_command}`."
    if blocker in {"peer", "peers"}:
        return f"Proof after data changes: run `make peer-mapping-queue TOP_N=25`, `make readiness`, then `{report_command}`."
    if blocker in {"earnings", "analyst_estimates", "optional_context"}:
        return f"Proof after data changes: run `make optional-context-readiness`, `make readiness`, then `{report_command}`."
    return f"Proof before interpretation: run `make readiness`, then `{report_command}`."


def build_decision_proof_queue_frame(
    decisions_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None = None,
    *,
    limit: int = 12,
) -> pd.DataFrame:
    if decisions_frame is None or decisions_frame.empty or "ticker" not in decisions_frame.columns:
        return pd.DataFrame(columns=QUEUE_COLUMNS)

    frame = decisions_frame.copy()
    frame["ticker"] = frame["ticker"].fillna("").astype(str).str.upper().str.strip()
    frame = frame.loc[frame["ticker"].ne("")].copy()
    if frame.empty:
        return pd.DataFrame(columns=QUEUE_COLUMNS)

    if (
        ticker_readiness_frame is not None
        and not ticker_readiness_frame.empty
        and "ticker" in ticker_readiness_frame.columns
    ):
        readiness_columns = [
            column
            for column in ["ticker", "in_active_universe", "dcf_ready", "peer_ready", "asset_type", "updated_at"]
            if column in ticker_readiness_frame.columns
        ]
        readiness = ticker_readiness_frame[readiness_columns].copy()
        readiness["ticker"] = readiness["ticker"].fillna("").astype(str).str.upper().str.strip()
        frame = frame.merge(readiness.drop_duplicates("ticker"), on="ticker", how="left", suffixes=("", "_readiness"))

    bucket_rank = (
        frame.get("decision_bucket", pd.Series("", index=frame.index))
        .fillna("")
        .astype(str)
        .map({"Research Now": 0, "Blocked by Data": 1, "Monitor": 2, "Excluded": 3})
        .fillna(4)
        .astype(int)
    )
    active_rank = (~_bool_series(frame, "in_active_universe")).astype(int)
    blocker_rank = (
        frame.get("primary_blocker", pd.Series("", index=frame.index))
        .fillna("")
        .astype(str)
        .str.lower()
        .map({"peers": 0, "peer": 0, "fundamentals": 1, "dcf": 1, "price": 2, "earnings": 3, "analyst_estimates": 3})
        .fillna(4)
        .astype(int)
    )
    frame = frame.assign(_bucket_rank=bucket_rank, _active_rank=active_rank, _blocker_rank=blocker_rank)
    frame = frame.sort_values(["_bucket_rank", "_active_rank", "_blocker_rank", "ticker"], kind="stable")

    rows: list[dict[str, object]] = []
    for _, row in frame.head(max(limit, 0)).iterrows():
        ticker = _format_missing(row.get("ticker"), "TICKER").upper()
        asset_type = _format_missing(row.get("asset_type"), row.get("asset_type_readiness", "")).lower()
        bucket = _format_missing(row.get("decision_bucket"), "Not available")
        if asset_type in {"etf", "index_proxy", "fund"} or "monitor" in bucket.lower():
            supported = "Monitor market, theme, liquidity, risk, or correlation context when local price data is ready."
            locked = "Operating-company DCF and peer-relative company valuation are excluded, not failed."
        else:
            supported = _format_missing(
                row.get("supported_analysis") or row.get("supporting_features"),
                "Review only the sections whose readiness gates are already marked ready.",
            )
            locked = _format_missing(
                row.get("unsupported_analysis") or row.get("blocked_features") or row.get("missing_data"),
                "No blocked section is listed, but conclusions still depend on source readiness and assumptions.",
            )
        action = _decision_next_action_summary(row)
        command = (
            _stock_report_md_command(ticker)
            if asset_type in {"etf", "index_proxy", "fund"} or "monitor" in bucket.lower()
            else _purpose_unlock_command(ticker, row.get("primary_blocker"), action)
        )
        rows.append(
            {
                "priority": len(rows) + 1,
                "ticker": ticker,
                "decision_bucket": bucket,
                "decision_subtype": _format_missing(row.get("decision_subtype"), "Not available"),
                "primary_blocker": _format_missing(row.get("primary_blocker"), "none"),
                "data_confidence": _format_missing(row.get("data_confidence"), "Not available"),
                "what_can_be_reviewed_now": _compact_reason(supported, max_sentences=2, max_chars=220),
                "what_stays_locked": _compact_reason(locked, max_sentences=2, max_chars=220),
                "copy_only_command": command,
                "proof_after_unlock": _decision_next_action_proof(row),
                "source_note": (
                    f"Local readiness updated {_format_missing(row.get('updated_at'), 'not available')}; "
                    "decision labels are review states, not recommendations."
                ),
            }
        )
    return pd.DataFrame(rows, columns=QUEUE_COLUMNS)


def build_decision_proof_queue_cards(queue_frame: pd.DataFrame | None) -> list[dict[str, object]]:
    if queue_frame is None or queue_frame.empty:
        return [
            {
                "kicker": "DECISION PROOF",
                "title": "No proof queue yet",
                "body": "Run make research-decisions and make readiness before reading decision proof rows.",
                "badges": ["refresh first", "copy only"],
                "command": "make research-decisions",
            }
        ]
    frame = queue_frame.copy()
    top = frame.iloc[0]
    bucket_counts = frame.get("decision_bucket", pd.Series(dtype=object)).fillna("Unknown").astype(str).value_counts()
    locked_text = " ".join(frame.get("what_stays_locked", pd.Series(dtype=object)).fillna("").astype(str).str.lower().tolist())
    peer_limited = locked_text.count("peer")
    optional_limited = locked_text.count("earnings") + locked_text.count("estimate")
    return [
        {
            "kicker": "DECISION PROOF",
            "title": f"{len(frame)} row(s) translated",
            "body": ", ".join(f"{bucket}: {int(count)}" for bucket, count in bucket_counts.head(3).items())
            + ". Each row states what can be reviewed now, what stays locked, and what proves an unlock.",
            "badges": ["plain English", "row-limited"],
            "command": "make decision-proof-queue TOP_N=12",
        },
        {
            "kicker": "TOP PROOF ROW",
            "title": f"{_format_missing(top.get('ticker'), 'Ticker')}: {_format_missing(top.get('decision_subtype'), 'Decision')}",
            "body": (
                f"Review now: {_compact_reason(top.get('what_can_be_reviewed_now'), max_sentences=1, max_chars=140)} "
                f"Locked: {_compact_reason(top.get('what_stays_locked'), max_sentences=1, max_chars=140)}"
            ),
            "badges": [_format_missing(top.get("primary_blocker"), "blocker"), _format_missing(top.get("data_confidence"), "confidence")],
            "command": _format_missing(top.get("copy_only_command"), "make project-status"),
        },
        {
            "kicker": "WITHHELD CONTEXT",
            "title": f"Peer mentions: {peer_limited} / optional mentions: {optional_limited}",
            "body": "Withheld context remains visible so peer comparison, earnings, estimates, or company-valuation exclusions do not look like hidden conclusions.",
            "badges": ["data-honest", "no fabrication"],
            "command": "make readiness",
        },
    ]


def build_decision_proof_queue_drawer_cards(
    queue_frame: pd.DataFrame | None,
    freshness: FreshnessStatus,
) -> list[dict[str, object]]:
    status_command = freshness.refresh_command if freshness.status in {"missing", "stale"} else "make decision-proof-queue TOP_N=12"
    status_badges = (
        [freshness.status, "refresh first"]
        if freshness.status in {"missing", "stale"}
        else [freshness.status, "review state only"]
    )
    cards: list[dict[str, object]] = [
        {
            "kicker": "QUEUE STATUS",
            "title": "Refresh before queue" if freshness.status in {"missing", "stale"} else "Decision proof queue ready",
            "body": (
                f"{freshness.message} "
                "Decision labels are review states for readiness work; they are not recommendations, rankings, or execution instructions."
            ),
            "badges": status_badges,
            "command": status_command,
        }
    ]
    if freshness.status in {"missing", "stale"}:
        cards.append(
            {
                "kicker": "NEXT SAFE ACTION",
                "title": "Rebuild the stale artifact first",
                "body": (
                    "Do not read old decision rows as current proof. Rebuild the named artifact, then reopen Data Health before copying queue commands."
                ),
                "badges": ["stale gate", "copy-only"],
                "command": status_command,
            }
        )
        cards.append(
            {
                "kicker": "FINISH THIS QUEUE",
                "title": "Three-step proof refresh",
                "body": (
                    f"1. Run `{status_command}`. 2. Run `make decision-proof-queue TOP_N=12`. "
                    "3. Reopen Data Health and read the top proof row only after freshness is current. "
                    "Until then, stale decision rows stay blocked proof, not weak research conclusions."
                ),
                "badges": ["checklist", "stale rows blocked"],
                "command": status_command,
            }
        )
        return cards
    if queue_frame is None or queue_frame.empty:
        cards.append(
            {
                "kicker": "TOP PROOF ROW",
                "title": "No queue rows available",
                "body": "Run make research-decisions after readiness is current, then rebuild the proof queue.",
                "badges": ["no rows", "refresh first"],
                "command": "make research-decisions",
            }
        )
        return cards

    top = queue_frame.iloc[0]
    ticker = _format_missing(top.get("ticker"), "Ticker")
    cards.extend(
        [
            {
                "kicker": "TOP PROOF ROW",
                "title": f"{ticker}: {_format_missing(top.get('decision_subtype'), 'Decision')}",
                "body": (
                    f"Main blocker: {_format_missing(top.get('primary_blocker'), 'none')}. "
                    f"Data confidence: {_format_missing(top.get('data_confidence'), 'not available')}."
                ),
                "badges": [_format_missing(top.get("decision_bucket"), "review state"), "not advice"],
                "command": _format_missing(top.get("copy_only_command"), "make project-status"),
            },
            {
                "kicker": "REVIEW NOW",
                "title": "What can be reviewed",
                "body": _compact_reason(top.get("what_can_be_reviewed_now"), max_sentences=2, max_chars=240),
                "badges": ["ready inputs only", "no inference"],
                "command": "",
            },
            {
                "kicker": "LOCKED",
                "title": "What stays locked",
                "body": _compact_reason(top.get("what_stays_locked"), max_sentences=2, max_chars=240),
                "badges": ["blocked visible", "no fabrication"],
                "command": "",
            },
            {
                "kicker": "PROOF AFTER UNLOCK",
                "title": "Verify before interpreting",
                "body": _compact_reason(top.get("proof_after_unlock"), max_sentences=2, max_chars=260),
                "badges": ["prove after", "copy-only"],
                "command": _format_missing(top.get("copy_only_command"), "make project-status"),
            },
        ]
    )
    return cards


def render_decision_proof_queue_guidance(cards: list[dict[str, object]]) -> str:
    lines = ["Decision proof queue guidance:"]
    for card in cards:
        kicker = _format_missing(card.get("kicker"), "QUEUE")
        title = _format_missing(card.get("title"), "Next step")
        body = _format_missing(card.get("body"), "")
        body = " ".join(body.replace("`", "").split())
        if len(body) > 420:
            body = body[:419].rstrip() + "..."
        command = _format_missing(card.get("command"), "")
        lines.append(f"- {kicker}: {title}")
        if body:
            lines.append(f"  {body}")
        if command:
            lines.append(f"  Copy-only command: {command}")
    return "\n".join(lines)


def _read_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame.columns = normalize_columns(list(frame.columns))
    if "ticker" in frame.columns:
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    return frame


def _artifact_gate(root: Path) -> tuple[FreshnessStatus, str]:
    decision_path = root / RESEARCH_DECISIONS_CSV
    readiness_path = root / TICKER_READINESS_CSV
    if not decision_path.exists():
        return FreshnessStatus("missing", f"Missing {RESEARCH_DECISIONS_CSV}. Run make research-decisions first."), "make research-decisions"
    if not readiness_path.exists():
        return FreshnessStatus("missing", f"Missing {TICKER_READINESS_CSV}. Run make readiness first."), "make readiness"
    freshness = readiness_freshness_status(root)
    if freshness.status != "current":
        return freshness, freshness.refresh_command
    if readiness_path.stat().st_mtime > decision_path.stat().st_mtime:
        return (
            FreshnessStatus(
                "stale",
                "Research decision output is older than the current ticker readiness report. Run make research-decisions before building the proof queue.",
                "make research-decisions",
            ),
            "make research-decisions",
        )
    return freshness, "make decision-proof-queue"


def decision_proof_queue_artifact_status(base_dir: Path | str | None = None) -> FreshnessStatus:
    root = resolve_project_root(base_dir)
    freshness, _refresh_command = _artifact_gate(root)
    return freshness


def _write_markdown(path: Path, queue: pd.DataFrame, freshness: FreshnessStatus) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decision Proof Queue",
        "",
        "Research-only queue. Decision labels are review states, not recommendations.",
        "",
        f"- Freshness: {freshness.status}",
        f"- Source note: {freshness.message}",
        "",
        "| Priority | Ticker | Review detail | Main blocker | Copy-only command | Proof after unlock |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in queue.iterrows():
        lines.append(
            "| "
            + " | ".join(
                str(row.get(column, "")).replace("|", "/")
                for column in [
                    "priority",
                    "ticker",
                    "decision_subtype",
                    "primary_blocker",
                    "copy_only_command",
                    "proof_after_unlock",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Guardrails: no broker integration, no auto-trading, no order routing, no direct transaction instructions, and no fabricated data.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decision_proof_queue(
    base_dir: Path | str | None = None,
    *,
    output_csv: Path | str | None = None,
    output_md: Path | str | None = None,
    limit: int = 12,
) -> DecisionProofQueueWriteResult:
    root = resolve_project_root(base_dir)
    freshness, refresh_command = _artifact_gate(root)
    csv_path = root / (Path(output_csv) if output_csv else DEFAULT_QUEUE_CSV)
    md_path = root / (Path(output_md) if output_md else DEFAULT_QUEUE_MD)
    if freshness.status != "current":
        return DecisionProofQueueWriteResult(
            status=freshness.status,
            message=freshness.message,
            freshness=freshness,
            rows=0,
            output_csv=csv_path,
            output_md=md_path,
            refresh_command=refresh_command,
        )
    decisions = _read_frame(root / RESEARCH_DECISIONS_CSV)
    readiness = _read_frame(root / TICKER_READINESS_CSV)
    queue = build_decision_proof_queue_frame(decisions, readiness, limit=limit)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(csv_path, index=False)
    _write_markdown(md_path, queue, freshness)
    return DecisionProofQueueWriteResult(
        status="written",
        message=f"Wrote {len(queue)} decision proof queue row(s).",
        freshness=freshness,
        rows=len(queue),
        output_csv=csv_path,
        output_md=md_path,
        refresh_command=refresh_command,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a compact read-only decision proof queue.")
    parser.add_argument("--project-root", help="Project root. Defaults to this repository.")
    parser.add_argument("--top-n", type=int, default=12, help="Maximum queue rows to write.")
    parser.add_argument("--output", default=str(DEFAULT_QUEUE_CSV), help="CSV output path relative to the project root.")
    parser.add_argument("--md-output", default=str(DEFAULT_QUEUE_MD), help="Markdown output path relative to the project root.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable status.")
    args = parser.parse_args()

    root = resolve_project_root(args.project_root)
    output_dir = resolve_outputs_dir(None, root)
    result = write_decision_proof_queue(root, output_csv=args.output, output_md=args.md_output, limit=args.top_n)
    payload = {
        "status": result.status,
        "message": result.message,
        "rows": result.rows,
        "output_csv": str(result.output_csv),
        "output_md": str(result.output_md),
        "freshness_status": result.freshness.status,
        "refresh_command": result.refresh_command,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_path_context(root, root / "data", output_dir))
        for key, value in payload.items():
            print(f"{key}: {value}")
        if result.status != "written":
            cards = build_decision_proof_queue_drawer_cards(pd.DataFrame(), result.freshness)
            print(render_decision_proof_queue_guidance(cards))
    if result.status != "written":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
