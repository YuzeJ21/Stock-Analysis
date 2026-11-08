# Bank peer evidence retention

Date: November 8, 2026. Baseline: `1f7e149df3587f18a0a8c6d1ea2caf6fe0a507d5`. The existing isolated checkout was reused; unrelated checkouts, canonical data and source permissions were preserved.

## What changed

JPM, BAC and C no longer lose their complete peer-source collection at the retained-packet limit. When a collection is too large, a versioned lossless storage envelope retains every original source value, exact document body, source URL, date, permission and digest. The full original packet is restored and its original digest checked before the existing valuation rules run. Small and previously saved plain packets remain readable.

The retained-company limit remains **8 MiB** and the retained-study limit remains **64 MiB**. Decoding has a separate **128 MiB** transient bound. Corrupt, truncated, concatenated, oversized, noncanonical, duplicate-key and nonfinite inputs are rejected. A failed or wrong-company restoration creates a specific peer hold while preserving independently qualified financials and prices. Classification references survive both normal pruning and resource-failure recovery.

Discover's existing **Coverage studies → Self-service** panel shows **Full peer source evidence retained · exact restoration verified** for a successfully restored collection. Expand **Reporting periods and original source receipts** for readable byte counts and the original packet digest. Retention does not establish valuation eligibility; unsupported inputs and source exclusions remain visible. Navigation does not fetch new sources or write snapshots.

An older observation that already discarded an oversized collection needs an explicit **Recheck company** to collect it again. Ordinary navigation never silently fetches replacement evidence.

## Real-source controlled verification

All three complete source collections were captured online and replayed privately through the new storage path. Each comparison preserved all twelve embedded raw-document receipts, including original decoded bytes and SHA-256 hashes. The restored full objects and the pre-/post-storage valuation results were identical. Receipts shared between comparisons are not counted as unique sources.

| Company | Original referenced packet bytes | Retained peer bytes | Whole retained company bytes | Eligible references |
| --- | ---: | ---: | ---: | ---: |
| JPM | 74,100,090 | 7,032,521 | 7,129,549 | 3 |
| BAC | 74,100,090 | 7,034,717 | 7,122,061 | 3 |
| C | 74,100,086 | 7,034,735 | 7,132,285 | 3 |

The former stored result was a capacity hold for all three. With the same complete inputs retained, all three support the existing reported annual diluted P/E industry comparison. JPM's references are BAC/WFC/C; BAC's are JPM/WFC/C; C's are JPM/BAC/WFC. Their completed closes share November 6, 2026. This is a bounded source-observed comparison, not an independent endorsement of economic-peer fit or a full valuation conclusion.

Captured peer observations are dated November 8, 2026, 20:40:30 UTC (JPM), 20:46:08 UTC (BAC) and 20:46:50 UTC (C). A subsequent production-default JPM online recheck at 20:54:24 UTC also retained the complete collection and qualified three references. Revalidating the existing twelve-company study with these bank replacements supports four comparisons, including its previously captured NVDA case; this is not a fresh acquisition of all twelve companies.

The rules are unchanged: exact issuer/common-share evidence, current compatible annual diluted EPS, completed same-day prices, split checks, the **35-day fiscal window**, and **at least three qualifying references**. No source rows or archive bodies were removed to make a reference qualify. Bank operating-company FCFF scenarios remain excluded. The comparison and source/security validators were not edited.

## Gaps retained

RY, TD and BNY remain excluded for unresolved share-class identity; NTB for the operating-issuer requirement; FRBT for missing annual filing evidence; BCSO for an unverified listing/share basis. C's current-quarter structured-facts gap remains separate from its qualified annual denominator. The other companies and legacy studies retain their own dated evidence and denominators.

Normalized research-snapshot save/replay remains a separate capability from complete peer-source retention. The newly available bank reference proofs expose an existing normalized-store acceptance gap: `raw_cover_observations` and nested `raw_symbol` are rejected by its raw-field rule. All three normalized contexts are below the separate 512 KiB snapshot bound; no snapshot files were written during that rejected rehearsal. This release does not discard the proofs, broaden snapshot acceptance or claim that bank snapshots now save successfully. TSM's separate research-context size hold and IBN's financial coverage gap are unchanged. Uncompressible evidence or evidence above a storage/decoded bound still produces an explicit capacity gap.

Personal inspection rights remain unchanged. Full SEC documents, provider observations and captured source packets stay private and are not part of the public repository or demo. No commercial or redistribution permission is granted by compression, tests or a successful comparison.

## Verification and synchronization

- Affected codec/source/security/identity/price/valuation/context/coverage/UI/documentation/navigation regression: **855 passed in 33.73 seconds**. The existing third-party dateutil deprecation warning remains. Earlier focused counts overlap and are not added to this total.
- Constructed desktop/phone journeys: **2 passed in 96.49 seconds**, at 1440×1000 light and 390×844 dark preference. Both use actual production source/retention/valuation functions, confirm every constructed raw document is restored, preserve unsupported EPS and bank FCFF holds, recheck JPM, and verify source-free reads, classification reuse, English, no overflow/exceptions, unchanged data/stores and readable proof metadata. Phone text contrast is checked at 4.5:1 or better. These are engineering checks, not independently approved real filing sources or human validation.
- All six research route renders passed. Public wording passed across **69 files**. Independent review found and fixed a company-scope certification mismatch; the new regression first failed, then passed. Final bounded re-review is clean in its stated scope.
- **89 protected files** match the baseline byte for byte, including canonical/demo data, rights configuration and public screenshots. Compact ordered path/content-digest manifest SHA-256: `6dea65bec009270b132211724f426c1fdb557979a8903a5f5cc93b92d9edb373`.
- Exact original/decoded object, original inner digest, all embedded raw-body bytes/digests and pre-/post-storage peer conclusions matched for all three real bank packets. None of the valuation, selected-security or source permission rules was changed.

The tested commit and exact GitHub synchronization are recorded below after completion. No full repository-suite, resulting-main hosted CI, independent human, market-wide coverage or hosted-service reliability claim follows from these checks.

Next inspect the exact normalized-store proof gap separately, then the filed quarterly evidence for C, DUK, SO and NEE and the remaining share-class/foreign-issuer exclusions. Preserve the complete source packet and existing financial rules in every step.

[Study method](CROSS_INDUSTRY_SELF_SERVICE.md) · [Prior stage evidence](CROSS_INDUSTRY_SELF_SERVICE_RELEASE.md) · [Roadmap](../ROADMAP.md)
