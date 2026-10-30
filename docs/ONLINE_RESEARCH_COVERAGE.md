# Online Research Coverage Method

Discover offers **U.S. listing coverage · online**. **Load U.S. listing inventory** retrieves the complete observed inventory from the Nasdaq Trader nasdaqlisted.txt / otherlisted.txt directory pair and SEC ticker / exchange maps. **Check next 20 issuers** separately inspects the next unique CIK candidates; ordinary rerenders reuse and revalidate session results. No per-company CSV or API subscription is required. Requests need the existing identifying SEC_USER_AGENT.

## Denominators and gaps

All non-test directory rows are retained, including known ETFs, unknown venues and unmatched identities. Exchange-labelled SEC-only records are added and marked with unknown security type / directory status. SEC OTC and null-exchange populations are counted separately. Schema, exact URL, source creation / modification and observation times, byte bounds and raw-byte SHA-256 are inspected. Unknown venue codes remain measurable rather than silently excluded. Dot/dash class aliases are explicit; company names never join identities. Duplicate classes share one CIK probe.

Listing records, resolved CIKs, financial-probe issuer candidates, attempted, failed and unprobed counts remain separate. Known ETF records are excluded from the financial queue; non-ETF and SEC-only status does not prove operating-company eligibility. Unprobed and unknown-industry candidates remain in their denominator. Field coverage uses the latest observed reporting period found in Companyfacts and compatible submissions metadata; older supported values never replace a newer gap.

This is a full **observed inventory**, not a verified census of every U.S. company. LTSE, Green Impact Exchange, NYSE Texas dual listings and remaining registered-venue listing scope retain explicit reconciliation gates. The two Nasdaq directories alone cannot prove every venue or dual listing. Presence establishes neither U.S. domicile, current listing activity, security type, analysis eligibility nor historical point-in-time membership.

## Financial definitions

Bank revenue net of interest expense and aggregate regulated / unregulated utility revenue are supported direct US-GAAP definitions with explicit labels. Customer-contract revenue including or excluding assessed tax stays qualified. No net-interest/noninterest or subsidiary sum is invented; pretax profit does not replace operating income.

IFRS standard revenue, operating profit, operating cash flow and narrowly defined PP&E purchases use a single source reporting currency. A unique non-USD currency in the latest period is preferred to convenience USD translations; ambiguous native currencies are withheld. Native-unit annual, direct-quarter and cumulative/interim periods have independent counters. Six-month / nine-month facts and a 6-K filing alone never establish a single quarter; no FX, ADS ratio, missing Q4, FCF, growth percentage or valuation is inferred. Mixed units, identities, accessions, malformed or later competing publications keep affected fields withheld. Custom or absent taxonomy fields remain gaps.

Counts are availability evidence, not comparisons of amounts or investment signals. The existing twelve-ticker cross-industry sample remains a separate diagnostic, not the full denominator. SIC is the current SEC industry classification, not GICS or domicile.

## Read-only commands

```sh
python3 -m src.online_us_universe
python3 -m src.online_us_universe --batches 1 --batch-size 20
python3 -m src.online_us_universe --scan-all
python3 -m src.online_research_coverage --tickers JPM,DUK,TSM,SAP
```

The first command loads all observed listing records without Companyfacts probes. Batches serialize SEC requests and share one map per inventory. --scan-all attempts the full observed issuer queue and can be lengthy; it never bulk-queries prices. Source failures stay recorded. Inventory observations expire for new probing after 24 hours; load a new inventory to start a new run instead of mixing cutoffs. CLI prints reduced availability evidence without raw financial amounts. Progress is session memory only: refreshing inventory, closing a process or losing the session starts a new run. No raw cache, canonical import or saved-readiness rebuild is performed.

SEC Companyfacts uses the existing registered direct-field scope; raw redistribution remains held. Nasdaq directory and SEC listing/SIC metadata remain distinct unregistered personal-inspection sources. Commercial/non-Personal mode cannot activate or reuse this feature. Code delivery does not distribute captured source data or grant commercial metadata rights.

Sources: [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Nasdaq symbol-directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs), [SEC registered exchanges](https://www.sec.gov/about/divisions-offices/division-trading-markets/national-securities-exchanges).
