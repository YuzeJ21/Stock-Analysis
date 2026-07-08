"""Build a source-review packet for manual peer mapping rows.

This module creates review scaffolds only. It does not infer peers, import rows,
apply CSV changes, connect to brokers, or provide investment advice.
"""

from __future__ import annotations

import argparse
import csv
import shlex
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable

from src.reviewed_batch import FreshnessStatus, readiness_freshness_status


DEFAULT_MD_OUTPUT = Path("outputs/peer_mapping_source_review.md")
DEFAULT_CSV_OUTPUT = Path("outputs/peer_mapping_source_review.csv")
PROJECT_STATUS_TOP_ACTIONS_PATH = Path("outputs/project_status_top_actions.csv")
PEER_READINESS_PATH = Path("data/reports/peer_readiness_report.csv")
CANONICAL_PEERS_PATH = Path("data/peers.csv")
IMPORT_PEERS_PATH = Path("data/imports/peers.csv")
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
    "candidate_context_state",
    "candidate_context_source",
    "candidate_context_count",
    "candidate_context_peers",
    "candidate_context_note",
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
    candidate_context_state: str = "not_loaded"
    candidate_context_source: str = "not_loaded"
    candidate_context_count: str = "0"
    candidate_context_peers: str = ""
    candidate_context_note: str = "Candidate context was not loaded for this source-review row."


@dataclass(frozen=True)
class PeerMappingSourceReviewPacket:
    freshness: FreshnessStatus
    top_n: int
    tickers: tuple[str, ...]
    rows: tuple[PeerMappingReviewRow, ...]
    selection_source: str = "not_loaded"


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


@dataclass(frozen=True)
class PeerMappingWriteBackGuard:
    status: str
    blocking_reasons: tuple[str, ...]
    duplicate_sources: tuple[str, ...]
    proof_record_status: str
    proof_record_missing_fields: tuple[str, ...]
    csv_header: str
    csv_row: str
    target_file: str
    validation_command: str
    apply_boundary: str
    post_apply_proof: str
    proof_record_command: str
    proof_record_boundary: str


@dataclass(frozen=True)
class PeerMappingPacketDecision:
    status: str
    answer: str
    next_safe_action: str
    candidate_context_state: str
    trusted_peer_proof_state: str
    boundary: str


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


def _shell_assignment(name: str, value: object) -> str:
    return f"{name}={shlex.quote(str(value or '').strip())}"


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
    validation_command = "make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>"
    apply_boundary = (
        "Run make imports-apply IMPORT_TICKERS=<ticker> only after imports-preview and rejected-row reports are reviewed."
        if ready
        else "Do not edit or apply data/imports/peers.csv until the source-review row is completion-ready."
    )
    return PeerMappingImportPreview(
        status=status,
        csv_header=peer_mapping_import_csv_header(),
        csv_row=csv_row,
        target_file=row.target_file,
        validation_command=validation_command,
        apply_boundary=apply_boundary,
        post_apply_proof="make readiness && make peer-mapping-queue TOP_N=25 && make reviewed-batch-compare LANE=peers ...",
    )


