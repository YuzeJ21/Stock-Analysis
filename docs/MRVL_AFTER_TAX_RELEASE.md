# MRVL issuer after-tax reconciliation: release evidence

Date: November 8, 2026 (Toronto). Baseline: `f6e84abb3614f81dc7028df71f0a666e600cc131`. Local implementation verification is complete. The tested commit and GitHub synchronization will be recorded after publication; no remote completion is claimed yet.

## Supported outcome

The existing explicit financial refresh now collects the exact SEC earnings report and furnished exhibit for an independent annual issuer reconciliation. The same MRVL profile and Companyfacts response are reused. At most two additional fixed HTML documents are fetched, without retry, source disk cache, new dependency or ordinary-read transport. A complete financial SEC run uses eight requests: association map, Companyfacts, two submissions, two annual documents, earnings report and exhibit.

The reviewed scope is **issuer-reported FY2026 aggregate GAAP-to-non-GAAP reconciliation for Personal Research inspection**. It is not recurring earnings, a sale-only after-tax EPS calculation, an adjusted P/E denominator, a forecast or an approved economic peer method.

| Exact source | Metadata | Verified role |
| --- | --- | --- |
| [MRVL 8-K](https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/mrvl-20260305.htm) | `0001835632-26-000006`; filed/reported 2026-03-05; CIK `0001835632` | Issuer, form/date, Item 2.02 furnished status and exact Exhibit 99.1 link |
| [Furnished Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/q426_8kx1312026ex-991.htm) | Same accession; year ended 2026-01-31 | Annual column, six signed special items, pretax subtotal, aggregate tax effect, non-GAAP income and separate reported share/EPS observations |
| [Annual 10-K](https://www.sec.gov/Archives/edgar/data/1835632/000183563226000011/mrvl-20260131.htm) | `0001835632-26-000011`; filed 2026-03-11; 2025-02-02 through 2026-01-31 | Independent annual GAAP anchors and actual annual interval |

## Validation boundaries

The year-ended column is distinct from three quarter columns, one of which has the same ending date. Visible title, units, spans, rows and local section context are checked. Reported millions and per-share units remain distinct. The signed subtotal and after-tax income bridge use decimal arithmetic and disclosed precision; dash-zero values do not create artificial rounding uncertainty. Each reported EPS is checked against its own disclosed diluted denominator, without deriving a replacement EPS or individual EPS adjustment.

Each observation retains raw displayed text, original precision, normalized units, scale multiplier, physical table/row/column location, source URL, observation date and raw-response digest. The annual start date is identified as coming from the independent 10-K. New raw payloads are bounded before the parent packet is hashed. Digest, identity, dates, amendments to this report, hidden/conflicting rows, conflicting unit/duration headings and unsupported shapes fail closed. A legitimate unavailable reconciliation source retains independently verified annual fields and AVGO context; a changed cached packet retains the existing integrity hold.

## Product behavior and remaining gaps

Valuation & Peers and Data Sources share one expandable reconciliation. It shows original million-dollar precision, signed adjustments, furnished status, sources and independent gaps. Overview remains clean. Section changes and Monitor return reuse the loaded packet without fetching again. A failed new observation drops its prior verified reconciliation rather than restoring an old verdict.

- The aggregate tax effect does not establish tax attributable to the business-sale gain alone.
- The source does not provide individual after-tax EPS effects for this actual annual bridge.
- Issuer non-GAAP income/EPS is not independently qualified recurring or normalized earnings.
- No alternative valuation denominator, common peer definition or trusted peer role is approved.
- Latest-quarter and cumulative cash-flow scopes remain separate from this annual review.

Annual GAAP EPS, same-day completed closes, 35-day fiscal windows and minimum three qualifying references are unchanged. AVGO's existing annual mismatch is unchanged. Source rights, approved financial fields, saved four-field SEC receipts, exports, readiness, universe and canonical data are unchanged. The new evidence is in-memory Personal Research inspection only; no commercial or redistribution clearance is claimed. Committed fixtures are constructed. Real source observations, document bodies, financial values and screenshots remain private outside Git.

## Verification record

| Check | Exact result |
| --- | --- |
| Protected affected-system regression | **537 passed, 1 existing dependency warning in 58.65s**; command and protected-artifact guard exit 0 |
| Final UI, Workbench and desktop/phone browser regression | **24 passed in 29.92s**; includes the two desktop/phone cases after the original-precision display change |
| Six research routes | Research Desk, Discover, Company Workbench, Monitor, Research Data Health and Research Proof History all passed; protected-artifact guard exit 0 |
| Fresh app health | Dashboard import and actual HTTP health check passed on an isolated port; no environment-limited substitute |
| Commercial-beta contracts | Exit 0; local readiness and external gates remain distinct |
| Live exact-source replay | Fifteen annual observations; zero pretax-subtotal and net-income residuals; both independent reported-EPS rounding checks passed |
| Live layouts | 1440×1000 desktop and 390×844 phone; English, source links, correct million-share scale, exact monetary precision and no horizontal overflow |
| Monitor return | MRVL, Data Sources and loaded observations retained; constructed browser request count remains eight through navigation |
| Unchanged-data proof | All 78 tracked data/config/assets files match baseline; protected data/outputs/docs-assets guard passed |
| Public documentation | README 165 lines; roadmap 320 lines; wording check passed across 64 public files |

The affected regression includes the new reconciliation and collector, original annual review, financial history, unchanged peer engines, integrated Workbench, online notes/evidence workflow and public documentation contracts. Its one warning is the existing python-dateutil UTC deprecation. No tests were skipped in these selected commands.

Baseline affected tests: 161 passed in 1.98s. Parser/collector/review/UI red-green cycles are recorded in the implementation plan. Independent review identified a scale-display mismatch and conflicting local-unit-header acceptance; both were reproduced and fixed with regressions. The composed builder-to-UI path now checks the million-share display, and four different contradictory section headings are rejected. A live desktop check additionally led to original-million precision in the detailed bridge, with a separate regression for amounts above one billion.

Live phone evidence verified a readable 315px-wide, 96px-high caption, correct per-share scale 1, source row/column provenance and wrapped digest text without overflow. The real Data Sources → Monitor → company return preserved the selected section and verified reconciliation. No real notes, saved SEC receipt, canonical record or source-rights decision was written by these checks.

The previous stage's 9,330-pass full run belongs to its own tested code commit. This stage uses the affected parsing, collector, review, existing peer/financial/workflow, UI, browser and documentation regression checks; it does not relabel the previous whole-repository result as a new run. GitHub CI remains PR-triggered. GitHub Pages remains the separate static demonstration; the full Workbench runs locally with online sources. No hosting, paid data, credentials or human-validation claim is added.

## Next executable step

Inspect one independently eligible industry reference's exact annual reconciliation and recurring-cost definitions. Keep issuer-specific adjustments and tax assumptions distinct; do not create a common adjusted multiple until identity, periods, share bases, definitions, prices, minimum reference count and rights separately qualify.
