# Exact quarterly SEC evidence

The financial refresh now inspects the latest exact 10-Q when current Companyfacts quarter evidence is unresolved. Supported archive facts flow through the company summary, quarterly chart/table, Business Trend, saved online research and Monitor. The archive lane keeps its own source permissions and the original Companyfacts pending state.

Baseline: `8868a5bd0f567d71151ff9b5d492837aa570ffdc`. Verification ran November 8 Toronto time / November 9 UTC, 2026. This is a bounded four-issuer engineering verification, not all-company coverage or an independent investment conclusion.

## Sources and measured coverage

The current source run made thirteen unique original HTTP requests: one shared SEC ticker map, and one Companyfacts response, submissions response and exact primary document per issuer. Full source bytes, original digests and observation receipts remain private. All four selected reporting periods end September 30, 2026.

| Company | Exact SEC accession and document | Filed | Standard direct-quarter fields |
| --- | --- | --- | --- |
| C | [0000831001-26-000056](https://www.sec.gov/Archives/edgar/data/831001/000083100126000056/c-20260930.htm) | 2026-11-05 | Revenue; operating income and quarter cash fields withheld |
| DUK | [0001326160-26-000051](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000051/duk-20260930.htm) | 2026-11-05 | Revenue and operating income; quarter cash fields withheld |
| SO | [0000092122-26-000069](https://www.sec.gov/Archives/edgar/data/92122/000009212226000069/so-20260930.htm) | 2026-11-05 | Revenue and operating income; quarter cash fields withheld |
| NEE | [0000753308-26-000081](https://www.sec.gov/Archives/edgar/data/753308/000075330826000081/nee-20260930.htm) | 2026-10-21 | Revenue and operating income; quarter cash fields withheld |

Across the four standard fields—revenue, operating income, operating cash flow and capital expenditures—**7/16 direct-quarter fields** are supported; **9/16 remain withheld**. Separately, **14/16 cumulative fields** are supported: C's operating income and NEE's capital expenditures stay held. C's directly reported net-interest and noninterest components remain separate observations, outside those standard-field counts; they are never added to manufacture revenue. No quarter cash flow is inferred by subtracting year-to-date amounts.

The financial refresh reuses the original map and submissions receipts, pins the latest exact filing version and rejects mismatched identities, dates, contexts, native units, revisions or literal numeric proofs. Parent-issuer facts are distinguished from subsidiary and dimensional contexts in utility joint filings. Source accession need not equal issuer CIK. Acceptance time and official filing date remain independent, including SO's different UTC acceptance and filing dates.

C's large original submissions receipt is retained losslessly with bounded compression. Default JSON raw retention remains 2 MiB; exact classification opts into at most 4 MiB. The source selector bounds raw catalogs before reducing relevant report forms. Classification is still rederived from the complete original JSON and matched to its original digest.

## Using the workflow

Search a company online, open Company Workbench and press **Research company** or **Refresh options → Financials only**. In **Financial Trends**, inspect **Exact SEC quarter**, select **Quarterly**, and open **Source and reporting basis**. The panel exposes missing reasons, concepts, periods, source references, filing/acceptance/observation dates and receipt digests. Data Sources repeats this source context.

**Research Notes → Saved online research** saves the normalized research context. An identical save retains the same immutable snapshot and reports **unchanged**. Historical replay and **Monitor → Saved online research updates → Reopen exact saved research** return to that company and snapshot without source requests. Literal proofs are accepted only in typed quarterly/cumulative field locations and rechecked on save/replay; source bodies, raw archive keys and base64 remain excluded. The 512 KiB snapshot cap is unchanged.

The four actual-source contexts saved and replayed exactly, with repeated-save identity unchanged: C 129,115 bytes; DUK 341,500; SO 291,244; NEE 338,749. These contexts exclude a new price or peer acquisition; they do not assert refreshed peer conclusions. Scenario revenue still requires an independently supported current annual base; banks remain excluded from operating-company FCFF scenarios. Annual EPS, same-day completed prices, the 35-day fiscal window and at least three eligible peer references retain their existing rules.

## Rights and unchanged inputs

Exact archive fields remain `unregistered_sec_archive_personal_inspection_only`, with commercial eligibility and saved readiness false. Companyfacts field permissions do not transfer to archive facts. No raw document, financial snapshot or source-derived screenshot is included in this public release. The source-rights registry, canonical/demo data, credentials and existing public assets are unchanged. No data was purchased.

All 89 protected files match the baseline byte for byte. Compact ordered path/content-digest manifest SHA-256: `6dea65bec009270b132211724f426c1fdb557979a8903a5f5cc93b92d9edb373`.

## Verification

- Affected source, identity, inline parser, annual/quarterly history, peer, context, snapshot, coverage and Workbench regressions: **910 passed in 97.63 seconds**. The existing external dateutil deprecation warning remains. Earlier focused counts overlap and are not added to this total.
- Desktop/phone journeys: **2 passed in 156.31 seconds**, at 1440×1000 light and 390×844 dark preference. Constructed source bytes pass through production loaders, parsers and research tools. All four cases verify direct-quarter fields, withheld reasons, separate cumulative cash, Quarterly chart/table controls, exact period source links and the unchanged twelve-company Discover denominator. DUK saves one immutable context, compares unchanged, replays historical evidence and returns through Monitor without later source calls. English, readable disclosures/actions, no page overflow or browser errors, and unchanged canonical/user stores were checked. These are responsive engineering checks; the separate thirteen-source run above establishes the real filing observations.
- All **six** research route renders passed. Public wording passed across **71 files**. Staged hygiene and whitespace passed with no generated or canonical data staged. The owned local application restarted and returned health `ok`.
- Independent review's final bounded recheck found no unresolved reproduced P1/P2 issue. All **89 protected files** remain unchanged as recorded above.

No full repository-suite, resulting-main hosted CI, independent human accessibility or hosted-service operation claim follows from this verification. The repository's current workflow runs on pull requests; this authorized direct main synchronization does not claim a resulting-main hosted CI run. The tested commit and remote synchronization are recorded below after the push.

Independent review reproduced a stale-structured comparison defect: a new archive value could be compared using the older structured current value. The headline now uses the same merged, validated history and requires equal revenue definitions. Broader productive-asset purchases also remain distinct from PP&E spending and cannot qualify the PP&E cash-generation metric.

The initial checks left Companyfacts lag, nine unsupported direct-quarter fields, C's operating-income definition and NEE's consolidated PP&E purchase definition visible. Later releases track foreign issuer and research-context work separately.

[Online workflow](ONLINE_COMPANY_RESEARCH.md) · [Self-service method](SELF_SERVICE_COMPANY_RESEARCH.md) · [Prior bank snapshots](BANK_RESEARCH_SNAPSHOT_RELEASE.md) · [Roadmap](../ROADMAP.md)

## Tested commit and synchronization

Verified implementation: [`5eba9e63713df9e51ef9aab475b159d4ff786bae`](https://github.com/YuzeJ21/Stock-Analysis/commit/5eba9e63713df9e51ef9aab475b159d4ff786bae). GitHub main accepted the fast-forward from the stated baseline. The remote Git ref and independent GitHub branch read matched the full commit; remote README and release-document blob IDs matched the local files. This documentation-only follow-up records those checks without changing tested runtime code, tests or protected inputs.

The ignored local review packet is `outputs/local/releases/exact-quarterly-evidence-20261108/`: reduced source/date/digest results, unchanged-input manifest, exact private replay outcomes, regression/review logs, constructed browser screenshots and a held local PR draft. Full original sources and actual research contexts remain private temporary captures. No PR was opened and no user notes or evidence stores were written during verification. The owned local application is healthy on port 8536; unrelated worktrees were preserved.

## NEE capital-investment review

The October 21, 2026 10-Q reports a consolidated total for capital expenditures, independent power and other investments, and nuclear fuel purchases for January 1 to September 30. The filing separately reports cash outlays for FPL capital expenditures, NEER independent power and other investments, nuclear fuel, and other capital expenditures. Workbench shows the reported total and each tagged cash-flow line under **Year-to-date capital investments**, with links to the exact facts. The separate FPL registrant statement, accrued property additions and quarter-length disclosures do not supply NEE consolidated cash purchases of PP&E. [Exact SEC 10-Q](https://www.sec.gov/Archives/edgar/data/753308/000075330826000081/nee-20260930.htm)

The supplemental evidence retains its nine-month duration and parent filing identity. The direct-quarter cash-flow and capital-purchase gaps stay visible. The nine-month consolidated PP&E field and PP&E-based cash-generation calculation remain withheld. Private snapshots retain the exact source definitions and receipt for offline replay. The source-rights registry and eligibility rules above also apply to this evidence.

The November 11, 2026 Toronto-time verification used the current official ticker map, Companyfacts, submissions and one exact primary-document response. Desktop (1440 × 1000) and phone (390 × 844) checks replayed those responses through the normal Workbench workflow. Both verified the filing links, separate periods, withheld fields, unchanged saved evidence and return from Monitor with zero additional source requests. All 89 protected files matched the baseline.

Affected regression tests recorded 3,108 passes and four UI timeouts in the broad run. The four timed-out cases passed when rerun together, for 3,112 verified cases. Exact source receipts and browser captures remain in the private local verification packet.
