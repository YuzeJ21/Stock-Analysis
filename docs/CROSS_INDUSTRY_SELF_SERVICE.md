# Cross-industry self-service capability study

The local app offers an optional **Discover → Coverage studies → Self-service** study. It uses the same online financial, filing, price, peer and research-tool contracts as Company Workbench. It requires no manually prepared company CSVs. The app must be running locally with network access and identifying SEC request information; public Pages remains a static demonstration.

## Fixed sample and controls

| Declared study group | Companies |
| --- | --- |
| Semiconductors | AMD, NVDA, QCOM |
| Banks | JPM, BAC, C |
| Utilities | DUK, SO, NEE |
| Foreign issuers | TSM, SAP, IBN |

Every global fraction uses the same twelve requested companies, and every group fraction uses its three declared members. Failed, excluded and unattempted companies remain in those denominators. These are selected research cases, not a representative market, industry or domicile census. Source-observed issuer identity, SIC, security type and currency remain separate evidence.

1. **Inspect next company** requests sources for the next unattempted company.
2. **Recheck company** explicitly replaces one attempted company's observation. It does not preserve a prior success after a failed refresh.
3. **Restart study** clears this session's progress without requesting sources.
4. Select **Company evidence** and expand **Reporting periods and original source receipts** to inspect periods, dates, sources, peer exclusions and replay reasons. Navigation and ordinary rerenders make no new source requests.

SEC access limits pause further collection while retaining the unattempted remainder. A later recheck is explicit. Retained evidence is revalidated with its original source dates; a stale observation becomes held rather than automatically refreshed.

## Ten independent capabilities

| Capability | What an available state establishes |
| --- | --- |
| SEC issuer match | The financial source matches the selected ticker and SEC CIK. |
| Usable filing catalog | Current submissions metadata passes the bounded catalog and source checks. |
| Current annual facts | Supported annual facts match the current filing context. |
| Current direct-quarter facts | A directly reported quarter matches its current filing and duration. |
| Current interim facts | A separately qualified interim duration matches its source; it is not a manufactured quarter. |
| Dated close | A validated completed closing-price observation, with its date. |
| Same-basis industry comparison | The independent annual diluted P/E and reference-comparison gates pass. |
| Compatible Business Trend metrics | At least one compatible observed metric is calculable; its reason distinguishes current from historical context. |
| Hypothetical scenario eligibility | The existing calculation kernel accepts a corroborated annual revenue base and fixed explicit hypotheses. |
| Exact private research replay | A disposable private-store save/reopen retains the complete normalized context and compares unchanged. |

Each capability retains **available**, **partial**, **held**, **excluded**, **failed** or **unattempted** with a reason. These states do not become one company score or investment conclusion. A usable catalog does not prove complete current financials. A dated close does not establish share-class identity, annual earnings eligibility or a peer comparison.

The scenario probe uses 8% revenue growth, a 15% hypothetical FCFF margin, 10% WACC, 2% terminal growth and five years. These fixed capability-test inputs are not issuer guidance, consensus or a user's saved assumptions. Missing capital structure does not manufacture net debt, shares or a traded-share value. Banks remain excluded from this operating-company FCFF method.

## Dated rerun

All twelve companies were inspected again on November 16, 2026 Toronto time. The retained source observations span November 17, 00:11:30–00:18:11 UTC, with 203 raw source callbacks and 345 adapter operations. Provider SDK calls have separate accounting. The comparison uses the November 8 retained online run and the same original sample, capability rules and denominators. The dates capture both source availability and product changes.

| Capability | November 8 | November 16 |
| --- | ---: | ---: |
| SEC issuer match | 11/12 | 11/12 |
| Usable filing catalog | 12/12 | 12/12 |
| Current annual facts | 9/12 | 10/12 |
| Current direct-quarter facts | 5/12 | 10/12 |
| Current interim facts | 0/12 | 1/12 |
| Dated close | 12/12 | 12/12 |
| Same-basis industry comparison | 1/12 | 4/12 |
| Compatible Business Trend metrics | 11/12 | 11/12 |
| Hypothetical scenario eligibility | 5/12 | 5/12 |
| Exact private research replay | 10/12 | 10/12 |

