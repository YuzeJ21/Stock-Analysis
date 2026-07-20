from __future__ import annotations

import importlib.util
import json
import subprocess
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


def test_pr_range_hygiene_inspects_committed_range_not_clean_worktree(tmp_path: Path):
    module = load_diff_hygiene_module()
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Range Test")
    git("config", "user.email", "range@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "base")
    base_sha = git("rev-parse", "HEAD")
    generated = repo / "data" / "reports" / "readiness.json"
    generated.parent.mkdir(parents=True)
    generated.write_text("{}\n", encoding="utf-8")
    git("add", "data/reports/readiness.json")
    git("commit", "-m", "generated")
    head_sha = git("rev-parse", "HEAD")

    assert git("status", "--porcelain") == ""
    entries = module.load_range_status(repo, base_sha, head_sha)
    report = module.build_range_check_report(entries, base_sha, head_sha)

    assert entries == [module.StatusEntry("A", "data/reports/readiness.json")]
    assert module.range_hygiene_has_blockers(entries) is True
    assert "Pull Request Range Hygiene Check" in report
    assert "data/reports/readiness.json" in report
    assert "failed" in report.lower()


def test_diff_hygiene_keeps_markdown_reports_as_reviewable_examples():
    module = load_diff_hygiene_module()

    assert module.classify_path("outputs/stock_reports/nvda.md") == "sample_report_candidate"
    assert module.classify_path("outputs/stock_reports/qqq.md") == "sample_report_candidate"


def test_diff_hygiene_classifies_product_files_as_commit_candidates():
    module = load_diff_hygiene_module()

    for path in (
        ".gitignore",
        ".github/workflows/commercial-research-beta.yml",
        ".streamlit/config.toml",
        ".streamlit/secrets.toml.example",
        "README.md",
        "Makefile",
        "requirements.txt",
        "config/hosted_demo.env.example",
        "config/provider_keys.env.example",
        "config/source_rights.yml",
        "docs/DIFF_HYGIENE_AUDIT.md",
        "src/dashboard.py",
        "tests/test_launchers.py",
        "scripts/diff_hygiene.py",
        "stock_analysis/pipeline.py",
        "data/reviewed_data_proofs.csv",
        "data/reviewed_batch_proofs.csv",
        "data/reviewed_research_events.csv",
        "data/research_thesis_journal.csv",
        "outputs/reviewed_batch_packet.md",
        "outputs/reviewed_batch_packet.csv",
        "outputs/pilot_readiness_packet.md",
        "data/demo/manifest.json",
        "data/demo/prices.csv",
        "outputs/demo/feature_readiness_summary.csv",
    ):
        assert module.classify_path(path) == "product_candidate"
    assert module.classify_path(".streamlit/secrets.toml") == "review_manually"
    assert module.classify_path("config/hosted_demo.env") == "review_manually"
    assert module.classify_path("config/provider_keys.env") == "review_manually"


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
    assert "Package status: product package pending commit; commit this package before starting another feature slice" in staging_readme
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
    assert "Package status: not checked" in report
    assert "Usage notes: outputs/staging/README.txt" in report
    assert "git add --pathspec-from-file=outputs/staging/product_files.txt" in report
    assert "git add --pathspec-from-file=outputs/staging/product_plus_reports.txt" in report
    assert "make staged-hygiene-check" in report
    assert "Do not stage generated churn by default" in report
    assert "broker" in report
    assert "order execution" in report
    assert "direct buy/sell" in report

    report_with_status = module.build_file_report(
        files,
        tmp_path,
        package_status="product package pending commit; commit this package before starting another feature slice",
    )
    assert "Package status: product package pending commit; commit this package before starting another feature slice" in report_with_status


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
    assert "Package status: product package pending commit; commit this package before starting another feature slice" in report
    assert "Use `make diff-hygiene` for full file lists" in report
    assert "New docs/scripts/tests are product candidates when intentional" in report
    assert "git add --" not in report
    assert "src/dashboard.py" not in report
    assert "outputs/research_decisions.csv" not in report
    assert "Research-only guardrail" in report


def test_diff_hygiene_summary_marks_generated_only_and_clean_states():
    module = load_diff_hygiene_module()

    generated_only = module.build_summary_report([module.StatusEntry("M", "data/prices.csv")])
    clean = module.build_summary_report([])

    assert "Package status: generated churn only; keep it local unless intentionally reviewed as evidence" in generated_only
    assert "Package status: clean; ready for the next reviewed work slice" in clean


def test_diff_hygiene_summary_keeps_sample_reports_out_of_product_package_status():
    module = load_diff_hygiene_module()

    report = module.build_summary_report(
        [
            module.StatusEntry("M", "outputs/stock_reports/apld.md"),
            module.StatusEntry("??", "outputs/stock_reports/newco.md"),
            module.StatusEntry("M", "data/prices.csv"),
        ]
    )

    assert "Product/code/docs/test candidates: 0 (0 changed, 0 new)" in report
    assert "Markdown sample report candidates: 2 (1 changed, 1 new)" in report
    assert "Generated CSV/JSON churn to avoid by default: 1 (1 changed, 0 new)" in report
    assert "Package status: generated/sample report churn only; keep it local unless intentionally reviewed as evidence" in report
    assert "product package pending commit" not in report


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


def test_public_release_package_reports_clean_push_path():
    module = load_diff_hygiene_module()

    report = module.build_public_release_package_report([])

    assert "Public Release Package" in report
    assert "Share-now answer:" in report
    assert "Share as controlled portfolio/demo evidence after public-check passes and generated churn stays excluded." in report
    assert "Do not call this open source or reusable software under the current root LICENSE." in report
    assert "If source-proof queues are exhausted, use provider setup before broad proof loops." in report
    assert "Free public sources: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance" in report
    assert "Keyed free-tier fallbacks: configured -; needs key FMP free tier, Alpha Vantage free tier, Finnhub free tier" in report
    assert "Optional broker boundary: IBKR read-only (disabled unless explicitly configured)" in report
    assert "Read-only: this command does not stage, delete, reset, refresh, rewrite files, commit, or push." in report
    assert "Branch status: not checked" in report
    assert "Working tree is clean." in report
    assert "Package status: clean; ready for the next reviewed work slice" in report
    assert "make public-check" in report
    assert "make browser-qa-capture-plan" not in report
    assert "git push origin main" in report
    assert "only when explicitly asked" in report
    assert "License gate: controlled demo LICENSE found" in report
    assert "root LICENSE" in report
    assert "make license-status" in report
    assert "controlled-demo terms" in report
    assert "investment advice" in report


def test_root_license_is_product_candidate():
    module = load_diff_hygiene_module()

    assert module.classify_path("LICENSE") == "product_candidate"


def test_public_release_package_stages_product_and_excludes_generated_churn():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "Makefile"),
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "tests/test_dashboard_helpers.py"),
        module.StatusEntry("??", "src/price_history_proof_queue.py"),
        module.StatusEntry("M", "data/prices.csv"),
        module.StatusEntry("??", "data/reports/ticker_readiness_report.previous.csv"),
    ]

    report = module.build_public_release_package_report(entries, branch_status="## main...origin/main [ahead 19]")

    assert "Share-now answer:" in report
    assert "Not yet: commit the reviewed product package first, then rerun public-check." in report
    assert "Do not stage generated churn or sample reports unless exact artifacts are reviewed evidence." in report
    assert "Product/code/docs/test candidates: 4 (3 changed, 1 new)" in report
    assert "Generated CSV/JSON churn excluded by default: 2 (1 changed, 1 new)" in report
    assert "Branch status: ## main...origin/main [ahead 19]" in report
    assert "Package status: product package pending commit; commit this package before starting another feature slice" in report
    assert "Ready to stage product files after public-check and local dashboard smoke pass." in report
    assert "git add -- Makefile src/dashboard.py tests/test_dashboard_helpers.py src/price_history_proof_queue.py" in report
    staging_block = report.split("Stage only reviewed product/docs/tests", 1)[1].split("Do not stage generated churn", 1)[0]
    assert "data/prices.csv" not in staging_block
    assert "data/reports/ticker_readiness_report.previous.csv" not in staging_block
    assert "git diff --cached --check" in staging_block
    assert "git diff --cached --name-only" in staging_block
    assert "make pilot-readiness-check TOP_N=10" in report
    assert "make browser-qa-evidence" in report
    assert "make browser-qa-capture-plan" in report
    assert "If screenshots were recaptured and visually reviewed, stage only those assets" in report
    assert "git add -- docs/assets/single-stock-workflow-fit-real.jpg docs/assets/operator-data-health-proof-real.jpg docs/assets/operator-data-health-queue-routing-real.jpg" in report
    assert "make dashboard-smoke" in report
    assert "If git staging is environment-blocked:" in report
    assert "Do not stage generated churn as a workaround." in report
    assert "make diff-hygiene-files" in report
    assert "git add --pathspec-from-file=outputs/staging/product_files.txt" in report
    assert "git add --pathspec-from-file=outputs/staging/product_plus_reports.txt" not in report
    assert "git commit -m \"Improve pilot handoff and workflow continuity\"" in report
    assert "git status --short --branch" in report
    assert "git push origin main" in report
    assert "only when explicitly asked" in report
    assert "License gate: controlled demo LICENSE found" in report
    assert "root LICENSE" in report
    assert "make license-status" in report
    assert "controlled-demo terms" in report
    assert "Provider setup gate:" in report
    assert "Coverage unlock decision:" in report
    assert "No broad coverage batch should run from setup alone" in report
    assert "Provider setup only makes a source executable" in report
    assert "readiness changes still require validate, preview, rejected-row review" in report
    assert "Do not retry exhausted proof queues" in report
    assert "make provider-setup-checklist" in report
    assert "Configure first: FMP free tier" in report
    assert "FMP_API_KEY" in report
    assert "Reviewed one-ticker smoke:" in report
    assert "One-ticker smoke:" not in report
    assert "make fmp-smoke TICKER=<ticker>" in report
    assert "Do not configure all missing providers at once" in report
    assert "source proof, validate, preview" in report
    assert "real Streamlit route review" in report
    assert "Research-only guardrail" in report
    assert "direct buy/sell" in report


