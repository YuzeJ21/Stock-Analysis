# Accessibility Evidence

This document records direct local accessibility evidence for the supported
Personal Research workflow. It is an evidence log, not a WCAG conformance
claim.

## 2026-07-23 partial workflow audit

Scope:

- Local Streamlit dashboard in Personal Research mode.
- Research Desk -> Discover -> Company Workbench -> Monitor.
- Desktop viewport: `1280x720`.
- Phone viewport: `390x844`.
- Browser: local Chromium-based browser.
- Company Workbench review ticker: `AVGO`.
- No readiness rebuild, data refresh, evidence recording, or repository
  screenshot generation was performed.

Directly observed:

- All four routes rendered at desktop and phone widths without document-level
  horizontal overflow.
- The document language was `en`.
- Visible form controls exposed labels or accessible names in the inspected
  DOM.
- No duplicate element IDs were found in the inspected routes.
- A focused Data Health link showed a visible three-pixel teal outline.
- Research-only and no-account-action boundaries remained visible.
- The Monitor `Open Discover` action initially rendered white normal-size text
  on Streamlit red, measured at approximately `3.3:1`.
- The local theme now gives primary link buttons a `#0b3b36` background and
  border with white text. Runtime retest measured the Monitor action at
  `12.4:1`.
- A route-preserving `Skip to page answer` link is now present in the
  accessibility tree on all four Personal Research routes. Direct desktop and
  phone retest verified the correct route, ticker, and open-state parameters
  for the Company Workbench link and a focusable `tabindex="-1"` answer target.
- Primary route sections now follow each route `h1` with `h2` headings.
  Direct desktop and phone DOM retest verified the complete Workbench sequence
  from `What Changed` through `Advanced Evidence`; Monitor retains the nested,
  non-empty `h3` for `Earnings evidence readiness`.
- The semantic correction was retested at `1280x720` and `390x844` with no
  document-level horizontal overflow. New screenshots remain ephemeral under
  `/tmp/stock-research-accessibility-audit-2026-07-23/` and are not repository
  or release artifacts.

Open findings:

- The inspected routes still expose no `main` landmark.
- Current local Streamlit `1.59.2` containers expose layout and key parameters
  but no semantic role or element parameter. A client-side workaround would
  require unsafe JavaScript tied to framework-owned DOM selectors. That
  approach is not accepted as a stable landmark implementation without a
  separately reviewed design and direct runtime evidence.
- The skip link is structurally present and uses the existing visible-on-focus
  CSS contract, but a complete keyboard traversal has not yet directly proved
  first-focus placement, focus transfer, or return-path behavior.
- Framework help controls measured approximately `16x16` CSS pixels and
  dataframe toolbar controls approximately `22x22`. Hidden native radio inputs
  also measured small, but their visible labels are larger and require separate
  hit-target review rather than treating the input box alone as the target.
- The inspected routes exposed no explicit live region. Dynamic update and
  validation announcements still require task-level assistive-technology
  testing.
- Browser automation did not prove the complete keyboard traversal order.
- Direct screen-reader tasks, 200% and 400% zoom, forced-colors behavior,
  reduced-motion environment verification, and error-association tasks remain
  untested.

Classification:

- `partial_local_accessibility_evidence`
- The contrast, route heading hierarchy, and route-preserving skip-link defects
  above are fixed and directly retested within the stated scope.
- Priority 7 remains incomplete. Screenshots, DOM inspection, and one focused
  contrast/semantic retest do not prove keyboard accessibility,
  assisted-technology support, or WCAG conformance.

Next safe local step:

1. Execute `docs/ACCESSIBILITY_TASK_PROTOCOL.md` in a suitable review
   environment and record direct keyboard traversal, focus, disclosure,
   search, navigation, validation, and error-recovery evidence.
2. Complete zoom/reflow, forced-colors, and screen-reader tasks from the same
   protocol.
3. Revisit the `main` landmark only through a stable Streamlit capability or a
   separately reviewed design; do not inject an unverified DOM-mutation patch.

The protocol is not completion evidence and no task result is inferred merely
because the protocol now exists.

## 2026-07-26 same-page skip-link routing audit

Scope:

- Local Streamlit `1.59.2` dashboard in Personal Research mode.
- macOS `26.5.1` at a `1280x720` CSS viewport.
- Research Desk and ticker-bound Company Workbench route for `AVGO`.
- No readiness rebuild, source refresh, research-record save, screenshot
  capture, or generated-artifact write.

Directly reproduced:

- Although the helper emitted no target attribute, the live Streamlit DOM
  normalized `Skip to page answer` to `target="_blank"`.
- Activating that live link did not move focus to the answer target or retain
  the current tab's route context.
