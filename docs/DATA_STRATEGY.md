# Data Strategy

The product is CSV-first. Local rows are the source of truth; provider-assisted rows are optional inputs that still have to pass readiness checks before analysis appears.

Provider-assisted does not mean provider-decided. A provider can help populate local price rows, but the product still validates local CSV coverage before momentum, liquidity, DCF, peer, or decision sections appear. Fundamentals, peer relationships, earnings, and analyst estimates need trusted source review before they become analysis inputs.

## Public Visitor FAQ

Use this section when someone asks whether the product is doing the analysis or copying a third-party answer:

- The product analysis comes from this repository's readiness gates, DCF calculations, peer gates, decision buckets, and report wording.
- Local or provider-assisted rows supply inputs; they do not decide valuation status, confidence, peer readiness, or research state.
- Prices are the safest lane to refresh at scale because they are repeatable time-series rows; dry-run and capped loops still come first.
- Fundamentals, peer mappings, earnings, and analyst estimates are judgment-required lanes; they should move through trusted source review, validation, preview, and readiness proof.
- Missing trusted rows are a product signal. They keep analysis locked so a visitor can see what is real, what is excluded, and what would prove the next layer is available.

## Quick Decision Guide

Use this guide before changing local data:

| If the gap is... | Do this first | Do not do this |
| --- | --- | --- |
| Missing or stale prices | Run `make price-refresh-loop DRY_RUN=1`, then snapshot readiness before any capped refresh. | Do not refresh the full universe blindly or commit broad CSV churn by default. |
| Missing fundamentals or DCF fields | Run `make trusted-data-pilot-candidates TOP_N=10`, then use SEC staging or trusted manual imports for 5-10 reviewed companies. | Do not fill placeholder fundamentals to make valuation appear ready. |
| Missing peers | Run `make peer-mapping-queue TOP_N=25`, then add source-backed peers and peer inputs only. | Do not turn sector or industry similarity into trusted peer valuation. |
| Missing earnings or estimates | Keep the section locked until trusted local rows pass validate, preview, and apply. | Do not render empty optional context as analysis. |

## Data Lanes

| Lane | Current strategy | Can be automated now? | Product boundary |
| --- | --- | --- | --- |
| Prices | Use local OHLCV CSVs, capped refresh loops, or reviewed manual imports. | Yes, with dry-run-first capped loops. | Missing prices block setup, momentum, liquidity, DCF, and peer context. |
| Fundamentals | Use trusted SEC staging when configured or reviewed manual fundamentals imports. | Partly. SEC staging can prepare rows, but apply remains reviewable. | Missing fundamentals block company-quality and DCF interpretation. |
| Peer mappings | Use source-backed manual peer mappings and peer metrics. | Not broadly yet. Human source judgment is still required. | Sector or industry fallback is not trusted peer valuation. |
| Earnings | Use trusted local earnings CSV rows only. | Not yet. | Empty earnings data stays intentionally locked. |
| Analyst estimates | Use trusted local analyst-estimate CSV rows only. | Not yet. | Consensus context is optional and must not become a recommendation. |

## Automation Boundary

The product can automate repeatable checks, but it should not automate source judgment. Use this split when deciding what belongs in code versus what belongs in a reviewed local CSV:

| Workflow | Safe to automate | Keep human-reviewed |
| --- | --- | --- |
| Price coverage | Dry-run planning, capped refresh loops, import normalization, validation, readiness rebuilds. | Whether a refreshed CSV should be committed or treated as local working data. |
| Fundamentals / DCF | Missing-field diagnostics, SEC staging helpers, schema validation, DCF readiness checks, report regeneration. | Whether a source row is trusted, which fiscal period is appropriate, and whether manual fundamentals should be applied. |
| Peers | Peer blocker queues, import schema checks, readiness status, peer trend versus valuation gating. | Which companies are real peers and whether any fallback sector/industry context is acceptable as context only. |
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
| Peers | No broad unattended apply. | Use peer queues to choose source-backed mappings. | Confirm the peer relationship and peer inputs before peer valuation appears. |
| Earnings / estimates | No. | Keep locked until trusted local rows exist. | Validate, preview, apply, then confirm optional-context readiness. |
| Public repo cleanup | Yes for checks, no for staging decisions. | `make public-check`, `make diff-hygiene`, `make staged-hygiene-check`. | Human review decides which docs, tests, sample reports, or data artifacts are published. |

The practical rule is simple: automate repeatable checks and capped previews; require human/source review before anything changes valuation, peer context, earnings context, estimates context, or public committed data.

## Freshness Without Daily Manual Work

You do not need to hand-refresh every ticker every day for the product to stay useful. Treat freshness as a lane-specific review workflow:

| Lane | Practical cadence | Safe automation | What still needs review |
| --- | --- | --- | --- |
| Prices | Run status/readiness checks whenever you open the project; use capped refresh loops only when coverage is stale or too short for the next research page. | `make price-refresh-loop DRY_RUN=1` can plan broad batches; a reviewed loop can refresh capped missing-price batches. | Inspect provider notes and generated CSV diffs before committing refreshed rows. |
| Fundamentals / DCF | Refresh only around company review, filings, or a trusted-data pilot; do not chase every ticker daily. | SEC staging and missing-field diagnostics can prepare review queues. | Source trust, fiscal period, rejected rows, validation/preview/apply, and rebuilt DCF readiness. |
| Peers | Update when a company enters a pilot or peer context is blocking a ready DCF report. | Peer queues can rank blockers and show exact next commands. | Whether the relationship is source-backed and whether peer valuation inputs are present. |
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

If you want to choose the next pilot from current local blockers, run `make trusted-data-pilot-candidates TOP_N=10`. It ranks operating-company candidates and excludes ETF/index monitor examples from the company DCF pilot list. The default candidate output is compact so visitors can see the shortlist, quick path, compact review board, and safe loop without reading every row-level proof detail; use `make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1` when you need full per-candidate file status, decision gates, rejected-row paths, and evidence expectations. If you want a one-company packet after choosing a name, run `make trusted-data-pilot-packet TICKER=CRDO`; it prints the before report, focused blocker check, lane review path, validate/apply step, rejected-row report path, rebuild proof, and evidence row to record. If you want the copyable read-only checklist after choosing several names, run `make trusted-data-pilot TICKERS=NVDA,CRDO,META TOP_N=10`. The broader checklist remains available as `make trusted-data-pilot TOP_N=10`. Each command does not refresh, import, or edit local CSV files.

The candidate list and one-company packet also print local file status, such as import CSV data-row counts, staged-folder file counts, and whether the rejected-row report path exists. Treat that as an inspection cue only. A file with rows is not automatically trusted coverage; it still needs source review, validation, preview, apply when appropriate, and rebuilt readiness before analysis is described as available.

Suggested company pilot: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`. ETF/index examples such as `QQQ` and `SMH` are useful monitor-context demos, but they are not operating-company DCF targets.

Decision rule: choose one company only when the matching trusted input can be reviewed. For fundamentals/DCF, that means trusted SEC or manual fundamentals rows. For peer mapping, that means source-backed peer relationships. For peer valuation, that means mapped peers also have trusted valuation inputs. If the source proof is missing, the correct outcome is not failure; it is a visible missing-data state and a move to the next candidate.

Each one-company packet now has a decision gate: continue only when the required source proof exists; otherwise leave the section blocked and do not apply placeholder rows so the report appears complete. This is the product boundary that keeps valuation useful rather than decorative.

The candidate command also prints a compact review board. Read it as:

| Step | Meaning |
| --- | --- |
| Continue | Use the company only when the named source proof exists for the missing lane. |
| Skip | Move to the next candidate when source proof is unavailable or not reviewable. |
| Prove | Record the evidence row, rerun readiness, and regenerate the stock report before describing the lane as available. |

This keeps the pilot practical: a useful result can be either "this ticker became supported after trusted rows were validated" or "this ticker stayed blocked for a specific missing input."

One-company evidence packet:

```bash
make readiness-snapshot
make trusted-data-pilot-candidates TOP_N=10
make trusted-data-pilot-packet TICKER=<ticker>
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
5. For peers, use `make peer-mapping-queue TOP_N=25` and add only source-backed rows.
6. For manual imports, run `make imports-validate`, then `make imports-preview`, then `make imports-apply`.
7. Prove the result with `make readiness`, `make project-status`, and `make stock-report-md TICKER=...`.
8. Keep the public branch clean with `make diff-hygiene`; stage only reviewed docs/code/tests or sample Markdown reports unless a refreshed CSV is the artifact you intentionally want to publish.

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
- Optional earnings or analyst-estimate context stays locked unless trusted local rows pass validation, preview, and apply.
- The final proof is a regenerated report plus refreshed readiness counts, recorded alongside any still-blocked reason; broad generated CSV churn should still stay out of the public branch unless intentionally reviewed.

## What Not To Automate Yet

- Broad fundamentals claims without trusted source rows.
- Applying SEC/manual fundamentals rows without validation and preview.
- Peer relationships inferred only from sector labels.
- Earnings or estimate context from empty optional files.
- Valuation labels for blocked rows.
- Broad generated CSV churn in the public branch.

The product should get more useful by improving trusted coverage and proof paths, not by filling missing fields with guesses.
