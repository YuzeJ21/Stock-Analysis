# Online Research Coverage Method

Discover offers **U.S. listing coverage · online**. **Load U.S. listing inventory** retrieves the complete observed inventory from the Nasdaq Trader nasdaqlisted.txt / otherlisted.txt directory pair and SEC ticker / exchange maps. **Check next 20 issuers** separately inspects the next unique CIK candidates; ordinary rerenders reuse and revalidate session results. **Save coverage progress** writes a private reduced checkpoint and **Restore saved coverage** revalidates it without source requests. The default file stays under outputs/local, outside Git. No per-company CSV or API subscription is required. Requests need the existing identifying SEC_USER_AGENT.

## Denominators and gaps

All non-test directory rows are retained, including known ETFs, unknown venues and unmatched identities. Exchange-labelled SEC-only records are added and marked with unknown security type / directory status. SEC OTC and null-exchange populations are counted separately. Schema, exact URL, source creation / modification and observation times, byte bounds and raw-byte SHA-256 are inspected. Unknown venue codes remain measurable rather than silently excluded. Dot/dash class aliases are explicit; company names never join identities. Duplicate classes share one CIK probe.

Listing records, resolved CIKs, financial-probe issuer candidates, attempted, failed and unprobed counts remain separate. Known ETF records are excluded from the financial queue; non-ETF and SEC-only status does not prove operating-company eligibility. Unprobed and unknown-industry candidates remain in their denominator. Field coverage uses the latest observed reporting period found in Companyfacts and compatible submissions metadata; older supported values never replace a newer gap.

The **observed inventory** covers the source union above. The dated Nasdaq Texas, NYSE Texas, Texas Stock Exchange, LTSE and Green Impact Exchange reviews below have their own scopes. Remaining registered-venue membership is tracked separately. Presence establishes neither U.S. domicile, current listing activity, legal security type, analysis eligibility nor historical point-in-time membership.

## Dated venue reviews

Open **Discover → Coverage studies → U.S. listings** for the five-venue summary. Each row gives the review date, the count supported for that sample or directory and the open gaps. Expand the individual checks below for filings and exchange sources. The NYSE Texas and LTSE rows show the completed November 12 filing reviews. Results from a new session check appear in the respective detail panel.

The venue reviews cover different dates and populations, and a security can be listed on multiple venues. The U.S. listing inventory below the reviews has its own sources, loading controls and coverage counts. Full U.S. coverage remains unverified.

The summary passed 149 affected tests, six research route checks and automated desktop and phone checks. Both browser runs confirmed that opening the summary made no source requests and that the dated counts stayed visible through the filing checks and an unavailable inventory response. All 89 protected files matched the baseline.

## Nasdaq Texas dated review

Open **Discover → Coverage studies → U.S. listings** and expand **Show Nasdaq Texas security evidence**. The panel is a dated source review. Opening it needs no source requests, and its counts stay separate from the online listing inventory and financial coverage denominators.

The reviewed set contains **40 securities**. Twelve stock classes across eleven issuers appear on dated SEC filing covers for both Nasdaq and Nasdaq Texas. Twenty-eight ETFs have matching exchange certifications and published effective dates. The two Rush stock classes are counted separately. The venue's former name was Nasdaq BX. Nasdaq Texas, TXSE and NYSE Texas are distinct venues. [SEC listing standards order](https://www.sec.gov/files/rules/sro/bx/2026/34-104907.pdf) · [Nasdaq dual-listing launch](https://ir.nasdaq.com/news-releases/news-release-details/nasdaq-texas-launches-inaugural-dual-listings) · [Nasdaq ETF effective-date notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=ETP2026-175) · [IVS prospectus supplement](https://www.sec.gov/Archives/edgar/data/1771146/000177114626002155/etfot-appliedfinanceivsetf.htm)