def peer_mapping_packet_decision(packet: PeerMappingSourceReviewPacket) -> PeerMappingPacketDecision:
    if packet.freshness.status in {"missing", "stale"}:
        return PeerMappingPacketDecision(
            status="blocked_by_freshness",
            answer=f"Peer source-review rows are blocked because readiness artifacts are {packet.freshness.status}.",
            next_safe_action=f"Run {packet.freshness.refresh_command} before reviewing peer rows.",
            candidate_context_state="not_reviewed",
            trusted_peer_proof_state="locked",
            boundary="Do not treat stale or missing readiness artifacts as trusted peer proof.",
        )
    if not packet.rows:
        return PeerMappingPacketDecision(
            status="still_blocked",
            answer="No peer source-review rows are available for the selected scope.",
            next_safe_action="Run make readiness && make peer-mapping-queue TOP_N=25, then rerun make peer-mapping-source-review.",
            candidate_context_state="not_loaded",
            trusted_peer_proof_state="locked",
            boundary="Do not infer peer mappings when the peer source-review packet has no rows.",
        )

    for row in packet.rows:
        completion = peer_mapping_source_review_completion(row, packet.freshness)
        if completion.status == "ready_for_import_row_scaffold":
            return PeerMappingPacketDecision(
                status="ready_for_validate_preview",
                answer=f"{row.ticker} / {row.mapping_slot} has reviewed source fields and can enter write-back guard review.",
                next_safe_action=f"Run make peer-mapping-writeback-guard for {row.ticker} / {row.mapping_slot}, then validate and preview.",
                candidate_context_state=str(row.candidate_context_state or "not_loaded"),
                trusted_peer_proof_state="ready_for_guard",
                boundary="Trusted peer proof is not supported until write-back guard, validate, preview, apply/skip decision, readiness rebuild, and proof ledger review pass.",
            )

    candidate_rows = [
        row for row in packet.rows if str(row.candidate_context_state or "").strip() == "candidate_context_only"
    ]
    if candidate_rows:
        sample = candidate_rows[0]
        return PeerMappingPacketDecision(
            status="candidate_context_only",
            answer=(
                f"{len(candidate_rows):,} candidate-only peer slot(s) can route source review, "
                "but no trusted peer row is ready."
            ),
            next_safe_action=f"Use candidate context for {sample.ticker} only to find durable peer source proof.",
            candidate_context_state="candidate_context_only",
            trusted_peer_proof_state="locked",
            boundary="Candidate context is not trusted peer proof and must not unlock peer-relative valuation.",
        )

    sample = packet.rows[0]
    return PeerMappingPacketDecision(
        status="needs_source_review_fields",
        answer="Peer source-review rows exist, but required reviewed fields are still missing.",
        next_safe_action=f"Fill reviewed peer source-review fields for {sample.ticker} / {sample.mapping_slot}.",
        candidate_context_state=str(sample.candidate_context_state or "not_loaded"),
        trusted_peer_proof_state="locked",
        boundary="Keep peer-relative valuation locked until source-backed peer rows pass the full review gate.",
    )


def _peer_pair_exists(root: Path, ticker: str, peer_ticker: str) -> tuple[str, ...]:
    matches: list[str] = []
    ticker_key = str(ticker or "").strip().upper()
    peer_key = str(peer_ticker or "").strip().upper()
    for relative_path in (CANONICAL_PEERS_PATH, IMPORT_PEERS_PATH):
        path = root / relative_path
        for row in _read_csv(path):
            existing_ticker = str(row.get("ticker") or "").strip().upper()
            existing_peer = str(row.get("peer_ticker") or "").strip().upper()
            if existing_ticker == ticker_key and existing_peer == peer_key:
                matches.append(str(relative_path))
                break
    return tuple(matches)


def peer_mapping_proof_record_missing_fields(guard_status: str) -> tuple[str, ...]:
    if guard_status != "ready_for_validate_preview":
        return ("guard_blocking_reasons",)
    return (
        "validation_result",
        "preview_result",
        "apply_result",
        "changed_readiness_counts",
        "changed_tickers",
        "generated_artifacts_reviewed",
        "final_outcome",
    )


def peer_mapping_proof_record_command(row: PeerMappingReviewRow, guard_status: str) -> str:
    ticker = str(row.ticker or "").strip().upper()
    peer_ticker = str(row.proposed_peer_ticker or "").strip().upper()
    review_date = str(row.review_date or "").strip()
    batch_date = review_date.replace("-", "") if review_date and not _is_placeholder(review_date) else "YYYYMMDD"
    batch_id = f"RB-PEER-{ticker}-{peer_ticker}-{batch_date}" if ticker and peer_ticker else "RB-PEER-<ticker>-<peer>-<yyyymmdd>"
    source_files = f"{IMPORT_PEERS_PATH}; {row.source}" if row.source and not _is_placeholder(row.source) else str(IMPORT_PEERS_PATH)
    command_run = (
        "make peer-mapping-writeback-guard ... && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>"
        if guard_status == "ready_for_validate_preview"
        else "make peer-mapping-writeback-guard ..."
    )
    values = {
        "BATCH_ID": batch_id,
        "LANE": "peers",
        "REVIEW_DATE": review_date if review_date and not _is_placeholder(review_date) else "<yyyy-mm-dd>",
        "REVIEWER": row.reviewer if row.reviewer and not _is_placeholder(row.reviewer) else "<reviewer>",
        "SCOPE": "source-backed peer mapping",
        "TICKERS": ticker or "<ticker>",
        "COMMAND_RUN": command_run,
        "VALIDATION_RESULT": "<imports-validate result>",
        "PREVIEW_RESULT": "<imports-preview and rejected-row review>",
        "APPLY_RESULT": "<not_run|applied|skipped after review>",
        "CHANGED_READINESS_COUNTS": "<from reviewed-batch-compare LANE=peers>",
        "CHANGED_TICKERS": "<from reviewed-batch-compare LANE=peers>",
        "SOURCE_FILES": source_files,
        "GENERATED_ARTIFACTS_REVIEWED": "<kept peer evidence or excluded generated churn>",
        "FINAL_OUTCOME": "<supported|candidate_context_only|still_blocked|skipped|excluded>",
        "NOTES": "peer row remains research-only until validate, preview, apply decision, readiness, and proof review pass",
    }
    assignments = " ".join(_shell_assignment(name, value) for name, value in values.items())
    return f"DRY_RUN=1 make reviewed-batch-proof-record {assignments}"


