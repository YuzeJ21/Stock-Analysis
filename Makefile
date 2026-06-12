.PHONY: help help-full demo trusted-data-pilot trusted-data-pilot-candidates trusted-data-pilot-packet trusted-data-pilot-lane trusted-data-pilot-board trusted-data-pilot-evidence diff-hygiene diff-hygiene-summary diff-hygiene-files staged-hygiene-check public-wording-check public-check status status-check test pipeline stock-report stock-report-md local-tickers monthly track-record validate-data data-sources-check data-sources research-health research-health-check action-queue action-queue-check project-status verify validate-all daily dashboard dashboard-smoke sec-stage sec-validate sec-preview sec-apply imports-validate imports-preview imports-apply import-staging universe-preview universe-apply universe-refresh universe-report universe-active coverage data-wizard unlock-ladder unlock-summary command-bundles command-bundle-details command-bundle-runbook bundle-prices bundle-fundamentals bundle-peers bundle-prices-broader bundle-fundamentals-broader bundle-peers-broader detail-prices detail-fundamentals detail-peers detail-prices-broader detail-fundamentals-broader detail-peers-broader runbook-prices runbook-fundamentals runbook-peers runbook-prices-broader runbook-fundamentals-broader runbook-peers-broader focus-price focus-fundamentals focus-peers onboarding templates price-status price-worklist fundamentals-peer-worklist optional-context-worklist sec-stage-queue peer-mapping-queue price-validate price-preview price-apply price-refresh price-refresh-loop price-normalize import-prices price-coverage dcf-readiness import-fundamentals optional-context-readiness import-earnings import-analyst-estimates readiness readiness-snapshot research-decisions

DEFAULT_TRUSTED_PILOT_TICKERS := MU,CRDO,HOOD,TSLA,META,A,APLD
DEFAULT_TRUSTED_PILOT_EVIDENCE_TICKERS := MU,CRDO

help:
	@echo "Stock Research Command Center"
	@echo ""
	@echo "Start here:"
	@echo "  make demo                       Print the clean visitor walkthrough"
	@echo "  make status-check TOP_N=5       Show current readiness and top blockers"
	@echo "  make stock-report-md TICKER=NVDA Generate the clearest sample stock report"
	@echo "  make dashboard                  Open the dashboard"
	@echo "  make trusted-data-pilot-candidates TOP_N=10"
	@echo "                                  Rank the next source-backed data pilot"
	@echo "  make trusted-data-pilot-packet TICKER=CRDO"
	@echo "                                  Print one company's read-only proof packet"
	@echo "  make trusted-data-pilot-lane LANE=fundamentals_dcf"
	@echo "                                  Print a read-only lane-group runbook"
	@echo "  make trusted-data-pilot-board TICKERS=MU,CRDO,HOOD"
	@echo "                                  Print a read-only multi-ticker pilot board"
	@echo "  make trusted-data-pilot-evidence TICKERS=MU,CRDO"
	@echo "                                  Write a read-only before-state evidence ledger"
	@echo "  make public-check               Run before sharing the GitHub link"
	@echo ""
	@echo "Useful next paths:"
	@echo "  Review one stock:        make stock-report-md TICKER=NVDA"
	@echo "  Improve data coverage:   make trusted-data-pilot-candidates TOP_N=10"
	@echo "  Check price freshness:   make price-refresh-loop DRY_RUN=1"
	@echo "  Verify public hygiene:   make diff-hygiene && make staged-hygiene-check"
	@echo ""
	@echo "For the full local command catalog, run: make help-full"

