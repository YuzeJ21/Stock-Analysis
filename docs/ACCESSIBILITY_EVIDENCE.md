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

## 2026-07-27 narrow-remediation direct browser gate

Run metadata:

- Run ID: `a11y-2026-07-27-narrow-remediation-gate-06`.
- Product-under-test commit:
  `94e469b0948a441ac54d130741185812179a1117`.
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

Direct automated results:

- All eight route-and-viewport cases passed with no rendered traceback and
  zero horizontal overflow.
- K01/K02 retest: exactly one `Skip to page answer` link was first in the
  visible application focus order. When focused, its horizontal box was
  approximately `x=8.8..141.4`, fully within both viewports. Enter activation
  retained the complete route query, appended only
  `#public-page-answer`, and focused that target.
- K03/P02 narrow-navigation retest: every route exposed one visible
  `Personal research workflow` navigation with one current route. Research
  Desk, Discover, and Monitor exposed the three applicable routes; the
  ticker-bound Workbench additionally exposed Company Workbench.
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
  and focused the affected field. No confirmation action or ledger write was
  performed.

Evidence boundary:

- This is reproducible local engineering evidence from automated direct
  browser control. It is not an independent human keyboard review,
  screen-reader result, hosted result, or WCAG conformance claim.
- Browser-runtime absence fails the gate closed. The gate records no generated
  evidence file; terminal output is intentionally ephemeral.
- True 200%/400% browser zoom, forced colors, reduced motion, supported
  screen-reader navigation, complete loading/empty/withheld/stale/failure
  states, independent human testing, and the separately designed stable
  semantic `main` landmark remain incomplete. Priority 7 therefore remains
  open.
