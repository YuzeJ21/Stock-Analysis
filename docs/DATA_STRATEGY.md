# Data Strategy

The product is CSV-first. Local rows are the source of truth; provider-assisted rows are optional inputs that still have to pass readiness checks before analysis appears.

Provider-assisted does not mean provider-decided. A provider can help populate local price rows, but the product still validates local CSV coverage before momentum, liquidity, DCF, peer, or decision sections appear. Fundamentals, peer relationships, earnings, and analyst estimates need trusted source review before they become analysis inputs.

## Public Visitor FAQ

Use this section when someone asks whether the product is doing the analysis or copying a third-party answer:

- The product analysis comes from this repository's readiness gates, DCF calculations, peer gates, decision buckets, and report wording.
- Local or provider-assisted rows supply inputs; they do not decide valuation status, data confidence, peer readiness, or research state.
- Prices are the safest lane to refresh at scale because they are repeatable time-series rows; dry-run and capped loops still come first.
- Fundamentals, peer mappings, earnings, and analyst estimates are judgment-required lanes; they should move through trusted source review, validation, preview, and readiness proof.
- Missing trusted rows are a product signal. They keep analysis locked so a visitor can see what is real, what is excluded, and what would prove the next layer is available.

## Quick Decision Guide

Use this guide before changing local data:

| If the gap is... | Do this first | Do not do this |
| --- | --- | --- |
| Missing or stale prices | Run `make price-refresh-loop DRY_RUN=1`, then snapshot readiness before any capped refresh. | Do not refresh the full universe blindly or commit broad CSV churn by default. |
| Missing fundamentals or DCF fields | Run `make trusted-data-pilot-candidates TOP_N=10`, then use SEC staging or trusted manual imports for 5-10 reviewed companies. | Do not fill placeholder fundamentals to make valuation appear ready. |
| Missing `shares_outstanding` | Run `make share-count-proof-queue TOP_N=10`, then review SEC/manual source proof for the named tickers. | Do not infer share count from price, market cap, peers, or placeholder rows. |
| Missing peers | Run `make peer-mapping-queue TOP_N=25`, then add source-backed mappings or mapped-peer price/fundamental inputs only. | Do not turn sector or industry similarity into trusted peer valuation. |
| Missing earnings or estimates | Keep the section locked until trusted local rows pass validate, preview, and apply. | Do not render empty optional context as analysis. |

## Data Lanes

| Lane | Current strategy | Can be automated now? | Product boundary |
| --- | --- | --- | --- |
| Prices | Use local OHLCV CSVs, capped refresh loops, or reviewed manual imports. | Yes, with dry-run-first capped loops. | Missing prices block setup, momentum, liquidity, DCF, and peer context. |
| Fundamentals | Use trusted SEC staging when configured or reviewed manual fundamentals imports. | Partly. SEC staging can prepare rows, but apply remains reviewable. | Missing fundamentals block company-quality and DCF interpretation. |
| Peer mappings and mapped-peer inputs | Use source-backed manual peer mappings first, then mapped-peer price, fundamentals, market cap, or valuation inputs. | Not broadly yet. Human source judgment is still required. | Sector or industry fallback is not trusted peer valuation. |
| Earnings | Use trusted local earnings CSV rows only. | Not yet. | Empty earnings data stays intentionally locked. |
| Analyst estimates | Use trusted local analyst-estimate CSV rows only. | Not yet. | Consensus context is optional and must not become a recommendation. |

## Automation Boundary

The product can automate repeatable checks, but it should not automate source judgment. Use this split when deciding what belongs in code versus what belongs in a reviewed local CSV:

| Workflow | Safe to automate | Keep human-reviewed |
| --- | --- | --- |
| Price coverage | Dry-run planning, capped refresh loops, import normalization, validation, readiness rebuilds. | Whether a refreshed CSV should be committed or treated as local working data. |
| Fundamentals / DCF | Missing-field diagnostics, SEC staging helpers, schema validation, DCF readiness checks, report regeneration. | Whether a source row is trusted, which fiscal period is appropriate, and whether manual fundamentals should be applied. |
| Share-count proof | Ranking DCF blockers where `shares_outstanding` is the gating input, printing copy-only SEC/manual review commands, and showing stop conditions. | Whether a reviewed 10-K, 10-Q, annual report, or trusted local source actually proves the share count. |
| Peers | Peer blocker queues, import schema checks, readiness status, peer trend versus valuation-input gating. | Which companies are real peers and whether any fallback sector/industry context is acceptable as context only. Also review whether mapped-peer inputs are source-backed. |
| Earnings / estimates | Schema templates, staged-folder checks, rejected-row reports, unavailable-state rendering. | Whether a source is trusted enough to become local optional context. |
| Public branch hygiene | Diff classification, public wording checks, staged hygiene, dashboard smoke. | Which generated sample reports or refreshed data artifacts are intentionally public. |

If a workflow depends on source credibility, issuer judgment, fiscal-period choice, peer selection, or optional provider licensing, treat it as reviewed input rather than background automation.

## Background Automation Map

Use this split when deciding what can run on a schedule and what should stay review-required.

| Workflow | Can run unattended? | Safe default | Review gate before analysis changes |
| --- | --- | --- | --- |
| Status and readiness checks | Yes. | `make status-check TOP_N=5`, `make readiness`, `make dashboard-smoke`. | None; these commands read or rebuild deterministic local status. |
| Price planning | Yes, as a dry run. | `make price-refresh-loop DRY_RUN=1`. | Review the planned tickers and source notes before any real refresh. |
| Price refresh | Only capped and intentionally. | Use capped loops after a dry run, then inspect local CSV diffs. | Run readiness, check source freshness, and avoid committing broad CSV churn by default. |
| Fundamentals / DCF | No broad unattended apply. | Stage or inspect a 5-10 company pilot. | Validate, preview, confirm trusted source rows, then rebuild DCF readiness. |
| Peers | No broad unattended apply. | Use peer queues to choose source-backed mappings or mapped-peer input gaps. | Confirm the peer relationship and mapped-peer inputs before peer valuation appears. |
| Earnings / estimates | No. | Keep locked until trusted local rows exist. | Start with read-only `make optional-context-summary`; after trusted row changes, validate, preview, apply, then confirm optional-context readiness. |
| Public repo cleanup | Yes for checks, no for staging decisions. | `make public-check`, `make diff-hygiene`, `make staged-hygiene-check`. | Human review decides which docs, tests, sample reports, or data artifacts are published. |

The practical rule is simple: automate repeatable checks and capped previews; require human/source review before anything changes valuation, peer context, earnings context, estimates context, or public committed data.

## Freshness Without Daily Manual Work

You do not need to hand-refresh every ticker every day for the product to stay useful. Treat freshness as a lane-specific review workflow:

| Lane | Practical cadence | Safe automation | What still needs review |
| --- | --- | --- | --- |
| Prices | Run status/readiness checks whenever you open the project; use capped refresh loops only when coverage is stale or too short for the next research page. | `make price-refresh-loop DRY_RUN=1` can plan broad batches; a reviewed loop can refresh capped missing-price batches. | Inspect provider notes and generated CSV diffs before committing refreshed rows. |
| Fundamentals / DCF | Refresh only around company review, filings, or a trusted-data pilot; do not chase every ticker daily. | SEC staging and missing-field diagnostics can prepare review queues. | Source trust, fiscal period, rejected rows, validation/preview/apply, and rebuilt DCF readiness. |
| Peers | Update when a company enters a pilot or peer context is blocking a ready DCF report. | Peer queues can rank missing mappings separately from mapped-peer valuation-input blockers. | Whether the relationship is source-backed and whether mapped-peer valuation inputs are present. |
| Earnings / estimates | Keep locked unless you have trusted local rows for a review cycle. | Templates, staged-folder checks, and rejected-row reports. | Whether the source is trusted and whether optional context should be applied. |

