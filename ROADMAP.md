# Roadmap

This roadmap reflects the current direction of the local Python/Streamlit stock research command center. The product principle remains:

1. Data readiness first.
2. Analysis second.
3. Research decision last.

The next phase is not to add more indicators or AI-generated summaries. The next phase should turn the product page into a shareable broad-market research workflow while continuing to prove decision-useful research through trusted fundamentals, peer metrics, earnings, and analyst estimates.

## 1. Completed Milestones

The following milestones are completed or mostly completed across the active-universe workflow and the broad-universe command-center foundation:

- [x] Readiness-first architecture.
- [x] CSV-first workflow.
- [x] Central readiness reporting.
- [x] Data-source status reporting.
- [x] Preview-first/manual import paths.
- [x] Price readiness for the current active universe.
- [x] Master-vs-active universe separation.
- [x] DCF gating.
- [x] ETF and index-proxy exclusion from operating-company DCF.
- [x] Final watchlist blocking when valuation is not ready.
- [x] Monthly picks staying empty when data is insufficient.
- [x] Dashboard smoke passing.
- [x] Test suite passing.
- [x] Broad-universe command center visibility for the current 3,538-ticker master universe.
- [x] Product-page readiness filters, row limits, and single-stock drilldown.
- [x] Peer Mapping Studio V1 with peer blocker filters and safe command cards.
- [x] Feature readiness summary and readiness-gated decision subtype reporting.
- [x] Single-stock report mode with readiness, methodology, source readiness check, DCF/peer gating, and ETF/index DCF exclusion.
- [x] Public-facing methodology documentation that explains readiness gates, fundamentals review, DCF formula path, peer boundaries, score limits, and report explanation.
- [x] Public README/dashboard polish for visitor-friendly demo paths, screenshot preview, generated-data hygiene, deep links, and research-only guardrails.
- [x] Visitor-first dashboard navigation with three main paths: review one stock, improve data coverage, and explore ready names, while detailed pages remain available under `More pages`.
- [x] Public Data Health polish with the three visitor paths before quick-read proof cards, while operator commands stay behind drawers.
- [x] Public data-strategy guidance that separates safe automation from human-reviewed source judgment.
- [x] Data Health freshness routine promoted into the beginner flow with read-only checks, capped price dry-run guidance, and review-required lanes.
- [x] Blocked single-stock reports hold peer-relative valuation behind fundamentals/DCF readiness so peer rows cannot bypass core company gates.
- [x] Readiness-gated benchmark and risk review metrics for single-stock reports and dashboard review.
- [x] Metrics lane operator queue shows page-level freshness, metric source/freshness, and proof-gate context before evidence tables or copy-only commands.
- [x] Status refresh path reuses current research-health, source, and onboarding payloads so operator status checks stay fast without weakening stale-artifact detection.
- [x] Pilot Readiness Checklist V1 with `make pilot-readiness-check`, Data Health pilot-gate cards, GitHub sync status, generated-artifact hygiene, readiness freshness, source-proof gates, proof-ledger status, public-check boundary, and research-only guardrails.
- [x] Pilot Packet Export V1 with `make pilot-readiness-packet`, `outputs/pilot_readiness_packet.md`, Data Health packet card, source-proof queue summary, latest proof outcome, manual gates, stop rules, and excluded generated-artifact list.
- [x] Pilot Reviewer Walkthrough V1 in Data Health so the operator sees pilot status, the leading manual gate, source-proof focus, packet export, and public-check boundary before raw tables.
- [x] Pilot Readiness Packaging V2 so the CLI packet and Data Health page show one reviewer handoff for share verdict, first manual gate, source-proof blocker, generated-churn boundary, and packet command before detailed pilot tables.
- [x] Pilot Handoff Accuracy V3 so `make pilot-readiness-check` and Data Health name the current leading source-proof queue and generated-churn count directly in the reviewer handoff.
- [x] Pilot Commit Package Handoff V1 so `make pilot-readiness-check` and Data Health print copy-only product staging, staged-hygiene, commit, and generated-churn exclusion steps before pilot sharing.
- [x] Pilot Commit Package Exclusion Clarity V2 so the pilot handoff names broad generated patterns like `data/*.csv`, `data/reports/*.csv`, and `outputs/*.csv` before staging.
- [x] Pilot Packet Exclusion Policy V2 so the reviewer packet separates broad generated-exclusion patterns from the currently dirty generated artifact list.
- [x] Data Health Visual Density V2 with a compact pilot workflow strip, collapsed pilot gate details, tighter first-screen hierarchy, and preserved copy-only proof controls.
- [x] Public Mode First-30-Seconds Polish V1 so visitors see ready coverage, blocked deeper-analysis inputs, and proof boundaries before operator paths or evidence drawers.
- [x] Operator Next Action Summary V1 so Data Health answers pilot status, main manual gate, leading source-proof blocker, and hidden-detail boundary before raw tables.
- [x] Coverage Summary Answer Contract V2 so Data Health gives one clear lane answer, blocker reason, proof-to-unlock, and stop rule before source-proof drawers, operator commands, or raw tables.
- [x] Browser QA Evidence V1 with `make browser-qa-evidence`, committed screenshot asset checks, route expectations, and environment-limited capture notes for GitHub/LinkedIn evidence.
- [x] Pilot Screenshot Capture Closeout V1 so pending real-app captures print route, first-view markers, save path, verify command, and reviewed-asset staging command without generating fake thumbnails.
- [x] Browser QA Evidence V2 with route-level manual checks for public home, single-stock, Data Health fast view, metrics review, and proof history before replacing public screenshots.
- [x] Browser Evidence Capture Plan V2 with a copy-ready session sequence for starting the dashboard, capturing pending real screenshots, verifying assets, running release gates, and staging only reviewed evidence.
- [x] Browser QA Marker Alignment V3 so the single-stock screenshot checklist expects the selected-ticker contract, report handoff, and stop rule now shown on the first viewport.
- [x] Browser Evidence Staging Command V3 so the screenshot capture plan prints the exact reviewed-asset `git add -- ...` command without including generated CSV/report churn.
- [x] Browser QA Reviewed Asset JSON V1 so automation and reviewer packets expose the exact reviewed screenshot asset staging command without including generated CSV/report churn.
- [x] Public Release Screenshot Handoff V1 so `make public-release-handoff` also prints the reviewed screenshot asset staging command after visual review.
- [x] Public Screenshot Recommendation V1 so `make browser-qa-evidence` names the current LinkedIn/GitHub image, pending workflow captures, and the boundary that screenshots do not prove data freshness or unlock blocked inputs.
- [x] Pilot Screenshot Evidence Gate V1 so `make pilot-readiness-check` includes real screenshot evidence status and pending workflow captures alongside sync, churn, source-proof, public-check, and research-only gates.
- [x] Pilot Evidence Review V1 so Data Health puts screenshot evidence, reviewer packet, public-check boundary, generated-churn policy, and leading source-proof blocker in one compact strip before detailed pilot tables.
- [x] Public Share Final Gate V1 so Data Health combines GitHub sync, public-check, browser QA evidence, generated-churn exclusion, pilot packet, and research-only boundary before GitHub or LinkedIn sharing.
- [x] Source Activation Console V2 so `make session-source-preflight`, `make project-status`, and `make provider-setup-checklist` separate free public sources, keyed free-tier setup, optional broker-disabled paths, last-tried source state, do-not-retry guidance, smoke commands, and the next executable lane before any broad coverage loop.
- [x] Data Health Workflow Continuity V4 so the operator sees one path from pilot evidence to final share gate, next action, queue route map, proof lane, artifact hygiene, and reviewer packet before raw tables.
- [x] Pilot Operator Runbook V1 so Data Health connects share gate, source gate, provider setup, reviewed one-provider smoke, validate/preview, packet, and hygiene without reopening broad proof loops.
- [x] Public Release Package V1 with `make public-release-package`, a read-only product staging, generated-churn exclusion, final-check, commit, and push checklist.
- [x] Short Price-History Proof Queue V1 with `make price-history-proof-queue`, separating complete price coverage from short-history blockers for momentum, track-record, and review-metric workflows.
- [x] Workflow Continuity V3 so Home, Single-Stock Report, and Data Health strip links route to the current page, proof drawer, next safe view, and stop-rule evidence without running commands.
- [x] Single-Stock Pre-Report Stop Rule V1 so the selected-ticker contract shows the report loop, matching Data Health lane, and stop rule before opening details.
- [x] Public README Flow Compression V1 so the visitor README stays compact while preserving pilot gates, generated-churn exclusions, and research-only boundaries.
- [x] Data Health Fast-View Stabilization V1 so deep links render the operator command center before broad proof queues, pilot gates, generated-artifact tables, or raw evidence drawers are opened.
- [x] Data Health Queue Detail Gate V1 so `drawer=queue` and the Prices lane stay fast while source-proof portfolios load only through explicit review-detail gates.
- [x] Data Coverage Proof Queue Performance V2 so broad proof queues reuse DCF blocker rows and avoid duplicate share-count readiness rebuilds.
- [x] Local Price Provider Cache V1 so metric-readiness and single-stock review paths reuse prepared local price rows instead of repeatedly normalizing the full prices CSV.
- [x] Readiness Queue Performance V3 so queue-specific CLI routes avoid prebuilding unrelated frontier views, share-count lanes reuse DCF blocker rows, and local provider lookups reuse ticker rows for financial and peer context.
- [x] Proof Lane Progressive Load UX V2 so Proof History shows deferred, loading, stale, warning, and loaded states before proof ledgers, packet details, or command builders render.
- [x] Data Health Drawer Routing V2 so readiness queue lanes expose navigation-only routes from lane drawer to source proof, comparison, proof record, and artifact hygiene without running commands.
- [x] Public Visitor Workflow Polish V3 so the GitHub/LinkedIn path starts browser-first, keeps examples as readiness states, and moves terminal proof commands into optional local checks.
- [x] Single-Stock Workflow Fit V3 so loaded ticker reports show selected state, reviewable sections, blocked/excluded lanes, Data Health handoff, and stop rule before detailed report sections.
- [x] Public Visitor Workflow Polish V4 so Home starts with a First 30 Seconds explanation before workflow examples or operator details.
- [x] Public Visitor Flow V5 so Home replaces repeated visitor blocks with a Connected Workflow map plus the research-loop strip before deeper examples.
- [x] Single-Stock Workflow Fit V5 so the selected ticker shows a pre-report readiness contract before raw coverage details or loaded report sections.
- [x] Data Health Operator Flow V4 so each queue lane starts with a compact where-am-I, previous-proof, next-action, and stop-rule strip before detailed route/action tables.
- [x] Trusted Fundamentals Proof Loop UX V3 so the DCF source loop shows current gate, reviewed evidence status, next safe action, and proof-record stop rule before detailed source tables.
- [x] Dashboard helper extraction V3 so the Single-Stock pre-report readiness contract lives in a tested workflow module instead of the Streamlit render body.
- [x] Single-Stock Workflow Fit V4 so both the drilldown and loaded report show current step, previous proof, next safe action, and stop rule before dense details.
- [x] Data Health Drawer Routing V3 so queue lane drawers summarize queue -> source proof -> comparison -> proof record routes before detailed action tables.
- [x] Public Visitor Workflow Polish V6 so Home opens with the research-loop strip, First 30 Seconds, Connected Workflow, and Visitor Path before heavier examples or operator details.
- [x] Single-Stock Workflow Fit V6 so loaded ticker workflow cards stay readable while copy-only commands move into a collapsed command drawer.
- [x] Single-Stock to Data Health Handoff V6 so loaded ticker reports show a compact route-focused handoff to the matching Data Health lane or proof drawer before Quick Read and raw detail.
- [x] Data Health Operator Flow V5 so queue lane route cards include generated-artifact hygiene before staging recommendations.
- [x] Trusted Fundamentals Proof Loop UX V3 so DCF source review shows source fields -> guard -> validate/preview -> apply/skip -> proof-record route cards before source tables.
- [x] Trusted Fundamentals Proof Loop UX V4 so the DCF evidence drawer starts with an operator summary of selected blocker family, current gate, guard/proof status, next safe action, and stop rule before lower source tables.
- [x] Trusted Fundamentals Evidence Writer Extraction V1 so dry-run preview and apply/skip gate logic live in a focused tested helper while Data Health remains the renderer.
- [x] DCF Input Family Helper Extraction V1 so proof-family filtering, DCF input row conversion, and filter cards live in a focused tested helper while Data Health keeps source-proof rows collapsed.
- [x] DCF Source Packet Extraction V1 so source-route grouping, capped fundamentals batch review, and DCF proof batch planner cards live in a focused tested helper while Data Health keeps commands copy-only and collapsed.
- [x] DCF Import Preview Extraction V1 so guard, preview-row, validate, preview, apply-boundary, and post-proof table logic live in a focused tested helper while Data Health remains copy-only.
- [x] Metric Readiness Console Extraction V1 so SPY/QQQ metric blocker summaries and progressive metric/proof detail gates live in a focused tested helper while Data Health keeps row-level details deferred.
- [x] Data Health Proof Loop UI Fit V1 so DCF and peer drawers share a compact status, blocker, next-proof, evidence, and stop-rule summary before detailed proof tables.
- [x] Public Visitor Flow V6 so Home shows the route choice before optional workflow detail, keeping repeated workflow and next-step cards collapsed for first-time visitors.
- [x] Single-Stock Pre-Report Handoff V1 so the selected ticker contract tells users to open the local report first, then route locked sections to the matching Data Health lane.
- [x] Data Health Progressive Detail Copy V1 so queue, batch, metrics, and proof controls use operator-friendly "open review details" language instead of internal load/switch wording.
- [x] Research Loop Helper Extraction V1 so Home, Single-Stock, and Data Health loop-strip contexts live in a focused tested module while Streamlit stays the rendering layer.
- [x] Peer Proof Operator Summary V1 so the peer evidence drawer starts with selected scope, current source-review gate, latest ledger status, next safe action, and stop rule before lower peer source/proof tables.
- [x] Peer Proof Operator Summary Extraction V1 so the peer first-read summary logic lives in a focused tested helper while Streamlit remains the rendering layer.
- [x] Data Coverage Proof Queue Summary Extraction V1 so post-price readiness queue cards and DCF, shares, fundamentals, peer mapping, and peer valuation proof queue cards live in a focused tested helper while Data Health keeps raw proof rows collapsed.
- [x] Universe Scope Guide V1 so market-wide review starts with master vs active vs analysis-ready counts, safe row-limited filters, single-stock lookup boundaries, and the no broad-conclusions stop rule before the Readiness Explorer.
- [x] Risk Context Workflow Extraction V1 so liquidity/correlation readiness and volatility-proxy approximation cards live in a focused tested helper while Data Health keeps raw risk tables collapsed.
- [x] Data Health Command Visibility Sweep V1 so Proof History, Operator context, and Pilot Share Gate detail summaries hide command snippets by default while detailed tables and the explicit packet command table remains available only inside opened review drawers.