def test_public_release_package_uses_cached_source_gate_when_available():
    module = load_diff_hygiene_module()
    current_preflight = {
        "source_activation_console_v2": {
            "operator_summary": {
                "can_run_now": ["coverage_workflow_evidence"],
                "needs_setup": ["fmp"],
                "avoid_repeating": ["fundamentals_share_count_source_ladder"],
                "next_step": "make project-status",
                "next_step_reason": "Current source-proof queues are exhausted.",
            }
        }
    }

    report = module.build_public_release_package_report(
        [module.StatusEntry("M", "src/dashboard.py")],
        current_preflight=current_preflight,
    )

    assert "current gate says coverage_workflow_evidence" in report
    assert "Do not retry fundamentals_share_count_source_ladder" in report
    assert "Current source-proof queues are exhausted" in report
    assert "current gate says -." not in report


def test_public_release_package_does_not_stage_broad_sample_reports_by_default():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "outputs/stock_reports/apld.md"),
        module.StatusEntry("??", "outputs/stock_reports/new_name.md"),
    ]

    report = module.build_public_release_package_report(entries)

    assert "Markdown sample report candidates: 2 (1 changed, 1 new)" in report
    assert "Stage only reviewed product/docs/tests by default:" in report
    staging_block = report.split("Stage only reviewed product/docs/tests by default:", 1)[1].split(
        "Sample reports are evidence-only by default:", 1
    )[0]
    assert "git add -- src/dashboard.py" in staging_block
    assert "outputs/stock_reports/apld.md" not in staging_block
    assert "outputs/stock_reports/new_name.md" not in staging_block
    sample_block = report.split("Sample reports are evidence-only by default:", 1)[1].split(
        "Do not stage generated churn by default:", 1
    )[0]
    assert "outputs/stock_reports/apld.md" in sample_block
    assert "outputs/stock_reports/new_name.md" in sample_block
    assert "Stage a specific report only after reviewing that exact artifact." in sample_block