def build_peer_mapping_writeback_guard(root: Path | str, row: PeerMappingReviewRow) -> PeerMappingWriteBackGuard:
    root = Path(root)
    freshness = readiness_freshness_status(root)
    preview = peer_mapping_import_preview(row, freshness)
    blocking_reasons: list[str] = []
    if preview.status != "ready_for_validate_preview":
        completion = peer_mapping_source_review_completion(row, freshness)
        blocking_reasons.extend(completion.missing_fields)
    ticker = str(row.ticker or "").strip().upper()
    peer_ticker = str(row.proposed_peer_ticker or "").strip().upper()
    if ticker and peer_ticker and ticker == peer_ticker:
        blocking_reasons.append("self_peer")
    duplicate_sources = _peer_pair_exists(root, ticker, peer_ticker)
    if duplicate_sources:
        blocking_reasons.append("duplicate_peer_pair")
    status = "ready_for_validate_preview" if not blocking_reasons else "blocked"
    csv_row = preview.csv_row if status == "ready_for_validate_preview" else ""
    apply_boundary = (
        preview.apply_boundary
        if status == "ready_for_validate_preview"
        else "Do not copy or apply this peer row until blocking reasons are resolved."
    )
    proof_record_status = "ready_for_review_fields" if status == "ready_for_validate_preview" else "blocked_by_guard"
    return PeerMappingWriteBackGuard(
        status=status,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        duplicate_sources=duplicate_sources,
        proof_record_status=proof_record_status,
        proof_record_missing_fields=peer_mapping_proof_record_missing_fields(status),
        csv_header=preview.csv_header,
        csv_row=csv_row,
        target_file=row.target_file,
        validation_command=preview.validation_command,
        apply_boundary=apply_boundary,
        post_apply_proof=preview.post_apply_proof,
        proof_record_command=peer_mapping_proof_record_command(row, status),
        proof_record_boundary=(
            "Copy this dry-run proof-record command only after the peer row is reviewed, validate/preview outputs are checked, any apply decision is made, readiness is rebuilt, and generated artifacts are classified."
            if status == "ready_for_validate_preview"
            else "Do not record a supported peer outcome while the write-back guard is blocked; resolve the guard or record a reviewed still_blocked outcome separately."
        ),
    )


def render_peer_mapping_writeback_guard(guard: PeerMappingWriteBackGuard, row: PeerMappingReviewRow) -> str:
    blocking = ",".join(guard.blocking_reasons) if guard.blocking_reasons else "-"
    duplicates = ",".join(guard.duplicate_sources) if guard.duplicate_sources else "-"
    csv_row = guard.csv_row or "-"
    proof_missing = ",".join(guard.proof_record_missing_fields) if guard.proof_record_missing_fields else "-"
    lines = [
        "Peer mapping write-back guard",
        "Research-only: this guard prints a reviewed peer import row only when source proof, duplicate checks, and freshness gates pass.",
        "It does not edit files, apply imports, connect to brokers, route orders, or provide direct buy/sell instructions.",
        f"status: {guard.status}",
        f"blocking_reasons: {blocking}",
        f"duplicate_sources: {duplicates}",
        f"proof_record_status: {guard.proof_record_status}",
        f"proof_record_missing_fields: {proof_missing}",
        f"target_file: {guard.target_file}",
        f"ticker: {row.ticker}",
        f"peer_ticker: {row.proposed_peer_ticker}",
        f"csv_header: {guard.csv_header}",
        f"csv_row: {csv_row}",
        f"validation_command: {guard.validation_command}",
        f"apply_boundary: {guard.apply_boundary}",
        f"post_apply_proof: {guard.post_apply_proof}",
        f"proof_record_command: {guard.proof_record_command}",
        f"proof_record_boundary: {guard.proof_record_boundary}",
    ]
    return "\n".join(lines) + "\n"