## 2. Current Product State

The product is usable today for price, momentum, and market-direction monitoring across the current active universe and a growing analysis-ready subset of the broad master universe.

The product is partially decision-useful for DCF-ready company research, but peer-relative analysis, earnings context, and analyst-estimate context remain blocked for most tickers because trusted source data is missing or incomplete. This is expected and correct: the system should not promote conclusions when the underlying data is not ready.

Current readiness pattern:

- Master universe rows: 3,538.
- Active research rows: 12.
- Price, momentum, liquidity, and correlation coverage can improve through capped local refresh/import workflows.
- Fundamentals and DCF coverage remain limited to trusted local/SEC-backed rows.
- Peer readiness remains intentionally sparse until source-backed peer mappings and peer inputs are imported.
- Earnings and analyst estimates remain locked until trusted local or reviewed provider-assisted CSV rows are imported.
- Decision buckets remain readiness-gated: incomplete rows stay `Blocked by Data` or `Monitor` rather than becoming recommendations.

Use `make status-check TOP_N=5`, `make readiness`, or the dashboard Home page for exact current local counts.

The product correctly withholds unavailable conclusions. The next improvement is product-page workflow clarity plus trusted data ingestion, not more indicators.

### Controlled Pilot Stage Gate

Current stage verdict: trusted-data pilot, ready to enter a controlled external pilot with manual gates.

