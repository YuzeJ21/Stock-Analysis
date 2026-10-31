# Online Company Research

Open Discover, enter a company name or ticker, and press **Search SEC now**. Choose an unambiguous candidate, then press **Check SEC annual facts** in Company Workbench. No per-company CSV preparation is required. The online annual action also runs without a canonical or staged fundamentals file; source-rights configuration remains required.

## Available review

- SEC candidate ticker/CIK association with observation, source modification time and digest.
- Direct annual revenue, operating income, operating cash flow, PP&E cash spending, filing date and share facts when the registered field scope and exact source checks pass.
- Descriptive operating-profit/loss and operating-cash-inflow/outflow observations.
- A direct comparison of operating cash flow and PP&E spending only when the same annual duration, unit, accession, source and observation are established. This comparison is not an issuer-defined free-cash-flow value and does not establish funding adequacy.
- Up to six historical annual periods from the same Companyfacts response, including publication dates, exact concepts and comparable revenue direction. Each period is validated separately; gaps break comparisons. These are latest reported values as observed now, including restatements, and cannot be used as point-in-time backtest inputs.
- Up to twelve directly reported quarter-length periods from that same response. Quarter revenue and operating income stay separate from cumulative cash flow. A valid quarterly path can remain available when annual definitions are unsupported; missing quarters, including Q4, are never inferred by subtraction.
- A separate **Check online price history** action for one year of dated Yahoo provider daily closes, excluding the observation day and retaining split-event context.
- A qualified price/filing listing association using the SEC CIK, current SEC ticker/exchange context and the price provider's explicit symbol/venue metadata. Share-class aliases are explicit; ambiguous venues and conflicting observations remain withheld.
- **Load U.S. listing inventory** and **Check next 20 issuers** actions in Discover, with full observed listing / issuer-candidate denominators, test exclusions, ETF flags, unknown venues, failed / unprobed counts and residual venue gates. A separate explicit **Run online coverage sample** action in Discover, covering a declared twelve-ticker cross-industry sample with SEC SIC classifications, field counts and failure reasons. The sample is not a market-wide denominator. See [Online Coverage Method](ONLINE_RESEARCH_COVERAGE.md).
- A capability panel showing supported analysis and the exact missing inputs for other lanes.

The adapter is generic across SEC search candidates and has no fixed six-company allowlist. Each result can still be unavailable: some issuers do not report supported standard concepts or USD units, and company-specific taxonomies are outside this adapter. A missing operating field does not become zero or prevent valid sibling fields from being inspected. Continuing-operations cash flow retains that scope and cannot be compared with total PP&E spending. Boolean or string amounts and conflicting same-context raw facts remain withheld before numeric extraction.

## Inputs and boundaries

The user supplies a name or ticker. Online retrieval requires network access and an identifying `SEC_USER_AGENT`; SEC does not require an API key for these endpoints. Requests are explicit and session-scoped, with unavailable attempts reused on normal rerenders. Clicking a result opens an online-only route even when a local ticker row exists; saved issuer identity is not silently assumed.

The financial review validates candidate CIK against Companyfacts, annual duration, publication and observation chronology, source URL, accession, concepts, units, field rights, numeric validity and duplicate fields. No canonical data, readiness report or source-rights registry is updated. The strict CLI comparison retains its existing required-canonical-file behavior.

The online wrapper now uses bounded exact-URL SEC JSON receipts with raw-byte digests, duplicate-key/nonfinite rejection and optional source-modification dates. Quarterly inspection pins one supported revenue concept for its newest supported quarter and accepts direct durations of 70–105 days in supported quarterly or annual filings. Six- and nine-month cash-flow evidence requires a matching cumulative revenue context in the same filing; it is labelled with its own full duration. No quarter value is manufactured from cumulative differences. Newer reporting dates elsewhere in the source expose a latest-quarter gap rather than allowing an old revenue tag to appear current. Supported quarterly and annual concepts can differ; their definitions remain explicit and are not numerically joined. Later revisions remain latest-reported observations rather than historical knowledge. A newer identifiable but unusable publication, changed unit or component-only amendment withholds the affected field; an older successful value is not silently restored or joined across accessions. Revision holds retain known competing publication dates.

