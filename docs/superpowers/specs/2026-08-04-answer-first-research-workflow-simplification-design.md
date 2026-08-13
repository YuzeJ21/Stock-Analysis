# Answer-First Research Workflow Simplification Design

## Purpose

The Stock Research Command Center already contains useful evidence, research-state, valuation, catalyst, outcome, authoring, and monitoring capabilities. The current problem is composition rather than missing analytical breadth: primary routes expose repeated navigation, profile metadata, readiness totals, technical modules, and overlapping empty states before the researcher reaches the answer and next task.

This design simplifies the existing Personal Research workflow without adding a route, calculation engine, ranking system, forecast, or data source. Every primary page will answer one research question first and progressively disclose the evidence behind that answer.

## Current Evidence

The current workflow was reproduced at `1280x720` and `390x844` with the fully loaded application state.

| Route | Question the user needs answered | Current evidence |
| --- | --- | --- |
| Research Desk | What needs my attention today? | The weekly answer begins after duplicated navigation, workspace/profile status, route framing, and recency detail. At `390x844`, the weekly summary begins near the bottom of the first viewport and the Discover action is far below it. |
| Discover | Which saved company has evidence I can inspect? | The strict queue and general selector are visually adjacent. A truthful empty strict queue can coexist with general rows described using ranking-adjacent priority language, so the two eligibility meanings are easy to confuse. |
| Company Workbench | What can I use, what is withheld, what changed, and what should I do next? | The selected-company answer is useful, but the fully loaded mobile route is about 8,079px tall and places many analytical and empty modules before the authoritative next task. The next action and research-only stop rule are not visible in the first `390x844` viewport. |
| Monitor | What requires verification, what is waiting for evidence, and when should I revisit it? | Evidence Monitor Brief, Research Discipline Review, and Research Change Monitor repeat related zero-state conclusions and separate the answer from its return action. |

The desktop routes also expose two route-selection systems: top workflow navigation and a sidebar route selector. Technical profile/readiness evidence consumes much of the first viewport on both desktop and mobile.

## Design Principles

1. **One page, one question.** Every route begins with its question, answer or truthful withheld state, short reason, one next action, and a stop rule.
2. **Answer before evidence mechanics.** Provenance, lineage, readiness matrices, identifiers, calculations, and operator detail remain available under `Advanced Evidence` unless they directly change the answer.
3. **One navigation authority.** The top workflow navigation owns Personal Research route movement. Workspace selection may remain in the sidebar, but the duplicate page selector will not compete with the top navigation.
4. **Capability is not eligibility.** A company that can be opened for evidence inspection is not presented as having passed a momentum, valuation, opportunity, or expected-return screen.
5. **Empty once, then act.** Related zero states are consolidated into one explanation and one safe next action.
6. **Preserve research truth.** Presentation changes cannot alter thresholds, deterministic calculations, readiness, provenance, source rights, evidence identities, or authoring persistence contracts.
7. **No-write primary workflow.** Ordinary route rendering composes current in-memory/application data and HTML. It does not rebuild readiness or generate CSV, JSON, report, screenshot, timing, output, or canonical-data artifacts.

## Considered Approaches

### A. In-place answer-first recomposition — selected

Reuse the four current routes, their existing evidence builders, and the current visual system. Introduce a small shared page-answer contract only where it removes repeated composition. Implement and verify each route separately.

This is the lowest-risk approach because it improves the user journey without migrating URLs, inventing data, or replacing tested evidence logic.

### B. Dense visual reskin only — rejected

Copying the reference dashboard's dark compact grid would improve apparent density but would leave the contradictory Discover meanings, repeated Monitor zero states, and buried Workbench conclusion intact. Visual compression alone does not answer the user's questions.

### C. New consolidated dashboard and route model — rejected

A new route or dashboard shell would duplicate existing logic, increase compatibility risk, and create another navigation model. The product already has the required capabilities; they need clearer hierarchy.

## Shared Page Contract

Every primary route will render this logical order:

1. **Question** — the task the page resolves, expressed in plain language.
2. **Answer** — current evidence-backed answer, or an explicit withheld/empty state.
3. **Why** — the shortest evidence-backed explanation that changes interpretation.
4. **Next action** — exactly one primary workflow action.
5. **Stop rule** — the boundary that prevents an unsupported conclusion or recommendation.
6. **Advanced Evidence** — detailed modules, technical evidence, alternative actions, and operator detail.

The answer layer must remain understandable without opening Advanced. It may contain multiple independent evidence states where collapsing them would overclaim, but it must not become a second dashboard of technical modules.

### Shared shell and navigation