Pilot entry criteria:

- `make pilot-readiness-check TOP_N=10` returns `pilot-ready with manual gates` or better.
- `make public-check`, `make browser-qa-evidence`, `make public-wording-check`, `make diff-hygiene`, and `git diff --check` pass in the target environment.
- The pilot operator follows `docs/PILOT_RUNBOOK.md`.
- Generated CSV/JSON/report churn is excluded unless the exact artifact is reviewed pilot evidence.
- Source-proof lanes keep `ready`, `partial`, `blocked`, `excluded`, `supported`, `candidate_context_only`, `still_blocked`, and `skipped` states visible.

Pilot exit criteria:

- 5 to 10 selected operating-company packets have recorded outcomes: `supported`, `candidate_context_only`, `still_blocked`, `skipped`, or `excluded`.
- Any supported lane has source proof, validation, preview, rejected-row review, apply or skip decision, rebuilt readiness, regenerated report, and proof-ledger evidence.
- Operators can complete one full reviewed source-proof slice from dashboard, runbook, CLI packet, proof comparison, and proof ledger without guessing the next gate.
- Remaining blockers are trusted-source, provider, licensing, or owner-decision constraints rather than product-code or documentation gaps.

Immediate pilot priorities:

1. Provider setup/source-boundary review: run `make provider-setup-checklist` when current source-proof queues have no unreviewed executable company candidates. Use it to confirm which free public, keyed free-tier, optional broker-disabled, and locked/manual sources can truthfully unlock the next coverage stage. After adding a key, run only that provider's reviewed one-ticker smoke command before any broader batch; smoke commands still require validate, preview, rejected-row review, and an intentional apply decision.
2. Run `make trusted-data-pilot-candidates TOP_N=10` only after `make project-status` or `make coverage-frontier TOP_N=10` shows new provider data, keyed sources, reviewed manual rows, new tickers, or changed blockers.
3. Close one reviewed source-proof lane at a time, starting with the top executable DCF/share-count/peer blocker.
4. Keep the pilot package clean: reviewed docs/code/evidence only, broad generated churn excluded by default.

Post-pilot priorities:

- Increase trusted fundamentals, share-count, and source-backed peer coverage.
- Improve optional earnings and analyst-estimate lanes only after trusted local or reviewed provider-assisted rows exist.
- Continue extracting dashboard logic into tested helpers where it reduces operator risk.

Launch-readiness priorities:

- Choose a license before describing the repository as open source.
- Confirm dashboard smoke and public checks in a normal local shell.
- Publish only reviewed data/evidence artifacts, not broad generated refresh churn.

Do not build before pilot:

- Broker connections, order routing, auto-trading, or account actions.
- AI-generated recommendations or unsupported rankings.
- Placeholder fundamentals, peers, earnings, estimates, valuation inputs, or metrics.
- More indicators that do not improve data readiness, evidence, or operator clarity.

## 3. Product-Page Roadmap

Goal: turn the Streamlit page into a research command center instead of a collection of CSV tables.

- Keep the top-level page focused on readiness, blockers, next actions, and single-stock drilldowns.
- Group next actions by feature:
  - Price Coverage Batch
  - Fundamentals / DCF Proof
  - Peer Mapping Proof
  - Peer Valuation Inputs Proof
  - Earnings Import Setup
  - Analyst Estimates Import Setup
  - Single-Stock Review
- Keep dashboard commands copyable only; do not run imports, refreshes, or account actions from the product page.
- Keep broad-universe tables row-limited by default.
- Add source readiness notes wherever an action depends on local CSVs, staged import files, Yahoo price refresh, SEC staging, or manual trusted inputs.
- [x] Add source readiness context to `project_status_next_steps.csv`, `make project-status`, and dashboard next-action cards.
- [x] Make active-universe vs master-universe language visible wherever counts differ.

### Data Readiness Operations Center V1

Goal: choose broad data-readiness lanes before drilling into individual tickers.

- [x] Add a read-only lane operations command with `make readiness-ops-center`.
- [x] Add a coverage frontier command with `make coverage-frontier TOP_N=10`.
- [x] Add a data coverage expansion planner with `make data-coverage-planner TOP_N=10` so frontier lanes become repeatable dry-run, proof, stop-condition, and churn gates without changing data.
- [x] Add a coverage expansion execution loop with `make coverage-expansion-loop TOP_N=10` so the next lane flows through preflight, reviewed packet, dry-run, comparison, proof-record preview, and hygiene before any data-changing step.
- [x] Add a compact lane readiness board inside `make coverage-expansion-loop` so operators can see the selected lane, locked/manual lanes, excluded states, and proof boundary without opening every planner output.
- [x] Add a source-proof intake checklist inside `make coverage-expansion-loop` so each selected lane names acceptable evidence, rejected shortcuts, review commands, and the exact proof-ready boundary before any CSV rows change.
- [x] Surface the coverage expansion loop in Data Health so the operator sees the compact planner -> preflight -> packet -> proof path before detailed workflow tables.
- [x] Keep price coverage, fundamentals/DCF, peer mapping, peer valuation inputs, locked earnings, locked analyst estimates, and excluded/not-applicable states separate.
- [x] Show batch next actions and generated-churn policies in Data Health before detailed ticker tables.
- [x] Add a reviewed-batch ladder in Data Health so frontier lanes become packet, dry-run, proof, and hygiene steps.
- Keep frontier ranks framed as data operations impact, not security attractiveness or investment recommendation.

### Reviewed Batch Execution V1

Goal: turn a selected coverage-frontier lane into a safe reviewed run packet.