- Existing tests asserted the constructed route URL and target element but did
  not cover the live same-tab contract.

Remediation and direct retest:

- The skip link now uses the fragment-only destination
  `#public-page-answer` plus explicit `target="_self"`. A fragment-only
  destination retains every current mode, route, ticker, and disclosure query
  parameter without triggering a Streamlit rerun that resets focus.
- The helper contract is covered for Public, Personal Research, and Operator
  routes.
- Direct Company Workbench retest retained
  `?mode=research&page=company-workbench&ticker=AVGO&open=1`, appended only
  `#public-page-answer`, kept the same browser tab, scrolled the answer target
  to the top of the viewport, and left `document.activeElement` on the
  focusable `public-page-answer` target.

Evidence boundary:

- This closes the reproduced new-tab/rerun defect and proves the live
  same-document target behavior in the stated environment.
- The available browser-control environment could not activate ordinary links
  through its synthetic Enter input, including the unrelated `Open Discover`
  control. K01 and K02 therefore remain `blocked_environment`, not
  `passed_direct`; no complete keyboard-only traversal is claimed.
- Priority 7 remains incomplete. Direct keyboard, zoom, forced-colors,
  reduced-motion, target-size, screen-reader, and stable-main-landmark evidence
  remains required under `docs/ACCESSIBILITY_TASK_PROTOCOL.md`.

## 2026-07-27 framework-control target-size audit

Scope:

- The same local Streamlit, macOS, Personal Research, and no-write boundary as
  the preceding audit.
- Ticker-bound Company Workbench for `AVGO`.
- Desktop `1280x720` and phone `390x844` CSS viewports.
- The Workbench quarterly-trend disclosure was opened only to expose its
  existing dataframe toolbars; no data or research state was changed.

Directly reproduced:

- The visible framework help target measured `16x16` CSS pixels.
- Visible dataframe `Show/hide columns`, `Download as CSV`, `Search`, and
  `Fullscreen` targets measured `22x22` CSS pixels.

Remediation and direct retest:

- The first style correction enlarged the tooltip wrapper, not its nested
  button. An expanded P02 audit caught the actual help button still at
  `16x24`; this intermediate result is not completion evidence.
- The corrected shared style now reserves at least `24x24` CSS pixels for the
  actual nested Streamlit tooltip/help buttons and dataframe toolbar buttons.
  The phone Workbench `Open Data Health` action also retains its compact text
  treatment with an explicit `24px` minimum height instead of the reproduced
  `21px`.
- Final desktop retest measured the visible actual help button and all 16
  exposed dataframe toolbar buttons at exactly `24x24`.
- Final phone retest measured the visible actual help and dataframe buttons at
  `24x24` and `Open Data Health` at `102x24`; document width remained equal to
  the `390px` viewport width.

Evidence boundary:

- This directly closes the reproduced P01 size defect for the inspected
  framework controls and current Streamlit markup.
- It does not prove pointer-spacing exceptions, every framework version,
  complete P02 route-control coverage, keyboard order, zoom, forced colors,
  reduced motion, screen-reader behavior, or WCAG conformance.
- Priority 7 remains incomplete under
  `docs/ACCESSIBILITY_TASK_PROTOCOL.md`.

## 2026-07-27 direct Chrome keyboard workflow audit

Run metadata:

- Run ID: `a11y-2026-07-27-chrome-keyboard-01`.
- Commit: `15c5270070238b91343a9f6eaa26f86527bfcaf2`.
- Route base: local `http://localhost:8501/`.
- Environment: macOS `26.5.1` build `25F80`; Google Chrome
  `150.0.7871.182`; external display `3440x1440`; explicit CSS viewport
  `1280x720`; 100% zoom; default colors and motion.
- Input: direct Chrome browser-control `Tab`, `Shift+Tab`, arrow, Enter, and
  text-key input. Screen reader: `not_run`. Reviewer:
  `Local supervised browser review`.
- The run used saved readiness only. It performed no refresh, readiness
  rebuild, research-record save, screenshot capture, or generated-artifact
  write. Browser-control input is direct functional evidence in this exact
  environment; it is not independent human or assistive-technology review.

Direct task results:

- K01: `failed_reproducible`. After reload, the first focus sequence was
  Workspace help button -> selected Workspace radio input -> selected route
  radio input -> Streamlit main section -> `Skip to page answer`. Each of the
  repeated shell controls therefore preceded the skip link. The inspected
  controls had a visible three-pixel teal outline.
- K02: `passed_direct` in the recorded environment. Enter on the focused skip
  link retained
  `?mode=research&page=research-desk`, appended only
  `#public-page-answer`, and moved `document.activeElement` to the
  `public-page-answer` target.
