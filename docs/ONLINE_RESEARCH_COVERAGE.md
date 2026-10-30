# Online Research Coverage Method

Discover contains a collapsed **Cross-industry coverage · online sample** panel. Press **Run online coverage sample** to inspect a bounded SEC sample; normal rerenders reuse the current session result. No local company CSV is required. Source access needs the existing identifying `SEC_USER_AGENT`; no API key, payment or new credential is needed.

The declared sample is MSFT, JPM, JNJ, XOM, PG, MCD, CAT, NEM, DUK, O, VZ and TSM. It deliberately spans different businesses and includes an issuer whose reporting definitions may be unsupported. It is a development sample, not a statistically representative sample, complete sector census or U.S. public-company universe. Industry labels are the current SEC SIC code and description, not GICS sectors or domicile classifications.

The read-only command prints the same aggregate evidence:

```sh
python3 -m src.online_research_coverage
python3 -m src.online_research_coverage --tickers MSFT,JPM,JNJ
```

Every requested ticker remains in the denominator. A source failure, unsupported financial definition, missing observation or unavailable SIC is retained, including an unknown-industry group. Requested symbols and resolved unique CIKs are counted separately. Multiple share classes cannot silently become multiple issuers. Duplicate or unrequested observations are invalid.

Counts use the latest reported annual or quarterly period found in compatible Companyfacts contexts and SEC submissions metadata, including a latest period that is withheld. Older supported-concept periods remain separately labelled historical evidence; they never fill a newer reporting gap. An older successful quarter is not substituted to improve coverage. Annual revenue, operating income, operating cash flow and capital spending are counted independently from the equivalent direct quarterly fields. A supported revenue concept can describe customer-contract revenue or net sales rather than every issuer revenue stream; its exact scope remains visible and is not silently treated as a universal total-revenue definition. Cumulative cash flow and capital spending have their own counters and never count as direct-quarter availability. Periods, per-field gaps, observation times, source references and raw-byte digests remain inspectable. These are availability counts, not numerical financial comparisons or investment signals.

One SEC ticker-map receipt is reused within a run. The study accepts at most twenty explicit tickers, serializes source requests and makes no Yahoo price requests. Results stay in session memory; the command prints reduced availability evidence without raw financial amounts. It creates no source cache, import, readiness rebuild or canonical-data write. Prices and the qualified listing association are inspected separately for a selected company.

SEC Companyfacts fields retain the existing registered direct-field scope; raw redistribution is held. SEC submissions identity/SIC metadata is a distinct unregistered personal-inspection source. Commercial mode and non-Personal routes cannot activate or reuse this study. Local engineering and sample availability do not grant distribution rights or establish point-in-time, active-listing, domicile, security-type or analysis-ready coverage.

The next coverage work is to inspect measured taxonomy and industry failures, then reconcile dated official listing and issuer receipts across missing venues. A broad universe claim requires a measured denominator and explicit gaps; success on this sample cannot replace that evidence.

Source context: [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) describes entity-wide standard XBRL concepts, reporting periods and company metadata; [Yahoo source information](https://help.yahoo.com/kb/SLN2310.html) is separate from the current personal price inspection and grants no redistribution approval here.