- [x] Add `DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10` for packet preview before intentionally writing reviewed batch artifacts.
- [x] Write `outputs/reviewed_batch_packet.md` and `outputs/reviewed_batch_packet.csv`.
- [x] Include snapshot, dry-run, capped execution, validate/preview/apply gates, post-run proof, expected artifacts, rollback, and proof-row template.
- [x] Warn when saved readiness artifacts are missing or stale before relying on counts.
- [x] Add Reviewed Batch Execution UX V2 in Data Health so operators choose one lane, see source/freshness gates, and open the full copy-only sequence without inspecting raw CSV tables first.
- [x] Add Readiness Batch Proof Ledger UX V1 in Data Health so Proof History starts with latest packet, comparison status, and proof-record scaffold before raw ledgers.
- [x] Add Reviewed Batch Snapshot Gate V1 in Data Health so missing baseline snapshots block packet/dry-run/proof work with a copy-only `make readiness-snapshot` step.
- [x] Add Reviewed Batch Apply Guard V1 in Data Health so mutating lanes stop at validate, preview, rejected-row review, and apply decision before any supported outcome.
- [x] Add Reviewed Batch Outcome Recorder V1 in Data Health so the proof drawer shows missing validation, preview, apply, changed-readiness, source-file, and artifact-review fields before recording an outcome.
- [x] Add Reviewed Batch Proof Record Command UX V1 so the proof drawer builds a copy-ready `make reviewed-batch-proof-record ...` command with reviewed values filled and unresolved fields left visible.
- [x] Extract reviewed-batch proof command-builder rules from the Streamlit dashboard into a focused module with direct tests.
- [x] Add Reviewed Batch Proof Record Validation V1 so proof commands show ready, needs-field-fills, snapshot-blocked, or invalid-outcome status before recording.
- [x] Add Reviewed Batch Ledger Record Safety V1 so `reviewed-batch-proof-record` can dry-run the exact ledger row and validation status before appending.
- [x] Add Reviewed Batch Loop Map V1 so Data Health shows snapshot -> reviewed packet/dry run -> validate/preview/apply gate -> proof record -> before/after comparison before the detailed drawer.
- [x] Add Readiness Coverage Delta Board V1 so Data Health summarizes prior/current lane deltas, still-blocked lanes, latest proof outcomes, and generated-artifact review status before raw CSV reports.
- [x] Add Generated Churn Review Drawer V1 so Data Health classifies dirty generated CSV/report artifacts as excluded by default versus reviewed evidence before staging.
- [x] Add Decision Proof Queue UI V2 so Data Health shows a completion checklist, freshness, top proof row, reviewable inputs, locked context, copy-only command, and post-unlock proof before raw decision rows.
- [x] Add Reviewed Batch Execution Checklist V2 so the reviewed-batch drawer shows lane choice, source/freshness warnings, packet, capped preview, validate/preview/apply gate, before/after comparison, proof outcome, and artifact hygiene before detailed tables.
- [x] Add first-class `share_count` reviewed-batch packets and preflight commands so shares-outstanding DCF blockers no longer fall back to generic fundamentals wording.
- [x] Add DCF Input Proof Queue UX in Data Health so top input families, source-review fields, import preview, proof packet handoff, stop rules, and latest proof outcome stay in one collapsed drawer before raw DCF tables.
- [x] Add DCF Proof Source Review Compact Checklist V1 so the DCF drawer shows missing source fields, import guard status, proof-record placeholders, and latest ledger outcome before detailed tables.
- [x] Add Trusted Fundamentals Source Packet UX so the DCF drawer separates SEC-stageable, trusted-local/manual, and price dry-run source routes before detailed import scaffolds.
- [x] Add Trusted Fundamentals Batch Review Queue UX so source packets become capped SEC-stageable, trusted-local/manual, or price dry-run review batches with validation, rejected-row, proof-record, and stop-rule gates.
- [x] Add Data Health Proof Checklist Summary V1 so DCF and peer proof-checklist status appears near the top of the operator page before detailed source/proof drawers.
- [x] Add DCF Proof Batch Planner V1 so the DCF drawer turns the top blocker family into one capped source-proof plan with packet, validation, proof-record, and stop-rule gates before detailed rows.
- [x] Add Proof Planner Outcome Summary V1 so Data Health compares DCF and peer planner states before opening lane-specific proof drawers.
- [x] Add Planner Summary Interaction V1 so proof planner summary cards include lane jump URLs and copy cues before detailed drawers are opened.
- [x] Add Proof Planner Drawer Auto-Context V1 so DCF and peer lanes show a "you came here for" proof-planning cue before their evidence drawers.
- [x] Add DCF Input Proof Queue Dashboard UX V1 so the Fundamentals / DCF lane shows top input families, next proof command, proof packet command, and stop rule before raw queue rows.
- [x] Add DCF Source Review Completion UX V1 so the DCF checklist card shows exact missing fields, next safest action, and stop rule before source-review tables.
- [x] Add DCF Source Review Command Builder V1 so source-review, guard, validate, preview, apply boundary, rebuild proof, and proof handoff commands appear before raw source-review tables.
- [x] Add DCF Source Review Outcome Triage V1 so blocked source fields, guard-ready steps, apply boundary, and proof handoff status appear before command details.
- [x] Add DCF Source Review Batch Selector V1 so a capped source-review scope and command-plan command appear before raw queue rows.
- [x] Add DCF Source Review Evidence Intake V1 so reviewer evidence fields appear before import-row scaffolds or proof-record outcomes.
- [x] Add DCF Source Review Guard Readiness V1 so selected evidence shows guard-ready, missing-field, or stop status before guard commands.
- [x] Add DCF Source Review Guard Preview V1 so guard-ready rows show the exact guard command, validate/preview gates, apply boundary, and post-guard proof before import-preview tables.
- [x] Add DCF Source Proof Handoff V2 so guard preview rows show proof-record dry-run fields, validation/preview boundaries, artifact review, and stop rules before lower source tables.
- [x] Add DCF Proof Ledger Outcome Compare V1 so source proof, before/after readiness comparison, and latest ledger outcome appear together before lower source tables.
- [x] Add DCF Proof Outcome Closeout V1 so supported, candidate-context-only, still-blocked, skipped, or excluded closeout status and remaining evidence gates appear before lower source tables.
- [x] Add Proof Closeout Summary Board V1 so DCF and peer closeout states appear side by side before opening lane-specific evidence drawers.
- [x] Add Proof Planner Stale-State CTA V1 so stale or missing readiness artifacts show one refresh-first CTA before DCF/peer proof-planning language.
- [x] Extract DCF/peer proof CTA card builders from the Streamlit dashboard into a focused tested module.
- [x] Extract DCF source command-plan card/frame helpers from the Streamlit dashboard into a focused tested module.
- [x] Extract proof planner outcome summary logic from the Streamlit dashboard into a focused tested module.
- [x] Extract generic DCF/peer proof outcome card logic from the Streamlit dashboard into a focused tested module.
- [x] Extract DCF/peer latest proof-ledger row selection from the Streamlit dashboard into a focused tested module.
- [x] Extract latest proof-ledger status/detail formatting from the Streamlit dashboard into a focused tested module.
- [x] Extract generic DCF/peer proof closeout state logic from the Streamlit dashboard into a focused tested module.
- [x] Extract proof closeout summary board logic from the Streamlit dashboard into a focused tested module.
- [x] Extract proof checklist summary logic from the Streamlit dashboard into a focused tested module.
- [x] Extract readiness queue outcome summary card logic from the Streamlit dashboard into a focused tested module.
- [x] Extract generated churn review drawer logic from the Streamlit dashboard into a focused tested module.
- [x] Extract readiness coverage delta board logic from the Streamlit dashboard into a focused tested module.
- [x] Extract readiness recent-progress card logic from the Streamlit dashboard into a focused tested module.
- [x] Extract readiness summary counting logic from the Streamlit dashboard into a focused tested module.
- [x] Extract market-wide readiness summary wrapper from the Streamlit dashboard into a focused tested module.
- [x] Extract feature readiness card logic from the Streamlit dashboard into a focused tested module.
- [x] Extract peer readiness product card logic from the Streamlit dashboard into a focused tested module.
- [x] Extract peer mapping studio summary card logic from the Streamlit dashboard into a focused tested module.
- [x] Extract peer analysis boundary card logic from the Streamlit dashboard into a focused tested module.
- [x] Extract peer function quality table logic from the Streamlit dashboard into a focused tested module.
- [x] Extract peer unlock operator card logic from the Streamlit dashboard into a focused tested module.
- Keep generated packet artifacts reviewed separately; do not commit broad data refresh churn by default.

### Trusted Coverage Growth V2

Goal: make coverage growth proof-backed at the lane level before any ticker-level analysis changes.

