# Read-Only Issuer-to-Security Bridge Design

## Intent

Measure what a dated listing-symbol receipt and an SEC ticker/CIK search association can jointly suggest, while making ambiguity and source-cut mismatch explicit. This is a local research inspection for the next U.S. universe stage. It cannot create issuer or security IDs, determine U.S. domicile, establish current active listings, or promote analysis readiness.

## Approaches

The chosen approach is a standalone read-only bridge using the already verified Nasdaq directory pair and a receipt-bound SEC association capture. It reports cross-source leads only when the two HTTP Last-Modified **calendar dates in UTC** match. The directory footer date, whose timezone is unspecified, remains separately recorded. Matching dates permit an inspection comparison, not a point-in-time membership claim. A direct import into the existing point-in-time universe contracts would invent missing issuer/security/lifecycle fields; using a bare ticker-map file would lose its source receipt.

## Inputs and output

- The directory loader reuses the existing exact two-file receipt validation and returns internal non-test rows with ACT, CQS, and Nasdaq symbol fields preserved separately. Its public receipt-audit JSON stays aggregate-only.
- The SEC loader accepts only an ignored local capture directory with `manifest.json` and `company_tickers_exchange.json`. It checks the exact official URL, file name, SHA-256, strict map schema, source Last-Modified and observation times, regular files, and bounded sizes. Extra capture entries are irrelevant; the selected map is verified from the same bytes parsed.
- The bridge compares one verified pair. On different HTTP Last-Modified UTC calendar dates it reports `cutoff_mismatch`, input counts and digests, and no cross-source gap or row queue. A valid same-date pair reports exact ACT leads, secondary-symbol leads, punctuation notation leads, ambiguous directory rows, SEC ticker/CIK conflicts, venue-review leads, and absent counterparts as distinct counts. A bounded queue describes reasons and candidate references; it never silently resolves ambiguity or equates a CIK with one security.
- Every result is `inspection_only`, `rights_status=unreviewed`, `safe_to_import=false`, with domicile, security type, active lifecycle, point-in-time membership, financial coverage, and analysis eligibility withheld. The CLI writes nothing; an ignored local packet can capture its JSON.

## Acceptance and boundaries

- Synthetic tests prove matching same-date inputs, mismatched cut dates, changed digest or schema, test-issue exclusion, duplicate/competing ACT/CQS/Nasdaq symbol observations, repeated SEC ticker across CIKs, multi-ticker CIKs, punctuation leads, unknown venues, and deterministic bounded output.
- The real saved pair must report the October 23 versus October 27 cutoff mismatch without exporting raw rows or presenting a same-cut company gap count. Existing cross-cut counts remain historical inspection leads only.
- No network request, source-data fixture, canonical data, readiness, rights-registry, dashboard state, or generated public asset is changed. Tests are automated; no human testing is required for this engineering stage. Distribution and any real import remain held for exact source/field/use rights and independently reviewed issuer-security evidence.
