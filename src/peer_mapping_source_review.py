"""Build a source-review packet for manual peer mapping rows.

This module creates review scaffolds only. It does not infer peers, import rows,
apply CSV changes, connect to brokers, or provide investment advice.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable

from src.reviewed_batch import FreshnessStatus, readiness_freshness_status


DEFAULT_MD_OUTPUT = Path("outputs/peer_mapping_source_review.md")
DEFAULT_CSV_OUTPUT = Path("outputs/peer_mapping_source_review.csv")
PEER_READINESS_PATH = Path("data/reports/peer_readiness_report.csv")
DEFAULT_MIN_PEERS = 2
SOURCE_REVIEW_COLUMNS = (
    "ticker",
    "mapping_slot",
    "proposed_peer_ticker",
    "peer_group",
    "sector",
    "industry",
    "source",
    "as_of_date",
    "relationship_rationale",
    "reviewer",
    "review_date",
    "source_proof_status",
    "import_row_ready",
    "target_file",
    "focus_command",
    "validation_sequence",
    "do_not_proceed_if",
)
REQUIRED_REVIEW_FIELDS = (
    "proposed_peer_ticker",
    "peer_group",
    "source",
    "as_of_date",
    "relationship_rationale",
    "reviewer",
    "review_date",
)
IMPORT_ROW_COLUMNS = ("ticker", "peer_ticker", "peer_group", "sector", "industry", "source", "as_of_date")
READY_SOURCE_PROOF_STATUSES = {"reviewed", "supported", "source_backed", "source-backed"}
READY_IMPORT_VALUES = {"yes", "true", "ready", "1"}


@dataclass(frozen=True)
class PeerMappingReviewRow:
    ticker: str
    mapping_slot: str
    proposed_peer_ticker: str
    peer_group: str
    sector: str
    industry: str
    source: str
    as_of_date: str
    relationship_rationale: str
    reviewer: str
    review_date: str
    source_proof_status: str
    import_row_ready: str
    target_file: str
    focus_command: str
    validation_sequence: str
    do_not_proceed_if: str


@dataclass(frozen=True)
class PeerMappingSourceReviewPacket:
    freshness: FreshnessStatus
    top_n: int
    tickers: tuple[str, ...]
    rows: tuple[PeerMappingReviewRow, ...]


@dataclass(frozen=True)
class PeerMappingReviewCompletion:
    status: str
    missing_fields: tuple[str, ...]
    next_safe_action: str
    import_row_scaffold: str


@dataclass(frozen=True)
class PeerMappingImportPreview:
    status: str
    csv_header: str
    csv_row: str
    target_file: str
    validation_command: str
    apply_boundary: str
    post_apply_proof: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _split_tickers(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    raw = value.split(",") if isinstance(value, str) else list(value)
    return tuple(dict.fromkeys(str(item).strip().upper() for item in raw if str(item).strip()))


def _missing_mapping(row: dict[str, str]) -> bool:
    blocker = str(row.get("peer_blocker_type") or "").strip().lower()
    status = str(row.get("mapping_status") or "").strip().lower()
    reason = str(row.get("missing_peer_reason") or "").strip().lower()
    return blocker == "missing_peer_mapping" or status == "missing_mapping" or "source-backed peer mappings" in reason


def _is_placeholder(value: object) -> bool:
    text = str(value or "").strip()
    return not text or (text.startswith("<") and text.endswith(">"))


def _csv_row(values: Iterable[object]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="")
    writer.writerow([str(value or "").strip() for value in values])
    return buffer.getvalue()


def peer_mapping_import_csv_header() -> str:
    return _csv_row(IMPORT_ROW_COLUMNS)


def peer_mapping_source_review_missing_fields(row: PeerMappingReviewRow) -> tuple[str, ...]:
    missing = [field for field in REQUIRED_REVIEW_FIELDS if _is_placeholder(getattr(row, field))]
    proof_status = str(row.source_proof_status or "").strip().lower()
    if proof_status not in READY_SOURCE_PROOF_STATUSES:
        missing.append("source_proof_status")
    import_ready = str(row.import_row_ready or "").strip().lower()
    if import_ready not in READY_IMPORT_VALUES:
        missing.append("import_row_ready")
    return tuple(missing)


def peer_mapping_import_row_scaffold(row: PeerMappingReviewRow) -> str:
    missing = peer_mapping_source_review_missing_fields(row)
    if missing:
        return f"blocked until reviewed fields are filled: {', '.join(missing)}"
    return _csv_row(
        (
            row.ticker,
            row.proposed_peer_ticker,
            row.peer_group,
            "" if _is_placeholder(row.sector) else row.sector,
            "" if _is_placeholder(row.industry) else row.industry,
            row.source,
            row.as_of_date,
        )
    )


def peer_mapping_source_review_completion(row: PeerMappingReviewRow, freshness: FreshnessStatus) -> PeerMappingReviewCompletion:
    if freshness.status in {"missing", "stale"}:
        return PeerMappingReviewCompletion(
            status="blocked_by_freshness",
            missing_fields=("freshness",),
            next_safe_action=f"Run `{freshness.refresh_command}` before using this peer source-review row.",
            import_row_scaffold="blocked until readiness artifacts are current",
        )
    missing = peer_mapping_source_review_missing_fields(row)
    if missing:
        return PeerMappingReviewCompletion(
            status="needs_field_fills",
            missing_fields=missing,
            next_safe_action=f"Fill {', '.join(missing)} for {row.ticker} / {row.mapping_slot}; keep peer valuation locked.",
            import_row_scaffold=peer_mapping_import_row_scaffold(row),
        )
    return PeerMappingReviewCompletion(
        status="ready_for_import_row_scaffold",
        missing_fields=(),
        next_safe_action="Review the scaffolded import row, then run validate and preview before any apply step.",
        import_row_scaffold=peer_mapping_import_row_scaffold(row),
    )


def peer_mapping_import_preview(row: PeerMappingReviewRow, freshness: FreshnessStatus) -> PeerMappingImportPreview:
    completion = peer_mapping_source_review_completion(row, freshness)
    ready = completion.status == "ready_for_import_row_scaffold"
    csv_row = completion.import_row_scaffold if ready else ""
    status = "ready_for_validate_preview" if ready else completion.status
    apply_boundary = (
        "Run make imports-apply only after imports-preview and rejected-row reports are reviewed."
        if ready
        else "Do not edit or apply data/imports/peers.csv until the source-review row is completion-ready."
    )
    return PeerMappingImportPreview(
        status=status,
        csv_header=peer_mapping_import_csv_header(),
        csv_row=csv_row,
        target_file=row.target_file,
        validation_command="make imports-validate && make imports-preview",
        apply_boundary=apply_boundary,
        post_apply_proof="make readiness && make peer-mapping-queue TOP_N=25 && make reviewed-batch-compare LANE=peers ...",
    )


def _candidate_tickers(root: Path, top_n: int, tickers: tuple[str, ...]) -> tuple[str, ...]:
    if tickers:
        return tickers[: max(top_n, 0)]
    rows = _read_csv(root / PEER_READINESS_PATH)
    candidates: list[str] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker and ticker not in candidates and _missing_mapping(row):
            candidates.append(ticker)
        if len(candidates) >= top_n:
            break
    return tuple(candidates)


def build_peer_mapping_source_review_packet(
    root: Path | str = ".",
    *,
    top_n: int = 10,
    tickers: str | Iterable[str] | None = None,
) -> PeerMappingSourceReviewPacket:
    root = Path(root)
    selected_tickers = _split_tickers(tickers)
    freshness = readiness_freshness_status(root)
    candidates = _candidate_tickers(root, top_n, selected_tickers)
    review_rows: list[PeerMappingReviewRow] = []
    for ticker in candidates:
        for slot in range(1, DEFAULT_MIN_PEERS + 1):
            review_rows.append(
                PeerMappingReviewRow(
                    ticker=ticker,
                    mapping_slot=f"peer_{slot}",
                    proposed_peer_ticker="<source-backed peer ticker>",
                    peer_group="<reviewed peer group>",
                    sector="<reviewed sector>",
                    industry="<reviewed industry>",
                    source="<durable URL or local document reference>",
                    as_of_date="<YYYY-MM-DD>",
                    relationship_rationale="<why this source supports the peer relationship>",
                    reviewer="<reviewer>",
                    review_date="<YYYY-MM-DD>",
                    source_proof_status="needs_review",
                    import_row_ready="no",
                    target_file="data/imports/peers.csv",
                    focus_command=f"make focus-peers TICKER={ticker}",
                    validation_sequence="make templates -> fill reviewed peer rows -> make imports-validate -> make imports-preview -> make imports-apply -> make readiness -> make peer-mapping-queue TOP_N=25",
                    do_not_proceed_if=(
                        "source does not name the peer relationship or comparable business context; "
                        "source is only sector/theme similarity; URL/document reference is missing; "
                        "review date or reviewer is missing; proposed peer ticker is not verified"
                    ),
                )
            )
    return PeerMappingSourceReviewPacket(
        freshness=freshness,
        top_n=top_n,
        tickers=candidates,
        rows=tuple(review_rows),
    )


def render_peer_mapping_source_review_markdown(packet: PeerMappingSourceReviewPacket) -> str:
    status = "blocked_by_freshness" if packet.freshness.status in {"missing", "stale"} else "ready_for_review"
    lines = [
        "# Peer Mapping Source Review Packet",
        "",
        "Research-only: this packet prepares manual source review for peer mappings. It is not investment advice, does not connect to brokers, does not route orders, and does not provide direct buy/sell instructions.",
        "",
        f"- Packet status: `{status}`",
        f"- Freshness status: `{packet.freshness.status}`",
        f"- Freshness note: {packet.freshness.message}",
        f"- Refresh command if blocked: `{packet.freshness.refresh_command}`",
        f"- Ticker scope: `{', '.join(packet.tickers) if packet.tickers else 'none'}`",
        f"- Review rows: `{len(packet.rows)}`",
        "",
        "## Source Proof Contract",
        "",
        "- Import schema: `ticker, peer_ticker, peer_group, sector, industry, source, as_of_date`.",
        "- Required review fields before import: proposed peer ticker, peer group, source, as-of date, relationship rationale, reviewer, and review date.",
        "- Accepted proof: a durable URL or local document that names the peer relationship or supports comparable business context.",
        "- Rejected shortcuts: memory, popularity, sector/theme similarity alone, row-count convenience, or placeholders.",
        "- Validation path: `make imports-validate -> make imports-preview -> make imports-apply` only after source review.",
        "- Post-run proof: `make readiness -> make peer-mapping-queue TOP_N=25 -> make reviewed-batch-compare LANE=peers ...`.",
        "- Import row scaffold appears only after source proof status and required review fields are filled.",
        "",
        "## Review Rows",
        "",
    ]
    if not packet.rows:
        lines.extend(
            [
                "No peer mapping source-review rows were generated. Run `make readiness` and `make peer-mapping-queue TOP_N=25`, then retry.",
                "",
            ]
        )
    for row in packet.rows:
        completion = peer_mapping_source_review_completion(row, packet.freshness)
        import_preview = peer_mapping_import_preview(row, packet.freshness)
        lines.extend(
            [
                f"### {row.ticker} / {row.mapping_slot}",
                "",
                f"- Completion status: `{completion.status}`",
                f"- Missing fields: `{', '.join(completion.missing_fields) if completion.missing_fields else 'none'}`",
                f"- Next safe action: {completion.next_safe_action}",
                f"- Import row scaffold: `{completion.import_row_scaffold}`",
                f"- Import preview status: `{import_preview.status}`",
                f"- CSV header: `{import_preview.csv_header}`",
                f"- CSV row: `{import_preview.csv_row or 'blocked until completion-ready'}`",
                f"- Validate / preview command: `{import_preview.validation_command}`",
                f"- Apply boundary: {import_preview.apply_boundary}",
                f"- Post-apply proof: `{import_preview.post_apply_proof}`",
                f"- Proposed peer ticker: `{row.proposed_peer_ticker}`",
                f"- Peer group: `{row.peer_group}`",
                f"- Source: `{row.source}`",
                f"- Relationship rationale: `{row.relationship_rationale}`",
                f"- Reviewer / review date: `{row.reviewer}` / `{row.review_date}`",
                f"- Target file after review: `{row.target_file}`",
                f"- Focus command: `{row.focus_command}`",
                f"- Validation sequence: `{row.validation_sequence}`",
                f"- Do not proceed if: {row.do_not_proceed_if}",
                "",
            ]
        )
    lines.extend(
        [
            "## Guardrails",
            "",
            "- Do not fabricate peer mappings or peer valuation inputs.",
            "- Do not treat sector or industry fallback as trusted peer valuation.",
            "- Do not stage broad generated CSV/JSON churn unless it is intentionally reviewed evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_peer_mapping_source_review_preview(packet: PeerMappingSourceReviewPacket) -> str:
    status = "blocked_by_freshness" if packet.freshness.status in {"missing", "stale"} else "ready_for_review"
    lines = [
        "Peer mapping source review preview",
        "Research-only: review peer mapping source proof before editing import rows; no broker integration, no auto-trading, and no direct buy/sell instructions.",
        f"status: preview",
        f"packet_status: {status}",
        f"freshness_status: {packet.freshness.status}",
        f"rows: {len(packet.rows)}",
        f"tickers: {','.join(packet.tickers) if packet.tickers else '-'}",
        "message: Previewed peer mapping source-review packet; no Markdown or CSV artifacts were written.",
    ]
    if packet.rows:
        row = packet.rows[0]
        completion = peer_mapping_source_review_completion(row, packet.freshness)
        import_preview = peer_mapping_import_preview(row, packet.freshness)
        lines.extend(
            [
                "top_review_row:",
                f"- ticker: {row.ticker}",
                f"- mapping_slot: {row.mapping_slot}",
                f"- completion_status: {completion.status}",
                f"- missing_fields: {','.join(completion.missing_fields) if completion.missing_fields else '-'}",
                f"- import_preview_status: {import_preview.status}",
                f"- csv_header: {import_preview.csv_header}",
                f"- csv_row: {import_preview.csv_row or '-'}",
                f"- target_file: {row.target_file}",
                f"- focus_command: {row.focus_command}",
                f"- do_not_proceed_if: {row.do_not_proceed_if}",
            ]
        )
    return "\n".join(lines) + "\n"


def write_peer_mapping_source_review_packet(
    packet: PeerMappingSourceReviewPacket,
    *,
    md_output: Path = DEFAULT_MD_OUTPUT,
    csv_output: Path = DEFAULT_CSV_OUTPUT,
) -> None:
    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(render_peer_mapping_source_review_markdown(packet), encoding="utf-8")
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_REVIEW_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in packet.rows:
            writer.writerow({field: getattr(row, field) for field in SOURCE_REVIEW_COLUMNS})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or write a peer mapping source-review packet.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--tickers", default="", help="Optional comma-separated ticker scope.")
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--csv-output", default=str(DEFAULT_CSV_OUTPUT))
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing Markdown or CSV artifacts.")
    parser.add_argument("--print", action="store_true", help="Print packet Markdown after writing outputs, or during dry run.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_peer_mapping_source_review_packet(args.root, top_n=args.top_n, tickers=args.tickers)
    if args.dry_run:
        print(render_peer_mapping_source_review_markdown(packet) if args.print else render_peer_mapping_source_review_preview(packet))
        return 0
    write_peer_mapping_source_review_packet(packet, md_output=Path(args.md_output), csv_output=Path(args.csv_output))
    if args.print:
        print(render_peer_mapping_source_review_markdown(packet))
    else:
        print(f"Wrote {args.md_output}")
        print(f"Wrote {args.csv_output}")
        print(f"Freshness status: {packet.freshness.status} - {packet.freshness.message}")
        print(f"Review rows: {len(packet.rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
