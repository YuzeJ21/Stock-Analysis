# Online Research Coverage Method

Discover offers **U.S. listing coverage · online**. **Load U.S. listing inventory** retrieves the complete observed inventory from the Nasdaq Trader nasdaqlisted.txt / otherlisted.txt directory pair and SEC ticker / exchange maps. **Check next 20 issuers** separately inspects the next unique CIK candidates; ordinary rerenders reuse and revalidate session results. **Save coverage progress** writes a private reduced checkpoint and **Restore saved coverage** revalidates it without source requests. The default file stays under outputs/local, outside Git. No per-company CSV or API subscription is required. Requests need the existing identifying SEC_USER_AGENT.

## Denominators and gaps

All non-test directory rows are retained, including known ETFs, unknown venues and unmatched identities. Exchange-labelled SEC-only records are added and marked with unknown security type / directory status. SEC OTC and null-exchange populations are counted separately. Schema, exact URL, source creation / modification and observation times, byte bounds and raw-byte SHA-256 are inspected. Unknown venue codes remain measurable rather than silently excluded. Dot/dash class aliases are explicit; company names never join identities. Duplicate classes share one CIK probe.

Listing records, resolved CIKs, financial-probe issuer candidates, attempted, failed and unprobed counts remain separate. Known ETF records are excluded from the financial queue; non-ETF and SEC-only status does not prove operating-company eligibility. Unprobed and unknown-industry candidates remain in their denominator. Field coverage uses the latest observed reporting period found in Companyfacts and compatible submissions metadata; older supported values never replace a newer gap.

The **observed inventory** covers the source union above. It leaves LTSE, Green Impact Exchange, TXSE, NYSE Texas and remaining registered-venue membership to separate reconciliation. The dated Nasdaq Texas review below is separate from this live inventory. Presence establishes neither U.S. domicile, current listing activity, legal security type, analysis eligibility nor historical point-in-time membership.

## Nasdaq Texas dated review

Open **Discover → Coverage studies → U.S. listings** and expand **Show Nasdaq Texas security evidence**. The panel is a dated source review. Opening it needs no source requests, and its counts stay separate from the online listing inventory and financial coverage denominators.

The reviewed set contains **40 securities**. Twelve stock classes across eleven issuers appear on dated SEC filing covers for both Nasdaq and Nasdaq Texas. Twenty-eight ETFs have matching exchange certifications and published effective dates. The two Rush stock classes are counted separately. The venue's former name was Nasdaq BX. Nasdaq Texas, TXSE and NYSE Texas are distinct venues. [SEC listing standards order](https://www.sec.gov/files/rules/sro/bx/2026/34-104907.pdf) · [Nasdaq dual-listing launch](https://ir.nasdaq.com/news-releases/news-release-details/nasdaq-texas-launches-inaugural-dual-listings) · [Nasdaq ETF effective-date notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=ETP2026-175) · [IVS prospectus supplement](https://www.sec.gov/Archives/edgar/data/1771146/000177114626002155/etfot-appliedfinanceivsetf.htm)