def test_public_release_package_surfaces_push_when_branch_ahead_without_product_changes():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "data/prices.csv"),
        module.StatusEntry("M", "outputs/feature_readiness_summary.csv"),
    ]

    report = module.build_public_release_package_report(entries, branch_status="## main...origin/main [ahead 1]")

    assert "No reviewed product package to stage; keep generated churn local unless intentionally selected as evidence." in report
    assert "Reviewed local commit is ahead of origin; push only when explicitly asked and after public-check passes." in report
    assert "git push origin main  # only when explicitly asked" in report
    assert "No reviewed product package to commit; generated churn remains local." in report


def test_diff_hygiene_treats_pilot_share_brief_as_reviewed_product_artifact():
    module = load_diff_hygiene_module()

    assert module.classify_path("outputs/pilot_share_brief.md") == "product_candidate"
    assert module.is_generated_churn("outputs/pilot_share_brief.md") is False


def test_public_release_handoff_prints_terminal_safe_sequence():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "Makefile"),
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("??", "src/dashboard_navigation.py"),
        module.StatusEntry("M", "tests/test_dashboard_helpers.py"),
        module.StatusEntry("M", "data/prices.csv"),
        module.StatusEntry("??", "data/reports/ticker_readiness_report.previous.csv"),
    ]

    report = module.build_public_release_handoff_report(entries, branch_status="## main...origin/main")

    assert "Public Release Terminal Handoff" in report
    assert "Read-only" in report
    assert "Product/code/docs/test candidates: 4 (3 changed, 1 new)" in report
    assert "Generated CSV/JSON churn excluded by default: 2 (1 changed, 1 new)" in report
    assert "Branch status: ## main...origin/main" in report
    assert "Package status: product package pending commit; commit this package before starting another feature slice" in report
    assert "License gate: controlled demo LICENSE found" in report
    assert "root LICENSE" in report
    assert "make license-status" in report
    assert "controlled-demo terms" in report
    assert "Provider setup gate:" in report
    assert "make provider-setup-checklist" in report
    assert "Configure first: FMP free tier" in report
    assert "FMP_API_KEY" in report
    assert "Reviewed one-ticker smoke:" in report
    assert "One-ticker smoke:" not in report
    assert "make fmp-smoke TICKER=<ticker>" in report
    assert "Do not configure all missing providers at once" in report
    assert "Step 1 - verify before staging" in report
    assert "make public-check" in report
    assert "make pilot-readiness-check TOP_N=10" in report
    assert "make public-release-package" in report
    assert "make browser-qa-evidence" in report
    assert "make browser-qa-capture-plan" in report
    assert "git add -- Makefile src/dashboard.py src/dashboard_navigation.py tests/test_dashboard_helpers.py" in report
    assert "If screenshots were recaptured and visually reviewed, stage only those evidence assets" in report
    assert "git add -- docs/assets/single-stock-workflow-fit-real.jpg docs/assets/operator-data-health-proof-real.jpg docs/assets/operator-data-health-queue-routing-real.jpg" in report
    assert "make staged-hygiene-check" in report
    assert "git diff --cached --check" in report
    assert "git commit -m \"Improve pilot handoff and workflow continuity\"" in report
    assert "git push origin main" in report
    assert "only when explicitly asked" in report
    staging_block = report.split("Step 2 - stage only", 1)[1].split("Step 3 - inspect", 1)[0]
    assert "data/prices.csv" not in staging_block
    assert "ticker_readiness_report.previous.csv" not in staging_block
    assert "data/prices.csv" in report.split("Generated churn to leave unstaged by default:", 1)[1]
    assert "real Streamlit route review" in report
    assert "Research-only guardrail" in report
    assert "direct buy/sell" in report


