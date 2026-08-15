# Company Workbench Document Workspace Design

**Status:** Approved visual direction. The owner selected the third displayed
ImageGen direction and then explicitly asked to build it while preserving the
current product functions.

**Visual target:**
`/Users/yjian070/.codex/generated_images/019fe1a2-ef19-73c0-8e1a-069060f28b90/exec-a7444f21-6213-40f5-b4c0-cfb6bcb75797.png`

**Visual target SHA-256:**
`0f4105b35445cf11c1397b6e2d5b422a023723be9c828dc43438c8df446f0d7f`

## Objective

Recompose Personal Research Company Workbench as a modern, document-first
research workspace. The selected company brief remains the first answer, a
compact evidence-status rail makes readiness visible without opening technical
tables, and the existing analytical and authoring modules remain available
through the current explicit detail gate.

This is a presentation and hierarchy change. It does not change data loading,
readiness calculations, evidence identities, scenario math, task arbitration,
authoring persistence, downloads, routes, or research conclusions.

## Approved Direction

The selected direction has four defining characteristics:

1. a restrained horizontal Personal Research header instead of a dominant
   desktop side rail;
2. an editorial company-brief title and four-column answer strip;
3. a dark evidence-status rail that distinguishes usable and withheld lanes;
   and
4. document-like detail below the answer, using spacing and rules instead of a
   wall of cards.

The generated mock is a visual-language reference, not a data source. Its
invented dates, company prose, statuses, notes, and update times must not enter
the application. Current saved evidence remains authoritative.

## Preservation Contract

The redesign must retain all current Company Workbench behavior:

- exact `mode=research&page=company-workbench&ticker=...&open=1` routing;
- no inferred ticker when the route has no registered saved company;
- the four-part Company Brief: Use now, Still withheld, What changed, and Next
  research task;
- exactly one authoritative Data Health handoff, including the peer-lane query
  when peers are the blocker;
- the research-only stop rule before detailed modules;
- the traceable-change timeline and truthful no-change state;
- collapsed Review path, selected-company lane coverage, observation-recency,
  and Full Company Brief evidence disclosures;
- the explicit `Open evidence and analysis modules` gate;
- Research Decision Lab, Business Trend, cash-generation preview when
  explicitly requested, Valuation, Forward View, What Remains Withheld,
  thesis/evidence journal, outcome review, authoring, decision-process
  scorecard, Research Conclusion, and HTML Research Brief download;
- the current `cash_preview=1` opt-in boundary;
- every existing session-state key, validate-preview-confirm authoring flow,
  scenario state, rerun behavior, download behavior, and no-write default;
- Data Health, Proof History, Discover, Monitor, Public, and Operator route
  behavior; and
- fail-closed handling for missing, stale, unverified, excluded, or
  rights-blocked evidence.

No function may be removed merely because it is not depicted in the generated
mock. Undepicted functions remain below the existing progressive-disclosure
gate.

## Information Architecture

### Personal Research navigation

At desktop widths, the existing single Personal Research navigation DOM becomes
a compact horizontal header. It retains Research Desk, Discover, Company
Workbench, Monitor, the disabled Workbench state when no ticker exists, current
route semantics, Public and Operator mode links, and the existing focus order.

At phone width and 200% zoom, the same DOM uses the existing wrapped route grid.
No duplicate desktop/mobile navigation is introduced.

### Company header

The existing route H1 remains `Company Workbench` for stable route identity and
browser contracts. The primary brief adds the editorial display title
`{TICKER} Company Brief`. A refined system-serif stack is used only for that
display title; the rest of the application keeps the established Inter / SF Pro
Text / Segoe UI stack.

### Primary brief

The four current answer lanes remain in their existing DOM and evidence order.
They are restyled as an open editorial strip with thin separators, restrained
state accents, and no outer card wall. The Data Health action remains a real
44-pixel target. The research-only stop rule becomes a separate full-width
boundary immediately below the four answers.

### Evidence-status rail

The rail is a new read-only projection of the already-built stock-report
readiness map. It contains exactly these lanes:

- Fundamentals — `fundamentals_ready`;
- DCF — `dcf_ready`;
- Peers — `peer_ready`;
- Earnings — `earnings_available` or `earnings_ready`; and
- Estimates — `analyst_estimates_available` or
  `analyst_estimates_ready`.

Each lane renders `Supported` only when its exact boolean is true. False or
missing values render `Withheld`; missing report state renders `Unavailable`.
One lane can never inherit another lane's state. The rail also shows the saved
readiness freshness using the established saved-source label and provides the
same authoritative Data Health href as the Company Brief.

The rail does not show invented update dates, notes, counts, recommendations,
scores, confidence, or current-market claims.

### Detailed modules

The report renderer remains the sole owner of all existing analytical,
scenario, journal, authoring, and download modules. The default explicit-open
gate remains unchanged. When opened, modules render below the document overview
in their existing order and with their existing behavior. The redesign may
soften borders and improve heading rhythm, but it must not replace real module
content with prose from the mock.

## Renderer Architecture

`src/research_workspace.py` owns a pure, escaped
`company_workbench_evidence_status_html(...)` projection. It accepts the
existing readiness mapping, saved freshness label, ticker, and Data Health href
and performs no loading or state mutation.

`src/dashboard.py` creates one keyed Company Workbench overview container with
two Streamlit columns. The left column owns the existing primary-answer and
supporting-evidence placeholders. The right column owns a status placeholder.
`render_single_stock_report(...)` receives the optional placeholder and fills it
after it computes the existing authoritative readiness map. If the report is
not available, it fills the rail with unavailable states. All downstream report
rendering remains outside the two-column overview so phone reflow never places
the rail after thousands of pixels of detail.

CSS remains scoped to Personal Research and the keyed Workbench container. No
Operator or Public selector is changed.

## Responsive And Accessibility Contract

- At `1440x1024` and `1280x720`, the brief and evidence rail form a readable
  main/aside composition with no horizontal overflow.
- At `390x844`, the brief appears first, the evidence rail follows it, and the
  module gate follows the overview. The four answer lanes stack in one column.
- At 200% zoom, the layout reflows to one column without clipped navigation,
  hidden stop text, or horizontal scrolling.
- The page retains one H1, one labelled Personal Research navigation, one
  Company Brief region, one evidence-status region, and one primary Data Health
  action.
- Keyboard order remains skip link, navigation, primary action, then advanced
  detail. No positive tabindex is added.
- All primary controls keep a minimum 44-by-44-pixel target.
- Status is communicated by text in addition to color. Forced-colors and
  reduced-motion behavior remain supported.
- Automated evidence remains engineering evidence only; it does not claim
  human screen-reader or WCAG completion.

## Test Strategy

Test-first work must prove:

1. the pure rail escapes text, exposes exactly five independent lanes, fails
   closed on missing readiness, and reuses the brief's Data Health href;
2. the primary brief exposes the editorial company title without changing its
   four answer labels, action, stop rule, or peer query;
3. the renderer wires the rail from the existing readiness map and does not
   load a second report, refresh a source, or mutate evidence;
4. every existing Workbench function listed in the preservation contract still
   appears in the relevant closed or opened state;
5. desktop and phone layout, target size, focus, overflow, runtime, and network
   checks pass; and
6. a same-viewport comparison against the selected image has no unresolved
   P0/P1/P2 design mismatch after intentional product-truth deviations are
   documented.

## Explicit Non-Goals

- no new company data, provider, refresh, import, apply, materialization, or
  generated-artifact mutation;
- no recommendation, ranking, scoring, probability, allocation, sizing,
  entry/exit, risk-budget, or trading language;
- no new route, page, authoring type, scenario, persistence model, or report
  format;
- no Figma dependency or token;
- no deployment, publishing, push, PR, merge, or hosted-product claim; and
- no redesign of Public or Operator workflows in this slice.

## Completion

The local slice is complete only when focused tests, affected render tests,
desktop/phone browser evidence, function-preservation checks, protected-artifact
checks, and design QA all pass on the final bytes and an independent reviewer
finds no Critical or Important regression.
