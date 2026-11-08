# MRVL issuer after-tax reconciliation

The authorized next stage extends the existing online MRVL annual review. Reuse the current Workbench and explicit financial refresh; keep its clean first screen, reported annual P/E and existing research tools. No further design or testing handoff is needed.

## Source and supported claim

- Reuse the current MRVL submissions receipt. Bind exact 8-K `0001835632-26-000006`, filed/reported `2026-03-05`, primary `mrvl-20260305.htm`, and its furnished Exhibit 99.1 `q426_8kx1312026ex-991.htm`, in that accession's SEC archive directory.
- The 8-K must verify MRVL/CIK `0001835632`, its report date/form, visible Item 2.02 furnished status and exact exhibit linkage. The exhibit must independently establish the issuer, reconciliation title, millions/per-share scale, and **Year Ended January 31, 2026** column. Three quarterly columns precede the annual column and share its ending date; position/date alone is insufficient.
- Verify the six signed special-item rows, pretax subtotal and aggregate tax adjustment against issuer non-GAAP net income, using decimal arithmetic and only disclosed rounding precision. Bind starting GAAP net income/EPS to the independently verified FY2026 annual observations (`2025-02-02` through `2026-01-31`). Check disclosed GAAP and non-GAAP diluted shares/EPS separately; report source EPS rather than manufacturing an EPS bridge.
- This supports an **issuer-reported annual non-GAAP after-tax reconciliation for inspection**. It does not establish recurring earnings, gain-only after-tax EPS, a replacement P/E denominator or peer-method comparability. The tax-rate reconciliation in the 10-K is not a sale-specific tax allocation.

## Approach and boundaries

Add a separate optional `after_tax_reconciliation` sibling to the existing sealed in-memory packet, not another Companyfacts concept or an annual-document key. A new pure source-specific module validates the two raw documents and table structure. Existing bounded transport supplies at most two additional HTML responses after source metadata qualifies; reuse both existing profiles and Companyfacts. No retry, render-time transport, new dependency or source disk cache.

Reject hidden/ambiguous rows, wrong spans/units/periods, duplicates, conflicting source metadata, bad digests, stale/future receipts and changed annual scope. A reconciliation failure retains independently verified annual fields and AVGO context. Old packets without this extension remain usable with an explicit reconciliation gap. Bound the new raw payloads before the parent packet digest is calculated.

Keep `profiles` and `documents` keyed exactly by MRVL/AVGO. Keep the seven annual fields, source-rights registry, approved fields, saved SEC schemas, canonical data, readiness and peer roles unchanged. Keep same-day completed closes, 35-day fiscal windows, annual GAAP EPS and minimum three references unchanged. Committed fixtures are constructed; live receipts, real values and screenshots stay outside Git.

## Presentation

Add one expandable issuer reconciliation in the existing Valuation & Peers and Data Sources review. Show the reported GAAP and issuer non-GAAP basis distinctly, signed adjustments and aggregate tax effect, net-income and rounding checks, reporting period, furnished status, source locations, dates, hashes and personal-research permissions. Replace the broad unresolved-bridge message only after this evidence qualifies; retain the specific unallocated-tax and unqualified-normalized-earnings gaps. The first screen and P/E caveat remain concise.

## Verification and delivery

Use red/green parser, receipt, request-bound, existing peer invariance, presentation and Workbench tests, then real online SEC verification and desktop/phone checks. Reuse the existing disposable browser fixture and test source/Monitor return without new requests. Run the affected regression suite, six-route render/health, wording/hygiene and unchanged-data checks; broaden only for an actual cross-cutting change or unresolved failure. The preceding baseline already passed its 9,330-test repository run. Finish with independent review, local commits, source/release documentation and authorized GitHub main sync, verifying its exact remote head.