- [x] Surface peer sub-state readiness in operations views: peer mapping, peer price, peer momentum, peer fundamentals, peer valuation, and peer valuation comparison.
- [x] Expand reviewed-batch packets with before/after proof fields for changed readiness counts, changed tickers, reviewed artifacts, and final outcome.
- [x] Add Data Health peer-readiness cards so peer trend and peer valuation gates stay visibly separate.
- [x] Add Peer Source-Review Intake in Data Health so operators see fillable source-proof fields before editing peer import rows.
- [x] Add Peer Source-Review Completion UX so placeholder fields, stale readiness, and import-row scaffold boundaries stay visible before peer CSV edits.
- [x] Add Peer Source-Review Import Preview UX so completion-ready rows show the exact import CSV header/row, validate-preview command, apply boundary, and post-apply proof.
- [x] Add Peer Source-Review Write-Back Guard V1 so reviewed peer rows are checked for placeholders, stale readiness, self-peers, and duplicate pairs before any copy/paste into the peer import file.
- [x] Add Peer Source-Review Ledger Handoff V1 so the write-back guard prints a dry-run reviewed-batch proof-record scaffold and the still-missing review fields before any supported outcome can be recorded.
- [x] Add Peer Proof-Loop Outcome UX in Data Health so source-review, write-back guard, validate/preview/rebuild, proof-record scaffold, and latest peer proof ledger outcome appear before raw peer tables.
- [x] Add Peer Proof Completion Checklist V1 so the peer drawer shows freshness, missing source fields, write-back guard status, proof-record readiness, and latest ledger outcome before detailed tables.
- [x] Add Peer Proof Batch Planner V1 so the peer drawer turns source-review rows into a capped source-proof plan with reviewed-batch packet, write-back guard, validation, proof-record, and stop-rule gates before raw peer tables.
- [x] Add Peer Proof Closeout Parity V1 so peer proof comparison, supported/candidate-context-only/still-blocked/skipped/excluded closeout status, and remaining evidence gates mirror the DCF closeout flow.
- Keep proof-ledger rows local and reviewable; do not claim a supported lane until source proof, validation, preview, rejected-row review, post-run readiness, and artifact hygiene are complete.

### Readiness-Gated Review Metrics V1

Goal: add useful benchmark, risk, fundamentals, valuation, and peer context without turning missing inputs into conclusions.

- [x] Add `make benchmark-risk-review TICKER=<ticker> BENCHMARK=SPY`.
- [x] Add `make metric-readiness` as an alias for the same read-only review path.
- [x] Calculate benchmark-relative return, max drawdown, rolling volatility, beta, Sharpe, and Sortino only from local price history.
- [x] Support SPY and QQQ benchmark choices when local benchmark rows exist.
- [x] Show partial/blocked states when benchmark history is missing or too short.
- [x] Label Sharpe and Sortino as historical review metrics, not recommendations.
- [x] Keep fundamentals trend partial unless multiple trusted fundamentals periods exist.
- [x] Keep valuation multiples blocked unless trusted fundamentals plus market-cap or price/share-count context exist.
- [x] Keep peer valuation dispersion blocked unless mapped peers have trusted valuation inputs.
- [x] Surface the metrics in single-stock Markdown reports and the dashboard Snapshot tab.
- [x] Add a central `make metric-readiness TOP_N=10` summary with explicit readiness freshness context.
- [x] Refine the dashboard metrics section from raw table-first output into summary cards plus an optional details table.
- [x] Add configurable risk-free-rate defaults in project config while keeping the assumption visible in report output.

Next improvements:

- [x] Add richer multi-period fundamentals trend only when trusted historical rows are available.
- [x] Add a read-only share-count proof queue for DCF blockers where `shares_outstanding` is the gating input.

## 4. Trusted Data Proof Roadmap

### A. Trusted Fundamentals Ingestion

Goal: prove fundamentals readiness without fabricating company data.

- Configure `SEC_USER_AGENT`.
- Run SEC staging for active company tickers.
- Or support trusted manual fundamentals import through existing validate/preview/apply workflows.
- Validate required fields:
  - `revenue`
  - `free_cash_flow`
  - `fcf_margin`
  - `shares_outstanding`
- Generate or update `fundamentals_coverage_report.csv`.
- Continue improving `fundamentals_ready` from the original trusted-data baseline of 23/3,538; current live status should be checked with `make project-status` before quoting coverage.

Acceptance notes:

- SEC staging should remain preview-first and reviewable.
- Manual imports must be source-backed.
- Shares outstanding should stay blocked unless SEC/manual source proof or a trusted local row verifies it; do not infer it from price, market cap, or peers.
- Invalid rows must be rejected into CSV reports instead of silently dropped.

### B. DCF Readiness Proof

Goal: allow valuation conclusions only when DCF data is genuinely ready.

- Keep ETFs and index proxies excluded from operating-company DCF.
- Do not generate undervalued or overvalued conclusions for `not_ready` tickers.
- Improve `dcf_readiness_report.csv`.
- Only allow valuation conclusions for DCF-ready companies.
- Keep missing fields explicit per ticker.

Acceptance notes:

- `undervalued_candidates.csv` must keep `valuation_status=not_ready` for incomplete rows.
- DCF-ready companies must have trusted price and fundamentals inputs.
- DCF logic should remain transparent and conservative.

### C. Peer Readiness Proof

Goal: support peer analysis without pretending peer valuation is available when only partial peer data exists.

- Add source-backed peer mappings.
- Add mapped-peer price, fundamentals, market cap, and valuation inputs when mappings already exist.
- Separate readiness into:
  - `peer_price_ready`
  - `peer_momentum_ready`
  - `peer_fundamentals_ready`
  - `peer_valuation_ready`
- Do not require valuation readiness for peer trend comparison.
- Do not show peer valuation if peer valuation inputs are missing.

Acceptance notes:

- Peer relationships must be source-backed or transparently labeled as sector/industry fallback.
- Peer trend comparison may use price/momentum readiness.
- Peer valuation requires valuation inputs and should remain blocked when metrics are missing.

### D. Decision-Bucket Refinement

Goal: improve decisions so they are more informative than generic monitoring rows.

Baseline issue: the system previously produced generic `Monitor` decisions when price data was ready but core company research data was blocked. Recent work has started separating company data blockers from ETF monitoring, but the roadmap should continue refining this into durable reason codes and sub-buckets.

Add reason codes or sub-buckets:

- [x] `Monitor - Price/Momentum Ready`
- [x] `Monitor - ETF Market Proxy`
- [x] `Blocked by Data - Missing Fundamentals`
- [x] `Blocked by Data - Missing Peer Mapping`
- [x] `Excluded - DCF Not Applicable`
- [x] Add `DRY_RUN=1 make decision-proof-queue` so refined decision rows can be previewed as a compact, freshness-gated proof queue with what can be reviewed now, what stays locked, copy-only local commands, and post-unlock proof steps before intentionally writing queue artifacts.
- [x] Surface the Decision Proof Queue in Data Health as a compact operator drawer with freshness status, top proof row, what can be reviewed now, what stays locked, copy-only command, and post-unlock proof step before raw rows.

Rules:

- `Research Now` cannot be assigned when critical data is missing.
- Company tickers with missing fundamentals or DCF inputs should not be treated as generic monitor candidates.
- ETFs can remain monitor candidates for market/risk use while staying excluded from company DCF.

## 5. P1 Roadmap

