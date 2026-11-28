# SAP depositary valuation-basis evidence

## Intent

Advance the next coverage priority after exact-head release reconciliation
passed at `64ec19d0b9acd855f63879941c3bed1213460f39` (10,586 full-suite
passes, three skips; all workflow steps, strict journey and release regressions
passed). Preserve that revision and implement this slice on a separate branch.

The retained November 24 SAP annual source matches the reviewed FY2025 20-F
body digest. It contains directly reported diluted EPS in EUR/share and a
disclosure using the term ADR, with one ordinary share represented by each
ADR. No reviewed USD conversion method or qualified price-to-filing join has
been supplied. Preserve these independent holds and the existing US-GAAP/USD
peer method.

## Approach and scope

Use the existing selected-security observation machinery to parse the exact
annual EPS fact and ratio disclosure, then expose the source basis in the
existing Valuation & Peers and Data Sources views. Preserve that evidence
through the existing normalized snapshot/Monitor workflow. Do not add a new
route, calculation engine, provider, readiness system or snapshot schema.

The user requested execution. The implementation choice is to deliver this
bounded source-backed slice now. Merely repeating the existing generic hold
would not advance coverage; calculating USD P/E would require unsupported
conversion and issuer-price evidence. The actual source uses ADR, so preserve
that unit rather than silently rewriting its terminology to ADS.

## Requirements

- Parse values from bound source bytes; never store an EPS value as a constant.
- Keep exact listing, issuer, annual metadata, body digest, entity, duration,
  concept, currency/unit, source paths and observation chronology checks.
- Use a new SAP policy revision. Legacy saved note-only SAP records remain
  readable; they do not acquire new observations retroactively.
- Bind the normalized EPS literal to its reviewed source-token digest as well
  as its parsed numeric proof, preventing a resealed edited number from passing.
- Snapshot permission applies only to the exact SAP subject-scope path and
  current policy. Wrong ticker, period, currency, note, ratio, flags or source
  metadata cannot gain the raw-token exception. TSM behavior stays intact.
- Validate SAP subject semantics even without a raw token or recognized marker.
  Legacy v1 permits only its exact two source notes; numeric/ratio rows require
  the full v2 contract. Enclosing peer identity, held status, permission flags,
  rights and method claims must agree. Annual leads and the facts query must
  match the exact issuer/filing; a profile cannot predate the filing acceptance.
- Match the selected directory receipt to retained listing metadata and apply
  the existing strict New York minute-clock, nonfuture and seven-day rule at
  the historical receipt. Financial inventory may be a separate valid fetch.
- Historical overview/valuation withhold malformed SAP peer projections while
  preserving independently checked filing fields. Historical Data Sources
  displays validated evidence. Test the production replay compositor and exact
  pinned snapshot/section with a newer decoy record and a server transport guard.
- Replace the single active SAP policy with v2; never append a second SAP/CIK
  live policy. The source ratio uses exact `adr_ordinary_ratio` grammar and a
  source-bound integer one, unit `ordinary_shares/ADR`. The EPS row binds its
  reviewed token SHA-256 and normalized proof. Preserve filed precision.
- Show reported EUR/share and source ADR ratio with source links and dates in
  current and saved views. Do not calculate EPS per ADS, FX, P/E, a reference
  median or a premium. Preserve explicit withholding and independent fields.
- Section changes, note saves and Monitor replay cause no provider requests.
- Constructed tests are software evidence; the retained capture proves only
  its dated source observation. Neither establishes current freshness, source
  rights, hosted operation, independent-human validation or commercial maturity.

## Later stages

Run existing read-only host/source/pilot checks after implementing this slice.
Classify missing host decisions, credentials/permissions and actual researcher
sessions explicitly. Do not fabricate any of those inputs, create accounts,
contact people, merge or deploy. Sync a reviewable branch and actual CI status.
