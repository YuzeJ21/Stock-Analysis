# Dashboard QA Notes

This file records lightweight browser QA evidence for public-facing dashboard polish.

## 2026-08-11 Calm Institutional Workspace acceptance contract

Personal Research now has one in-content workflow navigation for Research Desk,
Discover, Company Workbench, and Monitor. The same DOM becomes a compact desktop
rail and a wrapped phone grid; its Workspace mode disclosure replaces the
retired sidebar selector. Public uses one explicit five-step workflow nav.
Operator alone retains native sidebar workspace and route controls, and its
operator or compatibility warning precedes detail. Canonical mode isolation
fails disallowed links closed while preserving permitted ticker/evidence state.

Final local acceptance requires one ordered 15-route x 3-viewport x 2-zoom,
90-cell matrix at `1280x720`, `1440x1024`, and `390x844`, with 100% and 200% zoom.
Each result records structured region/control geometry, an idle `notRunning`
Streamlit state, console/page errors, and the bounded commit/worktree snapshot.
Passing automation remains engineering evidence only, not data freshness, source
rights, hosted behavior, WCAG conformance, independent review, or market validity.

At implementation anchor `2bc374ab8`, the clean read-only accessibility browser
gate passed all six routes at `1280x720` and `390x844`. It verified the labelled
top navigation on the four primary routes, exact route/H1/main identity, skip
focus, same-document rerun and away/return route preservation, forced-colors and
reduced-motion signals, route-owned primary answer markers, no horizontal
overflow, no browser or runtime errors, and unchanged repository state. The
same 18 generated data/output modifications were excluded. This is automated
local engineering evidence only, not independent-human, screen-reader, WCAG,
hosted, or market validation.

## 2026-08-05 Research Desk Today's Brief

Research Desk now renders one primary **Today's Research Brief** instead of a
weekly-card row plus four overlapping question cards. The brief asks **What
needs my attention today?**, gives one saved-evidence answer and reason, exposes
the saved-readiness warning, and provides one Monitor-or-Discover action. Its
stop rule says the answer is saved-workspace evidence rather than a
market-complete event feed, recommendation, or trade instruction. Weekly,
cohort, observation, coverage, and source-change detail remains available under
collapsed **Advanced Evidence**.

At implementation anchor `5a2aaf2a44dc7ae371161bb8642ab7f0755ad019`, the
read-only accessibility browser gate passed all six Research routes at
`1280x720` and `390x844`. The Desk brief and action were visible in normal,
forced-colors, and reduced-motion observations; the route had no horizontal
overflow, browser error, rendered traceback, or repository write. The gate
classified and excluded the same 18 generated data/output modifications. This
is local automated engineering evidence only, not independent-human,
screen-reader, WCAG, hosted, or market validation.

## 2026-08-05 Monitor Follow-up Queue

Exact local runtime anchor `199fa94b266a8bb325bfc4a4df1742158282d47a`
passed the automated direct-browser gate at `1280x720` and `390x844` across all
six Personal Research routes. Monitor exposed five visible labels — **SINCE LAST
REVIEW**, **NEEDS VERIFICATION**, **WAITING ON EVIDENCE**, **SCHEDULED CONTEXT**,
and **EVIDENCE FRESHNESS** — in a desktop two-column grid and a phone one-column
layout. The old Evidence Monitor Brief, Research Discipline Review, and Research
change monitor no longer compete as separate primary summaries. A controlled
empty state appears once, preserves the external-event boundary, and exposes
one Open Discover action. Complete stable-order process rows, identities, and
source-change evidence remain available in **Advanced: Monitor evidence**.
Neither viewport had horizontal overflow, a rendered traceback, console/page
errors, or server runtime errors. The same 18 protected generated working-tree
paths remained unchanged and unstaged after the gate.

This is automated local engineering evidence only. It does not establish human
or screen-reader accessibility, source rights, current-market validity, hosted
operation, independent workflow validation, probability calibration, or market
validation.

## 2026-08-01 Company Workbench HTML Research Brief

Open `?mode=research&page=company-workbench&ticker=<ticker>` with an explicit selected
ticker. Company Workbench displays **Download HTML Research Brief** only after
preparing the same session evidence and Scenario Lab result used by the visible
research answer. The download preserves complete, partial, and withheld states;
unsupported fields remain withheld independently and the brief stays
research-only.

Run `make company-workbench-html-browser-check` for the direct actual-byte
complete/partial/withheld browser, keyboard, responsive, print, media-
preference, PDF-in-memory, CSP, and repository-fingerprint matrix. No HTML, PDF, screenshot, JSON, timing, readiness, canonical-data, or report artifact is written. This command does not refresh data, acquire a source, activate readiness, or establish human/screen-reader accessibility.

This historical pre-fix matrix was recorded on 2026-08-01: commits `b10ebcfbd`, `923fa850e`, `9ce1a6ce4`, `84562a7f6`, and `8218af401` passed the 101-test HTML-browser matrix, while the six modal-passive reproductions were withheld. It is not current-head evidence. Exact-head repair evidence: commit `b69badfc80424d3a97fae5f77706aa6ed1533167` passed the 5,828-test full suite, the required dashboard, render, HTML, accessibility, public, and hygiene gates, branch/PR synchronization, and exact-head GitHub Actions run `30726301045`. This remains automated engineering evidence only and does not establish human or screen-reader accessibility.

Local engineering evidence does not establish source rights, current-market data, readiness activation, a new or professional line-item model, hosted operation, human or screen-reader conformance, independent validation, market fit, screening alpha, or probability calibration.

