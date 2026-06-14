import csv
import re
import subprocess
from pathlib import Path


def _makefile_targets() -> set[str]:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z0-9_.-]+):(?:\s|$)", makefile, flags=re.MULTILINE))


def test_tracked_holdings_file_is_sanitized_demo_data():
    holdings_path = Path("data/holdings.csv")
    rows = list(csv.DictReader(holdings_path.read_text(encoding="utf-8").splitlines()))

    assert rows
    for row in rows:
        assert float(row["Shares"]) == 0.0
        assert float(row["CostBasis"]) == 0.0
        assert float(row["PositionPercent"]) == 0.0
        assert "example" in row["OriginalThesis"].lower()


def test_generated_staging_pathspec_files_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "outputs/staging/" in gitignore


def test_streamlit_toolbar_uses_viewer_mode_for_public_dashboard():
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8")

    assert "[client]" in config
    assert 'toolbarMode = "viewer"' in config


def test_dashboard_launchers_force_viewer_mode_for_public_demo():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    launcher = Path("scripts/dashboard.sh").read_text(encoding="utf-8")

    assert "streamlit run src/dashboard.py --client.toolbarMode viewer --server.headless true" in makefile
    assert "--client.toolbarMode viewer" in launcher
    assert "--server.headless true" in launcher


def test_makefile_contains_convenience_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for target in (
        "help",
        "demo",
        "diff-hygiene",
        "trusted-data-pilot-candidates",
        "trusted-data-pilot-packet",
        "reviewed-data-proof",
        "reviewed-data-proof-record",
        "reviewed-batch-proof",
        "reviewed-batch-proof-record",
        "reviewed-batch-compare",
        "reviewed-batch-preflight",
        "lane-outcome-history",
        "price-reviewed-run",
        "public-demo-readiness-pack",
        "readiness-ops-center",
        "coverage-frontier",
        "data-coverage-planner",
        "coverage-expansion-loop",
        "readiness-ops-evidence",
        "reviewed-batch",
        "decision-proof-queue",
        "metric-readiness-board",
        "diff-hygiene-summary",
        "diff-hygiene-files",
        "staged-hygiene-check",
        "public-wording-check",
        "public-check",
        "status",
        "status-check",
        "test",
        "pipeline",
        "stock-report",
        "stock-report-md",
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
        "help-full:",
        "For the full local command catalog, run: make help-full",
        "Stock Research Command Center convenience commands",
        "First-time path:",
        "Print the clean visitor walkthrough",
        "make status-check TOP_N=5",
        "make stock-report-md TICKER=NVDA",
        "make metric-readiness-board TOP_N=10",
        "make dashboard-smoke",
        "make dashboard",
        "make trusted-data-pilot TOP_N=10",
        "Print the company-focused trusted-data pilot path",
        "make trusted-data-pilot-candidates TOP_N=10",
        "Rank current company candidates for the next trusted-data pilot",
        "make trusted-data-pilot-packet TICKER=CRDO",
        "Print one company's read-only evidence packet",
        "make trusted-data-pilot-lane LANE=fundamentals_dcf",
        "Print one lane group's ordered proof steps and evidence summary",
        "make reviewed-data-proof",
        "Print the durable reviewed data proof ledger",
        "make reviewed-batch-proof",
        "Show durable reviewed batch proof ledger",
        "make reviewed-batch-compare",
        "Compare before/after readiness snapshots for proof rows",
        "make reviewed-batch-preflight",
        "Check snapshot/freshness gates before a reviewed batch",
        "make lane-outcome-history",
        "Summarize lane outcomes from the durable proof ledger",
        "make price-reviewed-run",
        "Print the controlled reviewed capped price run workflow",
        "make public-demo-readiness-pack",
        "Print the small shareable public demo proof set",
        "make readiness-ops-center",
        "Print the broad lane-level readiness operations center",
        "make coverage-frontier",
        "Rank batch coverage opportunities by unlock impact",
        "make data-coverage-planner",
        "Print repeatable coverage expansion lanes without changing local data",
        "make coverage-expansion-loop",
        "Print the next reviewed coverage loop from planner to proof",
        "make readiness-ops-evidence",
        "Print the broad lane operations evidence checklist",
        "make reviewed-batch",
        "Preview or write a reviewed batch run packet for a selected lane",
        "make decision-proof-queue",
        "Preview or write the compact decision proof queue from current readiness outputs",
        "make metric-readiness-board [TICKERS=NVDA,META] [TOP_N=10] [BENCHMARKS=SPY,QQQ] [OUTPUT=outputs/metric_readiness_board.csv]",
        "make public-check     Run before sharing the GitHub link",
        "make demo",
        "make trusted-data-pilot [TICKERS=NVDA,AVGO,AMD,MU,CRDO] [TOP_N=10] Print a read-only company-focused trusted-data pilot plan",
        "make trusted-data-pilot-candidates [TICKERS=NVDA,CRDO,META] [TOP_N=10] Rank read-only company candidates for the next trusted-data pilot",
        "make trusted-data-pilot-packet TICKER=CRDO Print one company's read-only before-report/review/validate/rejected-row/rebuild evidence packet",
        "make trusted-data-pilot-lane LANE=fundamentals_dcf [TICKERS=MU,CRDO,HOOD] [TOP_N=10] Print a read-only lane-group runbook and evidence summary",
        "make reviewed-data-proof [LEDGER=data/reviewed_data_proofs.csv] Print the durable reviewed data proof ledger",
        "make lane-outcome-history [LEDGER=data/reviewed_data_proofs.csv] Print lane outcome history from reviewed proof rows",
        "make reviewed-data-proof-record LANE=<lane> PROOF_ID=<id> PROOF_DATE=<yyyy-mm-dd> FINAL_OUTCOME=<supported|still_blocked|skipped|excluded> Record an intentional reviewed proof row",
        "make reviewed-batch-proof [LEDGER=data/reviewed_batch_proofs.csv] Print durable reviewed batch proof rows",
        "make reviewed-batch-proof-record BATCH_ID=<id> LANE=<lane> REVIEW_DATE=<yyyy-mm-dd> FINAL_OUTCOME=<supported|still_blocked|skipped|excluded> Record a reviewed batch outcome",
        "make reviewed-batch-compare [BATCH_ID=<id>] [LANE=prices] [REVIEW_DATE=<yyyy-mm-dd>] Compare prior/current readiness snapshots for proof-ledger fields",
        "make reviewed-batch-preflight [LANE=prices] [TOP_N=100] [MAX_CANDIDATES=3500] Check snapshot, dry-run, compare, proof, and artifact gates",
        "make price-reviewed-run [MAX_CANDIDATES=3500] [TOP_N=100] [PROVIDER=yahoo] Print reviewed capped price-run execution, diff, and rollback plan",
        "make public-demo-readiness-pack Print the small shareable public demo proof set",
        "make readiness-ops-center Print lane-level ready/partial/blocked/excluded operations without refreshing data",
        "make coverage-frontier [TOP_N=10] Rank broad batch opportunities by unlock impact and safe command",
        "make data-coverage-planner [TOP_N=10] Print repeatable coverage expansion lanes with dry-run, proof, stop, and churn gates",
        "make coverage-expansion-loop [LANE=auto] [TOP_N=10] Print one copy-only planner -> preflight -> packet -> proof loop",
        "make readiness-ops-evidence [TOP_N=10] Print proof, churn, locked-lane, and exclusion evidence for readiness operations",
        "make reviewed-batch [DRY_RUN=1] [LANE=prices|fundamentals|share_count|peers|metrics|optional_context] [TOP_N=10] [TICKERS=NVDA,MSFT] Preview or write outputs/reviewed_batch_packet.md and .csv",
        "make decision-proof-queue [DRY_RUN=1] [TOP_N=12] [OUTPUT=outputs/decision_proof_queue.csv] [MD_OUTPUT=outputs/decision_proof_queue.md] Preview or write a copy-only proof queue from current decision/readiness outputs",
        "make diff-hygiene",
        "Print a read-only staging guide that separates product files from local data changes",
        "make diff-hygiene-summary",
        "Print a short read-only staging summary for public checks",
        "make diff-hygiene-files",
        "Write local pathspec files under outputs/staging for safer reviewed staging",
        "make staged-hygiene-check",
        "Fail if staged files include unreviewed local data/report changes",
        "make public-wording-check",
        "Scan public docs, dashboard copy, and sample reports for unsupported advice/execution wording",
        "make public-check",
        "Run share-safe checks before posting the repo link; does not refresh broad local data",
        "Run these from the repository root so make can find the project targets.",
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
        "make stock-report-md TICKER=NVDA [MD_OUTPUT=outputs/stock_reports/nvda.md]",
        "make stock-report TICKER=NVDA [OUTPUT=outputs/nvda_stock_report.json] [MD_OUTPUT=outputs/stock_reports/nvda.md]",
        "Generate a readable Markdown report for demos and review",
        "Generate the report plus optional report data for inspection",
        "make local-tickers",
        "make coverage [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make data-wizard [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make unlock-ladder [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make unlock-summary [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundles [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundle-details [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundle-runbook [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "Show ordered steps for the current guided data batches",
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
        "Show step-by-step price checks for the broader queue",
        "Show one ticker's peer detail and next local checks",
        "make price-status [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make price-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make price-refresh [TOP_N=25] [PROVIDER=stooq|yahoo]",
        "make price-refresh TICKERS=NVDA,MSFT [PROVIDER=yahoo]",
        "make price-refresh-loop [MAX_CANDIDATES=3500] [TOP_N=100] [PROVIDER=yahoo] [SLEEP_SECONDS=30]",
        "make price-refresh-loop DRY_RUN=1",
        "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100",
        "avoids repeating 25-ticker refreshes manually",
        "make fundamentals-peer-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make optional-context-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make sec-stage-queue [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make peer-mapping-queue [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "Most read-only onboarding views also accept TOP_N=10 for a shorter local summary",
        "make import-staging",
        "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual",
        "export SEC_USER_AGENT='Name email@example.com'",
        "make sec-stage TICKERS=NVDA,MSFT",
        "make imports-validate && make imports-preview && make imports-apply",
        "make universe-preview",
        "Preview-first fundamentals and universe imports",
    ):
        assert phrase in makefile

    for old_phrase in (
        "Generate one local stock report JSON plus a readable Markdown report",
        "Generate one local structured stock report plus a readable Markdown report",
        "Generate the report plus optional structured data for inspection",
        "Generate a readable Markdown report without printing the structured report data",
        "structured report data",
        "full JSON payload",
        "shorter terminal summary",
        "Fundamentals and universe import drafts:",
        "top bundle/runbook shortcut",
        "printed focus/runbook path",
        "Show only the price bundle runbook",
        "Show only the peer-mapping bundle",
        "Show one ticker's price detail row and runbook",
        "generated data churn",
    ):
        assert old_phrase not in makefile

    assert makefile.index("make stock-report-md TICKER=NVDA") < makefile.index("make stock-report TICKER=NVDA")
    assert makefile.index("First-time path:") < makefile.index("Core:")
    assert makefile.index("make price-refresh-loop DRY_RUN=1 Preview") < makefile.index(
        "make price-refresh [TOP_N=25]"
    )
    assert makefile.index("make price-refresh-loop [MAX_CANDIDATES=3500]") < makefile.index(
        "make price-refresh TICKERS=NVDA,MSFT"
    )


def test_make_help_output_stays_visitor_friendly():
    result = subprocess.run(["make", "help"], check=True, capture_output=True, text=True)
    output = result.stdout

    assert "Stock Research Command Center" in output
    assert "Start here:" in output
    assert "make demo" in output
    assert "make stock-report-md TICKER=NVDA" in output
    assert "make trusted-data-pilot-candidates TOP_N=10" in output
    assert "For the full local command catalog, run: make help-full" in output
    assert "Data onboarding:" not in output
    assert "Preview-first fundamentals and universe imports:" not in output
    assert len(output.splitlines()) <= 25


def test_metric_readiness_board_make_target_preserves_comma_default():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "DEFAULT_METRIC_BENCHMARKS := SPY,QQQ" in makefile
    assert '--benchmarks "$(if $(BENCHMARKS),$(BENCHMARKS),$(DEFAULT_METRIC_BENCHMARKS))"' in makefile
    assert "--output \"$(OUTPUT)\"" in makefile


def test_price_refresh_defaults_to_capped_broad_universe_batch():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "python3 -m src.data_update --universe-file data/universe.csv --missing-only --max-tickers $(or $(TOP_N),25)" in makefile