def _candidate_tickers_with_source(root: Path, top_n: int, tickers: tuple[str, ...]) -> tuple[tuple[str, ...], str]:
    if tickers:
        return tickers[: max(top_n, 0)], "explicit_tickers"
    candidates: list[str] = []
    top_actions = _read_csv(root / PROJECT_STATUS_TOP_ACTIONS_PATH)
    selection_source = ""
    for row in top_actions:
        dataset = str(row.get("dataset") or "").strip().lower()
        target_file = str(row.get("target_file") or "").strip()
        ticker = str(row.get("ticker") or "").strip().upper()
        if dataset == "peers" and target_file == "data/imports/peers.csv" and ticker and ticker not in candidates:
            candidates.append(ticker)
            selection_source = "project_status_top_actions"
        if len(candidates) >= top_n:
            return tuple(candidates), "project_status_top_actions"
    try:
        from src.data_onboarding import build_peer_mapping_queue, build_ticker_coverage

        coverage_rows = build_ticker_coverage(root)
        queue_rows = build_peer_mapping_queue(coverage_rows, root)
    except Exception:
        queue_rows = []
    for row in queue_rows:
        if bool(getattr(row, "has_peer_mapping", False)):
            continue
        if str(getattr(row, "candidate_context_state", "") or "").strip() == "excluded":
            continue
        ticker = str(getattr(row, "ticker", "") or "").strip().upper()
        if ticker and ticker not in candidates:
            candidates.append(ticker)
            if selection_source == "project_status_top_actions":
                selection_source = "project_status_top_actions_plus_peer_mapping_queue"
            elif not selection_source:
                selection_source = "peer_mapping_queue"
        if len(candidates) >= top_n:
            return tuple(candidates), selection_source or "peer_mapping_queue"
    rows = _read_csv(root / PEER_READINESS_PATH)
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker and ticker not in candidates and _missing_mapping(row):
            candidates.append(ticker)
            if selection_source and not selection_source.endswith("_plus_peer_readiness_report"):
                selection_source = f"{selection_source}_plus_peer_readiness_report"
            elif not selection_source:
                selection_source = "peer_readiness_report"
        if len(candidates) >= top_n:
            break
    return tuple(candidates), selection_source or "peer_readiness_report"


def _candidate_tickers(root: Path, top_n: int, tickers: tuple[str, ...]) -> tuple[str, ...]:
    candidates, _selection_source = _candidate_tickers_with_source(root, top_n, tickers)
    return candidates


def _candidate_context_by_ticker(root: Path) -> dict[str, dict[str, str]]:
    try:
        from src.data_onboarding import build_peer_mapping_queue, build_ticker_coverage

        coverage_rows = build_ticker_coverage(root)
        queue_rows = build_peer_mapping_queue(coverage_rows, root)
    except Exception:
        return {}

    context: dict[str, dict[str, str]] = {}
    for row in queue_rows:
        ticker = str(getattr(row, "ticker", "") or "").strip().upper()
        if not ticker:
            continue
        state = str(getattr(row, "candidate_context_state", "") or "not_loaded").strip()
        source = str(getattr(row, "candidate_context_source", "") or "not_loaded").strip()
        count = str(getattr(row, "candidate_context_count", 0) or 0)
        peers = str(getattr(row, "candidate_context_peers", "") or "").strip()
        note = str(getattr(row, "fallback_context_note", "") or "").strip()
        if not note:
            if state == "candidate_context_only":
                note = "Candidate-only research context is available; it is not trusted peer proof."
            elif state == "still_blocked":
                note = "No local candidate context is available; source-backed peer rows are still required."
            elif state == "excluded":
                note = "Operating-company peer mapping is excluded for this ticker."
            else:
                note = "Candidate context is informational only and does not unlock trusted peer proof."
        context[ticker] = {
            "candidate_context_state": state,
            "candidate_context_source": source,
            "candidate_context_count": count,
            "candidate_context_peers": peers,
            "candidate_context_note": note,
        }
    return context