help-full:
	@echo "Stock Research Command Center convenience commands"
	@echo ""
	@echo "First-time path:"
	@echo "  make demo             Print the clean visitor walkthrough"
	@echo "  make trusted-data-pilot TOP_N=10"
	@echo "                        Print the company-focused trusted-data pilot path"
	@echo "  make trusted-data-pilot-candidates TOP_N=10"
	@echo "                        Rank current company candidates for the next trusted-data pilot"
	@echo "  make trusted-data-pilot-packet TICKER=CRDO"
	@echo "                        Print one company's read-only evidence packet"
	@echo "  make trusted-data-pilot-lane LANE=fundamentals_dcf"
	@echo "                        Print one lane group's ordered proof steps and evidence summary"
	@echo "  make status-check TOP_N=5"
	@echo "  make stock-report-md TICKER=NVDA"
	@echo "  make dashboard-smoke"
	@echo "  make dashboard"
	@echo "  make public-check     Run before sharing the GitHub link"
	@echo ""
	@echo "Core:"
	@echo "  make demo             Print a short visitor demo path without refreshing broad local data"
	@echo "  make trusted-data-pilot [TICKERS=NVDA,AVGO,AMD,MU,CRDO] [TOP_N=10] Print a read-only company-focused trusted-data pilot plan"
	@echo "  make trusted-data-pilot-candidates [TICKERS=NVDA,CRDO,META] [TOP_N=10] Rank read-only company candidates for the next trusted-data pilot"
	@echo "  make trusted-data-pilot-packet TICKER=CRDO Print one company's read-only before-report/review/validate/rejected-row/rebuild evidence packet"
	@echo "  make trusted-data-pilot-lane LANE=fundamentals_dcf [TICKERS=MU,CRDO,HOOD] [TOP_N=10] Print a read-only lane-group runbook and evidence summary"
	@echo "  make trusted-data-pilot-board [TICKERS=MU,CRDO,HOOD] [TOP_N=10] Print a read-only multi-ticker outcome board without writing CSVs"
	@echo "  make trusted-data-pilot-evidence [TICKERS=MU,CRDO] [OUTPUT=outputs/trusted_data_pilot_evidence.csv] Write current before-state proof paths"
	@echo "  make diff-hygiene     Print a read-only staging guide that separates product files from local data changes"
	@echo "  make diff-hygiene-summary Print a short read-only staging summary for public checks"
	@echo "  make diff-hygiene-files Write local pathspec files under outputs/staging for safer reviewed staging"
	@echo "  make staged-hygiene-check Fail if staged files include unreviewed local data/report changes"
	@echo "  make public-wording-check Scan public docs, dashboard copy, and sample reports for unsupported advice/execution wording"
	@echo "  make public-check     Run share-safe checks before posting the repo link; does not refresh broad local data"
	@echo "  make status [TOP_N=5] Refresh supporting artifacts, then print read-only local project status"
	@echo "  make status-check [TICKERS=NVDA,MSFT] [TOP_N=5] Print the current read-only local project status without refreshing artifacts"
	@echo "  make test             Run unit tests"
	@echo "  make pipeline         Generate core CSV outputs"
	@echo "  make stock-report-md TICKER=NVDA [MD_OUTPUT=outputs/stock_reports/nvda.md] Generate a readable Markdown report for demos and review"
	@echo "  make stock-report TICKER=NVDA [OUTPUT=outputs/nvda_stock_report.json] [MD_OUTPUT=outputs/stock_reports/nvda.md] Generate the report plus optional report data for inspection"
	@echo "  make local-tickers    List tickers discoverable from local CSV datasets"
	@echo "  make verify           Run deterministic local verification"
	@echo "  make validate-all     Run extended local validation and dashboard smoke check"
	@echo "  make daily            Optional broader end-to-end local workflow refresh"
	@echo "  make dashboard        Open the Streamlit dashboard"
	@echo "  make dashboard-smoke  Start dashboard headless and check Streamlit health"
	@echo "  make data-sources-check [TICKERS=NVDA,MSFT] [TOP_N=10] Validate local source availability and gap status without rewriting outputs"
	@echo "  make data-sources    Refresh source status and gap report outputs only"
	@echo "  make status now prints the top data gap, suggested check, guided batch, then verify/smoke steps"
	@echo "  Use make status first, then the printed focused check or guided batch, then verify/smoke, then dashboard review"
	@echo ""
	@echo "Research outputs:"
	@echo "  make monthly          Generate monthly research candidates"
	@echo "  make track-record     Generate local monthly picks track record"
	@echo "  make research-health-check [TICKERS=NVDA,MSFT] [TOP_N=10] Print the current read-only research health summary"
	@echo "  make research-health  Generate data quality, liquidity, and correlation outputs"
	@echo "  make project-status   Write the dashboard-ready project status summary"
	@echo "  make action-queue-check [TICKERS=NVDA,MSFT] [TOP_N=10] Print the current read-only action queue summary"
	@echo "  make action-queue     Generate prioritized data/research actions"
	@echo ""
	@echo "Data onboarding:"
	@echo "  make onboarding       Write source status, coverage, research-health, action queue, and project status outputs"
	@echo "  make coverage [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker-level local data coverage"
	@echo "  make data-wizard [TICKERS=NVDA,MSFT] [TOP_N=10] Show prioritized data coverage proof steps"
	@echo "  make unlock-ladder [TICKERS=NVDA,MSFT] [TOP_N=10] Show one next proof stage per ticker"
	@echo "  make unlock-summary [TICKERS=NVDA,MSFT] [TOP_N=10] Show grouped proof priorities by holdings, theme, and sector ETF"
	@echo "  make command-bundles [TICKERS=NVDA,MSFT] [TOP_N=10] Show holdings-first guided data batches for prices, SEC, and peers"
	@echo "  make command-bundle-details [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker-level rows for the current guided data batches"
	@echo "  make command-bundle-runbook [TICKERS=NVDA,MSFT] [TOP_N=10] Show ordered steps for the current guided data batches"
	@echo "  make bundle-prices [TICKERS=NVDA,MSFT] [TOP_N=10] Show the holdings-first price guided batch when available"
	@echo "  make bundle-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10] Show the holdings-first SEC fundamentals guided batch"
	@echo "  make bundle-peers [TICKERS=NVDA,MSFT] [TOP_N=10] Show the holdings-first peer-mapping guided batch"
	@echo "  make bundle-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show the broader-queue price guided batch"
	@echo "  make bundle-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show the broader-queue SEC fundamentals guided batch"
	@echo "  make bundle-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show the broader-queue peer-mapping guided batch"
	@echo "  make detail-prices [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker rows for the holdings-first price guided batch"
	@echo "  make detail-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker rows for the holdings-first SEC fundamentals guided batch"
	@echo "  make detail-peers [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker rows for the holdings-first peer-mapping guided batch"
	@echo "  make detail-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker rows for the broader-queue price guided batch"
	@echo "  make detail-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker rows for the broader-queue SEC guided batch"
	@echo "  make detail-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker rows for the broader-queue peer guided batch"
	@echo "  make runbook-prices [TICKERS=NVDA,MSFT] [TOP_N=10] Show step-by-step price checks for the holdings-first batch"
	@echo "  make runbook-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10] Show step-by-step SEC fundamentals checks for the holdings-first batch"
	@echo "  make runbook-peers [TICKERS=NVDA,MSFT] [TOP_N=10] Show step-by-step peer checks for the holdings-first batch"
	@echo "  make runbook-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show step-by-step price checks for the broader queue"
	@echo "  make runbook-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show step-by-step SEC checks for the broader queue"
	@echo "  make runbook-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10] Show step-by-step peer checks for the broader queue"
	@echo "  make focus-price TICKER=AMD Show one ticker's price detail and next local checks"
	@echo "  make focus-fundamentals TICKER=NVDA Show one ticker's SEC/fundamentals detail and next local checks"
	@echo "  make focus-peers TICKER=NVDA Show one ticker's peer detail and next local checks"
	@echo "  make price-worklist [TICKERS=NVDA,MSFT] [TOP_N=10] Show ticker-by-ticker local price-history gaps"
	@echo "  make fundamentals-peer-worklist [TICKERS=NVDA,MSFT] [TOP_N=10] Show DCF and peer-relative local blockers"
	@echo "  make optional-context-worklist [TICKERS=NVDA,MSFT] [TOP_N=10] Show optional earnings and estimate gaps"
	@echo "  make sec-stage-queue [TICKERS=NVDA,MSFT] [TOP_N=10] Show prioritized SEC fundamentals staging candidates"
	@echo "  make peer-mapping-queue [TICKERS=NVDA,MSFT] [TOP_N=10] Show prioritized manual peer-mapping candidates"
	@echo "  Most read-only onboarding views also accept TOP_N=10 for a shorter local summary"
	@echo "  make templates        Write local CSV templates for peers, earnings, estimates, and manual fallbacks"
	@echo "  make import-staging   Write header-only staging CSV files under data/imports"
	@echo "  make validate-data    Validate local CSV datasets"
	@echo "  make readiness-snapshot Save current ticker readiness as data/reports/ticker_readiness_report.previous.csv before a refresh"
	@echo "  make readiness        Write central data/reports/ticker_readiness_report.csv"
	@echo ""
	@echo "Price fallback:"
	@echo "  make price-refresh-loop DRY_RUN=1 Preview the scalable capped refresh plan without changing local CSV files"
	@echo "  make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 Preview a broad capped plan without calculating batches manually"
	@echo "  make price-refresh-loop [MAX_CANDIDATES=3500] [TOP_N=100] [PROVIDER=yahoo] [SLEEP_SECONDS=30] Run calculated capped batches after reviewing the dry run; avoids repeating 25-ticker refreshes manually"
	@echo "  make price-refresh [TOP_N=25] [PROVIDER=stooq|yahoo] Attempt a capped missing-price remote refresh with local fallback"
	@echo "  make price-refresh TICKERS=NVDA,MSFT [PROVIDER=yahoo] Attempt a targeted free remote price refresh"
	@echo "  make price-status [TICKERS=NVDA,MSFT] [TOP_N=10] Show latest price update status"
	@echo "  make import-prices    Import verified CSVs from data/staged/prices/ into data/prices.csv"
	@echo "  make price-coverage   Write data/price_coverage_report.csv with rows per universe ticker"
	@echo "  Start with make status, then the printed price check or guided batch"
	@echo "  make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual"
	@echo "  make price-validate && make price-preview && make price-apply"
	@echo ""
	@echo "Preview-first fundamentals and universe imports:"
	@echo "  export SEC_USER_AGENT='Name email@example.com'"
	@echo "  make sec-stage TICKERS=NVDA,MSFT"
	@echo "  make dcf-readiness   Write data/dcf_readiness.csv"
	@echo "  make import-fundamentals Import verified CSVs from data/staged/fundamentals/ into data/imports/fundamentals.csv"
	@echo "  make import-earnings Import verified CSVs from data/staged/earnings/ into data/imports/earnings.csv"
	@echo "  make import-analyst-estimates Import verified CSVs from data/staged/analyst_estimates/ into data/imports/analyst_estimates.csv"
	@echo "  make optional-context-readiness Write data/earnings_readiness.csv and data/analyst_estimates_readiness.csv"
	@echo "  make imports-validate && make imports-preview && make imports-apply"
	@echo "  make universe-preview"
	@echo "  make universe-apply"
	@echo "  make universe-refresh Import staged universe rows and refresh master/active reports"
	@echo "  make universe-report  Write data/reports/universe_coverage_report.csv"
	@echo "  make universe-active  Ensure data/universe_active.csv exists"

