# Exact FX reference and separate historical currency review

Reviewed November 27, 2026. This follows PR125's dated listing/price assessment.
The new workflow captures one official public ECB reference. The app offers a
separate explicit historical currency review without changing original research.

## Delivered behavior

Current and historical Valuation & Peers and Data Sources have a closed Currency
conversion review entry. It makes no source request on ordinary render, route
change, saved replay or Monitor. Fetch FX reference is available only with a
matched dated SAP listing/price basis. The source capture is cached for the exact
original context/profile; a different context does not inherit the review.
Protected workspaces hold this prebuilt download for viewer, editor and owner
before package construction and at the export boundary; they require a separately
authorized delivery endpoint. Personal-mode download remains available.

The calculation translates directly reported native EUR EPS into a derived USD
amount per ordinary share using the exact price-date USD-per-EUR reference. It
uses Decimal and retains both original literal precisions. Extra decimal places
are arithmetic on rounded reported EPS, not greater economic precision. It does
not assert issuer-reported USD EPS, ADS/ADR mapping, P/E, a valuation denominator,
industry-reference admission, accounting comparability or commercial eligibility.

FX retrieval and review time are distinct from original research time. A later
capture does not establish availability at the old cutoff or first publication.
Point-in-time and valuation eligibility remain false. Neither the original source
capture nor saved research context is rewritten or retroactively supplemented.

Download currency review exports only fx.xml, receipt.json, SOURCE.txt and a
minimal review.json. Original notes, profile identifiers and complete private
research contexts are excluded. Raw XML is reparsed and the full receipt matched
before projection or export. Original transport timestamp/header metadata is
retained independently of the parsed receipt and checked against it. Subsecond
observation/review precision is preserved. Only a canonical revision digest and
validated profile binding can enter a derived review. Checksums establish consistency, not authenticity
against an entirely fabricated source and receipt.

## Exact source contract

The fixed [ECB last-90-days XML](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml)
is requested once, with a 20-second socket timeout and 2 MiB maximum. The socket setting is not
a guaranteed total wall-clock deadline. Complete HTTP 200 responses are required;
partial/content-range and advertised-length conflicts are rejected. There is no retry,
redirect, credential, nearest-date substitution or broad refresh. Parsing rejects
DTD/entities, non-UTF-8 or oversized bodies, wrong sender/namespace, duplicates,
wrong date, reversed/extra unit fields, nonpositive or nondecimal USD values.
Large legitimate non-USD quotations do not invalidate the selected USD rate.

The [ECB reference page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
describes informational euro-base references and discourages transaction use.
The [copyright conditions](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)
require accurate attribution and identification of modifications, with additional
disclosure conditions for paid distribution. The package cites ECB and marks the
calculation as derived. This review grants no product-wide source permissions.
Server Last-Modified, when supplied, is retained as metadata, not first publication.

## Acquisition and verification

The normal release workflow remains offline. A separate same-repository PR-open
workflow captures the retained price date November 23, 2026, into disposable runner
storage and preserves only the three named public source files for 30 days.
Unavailable acquisition exits nonzero and emits an explicit withheld receipt,
without fabricated XML or values. Subsequent fixes should reuse captured bytes.
Inspect the acquisition receipt/artifact before asserting actual source success;
a unit fixture or successful engineering job is not captured-source evidence.

The parser, Decimal review, explicit UI/cache and export checks were observed RED
then GREEN. Final focused integration passed 503 checks with one existing dateutil
warning. The constructed test uses a 1.2500 rate and hand-calculated 7.625000 USD
per ordinary share; it is not a captured actual ECB observation. Desktop/phone
browser cases exercise explicit action, route reuse, profile separation and ZIP
contents. Independent review found two critical and four important issues: minimal-runtime
imports, protected export, timestamp integrity/precision, private revision export,
XML shape, and browser route coverage. Those were corrected in one regression-driven
pass. A response-completeness concern was treated as material provenance and fixed
in the same pass. Twenty negative cases and an additional mixed-text source case
were observed failing before corrections. Actual compositor tests now cover current
and historical Valuation/Sources and absence of FX controls in Monitor. No second
review is claimed. Exact-head acquisition and browser/full CI still require their
current-revision results; no new full-suite pass is asserted here.

The pending PR125 full run completed with 10,682 passes, three skips and two
authentication-fixture failures: collection-time future nbf/iat values aged into
the past during the 67-minute run. A two-hour-delay reproduction failed before
the fix and passed afterward. PR125 head 43897487 sets those future values at
execution; production authorization remains unchanged and fresh CI is required.

## Following stages

1. Preserve and inspect actual acquisition evidence, then review any remaining
   security/continuity/accounting requirements before proposing valuation use.
2. Operate a private pilot on a selected actual host, with identity provider,
   named owner, private storage/audit, retention and demonstrated recovery.
3. Observe 10–20 consented actual researchers and later returns. Existing source,
   hosted-account and human gates cannot be completed by another mock or template.

[Full execution goal](goals/SAP_FX_REFERENCE_GOAL.md).
