from pathlib import Path


def test_makefile_contains_convenience_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for target in (
        "help",
        "status",
        "status-check",
        "test",
        "pipeline",
        "stock-report",
        "local-tickers",
        "monthly",
        "track-record",
        "validate-data",
        "data-sources-check",
        "data-sources",
        "research-health-check",
        "research-health",
        "action-queue-check",
        "action-queue",
        "project-status",
        "verify",
        "validate-all",
        "daily",
        "dashboard",
        "dashboard-smoke",
        "sec-stage",
        "sec-validate",
        "sec-preview",
        "sec-apply",
        "import-staging",
        "universe-preview",
        "universe-apply",
        "coverage",
        "data-wizard",
        "unlock-ladder",
        "unlock-summary",
        "command-bundles",
        "command-bundle-details",
        "command-bundle-runbook",
        "bundle-prices",
        "bundle-fundamentals",
        "bundle-peers",
        "bundle-prices-broader",
        "bundle-fundamentals-broader",
        "bundle-peers-broader",
        "detail-prices",
        "detail-fundamentals",
        "detail-peers",
        "detail-prices-broader",
        "detail-fundamentals-broader",
        "detail-peers-broader",
        "runbook-prices",
        "runbook-fundamentals",
        "runbook-peers",
        "runbook-prices-broader",
        "runbook-fundamentals-broader",
        "runbook-peers-broader",
        "focus-price",
        "focus-fundamentals",
        "focus-peers",
        "onboarding",
        "templates",
        "price-status",
        "price-worklist",
        "fundamentals-peer-worklist",
        "optional-context-worklist",
        "sec-stage-queue",
        "peer-mapping-queue",
        "price-validate",
        "price-preview",
        "price-apply",
        "price-refresh",
        "price-refresh-loop",
        "price-normalize",
    ):
        assert f"{target}:" in makefile


def test_makefile_help_documents_key_workflows():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for phrase in (
        "Stock Research Command Center convenience commands",
        "make status [TOP_N=5]",
        "make status-check [TICKERS=NVDA,MSFT] [TOP_N=5]",
        "make verify",
        "make validate-all",
        "make daily",
        "make dashboard-smoke",
        "make data-sources-check [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make data-sources",
        "make research-health-check [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make project-status",
        "make action-queue-check [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make stock-report TICKER=NVDA [OUTPUT=outputs/nvda_stock_report.json] [MD_OUTPUT=outputs/stock_reports/nvda.md]",
        "make local-tickers",
        "make coverage [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make data-wizard [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make unlock-ladder [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make unlock-summary [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundles [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundle-details [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundle-runbook [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-prices [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-peers [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-prices [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-peers [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-prices [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-peers [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make focus-price TICKER=AMD",
        "make focus-fundamentals TICKER=NVDA",
        "make focus-peers TICKER=NVDA",
        "make price-status [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make price-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make price-refresh [TOP_N=25] [PROVIDER=stooq|yahoo]",
        "make price-refresh TICKERS=NVDA,MSFT [PROVIDER=yahoo]",
        "make price-refresh-loop [BATCHES=5] [TOP_N=100] [PROVIDER=yahoo] [SLEEP_SECONDS=30]",
        "make price-refresh-loop DRY_RUN=1",
        "make fundamentals-peer-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make optional-context-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make sec-stage-queue [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make peer-mapping-queue [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "Most read-only onboarding views also accept TOP_N=10 for a shorter terminal summary",
        "make import-staging",
        "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual",
        "export SEC_USER_AGENT='Name email@example.com'",
        "make sec-stage TICKERS=NVDA,MSFT",
        "make imports-validate && make imports-preview && make imports-apply",
        "make universe-preview",
    ):
        assert phrase in makefile


def test_price_refresh_defaults_to_capped_broad_universe_batch():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "python3 -m src.data_update --universe-file data/universe.csv --missing-only --max-tickers $(or $(TOP_N),25)" in makefile