demo:
	@echo "Stock Research Command Center visitor demo"
	@echo "Read-only guide: this target prints the visitor path only. It does not refresh data, import rows, or rewrite reports."
	@echo "Full share-ready walkthrough: docs/PUBLIC_DEMO_WALKTHROUGH.md"
	@echo "Run these from the repository root so make can find the project targets."
	@echo ""
	@echo "Visitor demo path:"
	@echo "   Home -> NVDA ready -> META blocked -> QQQ excluded -> MU peer-limited -> CRDO fundamentals-gated -> trusted-data pilot"
	@echo "What this proves: ready data is analyzed, blocked data stays visible, and non-applicable methods are excluded instead of forced."
	@echo "Data-confidence note: data confidence describes readiness and review routing, not investment conviction."
	@echo ""
	@echo "1. Confirm the local snapshot:"
	@echo "   make status-check TOP_N=5"
	@echo "   Proves: current readiness counts and top blockers without changing local files."
	@echo ""
	@echo "2. Open the clean dashboard path:"
	@echo "   make dashboard"
	@echo "   Proves: the product journey starts with Review one stock, Improve data coverage, and Explore ready names."
	@echo ""
	@echo "3. Generate the minimum proof reports:"
	@echo "   Each report shows a data-confidence cue, valuation boundary, next proof step, and stop rule."
	@echo "   make stock-report-md TICKER=NVDA"
	@echo "      Shows: DCF-ready company review with assumptions and source readiness."
	@echo "   make stock-report-md TICKER=META"
	@echo "      Shows: price/setup review where valuation remains gated by trusted fundamentals."
	@echo "   make stock-report-md TICKER=QQQ"
	@echo "      Shows: ETF/index monitor context where operating-company DCF is excluded, not failed."
	@echo "   make stock-report-md TICKER=MU"
	@echo "      Shows: standalone DCF review with mapped-peer valuation inputs still locked."
	@echo "   make stock-report-md TICKER=CRDO"
	@echo "      Shows: fundamentals/DCF proof workflow with a one-company pilot packet."
	@echo ""
	@echo "   Optional extra states:"
	@echo "   make stock-report-md TICKER=A"
	@echo "      Shows: another standalone DCF review with peer-relative valuation still locked."
	@echo "   make stock-report-md TICKER=SMH"
	@echo "      Shows: sector ETF monitor context."
	@echo "   make stock-report-md TICKER=APLD"
	@echo "      Shows: price/setup review with fundamentals still locked."
	@echo ""
	@echo "4. Smoke-test the dashboard:"
	@echo "   make dashboard-smoke"
	@echo "   Proves: the Streamlit app can boot and answer its local health check."
	@echo ""
	@echo "5. Optional: see the safe coverage-improvement path:"
	@echo "   make trusted-data-pilot-candidates TOP_N=10"
	@echo "   make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1  # optional local proof detail"
	@echo "   make trusted-data-pilot-packet TICKER=CRDO"
	@echo "   make trusted-data-pilot TICKERS=<chosen names> TOP_N=10"
	@echo "   Proves: coverage improves through source proof, validation, rejected-row review, rebuild proof, and still-blocked evidence, not fake rows."
	@echo ""
	@echo "6. Before sharing or committing:"
	@echo "   make public-check"
	@echo "   make diff-hygiene"
	@echo "   make diff-hygiene-files  # optional for large dirty trees"
	@echo "   make staged-hygiene-check # after staging, before commit"
	@echo ""
	@echo "This target only prints a visitor path. If you later run stock-report-md commands, they write local Markdown reports under outputs/stock_reports/."
	@echo "Share-safe story: show NVDA as ready, META as blocked, QQQ as excluded, MU as peer-limited, CRDO as fundamentals-gated, then the trusted-data pilot as the honest proof path."

