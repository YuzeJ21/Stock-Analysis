# Company Workbench Answer-First Handoff Design

## Status

Approved by the user and implemented in commit `ca4772ffb` on the active feature branch. Focused test-first contracts, the full local release matrix, and desktop/phone browser acceptance pass; exact push, draft-PR update, and exact-head CI evidence remain required before the slice is safe for draft review.

## Problem

Company Workbench is intended to answer the selected-company question before showing navigation or technical evidence. A live local audit of the AVGO route at `390x844` found that the selected-ticker answer begins at approximately `753px`, while its Data Health handoff begins at approximately `1136px`. The phone viewport is `844px` high. The page has no horizontal overflow or browser error, but the usable/withheld/evidence-handoff answer is not available in the first viewport.

The current vertical order is:

1. Global readiness and profile trust context.
2. Full Personal Research workspace header, including freshness and next action already represented elsewhere.
3. `Selected Company` heading.
4. Collapsed `Review path`.
5. Collapsed `Advanced: selected-company lane coverage`.
6. Selected-ticker answer.

The two collapsed controls occupy approximately `100px`, but moving them alone is insufficient. The Workbench also repeats profile freshness and next-action context before the selected-ticker answer.

## User Outcome

A researcher opening Company Workbench for a selected ticker should see, in this order:

1. The page and selected ticker identity.
2. What evidence is usable now.
3. What remains withheld.
4. The Data Health evidence handoff and stop condition.
5. Review-path and lane-coverage navigation.
6. Business trend, valuation, Forward View, research conclusion, next task, and Advanced evidence.

The first four items should fit within the first `390x844` viewport for the audited AVGO route without hiding freshness, research-only boundaries, or blocked states.

## Chosen Design

Use a Workbench-specific compact header plus an anchored selected-answer slot.

### Compact Workbench Header

Extend the existing research workspace header contract with an explicit compact option used only by Company Workbench. The compact form keeps:

- `Personal research mode`.
- The semantic `h1` for `Company Workbench`.
- The selected ticker and profile label.
- The research-only, no-investment-advice boundary.

It omits the header freshness and next-action definition list because:

- The global profile trust strip already displays saved freshness.
- The selected-ticker answer already supplies the next safe action and evidence boundary.

Research Desk, Discover, Monitor, Data Health, and Proof History retain the existing header unchanged.

### Anchored Selected Answer

Company Workbench declares a Streamlit placeholder immediately after the compact header. It then renders the collapsed `Review path` and `Advanced: selected-company lane coverage` controls.

`render_single_stock_report` accepts an optional selected-answer target. When supplied:

- The fast loading summary renders into that target.
- The final report summary renders into the same target after local report composition.
- The summary is not duplicated at the report's execution position.
- All content after the summary continues to render in its current order below the two collapsed controls.

This preserves the existing loading/final handoff contract while changing only its visual placement in Company Workbench.

### Navigation Placement

Remove the redundant `Selected Company` level-three heading because the compact header already provides the semantic page heading and selected ticker identity.

Keep `Review path` and `Advanced: selected-company lane coverage` collapsed. They appear immediately after the anchored selected answer and before `What Changed` and the remaining report sections.

Technical lane coverage stays under Advanced. No raw tables or technical diagnostics move into the primary answer.

## Alternatives Rejected

### Hide Profile/Freshness Context On Phone

This would recover space but weaken the evidence-trust boundary. Freshness must remain visible and independent from the selected-company answer.

### Move Both Expanders After The Entire Report

This is mechanically simpler but makes the review path and lane coverage difficult to discover after a long report. The selected-answer slot provides answer-first placement without burying navigation.

### Render A Separate Approximate Summary Before The Report

The fast snapshot can differ from the final report state. Rendering an independent persistent summary would risk contradictory usable/withheld claims. The selected-answer slot must be filled by the same fast and final summary paths already used by the report.

## Data And State Flow

1. The route resolves the ticker and optional cash-generation preview exactly as it does now.
2. Company Workbench renders the compact header and creates the answer placeholder.
3. Collapsed review-path and technical lane-coverage controls render after the placeholder.
4. `render_single_stock_report` receives the placeholder.
5. If no report payload exists, the existing fail-closed fast snapshot renders into the placeholder while the saved local report is composed.
6. After rerun, the final readiness-derived selected-ticker answer replaces the fast answer in the same placeholder.
7. The report renders its existing sections and independent readiness states unchanged.

No provider call, refresh, import, canonical write, readiness rebuild, evidence append, or generated artifact is introduced.

## Failure And Loading Behavior