- K03: `passed_direct` in the recorded environment. Arrow Down on the selected
  route radio changed the URL to
  `?mode=research&page=discover`, rendered the `Discover` `h1`, retained
  keyboard focus, and showed the focus outline.
- K04: `failed_reproducible`. Search accepted `AVGO` and Enter, Tab, and Enter
  opened the correct ticker-bound Company Workbench route without a pointer.
  However, every result action exposed the same accessible text
  `Open review`; neither the ticker nor company identity was present in the
  link's accessible name. The action is operable but is not distinguishable
  in a screen-reader links list or when encountered outside its visual row.
- K05: `failed_reproducible` at the first material focus defect. Native
  disclosure `summary` elements received focus in the route sequence but had
  computed `outline: none`; the complete disclosure traversal was stopped at
  that first mismatch rather than promoted to a pass.
- K06-K09, Z01-Z03, C01-C02, M01, S01-S07, and remaining P02 coverage:
  `not_run` in this run.

Additional bounded observations:

- An intentionally incomplete authoring validation was triggered with a
  pointer only and saved no record. After the Streamlit rerun completed, the
  `thesis_id is required` message was contained by
  `data-testid="stAlertContainer"` with `role="alert"`. This DOM observation
  does not pass keyboard task K06 or screen-reader task S06.
- The earlier apparent `23.2x18.7` skip-link target was measured while the link
  was deliberately clipped off screen. When focused through the direct
  keyboard path, the visible target measured approximately `132.6x38.2`.
  No target-size defect is recorded from the clipped state.

Root-cause and next-design boundary:

- Streamlit renders the sidebar before the main section in DOM focus order.
  The current skip link lives in the main section, so source-call ordering
  cannot place it before sidebar controls.
- The shared focus selector covers links, buttons, form controls, explicit
  roles, and nonnegative `tabindex`, but not native `summary`.
- Discover renders ticker-specific destinations with identical visible and
  accessible `Open review` text.
- The narrow remediation should place one skip link as the first focusable
  sidebar child, add ticker-specific accessible names while retaining the
  concise visible action label, and include `summary:focus-visible` in the
  shared focus contract. This is a proposed design, not an implemented fix.
- Priority 7 remains incomplete. Phone keyboard, complete K05-K09, zoom,
  forced colors, reduced motion, screen-reader tasks, stable `main` landmark,
  and remaining P02 coverage still require direct current evidence.

## 2026-07-27 zoom-environment and phone-target follow-up

Run metadata:

- Run ID: `a11y-2026-07-27-reflow-targets-02`.
- Commit: `6aef0f8a9e89e8ec94d308095ca18ef33ea4177a`.
- Environment: the same macOS and Chrome versions as the preceding direct
  keyboard run. Screen reader: `not_run`. Reviewer:
  `Local supervised browser review`.
- The run used saved readiness and performed no refresh, readiness rebuild,
  valid authoring preview, research-record save, screenshot capture, or
  generated-artifact write.

Zoom classification:

- Chrome page-level keyboard input remained available for route tasks, but the
  connected review surface did not pass browser-level zoom shortcuts through
  to Chrome. Repeated `Meta`/`Control` plus zoom attempts left the CSS viewport
  and device-pixel ratio unchanged.
- Z01-Z03 are therefore `blocked_environment`, not `passed_direct`.
- A separate viewport-only stress check at `640px` and `320px` found no
  document-level horizontal overflow on Research Desk, Discover, Company
  Workbench, or Monitor. This is bounded responsive-reflow evidence only. A
  smaller viewport is not substituted for 200% or 400% browser zoom.

Phone target and spacing follow-up:

- At a `390x844` CSS viewport, every route was allowed to complete its
  Streamlit render before measurement.
- The first overlap scan included controls retained inside closed native
  disclosures and reported false-positive geometry intersections. Excluding
  closed disclosure contents removed those intersections; they are not
  recorded as product defects.
- Visible main-content route controls, primary links, search controls, and
  disclosure headers on the four routes had no measured target below
  `24px`, no measured adjacent overlap, and no document-level horizontal
  overflow in the inspected collapsed state.
- Opening `Add a reviewed research record` exposed the current thesis authoring
  controls without entering or saving data. The Record type control measured
  approximately `265.8x38`, Summary measured `297.8x92`, and
  `Validate and preview` measured `299.8x40`; no adjacent overlap or
  document-level horizontal overflow was measured.
- This advances P02 only as `partial_local_evidence`. Mobile-sidebar route
  choices, every record-kind field set, pointer misactivation, and controls
  revealed by all Advanced disclosures were not fully exercised and are not
  promoted to `passed_direct`.

Evidence boundary:

- The run found no new implementation defect beyond K01, K04, and K05 from the
  preceding direct keyboard audit.