trusted-data-pilot:
	@echo "Trusted Data Pilot"
	@echo "Read-only guide: this target prints commands only. It does not refresh prices, import rows, edit CSVs, or change readiness outputs."
	@echo ""
	@echo "Goal: improve 5-10 reviewed companies first, then prove readiness changed."
	@echo "Scope: $(if $(TICKERS),$(TICKERS),choose 5-10 tickers from the active research list or public demo path)"
	@echo "Suggested company pilot: $(if $(TICKERS),$(TICKERS),NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META)"
	@echo "ETF/index examples such as QQQ and SMH are monitor-context demos, not operating-company DCF targets."
	@echo "Ticker-scoped example: make trusted-data-pilot TICKERS=NVDA,AVGO,AMD,MU,CRDO TOP_N=10"
	@echo "Candidate list: make trusted-data-pilot-candidates TOP_N=10"
	@echo "Company-by-company loop: open one report, choose the matching lane, then validate trusted rows before reading any new valuation."
	@echo "Starter loop example: make stock-report-md TICKER=CRDO -> make trusted-data-pilot-packet TICKER=CRDO -> run the packet's lane-specific review command"
	@echo "Pilot proof target: each company should end with a regenerated report showing ready, locked, or excluded sections from current local evidence."
	@echo "Evidence bundle: keep the before/after readiness count, one regenerated Markdown report, the exact review, validate/apply, rejected-row report, and proof commands that changed the state."
	@if [ -n "$$SEC_USER_AGENT" ]; then echo "SEC credential state: SEC_USER_AGENT is configured for local staging checks."; else echo "SEC credential state: SEC_USER_AGENT is not configured; use manual trusted fundamentals or stop at diagnostics."; fi
	@echo "Evidence table columns to record: ticker | before_mode | after_mode | outcome_state | changed_inputs | validation_commands | report_path | still_blocked_reason."
	@echo "Stop condition: if trusted source rows are unavailable, do not fill placeholders; leave the ticker visibly blocked by missing data and record the missing input."
	@echo "Pilot evidence packet: baseline readiness, before report, focused blocker check, lane review path, validate/preview/apply, rejected-row check, rebuild proof, and still-blocked evidence row."
	@echo "One-company packet example:"
	@echo "   make readiness-snapshot"
	@echo "   make trusted-data-pilot-candidates TOP_N=10"
	@echo "   make trusted-data-pilot-packet TICKER=<ticker>"
	@echo "   make stock-report-md TICKER=<ticker>"
	@echo "   Run the lane-specific review command printed by the packet:"
	@echo "      fundamentals lane: make focus-fundamentals TICKER=<ticker>"
	@echo "      peer lane: make focus-peers TICKER=<ticker>"
	@echo "   make imports-validate && make imports-preview && make imports-apply"
	@echo "   Check the rejected-row report printed by the packet before treating the lane as available."
	@echo "   Run the matching rebuild proof:"
	@echo "      fundamentals lane: make readiness && make dcf-readiness"
	@echo "      peer lane: make readiness && make peer-mapping-queue TOP_N=25"
	@echo "   make stock-report-md TICKER=<ticker>"
	@echo ""
	@echo "1. Save the current baseline:"
	@echo "   make readiness-snapshot"
	@echo ""
	@echo "2. Confirm current blockers:"
	@echo "   make status-check $(if $(TICKERS),TICKERS=$(TICKERS) )TOP_N=$(or $(TOP_N),10)"
	@echo ""
	@echo "3. Check whether price coverage can be improved safely:"
	@echo "   make price-worklist $(if $(TICKERS),TICKERS=$(TICKERS) )TOP_N=$(or $(TOP_N),10)"
	@echo "   make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=$(or $(TOP_N),10) TOP_N=$(or $(TOP_N),10) PROVIDER=yahoo"
	@echo "   Use a real capped price loop only after reviewing the dry run and saving a readiness snapshot."
	@echo ""
	@echo "4. Review fundamentals / DCF blockers:"
	@echo "   make sec-stage-queue $(if $(TICKERS),TICKERS=$(TICKERS) )TOP_N=25"
	@echo "   make focus-fundamentals TICKER=<ticker>"
	@echo "   If SEC staging is not configured or source rows are not ready, stop at diagnostics and keep the ticker visibly blocked by missing data."
	@echo ""
	@echo "5. Review source-backed peer blockers:"
	@echo "   make peer-mapping-queue $(if $(TICKERS),TICKERS=$(TICKERS) )TOP_N=25"
	@echo "   make focus-peers TICKER=<ticker>"
	@echo "   Add peers only when you have source-backed relationships; sector/industry fallback is context, not trusted peer valuation."
	@echo ""
	@echo "6. Use trusted fundamentals, peer, earnings, or estimate rows only, then validate before apply:"
	@echo "   make templates"
	@echo "   make imports-validate"
	@echo "   make imports-preview"
	@echo "   make imports-apply"
	@echo ""
	@echo "7. Prove the lane is available before reading valuation:"
	@echo "   make readiness"
	@echo "   make dcf-readiness"
	@echo "   make peer-mapping-queue $(if $(TICKERS),TICKERS=$(TICKERS) )TOP_N=25"
	@echo "   make stock-report-md TICKER=<ticker>"
	@echo ""
	@echo "8. Keep the public branch clean:"
	@echo "   make diff-hygiene"
	@echo "   Stage only intentional docs/code/tests or reviewed sample Markdown reports; keep broad CSV/JSON refresh churn local unless it is the reviewed artifact."
	@echo ""
	@echo "Guardrail: do not fabricate fundamentals, peers, earnings, estimates, valuation inputs, or recommendations."

