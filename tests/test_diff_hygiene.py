from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_diff_hygiene_module():
    module_path = Path("scripts/diff_hygiene.py")
    spec = importlib.util.spec_from_file_location("diff_hygiene", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_diff_hygiene_classifies_generated_csv_churn_separately():
    module = load_diff_hygiene_module()

    assert module.classify_path("data/reports/ticker_readiness_report.csv") == "generated_csv_churn"
    assert module.classify_path("data/fundamentals.csv") == "generated_csv_churn"
    assert module.classify_path("data/outputs/research_decisions.csv") == "generated_csv_churn"
    assert module.classify_path("outputs/research_decisions.csv") == "generated_csv_churn"
    assert module.classify_path("outputs/decision_proof_queue.md") == "generated_csv_churn"


def test_diff_hygiene_keeps_markdown_reports_as_reviewable_examples():
    module = load_diff_hygiene_module()

    assert module.classify_path("outputs/stock_reports/nvda.md") == "sample_report_candidate"
    assert module.classify_path("outputs/stock_reports/qqq.md") == "sample_report_candidate"


def test_diff_hygiene_classifies_product_files_as_commit_candidates():
    module = load_diff_hygiene_module()

    for path in (
        ".gitignore",
        ".streamlit/config.toml",
        "README.md",
        "Makefile",
        "docs/DIFF_HYGIENE_AUDIT.md",
        "src/dashboard.py",
        "tests/test_launchers.py",
        "scripts/diff_hygiene.py",
        "stock_analysis/pipeline.py",
        "data/reviewed_data_proofs.csv",
        "data/reviewed_batch_proofs.csv",
        "outputs/reviewed_batch_packet.md",
        "outputs/reviewed_batch_packet.csv",
    ):
        assert module.classify_path(path) == "product_candidate"


def test_diff_hygiene_counts_untracked_and_staged_added_files_as_new():
    module = load_diff_hygiene_module()

    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("??", "docs/METHODOLOGY.md"),
        module.StatusEntry("A", "tests/test_new_feature.py"),
    ]

    assert module.count_new(entries) == 2
    assert module.format_count_line("Files", entries) == "Files: 3 (1 changed, 2 new)"


def test_diff_hygiene_report_is_read_only_and_research_only():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "outputs/research_decisions.csv"),
        module.StatusEntry("??", "outputs/stock_reports/nvda.md"),
    ]

    report = module.build_report(entries)

    assert "Read-only: this command does not stage, delete, reset, refresh, or rewrite files." in report
    assert "Likely product/code/docs/test candidates" in report
    assert "Count: 1 (1 changed, 0 new)" in report
    assert "Generated CSV/JSON churn" in report
    assert "Small Markdown sample report candidates" in report
    assert "Safe staging suggestions:" in report
    assert "These commands intentionally exclude generated CSV/JSON churn." in report
    assert "They include new product docs/scripts/tests" in report
    assert "make staged-hygiene-check" in report
    assert "Research-only guardrail" in report


def test_diff_hygiene_file_report_points_to_pathspec_files(tmp_path: Path):
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "outputs/research_decisions.csv"),
        module.StatusEntry("M", "outputs/stock_reports/nvda.md"),
    ]

    files = module.write_staging_files(entries, tmp_path / "outputs" / "staging")
    report = module.build_file_report(files, tmp_path)

    assert files["product_files"].read_text(encoding="utf-8") == "src/dashboard.py\n"
    assert files["product_plus_reports"].read_text(encoding="utf-8") == "src/dashboard.py\noutputs/stock_reports/nvda.md\n"
    assert files["sample_reports"].read_text(encoding="utf-8") == "outputs/stock_reports/nvda.md\n"
    assert files["generated_churn"].read_text(encoding="utf-8") == "outputs/research_decisions.csv\n"
    assert files["manual_review"].read_text(encoding="utf-8") == ""
    staging_readme = files["readme"].read_text(encoding="utf-8")
    assert "Diff Hygiene Local Staging Files" in staging_readme
    assert "Product files: outputs/staging/product_files.txt (1 path(s))" in staging_readme
    assert "git add --pathspec-from-file=outputs/staging/product_files.txt" in staging_readme
    assert "make staged-hygiene-check" in staging_readme
    assert "Do not stage generated churn by default" in staging_readme
    assert "Research-only guardrail" in staging_readme
    assert "Diff Hygiene File Lists" in report
    assert "did not stage, delete, reset, refresh, or rewrite product data" in report
    assert "Product files: outputs/staging/product_files.txt (1 path(s))" in report
    assert "Product plus reviewed Markdown reports: outputs/staging/product_plus_reports.txt (2 path(s))" in report
    assert "Markdown sample reports only: outputs/staging/sample_reports.txt (1 path(s))" in report
    assert "Generated CSV/JSON churn to avoid by default: outputs/staging/generated_churn.txt (1 path(s))" in report
    assert "Manual-review paths: outputs/staging/manual_review.txt (0 path(s))" in report
    assert "Usage notes: outputs/staging/README.txt" in report
    assert "git add --pathspec-from-file=outputs/staging/product_files.txt" in report
    assert "git add --pathspec-from-file=outputs/staging/product_plus_reports.txt" in report
    assert "make staged-hygiene-check" in report
    assert "Do not stage generated churn by default" in report
    assert "broker" in report
    assert "order execution" in report
    assert "direct buy/sell" in report