The November 5 Forms 10-Q for the quarter ended September 30 confirm that **CSTL and NUTX common stock** was dually registered as filed. CSTL's cover uses a continuation row for the same ticker. NUTX's cover repeats the class and ticker on both rows. Those observations close two of the three admission follow-ups. BWIN admission, first executions, listing continuity, primary listings and a complete dated roster remain open. [CSTL Form 10-Q](https://www.sec.gov/Archives/edgar/data/1447362/000162828026071038/cstl-20260930.htm) · [NUTX Form 10-Q](https://www.sec.gov/Archives/edgar/data/1479681/000162828026070993/nutx-20260930.htm) · [Nasdaq directory definitions](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs)

The November 12 recheck found that BWIN's November 9 Form 10-Q lists its Class A common stock on Nasdaq Global Select Market only. The May exchange certification was conditional on notice of issuance. BWIN's Nasdaq Texas admission and listing history remain unconfirmed. [BWIN Form 10-Q](https://www.sec.gov/Archives/edgar/data/1781755/000178175526000068/bwin-20260930.htm#f-16) · [SEC exchange certification](https://www.sec.gov/Archives/edgar/data/1781755/000087679626000012/BWIN_8A_Cert_1781755.pdf)

The November 12 integration verified 99 affected tests, six research route renders and two responsive browser journeys. Desktop and phone checks confirmed the exact cover links, visible gaps and request-free disclosure. Live inventory loading remains an explicit action. The review adds no records to the inventory, and 89 protected files matched the baseline.

## NYSE Texas filing reconciliation

Open **Discover → Coverage studies → U.S. listings → NYSE Texas listing check**. The check covers five selected securities. Dated Form 8-K covers report dual registration for the exact common-share classes of ICE, HAL, ABT and OIS. Each cover names NYSE Texas and the New York Stock Exchange. The check binds the accession, issuer CIK, form and primary document to SEC submissions metadata, then checks the visible security row. [ICE Form 8-K](https://www.sec.gov/Archives/edgar/data/1571949/000110465926119880/tm2628301d1_8k.htm) · [HAL Form 8-K](https://www.sec.gov/Archives/edgar/data/45012/000004501226000069/hal-20261015.htm) · [ABT Form 8-K](https://www.sec.gov/Archives/edgar/data/1800/000110465926099247/tm2623675d1_8k.htm) · [OIS Form 8-K](https://www.sec.gov/Archives/edgar/data/1121484/000112148426000036/ois-20261030.htm)

DIT's August 12 Form 8-A identifies AMCON's $0.01 par-value common stock and its NYSE American listing. The exchange certification approves the same class for NYSE Texas. The August 12 Form 8-K names **August 13, 2026** as the announced effective date and describes commencement as anticipated. The November 9 Form 10-K separately lists both venues for DIT's same common stock. Its November 6 close is reported for the exchanges collectively. [Form 8-A](https://www.sec.gov/Archives/edgar/data/928465/000110465926094454/tm2622611d1_8a12b.htm) · [Exchange certification](https://www.sec.gov/Archives/edgar/data/928465/000087688226000018/DIT081226.pdf) · [August Form 8-K](https://www.sec.gov/Archives/edgar/data/928465/000110465926094451/tm2622611d2_8k.htm) · [November Form 10-K](https://www.sec.gov/Archives/edgar/data/928465/000110465926124512/dit-20260930x10k.htm)

The DIT filing check retains the raw response digest and verifies the reviewed body. The PDF certificate uses its full response bytes. HTML verification excludes only the existing SEC empty external tail script. The 10-K cover check independently matches the common-share row and both exchanges.

The official NYSE Texas dual-listing table displayed DIT on November 12, with NYSE American as its primary exchange. November 12 is the browser observation date. The table supplies no as-of timestamp or listing history. Discover shows the dated observation and links to the exchange. [NYSE Texas dual listings](https://www.nyse.com/markets/nyse-texas#listed)

**DIT's first execution remains unverified.** The November 12 review searched August exchange notices for AMCON, DIT and NYSE Texas and found no dated execution confirmation. The public TAQ sample index lists July 1 and 2 files. The August 13 short-volume report and the July and August Rule 605 reports cover limited populations and supplied no dated DIT execution. NYSE Texas can trade securities under unlisted trading privileges, so a listing date alone does not establish when its first execution occurred. The five-security sample stays separate from the live inventory, and the full dated venue roster remains open. [NYSE TAQ catalog](https://www.nyse.com/market-data/historical/taq-trades) · [Public sample index](https://ftp.nyse.com/Historical%20Data%20Samples/TAQ%20NYSE%20TEXAS%20TRADES/) · [Short-volume report](https://ftp.nyse.com/ShortData/Texasshvol/Texasshvol2026/Texasshvol202608/Texasshvol20260813.pdf) · [Rule 605 reports](https://www.nyse.com/trade/reports/rule-605#nyse-texas) · [Exchange notices](https://www.nyse.com/trader-update/history) · [SEC notice on unlisted trading privileges](https://www.sec.gov/files/rules/sro/nysetex/2026/34-105815.pdf)

The November 12 integration replayed 13 captured SEC responses and verified all five sample registrations as filed. It passed 221 affected tests and both desktop and phone journeys. Both browser runs verified the exact source links, the first-trade gap, and request-free navigation. The listing inventory still requires its own explicit load. All 89 protected files matched the baseline.

## Texas Stock Exchange (TXSE) listing reconciliation

Open **Discover → Coverage studies → U.S. listings → Texas Stock Exchange (TXSE) listing check**. Texas Stock Exchange LLC, NYSE Texas and Nasdaq Texas are distinct venues. The SEC granted TXSE's exchange registration on September 30, 2025. TXSE scheduled its first live symbols for July 10, 2026 and confirmed completion of its production rollout on July 31. It separately reported the first primary-listed ETFs on September 16 and its first corporate primary listings on October 5. [SEC registration order](https://www.sec.gov/files/rules/other/2025/34-104146.pdf) · [July rollout schedule](https://www.txse.com/alerts/july-2026-symbol-rollout-schedule) · [July 31 exchange confirmation](https://www.txse.com/press/texas-stock-exchange-celebrates-successful-launch-of-trading) · [ETF start](https://www.txse.com/press/texas-stock-exchange-celebrates-transfer-of-texas-capital-s-txs-and-oilt-exchange-traded-funds) · [Corporate listing start](https://www.txse.com/press/texas-stock-exchange-celebrates-move-of-energy-transfer-partnership-s-primary-listings)

**July 10 first-execution date remains unverified.** The July 10 TXSE symbol file makes five non-test symbols eligible and the Cboe daily file reports 100 trades and 4,797 shares for TXSE that day. July 10 is the earliest positive TXSE row in the reviewed file. Its July 6–9 TXSE rows are missing. The exchange notices reviewed supplied no explicit first-execution confirmation, and the Market Data Center describes execution feeds without a public July 10 trade file in the reviewed catalog. The July Rule 605 download returned HTTP 403 on November 12. The index describes monthly reports. [July 10 symbol file](https://download.web.txse.com/historical/symbols/public_symbols_2026_07_10.txt) · [TXSE notices](https://www.txse.com/alerts-notices) · [Cboe daily file](https://cdn.cboe.com/resources/us/equities/market-statistics/historical-market-volume/market_history_2026.csv) · [Market Data Center](https://www.txse.com/market-data) · [Rule 605 index](https://www.txse.com/regulations/605-reports)

**November 3 baseline.** The exchange directory contained 23 security classes with supporting SEC filings, including ten ETFs. The November 4 TXSE symbol file and Nasdaq directory agreed on 22 primary listings after test issues were excluded. SCHW common stock was the separate secondary listing. Its October 15 Form 8-K names both the New York Stock Exchange and TXSE, and the exchange's market-action record gives an October 7 admission date. [November 4 TXSE symbols](https://download.web.txse.com/historical/symbols/public_symbols_2026_11_04.txt) · [SCHW market action](https://download.web.txse.com/calf/TXSE_MAF/2026/10/TXSE_MAF_20261006_2000_FINAL_NO_CUSIP.csv) · [SCHW SEC cover](https://www.sec.gov/Archives/edgar/data/316709/000031670926000035/schw-20261015.htm)

**November 12 follow-up.** The dated TXSE directory showed 25 securities, including ten ETFs. The November 12 TXSE symbol file had 24 non-test rows flagged `TXSEListed=Y`, with matching ETF flags in Nasdaq's same-day `F` rows after mapping `ET$I`, `CFR$B`, and `TXCP$B` to their exact TXSE suffixes. The TXSE file's 68 test rows and Nasdaq's four `F` test rows were excluded. SCHW remained the additional secondary listing. [TXSE directory](https://www.txse.com/listings/all-listings) · [November 12 TXSE symbols](https://download.web.txse.com/historical/symbols/public_symbols_2026_11_12.txt) · [Nasdaq directory](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt)

The two additional classes are **CFR common stock** and **CFR-PRB depositary shares**, each depositary share representing 1/40 of Cullen/Frost's Series B preferred stock. The November 9 SEC filing and exchange certificate establish both classes. TXSE's November 10 notice gives the November 12 transfer date. **TXCP and TXCP-PRB** are the November 9 successor symbols for the existing Texas Capital classes. They preserve the same identities and add zero listings to the count. [Cullen/Frost Form 8-A](https://www.sec.gov/Archives/edgar/data/39263/000003926326000060/draftform8-a81326.htm) · [Cullen/Frost exchange certificate](https://www.sec.gov/Archives/edgar/data/39263/000205484726000049/CFR8ACert.pdf) · [TXSE transfer notice](https://www.txse.com/alerts/df5469eb-88f0-4850-9a25-1eb2d217df1f) · [Texas Capital symbol change](https://www.txse.com/press/texas-stock-exchange-celebrates-transfer-of-texas-capital-s-primary-listing)

The Discover review opens without source requests and stays separate from the live inventory. It keeps the two listing dates, exact security classes and source links visible. Later roster changes, continuous membership and the first venue execution require their own evidence.

The integration passed 130 affected tests, six research route checks, and automated desktop and phone journeys. The browser checks opened both TXSE disclosures and verified the retained Nasdaq Texas and NYSE Texas workflows. All 89 protected files matched the baseline.

## LTSE filing reconciliation

Open **Discover → Coverage studies → U.S. listings → LTSE listing check** and select **Check LTSE filings**. The check binds each issuer's CIK, accession, form, date and primary document to SEC submissions metadata. It verifies the exact ticker, common-stock class and both venues in the filing's visible registration grid. Evidence is scoped to the filing date.

| Security | Class | Companion exchange | Exact SEC cover |
| --- | --- | --- | --- |
| ASAN | Class A common stock | NYSE | [November 10, 2026 Form 8-K](https://www.sec.gov/Archives/edgar/data/1477720/000162828026072757/asan-20261106.htm), report date November 6 |
| TDUP | Class A common stock | Nasdaq | [November 4, 2026 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1484778/000148477826000033/tdup-20260930.htm) |
| BLX | Class E common stock | NYSE | [April 20, 2026 Form 20-F](https://www.sec.gov/Archives/edgar/data/890541/000162828026026056/blx-20251231.htm) |

Bladex's June 8 Form 6-K records the issuer's name change to Bladex, Inc., effective June 4, and says the outstanding securities were unaffected. The October earnings Form 6-K uses the NYSE ticker label in narrative. The November 12 interim statements have no venue designation. Both later forms lack a Section 12(b) exchange grid. Discover keeps the name change and venue evidence separate. [June Form 6-K](https://www.sec.gov/Archives/edgar/data/890541/000162828026041363/a6knamechancebladexinc.htm) · [October Form 6-K](https://www.sec.gov/Archives/edgar/data/890541/000162828026067951/bancolatinoamericano6-k.htm) · [November Form 6-K](https://www.sec.gov/Archives/edgar/data/890541/000162828026073340/blxefstrimestralinglswdata.htm)

On November 12, the exchange's spotlight featured the three companies. The October 19 SEC notice describes LTSE's dual-listing model, and the filed Exhibit N says the listing schedule is available on request. The reviewed public material leaves current venue status for each security and the complete dated roster unverified. [LTSE spotlight](https://ltse.com/listings/listed-companies) · [SEC dual-listing notice](https://www.sec.gov/files/rules/sro/ltse/2026/34-106695.pdf) · [Exhibit N](https://www.sec.gov/Archives/edgar/vprr/2401/24010775.pdf#page=46)

The November 12 review found no matching registration or removal notice in the reviewed exchange indexes or SEC full-text search. The exchange indexes extended through November 6 for market announcements and August 31 for regulatory circulars. The SEC search covered selected registration and removal forms dated April 20 through November 12. Discover separately screens issuer submissions after each cover's acceptance. The captured screen found zero later filings for ASAN, one for TDUP, and 18 for BLX, with zero registration or removal form candidates. Any future candidate still requires security-class and venue review. [LTSE notices](https://ltse.com/trading/customer-notices) · [SEC full-text search](https://www.sec.gov/edgar/search/)

The audit keeps reduced evidence in the session. It leaves the live inventory, financial coverage and analysis eligibility separate.

The integration replayed seven captured SEC responses and verified all three dated covers. It passed 203 affected tests, six research route checks, and both desktop and phone browser journeys. The browser checks exercised the explicit SEC action and confirmed request-free disclosure and navigation. All 89 protected files matched the baseline.

## Green Impact Exchange launch and listing review

Open **Discover → Coverage studies → U.S. listings → Green Impact Exchange (GIX) listing check**. The review is dated November 12, 2026. The SEC granted Green Impact Exchange, LLC national securities exchange registration on April 11, 2025, subject to conditions before operations could begin. The approved rules described dual listings and trading under unlisted trading privileges. Those activities require separate evidence. [SEC registration order](https://www.sec.gov/files/rules/other/2025/34-102853.pdf)

**Trading start and first execution remain unverified.** The June 10 SEC notice records that GIX had yet to begin trading as of its May 28 filing. On July 1, GIX targeted Q1 2027 for its trading platform. The undated homepage still showed H2 2026 on November 12. The reviewed SEC rulemaking index and GIX news, trading and regulatory pages supplied no actual opening confirmation or execution record. [SEC trading-rule notice, footnote 17](https://www.sec.gov/files/rules/sro/gix/2026/34-105650.pdf#page=4) · [SEC GIX rulemaking index](https://www.sec.gov/rules-regulations/self-regulatory-organization-rulemaking/national-securities-exchanges/all-years?sro_organization=345326) · [July 1 GIX release](https://www.tradegix.com/news/gix-appoints-sara-dillon-as-chief-technology-officer) · [GIX homepage](https://www.tradegix.com/) · [GIX news](https://www.tradegix.com/news) · [GIX trading](https://www.tradegix.com/trading) · [GIX regulatory](https://www.tradegix.com/regulatory)

**Current listing count is unknown.** The review verified zero specific GIX security identities and added zero inventory records. The May 9, 2024 Exhibit N reported that no securities traded on GIX at that time. On November 12, the exchange listing page described eligibility and application materials. It supplied no complete dated roster or issuer, ticker and class tied to an effective GIX listing. [SEC Exhibit N](https://www.sec.gov/files/rules/other/2024/exhibit-n-green-impact-exchange-llc.pdf) · [GIX listing page](https://www.tradegix.com/listing)

An exact-name EDGAR search returned zero matches in Forms 8-A12B, CERT, 25 and 25-NSE and their amendments, from April 11, 2025 through November 12, 2026. Alternate names, paper filings and unindexed exhibits can fall outside that search. The review stays separate from the live listing inventory and financial coverage denominators. [EDGAR search result](https://efts.sec.gov/LATEST/search-index?q=%22Green+Impact+Exchange%22&dateRange=custom&startdt=2025-04-11&enddt=2026-11-12&forms=8-A12B%2C8-A12B%2FA%2CCERT%2CCERT%2FA%2C25%2C25-NSE%2C25%2FA%2C25-NSE%2FA)

The integration passed 148 affected tests, six research route checks and two automated browser journeys at desktop and phone sizes. The browser checks verified source links, visible gaps and request-free opening of the GIX panel. All 89 protected files matched the baseline.

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

### SEC-only listings and unresolved types

Open **Discover → Coverage studies → Security types → Listing gap review** for the November 12, 2026 findings. The production classifier replayed the four captured official sources and counted **13,791** records after excluding 38 test issues. Of the 826 records with unknown type, **544** came from the SEC exchange map without a confirmed directory join and **282** came from the directories. The directory gaps comprise 246 descriptions without recognized instrument wording, 19 ambiguous descriptions and 17 flag/description conflicts. After an explicit classification run, **Listing observations** and the symbol/description filter narrow the displayed rows while preserving the snapshot denominator.

The four sources were observed from 23:25:01 through 23:25:03 UTC on November 12. Both Nasdaq Trader files carry a November 12 creation timestamp of 18:01 ET. SEC HTTP modification dates for the ticker and exchange maps were November 10 at 20:53:05 and 20:52:19 UTC, respectively. The SEC files are search associations and their scope can differ from the directories. [SEC data documentation](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [Nasdaq Trader directory definitions](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs)

| Captured source | Raw SHA-256 |
| --- | --- |
| Nasdaq-listed directory | `163ca94e5a977640c8a1fea858bf1b174358ecd856467edaadcf476a283d8299` |
| Other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| SEC ticker map | `391effc6a807ae1752c9d2c351dbecab8f15aa1c59b035a9a28f7955a94feb0f` |
| SEC ticker/exchange map | `98d357e2c5b2fb5bfdb085f3d6a9010036e43a2306e63563061b1997d1e8224e` |

- **Initial SEC-only review, four rows.** Arbor Realty's October 30 Form 8-K and the November 12 Nasdaq Trader rows agree on the issuer, NYSE and distinct Series D, E and F preferred shares. They connect `ABR-PD`, `ABR-PE` and `ABR-PF` to `ABR$D`, `ABR$E` and `ABR$F`. The ALUR row carries a NYSE association, while the exchange's October 13 Form 25 states an October 26 removal date and the issuer's November 12 SEC submissions observation shows OTC. The notice also covers warrants. Only ALUR common stock appears in the SEC-only cohort. [Arbor Form 8-K](https://www.sec.gov/Archives/edgar/data/1253986/000125398626000064/abr-20261030.htm) · [NYSE Form 25](https://www.sec.gov/Archives/edgar/data/876661/000087666126000826/primary_doc.xml) · [NYSE attachment](https://www.sec.gov/Archives/edgar/data/876661/000087666126000826/ruleprovisionnotice.htm) · [ALUR submissions](https://data.sec.gov/submissions/CIK0001964979.json)
- **Initial directory-type review, three rows.** Alphabet's November 5 Form 8-K identifies GOOG as Class C Capital Stock on Nasdaq. ADS-TEC's May 15 Form 20-F identifies ADSEW as a Nasdaq warrant and lists ADSE ordinary shares separately. The initial PFBC SEC submissions screen yielded no eligible cover. The FDIC follow-up below supplies dated evidence for that class. **279 rows remain unreviewed.** [Alphabet Form 8-K](https://www.sec.gov/Archives/edgar/data/1652044/000119312526449835/d174184d8k.htm) · [ADS-TEC Form 20-F](https://www.sec.gov/Archives/edgar/data/1879248/000121390026057891/ea0290629-20f_adstec.htm) · [PFBC SEC submissions](https://data.sec.gov/submissions/CIK0001492165.json)

The findings use exact dated cases for personal inspection. The inventory and classification rules continue to produce the original source observations, with no broad symbol-suffix rule, roster promotion or financial coverage change. Full U.S. coverage, continuous membership and current trading status require separate evidence.

The integration passed 243 affected tests, six research route checks and automated desktop and phone checks. Both browser runs used controlled classification responses to verify the two filters, source links and separate venue summary. Opening the dated review made zero source requests. All 89 protected files matched the baseline.

#### Farmer Mac preferred-share follow-up

The follow-up reviewed the six Series D through I non-cumulative preferred classes for Federal Agricultural Mortgage Corporation, CIK `0000845877`. The visible covers of its November 12 Form 8-K and November 6 Form 10-Q match the issuer, NYSE, series and stated rates of the November 12 Nasdaq Trader other-listed rows. All six directory rows carry exchange code `N`, test flag `N` and ETF flag `N`. The Form 10-Q covers September 30. The observed SEC map, filing cover and directory use the distinct spellings below. [Form 8-K](https://www.sec.gov/Archives/edgar/data/845877/000084587726000143/agm-20261112.htm) · [Form 10-Q](https://www.sec.gov/Archives/edgar/data/845877/000084587726000139/agm-20260930.htm) · [Nasdaq Trader other-listed directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt)

| Series | Stated rate | SEC map | Filing cover | Directory ACT symbol |
| --- | --- | --- | --- | --- |
| D | 5.700% | `AGM-PD` | `AGM.PRD` | `AGM$D` |
| E | 5.750% | `AGM-PE` | `AGM.PRE` | `AGM$E` |
| F | 5.250% | `AGM-PF` | `AGM.PRF` | `AGM$F` |
| G | 4.875% | `AGM-PG` | `AGM.PRG` | `AGM$G` |
| H | 6.500% | `AGM-PH` | `AGM.PRH` | `AGM$H` |
| I | 6.875% | `AGM-PI` | `AGM.PRI` | `AGM$I` |

SEC submissions metadata binds the November 12 filing to accession `0000845877-26-000143`, accepted at 21:19:54 UTC, and the November 6 filing to `0000845877-26-000139`, accepted at 21:05:52 UTC. The covers were observed on November 12 at 23:35:41 and 23:35:42 UTC. Their raw SHA-256 digests are `14097f5aff6e587b7ef5d63110f87a7e82d64be146241ed09a0ab7148a02bbd7` and `b4db3ee28eee6f013a0238a4b7df4cf3ee9756970bbf6886c5b668438381ab3b`, respectively. [SEC submissions](https://data.sec.gov/submissions/CIK0000845877.json)

The Farmer Mac follow-up brought the reviewed count to ten of the original 544 SEC-only rows. The six matches are dated class evidence for the recorded symbols. Live classification, saved inventory, current trading status and financial eligibility retain their separate checks.

#### Triton preference-share follow-up

The next review matched seven cumulative redeemable perpetual preference classes for Triton International Limited, CIK `0001660734`. The February 20 Form 20-F cover binds each series, stated rate, literal symbol and NYSE. The November 6 Form 6-K's interim statements corroborate all seven classes and the NYSE venue as of September 30. The November 12 Nasdaq Trader file agrees on each rate and series. Its seven corresponding rows use venue code `N` and carry `N` for both the test and ETF flags. [SEC Form 20-F](https://www.sec.gov/Archives/edgar/data/1660734/000166073426000005/trtn-20251231.htm) · [SEC interim statements](https://www.sec.gov/Archives/edgar/data/1660734/000162828026071407/trtn-20260930.htm) · [Nasdaq Trader other-listed directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt)

| Series | Stated rate | SEC map | Filing cover | Directory ACT symbol |
| --- | --- | --- | --- | --- |
| A | 8.50% | `TRTN-PA` | `TRTN PRA` | `TRTN$A` |
| B | 8.00% | `TRTN-PB` | `TRTN PRB` | `TRTN$B` |
| C | 7.375% | `TRTN-PC` | `TRTN PRC` | `TRTN$C` |
| D | 6.875% | `TRTN-PD` | `TRTN PRD` | `TRTN$D` |
| E | 5.75% | `TRTN-PE` | `TRTN PRE` | `TRTN$E` |
| F | 7.625% | `TRTN-PF` | `TRTN PRF` | `TRTN$F` |
| G | 7.500% | `TRTN-PG` | `TRTN PRG` | `TRTN$G` |

The Form 20-F reports the fiscal year ended December 31, 2025. Series G appears on its cover after the January 12, 2026 issuance. The January 12 Form 8-A and January 13 NYSE certification separately support the Series G class and listing approval. The review supplies no first execution date or continuous listing history. [Series G Form 8-A](https://www.sec.gov/Archives/edgar/data/1660734/000119312526010370/d30078d8a12b.htm) · [NYSE listing certification](https://www.sec.gov/Archives/edgar/data/1660734/000087666126000041/TRTNPRG011326.pdf)

SEC submissions bind the Form 20-F to accession `0001660734-26-000005`, accepted February 20 at 15:20:31 UTC, and the Form 6-K to `0001628280-26-071407`, accepted November 6 at 14:47:09 UTC. Both documents were captured November 13 at 00:01:54 UTC, November 12 in Toronto. Raw SHA-256 was `30e24861e176c01f326d109b3beb6ef85d623bec98e8ce824018376613c18dbf` for the Form 20-F and `1bbb97e2e2dd25eba6a9f6c930d71c7fdbbcfa6108c27e1602f8e5bd2cc77785` for the interim exhibit. The Series G NYSE certificate digest was `aea9d1593d5c41711e5f4a34a90ffd39c356be4876fc1264a6ee7bd568f0adb3`. [SEC submissions](https://data.sec.gov/submissions/CIK0001660734.json)

The Triton follow-up brought the reviewed count to 17 of the original 544 SEC-only records. The seven matches apply to the dated sources and explicit symbol spellings above.

#### Rithm and Annaly preferred-share follow-up

The next batch matched nine direct preferred share classes from the same November 12 snapshot. Rithm Capital Corp. (CIK `0001556593`) reports Series A through F in its November 2 Form 10-Q for September 30. Annaly Capital Management, Inc. (CIK `0001043219`) reports Series F, G and J in its October 28 Form 10-Q for September 30. Each visible cover row gives NYSE and the exact symbol and class. The matching Nasdaq Trader rows all use exchange code `N` and have test and ETF flags `N`. The percentages below come from the security titles. Reset rates, yields and continuous listing history require their own evidence. [Rithm Form 10-Q](https://www.sec.gov/Archives/edgar/data/1556593/000155659326000035/nrz-20260930.htm) · [Annaly Form 10-Q](https://www.sec.gov/Archives/edgar/data/1043219/000104321926000083/nly-20260930.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt)

| Issuer and series | Title rate | SEC map | Filing cover | Directory ACT symbol |
| --- | --- | --- | --- | --- |
| Rithm A | 7.50% | `RITM-PA` | `RITM PR A` | `RITM$A` |
| Rithm B | 7.125% | `RITM-PB` | `RITM PR B` | `RITM$B` |
| Rithm C | 6.375% | `RITM-PC` | `RITM PR C` | `RITM$C` |
| Rithm D | 7.00% | `RITM-PD` | `RITM PR D` | `RITM$D` |
| Rithm E | 8.750% | `RITM-PE` | `RITM PR E` | `RITM$E` |
| Rithm F | 8.750% | `RITM-PF` | `RITM PR F` | `RITM$F` |
| Annaly F | 6.95% | `NLY-PF` | `NLY.F` | `NLY$F` |
| Annaly G | 6.50% | `NLY-PG` | `NLY.G` | `NLY$G` |
| Annaly J | 8.875% | `NLY-PJ` | `NLY.J` | `NLY$J` |

The NYSE certified Rithm Series F on January 21, 2026 and Annaly Series J on August 12, 2025. Rithm Series E's directory rate `8.75%` equals the filing's `8.750%`. Annaly Series F's directory title is shortened to the issuer, rate and series. The cover supplies the exact class and venue. The filed term sheet names `NLYPrF` as the NYSE listing symbol, and the November directory uses `NLYpF` in its CQS field. The dated match gives the `NLY$F` directory row class evidence while the original classification rule still returns unknown. [Rithm Series F NYSE certification](https://www.sec.gov/Archives/edgar/data/1556593/000087666126000052/RITMPRF012126.pdf) · [Annaly Series J NYSE certification](https://www.sec.gov/Archives/edgar/data/1043219/000087666125000592/NLYPRJ081225.pdf) · [Annaly Series F term sheet](https://www.sec.gov/Archives/edgar/data/1043219/000119312517235069/d417558dfwp.htm)

Annaly redeemed Series I on October 1. The NYSE Form 25 notice reports suspension on October 1 and specifies removal at the October 12 opening. Series I is absent from the November 12 input files and excluded from both reviewed counts. [Annaly Form 8-K](https://www.sec.gov/Archives/edgar/data/1043219/000104321926000070/nly-20261002.htm) · [NYSE Form 25 notice](https://www.sec.gov/Archives/edgar/data/876661/000087666126000807/ruleprovisionnotice.htm)

SEC submissions bind the Rithm Form 10-Q to accession `0001556593-26-000035`, accepted October 31 at 00:02:09 UTC, and the Annaly Form 10-Q to `0001043219-26-000083`, accepted October 28 at 20:06:15 UTC. The covers were captured November 13 at 02:09:42 and 02:08:58 UTC, respectively, November 12 in Toronto. Their raw SHA-256 digests were `990c0cd66f5b53275064eff230b34ada90b462190437271fa6179211d6307254` and `1189fb0d19d7fab55f20e30a62cbfb67f22afcc83894a51899ce3159caab15d9`. [Rithm submissions](https://data.sec.gov/submissions/CIK0001556593.json) · [Annaly submissions](https://data.sec.gov/submissions/CIK0001043219.json)

The Rithm and Annaly follow-up brought the reviewed count to 26 of 544 SEC-only records. The original 282 directory-type gaps include four with dated class evidence and 278 unreviewed. The SEC-only and directory counts measure separate source rows. The two Annaly Series F rows describe one security. PFBC's IRS number remains unreconciled.

The integration passed 249 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the nine new class matches, source links, Series I exclusion and prior PFBC finding. The dated review made zero source requests. All 89 protected files matched the baseline.

#### JPMorgan depositary-share follow-up

The next batch matched six NYSE depositary-share records for JPMorgan Chase & Co. (CIK `0000019617`). The November 3 Form 10-Q cover for September 30 and the November 12 Nasdaq Trader directory tie each listed depositary share to a `1/400` interest in a share of the named non-cumulative preferred series. The directory rows carry NYSE code `N` and `N` in the test and ETF fields. The ticker suffix and underlying series are distinct. The listed securities are the depositary shares. [JPMorgan Form 10-Q](https://www.sec.gov/Archives/edgar/data/19617/000162828026069523/jpm-20260930.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt)

| Underlying preferred series | Title rate | SEC map | Filing cover | Directory ACT symbol |
| --- | --- | --- | --- | --- |
| EE | 6.00% | `JPM-PC` | `JPM PR C` | `JPM$C` |
| DD | 5.75% | `JPM-PD` | `JPM PR D` | `JPM$D` |
| GG | 4.75% | `JPM-PJ` | `JPM PR J` | `JPM$J` |
| JJ | 4.55% | `JPM-PK` | `JPM PR K` | `JPM$K` |
| LL | 4.625% | `JPM-PL` | `JPM PR L` | `JPM$L` |
| MM | 4.20% | `JPM-PM` | `JPM PR M` | `JPM$M` |

NYSE separately certified the Series JJ depositary shares on March 18, 2021 and the Series MM depositary shares on July 29, 2021. Note 17 of the Form 10-Q records the June 1, 2026 redemption of the separate Series KK depositary shares, which each represented a `1/10` interest. `JPM-PK` maps to Series JJ. The October 15 issuer release includes Series MM among the outstanding series. The review leaves current trading and future redemption status open. [NYSE Series JJ certification](https://www.sec.gov/Archives/edgar/data/19617/000087666121000413/JPM031821.pdf) · [NYSE Series MM certification](https://www.sec.gov/Archives/edgar/data/19617/000087666121001134/JPMPRM072921.pdf) · [October 15 issuer release](https://www.jpmorganchase.com/ir/news/2026/jpmc-declares-preferred-stock-dividends-10-15)

SEC submissions bind the Form 10-Q to accession `0001628280-26-069523`, accepted November 3 at 21:17:12 UTC. The exact filing was captured November 13 at 02:18:27 UTC, November 12 in Toronto, with raw SHA-256 `2d3dadea07c09ab8d535867a6d1b9cfa2c833b0ea8abcce4dccfb9a25695045b`. The raw Series JJ and MM certificate digests were `fe26ea214690d7ede55b493212ea006be5b3d093c9ec2b88f882959153b1f79a` and `729578f2115a3672bf4b8e43af333ac6e29488a88e6e7aa6e83b1163ade250b3`, respectively. [SEC submissions](https://data.sec.gov/submissions/CIK0000019617.json)

The JPMorgan follow-up brought the reviewed count to 32 of the original 544 SEC-only records. The six directory counterparts already carried the depositary-receipt classification. The findings apply to these exact dated records. PFBC's IRS number remains unreconciled.

The integration passed 250 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the six exact mappings, source links, previous filters and PFBC finding. Opening the dated review made zero source requests. All 89 protected files matched the baseline.

#### Morgan Stanley depositary-share follow-up

The next batch matched nine NYSE depositary-share records for Morgan Stanley (CIK `0000895421`). The November 5 Form 10-Q cover for the quarter ended September 30 identifies each listed depositary share as a `1/1,000` interest in the named non-cumulative preferred series. The October 14 Form 8-K and 2025 Form 10-K securities description corroborate the nine classes. The fixed November 12 Nasdaq Trader records all have exchange code `N` and `N` in the ETF and test-issue fields. The November 12 NYSE short-sale volume report contains all nine exchange symbols for that session. The report covers a limited set of market activity and supplies no evidence of continuous listing or trading. [November 5 Form 10-Q](https://www.sec.gov/Archives/edgar/data/895421/000089542126000293/ms-20260930.htm) · [October 14 Form 8-K](https://www.sec.gov/Archives/edgar/data/895421/000089542126000288/ms-20261014.htm) · [Securities description](https://www.sec.gov/Archives/edgar/data/895421/000089542126000086/exhibit41q42025_10k.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 115](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=115)

| Underlying series | SEC map | Filing cover | Directory ACT symbol | NYSE report symbol |
| --- | --- | --- | --- | --- |
| A | `MS-PA` | `MS/PA` | `MS$A` | `MS PRA` |
| E | `MS-PE` | `MS/PE` | `MS$E` | `MS PRE` |
| F | `MS-PF` | `MS/PF` | `MS$F` | `MS PRF` |
| I | `MS-PI` | `MS/PI` | `MS$I` | `MS PRI` |
| K | `MS-PK` | `MS/PK` | `MS$K` | `MS PRK` |
| L | `MS-PL` | `MS/PL` | `MS$L` | `MS PRL` |
| O | `MS-PO` | `MS/PO` | `MS$O` | `MS PRO` |
| P | `MS-PP` | `MS/PP` | `MS$P` | `MS PRP` |
| Q | `MS-PQ` | `MS/PQ` | `MS$Q` | `MS PRQ` |

The abbreviated `MS$A` and `MS$F` descriptions still return unknown in the original classifier. Both have dated class evidence through the specific symbol matches above. The `MS$I` directory row says `Series 1` and has CQS symbol `MSpI`. The original wording is retained. The SEC cover, registered Series I terms and NYSE symbol `MS PRI` corroborate the letter I for the dated match. The NYSE also issued separate historical certifications for the Series P and Q depositary shares. [Series I Form 8-A](https://www.sec.gov/Archives/edgar/data/895421/000095010314006466/dp49485_8a12b-seriesi.htm) · [NYSE Series P certification](https://www.sec.gov/Archives/edgar/data/895421/000087666122000610/MSPRP080322.pdf) · [NYSE Series Q certification](https://www.sec.gov/Archives/edgar/data/895421/000087666124000612/MSPRQ073024.pdf)

SEC submissions bind the Form 10-Q to accession `0000895421-26-000293`, accepted November 5 at 21:21:51 UTC. Its raw SHA-256 was `ebaa1b40987fc219ea2512c1259dcdc7b8d4d6a2770788672bf12c982b18e92b`. The raw November 12 NYSE report digest was `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0`. The SEC and NYSE records were captured November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0000895421.json)

The Morgan Stanley follow-up brought the reviewed count to 41 of the original 544 SEC-only records. SEC-only rows and their directory counterparts can describe the same security.

The integration passed 251 affected tests, six research route checks and automated desktop and phone checks. The browser checks verified the nine exact mappings, source links, directory gaps and prior PFBC finding. The dated review made zero source requests. All 89 protected files matched the baseline.

#### Bank of America preferred-share follow-up

The next batch matched the ten `BAC`-prefixed NYSE preferred-linked rows for Bank of America Corporation (CIK `0000070858`). The October 30 Form 10-Q for September 30 and the October 14 Form 8-K identify nine depositary share listings, each representing a `1/1,000` interest in the named preferred stock, and one direct listing of Series L convertible preferred stock. All ten match the November 12 Nasdaq Trader directory with venue code `N`, ETF flag `N` and test flag `N`. The same-day NYSE short-sale volume report supplies ten distinct market-`N` rows. That report covers a limited set of activity for one date. [Form 10-Q](https://www.sec.gov/Archives/edgar/data/70858/000007085826000548/bac-20260930.htm) · [Form 8-K](https://www.sec.gov/Archives/edgar/data/70858/000007085826000481/bac-20261014.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 18](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=18)

| Preferred series | Listed instrument | SEC map | Filing cover | Directory ACT symbol | NYSE report symbol |
| --- | --- | --- | --- | --- | --- |
| GG | Depositary share | `BAC-PB` | `BAC PrB` | `BAC$B` | `BAC PRB` |
| E | Depositary share | `BAC-PE` | `BAC PrE` | `BAC$E` | `BAC PRE` |
| HH | Depositary share | `BAC-PK` | `BAC PrK` | `BAC$K` | `BAC PRK` |
| L | Direct convertible preferred stock | `BAC-PL` | `BAC PrL` | `BAC$L` | `BAC PRL` |
| KK | Depositary share | `BAC-PM` | `BAC PrM` | `BAC$M` | `BAC PRM` |
| LL | Depositary share | `BAC-PN` | `BAC PrN` | `BAC$N` | `BAC PRN` |
| NN | Depositary share | `BAC-PO` | `BAC PrO` | `BAC$O` | `BAC PRO` |
| PP | Depositary share | `BAC-PP` | `BAC PrP` | `BAC$P` | `BAC PRP` |
| QQ | Depositary share | `BAC-PQ` | `BAC PrQ` | `BAC$Q` | `BAC PRQ` |
| SS | Depositary share | `BAC-PS` | `BAC PrS` | `BAC$S` | `BAC PRS` |

The original classifier still returns unknown for the abbreviated `BAC$E` and `BAC$L` descriptions. The exact cover and symbol matches supply dated class evidence for both. The charter exhibit specifies the 7.25% Series L convertible preferred terms, and the Form 10-Q reports a holder conversion of 28 Series L shares on September 25. The full first-quarter redemption involved separate Series DD. The NYSE separately certified the Series SS depositary shares on January 31, 2022. The four `BML`-prefixed depositary rows are reviewed separately below. [Series L charter exhibit](https://www.sec.gov/Archives/edgar/data/70858/000007085826000548/bac-0930202610xqex31.htm) · [NYSE Series SS certification](https://www.sec.gov/Archives/edgar/data/70858/000087666122000107/BACPRS013122.pdf)

SEC submissions bind the Form 10-Q to accession `0000070858-26-000548`, accepted October 30 at 21:04:27 UTC. The cover was captured November 13 at 03:26:51 UTC, November 12 in Toronto, with raw SHA-256 `d028a28859783d6f956062bf18919edfbf5b56fa75442cc5fcd44dde25de5e86`. The November 12 NYSE report has raw digest `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0`, and the Series SS certificate has raw digest `5d4bc8e5184cc6a6c3a196cd9cf98d09055cbb0390afdd28c99b2844b877ef44`. [SEC submissions](https://data.sec.gov/submissions/CIK0000070858.json)

The BAC-prefixed follow-up brought the reviewed count to 51 of the original 544 SEC-only records. The two abbreviated directory rows brought the number with dated class evidence to eight of the original 282 directory-type gaps.

The integration passed 252 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the ten mappings, source links, remaining gaps and prior PFBC finding. The dated review made zero source requests. All 89 protected files matched the baseline.

#### BML depositary-share follow-up

The four `BML`-prefixed SEC-only records map to Bank of America Corporation (CIK `0000070858`). The October 30 Form 10-Q for September 30 and the October 23 Form 8-K identify each listed depositary share as a `1/1,200` interest in a share of the named floating-rate non-cumulative preferred series. The 2025 annual securities exhibit identifies these as the legacy Merrill Lynch preferred series. All four match the November 12 Nasdaq Trader directory, with venue code `N` and test and ETF flags `N`. The same-day NYSE short-sale volume report contains one market-`N` row for each exchange symbol and covers a limited set of activity on that date. [Form 10-Q](https://www.sec.gov/Archives/edgar/data/70858/000007085826000548/bac-20260930.htm) · [Form 8-K](https://www.sec.gov/Archives/edgar/data/70858/000119312526430566/d176604d8k.htm) · [Annual securities exhibit](https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/bac-1231202510xkex432.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 24](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=24)

| Underlying preferred series | SEC map | Filing cover | Directory ACT symbol | NYSE report symbol |
| --- | --- | --- | --- | --- |
| 1 | `BML-PG` | `BML PrG` | `BML$G` | `BML PRG` |
| 2 | `BML-PH` | `BML PrH` | `BML$H` | `BML PRH` |
| 4 | `BML-PJ` | `BML PrJ` | `BML$J` | `BML PRJ` |
| 5 | `BML-PL` | `BML PrL` | `BML$L` | `BML PRL` |

`BML-PL` represents Series 5. `BAC-PL` is the distinct direct Series L convertible preferred stock. All four BML directory counterparts already carried the depositary-receipt classification. Continuous listing and current trading status require separate evidence. The batch makes no determination about the history of Series 3.

SEC submissions bind the October 23 Form 8-K to accession `0001193125-26-430566`, accepted at 20:41:47 UTC. Its raw SHA-256 was `70e51266cf2cba675a3ac32e065f6627bb9708aad9fce1ba6f662708541f7246`. The October 30 cover and November 12 NYSE report retain the raw digests recorded in the BAC review above. [SEC submissions](https://data.sec.gov/submissions/CIK0000070858.json)

The BML follow-up brought the reviewed count to 55 of the original 544 SEC-only records, leaving 489 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 253 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the four mappings, source links, Series 5 distinction and prior PFBC finding. The dated review made zero source requests. All 89 protected files matched the baseline.

#### U.S. Bancorp depositary-share follow-up

The November 6 Form 8-K cover for U.S. Bancorp (CIK `0000036104`) identifies six NYSE depositary shares and their underlying non-cumulative perpetual preferred series. The November 5 Form 10-Q for September 30 corroborates the classes and fractions. The Form 8-K supplies the exact `USB PrR` spelling, where the 10-Q renders the last letter separately. Each November 12 Nasdaq Trader counterpart has venue code `N`, test and ETF flags `N`, and an existing depositary-receipt classification. Page 179 of the November 12 NYSE short-sale volume report has one market-`N` row with positive total volume for each class. The report covers a limited set of activity for that date. [Form 8-K](https://www.sec.gov/Archives/edgar/data/36104/000119312526450781/d172862d8k.htm) · [Form 10-Q](https://www.sec.gov/Archives/edgar/data/36104/000003610426000058/usb-20260930.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 179](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=179)

| SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Underlying series | Interest in one preferred share |
| --- | --- | --- | --- | --- | --- |
| `USB-PA` | `USB PrA` | `USB$A` | `USB PRA` | A | 1/100 |
| `USB-PH` | `USB PrH` | `USB$H` | `USB PRH` | B | 1/1,000 |
| `USB-PP` | `USB PrP` | `USB$P` | `USB PRP` | K | 1/1,000 |
| `USB-PQ` | `USB PrQ` | `USB$Q` | `USB PRQ` | L | 1/1,000 |
| `USB-PR` | `USB PrR` | `USB$R` | `USB PRR` | M | 1/1,000 |
| `USB-PS` | `USB PrS` | `USB$S` | `USB PRS` | O | 1/1,000 |

`USB-PP` represents Series K. The separate Series P depositary offering closed October 30 with a 1/25 interest per depositary share and falls outside this batch. These six dated matches do not establish continuous listing or current trading status. [October 30 Form 8-K](https://www.sec.gov/Archives/edgar/data/36104/000119312526441737/d20659d8k.htm) · [Series P deposit agreement](https://www.sec.gov/Archives/edgar/data/36104/000119312526441737/d20659dex43.htm)

SEC submissions bind the Form 8-K to accession `0001193125-26-450781`, accepted November 6 at 13:00:19 UTC, and the Form 10-Q to `0000036104-26-000058`, accepted November 4 at 22:44:17 UTC and filed November 5. The primary documents and Series P agreement were observed November 13 from 03:57:09 to 03:57:47 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0000036104.json) · [Form 10-Q filing detail](https://www.sec.gov/Archives/edgar/data/36104/000003610426000058/0000036104-26-000058-index.htm)

| Captured source | Raw SHA-256 |
| --- | --- |
| November 6 Form 8-K | `31ca96f38d5076916b32aa64daa52dbf6c01d986e6c39edfc2f152f1354f27f5` |
| November 5 Form 10-Q | `a744ea2af1407af705bc93dfd4534cc8e5398e1e68bfa3f8354a34b892ec215d` |
| October 30 Series P deposit agreement | `bc816c366217a935cbbc165fd7e1f3b5c02f5b3d8f78aa30a76cdfcde2ebbfc0` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The U.S. Bancorp follow-up brought the reviewed count to 61 of the original 544 SEC-only records, leaving 483 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 254 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the six mappings, five source links, Series P distinction and prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Public Storage preferred-share follow-up

Public Storage (CIK `0001393311`) lists 16 NYSE preferred-linked securities on the November 12 Form 8-K cover for a November 11 event. The October 26 Form 10-Q cover and Note 11 corroborate the classes. Series F through S each represent 1/1,000 of a cumulative preferred share. Series T and U are two distinct direct cumulative preferred shares. The July 21 NYSE certification approved both classes. Public Storage issued T and U on July 22 in exchange for National Storage Affiliates Trust Series A and B, respectively. The operating partnership's separate Series T-1 units fall outside this batch. [November 12 Form 8-K](https://www.sec.gov/Archives/edgar/data/1393311/000119312526456624/d158518d8k.htm) · [September-quarter Form 10-Q](https://www.sec.gov/Archives/edgar/data/1393311/000162828026067286/psa-20260930.htm) · [NYSE Series T and U certification](https://www.sec.gov/Archives/edgar/data/1393311/000087666126000633/PSAPRTPRU.pdf) · [July 22 merger closing Form 8-K](https://www.sec.gov/Archives/edgar/data/1393311/000119312526312563/d137665d8k.htm)

| Series | SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Listed security |
| --- | --- | --- | --- | --- | --- |
| F | `PSA-PF` | `PSAPrF` | `PSA$F` | `PSA PRF` | Depositary share |
| G | `PSA-PG` | `PSAPrG` | `PSA$G` | `PSA PRG` | Depositary share |
| H | `PSA-PH` | `PSAPrH` | `PSA$H` | `PSA PRH` | Depositary share |
| I | `PSA-PI` | `PSAPrI` | `PSA$I` | `PSA PRI` | Depositary share |
| J | `PSA-PJ` | `PSAPrJ` | `PSA$J` | `PSA PRJ` | Depositary share |
| K | `PSA-PK` | `PSAPrK` | `PSA$K` | `PSA PRK` | Depositary share |
| L | `PSA-PL` | `PSAPrL` | `PSA$L` | `PSA PRL` | Depositary share |
| M | `PSA-PM` | `PSAPrM` | `PSA$M` | `PSA PRM` | Depositary share |
| N | `PSA-PN` | `PSAPrN` | `PSA$N` | `PSA PRN` | Depositary share |
| O | `PSA-PO` | `PSAPrO` | `PSA$O` | `PSA PRO` | Depositary share |
| P | `PSA-PP` | `PSAPrP` | `PSA$P` | `PSA PRP` | Depositary share |
| Q | `PSA-PQ` | `PSAPrQ` | `PSA$Q` | `PSA PRQ` | Depositary share |
| R | `PSA-PR` | `PSAPrR` | `PSA$R` | `PSA PRR` | Depositary share |
| S | `PSA-PS` | `PSAPrS` | `PSA$S` | `PSA PRS` | Depositary share |
| T | `PSA-PT` | `PSAPrT` | `PSA$T` | `PSA PRT` | Direct preferred share |
| U | `PSA-PU` | `PSAPrU` | `PSA$U` | `PSA PRU` | Direct preferred share |

The November 12 Nasdaq Trader snapshot has all 16 counterpart rows with exchange code `N` and test and ETF flags `N`. Its existing description rules classify F through S as depositary receipts and T and U as preferred shares. The November 12 NYSE short-sale volume report contains one market-`N` row with positive total volume for each symbol on pages 139 and 140. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [NYSE report, F through R](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=139) · [NYSE report, S through U](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=140)

SEC submissions bind the November 12 Form 8-K to accession `0001193125-26-456624`, accepted at 11:03:57 UTC, and the October 26 Form 10-Q to `0001628280-26-067286`, accepted at 20:14:59 UTC. The July 21 NYSE certification is accession `0000876661-26-000633`. The filings and certification below were observed November 13 from 04:05:44 to 04:05:47 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0001393311.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| November 12 Form 8-K | `91862dc342b87bbfedd44df5e09ae3d9a285ea3bdb4e2be928faca924f48f986` |
| October 26 Form 10-Q | `ec9ba37b3eca86a4e2108b124f8a370e2519ef10b5321621defb5e250ab519f5` |
| July 21 NYSE Series T and U certification | `377df5ee90a48b2cff520fd8f5a4f862129fccdae7ada8e94c57afe093666be3` |
| July 22 merger closing Form 8-K | `6058c6127f0db75b26678134b193013947f173e3ce95405c22d6fd8b39b58f80` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Public Storage follow-up brought the reviewed count to 77 of the original 544 SEC-only records, leaving 467 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 255 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the 16 mappings, six source links, depositary and direct share distinctions, and prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Pacific Gas and Electric Company preferred-share follow-up

The November 2 utility-only Form 8-K for an October 29 event names Pacific Gas and Electric Company (CIK `0000075488`) and lists eight direct cumulative first preferred shares with $25 par value on NYSE American LLC. The October 22 joint Form 10-Q for September 30 corroborates all eight. The joint cover separately lists PG&E Corporation's `PCG-PrX` mandatory convertible preferred stock on NYSE under the parent (CIK `0001004980`). The parent's security falls outside this batch. The Series A designation in the utility's filing belongs to `PCG-PE`. [Utility Form 8-K](https://www.sec.gov/Archives/edgar/data/75488/000199937126024070/pcg-8k_102926.htm) · [Joint Form 10-Q](https://www.sec.gov/Archives/edgar/data/75488/000100498026000055/pcg-20260930.htm)

| SEC map and filing symbol | Directory ACT symbol | NYSE American report symbol | Filed class terms |
| --- | --- | --- | --- |
| `PCG-PA` | `PCG$A` | `PCG PRA` | 6% nonredeemable |
| `PCG-PB` | `PCG$B` | `PCG PRB` | 5.50% nonredeemable |
| `PCG-PC` | `PCG$C` | `PCG PRC` | 5% nonredeemable |
| `PCG-PD` | `PCG$D` | `PCG PRD` | 5% redeemable |
| `PCG-PE` | `PCG$E` | `PCG PRE` | 5% Series A redeemable |
| `PCG-PG` | `PCG$G` | `PCG PRG` | 4.80% redeemable |
| `PCG-PH` | `PCG$H` | `PCG PRH` | 4.50% redeemable |
| `PCG-PI` | `PCG$I` | `PCG PRI` | 4.36% redeemable |

The fixed SEC bulk exchange map associates all eight with the utility and labels the venue NYSE. The observed SEC submissions ticker arrays also place seven of the symbols under the parent and only `PCG-PA` under the utility. The utility-only filing cover supplies the registrant and registered venue for each exact symbol. All eight November 12 Nasdaq Trader counterparts have venue code `A`, test and ETF flags `N`, and an existing preferred classification. The November 12 NYSE American short-sale volume report has one market-`A` row with positive total volume per class on page 102. The separate same-day NYSE report has a market-`N` trading observation for `PCG PRA`, which does not establish an NYSE listing. These are dated observations of registration and limited trading activity. Continuous listing and current trading status require separate evidence. [SEC exchange map](https://www.sec.gov/files/company_tickers_exchange.json) · [Utility submissions](https://data.sec.gov/submissions/CIK0000075488.json) · [Parent submissions](https://data.sec.gov/submissions/CIK0001004980.json) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [NYSE American report, page 102](https://ftp.nyse.com/ShortData/Amexshvol/Amexshvol2026/Amexshvol202611/Amexshvol20261112.pdf#page=102) · [NYSE report](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf)

SEC submissions bind the November 2 Form 8-K to accession `0001999371-26-024070`, accepted at 13:00:36 UTC, and the October 22 Form 10-Q to `0001004980-26-000055`, accepted at 00:52:37 UTC. The SEC captures and NYSE American report were observed November 13 from 04:12:56 to 04:13:29 UTC, November 12 in Toronto. [Form 8-K filing detail](https://www.sec.gov/Archives/edgar/data/75488/000199937126024070/0001999371-26-024070-index.htm) · [Form 10-Q filing detail](https://www.sec.gov/Archives/edgar/data/75488/000100498026000055/0001004980-26-000055-index.htm)

| Captured source | Raw SHA-256 |
| --- | --- |
| November 2 utility Form 8-K | `a92f2285ff76c3bd24ec9d5ff59493603ae107928b502668f71c72bf2151b437` |
| October 22 joint Form 10-Q | `2fea7e18d78404261d775c9d9da00930755ce8de8edbe3f09a5fd9cf09b30cc6` |
| Utility SEC submissions | `83b6ef731a5907da0945243fda0af0a70f1bd3a6c5ceb722bee1b13bd78cd1fe` |
| Parent SEC submissions | `5081bb8a92551ac06f5a183e4fbc6c46b0887e8081c77f0d1ec3f37ad9cbab24` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE American short-sale volume report | `458e1a6d932407be6f4b4ba7f1bcc33364f44de751f5dd039bee5e5fd0c96c8a` |

The Pacific Gas and Electric Company follow-up brought the reviewed count to 85 of the original 544 SEC-only records, leaving 459 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 256 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the eight mappings, four source links, venue discrepancy, parent security distinction and prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Wells Fargo preferred-share follow-up

The October 28 Form 10-Q cover for Wells Fargo & Company (CIK `0000072971`) and its October 13 Form 8-K cover identify six NYSE preferred-linked listings. Five are depositary shares, each representing 1/1,000 of one non-cumulative perpetual Class A preferred share. Series L is direct 7.5% non-cumulative perpetual convertible Class A preferred stock. The NYSE certification dated July 27, 2021 independently identifies the Series DD depositary shares. [October 28 Form 10-Q](https://www.sec.gov/Archives/edgar/data/72971/000007297126000327/wfc-20260930.htm) · [October 13 Form 8-K](https://www.sec.gov/Archives/edgar/data/72971/000007297126000318/wfc-20261013.htm) · [NYSE Series DD certification](https://www.sec.gov/Archives/edgar/data/72971/000087666121001124/WFCPRD072921.pdf)

| SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Underlying series | Listed security |
| --- | --- | --- | --- | --- | --- |
| `WFC-PA` | `WFC.PRA` | `WFC$A` | `WFC PRA` | AA | Depositary share |
| `WFC-PC` | `WFC.PRC` | `WFC$C` | `WFC PRC` | CC | Depositary share |
| `WFC-PD` | `WFC.PRD` | `WFC$D` | `WFC PRD` | DD | Depositary share |
| `WFC-PL` | `WFC.PRL` | `WFC$L` | `WFC PRL` | L | Direct convertible preferred stock |
| `WFC-PY` | `WFC.PRY` | `WFC$Y` | `WFC PRY` | Y | Depositary share |
| `WFC-PZ` | `WFC.PRZ` | `WFC$Z` | `WFC PRZ` | Z | Depositary share |

The November 12 Nasdaq Trader snapshot gives each counterpart venue code `N` and test and ETF flags `N`. Its existing descriptions classify five as depositary receipts and Series L as preferred stock. The November 12 NYSE short-sale volume report has one market-`N` row with positive total volume per class on page 188. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 188](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=188)

Note 8 of the Form 10-Q reports all six underlying classes outstanding on September 30 and the separate Series BB redemption in March. The August 19 Form 8-K describes the separate Series HH offering with a 1/25 interest per depositary share. Both events fall outside this cohort. [Form 10-Q, Note 8](https://www.sec.gov/Archives/edgar/data/72971/000007297126000327/wfc-20260930.htm) · [Series HH Form 8-K](https://www.sec.gov/Archives/edgar/data/72971/000119312526356890/d144651d8k.htm)

SEC submissions bind the October 28 Form 10-Q for September 30 to accession `0000072971-26-000327`, accepted at 12:59:31 UTC, and the October 13 Form 8-K to `0000072971-26-000318`, accepted at 10:28:19 UTC. The Series DD certification is accession `0000876661-21-001124`. The Series HH Form 8-K is accession `0001193125-26-356890`. The two covers and supplementary filings were observed November 13 from 04:18:48 to 04:20:48 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0000072971.json) · [Form 10-Q filing detail](https://www.sec.gov/Archives/edgar/data/72971/000007297126000327/0000072971-26-000327-index.htm)

| Captured source | Raw SHA-256 |
| --- | --- |
| October 28 Form 10-Q | `110f4a9e3937f8f647d11e36bc383d22c5b7087f08aa70498564fcf6aa8021ef` |
| October 13 Form 8-K | `98aa72a9d44a5bc524d4c42a4014caddc8387815c3b25cdd2f4811f3137c5a17` |
| NYSE Series DD certification | `2dad750fece1b4ced613c5b9032bf3cc33ec41ee379fd303292662c2f2776aa6` |
| August 19 Series HH Form 8-K | `8e0b45dcd691a317265b6603652ba53f5017ba71cf3b8d97aae299b2a749de2e` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Wells Fargo follow-up brought the reviewed count to 91 of the original 544 SEC-only records, leaving 453 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 257 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the six mappings, six source links, the direct Series L and separate Series HH offering, and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Ashford Hospitality Trust preferred-share follow-up

Two November 10 Forms 8-K for Ashford Hospitality Trust, Inc. (CIK `0001232582`) identify five NYSE preferred share classes with the same literal symbols as the SEC exchange map. The June-quarter Form 10-Q and November 12 Nasdaq Trader directory corroborate the cumulative preferred stock classes and their stated rates. The directory already classified all five as preferred, with venue code `N` and test and ETF flags `N`. [Earnings Form 8-K](https://www.sec.gov/Archives/edgar/data/1232582/000123258226000214/aht-20261110.htm) · [Officer change Form 8-K](https://www.sec.gov/Archives/edgar/data/1232582/000110465926125247/tm2629394d1_8k.htm) · [June-quarter Form 10-Q](https://www.sec.gov/Archives/edgar/data/1232582/000123258226000183/aht-20260630.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt)

| SEC map and filing symbol | Directory ACT symbol | NYSE report symbol | Series | Stated class rate |
| --- | --- | --- | --- | --- |
| `AHT-PD` | `AHT$D` | `AHT PRD` | D | 8.45% |
| `AHT-PF` | `AHT$F` | `AHT PRF` | F | 7.375% |
| `AHT-PG` | `AHT$G` | `AHT PRG` | G | 7.375% |
| `AHT-PH` | `AHT$H` | `AHT PRH` | H | 7.50% |
| `AHT-PI` | `AHT$I` | `AHT PRI` | I | 7.50% |

The November 10 earnings exhibit reports shares outstanding for all five classes at September 30 and says that preferred dividends remain suspended and continue to accumulate. The percentages identify the class terms. Current yields and payment timing require separate evidence. Series J, K, L and M and the separately registered preferred stock purchase rights fall outside these five matches. The captured submissions index had yet to show a September-quarter Form 10-Q when reviewed on November 12. [September-quarter earnings exhibit](https://www.sec.gov/Archives/edgar/data/1232582/000123258226000214/aht2026q3earningsrelease.htm) · [SEC submissions](https://data.sec.gov/submissions/CIK0001232582.json)

The November 12 NYSE short-sale volume report has one market-`N` row with positive total volume per class on page 6. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [November 12 NYSE report, page 6](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=6)

SEC submissions bind the November 10 earnings Form 8-K to accession `0001232582-26-000214`, accepted at 22:28:33 UTC, and the officer change Form 8-K to `0001104659-26-125247`, accepted at 21:31:11 UTC. The SEC files below were observed November 13 from 04:24:03 to 04:24:50 UTC, November 12 in Toronto. [Earnings filing detail](https://www.sec.gov/Archives/edgar/data/1232582/000123258226000214/0001232582-26-000214-index.htm) · [Officer change filing detail](https://www.sec.gov/Archives/edgar/data/1232582/000110465926125247/0001104659-26-125247-index.htm)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `1c22fe0e28a06711f6e351c3b196a47e468658b9ca19db3eeb791d4a785a764e` |
| November 10 earnings Form 8-K | `2352906de201f66df9236838e66a8f1d5f655fa3e930d15261f2f1d37c2b919c` |
| November 10 officer change Form 8-K | `515576a61d150a40412e6c4154837100f97f5176612e825013eed112153cf0bd` |
| November 10 earnings exhibit | `d7acd1dd8533309dd1bd861be03e44807941fe2aeb1f739605d02777d212fb5f` |
| June-quarter Form 10-Q | `03cbfd3149fd347dc5b2d173b33713aef49651e80ac8bc1c5c5b1560e914a151` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Ashford Hospitality Trust follow-up brought the reviewed count to 96 of the original 544 SEC-only records, leaving 448 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 258 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the five mappings, five source links, dividend suspension, class exclusions and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Capital One preferred-share follow-up

The November 10 Form 8-K and November 3 Form 10-Q for Capital One Financial Corporation (CIK `0000927628`) identify five NYSE depositary share listings. Each depositary share represents a 1/40 interest in one fixed-rate non-cumulative perpetual preferred share of its respective series. The NYSE certification dated July 29, 2021 independently confirms approval to list and register Series N depositary shares. [November 10 Form 8-K](https://www.sec.gov/Archives/edgar/data/927628/000092762826000157/cof-20261110.htm) · [September-quarter Form 10-Q](https://www.sec.gov/Archives/edgar/data/927628/000092762826000152/cof-20260930.htm) · [NYSE Series N certification](https://www.sec.gov/Archives/edgar/data/927628/000087666121001133/COFPRN072921.pdf)

| SEC map | Filing cover and NYSE report symbol | Directory ACT symbol | Underlying series |
| --- | --- | --- | --- |
| `COF-PI` | `COF PRI` | `COF$I` | I |
| `COF-PJ` | `COF PRJ` | `COF$J` | J |
| `COF-PK` | `COF PRK` | `COF$K` | K |
| `COF-PL` | `COF PRL` | `COF$L` | L |
| `COF-PN` | `COF PRN` | `COF$N` | N |

The November 12 Nasdaq Trader snapshot gives each counterpart venue code `N`, test and ETF flags `N`, and an existing depositary-receipt classification. The same-day NYSE short-sale volume report has one market-`N` row with positive total volume per class on page 39. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 39](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=39)

The Form 10-Q reports all five underlying series outstanding at September 30. Series M was fully redeemed September 1. Series O, issued in connection with the Discover acquisition, has a 1/100 depositary fraction and falls outside these five matches. [Form 10-Q, preferred stock note](https://www.sec.gov/Archives/edgar/data/927628/000092762826000152/cof-20260930.htm) · [Series M Form 8-K](https://www.sec.gov/Archives/edgar/data/927628/000119312526378455/d477310d8k.htm)

SEC submissions bind the November 10 Form 8-K to accession `0000927628-26-000157`, accepted at 21:05:58 UTC, and the November 3 Form 10-Q for September 30 to `0000927628-26-000152`, accepted at 21:13:27 UTC. The Series N certification is accession `0000876661-21-001133`. The submissions index and exact documents below were observed November 13 from 04:28:07 to 04:28:56 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0000927628.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `3709c1b8da263853ef28a6d955733074b4e686bf5388c195234a81a35ba08921` |
| November 10 Form 8-K | `b7a7218116d2e3d67d3a58cb8f60d264be163a036f31ba662430e0f76a6c4025` |
| November 3 Form 10-Q | `7ce69ea43c976191cfc7884b05ab5915e2e5e1a519cfddbe546fd040c44ea3be` |
| NYSE Series N certification | `b47e4af2b7feb8410c7da62f3433d1b2c66e30ee7f31bb1569b290fca67d52e7` |
| [Series M certificate of elimination, Form 8-K Exhibit 3.1](https://www.sec.gov/Archives/edgar/data/927628/000119312526378455/d477310dex31.htm) | `6e8ae876ca0b4f707ebe97a1ab2d9923def508305e70d266b9596975325c5201` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Capital One follow-up brought the reviewed count to 101 of the original 544 SEC-only records, leaving 443 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 259 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the five mappings, six source links, the separate Series M and O scope, and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Allstate preferred-share follow-up

The November 4 Form 10-Q and Form 8-K for The Allstate Corporation (CIK `0000899051`) identify three NYSE depositary share listings. Each depositary share represents 1/1,000 of one preferred share in Series H, I or J. The May 24, 2023 NYSE certification independently identifies the Series J depositary shares. The same November covers identify `ALL.PR.B` as fixed-to-floating subordinated debentures due 2053, consistent with the original Form 8-A registration. The common stock's separate NYSE Texas registration is outside these four matches. [November 4 Form 10-Q](https://www.sec.gov/Archives/edgar/data/899051/000089905126000157/all-20260930.htm) · [November 4 Form 8-K](https://www.sec.gov/Archives/edgar/data/899051/000089905126000156/all-20261104.htm) · [NYSE Series J certification](https://www.sec.gov/Archives/edgar/data/899051/000087666123000432/ALLPRJ052423.pdf) · [Debentures Form 8-A](https://www.sec.gov/Archives/edgar/data/899051/000110465913001880/a13-2630_18a12b.htm)

| SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Filed security |
| --- | --- | --- | --- | --- |
| `ALL-PH` | `ALL PR H` | `ALL$H` | `ALL PRH` | Series H depositary share, 5.100% stated rate |
| `ALL-PI` | `ALL PR I` | `ALL$I` | `ALL PRI` | Series I depositary share, 4.750% stated rate |
| `ALL-PJ` | `ALL PR J` | `ALL$J` | `ALL PRJ` | Series J depositary share, 7.375% stated rate |
| `ALL-PB` | `ALL.PR.B` | `ALL$B` | `ALL PRB` | 5.100% fixed-to-floating rate subordinated debentures due 2053 |

The November 12 Nasdaq Trader snapshot gives all four directory counterparts venue code `N` and test and ETF flags `N`. Its existing rules classify H, I and J as depositary receipts and B as debt. The same-day NYSE short-sale volume report has one market-`N` row with positive total volume for each symbol on page 8. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 8](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=8)

SEC submissions bind the November 4 Form 10-Q for September 30 to accession `0000899051-26-000157`, accepted at 21:18:21 UTC, and the November 4 Form 8-K to `0000899051-26-000156`, accepted at 21:16:26 UTC. The Series J certification is accession `0000876661-23-000432` and the debentures Form 8-A is `0001104659-13-001880`. The SEC files below were observed November 13 from 04:32:39 to 04:33:44 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0000899051.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `6d716a5c10d0f9b5ddba01a010dfcec1d63ca6bcad8e331d825d1056c4c18785` |
| November 4 Form 10-Q | `cc07db370373d5397254f4dc86feffda9ae64f71373dd8713151a121d38752de` |
| November 4 Form 8-K | `d511929b2ba867125b30035c97cf4d6c3d9e783366854c7d6673cc1b8c481e4b` |
| NYSE Series J certification | `3000115e622ccbebe7b31a63b83e9ca9e185bd7785439af2206d911707e48ad3` |
| Debentures Form 8-A | `192dbdaed1bc6120d9773ff12250bf80f358b96a0e1ffde893d66dc4abe393f0` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Allstate follow-up brought the reviewed count to 105 of the original 544 SEC-only records, leaving 439 unreviewed at that stage. The four additions included three depositary share matches and one debt identification. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 260 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified all four symbol mappings, six source links, the separate debt identification and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Athene preferred-share follow-up

The November 12 Form 8-K and November 5 Form 10-Q for Athene Holding Ltd. (CIK `0001527469`) identify four NYSE depositary share listings. Each represents 1/1,000 of a perpetual non-cumulative preferred share of the corresponding series. The December 13, 2022 NYSE certification independently identifies the Series E depositary shares. The filings list the `ATHS` debentures separately. [November 12 Form 8-K](https://www.sec.gov/Archives/edgar/data/1527469/000152746926000090/ahl-20261112.htm) · [September-quarter Form 10-Q](https://www.sec.gov/Archives/edgar/data/1527469/000152746926000085/ahl-20260930.htm) · [NYSE Series E certification](https://www.sec.gov/Archives/edgar/data/1527469/000087666122001120/ATHPRE121322.pdf)

| SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Underlying series | Filed rate structure |
| --- | --- | --- | --- | --- | --- |
| `ATH-PA` | `ATHPrA` | `ATH$A` | `ATH PRA` | A | 6.35% fixed before June 30, 2029, then floating |
| `ATH-PB` | `ATHPrB` | `ATH$B` | `ATH PRB` | B | 5.625% fixed |
| `ATH-PD` | `ATHPrD` | `ATH$D` | `ATH PRD` | D | 4.875% fixed |
| `ATH-PE` | `ATHPrE` | `ATH$E` | `ATH PRE` | E | 7.750% fixed before the December 30, 2027 first reset |

The annual securities description supplies the rate boundaries for A and E. The table reports class terms. Future reset rates and current yields require separate evidence. Athene completed the redemption of Series C and its depositary shares on June 30, 2025. NYSE's removal notice specified removal at the July 11 opening. Series C is outside the four matches. [Athene securities description](https://www.sec.gov/Archives/edgar/data/1527469/000152746926000013/q42025exhibit48.htm) · [Series C redemption Form 8-K](https://www.sec.gov/Archives/edgar/data/1527469/000119312525154072/d948326d8k.htm) · [NYSE Series C removal notice](https://www.sec.gov/Archives/edgar/data/876661/000087666125000467/ruleprovisionnotice.htm)

The November 12 Nasdaq Trader snapshot gives each counterpart venue code `N`, test and ETF flags `N`, and an existing depositary-receipt classification. The same-day NYSE short-sale volume report shows one market-`N` row with positive total volume per class on page 14. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 14](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=14)

SEC submissions bind the November 12 Form 8-K to accession `0001527469-26-000090`, accepted at 12:50:55 UTC, and the November 5 Form 10-Q for September 30 to `0001527469-26-000085`, accepted at 21:17:23 UTC. The Series E certification is accession `0000876661-22-001120`. The SEC sources below were observed November 13 from 04:44:23 to 04:46:17 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0001527469.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `b82cbd2a7b3dbb8f36ec366f2a3e203f12632a896815619e17d66722bc315b62` |
| November 12 Form 8-K | `29020cd04c0f74791a0814f2e505626847596354047c53c149ef16de32240cfa` |
| November 5 Form 10-Q | `c7301ee09267e227c6978b7d05b2111ca6abc7efd34bff9f122d441c4bf41c47` |
| NYSE Series E certification | `303eb62ab5bbe047e7a14749c104bd11422a9f401a15e54f79e9666f16e73410` |
| Annual securities description, Form 10-K Exhibit 4.8 | `22abc469f3b36d96258ad5037f6365af0a85cc4a1a3c3f65fba2690ed300565c` |
| July 1, 2025 Series C redemption Form 8-K | `b5803dbfe9f794eba41a4656224c07aa593960673a6e2a92c6ddd288fb37edb1` |
| NYSE Series C removal notice | `72a3501af2849de4f7da2f6d2d1041fb36dad2cb1a6df7b160d82ebda30b3a37` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Athene follow-up brought the reviewed count to 109 of the original 544 SEC-only records, leaving 435 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 261 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the four mappings, seven source links, the filed rate boundaries, the Series C exclusion and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Chimera Investment preferred-share follow-up

The November 5 Form 10-Q and preferred-dividend Form 8-K for Chimera Investment Corporation (CIK `0001409493`) identify four direct cumulative redeemable preferred stock classes on NYSE. The January 22, 2019 NYSE certification independently identifies Series D. The Form 10-Q reports all four classes outstanding at September 30 and lists their optional call dates. [November 5 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1409493/000140949326000068/cim-20260930.htm) · [Preferred dividends Form 8-K](https://www.sec.gov/Archives/edgar/data/1409493/000120677426000594/cim4711711-8k.htm) · [NYSE Series D certification](https://www.sec.gov/Archives/edgar/data/1409493/000087666119000039/CIM8A012219.pdf)

| SEC map | Filing cover and NYSE report symbol | Directory ACT symbol | Series | Rate in class title | Q4 2026 dividend per share declared November 5 |
| --- | --- | --- | --- | --- | --- |
| `CIM-PA` | `CIM PRA` | `CIM$A` | A | 8.00% fixed | $0.50 |
| `CIM-PB` | `CIM PRB` | `CIM$B` | B | 8.00% fixed-to-floating | $0.6343 |
| `CIM-PC` | `CIM PRC` | `CIM$C` | C | 7.75% fixed-to-floating | $0.5751 |
| `CIM-PD` | `CIM PRD` | `CIM$D` | D | 8.00% fixed-to-floating | $0.6153 |

The Series A designation specifies an 8.00% fixed annual rate despite the wording in the Form 10-Q exhibit index. The Form 10-Q describes floating dividend periods for Series B and D beginning March 30, 2024, and for Series C beginning September 30, 2025. The November 5 exhibit reports annualized rates of 10.14841% for B, 9.10041% for C and 9.73641% for D for the declared fourth-quarter dividend. These rates apply to that declaration. Market yields and subsequent resets require separate evidence. [Series A designation](https://www.sec.gov/Archives/edgar/data/1409493/000119312516736773/d267895dex31.htm) · [Form 10-Q](https://www.sec.gov/Archives/edgar/data/1409493/000140949326000068/cim-20260930.htm) · [Preferred dividends exhibit](https://www.sec.gov/Archives/edgar/data/1409493/000120677426000594/cim4711711-ex991.htm)

The November 12 Nasdaq Trader snapshot gives each counterpart venue code `N`, test and ETF flags `N`, and an existing preferred-stock classification. The same-day NYSE short-sale volume report has one market-`N` row with positive total volume for each symbol on page 36. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 36](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=36)

SEC submissions bind the November 5 Form 10-Q for September 30 to accession `0001409493-26-000068`, accepted at 21:11:48 UTC, and the preferred-dividend Form 8-K to `0001206774-26-000594`, accepted at 11:45:43 UTC. The Series D certification is accession `0000876661-19-000039`. The SEC sources below were observed November 13 from 04:49:48 to 04:51:06 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0001409493.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `a6ee3b61f4eaefaa1cc9b12420488aee79d395ec1e518e878cd36be7bef06476` |
| November 5 Form 10-Q | `46287ca28122b999e1c15af76bda4d659cc85fc242daa72a0d2b811cc83a9fef` |
| November 5 preferred-dividend Form 8-K | `7f43bd66b3058eee9a65e59808d90b4479911db1d1f8a12d3d48be3b0e981207` |
| November 5 preferred dividends Exhibit 99.1 | `f674a4b0bbf453fbab4ab0061f5fb389be1d71e186bc5dc54f622718e59c3098` |
| NYSE Series D certification | `e901af3dec528db38d289ef525f0cd55643c63befd7fa2d4ab21e4e8d16fdf81` |
| Series A designation, Form 8-K Exhibit 3.1 | `b71dd4f073e1a17236f60553f9e473ae3adeaeb5586ed32ad1ce5e8fe6f38303` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Chimera Investment follow-up brought the reviewed count to 113 of the original 544 SEC-only records, leaving 431 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 262 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the four mappings, six source links, the dated floating-rate declarations and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Fifth Third preferred-share follow-up

The November 3 Form 10-Q for Fifth Third Bancorp (CIK `0000035527`) lists four NYSE depositary share classes. The June 9 transfer Form 8-A and NYSE certification corroborate each class and share fraction. The June 11 Form 25 concerns the Nasdaq withdrawal. The common stock's separate NYSE Texas registration falls outside this review. [November 3 Form 10-Q](https://www.sec.gov/Archives/edgar/data/35527/000003552726000243/fitb-20260930.htm) · [Transfer Form 8-A](https://www.sec.gov/Archives/edgar/data/35527/000119312526263043/d145237d8a12b.htm) · [NYSE certification](https://www.sec.gov/Archives/edgar/data/35527/000087666126000519/FITB060926.pdf) · [Nasdaq withdrawal Form 25](https://www.sec.gov/Archives/edgar/data/35527/000119312526267509/d132955d25.htm)

| SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Underlying series | Interest in one preferred share |
| --- | --- | --- | --- | --- | --- |
| `FITB-PA` | `FITB PrA` | `FITB$A` | `FITB PRA` | Class B, Series A | 1/40 |
| `FITB-PI` | `FITB PrI` | `FITB$I` | `FITB PRI` | I | 1/1,000 |
| `FITB-PK` | `FITB PrK` | `FITB$K` | `FITB PRK` | K | 1/1,000 |
| `FITB-PM` | `FITB PrM` | `FITB$M` | `FITB PRM` | M | 1/40 |

The Form 10-Q reports that Fifth Third issued Series M depositary shares to Comerica Series B holders at the February 1 merger. The June 3 Form 8-K reporting the June 1 transfer announcement records the earlier Nasdaq symbols `FITBP`, `FITBI`, `FITBO` and `FITBM` for A, I, K and M, respectively. [Form 10-Q, acquisition note](https://www.sec.gov/Archives/edgar/data/35527/000003552726000243/fitb-20260930.htm) · [Transfer announcement Form 8-K](https://www.sec.gov/Archives/edgar/data/35527/000119312526255417/d157060d8k.htm)

The transfer Form 8-A gave June 12 as the expected NYSE start. The June 12 NYSE short-sale volume report independently shows activity for all four on page 64. The report supports trading on that date. First executions remain unverified. The November 12 Nasdaq Trader snapshot gives the four counterparts venue code `N`, test and ETF flags `N`, and existing depositary-receipt classifications. The same-day NYSE short-sale volume report has one market-`N` row with positive total volume per class on page 65. Both reports cover limited activity on their dates. Continuous listing and current trading status require separate evidence. [June 12 NYSE report, page 64](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202606/NYSEshvol20260612.pdf#page=64) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 65](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=65)

SEC submissions bind the November 3 Form 10-Q for September 30 to accession `0000035527-26-000243`, accepted at 21:49:30 UTC. The June 9 Form 8-A and certification are `0001193125-26-263043` and `0000876661-26-000519`, respectively. The June 11 Form 25 is `0001193125-26-267509`. The SEC files and June 12 NYSE report listed below were observed November 13 from 04:54:14 to 04:55:47 UTC, November 12 in Toronto. [SEC submissions](https://data.sec.gov/submissions/CIK0000035527.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `01187b216badc9aa58a5d845a6e297221109f9ee9928873873480843e49ee411` |
| November 3 Form 10-Q | `d822180e7c2a86f318a73ec4e9c459ac695502aa43694854d7100d045edb343d` |
| June 3 transfer announcement Form 8-K | `06e1c2997feb88bcd3023cce7f1a06592a7500f34e2e6d84313dc0c36279ee4b` |
| June 9 transfer Form 8-A | `b6c75d2dddffe46e6bdd80e07f58f779866237e7f1c347986b1b5a27c0711f59` |
| June 9 NYSE certification | `732a00506a3e3fda4d8fdfb531a696754ec932debe9ba74fb2292b2e19d9c360` |
| June 11 Nasdaq withdrawal Form 25 | `91b7a13f7594460bc732fd9d5dda6b2e13382d770ec30fddc72f359bfa9de329` |
| June 12 NYSE short-sale volume report | `adb6a5e70616d219eeb9466ad5c7ed347f7a786aeceeab98b64a17d19b28880b` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Fifth Third follow-up brought the reviewed count to 117 of the original 544 SEC-only records, leaving 427 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 263 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the four mappings, six source links, the Nasdaq withdrawal and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Global Net Lease preferred-share follow-up

The November 5 Form 8-K and November 4 Form 10-Q for Global Net Lease, Inc. (CIK `0001526113`) identify four direct cumulative redeemable preferred stock classes on NYSE. The Form 10-Q shows all four outstanding at September 30. The September 11, 2023 NYSE certification independently confirms approval to list and register Series D and E. [November 5 Form 8-K](https://www.sec.gov/Archives/edgar/data/1526113/000110465926123343/tm2628765d1_8k.htm) · [September-quarter Form 10-Q](https://www.sec.gov/Archives/edgar/data/1526113/000162828026070177/gnl-20260930.htm) · [NYSE Series D and E certification](https://www.sec.gov/Archives/edgar/data/1526113/000087666123000715/GNLPRDGNLPRE091123.pdf)

| SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Series | Stated class rate |
| --- | --- | --- | --- | --- | --- |
| `GNL-PA` | `GNL PR A` | `GNL$A` | `GNL PRA` | A | 7.25% |
| `GNL-PB` | `GNL PR B` | `GNL$B` | `GNL PRB` | B | 6.875% |
| `GNL-PD` | `GNL PR D` | `GNL$D` | `GNL PRD` | D | 7.50% |
| `GNL-PE` | `GNL PR E` | `GNL$E` | `GNL PRE` | E | 7.375% |

The September 12, 2023 merger closing filing records the conversion of The Necessity Retail REIT Series A and C shares into Global Net Lease Series D and E, respectively. It reports both successor classes listed on NYSE as of the closing date. In the separate August 2026 Modiv merger, Modiv Series A holders received cash. The Modiv class falls outside these four matches. [2023 merger closing Form 8-K](https://www.sec.gov/Archives/edgar/data/1526113/000110465923100026/tm2325830d1_8k.htm) · [2026 Modiv merger closing Form 8-K](https://www.sec.gov/Archives/edgar/data/1526113/000110465926095323/tm2622741d1_8k.htm)

The November 12 Nasdaq Trader snapshot gives each counterpart venue code `N`, test and ETF flags `N`, and an existing preferred-stock classification. The same-day NYSE short-sale volume report has one market-`N` row with positive total volume per class on page 76. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 76](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=76)

SEC submissions bind the November 5 Form 8-K to accession `0001104659-26-123343`, accepted at 21:15:56 UTC, and the November 4 Form 10-Q for September 30 to `0001628280-26-070177`, accepted at 21:19:24 UTC. The Series D and E certification is accession `0000876661-23-000715`. The SEC sources below were observed November 13 from 12:51:28 to 12:52:39 UTC. [SEC submissions](https://data.sec.gov/submissions/CIK0001526113.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `4e485168740ea81628a5ad5c3f9f6ea6a76c051104963bef09add28bedc29616` |
| November 5 Form 8-K | `2b56a889409edaa97a8f656e996db6f876eab7b38709c333fa0969ad1a6dcf42` |
| November 4 Form 10-Q | `cfd79c4b9f86067e8bf65b9ae67f6915ae6fe46661715f82bb748afd2aa16b88` |
| NYSE Series D and E certification | `4d79652c53d9cee169061f438ea1b63b3be9c48bf01b3b1e2130eb160db1d3a0` |
| 2023 merger closing Form 8-K | `8429af6bcb0cfdeed020285296645894db36a53732bdd91c17a7a59c38029839` |
| 2026 Modiv merger closing Form 8-K | `965f20228a2b87f14452c221bfd30cb5b775f4e394437d7f3f3dae7ab1ae64b4` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The Global Net Lease follow-up brought the reviewed count to 121 of the original 544 SEC-only records, leaving 423 unreviewed at that stage. Eight of the original 282 directory-type gaps had dated class evidence. PFBC's IRS number remained unreconciled.

The integration passed 264 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the four mappings, six source links, the Series D and E predecessor classes and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### KeyCorp preferred-share follow-up

The November 3 Form 10-Q and November 2 Form 8-K for KeyCorp (CIK `0000091576`) identify four NYSE depositary share listings. Each share represents 1/40 of an underlying preferred share. The August 25, 2022 NYSE certification independently identifies the Series H depositary shares. The November 12 Nasdaq Trader description of `KEY$L` omits the reset feature shown in both SEC covers and the certification. The original directory wording remains the dated source observation. [November 3 Form 10-Q](https://www.sec.gov/Archives/edgar/data/91576/000009157626000023/key-20260930.htm) · [November 2 Form 8-K](https://www.sec.gov/Archives/edgar/data/91576/000119312526443714/d156521d8k.htm) · [NYSE Series H certification](https://www.sec.gov/Archives/edgar/data/91576/000087666122000709/KEYPRL082522.pdf)

| SEC map | Filing cover | Directory ACT symbol | NYSE report symbol | Underlying series | Filed rate structure |
| --- | --- | --- | --- | --- | --- |
| `KEY-PI` | `KEY PrI` | `KEY$I` | `KEY PRI` | E | Fixed-to-floating |
| `KEY-PJ` | `KEY PrJ` | `KEY$J` | `KEY PRJ` | F | Fixed |
| `KEY-PK` | `KEY PrK` | `KEY$K` | `KEY PRK` | G | Fixed |
| `KEY-PL` | `KEY PrL` | `KEY$L` | `KEY PRL` | H | Fixed-rate reset |

The October 20 earnings exhibit gives December 15, 2026 for the scheduled Series E floating-rate transition and December 15, 2027 for the first Series H reset. These dates describe the filed terms. The Form 10-Q's Note 16 confirms completion of the separate September 15, 2026 redemption of Series D and its 1/25 depositary shares. Series D falls outside these four matches. [October 20 preferred dividend terms](https://www.sec.gov/Archives/edgar/data/91576/000009157626000020/a3q26earningspresentatio.htm) · [Form 10-Q, Note 16](https://www.sec.gov/Archives/edgar/data/91576/000009157626000023/key-20260930.htm)

The November 12 Nasdaq Trader snapshot gives each counterpart venue code `N`, test and ETF flags `N`, and an existing depositary-receipt classification. The same-day NYSE short-sale volume report has one market-`N` row with positive total volume per class on page 100. The report covers limited activity for that date. Continuous listing and current trading status require separate evidence. [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt) · [November 12 NYSE report, page 100](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=100)

SEC submissions bind the November 3 Form 10-Q for September 30 to accession `0000091576-26-000023`, accepted at 21:45:12 UTC, and the November 2 Form 8-K to `0001193125-26-443714`, accepted at 21:23:17 UTC. The three SEC files in the digest table were observed November 13 from 12:57:34 to 12:58:20 UTC. The Series H certification is accession `0000876661-22-000709`. The official SEC web copies of the certification and October 20 exhibit were inspected. The local certificate request returned HTTP 503, so those two supporting sources have no local digest in this review. [SEC submissions](https://data.sec.gov/submissions/CIK0000091576.json)

| Captured source | Raw SHA-256 |
| --- | --- |
| SEC submissions | `2e7bab0cf58d7b8ddccda5902e5b4c3d52f4e9c459e2b7d3b2b30339a1e7483b` |
| November 3 Form 10-Q | `b96a1bdd2c99e33ddc68942d9018300d23affb07b3900ad238406e597e696b9b` |
| November 2 Form 8-K | `f74d5ca79701ec10ec0e75f6ef88daf42bf85511cdb062e826bd10b9527572c8` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

The KeyCorp batch brought the SEC-only review to 125 of the original 544 records, with 419 unreviewed at that stage. Eight of the 282 directory-type gaps had dated class evidence, with 274 unreviewed. The findings remain scoped to personal research. Full U.S. coverage remains unverified. PFBC's IRS number remains unreconciled.

The integration passed 265 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the four mappings, six source links, the rate-term distinctions, the Series D exclusion and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### M&T Bank preferred-share follow-up

The November 5 Form 10-Q and October 16 Form 8-K for M&T Bank Corporation (CIK `0000036270`) list all four symbols on NYSE. The Form 10-Q cover names the underlying preferred classes. NYSE's original certifications distinguish the listed instruments. The November 12 Nasdaq Trader directory gives Series H an explicit preferred type and Series J, K and L explicit depositary types, so these matches add four SEC-only reviews and zero directory-type reviews. [November 5 Form 10-Q](https://www.sec.gov/Archives/edgar/data/36270/000003627026000060/mtb-20260930.htm) · [October 16 Form 8-K](https://www.sec.gov/Archives/edgar/data/36270/000003627026000057/mbt-20261016.htm) · [Nasdaq Trader directory](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt)

| SEC map | SEC cover | Nasdaq Trader | Listed instrument | NYSE certification |
| --- | --- | --- | --- | --- |
| `MTB-PH` | `MTBPrH` | `MTB$H` | Series H direct preferred stock, fixed-to-floating | [March 31, 2022](https://www.sec.gov/Archives/edgar/data/36270/000087666122000329/MTBPRH033122.pdf) |
| `MTB-PJ` | `MTBPrJ` | `MTB$J` | Series J depositary share, 1/400 of 7.500% preferred stock | [May 14, 2024](https://www.sec.gov/Archives/edgar/data/36270/000087666124000343/MTBPRJ051424.pdf) |
| `MTB-PK` | `MTBPrK` | `MTB$K` | Series K depositary share, 1/400 of 6.350% preferred stock | [November 3, 2025](https://www.sec.gov/Archives/edgar/data/36270/000087666125000827/MTBPRK110325.pdf) |
| `MTB-PL` | `MTBPrL` | `MTB$L` | Series L depositary share, 1/400 of 6.625% preferred stock | [July 23, 2026](https://www.sec.gov/Archives/edgar/data/36270/000087666126000638/MTBPRL072326.pdf) |

Series H succeeded People's United Series A in the April 1, 2022 merger. The November 5 filing records the separate full redemption of Series F on November 1, 2026. Series F falls outside the batch. All four directory rows have NYSE code `N` and test and ETF flags `N`. Page 116 of the November 12 NYSE report shows positive total volume for `MTB PRH`, `MTB PRJ`, `MTB PRK` and `MTB PRL`. That report corroborates activity on its date. First trade, continuous listing history, current yield and analysis eligibility require separate evidence. [Merger Form 8-K](https://www.sec.gov/Archives/edgar/data/36270/000119312522094296/d349120d8k.htm) · [November 12 NYSE report, page 116](https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=116)

SEC submissions bind the September 30 Form 10-Q to accession `0000036270-26-000060`, accepted November 5 at 18:21:11 UTC, and the earnings Form 8-K to `0000036270-26-000057`, accepted October 16 at 10:02:42 UTC. The SEC submissions, filings and certifications below were observed November 13 from 13:02:18 to 13:03:17 UTC. [SEC submissions](https://data.sec.gov/submissions/CIK0000036270.json)

| Source receipt | Raw SHA-256 |
| --- | --- |
| SEC submissions | `b262bb1acce56ec3515103bcf905a8aedaa88e743d238984dfb1d518704ce2ff` |
| November 5 Form 10-Q | `2fa7c940bd39ea926d456c10cc1790876f6e7bc4c82b7744c98ebf63c021b614` |
| October 16 Form 8-K | `c84ecfe87c2bed9158f8eac78b1d122b15d15c0e72b04360aa007de888db6c10` |
| Merger Form 8-K | `81369268673711d6282d8893f7377db70462ba78a5a80d9d2e38cdfd51895b1c` |
| NYSE Series H certification | `830688b1a47e89b4c07ec60e2fed954bd4f418fd329130984141b28111e15253` |
| NYSE Series J certification | `aa10829a5d1bdef82b0c6d4cf861193b77b5e47bd63f0225b47548b652549334` |
| NYSE Series K certification | `a562e1287267c16066fc492d540a0f86e477484d5d20923c35bb738e2d3da195` |
| NYSE Series L certification | `8d7ffd7fae710eb04b723c34134127bbb10237f785b5ac51e3e088c49a82ee0c` |
| November 12 Nasdaq Trader other-listed directory | `7dd8aa2f8b3334bbdabceede7320475e50ef9a63e094151c6e616115e2cdbc3e` |
| November 12 NYSE short-sale volume report | `2e0e63aa7ed6ca20582c96dadf720b4994dd74d6000dde1ced4191422b7f7fd0` |

**129 of the original 544 SEC-only records have been reviewed, with 415 unreviewed.** Eight of the 282 directory-type gaps have dated class evidence, with 274 unreviewed. The findings remain scoped to personal research. Full U.S. coverage remains unverified. PFBC's IRS number remains unreconciled.

The integration passed 266 affected tests, six research route checks and automated browser checks at 1440 × 1000 and 390 × 844. Both browser runs verified the four mappings, eight scoped source links, the Series F exclusion, and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

#### Preferred Bank FDIC filing follow-up

The FDIC's public securities filings index for certificate `33539` ties Preferred Bank to Form 10-Q filing `12041`, filed November 9, 2026 for the quarter ended September 30, and Form 10-K filing `11872`, filed March 2, 2026 for the year ended December 31, 2025. Attachment 1 in each filing contains the Section 12(b) cover row for **PFBC common stock, no par value, on Nasdaq Stock Market LLC**. Both covers report the same bank name and certificate. The IRS identification number differs between the annual and quarterly covers and remains unreconciled. The October 27 Form 8-K cover lacks a Section 12(b) grid. [FDIC securities filings portal](https://securitiesfilings.fdicconnect.fdic.gov/) · [Certificate 33539 filings index](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/cert/33539) · [Form 10-Q](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12041/attachment/1) · [Form 10-K](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11872/attachment/1) · [Form 8-K](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12028/attachment/1)

The FDIC index and both cover documents were observed November 12 at 23:36:33, 23:37:17 and 23:37:18 UTC, respectively. Raw SHA-256 was `01425742eb85700a4b9408dbe6b2a20c0706633335f78dbfb5611e4dba9a1516` for the index, `20817448c10fea5d0047cdd6727148d3bcbc4127b57e8bdad174a7eed4dfb1ae` for the Form 10-Q and `36188ea29c839ffad580958b7bf7aae2ed3cd5cc4c25a82c958dd6f043d70316` for the Form 10-K. The exact row supplies a dated instrument and venue observation for PFBC. The original directory rule result remains unknown, and these documents supply no new automated financial coverage.

The follow-up passed 245 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the new dated findings and source links, the separate live classification filters with controlled responses and the earlier venue summary. Opening the dated review made zero source requests. All 89 protected files matched the baseline.

#### Preferred Bank IRS identification number review

The FDIC lists Preferred Bank under certificate `33539`. The reviewed filing covers show a repeated split between quarterly and annual/current reports. The bank certificate and the common-stock row provide the dated listing evidence. The correct IRS number remains unresolved. [FDIC supervised-bank list](https://www.fdic.gov/analysis/list-fdic-supervised-banks-filing-under-securities-exchange-act) · [Certificate 33539 filings index](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/cert/33539)

| FDIC filing covers reviewed | IRS number as filed |
| --- | --- |
| 2025 Form 10-Q covers for [March](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11715/attachment/1), [June](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11787/attachment/1) and [September](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11832/attachment/1) | `95-4340119` |
| 2026 Form 10-Q covers for [March](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11944/attachment/1), [June](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11992/attachment/1) and [September](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12041/attachment/1) | `95-4340119` |
| [Two 2024 Form 10-K entries](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11658/attachment/1) ([second entry](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11659/attachment/1)), [2024 Form 10-K/A](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11687/attachment/1), [2025 Form 10-K](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11872/attachment/1) and [October 27, 2026 Form 8-K](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12028/attachment/1) | `95-4340199` |

The April 15, 2025 Form 10-K/A explanatory note limits the amendment to filing the clawback policy with accompanying certifications. It retains `95-4340199`. The reviewed public filings supplied no correction or authoritative confirmation that resolves the conflict. Eight additional PDFs were observed November 13 from 00:02:28 to 00:02:35 UTC, November 12 in Toronto. The amendment's raw SHA-256 was `5a193b25b25eeeff7afbae1d6b928fa32ead6369af178b3c68bd6be8809a7ec8`. [FDIC amendment](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11687/attachment/1)

The index refreshed at 00:04:48 UTC on November 13 with the same 272 entries and raw digest. The 35 filings dated in 2025 and 2026 include one amendment by form label, the 2024 Form 10-K/A. The two March 14 annual attachments have different bytes and agree on their cover fields. The reviewed evidence leaves their order of precedence open. [FDIC filings index](https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/cert/33539)

The Triton and PFBC follow-up passed 247 affected tests, six research route checks and automated desktop and phone checks. The browser checks verified the new findings, 19 dated review links and the existing classification controls with controlled responses. Opening the dated review made zero source requests. All 89 protected files matched the baseline.