trusted-data-pilot-candidates:
	@python3 -m src.trusted_data_pilot --top-n $(or $(TOP_N),10) $(if $(TICKERS),--tickers $(TICKERS),) $(if $(filter 1 true TRUE yes YES,$(VERBOSE)),--verbose,)

trusted-data-pilot-packet:
ifndef TICKER
	$(error TICKER is required, for example: make trusted-data-pilot-packet TICKER=CRDO)
endif
	@python3 -m src.trusted_data_pilot --packet $(TICKER)

trusted-data-pilot-lane:
ifndef LANE
	$(error LANE is required, for example: make trusted-data-pilot-lane LANE=fundamentals_dcf)
endif
	@python3 -m src.trusted_data_pilot --lane $(LANE) --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_TICKERS)) --top-n $(or $(TOP_N),10)

trusted-data-pilot-board:
	@python3 -m src.trusted_data_pilot --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_TICKERS)) --top-n $(or $(TOP_N),10) --board

trusted-data-pilot-evidence:
	@python3 -m src.trusted_data_pilot --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_EVIDENCE_TICKERS)) --top-n $(or $(TOP_N),10) --write-evidence $(or $(OUTPUT),outputs/trusted_data_pilot_evidence.csv)

diff-hygiene:
	@python3 scripts/diff_hygiene.py

