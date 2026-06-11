# Data Strategy

The product is CSV-first. Local rows are the source of truth; provider-assisted rows are optional inputs that still have to pass readiness checks before analysis appears.

Provider-assisted does not mean provider-decided. A provider can help populate local price rows, but the product still validates local CSV coverage before momentum, liquidity, DCF, peer, or decision sections appear. Fundamentals, peer relationships, earnings, and analyst estimates need trusted source review before they become analysis inputs.

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

## Recommended Pilot

Do not try to make all 3,538 tickers fully analysis-ready at once. Start with 5 to 10 companies that matter for the public demo or active research list.

If you want to choose the next pilot from current local blockers, run `make trusted-data-pilot-candidates TOP_N=10`. It ranks operating-company candidates and excludes ETF/index monitor examples from the company DCF pilot queue. If you want a one-company packet after choosing a name, run `make trusted-data-pilot-packet TICKER=CRDO`; it prints the before report, focused blocker check, validation path, rebuild proof, and after report sequence. If you want the copyable read-only checklist after choosing several names, run `make trusted-data-pilot TICKERS=NVDA,CRDO,META TOP_N=10`. The broader checklist remains available as `make trusted-data-pilot TOP_N=10`. Each command does not refresh, import, or edit local CSV files.

Suggested company pilot: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`. ETF/index examples such as `QQQ` and `SMH` are useful monitor-context demos, but they are not operating-company DCF targets.

One-company evidence packet:

```bash
make readiness-snapshot
make stock-report-md TICKER=NVDA
make focus-fundamentals TICKER=NVDA
make focus-peers TICKER=NVDA
make imports-validate && make imports-preview && make imports-apply
make readiness && make dcf-readiness
make stock-report-md TICKER=NVDA
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
- Keep one regenerated Markdown report per pilot company so readers can see whether the mode changed or stayed data-blocked.
- Keep the exact validation path that changed the state: `make imports-validate`, `make imports-preview`, `make imports-apply`, then the relevant readiness command.
- The single-stock report opens with the correct mode: DCF-ready review, standalone DCF review, price/setup review only, monitor-only context, or data-unlock only.
- DCF-ready companies show assumptions, sensitivity, source readiness, and any locked optional context before interpretation.
- Peer-limited companies show the mapped peer blocker and the exact source-backed peer input needed next.
- Fundamentals-limited companies show the missing fields and whether SEC staging or manual fundamentals imports are the next trusted path.
- Optional earnings or analyst-estimate context stays locked unless trusted local rows pass validation, preview, and apply.
- The final proof is a regenerated report plus refreshed readiness counts; broad generated CSV churn should still stay out of the public branch unless intentionally reviewed.

## What Not To Automate Yet

- Broad fundamentals claims without trusted source rows.
- Applying SEC/manual fundamentals rows without validation and preview.
- Peer relationships inferred only from sector labels.
- Earnings or estimate context from empty optional files.
- Valuation labels for blocked rows.
- Broad generated CSV churn in the public branch.

The product should get more useful by improving trusted coverage and proof paths, not by filling missing fields with guesses.