- **Financial statements.** C, DUK, SO and NEE added current direct quarters through exact 10-Qs. TSM added current annual, direct-quarter and interim evidence through its exact native-currency filings. These counts require supported current facts. Individual statement fields can remain held.
- **Valuation.** November 16 completed closes qualified for all twelve. NVDA, JPM, BAC and C qualified for same-basis peer P/E. AMD's current annual amendment remains unresolved. QCOM did not reach three qualifying references. DUK, SO and NEE remain held on the share-class join in this run. TSM requires a separate ADS method, SAP's listing-to-issuer join remains unverified, and IBN's provider context was unavailable.
- **Exact replay.** TSM's fresh context reached the snapshot validator and failed on the typed native IFRS diluted-EPS proof retained under the selected-security evidence path. The proof is contextual and uses TWD per share. A disposable replay reproduced the validation error. The earlier 11/12 same-source replay pass used a different retained context and remains a separate result.
- **IBN bank evidence.** Workbench corroborated exact bank annual, direct-quarter and cumulative interim statements. A separate disposable Workbench snapshot reopened the same bank evidence and compared unchanged. The original study requires revenue in the general period table for its comparable financial counts and replay entry point. IBN's bank-only records remain outside those counts. Its Companyfacts request returned HTTP 404, and provider valuation context was unavailable.

Discover's **Dated study results** shows the per-company changes and unresolved reasons. The live study controls below it start a separate session. The published comparison contains reduced capability states. Filing bodies, provider prices and private snapshots stay in the research environment.

### Same-source TSM replay recheck