- Priority 7 remains incomplete. The proposed K01/K04/K05 remediation still
  requires design approval; Z01-Z03 require a true browser-zoom environment;
  forced colors, reduced motion, screen-reader tasks, stable `main` landmark,
  phone keyboard, and remaining P02 coverage remain open.

## 2026-07-27 Monitor keyboard and landmark continuation

Run metadata:

- Run ID: `a11y-2026-07-27-monitor-landmark-03`.
- Commit: `1a8727706595f87df459eeb5c7c762dafad83577`.
- Route base: local `http://localhost:8501/`.
- Environment: macOS `26.5.1` build `25F80`; Google Chrome
  `150.0.7871.182`; CSS viewport `3440x1208`; device-pixel ratio `1`;
  default colors and motion.
- Input: direct Chrome `Tab` and `Shift+Tab` keyboard input plus read-only
  accessibility-role inspection. Screen reader: `not_run`. Reviewer:
  `Local supervised browser review`.
- The run used saved readiness only. It performed no refresh, readiness
  rebuild, authoring input, research-record save, screenshot capture, or
  generated-artifact write.

Direct task results:

- K08: `passed_direct` for the recorded current Monitor state. Forward
  keyboard traversal reached the Research Discipline table controls and
  accessible canvas text, the truthful no-change state, the explicit
  `This is a monitoring state, not a stock ranking` boundary, the
  `Open Discover` next action, and the Advanced disclosures. The weekly
  summary reported `0 traceable items`; no fabricated change or ranked
  company was presented.
- K09: `failed_reproducible`. Forward traversal wrapped back to the first
  control and fourteen direct `Shift+Tab` steps reversed through the same
  route without a keyboard trap. However, each focused native `summary`
  again exposed computed `outline: none`, so the expected continuously
  visible reverse-focus state did not pass. This is the same focus-contract
  defect recorded under K05, not a separate remediation.
- Stable route-level `main` landmark: `failed_reproducible`. Direct
  accessibility-role inspection returned zero `main` landmarks on Research
  Desk, Discover, ticker-bound AVGO Company Workbench, and Monitor at the
  exact recorded commit. This does not promote screen-reader task S02, which
  remains `not_run`.
- C01-C02 and M01: `blocked_environment`. Both connected local browser
  surfaces reported forced colors and reduced motion inactive and exposed
  viewport control only; neither exposed a supported media-emulation or
  platform-mode control. Default-mode inspection cannot substitute for the
  named forced-colors or reduced-motion tasks.

Evidence boundary:

- This run extends direct desktop keyboard evidence only. It is not phone
  keyboard, screen-reader, forced-colors, reduced-motion, independent-human,
  hosted, or WCAG-conformance evidence.
- The pending narrow remediation still covers the first-focus skip placement,
  ticker-specific Discover action names, and native-summary focus visibility.
  A stable semantic `main` remains a separately named open design problem.
- Priority 7 remains incomplete. K06-K07, complete K05, phone keyboard, true
  zoom, forced colors, reduced motion, S01-S07, the stable `main` fix, and
  remaining P02 coverage still require direct evidence or remediation.

## 2026-07-27 keyboard authoring validation and no-write exit

Run metadata:

- Run ID: `a11y-2026-07-27-authoring-k06-k07-04`.
- Commit: `b1dd457b574045c06496fdf4ec6772dddfc7d751`.
- Route base: local
  `http://localhost:8501/?mode=research&page=workbench&ticker=AVGO&open=1`.
- Environment: macOS `26.5.1` build `25F80`; Google Chrome
  `150.0.7871.182`; default colors and motion.
- Input: direct Chrome keyboard input. Screen reader: `not_run`. Reviewer:
  `Local supervised browser review`.
- The run used saved readiness only. It entered no research content, produced
  no valid preview, saved no record, captured no screenshot, and wrote no
  generated artifact.

Pre-run ledger state:

- `data/research_thesis_journal.csv` existed with one header line and SHA-256
  `0c427c359c1bdb6d8c8410aece9b3a46831ffb9ccd91d401aeb7930b5f401717`.
- `data/catalyst_evidence.csv` and
  `data/research_outcome_reviews.csv` did not exist.

Direct task results:

- K06: `failed_reproducible`. Enter opened
  `Add a reviewed research record`. Nine direct Tab steps traversed Record
  type, every empty thesis field, Supersedes Entry Id, and
  `Validate and preview`; every inspected control had the shared visible
  three-pixel focus outline. Enter on the validation button produced
  `thesis_id is required` inside one `role="alert"` and exposed no
  `Confirm and save` button. However, the affected Thesis Id control had no
  `aria-invalid`, `aria-describedby`, or `aria-errormessage`, and focus
  remained on `Validate and preview`. The global alert is bounded positive
  evidence but does not satisfy the required affected-control association or
  screen-reader announcement.