diff-hygiene-summary:
	@python3 scripts/diff_hygiene.py --summary

diff-hygiene-files:
	@python3 scripts/diff_hygiene.py --write-files

staged-hygiene-check:
	@python3 scripts/diff_hygiene.py --staged-check

public-wording-check:
	@python3 scripts/public_wording_check.py

public-check:
	@echo "Public share check: diff hygiene"
	@$(MAKE) --silent diff-hygiene-summary
	@echo "Public share check: staged hygiene"
	@$(MAKE) --silent staged-hygiene-check
	@echo "Public share check: research-only wording"
	@$(MAKE) --silent public-wording-check
	@echo "Public share check: whitespace"
	@git diff --check
	@echo "Public share check: tests"
	@$(MAKE) --silent test
	@echo "Public share check: dashboard smoke"
	@$(MAKE) --silent dashboard-smoke
	@echo "Public share check: visitor demo"
	@$(MAKE) --silent demo

test:
	python3 -m pytest tests -q

status:
	python3 -m src.project_status --refresh-artifacts --top-n $(or $(TOP_N),5)

status-check:
	python3 -m src.project_status --check --top-n $(or $(TOP_N),5) $(if $(TICKERS),--tickers $(TICKERS),)

pipeline:
	python3 -m src.report_generator

stock-report:
ifndef TICKER
	$(error TICKER is required, for example: make stock-report TICKER=NVDA)
endif
	python3 -m src.stock_report --ticker $(TICKER) --provider $(if $(PROVIDER),$(PROVIDER),local) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(MD_OUTPUT),--markdown-output $(MD_OUTPUT),)

stock-report-md:
ifndef TICKER
	$(error TICKER is required, for example: make stock-report-md TICKER=NVDA)
