# Dashboard QA Notes

This file records lightweight browser QA evidence for public-facing dashboard polish.

## Current Screenshot Evidence Status

| Evidence | Status | Use |
| --- | --- | --- |
| `docs/assets/linkedin-public-dashboard.png` | Ready | GitHub/LinkedIn thumbnail from the real public dashboard. |
| `docs/assets/public-demo-home-real.jpg` | Ready | README first-screen product preview. |
| `docs/assets/operator-data-health-metrics-real.jpg` | Ready | Operator metrics lane proof that Data Health is readiness-gated and copy-only. |
| Single-stock workflow fit screenshot | Manual capture pending | Capture in a normal local browser before claiming full one-stock workflow screenshot coverage. |
| Data Health proof lane screenshot | Manual capture pending | Capture in a normal local browser before claiming proof-lane progressive-load screenshot coverage. |
| Data Health queue drawer routing screenshot | Manual capture pending | Capture in a normal local browser before claiming queue-to-proof routing screenshot coverage. |

Screenshot evidence is product evidence only. It does not refresh data, apply imports, unlock blocked fundamentals, peers, earnings, analyst estimates, valuation inputs, or prove current readiness counts.

## 2026-06-19 Workflow Continuity And Route Card Pass

Checked by tests and local read-only commands:

- Public Home: added a First 30 Seconds view before visitor path examples so a new viewer sees what the product does, how to read readiness, and when to stop.
- Public Home later moved the route choice to a visible `Where To Go Next` block before optional workflow detail, so screenshot review should confirm the first path reads as product navigation rather than a command-heavy demo.
- Single-Stock Report: added a compact current-step / next-safe-action / stop-rule loop before dense ticker details and added the same report-step cue to loaded reports.
- Data Health queue drawers: added a navigation-only route map before the detailed lane drawers and action tables so operators see queue -> source proof -> comparison -> proof record -> artifact hygiene without jumping across sections.
- Trusted Fundamentals / DCF source loop: added source-review route cards before the checklist table so source fields, guard, validate/preview, apply/skip, and proof-record boundaries stay in sequence.

Boundary checked:

- The new cards are workflow/navigation guidance only; they do not refresh data, apply imports, record proof rows, stage files, commit, push, or unlock missing fundamentals, peers, earnings, analyst estimates, valuation inputs, or metrics.
- Commands remain copy-only; missing source inputs remain visibly blocked until trusted source proof, validate, preview, rejected-row review, explicit apply or skip decision, rebuilt readiness, and proof record pass.
- In the restricted browser environment, the current in-app browser shows `localhost refused to connect`, so new real screenshot capture remains blocked until `make dashboard` is running in a normal local terminal.

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

The command separates committed real screenshot assets from newer route
screenshots that still need manual capture. A
`ready_with_manual_capture_pending` verdict means the existing committed assets
are usable, while the Single-Stock Workflow Fit, Data Health proof lane, and
Data Health queue drawer screenshots should still be captured in a normal local
browser before replacing GitHub or LinkedIn visuals. Do not use generated
thumbnails as proof of product state.

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

Capture blocker:

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

- Home: confirmed the visitor route shows `Review one stock`, `Improve data coverage`, and `Inspect proof`, plus a trusted-data pilot path for improving 5-10 companies first.
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

- Sidebar: confirmed the main navigation control reads `Choose your path` and exposes the public paths before the `More pages` section.
- Sidebar: confirmed detailed pages remain available under `More pages`, so deep research views are not removed.
- Home: confirmed the demo walkthrough shows copyable commands for the dashboard, NVDA ready proof, META blocked proof, QQQ excluded proof, MU peer-limited proof, CRDO fundamentals-gated proof, and the trusted-data pilot.
- Data Strategy: confirmed the Automation Boundary table separates repeatable checks from human-reviewed source judgment.

Boundary checked:

- Commands remain copy-only; the dashboard does not run refreshes or imports and does not connect to external accounts from the UI.
- Data coverage guidance still requires trusted source rows for fundamentals, peers, earnings, analyst estimates, and valuation inputs.

## 2026-06-10 Trusted Pilot Candidate UX Pass

Checked pages and docs:

- Home: confirmed the demo walkthrough now points visitors to `make trusted-data-pilot-candidates TOP_N=10` before the ticker-scoped trusted-data pilot checklist.
- Home: confirmed the next-step cards describe the candidate list as read-only and keep the ticker-scoped pilot as the follow-up proof loop.
- Portfolio Review: confirmed the page renders plain-language capability and limit cards after Streamlit finishes loading, with review-only wording and no portfolio action instruction.
- Public docs: confirmed the release checklist and LinkedIn brief explain candidate ranking first, then the selected-company evidence loop.

Boundary checked:

- Candidate ranking remains copy-only and read-only; it does not refresh prices, import rows, or change readiness outputs.
- ETF/index examples remain monitor-context demos, not operating-company DCF pilot targets.

## 2026-06-11 Public Route Alignment Pass

Checked pages and assets:

- README: confirmed the Product Tour routes `Inspect proof` to the Data Health proof drawers.
- Dashboard preview asset: confirmed the visual route copy now says `Inspect proof: readiness snapshots and proof ledger`.
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
- Public docs: confirmed README, Data Strategy, Public Release Checklist, LinkedIn brief, and `make demo` present compact candidate ranking first, then verbose detail only as an optional follow-up.
- Public release flow: confirmed the compact default points to one-company evidence packets before validate/preview/apply and rebuild proof, so visitors see the workflow without needing to import data.

Boundary checked:

- The compact candidate command is read-only; it does not refresh prices, import fundamentals, add peers, or change readiness outputs.
- `VERBOSE=1` exposes local proof detail only; it does not lower data gates or convert missing trusted rows into analysis.
