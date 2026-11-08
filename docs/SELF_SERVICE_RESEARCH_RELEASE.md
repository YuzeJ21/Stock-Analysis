# Self-service research release evidence

Date: November 8, 2026. Baseline: `3026da8a473905e662a69703b91d181784fb5113`. Implementation used the existing isolated worktree. The tested code commit and verified synchronization are recorded below.

## Delivered behavior

An online company absent from saved company rows can use **Research company**, Business Trend, reported annual components, online annual P/E or its specific gap, observed industry references, hypothetical Scenario Lab, issuer notes, Forward View/Decision Lab, normalized context save/compare, Monitor and exact historical replay. No manually prepared company financial/price CSV or ongoing coding session is needed for this supported workflow. The app server still runs locally; Pages remains a static example.

Every financial refresh independently attempts current SEC submissions after a matched directory CIK, including during a Companyfacts outage. Latest annual/quarterly versions, comparative periods, amendment scope and structured-facts lag remain distinct. An affected current scenario or peer verdict is withheld; historical observations remain dated. Ordinary section changes, calculations and replay do not fetch new source observations. The optional MRVL supplement reuses the generic submissions receipt.

Scenarios reuse existing calculation kernels with explicit hypothetical FCFF assumptions and a corroborated annual revenue base. Missing net debt or shares preserves enterprise value without inventing capital structure. Unsupported banking/entity bases remain held. Notes use existing preview/confirmation. Immutable normalized contexts retain exact profile/ticker/CIK, content IDs and checksums; raw archive bodies are excluded. The new Monitor queue is separate from annual SEC review counts.

## Verification

- Core observed-data, notes, store, Workbench, identity and transport regression: **390 passed in 69.32 seconds**.
- Navigation/workspace regression, including a snapshot-only company with no notes or SEC receipts: **189 passed in 14.63 seconds**. Subsequent exact-route regression verifies all five sections and Monitor retain the snapshot and a 22% draft assumption.
- Financial/identity/peer/quarter/source-rights/after-tax regression: **430 passed in 7.32 seconds**.
- Additional Workbench/peer-display/quarter checks: **70 passed in 3.67 seconds**.
- Desktop/phone self-service journey: **2 passed in 62.37 seconds**, at 1440×1000 and 390×844. Real calculation kernels, note preview/confirmation, identical snapshot saves, exact replay, retained assumptions, no horizontal overflow, English, no browser/app exceptions, no extra navigation requests and unchanged demo data are verified with constructed sources in disposable storage.
- Legacy browser/performance group: 42 passed with one obsolete duplicate-refresh assertion; the corrected combined-action Monitor cases then passed **2 tests in 31.90 seconds**. The other 42 passing cases were unchanged. The initial in-progress broad run was interrupted after 90 passes and nine stale label/call-count assertions; it was not a full-suite pass. No full repository suite is claimed for this release.
- Documentation/method/source-history group: 179 passed with six documentation mismatches; the six were corrected. The later documentation/public-hygiene group recorded 149 passes with three residual wording/index assertions, followed by their passing targeted rerun. The combined completed-milestone heading preserves both external hosting and independent-session gates.
- Documentation residual/public-wording checks: **9 passed in 1.37 seconds**. An unrelated launcher write-free check initially observed another test process changing its cache; with a quiescent checkout and cache writing disabled, that exact test passed **1 test in 53.19 seconds**. Its canonical no-write assertions were preserved. The broader launcher run was interrupted and is not claimed complete.
- Six research route renders passed; a fresh isolated server import and HTTP health check passed. Public wording scanned 66 files successfully. Source-rights diagnostics remain read-only.

Counts above overlap; they must not be summed into a unique test total. The existing dateutil import deprecation warning remains. The focused modules separately cover 46 filing, 48 tool and 41 private-store cases. Independent review found stale primary peer rendering, Monitor draft loss, coupled filing-source failure, a commercial replay bypass and a snapshot-only route gap; each was reproduced, fixed and re-reviewed. No actionable P1/P2 remained in the reviewed paths.

## Real-source checks and boundaries

Microsoft's online annual period ended June 30, 2026 and quarter ended September 30, 2026 matched their latest SEC filings. Marvell's annual period ended January 31, 2026 and quarter ended August 1, 2026 also matched. Each produced 18 supported historical periods and a working hypothetical enterprise-value scenario without a prepared company CSV. Marvell's normalized context saved at about 284 KB and compared unchanged against the same inputs. Its missing standard net-income selection remained a component gap rather than an invented value.

An actual Microsoft browser run loaded online financials and a dated completed close, calculated a hypothetical scenario, and retained a peer-comparability hold. Live observations and screenshots remain private outside Git. These are observed source checks, not broad coverage, investment validation or a guarantee of future provider availability. Later-filing/facts-pending and amendment transitions use controlled source tests; an independently observed future filing transition is not claimed.

## Preservation and rights

All **89 tracked files** under `data/`, `config/`, `assets/` and `docs/assets/` match the baseline byte-for-byte. Manifest SHA-256: `6dea65bec009270b132211724f426c1fdb557979a8903a5f5cc93b92d9edb373`. No canonical rows, source-rights decisions, saved readiness, existing SEC receipt schema or public screenshot was changed. Existing SEC registered direct-field permission remains limited to its field scope; new metadata/components, archive inspection and price observations keep their separate personal-inspection boundaries. Commercial mode blocks the new replay UI. This is not blanket distribution clearance or commercially licensed operation.

No paid data, new provider account, credentials, deployment or third-party communication was introduced. Automated tests do not establish human validation, screen-reader conformance, demand or hosted reliability.

## Next executable stage

Measure the generic filing-and-tool workflow across the existing cross-industry sample, retain failure-inclusive denominators and current filing versions, then address the largest verified definition gap. Prioritize meaningful saved updates using independently observed subsequent filings. Keep custom/unstructured taxonomy, bank valuation, FX/ADS, consensus, tax allocation, share-class capital structure, hosting and operated rights as separate gates. [Roadmap](../ROADMAP.md) · [User workflow](SELF_SERVICE_COMPANY_RESEARCH.md)

## Commit and synchronization record

Tested code commit: [`afacbba216b1bfaed7b864643d60ac87eead9684`](https://github.com/YuzeJ21/Stock-Analysis/commit/afacbba216b1bfaed7b864643d60ac87eead9684). On that committed tree, the seven-file filing/tool/store/financial/UI/workflow/navigation regression passed **231 tests in 18.86 seconds**. The earlier final browser run passed both viewports in 62.37 seconds on the same executable implementation; subsequent test-file EOF cleanup changed no executable source.

The tested commit was fast-forwarded to GitHub `main`; both `git ls-remote` and the GitHub branch API returned its full SHA. This documentation-only follow-up records those results and completes the execution ledger. The existing Commercial Research Beta workflow triggers on pull requests, so no exact-head hosted CI result is claimed for the direct authorized main synchronization. No pull request, release, new hosting or manual deployment was created.