- Keep the current route query parameters and direct-link compatibility.
- Keep one visible Personal Research workflow navigation: `Research Desk`, `Discover`, `Company Workbench`, and `Monitor`.
- When no company is selected, Workbench is shown as unavailable with the instruction to choose a company in Discover; it must not become a broken link.
- Remove the duplicate desktop sidebar page selector for Personal Research. Retain workspace-mode selection and any genuinely global control.
- Compress the primary profile/readiness strip to the state that changes the page answer. Move broad lane totals, data profile, build evidence, and operator diagnostics under Advanced or Operator evidence.
- Keep one H1 and one primary landmark per route. Do not duplicate route titles in the top bar and page body.

## Route Designs

### Research Desk — Today's Research Brief

**Question:** What needs my attention today?

**Primary layer:**

- one concise count or truthful no-item state;
- the most important evidence-backed reason;
- one action to open Discover when selection is needed, or Monitor when an existing follow-up requires verification;
- the relevant freshness warning;
- the research-only stop rule that the brief is not a market-complete event feed or recommendation.

The existing four overlapping answer cards are replaced by one brief composition. Universe coverage, readiness matrices, focused-cohort mechanics, and weekly evidence rows move under Advanced. Desk summarizes attention; it does not reproduce Monitor's detailed follow-up queue.

### Discover — Find a Company

**Question:** Which saved company has evidence I can inspect?

Discover contains two explicitly separate capabilities:

1. **Screen eligibility — when supported.** This is the strict deterministic queue. Existing thresholds remain unchanged. When no company passes every gate, show one empty state: no company currently has complete evidence for the strict screen. State which evidence classes block eligibility without implying that no company is worth researching.
2. **Browse saved companies.** This is an alphabetical evidence-access list. Rows explain inspectability through available evidence and the principal evidence gap. They do not use `High review priority`, priority order, opportunity, expected return, best-stock, recommendation, or screen-passing language.

The primary action is `Open Company Brief`. General browsing rows cannot inherit legacy ranking order or ranking-derived copy. If alphabetical ordering cannot be guaranteed from current saved-company identities, the route must fail closed rather than silently use a ranking source.

**Stop rule:** saved-company availability does not mean strict screen eligibility, momentum strength, attractive valuation, or an investment recommendation.

### Company Workbench — Company Brief

**Question:** What can I use now, what remains withheld, what changed, and what is the next research task?

The primary layer contains only:

- **Use now** — independent evidence lanes currently usable for research;
- **Still withheld** — independent missing, stale, unverified, or rights-blocked lanes;
- **What changed** — traceable saved changes, or a truthful no-traceable-change state;
- **Next research task** — one authoritative action derived from the current evidence gap;
- **Research-only stop rule** — no recommendation, transaction instruction, probability, or unsupported current-market conclusion.

Repeated blocked and empty modules are consolidated into an `Evidence Gaps` summary. Empty ledgers remain truthfully empty but do not each occupy a full primary module.

These existing capabilities remain under logical progressive disclosure unless they directly change the primary answer:

- Research Decision Lab detail;
- raw quarterly and SEC evidence;
- historical valuation mechanics;
- scenario assumptions and sensitivity;
- peer evidence mechanics;
- earnings and consensus mechanics;
- thesis, evidence, catalyst, and outcome authoring history;
- decision-process scorecard;
- lineage, provenance, identifiers, and source-rights detail;
- downloadable HTML detail.

In-app authoring keeps the current preview-confirm-save contract. A single secondary `Add research note` entry may remain close to the next task, but empty authoring forms and history do not dominate the first layer.

### Monitor — Follow-up Queue

**Question:** What requires verification, what is waiting for evidence, and when should I revisit it?

One queue composes five evidence-backed states:

- Since last review;
- Needs verification;
- Waiting on evidence;
- Scheduled context;
- Evidence freshness.

Each non-empty panel uses a compact label, visible state, short interpretation, and one relevant action. Full monitor identities and technical evidence move under Advanced.

When every actionable count is zero, render one concise empty state, explicitly state that it does not prove no external event exists, and provide one `Open Discover` action. Do not repeat the zero-state conclusion in separate Monitor Brief, Discipline Review, and Change Monitor sections.

## Reference Dashboard Usage

The supplied reference is a hierarchy reference, not a data or product-semantics source. Adopt:

- compact panels;
- strong question/state labels;
- short interpretation;
- obvious next action;
- consistent density.

Do not copy macro regime, liquidity, cross-asset, confidence percentage, CIO decision-card, trade expression, trigger, risk-budget, ranking, or portfolio semantics. No reference example becomes product evidence.

## Data, State, and Failure Behavior

