# MRVL peer valuation and earnings quality

## Intent and authorization

The user authorized the next stage, online MRVL evidence, visible gaps, automated desktop/phone checks and GitHub synchronization without human testing. Reuse the clean five-section Workbench. This is an explanation feature, not an investment recommendation or a new valuation method.

## Approach

Keep the reported annual P/E engine unchanged. Add an independent annual SEC evidence review to the existing explicit financial refresh, using its already fetched Companyfacts response. Render it in Valuation & Peers and Data Sources even when price or peer prerequisites fail. A peer-refresh-only attachment would hide earnings evidence behind unrelated price/listing failures; a new adjusted or TTM multiple would lack a qualified method. The selected approach is the implementer's choice within the authorized scope.

## Evidence and boundaries

First scope is MRVL CIK 0001835632, FY2026 10-K accession 0001835632-26-000011, period February 2, 2025–January 31, 2026, filed March 11, 2026. Exact primary: `mrvl-20260131.htm` at https://www.sec.gov/Archives/edgar/data/1835632/000183563226000011/mrvl-20260131.htm. Current SEC submissions must still select that exact annual. A newer annual/amendment or conflicting identity retains a gap rather than silently restoring the older source.

Use seven exact US-GAAP concepts: EarningsPerShareDiluted (USD/shares), NetIncomeLoss, NetCashProvidedByUsedInOperatingActivities, PaymentsToAcquirePropertyPlantAndEquipment, ShareBasedCompensation, AmortizationOfIntangibleAssets and GainLossOnSaleOfBusiness (USD). Match every fact to one selected accession, form, publication date and exact annual interval. Missing/conflicting/nonfinite/wrong-unit observations remain per-field gaps; never treat absence as zero. Preserve reported losses. Do not substitute continuing-operation cash flow, quarterly/YTD facts or another filing.

The named comparison is AVGO CIK 0001730168, FY2025 10-K accession 0001730168-25-000121, period November 4, 2024–November 2, 2025, filed December 18, 2025. Exact primary: `avgo-20251102.htm` at https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm. Fetch both exact annual documents and current submissions online on the financial action. Bind document identity/type/end to metadata and verify concise business evidence: MRVL names Broadcom in direct competition; Broadcom has semiconductor and infrastructure-software segments. Paraphrase the relevance and business-mix limitation with source links. This is economic research context, not an approved core peer or valuation anchor.

Calculate actual annual end-date distance from verified metadata (90 days for these scopes). Explain why it fails the existing 35-day window without changing admission or pretending that other security/price checks passed. Existing same-day completed close, annual diluted EPS, fiscal start/end, common-share identity, source freshness and minimum-three-reference rules remain unchanged.

Explain that a business-disposal gain affects reported earnings, CFO differs from net income, and SBC/amortization require care. Do not subtract a pretax gain from after-tax earnings, add components to manufacture adjusted EPS, infer FCF, or calculate another multiple. Adjusted/recurring earnings remain explicitly unresolved without an independently qualified after-tax reconciliation. Latest-quarter analysis remains separate from this annual denominator.

## Architecture and contracts

- `src/mrvl_earnings_review.py`: pure validation, explicit concept allowlist and source normalization, packet sealing, per-field evidence and named relationship assessment. APIs: `normalize_review_facts(receipt)`, `normalize_review_profile(receipt)`, `seal_review_packet(packet)`, `build_mrvl_earnings_review(packet, *, expected_cik=None, as_of=None)`, `validated_mrvl_review(financial_view, *, expected_cik=None, as_of=None)`.
- Packet: schema_version `mrvl-earnings-review-v1`, ticker, sec_cik, observed_at; normalized `facts` receipt; `profiles` and `documents` mappings keyed MRVL/AVGO; packet_digest. Each receipt has exact URL, UTC observation, raw payload_sha256; normalized JSON receipts also have their own normalized_sha256. Documents use verified bounded payload_raw_base64, never a claimed invented raw digest. Profile/facts raw HTTP digests remain distinct from normalized subset digests.
- `src/mrvl_earnings_sources.py`: research-only bounded collector `fetch_mrvl_earnings_review(facts_receipt, *, ticker, expected_cik, user_agent, source_fetcher=None, observed_at=None)`. Reuse existing SEC JSON and exact-source HTML transport. At most two submissions and two annual documents; no retries, disk writes, extra Companyfacts request or non-SEC URLs. Independent failures do not disable financial history. Unavailable receipts keep stable safe reasons.
- `src/sec_annual_history.py`: after verified MRVL Companyfacts identity, attach the packet under `mrvl_earnings_review`; no changes to approved_direct_fields, histories, saved SEC schemas, registry or canonical data.
- `src/mrvl_earnings_review_ui.py`: `mrvl_earnings_review_html(financial_view, *, expected_cik=None, as_of=None, sources_only=False)`; no transport/state writes. Lead with a short quality implication and named-peer status, with expandable field values, actual dates/units/concepts, source receipts and rights/gaps. Empty for non-MRVL. Unsupported MRVL scope stays visible.
- `src/company_workbench_ui.py`: render the same review in Valuation & Peers and Data Sources. Reuse the loaded financial view across section/Monitor changes. Keep the Overview first screen and all existing tools intact.

## Rights and source control

Personal Research inspection only. New net-income/SBC/amortization/disposal fields and business documents do not inherit commercial approval. No additions to source_rights.yml, canonical fields, immutable saved SEC receipts, export fields, peer roles or readiness. Raw/real normalized observations and live screenshots stay private and outside Git. Tests use constructed values/documents. Official live observations support local verification, not distribution clearance.

## Acceptance

Automated evidence covers exact and mismatched identities, dates, accessions, units, field conflicts, negative observations, stale/future/altered receipts, unreviewed source versions, independent document failures, mode guards, URL/size bounds, no additional fetch on ordinary reads or section changes, and unchanged numeric valuation/membership. Desktop and phone checks exercise the real Workbench and expandable explanations. Run appropriate regression/hygiene checks, preserve canonical bytes, update active documentation and a release packet, commit and synchronize only verified changes.