def test_price_refresh_loop_uses_capped_defaults_and_rebuilds_status():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    script = Path("scripts/price_refresh_loop.sh").read_text(encoding="utf-8")

    assert "price-refresh-loop:" in makefile
    assert "BATCHES=$(or $(BATCHES),5) TOP_N=$(or $(TOP_N),100) PROVIDER=$(or $(PROVIDER),yahoo) SLEEP_SECONDS=$(or $(SLEEP_SECONDS),30) DRY_RUN=$(or $(DRY_RUN),0)" in makefile
    assert 'BATCHES="${BATCHES:-5}"' in script
    assert 'TOP_N="${TOP_N:-100}"' in script
    assert 'PROVIDER="${PROVIDER:-yahoo}"' in script
    assert 'DRY_RUN="${DRY_RUN:-0}"' in script
    assert "Dry run only. No local CSV files were changed." in script
    assert 'make price-refresh TOP_N="$TOP_N" PROVIDER="$PROVIDER"' in script
    assert "make price-coverage TOP_N=25" in script
    assert "make readiness" in script
    assert "make project-status" in script


def test_readme_public_landing_page_is_short_visual_and_command_focused():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) < 180
    assert "![Dashboard preview](docs/assets/dashboard-preview.svg)" in readme
    assert "## Quick Start" in readme
    assert "## What You Can Analyze" in readme
    assert "## Try This Demo Path" in readme
    assert "## Generated Data Hygiene" in readme
    assert "## Analysis Logic Provenance" in readme
    for phrase in (
        "make pipeline",
        "make readiness",
        "make stock-report TICKER=NVDA",
        "make stock-report TICKER=QQQ",
        "make stock-report TICKER=SMH",
        "make stock-report TICKER=APLD",
        "make dashboard",
        "make dashboard-smoke",
        "make status-check TOP_N=5",
        "make research-health-check TOP_N=10",
        "make price-worklist TOP_N=10",
        "make price-refresh-loop DRY_RUN=1",
        "make price-refresh-loop BATCHES=5 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30",
        "make focus-fundamentals TICKER=NVDA",
        "make peer-mapping-queue TOP_N=10",
        "make optional-context-worklist TOP_N=10",
        "not investment advice",
        "Roadmap Snapshot",
        "Review them before committing",
        "not copied stock-picking or recommendation engines",
    ):
        assert phrase in readme


def test_dashboard_advanced_commands_recommend_dry_run_before_refresh():
    dashboard = Path("src/dashboard.py").read_text(encoding="utf-8")
    dry_run_index = dashboard.index("make price-refresh-loop DRY_RUN=1")
    refresh_index = dashboard.index("make price-refresh-loop BATCHES=5 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30")

    assert dry_run_index < refresh_index
    assert "broad refresh churn should be inspected before it is committed or shared publicly" in dashboard
    assert "Generate Local Stock Report" in dashboard
    assert "Use optional online data" in dashboard
    assert "research rows" in dashboard

def test_readme_preserves_research_only_guardrails_and_preview_first_imports():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Research-Only Guardrails" in readme
    assert "not a trading system" in readme
    for phrase in (
        "place orders",
        "connect to brokers",
        "auto-trade",
        "recommend option trades",
        "provide direct buy/sell instructions",
        "fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations",
        "make templates",
        "make imports-validate",
        "make imports-preview",
        "make imports-apply",
    ):
        assert phrase in readme


def test_shell_launchers_anchor_to_repo_root():
    for script_name in ("daily.sh", "dashboard.sh", "validate_all.sh", "smoke_dashboard.sh"):
        script = (Path("scripts") / script_name).read_text(encoding="utf-8")
        assert "set -euo pipefail" in script
        assert "REPO_ROOT" in script
        assert 'cd "${REPO_ROOT}"' in script
        assert 'echo "Repo root: ${REPO_ROOT}"' in script


def test_dashboard_smoke_launcher_checks_streamlit_health_safely():
    script = Path("scripts/smoke_dashboard.sh").read_text(encoding="utf-8")

    assert "_stcore/health" in script
    assert "SERVER_PID" in script
    assert "trap cleanup EXIT" in script


