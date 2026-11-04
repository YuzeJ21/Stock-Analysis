# NEM exact filing gap review

Implement the owner's requested source review in the existing NEM save/replay/Monitor workflow. Preserve canonical data, original receipts and source rights. The live FY2025 exact filing inspection found no matching standard direct operating-income fact; pretax income, segment measures and EBITDA cannot substitute.

## Design and acceptance

- Reuse the exact SEC filing adapter and its validated identity/source receipts. Bind an optional version-2 metadata-only operating-income check to the saved Companyfacts issuer, accession, filing date, annual duration, taxonomy and currency. Keep version-1 replay intact.
- Record exact source URL/digest, observation/publication dates, checked concept and reason. An absent, conflicting or rights-held direct field remains a gap. Never copy archive monetary values, raw text or substitute metrics into approved fields.
- Explicit online check, explicit save, offline replay and Monitor use the same receipt. Mismatched current evidence cannot inherit an older check. Failed refresh is visible. Same semantic inputs remain unchanged; source-review changes are distinct from financial value changes.
- Test synthetic direct/missing/pretax/conflict inputs, mismatches, legacy packets, invalid imports, unchanged observations, changed review provenance and fresh-session Monitor. Check real NEM on desktop and phone and compare two real saved source observations. Do not manufacture a changed filing.
- Run final guarded full suite and relevant hygiene gates, record exact commit and protected-file digests, then push the existing authorized developer branch. No merge, deployment or real source fixtures in Git.

## Execution ledger

- Source audit complete: Companyfacts has no OperatingIncomeLoss history; exact FY2025 10-K parser yields matching_direct_native_unit_fact_unavailable. Private receipts are under outputs/local/nem_operating_income_review_2026-11-02; source bodies are not committed.
- Adapter/receipt tests: observed 17 expected failures before implementation; 40 passed after. UI tests: observed 2 expected failures before implementation. Expanded regression: 145 passed, one pre-existing dateutil warning. Parser/adapter/UI set: 68 passed.
- Real browser source check and first version-2 save complete; comparison to original version-1 receipt reports gaps_changed, zero financial changes. Repeated real capture is unchanged with an open gap. Original receipts remain intact.
- Final independent review found one Important date-compatibility issue and no Critical/Minor findings. Fixed next-business-day SEC filing dates: new annual v2 roundtrip test observed RED then GREEN; pre-period acceptance stays rejected. Expanded focused regression: 187 passed.
- Ruling: custom-concept/derived operating income remains outside this standard direct-fact slice, as requested; cost is an explicit unresolved financial coverage gap, not an invented substitute.
- Ruling: the real observations do not establish a changed filing; cost is that real revision detection remains unproven beyond synthetic regression. Preserve the independent changed-source gate.
- Desktop 1280x900 and phone 390x844 exercised saved comparison and Monitor; no horizontal overflow or Streamlit exceptions. Known original saved-model price absence remains separate. Final full regression and exact-commit browser recheck complete the reviewer-deferred validation.
- Pending: exact-commit full regression; GitHub synchronization. Local release packet will carry final results without publishing real-source evidence.

## Review focus

Check version compatibility, metadata-only archive retention, time/order/source identity gates, malformed import handling, cached check reuse after source change, no readiness promotion, and whether Monitor explains the remaining gap without implying a financial revision.
