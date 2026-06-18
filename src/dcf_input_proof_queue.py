"""DCF input proof queue for missing valuation inputs.

This read-only queue explains which specific DCF input family blocks each
company before any valuation section can appear. It does not refresh data,
apply imports, infer missing inputs, or create investment conclusions.
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
from src.reviewed_batch_command_builder import shell_assignment


QUEUE_COLUMNS = [
    "priority",
    "ticker",
    "scope",
    "missing_input_family",
    "missing_dcf_fields",
    "ready_dcf_inputs",
    "dcf_input_status",
    "source_mode",
    "next_safe_command",
    "proof_packet_command",
    "validation_sequence",
    "proof_after_update",
    "stop_rule",
    "source_note",
]

HANDOFF_COLUMNS = [
    "input_family",
    "tickers",
    "selected_rows",
    "lane",
    "proof_packet_command",
    "validation_command",
    "preview_command",
    "apply_boundary",
    "post_run_proof_command",
    "compare_command",
    "proof_record_scaffold",
    "stop_rule",
    "record_boundary",
]

SOURCE_REVIEW_COLUMNS = [
    "ticker",
    "input_family",
    "missing_dcf_fields",
    "target_file",
    "source_type",
    "source_file_or_url",
    "source_as_of_date",
    "reviewer",
    "review_date",
    "source_proof_status",
    "validation_result",
    "preview_result",
    "apply_decision",
    "completion_status",
    "missing_review_fields",
    "import_row_scaffold",
    "next_safe_action",
    "do_not_proceed_if",
]

SOURCE_GUARD_COLUMNS = [
    "status",
    "ticker",
    "input_family",
    "blocking_reasons",
    "csv_header",
    "csv_row",
    "target_file",
    "validation_command",
    "preview_command",
    "apply_boundary",
    "post_apply_proof",
    "proof_record_boundary",
]

SOURCE_COMMAND_PLAN_COLUMNS = [
    "step",
    "status",
    "command",
    "fields_to_fill",
    "review_boundary",
]

REQUIRED_SOURCE_REVIEW_FIELDS = (
    "source_type",
    "source_file_or_url",
    "source_as_of_date",
    "reviewer",
    "review_date",
    "source_proof_status",
    "validation_result",
    "preview_result",
    "apply_decision",
)

READY_SOURCE_PROOF_STATUSES = {"reviewed", "supported", "source_backed", "source-backed"}
READY_GATE_VALUES = {"pass", "passed", "reviewed", "ready", "not_applicable_read_only", "skipped_after_review"}
FUNDAMENTALS_IMPORT_COLUMNS = (
    "ticker",
    "period",
    "revenue",
    "free_cash_flow",
    "fcf_margin",
    "shares_outstanding",
    "source",
    "as_of_date",
)

DCF_FIELD_LABELS = {
    "free_cash_flow": "free cash flow",
    "shares_outstanding": "shares outstanding",
    "revenue": "revenue",
    "fcf_margin": "FCF margin",
    "price": "price",
}

FIELD_PRIORITY = {
    "shares_outstanding": 0,
    "free_cash_flow": 1,
    "revenue": 2,
    "fcf_margin": 3,
    "price": 4,
}


@dataclass(frozen=True)
class DcfInputProofRow:
    priority: int
    ticker: str
    scope: str
    missing_input_family: str
    missing_dcf_fields: str
    ready_dcf_inputs: str
    dcf_input_status: str
    source_mode: str
    next_safe_command: str
    proof_packet_command: str
    validation_sequence: str
    proof_after_update: str
    stop_rule: str
    source_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DcfInputProofHandoff:
    input_family: str
    tickers: str
    selected_rows: int
    lane: str
    proof_packet_command: str
    validation_command: str
    preview_command: str
    apply_boundary: str
    post_run_proof_command: str
    compare_command: str
    proof_record_scaffold: str
    stop_rule: str
    record_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DcfInputSourceReviewRow:
    ticker: str
    input_family: str
    missing_dcf_fields: str
    target_file: str
    source_type: str
    source_file_or_url: str
    source_as_of_date: str
    reviewer: str
    review_date: str
    source_proof_status: str
    validation_result: str
    preview_result: str
    apply_decision: str
    completion_status: str
    missing_review_fields: str
    import_row_scaffold: str
    next_safe_action: str
    do_not_proceed_if: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DcfInputSourceGuard:
    status: str
    ticker: str
    input_family: str
    blocking_reasons: tuple[str, ...]
    csv_header: str
    csv_row: str
    target_file: str
    validation_command: str
    preview_command: str
    apply_boundary: str
    post_apply_proof: str
    proof_record_boundary: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocking_reasons"] = ", ".join(self.blocking_reasons)
        return data


@dataclass(frozen=True)
class DcfInputSourceCommandPlan:
    step: str
    status: str
    command: str
    fields_to_fill: str
    review_boundary: str

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
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _split_fields(value: object) -> list[str]:
    fields: list[str] = []
    for part in str(value or "").replace("|", ",").replace(";", ",").split(","):
        field = part.strip()
        if field:
            fields.append(field)
    return fields


def _display_fields(fields: list[str]) -> str:
    if not fields:
        return "-"
    return ", ".join(fields)


def _is_placeholder(value: object) -> bool:
    text = str(value or "").strip()
    if not text or text in {"-", "not recorded"}:
        return True
    return text.startswith("<") and text.endswith(">")


def _csv_row(values: list[object]) -> str:
    escaped = []
    for value in values:
        text = str(value or "").strip()
        if "," in text or '"' in text:
            text = '"' + text.replace('"', '""') + '"'
        escaped.append(text)
    return ",".join(escaped)


def _ready_inputs(row: pd.Series) -> list[str]:
    checks = [
        ("free_cash_flow", "has_free_cash_flow"),
        ("shares_outstanding", "has_shares_outstanding"),
        ("revenue", "has_revenue"),
        ("fcf_margin", "has_fcf_margin"),
        ("price", "has_price"),
    ]
    return [field for field, column in checks if _truthy(row.get(column))]


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


def _missing_input_family(fields: list[str]) -> str:
    field_set = set(fields)
    if not fields:
        return "none"
    if field_set == {"shares_outstanding"}:
        return "shares_outstanding"
    if field_set == {"price"}:
        return "price"
    if field_set == {"fcf_margin"}:
        return "fcf_margin"
    if field_set == {"free_cash_flow"}:
        return "free_cash_flow"
    if field_set == {"revenue"}:
        return "revenue"
    if "shares_outstanding" in field_set and len(field_set) > 1:
        return "fundamentals_bundle_plus_shares"
    if field_set & {"free_cash_flow", "revenue", "fcf_margin"}:
        return "fundamentals_bundle"
    return "other_dcf_input"


def _dcf_input_status(fields: list[str], ready_fields: list[str]) -> str:
    if len(fields) == 1:
        return f"single-input blocker: {fields[0]}"
    return f"input bundle blocker: {_display_fields(fields)}; ready inputs: {_display_fields(ready_fields)}"


def _source_mode(family: str, *, sec_configured: bool) -> str:
    if family == "price":
        return "price dry-run first"
    if sec_configured:
        return "SEC-stageable or trusted-local"
    return "trusted-local/manual; configure SEC_USER_AGENT for SEC staging"


def _next_safe_command(ticker: str, family: str) -> str:
    if family == "price":
        return f"make price-worklist TICKERS={ticker}"
    if family == "shares_outstanding":
        return f"make share-count-proof-queue TICKERS={ticker}"
    return f"make focus-fundamentals TICKER={ticker}"


def _proof_packet_command(ticker: str, family: str) -> str:
    if family == "price":
        return f"make reviewed-batch LANE=prices TICKERS={ticker} DRY_RUN=1"
    if family == "shares_outstanding":
        return f"DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS={ticker}"
    return f"DRY_RUN=1 make fundamentals-batch-proof TICKERS={ticker}"


def _validation_sequence(family: str) -> str:
    if family == "price":
        return "dry-run -> reviewed capped refresh/import -> make price-validate -> make price-preview -> reviewed apply"
    return "make imports-validate -> make imports-preview -> rejected-row review -> make imports-apply"


def _proof_after_update(ticker: str, family: str) -> str:
    if family == "price":
        return f"make price-coverage TOP_N=25 && make readiness && make stock-report-md TICKER={ticker}"
    return f"make dcf-readiness && make readiness && make stock-report-md TICKER={ticker}"


def _stop_rule(family: str) -> str:
    if family == "price":
        return "Stop if price rows cannot be source-reviewed or the refresh/import scope is broader than the reviewed cap."
    if family == "shares_outstanding":
        return (
            "Stop if shares_outstanding is unavailable from SEC/manual source proof; do not infer it from price, market cap, "
            "peers, or placeholder rows."
        )
    return (
        "Stop if trusted source rows do not prove the required revenue, free cash flow, FCF margin, and share-count fields; "
        "missing inputs must stay blocked."
    )


def _lane_for_family(family: str) -> str:
    if family == "price":
        return "prices"
    if family == "shares_outstanding":
        return "share_count"
    return "fundamentals"


def _family_packet_command(tickers: list[str], family: str) -> str:
    ticker_arg = ",".join(tickers) if tickers else "<reviewed_tickers>"
    lane = _lane_for_family(family)
    if lane == "prices":
        return f"DRY_RUN=1 make reviewed-batch LANE=prices TICKERS={ticker_arg}"
    if lane == "share_count":
        return f"DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS={ticker_arg}"
    return f"DRY_RUN=1 make fundamentals-batch-proof TICKERS={ticker_arg}"


def _family_validation_command(family: str) -> str:
    if family == "price":
        return "make price-validate"
    return "make imports-validate"


def _family_preview_command(family: str) -> str:
    if family == "price":
        return "make price-preview"
    return "make imports-preview"


def _family_apply_boundary(family: str) -> str:
    if family == "price":
        return "Reviewed boundary: apply/import price rows only after dry-run scope, validation, preview, and generated-artifact review."
    return "Reviewed boundary: run make imports-apply only after source proof, validation, preview, and rejected-row review."


def _family_post_run_proof_command(tickers: list[str], family: str) -> str:
    ticker = tickers[0] if tickers else "<reviewed_ticker>"
    if family == "price":
        return f"make price-coverage TOP_N=25 && make readiness && make stock-report-md TICKER={ticker}"
    return f"make dcf-readiness && make readiness && make stock-report-md TICKER={ticker}"


def _proof_record_scaffold(*, lane: str, tickers: list[str], command_run: str) -> str:
    values = {
        "BATCH_ID": "<reviewed_batch_id>",
        "LANE": lane,
        "REVIEW_DATE": "<yyyy-mm-dd>",
        "FINAL_OUTCOME": "<supported|still_blocked|skipped|excluded>",
        "TICKERS": ",".join(tickers) if tickers else "<reviewed_tickers>",
        "COMMAND_RUN": command_run,
        "VALIDATION_RESULT": "<reviewed_validation_result>",
        "PREVIEW_RESULT": "<reviewed_preview_result>",
        "APPLY_RESULT": "<reviewed_apply_result>",
        "CHANGED_READINESS_COUNTS": "<from_reviewed_batch_compare>",
        "CHANGED_TICKERS": "<from_reviewed_batch_compare>",
        "SOURCE_FILES": "<reviewed_source_files>",
        "GENERATED_ARTIFACTS_REVIEWED": "<kept_evidence_or_excluded_churn>",
    }
    assignments = " ".join(shell_assignment(name, value) for name, value in values.items())
    return f"DRY_RUN=1 make reviewed-batch-proof-record {assignments}"


def _make_assignments(values: dict[str, object]) -> str:
    return " ".join(shell_assignment(name, value) for name, value in values.items() if str(value or "").strip())


def _source_type_for_family(family: str) -> str:
    if family == "price":
        return "verified_price_file_or_provider_log"
    if family == "shares_outstanding":
        return "SEC filing or annual/quarterly report"
    return "SEC Companyfacts or reviewed company filing"


def _target_file_for_family(family: str) -> str:
    if family == "price":
        return "data/imports/prices.csv"
    return "data/imports/fundamentals.csv"


def _blank_import_row_scaffold(row: DcfInputProofRow) -> str:
    if row.missing_input_family == "price":
        return "blocked until reviewed OHLCV rows are available through the price import path"
    fields = set(_split_fields(row.missing_dcf_fields))
    values = {
        "ticker": row.ticker,
        "period": "<reviewed_period>",
        "revenue": "<reviewed_revenue>" if "revenue" in fields else "",
        "free_cash_flow": "<reviewed_free_cash_flow>" if "free_cash_flow" in fields else "",
        "fcf_margin": "<reviewed_fcf_margin>" if "fcf_margin" in fields else "",
        "shares_outstanding": "<reviewed_shares_outstanding>" if "shares_outstanding" in fields else "",
        "source": "<reviewed_source>",
        "as_of_date": "<yyyy-mm-dd>",
    }
    return _csv_row([values[column] for column in FUNDAMENTALS_IMPORT_COLUMNS])


def _reviewed_value_assignments(row: DcfInputSourceReviewRow) -> dict[str, object]:
    fields = set(_split_fields(row.missing_dcf_fields))
    values: dict[str, object] = {
        "TICKER": row.ticker,
        "FAMILY": row.input_family,
        "MISSING_DCF_FIELDS": row.missing_dcf_fields,
        "PERIOD": "<reviewed_period>",
        "SOURCE_TYPE": row.source_type,
        "SOURCE_FILE_OR_URL": row.source_file_or_url,
        "SOURCE_AS_OF_DATE": row.source_as_of_date,
        "REVIEWER": row.reviewer,
        "REVIEW_DATE": row.review_date,
        "SOURCE_PROOF_STATUS": row.source_proof_status,
        "VALIDATION_RESULT": row.validation_result,
        "PREVIEW_RESULT": row.preview_result,
        "APPLY_DECISION": row.apply_decision,
    }
    if "revenue" in fields or row.input_family in {"fundamentals_bundle", "fundamentals_bundle_plus_shares"}:
        values["REVENUE"] = "<reviewed_revenue>"
    if "free_cash_flow" in fields or row.input_family in {"fundamentals_bundle", "fundamentals_bundle_plus_shares"}:
        values["FREE_CASH_FLOW"] = "<reviewed_free_cash_flow>"
    if "fcf_margin" in fields or row.input_family in {"fundamentals_bundle", "fundamentals_bundle_plus_shares"}:
        values["FCF_MARGIN"] = "<reviewed_fcf_margin>"
    if "shares_outstanding" in fields or row.input_family in {"shares_outstanding", "fundamentals_bundle_plus_shares"}:
        values["SHARES_OUTSTANDING"] = "<reviewed_shares_outstanding>"
    return values


def _source_review_missing_fields(values: dict[str, str]) -> list[str]:
    missing = [field for field in REQUIRED_SOURCE_REVIEW_FIELDS if _is_placeholder(values.get(field))]
    proof_status = str(values.get("source_proof_status") or "").strip().lower()
    if proof_status and proof_status not in READY_SOURCE_PROOF_STATUSES and "source_proof_status" not in missing:
        missing.append("source_proof_status")
    for gate in ("validation_result", "preview_result", "apply_decision"):
        gate_value = str(values.get(gate) or "").strip().lower()
        if gate_value and gate_value not in READY_GATE_VALUES and gate not in missing:
            missing.append(gate)
    return missing


def _required_dcf_values(input_family: str, missing_dcf_fields: str) -> tuple[str, ...]:
    fields = tuple(_split_fields(missing_dcf_fields))
    if fields:
        return fields
    if input_family == "shares_outstanding":
        return ("shares_outstanding",)
    if input_family == "fcf_margin":
        return ("fcf_margin",)
    if input_family == "free_cash_flow":
        return ("free_cash_flow",)
    if input_family == "revenue":
        return ("revenue",)
    if input_family in {"fundamentals_bundle", "fundamentals_bundle_plus_shares"}:
        return ("revenue", "free_cash_flow", "fcf_margin", "shares_outstanding")
    return ()


def _numeric_or_placeholder(value: object) -> bool:
    if _is_placeholder(value):
        return False
    try:
        float(str(value).strip())
    except ValueError:
        return False
    return True


def _source_note(fields: list[str], family: str, *, sec_configured: bool) -> str:
    if family == "price":
        return "Price input is repeatable but still needs dry-run scope review before local CSV updates."
    source = "SEC staging is configured" if sec_configured else "SEC staging is not configured"
    if family == "shares_outstanding":
        return f"{source}; use SEC/manual filing proof or trusted local rows for shares_outstanding only."
    return f"{source}; review the exact DCF fields before validate/preview/apply: {_display_fields(fields)}."


def _rank(row: pd.Series, universe: pd.DataFrame) -> tuple[int, int, int, str]:
    ticker = str(row.get("ticker", "")).upper()
    scope_rank = 0 if _universe_scope(universe, ticker) == "active universe" else 1
    fields = _split_fields(row.get("missing_dcf_fields"))
    single_input_rank = 0 if len(fields) == 1 else 1
    family_rank = min((FIELD_PRIORITY.get(field, 99) for field in fields), default=99)
    return scope_rank, single_input_rank, family_rank, ticker


def build_dcf_input_proof_queue(
    *,
    universe: pd.DataFrame,
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> list[DcfInputProofRow]:
    dcf = build_dcf_readiness_frame(universe=universe, fundamentals=fundamentals, prices=prices)
    if dcf.empty:
        return []
    company = dcf.get("asset_type", pd.Series("", index=dcf.index)).astype(str).str.lower().eq("company")
    blocked = ~dcf.get("is_dcf_ready", pd.Series(False, index=dcf.index)).astype(bool)
    queue = dcf.loc[company & blocked].copy()
    if tickers:
        wanted = {ticker.upper().strip() for ticker in tickers if ticker.strip()}
        queue = queue.loc[queue["ticker"].astype(str).str.upper().isin(wanted)]
    if queue.empty:
        return []
    ranked = sorted((row for _, row in queue.iterrows()), key=lambda row: _rank(row, universe))
    rows: list[DcfInputProofRow] = []
    for row in ranked[: max(top_n, 0)]:
        ticker = str(row.get("ticker", "")).upper().strip()
        fields = _split_fields(row.get("missing_dcf_fields"))
        ready = _ready_inputs(row)
        family = _missing_input_family(fields)
        sec_configured = _truthy(row.get("sec_user_agent_configured"))
        rows.append(
            DcfInputProofRow(
                priority=len(rows) + 1,
                ticker=ticker,
                scope=_universe_scope(universe, ticker),
                missing_input_family=family,
                missing_dcf_fields=_display_fields(fields),
                ready_dcf_inputs=_display_fields(ready),
                dcf_input_status=_dcf_input_status(fields, ready),
                source_mode=_source_mode(family, sec_configured=sec_configured),
                next_safe_command=_next_safe_command(ticker, family),
                proof_packet_command=_proof_packet_command(ticker, family),
                validation_sequence=_validation_sequence(family),
                proof_after_update=_proof_after_update(ticker, family),
                stop_rule=_stop_rule(family),
                source_note=_source_note(fields, family, sec_configured=sec_configured),
            )
        )
    return rows


def build_dcf_input_proof_queue_from_files(
    root: Path,
    *,
    data_dir: Path | None = None,
    top_n: int = 10,
    tickers: list[str] | None = None,
) -> list[DcfInputProofRow]:
    data_path = resolve_data_dir(data_dir, root)
    return build_dcf_input_proof_queue(
        universe=_read_csv(data_path / "universe.csv"),
        fundamentals=_read_csv(data_path / "fundamentals.csv"),
        prices=_read_csv(data_path / "prices.csv"),
        top_n=top_n,
        tickers=tickers,
    )


def summarize_missing_input_families(rows: list[DcfInputProofRow], *, limit: int = 5) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.missing_input_family] = counts.get(row.missing_input_family, 0) + 1
    if not counts:
        return "none"
    return ", ".join(
        f"{family}: {count}"
        for family, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[: max(limit, 0)]
    )


def build_dcf_input_proof_handoff(
    rows: list[DcfInputProofRow],
    *,
    family: str | None = None,
    limit: int = 10,
) -> DcfInputProofHandoff:
    family_key = str(family or "").strip()
    if not family_key and rows:
        family_key = rows[0].missing_input_family
    selected = [row for row in rows if not family_key or row.missing_input_family == family_key]
    selected = selected[: max(limit, 0)]
    if not selected:
        empty_family = family_key or "all families"
        command_run = "make dcf-input-proof-queue TOP_N=10"
        return DcfInputProofHandoff(
            input_family=empty_family,
            tickers="<reviewed_tickers>",
            selected_rows=0,
            lane="fundamentals",
            proof_packet_command="DRY_RUN=1 make fundamentals-batch-proof TOP_N=10",
            validation_command="make imports-validate",
            preview_command="make imports-preview",
            apply_boundary="Reviewed boundary: do not apply rows until source proof, validation, preview, and rejected-row review exist.",
            post_run_proof_command="make dcf-readiness && make readiness",
            compare_command="make reviewed-batch-compare LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            proof_record_scaffold=_proof_record_scaffold(lane="fundamentals", tickers=[], command_run=command_run),
            stop_rule="Stop if the selected DCF input family has no queued blockers or source proof is unavailable.",
            record_boundary="Preview only; do not record proof until required fields replace placeholders and readiness comparison is reviewed.",
        )
    first = selected[0]
    input_family = family_key or first.missing_input_family
    tickers = [row.ticker for row in selected if row.ticker]
    lane = _lane_for_family(input_family)
    command_run = _family_packet_command(tickers, input_family)
    stop_rules = list(dict.fromkeys(row.stop_rule for row in selected if row.stop_rule))
    return DcfInputProofHandoff(
        input_family=input_family,
        tickers=",".join(tickers),
        selected_rows=len(selected),
        lane=lane,
        proof_packet_command=command_run,
        validation_command=_family_validation_command(input_family),
        preview_command=_family_preview_command(input_family),
        apply_boundary=_family_apply_boundary(input_family),
        post_run_proof_command=_family_post_run_proof_command(tickers, input_family),
        compare_command=f"make reviewed-batch-compare LANE={lane} BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
        proof_record_scaffold=_proof_record_scaffold(lane=lane, tickers=tickers, command_run=command_run),
        stop_rule=stop_rules[0] if stop_rules else _stop_rule(input_family),
        record_boundary="Copy the proof-record command only after packet review, validate/preview/apply decision, rebuilt readiness, comparison, source files, and generated-artifact review.",
    )


def build_dcf_input_source_review_rows(
    rows: list[DcfInputProofRow],
    *,
    family: str | None = None,
    limit: int = 10,
) -> list[DcfInputSourceReviewRow]:
    family_key = str(family or "").strip()
    if not family_key and rows:
        family_key = rows[0].missing_input_family
    selected = [row for row in rows if not family_key or row.missing_input_family == family_key]
    selected = selected[: max(limit, 0)]
    review_rows: list[DcfInputSourceReviewRow] = []
    for row in selected:
        values = {
            "source_type": _source_type_for_family(row.missing_input_family),
            "source_file_or_url": "<reviewed_source_file_or_url>",
            "source_as_of_date": "<yyyy-mm-dd>",
            "reviewer": "<reviewer>",
            "review_date": "<yyyy-mm-dd>",
            "source_proof_status": "<reviewed|supported|source_backed>",
            "validation_result": "<pass|not_applicable_read_only>",
            "preview_result": "<reviewed_preview_result>",
            "apply_decision": "<applied|skipped_after_review|not_applicable_read_only>",
        }
        missing = _source_review_missing_fields(values)
        completion_status = "needs_field_fills" if missing else "ready_for_validate_preview"
        next_action = (
            f"Fill {', '.join(missing)} for {row.ticker}; keep DCF blocked until reviewed source proof exists."
            if missing
            else "Review the import row scaffold, then run validate and preview before any apply decision."
        )
        review_rows.append(
            DcfInputSourceReviewRow(
                ticker=row.ticker,
                input_family=row.missing_input_family,
                missing_dcf_fields=row.missing_dcf_fields,
                target_file=_target_file_for_family(row.missing_input_family),
                source_type=values["source_type"],
                source_file_or_url=values["source_file_or_url"],
                source_as_of_date=values["source_as_of_date"],
                reviewer=values["reviewer"],
                review_date=values["review_date"],
                source_proof_status=values["source_proof_status"],
                validation_result=values["validation_result"],
                preview_result=values["preview_result"],
                apply_decision=values["apply_decision"],
                completion_status=completion_status,
                missing_review_fields=", ".join(missing),
                import_row_scaffold=_blank_import_row_scaffold(row),
                next_safe_action=next_action,
                do_not_proceed_if=row.stop_rule,
            )
        )
    return review_rows


def render_dcf_input_source_review_rows(rows: list[DcfInputSourceReviewRow]) -> str:
    lines = [
        "DCF Input Source Review Intake",
        "Read-only: this intake creates fillable proof scaffolds only; it does not apply imports or record ledger rows.",
        "Research-only: source review proves data readiness, not investment advice, broker integration, order routing, or buy/sell instructions.",
        "Do not infer revenue, free cash flow, FCF margin, shares outstanding, price, market cap, or valuation inputs.",
    ]
    if not rows:
        lines.append("No DCF source-review rows found for the selected queue/family.")
        return "\n".join(lines)
    needs_fills = sum(1 for row in rows if row.completion_status != "ready_for_validate_preview")
    lines.append(f"Rows shown: {len(rows)}; rows needing field fills: {needs_fills}")
    lines.append("")
    lines.append("Ticker | Input family | Missing fields | Completion status | Missing review fields | Next safe action")
    lines.append("--- | --- | --- | --- | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    row.ticker,
                    row.input_family,
                    row.missing_dcf_fields,
                    row.completion_status,
                    row.missing_review_fields or "-",
                    row.next_safe_action,
                ]
            )
        )
    lines.append("")
    lines.append("Review boundary:")
    lines.append("- Fill source file or URL, as-of date, reviewer, review date, source proof status, validation, preview, and apply decision.")
    lines.append("- Use the import row scaffold only after the source fields are reviewed.")
    lines.append("- Run validate -> preview -> rejected-row review -> apply decision before any supported proof outcome.")
    lines.append("- Keep proof-record commands in dry-run until source files, changed readiness counts, changed tickers, and artifact review are filled.")
    return "\n".join(lines)


def build_dcf_input_source_command_plan(
    rows: list[DcfInputProofRow],
    *,
    family: str | None = None,
    limit: int = 10,
) -> list[DcfInputSourceCommandPlan]:
    review_rows = build_dcf_input_source_review_rows(rows, family=family, limit=limit)
    if not review_rows:
        family_label = str(family or "selected DCF family").strip()
        return [
            DcfInputSourceCommandPlan(
                step="1. Refresh DCF input queue",
                status="blocked",
                command="make dcf-input-proof-queue TOP_N=10",
                fields_to_fill="queued DCF blockers",
                review_boundary=f"No source-review command can be built until {family_label} has queued blockers.",
            )
        ]
    first = review_rows[0]
    family_key = first.input_family
    ticker = first.ticker
    guard_command = f"make dcf-input-source-guard {_make_assignments(_reviewed_value_assignments(first))}"
    handoff = build_dcf_input_proof_handoff(rows, family=family_key, limit=limit)
    missing_fields = first.missing_review_fields or "reviewed source fields"
    return [
        DcfInputSourceCommandPlan(
            step="1. Open source-review intake",
            status=first.completion_status,
            command=f"make dcf-input-source-review FAMILY={family_key} TOP_N={max(limit, 0) or 10}",
            fields_to_fill=missing_fields,
            review_boundary="Use this first to see source fields before editing import rows or proof records.",
        ),
        DcfInputSourceCommandPlan(
            step="2. Fill and run source guard",
            status="blocked_until_reviewed_fields_filled" if first.completion_status != "ready_for_validate_preview" else "ready_for_guard",
            command=guard_command,
            fields_to_fill=missing_fields,
            review_boundary="Replace placeholders with reviewed source proof; the guard prints an import row preview only.",
        ),
        DcfInputSourceCommandPlan(
            step="3. Validate import rows",
            status="copy_only_after_guard",
            command="make imports-validate",
            fields_to_fill="validation_result",
            review_boundary="Validation must pass before preview or apply decisions count as proof.",
        ),
        DcfInputSourceCommandPlan(
            step="4. Preview import merge",
            status="copy_only_after_validate",
            command="make imports-preview",
            fields_to_fill="preview_result and rejected-row review",
            review_boundary="Preview and rejected-row reports must be reviewed before any apply step.",
        ),
        DcfInputSourceCommandPlan(
            step="5. Apply boundary",
            status="manual_review_boundary",
            command="make imports-apply",
            fields_to_fill="apply_decision",
            review_boundary="Do not run apply unless source proof, validation, preview, rejected-row review, and scope review are complete.",
        ),
        DcfInputSourceCommandPlan(
            step="6. Rebuild DCF proof",
            status="copy_only_after_apply_or_skip",
            command=f"make dcf-readiness && make readiness && make stock-report-md TICKER={ticker}",
            fields_to_fill="post-run readiness proof",
            review_boundary="A supported outcome needs rebuilt readiness proof; skipped or still-blocked outcomes should stay honest.",
        ),
        DcfInputSourceCommandPlan(
            step="7. Proof handoff",
            status="dry_run_first",
            command=f"make dcf-input-proof-handoff FAMILY={family_key} TOP_N={max(limit, 0) or 10}",
            fields_to_fill="changed counts, changed tickers, source files, generated artifact review",
            review_boundary=handoff.record_boundary,
        ),
    ]


def render_dcf_input_source_command_plan(plan: list[DcfInputSourceCommandPlan]) -> str:
    lines = [
        "DCF Source Review Command Plan",
        "Read-only: this plan prints copy-ready commands only; it does not apply imports, record proof, or unlock DCF readiness.",
        "Research-only: commands support data-readiness review, not investment advice, broker integration, order routing, or buy/sell instructions.",
        "Do not replace placeholders unless reviewed source proof exists.",
    ]
    if not plan:
        lines.append("No DCF source-review command plan available.")
        return "\n".join(lines)
    lines.append("")
    lines.append("Step | Status | Command | Fields to fill | Review boundary")
    lines.append("--- | --- | --- | --- | ---")
    for row in plan:
        lines.append(" | ".join([row.step, row.status, row.command, row.fields_to_fill, row.review_boundary]))
    return "\n".join(lines)


def build_dcf_input_source_guard(
    *,
    ticker: str,
    input_family: str,
    missing_dcf_fields: str = "",
    period: str = "",
    revenue: str = "",
    free_cash_flow: str = "",
    fcf_margin: str = "",
    shares_outstanding: str = "",
    source_type: str = "",
    source_file_or_url: str = "",
    source_as_of_date: str = "",
    reviewer: str = "",
    review_date: str = "",
    source_proof_status: str = "",
    validation_result: str = "",
    preview_result: str = "",
    apply_decision: str = "",
) -> DcfInputSourceGuard:
    ticker_key = str(ticker or "").strip().upper()
    family_key = str(input_family or "").strip()
    values = {
        "source_type": source_type or _source_type_for_family(family_key),
        "source_file_or_url": source_file_or_url,
        "source_as_of_date": source_as_of_date,
        "reviewer": reviewer,
        "review_date": review_date,
        "source_proof_status": source_proof_status,
        "validation_result": validation_result,
        "preview_result": preview_result,
        "apply_decision": apply_decision,
    }
    blocking = _source_review_missing_fields(values)
    if not ticker_key:
        blocking.append("ticker")
    if not family_key:
        blocking.append("input_family")
    if family_key == "price":
        blocking.append("price_inputs_use_price_import_path")
    if _is_placeholder(period):
        blocking.append("period")
    dcf_values = {
        "revenue": revenue,
        "free_cash_flow": free_cash_flow,
        "fcf_margin": fcf_margin,
        "shares_outstanding": shares_outstanding,
    }
    for field in _required_dcf_values(family_key, missing_dcf_fields):
        if field in dcf_values and not _numeric_or_placeholder(dcf_values[field]):
            blocking.append(field)
    status = "ready_for_validate_preview" if not blocking else "blocked"
    source = source_file_or_url or "<reviewed_source_file_or_url>"
    as_of = source_as_of_date or "<yyyy-mm-dd>"
    row_values = {
        "ticker": ticker_key,
        "period": period,
        "revenue": revenue if not _is_placeholder(revenue) else "",
        "free_cash_flow": free_cash_flow if not _is_placeholder(free_cash_flow) else "",
        "fcf_margin": fcf_margin if not _is_placeholder(fcf_margin) else "",
        "shares_outstanding": shares_outstanding if not _is_placeholder(shares_outstanding) else "",
        "source": source,
        "as_of_date": as_of,
    }
    csv_header = _csv_row(list(FUNDAMENTALS_IMPORT_COLUMNS))
    csv_row = _csv_row([row_values[column] for column in FUNDAMENTALS_IMPORT_COLUMNS]) if status == "ready_for_validate_preview" else ""
    return DcfInputSourceGuard(
        status=status,
        ticker=ticker_key or "<ticker>",
        input_family=family_key or "<input_family>",
        blocking_reasons=tuple(dict.fromkeys(blocking)),
        csv_header=csv_header,
        csv_row=csv_row,
        target_file=_target_file_for_family(family_key),
        validation_command="make imports-validate",
        preview_command="make imports-preview",
        apply_boundary=(
            "Run make imports-apply only after imports-preview and rejected-row reports are reviewed."
            if status == "ready_for_validate_preview"
            else "Do not edit or apply data/imports/fundamentals.csv until blocking reasons are resolved."
        ),
        post_apply_proof=f"make dcf-readiness && make readiness && make stock-report-md TICKER={ticker_key or '<ticker>'}",
        proof_record_boundary=(
            "After rebuilt readiness and comparison are reviewed, use DRY_RUN=1 make reviewed-batch-proof-record with source files and artifact review filled."
        ),
    )


def render_dcf_input_source_guard(guard: DcfInputSourceGuard) -> str:
    lines = [
        "DCF Input Source Review Guard",
        "Read-only: this guard validates reviewed source fields and prints an import-row preview only; it does not apply imports.",
        "Research-only: this is data-readiness proof, not investment advice, broker integration, order routing, or buy/sell instructions.",
        f"Status: {guard.status}",
        f"Ticker: {guard.ticker}",
        f"Input family: {guard.input_family}",
    ]
    if guard.blocking_reasons:
        lines.append(f"Blocking reasons: {', '.join(guard.blocking_reasons)}")
    lines.extend(
        [
            f"Target file: {guard.target_file}",
            f"CSV header: {guard.csv_header}",
            f"CSV row: {guard.csv_row or 'blocked until reviewed fields are complete'}",
            f"Validate: {guard.validation_command}",
            f"Preview: {guard.preview_command}",
            f"Apply boundary: {guard.apply_boundary}",
            f"Post-apply proof: {guard.post_apply_proof}",
            f"Proof record boundary: {guard.proof_record_boundary}",
        ]
    )
    return "\n".join(lines)


def render_dcf_input_proof_handoff(handoff: DcfInputProofHandoff) -> str:
    lines = [
        "DCF Input Proof Handoff",
        "Read-only: this handoff builds copy-ready review commands only; it does not apply data or record proof.",
        "Research-only: proof records capture data-readiness outcomes, not recommendations, broker integration, order routing, or buy/sell instructions.",
        f"Input family: {handoff.input_family}",
        f"Selected rows: {handoff.selected_rows}",
        f"Tickers: {handoff.tickers}",
        f"Lane: {handoff.lane}",
        "",
        "Copy-only sequence:",
        f"- Proof packet: {handoff.proof_packet_command}",
        f"- Validate: {handoff.validation_command}",
        f"- Preview: {handoff.preview_command}",
        f"- Apply boundary: {handoff.apply_boundary}",
        f"- Post-run proof: {handoff.post_run_proof_command}",
        f"- Compare: {handoff.compare_command}",
        f"- Proof record dry run: {handoff.proof_record_scaffold}",
        "",
        f"Stop rule: {handoff.stop_rule}",
        f"Record boundary: {handoff.record_boundary}",
    ]
    return "\n".join(lines)


def render_dcf_input_proof_queue(rows: list[DcfInputProofRow]) -> str:
    lines = [
        "DCF Input Proof Queue",
        "Read-only: this queue does not refresh data, apply imports, or create valuation conclusions.",
        "Research-only: DCF input proof is a readiness gate, not investment advice, execution, or direct buy/sell instructions.",
        "Do not infer prices, revenue, free cash flow, FCF margin, shares outstanding, market cap, or peer inputs.",
    ]
    if not rows:
        lines.append("No company DCF input blockers found for the selected scope.")
        return "\n".join(lines)
    lines.append(f"Rows shown: {len(rows)}")
    lines.append(f"Shown missing input families: {summarize_missing_input_families(rows)}")
    lines.append(f"Next safest action: {rows[0].next_safe_command}")
    lines.append("")
    lines.append("Priority | Ticker | Scope | Missing family | Missing DCF fields | Source mode | Next safe command")
    lines.append("---: | --- | --- | --- | --- | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    str(row.priority),
                    row.ticker,
                    row.scope,
                    row.missing_input_family,
                    row.missing_dcf_fields,
                    row.source_mode,
                    row.next_safe_command,
                ]
            )
        )
    lines.append("")
    lines.append("Review sequence:")
    lines.append("- Open the ticker proof path printed in `next_safe_command` before editing any import row.")
    lines.append("- Use the proof packet command when the scope should become a reviewed batch packet.")
    lines.append("- Keep validate -> preview -> rejected-row review -> apply for mutating local fundamentals workflows.")
    lines.append("- Rebuild DCF readiness and the stock report before marking any row supported.")
    lines.append("")
    lines.append("Stop rules:")
    for row in rows[:5]:
        lines.append(f"- {row.ticker}: {row.stop_rule}")
    return "\n".join(lines)


def _split_tickers(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a read-only DCF input proof queue.")
    parser.add_argument("--project-root")
    parser.add_argument("--data-dir")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--tickers")
    parser.add_argument("--family", help="Optional DCF input family to hand off, such as shares_outstanding or fcf_margin.")
    parser.add_argument("--handoff", action="store_true", help="Print a reviewed-batch proof handoff for the selected queue/family.")
    parser.add_argument("--source-intake", action="store_true", help="Print fillable source-review rows for the selected DCF queue/family.")
    parser.add_argument("--source-command-plan", action="store_true", help="Print copy-only source-review, guard, validate, preview, and proof handoff commands.")
    parser.add_argument("--source-guard", action="store_true", help="Validate reviewed source fields and print an import-row preview when complete.")
    parser.add_argument("--ticker")
    parser.add_argument("--missing-dcf-fields", default="")
    parser.add_argument("--period", default="")
    parser.add_argument("--revenue", default="")
    parser.add_argument("--free-cash-flow", default="")
    parser.add_argument("--fcf-margin", default="")
    parser.add_argument("--shares-outstanding", default="")
    parser.add_argument("--source-type", default="")
    parser.add_argument("--source-file-or-url", default="")
    parser.add_argument("--source-as-of-date", default="")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--review-date", default="")
    parser.add_argument("--source-proof-status", default="")
    parser.add_argument("--validation-result", default="")
    parser.add_argument("--preview-result", default="")
    parser.add_argument("--apply-decision", default="")
    parser.add_argument("--output", help="Optional CSV output path.")
    args = parser.parse_args()

    root = resolve_project_root(Path(args.project_root) if args.project_root else None)
    data_path = resolve_data_dir(Path(args.data_dir) if args.data_dir else None, root)
    print(format_path_context(root, data_path, resolve_outputs_dir(None, root)))
    if args.source_guard:
        guard = build_dcf_input_source_guard(
            ticker=args.ticker or "",
            input_family=args.family or "",
            missing_dcf_fields=args.missing_dcf_fields,
            period=args.period,
            revenue=args.revenue,
            free_cash_flow=args.free_cash_flow,
            fcf_margin=args.fcf_margin,
            shares_outstanding=args.shares_outstanding,
            source_type=args.source_type,
            source_file_or_url=args.source_file_or_url,
            source_as_of_date=args.source_as_of_date,
            reviewer=args.reviewer,
            review_date=args.review_date,
            source_proof_status=args.source_proof_status,
            validation_result=args.validation_result,
            preview_result=args.preview_result,
            apply_decision=args.apply_decision,
        )
        print(render_dcf_input_source_guard(guard))
    else:
        rows = build_dcf_input_proof_queue_from_files(
            root,
            data_dir=data_path,
            top_n=args.top_n,
            tickers=_split_tickers(args.tickers),
        )
        if args.source_intake:
            source_rows = build_dcf_input_source_review_rows(rows, family=args.family, limit=args.top_n)
            print(render_dcf_input_source_review_rows(source_rows))
        elif args.source_command_plan:
            command_plan = build_dcf_input_source_command_plan(rows, family=args.family, limit=args.top_n)
            print(render_dcf_input_source_command_plan(command_plan))
        elif args.handoff:
            handoff = build_dcf_input_proof_handoff(rows, family=args.family, limit=args.top_n)
            print(render_dcf_input_proof_handoff(handoff))
        else:
            print(render_dcf_input_proof_queue(rows))
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.source_guard:
            guard = build_dcf_input_source_guard(
                ticker=args.ticker or "",
                input_family=args.family or "",
                missing_dcf_fields=args.missing_dcf_fields,
                period=args.period,
                revenue=args.revenue,
                free_cash_flow=args.free_cash_flow,
                fcf_margin=args.fcf_margin,
                shares_outstanding=args.shares_outstanding,
                source_type=args.source_type,
                source_file_or_url=args.source_file_or_url,
                source_as_of_date=args.source_as_of_date,
                reviewer=args.reviewer,
                review_date=args.review_date,
                source_proof_status=args.source_proof_status,
                validation_result=args.validation_result,
                preview_result=args.preview_result,
                apply_decision=args.apply_decision,
            )
            pd.DataFrame([guard.to_dict()], columns=SOURCE_GUARD_COLUMNS).to_csv(output, index=False)
            print(f"\nWrote DCF input source-review guard CSV: {output}")
            return
        rows = build_dcf_input_proof_queue_from_files(
            root,
            data_dir=data_path,
            top_n=args.top_n,
            tickers=_split_tickers(args.tickers),
        )
        if args.source_intake:
            source_rows = build_dcf_input_source_review_rows(rows, family=args.family, limit=args.top_n)
            pd.DataFrame([row.to_dict() for row in source_rows], columns=SOURCE_REVIEW_COLUMNS).to_csv(output, index=False)
            print(f"\nWrote DCF input source-review intake CSV: {output}")
        elif args.source_command_plan:
            command_plan = build_dcf_input_source_command_plan(rows, family=args.family, limit=args.top_n)
            pd.DataFrame([row.to_dict() for row in command_plan], columns=SOURCE_COMMAND_PLAN_COLUMNS).to_csv(output, index=False)
            print(f"\nWrote DCF input source-review command plan CSV: {output}")
        elif args.handoff:
            handoff = build_dcf_input_proof_handoff(rows, family=args.family, limit=args.top_n)
            pd.DataFrame([handoff.to_dict()], columns=HANDOFF_COLUMNS).to_csv(output, index=False)
            print(f"\nWrote DCF input proof handoff CSV: {output}")
        else:
            pd.DataFrame([row.to_dict() for row in rows], columns=QUEUE_COLUMNS).to_csv(output, index=False)
            print(f"\nWrote DCF input proof queue CSV: {output}")


if __name__ == "__main__":
    main()