def build_peer_mapping_source_review_packet(
    root: Path | str = ".",
    *,
    top_n: int = 10,
    tickers: str | Iterable[str] | None = None,
) -> PeerMappingSourceReviewPacket:
    root = Path(root)
    selected_tickers = _split_tickers(tickers)
    freshness = readiness_freshness_status(root)
    candidates, selection_source = _candidate_tickers_with_source(root, top_n, selected_tickers)
    candidate_context = _candidate_context_by_ticker(root)
    review_rows: list[PeerMappingReviewRow] = []
    for ticker in candidates:
        context = candidate_context.get(
            ticker,
            {
                "candidate_context_state": "not_loaded",
                "candidate_context_source": "not_loaded",
                "candidate_context_count": "0",
                "candidate_context_peers": "",
                "candidate_context_note": "Candidate context was not loaded for this source-review row.",
            },
        )
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
                    validation_sequence=(
                        "make templates -> fill reviewed peer rows -> "
                        f"make imports-validate IMPORT_TICKERS={ticker} -> "
                        f"make imports-preview IMPORT_TICKERS={ticker} -> "
                        f"make imports-apply IMPORT_TICKERS={ticker} -> "
                        "make readiness -> make peer-mapping-queue TOP_N=25"
                    ),
                    do_not_proceed_if=(
                        "source does not name the peer relationship or comparable business context; "
                        "source is only sector/theme similarity; URL/document reference is missing; "
                        "review date or reviewer is missing; proposed peer ticker is not verified"
                    ),
                    candidate_context_state=context["candidate_context_state"],
                    candidate_context_source=context["candidate_context_source"],
                    candidate_context_count=context["candidate_context_count"],
                    candidate_context_peers=context["candidate_context_peers"],
                    candidate_context_note=context["candidate_context_note"],
                )
            )
    return PeerMappingSourceReviewPacket(
        freshness=freshness,
        top_n=top_n,
        tickers=candidates,
        rows=tuple(review_rows),
        selection_source=selection_source,
    )


