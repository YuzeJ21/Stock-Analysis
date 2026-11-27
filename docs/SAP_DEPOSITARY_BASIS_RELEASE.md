# SAP depositary source-basis research

Reviewed November 27, 2026. This slice follows the verified release baseline
`64ec19d0b9acd855f63879941c3bed1213460f39` and advances the open SAP method
investigation. It does not activate USD/ADS earnings or peer valuation.

## Delivered behavior

Valuation & Peers and Data Sources show the exact annual native-currency EPS
observation together with the filing's depositary ratio, source links, fiscal
period, filing date and original observation date. Compact research keeps the
period visible and retains the filed decimal precision.

The existing save, Monitor and historical-return functions now retain and
display the same SAP evidence. Replay remains dated history, with no source
requests or freshness promotion. Old note-only SAP records remain readable;
they do not acquire new facts retroactively. TSM's validator and saved API
retain their existing behavior.

## Source boundary

The retained November 24 observation binds SAP SE, CIK `0001000184`, to its
FY2025 Form 20-F, filed February 26, 2026, accession
`0001104659-26-020058`. Its reviewed filing-body digest is
`95017d7d5ea133ec3eaa11522a6b4a6661d99308394081735ae9e2efbc875151`.

The exact annual statement reports diluted EPS as **6.10 EUR/share** for
January 1–December 31, 2025. This value is parsed from the inline fact, with
its entity, concept, duration and unit checked. The policy pins source locations
and digests, not an EPS output value.
[Annual statement fact](https://www.sec.gov/Archives/edgar/data/1000184/000110465926020058/sap-20251231x20f.htm#Tc_V_yoeF7cbkqD3dW4XbtEFA_42_4)

The separate NYSE disclosure uses the term ADR and states that each represents
one ordinary share. The exchange directory identifies SAP's depositary listing
as ADS. The app preserves the filing's ratio unit, `ordinary_shares/ADR`, and
does not silently convert the statement into directly reported EPS per ADS.
[Exact annual filing](https://www.sec.gov/Archives/edgar/data/1000184/000110465926020058/sap-20251231x20f.htm)

The new active SAP policy is v2. It validates both source notes and the exact
native EPS fact. The normalized snapshot exception is restricted to the SAP
subject path, expected policy and source document, matched historical inventory,
listing identity, receipt chronology and complete observations. It checks the
filed numeric token digest as well as its arithmetic proof. Editing the token
and numeric value together, then resealing a record, does not admit a new value.

**Still withheld:** a reviewed USD conversion basis, USD/ADS earnings,
qualified price-to-filing association, P/E, reference median and premium.
These observations remain financially ineligible for the existing US-GAAP/USD
peer method. No alias eligibility is inherited by SAPGF. Permissions and
canonical readiness remain unchanged.

## Verification

- Before this slice, exact-head baseline CI passed **10,586 tests**, with three
  skips and four warnings, followed by successful startup, all six Personal
  Research route renders, wording, hygiene and whitespace checks. The strict
  journey passed 109 checks including all six mandatory desktop/phone cases;
  release regressions passed 115 checks.
- New source, snapshot and actual Streamlit save/Monitor/return checks were
  observed failing before implementation. Negative cases cover currency,
  period, issuer, source, ratios, edited literals, future receipts and promotion.
- The final focused integration run passed **466 checks**, including the
  compact-period regression and existing snapshot, tools, source and public
  documentation contracts. One existing dateutil deprecation warning remains.
  The complete-suite and browser result for this slice belongs to its
  revision-specific [CI checks](https://github.com/YuzeJ21/Stock-Analysis/actions).
  No new whole-suite or browser pass is asserted by this document.
- Independent code review identified five material gaps: marker-based legacy
  bypass, unverified parent permission claims, directory provenance/chronology,
  contradictory annual metadata, and missing historical Data Sources coverage.
  Each was reproduced and fixed with regressions observed failing then passing.
  The browser test now uses the production historical Workbench, pins the exact
  ID and section despite a newer record, reloads Monitor, and checks a Python
  transport sentinel as well as browser requests. No second review is claimed.
- The final validator revalidated the actual retained v2 source context and an
  actual baseline-valid v1 note-only record. Earlier experimental v1 records
  containing numeric observations already failed the verified baseline and
  remain unverified; compatibility does not admit their unsupported fields.
- The actual retained SAP context saved and reopened unchanged in disposable
  storage, with its original dates and both native observations visible.
- A fixed twelve-company replay at the original shared cutoff
  `2026-11-24T05:17:10.091926+00:00` kept qualified comparisons at **4/12**.
  The verified baseline had **5/12** exact replays. The new SAP source revision
  correctly invalidated its old replay proof until an explicit retained recheck
  restored **5/12**. Original source bytes were unchanged and no transport ran.
  This common-cutoff check is separate from the November 19 post-close 8/12
  comparison benchmark and does not rewrite it.

The browser regression exercises desktop and phone: show native basis, save,
open Monitor, reload, return to the exact saved context, and retain the hold.
Missing Chromium fails the check. The declared-runtime CI runs this slice before
the broader regression matrix and retains the complete engineering workflow.

One minor wording item remains deferred: the singular ADR ratio still uses the
existing plural unit label. Its integer value and machine unit are unchanged.

## Remaining stages

1. Review an exact USD conversion and selected-security price association
   before proposing any separately scoped SAP valuation method. No FX source
   or accounting comparability is inferred from existing price permissions.
2. Provide an intended host and verify real OIDC, private storage, audit,
   retention/deletion/export decisions, named operations and recovery. Existing
   read-only checks found no configured hosted URL in environment or project
   configuration; local contract readiness does not complete hosted operation.
3. Observe actual independent researchers and later return use. The example
   feedback log correctly yields `awaiting_external_review` and
   `operated_pilot_ready=false`; it is only a template check, not session evidence.
4. Keep permitted point-in-time universe, consensus, reviewed economic peers
   and calibration as separate later evidence gates.