endif
	@python3 -m src.stock_report --ticker $(TICKER) --provider $(if $(PROVIDER),$(PROVIDER),local) --quiet $(if $(MD_OUTPUT),--markdown-output $(MD_OUTPUT),)

local-tickers:
	python3 -m src.stock_report --list-local-tickers

monthly:
	python3 -m src.monthly_picks --generate --top-n 5

track-record:
	python3 -m src.track_record --monthly-picks

validate-data:
	python3 -m src.stock_report --validate-local-data

data-sources-check:
	python3 -m src.data_sources --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)

data-sources:
	python3 -m src.data_sources --write-output

research-health:
	python3 -m src.research_health --write-output

research-health-check:
	python3 -m src.research_health --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)

action-queue:
	python3 -m src.action_queue --write-output

action-queue-check:
	python3 -m src.action_queue --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)

project-status:
	python3 -m src.project_status --write-output

verify:
	$(MAKE) test
	$(MAKE) pipeline
	$(MAKE) validate-data
	$(MAKE) onboarding

validate-all:
	scripts/validate_all.sh

coverage:
	python3 -m src.data_onboarding --coverage $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

data-wizard:
	python3 -m src.data_onboarding --wizard $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

unlock-ladder:
	python3 -m src.data_onboarding --unlock-ladder $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

unlock-summary:
	python3 -m src.data_onboarding --unlock-summary $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

command-bundles:
	python3 -m src.data_onboarding --command-bundles $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

command-bundle-details:
	python3 -m src.data_onboarding --command-bundle-details $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

command-bundle-runbook:
	python3 -m src.data_onboarding --command-bundle-runbook $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

bundle-prices:
	python3 -m src.data_onboarding --command-bundles --lane prices --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

bundle-fundamentals:
	python3 -m src.data_onboarding --command-bundles --lane fundamentals --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

bundle-peers:
	python3 -m src.data_onboarding --command-bundles --lane peers --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

bundle-prices-broader:
	python3 -m src.data_onboarding --command-bundles --lane prices --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

bundle-fundamentals-broader:
	python3 -m src.data_onboarding --command-bundles --lane fundamentals --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

bundle-peers-broader:
	python3 -m src.data_onboarding --command-bundles --lane peers --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

detail-prices:
	python3 -m src.data_onboarding --command-bundle-details --lane prices --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

detail-fundamentals:
	python3 -m src.data_onboarding --command-bundle-details --lane fundamentals --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

detail-peers:
	python3 -m src.data_onboarding --command-bundle-details --lane peers --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

detail-prices-broader:
	python3 -m src.data_onboarding --command-bundle-details --lane prices --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

detail-fundamentals-broader:
	python3 -m src.data_onboarding --command-bundle-details --lane fundamentals --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

detail-peers-broader:
	python3 -m src.data_onboarding --command-bundle-details --lane peers --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

runbook-prices:
	python3 -m src.data_onboarding --command-bundle-runbook --lane prices --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

runbook-fundamentals:
	python3 -m src.data_onboarding --command-bundle-runbook --lane fundamentals --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

runbook-peers:
	python3 -m src.data_onboarding --command-bundle-runbook --lane peers --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

runbook-prices-broader:
	python3 -m src.data_onboarding --command-bundle-runbook --lane prices --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

runbook-fundamentals-broader:
	python3 -m src.data_onboarding --command-bundle-runbook --lane fundamentals --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

runbook-peers-broader:
	python3 -m src.data_onboarding --command-bundle-runbook --lane peers --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

focus-price:
ifndef TICKER
	$(error TICKER is required, for example: make focus-price TICKER=AMD)
endif
	python3 -m src.data_onboarding --command-bundle-details --lane prices --tickers $(TICKER)
	python3 -m src.data_onboarding --command-bundle-runbook --lane prices --tickers $(TICKER)

focus-fundamentals:
ifndef TICKER
	$(error TICKER is required, for example: make focus-fundamentals TICKER=NVDA)
endif
	python3 -m src.data_onboarding --command-bundle-details --lane fundamentals --tickers $(TICKER)
	python3 -m src.data_onboarding --command-bundle-runbook --lane fundamentals --tickers $(TICKER)

focus-peers:
ifndef TICKER
	$(error TICKER is required, for example: make focus-peers TICKER=NVDA)
endif
	python3 -m src.data_onboarding --command-bundle-details --lane peers --tickers $(TICKER)
	python3 -m src.data_onboarding --command-bundle-runbook --lane peers --tickers $(TICKER)