- K07: `passed_direct`. Keyboard activation of the selected Company Workbench
  route radio followed by Arrow Down opened Monitor, retained active focus on
  the selected Monitor route, and rendered the truthful Monitor state without
  a trap. After exit, the thesis journal line count and SHA-256 were unchanged,
  the catalyst and outcome ledgers remained absent, and no ledger path was
  dirty.

Evidence boundary:

- This run does not pass S06 or S07 because no screen reader was used.
- The required K06 remediation is field-level invalid-state and error
  association, followed by direct keyboard and supported screen-reader
  retesting. Confirmation and persistence must remain unavailable for a
  rejected draft.
- Priority 7 remains incomplete. K01, K04-K06, K09, phone keyboard, true zoom,
  forced colors, reduced motion, S01-S07, stable `main`, and remaining P02
  coverage still require remediation or direct evidence.

## 2026-07-27 phone keyboard and mobile-sidebar continuation

Run metadata:

- Run ID: `a11y-2026-07-27-phone-keyboard-05`.
- Commit: `c748b192dd4fe27f1c17f2feba07eaccd24e4619`.
- Route base: local `http://localhost:8501/`.
- Environment: macOS `26.5.1` build `25F80`; Google Chrome
  `150.0.7871.182`; explicit CSS viewport `390x844`; device-pixel ratio `1`;
  default colors and motion.
- Input: direct Chrome keyboard input plus read-only target geometry.
  Screen reader: `not_run`. Reviewer: `Local supervised browser review`.
- The run used saved readiness only. It entered no research content, produced
  no authoring preview, saved no record, captured no screenshot, and wrote no
  generated artifact.

Direct task results:

- K01 phone: `failed_reproducible`. After reload, the first focus sequence was
  Workspace help at approximately `x=-202`, the selected Workspace radio at
  `x=-271`, the selected route radio at `x=-271`, the Streamlit main section,
  then the visible `Skip to page answer` link. The first three controls were
  in the closed off-canvas sidebar and could not expose perceivable focus in
  the `390px` viewport.
- K02 phone: `passed_direct` on ticker-bound AVGO Company Workbench. Enter on
  the visible skip link retained `mode=research`, the Workbench route,
  `ticker=AVGO`, and `open=1`, appended only `#public-page-answer`, and moved
  focus to the answer target.
- K03 phone: `failed_reproducible`. Arrow Down on the off-canvas selected
  route radio changed the URL and rendered Discover, but the focused radio
  remained at approximately `x=-271`. The route was keyboard-operable but did
  not satisfy visible focus. The framework sidebar-open control measured
  `0x0`, was hidden, and did not occur in the recorded Tab sequence.
- K04 phone: `failed_reproducible` for the same identity defect as desktop.
  Keyboard input reached the visible `334x36` search control, entered and
  applied `AVGO`, and opened the correct ticker-bound Workbench from an
  approximately `86x44` action. The action's accessible name remained only
  `Open review`; the preceding Advanced summary also repeated the
  no-visible-outline defect.
- K05/K09 phone: not rerun end to end. The directly encountered focused
  Advanced summary again had computed `outline: none`; no broader pass is
  inferred.

P02 mobile-sidebar result:

- P02: `failed_reproducible` for the mobile sidebar route choices. Research
  Desk, Discover, Company Workbench, and Monitor labels measured approximately
  `104x50`, but all target boxes began at `x=-279` and ended left of the
  visible viewport. The hidden `0x0` sidebar-open control provided no visible
  pointer or keyboard entry to those choices.
- Visible main-route controls inspected in this run retained at least `24px`
  on each measured target dimension, and Company Workbench retained
  `document.scrollWidth == document.clientWidth == 390`. These bounded
  positives do not override the off-canvas route-choice failure.

Evidence boundary:

- The new defect is mobile navigation visibility, not route-state logic:
  off-canvas arrow navigation changed routes deterministically, but users
  cannot rely on an invisible focused control.
- Remediation requires a visible, labelled, keyboard-operable mobile route
  navigation entry plus direct keyboard and pointer retesting. It must not
  duplicate route state, change research readiness, or move technical
  evidence into the primary answer.
- Priority 7 remains incomplete. K01, K03-K06, K09, mobile navigation P02,
  true zoom, forced colors, reduced motion, S01-S07, stable `main`, and
  remaining disclosure-state coverage still require remediation or direct
  evidence.

## 2026-07-28 narrow-remediation direct browser gate

Run metadata:

- Run ID: `a11y-2026-07-28-narrow-remediation-gate-07`.
- Product-under-test commit:
  `0000c97e7db17e5d4353e30e976f2b7dec6bfd46`.