def test_price_refresh_loop_uses_capped_defaults_and_rebuilds_status():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    script = Path("scripts/price_refresh_loop.sh").read_text(encoding="utf-8")

    assert "price-refresh-loop:" in makefile
    assert 'MAX_CANDIDATES="$(MAX_CANDIDATES)" BATCHES=$(or $(BATCHES),5) TOP_N=$(or $(TOP_N),100) PROVIDER=$(or $(PROVIDER),yahoo) SLEEP_SECONDS=$(or $(SLEEP_SECONDS),30) DRY_RUN=$(or $(DRY_RUN),0)' in makefile
    assert 'BATCHES="${BATCHES:-5}"' in script
    assert 'TOP_N="${TOP_N:-100}"' in script
    assert 'PROVIDER="${PROVIDER:-yahoo}"' in script
    assert 'DRY_RUN="${DRY_RUN:-0}"' in script
    assert 'MAX_CANDIDATES="${MAX_CANDIDATES:-}"' in script
    assert "MAX_CANDIDATES must be a positive integer when provided. Example: make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo" in script
    assert "BATCHES must be a positive integer. For broad coverage, prefer DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 so the loop calculates batches for you." in script
    assert "TOP_N must be a positive integer. Use TOP_N=100 for a capped broad dry run before changing local CSV files." in script
    assert 'BATCHES=$(((MAX_CANDIDATES + TOP_N - 1) / TOP_N))' in script
    assert "TOTAL_CANDIDATES=$((BATCHES * TOP_N))" in script
    assert "MANUAL_25_BATCHES=$(((TOTAL_CANDIDATES + 24) / 25))" in script
    assert "Coverage target: $TARGET_NOTE. The final batch may have unused capacity if fewer missing tickers remain." in script
    assert "Provider boundary: this can add research-grade price rows only; it does not create fundamentals, peers, earnings, estimates, DCF inputs, or conclusions." in script
    assert "Use this loop for broad coverage work instead of repeating 25-ticker refreshes manually." in script
    assert "Manual equivalent avoided: about $MANUAL_25_BATCHES separate 25-ticker refresh command(s)." in script
    assert "Estimated wait between batches: about $WAIT_SECONDS second(s), plus provider response time." in script
    assert "Resume behavior: each batch uses the missing-price worklist" in script
    assert "Before a real run, copy make readiness-snapshot" in script
    assert "What changes on a real run: local price CSVs and generated readiness/report outputs may update." in script
    assert "What stays manual: staging, validation, commit selection, and any generated CSV review remain under your control." in script
    assert "Plain planning knob: set MAX_CANDIDATES=3500" in script
    assert "Use MAX_CANDIDATES first when you know the approximate missing-price count; use BATCHES only as an advanced override." in script
    assert "for a 3000+ ticker universe, set MAX_CANDIDATES and dry-run again" in script
    assert "do not babysit hundreds of tiny commands" in script
    assert "Review summary: one dry run gives a copyable capped plan; one reviewed loop command replaces many manual refresh commands." in script
    assert "Review summary: MAX_CANDIDATES is the approximate missing-price target; TOP_N is the per-batch safety cap." in script
    assert "Dry run only. No local CSV files were changed." in script
    assert "Requested target: up to $REQUESTED_TARGET missing-price candidate(s)." in script
    assert "Rounded batch capacity: up to $TOTAL_CANDIDATES ticker slot(s) across $BATCHES capped batch(es)." in script
    assert "Unused capacity is expected when the last batch has fewer missing tickers than TOP_N." in script
    assert "Manual 25-ticker commands avoided: about $MANUAL_25_BATCHES." in script
    assert "If interrupted or provider-limited, rerun the dry run" in script
    assert "No provider call, import, validation apply, or external account action runs during this dry run." in script
    assert "Planned loop command: make price-refresh-loop MAX_CANDIDATES=$MAX_CANDIDATES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "Planned loop command: make price-refresh-loop BATCHES=$BATCHES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "Each capped batch would run: make price-refresh TOP_N=$TOP_N PROVIDER=$PROVIDER" in script
    assert "Snapshot command before a real run: make readiness-snapshot" in script
    assert "Hygiene command after a real run: make diff-hygiene" in script
    assert "Recommended next sequence:" in script
    assert "1. make readiness-snapshot" in script
    assert "2. make price-refresh-loop MAX_CANDIDATES=$MAX_CANDIDATES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "2. make price-refresh-loop BATCHES=$BATCHES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "3. make diff-hygiene" in script
    assert "4. make stock-report-md TICKER=NVDA or reopen the dashboard to review the local result" in script
    assert "If you want broader coverage, set MAX_CANDIDATES first while keeping TOP_N capped, then dry-run again." in script
    assert "Example broad dry run: make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=$PROVIDER" in script
    assert "Advanced alternative: make price-refresh-loop DRY_RUN=1 BATCHES=30 TOP_N=100 PROVIDER=$PROVIDER" in script
    assert "copy the one planned loop command instead of running many 25-ticker commands by hand" in script
    assert "Dry-run result: no data changed; review the planned command, then run exactly one capped loop when ready." in script
    assert "Recalculate anytime: rerun DRY_RUN=1 after interruptions, provider limits, or local CSV changes." in script
    assert "Safe fallback: use make runbook-prices-broader or make focus-price TICKER=... to switch to the local import file workflow." in script
    assert "Manual CSV path: normalize downloaded OHLCV rows with make price-normalize" in script
    assert "Resume note: after fixing the source issue, rerun make price-refresh-loop DRY_RUN=1" in script
    assert 'make price-refresh TOP_N="$TOP_N" PROVIDER="$PROVIDER"' in script
    assert "Price refresh batch $i failed." in script
    assert "This replaces repeating 25-ticker refreshes manually" in script
    assert "make price-coverage TOP_N=25" in script
    assert "make readiness" in script
    assert "make project-status" in script
    assert "run make diff-hygiene before staging" in script


def test_price_refresh_loop_dry_run_calculates_broad_universe_plan_without_writes():
    result = subprocess.run(
        ["sh", "scripts/price_refresh_loop.sh"],
        check=True,
        capture_output=True,
        text=True,
        env={
            "BATCHES": "5",
            "TOP_N": "100",
            "PROVIDER": "yahoo",
            "SLEEP_SECONDS": "30",
            "DRY_RUN": "1",
            "MAX_CANDIDATES": "3538",
        },
    )
    output = result.stdout.lower()

    assert "dry run only. no local csv files were changed." in output
    assert "requested coverage target: up to 3538 missing-price candidates; calculated 36 capped batch(es)." in output
    assert "requested target: up to 3538 missing-price candidate(s)." in output
    assert "rounded batch capacity: up to 3600 ticker slot(s) across 36 capped batch(es)." in output
    assert "unused capacity is expected when the last batch has fewer missing tickers than top_n." in output
    assert "manual 25-ticker commands avoided: about 144." in output
    assert "review summary: one dry run gives a copyable capped plan; one reviewed loop command replaces many manual refresh commands." in output
    assert "review summary: max_candidates is the approximate missing-price target; top_n is the per-batch safety cap." in output
    assert "no provider call, import, validation apply, or external account action runs during this dry run." in output
    assert "provider boundary: this can add research-grade price rows only; it does not create fundamentals, peers, earnings, estimates, dcf inputs, or conclusions." in output
    assert "planned loop command: make price-refresh-loop max_candidates=3538 top_n=100 provider=yahoo sleep_seconds=30" in output
    assert "copy the one planned loop command instead of running many 25-ticker commands by hand" in output
    assert "dry-run result: no data changed; review the planned command, then run exactly one capped loop when ready." in output
    assert "recalculate anytime: rerun dry_run=1 after interruptions, provider limits, or local csv changes." in output
    assert "does not connect to brokers, place orders, or make recommendations" in output
    assert "buy" not in output
    assert "sell" not in output