- The loading answer remains explicitly temporary and cannot state that unavailable sections are ready.
- A report composition failure keeps existing warning/error behavior; it does not promote the fast snapshot into trusted final evidence.
- An empty answer frame continues to show the existing no-answer state.
- The optional target defaults to absent, preserving all current public and operator callers.
- The selected answer must render exactly once in the final Workbench DOM.

## Accessibility And Responsive Requirements

- `Company Workbench` remains the page `h1`.
- The selected answer retains `aria-label="Selected ticker answer"`.
- The Data Health link retains its ticker-preserving research-mode URL.
- The reading order is page identity, selected answer, review navigation, report content.
- The phone route has no horizontal overflow.
- The Data Health handoff is fully inside the first `390x844` viewport with a non-negative bottom clearance.
- The desktop route preserves the existing multi-column selected-answer layout and visible evidence handoff.
- Screenshot evidence cannot prove keyboard, screen-reader, contrast, or full WCAG conformance; existing automated and semantic checks remain required.

## Test-First Implementation

### Red

Add failing contracts that require:

- A compact header to retain page identity, ticker/profile scope, and research-only boundary while omitting duplicated freshness/action metadata.
- Company Workbench to declare its selected-answer target before review-path and lane-coverage controls.
- The report renderer to receive that target.
- Fast and final research-mode summaries to use the supplied target rather than render duplicate summaries.
- The final Workbench render to contain exactly one selected-ticker answer and preserve the ticker-specific Data Health URL.

### Green

Implement only the compact header option, optional selected-answer target, and Workbench placement changes needed to pass those contracts.

### Verification

- Focused research workspace, dashboard helper, render-smoke, and performance-contract tests.
- `python3 -m pytest tests -q`.
- `make dashboard-smoke`.
- `make public-wording-check`.
- `make public-check`.
- `make commercial-beta-release-check`.
- `make pilot-readiness-check TOP_N=10`.
- `make pr-range-hygiene-check`.
- `make diff-hygiene-summary`.
- `git diff --check`.
- `make staged-hygiene-check` after exact staging.
- Fresh desktop and `390x844` browser measurements of order, overflow, link visibility, and error state.

## Invariants

- Research-only; no investment advice or direct buy/sell instruction.
- No broker integration, order routing, auto-trading, or post-earnings price prediction.
- Candidate context cannot alter deterministic forecasts or become trusted evidence.
- Actuals, consensus, Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, peer, catalyst, outcome, backtest, and calibration readiness remain independent.
- Missing evidence remains withheld.
- EPS split basis remains unverified without explicit proof.
- Q4 requires explicit SEC-filed three-month table evidence.
- Synthetic fixtures remain test-only.
- Empty valuation, catalyst, outcome, consensus, and field-proof ledgers remain empty.
- No readiness rebuild or generated CSV, JSON, report, sample-report, screenshot, timing, or canonical-data artifact enters the commit.

## Acceptance Criteria

The slice is complete only when:

1. Focused and full tests pass.
2. The complete local release matrix passes.
3. Live desktop and phone evidence confirms the selected answer precedes both collapsed controls.
4. The ticker-specific Data Health handoff is fully visible in the first `390x844` viewport.
5. Exactly one final selected-ticker answer exists.
6. No readiness, source, report conclusion, or evidence state changes.
7. Only intentional code, test, documentation, and specification files are staged.
8. The 18 pre-existing generated CSV/report changes remain unstaged.
9. Independent engineering review reports no unresolved Critical or Important findings.
10. The exact pushed HEAD passes GitHub Actions while PR #113 remains draft.

## Implementation Evidence

The implementation uses a Workbench-only compact header, an anchored Streamlit target, and one target-aware summary renderer shared by the fast and final report paths. Live review also found that the selected answer's tracked multi-column styles were loaded only in Public mode, despite the design assumption that Personal Research mode already inherited them. The implementation therefore adds an explicit `research` summary class with scoped desktop and phone styles; it does not load the Public shell or change other routes.

Current-tree AVGO measurements:

- `1280x720`: one selected answer; CSS grid columns `128px 303.5px 303.508px 242.797px`; Data Health visible; answer precedes Review path; no horizontal overflow.
- `390x844`: one selected answer from approximately `409px` to `711px`; Data Health ends near `669px`; stop condition ends near `705px`; Review path ends near `746px`; lane coverage ends near `806px`; document and viewport widths are both `390px`.
- Browser logs contained only the initial connection-health errors recorded more than seven minutes before final measurement; no later product/runtime error was recorded during the final desktop or phone acceptance run.

Screenshots remain ephemeral under `/tmp/stock-research-workflow-audit-2026-07-22/` and must not be staged. These measurements are local runtime evidence only and do not prove hosting, full accessibility conformance, independent review, demand, or market validation.