def test_public_release_handoff_surfaces_stale_github_link_when_branch_ahead():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "data/prices.csv"),
        module.StatusEntry("M", "outputs/feature_readiness_summary.csv"),
    ]

    report = module.build_public_release_handoff_report(
        entries,
        branch_status="## main...origin/main [ahead 4]",
    )

    assert "Branch status: ## main...origin/main [ahead 4]" in report
    assert "GitHub pilot link is not current until reviewed local commits are pushed." in report
    assert "push only when explicitly asked after public-check passes and generated churn stays excluded" in report


def test_public_release_handoff_loads_cached_preflight_from_repo_root(tmp_path):
    module = load_diff_hygiene_module()
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "session_source_preflight.json").write_text(
        json.dumps(
            {
                "source_activation_console_v2": {
                    "operator_summary": {
                        "can_run_now": ["coverage_workflow_evidence"],
                        "needs_setup": ["fmp", "alpha_vantage"],
                        "avoid_repeating": ["fundamentals_share_count_source_ladder"],
                        "next_step": "make project-status",
                        "next_step_reason": "Wait for keyed provider data before retrying.",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    report = module.build_public_release_handoff_report(
        [module.StatusEntry("M", "src/dashboard.py")],
        repo_root=tmp_path,
    )

    assert "current gate says coverage_workflow_evidence" in report
    assert "Do not retry fundamentals_share_count_source_ladder" in report
    assert "current gate says -." not in report


def test_public_release_handoff_does_not_stage_broad_sample_reports_by_default():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("M", "outputs/stock_reports/apld.md"),
        module.StatusEntry("??", "outputs/stock_reports/new_name.md"),
    ]

    report = module.build_public_release_handoff_report(entries)

    assert "Markdown sample report candidates: 2 (1 changed, 1 new)" in report
    assert "Step 2 - stage only reviewed product/docs/tests by default:" in report
    staging_block = report.split("Step 2 - stage only reviewed product/docs/tests by default:", 1)[1].split(
        "Sample reports are evidence-only by default:", 1
    )[0]
    assert "git add -- src/dashboard.py" in staging_block
    assert "outputs/stock_reports/apld.md" not in staging_block
    assert "outputs/stock_reports/new_name.md" not in staging_block
    sample_block = report.split("Sample reports are evidence-only by default:", 1)[1].split(
        "Step 3 - inspect staged package:", 1
    )[0]
    assert "outputs/stock_reports/apld.md" in sample_block
    assert "outputs/stock_reports/new_name.md" in sample_block


def test_public_release_handoff_defaults_branch_status_when_not_checked():
    module = load_diff_hygiene_module()

    report = module.build_public_release_handoff_report([])

    assert "Branch status: not checked" in report
    assert "Package status: clean; ready for the next reviewed work slice" in report
    assert "Generated churn to leave unstaged by default:" in report


def test_public_release_handoff_marks_generated_only_tree_as_local_churn():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "data/prices.csv"),
        module.StatusEntry("??", "data/reports/ticker_readiness_report.previous.csv"),
    ]

    report = module.build_public_release_handoff_report(entries)

    assert "Product/code/docs/test candidates: 0 (0 changed, 0 new)" in report
    assert "Generated CSV/JSON churn excluded by default: 2 (1 changed, 1 new)" in report
    assert "Package status: generated churn only; keep it local unless intentionally reviewed as evidence" in report
    assert "Step 4 - skip commit when no reviewed files are staged:" in report
    assert "# no commit; generated churn remains local" in report
    assert 'git commit -m "Improve pilot handoff and workflow continuity"' not in report


def test_public_release_package_marks_generated_only_tree_as_local_churn():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "data/prices.csv"),
        module.StatusEntry("??", "data/reports/ticker_readiness_report.previous.csv"),
    ]

    report = module.build_public_release_package_report(entries)

    assert "Share-now answer:" in report
    assert "Share as controlled portfolio/demo evidence after public-check passes and generated churn stays excluded." in report
    assert "Generated churn can stay local; do not create a release commit just for it." in report
    assert "Product/code/docs/test candidates: 0 (0 changed, 0 new)" in report
    assert "Generated CSV/JSON churn excluded by default: 2 (1 changed, 1 new)" in report
    assert "Package status: generated churn only; keep it local unless intentionally reviewed as evidence" in report
    assert "Release verdict:" in report
    assert "No reviewed product package to stage; keep generated churn local unless intentionally selected as evidence." in report
    assert "No reviewed product package to commit; generated churn remains local." in report
    assert 'git commit -m "Improve pilot handoff and workflow continuity"' not in report
    assert "git add --pathspec-from-file=outputs/staging/product_files.txt" not in report
    assert "Not ready to stage automatically" not in report


