# Online peer valuation research

## Outcome

Company Workbench can explain whether a company's **reported annual diluted P/E** is above or below a disclosed industry reference median. Show the company, median, signed premium/discount, contributing companies, actual financial periods, price date, sources and every exclusion. This is personal research context, not a fair-value estimate, recommendation or promotion of saved-model readiness.

The user authorized autonomous implementation, automated desktop/phone verification and developer-branch synchronization. Reuse the clean existing linked worktree. No human testers, paid services, new credentials, PR, merge, deployment or publication. The implementation choices below are the executor's decisions within that scope.

## Approaches considered

1. Reuse an online vendor's ready-made trailing multiples. Convenient, but the available snapshot does not establish every denominator's exact definition and reporting window. Do not mix these values into the supported comparison.
2. Calculate one transparent annual P/E from directly filed diluted GAAP EPS and a dated price, with a separately checked vendor filing/CIK link. **Chosen implementation:** precise source lineage and explicit exclusions, with bounded industry candidates. This is a separate research method; existing strict saved comparisons remain unchanged.
3. Add another quote website or paid feed. No configured paid keys exist; the current Nasdaq and Stock Analysis website terms do not establish a permitted automated product-data path. Do not scrape those quote pages or invent permission.

## Evidence and method

- Personal Research only. Commercial mode or invalid mode configuration blocks transport and cached results. No source registry approval, canonical data, journal, readiness or coverage checkpoint changes.
- Reuse the existing official listing classification. Require a unique SEC issuer association, an explicit ordinary/common-share description, one issuer ticker/class, a matching SEC submissions ticker/exchange, operating-company reporting, and a supported provider venue. Funds, wrappers, ADRs, ambiguous classes, blank-check and investment-company reporting stay excluded. Listing identity is not domicile, active status, historical continuity or general analysis eligibility.
- Use `yfinance.Ticker.get_info` and `get_sec_filings` only as a bounded price/context observation under the existing research scope. Hash the normalized returned fields, not a fictional raw HTTP response. Validate the quote symbol, USD currency, venue, timezone, regular-market timestamp and positive price. Require at least one vendor filing link's issuer CIK, accession, date, form and primary document to match independent SEC submissions metadata. Filing-agent accession prefixes are not issuer CIKs.
- Reuse the validated Yahoo daily-price inspection. Its latest completed bar must equal the vendor regular-market observation's date and close; all contributing companies must share that date. Exclude incomplete/current-day, future or more-than-seven-day-old prices. Do not reuse an intraday quote as an earlier close.
- SEC Companyfacts denominator: exactly `us-gaap:EarningsPerShareDiluted`, `USD/shares`, directly reported in the latest available annual filing for its report date. Require a 350–380 day duration, matching accession/form/publication/report end, no conflicting tied values, finite positive EPS, and at most 550 days from annual end to price date. A newer amendment lacking the field stays withheld. Negative/zero EPS is not cheap. No annual-to-TTM inference or adjusted/forecast EPS.
- Reject any observed split after the EPS period end through the source observation, and invalid split evidence; do not invent an adjustment factor. The comparison uses a completed recent price only, not historical return or continuous-security claims.
- Candidate discovery: the subject's vendor industry list, preserving source order and recording truncation, at most **12 other symbols**, no exhaustive industry claim. Individual candidates must independently match the same vendor industry and SEC SIC. At least **three distinct issuers** must pass. This is an **automatically screened industry reference group**, not analyst-approved economic peers. Business mix, growth, profitability, capital needs and risk are not adjusted.
- Each reference's annual start and end boundaries may each differ by at most **35 calendar days from the subject**; references on opposite sides can differ by70 days from one another. Show actual dates and this declared subject-relative window. This accommodates adjacent fiscal calendars without claiming identical periods. Saved comparison's exact-period policy remains unchanged.
- Comparison: subject P/E divided by median accepted peer P/E minus one. Display higher/lower/equal relative multiples with metric-qualified Chinese wording; never an overall overvalued/undervalued score. Protect finite numeric bounds and duplicate issuer/share-class exclusion.
- Keep per-source observations within 24 hours and revalidate cached data on every read. No new network requests on ordinary section changes, including failed attempts. An explicit retry replaces the prior attempt rather than retaining an earlier successful verdict.

## Product integration

Add an explicit **更新在线同行估值** action inside 估值与同行. Share its ticker/CIK-scoped observation with 数据来源. The visible answer leads with the metric, date and supported conclusion; failed or thin groups lead with the blocking reason and qualified count. Tables disclose each included and excluded candidate, actual dates, EPS, price and sources. Missing P/S, P/FCF, EV/EBITDA and TTM remain explicitly withheld.

After an online attempt, keep the existing saved scenario/valuation tools in a clearly labelled separate expander; their inputs, qualification gates and HTML brief are unchanged. Before any online attempt, preserve existing default saved flows. Online-only companies use the same online evidence path without reading same-symbol saved records. No automatic journal or model write.

## Verification and delivery

Pure tests cover identity, reporting/amendment ties, units, dates, splits, negative earnings, fiscal-window boundaries, duplicate issuers, arithmetic and mode/rights boundaries. Transport tests prove candidate/request bounds, explicit action, source failures and cache replacement/revalidation. AppTest and automated browser checks cover saved/online routes, source disclosure, no extra transport on pane changes, responsive desktop/phone layouts and existing saved tools.

Record a live source-backed case or the exact external blockers. Keep receipts/screenshots local; commit source code, synthetic tests and neutral documentation only. Run focused tests, one independent review with regression repairs, then the full guarded suite sequentially. Verify protected hashes, clean staging and exact remote commit after the authorized push; hosted CI is reported separately. Preserve all unrelated work.
