# Online Historical Financials and Price Inspection Plan

**Goal:** Extend the generic SEC company workflow with dated annual financial history, comparable revenue direction and session-only personal-research price history, then synchronize reviewed code to the existing GitHub branch after automated checks.

**Design:** Reuse the explicit SEC action's one Companyfacts response. Inspect up to six annual periods using one consistent revenue concept and exact filing contexts, including raw-value/conflict checks and registered direct-field rights. Report latest-as-observed history with publication/observation dates; do not claim point-in-time history. Compare adjacent periods only when definitions, units and annual durations match. Numeric growth rates retain their existing field-scope gate; direct annual values and increase/decrease direction are available.

Price inspection is a separate explicit Personal Research action using the Yahoo chart endpoint. It makes one bounded in-memory request, validates exact provider symbol, equity type, USD currency, exchange timezone, chronology, daily OHLCV and duplicates, and excludes the observation day's incomplete bar. Display provider daily closes with unverified adjustment basis and split events; never imply total returns or a verified SEC-to-price issuer join. `yahoo_chart` remains a distinct unregistered inspection source; the existing yfinance entry is not borrowed as an approval. Commercial use and redistribution remain held. No canonical/readiness/rights file changes, disk caches, credentials, purchases, PR opening, merge, deployment or publication.

1. Add failing synthetic tests and implement SEC annual history with strict revisions, ambiguity, source and comparison boundaries; integrate without repeat network calls.
2. Add failing tests and implement bounded session-only Yahoo price inspection with clear rights/identity/adjustment/freshness states.
3. Add responsive history and price views to Company Workbench, with sources and missing-lane reasons. Update methodology and roadmap.
4. Run relevant and required automated checks, live bounded cross-sector checks, desktop/phone/zoom browser geometry, source/canonical hash checks and independent review. Commit code/docs/tests locally.
5. Verify remote ancestry, push only the current work branch, then verify the exact remote commit and report hosted-check availability separately. Preserve ignored local evidence and a held PR draft.
