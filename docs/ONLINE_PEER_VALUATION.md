# Online annual P/E and industry references

Open a company, choose **估值与同行**, and select **更新在线同行估值**. The page requests source observations on that action only. Switching sections reuses the same attempt, including its failures. **数据来源** shows the same field definitions, actual periods, source links, observation dates and digests. An explicit failed retry withdraws the prior answer.

## What the answer means

The first connected metric is **price divided by directly reported annual diluted GAAP earnings per share**. It is neither trailing-twelve-month nor forecast P/E. Compare its company multiple with the median among at least three qualifying industry references. Premium/discount is company multiple divided by reference median, minus one. A higher multiple is not proof of overvaluation; a lower multiple is not proof of undervaluation. Business mix, growth, profitability, capital needs and risk are not adjusted.

The industry reference group is automatically screened, not analyst-approved economic peers. Candidate discovery follows the price/context provider's industry list, preserving its order, and attempts at most12 other symbols. The page reports the list size, limit, accepted companies and every exclusion. This is not an exhaustive sector benchmark or an investment ranking.

## Consistent definitions and disclosed differences

- The exact denominator is `us-gaap:EarningsPerShareDiluted`, `USD/shares`, in the latest supported annual10-K/20-F or amendment, for a350–380 day duration. No adjusted earnings, quarter arithmetic or TTM inference is used. The annual end must be within550 days of the price date.
- Every reference uses that same definition, USD price/financial currency, the same completed price date, and the same provider industry and SEC SIC. Actual financial start/end boundaries may each differ from the subject by at most35 calendar days. Dates are shown individually; the method does not claim identical fiscal periods. The prior saved comparison retains its stricter exact-period requirements.
- A price must be within seven calendar days. Provider regular-market price/time must match the latest completed daily bar/date, allowing only floating-point encoding precision. The quote cannot postdate either source observation. An intraday quote cannot be treated as an earlier close.
- A vendor SEC filing link must match an independent SEC issuer CIK, accession, form, publication date and primary document. Accession prefixes can identify a filing agent; they are not assumed to be issuer identifiers. Explicit common-share descriptions, one issuer class/ticker and exchange agreement are required. This does not establish domicile, legal security type, active status or historical continuity.
- Post-period splits, insufficient split-history range, ADRs, ambiguous classes, foreign currency, investment companies and unsupported financial definitions remain withheld. Zero/negative EPS is not a cheap P/E. Failed, conflicting, missing, stale and excluded observations are not filled or silently removed from the gap report.
- Same-day annual versions use SEC acceptance timestamps when available. Without a unique supported latest version, or when its EPS is absent, the comparison remains withheld. An older original does not mask an amendment gap.

## Earnings context beside the multiple

The page also shows **盈利变化背景**: reported current/prior annual diluted EPS from the **same selected accession, form and publication date**. The prior period must end exactly one day before the current period begins and span350–380 days. An older filing's value never substitutes for the comparative printed in the selected filing. Values are latest reported in that observed filing, not point-in-time history or organic earnings growth.

EPS change is current EPS divided by positive prior EPS, minus one. The page shows both values, actual dates and the same source links. A zero/negative base, absent comparative, conflicting value/period/unit or invalid metadata withholds the percentage with a reason. Missing growth context does not remove a valid P/E or change median membership. Historical EPS change is not a forecast, sustainable-growth estimate, PEG or growth-adjusted valuation; business differences remain unadjusted.

Peer collection explicitly requests **two years** of daily prices and split events, with at most800 rows; standalone price-history inspection retains its one-year request and400-row limit. Source URLs and declared ranges must agree. Source details show the actual first/last completed observations: a requested range does not guarantee complete history. If the actual history still begins after annual end, or a later split exists, the ratio remains withheld. No inferred share adjustment or hidden range fallback is used.

## Sources and rights

Official [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) supply submissions and Companyfacts. Standard tags do not eliminate differences in reporting calendars. The collector retains source URLs, original-response digests and separately identified normalized subset digests. It never invents a raw HTTP digest for a public SDK return value.

The installed yfinance public methods provide bounded quote/context, SEC-link and industry-list observations. The existing chart adapter supplies daily prices and observed splits. [Yahoo's adjustment explanation](https://help.yahoo.com/kb/SLN28256.html) describes why share actions matter; this method does not infer a split adjustment. Current source gates are retained: Personal Research only, blocked in commercial or invalid mode, no new source approval, commercial field authorization or redistribution clearance. SEC annual EPS in this independent inspection is not added to the registered commercial field scope.

No alternate quote-page scraping was added. The reviewed [Nasdaq website terms](https://www.nasdaq.com/legal) and [Stock Analysis terms](https://stockanalysis.com/terms-of-use/) did not establish an authorized automated product-data path for this implementation. No paid feed, trial or new credentials are required.

Results stay in session memory and are revalidated on each read. Protected financials, source-rights registry, research ledgers, saved readiness and universe checkpoints remain unchanged. SDK operational caches are managed by the existing library. Screenshots and source-backed delivery receipts are local evidence, not cleared distribution assets.

## Separate saved work and remaining gaps

After an online attempt, **已保存的估值与情景分析** retains the prior saved tools, qualifications and input dates separately. Online-only company identities do not read same-symbol saved tools. The offline HTML brief remains a snapshot of its existing saved scope.

TTM/forward P/E, P/S, P/FCF and EV/EBITDA need independent financial, share-count, enterprise-value and component definitions. Custom economic-peer approval, source distribution rights and complete all-company coverage remain separate work. The next evidence expansion should address measured exclusion reasons and specific missing filings, rather than manufacture values for the other measures.