def test_readme_public_landing_page_is_short_visual_and_command_focused():
    readme = Path("README.md").read_text(encoding="utf-8")
    preview = Path("docs/assets/dashboard-preview.svg").read_text(encoding="utf-8")
    public_demo = Path("docs/PUBLIC_DEMO_WALKTHROUGH.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) < 180
    assert "![Dashboard preview](docs/assets/public-demo-home-real.jpg)" in readme
    assert "docs/assets/operator-data-health-metrics-real.jpg" in readme
    for preview_phrase in (
        "plain-language stock analysis modes",
        "At A Glance single-stock status",
        "Evaluation Snapshot",
        "Best Review Path",
        "At A Glance + Proof Checklist before tables",
        "Inspect proof: readiness snapshots and proof ledger",
        "Mode + decision",
        "DCF + peers",
        "What not to infer",
        "Next local step",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review",
        "Monitor-only context",
        "Data needed before analysis",
        "Data-confidence cue",
        "Public Demo",
        "MU peer-input and CRDO fundamentals-gated proof paths",
        "Pilot outcomes: Supported, Still blocked, or Skip after proof",
        "QQQ excluded",
        "project DCF method notes",
        "DCF path: cash flows, terminal value, cash/debt, fair value/share",
        "copy-only proof commands",
    ):
        assert preview_phrase in preview
    for stale_preview_phrase in ("Analysis modes before tables", "Standalone DCF</text>", "Price/setup only", "Monitor-only</text>", "Explore ready names: Home filters and sample reports"):
        assert stale_preview_phrase not in preview
    assert "## Quick Start" in readme
    assert "flowchart LR" in readme
    assert 'Home["Home: ready vs blocked"] --> Report["Single-stock report"]' in readme
    assert 'Report --> Health["Data Health: missing input"]' in readme
    assert 'Health --> Pilot["Trusted-data pilot"]' in readme
    assert "Run these from the repository root so `make` can find the project targets. This first path is visitor-safe" in readme
    assert "it does not rebuild broad generated outputs before you have seen the product" in readme
    assert "When you want to rebuild local outputs after changing data, use the deeper [Local Workflow Guide](docs/OPERATOR_GUIDE.md) for rebuild, import, refresh, and proof steps." in readme
    assert "## What You Can Analyze" in readme
    assert "## How Analysis Works" in readme
    assert "Read the counts in three layers:" in readme
    assert "| Master universe | The broad ticker list the project can track. | Good for coverage planning, not proof that every analysis is ready. |" in readme
    assert "| Active universe | The focused research list for demo and portfolio-style review. | Best place to inspect product flow and next trusted-data steps. |" in readme
    assert "| Analysis-ready subset | Tickers whose required local inputs passed readiness for a feature. | Use this layer for DCF, peer context, or candidate review; blocked rows stay visibly locked. |" in readme
    assert "## What Works Today" in readme
    assert "## Try This Demo Path" in readme
    assert "Optional extra report states:" in readme
    assert "| Review one stock | You want a ticker-level research note with ready, blocked, excluded, and data-confidence states. | `Single-Stock Report` |" in readme
    assert "| Inspect proof | You want to see the latest readiness snapshot, reviewed batch packet, proof ledger, and still-blocked fields. | `Data Health` |" in readme
    assert "`Home`, then focused review pages" not in readme
    assert "The shortest public walkthrough is: Home -> NVDA proof report -> META blocked example -> QQQ excluded example -> MU peer-limited example -> CRDO fundamentals-gated example -> trusted-data pilot." in readme
    assert "[Public Demo Walkthrough](docs/PUBLIC_DEMO_WALKTHROUGH.md)" in readme
    assert "validate/apply step, rejected-row report, and rebuild-proof packet" not in readme
    assert "make trusted-data-pilot-candidates TOP_N=10" in public_demo
    assert "make trusted-data-pilot-packet TICKER=MU" in public_demo
    assert "make trusted-data-pilot-packet TICKER=CRDO" in public_demo
    assert "Local file presence, row counts, staged files, and rejected-row reports are inspection cues, not proof" in public_demo
    assert "mapped-peer valuation inputs" in public_demo
    assert "Missing data is not a product failure here" in public_demo
    assert "snapshot the baseline, review source proof, validate/preview and check rejected rows, rebuild readiness and the stock report, then compare the after report" not in readme
    assert "snapshot the baseline, review source proof, validate/preview and check rejected rows, rebuild readiness and the stock report, then compare the after report" in public_demo
    assert "Read the outcome in three states: `Supported` means rebuilt readiness and the regenerated report show the lane is ready" not in readme
    assert "Read the outcome in three states: `Supported` means rebuilt readiness and the regenerated report show the lane is ready" in public_demo
    assert "`Still blocked` means validation failed, rejected rows appeared, or the report stayed locked" not in readme
    assert "`Still blocked` means validation failed, rejected rows appeared, or the report stayed locked" in public_demo
    assert "`Skip` means source proof is unavailable, so no placeholder rows are applied" not in readme
    assert "`Skip` means source proof is unavailable, so no placeholder rows are applied" in public_demo
    assert readme.index("make stock-report-md TICKER=NVDA # company report with DCF assumptions") < readme.index("make stock-report-md TICKER=META # price/setup report with valuation still gated")
    assert readme.index("make stock-report-md TICKER=META # price/setup report with valuation still gated") < readme.index("make stock-report-md TICKER=QQQ  # ETF/index report with DCF excluded")
    assert readme.index("make trusted-data-pilot-candidates TOP_N=10 # read-only coverage candidate list") < readme.index("Optional extra report states:")
    demo_path = readme.split("## Try This Demo Path", 1)[1].split("Optional extra report states:", 1)[0]
    assert demo_path.index("make trusted-data-pilot-candidates TOP_N=10 # read-only coverage candidate list") < demo_path.index("make trusted-data-pilot-packet TICKER=MU")
    assert demo_path.index("make trusted-data-pilot-packet TICKER=MU") < demo_path.index("make trusted-data-pilot-packet TICKER=CRDO")
    assert "## Local Data Hygiene" in readme
    assert "## License" in readme
    assert "## Analysis Methodology" in readme
    assert "docs/METHODOLOGY.md" in readme
    assert "docs/analysis_capability_audit.md" in readme
    assert "[Local Workflow Guide](docs/OPERATOR_GUIDE.md)" in readme
    assert "[Data Strategy](docs/DATA_STRATEGY.md)" in readme
    assert "pip install -e '.[dev]'" in readme
    assert "pip install -e .[dev]" not in readme
    for phrase in (
        "make demo",
        "make trusted-data-pilot TOP_N=10",
        "make trusted-data-pilot-packet TICKER=MU",
        "make trusted-data-pilot-packet TICKER=CRDO",
        "make public-check",
        "make stock-report-md TICKER=NVDA",
        "make stock-report-md TICKER=A",
        "make stock-report-md TICKER=META",
        "make stock-report-md TICKER=QQQ",
        "make stock-report-md TICKER=SMH",
        "make stock-report-md TICKER=APLD",
        "price/setup report with fundamentals still locked",
        "make stock-report TICKER=NVDA",
        "make dashboard",
        "make status-check TOP_N=5",
        "not investment advice",
        "review states",
        "Example map",
        "Operating-company DCF is excluded, not failed",
        "Price/setup review with valuation still locked",
        "next trusted fundamentals proof step",
        "ranked pilot packet first when a peer-input lane leads",
        "guessed peers or file row counts do not become valuation",
        "The pilot candidate command may rank a peer-input example such as `MU` first and also name a fundamentals/DCF example such as `CRDO`",
        "both remain read-only proof packets until source review and rebuilt readiness prove a lane changed",
        "At A Glance status, a plain-English Reader Guide, an Evaluation Snapshot, a Proof Checklist, Best Review Path, data-confidence cues, source readiness notes, and copyable local proof commands",
        "At A Glance status, a Reader Guide, an Evaluation Snapshot, a Proof Checklist, Best Review Path, data-confidence cues, methodology, risks, blockers, copyable local proof commands",
        "The report is not a black box",
        "project rules decide what can be analyzed",
        "Readiness gate: checks prices, fundamentals, DCF fields, peers, earnings, and estimates before deeper analysis appears",
        "Supported analysis: price-ready rows can support setup/risk context",
        "DCF-ready rows can support assumptions and sensitivity",
        "peer-ready rows can support source-backed relative context",
        "Locked or excluded boundaries: missing fundamentals, peer inputs, earnings, or estimates stay locked",
        "company valuation is excluded for ETF/index/fund monitor rows, not failed",
        "Report explanation: single-stock reports show what came from source rows",
        "what the product calculated",
        "what stayed withheld",
        "next local proof step",
        "Markdown reports start with a visitor scan cue, then `At A Glance`, a `Reader Guide`, an `Evaluation Snapshot`, a `Proof Checklist`, and `Best Review Path`",
        "what evidence proves the current mode",
        "what valuation is supported or blocked",
        "what to read first",
        "Copyable Proof Commands",
        "readiness-state output, not an action list",
        "Roadmap Snapshot",
        "Review them before committing",
        "Before sharing or committing, run `make public-check`, then `make diff-hygiene`",
        "For a large dirty tree, run `make diff-hygiene-files`",
        "make staged-hygiene-check",
        "outputs/staging/",
        "internal development notes, and stale repo links",
        "safe staging suggestion for product files and reviewed Markdown reports",
        "large generated CSV/JSON changes",
        "Reuse terms are not specified yet",
        "reuse rights are not granted until a license is added",
        "[License Decision Guide](docs/LICENSE_DECISION_GUIDE.md)",
        "where the method lives",
        "analysis rules, valuation gates, decision buckets",
        "Strongest today",
        "Main modes",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review only",
        "Monitor-only context",
        "Data needed before analysis",
        "Company DCF assumptions and source-backed peer context",
        "Standalone DCF review where peer-relative valuation is still locked",
        "Price/setup review where valuation remains gated",
        "[NVDA](outputs/stock_reports/nvda.md)",
        "[A](outputs/stock_reports/a.md)",
        "[META](outputs/stock_reports/meta.md)",
        "[QQQ](outputs/stock_reports/qqq.md)",
        "[SMH](outputs/stock_reports/smh.md)",
        "[APLD](outputs/stock_reports/apld.md)",
        "Useful with limits",
        "Intentionally locked",
        "Not built to be",
        "Visitor status: the product workflow, dashboard, single-stock reports, readiness gates, demo path, and public checks are working",
        "remain visibly blocked by missing trusted data until trusted rows exist",
        "source-proof work rather than broken analysis",
        "`undervalued_candidates.csv` is a legacy filename for valuation-readiness and re-rating context",
        "not automatic undervalued calls",
    ):
        assert phrase in readme
    quick_start = readme.split("## Quick Start", 1)[1].split("## Try This Demo Path", 1)[0]
    assert "make pipeline" not in quick_start
    assert "make readiness" not in quick_start
    assert quick_start.index("make demo") < quick_start.index("make status-check TOP_N=5")
    assert quick_start.index("make status-check TOP_N=5") < quick_start.index("make stock-report-md TICKER=NVDA")
    assert quick_start.index("make stock-report-md TICKER=NVDA") < quick_start.index("make dashboard")
    operator_guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    for phrase in (
        "make price-worklist TOP_N=10",
        "make price-refresh-loop DRY_RUN=1",
        "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo",
        "make readiness-snapshot",
        "make diff-hygiene",
        "make focus-fundamentals TICKER=NVDA",
        "make peer-mapping-queue TOP_N=10",
        "make optional-context-worklist TOP_N=10",
        "make templates",
        "make imports-validate",
        "make imports-preview",
        "make imports-apply",
        "Large refreshed CSVs are local working data",
        "Provider boundary: price refreshes can improve research-grade local price rows",
        "they do not create fundamentals, source-backed peers, earnings, analyst estimates, DCF inputs, or research conclusions",
    ):
        assert phrase in operator_guide
    for visitor_clutter in (
        "http://localhost:8501/?page=single-stock-report",
        "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30",
        "Targeted missing-data examples",
        "Preview-first import flow",
    ):
        assert visitor_clutter not in readme
    for old_phrase in (
        "operator console",
        "deeper local runbook",
        "refreshed generated CSV churn",
        "generated data churn",
        "generated CSV/JSON churn",
        "broad refresh churn",
        "generated report CSVs",
        "operator workflow",
        "source/freshness auditability",
    ):
        assert old_phrase not in readme


def test_public_markdown_links_resolve_to_tracked_local_files():
    public_docs = [
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("PRODUCT_SPEC.md"),
        Path("READINESS_MODEL.md"),
        Path("DECISION_OUTPUT_MODEL.md"),
        *Path("docs").glob("*.md"),
        *Path("outputs/stock_reports").glob("*.md"),
    ]
    missing: list[tuple[str, str]] = []

    for path in public_docs:
        text = path.read_text(encoding="utf-8")
        image_targets = [match.group(1) for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text)]
        link_targets = [match.group(1) for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text)]
        for target in image_targets + link_targets:
            local_target = target.split("#", 1)[0].strip()
            if (
                not local_target
                or re.match(r"^[a-z][a-z0-9+.-]*:", local_target)
                or local_target.startswith("/")
            ):
                continue
            resolved = (path.parent / local_target).resolve()
            if not resolved.exists():
                missing.append((str(path), target))

    assert missing == []


def test_public_docs_only_reference_existing_make_targets():
    targets = _makefile_targets()
    docs = [Path("README.md"), Path("ROADMAP.md"), Path("PRODUCT_SPEC.md"), *Path("docs").glob("*.md")]
    missing: list[tuple[str, str]] = []

    for path in docs:
        text = path.read_text(encoding="utf-8")
        command_surfaces = re.findall(r"`([^`]*\bmake\s+[^`]*)`", text)
        command_surfaces.extend(match.group(1) for match in re.finditer(r"```(?:bash|text)?\n(.*?)```", text, flags=re.DOTALL))
        for surface in command_surfaces:
            for match in re.finditer(r"\bmake\s+([A-Za-z0-9_.-]+)", surface):
                target = match.group(1).rstrip(".,;:)")
                if target not in targets:
                    missing.append((str(path), target))

    assert missing == []


def test_public_docs_prose_does_not_accidentally_look_like_make_commands():
    docs = [Path("README.md"), Path("ROADMAP.md"), Path("PRODUCT_SPEC.md"), *Path("docs").glob("*.md")]
    suspicious: list[tuple[str, str]] = []

    for path in docs:
        text = path.read_text(encoding="utf-8")
        code_ranges = [(match.start(), match.end()) for match in re.finditer(r"`[^`]*`|```.*?```", text, flags=re.DOTALL)]
        for match in re.finditer(r"\bmake\s+([a-z][a-z-]+)", text):
            if any(start <= match.start() < end for start, end in code_ranges):
                continue
            target = match.group(1)
            if target not in {"the", "clear", "decisions", "risk", "unsupported"}:
                continue
            suspicious.append((str(path), match.group(0)))

    assert suspicious == []


def test_sample_stock_reports_explain_methodology_and_use_current_research_boundary():
    for report_name in ("a.md", "meta.md", "nvda.md", "qqq.md", "smh.md", "apld.md"):
        report = Path("outputs/stock_reports", report_name).read_text(encoding="utf-8")
        assert "Single-Stock Research Report" in report
        assert "## At A Glance" in report
        assert "## Evaluation Snapshot" in report
        assert "## Best Review Path" in report
        assert report.index("## At A Glance") < report.index("## How To Read This Report")
        assert (
            report.index("## At A Glance")
            < report.index("## Evaluation Snapshot")
            < report.index("## Best Review Path")
            < report.index("## How To Read This Report")
        )
        assert "- Mode:" in report
        assert "- Decision view:" in report
        assert "- DCF:" in report
        assert "- Peer context:" in report
        assert "- Optional context:" in report
        assert "- Method: project readiness gates decide what can appear" in report
        assert any(
            method_boundary in report
            for method_boundary in (
                "discounted terminal value, cash/debt adjustment, and fair value per share when ready",
                "DCF formula output is withheld until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness",
                "monitor reports use local price, market, liquidity, correlation, or theme context and exclude operating-company valuation methods",
            )
        )
        assert "- Next local step:" in report
        assert "## Analysis Quality" in report
        assert "## Methodology" in report
        assert "## Evaluation Function Check" in report
        assert "## Copyable Proof Commands" in report
        assert "Copy-only: these are local research commands to copy when you choose" in report
        assert "the report does not run imports or refreshes and does not connect to external accounts" in report
        assert "## Copyable Proof Commands" in report.split("## Source Readiness Check")[0]
        assert "readiness gate first, supported analysis second, valuation math third, explanation last" in report
        assert "Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording" in report
        assert "DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value" in report
        assert "Score boundary: setup, watchlist, confidence, and monthly scores are triage aids" in report
        assert "not price targets, expected returns, or allocation instructions" in report
        assert "missing fields are not inferred" in report
        assert "copyable command only" in report
        assert "Local CSV-backed research data" not in report
        assert "T00:00:00" not in report
        if report_name != "apld.md":
            assert "Saved local research data" in report
        assert "Broken" not in report
        assert "Avoid" not in report
        assert "not_ready" not in report
        assert "monitor_context" not in report
        assert "peer_data_unavailable" not in report
        assert "insufficient_data" not in report
        assert "method=fcf_direct" not in report
        assert "DCF assumptions and sensitivity; DCF assumptions and sensitivity" not in report
        assert "method=revenue_fcf_margin" not in report
        assert "Price ready: True" not in report
        assert "Price ready: False" not in report
        assert "Earnings ready: False" not in report
        assert "Analyst estimates ready: False" not in report
        assert re.search(r"(?<!`)Run make\s+[A-Za-z0-9_.-]+", report) is None
        assert re.search(r"(?<!`)run make\s+[A-Za-z0-9_.-]+", report) is None
        assert "final state: Ignore" not in report
        assert "current state is Ignore" not in report
        for raw_field in (
            "EPSGrowth",
            "GrossMargin",
            "DebtToEquity",
            "ForwardPE",
            "EVToSales",
            "EVToEBITDA",
            "PriceToFCF",
            "FCFYield",
            "shares_outstanding",
            "free_cash_flow",
            "fcf_margin",
            "market_cap_or_price_and_shares",
            "reason_not_ready",
            "missing_dcf_fields",
            "market_direction",
        ):
            assert raw_field not in report
        assert "transaction execution" not in report.lower()
        assert "trade instruction" not in report.lower()
        assert "preview-first local import workflows" in report
        assert "staged import workflows" not in report


