# Product decision: turn the company pilot into a reusable review workflow

## Current truth and assessment

Reviewed from clean developer commit `1a3107ffdb0b90b5cf767d6697ccb080136aad21`, matching origin; main remains `95699820ab796cd300bae200d45ef47265158efa`. The preceding full local suite passed 8,876 tests with one skip. Those results describe that commit, not the next implementation; GitHub had no exact-commit hosted run. Current stage evidence is private under outputs/local/multi_company_review_2026-11-03.

The product already supports online company discovery, annual and quarterly financial history, prices, guarded annual reported P/E, five company sections, saved research tools and Monitor. NEM adds portable normalized SEC observations, exact-source gap metadata, unchanged-input comparison and a separate Monitor handoff. The strengths are explicit identity, financial definitions, source dates, rights and missingness. Weaknesses are inconsistent persistence across companies, overlapping online-versus-saved states, limited valuation methods, source acquisition dependencies and a growing maintenance burden of issuer exceptions. Engineering checks do not prove demand or accounting completeness.

## Market comparison

Official product pages checked November 3 UTC / November 2 Toronto, 2026. These are vendor capability claims, not hands-on quality benchmarks.

| Alternative | Published capability | Implication |
| --- | --- | --- |
| [Koyfin](https://www.koyfin.com/features/) | Financial charting and price, valuation, technical and news alerts across watchlists | Competing on another broad dashboard or basic alert list offers little distinction. |
| [Fiscal.ai](https://fiscal.ai/products/terminal/) | Source-linked financials, estimates, filings, transcripts and an auditability claim | Source links alone are not unique; repeatable comparison and explicit exclusions must save research effort. |
| [Stock Analysis](https://stockanalysis.com/pro/) | Long financial histories, watchlists, screeners, alerts and downloads | Breadth and convenient access already have established low-cost competition. |

Our opportunity is a hypothesis: a researcher can query online, preserve a permitted observation, revisit it later, understand whether values or evidence changed and see unresolved tasks across companies. Our risks are narrower source/method coverage, slower workflows, mixed presentation language, source-rights constraints and no measured repeat usage. No claim that competitors lack similar review features is made.

## Adjust now

1. Reuse the NEM receipt/comparator for qualified annual US-GAAP/USD Companyfacts observations across issuers. Persist the SEC ticker-to-CIK association metadata and preserve separate company/profile histories. Do not copy an exact-source NEM exception to other issuers.
2. Make Monitor summarize the companies actually saved, with field gaps, missing comparison baselines, comparable changes and damaged stores kept distinct. These are data-review items, not process events or investment alerts. Keep company-specific return links.
3. Make saved review state easy to recognize: compact receipt labels and a clear next action. Do not spend this stage on another broad visual redesign.
4. Correct the roadmap dependency: an independently changed NEM filing remains an evidence gate for claiming real revision detection; it does not block implementing a reusable contract or independently qualifying another company. No fabricated revisions and no repeated retry of an unchanged absent standard fact.

## Stages and exit criteria

| Stage | Outcome | Evidence and boundaries |
| --- | --- | --- |
| Execute now: reusable company reviews | Qualified companies can save/import/replay/compare with a multi-company Monitor queue | Legacy NEM compatible; new issuer association retained; cross-company/profile/period/unit mixes rejected; real AMD, DUK and NEM checks reported with successes and holds; no universal coverage claim. |
| Next: useful valuation explanations | Explain the reported multiple, comparison date, peer selection rationale and exclusions together | Separate industry references from economic peers, annual from TTM/forward metrics, and issuer from security/ADS/share basis. Qualify price-retention rights before persisting a price-backed verdict. |
| Then: measured coverage and maintenance | A dated coverage matrix with venue, security, issuer, financial, price and method denominators | Reuse existing coverage checkpoints; include failures and unresolved rows; do not equate a queried symbol with complete analysis. Prioritize recurring failure causes instead of ticker-by-ticker exception work. |
| Later: operation and adoption | Repeated complete research cases, reliable refresh and manageable cost | Automated task success and latency can be measured now. Demand, independent accessibility, operated licensing and willingness to pay remain unproven without corresponding evidence. No paid service or deployment is authorized. |

Automated validation remains mandatory. Human testers are not required for this engineering stage, and automated results must not be relabelled as independent user validation.