Registered SEC Companyfacts direct-field scope is distinct from directory identity distribution rights. Raw financial redistribution remains held under the current registry. Percentage growth rates, numerical margins, free cash flow, valuation and forecasts are not manufactured from these inspection results. Direct annual revenue charts and increase/decrease/unchanged comparisons are supported only for matching concepts, units and adjacent non-overlapping annual periods. The review does not establish current-market interpretation, full U.S. venue coverage, issuer domicile, security type or listing activity.

## Industry and foreign-issuer definitions

The same Companyfacts response supports direct bank revenue net of interest expense, regulated / unregulated utility operating revenue and qualified tax-inclusive customer revenue. Each label retains its definition; no aggregate is manufactured by adding components. Operating income stays withheld when only bank pretax income is present.

A separate IFRS view retains one reporting currency and exact standard concepts for annual, direct-quarter and cumulative/interim statements. A single non-USD source currency is preferred to convenience USD translations; multiple plausible native currencies are withheld. No FX conversion, ADS ratio, quarter subtraction or valuation joins are performed. Foreign issuers without supported current standard facts retain dated historical evidence and a latest-period coverage gap; a 6-K date alone cannot create a quarter.

## Exact primary-filing inspection

Open **Exact SEC filing evidence** in Company Workbench, choose **Latest quarter** or **Latest annual**, then press **Check latest SEC filing**. The source selector rechecks the symbol/CIK association and selects the newest matching report and publication from current SEC submissions. The accession may identify a filing agent; the archive directory remains bound to the issuer CIK. A malformed or tied latest amendment is withheld rather than replaced by an older filing. Automatic selection currently supports10-Q and annual10-K/20-F/40-F forms with Inline XBRL, not arbitrary6-K releases.

The separate archive adapter validates the exact primary-document URL, source dates/digest, DEI issuer/form/period, context entity CIK and absence of dimensions/scenarios. Combined utility filings cannot silently contribute subsidiary numbers. Supported namespace URIs, currency measures and numeric transformations/scale/sign/decimals are retained. Invalid/nil/conflicting facts and unsupported/custom concepts remain withheld. IFRS customer-contract revenue retains its definition; a unique non-USD currency is preferred to convenience USD translations. Capital purchases retain their outflow definition without manufacturing FCF or netting other investing items. Quarter and cumulative periods are separate; six-month cash flow never becomes a quarter by subtraction.

SEC archive display is **unregistered personal inspection only**. It does not inherit Companyfacts commercial field approval or authorize raw redistribution, canonical import, saved-readiness changes, valuation or Companyfacts coverage promotion. Ordinary rerenders reuse validated ticker/period-scoped results without new source requests.

The [SEC filing-status guide](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/determine-status-my-filing) explains why a formal filing date can follow acceptance time. Both source fields remain separate, each checked against the report and observation dates; the adapter does not infer publication time or filing deadlines.

## Price inspection scope

`yahoo_chart` is a distinct unregistered exact-source inspection adapter. It does not inherit the `yfinance` registry entry as an approval. Commercial mode and non-Personal routes cannot activate it. Results stay in session memory; no source cache, import, readiness update, numerical price-to-financial join or export is produced. Provider symbol, equity type, USD currency, exchange timezone, raw numeric OHLCV, chronology, duplicate daily bars and split events are validated. Raw source bars that are entirely missing are counted, not filled. The provider close adjustment basis is unverified, so no total return is computed. The displayed price is dated and may be stale; it is not a real-time quote.

