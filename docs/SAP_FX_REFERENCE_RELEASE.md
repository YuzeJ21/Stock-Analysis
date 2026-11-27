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
PR126's [one-shot capture](https://github.com/YuzeJ21/Stock-Analysis/actions/runs/46076941699)
succeeded at 2026-11-27T22:29:37.486966Z. Its exact November 23 reference is
**1.0939 USD per EUR**. The 70,573 original XML bytes have SHA-256
`bcca89ff638aebb161b8da6158e7095891436c1ac74e74070529d4810b29c0d6`.
The [retained-byte inspection](https://github.com/YuzeJ21/Stock-Analysis/actions/runs/46077581899)
reused that immutable public artifact, matched the receipt and parsed the raw XML;
it made no new ECB request. This PR's subsequent fixes inspect that same artifact,
with public-artifact read access limited to the separate source workflow.

The actual retained SAP review at 2026-11-27T22:36:41.141615Z reproduced filed
EUR 6.10 × 1.0939 = **USD 6.672790 per ordinary share**. Original context time
remains 2026-11-24T05:16:08+00:00, with its November 23 price date. The original
session SHA-256 remains `a76aabe08c0f0ac3f1aaf1e0de863acea85184a2bcb9e2396a0a19fa9bd3ba4e`.
The offline reconstruction made zero provider requests and changed no original
bytes. Later retrieval is explicit; valuation, point-in-time and commercial
eligibility remain false. The separate minimal package contains the original
XML, receipt/transport metadata, attribution and derived review only.

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
review is claimed. First CI passed 172 SAP/FX checks but the phone case exposed
mobile-selector interaction and download-rerender timing; the harness now uses
the explicit phone control and existing completed-render/DOM-stability waits.
No thresholds, route checks or no-refetch assertions were removed. Fresh browser
and full CI are required for this correction; no new full-suite pass is asserted.

The pending PR125 full run completed with 10,682 passes, three skips and two
authentication-fixture failures: collection-time future nbf/iat values aged into
the past during the 67-minute run. A two-hour-delay reproduction failed before
the fix and passed afterward. PR125 head 43897487 sets those future values at
execution; production authorization remains unchanged. Its fresh source/browser
gate passed 98 cases and the strict journey passed, but release regressions exposed
a refresh-popover geometry assertion (109 passed before stopping). The later
stage retains full diagnostic geometry output; fresh CI must resolve this gate.

## Following stages

1. Complete current-revision release verification, then review remaining
   security/continuity/accounting requirements before proposing valuation use.
2. Operate a private pilot on a selected actual host, with identity provider,
   named owner, private storage/audit, retention and demonstrated recovery.
3. Observe 10–20 consented actual researchers and later returns. Existing source,
   hosted-account and human gates cannot be completed by another mock or template.

[Full execution goal](goals/SAP_FX_REFERENCE_GOAL.md).
