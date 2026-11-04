# Quarterly evidence, coverage and listing association

## Intent

Continue the generic online company workflow with reported quarterly financial evidence, a measured cross-industry sample and a source-bound price/filing association. The user has authorized autonomous implementation, automated verification and work-branch synchronization. Preserve canonical data, readiness, credentials and source-rights decisions. No PR, merge, deployment, purchase or publication is included.

## Chosen approach

Reuse the existing Python/Streamlit application and one Companyfacts response for annual and quarterly views. A bounded, exact-URL SEC receipt adapter supplies raw-byte digests without writing a cache. Accept only directly reported supported USD fields with exact filing contexts and registered field scope. Show up to twelve quarter-length periods; display cumulative cash-flow facts separately. Never derive a quarter by subtraction, infer a missing Q4 or relabel cumulative data as single-quarter data. Values are latest reported as observed, including revisions, rather than historical point-in-time evidence.

An explicit price or SEC action may fetch the selected CIK's SEC submissions metadata when both price and filing evidence exist. Match the price symbol (including an explicit share-class alias), supported provider venue codes and the issuer's current SEC ticker/exchange context. Multiple venues, mismatched identities, stale cross-source observations and missing identifiers remain visible holds. A matched listing association is not an independently verified vendor issuer identifier, historical security continuity or valuation clearance. No fuzzy company-name join is permitted.

Measure coverage with a predeclared, bounded cross-industry sample and SEC SIC classifications. Every attempted ticker stays in the denominator, including failures and unknown industries. Count annual, direct quarterly and cumulative fields independently; assess the latest attempted period rather than cherry-picking an older successful period. Do not treat the sample as the U.S. public-company universe or fetch Yahoo in bulk. Provide an explicit Personal Research study action and a read-only command that prints the same aggregate evidence.

Alternatives considered: changing the canonical ingestion pipeline would couple online inspection to saved readiness; buying a new feed would violate the zero-budget constraint; matching on names alone would create unsupported identity claims. None is required for this stage.

## Boundaries

- Existing registered SEC direct-field scope remains unchanged. SEC submissions metadata and Yahoo chart inspection retain separate unregistered personal-inspection status; commercial activation and redistribution remain held.
- Default page renders make no new network request. Results stay in ticker-scoped session memory; an explicit study is bounded to at most twenty tickers and serialized SEC requests.
- Annual and quarterly availability remain independent. An unsupported annual anchor cannot erase otherwise valid direct quarterly evidence.
- Keep listing identity, issuer domicile, security type, active status, analysis eligibility and point-in-time coverage distinct. No source, field, review or rights approval is invented.
- Browser evidence covers desktop, phone and narrow reflow. No human testers are required or claimed.

## Acceptance

Synthetic tests reject raw conflicts, booleans, nonfinite/string amounts, unsupported units/concepts, mixed periods/filings, ambiguous identities and malformed cached evidence. Tests distinguish direct quarter cash flows from cumulative facts and preserve failures in coverage denominators. Bounded live SEC checks across industries and per-company price association checks record real gaps. Fresh whole-change review, the complete repository test suite, browser checks, wording, hygiene and unchanged-data hashes precede a normal work-branch push and exact remote-SHA verification.
