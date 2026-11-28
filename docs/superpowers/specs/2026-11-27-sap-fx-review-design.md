# Exact ECB reference and separate SAP currency review

## Intent and choice
Advance the open FX evidence gap with one actual capture and a usable,
inspectable historical calculation. Repeating local download failures gives no
new evidence; embedding a public-source fetch in every engineering test would
make release checks depend on a remote service. The chosen approach is a separate
PR-open source-capture workflow plus an explicit in-app review. The user's repeated
execution request authorizes this bounded read and normal GitHub sync. No core
valuation or saved-snapshot schema changes are proposed.

## Source and parser
Create src/ecb_fx_reference.py. Fixed URL:
https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml.
Use one request, 20-second socket timeout (not an overall deadline), maximum 2 MiB, no redirects to other URLs,
no credentials, and no retries. Capture observation time after reading completes.
The injected fetcher returns (bytes, headers, final_url); a clock supplies an aware
UTC datetime. Personal-research mode is required before transport.

`parse_ecb_usd(raw, *, reference_date, observed_at, last_modified=None)` validates
bytes, date and timestamp; rejects DTD/entity declarations and malformed XML;
requires the GESMES Envelope, ECB sender, ECB eurofxref Cube hierarchy, one matching
date and one USD rate. No nearest-date/weekend substitution. Rate is a positive
ASCII decimal with at most eight decimal places and four integer digits. Preserve
literal precision and SHA-256. Receipt schema ecb-eur-usd-reference-v1 pins EUR
base, USD quote and USD_per_EUR. Transport time and header metadata are retained independently from the parsed
receipt, checked on review, and preserve subsecond precision. Last-Modified is optional metadata, not first
publication proof. Always first_publication_status=unverified and commercial
eligibility false. Reject any reference date after the observation's Berlin date.

`capture_ecb_usd(reference_date, *, fetcher=None, clock=None)` returns a captured
packet {status, receipt, xml: bytes} or stable withheld result. A CLI capture command
writes only fx.xml (on success), receipt.json and SOURCE.txt into an explicitly
supplied disposable output directory; stdout contains a bounded JSON summary.

## Historical review
Create src/sap_fx_review.py. `build_sap_fx_review(context, capture, *, reviewed_at)`
requires assess_sap_price_basis(context) to match, reparses original XML and strictly
matches the complete supplied receipt, requires the reference date to equal the
original price date and both source/context observations <= reviewed_at. Use
Decimal over the source-bound native EUR EPS token and rate literal; result unit
USD/ordinary_share. Pin the exact context digest/source revision and retain its
original observed_at. No FX receipt is attached to or retimestamps that context.

The result always has valuation_eligible=false, commercial_eligible=false,
point_in_time_eligible=false. Explicitly distinguish observation_after_original_cutoff
and unverified first publication. This is a price-date informational translation
of rounded reported ordinary-share EPS, not accounting translation, ADS mapping,
reported USD EPS, a valuation denominator or a comparison. A coherent fabricated
source/receipt is not authenticated by checksum; no signing redesign is included.

## UI and download
Create src/sap_fx_review_ui.py with render_sap_fx_review(st, context, *, fetcher=None,
clock=None). Only SAP appears. Show a closed Currency conversion review expander.
The Fetch FX reference button is enabled only for matched original price basis.
No transport before that action. Cache by digest of the complete original context,
including profile/issuer identity. Ordinary rerenders and section changes reuse the
same capture; another context never receives it. A retry requires another explicit
click. Display a later review separately from original snapshot dates and all holds.
Render in current Valuation/Sources and historical Valuation/Sources, never Monitor.
Download a ZIP of public fx.xml, receipt.json, SOURCE.txt and minimal review.json;
exclude notes and profile keys; require a canonical source-revision digest and
valid original profile scope. Protected workspaces hold all prebuilt exports
before construction/registration and at the package boundary, independent of role.
Validate/recompute before projection or download.
Styling must compose once with existing markup. Preserve all existing no-fetch and
exact-return browser assertions when no new FX action is requested.

## Acquisition workflow
Add .github/workflows/ecb-reference-capture.yml, separate from minimal offline gate.
Trigger on same-repository PR opened only, main base, affected source/workflow paths;
read-only contents permission, no secrets, 5-minute timeout. Check out exact PR head,
Python 3.12 plus existing declared PyYAML for the shared mode guard. Capture reference date 2026-11-23 once into
RUNNER_TEMP/ecb-reference; upload only its three named public files with the official
upload-artifact v7 action, retention 30 days. No original context or private files.
Failure still emits an explicit withheld receipt, not false data; deterministic
unit/browser checks remain mandatory independently. Reuse any captured bytes for
later code fixes rather than refetching or changing original observation time.

## Review focus
- Duplicate dates/rates, wrong namespace/sender, DTD, malformed/oversized bodies.
- Reversed direction, edited normalized receipts and source/price date mismatch.
- Retrieval after original cutoff cannot become historical availability evidence.
- Cached capture must stay with its original profile/context; no automatic fetch.
- ZIP/source artifact contains only allowlisted public source and minimal review.

ECB reference and copyright pages reviewed November 27, 2026: informational use,
accurate attribution and explicit marking of derived modifications are required.
Paid distribution has separate disclosure conditions; no product-wide source-rights
approval follows. Source links belong in the receipt and downloaded attribution.
