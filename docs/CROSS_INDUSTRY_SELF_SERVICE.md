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

## November 19 midday study rerun

All twelve companies were attempted again on November 19, 2026. The observations span 13:38–13:41 Toronto time, before the regular close. The study used the same companies, four groups, and capability denominators. It recorded 58 raw source callbacks and 106 adapter operations, with no SEC access pause. Provider SDK requests have separate accounting.

| Capability | November 16 | November 19 |
| --- | ---: | ---: |
| SEC issuer match | 11/12 | 11/12 |
| Usable filing catalog | 12/12 | 12/12 |
| Current annual facts | 10/12 | 10/12 |
| Current direct-quarter facts | 10/12 | 10/12 |
| Current interim facts | 1/12 | 1/12 |
| Dated close | 12/12 | 12/12 |
| Same-basis industry comparison | 4/12 | 0/12 |
| Compatible Business Trend metrics | 11/12 | 11/12 |
| Hypothetical scenario eligibility | 5/12 | 5/12 |
| Exact private research replay | 10/12 | 7/12 |

- **Price and peer coverage.** All twelve dated closes were from November 18. AMD, NVDA, BAC, and C had quote chronology holds. QCOM and DUK lacked quotes for the most recent common completed session required by the peer comparison. JPM, SO, and NEE had issuer share-class holds. TSM requires a separate ADS approach, SAP's listing-to-CIK match was unverified, and IBN lacked vendor context. The peer rules stayed at the same-day close, compatible annual diluted EPS, 35-day window, and three eligible references.
- **Financial and replay holds.** AMD's annual amendment remained unresolved and SAP lacked a supported direct-quarter filing. AMD, NVDA, BAC, and C each reopened at their individual capture times. At the shared study cutoff, their quote context had changed and the bound replay proofs required an explicit recheck. IBN remained held under the original revenue-based replay measure, with separate verified bank evidence and unchanged bank replay. The TSM result in the same-source recheck above uses a different observation.

The release candidate reproduced all rows and request counts at the recorded cutoff. Desktop and phone Discover checks showed the same denominators, group counts and held states. Reopening the retained study made zero new source requests.

### Receipt timing and retained replay

The November 19 investigation traced the four quote chronology holds to the collection clock. The study previously supplied the same attempt-start timestamp to every adapter. AMD, NVDA, BAC, and C returned market events two to four seconds after that start. Those quotes were from the November 19 intraday session, while the completed price bars were dated November 18.

Live collection now lets each adapter record when it obtained its evidence and evaluates the packet after collection ends. A fixed verification clock remains available for deterministic replay. The valuation comparison still requires the same completed price date, compatible annual diluted EPS and at least three qualifying references in the existing 35-day window.

When a selected company's proof needs checking again, **Recheck retained replay** verifies the saved context from the existing observations in a disposable store. The action preserves source receipts and dates. Stale inputs can still hold the result. **Recheck company** collects new inputs.

Rechecking AMD, NVDA, BAC, and C at the original midday cutoff raised exact replay from **7/12 to 11/12** on the same inputs. The four contexts reopened as Unchanged. Peer comparison stayed **0/12**, every other count matched, and no provider requests or user-store writes occurred. Desktop and phone automation exercised the action and verified unchanged source receipts and protected files.

The corrected live run observed the same twelve companies from 13:53 to 13:58 ET. All twelve dated closes still came from November 18. AMD, NVDA, BAC, and C now show the same intraday-versus-completed-close hold as QCOM and DUK. Exact replay qualified for **11/12**, direct-quarter facts for **10/12**, and same-basis peer comparison for **0/12**. The run made 58 raw callbacks and 106 adapter operations with no SEC access pause.