def test_methodology_doc_explains_formulas_limits_and_code_paths():
    methodology = Path("docs/METHODOLOGY.md").read_text(encoding="utf-8")

    for phrase in (
        "Base FCF = free_cash_flow",
        "Terminal value = Terminal FCF / (WACC - terminal growth)",
        "Fair value per share = Equity value / shares outstanding",
        "Valuation status is a gate, not a recommendation",
        "Scores And Ranking Context",
        "setup scores, watchlist scores, data-confidence scores, and monthly",
        "Scores are not:",
        "Price targets",
        "Expected returns",
        "Portfolio weights",
        "Buy/sell/hold recommendations",
        "converted into a weak score-based conclusion",
        "outputs/undervalued_candidates.csv",
        "valuation-readiness and",
        "not an automatic undervalued-stock list",
        "not_ready",
        "meaning not enough trusted data exists for valuation",
        "`insufficient_data`, meaning the valuation is intentionally blocked until trusted inputs exist",
        "What Is Data Versus App Method",
        "The product separates source inputs from analysis rules so the report is not a black box",
        "Third-party or optional provider data can supply rows, but it does not decide the research conclusion",
        "How This Compares To Standard Research Workflows",
        "The product follows a familiar equity-research sequence, but keeps each step visible and gated",
        "Standard research step",
        "Intrinsic valuation",
        "Relative valuation",
        "A free-cash-flow DCF with visible scenario assumptions, WACC, terminal growth, and sensitivity",
        "Peer valuation from guessed relationships, sector fallback, or incomplete peer metrics",
        "Compared with a professional research terminal or analyst model, this project is intentionally narrower",
        "the same project code checks data readiness, runs DCF math only when inputs exist",
        "Fundamental review is therefore a validation-and-interpretation layer",
        "DCF output is treated as scenario math, not a price target",
        "Conservative DCF Normalization",
        "It is a transparent guardrail inside `src/valuation.py`",
        "Observed revenue growth above the conservative start-growth cap is capped before projection",
        "Projected early-year FCF growth can be capped even after the revenue-growth path is built",
        "Observed FCF margin above the conservative margin cap is capped before projection",
        "Normalized long-term growth is kept below WACC, and terminal growth must remain below WACC",
        "These warnings are part of the model audit trail",
        "not that the product guessed missing data or changed source inputs",
        "Data confidence follows the same principle",
        "Data Confidence And Decision Scores",
        "Data confidence is a data-quality and review-routing signal, not investment conviction",
        "Data readiness score =",
        "(ready features + 0.45 * partial features) / ready-or-partial-or-blocked features",
        "0.80 or higher",
        "0.55 to below 0.80",
        "0.25 to below 0.55",
        "Data confidence is capped by decision bucket",
        "Blocked by Data",
        "Stays low even if some partial context exists",
        "an ETF/index monitor row can have low or medium data confidence for monitoring while DCF stays excluded",
        "When a company ticker has the full trusted local input stack",
        "At A Glance status: mode, decision view, DCF state, peer context, optional context, method cue, and next local step",
        "Best Review Path: tells the reader whether to review DCF and peers",
        "Evaluation Snapshot: summarizes supported evaluation, valuation boundary, data-confidence cue, next proof step, and stop rule before the detailed sections",
        "The report should be read top-down: visitor scan cue first, At A Glance second, Reader Guide third, Evaluation Snapshot fourth, Proof Checklist fifth",
        "copyable local proof commands next",
        "the report does not run imports or refreshes and does not connect to external accounts",
        "At A Glance mode, method cue, and next local step",
        "Evaluation Snapshot for supported evaluation, valuation boundary, data-confidence cue, next proof, and stop rule",
        "Best Review Path for the safest reading order and proof step",
        "Price, momentum, liquidity, and market-context review",
        "Standalone DCF assumptions, bear/base/bull scenario values, and sensitivity context",
        "Peer trend or peer valuation context only when source-backed peer inputs are ready",
        "Copyable local commands for optional context, peer review, or source-readiness checks",
        "When any part of that stack is missing, only the supported sections appear",
        "local command path for inspecting or proving that input",
        "Readiness Proof Ladder",
        "The product uses the same readiness proof ladder in the dashboard, single-stock reports, and Data Health review lists",
        "Price-ready does not mean fundamentals-ready",
        "Fundamentals-ready does not mean DCF-ready unless all required DCF fields pass",
        "DCF-ready does not mean peer-ready",
        "Peer-ready does not mean earnings or analyst estimates are available",
        "blocked rows must not be labeled undervalued, overvalued, DCF-ready, peer-ready, or optional-context-ready",
        "operating-company DCF and peer valuation are excluded, not failed",
        "`make focus-fundamentals TICKER=NVDA`",
        "`make focus-peers TICKER=A`",
        "`data/imports/fundamentals.csv`",
        "`data/imports/peers.csv`",
        "`make imports-validate`, then `make imports-preview`, then `make imports-apply`",
        "they show the first trustworthy proof step instead of hiding the gap behind a weak conclusion",
        "Where This Lives In Code",
        "`src/readiness_engine.py`",
        "`src/dcf_readiness.py`",
        "`src/valuation.py`",
        "`src/stock_report.py`",
        "not hidden in a model prompt",
    ):
        assert phrase in methodology


def test_roadmap_treats_single_stock_report_as_implemented_and_next_stage_as_v2():
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    for phrase in (
        "Single-stock report mode with readiness, methodology, source readiness check",
        "Public-facing methodology documentation",
        "Public README/dashboard polish",
        "### B. Single-Stock Research Mode V2",
        "`make stock-report-md TICKER=...` generates clean Markdown reports for visitor demos",
        "`make stock-report TICKER=...` remains available when optional report data is useful for inspection",
        "Reports show readiness, Evaluation Snapshot, Proof Checklist, Best Review Path, analysis quality, methodology, evaluation function checks",
        "Reports now open with a visitor scan cue, then `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, and `Best Review Path`",
        "ETF/index/fund reports show operating-company DCF as excluded, not failed",
        "`Blocked by Data - Missing Peer Mapping`",
        "## 8. Next Public Roadmap Stage",
        "Scalable price refresh",
        "`make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo`",
        "`make readiness-snapshot`",
        "`make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30`",
        "`make diff-hygiene`",
        "Trusted fundamentals",
        "`make sec-stage-queue TOP_N=25`",
        "Source-backed peers",
        "`make peer-mapping-queue TOP_N=25`",
        "Optional context",
        "`make optional-context-worklist TOP_N=25`",
        "Source readiness guidance",
        "`make public-check`, `make diff-hygiene`",
        "Data strategy",
        "Read `docs/DATA_STRATEGY.md`, then use the targeted commands above for a 5-10 company pilot.",
        "Do not publish broad generated CSV churn unless it is the reviewed artifact for that release",
        "Do not add workflows that run imports, refreshes, account actions, direct recommendations, fabricated data, or valuation labels without ready inputs",
    ):
        assert phrase in roadmap

    assert "### B. Single Stock Research Mode\n\nGoal: produce a data-honest single-ticker research report" not in roadmap
    assert "- Add ticker search in the dashboard." not in roadmap
    assert "`make price-refresh-loop BATCHES=... TOP_N=... PROVIDER=yahoo`" not in roadmap


def test_product_spec_keeps_execution_features_permanently_out_of_scope():
    spec = Path("PRODUCT_SPEC.md").read_text(encoding="utf-8")

    for phrase in (
        "## Current Product Surfaces",
        "`Home`: plain-language readiness cards and next-action cards first, with methodology ladder and example report comparisons in collapsed sections",
        "`Single-Stock Report`: ticker-level visitor scan cue, At A Glance status, Reader Guide, Evaluation Snapshot, Proof Checklist, Best Review Path, data-confidence cue, methodology cue, analysis quality, valuation state, source readiness check, and copyable local proof commands",
            "`Data Health`: trusted local data paths, import validation, rejected-row reports, and proof review paths",
        "`Value / Re-rating`: DCF-ready, peer-limited, blocked, and ETF/index/fund excluded valuation states",
        "Markdown reports under `outputs/stock_reports/`",
        "richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data modes",
        "Broad-universe tables should stay filtered and row-limited by default",
        "## Public Share Definition",
        "the README has a short demo path and dashboard preview",
        "sample reports show a visitor scan cue, `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, `Best Review Path`, data-confidence cues, methodology, evaluation function checks, source readiness, and copyable local proof commands",
        "project code provides readiness gates, DCF math, peer boundaries, and report wording",
        "`make public-check` passes",
        "generated CSV/JSON churn is reviewed before staging and is not committed by default",
        "## Future Research Enhancements Not Implemented Yet",
        "Paid or licensed data-provider integrations for trusted research inputs",
        "Full SEC financial-statement modeling beyond preview-first fundamentals imports",
        "Full market-scale background job scheduling for local refresh/import workflows",
        "Automated peer suggestions only when clearly labeled as fallback",
        "## Permanently Out Of Scope",
        "Broker connections",
        "Automated order routing",
        "Auto-trading",
        "Direct buy/sell/hold recommendations",
        "Options trade recommendations",
        "Fabricated prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or research conclusions",
    ):
        assert phrase in spec

    future_section = spec.split("## Future Research Enhancements Not Implemented Yet", 1)[1].split("## Permanently Out Of Scope", 1)[0]
    for forbidden in (
        "Broker connections",
        "Automated order routing",
        "Auto-trading",
        "Direct buy/sell/hold recommendations",
        "Options trade recommendations",
    ):
        assert forbidden not in future_section


def test_operator_guide_is_command_focused_and_research_only():
    guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")

    for phrase in (
        "Data readiness first",
        "Analysis second",
        "Research decision last",
        "does not connect to brokers",
        "make pipeline",
        "make readiness",
        "make project-status",
        "make stock-report-md TICKER=NVDA",
        "make stock-report-md TICKER=A",
        "make stock-report-md TICKER=META",
        "make stock-report-md TICKER=QQQ",
        "make stock-report-md TICKER=SMH",
        "make stock-report-md TICKER=APLD",
        "For public demos, prefer `make stock-report-md TICKER=NVDA`.",
        "Use `make stock-report TICKER=NVDA` only when you want the optional local report data for inspection.",
        "make dashboard",
        "make dashboard-smoke",
        "Open the Home page `Example reports` section to compare richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data examples",
        "make price-worklist TOP_N=10",
        "make focus-fundamentals TICKER=NVDA",
        "make peer-mapping-queue TOP_N=10",
        "make optional-context-worklist TOP_N=10",
        "make imports-validate",
        "make imports-preview",
        "make imports-apply",
        "make price-refresh-loop DRY_RUN=1",
        "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30",
        "make readiness-snapshot",
        "make diff-hygiene",
        "snapshot readiness, then run one capped loop",
        "Read the visitor scan cue first, then `At A Glance`",
        "At A Glance",
        "Best Review Path",
        "method cue",
        "Analysis Quality",
        "Methodology",
        "DCF formula path",
        "The At A Glance method cue and the `Methodology` section show the DCF formula path",
        "For local import files, use preview before apply",
        "Evaluation Function Check",
        "Copyable Proof Commands",
        "does not run imports or refreshes and does not connect to external accounts",
        "ready, blocked, excluded, or optional",
        "Analysis Modes",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review only",
        "Monitor-only context",
        "Data needed before analysis",
        "Large refreshed CSVs are local working data",
        "set `MAX_CANDIDATES` to the approximate number of missing-price rows you want to cover",
        "docs/analysis_capability_audit.md",
        "What Powers The Analysis",
        "shipped analysis comes from project code under `src/`",
        "Support tools and libraries are not the stock-analysis rules",
        "shipped readiness gates, valuation gates",
    ):
        assert phrase in guide
    assert "META` demonstrates company-level analysis where peer context is still locked" not in guide
    assert "For local import draft workflows" not in guide
    assert "For local import drafts, use preview before apply" not in guide
    assert "make price-refresh-loop BATCHES=5 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30" not in guide

    for forbidden in (
        "buy recommendation",
        "sell recommendation",
        "auto-trading system",
        "hidden investing engine",
    ):
        assert forbidden not in guide.lower()