def test_staged_hygiene_check_passes_clean_product_and_sample_report_stage():
    module = load_diff_hygiene_module()
    entries = [
        module.StatusEntry("M", "config.yaml"),
        module.StatusEntry("M", "src/dashboard.py"),
        module.StatusEntry("A", "docs/METHODOLOGY.md"),
        module.StatusEntry("D", "stock_analysis/pipeline.py"),
        module.StatusEntry("M", "outputs/stock_reports/nvda.md"),
        module.StatusEntry("A", "data/reviewed_research_events.csv"),
        module.StatusEntry("A", "data/research_thesis_journal.csv"),
    ]

    report = module.build_staged_check_report(entries)

    assert module.staged_hygiene_has_blockers(entries) is False
    assert "Staged Hygiene Check" in report
    assert "Staged product/code/docs/test files: 6 (3 changed, 3 new)" in report
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


def test_staged_hygiene_accepts_proof_backed_peer_data(monkeypatch):
    module = load_diff_hygiene_module()
    staged_lines = {
        "data/peers.csv": [
            "SNDK,MU,Memory and storage semiconductors,Information Technology,Memory chips and storage,https://example.com/source,2026-06-24",
            "SNDK,WDC,Memory and storage hardware,Information Technology,Data storage and flash memory,https://example.com/source,2026-06-24",
        ],
        "data/reviewed_batch_proofs.csv": [
            "RB-1,2026-07-01,Codex source review,peers,reviewed scope,SNDK,validate,valid,preview,apply,pre,post,Peer Mapping Proof ready 27->28,SNDK,data/imports/peers.csv; data/peers.csv,human_reviewed_supported,source reviewed",
        ],
    }
    monkeypatch.setattr(
        module,
        "load_staged_added_lines",
        lambda _root, path: staged_lines.get(path, []),
    )
    entries = [
        module.StatusEntry("M", "data/peers.csv"),
        module.StatusEntry("M", "data/reviewed_batch_proofs.csv"),
    ]

    report = module.build_staged_check_report(entries, Path("."))

    assert module.staged_hygiene_has_blockers_for_repo(entries, Path(".")) is False
    assert "Staged hygiene check passed." in report
    assert "Reviewed canonical data accepted by proof ledger:" in report
    assert "data/peers.csv" in report