The repaired snapshot store reopened TSM's exact retained November 16 research context and compared it as **Unchanged**, preserving all four fiscal 2025 IFRS diluted EPS observations and the notes in the selected-security evidence. On those same twelve-company inputs, exact replay rose from **10/12 to 11/12**. The original dated run remains recorded above. IBN's bank-only evidence retains its separate Workbench result. TSM's ADS valuation remains withheld, and the cohort's peer comparison count stays **4/12**. [TSM replay verification](TSM_SNAPSHOT_REPLAY_RELEASE.md#same-source-recheck-of-the-november-16-study)

### Bank-specific evidence in Discover

Select IBN under **Company evidence** after inspection. **Bank filing evidence** shows the verified consolidated annual, direct-quarter and fiscal year-to-date periods, with their INR reporting basis and filing and observation dates. The July 20 Form 20-F covers the fiscal year ended March 31, 2026. The October 22 Form 6-K covers the July–September direct quarter and April–September fiscal year to date. The cash-flow statement covers six months, so Discover labels quarterly operating cash flow **Withheld**. [Exact annual filing](https://www.sec.gov/Archives/edgar/data/1103838/000095010326010820/dp249803_20f.htm) · [Exact interim filing](https://www.sec.gov/Archives/edgar/data/1103838/000095010326015987/dp255170_6k.htm)

**Inspect next company** and **Recheck company** verify replay in a disposable store and bind the result to the full research context. **Unchanged** means the saved context reopened exactly with the same inputs. Passive navigation revalidates the recorded result. Older sessions may need an explicit recheck to record the bank replay proof. The twelve-company table continues to measure the original revenue-based capabilities. [ICICI Bank evidence scope](IBN_NON_XBRL_RESEARCH.md)

The November 19 verification reparsed retained SEC filing bytes and matched the annual, direct-quarter and six-month fields in the November 16 Toronto study observation. A disposable replay reopened the exact normalized IBN context as **Unchanged**. Revalidating the original study at its capture time preserved all aggregate and group counts, including **12/12** attempted, **10/12** annual, **10/12** direct quarter, **1/12** interim, **4/12** peer comparison and **10/12** generic replay. The separately dated TSM recheck records its own **11/12** replay result.

Desktop (1440 × 1000) and phone (390 × 844) automation checks the Inspect and Recheck actions, original filing links, the quarterly cash-flow hold, unchanged replay, and unchanged study counts. Moving between companies or reopening the study uses the recorded proof without new source requests.

## November 8 controlled repair

Reprocessing the same twelve captured source observations before and after the shared catalog repair improved usable filing catalogs from **5/12 to 12/12**. This is a controlled comparison using the same source inputs, not a fresh market-coverage pass.

| Same-source capability | Available / requested |
| --- | --- |
| Current annual facts | 9/12 |
| Current direct-quarter facts | 5/12 |
| Current interim facts | 0/12 |
| Dated close | 12/12 |
| Compatible current or historical Business Trend metrics | 11/12 |
| Hypothetical scenarios | 5/12 |
| Exact disposable private replay | 10/12 |

All three banks remained excluded from operating-company FCFF scenarios. TSM's normalized context was **758,318 bytes**, above the unchanged **524,288-byte** replay bound, so exact replay stayed held. IBN's Companyfacts source was unavailable; missing financial evidence and replay did not become zero or success. Source-specific gaps remain visible for the other incomplete lanes.

The original fresh peer-source collection has its own observation dates and exclusions. See the [initial release evidence](CROSS_INDUSTRY_SELF_SERVICE_RELEASE.md) for that source pass and [bank retention evidence](BANK_PEER_EVIDENCE_RELEASE.md) for the later bounded repair. Each measurement retains its original dates and sample.

## Shared source repair

The filing catalog accepts bounded large submissions catalogs and filters relevant annual, quarterly and current-report forms before constructing the reduced inventory. This addresses large bank catalogs without treating unrelated filing rows as financial statements. Source identity, byte bounds, dates, report limits and exact paths remain checked.

8-K/6-K event report dates stay separate from financial period ends. Valid legacy document metadata can be retained; absent documents remain explicit gaps without invented URLs. Missing current-document metadata cannot silently select an older report. Native-currency 6-K quarter/interim evidence requires validated structured durations and an exact filing accession/date match. A newer known reporting period can still hold an otherwise usable historical duration.

## Lossless bank peer sources

JPM, BAC and C collections can exceed the retained limit because they contain exact SEC documents. Large eligible packets now use bounded lossless storage, then restore every original value and original packet digest before the existing source/valuation checks. The retained-company and study limits stay unchanged. The selected-company source details show a separate retained-evidence proof; this is not valuation approval. Wrong-company or damaged restoration stays a precise peer gap, with independent financials and prices preserved. Both classification-pruning paths retain older packet references.

The [bank release evidence](BANK_PEER_EVIDENCE_RELEASE.md) records exact source-byte comparisons, eligible/excluded references, resource bounds and the prior normalized research-snapshot gap. That gap is now addressed by the [versioned bank snapshot format](BANK_RESEARCH_SNAPSHOT_RELEASE.md), with complete cover observations retained. Ordinary navigation remains source-free.

## Privacy, rights and next work

The study retains source packets in session memory and displays reduced capability states and provenance. Its replay probe uses disposable private storage, reads no user notes and writes no user evidence stores; the temporary store is removed after the check. The normal **Save research snapshot** workflow remains a separate explicit user action. Raw responses, real captures and screenshots remain private; this documentation does not publish them.

Personal inspection permissions are unchanged. Metadata, archive inspection and price observations do not inherit broader Companyfacts field rights. The study changes no canonical rows, saved-model readiness, source-rights decision or commercial eligibility. Annual P/E still requires the existing identity/share checks, same-day completed closes, compatible annual diluted EPS, the 35-day fiscal window and at least three qualifying references. No FX/ADS conversion, missing quarter, tax allocation, normalized earnings or reviewed economic-peer relationship is inferred.

The November 11 follow-up used the same captured observations and verified exact replay for 11/12, including the previously size-held TSM. The dated counts above remain the original study results. Later issuer-specific verification established TSM's native annual and quarterly workflows and IBN's exact non-XBRL annual workflow. [TSM replay evidence](TSM_SNAPSHOT_REPLAY_RELEASE.md) · [Native annual evidence](NATIVE_ANNUAL_OVERVIEW_RELEASE.md) · [Native quarterly evidence](NATIVE_QUARTER_RELEASE.md) · [IBN annual evidence](IBN_NON_XBRL_RESEARCH.md) · [Current roadmap](../ROADMAP.md)

[Self-service workflow](SELF_SERVICE_COMPANY_RESEARCH.md) · [Online source methods](ONLINE_COMPANY_RESEARCH.md) · [Coverage methods](ONLINE_RESEARCH_COVERAGE.md) · [Roadmap](../ROADMAP.md)
