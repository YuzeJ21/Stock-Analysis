# Data Strategy

The product is CSV-first. Local rows are the source of truth; provider-assisted rows are optional inputs that still have to pass readiness checks before analysis appears.

Provider-assisted does not mean provider-decided. A provider can help populate local price rows, but the product still validates local CSV coverage before momentum, liquidity, DCF, peer, or decision sections appear. Fundamentals, peer relationships, earnings, and analyst estimates need trusted source review before they become analysis inputs.

## Data Lanes

| Lane | Current strategy | Can be automated now? | Product boundary |
| --- | --- | --- | --- |
| Prices | Use local OHLCV CSVs, capped refresh loops, or reviewed manual imports. | Yes, with dry-run-first capped loops. | Missing prices block setup, momentum, liquidity, DCF, and peer context. |
| Fundamentals | Use trusted SEC staging when configured or reviewed manual fundamentals imports. | Partly. SEC staging can prepare rows, but apply remains reviewable. | Missing fundamentals block company-quality and DCF interpretation. |
| Peer mappings | Use source-backed manual peer mappings and peer metrics. | Not broadly yet. Human source judgment is still required. | Sector or industry fallback is not trusted peer valuation. |
| Earnings | Use trusted local earnings CSV rows only. | Not yet. | Empty earnings data stays intentionally locked. |
| Analyst estimates | Use trusted local analyst-estimate CSV rows only. | Not yet. | Consensus context is optional and must not become a recommendation. |

## Recommended Pilot

Do not try to make all 3,538 tickers fully analysis-ready at once. Start with 5 to 10 companies that matter for the public demo or active research list.

If you want the copyable read-only checklist first, run `make trusted-data-pilot TOP_N=10`. It prints the pilot sequence and does not refresh, import, or edit local CSV files.

Suggested company pilot: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`. ETF/index examples such as `QQQ` and `SMH` are useful monitor-context demos, but they are not operating-company DCF targets.

1. Save the baseline with `make readiness-snapshot`.
2. Confirm blockers with `make status-check TOP_N=10`.
3. For prices, inspect ticker-level gaps with `make price-worklist TOP_N=10`, then preview any broader update with `make price-refresh-loop DRY_RUN=1`.
4. For fundamentals, use `make sec-stage-queue TOP_N=25` and `make focus-fundamentals TICKER=...`.
5. For peers, use `make peer-mapping-queue TOP_N=25` and add only source-backed rows.
6. For manual imports, run `make imports-validate`, then `make imports-preview`, then `make imports-apply`.
7. Prove the result with `make readiness`, `make project-status`, and `make stock-report-md TICKER=...`.

## What Not To Automate Yet

- Broad fundamentals claims without trusted source rows.
- Applying SEC/manual fundamentals rows without validation and preview.
- Peer relationships inferred only from sector labels.
- Earnings or estimate context from empty optional files.
- Unsupported valuation labels for blocked rows.
- Broad generated CSV churn in the public branch.

The product should get more useful by improving trusted coverage and proof paths, not by filling missing fields with guesses.