def test_staged_hygiene_blocks_peer_data_without_supported_proof(monkeypatch):
    module = load_diff_hygiene_module()
    staged_lines = {
        "data/peers.csv": [
            "SNDK,MU,Memory and storage semiconductors,Information Technology,Memory chips and storage,https://example.com/source,2026-06-24",
        ],
        "data/reviewed_batch_proofs.csv": [
            "RB-1,2026-07-01,Codex source review,peers,reviewed scope,SNDK,validate,valid,preview,not applied,pre,post,none,SNDK,data/imports/peers.csv; data/peers.csv,still_blocked,source not sufficient",
        ],
    }
    monkeypatch.setattr(
        module,
        "load_staged_added_lines",
        lambda _root, path: staged_lines.get(path, []),
    )
    entries = [
        module.StatusEntry("M", "data/peers.csv"),
        module.StatusEntry("M", "data/reviewed_batch_proofs.csv"),
    ]

    report = module.build_staged_check_report(entries, Path("."))

    assert module.staged_hygiene_has_blockers_for_repo(entries, Path(".")) is True
    assert "Staged hygiene check failed." in report
    assert "Generated CSV/JSON churn currently staged:" in report
    assert "data/peers.csv" in report


def test_staged_hygiene_accepts_proof_backed_universe_metadata(monkeypatch):
    module = load_diff_hygiene_module()
    staged_lines = {
        "data/universe.csv": [
            "ARM,,,,,Arm Holdings plc,smh,SMH weight: 1.15%,,SMH,,False,2026-07-05,False,False,False,True,False,False",
            "STM,,,,,STMicroelectronics N.V.,smh,SMH weight: 1.28%,,SMH,,False,2026-07-05,False,False,False,True,False,False",
            "TSM,,,,,Taiwan Semiconductor Manufacturing Company Limited,smh,SMH weight: 9.40%,,SMH,,False,2026-07-05,False,False,False,True,False,False",
        ],
        "data/reviewed_batch_proofs.csv": [
            "RB-1,2026-07-05,Codex source review,universe_metadata,reviewed universe metadata slice,\"ARM,STM,TSM\",validate,valid,preview,apply,pre,post,Universe metadata rows applied,\"ARM,STM,TSM\",data/imports/universe.csv; data/universe.csv,human_reviewed_supported,source reviewed",
        ],
    }
    monkeypatch.setattr(
        module,
        "load_staged_added_lines",
        lambda _root, path: staged_lines.get(path, []),
    )
    entries = [
        module.StatusEntry("M", "data/universe.csv"),
        module.StatusEntry("M", "data/reviewed_batch_proofs.csv"),
    ]

    report = module.build_staged_check_report(entries, Path("."))

    assert module.staged_hygiene_has_blockers_for_repo(entries, Path(".")) is False
    assert "Staged hygiene check passed." in report
    assert "Reviewed canonical data accepted by proof ledger:" in report
    assert "data/universe.csv" in report