## 2026-07-18 Personal Research Evidence Detour Continuity

Read-only AppTest coverage now verifies six Personal Research surfaces: Research Desk, Discover, Company Workbench, Monitor, Research Data Health, and Research Proof History. Data Health and Proof History stay inside Personal Research mode when opened from Company Workbench Advanced Evidence, preserve the selected ticker, and show **Return to Company Workbench** before existing evidence content.

The same-mode detour does not change readiness or evidence state, add a route, expose Operator commands, refresh data, record a review outcome, or treat Proof History as an unlock. The active continuation contract prohibited new screenshots, so this pass proves route and render continuity only; it does not prove visual spacing, focus order, contrast, assistive-technology behavior, hosted behavior, or accessibility compliance.

## Company Workbench Authoritative Task Contract

Company Workbench renders one overall `ONE NEXT TASK` card. The change-answer contract explicitly distinguishes `none`, `snapshot_only`, and `source_backed`: no matching change renders a neutral no-queued-change badge, snapshot-only context renders only its own badge, and eligible source-backed context renders the source-backed badge. A change can win only when its answer also carries strict source-backed eligibility. Open items keep their suggested review task; still-blocked and intentionally deferred items preserve their existing wait and monitor routing plus the recorded wait condition. Forward View keeps lane-specific guidance and is not a competing overall task. This composition does not alter readiness or evidence states, which remain independent.

A focused Streamlit AppTest regression renders the normal AVGO Company Workbench route with zero exceptions, a scoped no-queued-change Evidence Change card without a snapshot-only badge, exactly one `ONE NEXT TASK` marker, the current peer-evidence priority `Add peer mappings`, and one `FORWARD-VIEW LANE UNBLOCK` marker. It rejects the retired uppercase `NEXT RESEARCH TASK` kicker while retaining the established title-case `Next Research Task` section heading. This is deterministic local render evidence only, not current-data, source-rights, hosted, or visual-browser evidence.

## Readiness Continuation Gate

When the selected profile is stale, incomplete, unverified, or current but untracked, the readiness continuation gate makes `make readiness-preview TOP_N=20` the only continuation-safe action. Project-status next steps are suppressed, while provider setup details, coverage rankings, scheduled-operation details, and Advanced Data Health cards remain planning context only. Advanced Data Health cards derive the gate from the selected profile even when their cached preflight predates the gate. After explicit source and artifact authorization, `CONFIRM_MATERIALIZE=1 make readiness-materialize PROFILE=<default|demo|local>` may create an ignored local snapshot; release eligibility is separately checked with `make readiness-release-review TOP_N=20`, recorded with `make readiness-release-record ...`, and enforced with `make readiness-release-guard RECORD_ID=<record_id>`. The UI and CLI must not imply that preview refreshes data, makes saved readiness current or tracked, or authorizes source execution.

## 2026-07-18 Monitor Answer-First Live Review

The default-profile Monitor route was reviewed before and after the hierarchy
change at `1280x720` and `390x844`. Before the change, five-company Earnings
Nowcast readiness interrupted the path between the weekly summary and the
actual research-change answer. After the change, the weekly summary is followed
by `Research change monitor`, the neutral empty-queue answer, and one Open
Discover action. Five-company readiness cards and full rows remain unchanged
inside the collapsed `Advanced: five-company Earnings Nowcast readiness`
drawer.

At both widths, no details element was expanded, the technical readiness card
was absent from visible text while Advanced was closed, and the document width
matched the viewport exactly (`1280px` and `390px`). The browser recorded no
errors. The phone review confirmed the answer, Open Discover action, and all
three Advanced drawers in reading order without horizontal overflow. Computed
styles confirmed the primary action and its nested text use a white foreground
on the existing primary-button background; the action measured approximately
`110x40px`.

Reviewed before/after screenshots were saved outside the repository and remain
unstaged. They prove local route hierarchy, responsive reflow, and visible
control styling only; they do not prove current market data, source rights,
hosted behavior, full keyboard or assistive-technology support, or predictive
validity.

## 2026-07-18 Research Desk Answer-First Live Review

The live default-profile Research Desk route was reviewed at `1280x720` and
`390x844`. The workspace boundary and Discover next action were followed by the
weekly research summary, four direct research answers, and the Open Discover
action. Focused-cohort scope, concise lane coverage, full matrices, and weekly
rows remained available inside the existing collapsed `Advanced Evidence`
drawer.

At both widths, no details element was expanded by default and the hidden cohort
cards were absent from rendered visible text. The weekly summary, `What should I
review next?`, Open Discover, and Advanced Evidence remained present. The
document width matched the viewport exactly (`1280px` and `390px`), with no
horizontal overflow, and the browser recorded no errors.

Reviewed screenshots were saved outside the repository in the temporary review
workspace and remain unstaged. They prove local layout and route composition
only; they do not prove current data, source rights, hosted behavior, or
predictive validity.

## 2026-07-18 Company Workbench Answer-First Live Review

The live default-profile Company Workbench route for NVDA was reviewed at
`1280x720` and `390x844`. The route rendered the workspace boundary and one
next action, then kept selected-company lane cards closed under
`Advanced: selected-company lane coverage`. The unchanged selected-ticker
answer remained visible and the full review continued through What Changed,
Business Trend, Valuation, Forward View, What Remains Withheld, Research
Conclusion, and Next Research Task.

At both widths, no details element was expanded by default and the hidden lane
cards were absent from rendered visible text. The document width matched the
viewport exactly (`1280px` and `390px`), with no horizontal overflow. The phone
first view retained the research-only boundary and primary next action before
the selected-company content continued below it.

