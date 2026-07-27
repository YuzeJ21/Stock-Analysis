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