- Command: `make research-accessibility-browser-check`.
- Environment: macOS arm64; local Streamlit demo profile; Google Chrome at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`; Playwright
  headless browser control.
- Routes: Research Desk, Discover, ticker-bound NVDA Company Workbench, and
  Monitor.
- Viewports: desktop `1280x720` and phone `390x844`.
- The gate starts one local demo-profile server, reads the rendered DOM, and
  returns results in memory/stdout. It does not write timing, JSON, report,
  screenshot, readiness, canonical-data, or research-ledger artifacts.
- Before attributing the run, the gate verified the rendered Stock Research
  Command Center identity and `Demo` profile, verified a clean
  product/code/test/docs tree, and classified and excluded exactly 18 unstaged
  generated CSV/output paths under the existing hygiene contract.

Direct automated results:

- All eight route-and-viewport cases passed with no rendered traceback and
  zero horizontal overflow.
- K01/K02 retest: after initial focus was cleared, one physical Tab focused
  the sole `Skip to page answer` link. No DOM-order enumeration or
  programmatic link focus substitutes for that keyboard result. Its focused
  box was approximately `x=8.8..141.4`, `y=8.8..47.0`, fully within both the
  horizontal and vertical bounds of each viewport. Enter activation retained
  the complete route query, appended only `#public-page-answer`, and focused
  that target.
- K03/P02 narrow-navigation retest: every route exposed one visible
  `Personal research workflow` navigation with one current route. Research
  Desk, Discover, and Monitor exposed the three applicable routes; the
  ticker-bound Workbench additionally exposed Company Workbench. Every
  applicable route link was fully inside the horizontal viewport and at least
  `44px` high. Desktop navigation began at approximately `y=24`; phone
  navigation began at approximately `y=22.4`, and its links wrapped without
  leaving the viewport.
- K04 retest: Discover rendered four actual eligible actions in the demo
  profile at each viewport. Every action used a unique
  `Open {TICKER} review` accessible name that matched its ticker-bound
  destination. The gate fails when zero eligible actions render and does not
  assume or fabricate a row count.
- K05/K09 retest: the directly focused native disclosure summary on every
  route and viewport exposed a solid `3px` outline with color
  `rgb(15, 118, 110)`.
- K06 retest: empty thesis validation on Company Workbench retained one
  global `thesis_id is required` alert, applied `aria-invalid=true` and one
  stable `aria-describedby` target to Thesis Id, rendered the adjacent error,
  and focused the affected field. A live draft change then removed the
  bridge-owned Thesis Id error node and relationships. The next validation
  associated, described, and focused only Effective At for
  `effective_at is required`, on both desktop and phone. AppTest additionally
  verified cleanup payloads for accepted preview and non-field errors while
  preserving all three ledger byte states. No confirmation action or ledger
  write was performed.

Evidence boundary:

- This is reproducible local engineering evidence from automated direct
  browser control. It is not an independent human keyboard review,
  screen-reader result, hosted result, or WCAG conformance claim.
- A non-loopback or rendered-identity/profile-mismatched server, staged path,
  dirty non-generated implementation path, or absent Chrome/Playwright runtime
  fails the gate closed. Such a run receives no local commit/profile
  attribution. The gate records no generated evidence file; terminal output
  is intentionally ephemeral.
- True 200%/400% browser zoom, forced colors, reduced motion, supported
  screen-reader navigation, complete loading/empty/withheld/stale/failure
  states, independent human testing, and the separately designed stable
  semantic `main` landmark remain incomplete. Priority 7 therefore remains
  open.

## 2026-07-28 framework-safe semantic-main browser gate

Run metadata:

- Run ID: `a11y-2026-07-28-semantic-main-gate-10`.
- Product-under-test commit:
  `d1328eaa4d08cf08ec2b70939e4e031ee5f907b0`.
- Commands:
  `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest
  tests/test_research_accessibility_browser_gate.py -q` and
  `make research-accessibility-browser-check`.
- Focused result: `22 passed`.
- Environment: macOS arm64; local Streamlit demo profile; Google Chrome at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`; Playwright
  headless browser control.
- Routes: Research Desk, Discover, ticker-bound NVDA Company Workbench,
  Monitor, Research Data Health, and Research Proof History.
- Viewports: desktop `1280x720` and phone `390x844`, for 12
  route-and-viewport results.
- Before attributing the browser run, the gate verified the rendered Stock
  Research Command Center identity and `Demo` profile, verified a clean
  product/code/test/docs tree, and classified and excluded exactly 18
  unstaged generated CSV/output paths under the existing hygiene contract.

Direct automated results:

- The gate verdict was `passed`, with an empty failure list and all 12
  route-and-viewport results passing.
- Every initial route DOM exposed exactly one role-based `main` with exact
  `role="main"`, `id="research-main"`, and
  `aria-label="Stock research workspace"`. That unique landmark contained
  exactly one `#public-page-answer` and exactly one level-one heading, and the
  host status was exactly
  `data-research-main-bridge-status="applied"`.