def test_public_release_docs_point_to_operator_guide_without_stale_future_copy():
    checklist = Path("docs/PUBLIC_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    audit = Path("docs/public_cleanup_audit.md").read_text(encoding="utf-8")
    diff_audit = Path("docs/DIFF_HYGIENE_AUDIT.md").read_text(encoding="utf-8")

    assert "docs/OPERATOR_GUIDE.md" in checklist
    assert "docs/DATA_STRATEGY.md" in checklist
    assert "docs/LICENSE_DECISION_GUIDE.md" in checklist
    assert "docs/DIFF_HYGIENE_AUDIT.md" in checklist
    assert "portfolio/demo project" in checklist
    assert "deeper local workflow guide" in checklist
    assert "dashboard `Data Health` page visible as the safe freshness guide" in checklist
    assert "read-only routine first, capped price dry-run before real refreshes" in checklist
    assert "review-required lanes for fundamentals, peers, earnings, and analyst estimates" in checklist
    assert "not told to manually refresh all 3,538 tickers every day" in checklist
    assert "lane-specific freshness and generated-data hygiene" in checklist
    assert "make demo`, `make status-check TOP_N=5`, `make stock-report-md TICKER=NVDA`, and `make dashboard" in checklist
    assert "make stock-report-md TICKER=NVDA" in checklist
    assert "make trusted-data-pilot-candidates TOP_N=10" in checklist
    assert "make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1" in checklist
    assert "default candidate output stays compact for visitors" in checklist
    assert "make trusted-data-pilot-packet TICKER=CRDO" in checklist
    assert "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10" in checklist
    assert "read-only first step for ranking current company blockers" in checklist
    assert "choose 5-10 operating companies only when source proof exists" in checklist
    assert "file presence, row counts, staged-folder counts, or rejected-row report existence are not proof" in checklist
    assert "source review, validation, preview/apply, readiness rebuild, and the regenerated report prove the lane changed" in checklist
    assert "define a useful pilot win as before report, lane review, trusted source row" in checklist
    assert "Suggested starter set: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`" in checklist
    assert "Treat `QQQ` and `SMH` as ETF/index monitor demos" in checklist
    assert "Keep the pilot evidence packet visible" in checklist
    assert "before report, review path, validate/apply, rejected-row, and rebuild-proof packet" in checklist
    assert "baseline readiness, before report, focused blocker check, lane review path" in checklist
    assert "validate/preview/apply, rejected-row check, rebuild proof" in checklist
    assert "prefer `make stock-report-md` for LinkedIn/GitHub visitors" in checklist
    assert "`At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, `Best Review Path`, `Analysis Quality`, `Methodology`, `Evaluation Function Check`, and `Copyable Proof Commands`" in checklist
    assert "small pilot" in checklist
    assert "After it passes, run `make diff-hygiene`" in checklist
    assert "make diff-hygiene-files" in checklist
    assert "make staged-hygiene-check" in checklist
    assert "outputs/staging/" in checklist
    assert "git add --pathspec-from-file=..." in checklist
    assert "local review next steps" in diff_audit
    assert "operator next steps" not in diff_audit
    assert "safe staging" in checklist
    assert "generated CSV/JSON churn" in checklist
    assert "new `docs/`, `scripts/`, and `tests/` files" in checklist
    assert "changed and new file counts" in diff_audit
    assert "make diff-hygiene-files" in diff_audit
    assert "make staged-hygiene-check" in diff_audit
    assert "outputs/staging/product_files.txt" in diff_audit
    assert "outputs/staging/product_plus_reports.txt" in diff_audit
    assert "New files under `docs/`" in diff_audit
    assert "`scripts/`, and `tests/` are treated as product candidates" in diff_audit
    for demo_command in (
        "make demo",
        "make stock-report-md TICKER=APLD",
        "make stock-report-md TICKER=NVDA",
        "make stock-report-md TICKER=A",
        "make stock-report-md TICKER=META",
        "make stock-report-md TICKER=QQQ",
        "make stock-report-md TICKER=SMH",
    ):
        assert demo_command in checklist

    for phrase in (
        "Public Release Hygiene",
        "Visitor Experience",
        "Data Hygiene",
        "License Decision",
        "Methodology And Trust",
        "Public Wording",
        "Verification Before Sharing",
        "docs/OPERATOR_GUIDE.md",
        "docs/METHODOLOGY.md",
        "docs/LICENSE_DECISION_GUIDE.md",
        "public reuse rights are not granted yet",
        "timestamp-only churn",
        "Research-only; no broker integration or order execution.",
        "make dashboard-smoke",
            "make demo",
            "make public-check",
            "make stock-report-md TICKER=NVDA",
            "git diff --check",
    ):
        assert phrase in audit

    assert "AGENTS.md" not in audit
    assert ".agents" not in audit
    assert "internal agent" not in audit.lower()
    assert "may benefit from a separate `docs/OPERATOR_GUIDE.md` later" not in audit
    assert "Whether to create a separate `docs/OPERATOR_GUIDE.md`" not in audit

    for phrase in (
        "Do not stage broad refreshed local data",
        "data/prices.csv",
        "outputs/*.csv",
        "small Markdown sample reports only",
        "make dashboard-smoke",
        "make demo",
        "make public-check",
    ):
        assert phrase in diff_audit


def test_public_docs_avoid_machine_readable_first_read_copy():
    public_docs = {
        "README.md": Path("README.md").read_text(encoding="utf-8"),
        "docs/OPERATOR_GUIDE.md": Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8"),
        "docs/PUBLIC_RELEASE_CHECKLIST.md": Path("docs/PUBLIC_RELEASE_CHECKLIST.md").read_text(encoding="utf-8"),
    }

    for path, text in public_docs.items():
        assert "machine-readable" not in text, path


def test_license_decision_guide_is_present_until_license_is_chosen():
    guide = Path("docs/LICENSE_DECISION_GUIDE.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert not Path("LICENSE").exists()
    for phrase in (
        "does not currently grant public reuse rights",
        "Portfolio showcase only",
        "Do not claim the project is open source until a license is added",
        "add a root-level `LICENSE` file",
    ):
        assert phrase in guide
    assert "reuse rights are not granted until a license is added" in readme
    assert "MIT License" not in readme
    assert "Apache License" not in readme


def test_stock_report_cli_data_unlock_fallback_uses_product_language():
    source = Path("src/stock_report.py").read_text(encoding="utf-8")

    assert "Data-needed Markdown report:" in source
    assert "First blocker to resolve:" in source
    assert "Readiness-only Markdown report:" not in source
    assert "Full stock report blocked:" not in source


def test_linkedin_project_brief_uses_current_demo_path_and_analysis_quality():
    brief = Path("docs/LINKEDIN_PROJECT_BRIEF.md").read_text(encoding="utf-8")

    for phrase in (
        "data readiness first, analysis second, research decision last",
        "what can be reviewed now",
        "what is blocked by missing data",
        "what is excluded because the method does not apply",
        "which trusted local input would unlock the next layer",
        "Best demos",
        "`NVDA` for DCF-ready company review",
        "`META` for valuation still gated by trusted fundamentals",
        "`QQQ` for ETF/index monitor context",
        "`MU` for standalone DCF with peer valuation still locked",
        "`CRDO` for a fundamentals-gated proof workflow",
        "A Streamlit command center dashboard",
        "Market-wide readiness checks across a broad ticker universe",
        "Single-stock Markdown reports",
        "At A Glance",
        "Reader Guide",
        "Evaluation Snapshot",
        "Proof Checklist",
        "Best Review Path",
        "DCF-ready, standalone DCF, price/setup-only, monitor-only, and data-needed-before-analysis report modes",
        "Source readiness notes and copyable local proof commands",
        "CSV-first import, validation, preview, rejected-row, and readiness workflows",
        "ready data can be analyzed, blocked data is explained",
        "missing rows are treated as the next proof step",
        "At A Glance status, Evaluation Snapshot, Proof Checklist, Best Review Path, method cue, DCF assumptions",
        "make trusted-data-pilot-candidates TOP_N=10",
        "make trusted-data-pilot-packet TICKER=CRDO",
        "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10",
        "without importing or applying rows",
        "one-company evidence packet",
        "source evidence, and a rebuilt report",
        "leave the rest visibly blocked by missing data until trusted rows exist",
        "docs/DATA_STRATEGY.md",
        "docs/analysis_capability_audit.md",
        "outputs/stock_reports/nvda.md",
        "outputs/stock_reports/a.md",
        "outputs/stock_reports/meta.md",
        "outputs/stock_reports/qqq.md",
        "outputs/stock_reports/smh.md",
        "outputs/stock_reports/apld.md",
        "research-only",
        "does not connect to a broker or place trades",
        "README example map",
        "click the tracked sample reports under `outputs/stock_reports/`",
        "make status-check TOP_N=5",
        "read-only command-center summary without refreshing local artifacts",
        "exact copyable local commands for the next proof step",
    ):
        assert phrase in brief

    assert "standalone DCF review where peer-relative valuation is still locked" in brief
    assert "price/setup review where valuation remains gated" in brief
    assert "CSV-first staged import workflows" not in brief
    assert "staged import validation" not in brief
    assert "refusing to present every ticker as complete" in brief
    for guardrail_phrase in (
        "direct buy/sell instructions",
        "jumping straight to rankings",
        "no broker integration",
    ):
        assert guardrail_phrase in brief


def test_dashboard_qa_records_latest_public_flow_browser_check():
    qa = Path("docs/DASHBOARD_QA.md").read_text(encoding="utf-8")

    for phrase in (
        "2026-06-07 Public Product Flow Pass",
        "`Review one stock`, `Improve data coverage`, and `Inspect proof`",
        "trusted-data pilot path for improving 5-10 companies first",
        "`At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, then `Best Review Path`",
        "routes the DCF/peer-ready `NVDA` example to review DCF, peers, and source readiness",
        "2026-06-07 Follow-Up Product Copy Pass",
        "2026-06-10 Public Navigation And Data Strategy Pass",
        "2026-06-10 Trusted Pilot Candidate UX Pass",
        "2026-06-11 Public Route Alignment Pass",
        "main navigation control reads `Choose your path`",
        "`Review one stock`, `Improve data coverage`, and `Inspect proof`",
        "detailed pages remain available under `More pages`",
        "Automation Boundary table separates repeatable checks from human-reviewed source judgment",
        "demo walkthrough now points visitors to `make trusted-data-pilot-candidates TOP_N=10`",
        "candidate list as read-only",
        "Portfolio Review: confirmed the page renders plain-language capability and limit cards",
        "checklist/review-path language before advanced command detail",
        "broad valuation input count is labeled separately from exact company DCF-ready counts",
        "`next-step context` instead of internal-tool operational wording",
        "prints a company starter set and separates `QQQ` / `SMH` as ETF/index monitor examples",
        "standalone DCF peer wording no longer repeats `DCF assumptions and sensitivity`",
        "Product Tour routes `Inspect proof` to the Data Health proof drawers",
        "Inspect proof: readiness snapshots and proof ledger",
        "generated Monthly Picks CSV remains local working output",
        "2026-06-11 Visitor Guide Browser Pass",
        "Monthly Picks: confirmed the page renders the new `Reader Guide`",
        "`Open a one-stock report next`, `No automatic conclusion`",
        "Single-Stock Report: confirmed the page renders the demo ticker guide",
        "`NVDA`, `META`, `QQQ`, `MU`, `CRDO`, plus optional `A`, `SMH`, and `APLD`",
        "Trusted Data Pilot CLI: confirmed candidate output no longer repeats the `Decision gate` label",
        "Monthly candidate guidance stays a research queue, not a recommendation list.",
        "2026-06-11 Data Health Freshness Routine Pass",
        "Data Health: confirmed the `Freshness Routine` section explains a read-only daily/opening routine",
        "quick read`, `fix first`, and `trusted-data pilot",
        "Refresh and command details",
        "price freshness guidance starts with a capped dry-run command",
        "fundamentals, peer mappings, earnings, and analyst estimates remain review-required lanes",
        "does not claim new fundamentals, peer, earnings, or analyst-estimate coverage",
        "Commands remain copy-only",
        "No generated CSV/JSON churn was published with the UI copy pass",
        "2026-06-11 Trusted Pilot Compact Output Pass",
        "`make trusted-data-pilot-candidates TOP_N=10` prints a compact visitor-friendly shortlist",
        "`make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1` remains available for local proof detail",
        "file status, decision gates, rejected-row paths, and evidence expectations",
        "README, Data Strategy, Public Release Checklist, LinkedIn brief, and `make demo`",
        "compact default points to one-company evidence packets before validate/preview/apply and rebuild proof",
        "The compact candidate command is read-only",
        "`VERBOSE=1` exposes local proof detail only",
    ):
        assert phrase in qa


def test_analysis_capability_audit_is_public_and_data_honest():
    audit = Path("docs/analysis_capability_audit.md").read_text(encoding="utf-8")

    for phrase in (
        "What Is Strong Today",
        "Plain Answer",
        "Function Quality Matrix",
        "What Is Intentionally Limited",
        "Methodology And Provenance",
        "Support Tooling Boundary",
        "Input-To-Output Contract",
        "At A Glance status",
        "Reader Guide near the top",
        "Evaluation Snapshot",
        "Best Review Path",
        "copyable local proof commands",
        "Reader Guide near the top, Evaluation Snapshot near the top, Proof Checklist next",
        "copyable local missing-data proof commands",
        "Supported-Today Assessment",
        "Methodology visibility",
        "Methodology and explanation",
        "docs/METHODOLOGY.md",
        "base FCF, projected FCF, discounted cash flows plus discounted terminal value",
        "filling the gap with an inferred value",
        "Analysis Modes",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review only",
        "Monitor-only context",
        "Data needed before analysis",
        "Standard Python packages support data handling, UI, tests, and optional provider access",
        "Readiness gates",
        "Fundamentals and DCF",
        "Peer comparison",
        "ETF/index monitor context",
        "Single-stock report",
        "Quality verdict",
        "Best use today",
        "Strong today",
        "Good for DCF-ready companies only",
        "Ready when peer data exists",
        "Support layer, not analysis rules",
        "What it refuses to do",
        "src/valuation.py",
        "src/readiness_engine.py",
        "pyproject.toml",
        "`numpy`",
        "`pandas`",
        "`PyYAML`",
        "`streamlit`",
        "`yfinance`",
        "`pytest`",
        "Optional unofficial research-grade data adapter",
        "not a wrapper around external investing services",
        "dependencies support the workflow",
        "they are not the analysis rules",
        "Support Tooling Boundary",
        "Support tools and libraries are outside the stock-analysis rules",
        "not embedded valuation rules",
        "recommendation rules",
        "public product should be judged by the files in this repository",
        "local or provider-assisted data supplies rows",
        "does not import a third-party analyst opinion",
        "Validate whether each feature is `ready`, `partial`, `blocked`, or `excluded`",
        "Reduce data confidence or withhold sections when required inputs are missing",
        "full-data company can show fundamentals, DCF assumptions, sensitivity, and peer context",
        "not yet a full-market data platform",
    ):
        assert phrase in audit
    for forbidden in ("place orders", "connect to brokers", "auto-trade", "direct buy/sell"):
        assert forbidden not in audit.lower()
    assert "Open-source Python packages support data handling" not in audit


def test_package_metadata_matches_public_research_only_positioning():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    for phrase in (
        'name = "stock-research-command-center"',
        "CSV-first, research-only stock command center",
        "readiness gates",
        "single-stock reports",
        "transparent valuation blockers",
        'keywords = ["stocks", "research", "streamlit", "readiness", "valuation", "csv"]',
        "[project.urls]",
        'Repository = "https://github.com/YuzeJ21/Stock-Analysis"',
    ):
        assert phrase in pyproject

    assert "license =" not in pyproject
    assert "github.com/davidjiang8888" not in pyproject
    assert "broker" not in pyproject.lower()
    assert "trading" not in pyproject.lower()


def test_legacy_stock_analysis_scaffold_is_not_published():
    publishable_legacy_files = [
        path
        for path in Path("stock_analysis").rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and not path.name.endswith((".pyc", ".pyo"))
    ]
    assert publishable_legacy_files == []

    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'packages = ["src", "src.providers"]' in pyproject
    assert "stock_analysis" not in pyproject


def test_decision_output_model_matches_current_evaluation_contract():
    model = Path("DECISION_OUTPUT_MODEL.md").read_text(encoding="utf-8")

    for phrase in (
        "decision_subtype",
        "primary_blocker",
        "next_best_action",
        "readiness_score",
        "data_confidence",
        "evaluation_status",
        "purpose_fit",
        "setup_quality",
        "valuation_view",
        "risk_view",
        "missing_data_summary",
        "next_research_step",
        "source_freshness_summary",
        "feature_summary",
        "Current Review Details",
        "Research Candidate - DCF Ready But Peer Blocked",
        "Research Candidate - Optional Context Locked",
        "Monitor - ETF Market Proxy",
        "Monitor - Price/Momentum Ready",
        "Blocked by Data - Missing Price",
        "Blocked by Data - Missing Fundamentals",
        "Blocked by Data - Missing Peer Mapping",
        "Excluded - DCF Not Applicable",
        "Confidence And Scores",
        "Scores must not be displayed as price targets, expected returns, or direct",
        "Base score",
        "CompositeScore",
        "review-order or confidence aid only",
        "ETF/index/fund rows must show DCF as excluded",
    ):
        assert phrase in model


def test_readiness_model_documents_peer_layers_and_snapshot_history():
    model = Path("READINESS_MODEL.md").read_text(encoding="utf-8")

    for phrase in (
        "Peer Readiness Layers",
        "peer_price_ready",
        "peer_momentum_ready",
        "peer_fundamentals_ready",
        "peer_valuation_ready",
        "peer_trend_comparison_ready",
        "peer_valuation_comparison_ready",
        "peer_dcf_comparison_ready",
        "Peer trend comparison may appear before peer valuation",
        "Peer valuation must stay blocked when peer fundamentals or valuation inputs are missing",
        "Sector or industry fallback context must be labeled as fallback",
        "Readiness Snapshot History",
        "make readiness-snapshot",
        "data/reports/ticker_readiness_report.previous.csv",
        "current-only baseline instead of fake deltas",
        "valuation-readiness context in legacy `undervalued_candidates.csv`",
    ):
        assert phrase in model


def test_dashboard_advanced_commands_recommend_dry_run_before_refresh():
    dashboard = Path("src/dashboard.py").read_text(encoding="utf-8")
    dry_run_index = dashboard.index("make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo")
    refresh_index = dashboard.index("make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30")

    assert dry_run_index < refresh_index
    assert "Inspect broad refresh changes before committing or sharing them publicly" in dashboard
    assert "broad refresh churn should be inspected before it is committed or shared publicly" not in dashboard
    assert "Show Local Report" in dashboard
    assert "Build Local Report Preview" not in dashboard
    assert "Show Report Preview" not in dashboard
    assert "Generate Local Stock Report" not in dashboard
    assert "Online lookup (off by default)" in dashboard
    assert "Online data check (optional)" not in dashboard
    assert "Use research-grade online data" not in dashboard
    assert "Show data source details" in dashboard
    assert "Show source readiness details" not in dashboard
    assert "Show report source details" not in dashboard
    assert "Download Local Report Data" in dashboard
    assert "Download Structured Report" not in dashboard
    assert "Download Report Data" not in dashboard
    assert "Download Report Data (JSON)" not in dashboard
    assert "technical context" not in dashboard.lower()
    assert "trend and risk context" in dashboard
    assert "Analysis mode guide." in dashboard
    assert "At A Glance" in dashboard
    assert "stock_report_at_a_glance_cards(report_payload" in dashboard
    assert "stock_report_mode_guide_cards(report_payload)" in dashboard
    assert "Project calculations in src/indicators.py and src/momentum_engine.py." in dashboard
    assert "Project calculations in src/report_generator.py and dashboard helpers." not in dashboard
    assert "Developer detail: raw report JSON" not in dashboard
    assert "Show advanced report data (JSON)" not in dashboard
    assert "Use optional online data" not in dashboard
    assert "Local stock research dashboard" in dashboard
    assert "names checked" in dashboard
    assert "CSV-first research cockpit" not in dashboard
    assert "stocks checked" not in dashboard
    assert "Today's Best Local Research Path" in dashboard
    assert "One compact review path" in dashboard
    assert "operator path" not in dashboard
    assert "Local file checklist" in dashboard
    assert "Local generated file checklist" not in dashboard
    assert "Next Steps" in dashboard
    assert "Next Action Console" not in dashboard
    assert "local file changes" in dashboard
    assert "generated-data churn" not in dashboard


def test_stock_report_cli_help_uses_readable_report_language():
    source = Path("src/stock_report.py").read_text(encoding="utf-8")

    assert "Generate a readable local single-stock research report." in source
    assert "optional report data" in source
    assert "structured stock report" not in source
    assert "structured report data" not in source
    assert "full JSON payload" not in source

def test_readme_preserves_research_only_guardrails_and_preview_first_imports():
    readme = Path("README.md").read_text(encoding="utf-8")
    operator_guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    data_strategy = Path("docs/DATA_STRATEGY.md").read_text(encoding="utf-8")

    assert "Research-Only Guardrails" in readme
    assert "not a trading system" in readme
    assert "docs/DATA_STRATEGY.md" in operator_guide
    assert "Public Visitor FAQ" in data_strategy
    assert "The product analysis comes from this repository's readiness gates, DCF calculations, peer gates, decision buckets, and report wording." in data_strategy
    assert "Local or provider-assisted rows supply inputs; they do not decide valuation status, data confidence, peer readiness, or research state." in data_strategy
    assert "Prices are the safest lane to refresh at scale because they are repeatable time-series rows" in data_strategy
    assert "Fundamentals, peer mappings, earnings, and analyst estimates are judgment-required lanes" in data_strategy
    assert "Missing trusted rows are a product signal." in data_strategy
    assert "Do not try to make all 3,538 tickers fully analysis-ready at once" in data_strategy
    assert "make trusted-data-pilot-candidates TOP_N=10" in data_strategy
    assert "make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1" in data_strategy
    assert "default candidate output is compact" in data_strategy
    assert "row-level proof detail" in data_strategy
    assert "row-level diagnostic" not in data_strategy
    assert "make trusted-data-pilot-packet TICKER=CRDO" in data_strategy
    assert "make trusted-data-pilot TOP_N=10" in data_strategy
    assert "rejected-row report path, rebuild proof, and evidence row to record" in data_strategy
    assert "Suggested company pilot: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`" in data_strategy
    assert "ETF/index examples such as `QQQ` and `SMH` are useful monitor-context demos" in data_strategy
    assert "One-company evidence packet:" in data_strategy
    assert "make trusted-data-pilot-packet TICKER=<ticker>" in data_strategy
    assert "make stock-report-md TICKER=<ticker>" in data_strategy
    assert "Run the lane-specific review command printed by the packet:" in data_strategy
    assert "fundamentals lane: make focus-fundamentals TICKER=<ticker>" in data_strategy
    assert "peer lane: make focus-peers TICKER=<ticker>" in data_strategy
    assert "make imports-validate && make imports-preview && make imports-apply" in data_strategy
    assert "Check the rejected-row report printed by the packet before treating the lane as available." in data_strategy
    assert "Run the matching rebuild proof:" in data_strategy
    assert "fundamentals lane: make readiness && make dcf-readiness" in data_strategy
    assert "peer lane: make readiness && make peer-mapping-queue TOP_N=25" in data_strategy
    assert "lane review path, validate/apply step, rejected-row report path, rebuild proof, and evidence row to record" in data_strategy
    assert "The candidate list and one-company packet also print local file status" in data_strategy
    assert "A file with rows is not automatically trusted coverage" in data_strategy
    assert "Every pilot packet follows the same proof loop" in data_strategy
    assert "snapshot the baseline, generate the before report, review the source proof for the missing lane" in data_strategy
    assert "Only the rebuilt report can prove a lane changed" in data_strategy
    assert "keep the blocker visible and move to the next candidate" in data_strategy
    assert "Read each pilot outcome in durable states:" in data_strategy
    assert "`supported`, `still_blocked`, `skipped`, or `excluded`" in data_strategy
    assert "| Supported | Rebuilt readiness and the regenerated report show the lane is ready. |" in data_strategy
    assert "| Still blocked | Validation failed, rejected rows appeared, or the report stayed locked; keep the named blocker visible. |" in data_strategy
    assert "| Skip | Source proof is unavailable or not reviewable; do not apply placeholder rows, and move to the next shortlisted company. |" in data_strategy
    assert "rejected-row report path, then the relevant readiness proof command" in data_strategy
    assert "does not refresh, import, or edit local CSV files" in data_strategy
    assert "provider-assisted rows are optional inputs" in data_strategy
    assert "Provider-assisted does not mean provider-decided" in data_strategy
    assert "Automation Boundary" in data_strategy
    assert "The product can automate repeatable checks, but it should not automate source judgment." in data_strategy
    assert "Dry-run planning, capped refresh loops, import normalization, validation, readiness rebuilds." in data_strategy
    assert "Freshness Without Daily Manual Work" in data_strategy
    assert "You do not need to hand-refresh every ticker every day for the product to stay useful." in data_strategy
    assert "Treat freshness as a lane-specific review workflow" in data_strategy
    assert "Run status/readiness checks whenever you open the project" in data_strategy
    assert "use capped refresh loops only when coverage is stale or too short for the next research page" in data_strategy
    assert "Only run a real capped price loop after reviewing the dry-run plan." in data_strategy
    assert "Do not schedule unattended fundamentals, peer, earnings, estimate imports, or public commits." in data_strategy
    assert "Whether a source row is trusted, which fiscal period is appropriate, and whether manual fundamentals should be applied." in data_strategy
    assert "Which companies are real peers and whether any fallback sector/industry context is acceptable as context only." in data_strategy
    assert "If a workflow depends on source credibility, issuer judgment, fiscal-period choice, peer selection, or optional provider licensing" in data_strategy
    assert "Safe Overnight Automation" in data_strategy
    assert "keep the job in review mode by default" in data_strategy
    assert "Run `make price-refresh-loop DRY_RUN=1` to produce a capped price-refresh plan without changing local files." in data_strategy
    assert "Do not run unattended jobs that apply fundamentals, peer mappings, earnings, analyst estimates, or public commits." in data_strategy
    assert "make price-worklist TOP_N=10" in data_strategy
    assert "then preview any broader update with `make price-refresh-loop DRY_RUN=1`" in data_strategy
    assert "Pilot Evidence Checklist" in data_strategy
    assert "A company is a useful pilot win only when the evidence is reviewable, not just when a CSV row exists." in data_strategy
    assert "Keep a before/after readiness count from `make readiness-snapshot` and `make readiness`." in data_strategy
    assert "Keep one regenerated Markdown report per pilot company" in data_strategy
    assert "Keep the exact review and validation path that changed the state" in data_strategy
    assert "Record local file status from the pilot output, but do not treat row counts or file existence as proof by themselves." in data_strategy
    assert "Peer-limited companies show the mapped peer blocker and the exact source-backed peer input needed next." in data_strategy
    assert "The final proof is a regenerated report plus refreshed readiness counts, recorded alongside any still-blocked reason" in data_strategy
    assert "Reviewed Data Proof V1" in data_strategy
    assert "Use `make reviewed-data-proof` to show the durable lane-level proof ledger" in data_strategy
    assert "source proof status, reviewer outcome, validate/preview/apply result, rejected-row status, readiness before/after" in data_strategy
    assert "Use `make lane-outcome-history` to summarize lane outcomes over time from the reviewed proof ledger." in data_strategy
    assert "Use `make reviewed-data-proof-record` only after the source proof, validation, preview, rejected-row review, apply step, and readiness proof have been reviewed." in data_strategy
    assert "Use `make price-reviewed-run` after a dry-run plan has been reviewed." in data_strategy
    assert "Use `make public-demo-readiness-pack` or open `docs/PUBLIC_DEMO_READINESS_PACK.md`" in data_strategy
    assert "Data Health also surfaces the latest reviewed proof timeline" in data_strategy
    assert "Reviewed Batch Execution V1" in data_strategy
    assert "Use `DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10` to preview a frontier lane as a reviewed run packet without writing packet artifacts." in data_strategy
    assert "The packet includes the pre-run readiness snapshot command, dry-run command, capped execution command, validate/preview/apply gates" in data_strategy
    assert "the packet says to run `make readiness` before relying on final counts." in data_strategy
    assert "Keep the public branch clean with `make diff-hygiene`" in data_strategy
    assert "Applying SEC/manual fundamentals rows without validation and preview" in data_strategy
    assert "Peer relationships inferred only from sector labels" in data_strategy
    for phrase in (
        "place orders",
        "connect to brokers",
        "auto-trade",
        "recommend option trades",
        "provide direct buy/sell instructions",
        "fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations",
    ):
        assert phrase in readme
    for phrase in (
        "make templates",
        "make imports-validate",
        "make imports-preview",
        "make imports-apply",
    ):
        assert phrase in operator_guide


def test_product_facing_status_labels_avoid_action_language():
    public_paths = [
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("PRODUCT_SPEC.md"),
        Path("READINESS_MODEL.md"),
        Path("DECISION_OUTPUT_MODEL.md"),
        *Path("docs").glob("*.md"),
        *Path("outputs/stock_reports").glob("*.md"),
        Path("src/momentum_engine.py"),
        Path("src/monthly_picks.py"),
        Path("src/portfolio_review.py"),
        Path("src/state_machine.py"),
        Path("src/dashboard.py"),
    ]
    forbidden_labels = ("Buyable Area", "Pullback Add Candidate", "Add Candidate", "Hold but Do Not Add")

    for path in public_paths:
        text = path.read_text(encoding="utf-8")
        for label in forbidden_labels:
            assert label not in text, f"{path} still exposes action-sounding label {label!r}"

    for replacement in ("Research Ready", "Pullback Review Candidate", "Constructive Review", "Hold Review Only"):
        assert replacement in Path("src/dashboard.py").read_text(encoding="utf-8")


def test_generated_product_outputs_use_current_import_draft_language():
    committed_generated_paths = [
        Path("outputs/research_decisions.csv"),
        Path("outputs/peer_unlock_worklist.csv"),
        Path("data/outputs/research_decisions.csv"),
        *Path("outputs/stock_reports").glob("*.md"),
    ]
    local_generated_paths = [
        Path("outputs/command_bundle_runbook.csv"),
        Path("outputs/project_status_next_steps.csv"),
        Path("outputs/project_status_top_actions.csv"),
    ]
    generated_paths = committed_generated_paths + [path for path in local_generated_paths if path.exists()]
    stale_phrases = (
        "Import staged price rows",
        "staged price rows",
        "staged imports",
        "staged local workflow",
        "staged local data",
        "staged price import",
        "Advance staged",
        "live staged",
        "full JSON payload",
        "technical context",
    )

    for path in committed_generated_paths:
        assert path.exists(), f"{path} is missing"

    for path in generated_paths:
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still contains stale generated wording {phrase!r}"


def test_public_docs_do_not_reference_stale_github_or_internal_thread_links():
    public_paths = [
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("PRODUCT_SPEC.md"),
        Path("READINESS_MODEL.md"),
        Path("DECISION_OUTPUT_MODEL.md"),
        *Path("docs").glob("*.md"),
        *Path("outputs/stock_reports").glob("*.md"),
    ]
    forbidden = (
        "github.com/davidjiang8888",
        "davidjiang8888/Stock-Analysis",
        "pull/1",
        "Draft PR",
        "codex/market-command-center-roadmap-sync",
        "/Users/",
        "Documents/New project",
        "yjian070",
        "AGENTS.md",
        ".agents",
        "docs/CODEX_SKILLS_OVERVIEW.md",
        "Codex thread",
        "goal prompt",
    )

    for path in public_paths:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in text, f"{path} still references stale/internal link text {phrase!r}"

    linkedin_brief = Path("docs/LINKEDIN_PROJECT_BRIEF.md").read_text(encoding="utf-8")
    assert "https://github.com/YuzeJ21/Stock-Analysis" in linkedin_brief


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
    assert "trusted-data-pilot:\n\t@echo \"Trusted Data Pilot\"" in makefile
    assert "trusted-data-pilot-candidates:\n\t@python3 -m src.trusted_data_pilot --top-n $(or $(TOP_N),10) $(if $(TICKERS),--tickers $(TICKERS),) $(if $(filter 1 true TRUE yes YES,$(VERBOSE)),--verbose,)" in makefile
    assert "trusted-data-pilot-packet:\nifndef TICKER\n\t$(error TICKER is required, for example: make trusted-data-pilot-packet TICKER=CRDO)\nendif\n\t@python3 -m src.trusted_data_pilot --packet $(TICKER)" in makefile
    assert "DEFAULT_TRUSTED_PILOT_TICKERS := MU,CRDO,HOOD,TSLA,META,A,APLD" in makefile
    assert "DEFAULT_TRUSTED_PILOT_EVIDENCE_TICKERS := MU,CRDO" in makefile
    assert "trusted-data-pilot-lane:\nifndef LANE\n\t$(error LANE is required, for example: make trusted-data-pilot-lane LANE=fundamentals_dcf)\nendif\n\t@python3 -m src.trusted_data_pilot --lane $(LANE) --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_TICKERS)) --top-n $(or $(TOP_N),10)" in makefile
    assert "trusted-data-pilot-board:\n\t@python3 -m src.trusted_data_pilot --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_TICKERS)) --top-n $(or $(TOP_N),10) --board" in makefile
    assert "trusted-data-pilot-evidence:\n\t@python3 -m src.trusted_data_pilot --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_EVIDENCE_TICKERS)) --top-n $(or $(TOP_N),10) --write-evidence $(or $(OUTPUT),outputs/trusted_data_pilot_evidence.csv)" in makefile
    assert "reviewed-data-proof:\n\t@python3 -m src.reviewed_data_proof --ledger $(or $(LEDGER),data/reviewed_data_proofs.csv)" in makefile
    assert "lane-outcome-history:\n\t@python3 -m src.reviewed_data_proof --ledger $(or $(LEDGER),data/reviewed_data_proofs.csv) --history" in makefile
    assert "price-reviewed-run:\n\t@python3 -m src.reviewed_data_proof --price-reviewed-run --max-candidates $(or $(MAX_CANDIDATES),3500) --top-n $(or $(TOP_N),100) --provider $(or $(PROVIDER),yahoo) --sleep-seconds $(or $(SLEEP_SECONDS),30)" in makefile
    assert "public-demo-readiness-pack:\n\t@python3 -m src.reviewed_data_proof --ledger $(or $(LEDGER),data/reviewed_data_proofs.csv) --public-demo-pack" in makefile
    assert "readiness-ops-center:\n\t@python3 -m src.readiness_ops --root ." in makefile
    assert "coverage-frontier:\n\t@python3 -m src.readiness_ops --root . --coverage-frontier --top-n $(or $(TOP_N),10)" in makefile
    assert "data-coverage-planner:\n\t@python3 -m src.readiness_ops --root . --expansion-plan --top-n $(or $(TOP_N),10)" in makefile
    assert "coverage-expansion-loop:\n\t@python3 -m src.coverage_expansion_loop --root . --lane $(or $(LANE),auto) --top-n $(or $(TOP_N),10)" in makefile
    assert "readiness-ops-evidence:\n\t@python3 -m src.readiness_ops --root . --evidence --top-n $(or $(TOP_N),10)" in makefile
    assert "reviewed-batch:\n\t@python3 -m src.reviewed_batch --root . --lane $(or $(LANE),prices) --top-n $(or $(TOP_N),10)" in makefile
    assert "reviewed-batch-proof:\n\t@python3 -m src.reviewed_batch_proof --ledger $(or $(LEDGER),data/reviewed_batch_proofs.csv)" in makefile
    assert "reviewed-batch-compare:\n\t@python3 -m src.readiness_comparison --root ." in makefile
    assert "reviewed-batch-preflight:\n\t@python3 -m src.reviewed_batch_preflight --root ." in makefile
    assert "reviewed-batch-proof-record:\nifndef BATCH_ID" in makefile
    assert "reviewed-data-proof-record:\nifndef LANE" in makefile
    assert "Read-only guide: this target prints commands only. It does not refresh prices, import rows, edit CSVs, or change readiness outputs." in makefile
    assert "Check whether price coverage can be improved safely" in makefile
    assert "Suggested company pilot: $(if $(TICKERS),$(TICKERS),NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META)" in makefile
    assert "ETF/index examples such as QQQ and SMH are monitor-context demos, not operating-company DCF targets." in makefile
    assert "Ticker-scoped example: make trusted-data-pilot TICKERS=NVDA,AVGO,AMD,MU,CRDO TOP_N=10" in makefile
    assert "Candidate list: make trusted-data-pilot-candidates TOP_N=10" in makefile
    assert "Company-by-company loop: open one report, choose the matching lane, then validate trusted rows before reading any new valuation." in makefile
    assert "Starter loop example: make stock-report-md TICKER=CRDO -> make trusted-data-pilot-packet TICKER=CRDO -> run the packet's lane-specific review command" in makefile
    assert "Pilot proof target: each company should end with a regenerated report showing ready, locked, or excluded sections from current local evidence." in makefile
    assert "Evidence bundle: keep the before/after readiness count, one regenerated Markdown report, the exact review, validate/apply, rejected-row report, and proof commands that changed the state." in makefile
    assert "SEC credential state: SEC_USER_AGENT is configured for local staging checks." in makefile
    assert "SEC credential state: SEC_USER_AGENT is not configured; use manual trusted fundamentals or stop at diagnostics." in makefile
    assert "Evidence table columns to record: ticker | before_mode | after_mode | outcome_state | changed_inputs | validation_commands | report_path | still_blocked_reason." in makefile
    assert "Stop condition: if trusted source rows are unavailable, do not fill placeholders; leave the ticker visibly blocked by missing data and record the missing input." in makefile
    assert "Pilot evidence packet: baseline readiness, before report, focused blocker check, lane review path, validate/preview/apply, rejected-row check, rebuild proof, and still-blocked evidence row." in makefile
    assert "One-company packet example:" in makefile
    assert "make trusted-data-pilot-candidates TOP_N=10" in makefile
    assert "make trusted-data-pilot-packet TICKER=<ticker>" in makefile
    assert "make stock-report-md TICKER=<ticker>" in makefile
    assert "Run the lane-specific review command printed by the packet:" in makefile
    assert "fundamentals lane: make focus-fundamentals TICKER=<ticker>" in makefile
    assert "peer lane: make focus-peers TICKER=<ticker>" in makefile
    assert "make imports-validate && make imports-preview && make imports-apply" in makefile
    assert "Check the rejected-row report printed by the packet before treating the lane as available." in makefile
    assert "Run the matching rebuild proof:" in makefile
    assert "fundamentals lane: make readiness && make dcf-readiness" in makefile
    assert "peer lane: make readiness && make peer-mapping-queue TOP_N=25" in makefile
    assert "If SEC staging is not configured or source rows are not ready, stop at diagnostics and keep the ticker visibly blocked by missing data." in makefile
    assert "Add peers only when you have source-backed relationships; sector/industry fallback is context, not trusted peer valuation." in makefile
    assert "Stage only intentional docs/code/tests or reviewed sample Markdown reports; keep broad CSV/JSON refresh churn local unless it is the reviewed artifact." in makefile
    assert "make price-worklist $(if $(TICKERS),TICKERS=$(TICKERS) )TOP_N=$(or $(TOP_N),10)" in makefile
    assert "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=$(or $(TOP_N),10) TOP_N=$(or $(TOP_N),10) PROVIDER=yahoo" in makefile
    assert "Use a real capped price loop only after reviewing the dry run and saving a readiness snapshot." in makefile
    assert "Use trusted fundamentals, peer, earnings, or estimate rows only, then validate before apply" in makefile
    assert "make trusted-data-pilot [TICKERS=NVDA,AVGO,AMD,MU,CRDO] [TOP_N=10] Print a read-only company-focused trusted-data pilot plan" in makefile
    assert "make trusted-data-pilot-candidates [TICKERS=NVDA,CRDO,META] [TOP_N=10] Rank read-only company candidates for the next trusted-data pilot" in makefile
    assert "make trusted-data-pilot-lane LANE=fundamentals_dcf [TICKERS=MU,CRDO,HOOD] [TOP_N=10] Print a read-only lane-group runbook and evidence summary" in makefile
    assert "price-normalize:\nifndef INPUT\n\t$(error INPUT is required, for example: make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual)\nendif" in makefile
    assert "stock-report:\nifndef TICKER\n\t$(error TICKER is required, for example: make stock-report TICKER=NVDA)\nendif\n\tpython3 -m src.stock_report --ticker $(TICKER) --provider $(if $(PROVIDER),$(PROVIDER),local) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(MD_OUTPUT),--markdown-output $(MD_OUTPUT),)" in makefile
    assert "stock-report-md:\nifndef TICKER\n\t$(error TICKER is required, for example: make stock-report-md TICKER=NVDA)\nendif\n\t@python3 -m src.stock_report --ticker $(TICKER) --provider $(if $(PROVIDER),$(PROVIDER),local) --quiet $(if $(MD_OUTPUT),--markdown-output $(MD_OUTPUT),)" in makefile
    assert "local-tickers:\n\tpython3 -m src.stock_report --list-local-tickers" in makefile
    assert "import-staging:\n\tpython3 -m src.stock_report --write-import-staging" in makefile
    assert "data-sources-check:\n\tpython3 -m src.data_sources --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "data-sources:\n\tpython3 -m src.data_sources --write-output" in makefile
    assert "research-health-check:\n\tpython3 -m src.research_health --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "action-queue-check:\n\tpython3 -m src.action_queue --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "price-status:\n\tpython3 -m src.data_update --price-status $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert '@echo "Read-only guide: this target prints the visitor path only. It does not refresh data, import rows, or rewrite reports."' in makefile
    assert "@echo \"Visitor demo path:\"" in makefile
    assert "@echo \"   Home -> NVDA ready -> META blocked -> QQQ excluded -> MU peer-limited -> CRDO fundamentals-gated -> trusted-data pilot\"" in makefile
    assert "@echo \"What this proves: ready data is analyzed, blocked data stays visible, and non-applicable methods are excluded instead of forced.\"" in makefile
    assert "@echo \"Data-confidence note: data confidence describes readiness and review routing, not investment conviction.\"" in makefile
    assert "@echo \"2. Open the clean dashboard path:\"" in makefile
    assert "@echo \"   Proves: current readiness counts and top blockers without changing local files.\"" in makefile
    assert "@echo \"   Proves: the product journey starts with Review one stock, Improve data coverage, and Inspect proof.\"" in makefile
    assert "@echo \"3. Generate the minimum proof reports:\"" in makefile
    assert "@echo \"   Each report shows a data-confidence cue, valuation boundary, next proof step, and stop rule.\"" in makefile
    assert "@echo \"      Shows: DCF-ready company review with assumptions and source readiness.\"" in makefile
    assert "@echo \"      Shows: price/setup review where valuation remains gated by trusted fundamentals.\"" in makefile
    assert "@echo \"      Shows: ETF/index monitor context where operating-company DCF is excluded, not failed.\"" in makefile
    assert "@echo \"      Shows: fundamentals/DCF proof workflow with a one-company pilot packet.\"" in makefile
    assert "@echo \"   Optional extra states:\"" in makefile
    assert "@echo \"      Shows: standalone DCF review with mapped-peer valuation inputs still locked.\"" in makefile
    assert "@echo \"      Shows: standalone DCF review with peer-relative valuation still locked.\"" not in makefile
    assert "@echo \"      Shows: another standalone DCF review with peer-relative valuation still locked.\"" in makefile
    assert "@echo \"      Shows: sector ETF monitor context.\"" in makefile
    assert "@echo \"      Shows: price/setup review with fundamentals still locked.\"" in makefile
    assert makefile.index('@echo "   make stock-report-md TICKER=NVDA"') < makefile.index('@echo "   make stock-report-md TICKER=META"')
    assert makefile.index('@echo "   make stock-report-md TICKER=META"') < makefile.index('@echo "   make stock-report-md TICKER=QQQ"')
    assert makefile.index('@echo "   make stock-report-md TICKER=QQQ"') < makefile.index('@echo "   make stock-report-md TICKER=MU"')
    assert makefile.index('@echo "   make stock-report-md TICKER=MU"') < makefile.index('@echo "   make stock-report-md TICKER=CRDO"')
    assert makefile.index('@echo "   make stock-report-md TICKER=CRDO"') < makefile.index('@echo "   Optional extra states:"')
    assert makefile.index('@echo "   Optional extra states:"') < makefile.index('@echo "   make stock-report-md TICKER=A"')
    assert "@echo \"4. Smoke-test the dashboard:\"" in makefile
    assert "@echo \"   Proves: the Streamlit app can boot and answer its local health check.\"" in makefile
    assert "@echo \"5. Optional: see the safe coverage-improvement path:\"" in makefile
    assert "@echo \"   make trusted-data-pilot-candidates TOP_N=10\"" in makefile
    assert "@echo \"   make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1  # optional local proof detail\"" in makefile
    assert "@echo \"   make trusted-data-pilot-packet TICKER=CRDO\"" in makefile
    assert "@echo \"   make trusted-data-pilot TICKERS=<chosen names> TOP_N=10\"" in makefile
    assert "@echo \"   Proves: coverage improves through source proof, validation, rejected-row review, rebuild proof, and still-blocked evidence, not fake rows.\"" in makefile
    assert makefile.index('@echo "   make trusted-data-pilot-candidates TOP_N=10"') < makefile.index('@echo "   make trusted-data-pilot TICKERS=<chosen names> TOP_N=10"')
    assert makefile.index('@echo "   make trusted-data-pilot-candidates TOP_N=10"') < makefile.index('@echo "   make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1  # optional local proof detail"')
    assert "@echo \"6. Before sharing or committing:\"" in makefile
    assert "@echo \"   make public-check\"" in makefile
    assert "@echo \"   make diff-hygiene\"" in makefile
    assert "@echo \"   make diff-hygiene-files  # optional for large dirty trees\"" in makefile
    assert "@echo \"   make staged-hygiene-check # after staging, before commit\"" in makefile
    assert 'This target only prints a visitor path. If you later run stock-report-md commands, they write local Markdown reports under outputs/stock_reports/.' in makefile
    assert "Share-safe story: show NVDA as ready, META as blocked, QQQ as excluded, MU as peer-limited, CRDO as fundamentals-gated, then the trusted-data pilot as the honest proof path." in makefile
    assert "diff-hygiene-files:\n\t@python3 scripts/diff_hygiene.py --write-files" in makefile
    assert "staged-hygiene-check:\n\t@python3 scripts/diff_hygiene.py --staged-check" in makefile
    assert "public-check:" in makefile
    for phrase in (
        'Public share check: diff hygiene',
        'Public share check: staged hygiene',
        'Public share check: whitespace',
        'Public share check: tests',
        'Public share check: dashboard smoke',
        'Public share check: visitor demo',
        "@$(MAKE) --silent diff-hygiene-summary",
        "@$(MAKE) --silent staged-hygiene-check",
        "@git diff --check",
        "@$(MAKE) --silent test",
        "@$(MAKE) --silent dashboard-smoke",
        "@$(MAKE) --silent demo",
    ):
        assert phrase in makefile
    assert "verify:\n\t$(MAKE) test\n\t$(MAKE) pipeline\n\t$(MAKE) validate-data\n\t$(MAKE) onboarding" in makefile
    assert "daily:\n\t$(MAKE) price-refresh\n\t$(MAKE) pipeline\n\t$(MAKE) monthly\n\t$(MAKE) track-record\n\t$(MAKE) validate-data\n\t$(MAKE) onboarding" in makefile
    public_check_body = makefile.split("public-check:", 1)[1].split("\n\ntest:", 1)[0]
    assert "price-refresh" not in public_check_body
    assert "imports-apply" not in public_check_body
    assert "pipeline" not in public_check_body
    assert "verify:\n\tpython3 -m pytest tests -q" not in makefile
    assert "daily:\n\tpython3 -m src.data_update --universe-file data/universe.csv" not in makefile
