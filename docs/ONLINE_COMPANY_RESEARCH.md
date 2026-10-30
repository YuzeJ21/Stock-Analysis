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
- An explicit **Run online coverage sample** action in Discover, covering a declared twelve-ticker cross-industry sample with SEC SIC classifications, field counts and failure reasons. The sample is not a market-wide denominator. See [Online Coverage Method](ONLINE_RESEARCH_COVERAGE.md).
- A capability panel showing supported analysis and the exact missing inputs for other lanes.

The adapter is generic across SEC search candidates and has no fixed six-company allowlist. Each result can still be unavailable: some issuers do not report supported standard concepts or USD units, and company-specific taxonomies are outside this adapter. A missing operating field does not become zero or prevent valid sibling fields from being inspected. Continuing-operations cash flow retains that scope and cannot be compared with total PP&E spending. Boolean or string amounts and conflicting same-context raw facts remain withheld before numeric extraction.

## Inputs and boundaries

The user supplies a name or ticker. Online retrieval requires network access and an identifying `SEC_USER_AGENT`; SEC does not require an API key for these endpoints. Requests are explicit and session-scoped, with unavailable attempts reused on normal rerenders. Clicking a result opens an online-only route even when a local ticker row exists; saved issuer identity is not silently assumed.

The financial review validates candidate CIK against Companyfacts, annual duration, publication and observation chronology, source URL, accession, concepts, units, field rights, numeric validity and duplicate fields. No canonical data, readiness report or source-rights registry is updated. The strict CLI comparison retains its existing required-canonical-file behavior.

The online wrapper now uses bounded exact-URL SEC JSON receipts with raw-byte digests, duplicate-key/nonfinite rejection and optional source-modification dates. Quarterly inspection pins one supported revenue concept for its newest supported quarter and accepts direct durations of 70–105 days in supported quarterly or annual filings. Six- and nine-month cash-flow evidence requires a matching cumulative revenue context in the same filing; it is labelled with its own full duration. No quarter value is manufactured from cumulative differences. Newer reporting dates elsewhere in the source expose a latest-quarter gap rather than allowing an old revenue tag to appear current. Supported quarterly and annual concepts can differ; their definitions remain explicit and are not numerically joined. Later revisions remain latest-reported observations rather than historical knowledge.

Registered SEC Companyfacts direct-field scope is distinct from directory identity distribution rights. Raw financial redistribution remains held under the current registry. Percentage growth rates, numerical margins, free cash flow, valuation and forecasts are not manufactured from these inspection results. Direct annual revenue charts and increase/decrease/unchanged comparisons are supported only for matching concepts, units and adjacent non-overlapping annual periods. The review does not establish current-market interpretation, full U.S. venue coverage, issuer domicile, security type or listing activity.

## Price inspection scope

`yahoo_chart` is a distinct unregistered exact-source inspection adapter. It does not inherit the `yfinance` registry entry as an approval. Commercial mode and non-Personal routes cannot activate it. Results stay in session memory; no source cache, import, readiness update, numerical price-to-financial join or export is produced. Provider symbol, equity type, USD currency, exchange timezone, raw numeric OHLCV, chronology, duplicate daily bars and split events are validated. Raw source bars that are entirely missing are counted, not filled. The provider close adjustment basis is unverified, so no total return is computed. The displayed price is dated and may be stale; it is not a real-time quote.

After an explicit price or SEC action, the identity panel can inspect the selected CIK's SEC submissions metadata when both sources exist. Supported provider venue aliases must agree with a single SEC issuer exchange and the exact ticker/class association. All four source observations must be within 24 hours of one another. A matched current listing context does not supply an independent vendor issuer identifier, historical security continuity, domicile, active status or valuation eligibility. Company names are not join keys. SEC submissions identity/SIC metadata remains a separate unregistered personal-inspection source; it grants no commercial or redistribution approval.

## Next expansion

1. Add reproducible permitted receipt replay and point-in-time revision evidence to the annual and reported-quarter paths.
2. Reconcile dated official listing and issuer receipts, including missing venues, foreign issuers, test issues and inactive securities.
3. Review exact price-source rights, an independent vendor issuer identifier and adjustment/share basis before any numerical price-to-fundamentals join or valuation. The current listing association is qualified personal inspection only.
4. Expand taxonomy and industry support from the measured sample failures, then measure a dated broad U.S. denominator. Assess peers and point-in-time consensus separately.

## Source references

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) explains Companyfacts, standard taxonomy and entity-level coverage, units, update timing and fair-access requirements. The live association source is [SEC company ticker/exchange data](https://www.sec.gov/files/company_tickers_exchange.json). Neither API availability nor a ticker association proves complete research support.

The [yfinance documentation](https://ranaroussi.github.io/yfinance/) describes the personal-use boundary for Yahoo data. The direct chart adapter remains a separate source whose commercial and redistribution rights have not been approved.