A safe recurring routine is read-only by default: run `make status-check TOP_N=5`, `make readiness`, `make dashboard-smoke`, and `make price-refresh-loop DRY_RUN=1`. Only run a real capped price loop after reviewing the dry-run plan. Do not schedule unattended fundamentals, peer, earnings, estimate imports, or public commits.

## Safe Overnight Automation

If you want the project to keep working while unattended, keep the job in review mode by default.

Safe overnight jobs:

- Run status, readiness, dashboard smoke, public wording, and diff-hygiene checks.
- Run `make price-refresh-loop DRY_RUN=1` to produce a capped price-refresh plan without changing local files.
- Run capped price refreshes only when you already accepted the planned scope; review refreshed CSV diffs before committing.
- Regenerate selected Markdown reports for demo tickers after reviewed data changes.

Do not run unattended jobs that apply fundamentals, peer mappings, earnings, analyst estimates, or public commits. Those lanes require source judgment, validation, preview, rejected-row review, and readiness proof before analysis changes.

## Recommended Pilot

Do not try to make all 3,538 tickers fully analysis-ready at once. Start with 5 to 10 companies that matter for the public demo or active research list.

If you want to choose the next pilot from current local blockers, run `make trusted-data-pilot-candidates TOP_N=10`. It ranks operating-company candidates and excludes ETF/index monitor examples from the company DCF pilot list. The default candidate output is compact so visitors can see the shortlist, quick path, compact review board, and safe loop without reading every row-level proof detail; use `make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1` when you need full per-candidate file status, decision gates, rejected-row paths, and evidence expectations. If you want a batch operating view before drilling into individual names, run `make trusted-data-pilot-board TICKERS=MU,CRDO,HOOD,TSLA,META,A,APLD`; it prints the lane mix, outcome mix, lane-group workflows, per-ticker blocker rows, and suggested lane-group next step without writing a CSV. Lane-group workflows show candidate count, tickers, shared blocker theme, review command pattern, trusted row target, rejected-row report, proof command pattern, stop condition, and whether the lane is review-only, locked, or safe for dry-run batching. If you already know the lane group, run `make trusted-data-pilot-lane LANE=fundamentals_dcf`, `make trusted-data-pilot-lane LANE=peer_mapping`, `make trusted-data-pilot-lane LANE=peer_valuation_inputs`, `make trusted-data-pilot-lane LANE=optional_context_locked`, or `make trusted-data-pilot-lane LANE=price_coverage`; the command prints ordered lane-specific steps plus the evidence summary for what proves the lane, which rows/files are needed, which rejected-row reports matter, which readiness command confirms a change, and what remains blocked. Price coverage stays separate as a dry-run-first planning lane; fundamentals, peers, earnings, and analyst estimates remain review-required. If you want a one-company packet after choosing a lane group, run `make trusted-data-pilot-packet TICKER=CRDO`; it prints the before report, focused blocker check, lane review path, validate/apply step, rejected-row report path, rebuild proof, and evidence row to record. If you want a CSV ledger for selected before-state proof paths, run `make trusted-data-pilot-evidence TICKERS=MU,CRDO`; it writes current modes, lane blockers, proof commands, trusted-row targets, rejected-row checks, and still-blocked reasons without changing source rows or readiness. If you want the copyable read-only checklist after choosing several names, run `make trusted-data-pilot TICKERS=NVDA,CRDO,META TOP_N=10`. The broader checklist remains available as `make trusted-data-pilot TOP_N=10`. Each command does not refresh, import, or edit local CSV files.

The candidate list and one-company packet also print local file status, such as import CSV data-row counts, staged-folder file counts, and whether the rejected-row report path exists. Treat that as an inspection cue only. A file with rows is not automatically trusted coverage; it still needs source review, validation, preview, apply when appropriate, and rebuilt readiness before analysis is described as available.