The November 16 after-close cohort provides the retained positive control with four qualifying peer comparisons. The November 18 DUK check shows that the two provider responses can settle at different times after the bell. [NYSE trading schedule](https://www.nyse.com/trade/hours-calendars) · [DUK post-close review](ONLINE_PEER_VALUATION.md)

### November 19 post-close rerun

The same twelve companies were measured from 16:16 to 16:23 ET, after the regular 16:00 close. All twelve had a verified November 19 closing price. Same-basis peer P/E rose from **0/12** in the corrected midday run to **1/12**. All other capability counts matched that run, including **10/12** direct-quarter facts and **11/12** exact research replay. The study made 172 raw source callbacks and 310 adapter operations with no SEC access pause.

The comparison uses a common completed closing date, compatible annual diluted GAAP EPS, the 35-day fiscal window, and at least three eligible industry references.

| Company | Peer valuation result |
| --- | --- |
| AMD | Withheld. Its current annual filing is still uncorroborated in Workbench. |
| NVDA | Qualified. Six references passed: AMD, TXN, MRVL, NXPI, MPWR, and ALAB. |
| QCOM | Withheld. Zero of at least three required references qualified. |
| JPM | Withheld. The selected common-share scope was unresolved. |
| BAC | Withheld. One reference qualified (C). Three are required. |
| C | Withheld. Two references qualified (BAC and WFC). Three are required. |
| DUK | Withheld. The selected common-share scope was unresolved in this refresh. |
| SO | Withheld. The selected common-share scope was unresolved. |
| NEE | Withheld. The selected common-share scope was unresolved. |
| TSM | Withheld. The ADS needs its own currency and per-share method. |
| SAP | Withheld. The selected listing-to-SEC-issuer match was unverified. |
| IBN | Unavailable. The quote provider's company context was unavailable. |

AMD's admission as an NVDA reference uses the peer method's annual filing evidence. Its own Workbench result also requires corroboration of the current structured annual filing. DUK's November 18 result remains a dated comparison. The November 19 run required current common-share evidence again. [Valuation and evidence method](ONLINE_PEER_VALUATION.md)

Desktop (1440 × 1000) and phone (390 × 844) Discover checks reproduced the retained counts at the recorded cutoff and showed the NVDA qualification and AMD hold. Replay made zero provider requests. All 89 protected files and the original retained inputs matched.

### November 19 common-share rerun

The same twelve companies were rerun from 16:38:49 to 16:51:08 ET. The SEC filings and dated Nasdaq Trader exchange directory verified JPM, DUK, SO, and NEE as the selected NYSE common shares. Same-basis peer P/E coverage rose from **1/12 to 6/12** across the two post-close runs. All twelve still had a verified November 19 close. Other capability counts matched the earlier run, including **10/12** current annual facts, **10/12** direct-quarter facts, and **11/12** exact research replay. The rerun recorded 265 raw source callbacks and 447 adapter operations with no SEC access pause. [Common-share source review](ONLINE_PEER_VALUATION.md#november-19-common-share-source-review)

The same-day completed close, compatible annual diluted GAAP EPS, 35-day fiscal window, and minimum of three eligible industry references were applied to every comparison.

| Company | Peer valuation result | Eligible references |
| --- | --- | --- |
| AMD | Withheld because Workbench could not corroborate the current structured annual filing. | Six references cleared the peer checks. The subject filing gate still holds the comparison. |
| NVDA | Qualified | AMD, TXN, MRVL, NXPI, MPWR, ALAB |
| QCOM | Withheld because zero of the required three references qualified. | — |
| JPM | Qualified | BAC, WFC, C |
| BAC | Qualified | JPM, WFC, C |
| C | Qualified | JPM, BAC, WFC |
| DUK | Qualified | ED, WEC, PEG, AEE |
| SO | Withheld because the provider's exhibit link could not be matched to the SEC parent issuer. | — |
| NEE | Qualified | AEP, D, ETR |
| TSM | Withheld because the ADS needs a separate currency and per-share method. | — |
| SAP | Withheld because the selected listing-to-SEC-issuer match is unverified. | — |
| IBN | Unavailable because the quote provider's company context was unavailable. Generic replay remained held. | — |

SO's NYSE common-share evidence passed independently. The fresh quote-provider packet linked the exhibit for accession `0000092122-25-000084` under Southern Power's CIK `0001160661`. The SEC index lists both Southern Power and The Southern Company as filers. The existing valuation check still requires an exhibit bound to the parent issuer's CIK `0000092122`. [SEC joint filing index](https://www.sec.gov/Archives/edgar/data/92122/000009212225000084/0000092122-25-000084-index.htm)

Desktop (1440 × 1000) and phone (390 × 844) Discover checks reproduced the 12-company results. Workbench displayed the exact verified common-share sources for all four issuers and the separate SO hold. The checks made zero provider requests and preserved all 89 protected files and the original source inputs.

### November 19 joint-filing rerun

The same twelve companies were rerun with observation times from 17:14:09 to 17:27:26 ET. Same-basis peer P/E coverage moved from **6/12 to 7/12**. All twelve companies still had a verified November 19 close, with **10/12** current annual facts, **10/12** direct-quarter facts, and **11/12** exact research replay. The run recorded 299 raw source callbacks and 497 adapter operations with no SEC access pause.

SO qualified with NEE, AEP, D, and ETR. DUK, ED, WEC, PEG, and AEE had a different SEC industry code. XEL and PCG had unresolved issuer share classes. EXC's provider filing link remained unmatched. NEE also gained SO as an eligible reference alongside AEP, D, and ETR. The joint filing resolves SO's provider identity. Its annual diluted EPS comes from the parent's FY2025 10-K. The comparison retains the same-day completed close, compatible annual diluted GAAP EPS, 35-day fiscal window, and minimum of three eligible industry references. [Exact joint-filing review](ONLINE_PEER_VALUATION.md#southern-company-joint-filing-identity)

NVDA, JPM, BAC, C, and DUK retained their earlier qualifications. The five remaining comparison gaps were:

| Company | First unresolved check |
| --- | --- |
| AMD | Workbench could not corroborate the current structured annual filing. |
| QCOM | Zero of the required three industry references qualified. |
| TSM | The ADS requires a separate currency and per-share method. |
| SAP | The selected listing-to-SEC-issuer match is unverified. |
| IBN | Provider company context was unavailable. Generic replay remained held. |

Discover and Workbench passed browser checks at 1440 × 1000 and 390 × 844. Discover reproduced the saved study counts. Workbench showed both SEC index links, the separate annual EPS source, and the four qualifying references and eight exclusions. The checks made zero provider requests and preserved all 89 protected files and the original source inputs.

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
