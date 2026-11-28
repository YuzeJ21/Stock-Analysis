# SAP price-basis design

## Intent and scope
SAP has a verified NYSE ADS directory row and native EUR ordinary-share EPS,
but its generic price/filing association remains withheld because SEC lists
NYSE and OTC. Add an independently labelled listing/price context assessment,
not a replacement issuer-ID approval or a valuation engine.

## Approaches and decision
Relaxing the generic single-exchange check would affect unrelated share classes.
Enabling USD EPS/P/E now would require missing FX and comparability evidence.
The chosen bounded approach reuses the exact SAP v2 validator, retains the
validated price metadata, and derives an informational assessment for current
and saved views. This is the implementer's choice under the user's execution
instruction; the existing generic association remains independently labelled.

## Contract
`assess_sap_price_basis(context)` in `src/sap_price_basis.py` returns a JSON-safe
status/reason with `valuation_eligible=false`, `commercial_eligible=false`,
`fx_status=unverified`, and no multiple or converted earnings. A match requires
valid SAP v2 scope, exact ticker/CIK, source-bound USD Yahoo SAP/NYQ/EQUITY price
metadata and an independent date/close/identity projection in the daily receipt,
a positive non-boolean close, a completed New York weekday closing
clock, a matching daily-price receipt and source observations within 24 hours,
all at or before the historical context cutoff. This clock is a bounded sanity
check, not an exchange-holiday or early-close calendar. Source adjustments,
vendor issuer ID, continuity and comparison eligibility remain unverified.

`build_online_research_context` retains required price identity metadata for SAP
only, after existing price validation. The semantic source revision binds it.
Old snapshots acquire no metadata or facts retroactively. Invalid/missing new
metadata yields a held basis assessment and must not hide valid native EPS.
The current Valuation & Peers/Sources views and historical SAP/Monitor disclosure
reuse one HTML projection. No network or filesystem write belongs in assessment. The current selected-price
route uses the existing one-year URL; two-year peer packets remain separate.
Receipt consistency is not source authentication: joint source/receipt fabrication
is outside this normalized snapshot contract.

## FX source research
ECB official reference-rate and copyright pages were reviewed November 27, 2026.
References are informational and quoted as foreign currency per euro. Conditions
include source attribution, accurate reproduction and marking modifications;
paid distribution has additional disclosure conditions. This is source research,
not project-wide commercial approval. Proposed future convention: price-date
USD per EUR times native EUR per ordinary share times ordinary shares per ADR,
explicitly derived and separate from reported EPS and the US-GAAP peer method.
Annual-average convenience translation is a different method. No raw rate was
captured: Data Portal/API could not be retrieved and official XML download failed.
Do not invent a rate, source hash or historical receipt, or retry unchanged access.

## Review focus
- A forged price currency, venue or same-name OTC symbol must not match.
- A directory/price/profile observation after the saved cutoff must be withheld.
- Missing legacy price metadata preserves original native filing presentation.
- A matched listing context must never override any valuation/rights hold.
- Current and historical projections must use the identical assessment.