Suggested company pilot: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`. ETF/index examples such as `QQQ` and `SMH` are useful monitor-context demos, but they are not operating-company DCF targets.

Decision rule: choose one company only when the matching trusted input can be reviewed. For fundamentals/DCF, that means trusted SEC or manual fundamentals rows. For peer mapping, that means source-backed peer relationships. For peer valuation, that means mapped peers also have trusted valuation inputs. If the source proof is missing, the correct outcome is not failure; it is a visible missing-data state and a move to the next candidate.

Each one-company packet now has a decision gate: continue only when the required source proof exists; otherwise leave the section blocked and do not apply placeholder rows so the report appears complete. This is the product boundary that keeps valuation useful rather than decorative.

Every pilot packet follows the same proof loop: snapshot the baseline, generate the before report, review the source proof for the missing lane, validate/preview and check rejected rows before applying changes, rebuild readiness and the stock report, then compare the after report. Only the rebuilt report can prove a lane changed. If the proof is missing or the report remains blocked, keep the blocker visible and move to the next candidate.

The candidate command also prints a compact review board. Read it as:

| Step | Meaning |
| --- | --- |
| Continue | Use the company only when the named source proof exists for the missing lane. |
| Skip | Move to the next candidate when source proof is unavailable or not reviewable. |
| Prove | Record the evidence row, rerun readiness, and regenerate the stock report before describing the lane as available. |

This keeps the pilot practical: a useful result can be either "this ticker became supported after trusted rows were validated" or "this ticker stayed blocked for a specific missing input."

Read each pilot outcome in durable states:

| Outcome | Meaning |
| --- | --- |
| Supported | Rebuilt readiness and the regenerated report show the lane is ready. |
| Still blocked | Validation failed, rejected rows appeared, or the report stayed locked; keep the named blocker visible. |
| Skip | Source proof is unavailable or not reviewable; do not apply placeholder rows, and move to the next shortlisted company. |
| Excluded | The ticker is not an operating-company pilot target. |

Pilot evidence rows should also carry a durable `outcome_state`: `supported`, `still_blocked`, `skipped`, or `excluded`. Use `supported` only after rebuilt readiness and the regenerated report prove the lane changed. Use `still_blocked` when validation fails, rejected rows appear, or the report remains locked. Use `skipped` when source proof is unavailable. Use `excluded` when the ticker is not an operating-company pilot target.

One-company evidence packet:

```bash
make readiness-snapshot
make trusted-data-pilot-candidates TOP_N=10
make trusted-data-pilot-lane LANE=fundamentals_dcf
make trusted-data-pilot-packet TICKER=<ticker>
make trusted-data-pilot-evidence TICKERS=MU,CRDO
make stock-report-md TICKER=<ticker>
Run the lane-specific review command printed by the packet:
  fundamentals lane: make focus-fundamentals TICKER=<ticker>
  peer lane: make focus-peers TICKER=<ticker>
make imports-validate && make imports-preview && make imports-apply
Check the rejected-row report printed by the packet before treating the lane as available.
Run the matching rebuild proof:
  fundamentals lane: make readiness && make dcf-readiness
  peer lane: make readiness && make peer-mapping-queue TOP_N=25