Reviewed screenshots were saved outside the repository in the temporary review
workspace and remain unstaged. They prove local layout and route composition
only; they do not prove current data, source rights, hosted behavior, or
predictive validity.

## 2026-08-01 Personal Research Workflow Peer-Readiness Review

The live local workflow was reviewed in order through Research Desk, Discover,
AVGO Company Workbench, and Monitor. Research Desk exposed one next action;
Discover kept the empty strict Momentum & Valuation queue separate from its
alphabetical readiness-backed review rows; Monitor preserved process timing as
non-ranking context. The first AVGO Workbench load exposed a contradictory peer
projection: broad peer trend readiness briefly unlocked peer-input wording even
though `peer_valuation_comparison_ready` was false and the settled report
withheld peer-relative valuation.

The selected answer, next-step routing, reader guide, quick read, methodology,
and source audit now use peer-valuation readiness for valuation claims while
retaining independently ready peer-trend context. A fresh server session showed
the same fail-closed AVGO answer before and after the saved report settled:
standalone DCF reviewable, peer trend context separately available, and
peer-relative valuation still withheld. Audit screenshots remain under
`/tmp/stock-research-workflow-audit-2026-08-01` and are not repository evidence.
This local review does not prove source rights, current data, hosted behavior,
human accessibility, independent understanding, or predictive validity.

## 2026-07-18 Discover Answer-First Live Review

The live demo-profile Discover route was reviewed from the selected worktree at
`1280x720` and `390x844`. In both viewports, the Personal Research header and
research-only boundary are followed directly by `Which stock can I review?`,
the readiness-backed search control, and the existing Company Workbench actions.
Focused-cohort scope and lane-coverage cards now remain closed under
`Advanced: cohort readiness context` after the selection task.

The phone viewport reported a `390px` document width at a `390px` viewport,
with no horizontal overflow and no details element expanded by default. The
selector remained limited to the same deterministic cohort, and its links
continued to target Company Workbench in Personal Research mode. This was a
presentation-order change only; no readiness, data, ranking, or route contract
changed.

Reviewed screenshots were saved outside the repository in the temporary review
workspace and remain unstaged. They are product-layout evidence only;
they do not prove data freshness, source rights, hosted behavior, or predictive
validity.

## 2026-07-17 Commercial Beta Research Workflow Live Review

The live local Streamlit app was reviewed in the in-app browser at `1280x720`
and `390x844` across Research Desk, Discover, Company Workbench, and Monitor.
Each route rendered from the selected worktree, kept the research-only boundary
visible, preserved one next action, kept Advanced evidence closed, and showed no horizontal overflow at either viewport.

The first settled Company Workbench review exposed a real `ArrowInvalid`
failure when immutable Forward View evidence reached the display table. The
display adapter now serializes that immutable nested evidence into deterministic
JSON text. A fresh server restart and repeat NVDA review completed through
Research Conclusion and Next Research Task without traceback text. Focused and
full tests plus the dashboard and public gates cover the corrected contract.

This live review is product evidence only. It does not prove hosted behavior,
data freshness, licensed commercial source operation, external reviewer
success, or predictive validity. No screenshot from this session is committed;
generated capture output remains excluded.

## 2026-07-11 Public Workflow Modernization

The current public first-view contract is intentionally simpler than older
captures and historical notes below:

- Home: one readiness-first answer, `Start with Stock Selector`, and the
  `No data, no conclusion` boundary.
- Stock Selector: a direct `Search this review queue` control before optional
  filters and compact review rows.
- Single-Stock Report: selected ticker, `Use now`, `Still withheld`, and one
  `Open Data Health` handoff before detailed sections.
- Data Health: four comparison rows that state usable scope, coverage, and one
  blocker per lane before Advanced details.
- Proof History: latest evidence first; the raw proof ledger remains under
  Advanced.

Real screenshots remain product evidence only. Existing assets may show older
copy; recapture in a normal local browser before using an image as proof of
exact current wording.

## Current Screenshot Evidence Status

| Evidence | Status | Use |
| --- | --- | --- |
| `docs/assets/linkedin-public-dashboard.png` | Ready | GitHub/LinkedIn thumbnail from the real public dashboard. |
| `docs/assets/public-demo-home-real.jpg` | Ready | README first-screen product preview. |
| `docs/assets/operator-data-health-metrics-real.jpg` | Ready | Operator metrics lane proof that Data Health is readiness-gated and copy-only. |
| `docs/assets/single-stock-workflow-fit-real.jpg` | Ready | Public single-stock workflow proof with selected-ticker readiness, usable-now scope, blocked inputs, and one next step. |
| `docs/assets/operator-data-health-proof-real.jpg` | Ready | Operator proof-lane screenshot showing progressive proof detail rather than raw tables first. |
| `docs/assets/operator-data-health-queue-routing-real.jpg` | Ready | Operator queue drawer routing proof from source proof to comparison, proof record, and artifact hygiene. |

Screenshot evidence is product evidence only. It does not refresh data, apply imports, unlock blocked fundamentals, peers, earnings, analyst estimates, valuation inputs, or prove current readiness counts.

## 2026-07-21 Public Desktop And Phone Workflow Review

A fresh local review covered all five public pages—Home, Stock Selector,
Single-Stock Report, Data Health, and Proof History—at desktop and `390x844`
phone viewports. Every page passed its current review with its first answer and
primary handoff visible, Advanced/raw detail collapsed, no horizontal overflow,
and no traceback.