- Each case activated the exact unselected `Public visitor mode` Workspace
  radio through a controlled native DOM event. The installed Streamlit
  `1.59.2` test-state contract recorded a complete
  `notRunning` -> `running` -> `notRunning` script cycle while retaining the
  same top document, recording zero top-level frame navigations, and
  preserving the exact pathname and query.
- After that same-document cycle, the gate required the bridge target to be
  the current connected `stMain`. It changed the host status to a probe value
  and appended one hidden, `aria-hidden` inert node beneath that target; the
  active bridge observer had to restore the exact `applied` status before the
  probe node was removed. The gate then repeated the exact route heading,
  landmark count, metadata, answer-target count, heading count, and applied
  host status. Research Data Health and Research Proof History additionally
  proved the intentional absence of the primary
  `Personal research workflow` navigation before and after the script cycle.
- Separately from that same-document proof, each case navigated to its
  explicitly mapped different Research route and then back to the exact
  original route. After marker, DOM-stability, and exact route-H1 waits, the
  gate required the full URL to match exactly, including the complete query
  string and empty fragment, with the ticker parameter where present. It
  repeated the exact semantic-main and runtime assertions on both the away
  and returned DOMs, required the correct primary workflow navigation where
  applicable, and explicitly required its absence on secondary evidence
  routes.
- The existing primary-route assertions remained active. After initial focus
  was cleared, one physical Tab focused the sole skip link; Enter preserved
  the route and focused the one `#public-page-answer`, and that focused target
  was inside the unique main. Primary workflow navigation geometry, summary
  focus outline, Discover action names and destinations, and Workbench
  field-error association and cleanup also passed where applicable.
- All 12 cases reported no browser console error, uncaught page error,
  rendered traceback, or document-level horizontal overflow. Traceback and
  overflow checks were repeated after the same-document Streamlit script
  cycle, observer-liveness probe, away transition, and exact-route return.
- The fixed same-origin bridge accepts no research-content input and performs
  no application action. The gate triggers only the controlled Workspace
  widget rerun and inert observer probe before deliberately navigating to one
  deterministic away route and back for transition evidence. It performs no
  research-data write or persistence action and remained repository/data
  read-only and in-memory/stdout-only: it wrote no screenshot, timing, JSON,
  report, readiness, canonical-data, research-ledger, or generated repository
  artifact.

Evidence boundary:

- This closes the stable route-level semantic-main defect only for the
  recorded local automated DOM matrix at the exact implementation anchor.
  It does not establish assistive-technology behavior beyond those DOM
  assertions.
- Automated DOM verification is not WCAG conformance, screen-reader landmark
  navigation or usability, hosted behavior, independent-human accessibility
  validation, or complete keyboard-order evidence.
- The native DOM radio activation and Streamlit test-state transition are
  controlled framework engineering evidence only. They do not prove pointer,
  keyboard, or closed-mobile-sidebar operability, and the installed runtime's
  test-state attribute is not a public cross-version compatibility guarantee.
- True 200%/400% browser zoom and reflow, forced colors, reduced motion,
  supported screen-reader tasks, dynamic announcements, complete
  loading/empty/withheld/stale/failure states, remaining small framework
  controls, and independent-human testing remain incomplete. Priority 7
  therefore remains open.

## 2026-07-29 same-document transport behavior and instrumentation

Verified implementation evidence:

- Product-under-test commits:
  behavior-first repair `e8084099b3ea1b794ce8e2a0af00998602133084`;
  exact transport-instrumentation run
  `d68ab27bee9c07c450faeb866b08cbf13638b56f`.
- Supported dependency contract: `streamlit>=1.52,<2`; installed local
  runtime: Streamlit `1.59.2`.
- Direct command: `make research-accessibility-browser-check`.
- Environment: macOS arm64; local `Demo` profile; Google Chrome at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- Routes: Research Desk, Discover, ticker-bound NVDA Company Workbench,
  Monitor, Research Data Health, and Research Proof History.
- Viewports: `1280x720` and `390x844`, for 12 route-and-viewport results.
- Result: `passed`, with an empty failure list. Repository hygiene classified
  and excluded exactly 18 unstaged generated CSV/output paths.

The direct run proved that the behavior-first `st.html` correction retained
one applied same-document main landmark, one contained answer, exact route H1,
skip focus and activation, exact query retention, rerun and mutation recovery,
away-and-return route recovery, Workbench Thesis Id cleanup and Effective At
rebinding, zero browser error, and zero horizontal overflow across the
recorded matrix. It supersedes the earlier iframe-topology failure only for
this exact local runtime and commit.