### A. Portfolio/Risk Completeness

Goal: clarify risk readiness and reduce avoidable warnings.

- [x] Classify missing sector/theme ETF OHLCV, such as `ARKF`, as optional benchmark/proxy context rather than a core ticker price blocker.
- Continue improving liquidity/correlation readiness from the original broad baseline of 232/3,538 where appropriate; current live counts should be checked with `make risk-context`.
- [x] Add ATR versus volatility-proxy provenance to momentum outputs, dashboard cards, monthly-pick reasons, and stock-report Markdown.
- [x] Surface liquidity, correlation, and proxy-risk readiness cards in Data Health before detailed tables.
- Keep proxy-based risk notes clearly labeled as approximations in generated outputs after the next pipeline/report refresh.

### B. Single-Stock Research Mode V2

Goal: keep improving the already implemented single-ticker report so it is the clearest product surface for stock evaluation.

Current status:

- `make stock-report-md TICKER=...` generates clean Markdown reports for visitor demos.
- `make stock-report TICKER=...` remains available when optional report data is useful for inspection.
- The dashboard includes a Single-Stock Report page and local deep links such as `?page=single-stock-report`.
- Reports show readiness, Evaluation Snapshot, Proof Checklist, Best Review Path, analysis quality, methodology, evaluation function checks, valuation status, research decision, source readiness check, blocked inputs, and next research steps.
- ETF/index/fund reports show operating-company DCF as excluded, not failed.
- Reports now open with a visitor scan cue, then `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, and `Best Review Path` so first-time visitors see mode, decision view, DCF state, peer context, optional context, data-confidence cue, proof step, and next local step before methodology detail.
- The dashboard Single-Stock Report page includes At A Glance and Best Review Path cards, while Markdown reports include an Evaluation Snapshot explaining supported evaluation, valuation boundary, data-confidence cue, next proof, and stop rule before detailed sections.
- Reports include a mode guide comparing `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, and `Data needed before analysis`.
- Blocked and partial reports include `Copyable Proof Commands` with capped, local, research-only commands for price, fundamentals/DCF, peer mapping, optional-context imports, and the one-company trusted-data pilot packet.
- Reports flag caveated peer-relative context in At A Glance when trusted peers exist but mapped-peer valuation metrics are incomplete.

Next improvements:

- [x] Add more visible examples of richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data reports on the dashboard Home page.
- [x] Link Data Health and blocked single-stock reports to `make trusted-data-pilot-packet TICKER=<ticker>` so the trusted-data pilot has one consistent before/report, review, validate/preview gate, apply boundary, and rebuild-proof path.
- Keep methodology and assumptions visible while continuing to reduce engineer-heavy wording.

Rules:

- Must stay data-honest.
- Must show blocked, partial, ready, and excluded states.
- Must not fabricate missing fundamentals, earnings, analyst estimates, peers, or valuation inputs.
- Must not produce buy/sell instructions.

### C. Market-Wide Universe Layer

Goal: support broader universe management without forcing expensive full-market analysis on dashboard load.

- [x] Keep master-universe rows separate from active research rows in readiness and dashboard workflows.
- [x] Keep active-universe review as the recommended first scope before broad master-universe rows.
- [x] Allow single-stock lookup outside the active universe without forcing full-market analysis.
- [x] Avoid full-market analysis on dashboard load by keeping broad views row-limited, lazy, and gated behind scope choices.
- [x] Support lazy/scoped analysis with `make universe-scope TOP_N=10` and Data Health scope cards.
- [x] Support active-universe, ticker-list, sector/theme, ready-only, and missing-data scopes.
- [x] Keep risk context behind scope selection with `make risk-context`, so liquidity, correlation, and proxy-risk rows stay historical context rather than research conclusions.

Acceptance notes:

- `make universe-scope TOP_N=10` should remain read-only and copy-only; it must not refresh, import, apply, stage, or infer missing values.
- `make risk-context` should continue to tell operators to choose scope first and keep short price-history blockers visible.
- When source-proof queues are exhausted, `make project-status` should route operators to `make provider-setup-checklist` before reopening broad trusted-data candidate loops.
- Master-universe coverage should stay framed as coverage planning, not proof that every analysis surface is ready.

## 6. P2 Roadmap

Goal: add trusted optional context workflows after fundamentals/DCF/peer readiness is no longer the main blocker.

- [x] Trusted earnings import.
- [x] Trusted analyst estimates import.
- [x] Dashboard unavailable states when no trusted rows exist.
- [x] Rejected-row reporting.
- [x] Read-only optional-context summary before writing readiness CSVs.
- [x] Readiness reports for earnings and analyst estimates.

Rules:

- Earnings and analyst estimates are manual/trusted-local only until a provider interface is deliberately added.
- Empty trusted rows should render as unavailable, not as conclusions.
- Analyst consensus must not be treated as a recommendation.

## 7. Deprioritized Items

The following are intentionally deprioritized:

- More indicators.
- AI-generated recommendations.
- Monthly picks.
- Full-market ranking.
- Complex DCF model tuning.
- Additional dashboard charts.

Reason: the blocker is not the lack of indicators. The blocker is missing trusted data for fundamentals, peers, earnings, and analyst estimates.

## 8. Next Public Roadmap Stage

Goal: turn the public project into a usable research workflow while the data universe grows through safe, reviewable proof steps.

This stage should improve breadth without pretending the whole 3,538-ticker universe is analysis-ready. It should favor capped refreshes, preview-first imports, source readiness visibility, and plain-English next actions.

