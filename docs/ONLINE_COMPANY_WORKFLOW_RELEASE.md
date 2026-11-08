# Online Company Workflow release evidence

Date: November 7, 2026. Baseline: `9377dff2a7ad8c775af01248df8b225eb660128c`.

## Scope

- Company Notes no longer constructs a price-dependent local report before showing user records. Existing saved-workspace journals remain separate from online issuer notes and remain accessible without model/universe rows.
- Online note files are created only after explicit preview and confirmation, using the actual profile and ticker with a separate CIK-scoped storage path and UI namespace. Notes-only routes can reopen after reload; saved identity does not establish a current listing.
- Monitor lists saved user follow-ups independently of SEC comparisons and legacy research-process counts. Return navigation retains the captured company/issuer, section and loaded session observations.
- Generic eligible annual SEC capture, import, replay and comparison remain independent of local company CSVs. An explicit selected CIK guards these operations. Identical inputs retain No change; incomparable identities, periods, definitions and permissions retain gaps.
- Saved-model Scenario Lab, Decision Lab, Forward View, catalysts, outcome history and the HTML Research Brief retain independent input requirements. Notes offers explicit access to model-dependent tools when a saved company exists.
- The outer Workbench columns stack at the same breakpoint as mobile navigation. Desktop rail, phone two-column observation cards and 44px controls are retained.

## Verification record

Verified source revision: `6b82a9691ac9b496029463b4812ac142fa1ffb8d`, synchronized to GitHub `main` and independently fetched through GitHub. Baseline: `9377dff2a7ad8c775af01248df8b225eb660128c`. The final publication adds documentation only after this source revision.

The complete 9,164-case collection is accounted for by latest case-ID results: **9,161 passed, 3 explicitly skipped, zero unresolved failures**. This is combined evidence across the groups below, not a claim that one fresh full-suite invocation exited green. Unchanged passing cases were retained after narrowly scoped corrections.

| Verification group | Final distinct-case result | Evidence |
| --- | --- | --- |
| Standalone HTML brief browser contracts | 320 passed | Retained from the frozen `4370bea786a6fb1e15bec4ffb53b4f0970848684` run. Renderer, collector and this test module remain unchanged; they do not import the subsequently updated navigation helper. |
| Repository prefix before public release documentation, excluding that standalone module | 6,538 passed; 3 skipped | Retained from the `a883a6ba3608aa3d0f5bee12a82c034dfd9760c6` run. Subsequent changes affected documentation and a test fixture; all runtime source remains byte-identical to this revision. |
| Public release documentation | 97 passed | Full module rerun in 1.39s after restoring the append-only thesis journal and legacy Follow-up Queue descriptions and moving historical layout detail to Completed Milestones. |
| Remaining repository modules | 2,206 passed after fixture correction | Initial run: 2,202 passed and four saved-issuer fixture failures. The complete Monitor browser module then passed all 12 cases in 198.47s, replacing those four failures without double-counting the other eight. |

The three skips are the historical real six-company pair test, whose ignored private receipts are absent, and the opt-in live AMD/QCOM browser cases, whose `STOCK_LIVE_WORKBENCH_BASE_URL` was not set. They are not passing live-company results. Separately, live MRVL online financials and a dated close were checked read-only on desktop and phone, including Monitor return with loaded observations retained.

Additional overlapping verification, excluded from the distinct-case total:

- Integrated focused checks: 241 passed in 97.48s.
- Online persistence and responsive browser groups: 10 passed in 79.14s; widths 390, 711, 726, 767, 768 and 1440 pixels. No page overflow; 44px actions and phone observation cards retained. Model-gap caption opacity is 1.
- Saved-model smoke and AppTest isolation corrections: 10 passed in 75.06s.
- Navigation helper: 2 real-browser cases passed in 26.08s and 3 focused unit contracts passed. Keyboard retries, uniqueness, visibility and content assertions remain intact.
- Dashboard import/startup, all six Personal Research route renders, public wording, staged hygiene and whitespace checks passed. The commercial-beta command passed its local checks while retaining external hosting, rights and operations gates.
- SHA-256 comparison: all 78 tracked files under `data/`, `config/` and `assets/` match the baseline.

### Corrections and failed-run accounting

The preliminary broad run was stopped for source corrections and is not a passing result. Another intermediate run correctly detected concurrent source/document edits through its repository fingerprint guard. Source was then frozen for subsequent runs.

The frozen full run reported 3,601 passed, one skipped and five obsolete saved-model UI expectations in 855.72s. The remaining-suite run reported 6,628 passed, three skipped and five documentation failures in 1,109.30s. The final module group initially reported 2,202 passed and four fixture failures in 896.39s. Every failed case was corrected and rechecked as described above. Assertions were preserved or strengthened: tests now open the explicit saved-model action, exact summary-parent selectors identify nested briefs, and the fixture accepts only the exact NEM/AMD/DUK saved CIK or the existing legacy no-CIK scope. Mismatched identities and unexpected refreshes remain rejected.

Independent automated review also led to regressions for bounded-note write/read consistency, corrupt CSV handling, saved issuer versus ticker-only models, inventory overflow, external thesis updates, missing legacy directories/profiles, saved-SEC-only drafts and pinned return identity. Final review reported no unresolved actionable P1/P2 findings.

Repository CI is pull-request-triggered. Direct `main` synchronization does not produce a new Commercial Research Beta CI run; no hosted CI pass is claimed.

## Data and permissions

No canonical financial, price, universe, readiness or source-rights changes are included. Private note stores, saved SEC captures, real provider observations and browser screenshots are excluded from Git. Browser persistence tests use synthetic user-authored records and disposable storage; live checks do not create real research records.

New issuer note files enforce their serialized file-size and readable-field limits both at preview and the locked confirmation step. Existing valid legacy journals preserve their prior size behavior. Saved SEC receipts remain immutable and the reasoned exact-pair disposition allowlist remains NEM, AMD and DUK.

The full application runs locally and uses online sources. GitHub Pages remains the static English demonstration and dated AMD example. This slice does not deploy a hosted workspace, grant provider rights, approve financial models or establish independent user validation.

## Next executable step

Review one named economic peer relationship and its earnings-quality differences using exact sources. Keep reported annual, trailing, adjusted and forecast denominators distinct, and preserve existing price/period/minimum-reference gates.
