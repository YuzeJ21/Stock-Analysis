# Online Company Research

Open Discover, enter a company name or ticker, and press **Search SEC now**. Choose an unambiguous candidate, then press **Check SEC annual facts** in Company Workbench. No per-company CSV preparation is required. The online annual action also runs without a canonical or staged fundamentals file; source-rights configuration remains required.

## Available review

- SEC candidate ticker/CIK association with observation, source modification time and digest.
- Direct annual revenue, operating income, operating cash flow, PP&E cash spending, filing date and share facts when the registered field scope and exact source checks pass.
- Descriptive operating-profit/loss and operating-cash-inflow/outflow observations.
- A direct comparison of operating cash flow and PP&E spending only when the same annual duration, unit, accession, source and observation are established. This comparison is not an issuer-defined free-cash-flow value and does not establish funding adequacy.
- A capability panel showing supported analysis and the exact missing inputs for other lanes.

The adapter is generic across SEC search candidates and has no fixed six-company allowlist. Each result can still be unavailable: some issuers do not report supported standard concepts or USD units, and company-specific taxonomies are outside this adapter. A missing operating field does not become zero or prevent valid sibling fields from being inspected. Continuing-operations cash flow retains that scope and cannot be compared with total PP&E spending. Boolean or string amounts and conflicting same-context raw facts remain withheld before numeric extraction.

## Inputs and boundaries

The user supplies a name or ticker. Online retrieval requires network access and an identifying `SEC_USER_AGENT`; SEC does not require an API key for these endpoints. Requests are explicit and session-scoped, with unavailable attempts reused on normal rerenders. Clicking a result opens an online-only route even when a local ticker row exists; saved issuer identity is not silently assumed.

The financial review validates candidate CIK against Companyfacts, annual duration, publication and observation chronology, source URL, accession, concepts, units, field rights, numeric validity and duplicate fields. No canonical data, readiness report or source-rights registry is updated. The strict CLI comparison retains its existing required-canonical-file behavior.

Registered SEC Companyfacts direct-field scope is distinct from directory identity distribution rights. Raw financial redistribution remains held under the current registry. Numerical margins, free cash flow, valuation and forecasts are not manufactured from these inspection results. The review does not establish current-market interpretation, full U.S. venue coverage, issuer domicile, security type or listing activity.

## Next expansion

1. Add validated historical annual periods and reproducible permitted source receipts for growth and change review.
2. Reconcile dated official listing and issuer receipts, including missing venues, foreign issuers, test issues and inactive securities.
3. Add one permitted price path with observation dates and share-basis checks; then enable only the valuation inputs whose definitions and rights are reviewed.
4. Expand taxonomy and sector support from measured failures. Assess peers and point-in-time consensus separately.

## Source references

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) explains Companyfacts, standard taxonomy and entity-level coverage, units, update timing and fair-access requirements. The live association source is [SEC company ticker/exchange data](https://www.sec.gov/files/company_tickers_exchange.json). Neither API availability nor a ticker association proves complete research support.