| Workstream | Next product step | Safe command path | Completion signal |
| --- | --- | --- | --- |
| Scalable price refresh | Separate complete price coverage from short-history blockers, then use capped batches only after review; `PROVIDER=auto` should use Yahoo, Stooq, and configured FMP/Alpha Vantage/Finnhub fallbacks without manual provider hopping. | `make price-history-proof-queue TOP_N=10`, `make focus-price TICKER=...`, then `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto`, then `make readiness-snapshot`, then capped `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30` only if reviewed, then `make diff-hygiene`. | Price-ready coverage stays honest while short-history momentum/track-record blockers move only from source-backed rows. |
| Trusted fundamentals | Use the session-aware fundamentals source ladder, then trusted local imports when no configured source path is available. | `make session-source-preflight`, `make fundamentals-source-ladder-queue TOP_N=25`, `make focus-fundamentals TICKER=...`, then `make imports-validate IMPORT_TICKERS=...` and `make imports-preview IMPORT_TICKERS=...`; apply only after source-backed scope review, intended preview scope, and zero rejected rows. | `fundamentals_ready` and `dcf_ready` improve only from trusted rows; SEC/Yahoo failures pivot to configured FMP, Alpha Vantage, or Finnhub instead of stopping the workflow. |
| Source-backed peers | Prioritize active-universe and DCF-ready peer blockers before broad peer work. | `make peer-mapping-queue TOP_N=25`, `make focus-peers TICKER=...`, `make templates`, then `make imports-validate IMPORT_TICKERS=...` and `make imports-preview IMPORT_TICKERS=...`; apply only after reviewed peer scope, intended preview scope, and zero rejected rows. | Peer trend and peer valuation states are separated; peer valuation appears only when trusted peer inputs pass readiness. |
| Optional context | Keep earnings and analyst estimates locked until trusted local or reviewed provider-assisted rows exist. | `make optional-context-worklist TOP_N=25`, `make optional-context-source-ladder-queue TOP_N=10`, `make import-earnings`, `make import-analyst-estimates`, then `make imports-validate IMPORT_TICKERS=...` and `make imports-preview IMPORT_TICKERS=...`; apply only after reviewed optional-context scope, intended preview scope, and zero rejected rows. | Empty optional context reads as intentionally locked, not broken or inferred. |
| Source readiness guidance | Make source age, rejected-row reports, and generated-data hygiene visible before interpretation. | `make project-status`, `make research-health-check TOP_N=10`, `make public-check`, `make diff-hygiene`. | Visitors can see what is fresh, what is stale, what is local-only, and what should not be committed. |
| Data strategy | Keep a public, data-honest explanation of what can refresh safely and what still needs trusted human/source review. | Read `docs/DATA_STRATEGY.md`, then use the targeted commands above for a 5-10 company pilot. | Visitors understand why broad valuation coverage is limited and how the next trusted proof step should happen. |

Public-share rules for this stage:

- Keep the README demo path and sample reports short enough for GitHub/LinkedIn visitors.
- Keep dashboard pages plain-language first, with commands and file paths behind focused help or tables.
- Keep the sidebar focused on the three main visitor paths, with `More pages` still reachable for deeper local review.
- Do not publish broad generated CSV churn unless it is the reviewed artifact for that release.
- Do not add workflows that run imports, refreshes, account actions, direct recommendations, fabricated data, or valuation labels without ready inputs.

## 9. Acceptance Criteria For The Next Roadmap Milestone

The next roadmap milestone is complete when:

- [x] The product page clearly separates the 3,538-ticker master universe, 12-ticker active universe, and analysis-ready subset through the top-level Universe Layers cards and table.
- [x] The product page includes a grouped next-action console with safe capped or ticker-targeted commands.
- [x] Next-action rows include source readiness context and clearly state that dashboard commands are copyable only.
- [x] `SEC_USER_AGENT` is detected locally, and manual fundamentals imports validate/preview through the trusted CSV workflow.
- [x] `fundamentals_ready` improves beyond 23/3,538 with trusted data only.
- [x] `dcf_ready` improves beyond 23/3,538 with trusted data only.
- Evidence: a reviewed SEC Companyfacts import updated META from an old 2017-period fundamentals row to a 2025-period row filed in 2026; regenerated proof showed fundamentals-ready at 27/3,538 and DCF-ready at 24/3,538.
- [x] Peer readiness improves beyond 3/3,538 or peer blockers become more specific and actionable.
- [x] Decision buckets remain more informative than generic monitor rows.
- [x] `ARKF` and risk warnings are resolved or clearly classified.
- [x] Single-stock research mode can generate a data-honest report.
- [x] Single-stock reports distinguish clean peer readiness from peer readiness with missing valuation-metric caveats.
- [x] Dashboard navigation defaults to public visitor paths while preserving `More pages` and deep links.
- [x] Public data-strategy docs explain what can be automated and what still requires trusted source judgment.
- [x] `make pipeline` passes in the latest full data-output verification run.
- [x] `make onboarding` passes in the latest full data-output verification run.
- [x] `make research-health` passes in the latest full data-output verification run.
- [x] `make readiness` passes in the latest full data-output verification run.
- [x] `make test` passes through `make public-check`.
- [x] `make dashboard-smoke` passes through `make public-check`.

Current boundary:

- The product workflow for fundamentals import, SEC staging guidance, peer blocker triage, public UI polish, and single-stock report generation is implemented and verified at the public-share gate.
- Data Health now has compact DCF and peer proof-loop summaries, with lower row-level proof tables tucked into collapsed evidence drawers so operators see status, blocker, next proof step, evidence, and stop rule before raw tables.
- Single-Stock reports now keep workflow-fit, review-now, blocked/excluded, and Data Health handoff cards ahead of collapsed setup/fundamental detail tables.
- Public Home now puts the next page choice before optional workflow detail so first-time visitors see the product loop without walking through every command-oriented card.
- The Single-Stock pre-report contract now includes a report-first handoff before Data Health lane routing, reducing the feeling that the selected ticker, loaded report, and proof lane are separate demo surfaces.
- Data Health progressive-detail controls now use review-drawer language for queue, batch, metrics, and proof detail, reducing the sense that operators are managing internal load state.
- Cross-page research-loop context is now extracted into `src/research_loop.py` with direct tests, reducing dashboard monolith risk while preserving the same Home, Single-Stock, and Data Health orientation strip behavior.
- Public Home computes freshness before rendering the research-loop strip, keeping the visitor path stable while stale-artifact warnings remain visible.
- Readiness queue drilldowns now keep route cards visible while lane action tables and raw evidence rows stay collapsed by default.
- Trusted Fundamentals source-review drawers now keep command, evidence-writer, apply-decision, and raw source-review tables collapsed under the first-read cards.
- The remaining unchecked readiness-count items require real trusted data rows. They should not be closed by fabricated data or by committing broad CSV churn.
- If the next work session is data-focused, start with `make readiness-snapshot`, then run only scoped trusted-data proof loops, then run the full verification commands listed above before updating these boxes.

## Guardrails

- Do not fabricate market data.
- Do not fabricate fundamentals.
- Do not fabricate peer metrics.
- Do not fabricate earnings.
- Do not fabricate analyst estimates.
- Do not add broker integration.
- Do not add auto-trading.
- Do not produce buy/sell recommendations.