def render_peer_mapping_source_review_markdown(packet: PeerMappingSourceReviewPacket) -> str:
    status = "blocked_by_freshness" if packet.freshness.status in {"missing", "stale"} else "ready_for_review"
    decision = peer_mapping_packet_decision(packet)
    lines = [
        "# Peer Mapping Source Review Packet",
        "",
        "Research-only: this packet prepares manual source review for peer mappings. It is not investment advice, does not connect to brokers, does not route orders, and does not provide direct buy/sell instructions.",
        "",
        f"- Packet status: `{status}`",
        f"- Freshness status: `{packet.freshness.status}`",
        f"- Freshness note: {packet.freshness.message}",
        f"- Refresh command if blocked: `{packet.freshness.refresh_command}`",
        f"- Selection source: `{packet.selection_source}`",
        f"- Ticker scope: `{', '.join(packet.tickers) if packet.tickers else 'none'}`",
        f"- Review rows: `{len(packet.rows)}`",
        "",
        "## First Peer Readiness Answer",
        "",
        f"- First answer status: `{decision.status}`",
        f"- Answer: {decision.answer}",
        f"- Next safe action: {decision.next_safe_action}",
        f"- Candidate context state: `{decision.candidate_context_state}`",
        f"- Trusted peer proof state: `{decision.trusted_peer_proof_state}`",
        f"- Boundary: {decision.boundary}",
        "",
        "## Source Proof Contract",
        "",
        "- Import schema: `ticker, peer_ticker, peer_group, sector, industry, source, as_of_date`.",
        "- Required review fields before import: proposed peer ticker, peer group, source, as-of date, relationship rationale, reviewer, and review date.",
        "- Accepted proof: a durable URL or local document that names the peer relationship or supports comparable business context.",
        "- Rejected shortcuts: memory, popularity, sector/theme similarity alone, row-count convenience, or placeholders.",
        "- Candidate context: local classification leads may help source review, but remain `candidate_context_only` and never count as trusted peer proof.",
        "- Validation path: `make imports-validate IMPORT_TICKERS=<ticker> -> make imports-preview IMPORT_TICKERS=<ticker> -> make imports-apply IMPORT_TICKERS=<ticker>` only after source review.",
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
                f"- Candidate context state: `{row.candidate_context_state}`",
                f"- Candidate context source: `{row.candidate_context_source}`",
                f"- Candidate context count: `{row.candidate_context_count}`",
                f"- Candidate context peers: `{row.candidate_context_peers or '-'}`",
                f"- Candidate context boundary: {row.candidate_context_note}",
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
    decision = peer_mapping_packet_decision(packet)
    lines = [
        "Peer mapping source review preview",
        "Research-only: review peer mapping source proof before editing import rows; no broker integration, no auto-trading, and no direct buy/sell instructions.",
        f"status: preview",
        f"packet_status: {status}",
        f"freshness_status: {packet.freshness.status}",
        f"first_answer_status: {decision.status}",
        f"first_answer_next_safe_action: {decision.next_safe_action}",
        f"candidate_context_state: {decision.candidate_context_state}",
        f"trusted_peer_proof_state: {decision.trusted_peer_proof_state}",
        f"first_answer_boundary: {decision.boundary}",
        f"selection_source: {packet.selection_source}",
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
                f"- candidate_context_state: {row.candidate_context_state}",
                f"- candidate_context_source: {row.candidate_context_source}",
                f"- candidate_context_count: {row.candidate_context_count}",
                f"- candidate_context_peers: {row.candidate_context_peers or '-'}",
                f"- candidate_context_boundary: {row.candidate_context_note}",
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
    parser.add_argument("--guard-writeback", action="store_true", help="Preview one reviewed peer import row and block unsafe write-back.")
    parser.add_argument("--ticker", default="<ticker>")
    parser.add_argument("--peer-ticker", default="<source-backed peer ticker>")
    parser.add_argument("--peer-group", default="<reviewed peer group>")
    parser.add_argument("--sector", default="<reviewed sector>")
    parser.add_argument("--industry", default="<reviewed industry>")
    parser.add_argument("--source", default="<durable URL or local document reference>")
    parser.add_argument("--as-of-date", default="<YYYY-MM-DD>")
    parser.add_argument("--relationship-rationale", default="<why this source supports the peer relationship>")
    parser.add_argument("--reviewer", default="<reviewer>")
    parser.add_argument("--review-date", default="<YYYY-MM-DD>")
    parser.add_argument("--source-proof-status", default="needs_review")
    parser.add_argument("--import-row-ready", default="no")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.guard_writeback:
        row = PeerMappingReviewRow(
            ticker=str(args.ticker).strip().upper(),
            mapping_slot="peer_1",
            proposed_peer_ticker=str(args.peer_ticker).strip().upper(),
            peer_group=args.peer_group,
            sector=args.sector,
            industry=args.industry,
            source=args.source,
            as_of_date=args.as_of_date,
            relationship_rationale=args.relationship_rationale,
            reviewer=args.reviewer,
            review_date=args.review_date,
            source_proof_status=args.source_proof_status,
            import_row_ready=args.import_row_ready,
            target_file=str(IMPORT_PEERS_PATH),
            focus_command=f"make focus-peers TICKER={str(args.ticker).strip().upper()}",
            validation_sequence=(
                f"make imports-validate IMPORT_TICKERS={str(args.ticker).strip().upper()} -> "
                f"make imports-preview IMPORT_TICKERS={str(args.ticker).strip().upper()} -> "
                f"make imports-apply IMPORT_TICKERS={str(args.ticker).strip().upper()} -> "
                "make readiness -> make peer-mapping-queue TOP_N=25"
            ),
            do_not_proceed_if=(
                "source does not name the peer relationship or comparable business context; "
                "source is only sector/theme similarity; duplicate or self-peer row is detected; "
                "review date or reviewer is missing; proposed peer ticker is not verified"
            ),
            candidate_context_state="guard_scope",
            candidate_context_source="reviewed_cli_inputs",
            candidate_context_count="0",
            candidate_context_peers="",
            candidate_context_note="Write-back guard uses reviewed CLI fields; candidate context is not trusted peer proof.",
        )
        print(render_peer_mapping_writeback_guard(build_peer_mapping_writeback_guard(args.root, row), row))
        return 0
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