The browser gate now also has fail-closed per-result fields for
`deprecated_component_warning_count`, `bridge_iframe_count`,
`bridge_focusable_count`, and `bridge_height`. Focused tests first failed
because the evaluator and live-DOM observation did not exist, then returned
`33 passed` after implementation and review hardening. Counts accept only
exact nonnegative integers; booleans, fractional values, negative values, and
strings fail closed. The normal gate-owned local server retains a bounded
in-memory stdout/stderr tail and increments the deprecation counter during
streaming against the full normalized line, before line-length truncation or
old-line eviction; lock-protected snapshots avoid reader/route races. Reader
exceptions and a reader still alive after the bounded shutdown join change
capture status to explicit failed/incomplete states, which fail the overall
verdict. An alive reader is not synchronously closed after timeout because a
shared `TextIOWrapper` lock could block the gate; normal and exception readers
that have stopped are closed. That exact count is combined with browser console and rendered
messages. Explicit `BASE_URL` mode reports
server output as `unavailable_external_base_url` and cannot receive a strict
passing transport verdict. `make research-dashboard-render-smoke`
passed all six Research routes without the former
`st.components.v1.html` deprecation warning.

The clean exact-head run at `d68ab27bee9c07c450faeb866b08cbf13638b56f`
closed the local transport-instrumentation evidence item. All 12
route-and-viewport results reported
`deprecated_component_warning_count=0`, `bridge_iframe_count=0`,
`bridge_focusable_count=0`, and `bridge_height=0`; each result recorded
`server_runtime_output_status=captured_local_server`. The overall bounded
server stdout/stderr evidence also passed with zero deprecated-component
warnings. The same run had an empty failure list and excluded the same 18
generated paths. The surrounding verification returned 4,381 passing tests
and passed dashboard, Research render, public wording, public package,
commercial-beta, pilot-readiness, hygiene, and whitespace gates.

Hosted exact-head CI remains separate and must be reverified after the
intentional push. The local result does not expand the evidence boundary below.

Evidence boundary:

- The bridges execute fixed local scripts only and do not read research
  content, change readiness, persist a record, or perform a research action.
- No generated data, screenshot, JSON, report, or timing artifact was created
  by these checks.
- This is local automated engineering evidence, not screen-reader, WCAG,
  hosted, cross-major-version, independent-human, or market validation.

## 2026-07-29 research-state implementation and environment-limited gate

Current local implementation evidence:

- A closed five-transition helper maps validation rejection and reload
  uncertainty to assertive alerts, and preview readiness, edited drafts, and
  verified reloads to polite statuses.
- Company Workbench authoring uses exact profile, ticker, record kind, receipt
  or digest, and persisted record identity to deduplicate transitions. The
  same state remains visible on a normal rerender without another live node.
- Focused pure and authoring tests passed for escaping, deterministic identity,
  required-field association, preview-unsaved wording, edited-draft recovery,
  verified reload, reload uncertainty, and temporary-ledger isolation.
- A synthetic AppTest harness now covers six ordinary static states and all
  five transitions using the production renderer and TEST1-only content.
- The final surrounding full suite reported 4,424 passing tests and one existing
  skip. Its only two failures were environment failures: the managed sandbox
  rejected loopback socket binding before the two direct browser tests could
  start.

Evidence boundary:

- Implementation commit `d353ed652` contains the 18-file product package.
  Exact staged hygiene reported 18 product/code/docs/test files, zero generated
  files, zero canonical-data files, and zero manual-review paths.
- The browser gate now runs the harness at both viewports, rejects duplicate or
  hidden live nodes, verifies unchanged rerenders become visible non-live
  messages, checks overflow/errors/tracebacks, and compares repository status
  byte-for-byte before and after. Discover three-answer rows and Monitor
  process-only semantic tables now have direct browser assertions too. Its
  repository fingerprint includes Git status plus current content for every
  tracked dirty and untracked path, so another write to an already-modified
  generated file also fails the gate.
- The final focused browser/state/dashboard/document contract run passed 1,220
  tests; all six Research routes also passed the non-browser render smoke.
- The clean-tree gate verified product hygiene and excluded exactly 18
  unstaged generated paths. The environment then terminated headless Chrome
  before any route or synthetic-harness case executed, so no desktop/phone
  result is credited.
- A supported direct browser run, push, draft-PR update, and exact-head CI
  remain open.
- No production research ledger or generated CSV, JSON, report, screenshot, or
  timing artifact was written by the candidate tests.
- This is not screen-reader, WCAG, hosted, independent-human, or market
  validation evidence.
