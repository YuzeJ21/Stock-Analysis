# Bank research snapshots: save, replay and Monitor

Date: November 8, 2026. Baseline: `6465f9596687705598b0b7257d6e0cf5b76a00c0`. The existing isolated checkout was reused. This stage addresses the normalized snapshot gap recorded by the prior bank peer-retention release.

## Delivered behavior

JPM, BAC and C research contexts now retain their complete parsed cover evidence in a versioned normalized format. The literal symbol, title, exchange and context ID keep their original values and ordering. Selected-common fact links, original document/reference hashes, publication/observation dates, EPS proofs, companion links and duplicate-source references remain intact. No raw filing bodies are admitted to normalized snapshots.

The cover producer names parsed observations `cover_observations` with literal `trading_symbol` and an explicit `sec-cover-observations-v1` document marker. The previous names incorrectly identified these parsed fields as raw data. This is a representation correction, not a new financial observation or an issuer-symbol alias mapping. A reversible comparison accounts for every original value and every unrelated context field; only the semantic/source metadata revision hashes change with the new format.

The private snapshot store validates bounded row types, known source-document paths, owner identity, selected-common association, document/companion/source references and recorded EPS relationships. Unrecognized versions, misplaced fields, malformed values, markup, arbitrary raw/archive data and owner substitutions remain rejected. The original raw/archive rule, EPS numeric-proof guard, **512 KiB** snapshot cap and complexity limits remain in force. Historical replay uses recorded relationships rather than today's policies or source freshness.

The selected-security disclosure shows all four literal cover values and retains read-only display support for the prior live format. This does not let old unqualified raw-field contexts bypass storage validation. Previously blocked captures must be rebuilt through the validated research path; existing successful snapshot formats are unchanged.

## Exact captured-source verification

The three original full source packets were replayed privately at a compatible recorded observation cutoff. No source timestamps, source-body bytes, price inputs, financial periods or permissions were rewritten. Each context was saved twice in a disposable store, reopened exactly, and compared as **unchanged**. The second save returned the original content identity and immutable file bytes.

| Company | Normalized context bytes | Saved snapshot bytes | Same-input saves | Replay |
| --- | ---: | ---: | --- | --- |
| JPM | 207,437 | 208,069 | One immutable identity | Exact / unchanged |
| BAC | 195,694 | 196,326 | One immutable identity | Exact / unchanged |
| C | 190,359 | 190,989 | One immutable identity | Exact / unchanged |

Each case retains three eligible same-basis P/E references and the original exclusions, using the recorded November 6, 2026 completed closes. C's latest direct-quarter structured facts remain pending. All three retain the bank operating-company FCFF exclusion. Missing hypotheses, unsupported forecast/consensus claims and unrelated research gaps do not become qualified because a snapshot saves.

Cover rows are repeated in subject, accepted-reference and independent source contexts. The verification accounts for all 111/129/108 row occurrences in JPM/BAC/C respectively; those are not unique securities or additional source documents. Original source packets remain unchanged. The snapshots retain normalized evidence and source links/digests, while full filing bodies remain in the separate private source packets.

## Use the application

Open the company online, inspect its financial/peer evidence, then use **Research Notes → Saved online research → Save research snapshot**. Repeating the same save preserves the immutable identity and shows **Current versus latest saved: unchanged**. Open historical research or use **Open Monitor → Saved online research updates → Reopen exact saved research** to return to that company and snapshot.

Replay is explicitly historical. It performs no source requests, does not substitute today's filing or price, and does not promote saved readiness or commercial eligibility. Refresh company research explicitly for new observations. Old snapshots stay immutable; a subsequent source observation is a separate input.

## Verification and remaining work

- Affected source/security/codec/price/valuation/store/coverage/UI/navigation/workspace/documentation regression: **1,046 passed in 39.08 seconds**. The existing third-party dateutil deprecation warning remains. Earlier focused counts overlap and are not added to this total.
- Exact-tree desktop/phone journeys: **2 passed in 101.86 seconds**, at 1440×1000 light and 390×844 dark preference, covering all three banks. Production source/cover/EPS/price/peer/context/store/Monitor functions run over constructed exact-body-bound fixtures. Repeated saves retain original bytes and identity; comparison is unchanged; historical and Monitor returns retain the original company/snapshot; no replay source calls occur. Original cover tuples, companion references and a deliberately excluded EPS conflict survive. Bank FCFF stays excluded. English, no overflow/exceptions, untouched demo data and readable actions/evidence were checked; minimum measured contrast was **9.94:1**. These are responsive engineering checks, not independent human validation or real filing approval.
- Actual captured-source replay independently verified all three rows in the table, under the unchanged 512 KiB bound. A reversible representation comparison restored every old cover field and matched all other context content except the two format revision hashes. Complete original source packets remained unchanged.
- All six research route renders passed. Public wording passed across **70 files**. Independent review identified three compatibility gaps involving excluded-peer evidence, independent filing/acceptance dates and companion fragment links; all were repaired with failing-then-passing regressions. Final bounded re-review is clean.
- All **89 protected files** match the baseline byte for byte, including canonical/demo data, source-rights configuration and public screenshots. Compact ordered path/content-digest manifest SHA-256: `6dea65bec009270b132211724f426c1fdb557979a8903a5f5cc93b92d9edb373`.

The tested commit and exact GitHub synchronization are recorded below after completion. No full repository-suite or resulting-main hosted CI pass is claimed. Constructed browser evidence and captured-source replay are separate from independent human validation, market-wide coverage, redistribution rights and hosted-service operation.

Next inspect the filed quarterly evidence behind C/DUK/SO/NEE gaps, then remaining identity/foreign-issuer exclusions and meaningful subsequent-filing changes. TSM's separate normalized-context size hold, IBN's financial support gap, source permissions and unsupported valuation methods remain separate. No purchases, credentials, canonical rows or source-rights decisions were changed.

[Self-service method](SELF_SERVICE_COMPANY_RESEARCH.md) · [Bank peer retention](BANK_PEER_EVIDENCE_RELEASE.md) · [Roadmap](../ROADMAP.md)

## Tested commit and GitHub state

Verified implementation: [`5cf08bfe191e1ff2f01763b62595e06865d4b960`](https://github.com/YuzeJ21/Stock-Analysis/commit/5cf08bfe191e1ff2f01763b62595e06865d4b960). GitHub main accepted the fast-forward from the stated baseline. The Git remote and independent GitHub branch read matched that full commit; remote README and release-document blob IDs matched their local files. This documentation-only follow-up records those checks without changing tested runtime code or protected assets.

Staged hygiene and whitespace passed with zero canonical/generated data staged. The implementation checkout was clean after commit. The owned local app restarted on port 8536 and returned health `ok`; other checkouts were preserved. The repository workflow runs on pull requests, so no resulting-main hosted CI pass is asserted for this authorized direct synchronization.

The ignored local review packet is `outputs/local/releases/bank-research-snapshots-20261108/`: reduced before/after results, unchanged-data manifest, regression/review logs and constructed browser screenshots. Actual financial snapshots and full original source packets remain private temporary captures, outside public distribution. No user notes or user evidence stores were written during verification.