onboarding:
	python3 -m src.manual_price_import --coverage-only --top-n $(or $(TOP_N),20)
	python3 -m src.dcf_readiness --top-n $(or $(TOP_N),20)
	python3 -m src.optional_context_readiness
	python3 -m src.readiness_engine
	python3 -m src.data_sources --write-output
	python3 -m src.data_onboarding --write-output --top-n $(or $(TOP_N),20)
	python3 -m src.research_health --write-output
	python3 -m src.action_queue --write-output
	python3 -m src.research_decisions
	python3 -m src.project_status --write-output

templates:
	python3 -m src.data_onboarding --write-templates

import-staging:
	python3 -m src.stock_report --write-import-staging

price-status:
	python3 -m src.data_update --price-status $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

import-prices:
	python3 -m src.manual_price_import

price-coverage:
	python3 -m src.manual_price_import --coverage-only --top-n $(or $(TOP_N),25)

price-worklist:
	python3 -m src.data_onboarding --price-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

fundamentals-peer-worklist:
	python3 -m src.data_onboarding --fundamentals-peer-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

optional-context-worklist:
	python3 -m src.data_onboarding --optional-context-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

sec-stage-queue:
	python3 -m src.data_onboarding --sec-stage-queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

peer-mapping-queue:
	python3 -m src.data_onboarding --peer-mapping-queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)

price-validate:
	python3 -m src.data_update --validate-price-imports

price-preview:
	python3 -m src.data_update --preview-price-import-merge

price-apply:
	python3 -m src.data_update --apply-price-import-merge

price-refresh:
ifdef TICKERS
	python3 -m src.data_update --tickers $(TICKERS) $(if $(PROVIDER),--provider $(PROVIDER),) $(if $(REFRESH),--refresh,)
else
	python3 -m src.data_update --universe-file data/universe.csv --missing-only --max-tickers $(or $(TOP_N),25) $(if $(PROVIDER),--provider $(PROVIDER),) $(if $(REFRESH),--refresh,)
endif

price-refresh-loop:
	MAX_CANDIDATES="$(MAX_CANDIDATES)" BATCHES=$(or $(BATCHES),5) TOP_N=$(or $(TOP_N),100) PROVIDER=$(or $(PROVIDER),yahoo) SLEEP_SECONDS=$(or $(SLEEP_SECONDS),30) DRY_RUN=$(or $(DRY_RUN),0) sh scripts/price_refresh_loop.sh

price-normalize:
ifndef INPUT
	$(error INPUT is required, for example: make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual)
endif
ifdef TICKER
	python3 -m src.price_import_normalizer --input $(INPUT) --ticker $(TICKER) --source $(or $(SOURCE),generic_manual)
else
	python3 -m src.price_import_normalizer --input $(INPUT) --source $(or $(SOURCE),generic_manual)
endif

daily:
	$(MAKE) price-refresh
	$(MAKE) pipeline
	$(MAKE) monthly
	$(MAKE) track-record
	$(MAKE) validate-data
	$(MAKE) onboarding
	python3 -m src.action_queue --write-output
	python3 -m src.project_status --write-output

dashboard:
	streamlit run src/dashboard.py --client.toolbarMode viewer --server.headless true

dashboard-smoke:
	scripts/smoke_dashboard.sh

sec-stage:
ifdef TICKERS
	python3 -m src.stock_report --sec-stage-fundamentals --tickers $(TICKERS)
else
	python3 -m src.stock_report --sec-stage-fundamentals --from-local-tickers
endif

sec-validate:
	python3 -m src.stock_report --validate-imports

sec-preview:
	python3 -m src.stock_report --preview-import-merge

sec-apply:
	python3 -m src.stock_report --apply-import-merge

imports-validate:
	python3 -m src.stock_report --validate-imports

imports-preview:
	python3 -m src.stock_report --preview-import-merge

imports-apply:
	python3 -m src.stock_report --apply-import-merge

dcf-readiness:
	python3 -m src.dcf_readiness

import-fundamentals:
	python3 -m src.manual_fundamentals_import

optional-context-readiness:
	python3 -m src.optional_context_readiness

import-earnings:
	python3 -m src.manual_optional_context_import earnings

import-analyst-estimates:
	python3 -m src.manual_optional_context_import analyst_estimates

readiness:
	python3 -m src.readiness_engine

readiness-snapshot:
	python3 -m src.readiness_engine --snapshot-only

research-decisions:
	python3 -m src.research_decisions

universe-preview:
	python3 -m src.universe_builder --preview --preset sp500_smh --max-tickers 50

universe-apply:
	python3 -m src.universe_builder --write-import --preset sp500_smh --max-tickers 50
	python3 -m src.universe_builder --apply-import

universe-refresh:
	python3 -m src.universe_model

universe-report:
	python3 -m src.universe_model --report-only

universe-active:
	python3 -m src.universe_model --ensure-only
