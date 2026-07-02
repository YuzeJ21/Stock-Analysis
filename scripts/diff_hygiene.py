"""Print a read-only staging hygiene report for the current git diff."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from shlex import quote
from dataclasses import dataclass
from pathlib import Path

from src.source_activation_guide import build_provider_setup_checklist


SOURCE_PREFIXES = (
    "src/",
    "tests/",
    "scripts/",
    "docs/",
)

ROOT_PRODUCT_FILES = {
    ".gitignore",
    ".streamlit/config.toml",
    "README.md",
    "ROADMAP.md",
    "PRODUCT_SPEC.md",
    "READINESS_MODEL.md",
    "DECISION_OUTPUT_MODEL.md",
    "Makefile",
    "config.yaml",
    "config/provider_keys.env.example",
    "pyproject.toml",
    "data/reviewed_data_proofs.csv",
    "data/reviewed_batch_proofs.csv",
    "outputs/reviewed_batch_packet.csv",
    "outputs/reviewed_batch_packet.md",
    "outputs/pilot_readiness_packet.md",
    "outputs/pilot_share_brief.md",
}

GENERATED_MARKDOWN_ARTIFACTS = {
    "outputs/decision_proof_queue.md",
}

REVIEWED_CANONICAL_DATA_PATHS = {
    "data/peers.csv": "peers",
}

SUPPORTED_REVIEW_OUTCOMES = {
    "supported",
    "auto_supported",
    "human_reviewed_supported",
}

REVIEWED_SCREENSHOT_ASSET_PATHS = (
    "docs/assets/single-stock-workflow-fit-real.jpg",
    "docs/assets/operator-data-health-proof-real.jpg",
    "docs/assets/operator-data-health-queue-routing-real.jpg",
)

LICENSE_DECISION_OPTIONS = (
    "  - Portfolio showcase only | Keep no license for now | Visitors can read the code, but reuse rights are not granted.",
    "  - Let others reuse with attribution | Add MIT or Apache-2.0 | Visitors can reuse under the selected license terms.",
    "  - Keep stronger control | Add a custom or proprietary notice | Visitors should ask before reuse; use legal review for custom wording.",
)


@dataclass(frozen=True)
class StatusEntry:
    status: str
    path: str


def parse_status_line(line: str) -> StatusEntry:
    if line.startswith("?? "):
        return StatusEntry("??", line[3:])
    return StatusEntry(line[:2].strip(), line[3:])


def parse_name_status_line(line: str) -> StatusEntry:
    parts = line.split("\t")
    status = parts[0].strip()
    path = parts[-1].strip()
    return StatusEntry(status, path)


def is_generated_churn(path: str) -> bool:
    if path.startswith("outputs/stock_reports/") and path.endswith(".md"):
        return False
    if path in GENERATED_MARKDOWN_ARTIFACTS:
        return True
    if path in {
        "data/reviewed_data_proofs.csv",
        "data/reviewed_batch_proofs.csv",
        "outputs/reviewed_batch_packet.csv",
        "outputs/reviewed_batch_packet.md",
    }:
        return False
    if path.startswith("data/") and path.endswith((".csv", ".json")):
        return True
    if path.startswith("outputs/") and path.endswith((".csv", ".json")):
        return True
    return False


def classify_path(path: str) -> str:
    if is_generated_churn(path):
        return "generated_csv_churn"
    if path.startswith("outputs/stock_reports/") and path.endswith(".md"):
        return "sample_report_candidate"
    if path in ROOT_PRODUCT_FILES or path.startswith(SOURCE_PREFIXES):
        return "product_candidate"
    if path.startswith("stock_analysis/"):
        return "product_candidate"
    return "review_manually"


def load_status(repo_root: Path) -> list[StatusEntry]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [parse_status_line(line) for line in result.stdout.splitlines() if line]


def load_staged_status(repo_root: Path) -> list[StatusEntry]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [parse_name_status_line(line) for line in result.stdout.splitlines() if line]


def load_staged_added_lines(repo_root: Path, path: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--", path],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    rows: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        rows.append(line[1:])
    return rows


def load_branch_status(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()[0] if result.stdout.splitlines() else "branch status unavailable"


def format_paths(entries: list[StatusEntry], *, limit: int = 80) -> list[str]:
    rows = [f"  {entry.status or 'M'} {entry.path}" for entry in entries[:limit]]
    if len(entries) > limit:
        rows.append(f"  ... {len(entries) - limit} more")
    return rows


def format_git_add_command(entries: list[StatusEntry], *, label: str, max_paths: int = 80) -> list[str]:
    if not entries:
        return [f"  # {label}: no files in this bucket"]
    paths = [entry.path for entry in entries[:max_paths]]
    command = "git add -- " + " ".join(quote(path) for path in paths)
    rows = [f"  # {label}", f"  {command}"]
    if len(entries) > max_paths:
        rows.append(f"  # Review and stage {len(entries) - max_paths} additional file(s) from this bucket manually.")
    return rows


def reviewed_screenshot_asset_stage_command() -> str:
    return "git add -- " + " ".join(quote(path) for path in REVIEWED_SCREENSHOT_ASSET_PATHS)


def format_license_gate(repo_root: Path | None = None) -> list[str]:
    root = repo_root or Path(".")
    if (root / "LICENSE").exists():
        return [
            "License gate: root LICENSE file found.",
            "  Run make license-status before public sharing.",
            "  Confirm README License wording matches the selected license before public reuse claims.",
        ]
    return [
        "License gate: no root LICENSE file found.",
        "  Share as portfolio/demo only; do not describe as open source or reusable software until a license is selected.",
        "  Run make license-status before public sharing.",
        "  See docs/LICENSE_DECISION_GUIDE.md before adding reuse-rights language.",
        "  License decision options:",
        *LICENSE_DECISION_OPTIONS,
    ]


def load_cached_source_preflight(repo_root: Path | None = None) -> dict[str, object] | None:
    if repo_root is None:
        return None
    root = repo_root
    path = root / "outputs" / "session_source_preflight.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def format_provider_setup_gate(current_preflight: dict[str, object] | None = None) -> list[str]:
    checklist = build_provider_setup_checklist(current_preflight=current_preflight)
    source_answer = checklist.get("source_answer", {})
    unlock_decision = checklist.get("coverage_unlock_decision", {})
    current_gate = checklist.get("current_gate", {})
    setup_order = checklist.get("one_provider_setup_order", [])
    lines = [
        "Provider setup gate:",
        "  Run make provider-setup-checklist before reopening broad source-proof queues.",
    ]
    if isinstance(unlock_decision, dict) and unlock_decision:
        lines.extend(
            [
                "  Coverage unlock decision:",
                f"    {unlock_decision.get('answer', '-')}",
                f"    {unlock_decision.get('can_use_now', '-')}",
                f"    {unlock_decision.get('configure_first', '-')}",
                f"    {unlock_decision.get('do_not_retry', '-')}",
                f"    {unlock_decision.get('proof_boundary', '-')}",
            ]
        )
    if isinstance(current_gate, dict) and current_gate:
        lines.extend(
            [
                "  Current source gate:",
                f"    can_run_now: {current_gate.get('can_run_now', '-')}",
                f"    needs_setup: {current_gate.get('needs_setup', '-')}",
                f"    avoid_repeating: {current_gate.get('avoid_repeating', '-')}",
                f"    next_step: {current_gate.get('next_step', '-')}",
                f"    next_step_reason: {current_gate.get('next_step_reason', '-')}",
            ]
        )
    if isinstance(source_answer, dict) and source_answer:
        configured_keyed = source_answer.get("configured_keyed", "-")
        needs_key = source_answer.get("needs_key", "-")
        lines.extend(
            [
                f"  Free public sources: {source_answer.get('free_public_now', '-')}",
                f"  Keyed free-tier fallbacks: configured {configured_keyed}; needs key {needs_key}",
                f"  Optional broker boundary: {source_answer.get('optional_broker', '-')}",
                "  Provider setup only makes a source executable; it does not run broad batches or apply data.",
            ]
        )
    first = next((row for row in setup_order if isinstance(row, dict)), None) if isinstance(setup_order, list) else None
    if first:
        lines.extend(
            [
                f"  Configure first: {first.get('provider', '-')}",
                f"  Why first: {first.get('why_first', '-')}",
                f"  Setup env: {first.get('setup_env', '-')}",
                f"  One-ticker smoke: {first.get('smoke_command', '-')}",
                "  Do not configure all missing providers at once; configure one, rerun preflight, smoke one ticker, then validate/preview before any apply.",
            ]
        )
    else:
        lines.append("  No missing keyed provider setup step is currently suggested by the checklist.")
    return lines


def format_sample_report_review_block(entries: list[StatusEntry], *, limit: int = 30) -> list[str]:
    rows = [
        "Sample reports are evidence-only by default:",
        "  Stage a specific report only after reviewing that exact artifact.",
    ]
    if entries:
        rows.extend(format_paths(entries, limit=limit))
    else:
        rows.append("  none")
    return rows


def write_path_file(path: Path, entries: list[StatusEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{entry.path}\n" for entry in entries)
    path.write_text(body, encoding="utf-8")


def count_path_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return len([line for line in text.splitlines() if line.strip()])


def build_staging_readme(files: dict[str, Path], repo_root: Path, *, package_status: str = "") -> str:
    def _rel(path: Path) -> str:
        return path.relative_to(repo_root).as_posix()

    def _line(label: str, key: str) -> str:
        path = files[key]
        return f"- {label}: {_rel(path)} ({count_path_file(path)} path(s))"

    return "\n".join(
        [
            "Diff Hygiene Local Staging Files",
            "",
            "These ignored files are generated by `make diff-hygiene-files`.",
            "They are review aids only; the command does not stage, delete, reset, refresh, or rewrite product data.",
            "",
            _line("Product files", "product_files"),
            _line("Product plus reviewed Markdown reports", "product_plus_reports"),
            _line("Markdown sample reports only", "sample_reports"),
            _line("Generated CSV/JSON churn to avoid by default", "generated_churn"),
            _line("Manual-review paths", "manual_review"),
            f"Package status: {package_status or 'not checked'}",
            "",
            "After reviewing the path list you want, optional staging commands are:",
            "git add --pathspec-from-file=outputs/staging/product_files.txt",
            "git add --pathspec-from-file=outputs/staging/product_plus_reports.txt",
            "make staged-hygiene-check",
            "",
            "Do not stage generated churn by default. It is listed separately so it can be inspected, not swept into public commits.",
            "Research-only guardrail: never stage broker, order execution, auto-trading, options recommendation, or direct buy/sell instruction language.",
            "",
        ]
    )


def write_staging_files(entries: list[StatusEntry], output_dir: Path) -> dict[str, Path]:
    groups = group_entries(entries)
    package_status = package_status_for_groups(groups)
    files = {
        "readme": output_dir / "README.txt",
        "product_files": output_dir / "product_files.txt",
        "product_plus_reports": output_dir / "product_plus_reports.txt",
        "sample_reports": output_dir / "sample_reports.txt",
        "generated_churn": output_dir / "generated_churn.txt",
        "manual_review": output_dir / "manual_review.txt",
    }
    write_path_file(files["product_files"], groups["product_candidate"])
    write_path_file(files["product_plus_reports"], groups["product_candidate"] + groups["sample_report_candidate"])
    write_path_file(files["sample_reports"], groups["sample_report_candidate"])
    write_path_file(files["generated_churn"], groups["generated_csv_churn"])
    write_path_file(files["manual_review"], groups["review_manually"])
    files["readme"].write_text(
        build_staging_readme(files, output_dir.parents[1], package_status=package_status),
        encoding="utf-8",
    )
    return files


def build_file_report(files: dict[str, Path], repo_root: Path, *, package_status: str = "") -> str:
    def _rel(path: Path) -> str:
        return path.relative_to(repo_root).as_posix()

    def _file_line(label: str, key: str) -> str:
        path = files[key]
        return f"{label}: {_rel(path)} ({count_path_file(path)} path(s))"

    product_file = _rel(files["product_files"])
    product_plus_reports_file = _rel(files["product_plus_reports"])
    generated_file = _rel(files["generated_churn"])
    return "\n".join(
        [
            "Diff Hygiene File Lists",
            "Generated local path lists for review; this did not stage, delete, reset, refresh, or rewrite product data.",
            "",
            _file_line("Product files", "product_files"),
            _file_line("Product plus reviewed Markdown reports", "product_plus_reports"),
            _file_line("Markdown sample reports only", "sample_reports"),
            _file_line("Generated CSV/JSON churn to avoid by default", "generated_churn"),
            _file_line("Manual-review paths", "manual_review"),
            f"Package status: {package_status or 'not checked'}",
            f"Usage notes: {_rel(files['readme'])}",
            "",
            "Optional staging commands after review:",
            f"  git add --pathspec-from-file={product_file}",
            f"  git add --pathspec-from-file={product_plus_reports_file}",
            "  make staged-hygiene-check",
            "",
            "Do not stage generated churn by default. Review this file instead:",
            f"  {generated_file}",
            "",
            "Research-only guardrail: never stage broker, order execution, auto-trading,",
            "options recommendation, or direct buy/sell instruction language.",
        ]
    )


def count_new(entries: list[StatusEntry]) -> int:
    return sum(1 for entry in entries if entry.status in {"??", "A"})


def format_count_line(label: str, entries: list[StatusEntry]) -> str:
    new_count = count_new(entries)
    changed_count = len(entries) - new_count
    return f"{label}: {len(entries)} ({changed_count} changed, {new_count} new)"


def group_entries(entries: list[StatusEntry]) -> dict[str, list[StatusEntry]]:
    groups: dict[str, list[StatusEntry]] = {
        "product_candidate": [],
        "sample_report_candidate": [],
        "generated_csv_churn": [],
        "review_manually": [],
    }
    for entry in entries:
        groups[classify_path(entry.path)].append(entry)
    return groups


def package_status_for_groups(groups: dict[str, list[StatusEntry]]) -> str:
    if groups["product_candidate"]:
        return "product package pending commit; commit this package before starting another feature slice"
    if groups["sample_report_candidate"]:
        if groups["generated_csv_churn"]:
            return "generated/sample report churn only; keep it local unless intentionally reviewed as evidence"
        return "sample report churn only; keep it local unless intentionally reviewed as evidence"
    if groups["generated_csv_churn"]:
        return "generated churn only; keep it local unless intentionally reviewed as evidence"
    return "clean; ready for the next reviewed work slice"


def public_release_share_now_lines(groups: dict[str, list[StatusEntry]]) -> list[str]:
    product = groups["product_candidate"]
    sample_reports = groups["sample_report_candidate"]
    generated = groups["generated_csv_churn"]
    manual = groups["review_manually"]
    lines = ["Share-now answer:"]
    if manual:
        lines.append("  Not yet: inspect manual-review paths before staging or sharing.")
    elif product:
        lines.append("  Not yet: commit the reviewed product package first, then rerun public-check.")
    else:
        lines.append("  Share as portfolio/demo only after public-check passes and generated churn stays excluded.")
    lines.extend(
        [
            "  Do not call this open source until a root LICENSE exists.",
            "  If source-proof queues are exhausted, use provider setup before broad proof loops.",
        ]
    )
    if generated or sample_reports:
        lines.append("  Do not stage generated churn or sample reports unless exact artifacts are reviewed evidence.")
    if generated and not product and not manual:
        lines.append("  Generated churn can stay local; do not create a release commit just for it.")
    return lines


def build_summary_report(entries: list[StatusEntry]) -> str:
    groups = group_entries(entries)
    package_status = package_status_for_groups(groups)
    lines = [
        "Diff Hygiene Summary",
        "Read-only: this command does not stage, delete, reset, refresh, or rewrite files.",
        "",
    ]
    if not entries:
        lines.extend(["Working tree is clean.", f"Package status: {package_status}"])
        return "\n".join(lines)
    lines.extend(
        [
            format_count_line("Product/code/docs/test candidates", groups["product_candidate"]),
            format_count_line("Markdown sample report candidates", groups["sample_report_candidate"]),
            format_count_line("Generated CSV/JSON churn to avoid by default", groups["generated_csv_churn"]),
            format_count_line("Manual-review paths", groups["review_manually"]),
            f"Package status: {package_status}",
            "",
            "Use `make diff-hygiene` for full file lists and safe staging suggestions.",
            "New docs/scripts/tests are product candidates when intentional; review them before staging.",
            "Generated CSV/JSON churn is intentionally excluded from the suggested staging commands.",
            "",
            "Research-only guardrail: never stage broker, order execution, auto-trading,",
            "options recommendation, or direct buy/sell instruction language.",
        ]
    )
    return "\n".join(lines)


def staged_hygiene_has_blockers(entries: list[StatusEntry]) -> bool:
    groups = group_entries(entries)
    return bool(groups["generated_csv_churn"] or groups["review_manually"])


def staged_reviewed_data_tickers(repo_root: Path, entry: StatusEntry) -> set[str]:
    if entry.path not in REVIEWED_CANONICAL_DATA_PATHS:
        return set()
    tickers: set[str] = set()
    for line in load_staged_added_lines(repo_root, entry.path):
        if not line.strip() or line.lower().startswith("ticker,"):
            continue
        ticker = line.split(",", 1)[0].strip().upper()
        if ticker:
            tickers.add(ticker)
    return tickers


def staged_supported_proof_tickers(repo_root: Path, *, lane: str, path: str) -> set[str]:
    supported: set[str] = set()
    for line in load_staged_added_lines(repo_root, "data/reviewed_batch_proofs.csv"):
        parts = next(csv.reader([line]), [])
        if len(parts) < 15:
            continue
        row_lane = parts[3].strip().lower()
        ticker = parts[5].strip().upper()
        outcome = parts[-2].strip().lower()
        if row_lane != lane or outcome not in SUPPORTED_REVIEW_OUTCOMES:
            continue
        if path not in line:
            continue
        if ticker:
            supported.add(ticker)
    return supported


def is_staged_reviewed_canonical_data(repo_root: Path, entry: StatusEntry) -> bool:
    lane = REVIEWED_CANONICAL_DATA_PATHS.get(entry.path)
    if lane is None:
        return False
    tickers = staged_reviewed_data_tickers(repo_root, entry)
    if not tickers:
        return False
    supported_tickers = staged_supported_proof_tickers(repo_root, lane=lane, path=entry.path)
    return tickers.issubset(supported_tickers)


def staged_hygiene_blockers(entries: list[StatusEntry], repo_root: Path) -> dict[str, list[StatusEntry]]:
    groups = group_entries(entries)
    reviewed_generated = [
        entry
        for entry in groups["generated_csv_churn"]
        if is_staged_reviewed_canonical_data(repo_root, entry)
    ]
    reviewed_paths = {entry.path for entry in reviewed_generated}
    return {
        "generated_csv_churn": [
            entry for entry in groups["generated_csv_churn"] if entry.path not in reviewed_paths
        ],
        "reviewed_canonical_data": reviewed_generated,
        "review_manually": groups["review_manually"],
    }


def staged_hygiene_has_blockers_for_repo(entries: list[StatusEntry], repo_root: Path) -> bool:
    blockers = staged_hygiene_blockers(entries, repo_root)
    return bool(blockers["generated_csv_churn"] or blockers["review_manually"])


def tracked_entries(entries: list[StatusEntry]) -> list[StatusEntry]:
    return [entry for entry in entries if entry.status != "??"]


def untracked_entries(entries: list[StatusEntry]) -> list[StatusEntry]:
    return [entry for entry in entries if entry.status == "??"]


def format_shell_command(
    prefix: str,
    entries: list[StatusEntry],
    *,
    max_paths: int = 60,
    empty_message: str = "# no matching paths",
) -> list[str]:
    if not entries:
        return [f"  {empty_message}"]
    paths = " ".join(quote(entry.path) for entry in entries[:max_paths])
    rows = [f"  {prefix} {paths}"]
    if len(entries) > max_paths:
        rows.append(f"  # Review {len(entries) - max_paths} additional path(s) manually before extending this command.")
    return rows


def build_data_release_decision_report(entries: list[StatusEntry]) -> str:
    groups = group_entries(entries)
    product = groups["product_candidate"]
    generated = groups["generated_csv_churn"]
    manual = groups["review_manually"]
    sample_reports = groups["sample_report_candidate"]
    proof_artifacts = [
        entry
        for entry in product
        if entry.path
        in {
            "data/reviewed_data_proofs.csv",
            "data/reviewed_batch_proofs.csv",
            "outputs/reviewed_batch_packet.csv",
            "outputs/reviewed_batch_packet.md",
        }
    ]
    product_without_proofs = [entry for entry in product if entry not in proof_artifacts]
    cleanup_tracked = tracked_entries(generated + proof_artifacts)
    cleanup_untracked = untracked_entries(generated + proof_artifacts)

    lines = [
        "Data Release Decision",
        "Read-only: this command does not stage, delete, reset, refresh, rewrite files, or publish data.",
        "Research-only: data release choices are evidence-packaging decisions, not investment advice or execution instructions.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "Working tree is clean.",
                "Recommendation: public code/docs/tests are ready to share; no local data release package is pending.",
                "",
                "Next safe data step:",
                "  make coverage-expansion-loop TOP_N=10",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            format_count_line("Product/code/docs/test candidates", product_without_proofs),
            format_count_line("Reviewed proof artifacts", proof_artifacts),
            format_count_line("Generated CSV/JSON churn", generated),
            format_count_line("Markdown sample report candidates", sample_reports),
            format_count_line("Manual-review paths", manual),
            "",
        ]
    )

    if manual:
        lines.extend(
            [
                "Stop first: manual-review paths are present.",
                "Inspect these before choosing a public-code cleanup or reviewed data release:",
                *format_paths(manual, limit=30),
                "",
            ]
        )

    lines.extend(
        [
            "Recommended decision:",
        ]
    )
    if generated:
        lines.append(
            "  Keep generated CSV/JSON churn local by default. Publish a data snapshot only when the exact refreshed artifacts are the deliverable."
        )
    elif proof_artifacts:
        lines.append(
            "  Proof ledger artifacts changed without generated churn; stage them only if they describe an intentionally reviewed outcome."
        )
    elif product_without_proofs or sample_reports:
        lines.append("  Stage product/docs/tests or reviewed Markdown samples with the normal diff-hygiene path.")
    else:
        lines.append("  No generated data release decision is pending.")

    lines.extend(
        [
            "",
            "Option A - public code/docs release",
            "Use when refreshed data was only local working evidence and should not become the public snapshot.",
            "Copy only after confirming the local batch evidence can be discarded:",
        ]
    )
    lines.extend(format_shell_command("git restore --", cleanup_tracked, empty_message="# no tracked generated/proof paths to restore"))
    lines.extend(format_shell_command("rm -f", cleanup_untracked, empty_message="# no untracked generated/proof paths to remove"))
    lines.extend(
        [
            "  make diff-hygiene-summary",
            "",
            "Option B - reviewed data snapshot release",
            "Use only when the refreshed CSVs and proof artifacts are intentionally part of the deliverable.",
        ]
    )
    if proof_artifacts:
        lines.extend(format_git_add_command(proof_artifacts, label="Stage reviewed proof artifacts"))
    else:
        lines.append("  # No reviewed proof artifact changed; record or review the proof row before publishing data churn.")
    if generated:
        lines.extend(
            [
                "  # Review generated churn individually; do not use git add -A.",
                "  make diff-hygiene-files",
                "  # Inspect outputs/staging/generated_churn.txt, then stage only the exact reviewed artifacts.",
            ]
        )
    else:
        lines.append("  # No generated CSV/JSON churn is present.")
    lines.extend(
        [
            "  make staged-hygiene-check",
            "  make public-check",
            "",
            "Option C - keep local evidence only",
            "Use when the batch result matters locally but should not be committed yet.",
            "  # Do nothing to git; keep the dirty tree local and rerun make diff-hygiene before any commit.",
            "",
            "Do not proceed if:",
            "- source proof is unavailable",
            "- validation, preview, rejected-row review, or apply decision is missing for a mutating workflow",
            "- changed readiness counts or changed tickers are not documented",
            "- generated artifacts cannot be classified before staging",
            "",
            "Research-only guardrail: never stage broker, order execution, auto-trading,",
            "options recommendation, or direct buy/sell instruction language.",
        ]
    )
    return "\n".join(lines)


def build_public_release_package_report(
    entries: list[StatusEntry],
    *,
    branch_status: str = "",
    current_preflight: dict[str, object] | None = None,
    repo_root: Path | None = None,
) -> str:
    groups = group_entries(entries)
    product = groups["product_candidate"]
    sample_reports = groups["sample_report_candidate"]
    generated = groups["generated_csv_churn"]
    manual = groups["review_manually"]
    package_status = package_status_for_groups(groups)
    branch_is_ahead = "[ahead" in (branch_status or "")

    lines = [
        "Public Release Package",
        "Read-only: this command does not stage, delete, reset, refresh, rewrite files, commit, or push.",
        "Research-only: release packaging must preserve data-readiness gates, not investment advice or execution language.",
        f"Branch status: {branch_status or 'not checked'}",
        "",
        *public_release_share_now_lines(groups),
        "",
        *format_license_gate(),
        "",
        *format_provider_setup_gate(current_preflight or load_cached_source_preflight(repo_root)),
        "",
    ]
    if not entries:
        lines.extend(
            [
                "Working tree is clean.",
                f"Package status: {package_status}",
                "Next safe action:",
                "  make public-check",
                "  git push origin main  # only when explicitly asked and after confirming the branch is ready to publish",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            format_count_line("Product/code/docs/test candidates", product),
            format_count_line("Markdown sample report candidates", sample_reports),
            format_count_line("Generated CSV/JSON churn excluded by default", generated),
            format_count_line("Manual-review paths", manual),
            f"Package status: {package_status}",
            "",
        ]
    )
    if manual:
        lines.extend(
            [
                "Stop first: manual-review paths exist.",
                "Inspect these paths before staging or sharing:",
                *format_paths(manual, limit=30),
                "",
            ]
        )

    environment_blocked_lines = (
        [
            "If git staging is environment-blocked:",
            "  # Do not stage generated churn as a workaround.",
            "  make diff-hygiene-files",
            "  # In a normal local terminal, run:",
            "  git add --pathspec-from-file=outputs/staging/product_files.txt",
            "  make staged-hygiene-check",
        ]
        if product
        else [
            "If git staging is environment-blocked:",
            "  # No product files are queued; do not stage generated churn as a workaround.",
            "  make diff-hygiene-files",
        ]
    )

    lines.extend(
        [
            "Release verdict:",
            (
                "  Ready to stage product files after public-check and local dashboard smoke pass."
                if product and not manual
                else (
                    "  Stop first: resolve manual-review paths before staging."
                    if manual
                    else "  No reviewed product package to stage; keep generated churn local unless intentionally selected as evidence."
                )
            ),
            "",
            "Stage only reviewed product/docs/tests by default:",
            *format_git_add_command(product, label="Stage public release package"),
            "  make staged-hygiene-check",
            "  git diff --cached --stat",
            "  git diff --cached --check",
            "  git diff --cached --name-only",
            "",
            *format_sample_report_review_block(sample_reports),
            "",
            *environment_blocked_lines,
            "",
            "Do not stage generated churn by default:",
        ]
    )
    if generated:
        lines.extend(format_paths(generated, limit=40))
    else:
        lines.append("  none")
    commit_share_lines = (
        [
            "Commit and push only after staged hygiene passes:",
            "  git commit -m \"Improve pilot handoff and workflow continuity\"",
            "  git status --short --branch",
            "  git push origin main  # only when explicitly asked",
        ]
        if product
        else (
            [
                "Commit and push:",
                "  # No reviewed product package to commit; generated churn remains local.",
                "  Reviewed local commit is ahead of origin; push only when explicitly asked and after public-check passes.",
                "  git status --short --branch",
                "  git push origin main  # only when explicitly asked",
            ]
            if branch_is_ahead
            else [
                "Commit and push:",
                "  # No reviewed product package to commit; generated churn remains local.",
                "  git status --short --branch",
            ]
        )
    )

    lines.extend(
        [
            "",
            "Required final checks before commit/share:",
            "  make public-check",
            "  make pilot-readiness-check TOP_N=10",
            "  make browser-qa-evidence",
            "  make browser-qa-capture-plan  # before replacing public/GitHub/LinkedIn screenshots",
            "  # If screenshots were recaptured and visually reviewed, stage only those assets:",
            f"  {reviewed_screenshot_asset_stage_command()}",
            "  make dashboard-smoke  # rerun in a normal local terminal if sandbox socket binding is limited",
            "  git diff --check",
            "",
            *commit_share_lines,
            "",
            "Do not proceed if:",
            "- public-check fails",
            "- dashboard smoke fails for product-code reasons",
            "- generated CSV/JSON churn is staged unintentionally",
            "- public screenshots are replaced without real Streamlit route review and first-viewport marker checks",
            "- missing fundamentals, peers, earnings, estimates, valuation inputs, or metrics are presented as conclusions",
            "- source proof, validate, preview, rejected-row review, apply or skip decision, rebuilt readiness, or proof record gates are incomplete",
            "",
            "Research-only guardrail: never stage broker, order execution, auto-trading,",
            "options recommendation, or direct buy/sell instruction language.",
        ]
    )
    return "\n".join(lines)


def build_public_release_handoff_report(
    entries: list[StatusEntry],
    *,
    branch_status: str = "",
    current_preflight: dict[str, object] | None = None,
    repo_root: Path | None = None,
) -> str:
    groups = group_entries(entries)
    product = groups["product_candidate"]
    sample_reports = groups["sample_report_candidate"]
    generated = groups["generated_csv_churn"]
    manual = groups["review_manually"]
    package_status = package_status_for_groups(groups)

    lines = [
        "Public Release Terminal Handoff",
        "Read-only: this command prints the safe terminal sequence only. It does not stage, delete, reset, refresh, rewrite files, commit, or push.",
        "Research-only: the release handoff must preserve readiness-first workflow, blocked states, and no advice/execution boundaries.",
        "",
        format_count_line("Product/code/docs/test candidates", product),
        format_count_line("Markdown sample report candidates", sample_reports),
        format_count_line("Generated CSV/JSON churn excluded by default", generated),
        format_count_line("Manual-review paths", manual),
        f"Branch status: {branch_status or 'not checked'}",
        f"Package status: {package_status}",
        "",
        *format_license_gate(),
        "",
        *format_provider_setup_gate(current_preflight or load_cached_source_preflight(repo_root)),
        "",
    ]
    if manual:
        lines.extend(
            [
                "Stop first: manual-review paths exist.",
                "Inspect these paths before staging or sharing:",
                *format_paths(manual, limit=30),
                "",
            ]
        )
    commit_step = (
        [
            "Step 4 - commit locally if staged hygiene passes:",
            "  git commit -m \"Improve pilot handoff and workflow continuity\"",
        ]
        if product
        else [
            "Step 4 - skip commit when no reviewed files are staged:",
            "  # no commit; generated churn remains local",
        ]
    )

    lines.extend(
        [
            "Step 1 - verify before staging:",
            "  make public-check",
            "  make pilot-readiness-check TOP_N=10",
            "  make public-release-package",
            "  make browser-qa-evidence",
            "  make browser-qa-capture-plan  # only needed before replacing screenshots",
            "  git diff --check",
            "",
            "Step 2 - stage only reviewed product/docs/tests by default:",
            *format_git_add_command(product, label="Stage public release handoff"),
            "  # If screenshots were recaptured and visually reviewed, stage only those evidence assets:",
            f"  {reviewed_screenshot_asset_stage_command()}",
            "",
            *format_sample_report_review_block(sample_reports),
            "",
            "Step 3 - inspect staged package:",
            "  make staged-hygiene-check",
            "  git diff --cached --stat",
            "  git diff --cached --check",
            "  git diff --cached --name-only",
            "",
            *commit_step,
            "",
            "Step 5 - push only when explicitly asked after the local commit is reviewed:",
            "  git status --short --branch",
            "  git push origin main  # only when explicitly asked",
            "",
            "Generated churn to leave unstaged by default:",
        ]
    )
    if generated:
        lines.extend(format_paths(generated, limit=40))
    else:
        lines.append("  none")
    lines.extend(
        [
            "",
            "Do not proceed if:",
            "- staged hygiene shows generated CSV/JSON churn or manual-review paths",
            "- public-check fails",
            "- dashboard smoke fails for product-code reasons",
            "- screenshots are replaced without real Streamlit route review and first-viewport marker checks",
            "- blocked fundamentals, shares, peers, earnings, estimates, valuation inputs, or metrics are presented as conclusions",
            "",
            "Research-only guardrail: never stage broker, order execution, auto-trading,",
            "options recommendation, or direct buy/sell instruction language.",
        ]
    )
    return "\n".join(lines)


def build_staged_check_report(entries: list[StatusEntry], repo_root: Path | None = None) -> str:
    groups = group_entries(entries)
    repo_root = repo_root or Path.cwd()
    blockers = staged_hygiene_blockers(entries, repo_root)
    lines = [
        "Staged Hygiene Check",
        "Read-only: this command inspects the staged diff and does not stage, delete, reset, refresh, or rewrite files.",
        "",
    ]
    if not entries:
        lines.append("No staged changes. Nothing to commit yet.")
        return "\n".join(lines)

    lines.extend(
        [
            format_count_line("Staged product/code/docs/test files", groups["product_candidate"]),
            format_count_line("Staged Markdown sample reports", groups["sample_report_candidate"]),
            format_count_line("Staged generated CSV/JSON churn", groups["generated_csv_churn"]),
            format_count_line("Staged reviewed canonical data", blockers["reviewed_canonical_data"]),
            format_count_line("Staged manual-review paths", groups["review_manually"]),
            "",
        ]
    )
    if staged_hygiene_has_blockers_for_repo(entries, repo_root):
        lines.extend(
            [
                "Staged hygiene check failed.",
                "Generated CSV/JSON churn or manual-review paths are staged. Unstage or explicitly review them before committing.",
            ]
        )
        if blockers["generated_csv_churn"]:
            lines.extend(["", "Generated CSV/JSON churn currently staged:"])
            lines.extend(format_paths(blockers["generated_csv_churn"], limit=40))
        if blockers["review_manually"]:
            lines.extend(["", "Manual-review paths currently staged:"])
            lines.extend(format_paths(blockers["review_manually"], limit=40))
    else:
        lines.extend(
            [
                "Staged hygiene check passed.",
                "Only product/code/docs/tests, reviewed Markdown sample reports, proof artifacts, and proof-backed canonical data are staged.",
            ]
        )
        if blockers["reviewed_canonical_data"]:
            lines.extend(["", "Reviewed canonical data accepted by proof ledger:"])
            lines.extend(format_paths(blockers["reviewed_canonical_data"], limit=40))
    lines.extend(
        [
            "",
            "Research-only guardrail: never stage broker, order execution, auto-trading,",
            "options recommendation, or direct buy/sell instruction language.",
        ]
    )
    return "\n".join(lines)


def build_report(entries: list[StatusEntry]) -> str:
    groups = group_entries(entries)
    lines = [
        "Diff Hygiene Report",
        "Read-only: this command does not stage, delete, reset, refresh, or rewrite files.",
        "",
    ]
    if not entries:
        lines.append("Working tree is clean.")
        return "\n".join(lines)

    sections = (
        (
            "Likely product/code/docs/test candidates",
            groups["product_candidate"],
            "Review normally. New docs/scripts/tests in this bucket can be staged when intentional.",
        ),
        (
            "Small Markdown sample report candidates",
            groups["sample_report_candidate"],
            "Stage only if the regenerated examples demonstrate intentional visitor-facing behavior.",
        ),
        (
            "Generated CSV/JSON churn",
            groups["generated_csv_churn"],
            "Do not stage by default. Keep only if the data artifact itself is the deliverable.",
        ),
        (
            "Manual review required",
            groups["review_manually"],
            "Inspect these paths before deciding whether they belong in the public diff.",
        ),
    )
    for title, section_entries, note in sections:
        lines.extend([title, note, format_count_line("Count", section_entries)])
        lines.extend(format_paths(section_entries) if section_entries else ["  none"])
        lines.append("")

    lines.extend(
        [
            "Safe staging suggestions:",
            "These commands intentionally exclude generated CSV/JSON churn.",
            "They include new product docs/scripts/tests because those are commonly intentional in public polish work.",
            *format_git_add_command(groups["product_candidate"], label="Stage product/code/docs/tests only"),
            *format_git_add_command(
                groups["product_candidate"] + groups["sample_report_candidate"],
                label="Stage product files plus reviewed Markdown sample reports",
            ),
            "",
            "Verification commands:",
            "  git diff --stat",
            "  git diff --check",
            "  make staged-hygiene-check",
            "  git diff --cached --stat",
            "  git diff --cached --name-only",
            "",
            "Research-only guardrail: never stage broker, order execution, auto-trading,",
            "options recommendation, or direct buy/sell instruction language.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a read-only git diff hygiene report.")
    parser.add_argument("--summary", action="store_true", help="Print counts and guidance without long file lists.")
    parser.add_argument(
        "--write-files",
        action="store_true",
        help="Write newline-delimited staging candidate path lists under outputs/staging.",
    )
    parser.add_argument(
        "--staged-check",
        action="store_true",
        help="Fail if the staged diff includes generated CSV/JSON churn or manual-review paths.",
    )
    parser.add_argument(
        "--data-release-decision",
        action="store_true",
        help="Print read-only keep-local vs reviewed-data-release vs cleanup guidance for dirty generated artifacts.",
    )
    parser.add_argument(
        "--public-release-package",
        action="store_true",
        help="Print read-only product staging, generated-exclusion, and final public-share guidance.",
    )
    parser.add_argument(
        "--public-release-handoff",
        action="store_true",
        help="Print a copy-ready terminal handoff for verifying, staging, committing, and pushing a public-safe package.",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    if args.staged_check:
        entries = load_staged_status(repo_root)
        print(build_staged_check_report(entries, repo_root))
        return 1 if staged_hygiene_has_blockers_for_repo(entries, repo_root) else 0
    entries = load_status(repo_root)
    if args.public_release_package:
        print(build_public_release_package_report(entries, branch_status=load_branch_status(repo_root), repo_root=repo_root))
        return 0
    if args.public_release_handoff:
        print(build_public_release_handoff_report(entries, branch_status=load_branch_status(repo_root), repo_root=repo_root))
        return 0
    if args.data_release_decision:
        print(build_data_release_decision_report(entries))
        return 0
    if args.write_files:
        files = write_staging_files(entries, repo_root / "outputs" / "staging")
        print(build_file_report(files, repo_root, package_status=package_status_for_groups(group_entries(entries))))
    else:
        print(build_summary_report(entries) if args.summary else build_report(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
