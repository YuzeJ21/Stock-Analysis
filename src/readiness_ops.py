"""Read-only lane operations center for broad data readiness workflows."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.dcf_input_proof_queue import DcfInputProofRow, build_dcf_input_proof_queue_from_files, summarize_missing_input_families
from src.reviewed_batch_proof import ReviewedBatchProof, load_reviewed_batch_proofs
from src.session_source_preflight import load_session_source_preflight


LANE_ORDER = (
    "price_coverage",
    "fundamentals_dcf",
    "share_count_proof",
    "peer_mapping",
    "peer_valuation_inputs",
    "earnings_locked",
    "analyst_estimates_locked",
    "excluded_not_applicable",
)
COMPANY_PEER_EXCLUDED_ASSET_TYPES = {"etf", "index_proxy", "fund"}


@dataclass(frozen=True)
class ReadinessLane:
    lane: str
    label: str
    readiness_state: str
    workflow_mode: str
    total_count: int
    ready_count: int
    partial_count: int
    blocked_count: int
    excluded_count: int
    unlock_impact: int
    source_lane: str
    source_readiness: str
    next_safe_command: str
    proof_command: str
    generated_churn_policy: str
    stale_proof_warning: str
    notes: str
    reviewed_proof_status: str = ""


@dataclass(frozen=True)
class CoverageFrontierOpportunity:
    rank: int
    lane: str
    label: str
    unlock_impact: int
    possible_state_move: str
    source_lane: str
    workflow_mode: str
    next_safe_command: str
    proof_command: str
    generated_churn_policy: str
    guardrail: str
    reviewed_proof_status: str = ""


@dataclass(frozen=True)
class DataCoverageExpansionStep:
    step: int
    lane: str
    label: str
    workflow_mode: str
    batch_scope: str
    next_safe_command: str
    review_gate: str
    proof_command: str
    stop_condition: str
    generated_churn_policy: str
    outcome_boundary: str


@dataclass(frozen=True)
class DataCoverageProofQueueRow:
    queue_key: str
    label: str
    readiness_state: str
    queued_rows: int
    ready_count: int
    partial_count: int
    blocked_count: int
    top_blockers: str
    source_mode: str
    next_safe_command: str
    proof_packet_command: str
    review_gate: str
    stop_rule: str
    proof_record_boundary: str
    generated_churn_policy: str


@dataclass(frozen=True)
class PeerReadinessSummary:
    total_count: int
    peer_mapping_ready: int
    peer_price_ready: int
    peer_momentum_ready: int
    peer_fundamentals_ready: int
    peer_valuation_ready: int
    peer_valuation_comparison_ready: int
    missing_mapping: int
    missing_peer_price: int
    missing_peer_momentum: int
    missing_peer_fundamentals: int
    peer_valuation_blocked: int
    source_context: str

    @property
    def trend_ready(self) -> int:
        return self.peer_momentum_ready

    @property
    def valuation_input_blockers(self) -> int:
        return self.missing_peer_price + self.missing_peer_fundamentals + self.peer_valuation_blocked

    @property
    def summary_text(self) -> str:
        return (
            f"mapping={self.peer_mapping_ready}/{self.total_count}; "
            f"peer_price={self.peer_price_ready}; peer_momentum={self.peer_momentum_ready}; "
            f"peer_fundamentals={self.peer_fundamentals_ready}; "
            f"peer_valuation={self.peer_valuation_ready}; "
            f"peer_valuation_comparison={self.peer_valuation_comparison_ready}; "
            f"blocked: mappings={self.missing_mapping}, peer_prices={self.missing_peer_price}, "
            f"peer_momentum={self.missing_peer_momentum}, peer_fundamentals={self.missing_peer_fundamentals}, "
            f"mapped_peer_inputs={self.valuation_input_blockers}"
        )


@dataclass(frozen=True)
class ReadinessQueueRow:
    lane: str
    label: str
    readiness_state: str
    ready_count: int
    partial_count: int
    blocked_count: int
    excluded_count: int
    total_count: int
    top_missing_input_families: str
    source_mode: str
    source_lane: str
    next_safe_command: str
    proof_gate: str
    guardrail: str


@dataclass(frozen=True)
class ReviewedBatchLedgerSummary:
    lane: str
    record_count: int
    unique_ticker_count: int
    outcome_counts: dict[str, int]
    latest_batch_id: str
    latest_outcome: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _clean(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def _count_true(rows: Iterable[dict[str, str]], field: str) -> int:
    return sum(1 for row in rows if _truthy(row.get(field)))


def _count_contains(rows: Iterable[dict[str, str]], field: str, text: str) -> int:
    needle = text.lower()
    return sum(1 for row in rows if needle in str(row.get(field) or "").lower())


def _feature_list_contains(row: dict[str, str], field: str, feature: str) -> bool:
    values = [part.strip().lower() for part in str(row.get(field) or "").split(",")]
    return feature.lower() in values


def _row_excludes_company_peer_context(row: dict[str, str]) -> bool:
    asset_type = str(row.get("asset_type") or "").strip().lower()
    return asset_type in COMPANY_PEER_EXCLUDED_ASSET_TYPES or _feature_list_contains(row, "excluded_features", "peer")


def _feature_row(feature_rows: list[dict[str, str]], feature: str) -> dict[str, str] | None:
    for row in feature_rows:
        if str(row.get("feature") or "").strip().lower() == feature:
            return row
    return None


def _int_value(value: object, fallback: int = 0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return fallback


def _lane_state(*, ready: int, partial: int = 0, blocked: int = 0, excluded: int = 0) -> str:
    if excluded and not ready and not partial and not blocked:
        return "excluded"
    if ready and not partial and not blocked:
        return "ready"
    if ready or partial:
        return "partial"
    if blocked:
        return "blocked"
    return "blocked"


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def build_stale_proof_warning(root: Path) -> str:
    ledger = root / "data" / "reviewed_data_proofs.csv"
    proof_time = _mtime(ledger)
    if not proof_time:
        return "No reviewed proof ledger found; record proof only after reviewed source changes."
    watched = [
        root / "data" / "prices.csv",
        root / "data" / "fundamentals.csv",
        root / "data" / "peers.csv",
        root / "data" / "earnings.csv",
        root / "data" / "analyst_estimates.csv",
        root / "data" / "reports" / "ticker_readiness_report.csv",
    ]
    newer = [path.relative_to(root).as_posix() for path in watched if _mtime(path) > proof_time]
    if not newer:
        return "Latest reviewed proof is at least as recent as watched source/readiness files."
    return "Reviewed proof may be stale after changes in: " + ", ".join(newer[:6])


def _ticker_set(rows: Iterable[ReviewedBatchProof]) -> set[str]:
    tickers: set[str] = set()
    for row in rows:
        for ticker in row.tickers.split(","):
            cleaned = ticker.strip()
            if cleaned and cleaned != "-":
                tickers.add(cleaned.upper())
    return tickers


def build_reviewed_batch_ledger_summaries(root: Path | str = ".") -> dict[str, ReviewedBatchLedgerSummary]:
    rows = load_reviewed_batch_proofs(Path(root) / "data" / "reviewed_batch_proofs.csv")
    by_lane: dict[str, list[ReviewedBatchProof]] = {}
    for row in rows:
        by_lane.setdefault(row.lane, []).append(row)

    summaries: dict[str, ReviewedBatchLedgerSummary] = {}
    for lane, lane_rows in by_lane.items():
        latest = lane_rows[-1]
        summaries[lane] = ReviewedBatchLedgerSummary(
            lane=lane,
            record_count=len(lane_rows),
            unique_ticker_count=len(_ticker_set(lane_rows)),
            outcome_counts=dict(Counter(row.final_outcome for row in lane_rows)),
            latest_batch_id=latest.batch_id,
            latest_outcome=latest.final_outcome,
        )
    return summaries


def _reviewed_batch_ledger_note(summary: ReviewedBatchLedgerSummary | None, *, lane_label: str) -> str:
    if summary is None or summary.record_count <= 0:
        return ""
    outcomes = ", ".join(
        f"{outcome}={count}" for outcome, count in sorted(summary.outcome_counts.items())
    )
    return (
        f"Reviewed proof ledger: {lane_label} has {summary.record_count} reviewed record(s) "
        f"across {summary.unique_ticker_count} unique ticker(s); outcomes {outcomes}; "
        f"latest {summary.latest_batch_id}={summary.latest_outcome}."
    )


def _reviewed_batch_coverage_status(
    summary: ReviewedBatchLedgerSummary | None,
    *,
    lane_label: str,
    expected_count: int,
) -> str:
    if summary is None or expected_count <= 0 or summary.unique_ticker_count < expected_count:
        return ""
    outcomes = ", ".join(f"{outcome}={count}" for outcome, count in sorted(summary.outcome_counts.items()))
    return (
        f"reviewed proof ledger covers current {lane_label} scope "
        f"({summary.unique_ticker_count}/{expected_count} ticker(s); outcomes {outcomes}); "
        "do not repeat this proof loop unless new source-backed rows, new tickers, or changed blockers appear."
    )


def _feature_counts(
    feature_rows: list[dict[str, str]],
    feature: str,
    readiness_rows: list[dict[str, str]],
    readiness_field: str,
) -> tuple[int, int, int, int, int]:
    row = _feature_row(feature_rows, feature)
    total = len(readiness_rows) or _int_value((row or {}).get("total_count"))
    ready = _int_value((row or {}).get("ready_count"), _count_true(readiness_rows, readiness_field))
    partial = _int_value((row or {}).get("partial_count"))
    blocked = _int_value((row or {}).get("blocked_count"), max(total - ready - partial, 0))
    excluded = _int_value((row or {}).get("excluded_count"))
    return total, ready, partial, blocked, excluded


def _source_status(sources: dict[str, object], key: str) -> dict[str, object]:
    value = sources.get(key, {})
    return value if isinstance(value, dict) else {}


def _fundamentals_source_ladder_context(root: Path) -> tuple[str, bool]:
    preflight = load_session_source_preflight(root)
    if not preflight:
        return (
            "Session source availability is not recorded; run make session-source-preflight before retrying source-backed coverage work.",
            False,
        )
    sources = preflight.get("sources", {})
    if not isinstance(sources, dict):
        return (
            "Session source availability is unreadable; rerun make session-source-preflight before retrying source-backed coverage work.",
            False,
        )

    pieces: list[str] = []
    ladder_available = False
    provider_labels = {
        "sec": "SEC",
        "yfinance_stage": "Yahoo/yfinance",
        "fmp": "FMP",
        "alpha_vantage": "Alpha Vantage",
        "finnhub": "Finnhub",
    }
    for key, label in provider_labels.items():
        source = _source_status(sources, key)
        status = str(source.get("status") or "").strip()
        reason = str(source.get("reason_code") or "").strip()
        if status == "available":
            ladder_available = True
            if key == "fmp":
                pieces.append("FMP configured")
            elif key == "alpha_vantage":
                pieces.append("Alpha Vantage configured")
            elif key == "finnhub":
                pieces.append("Finnhub configured")
            else:
                pieces.append(f"{label} available")
        elif reason == "provider_key_missing":
            if key == "fmp":
                pieces.append("FMP_API_KEY missing")
            elif key == "alpha_vantage":
                pieces.append("ALPHA_VANTAGE_API_KEY missing")
            elif key == "finnhub":
                pieces.append("FINNHUB_API_KEY missing")
        elif status:
            pieces.append(f"{label} unavailable ({reason or status})")

    local = _source_status(sources, "local_fundamentals")
    if str(local.get("status") or "").strip() == "available":
        row_count = _int_value(local.get("ticker_count") or local.get("row_count"))
        fixable = _int_value(local.get("fundamentals_fixable_ticker_count")) + _int_value(
            local.get("share_count_fixable_ticker_count")
        )
        if fixable:
            pieces.append(f"local reviewed rows available ({fixable} current blocker match{'es' if fixable != 1 else ''})")
        elif row_count:
            pieces.append(f"local reviewed rows available ({row_count} ticker{'s' if row_count != 1 else ''})")
        else:
            pieces.append("local reviewed rows available")

    if not pieces:
        return (
            "Session source availability has no executable fundamentals/share-count source recorded.",
            False,
        )
    return "Session source availability: " + "; ".join(pieces) + ".", ladder_available


def _source_activation_context(root: Path) -> tuple[bool, str]:
    preflight = load_session_source_preflight(root)
    if not isinstance(preflight, dict):
        return False, ""
    activation = preflight.get("source_activation", {})
    if not isinstance(activation, dict) or activation.get("status") != "required":
        return False, ""
    detail = str(activation.get("detail") or "").strip()
    next_action = str(activation.get("next_action") or "").strip()
    pieces = ["Source activation required before more source-backed coverage expansion."]
    if detail:
        pieces.append(detail)
    if next_action:
        pieces.append(next_action)
    pieces.append("Use make coverage-expansion-loop TOP_N=10 for the setup-only gate.")
    return True, " ".join(pieces)


def build_peer_readiness_summary(root: Path | str = ".") -> PeerReadinessSummary:
    root = Path(root)
    rows = _read_csv(root / "data" / "reports" / "peer_readiness_report.csv")
    total = len(rows)
    if not rows:
        return PeerReadinessSummary(
            total_count=0,
            peer_mapping_ready=0,
            peer_price_ready=0,
            peer_momentum_ready=0,
            peer_fundamentals_ready=0,
            peer_valuation_ready=0,
            peer_valuation_comparison_ready=0,
            missing_mapping=0,
            missing_peer_price=0,
            missing_peer_momentum=0,
            missing_peer_fundamentals=0,
            peer_valuation_blocked=0,
            source_context="data/reports/peer_readiness_report.csv missing; run make readiness before using peer sub-state counts.",
        )
    return PeerReadinessSummary(
        total_count=total,
        peer_mapping_ready=sum(1 for row in rows if str(row.get("mapping_status") or "").strip().lower() == "mapped"),
        peer_price_ready=_count_true(rows, "peer_price_ready"),
        peer_momentum_ready=_count_true(rows, "peer_momentum_ready"),
        peer_fundamentals_ready=_count_true(rows, "peer_fundamentals_ready"),
        peer_valuation_ready=_count_true(rows, "peer_valuation_ready"),
        peer_valuation_comparison_ready=_count_true(rows, "peer_valuation_comparison_ready"),
        missing_mapping=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "missing_peer_mapping"),
        missing_peer_price=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_price_missing"),
        missing_peer_momentum=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_momentum_missing"),
        missing_peer_fundamentals=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_fundamentals_missing"),
        peer_valuation_blocked=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_valuation_blocked"),
        source_context="data/reports/peer_readiness_report.csv; peer trend can be ready before peer valuation comparison is ready.",
    )


def build_readiness_ops_lanes(
    root: Path | str = ".",
    *,
    dcf_input_rows: list[DcfInputProofRow] | None = None,
    share_count_rows: list[object] | None = None,
    peer_summary: PeerReadinessSummary | None = None,
) -> list[ReadinessLane]:
    root = Path(root)
    data = root / "data"
    reports = data / "reports"
    readiness_rows = _read_csv(reports / "ticker_readiness_report.csv")
    feature_rows = _read_csv(reports / "feature_readiness_summary.csv")
    peer_unlock_rows = _read_csv(reports / "peer_unlock_worklist.csv")
    peer_summary = peer_summary or build_peer_readiness_summary(root)
    dcf_input_rows = dcf_input_rows if dcf_input_rows is not None else build_dcf_input_proof_queue_from_files(root, top_n=100000)
    dcf_input_summary = summarize_missing_input_families(dcf_input_rows)
    share_count_rows = share_count_rows if share_count_rows is not None else _share_count_dcf_rows(dcf_input_rows)
    share_count_only_blockers = sum(
        1
        for row in share_count_rows
        if str(getattr(row, "dcf_input_status", "") or "").startswith(("share-count-only", "single-input blocker: shares_outstanding"))
    )
    stale_warning = build_stale_proof_warning(root)

    total = len(readiness_rows)
    share_count_ready = max(total - len(share_count_rows), 0)
    price_total, price_ready, price_partial, price_blocked, price_excluded = _feature_counts(
        feature_rows, "price", readiness_rows, "price_ready"
    )
    fundamentals_total, fundamentals_ready, fundamentals_partial, fundamentals_blocked, fundamentals_excluded = _feature_counts(
        feature_rows, "fundamentals", readiness_rows, "fundamentals_ready"
    )
    dcf_ready = _count_true(readiness_rows, "dcf_ready")
    peer_ready = _count_true(readiness_rows, "peer_ready")
    peer_mapping_excluded = sum(1 for row in readiness_rows if _row_excludes_company_peer_context(row))
    peer_mapping_blocked = sum(
        1
        for row in readiness_rows
        if "source-backed peer mappings" in str(row.get("missing_data") or "").lower()
        and not _row_excludes_company_peer_context(row)
    )
    peer_valuation_worklist_blocked = sum(
        1 for row in peer_unlock_rows if str(row.get("workflow_group") or "").strip() == "peer_valuation_unlock"
    )
    peer_valuation_blocked = (
        peer_summary.valuation_input_blockers
        if peer_summary.total_count
        else peer_valuation_worklist_blocked or _count_contains(readiness_rows, "missing_data", "peer")
    )
    peer_valuation_ready = peer_summary.peer_valuation_comparison_ready if peer_summary.total_count else peer_ready
    peer_valuation_partial = max(peer_summary.peer_mapping_ready - peer_valuation_ready - peer_valuation_blocked, 0)
    earnings_ready = _count_true(readiness_rows, "earnings_ready")
    analyst_ready = _count_true(readiness_rows, "analyst_estimates_ready")
    earnings_blocked = max(total - earnings_ready, 0)
    analyst_blocked = max(total - analyst_ready, 0)
    excluded_dcf = _count_contains(readiness_rows, "excluded_features", "dcf")
    fundamentals_source_context, source_ladder_available = _fundamentals_source_ladder_context(root)
    source_activation_required, source_activation_context = _source_activation_context(root)
    batch_ledger_summaries = build_reviewed_batch_ledger_summaries(root)
    price_ledger_note = _reviewed_batch_ledger_note(
        batch_ledger_summaries.get("prices"),
        lane_label="price coverage",
    )
    peer_ledger_note = _reviewed_batch_ledger_note(batch_ledger_summaries.get("peers"), lane_label="peer mapping")
    peer_valuation_ledger_note = _reviewed_batch_ledger_note(
        batch_ledger_summaries.get("peer_valuation_inputs"),
        lane_label="peer valuation inputs",
    )
    optional_ledger_note = _reviewed_batch_ledger_note(
        batch_ledger_summaries.get("optional_context"),
        lane_label="optional context",
    )
    peer_ledger_status = _reviewed_batch_coverage_status(
        batch_ledger_summaries.get("peers"),
        lane_label="peer mapping",
        expected_count=peer_mapping_blocked,
    )
    peer_valuation_ledger_status = _reviewed_batch_coverage_status(
        batch_ledger_summaries.get("peer_valuation_inputs"),
        lane_label="peer valuation input",
        expected_count=peer_valuation_blocked,
    )
    optional_ledger_status = _reviewed_batch_coverage_status(
        batch_ledger_summaries.get("optional_context"),
        lane_label="optional context",
        expected_count=total,
    )
    price_ledger_status = _reviewed_batch_coverage_status(
        batch_ledger_summaries.get("prices"),
        lane_label="price coverage",
        expected_count=price_partial + price_blocked,
    )
    source_activation_command = "make coverage-expansion-loop TOP_N=10"
    source_activation_workflow = "source_activation_required"
    fundamentals_next_command = "make fundamentals-source-ladder-queue TOP_N=25"
    share_count_next_command = "make fundamentals-source-ladder-queue TOP_N=10"
    optional_context_next_command = "make optional-context-source-ladder-queue TOP_N=10"
    if source_activation_required:
        fundamentals_next_command = source_activation_command
        share_count_next_command = source_activation_command
        optional_context_next_command = source_activation_command

    return [
        ReadinessLane(
            lane="price_coverage",
            label="Price Coverage",
            readiness_state=_lane_state(ready=price_ready, partial=price_partial, blocked=price_blocked, excluded=price_excluded),
            workflow_mode=source_activation_workflow if source_activation_required else "dry_run_first",
            total_count=price_total,
            ready_count=price_ready,
            partial_count=price_partial,
            blocked_count=price_blocked,
            excluded_count=price_excluded,
            unlock_impact=price_blocked + price_partial,
            source_lane="prices",
            source_readiness=(
                source_activation_context
                if source_activation_required
                else (
                    "Provider-assisted price rows can be planned at scale; PROVIDER=auto tries Stooq, Yahoo, "
                    "then configured FMP/Alpha Vantage/Finnhub fallbacks; dry-run and capped review come first."
                )
            ),
            next_safe_command=(
                source_activation_command
                if source_activation_required
                else "make price-history-proof-queue TOP_N=25"
                if price_ledger_status
                else "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto"
            ),
            proof_command="make readiness && make price-coverage TOP_N=25 && make status-check TOP_N=5",
            generated_churn_policy="Price refreshes can create broad CSV churn; keep refreshed data local unless intentionally reviewed.",
            stale_proof_warning=stale_warning,
            notes=(
                "Improves setup, momentum, liquidity, risk, and peer trend inputs only; it does not create fundamentals or valuation inputs."
                + (f" {price_ledger_note}" if price_ledger_note else "")
            ),
            reviewed_proof_status=price_ledger_status,
        ),
        ReadinessLane(
            lane="fundamentals_dcf",
            label="Fundamentals / DCF Proof",
            readiness_state=_lane_state(
                ready=min(fundamentals_ready, dcf_ready),
                partial=max(fundamentals_ready - dcf_ready, fundamentals_partial, 0),
                blocked=fundamentals_blocked,
                excluded=fundamentals_excluded,
            ),
            workflow_mode=source_activation_workflow if source_activation_required else "preview_first_reviewed_apply",
            total_count=fundamentals_total,
            ready_count=dcf_ready,
            partial_count=max(fundamentals_ready - dcf_ready, fundamentals_partial, 0),
            blocked_count=fundamentals_blocked,
            excluded_count=fundamentals_excluded,
            unlock_impact=fundamentals_blocked + max(fundamentals_ready - dcf_ready, 0),
            source_lane="fundamentals",
            source_readiness=(
                (
                    "Source activation required before the fundamentals source ladder can be used. "
                    if source_activation_required
                    else "source ladder tries SEC, yfinance, FMP, Alpha Vantage, then Finnhub when those session paths are available; "
                )
                + "Trusted local rows can still be reviewed through validate/preview. "
                f"{fundamentals_source_context}"
            ),
            next_safe_command=fundamentals_next_command,
            proof_command=(
                "make imports-validate IMPORT_TICKERS=<ticker> && "
                "make imports-preview IMPORT_TICKERS=<ticker> && make readiness && make dcf-readiness"
            ),
            generated_churn_policy="Stage/apply only reviewed trusted fundamentals rows; avoid broad generated report churn by default.",
            stale_proof_warning=stale_warning,
            notes=(
                "Missing DCF inputs keep valuation withheld; no placeholder revenue, cash flow, margin, or shares rows. "
                f"Current DCF input families: {dcf_input_summary}."
            ),
        ),
        ReadinessLane(
            lane="share_count_proof",
            label="Share Count Proof",
            readiness_state=_lane_state(ready=share_count_ready, partial=share_count_only_blockers, blocked=len(share_count_rows)),
            workflow_mode=source_activation_workflow if source_activation_required else "preview_first_reviewed_apply",
            total_count=total,
            ready_count=share_count_ready,
            partial_count=share_count_only_blockers,
            blocked_count=len(share_count_rows),
            excluded_count=0,
            unlock_impact=len(share_count_rows),
            source_lane="shares_outstanding",
            source_readiness=(
                (
                    "Source activation required before the share-count source ladder can be used. "
                    if source_activation_required
                    else "shares_outstanding proof must come from SEC/source-ladder proof or trusted local fundamentals rows; "
                )
                + "Do not infer it from price, market cap, or peers. "
                f"{fundamentals_source_context}"
            ),
            next_safe_command=share_count_next_command,
            proof_command=(
                "make imports-validate IMPORT_TICKERS=<ticker> && "
                "make imports-preview IMPORT_TICKERS=<ticker> && make dcf-readiness && make readiness"
            ),
            generated_churn_policy=(
                "Apply only reviewed trusted share-count rows; broad readiness/report CSV churn stays local unless intentionally reviewed."
            ),
            stale_proof_warning=stale_warning,
            notes=(
                f"{len(share_count_rows)} DCF blocker(s) need shares_outstanding proof; "
                f"{share_count_only_blockers} have price, revenue, free cash flow, and FCF margin already present."
            ),
        ),
        ReadinessLane(
            lane="peer_mapping",
            label="Peer Mapping Proof",
            readiness_state=_lane_state(ready=peer_ready, blocked=peer_mapping_blocked, excluded=peer_mapping_excluded),
            workflow_mode="preview_first_reviewed_apply",
            total_count=total,
            ready_count=peer_ready,
            partial_count=max(peer_valuation_blocked - peer_mapping_blocked, 0),
            blocked_count=peer_mapping_blocked,
            excluded_count=peer_mapping_excluded,
            unlock_impact=peer_mapping_blocked,
            source_lane="peers",
            source_readiness="Peer relationships must be source-backed or clearly labeled fallback context only.",
            next_safe_command="make peer-mapping-queue TOP_N=25",
            proof_command=(
                "make imports-validate IMPORT_TICKERS=<ticker> && "
                "make imports-preview IMPORT_TICKERS=<ticker> && make readiness && make peer-mapping-queue TOP_N=25"
            ),
            generated_churn_policy="Apply only reviewed peer rows; do not infer trusted peers from sector similarity.",
            stale_proof_warning=stale_warning,
            notes=(
                "Source-backed peer mappings unlock peer trend checks, but peer valuation still waits for mapped-peer inputs. "
                f"Peer sub-states: {peer_summary.summary_text}."
                + (f" {peer_ledger_note}" if peer_ledger_note else "")
            ),
            reviewed_proof_status=peer_ledger_status,
        ),
        ReadinessLane(
            lane="peer_valuation_inputs",
            label="Peer Valuation Inputs Proof",
            readiness_state=_lane_state(
                ready=peer_valuation_ready,
                partial=peer_valuation_partial,
                blocked=peer_valuation_blocked,
            ),
            workflow_mode="preview_first_reviewed_apply",
            total_count=total,
            ready_count=peer_valuation_ready,
            partial_count=peer_valuation_partial,
            blocked_count=peer_valuation_blocked,
            excluded_count=0,
            unlock_impact=peer_valuation_blocked,
            source_lane="mapped_peer_inputs",
            source_readiness="Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears.",
            next_safe_command="make peer-mapping-queue TOP_N=25",
            proof_command="make readiness && make peer-mapping-queue TOP_N=25",
            generated_churn_policy="Keep mapped-peer data changes reviewed; broad readiness/report CSV churn is not staged by default.",
            stale_proof_warning=stale_warning,
            notes=(
                "Peer trend can be partial while peer valuation remains blocked; keep those states separate. "
                f"Peer sub-states: {peer_summary.summary_text}."
                + (f" {peer_valuation_ledger_note}" if peer_valuation_ledger_note else "")
                + (f" Related peer mapping ledger: {peer_ledger_note}" if peer_ledger_note else "")
            ),
            reviewed_proof_status=peer_valuation_ledger_status,
        ),
        ReadinessLane(
            lane="earnings_locked",
            label="Earnings Locked Lane",
            readiness_state=_lane_state(ready=earnings_ready, blocked=earnings_blocked),
            workflow_mode=source_activation_workflow if source_activation_required else "optional_source_ladder",
            total_count=total,
            ready_count=earnings_ready,
            partial_count=0,
            blocked_count=earnings_blocked,
            excluded_count=0,
            unlock_impact=earnings_blocked,
            source_lane="earnings",
            source_readiness=(
                source_activation_context
                if source_activation_required
                else "Trusted local or reviewed provider-assisted earnings rows only; empty rows render unavailable, not analysis."
            ),
            next_safe_command=optional_context_next_command,
            proof_command=(
                "make imports-validate IMPORT_TICKERS=<ticker> && "
                "make imports-preview IMPORT_TICKERS=<ticker> && "
                "make imports-apply IMPORT_TICKERS=<ticker> && make optional-context-readiness"
            ),
            generated_churn_policy="Do not apply or publish earnings rows unless trusted local/provider source rows were reviewed.",
            stale_proof_warning=stale_warning,
            notes=(
                "Optional context stays locked until trusted local or reviewed provider-assisted rows exist."
                + (f" {optional_ledger_note}" if optional_ledger_note else "")
            ),
            reviewed_proof_status=optional_ledger_status,
        ),
        ReadinessLane(
            lane="analyst_estimates_locked",
            label="Analyst Estimates Locked Lane",
            readiness_state=_lane_state(ready=analyst_ready, blocked=analyst_blocked),
            workflow_mode=source_activation_workflow if source_activation_required else "optional_source_ladder",
            total_count=total,
            ready_count=analyst_ready,
            partial_count=0,
            blocked_count=analyst_blocked,
            excluded_count=0,
            unlock_impact=analyst_blocked,
            source_lane="analyst_estimates",
            source_readiness=(
                source_activation_context
                if source_activation_required
                else "Trusted local or reviewed provider-assisted analyst-estimate rows only; consensus context is optional and never a recommendation."
            ),
            next_safe_command=optional_context_next_command,
            proof_command=(
                "make imports-validate IMPORT_TICKERS=<ticker> && "
                "make imports-preview IMPORT_TICKERS=<ticker> && "
                "make imports-apply IMPORT_TICKERS=<ticker> && make optional-context-readiness"
            ),
            generated_churn_policy="Do not apply or publish estimates unless trusted local/provider source rows were reviewed.",
            stale_proof_warning=stale_warning,
            notes=(
                "Optional context is unavailable by design when trusted local or reviewed provider-assisted rows are missing."
                + (f" {optional_ledger_note}" if optional_ledger_note else "")
            ),
            reviewed_proof_status=optional_ledger_status,
        ),
        ReadinessLane(
            lane="excluded_not_applicable",
            label="Excluded / Not Applicable",
            readiness_state="excluded",
            workflow_mode="excluded",
            total_count=total,
            ready_count=0,
            partial_count=0,
            blocked_count=0,
            excluded_count=excluded_dcf,
            unlock_impact=0,
            source_lane="asset_type_scope",
            source_readiness="ETF/index/fund rows can support market monitoring while operating-company DCF is excluded.",
            next_safe_command="make stock-report-md TICKER=QQQ",
            proof_command="make readiness && make stock-report-md TICKER=QQQ",
            generated_churn_policy="Excluded examples are demo/report artifacts only when intentionally reviewed.",
            stale_proof_warning=stale_warning,
            notes="Excluded means not applicable, not failed; do not force company valuation onto non-company rows.",
        ),
    ]


def build_coverage_frontier(lanes: list[ReadinessLane], *, top_n: int = 10) -> list[CoverageFrontierOpportunity]:
    ranked_lanes = [
        lane
        for lane in lanes
        if lane.workflow_mode != "excluded" and lane.unlock_impact > 0
    ]
    workflow_rank = {
        "source_activation_required": -1,
        "dry_run_first": 0,
        "preview_first_reviewed_apply": 1,
        "reviewed_apply": 2,
        "optional_source_ladder": 3,
        "locked_manual": 4,
    }
    ranked_lanes.sort(
        key=lambda lane: (
            workflow_rank.get(lane.workflow_mode, 9),
            bool(lane.reviewed_proof_status),
            -lane.unlock_impact,
            lane.label,
        )
    )
    rows: list[CoverageFrontierOpportunity] = []
    for rank, lane in enumerate(ranked_lanes[: max(top_n, 0)], start=1):
        if lane.reviewed_proof_status:
            move = "reviewed proof already recorded -> wait for new source-backed rows, new tickers, or changed blockers"
        elif lane.workflow_mode == "source_activation_required":
            move = "source unavailable -> source activation gate before more coverage expansion"
        elif lane.workflow_mode == "dry_run_first":
            move = "blocked/partial price coverage -> reviewed price-ready coverage after capped run proof"
        elif lane.workflow_mode in {"locked_manual", "optional_source_ladder"}:
            move = "locked optional context -> partial/ready only after trusted local/provider rows are reviewed"
        else:
            move = "blocked/partial analysis lane -> supported only after source proof and rebuilt readiness"
        rows.append(
            CoverageFrontierOpportunity(
                rank=rank,
                lane=lane.lane,
                label=lane.label,
                unlock_impact=lane.unlock_impact,
                possible_state_move=move,
                source_lane=lane.source_lane,
                workflow_mode=lane.workflow_mode,
                next_safe_command=lane.next_safe_command,
                proof_command=lane.proof_command,
                generated_churn_policy=lane.generated_churn_policy,
                guardrail="This rank is an operations queue, not a security recommendation or evidence that data is already available.",
                reviewed_proof_status=lane.reviewed_proof_status,
            )
        )
    return rows


def _expansion_batch_scope(lane: ReadinessLane) -> str:
    if lane.workflow_mode == "source_activation_required":
        return "source activation setup only; do not run provider refresh, import, apply, or broad batch commands"
    if lane.lane == "price_coverage":
        return "broad capped missing-price batches; dry-run first; no ticker-by-ticker loop by default"
    if lane.lane == "fundamentals_dcf":
        return "SEC-stageable or trusted-manual fundamentals rows for a capped reviewed company set"
    if lane.lane == "share_count_proof":
        return "capped DCF blockers where shares_outstanding is the gating input; source proof first"
    if lane.lane == "peer_mapping":
        return "source-backed peer relationships for capped peer blockers; mapping before valuation inputs"
    if lane.lane == "peer_valuation_inputs":
        return "mapped-peer price, fundamentals, market-cap, or valuation-input proof after mappings exist"
    if lane.workflow_mode in {"locked_manual", "optional_source_ladder"}:
        return "optional trusted-local or provider-assisted rows only; keep locked until reviewed rows pass gates"
    return "readiness lane review only"


def _expansion_next_command(lane: ReadinessLane) -> str:
    if lane.workflow_mode == "source_activation_required":
        return lane.next_safe_command
    if lane.lane == "fundamentals_dcf":
        return "make fundamentals-batch-proof TOP_N=10"
    if lane.lane == "share_count_proof":
        return "make share-count-proof-queue TOP_N=10"
    if lane.lane in {"peer_mapping", "peer_valuation_inputs"}:
        return "make peer-batch-proof TOP_N=10"
    return lane.next_safe_command


def _expansion_review_gate(lane: ReadinessLane) -> str:
    if lane.workflow_mode == "source_activation_required":
        return "configure at least one provider key or reviewed local source path, then rerun make session-source-preflight"
    if lane.lane == "price_coverage":
        return "review dry-run tickers, provider/source notes, expected artifacts, and save readiness snapshot before any real capped refresh"
    if lane.lane == "fundamentals_dcf":
        return "verify SEC_USER_AGENT or trusted manual source proof, then require imports-validate, imports-preview, rejected-row review, and reviewed apply decision"
    if lane.lane == "share_count_proof":
        return "verify SEC/manual source proof for shares_outstanding, then require imports-validate, imports-preview, rejected-row review, and reviewed apply decision"
    if lane.lane == "peer_mapping":
        return "verify source-backed peer relationships; sector or industry similarity stays fallback context, not trusted peer mapping"
    if lane.lane == "peer_valuation_inputs":
        return "verify mapped peers have trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears"
    if lane.workflow_mode in {"locked_manual", "optional_source_ladder"}:
        return "do not unlock optional context unless trusted local or reviewed provider-assisted earnings/estimate rows pass validate and preview"
    return "review readiness state and proof notes before changing local files"


def _expansion_stop_condition(lane: ReadinessLane) -> str:
    if lane.workflow_mode == "source_activation_required":
        return "stop before coverage expansion while SEC/Yahoo are unavailable, keyed providers are missing, and local rows do not fix blockers"
    if lane.lane == "price_coverage":
        return "stop if the dry run has unexpected scope, provider failures, or source rows that cannot be reviewed"
    if lane.lane == "fundamentals_dcf":
        return "stop if SEC staging is not configured, source proof is missing, validation fails, or preview/rejected rows are unresolved"
    if lane.lane == "share_count_proof":
        return "stop if shares_outstanding is unavailable from SEC/manual proof or would be inferred from price, market cap, peers, or placeholders"
    if lane.lane == "peer_mapping":
        return "stop if peer relationships are guessed, undocumented, self-peers only, or not source-backed"
    if lane.lane == "peer_valuation_inputs":
        return "stop if mapped peers lack trusted fundamentals, market-cap, price, or valuation-input rows"
    if lane.workflow_mode in {"locked_manual", "optional_source_ladder"}:
        return "stop if no trusted local/provider rows pass review; locked optional context is the correct state"
    return "stop if proof would rely on inferred or stale data"


def _expansion_outcome_boundary(lane: ReadinessLane) -> str:
    if lane.workflow_mode == "source_activation_required":
        return "coverage expansion resumes only after source activation preflight shows an executable path"
    if lane.lane == "price_coverage":
        return "price readiness can unlock setup, risk, liquidity, and benchmark review; it does not unlock fundamentals or valuation by itself"
    if lane.lane == "fundamentals_dcf":
        return "fundamentals can unlock DCF only after required trusted fields are present; no placeholder revenue, FCF, margin, shares, or market context"
    if lane.lane == "share_count_proof":
        return "share-count proof can unlock DCF only when all other required DCF inputs are ready; it does not create valuation by itself"
    if lane.lane == "peer_mapping":
        return "peer mappings can unlock peer trend setup, but peer valuation remains blocked until mapped-peer inputs exist"
    if lane.lane == "peer_valuation_inputs":
        return "peer valuation dispersion appears only when peer input readiness passes; sector fallback remains context only"
    if lane.workflow_mode in {"locked_manual", "optional_source_ladder"}:
        return "earnings and analyst estimates are optional review context, not required analysis inputs or auto-unlocks"
    return "excluded or unsupported states remain visible"


def build_data_coverage_expansion_plan(
    lanes: list[ReadinessLane],
    *,
    top_n: int = 10,
) -> list[DataCoverageExpansionStep]:
    frontier = build_coverage_frontier(lanes, top_n=top_n)
    lane_by_name = {lane.lane: lane for lane in lanes}
    steps: list[DataCoverageExpansionStep] = []
    for row in frontier:
        lane = lane_by_name.get(row.lane)
        if lane is None:
            continue
        steps.append(
            DataCoverageExpansionStep(
                step=len(steps) + 1,
                lane=lane.lane,
                label=lane.label,
                workflow_mode=lane.workflow_mode,
                batch_scope=_expansion_batch_scope(lane),
                next_safe_command=_expansion_next_command(lane),
                review_gate=_expansion_review_gate(lane),
                proof_command=lane.proof_command,
                stop_condition=_expansion_stop_condition(lane),
                generated_churn_policy=lane.generated_churn_policy,
                outcome_boundary=_expansion_outcome_boundary(lane),
            )
        )
    return steps


def _configured_risk_free_rate(root: Path) -> float:
    from src.config import AppConfig

    try:
        config = AppConfig.load(root / "config.yaml")
    except FileNotFoundError:
        return 0.0
    return config.get_pct("risk_rules", "annual_risk_free_rate_pct", 0.0)


def _queue_state(*, ready: int, partial: int = 0, blocked: int = 0, excluded: int = 0) -> str:
    return _lane_state(ready=ready, partial=partial, blocked=blocked, excluded=excluded)


def _metric_queue_rollup(root: Path, *, top_n: int) -> ReadinessQueueRow:
    from src.providers.local_market_data import LocalCSVMarketDataProvider
    from src.review_metrics import build_metric_readiness_board

    provider = LocalCSVMarketDataProvider(base_dir=root, data_dir=root / "data")
    rows = build_metric_readiness_board(
        root,
        provider,
        benchmarks=["SPY", "QQQ"],
        annual_risk_free_rate=_configured_risk_free_rate(root),
        top_n=top_n,
    )
    if not rows:
        return ReadinessQueueRow(
            lane="metrics_readiness",
            label="Metrics Readiness",
            readiness_state="blocked",
            ready_count=0,
            partial_count=0,
            blocked_count=0,
            excluded_count=0,
            total_count=0,
            top_missing_input_families="metric-readiness rows unavailable",
            source_mode="local_readiness",
            source_lane="review_metrics",
            next_safe_command="make metric-readiness-board TOP_N=10",
            proof_gate="Run metric-readiness after local price and readiness artifacts exist.",
            guardrail="Review metrics are historical readiness outputs, not rankings or recommendations.",
        )
    ready = sum(1 for row in rows if row.overall_state == "ready")
    partial = sum(1 for row in rows if row.overall_state == "partial")
    blocked = sum(1 for row in rows if row.overall_state == "blocked")
    excluded = sum(1 for row in rows if row.overall_state == "excluded")
    family_counts: dict[str, int] = {}
    for row in rows:
        family = row.blocker_family or "none"
        if family == "none":
            continue
        family_counts[family] = family_counts.get(family, 0) + 1
    top_families = ", ".join(
        f"{family}: {count}"
        for family, count in sorted(family_counts.items(), key=lambda item: (-item[1], item[0]))[:4]
    )
    if not top_families:
        top_families = "none"
    first_action = next((row.next_action for row in rows if row.top_blocker and row.top_blocker != "none"), "")
    return ReadinessQueueRow(
        lane="metrics_readiness",
        label="Metrics Readiness",
        readiness_state=_queue_state(ready=ready, partial=partial, blocked=blocked, excluded=excluded),
        ready_count=ready,
        partial_count=partial,
        blocked_count=blocked,
        excluded_count=excluded,
        total_count=len(rows),
        top_missing_input_families=top_families,
        source_mode="local_readiness",
        source_lane="review_metrics",
        next_safe_command=first_action or "make metric-readiness-board TOP_N=10",
        proof_gate=(
            "SPY/QQQ benchmark, risk, fundamentals trend, valuation multiples, and peer dispersion metrics "
            "stay ready, partial, blocked, or excluded from trusted local inputs."
        ),
        guardrail="Sharpe, Sortino, beta, drawdown, trend, multiples, and peer dispersion are review metrics only.",
    )


def _queue_row_from_lane(
    lane: ReadinessLane,
    *,
    top_missing_input_families: str,
    source_mode: str,
    proof_gate: str,
) -> ReadinessQueueRow:
    return ReadinessQueueRow(
        lane=lane.lane,
        label=lane.label,
        readiness_state=lane.readiness_state,
        ready_count=lane.ready_count,
        partial_count=lane.partial_count,
        blocked_count=lane.blocked_count,
        excluded_count=lane.excluded_count,
        total_count=lane.total_count,
        top_missing_input_families=top_missing_input_families,
        source_mode=source_mode,
        source_lane=lane.source_lane,
        next_safe_command=lane.next_safe_command,
        proof_gate=proof_gate,
        guardrail="Readiness queue only; no investment advice, rankings, trade instructions, or fabricated unlocks.",
    )


def build_fundamentals_peer_metrics_queue(
    root: Path | str = ".",
    *,
    top_n: int = 10,
) -> list[ReadinessQueueRow]:
    root = Path(root)
    return build_fundamentals_peer_metrics_queue_from_lanes(
        build_readiness_ops_lanes(root),
        root=root,
        top_n=top_n,
    )


def build_fundamentals_peer_metrics_queue_from_lanes(
    lanes: list[ReadinessLane] | tuple[ReadinessLane, ...],
    *,
    root: Path | str = ".",
    top_n: int = 10,
) -> list[ReadinessQueueRow]:
    root = Path(root)
    lanes_by_key = {lane.lane: lane for lane in lanes}
    rows: list[ReadinessQueueRow] = []
    fundamentals = lanes_by_key.get("fundamentals_dcf")
    if fundamentals is not None:
        rows.append(
            _queue_row_from_lane(
                fundamentals,
                top_missing_input_families=(
                    "exact DCF input families via make dcf-input-proof-queue TOP_N=25; "
                    "trusted fundamentals, dated revenue, free cash flow, FCF margin, shares outstanding"
                ),
                source_mode="SEC-stageable or trusted-local",
                proof_gate="Validate -> preview -> rejected-row review -> apply only reviewed trusted rows -> rebuild readiness.",
            )
        )
    peer_mapping = lanes_by_key.get("peer_mapping")
    if peer_mapping is not None:
        rows.append(
            _queue_row_from_lane(
                peer_mapping,
                top_missing_input_families="source-backed peer mappings",
                source_mode="manual/source-reviewed",
                proof_gate="Peer relationships need source proof; sector similarity remains fallback context only.",
            )
        )
    peer_inputs = lanes_by_key.get("peer_valuation_inputs")
    if peer_inputs is not None:
        rows.append(
            _queue_row_from_lane(
                peer_inputs,
                top_missing_input_families="mapped peer prices, market cap, fundamentals, valuation inputs",
                source_mode="trusted mapped-peer inputs",
                proof_gate="Mapped peers need trusted input rows before peer valuation dispersion can appear.",
            )
        )
    rows.append(_metric_queue_rollup(root, top_n=top_n))
    for lane_name, missing_inputs in (
        ("earnings_locked", "trusted local or provider-assisted earnings rows"),
        ("analyst_estimates_locked", "trusted local or provider-assisted analyst-estimate rows"),
    ):
        lane = lanes_by_key.get(lane_name)
        if lane is not None:
            rows.append(
                _queue_row_from_lane(
                    lane,
                    top_missing_input_families=missing_inputs,
                    source_mode="optional source ladder plus trusted-local fallback",
                    proof_gate="Optional context stays locked unless reviewed local/provider rows exist and pass validate/preview gates.",
                )
            )
    return rows


def render_data_coverage_expansion_plan(steps: list[DataCoverageExpansionStep]) -> str:
    lines = [
        "Data Coverage Expansion Planner",
        "Read-only: repeatable lane batches, not ticker-by-ticker work. This command does not refresh, import, apply, or rewrite local data.",
        "Research-only: planning data readiness coverage does not create security rankings, investment advice, or trade instructions.",
        "",
    ]
    if not steps:
        lines.append("No expansion steps are available. Run make readiness before using the planner if saved reports are missing.")
        return "\n".join(lines)
    for step in steps:
        lines.extend(
            [
                f"{step.step}. {step.label} | {step.workflow_mode}",
                f"   batch_scope: {step.batch_scope}",
                f"   next_safe_command: {step.next_safe_command}",
                f"   review_gate: {step.review_gate}",
                f"   proof_command: {step.proof_command}",
                f"   stop_condition: {step.stop_condition}",
                f"   generated_churn_policy: {step.generated_churn_policy}",
                f"   outcome_boundary: {step.outcome_boundary}",
            ]
        )
    return "\n".join(lines)


def _top_family(rows: list[object], *, fallback: str = "shares_outstanding") -> str:
    counts: dict[str, int] = {}
    for row in rows:
        family = str(getattr(row, "missing_input_family", "") or "").strip()
        if not family:
            continue
        counts[family] = counts.get(family, 0) + 1
    if not counts:
        return fallback
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _fundamentals_dcf_rows(rows: list[object]) -> list[object]:
    fundamentals_families = {
        "revenue",
        "free_cash_flow",
        "fcf_margin",
        "fundamentals_bundle",
        "fundamentals_bundle_plus_shares",
    }
    return [row for row in rows if str(getattr(row, "missing_input_family", "") or "") in fundamentals_families]


def _share_count_dcf_rows(rows: list[DcfInputProofRow]) -> list[DcfInputProofRow]:
    return [row for row in rows if "shares_outstanding" in str(row.missing_dcf_fields or "")]


def _share_count_only_dcf_rows(rows: list[DcfInputProofRow]) -> list[DcfInputProofRow]:
    return [
        row
        for row in rows
        if row.missing_input_family == "shares_outstanding"
        and str(row.dcf_input_status or "").startswith("single-input blocker")
    ]


def build_data_coverage_proof_queues(
    root: Path | str = ".",
    *,
    top_n: int = 10,
) -> list[DataCoverageProofQueueRow]:
    """Build the post-price proof queues without refreshing or applying local data."""

    root = Path(root)
    dcf_rows = build_dcf_input_proof_queue_from_files(root, top_n=100000)
    share_count_rows = _share_count_dcf_rows(dcf_rows)
    fundamentals_rows = _fundamentals_dcf_rows(dcf_rows)
    top_family = _top_family(fundamentals_rows or dcf_rows, fallback="shares_outstanding")
    peer_summary = build_peer_readiness_summary(root)
    lanes = build_readiness_ops_lanes(root, dcf_input_rows=dcf_rows, share_count_rows=share_count_rows, peer_summary=peer_summary)
    lanes_by_key = {lane.lane: lane for lane in lanes}
    rows: list[DataCoverageProofQueueRow] = []

    dcf_lane = lanes_by_key.get("fundamentals_dcf")
    if dcf_lane is not None:
        rows.append(
            DataCoverageProofQueueRow(
                queue_key="dcf_input_batches",
                label="DCF Input Proof Batches",
                readiness_state=dcf_lane.readiness_state,
                queued_rows=len(dcf_rows),
                ready_count=dcf_lane.ready_count,
                partial_count=dcf_lane.partial_count,
                blocked_count=dcf_lane.blocked_count,
                top_blockers=summarize_missing_input_families(dcf_rows),
                source_mode="SEC-stageable or trusted-local fundamentals rows",
                next_safe_command=f"make dcf-input-proof-queue TOP_N={top_n}",
                proof_packet_command=f"make dcf-input-proof-handoff FAMILY={top_family} TOP_N={top_n}",
                review_gate="Source proof -> validate -> preview -> rejected-row review -> reviewed apply decision -> rebuild readiness.",
                stop_rule="Stop if any required DCF input would be inferred, stale, or placeholder-backed.",
                proof_record_boundary="Record supported only after rebuilt readiness and reviewed-batch comparison prove the lane changed.",
                generated_churn_policy=dcf_lane.generated_churn_policy,
            )
        )

    share_lane = lanes_by_key.get("share_count_proof")
    if share_lane is not None:
        share_only = len(_share_count_only_dcf_rows(share_count_rows))
        rows.append(
            DataCoverageProofQueueRow(
                queue_key="shares_outstanding",
                label="Shares Outstanding Proof",
                readiness_state=share_lane.readiness_state,
                queued_rows=len(share_count_rows),
                ready_count=share_lane.ready_count,
                partial_count=share_lane.partial_count,
                blocked_count=share_lane.blocked_count,
                top_blockers=f"shares_outstanding: {len(share_count_rows)}; share-count-only blockers: {share_only}",
                source_mode="SEC/manual source proof or trusted local fundamentals rows",
                next_safe_command=f"make share-count-proof-queue TOP_N={top_n}",
                proof_packet_command=f"DRY_RUN=1 make reviewed-batch LANE=share_count TOP_N={top_n}",
                review_gate="Use SEC/manual source proof, then imports-validate and imports-preview before any apply decision.",
                stop_rule="Stop if shares outstanding would be inferred from price, market cap, peers, or placeholders.",
                proof_record_boundary="Use the reviewed-batch proof record only after source files, changed counts, changed tickers, and artifact review are filled.",
                generated_churn_policy=share_lane.generated_churn_policy,
            )
        )

    if dcf_lane is not None:
        rows.append(
            DataCoverageProofQueueRow(
                queue_key="trusted_fundamentals",
                label="Trusted Fundamentals Proof Queue",
                readiness_state=dcf_lane.readiness_state,
                queued_rows=len(fundamentals_rows),
                ready_count=dcf_lane.ready_count,
                partial_count=dcf_lane.partial_count,
                blocked_count=dcf_lane.blocked_count,
                top_blockers=summarize_missing_input_families(fundamentals_rows),
                source_mode="SEC-stageable or trusted local revenue, free cash flow, FCF margin, and shares rows",
                next_safe_command=f"make dcf-input-source-command-plan FAMILY={top_family} TOP_N={top_n}",
                proof_packet_command=f"DRY_RUN=1 make fundamentals-batch-proof TOP_N={top_n}",
                review_gate="Do not edit import rows until source-review fields are filled and the guard can preview a row.",
                stop_rule="Stop if revenue, free cash flow, FCF margin, or share-count proof is unavailable.",
                proof_record_boundary="Keep proof-record commands dry-run until validation, preview, apply result, source files, and generated-artifact review are complete.",
                generated_churn_policy=dcf_lane.generated_churn_policy,
            )
        )

    peer_mapping_lane = lanes_by_key.get("peer_mapping")
    if peer_mapping_lane is not None:
        rows.append(
            DataCoverageProofQueueRow(
                queue_key="peer_mapping",
                label="Peer Mapping Proof Queue",
                readiness_state=peer_mapping_lane.readiness_state,
                queued_rows=peer_summary.missing_mapping or peer_mapping_lane.blocked_count,
                ready_count=peer_mapping_lane.ready_count,
                partial_count=peer_mapping_lane.partial_count,
                blocked_count=peer_mapping_lane.blocked_count,
                top_blockers=f"source-backed peer mappings: {peer_summary.missing_mapping or peer_mapping_lane.blocked_count}",
                source_mode="manual/source-reviewed peer relationships",
                next_safe_command=f"DRY_RUN=1 make peer-mapping-source-review TOP_N={top_n}",
                proof_packet_command=f"DRY_RUN=1 make peer-batch-proof TOP_N={top_n}",
                review_gate="Peer relationships need source proof; sector or theme similarity stays fallback context only.",
                stop_rule="Stop if peer rows are guessed, self-peers, duplicates, undocumented, or stale.",
                proof_record_boundary="Use the peer write-back guard and reviewed-batch proof record only after validate, preview, readiness, and artifact review.",
                generated_churn_policy=peer_mapping_lane.generated_churn_policy,
            )
        )

    peer_input_lane = lanes_by_key.get("peer_valuation_inputs")
    if peer_input_lane is not None:
        rows.append(
            DataCoverageProofQueueRow(
                queue_key="peer_valuation_inputs",
                label="Peer Valuation Input Proof Queue",
                readiness_state=peer_input_lane.readiness_state,
                queued_rows=peer_summary.valuation_input_blockers or peer_input_lane.blocked_count,
                ready_count=peer_input_lane.ready_count,
                partial_count=peer_input_lane.partial_count,
                blocked_count=peer_input_lane.blocked_count,
                top_blockers=(
                    f"peer prices: {peer_summary.missing_peer_price}; "
                    f"peer fundamentals: {peer_summary.missing_peer_fundamentals}; "
                    f"mapped-peer valuation blockers: {peer_summary.peer_valuation_blocked}"
                ),
                source_mode="trusted mapped-peer prices, fundamentals, market cap, and valuation inputs",
                next_safe_command="make peer-mapping-queue TOP_N=25",
                proof_packet_command=f"DRY_RUN=1 make peer-batch-proof TOP_N={top_n}",
                review_gate="Peer valuation appears only after mapped peers and trusted peer inputs pass readiness.",
                stop_rule="Stop if mapped peers lack trusted price, market-cap, fundamentals, or valuation-input rows.",
                proof_record_boundary="Record still_blocked when mappings exist but peer valuation inputs remain missing.",
                generated_churn_policy=peer_input_lane.generated_churn_policy,
            )
        )
    return rows


def render_data_coverage_proof_queues(rows: list[DataCoverageProofQueueRow]) -> str:
    lines = [
        "Data Coverage Proof Queues",
        "Read-only: this queue portfolio does not refresh data, apply imports, record proof, or rewrite local CSVs.",
        "Research-only: these are data-readiness proof queues, not rankings, recommendations, or trade instructions.",
        "",
    ]
    if not rows:
        lines.append("No proof queues are available. Run make readiness before relying on data-coverage queue counts.")
        return "\n".join(lines)
    lines.append(
        "Queue | State | Queued | Ready | Partial | Blocked | Top blockers | Next safe command | Proof packet"
    )
    lines.append("--- | --- | ---: | ---: | ---: | ---: | --- | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    row.label,
                    row.readiness_state,
                    str(row.queued_rows),
                    str(row.ready_count),
                    str(row.partial_count),
                    str(row.blocked_count),
                    row.top_blockers,
                    row.next_safe_command,
                    row.proof_packet_command,
                ]
            )
        )
    lines.append("")
    lines.append("Review gates and stop rules:")
    for row in rows:
        lines.append(f"- {row.label}: {row.review_gate} Stop rule: {row.stop_rule}")
    lines.append("")
    lines.append("Proof-record boundaries:")
    for row in rows:
        lines.append(f"- {row.label}: {row.proof_record_boundary}")
    lines.append("")
    lines.append("Generated-artifact policy:")
    for row in rows:
        lines.append(f"- {row.label}: {row.generated_churn_policy}")
    lines.append("")
    lines.append("Guardrail: missing inputs remain blocked; do not fabricate fundamentals, shares, market cap, peers, or valuation inputs.")
    return "\n".join(lines)


def render_fundamentals_peer_metrics_queue(rows: list[ReadinessQueueRow]) -> str:
    lines = [
        "Fundamentals, Peer, and Metrics Readiness Queue",
        "Read-only: queue-level blocker summary across DCF, peer, optional context, and SPY/QQQ review metrics.",
        "Research-only: this is data-readiness triage, not a ranking, recommendation, or trade instruction.",
        "",
    ]
    if not rows:
        lines.append("No queue rows are available. Run make readiness before relying on exact counts.")
        return "\n".join(lines)
    lines.append(
        "Lane | State | Ready | Partial | Blocked | Excluded | Missing input families | Source mode | Next proof"
    )
    lines.append("--- | --- | ---: | ---: | ---: | ---: | --- | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    row.label,
                    row.readiness_state,
                    str(row.ready_count),
                    str(row.partial_count),
                    str(row.blocked_count),
                    str(row.excluded_count),
                    row.top_missing_input_families,
                    row.source_mode,
                    row.next_safe_command,
                ]
            )
        )
    lines.append("")
    lines.append("Proof gates:")
    for row in rows:
        lines.append(f"- {row.label}: {row.proof_gate}")
    lines.append("")
    lines.append("Lane guardrails:")
    for row in rows:
        lines.append(f"- {row.label}: {row.guardrail}")
    lines.append("")
    lines.append("Guardrail: missing inputs stay blocked or locked; do not infer fundamentals, market cap, peers, or metric values.")
    return "\n".join(lines)


def render_readiness_ops_center(lanes: list[ReadinessLane]) -> str:
    lines = [
        "Data Readiness Operations Center",
        "Read-only: lane-level operations view. It does not refresh, import, apply, or rewrite local data.",
        "Research-only: lanes show data readiness and proof commands, not investment advice or trade instructions.",
        "",
    ]
    for lane in lanes:
        lines.extend(
            [
                f"- {lane.label} | {lane.readiness_state} | {lane.workflow_mode}",
                f"  counts: ready={lane.ready_count}; partial={lane.partial_count}; blocked={lane.blocked_count}; excluded={lane.excluded_count}; total={lane.total_count}",
                f"  unlock_impact: {lane.unlock_impact}",
                f"  source_lane: {lane.source_lane}; source_readiness: {lane.source_readiness}",
                f"  next_safe_command: {lane.next_safe_command}",
                f"  proof_command: {lane.proof_command}",
                f"  generated_churn_policy: {lane.generated_churn_policy}",
                f"  proof_freshness: {lane.stale_proof_warning}",
                f"  notes: {lane.notes}",
            ]
        )
    return "\n".join(lines)


def render_coverage_frontier(frontier: list[CoverageFrontierOpportunity]) -> str:
    lines = [
        "Coverage Frontier Planner",
        "Read-only: ranks batch data-readiness opportunities by unlock impact. It does not imply data is available.",
        "Research-only: this is an operations queue, not investment advice or trade instruction.",
        "",
    ]
    if not frontier:
        lines.append("No coverage frontier rows are available. Run make readiness first if saved reports are missing.")
        return "\n".join(lines)
    for row in frontier:
        lines.extend(
            [
                f"{row.rank}. {row.label} | unlock_impact={row.unlock_impact} | {row.workflow_mode}",
                f"   possible_state_move: {row.possible_state_move}",
                f"   source_lane: {row.source_lane}",
                f"   next_safe_command: {row.next_safe_command}",
                f"   proof_command: {row.proof_command}",
                f"   generated_churn_policy: {row.generated_churn_policy}",
                f"   guardrail: {row.guardrail}",
            ]
        )
        if row.reviewed_proof_status:
            lines.append(f"   reviewed_proof_status: {row.reviewed_proof_status}")
    return "\n".join(lines)


def render_readiness_ops_evidence(lanes: list[ReadinessLane], frontier: list[CoverageFrontierOpportunity]) -> str:
    latest = frontier[0] if frontier else None
    lines = [
        "Readiness Ops Evidence",
        "Durable proof checklist for broad lane operations.",
        "",
        f"- lane_count: {len(lanes)}",
        f"- frontier_count: {len(frontier)}",
        f"- top_frontier_lane: {latest.label if latest else '-'}",
        f"- top_frontier_command: {latest.next_safe_command if latest else '-'}",
        "- proof_required_before_supported: source proof, validation, preview, rejected-row review, apply when appropriate, rebuilt readiness, and reviewed proof row.",
        "- generated_churn_policy: broad CSV/JSON churn stays out of commits unless intentionally reviewed evidence.",
        "- locked_lanes: earnings and analyst estimates remain locked unless trusted local/provider rows pass import review.",
        "- excluded_lanes: non-company DCF exclusion remains excluded/not applicable, not failed.",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print read-only readiness operations views.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--coverage-frontier", action="store_true", help="Print coverage frontier planner.")
    parser.add_argument("--expansion-plan", action="store_true", help="Print repeatable data coverage expansion plan.")
    parser.add_argument("--coverage-proof-queues", action="store_true", help="Print DCF/fundamentals/peer proof queue portfolio.")
    parser.add_argument("--readiness-queue", action="store_true", help="Print fundamentals, peer, and metrics readiness queue.")
    parser.add_argument("--evidence", action="store_true", help="Print readiness ops evidence checklist.")
    parser.add_argument("--top-n", type=int, default=10)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root)
    if args.evidence:
        lanes = build_readiness_ops_lanes(root)
        frontier = build_coverage_frontier(lanes, top_n=args.top_n)
        print(render_readiness_ops_evidence(lanes, frontier))
    elif args.coverage_proof_queues:
        print(render_data_coverage_proof_queues(build_data_coverage_proof_queues(root, top_n=args.top_n)))
    elif args.readiness_queue:
        print(render_fundamentals_peer_metrics_queue(build_fundamentals_peer_metrics_queue(root, top_n=args.top_n)))
    elif args.expansion_plan:
        lanes = build_readiness_ops_lanes(root)
        print(render_data_coverage_expansion_plan(build_data_coverage_expansion_plan(lanes, top_n=args.top_n)))
    elif args.coverage_frontier:
        lanes = build_readiness_ops_lanes(root)
        frontier = build_coverage_frontier(lanes, top_n=args.top_n)
        print(render_coverage_frontier(frontier))
    else:
        lanes = build_readiness_ops_lanes(root)
        print(render_readiness_ops_center(lanes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
