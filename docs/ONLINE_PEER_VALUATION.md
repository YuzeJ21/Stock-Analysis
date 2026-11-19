# Online annual P/E and industry references

Open a company, choose **Valuation & Peers**, and select **Refresh peer valuation**. The page requests source observations on that action only. Switching sections reuses the same attempt, including its failures. **Data Sources** shows the same field definitions, actual periods, source links, observation dates and digests. An explicit failed retry withdraws the prior answer.

## Listing-source continuity

Before the action, the page explains that a temporarily unavailable listing source may use a complete classification previously obtained in this session. A refresh makes one classification acquisition attempt, with no automatic retry. Recovery requires all four original source observations to remain within24 hours, neither future-dated nor altered, and directory creation to remain within seven days. A malformed successful packet, source access limit, missing prior receipt or expired receipt keeps the result withheld. There is no disk cache and no automatic import of private captures.

The result distinguishes the latest attempt from the original listing-observation range and directory creation dates. Source details retain safe response status, URL, size and raw digest when available; exceptions and headers are not exposed. Recovery never renews dates or reinstates an earlier financial verdict. The company identity, current financial/price observations and peer rules are checked again. A subsequent financial failure withdraws the old answer even when listing recovery succeeded. Discover uses the same freshness validator for its existing bounded session classification pool.

The five company sections remain the product workflow. Peer-source observations remain session-bound. Company Notes, saved SEC financial receipts and Monitor have their own persistence method; that does not grant retention or distribution rights for peer-source packets.

## What the answer means

The first connected metric is **price divided by directly reported annual diluted GAAP earnings per share**. It is neither trailing-twelve-month nor forecast P/E. Compare its company multiple with the median among at least three qualifying industry references. Premium/discount is company multiple divided by reference median, minus one. A higher multiple is not proof of overvaluation; a lower multiple is not proof of undervaluation. Business mix, growth, profitability, capital needs and risk are not adjusted.

The industry reference group is automatically screened, not analyst-approved economic peers. Candidate discovery follows the price/context provider's industry list, preserving its order, and attempts at most12 other symbols. The page reports the list size, limit, accepted companies and every exclusion. This is not an exhaustive sector benchmark or an investment ranking.

## Consistent definitions and disclosed differences

- The exact denominator is `us-gaap:EarningsPerShareDiluted`, `USD/shares`, in the latest supported annual10-K/20-F or amendment, for a350–380 day duration. No adjusted earnings, quarter arithmetic or TTM inference is used. The annual end must be within550 days of the price date.
- Every reference uses that same definition, USD price/financial currency, the same completed price date, and the same provider industry and SEC SIC. Actual financial start/end boundaries may each differ from the subject by at most35 calendar days. Dates are shown individually; the method does not claim identical fiscal periods. The prior saved comparison retains its stricter exact-period requirements.
- A price must be within seven calendar days. Provider regular-market price/time must match the latest completed daily bar/date, allowing only floating-point encoding precision. The quote cannot postdate either source observation. An intraday quote cannot be treated as an earlier close.
- A vendor SEC filing link must match an independent SEC issuer CIK, accession, form, publication date and primary document. Accession prefixes can identify a filing agent; they are not assumed to be issuer identifiers. Explicit common-share descriptions, one issuer class/ticker and exchange agreement are required. This does not establish domicile, legal security type, active status or historical continuity.
- Post-period splits, insufficient split-history range, ADRs, ambiguous classes, foreign currency, investment companies and unsupported financial definitions remain withheld. Zero/negative EPS is not a cheap P/E. Failed, conflicting, missing, stale and excluded observations are not filled or silently removed from the gap report.
- Same-day annual versions use SEC acceptance timestamps when available. Without a unique supported latest version, or when its EPS is absent, the comparison remains withheld unless the separately bound exact-scope bridge below qualifies. An older original never silently masks an amendment gap.

## Exact AMD amendment scope