def test_diff_hygiene_staging_suggestions_exclude_generated_churn():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "docs/METHODOLOGY.md"),
        module.StatusEntry("M", "outputs/research_decisions.csv"),
        module.StatusEntry("M", "data/reports/ticker_readiness_report.csv"),
        module.StatusEntry("M", "outputs/stock_reports/nvda.md"),
    ]

    report = module.build_report(entries)

    assert "git add -- src/dashboard.py docs/METHODOLOGY.md" in report
    assert "outputs/stock_reports/nvda.md" in report
    staging_block = report.split("Safe staging suggestions:", 1)[1].split("Verification commands:", 1)[0]
    assert "outputs/research_decisions.csv" not in staging_block
    assert "data/reports/ticker_readiness_report.csv" not in staging_block


def test_diff_hygiene_summary_is_concise_but_preserves_guardrails():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "outputs/research_decisions.csv"),
        module.StatusEntry("M", "outputs/stock_reports/nvda.md"),
    ]

    report = module.build_summary_report(entries)

    assert "Diff Hygiene Summary" in report
    assert "Product/code/docs/test candidates: 1 (1 changed, 0 new)" in report
    assert "Markdown sample report candidates: 1 (1 changed, 0 new)" in report
    assert "Generated CSV/JSON churn to avoid by default: 1 (1 changed, 0 new)" in report
    assert "Use `make diff-hygiene` for full file lists" in report
    assert "New docs/scripts/tests are product candidates when intentional" in report
    assert "git add --" not in report
    assert "src/dashboard.py" not in report
    assert "outputs/research_decisions.csv" not in report
    assert "Research-only guardrail" in report


def test_data_release_decision_reports_clean_public_state():
    module = load_diff_hygiene_module()

    report = module.build_data_release_decision_report([])

    assert "Data Release Decision" in report
    assert "Read-only: this command does not stage, delete, reset, refresh, rewrite files, or publish data." in report
    assert "Working tree is clean." in report
    assert "public code/docs/tests are ready to share" in report
    assert "make coverage-expansion-loop TOP_N=10" in report
    assert "investment advice" in report


def test_data_release_decision_keeps_generated_churn_local_by_default():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "data/prices.csv"),
        module.StatusEntry("M", "data/reports/ticker_readiness_report.csv"),
        module.StatusEntry("M", "data/reviewed_batch_proofs.csv"),
        module.StatusEntry("??", "data/reports/ticker_readiness_report.previous.csv"),
        module.StatusEntry("M", "src/dashboard.py"),
    ]

    report = module.build_data_release_decision_report(entries)

    assert "Reviewed proof artifacts: 1 (1 changed, 0 new)" in report
    assert "Generated CSV/JSON churn: 3 (2 changed, 1 new)" in report
    assert "Keep generated CSV/JSON churn local by default" in report
    assert "Option A - public code/docs release" in report
    assert "git restore -- data/prices.csv data/reports/ticker_readiness_report.csv data/reviewed_batch_proofs.csv" in report
    assert "rm -f data/reports/ticker_readiness_report.previous.csv" in report
    assert "Option B - reviewed data snapshot release" in report
    assert "git add -- data/reviewed_batch_proofs.csv" in report
    assert "Review generated churn individually; do not use git add -A." in report
    assert "Option C - keep local evidence only" in report
    assert "changed readiness counts or changed tickers are not documented" in report
    assert "broker" in report
    assert "direct buy/sell" in report


def test_staged_hygiene_check_passes_clean_product_and_sample_report_stage():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "config.yaml"),
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("A", "docs/METHODOLOGY.md"),
        module.StatusEntry("D", "stock_analysis/pipeline.py"),
        module.StatusEntry("M", "outputs/stock_reports/nvda.md"),
    ]

    report = module.build_staged_check_report(entries)

    assert module.staged_hygiene_has_blockers(entries) is False
    assert "Staged Hygiene Check" in report
    assert "Staged product/code/docs/test files: 4 (3 changed, 1 new)" in report
    assert "Staged Markdown sample reports: 1 (1 changed, 0 new)" in report
    assert "Staged generated CSV/JSON churn: 0 (0 changed, 0 new)" in report
    assert "Staged hygiene check passed." in report
    assert "Research-only guardrail" in report


def test_staged_hygiene_check_fails_generated_or_manual_review_stage():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "outputs/research_decisions.csv"),
        module.StatusEntry("A", "private_notes.txt"),
    ]

    report = module.build_staged_check_report(entries)

    assert module.staged_hygiene_has_blockers(entries) is True
    assert "Staged hygiene check failed." in report
    assert "Generated CSV/JSON churn or manual-review paths are staged" in report
    assert "outputs/research_decisions.csv" in report
    assert "private_notes.txt" in report


def test_staged_hygiene_check_handles_empty_stage():
    module = load_diff_hygiene_module()
    report = module.build_staged_check_report([])

    assert module.staged_hygiene_has_blockers([]) is False
    assert "No staged changes. Nothing to commit yet." in report