After an explicit price or SEC action, the identity panel can inspect the selected CIK's SEC submissions metadata when both sources exist. Supported provider venue aliases must agree with a single SEC issuer exchange and the exact ticker/class association. All four source observations must be within 24 hours of one another. A matched current listing context does not supply an independent vendor issuer identifier, historical security continuity, domicile, active status or valuation eligibility. Company names are not join keys. SEC submissions identity/SIC metadata remains a separate unregistered personal-inspection source; it grants no commercial or redistribution approval.

## Next expansion

1. Expand the exact-primary-filing adapter from measured remaining definition/context gaps; preserve permitted receipt replay and separate point-in-time revision evidence.
2. Reconcile dated official listing and issuer receipts, including missing venues, foreign issuers, test issues and inactive securities.
3. Review exact price-source rights, an independent vendor issuer identifier and adjustment/share basis before any numerical price-to-fundamentals join or valuation. The current listing association is qualified personal inspection only.
4. Extend remaining exact-source definitions from full-inventory probe failures, reconcile residual venues and distinguish foreign reporting cadences. The full observed inventory and bank / utility / IFRS direct paths are implemented; universal field coverage remains unproven. Assess peers and point-in-time consensus separately.

## Source references

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) explains Companyfacts, standard taxonomy and entity-level coverage, units, update timing and fair-access requirements. The live association source is [SEC company ticker/exchange data](https://www.sec.gov/files/company_tickers_exchange.json). Neither API availability nor a ticker association proves complete research support.

The [yfinance documentation](https://ranaroussi.github.io/yfinance/) describes the personal-use boundary for Yahoo data. The direct chart adapter remains a separate source whose commercial and redistribution rights have not been approved.

## Listing descriptions, issuer profiles and non-XBRL bank statements

Use **Check listing and issuer type** for current official directory descriptions and a separately sourced SEC reporting profile. Common/ordinary shares, receipts, preferred, debt, units, warrants, rights, ETF and unknown labels retain their rule and raw description. They do not establish current legal security type; a depositary receipt may carry a common-share directory label. Investment-company or annual forms describe observed reporting, not operating-company eligibility or domicile. Rerenders and company switches perform no source requests.

IBN Latest annual also supports its non-XBRL20-F consolidated Indian-GAAP statements: three directly reported annual columns, native INR-thousands normalized to INR, income/interest definitions, Group-attributable profit, operating cash flow and signed fixed-asset purchases. Exact issuer cover, captions, units, dated column spans, real anchors and table/row/column positions bind each value. Generic revenue/operating income, net-interest arithmetic, FCF, FX/ADS conversion and valuation remain held. The cover ADS disclosure is labelled as filed, independently of current directory descriptions. Other non-XBRL issuers remain unsupported until separately validated. Archive and metadata rights remain unregistered personal inspection only.

## Clear valuation and research paths

Company Workbench displays **Valuation and peers** in its primary flow for saved and online-only companies. It explains the company multiple, peer median, premium or discount and metric-specific compatible-peer count. A higher multiple is not proof of overvaluation. At least three distinct reviewed peer companies, source-backed metric definitions, aligned financial periods, currency and price dates, permitted fields and current quantitative evidence are required. Legacy aggregate medians do not establish these conditions; the current real-company comparison remains withheld where the required evidence is absent. The native illustrative example uses synthetic companies only and cannot change company data or readiness. See [Reading Peer Valuation](READING_PEER_VALUATION.md).

The selected listing/issuer check now projects a separate research path. A fund, warrant, bank SIC, blank-check SIC, operating-entity observation and unknown profile retain their different meaning; none establishes current legal security type, U.S. domicile, activity or analysis eligibility.

Exact inline filings with source-observed bank SIC6021/6022/6029/6035/6036 can expose direct **InterestIncomeExpenseNet** and **NoninterestIncome** in a separate bank-context schema. These are independent reported components; absent generic revenue and operating income remain withheld. Direct quarters and cumulative cash flow retain their own periods. Archive field rights remain unregistered personal inspection only; Companyfacts counts, canonical rows and saved readiness are unchanged.