A separate AMD-only bridge handles the known2025 annual amendment accession0000002488-26-000021 and original0000002488-26-000018. The [amendment's explanatory note](https://www.sec.gov/Archives/edgar/data/2488/000000248826000021/amd-20251227.htm) limits its change to transposed Client MD&A percentages and affirmatively leaves other disclosures unchanged. Retaining original EPS is a **technical interpretation of that affirmative scope**, not an inference merely because amended EPS is missing, and not a source/legal/commercial approval.

On explicit refresh, both exact primary documents are fetched online and matched to pinned filing-body digests, current SEC identities, report/filed/acceptance dates and inline metadata. Each raw response retains its own verified digest. The body binding removes only the existing SEC empty external tail-script pattern. The current bodies were compared byte for byte with the previously reviewed captures after removing that script. The original's dimensionless annual diluted EPS with divided USD/shares units must independently agree with Companyfacts from that same original accession. A body change, a new annual or amendment, missing scope, conflicting EPS or unavailable source keeps the gap. No EPS value is hardcoded or calculated from earnings/shares.

The amendment has DocumentType10-K/A but AmendmentFlag=false. The page discloses this discrepancy and retains the generic financial parser's rejection; that parser is unchanged. The bridge preserves original financial accession/form/publication identity and shows the amendment separately, with both source URLs, observation dates and digests. Generic amendments and the other financial, security, price, split, period and peer gates remain held. See [industry coverage](PEER_COVERAGE_METHOD.md) for a failure-inclusive declared query sample.

## Earnings context beside the multiple

The page also shows **Earnings change context**: reported current/prior annual diluted EPS from the **same selected accession, form and publication date**. The prior period must end exactly one day before the current period begins and span350–380 days. An older filing's value never substitutes for the comparative printed in the selected filing. Values are latest reported in that observed filing, not point-in-time history or organic earnings growth.

EPS change is current EPS divided by positive prior EPS, minus one. The page shows both values, actual dates and the same source links. A zero/negative base, absent comparative, conflicting value/period/unit or invalid metadata withholds the percentage with a reason. Missing growth context does not remove a valid P/E or change median membership. Historical EPS change is not a forecast, sustainable-growth estimate, PEG or growth-adjusted valuation; business differences remain unadjusted.

Peer collection explicitly requests **two years** of daily prices and split events, with at most800 rows; standalone price-history inspection retains its one-year request and400-row limit. Source URLs and declared ranges must agree. Source details show the actual first/last completed observations: a requested range does not guarantee complete history. If the actual history still begins after annual end, or a later split exists, the ratio remains withheld. No inferred share adjustment or hidden range fallback is used.

## Sources and rights

Official [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) supply submissions and Companyfacts. Standard tags do not eliminate differences in reporting calendars. The collector retains source URLs, original-response digests and separately identified normalized subset digests. It never invents a raw HTTP digest for a public SDK return value.

The installed yfinance public methods provide bounded quote/context, SEC-link and industry-list observations. The existing chart adapter supplies daily prices and observed splits. [Yahoo's adjustment explanation](https://help.yahoo.com/kb/SLN28256.html) describes why share actions matter; this method does not infer a split adjustment. Current source gates are retained: Personal Research only, blocked in commercial or invalid mode, no new source approval, commercial field authorization or redistribution clearance. SEC annual EPS in this independent inspection is not added to the registered commercial field scope.

No alternate quote-page scraping was added. The reviewed [Nasdaq website terms](https://www.nasdaq.com/legal) and [Stock Analysis terms](https://stockanalysis.com/terms-of-use/) did not establish an authorized automated product-data path for this implementation. No paid feed, trial or new credentials are required.

Results stay in session memory and are revalidated on each read. Protected financials, source-rights registry, research ledgers, saved readiness and universe checkpoints remain unchanged. SDK operational caches are managed by the existing library. Screenshots and source-backed delivery receipts are local evidence, not cleared distribution assets.

## Separate saved work and remaining gaps

After an online attempt, **Saved Valuation & Scenarios** retains the prior saved tools, qualifications and input dates separately. Online-only company identities do not read same-symbol saved tools. The offline HTML brief remains a snapshot of its existing saved scope.

TTM/forward P/E, P/S, P/FCF and EV/EBITDA need independent financial, share-count, enterprise-value and component definitions. Custom economic-peer approval, source distribution rights and complete all-company coverage remain separate work. The next evidence expansion should address measured exclusion reasons and specific missing filings, rather than manufacture values for the other measures.

## Selected common securities and identity gaps

A source-bound DUK/JPM/BAC/WFC/C/SO/NEE technical scope can supplement the legacy single-code test. It requires literal common symbols, issuer-bound cover contexts, affirmative annual common-capital/EPS definitions, direct dimensionless annual USD/shares EPS agreeing with Companyfacts, unchanged current metadata and symbol sets, plus all existing price, currency, fiscal, split and peer rules. It does not classify all other issuer-associated codes or infer issuer domicile, legal security status or point-in-time continuity. Sources show each raw response digest separately from an explicitly normalized exact reviewed-body digest; see [Peer coverage method](PEER_COVERAGE_METHOD.md). Changed financial bytes or unreviewed filing versions remain withheld.

NEMCL association, TSM's ADS method and XOM's successor annual earnings basis remain separate gaps. A common title alone cannot admit a wrapper, and a one-for-one security exchange does not authorize splicing annual EPS across issuer identifiers. A single current-declared historical SEC archive may verify an old vendor link while current annual financial selection remains unchanged. Company Workbench's valuation and sources sections explain these source roles and blocked reasons; Discover keeps security-scope evidence separate from qualified annual P/E and comparison counts.

### Duke Energy common-share recheck

The November 18, 2026 review matched `DUK` to Duke Energy Corporation, CIK `0001326160`, and its NYSE common stock. The November 17 SEC 8-K replaced the September cover used for identity. The February 26 10-K remains the FY2025 annual diluted EPS source. The bound filings identify the same common symbol and venue. [November 17 SEC 8-K](https://www.sec.gov/Archives/edgar/data/1326160/000110465926128747/tm2629986d1_8k.htm#Fact000046) · [FY2025 SEC 10-K](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/duk-20251231.htm)

The November 18 Nasdaq Trader directory listed DUK common stock, the Series A depositary shares, DUKB debt and DUKU corporate units as separate NYSE securities. NYSE's dated volume report also shows separate symbols, and its August certification identifies DUKU as corporate units. Workbench requires the title, symbol and venue in the selected SEC cover row to agree with the common-share scope. A preferred row cannot borrow the common title of another row with the same symbol. Other issuer symbols stay outside the DUK annual EPS calculation. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt) · [November 17 NYSE volume report](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261117.pdf#page=52) · [NYSE corporate-units certification](https://www.sec.gov/Archives/edgar/data/1326160/000087666126000683/DUKU081326.pdf)

The same completed-close date, direct annual diluted GAAP EPS, 35-day fiscal window and at least three eligible references still apply. A newer unreviewed SEC identity filing or a conflicting class remains a hold.

The November 18 intraday check verified the selected common share and held the comparison at the completed-close check. The first three refreshes after the bell still returned a quote timestamp before the session ended. Workbench kept the comparison withheld before screening any candidates.

The 4:16 p.m. ET refresh verified the November 18 completed close and screened all 12 candidates. Four qualified with the same close date and the same January–December 2025 period for reported annual diluted GAAP EPS. Eight were excluded at their first failing check. Four had unresolved issuer share classes, three had a different SEC industry code, and one lacked a verified match between the provider filing link and SEC metadata. The accepted companies, exclusions and original source references are available in the Workbench valuation and source disclosures during the research session. [NYSE trading hours](https://www.nyse.com/trade/trading-information)

### November 19 common-share source review

The November 19 Nasdaq Trader other-listed directory verified JPM, DUK, SO and NEE as separate NYSE common-stock listings. The issuer-associated debt, preferred and unit codes remain outside the selected common-share calculation. Each scope binds the literal common row to the parent issuer in the FY2025 annual filing and the latest reviewed SEC cover. [Nasdaq Trader other-listed directory](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt)

| Common share | Parent CIK | Annual diluted EPS filing | Current reviewed cover |
| --- | --- | --- | --- |
| JPM | 0000019617 | [FY2025 10-K](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm) | [November 17 8-K](https://www.sec.gov/Archives/edgar/data/19617/000001961726000407/jpm-20261117.htm) |
| DUK | 0001326160 | [FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/duk-20251231.htm) | [November 19 8-K](https://www.sec.gov/Archives/edgar/data/1326160/000110465926130154/tm2630241d1_8k.htm) |
| SO | 0000092122 | [FY2025 10-K](https://www.sec.gov/Archives/edgar/data/92122/000009212226000006/so-20251231.htm) | [November 17 8-K](https://www.sec.gov/Archives/edgar/data/92122/000009212226000082/so-20261112.htm) |
| NEE | 0000753308 | [FY2025 10-K](https://www.sec.gov/Archives/edgar/data/753308/000075330826000015/nee-20251231.htm) | [November 5 8-K](https://www.sec.gov/Archives/edgar/data/753308/000075330826000084/nee-20261105.htm) |

The November 17 JPM and November 19 DUK covers superseded their previous reviewed covers. SO's annual and current covers show different par values. Its charter amendment changed common par value from $5 to $0.01 while preserving share rights and the authorized share count. The common-share scope keeps the annual EPS period and source unchanged. NEE's cover separately lists corporate units. [SO proxy](https://www.sec.gov/Archives/edgar/data/92122/000009212226000028/so-20260402.htm) · [SO charter amendment](https://www.sec.gov/Archives/edgar/data/92122/000009212226000040/ex31socertificateofamendme.htm)

## Incorporated bank filing documents

Some bank filings distribute cover facts and financial resources across documents explicitly linked in the same accession. The bounded bank scope can inspect one incorporated companion for each annual or latest identity primary: WFC uses its linked EX-13 financial report, and C uses linked EX-99.01 cover exhibits. The primary remains selected by current submissions; an exhibit is never relabelled as the primary or another filing. Exact parent links, safe same-accession paths, original response and reviewed-body digests, freshness, compatible namespaces and globally unique identifiers are required before shared contexts or units can be resolved. Limits are two documents per role, four per scope,32MiB per document and64MiB total. No external XML resource is retrieved.

Only explicitly enumerated WFC exchange facts may be repeated, and every listed unqualified literal must agree in concept, context and value. Other duplicates or changed source versions remain withheld. The selected-cover date reader accepts the exact2022 English month/day/year transformation for the bound C cover; the generic financial transform parser and AMD scope are unchanged. EPS still comes from directly reported entity-only annual USD/shares facts and must agree with Companyfacts from that same accession.

Valuation and sources disclose the primary/companion relationship and individual raw/body digests. Cover, EPS, context, unit and basis links identify the actual supplying document. Companion period/publication metadata is explicitly inherited from its parent filing. These source scopes do not relax the existing minimum-three, industry/SIC, fiscal-window, price-date, currency, split or issuer rules, and do not establish preferred-symbol aliases, independent economic comparability or source rights.


## Cross-security evidence

NEM has a separate exact literal-common scope with explicitly declared dimensionless cover contexts in its annual and latest8-K, direct annual EPS and Companyfacts agreement. A missing independent directory instrument description can be supplemented only by that validated literal security proof; an explicit conflicting security type remains held. NEMCL remains separately associated and is not admitted as an alias or ordinary-price input. Private official FINRA/CDI and SEC security-description reconnaissance records its relationship; this does not add a FINRA runtime feed or establish NEMCL price/currency eligibility.

TSM's exact annual source exposes ordinary and ADS diluted IFRS EPS separately, including native TWD and source-reported USD convenience presentation, with actual class context and units. The source directly reports ADS EPS; the app does not multiply rounded ordinary EPS or apply FX. The ratio and complete convenience/nontrading notes have their own source locations. These are inspection observations and do not enter the ordinary US-GAAP USD annual P/E denominator, median or saved readiness. A general ADS/IFRS/FX comparison method remains separate work.

XOM's exact successor8-K12B and quarter Note1 expose security exchange, registration and financial-reporting continuity. Non-inline prose is located by a body-bound paragraph ordinal and normalized-text digest, with a full-document link rather than an invented DOM fragment. Continued inline notes preserve every actual source fragment. The quarter's predecessor entity context remains distinct from current filing CIK. Current-CIK annual absence and vendor issuer conflict remain independent blockers; predecessor/quarter EPS is not spliced into the current annual method.

## MRVL annual earnings quality and named AVGO context

After **Refresh financials and prices** or **Financials only**, MRVL has a separate **Earnings quality behind annual P/E** review in Valuation & Peers. Data Sources shows the same revalidated evidence. It reuses the financial action's Companyfacts response and requests at most two SEC submissions, two exact annual documents and two exact earnings documents. The latter are attempted only after the existing MRVL profile qualifies the named 8-K; neither Companyfacts nor submissions is fetched a second time for the reconciliation. Quote/listing failures cannot hide independently verified financial components. Section changes and Monitor return reuse the session observation without fetching again.

The first named scope is MRVL FY2026, accession `0001835632-26-000011`, February 2, 2025–January 31, 2026, filed March 11, 2026. Every component matches that accession, annual interval, form, publication date and exact unit: diluted EPS, net income, total operating cash flow, PP&E purchases, share-based compensation, intangible amortization and business-sale gain. Missing or conflicting components retain their own reasons; reported losses and zero values remain observations. Current submissions must still select this exact annual. A changed annual or amendment opens a scope-review gap.

The review explains why a disposal gain can affect reported P/E and why cash flow, compensation and amortization need separate interpretation. It does not subtract a pretax gain from after-tax earnings, construct adjusted EPS, infer a cash-flow multiple or mix the latest quarter with annual/YTD observations. The issuer's aggregate after-tax reconciliation is verified separately for inspection; a gain-only after-tax adjustment and recurring earnings remain unqualified.

MRVL's exact annual names Broadcom in direct competition. AVGO's exact FY2025 annual, accession `0001730168-25-000121`, reports semiconductor and infrastructure-software segments. These affirmative visible disclosures support research relevance with a business-mix caveat. Negated, incidental or hidden text does not establish the relationship. Source links and raw document digests stay available. This does not populate a trusted core-peer role or valuation anchor.

MRVL's January 31, 2026 annual end and AVGO's November 2, 2025 annual end are 90 days apart. The unchanged annual method therefore excludes AVGO under its 35-day rule. The existing peer result continues to own every actual admission, exclusion, same-day price and minimum-three check. Economic relevance is distinct from numerical eligibility.

New quality fields and archive documents retain Personal Research inspection status. The rights registry, registered direct fields, canonical data, saved four-field SEC receipts, exports, peer membership and readiness remain unchanged. No real observations, raw documents or provider screenshots are published by this slice. [MRVL release evidence](MRVL_PEER_EARNINGS_RELEASE.md)

## MRVL issuer after-tax reconciliation

The optional **Issuer after-tax reconciliation** disclosure uses exact SEC 8-K `0001835632-26-000006`, filed/reported March 5, 2026, primary `mrvl-20260305.htm`, and its furnished Exhibit 99.1 `q426_8kx1312026ex-991.htm`. The current submissions metadata, primary issuer/form/date, visible Item 2.02 furnished status and exact exhibit link must agree. An amendment to that report requires review; a different report's unrelated amendment does not erase this qualified source.

The reviewed exhibit's year-ended January 31, 2026 column is separate from the three preceding quarter columns, including a quarter with the same ending date. Title, units, physical spans, visible rows and section context must agree. The start date is anchored to the independently verified 10-K interval; it is not invented as an exhibit disclosure. The exhibit's dollar sign and millions scale are bound to matching annual GAAP USD income and per-share observations.

All six signed special items, the reported pretax subtotal, aggregate income-tax adjustment and issuer non-GAAP income are checked with decimal arithmetic and reporting-precision bounds. The separately reported GAAP/non-GAAP diluted-share denominators and EPS receive independent rounding checks. The UI keeps original millions precision and source locations; it reports issuer EPS rather than constructing an item-level EPS bridge. Missing, hidden, duplicate, conflicting, stale or altered evidence withholds this extension while retaining independently valid annual and AVGO evidence. Old packets without this member retain an explicit gap.

This closes only the **issuer aggregate reconciliation** gap. The table does not allocate tax to the disposal gain alone or disclose individual after-tax EPS effects. The 10-K's statutory-to-effective tax-rate reconciliation is not a total sale-tax allocation. Issuer non-GAAP results are not established recurring earnings, and source arithmetic does not qualify another P/E denominator or common peer definition. Same-day closes, annual GAAP EPS, the 35-day window and minimum three references remain unchanged. Rights, approved fields, saved receipts, exports, readiness and canonical data are unchanged. [After-tax release evidence](MRVL_AFTER_TAX_RELEASE.md)
