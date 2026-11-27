# SAP listing/price basis and FX method review

Reviewed November 27, 2026. This follows PR124's native-EPS source basis and adds
an independent listing/price context assessment. It does not resolve the generic
vendor issuer-ID association, USD earnings, P/E or comparison eligibility.

## Delivered

The selected Workbench price route is bounded to its existing one-year request.
The two-year peer-packet route and generic issuer validator are unchanged.
The app retains SAP's already-validated price symbol, venue, instrument type,
timezone, rights and adjustment metadata in new normalized research contexts.
A pure assessor requires the exact reviewed SAP v2 filing/directory scope, the
USD Yahoo SAP/NYQ observation, independently retained date/close/identity binding in the daily receipt, original cutoff and source
observations within 24 hours. It performs a weekday/New York 16:00 sanity check;
this is not a holiday/early-close exchange calendar. It explicitly preserves
vendor issuer-ID, continuity, adjustment, FX, accounting and permission holds.

Current Valuation & Peers and Data Sources and saved Workbench/Monitor show the
same derived assessment. Old snapshots without the new metadata stay readable
and keep native filing evidence; their price basis remains unverified. A listing
match does not replace the separate generic issuer-association check. No numeric
valuation is calculated and the US-GAAP/USD comparison rules are unchanged.

## Actual retained evidence

The original November 24 capture contains SAP's November 23 daily close of
203.39999389648438 USD, observed November 24 at 05:16:06 UTC. The new normalizer
matches SAP/NYQ/NYSE/EQUITY to the exact reviewed SAP NYSE ADS directory and
filing scope at the original shared cutoff 05:17:10.091926 UTC. The resulting
context saves and reopens unchanged. No transport runs or source timestamps are
rewritten; the retained session's SHA-256 remains
`a76aabe08c0f0ac3f1aaf1e0de863acea85184a2bcb9e2396a0a19fa9bd3ba4e`.
The receipt binding establishes internal consistency, not external source
authenticity or protection against an entirely fabricated source and receipt.
The peer comparison remains withheld for the separate depositary method.
These dated observations are not current-market evidence or new cohort coverage.

## FX investigation and proposed next method

The [ECB reference-rate page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
quotes foreign currencies per euro and describes the rates as informational;
transaction use is discouraged. The [ECB framework](https://www.ecb.europa.eu/stats/pdf/exchange/Frameworkfortheeuroforeignexchangereferencerates.en.pdf)
describes the setting/publication process. The [copyright conditions](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)
require accurate attribution, identification of modifications, and additional
disclosures for paid distribution. These reviewed conditions identify a candidate
source; they do not authorize all product data or certify commercial readiness.

A proposed separate research convention uses the reference rate for the exact
price date, expressed as USD per EUR, with the reviewed ordinary-shares/ADR ratio.
Any translated amount must be labelled derived; it is not issuer-reported USD EPS.
A fiscal annual-average translation is a different convention and must not be
silently substituted. IFRS and US-GAAP earnings do not become comparable through
currency conversion. No addition to the existing peer pool is proposed.

No raw FX observation was captured. Data Portal/API retrieval was unavailable
and the official historical XML download failed. Search-rendered table cells are
not a retained source response with a verifiable digest/publication receipt.
Capture the exact permitted response, original observation time, rate direction,
date and publication evidence before implementing the proposed translation.
Do not backdate a future retrieval into the November 24 cohort or repeat unchanged
access probes. USD/ADS EPS and P/E therefore remain withheld.

## Verification

The new assessment, normalization and UI checks were observed RED then GREEN.
Final focused integration: 404 passed, with one existing dateutil warning.
An earlier local run encountered the known localhost PermissionError in
`test_history_and_price_sections_survive_streamlit_markdown_on_desktop_and_phone`;
that unchanged browser case needs the declared CI runtime. Desktop/phone browser
assertions include the matched listing context and unresolved FX through save,
Monitor reload and exact return; their current-head result belongs to GitHub CI.
Independent review found two material gaps: the original receipt did not bind
normalized price date/close, and the initial historical Valuation screen omitted
the assessment. Seven regression cases were observed failing before correction;
the final 403-case run passes. The actual retained source still matches unchanged,
and edited date/close records now remain held after resealing and reload. A minor
test-isolation improvement for the closing-clock case is deferred. No second
review is claimed. New-revision browser/full CI remains necessary; no complete-
suite pass is claimed here. PR124 separately passed its 58 SAP, 109 strict-journey
and 115 release-regression checks; its full suite was still running at review.

## Following goals

1. Capture exact FX and publication evidence; review a separately labelled
   conversion convention plus price/security continuity and accounting scope.
2. Supply a selected private host, identity provider and operating owner; verify
   actual storage/audit, retention, recovery and access isolation.
3. Execute 10–20 consented independent researcher sessions and observed later
   returns; existing templates and automated journeys cannot supply these facts.

Full executable prompt: [SAP price-basis goal](goals/SAP_PRICE_BASIS_GOAL.md).

The first new-revision CI passed 95 source/snapshot/basis cases, then failed the
Monitor heading visibility assertion. The combined disclosure embedded a second
style block inside its section; standalone views had passed. The saved composition
now supplies the shared styles once, with a regression for style placement. The
404-case local integration passes; actual browser confirmation requires the new
revision-specific run, with its original heading/receipt/transport assertions.
