# MRVL peer valuation and earnings review: release evidence

Completed: November 8, 2026 (Toronto); implementation began November 7. Baseline: `15b04442a0e4660d2091f786df5013f6b4a64105`. Tested code commit: [`adefcdbdd54821401914749952312b9406da9c15`](https://github.com/YuzeJ21/Stock-Analysis/commit/adefcdbdd54821401914749952312b9406da9c15), synchronized to GitHub main and independently confirmed by the remote ref. The final README and verification ledger follow as a documentation-only commit; runtime code and tests are unchanged.

## Delivered scope

- The existing explicit financial refresh reuses its Companyfacts response for an independent MRVL annual review. At most two SEC submissions and two exact annual documents are additionally requested. There is no second Companyfacts request, new dependency, manual company CSV preparation, ordinary-read transport or source disk cache.
- Valuation & Peers displays a short annual-earnings caveat near the multiple, linked to expandable earnings quality and a named AVGO business comparison. Data Sources reuses the same evidence. The Overview, existing research tools, Notes and Monitor retain their own scope.
- Seven exact annual concepts cover diluted EPS, net income, total operating cash flow, PP&E purchases, share-based compensation, intangible amortization and disposal gain. Every field retains its exact accession, form, publication date, annual interval, unit, observation and raw response reference. Missing/conflicting/invalid components remain distinct gaps; reported losses and zeros are preserved.
- Named business relevance requires affirmative visible annual disclosures. Negation, exclusions, incidental company mentions and hidden text do not establish either business proof. This is a research relationship, not a trusted core-peer or valuation-anchor approval.
- The annual MRVL and AVGO ends are 90 days apart, exceeding the unchanged 35-day rule. Numeric admission, same-day completed closes, share/issuer identity, split history and minimum three references remain owned by the existing valuation engine.
- Pretax gains, after-tax net income, cash-flow addbacks, annual results, latest-quarter values and cumulative cash flows remain distinct. No adjusted/normalized EPS, FCF or additional multiple is constructed. An independently qualified after-tax reconciliation remains a gap.

## Exact official source scopes

| Scope | Accession | Actual annual interval | Filed | Primary document |
| --- | --- | --- | --- | --- |
| MRVL / CIK 0001835632 / FY2026 | 0001835632-26-000011 | 2025-02-02 to 2026-01-31 | 2026-03-11 | [MRVL 10-K](https://www.sec.gov/Archives/edgar/data/1835632/000183563226000011/mrvl-20260131.htm) |
| AVGO / CIK 0001730168 / FY2025 | 0001730168-25-000121 | 2024-11-04 to 2025-11-02 | 2025-12-18 | [AVGO 10-K](https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm) |

Current submissions must independently select these exact filings. A newer annual, amendment, conflicting identity or changed context retains a source-scope gap. Documents are bound to issuer, annual duration, type and end; actual response digests remain separate from normalized source-subset digests. A broken peer document does not erase valid MRVL annual fields.

## Verification record

| Check | Exact result |
| --- | --- |
| Frozen-source full repository suite, protected-artifact guard | **9,330 passed, 3 skipped, 1 dependency warning in 2,531.33s (42:11)**; command and guard exit 0 |
| Final documentation contracts | **97 passed** after the README next-stage correction; documentation review clean |
| Focused source, integration, existing peer and documentation regression | **451 passed in 61.80s** |
| Desktop/phone browser, UI and Workbench caption regression | **16 passed in 28.00s** |
| Independent final code review | No actionable P1/P2 findings; **181 focused tests passed in 2.84s** |
| Research route rendering | All six routes passed: Research Desk, Discover, Company Workbench, Monitor, Research Data Health, Research Proof History |
| Fresh dashboard instance | Import and HTTP health checks passed on an isolated port; no environment-limited substitute |
| Commercial-beta contracts | Exit 0; local readiness only; external account, operation and source-rights gates remain visible |
| Public wording and staged hygiene | Passed; 63 public text files scanned; no new generated CSV/JSON or canonical data staged |
| Unchanged-data comparison | All 78 tracked files under data/config/assets unchanged from baseline; data, outputs and docs/assets protected-artifact guard passed |

The full command used Python 3.12 in the pinned environment, with bytecode writes disabled: `python -m src.no_write_artifact_guard --project-root . -- python -m pytest tests -q --tb=short --maxfail=5`. Its three skips were the historical real-pair check whose ignored private receipts are absent, and two opt-in live AMD/QCOM checks whose live origin was not configured. The MRVL desktop/phone cases ran and passed. The one warning is an existing python-dateutil UTC deprecation.

Live MRVL checks used 1440 × 1000 desktop and 390 × 844 phone viewports. English content, one company heading, source disclosures, actual peer exclusions and no horizontal overflow were verified. Data Sources → Monitor → return retained MRVL, the selected section and loaded observations. The phone check exposed and verified a caption layout fix (315px wide, 72px high); its red/green browser regression is included above. Live observations and screenshots remain outside Git; no market-price or real financial-value fixture is published here.

The implemented live SEC path has already returned all seven supported annual components and both named document proofs. Existing online valuation was separately exercised with actual same-day completed prices and explicit accepted/excluded references. These private source observations do not establish recurring earnings, valuation suitability, commercial source rights or all-company coverage.

Independent automated review identified a narrative false-positive risk; affirmative visible source checks and negative/hidden-text regressions corrected it. An independent whole-branch review found no remaining actionable P1/P2 issue; its 181 focused tests passed in 2.84s. The frozen-source whole-repository run then passed as recorded above.

## Data and rights

The source-rights registry, approved direct financial fields, saved four-field SEC receipt schema, canonical data, readiness, universe and trusted peer roles remain unchanged. New financial-quality fields and archive material carry Personal Research inspection status, without commercial field authorization or redistribution clearance. Real receipts, document bodies, source-derived output and live screenshots remain private, outside the repository. Committed fixtures are explicitly constructed transport and presentation data.

The full workspace still runs locally with online retrieval. GitHub Pages remains the separate static English demonstration. No hosting, paid feed, credential change or independent human validation is claimed. Repository CI remains pull-request-triggered; a direct main sync is not a new hosted CI result.

## Next executable step

Verify one issuer-reported after-tax earnings reconciliation from an exact SEC-furnished source and assess its period/component definitions independently. Do not turn its availability into a normalized, TTM or forward multiple without a separately qualified method and rights decision.