def test_validate_all_reuses_current_verification_targets():
    script = Path("scripts/validate_all.sh").read_text(encoding="utf-8")

    assert "make verify" in script
    assert "make data-sources-check" in script
    assert "make monthly" in script
    assert "make track-record" in script
    assert "make dashboard-smoke" in script
    assert "python3 -m pytest tests -q" not in script
    assert "python3 -m src.data_sources --check" not in script


def test_daily_launcher_reuses_current_make_targets():
    script = Path("scripts/daily.sh").read_text(encoding="utf-8")

    for command in (
        "make price-refresh",
        "make pipeline",
        "make monthly",
        "make track-record",
        "make validate-data",
        "make onboarding",
    ):
        assert command in script

    assert "python3 -m src.data_update --universe-file data/universe.csv" not in script
    assert "python3 -m src.report_generator" not in script


def test_makefile_verify_and_daily_targets_reuse_shared_make_workflows():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "status:\n\tpython3 -m src.project_status --refresh-artifacts --top-n $(or $(TOP_N),5)" in makefile
    assert "status-check:\n\tpython3 -m src.project_status --check --top-n $(or $(TOP_N),5) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "coverage:\n\tpython3 -m src.data_onboarding --coverage $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "data-wizard:\n\tpython3 -m src.data_onboarding --wizard $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "unlock-ladder:\n\tpython3 -m src.data_onboarding --unlock-ladder $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "unlock-summary:\n\tpython3 -m src.data_onboarding --unlock-summary $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "command-bundles:\n\tpython3 -m src.data_onboarding --command-bundles $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "command-bundle-details:\n\tpython3 -m src.data_onboarding --command-bundle-details $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "command-bundle-runbook:\n\tpython3 -m src.data_onboarding --command-bundle-runbook $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "bundle-fundamentals:\n\tpython3 -m src.data_onboarding --command-bundles --lane fundamentals --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "detail-peers:\n\tpython3 -m src.data_onboarding --command-bundle-details --lane peers --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "runbook-prices-broader:\n\tpython3 -m src.data_onboarding --command-bundle-runbook --lane prices --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "price-worklist:\n\tpython3 -m src.data_onboarding --price-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "fundamentals-peer-worklist:\n\tpython3 -m src.data_onboarding --fundamentals-peer-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "optional-context-worklist:\n\tpython3 -m src.data_onboarding --optional-context-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "sec-stage-queue:\n\tpython3 -m src.data_onboarding --sec-stage-queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "peer-mapping-queue:\n\tpython3 -m src.data_onboarding --peer-mapping-queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "price-normalize:\nifndef INPUT\n\t$(error INPUT is required, for example: make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual)\nendif" in makefile
    assert "stock-report:\nifndef TICKER\n\t$(error TICKER is required, for example: make stock-report TICKER=NVDA)\nendif\n\tpython3 -m src.stock_report --ticker $(TICKER) --provider $(if $(PROVIDER),$(PROVIDER),local) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(MD_OUTPUT),--markdown-output $(MD_OUTPUT),)" in makefile
    assert "local-tickers:\n\tpython3 -m src.stock_report --list-local-tickers" in makefile
    assert "import-staging:\n\tpython3 -m src.stock_report --write-import-staging" in makefile
    assert "data-sources-check:\n\tpython3 -m src.data_sources --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "data-sources:\n\tpython3 -m src.data_sources --write-output" in makefile
    assert "research-health-check:\n\tpython3 -m src.research_health --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "action-queue-check:\n\tpython3 -m src.action_queue --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "price-status:\n\tpython3 -m src.data_update --price-status $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "verify:\n\t$(MAKE) test\n\t$(MAKE) pipeline\n\t$(MAKE) validate-data\n\t$(MAKE) onboarding" in makefile
    assert "daily:\n\t$(MAKE) price-refresh\n\t$(MAKE) pipeline\n\t$(MAKE) monthly\n\t$(MAKE) track-record\n\t$(MAKE) validate-data\n\t$(MAKE) onboarding" in makefile
    assert "verify:\n\tpython3 -m pytest tests -q" not in makefile
    assert "daily:\n\tpython3 -m src.data_update --universe-file data/universe.csv" not in makefile