Only the Single-Stock Report needed a later regression correction. Its
direct-open loading state placed three large quick-read cards before the
evidence handoff even though the completed report used the compact answer.
The loading state now renders the same compact selected-ticker answer before
provider and report work, preserving Selected ticker -> `Use now` -> `Still
withheld` -> `Open Data Health`. Browser measurement at `390x844` verified the
44px handoff fully inside the viewport with at least 50px of bottom clearance,
no horizontal overflow, and no traceback. Desktop remains a four-column layout
with the same handoff visible.

### 2026-08-02 Complete Stop-Rule Follow-Up

A current-head recapture found a narrower follow-up regression: the 44px
handoff still fit, but the complete two-line research-only stop rule ended
27.9px below the `390x844` first viewport. The phone action block inherited
both its desktop grid gap and stop-rule top margin, and the selected-ticker
summary still inherited its desktop top margin. Commit
`34b08ea867316ae3683a9a769d1ed37bd62d61ce` removes that duplicate phone-only
spacing without changing copy, reading order, research state, or desktop
layout.

Fresh live phone geometry reported `stop_top=811.4609375`,
`stop_bottom=843.4296875`, `stop_clearance=0.5703125`,
`action_height=44`, `action_clearance=78.8203125`, and `scroll_width=390`.
The viewport was exactly `390x844`; Advanced details open count was zero and
no traceback was visible.
The summary began 2.2265625px after the trust strip, so the correction did not
overlap the preceding evidence. At `1280x720`, the summary retained four
computed columns (`128px 378.859px 378.859px 303.094px`), the action remained
44px high, `scroll_width=1280`, and no traceback was visible. The live screen
was inspected, but no screenshot file was created. This is local
product-layout evidence only; it does not prove data freshness, source rights,
hosted behavior, accessibility conformance, external review, demand, or market
validation.

### 2026-08-08 Zero-Scroll Supersession

A fresh top-of-page audit supersedes the 2026-08-02 first-viewport conclusion.
The earlier evidence did not record the scroll position, so its
`stop_bottom=843.4296875` result cannot prove that the complete stop rule was
inside the initial viewport. The new audit explicitly recorded
`window.scrollY=0`, document and body scroll offsets of zero, and
`stMain.scrollTop=0`.

At `390x844`, both the archived evidence tree
`60492ffa5475fc00cebbc2d4c2dff0c2b140c467` and audited product head
`2e58e00bb6ddff6791299a514b562c96ce911196` rendered pixel-identical
first-answer geometry in both controlled browser surfaces. The primary action
remained fully visible with `action_top=764.0625`, `action_bottom=808.0625`,
`action_height=44`, and `action_clearance=35.9375`; the complete stop rule
reported `stop_top=854.34375`, `stop_bottom=886.3125`, and
`stop_clearance=-42.3125`. Document width remained `390` with no horizontal
overflow or traceback. The `42.8828125px` difference from the earlier recorded
stop bottom is consistent with an unrecorded scroll offset, but the prior run
did not capture that value and its exact cause is therefore not asserted.

This proves that no later tracked product change introduced the current
failure and that the existing selector-local spacing rules still render as
implemented. It does not prove that the complete safety boundary is visible at
the top of the phone route. The phone result is `blocked_with_evidence` until
an owner-approved responsive repair is implemented and remeasured with an
explicit zero-scroll assertion. No product code, readiness, source, research,
or generated artifact changed during this reconciliation.

### 2026-08-08 Owner-Approved Zero-Scroll Repair

The owner-approved implementation at anchor
`18417d90766e9aeb629eef6bb1ef4fc40805773c` keeps Home's direct answer and the
Single-Stock Report direct-open loading state inside the initial phone
viewport without changing copy or the shared Public shell. The selected answer
still reads Selected ticker -> `Use now` -> `Still withheld` -> `Open Data
Health`, and both primary actions remain 44px high.

Fresh zero-scroll `resolved_post_fix` evidence at `390x844` recorded Home
`stop_bottom=843.609375`, `action_height=44`, and `visible_stops=1`; the one
visible stop rule follows the primary action and precedes metrics in both DOM
and visual order. Single-Stock Report `stop_bottom=836.421875`,
`action_height=44`, and `trust_gap=2.21875`. Both routes recorded
`scroll_width=390`; all four measured scroll offsets were zero, Advanced open
count was zero, and there was no horizontal overflow, no traceback, console
warning, or page error.

At `1280x720`, desktop retained two Home grid tracks and four Single-Stock
Report grid tracks. Home showed only the desktop stop across the second row;
Single Stock preserved its four-column answer; both actions remained 44px and
both routes had zero scroll offsets, matching client/document widths, and no
runtime error. The repair changed no readiness, source, research, or
generated-artifact state and wrote no screenshot, timing, report, or data
artifact.

Data Health and Proof History remain answer/evidence destinations. This review
adds no invented calls to action, does not turn either route into a readiness
unlock, and does not change readiness, source, research, or generated-artifact
state. The earlier screenshots predate this regression fix and remain
historical presentation evidence only; their old measurements do not prove the
corrected loading state. The later result was verified through live browser
layout measurement, and no new screenshot artifact was created. Neither form
of local presentation evidence proves data freshness, source rights, hosted
behavior, accessibility compliance, external reviewer behavior, or predictive
validity.

The review-note gate preserves the corrective history without understating the
finished audit. `resolved` is a direct successful review;
`resolved_post_fix` is a successful fresh recapture after a correction. The
current raw counts are eight `resolved` rows and two `resolved_post_fix` rows,
while the aggregate gate reports `10/10` and `share_review_ready`. Only those
two explicit labels are successful. Unknown labels—including values that merely
start with `resolved`—and deferred, environment-limited, skipped, blocked, or
pending rows remain fail closed. This is screenshot-based local workflow QA,
not WCAG, keyboard, screen-reader, hosted, external-reviewer, freshness, or
market-validation evidence.