```

1. Save the baseline with `make readiness-snapshot`.
2. Confirm blockers with `make status-check TOP_N=10`.
3. For prices, inspect ticker-level gaps with `make price-worklist TOP_N=10`, then preview any broader update with `make price-refresh-loop DRY_RUN=1`.
4. For fundamentals, use `make sec-stage-queue TOP_N=25` and `make focus-fundamentals TICKER=...`.
5. When the DCF gap is `shares_outstanding`, use `make share-count-proof-queue TOP_N=10` to separate share-count-only blockers from tickers that still need price, revenue, free cash flow, or FCF margin too.
6. For peers, use `make peer-mapping-queue TOP_N=25` and add only source-backed rows.
7. For manual imports, run `make imports-validate`, then `make imports-preview`, then `make imports-apply`.
8. Prove the result with `make readiness`, `make project-status`, and `make stock-report-md TICKER=...`.
9. Keep the public branch clean with `make diff-hygiene`; stage only reviewed docs/code/tests or sample Markdown reports unless a refreshed CSV is the artifact you intentionally want to publish.

## Pilot Evidence Checklist

A company is a useful pilot win only when the evidence is reviewable, not just when a CSV row exists.

- Keep a before/after readiness count from `make readiness-snapshot` and `make readiness`.
- Keep one regenerated Markdown report per pilot company so readers can see whether the mode changed or stayed visibly blocked by missing data.
- Keep the exact review and validation path that changed the state: lane review command, `make imports-validate`, `make imports-preview`, `make imports-apply`, rejected-row report path, then the relevant readiness proof command.
- Record local file status from the pilot output, but do not treat row counts or file existence as proof by themselves.
- The single-stock report opens with the correct mode: DCF-ready review, standalone DCF review, price/setup review only, monitor-only context, or data needed before analysis.
- DCF-ready companies show assumptions, sensitivity, source readiness, and any locked optional context before interpretation.
- Peer-limited companies show the mapped peer blocker and the exact source-backed peer input needed next.
- Fundamentals-limited companies show the missing fields and whether SEC staging or manual fundamentals imports are the next trusted path.
- Optional earnings or analyst-estimate context stays locked unless trusted local rows pass validation, preview, and apply. Use `make optional-context-summary TOP_N=10` when you only need to inspect the locked lane without writing readiness CSVs.
- The final proof is a regenerated report plus refreshed readiness counts, recorded alongside any still-blocked reason; broad generated CSV churn should still stay out of the public branch unless intentionally reviewed.

## Reviewed Data Proof V1

Use `make reviewed-data-proof` to show the durable lane-level proof ledger in `data/reviewed_data_proofs.csv`. This ledger is intentionally small and source-controlled: it records source proof status, reviewer outcome, validate/preview/apply result, rejected-row status, readiness before/after, final `supported`, `still_blocked`, `skipped`, or `excluded` outcome, the proof command, and the artifact/churn policy. It is not a generated readiness CSV and should not be refreshed broadly.

Use `make lane-outcome-history` to summarize lane outcomes over time from the reviewed proof ledger. This keeps lane history durable without relying on generated CSV churn from `make readiness`, onboarding, or report refreshes.

Use `make reviewed-data-proof-record` only after the source proof, validation, preview, rejected-row review, apply step, and readiness proof have been reviewed. The target requires an explicit lane, proof id, proof date, and final outcome so vague or accidental proof rows are not appended.

Use `make price-reviewed-run` after a dry-run plan has been reviewed. It prints the controlled capped price execution workflow: status check, readiness snapshot, dry run, reviewed capped run command, post-run price coverage/readiness/status checks, diff hygiene, and rollback notes. Price coverage remains separate from fundamentals and peers; price rows can improve coverage only, not valuation inputs or conclusions.

Use `make public-demo-readiness-pack` or open `docs/PUBLIC_DEMO_READINESS_PACK.md` for the small shareable proof set: Home, Data Health lane board, one ready report, one blocked report, and one excluded/monitor example. Data Health also surfaces the latest reviewed proof timeline from the durable ledger so visitors can see what changed, what stayed blocked, and which command proves it.

## Data Readiness Operations Center V1

Use `make readiness-ops-center` before drilling into individual tickers. It prints a read-only lane board for price coverage, fundamentals/DCF proof, peer mapping proof, peer valuation inputs, earnings locked context, analyst-estimates locked context, and excluded/not-applicable rows. Each lane keeps ready, partial, blocked, and excluded counts visible, shows the workflow mode, and names the next safe command without refreshing, importing, applying, or rewriting local files.

Trusted Coverage Growth V2 keeps peer readiness split into sub-states before a lane can be called supported: peer mapping, peer price, peer momentum, peer fundamentals, peer valuation, and peer valuation comparison. Peer trend context can become usable before peer valuation is ready. Sector or industry fallback remains research context only; it is not trusted peer mapping or peer valuation proof.

Use `make coverage-frontier TOP_N=10` to rank broad batch opportunities by unlock impact. This is an operations queue, not a security ranking: a high-impact lane means many feature states are blocked or partial, not that any ticker is attractive or that source data is already available. The command includes the source lane, workflow mode, possible state move, proof command, and generated-churn policy.

Use `make data-coverage-planner TOP_N=10` after the frontier check to convert those lanes into a repeatable expansion plan. The planner is read-only: it names the capped or proof-first command, review gate, stop condition, proof command, outcome boundary, and generated-churn policy for each lane without refreshing prices, staging fundamentals, applying imports, inferring peers, or rewriting readiness outputs.

Use `make coverage-expansion-loop TOP_N=10` when the operator is ready to turn the planner into one reviewed loop. It keeps the flow copy-only: selected lane, preflight gate, reviewed packet, readiness snapshot, dry run, capped command boundary, validate/preview/apply gate, rebuilt readiness, before/after comparison, proof-record dry run, and diff hygiene. If the current report, prior snapshot, or freshness gate is not ready, the loop stops at the preflight fix instead of treating stale counts as proof.

In public Data Health, visitors see the three simple paths first: review one stock, improve data coverage, and inspect proof. The same coverage expansion loop appears only as a compact operator card before the detailed batch tables. The full loop rows stay inside the reviewed-batch drawer so the page starts with the next safe action instead of raw command sprawl.

Use `make readiness-ops-evidence` as the compact evidence checklist before packaging work. It restates the proof gate, locked optional lanes, excluded/not-applicable boundary, and broad CSV/JSON churn policy. Data Health surfaces the same operations-center and coverage-frontier views before the trusted-data pilot and detailed tables so the product starts from batch lanes rather than one-name manual loops.

In Operator mode, Data Health is organized as a readiness operations command center rather than a long proof dump. Start with the Executive Snapshot, choose one lane in the Operator Queue, then open an evidence drawer only when you need copy-only commands, proof rows, or detailed tables. Public mode keeps the quick-read visitor path separate from the operator runbooks.

## Reviewed Batch Execution V1

Use `make reviewed-batch LANE=prices TOP_N=10` to convert a frontier lane into a reviewed run packet. The packet is written to `outputs/reviewed_batch_packet.md` and `outputs/reviewed_batch_packet.csv`; it is copy-only and does not refresh, import, apply, or rewrite local data. Supported lane aliases are `prices`, `fundamentals`, `peers`, `metrics`, and `optional_context`, with optional `TICKERS=...` for a capped reviewed scope.

The packet includes the pre-run readiness snapshot command, dry-run command, capped execution command, validate/preview/apply gates, post-run verification commands, expected artifacts, rollback notes, proof-row template, research-only guardrails, and "do not proceed if" blockers. If saved readiness artifacts are missing or stale because source CSVs changed after the reports, the packet says to run `make readiness` before relying on final counts.

Use the reviewed batch packet after `make coverage-frontier TOP_N=10` identifies the best lane to inspect. A high-impact lane is still an operations queue, not a security ranking, and every mutating workflow remains validate -> preview -> apply before any supported outcome is recorded.

In the dashboard, use Operator mode -> Data Health -> selected lane as the V2 workflow surface. The page shows one reviewed-batch lane at a time, source/freshness warnings before commands, a capped reviewed packet action, and a collapsed review drawer with dry-run, capped execution, validate, preview, apply, proof, rollback, and generated-artifact hygiene steps. Public mode intentionally hides these operator-heavy details.

The reviewed-batch drawer now starts with a Batch Execution Checklist so the full loop can be reviewed without stitching together raw tables: choose lane, read source/freshness warnings, generate the reviewed packet, preview the capped batch, pass the validate/preview/apply gate, compare before/after readiness, dry-run the proof record, and classify generated artifacts. Metrics remain read-only in that checklist; price, fundamentals, peers, and optional-context lanes keep their lane-specific validation and preview gates.

Use `make reviewed-batch LANE=metrics TOP_N=10` when the next work is metric-readiness triage rather than a source-row import. This packet is read-only: it runs the SPY/QQQ metric-readiness board, summarizes blocker families, and tells the operator which underlying source lane needs proof. It does not apply metric rows, infer missing Sharpe/Sortino/beta/drawdown/trend/multiple values, or bypass the price, fundamentals, market-context, or peer-input gates.

Use the Data Health decision proof drawer when research decisions are stale or blocked. It now shows one compact checklist before raw decision rows: freshness status, top proof row, what can be reviewed now, what stays locked, the copy-only local command, and the proof command required after an unlock. If research decisions are older than readiness, the drawer keeps the queue blocked until `make research-decisions` and `make decision-proof-queue TOP_N=12` rebuild current proof rows.

Use `make reviewed-batch-preflight LANE=prices TOP_N=100` before a reviewed batch when the next action could mutate local data. It checks whether the current readiness report exists, whether the prior readiness snapshot exists, whether freshness is current, which dry-run and capped command would apply, which artifacts need review, and which conditions should stop the run. The preflight is read-only and is designed to catch missing `make readiness-snapshot` evidence before a proof row needs changed counts.

For Trusted Coverage Growth V2, reviewed batches should leave a proof row rather than a vague note. Record the batch id, lane, scope, tickers, pre-run readiness snapshot, exact command, validation result, preview result, apply result, post-run readiness snapshot, changed readiness counts, changed tickers, reviewer, review date, source files, generated artifacts reviewed, final outcome, and notes. Valid final outcomes are `supported`, `still_blocked`, `skipped`, and `excluded`.

Use `make reviewed-batch-proof` to read the durable reviewed batch ledger in `data/reviewed_batch_proofs.csv`. Use `DRY_RUN=1 make reviewed-batch-proof-record ...` to preview the exact ledger row and validation status without appending. Use `make reviewed-batch-proof-record` only after the packet, dry-run or capped reviewed scope, validate/preview/apply decision, readiness proof, and generated-artifact review are complete. This command appends one proof row; it does not refresh data, apply imports, infer missing peer inputs, or create a recommendation.

Use `make reviewed-batch-compare LANE=prices BATCH_ID=<id> REVIEW_DATE=<yyyy-mm-dd>` after `make readiness-snapshot`, a reviewed batch step, and `make readiness`. It compares `data/reports/ticker_readiness_report.previous.csv` with the current readiness report and prints changed readiness counts, changed tickers, and a proof-ledger command scaffold. If the prior or current snapshot is missing, it tells the operator which refresh or snapshot command to run instead of guessing.

In Data Health -> Proof History, the Reviewed Batch Proof drawer now puts the completion loop first: latest reviewed packet, before/after comparison status, and proof-record scaffold. The detailed reviewed data ledger, reviewed batch ledger, and comparison table remain available underneath, but the operator can finish the batch proof without scanning raw tables first.

The dashboard also surfaces a Snapshot Gate before reviewed batch work. If the current readiness report is missing, the operator sees `make readiness` first. If the prior baseline snapshot is missing, the operator sees `make readiness-snapshot` before packet, dry-run, capped execution, comparison, or proof-record commands. A supported outcome should not be recorded until the baseline snapshot, source proof, validation, preview/apply decision, rebuilt readiness, and artifact classification are all reviewed.

The Reviewed Batch Apply Guard makes the mutating step explicit. Price batches stop at `make price-validate` and `make price-preview` before any reviewed `make price-apply` decision. Fundamentals, peers, earnings, and analyst-estimate rows stop at `make imports-validate` and `make imports-preview` until rejected-row reports are reviewed. Metrics remain read-only and cannot create a supported outcome by themselves; they route missing inputs back to the appropriate source lane.

The Reviewed Batch Outcome Recorder shows the proof-row fields that are still missing before an outcome can be recorded. It checks validation result, preview result, apply result, changed readiness counts, changed tickers, source files, and generated-artifact review. Placeholder template values stay marked as missing, and changed readiness fields remain blocked until the snapshot comparison is available.

The Proof Record Command Builder converts the reviewed packet, outcome recorder, and snapshot comparison into one copy-ready `make reviewed-batch-proof-record ...` command. Reviewed values are filled when available; unresolved reviewer, review date, final outcome, notes, validation, preview, apply, source, or artifact-review fields remain visible as placeholders so the operator does not hand-edit the proof row silently.

The proof recorder and command-builder rules now live in `src/reviewed_batch_command_builder.py`, with the dashboard kept as the rendering layer. This keeps the reviewed-batch UX easier to test without changing the append-only proof ledger behavior.

The Proof Record Validation layer checks the copy-ready command before it is treated as record-ready. Required proof fields must be real reviewed values, `FINAL_OUTCOME` must be exactly `supported`, `still_blocked`, `skipped`, or `excluded`, and snapshot-dependent fields stay blocked until the before/after comparison is available. Reviewer and notes remain visible manual fields, but they do not hide required proof placeholders.

The Ledger Record Safety layer applies the same boundary at the CLI write path. A dry run prints the exact `data/reviewed_batch_proofs.csv` row shape plus `ready_to_record`, `needs_field_fills`, or `invalid_outcome` validation. A real append is blocked when required fields still contain placeholders, so the dashboard preview and command-line write path share the same safety gate.

## Readiness-Gated Review Metrics

Use `make metric-readiness TOP_N=10 BENCHMARK=SPY` to inspect the capped metric-readiness queue without refreshing or importing data. Use `make benchmark-risk-review TICKER=<ticker> BENCHMARK=SPY` for one ticker. Both commands read local CSV-backed provider data and print ready, partial, blocked, or excluded states for each metric, with freshness context before the summary.

Price-derived metrics can become ready from trusted local price history: benchmark-relative return, max drawdown, rolling volatility, beta, Sharpe, and Sortino. Benchmark-relative return and beta require enough aligned ticker and benchmark rows; if SPY or QQQ history is missing or too short, those metrics remain partial or blocked.

Fundamentals, valuation, and peer metrics keep stricter gates. Revenue growth and FCF margin can show current trusted-row source context, but numeric trend values stay withheld until at least two period-labeled trusted fundamentals rows support row-derived revenue growth and FCF margin change. Valuation multiples require trusted fundamentals plus market-cap or trusted price/share-count context. Peer valuation dispersion requires mapped peers plus trusted peer valuation inputs. None of these metrics should be filled from placeholder rows.

Partial or blocked metrics intentionally withhold numeric values in reports and dashboard tables. The exact missing input remains visible so a reader sees the readiness gap instead of mistaking a partial calculation for a completed review metric.

Sharpe and Sortino are historical review metrics only. Keep the risk-free-rate assumption explicit; the default lives in `config.yaml` under `risk_rules.annual_risk_free_rate_pct`, and command-line review can override it with `RISK_FREE_RATE=...`. Do not use benchmark or risk metrics as rankings, forecasts, allocation guidance, or account-action instructions.

Data Health surfaces these review metric lanes as readiness gates, not calculations to trust blindly: benchmark/risk metrics require local price history, fundamentals trend requires trusted fundamentals rows, valuation multiples require market-cap or trusted price/share-count context, peer dispersion requires mapped peer valuation inputs, and ETF/index proxies exclude operating-company metrics.

Operator mode also shows a compact SPY/QQQ metric-readiness queue in Data Health. Use it to find the dominant blocker family across benchmarks before opening single-stock reports one by one. The same view is available outside Streamlit with `make metric-readiness-board TOP_N=10`; add `OUTPUT=outputs/metric_readiness_board.csv` only when the CSV board is an intentional reviewed artifact.

## What Not To Automate Yet

- Broad fundamentals claims without trusted source rows.
- Applying SEC/manual fundamentals rows without validation and preview.
- Peer relationships inferred only from sector labels.
- Earnings or estimate context from empty optional files.
- Valuation labels for blocked rows.
- Broad generated CSV churn in the public branch.

The product should get more useful by improving trusted coverage and proof paths, not by filling missing fields with guesses.
