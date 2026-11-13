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

**91 of the original 544 SEC-only records have been reviewed, with 453 unreviewed.** Eight of the 282 directory-type gaps have dated class evidence, with 274 unreviewed. The findings remain scoped to personal research. Full U.S. coverage remains unverified. PFBC's IRS number remains unreconciled.

The integration passed 257 affected tests, six research route checks and automated desktop and phone checks. Both browser runs verified the six mappings, six source links, the direct Series L and separate Series HH offering, and the prior PFBC finding. Opening the dated review made zero source requests. All 89 protected baseline files matched their saved digests.

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