The November 5 Forms 10-Q for the quarter ended September 30 confirm that **CSTL and NUTX common stock** was dually registered as filed. CSTL's cover uses a continuation row for the same ticker. NUTX's cover repeats the class and ticker on both rows. Those observations close two of the three admission follow-ups. BWIN admission, first executions, listing continuity, primary listings and a complete dated roster remain open. [CSTL Form 10-Q](https://www.sec.gov/Archives/edgar/data/1447362/000162828026071038/cstl-20260930.htm) · [NUTX Form 10-Q](https://www.sec.gov/Archives/edgar/data/1479681/000162828026070993/nutx-20260930.htm) · [Nasdaq directory definitions](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs)

The November 12 recheck found that BWIN's November 9 Form 10-Q lists its Class A common stock on Nasdaq Global Select Market only. The May exchange certification was conditional on notice of issuance. BWIN's Nasdaq Texas admission and listing history remain unconfirmed. [BWIN Form 10-Q](https://www.sec.gov/Archives/edgar/data/1781755/000178175526000068/bwin-20260930.htm#f-16) · [SEC exchange certification](https://www.sec.gov/Archives/edgar/data/1781755/000087679626000012/BWIN_8A_Cert_1781755.pdf)

The November 12 integration verified 99 affected tests, six research route renders and two responsive browser journeys. Desktop and phone checks confirmed the exact cover links, visible gaps and request-free disclosure. Live inventory loading remains an explicit action. The review adds no records to the inventory, and 89 protected files matched the baseline.

## Financial definitions

Bank revenue net of interest expense and aggregate regulated / unregulated utility revenue are supported direct US-GAAP definitions with explicit labels. Customer-contract revenue including or excluding assessed tax stays qualified. No net-interest/noninterest or subsidiary sum is invented; pretax profit does not replace operating income.

IFRS standard revenue, operating profit, operating cash flow and narrowly defined PP&E purchases use a single source reporting currency. A unique non-USD currency in the latest period is preferred to convenience USD translations; ambiguous native currencies are withheld. Native-unit annual, direct-quarter and cumulative/interim periods have independent counters. Six-month / nine-month facts and a 6-K filing alone never establish a single quarter; no FX, ADS ratio, missing Q4, FCF, growth percentage or valuation is inferred. Mixed units, identities, accessions, malformed or later competing publications keep affected fields withheld. Custom or absent taxonomy fields remain gaps.

Counts are availability evidence, not comparisons of amounts or investment signals. The existing twelve-ticker cross-industry sample remains a separate diagnostic, not the full denominator. SIC is the current SEC industry classification, not GICS or domicile.

## Read-only commands

```sh
python3 -m src.online_us_universe
python3 -m src.online_us_universe --batches 1 --batch-size 20
python3 -m src.online_us_universe --checkpoint /absolute/private/path/coverage.json --batches 25
python3 -m src.online_us_universe --checkpoint /absolute/private/path/coverage.json --resume --batches 5
python3 -m src.online_us_universe --checkpoint /absolute/private/path/coverage.json --resume --scan-all
python3 -m src.online_research_coverage --tickers JPM,DUK,TSM,SAP
```

The first command loads all observed listing records without Companyfacts probes. Batches serialize SEC requests and share one map per inventory. --scan-all attempts the full observed issuer queue and can be lengthy; it never bulk-queries prices. Source failures stay recorded. Inventory observations expire for new probing after 24 hours; load a new inventory to start a new run instead of mixing cutoffs. CLI prints reduced availability evidence without raw financial amounts. Without an explicit checkpoint, progress is session memory only. Explicit checkpoints retain normalized inventory/map metadata, reduced field-availability rows and source references, never raw Companyfacts/filing bodies or financial amounts. Resume uses the same inventory fingerprint and contract, preserving unique CIK counts and source failures. It does not claim past browser-only observations were saved. Refreshing inventory starts a distinct run. No raw cache, canonical import or saved-readiness rebuild is performed.

SEC Companyfacts uses the existing registered direct-field scope; raw redistribution remains held. Nasdaq directory and SEC listing/SIC metadata remain distinct unregistered personal-inspection sources. Commercial/non-Personal mode cannot activate or reuse this feature. Code delivery does not distribute captured source data or grant commercial metadata rights.

Sources: [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Nasdaq symbol-directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs), [SEC registered exchanges](https://www.sec.gov/about/divisions-offices/division-trading-markets/national-securities-exchanges).

## Checkpoint and source-access boundaries

The local POSIX writer uses0600 files, an exclusive file lock, expected-content-digest checks, atomic replacement/fsync and a byte-exact .previous.json backup. It refuses canonical/config/code destinations, symlink targets, unrelated existing files, corruption and incompatible schemas/contracts. A failed replacement preserves the prior checkpoint. A restored snapshot can be inspected after its probing window expires; further source requests require a fresh inventory. Metadata authenticity and source rights are not established by a local content digest.

HTTP403/429/503 pauses later issuer requests, records the affected failed observation and keeps the full denominator/unprobed remainder. The source access pause is retained in the checkpoint. No request is made before its recorded resume time; resumption remains explicit. A previously blocked issuer remains a recorded failed first-pass observation, rather than being counted twice. The default SEC transport throttles failed requests too. No credentials, paid feeds or anti-block workarounds are introduced.

Exact-primary-filing inspection is separate from the Companyfacts field counters shown here. The archive source remains personal-only and does not promote saved readiness or these registered-source coverage metrics.

## Separate security-description classification

Discover can **Classify observed listings**, then filter by symbol or description without refetching. A new classification snapshot has its own official source dates and denominator; it does not rebase or relabel the saved financial census. Source-declared ETF flags and deterministic description rules produce qualified labels with unknown/composite/conflicting records retained. SEC-only issuer names are insufficient security descriptions. Unit/warrant/right/receipt labels preserve their wrapper role instead of selecting underlying common shares. Current legal type, issuer domicile, listing activity, analysis eligibility and point-in-time membership stay unresolved. Selected-company SEC reporting forms and SIC remain independently inspectable even when financial evidence is held. A complete attempted queue is a measured availability pass, not complete all-company analysis.
