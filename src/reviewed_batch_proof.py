"""Reviewed batch proof ledger.

This ledger records reviewed batch execution outcomes separately from broad
generated readiness reports. The command is append-only by design: it does not
refresh providers, import rows, apply data, or produce research conclusions.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.paths import DATA_PROFILE_ENV, resolve_data_profile


DEFAULT_BATCH_PROOF_LEDGER = Path("data/reviewed_batch_proofs.csv")
BATCH_OUTCOMES = {
    "supported",
    "auto_supported",
    "human_reviewed_supported",
    "candidate_context_only",
    "still_blocked",
    "skipped",
    "excluded",
}
BATCH_PROOF_COLUMNS = (
    "batch_id",
    "review_date",
    "reviewer",
    "lane",
    "scope",
    "tickers",
    "command_run",
    "validation_result",
    "preview_result",
    "apply_result",
    "pre_run_readiness_snapshot",
    "post_run_readiness_snapshot",
    "changed_readiness_counts",
    "changed_tickers",
    "source_files",
    "generated_artifacts_reviewed",
    "final_outcome",
    "notes",
)
READINESS_PROFILES = {"default", "demo", "local"}
POST_APPLY_READINESS_TOKENS = {
    "fundamentals": ("make dcf-readiness",),
    "fundamentals_dcf": ("make dcf-readiness",),
    "share_count": ("make dcf-readiness",),
    "shares_outstanding": ("make dcf-readiness",),
    "optional_context": ("make optional-context-readiness",),
    "optional_context_locked": ("make optional-context-readiness",),
}
PRIMARY_PRODUCT_PLACEHOLDER = re.compile(r"<[A-Za-z0-9][A-Za-z0-9_-]*>")
PRIMARY_REVIEWED_READ_ONLY_TARGETS = {
    "imports-validate",
    "imports-preview",
    "price-validate",
    "price-preview",
    "status-check",
}
PRIMARY_REVIEWED_APPLY_TARGETS = {"imports-apply", "price-apply"}
PRIMARY_REVIEWED_WRITE_SEQUENCES = {
    ("imports-validate", "imports-preview", "imports-apply"),
    ("price-validate", "price-preview", "price-apply"),
}
PRIMARY_IMPORT_LANES = {"fundamentals", "share_count", "peers", "optional_context"}
PRIMARY_REVIEWED_ARGUMENT_KEYS = {
    "imports-validate": {"IMPORT_TICKERS", "IMPORT_FILES"},
    "imports-preview": {"IMPORT_TICKERS", "IMPORT_FILES"},
    "imports-apply": {"IMPORT_TICKERS", "IMPORT_FILES"},
    "price-validate": set(),
    "price-preview": set(),
    "price-apply": set(),
    "status-check": {"TOP_N"},
}
PRIMARY_PRICE_LANES = {"price", "prices", "daily_price_refresh"}
PRIMARY_PRICE_UNAVAILABLE = "Price writes are unavailable outside local profile; rerun with PROFILE=local."

REQUIRED_BATCH_PROOF_FIELDS = (
    "batch_id",
    "review_date",
    "lane",
    "command_run",
    "validation_result",
    "preview_result",
    "apply_result",
    "changed_readiness_counts",
    "changed_tickers",
    "source_files",
    "generated_artifacts_reviewed",
    "final_outcome",
)


@dataclass(frozen=True)
class ReviewedBatchProof:
    batch_id: str
    review_date: str
    reviewer: str
    lane: str
    scope: str
    tickers: str
    command_run: str
    validation_result: str
    preview_result: str
    apply_result: str
    pre_run_readiness_snapshot: str
    post_run_readiness_snapshot: str
    changed_readiness_counts: str
    changed_tickers: str
    source_files: str
    generated_artifacts_reviewed: str
    final_outcome: str
    notes: str


class DuplicateBatchProofError(ValueError):
    """Raised when a ledger append would create an ambiguous batch id."""


def resolve_readiness_proof_profile(
    profile: str | None = None,
    *,
    project_root: Path | str | None = None,
) -> str:
    """Resolve the active profile and reject every non-concrete value."""

    raw_profile = os.getenv(DATA_PROFILE_ENV) if profile is None else str(profile)
    selected_profile = "default" if raw_profile is None else raw_profile.strip()
    if selected_profile not in READINESS_PROFILES:
        raise ValueError("a concrete readiness profile is required: default, demo, or local")
    try:
        selected = resolve_data_profile(selected_profile, project_root=project_root).name
    except ValueError as exc:
        raise ValueError("a concrete readiness profile is required: default, demo, or local") from exc
    if selected not in READINESS_PROFILES:
        raise ValueError("a concrete readiness profile is required: default, demo, or local")
    return selected


def profile_bound_readiness_proof_sequence(
    *,
    profile: str,
    lane: str,
    batch_id: str,
    review_date: str,
    reviewed_steps: Iterable[str] = (),
) -> str:
    """Return the one snapshot-before/reviewed-change/in-memory-compare proof sequence."""

    selected_profile = str(profile or "").strip()
    if selected_profile not in READINESS_PROFILES:
        raise ValueError("a concrete readiness profile is required: default, demo, or local")
    selected_lane = str(lane or "").strip()
    selected_batch = str(batch_id or "").strip()
    selected_date = str(review_date or "").strip()
    if not selected_lane or "<" in selected_lane or ">" in selected_lane:
        raise ValueError("lane is required and must not contain a placeholder")
    if not selected_batch or "<" in selected_batch or ">" in selected_batch:
        raise ValueError("batch_id is required and must not contain a placeholder")
    if not selected_date or "<" in selected_date or ">" in selected_date:
        raise ValueError("review_date is required and must not contain a placeholder")
    commands = [f"make readiness-snapshot PROFILE={selected_profile}"]
    commands.extend(str(step).strip() for step in reviewed_steps if str(step).strip())
    commands.append(
        f"make reviewed-batch-compare PROFILE={selected_profile} LANE={selected_lane} "
        f"BATCH_ID={selected_batch} REVIEW_DATE={selected_date}"
    )
    return " && ".join(commands)


def profile_bound_reviewed_write_proof_sequence(
    *,
    profile: str,
    lane: str,
    reviewed_steps: Iterable[str],
    after_compare_steps: Iterable[str] = (),
) -> str:
    """Return one copy-ready snapshot-before-write proof template."""

    selected_profile = resolve_readiness_proof_profile(profile)
    selected_lane = str(lane or "").strip()
    if not selected_lane or "<" in selected_lane or ">" in selected_lane:
        raise ValueError("lane is required and must not contain a placeholder")
    steps = [str(step).strip() for step in reviewed_steps if str(step).strip()]
    validate_index = next((index for index, step in enumerate(steps) if "-validate" in step), -1)
    preview_index = next((index for index, step in enumerate(steps) if "-preview" in step), -1)
    apply_index = next((index for index, step in enumerate(steps) if "-apply" in step), -1)
    if not (0 <= validate_index < preview_index < apply_index):
        raise ValueError("reviewed write steps must contain validate, preview, and apply in order")
    required_readiness_tokens = POST_APPLY_READINESS_TOKENS.get(selected_lane, ())
    if required_readiness_tokens and not any(
        index > apply_index and any(token in step for token in required_readiness_tokens)
        for index, step in enumerate(steps)
    ):
        raise ValueError(f"lane {selected_lane} requires a post-apply readiness rebuild")
    profile_prefix = f"{DATA_PROFILE_ENV}={selected_profile} "

    def profile_scoped_step(step: str) -> str:
        if step.startswith(f"{DATA_PROFILE_ENV}="):
            if not step.startswith(profile_prefix):
                raise ValueError("reviewed write step profile must match the selected proof profile")
            return step
        return f"{profile_prefix}{step}"

    commands = [
        f"make readiness-snapshot PROFILE={selected_profile}",
        *(profile_scoped_step(step) for step in steps),
    ]
    commands.append(
        f"make reviewed-batch-compare PROFILE={selected_profile} LANE={selected_lane} "
        "BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>"
    )
    commands.extend(
        profile_scoped_step(str(step).strip())
        for step in after_compare_steps
        if str(step).strip()
    )
    return " && ".join(commands)


def _primary_reviewed_step_target(*, profile: str, step: str, allow_apply: bool = False) -> str:
    """Validate one primary proof command and return its single make target."""

    selected_profile = resolve_readiness_proof_profile(profile)
    raw_step = str(step or "")
    if any(token in raw_step for token in ("&", "\r", "\n")):
        raise ValueError("primary proof steps must be one shell-free make command")
    original = raw_step.strip()
    normalized = PRIMARY_PRODUCT_PLACEHOLDER.sub("placeholder", original)
    if not normalized or any(token in normalized for token in ("&&", ";", "|", ">", "<", "`", "$")):
        raise ValueError("primary proof steps must be one shell-free make command")
    parts = normalized.split()
    profile_prefix = f"{DATA_PROFILE_ENV}="
    if parts and parts[0].startswith(profile_prefix):
        if parts[0] != f"{profile_prefix}{selected_profile}":
            raise ValueError("primary proof step profile must match the selected proof profile")
        parts = parts[1:]
    if len(parts) < 2 or parts[0] != "make":
        raise ValueError("primary proof steps must contain exactly one make target")
    target = parts[1]
    if any(part.startswith(profile_prefix) for part in parts):
        raise ValueError("primary proof step profile must be the sole selected leading prefix")
    allowed_argument_keys = PRIMARY_REVIEWED_ARGUMENT_KEYS.get(target)
    if allowed_argument_keys is None:
        raise ValueError(f"primary proof target is not approved: {target}")
    seen_argument_keys: set[str] = set()
    for argument in parts[2:]:
        key, separator, value = argument.partition("=")
        if not separator or not key or not value or key not in allowed_argument_keys or key in seen_argument_keys:
            raise ValueError("primary proof step arguments must be approved KEY=VALUE inputs")
        seen_argument_keys.add(key)
    allowed_targets = PRIMARY_REVIEWED_READ_ONLY_TARGETS | (PRIMARY_REVIEWED_APPLY_TARGETS if allow_apply else set())
    if target not in allowed_targets:
        raise ValueError(f"primary proof target is not approved: {target}")
    return target


def _primary_profile_scoped_step(*, profile: str, step: str) -> str:
    selected_profile = resolve_readiness_proof_profile(profile)
    command = str(step).strip()
    prefix = f"{DATA_PROFILE_ENV}={selected_profile} "
    return command if command.startswith(prefix) else f"{prefix}{command}"


def primary_profile_scoped_reviewed_step(*, profile: str, step: str) -> str:
    """Return one approved, read-only primary proof command bound to ``profile``."""

    selected_profile = resolve_readiness_proof_profile(profile)
    _primary_reviewed_step_target(profile=selected_profile, step=step)
    return _primary_profile_scoped_step(profile=selected_profile, step=step)


def primary_profile_bound_reviewed_write_proof_sequence(
    *,
    profile: str,
    lane: str,
    reviewed_steps: Iterable[str],
    after_compare_steps: Iterable[str] = (),
) -> str:
    """Compose the strict, primary-only reviewed-write proof sequence."""

    selected_profile = resolve_readiness_proof_profile(profile)
    raw_lane = str(lane or "")
    if any(token in raw_lane for token in ("&", ";", "|", ">", "<", "`", "$", "\r", "\n")):
        raise ValueError("primary proof lane must be one approved shell-free identifier")
    selected_lane = raw_lane.strip()
    if selected_lane not in PRIMARY_IMPORT_LANES | PRIMARY_PRICE_LANES:
        raise ValueError("primary proof lane is not approved")
    steps = [str(step).strip() for step in reviewed_steps if str(step).strip()]
    targets = tuple(
        _primary_reviewed_step_target(profile=selected_profile, step=step, allow_apply=True) for step in steps
    )
    if targets not in PRIMARY_REVIEWED_WRITE_SEQUENCES:
        raise ValueError("primary reviewed write steps must be exactly validate, preview, and apply in order")
    is_price_sequence = targets == ("price-validate", "price-preview", "price-apply")
    is_price_lane = selected_lane.casefold() in PRIMARY_PRICE_LANES
    if is_price_sequence != is_price_lane:
        raise ValueError("primary price proof targets must match a price lane")
    if is_price_sequence and selected_profile != "local":
        return PRIMARY_PRICE_UNAVAILABLE
    scoped_steps = [_primary_profile_scoped_step(profile=selected_profile, step=step) for step in steps]
    scoped_tails: list[str] = []
    for step in after_compare_steps:
        if not str(step).strip():
            continue
        target = _primary_reviewed_step_target(profile=selected_profile, step=str(step))
        if target != "status-check":
            raise ValueError("primary proof after-compare steps must be approved read-only status checks")
        scoped_tails.append(primary_profile_scoped_reviewed_step(profile=selected_profile, step=str(step)))
    commands = [
        f"make readiness-snapshot PROFILE={selected_profile}",
        *scoped_steps,
        (
            f"make reviewed-batch-compare PROFILE={selected_profile} LANE={selected_lane} "
            "BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>"
        ),
        *scoped_tails,
    ]
    return " && ".join(commands)


def _clean(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _is_placeholder(value: object) -> bool:
    text = str(value or "").strip()
    lowered = text.lower()
    if not text or lowered in {"-", "na", "n/a", "not available", "unknown"}:
        return True
    if lowered.startswith("<") and lowered.endswith(">"):
        return True
    if "<" in lowered and ">" in lowered:
        return True
    return "|" in lowered and any(token in lowered for token in BATCH_OUTCOMES)


def _is_reviewed_no_change(field: str, value: object) -> bool:
    return field in {"changed_readiness_counts", "changed_tickers"} and str(value or "").strip().lower().startswith("none")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def batch_proof_from_row(row: dict[str, str]) -> ReviewedBatchProof:
    values = {column: _clean(row.get(column)) for column in BATCH_PROOF_COLUMNS}
    values["final_outcome"] = values["final_outcome"].lower()
    return ReviewedBatchProof(**values)


def load_reviewed_batch_proofs(path: Path = DEFAULT_BATCH_PROOF_LEDGER) -> list[ReviewedBatchProof]:
    return [batch_proof_from_row(row) for row in _read_csv(path)]


def write_reviewed_batch_proofs(
    rows: Iterable[ReviewedBatchProof],
    path: Path = DEFAULT_BATCH_PROOF_LEDGER,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BATCH_PROOF_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in BATCH_PROOF_COLUMNS})
    return path


def append_reviewed_batch_proof(
    row: ReviewedBatchProof,
    path: Path = DEFAULT_BATCH_PROOF_LEDGER,
) -> Path:
    existing = load_reviewed_batch_proofs(path)
    duplicate = next((item for item in existing if item.batch_id == row.batch_id), None)
    if duplicate is not None:
        raise DuplicateBatchProofError(
            f"batch_id {row.batch_id} already exists in {path}; use a unique batch id before recording."
        )
    existing.append(row)
    return write_reviewed_batch_proofs(existing, path)


def latest_reviewed_batch_proof(rows: list[ReviewedBatchProof]) -> ReviewedBatchProof | None:
    if not rows:
        return None
    return sorted(rows, key=lambda row: (row.review_date, row.batch_id))[-1]


def reviewed_batch_proof_validation_rows(row: ReviewedBatchProof) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in REQUIRED_BATCH_PROOF_FIELDS:
        value = getattr(row, field)
        status = "ready"
        reason = "Reviewed value is present."
        if field == "final_outcome" and row.final_outcome not in BATCH_OUTCOMES:
            status = "invalid_outcome"
            reason = (
                "FINAL_OUTCOME must be one of supported, auto_supported, human_reviewed_supported, "
                "candidate_context_only, still_blocked, skipped, or excluded."
            )
        elif _is_placeholder(value) and not _is_reviewed_no_change(field, value):
            status = "missing_required"
            reason = "Required ledger field still contains a placeholder or missing value."
        rows.append(
            {
                "field": field,
                "status": status,
                "value": value,
                "reason": reason,
            }
        )
    return rows


def reviewed_batch_proof_validation_status(rows: Iterable[dict[str, str]]) -> str:
    statuses = {row["status"] for row in rows}
    if "invalid_outcome" in statuses:
        return "invalid_outcome"
    if "missing_required" in statuses:
        return "needs_field_fills"
    return "ready_to_record"


def render_reviewed_batch_proof_row(row: ReviewedBatchProof) -> str:
    return "\n".join(f"{column}: {getattr(row, column)}" for column in BATCH_PROOF_COLUMNS)


def render_reviewed_batch_proof_validation(row: ReviewedBatchProof) -> str:
    rows = reviewed_batch_proof_validation_rows(row)
    status = reviewed_batch_proof_validation_status(rows)
    lines = [
        f"Validation status: {status}",
        "Copy boundary: dry-run preview only; record only after source files and generated artifacts are reviewed.",
    ]
    for item in rows:
        if item["status"] != "ready":
            lines.append(f"- {item['field']}: {item['status']} ({item['reason']})")
    if status == "ready_to_record":
        lines.append("All required ledger fields are ready after final review.")
    return "\n".join(lines)


def render_reviewed_batch_proofs(rows: list[ReviewedBatchProof]) -> str:
    lines = [
        "Reviewed Batch Proof Ledger",
        "Durable: this ledger records reviewed batch outcomes; it is not broad generated CSV/JSON churn.",
        "Research-only: proof rows do not provide investment advice, broker actions, auto-trading, order routing, or direct buy/sell instructions.",
        "",
    ]
    if not rows:
        lines.extend(
            [
                "No reviewed batch proof rows are recorded yet.",
                "Use reviewed-batch-proof-record after a copy-only packet, dry-run or reviewed scope, validation, preview, apply decision, readiness proof, and churn review.",
            ]
        )
        return "\n".join(lines)
    for row in sorted(rows, key=lambda item: (item.review_date, item.batch_id), reverse=True):
        lines.extend(
            [
                f"- {row.batch_id} | {row.review_date} | {row.lane} | {row.final_outcome}",
                f"  scope: {row.scope}; tickers: {row.tickers}",
                f"  Historical Command (not executable): {row.command_run}",
                f"  validate/preview/apply: {row.validation_result} / {row.preview_result} / {row.apply_result}",
                f"  readiness before -> after: {row.pre_run_readiness_snapshot} -> {row.post_run_readiness_snapshot}",
                f"  changed_readiness_counts: {row.changed_readiness_counts}",
                f"  changed_tickers: {row.changed_tickers}",
                f"  source_files: {row.source_files}",
                f"  generated_artifacts_reviewed: {row.generated_artifacts_reviewed}",
                f"  reviewer: {row.reviewer}",
                f"  notes: {row.notes}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_batch_proof_from_args(args: argparse.Namespace, *, strict_outcome: bool = True) -> ReviewedBatchProof:
    final_outcome = _clean(args.final_outcome).lower()
    if strict_outcome and final_outcome not in BATCH_OUTCOMES:
        raise SystemExit(
            "FINAL_OUTCOME must be one of supported, auto_supported, human_reviewed_supported, "
            "candidate_context_only, still_blocked, skipped, or excluded."
        )
    return ReviewedBatchProof(
        batch_id=_clean(args.batch_id),
        review_date=_clean(args.review_date),
        reviewer=_clean(args.reviewer),
        lane=_clean(args.lane),
        scope=_clean(args.scope),
        tickers=_clean(args.tickers),
        command_run=_clean(args.command_run),
        validation_result=_clean(args.validation_result),
        preview_result=_clean(args.preview_result),
        apply_result=_clean(args.apply_result),
        pre_run_readiness_snapshot=_clean(args.pre_run_readiness_snapshot),
        post_run_readiness_snapshot=_clean(args.post_run_readiness_snapshot),
        changed_readiness_counts=_clean(args.changed_readiness_counts),
        changed_tickers=_clean(args.changed_tickers),
        source_files=_clean(args.source_files),
        generated_artifacts_reviewed=_clean(args.generated_artifacts_reviewed),
        final_outcome=final_outcome,
        notes=_clean(args.notes),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reviewed batch proof ledger tools.")
    parser.add_argument("--ledger", default=str(DEFAULT_BATCH_PROOF_LEDGER))
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Preview and validate the ledger row without appending it.")
    for column in BATCH_PROOF_COLUMNS:
        parser.add_argument(f"--{column.replace('_', '-')}", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ledger_path = Path(args.ledger)
    if args.record or args.dry_run:
        row = build_batch_proof_from_args(args, strict_outcome=False)
        validation_rows = reviewed_batch_proof_validation_rows(row)
        validation_status = reviewed_batch_proof_validation_status(validation_rows)
        if args.dry_run:
            print("Reviewed Batch Proof Dry Run")
            print(f"Ledger: {ledger_path}")
            print("Preview row:")
            print(render_reviewed_batch_proof_row(row))
            print(render_reviewed_batch_proof_validation(row))
            if validation_status != "ready_to_record":
                return 2
            return 0
        if validation_status != "ready_to_record":
            print("Reviewed Batch Proof Record blocked")
            print(render_reviewed_batch_proof_validation(row))
            return 2
        try:
            written = append_reviewed_batch_proof(row, ledger_path)
        except DuplicateBatchProofError as exc:
            print("Reviewed Batch Proof Record blocked")
            print(str(exc))
            return 2
        print("Reviewed Batch Proof Record")
        print(f"Wrote: {written}")
        print(f"Batch: {row.batch_id} | {row.lane} | {row.final_outcome}")
        return 0
    print(render_reviewed_batch_proofs(load_reviewed_batch_proofs(ledger_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