## V1 Public UI Replacement QA

This is the current replacement-readiness browser QA contract for the public
workflow. Older dated sections below remain historical evidence for prior
iterations.

Checked public routes:

- Home: `?mode=public&page=home`.
- Stock Selector: `?mode=public&page=stock-selector`.
- Single-Stock Report with ticker query: `?mode=public&page=single-stock-report&ticker=NVDA&open=1`.
- Data Health: `?mode=public&page=data-health`.
- Proof History: `?mode=public&page=proof-history`.

Current replacement criteria:

- V1 header, route rail, research loop, action strip, and workbench cards render consistently across desktop and mobile.
- Stock Selector shows readiness-backed rows with row actions for opening a report or checking proof.
- Single-Stock Report accepts the ticker query and keeps one-ticker review separate from selection.
- Data Health stays source-proof first instead of operator-table first.
- Proof History is an independent public route for proof inspection.
- Public first views have no visible first-viewport raw dataframe, no clipped table text, no incoherent overlap, and no route mismatch.

Boundary checked:

- Browser QA does not refresh data, apply imports, record proof rows, stage files,
  commit, push, or unlock missing fundamentals, peers, earnings, analyst
  estimates, valuation inputs, or metrics.
- The selector is a research queue, not a recommendation list.

Current live-review handoff:

- `make browser-qa-evidence` is the deterministic share gate for committed
  route markers and screenshot assets.
- `make public-check` is the current end-to-end public gate; it includes public
  wording, whitespace, full tests, dashboard smoke, browser QA evidence,
  license boundary, and visitor-demo checks.
- `make public-ux-review-checklist` is the copy-only normal-browser checklist
  for reviewing the five public pages at desktop and phone width before
  replacing screenshots or changing share copy. It now names each page
  question and the matching failure action so reviewers fix the confusing page
  contract before adding sections or routes.
- `make project-status-check` is the no-write status read for review loops;
  use `make project-status` only when intentionally refreshing the
  dashboard-ready status snapshot files.
- The remaining UX task is a normal-browser desktop/mobile pass for
  first-viewport spacing, unclear Data Health wording, and confusing next
  actions.
- Treat in-app browser capture timeouts as environment-limited; keep existing
  real screenshots unless a normal browser shows a route mismatch, traceback,
  raw-table-first view, or missing research-only boundary.

## 2026-07-06 Mobile And Wide-Desktop Public Flow Pass

Checked by the live local Streamlit app, source-level responsive tests, and
phone-width Chrome screenshots saved under
`/tmp/stock-command-center-mobile-audit-20260706`:

- Home: phone-width first viewport shows the public route rail, page answer,
  primary Stock Selector handoff, and research-only stop rule without horizontal
  overflow.
- Stock Selector: phone-width first viewport opens on one readiness-backed
  ticker handoff before filters and avoids raw table or command-heavy detail.
- Single-Stock Report: phone-width first viewport shows selected ticker state,
  readable-now scope, blocked/excluded inputs, and the Data Health handoff before
  detailed report sections.
- Data Health: phone-width first viewport shows one lane answer before proof
  rows, queue drawers, route maps, provider setup, or raw tables.
- Proof History: phone-width first viewport stays evidence-only and keeps raw
  ledger rows collapsed.

Accepted evidence:

- `/tmp/stock-command-center-mobile-audit-20260706/home-mobile.png`
- `/tmp/stock-command-center-mobile-audit-20260706/stock-selector-mobile.png`
- `/tmp/stock-command-center-mobile-audit-20260706/single-stock-mobile.png`
- `/tmp/stock-command-center-mobile-audit-20260706/data-health-mobile.png`
- `/tmp/stock-command-center-mobile-audit-20260706/proof-history-mobile.png`
- `/tmp/stock-command-center-responsive-audit-20260706/01-home-desktop-after-width-cap-ready.png`
- `/tmp/stock-command-center-responsive-audit-20260706/02-stock-selector-desktop-after-width-cap.png`
- `/tmp/stock-command-center-responsive-audit-20260706/03-single-stock-desktop-ready-recheck.png`
- `/tmp/stock-command-center-responsive-audit-20260706/04-data-health-desktop-after-width-cap.png`
- `/tmp/stock-command-center-responsive-audit-20260706/05-proof-history-desktop-after-width-cap.png`

Accepted fix:

- Cap the public Streamlit content width on ultrawide desktop so Data Health lane
  cards stay centered and readable.
- Keep the compact mobile topbar focused on the readiness answer, no-account
  stop cue, and Data Health blocked-input handoff.

Boundary checked:

- These screenshots are product evidence only. They do not prove data freshness,
  apply imports, record proof rows, or unlock blocked source inputs.
- Generated CSV/report/sample-report churn stayed excluded from staging.

## 2026-07-05 Public Home First-Viewport Copy Pass

Checked by tests, public gates, and one accepted in-app browser screenshot:

- Public Home still shows the five-page route rail, readiness-first header,
  `First 30 Seconds`, and `Primary Workflow` markers in the first viewport.
- The first-scan Home cards now use shorter copy so the workflow header,
  product explanation, and primary workflow do not repeat the full route in
  every visible block.
- The committed screenshot assets remain valid product evidence for route
  markers and share packaging, but they are not data freshness proof and may not
  reflect every latest copy edit pixel-for-pixel.