- Actuals, consensus, Revenue, EPS, valuation, peers, catalysts, outcomes, backtesting, and calibration keep independent readiness states.
- Candidate context cannot alter deterministic output or trusted evidence.
- Synthetic fixtures remain test-only and are visibly identified in controlled tests.
- No company, event, peer, evidence, timestamp, freshness, outcome, source right, forecast, or recommendation is inferred to fill an empty state.
- EPS split basis stays unverified without explicit proof.
- Q4 actuals require explicit SEC-filed Q4 table evidence.
- Numerical Beat/Miss probability remains withheld until the calibration gate has valid evidence.
- If an answer builder receives inconsistent or incomplete state, it preserves independent withheld states and provides the safest next evidence task.
- Route composition does not persist a preview, change readiness, or write a generated artifact.

## Responsive and Accessibility Contract

At both `1280x720` and `390x844`, the route must expose the complete primary answer, one action, and stop rule before technical evidence. The phone layout may stack the answer components, but it must not hide safety text to satisfy the viewport.

The implementation must preserve or improve:

- keyboard focus order and visible focus;
- skip-link behavior and destination;
- one H1 and non-duplicated landmarks;
- direct route/query preservation;
- minimum primary-action target sizing;
- 200% zoom reflow and no horizontal overflow;
- forced-colors semantics;
- reduced-motion behavior;
- critical-text contrast;
- meaningful empty-state announcements.

Automated and controlled-browser results are engineering evidence only. They do not establish WCAG conformance, screen-reader usability, independent-human validation, or market comprehension.

## Implementation Slices

Implementation follows separate test-first, independently reviewable slices:

1. **Shared answer shell and Discover truth separation.** Consolidate navigation where required for Discover, label strict eligibility, render the alphabetical saved-company fallback, remove ranking-adjacent presentation, and protect route compatibility.
2. **Company Workbench primary brief.** Compose Use now, Still withheld, What changed, Next research task, stop rule, and Evidence Gaps; move secondary modules under progressive disclosure without changing calculations or authoring persistence.
3. **Monitor consolidation.** Replace three competing summaries with one Follow-up Queue and one zero-state action while retaining Advanced monitor identities.
4. **Research Desk simplification.** Replace overlapping primary cards with Today's Research Brief and keep detailed universe/readiness evidence under Advanced.
5. **Cross-route responsive and accessibility closure.** Resolve any shared shell, viewport, target-size, focus, landmark, or wording regressions revealed by current browser evidence.
6. **Documentation reconciliation.** Update public and operator documentation, ROADMAP, active continuation instructions, and PR evidence to describe the question-first workflow rather than enumerate every internal capability as a primary feature.

No slice may proceed on top of a failed prior slice. Generated-artifact hashes are checked before and after each slice.

## Test Strategy

Each slice begins with failing composition/contract tests for the changed behavior, then adds the smallest implementation that satisfies them.

Focused coverage must protect:

- exact route question and primary answer order;
- strict Discover eligibility versus saved-company browsing;
- alphabetical browse order and absence of ranking-adjacent wording;
- independent usable/withheld Workbench states;
- one authoritative Workbench next task and stop rule before Advanced;
- one Monitor zero state and return action;
- Desk summary versus Monitor detail separation;
- route/query compatibility;
- no generated writes during primary route rendering;
- responsive source order, landmarks, actions, and safety text.

After each meaningful slice, run the focused tests, full repository suite, dashboard and research render smoke, public wording/check/performance gates, pilot readiness check, accessibility browser check for UI changes, diff hygiene, whitespace checks, staged hygiene, protected-artifact hash comparison, direct desktop/mobile review, and exact-head CI.

## Documentation and Evidence

`ROADMAP.md`, `README.md`, `docs/PERSONAL_RESEARCH_MODE.md`, relevant methodology/operator documentation, the active continuation prompt, and draft PR #113 will be reconciled after verified implementation slices. Public documentation will describe the four questions and the research-only boundary, not market the number of internal modules.

The independent workflow protocol remains incomplete until 10–20 target-persona sessions are genuinely conducted. The protocol will measure time to first useful answer, usable-versus-withheld comprehension, strict-screen-versus-browsing comprehension, evidence tracing, authoring friction, trust, recommendation misinterpretation, repeat-use intent, and missing workflow. No session or result may be simulated.

## Completion Boundaries

Local UX completion requires direct evidence for the four route implementations, responsive/accessibility engineering checks, documentation reconciliation, generated-artifact integrity, and exact-head CI.

Overall product maturity remains externally incomplete until applicable point-in-time benchmark/universe, consensus, reviewed peer, hosted-operation, independent accessibility, target-persona workflow, and at-least-100-event leakage-safe calibration gates have direct evidence. Local test success cannot promote any of those gates.