Capture limitation:

- The in-app browser accepted `/tmp/stock-first-viewport-audit-20260705/desktop-home.png`
  for the Home review, then timed out during later `Page.captureScreenshot`
  calls.
- Keep the committed real screenshots until a normal local browser can recapture
  and visually review any asset that needs exact current-copy proof.

## 2026-07-10 Compact Public Workflow Evidence Refresh

Checked with fresh real Streamlit captures at desktop and phone widths:

- The public shell now uses a compact `Saved readiness` status strip, the page's
  literal question, and the `Research-only` boundary. The in-content public workflow navigation is the route chooser; this supersedes the retired sidebar chooser described by older captures.
- The Home, Single-Stock Report, Data Health, and Proof History first views no
  longer repeat a generic current-question / primary-next-step / stop-rule card
  set. Each page shows its own answer before Advanced details.
- The completed single-stock route now replaces its preparation contract with
  the report answer rather than stacking both states. The selected ticker flows
  directly into `What Can Be Read Now`.
- Refreshed real captures: `docs/assets/linkedin-public-dashboard.png`,
  `docs/assets/public-demo-home-real.jpg`, and
  `docs/assets/single-stock-workflow-fit-real.jpg`.

Boundary checked:

- Screenshots remain product evidence only. They do not prove data freshness,
  source coverage, import success, or readiness changes.
- Generated CSV/report/sample-report output remains excluded from the reviewed
  product package.

## 2026-06-19 Workflow Continuity And Route Card Pass

Checked by tests and local read-only commands:

- Public Home: added a First 30 Seconds view before visitor path examples so a new viewer sees what the product does, how to read readiness, and when to stop.
- Public Home later moved route choices behind the clearer `Primary Workflow` and `Learn more` structure, so screenshot review should confirm the first path reads as page navigation rather than a command-heavy demo.
- Single-Stock Report: added a compact current-step / next-safe-action / stop-rule loop before dense ticker details and added the same report-step cue to loaded reports.
- Data Health queue drawers: added a navigation-only route map before the detailed lane drawers and action tables so operators see queue -> source proof -> comparison -> proof record -> artifact hygiene without jumping across sections.
- Trusted Fundamentals / DCF source loop: added source-review route cards before the checklist table so source fields, guard, validate/preview, apply/skip, and proof-record boundaries stay in sequence.

Boundary checked:

- The new cards are workflow/navigation guidance only; they do not refresh data, apply imports, record proof rows, stage files, commit, push, or unlock missing fundamentals, peers, earnings, analyst estimates, valuation inputs, or metrics.
- Commands remain copy-only; missing source inputs remain visibly blocked until trusted source proof, validate, preview, rejected-row review, explicit apply or skip decision, rebuilt readiness, and proof record pass.
- Historical blocker for this pass: the restricted browser environment showed
  `localhost refused to connect`, so new real screenshot capture was deferred
  until `make dashboard` could run in a normal local terminal.

## 2026-06-19 Browser QA Evidence V2

Added route-level manual QA, local capture checklists, and a copy-ready capture
session plan to `make browser-qa-evidence`.

Use it after starting the dashboard locally:

```bash
make dashboard
make browser-qa-evidence
make browser-qa-capture-plan
python3 -m src.browser_qa_evidence --json
```

The command remains read-only. It checks committed screenshot assets, prints exact
local capture targets, gives a six-step capture session plan, and lists route
checks for:

- Public visitor home.
- Single-stock workflow fit.
- Data Health operator fast view.
- Data Health metrics review.
- Data Health proof lane progressive load.
- Data Health proof history detail.
- Data Health queue drawer routing.

The command separates committed real screenshot assets from route screenshots
that still need manual capture. A `ready` verdict means the committed assets are
present, large enough, and matched to the expected first-view markers. If future
routes return `ready_with_manual_capture_pending`, capture the named targets in
a normal local browser before replacing GitHub or LinkedIn visuals. Do not use
generated thumbnails as proof of product state.

Local capture checklist:

- Start the app with `make dashboard` in a normal local terminal.
- Open each route printed under `Local Capture Checklist`.
- Save only real app screenshots to the listed `docs/assets/...` path.
- Keep the asset only if the first view shows the expected markers and no traceback, raw tables first, command-heavy public copy, or missing guardrails.
- Re-run `make browser-qa-evidence`, `make public-check`, and `make diff-hygiene-summary`.
- Follow the `Capture Session Plan` table from `make browser-qa-evidence` when
  replacing assets: start dashboard, capture pending views, confirm the first
  viewport, verify assets, run release gates, then stage only reviewed evidence
  assets plus product/docs/test files.
- The reviewed asset staging command is printed by `make browser-qa-capture-plan`;
  use it only after visual review and before `make staged-hygiene-check`.
- Use `make browser-qa-capture-plan` when you only need the capture sequence and
  not the full asset manifest.

For automation or reviewer packets, `python3 -m src.browser_qa_evidence --json`
prints the same verdict, committed screenshot assets, manual capture targets,
local capture checklist, capture session plan, route QA checklist, and
research-only boundary as structured JSON. The JSON also includes
`reviewed_asset_stage_command`, which names only the reviewed screenshot assets
that may be staged after visual review; broad `data/`, `data/reports/`, and
`outputs/` CSV/report churn remains excluded by default.

Review boundary:

- First view should show the workflow strip, current mode, readiness snapshot, and next safe action.
- Single-stock should show selected ticker state, what can be reviewed now, what is blocked or excluded, the Data Health handoff, and a stop rule before detailed report sections.
- Proof lane first view should show an intentional shell/loading boundary, not an empty page or expanded ledger.
- Queue drawer routes should show the route map and artifact-hygiene boundary, stay navigation-only, and should not run commands or imply generated churn belongs in a default staging set.
- Raw tables, proof rows, generated-artifact lists, and command-heavy details should stay collapsed until the relevant review route or drawer is opened.
- Missing source inputs stay blocked; browser evidence does not unlock fundamentals, peers, earnings, analyst estimates, valuation inputs, or metrics.

Historical capture blocker:

- In the restricted local QA environment, `make dashboard` could not bind the local Streamlit socket (`PermissionError: [Errno 1] Operation not permitted`), so new screenshot capture remains environment-limited for this pass.
- Keep using the existing real committed assets until a normal local browser can recapture the Single-Stock Workflow Fit, proof-lane progressive-load, and queue-drawer-routing screenshots.

## 2026-06-19 Browser QA Evidence V1

Checked pages:

- Public Home: confirmed the public visitor route renders the research loop strip and does not show a traceback.
- Single-Stock Report: confirmed the public route renders the workflow continuity strip and keeps example report states below the main report path.
- Data Health metrics lane: confirmed `?mode=operator&page=data-health&lane=metrics&drawer=metrics` renders the research loop strip, current-mode strip, operator queue, and review-detail route without horizontal overflow.
- Data Health proof lane: confirmed `?mode=operator&page=data-health&lane=proof&drawer=proof` renders without traceback or horizontal overflow.

Screenshot asset check:

- Use `make browser-qa-evidence` to verify the current committed dashboard screenshot assets, dimensions, route expectations, and public/LinkedIn use.
- Current LinkedIn thumbnail path remains [LinkedIn public dashboard](assets/linkedin-public-dashboard.png).
- Current public README screenshot remains [Public demo home](assets/public-demo-home-real.jpg).
- Current operator-mode reference remains [Operator Data Health metrics](assets/operator-data-health-metrics-real.jpg).

Capture limitation:

- The in-app browser could read and verify the Streamlit routes, but its screenshot endpoint timed out during `Page.captureScreenshot`.
- The local `screencapture` fallback also failed with `could not create image from display`.
- Because screenshot capture is environment-limited in this run, keep the existing real screenshot assets until a normal local browser can recapture them.

Boundary checked:

- Browser QA and screenshot assets are product evidence only; they do not refresh data, apply imports, record proof rows, stage files, commit, push, or unlock missing fundamentals, peers, earnings, analyst estimates, valuation inputs, or metrics.
- Commands remain copy-only; missing source inputs remain visibly blocked until trusted source proof, validate, preview, rejected-row review, apply or skip decision, rebuilt readiness, and proof record pass.

## 2026-06-06 Main Gap Fix Pass

Checked pages:

- Home: confirmed the Current Data Coverage section renders with the latest local readiness snapshot and copy-only proof commands.
- Single-Stock Report: confirmed the page renders with ready, blocked, excluded, and copy-only guidance.
- Value / Re-rating: confirmed the page renders valuation readiness language without overclaims.
- Data Health: confirmed the page renders proof workflow guidance and keeps missing context locked.

Screenshots:

- [Home coverage QA](assets/dashboard-qa-home-coverage.png)
- [Data Health QA](assets/dashboard-qa-data-health.png)

Boundary checked:

- No broker integration, order execution, auto-trading, or direct buy/sell instruction language appeared in the checked pages.
- Commands remain copy-only; the dashboard does not run refreshes or imports from the UI.

## 2026-06-07 Public Product Flow Pass

Checked pages:

- Home: confirmed the visitor route shows `Stock Selector`, `Single-Stock Report`, `Data Health`, and `Proof History`, plus a trusted-data pilot path for improving 5-10 companies first.
- Single-Stock Report: confirmed a local `NVDA` preview renders the visitor scan cue, `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, then `Best Review Path` before detailed tabs.

Boundary checked:

- `Best Review Path` correctly routes the DCF/peer-ready `NVDA` example to review DCF, peers, and source readiness instead of sending it back to price coverage.
- Optional earnings and analyst-estimate context remains locked unless trusted local rows exist.
- Commands remain copy-only; the dashboard does not run refreshes or imports and does not connect to external accounts from the UI.

## 2026-06-07 Follow-Up Product Copy Pass

Checked pages and reports:

- Sidebar: confirmed the main navigation control reads `Choose your path`, not internal review-control language.
- Data Health: confirmed first-screen wording uses checklist/review-path language before advanced command detail.
- Value / Re-rating: confirmed the broad valuation input count is labeled separately from exact company DCF-ready counts.
- Portfolio Review: confirmed table helper copy says `next-step context` instead of internal-tool operational wording.
- Trusted Data Pilot: confirmed the read-only pilot prints a company starter set and separates `QQQ` / `SMH` as ETF/index monitor examples, not operating-company DCF targets.
- `outputs/stock_reports/a.md`: confirmed standalone DCF peer wording no longer repeats `DCF assumptions and sensitivity`.

Boundary checked:

- The changes stay copy-only and research-only.
- No generated CSV/JSON churn was published with the UI copy pass.

## 2026-06-10 Public Navigation And Data Strategy Pass

Checked pages and docs:

- Sidebar: confirmed the main navigation control reads `Choose your path` and exposes the public paths before the `Optional research views` section.
- Sidebar: confirmed detailed pages remain available under `Optional research views`, so deep research views are not removed.
- Home: confirmed the demo walkthrough shows copyable commands for the dashboard, NVDA ready proof, META blocked proof, QQQ excluded proof, MU peer-limited proof, CRDO fundamentals-gated proof, and the trusted-data pilot.
- Data Strategy: confirmed the Automation Boundary table separates repeatable checks from human-reviewed source judgment.

Boundary checked:

- Commands remain copy-only; the dashboard does not run refreshes or imports and does not connect to external accounts from the UI.
- Data coverage guidance still requires trusted source rows for fundamentals, peers, earnings, analyst estimates, and valuation inputs.

## 2026-06-10 Trusted Pilot Candidate UX Pass

Checked pages and docs:

- Home: confirmed the demo walkthrough points visitors to `make project-status-check` first, then `make provider-setup-checklist` when source-proof queues are exhausted, before any ticker-scoped trusted-data pilot checklist.
- Home: confirmed the next-step cards describe the status gate as read-only and keep the candidate list available only when executable company candidates exist.
- Portfolio Review: confirmed the page renders plain-language capability and limit cards after Streamlit finishes loading, with review-only wording and no portfolio action instruction.
- Public docs: confirmed the release checklist and LinkedIn brief explain project status first, provider setup when queues are exhausted, then the selected-company evidence loop only when executable candidates exist.

Boundary checked:

- Candidate ranking remains copy-only and read-only; it does not refresh prices, import rows, or change readiness outputs.
- ETF/index examples remain monitor-context demos, not operating-company DCF pilot targets.

## 2026-06-11 Public Route Alignment Pass

Checked pages and assets:

- README: confirmed the Product Tour routes `Proof History` to the Proof History route.
- Dashboard preview asset: confirmed the visual route copy now says `Proof History: evidence for changed states`.
- Public checks: confirmed `make public-check` passes after the route and preview alignment.

Boundary checked:

- The route change is navigation copy only; it does not refresh data, import rows, or change readiness outputs.
- The generated Monthly Picks CSV remains local working output and was not committed as part of this QA pass.

## 2026-06-11 Visitor Guide Browser Pass

Checked pages and commands:

- Monthly Picks: confirmed the page renders the new `Reader Guide` with `Open a one-stock report next`, `No automatic conclusion`, and the Data Health path for empty candidate states.
- Single-Stock Report: confirmed the page renders the demo ticker guide for `NVDA`, `META`, `QQQ`, `MU`, `CRDO`, plus optional `A`, `SMH`, and `APLD` before the report button.
- Trusted Data Pilot CLI: confirmed candidate output no longer repeats the `Decision gate` label and still prints read-only source-proof boundaries.

Boundary checked:

- The browser pass used the local Streamlit page only; it did not refresh data, import rows, or change readiness outputs.
- Monthly candidate guidance stays a research queue, not a recommendation list.
- Single-stock demo guidance keeps DCF-ready, blocked, excluded, and standalone DCF examples separate.

## 2026-06-11 Data Health Freshness Routine Pass

Checked pages and docs:

- Data Health: confirmed the `Freshness Routine` section explains a read-only daily/opening routine before any refresh or import step.
- Data Health: confirmed the beginner path now starts with `quick read`, `fix first`, and `trusted-data pilot`, with refresh and command-heavy details available only when opened.
- Data Health: confirmed price freshness guidance starts with a capped dry-run command and tells users to inspect generated CSV diffs before a real capped loop.
- Data Health: confirmed fundamentals, peer mappings, earnings, and analyst estimates remain review-required lanes instead of unattended automation targets.
- Public checklist: confirmed the release flow points visitors to Data Health for safe freshness guidance without suggesting daily manual full-universe refreshes.

Boundary checked:

- The freshness routine is copy-only; the dashboard does not execute refreshes, imports, broker actions, or trades.

## 2026-06-11 Data Health Compact Default Pass

Checked pages and docs:

- Data Health: confirmed the default page keeps `Data Health Quick Read`, `Fix First`, and `Trusted Data Pilot` visible before broad tables.
- Data Health: confirmed `Refresh and command details` is collapsed by default, so `Freshness Routine` and `Copy-Only Next Steps` do not crowd the first scan.
- Data Health: confirmed `Pilot selection details` is collapsed by default, while top pilot candidates remain visible.
- Sidebar: confirmed the control reads `Show reader tips`, not `Show page tips`.

Boundary checked:

- Collapsing details is a UI/readability change only; commands remain copy-only and no data refresh, import, or account action is triggered from the dashboard.
- This pass documents workflow clarity only; it does not claim new fundamentals, peer, earnings, or analyst-estimate coverage.

## 2026-06-11 Trusted Pilot Compact Output Pass

Checked commands and docs:

- Trusted Data Pilot CLI: confirmed `make trusted-data-pilot-candidates TOP_N=10` prints a compact visitor-friendly shortlist, quick path, and short review board instead of a full row-by-row diagnostics wall.
- Trusted Data Pilot CLI: confirmed `make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1` remains available for local proof detail, including file status, decision gates, rejected-row paths, and evidence expectations.
- Public docs: confirmed README, Data Strategy, Public Release Checklist, LinkedIn brief, and `make demo` present compact project-status routing first, then candidate ranking only when executable company candidates exist; verbose detail remains an optional follow-up.
- Public release flow: confirmed the compact default points to one-company evidence packets before validate/preview gate, apply boundary, and rebuild proof, so visitors see the workflow without needing to import data.

Boundary checked:

- The compact candidate command is read-only; it does not refresh prices, import fundamentals, add peers, or change readiness outputs.
- `VERBOSE=1` exposes local proof detail only; it does not lower data gates or convert missing trusted rows into analysis.
