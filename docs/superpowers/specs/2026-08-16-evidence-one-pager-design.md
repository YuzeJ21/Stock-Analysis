# Evidence One-Pager Design

**Status:** Approved. The owner approved Approach A: place a compact,
evidence-bound summary at the front of the existing Company Workbench HTML
Research Brief while preserving the current Workbench and complete report.

**Visual reference:**
`/var/folders/cw/xfqgmp_57rn7nn3fq68z_6280000gn/T/codex-clipboard-80b40520-4c8b-493e-89af-a87e159e329b.png`

**Visual reference SHA-256:**
`d467ce50f7803b3a269b5cfd748a87c1ce4a269345943ca6993d365056c72d59`

The reference currently lives in temporary attachment storage. If that exact
file is unavailable at visual closeout, the owner must reattach it and its
SHA-256 must match before same-viewport comparison. The implementation must not
copy the reference into tracked product assets.

**Implementation base:** `origin/main` at
`9147a47c327774e31e5ad76a370561b572d3ccbd`

## Objective

Make the product's evidence-first advantage understandable in the time it
takes to read one compact summary. The existing offline HTML Research Brief
will open with an Evidence One-Pager that compresses the selected company's
answer, scenario assumptions, supported evidence, falsifiers, unanswered
questions, provenance, and next research task.

This is a presentation and projection change. It does not create another
research engine, report format, route, source, readiness state, calculation,
ledger, or recommendation surface. Missing or unproven evidence remains
visible as withheld.

## Approved Approach

The Evidence One-Pager becomes the first section of the existing HTML Research
Brief. The same document continues immediately into the complete current
report. The current in-app Company Brief, explicit module-open gate, HTML
Research Brief expander, download control, MIME type, file-name convention,
offline security policy, and full report remain in place.

This direction was selected over:

- replacing the Company Workbench first view, which would risk the approved
  four-answer workflow and progressive-disclosure contract; and
- creating a separate one-pager download, which would fragment evidence and
  require users to choose between a summary and its supporting report.

"One-Pager" means one bounded summary section. The implementation must not
clip, truncate, hide, or shrink content to promise exactly one physical sheet.

## Product Position

The summary is an auditable research artifact, not an investment pitch. It
must make the following product strengths legible on first read:

- data readiness before analysis;
- independent available, partial, stale, excluded, not-recorded, and withheld
  states;
- explicit source, date, rights, field-scope, model, and input identity;
- scenario assumptions rather than targets;
- explicit process status for reviewer-authored thesis and invalidation rather
  than generated conviction;
- unanswered questions and the next evidence task; and
- a direct continuation into the complete evidence report.

## Information Hierarchy

The summary uses this fixed semantic and visual order.

### 1. Snapshot header

Show:

- `{TICKER} Evidence One-Pager`;
- review cutoff;
- source-through date;
- saved freshness state;
- portable rights state;
- model version;
- snapshot identity; and
- the visible research-only boundary.

Use `Saved evidence snapshot`. Never use `Certified`, `engine certified`,
`approved`, or another unscoped quality badge.

### 2. Company Brief answer strip

Show exactly four independently stateful answers:

1. Use now;
2. Still withheld;
3. What changed; and
4. Next research task.

Use now, Still withheld, and Next research task come from the existing frozen
portable inputs. What changed comes only from the already-computed Workbench
change answer supplied to the portable builder together with the selected
ticker and profile key. The portable renderer must not load, recalculate, rank,
or infer a change. Missing, unsafe, unscoped, or mismatched change input renders
a not-recorded answer.

### 3. Scenario values under assumptions

Show the existing Bear, Base, and Bull scenarios only. For each scenario show:

- exact state;
- scenario value per share only when the existing `per_share_state` permits it;
- revenue growth;
- FCF margin;
- WACC;
- terminal growth; and
- forecast years.

When value per share is withheld, keep safe assumptions visible and show the
existing blocker. Do not show current price, percentage versus spot, upside,
downside, target, margin of safety, expected return, Blue Sky, probability, or
confidence.

This slice does not create a stricter share-basis readiness rule. When the
existing `per_share_state` permits display, the one-pager may show the supplied
value and must display the existing `share_basis_state` beside it, including
`unverified`. This is scenario-math disclosure, not a readiness promotion or
valuation conclusion.

### 4. Research case

Project only existing portable sections:

- Decision Lab Plan;
- Decision Lab Evidence;
- Business Trend; and
- Key Drivers.

These cards are process-status projections from the existing frozen snapshot.
They do not promise the underlying thesis or evidence prose. Do not generate,
rewrite, rank, extract from narrative text, or pad claims. Actual
reviewer-authored prose is out of scope for this slice because the current
portable snapshot does not carry field-complete portable lineage for it.

### 5. Operating and valuation evidence

Project only the existing portable Business Trend, Key Drivers, DCF bridge, and
valuation-regime status, answer, safe facts, and blocker fields. Scenario and
bridge numbers already frozen in the current snapshot may be shown under their
existing independent states. Do not extract a quarterly value from narrative
text or imply field-level source linkage that the snapshot does not contain.
A later structured-quarterly slice requires explicit field, period, unit,
definition, source, rights, field-scope, and cutoff bindings.

Do not introduce a capital-allocation scoreboard, ROIC, acquisition return,
buyback, stock-compensation, dilution, customer, ARPC, attach-rate, product
unit, or service-mix metric in this slice. Those fields need separate structured
and reviewed evidence contracts.

### 6. What could break the research case

Show only existing portable Risks and Decision Lab Invalidation process-status
content. Missing invalidation status renders `Not recorded`. Actual
reviewer-authored invalidation prose is out of scope for this slice. The product
must not generate falsifiers from scenario output or narrative context.

### 7. Questions still requiring evidence

Show:

- Decision Lab Review Trigger;
- Evidence Gaps; and
- the authoritative Next research task.

The next task remains evidence/process work. It must not become a buy, sell,
hold, size, allocation, entry, exit, stop, profit, or transaction instruction.

### 8. Provenance and full-report handoff

End with:

- compact source/readiness status;
- blockers and assumptions;
- model and input identity;
- the research-only boundary; and
- `Continue to the full evidence report below.`

The complete existing report follows in the same document. The summary must
never imply that it replaces full diligence.

## Data And Trust Contract

The existing `CompanyWorkbenchHtmlSnapshot` remains the sole frozen source of
portable report truth. The one-pager may select, order, label, and format values
from that snapshot. It may not read files, call providers, refresh data,
rebuild readiness, append a ledger, recalculate DCF, derive spot comparisons,
or mutate session or repository state.

The snapshot builder may be extended only to freeze the already-computed What
changed answer. That extension must:

- accept a supplied mapping plus explicit selected ticker and profile key as
  part of `CompanyWorkbenchHtmlInputs`;
- normalize and sanitize its title, body, workflow state, context kind,
  `source_backed_eligible`, and source references;
- fail closed on absent, unsafe, unscoped, or mismatched input;
- bind the normalized value into snapshot identity; and
- perform no loading or independent change calculation.

The portable What changed display state is exact:

| Context kind | Additional condition | Portable display state |
| --- | --- | --- |
| `none` | None | `not_recorded` |
| `snapshot_only` | Safe scoped input | `partial` |
| `source_backed` | `source_backed_eligible=true` and at least one portable safe source reference | `partial`, with a blocker that portable publication/retrieval dates, rights, field scope, and cutoff proof are not frozen |
| `source_backed` | Eligibility or portable reference incomplete | `partial`, with an incomplete-reference blocker |
| Unknown or unsafe | Any | `withheld` |

Workflow states `monitor`, `review_now`, and `wait_for_evidence` remain visible
as safe labels; they do not independently promote the evidence state.
No What changed answer may become `available` in this slice. A later wider
contract may permit that only after it freezes source identity,
publication/retrieval timestamps, permitted rights, permitted field scope, and
cutoff validation.

Each section stays independently gated:

| Summary block | Required evidence | Failure behavior |
| --- | --- | --- |
| Whole summary | Exact ticker/profile scope, safe cutoff, deterministic snapshot identity | Return explicit summary-unavailable markup; keep the full report available. |
| Freshness | Existing selected saved-recency state | Show saved, stale, or withheld; never relabel as current. |
| What changed | Supplied eligible Workbench change answer | Preserve none, snapshot-only, or source-backed; otherwise not recorded. |
| Scenario value | Existing finite scenario result and permitted `per_share_state` | Reuse the current display gate, disclose `share_basis_state`, and expose blockers. |
| Portable business evidence | Existing frozen section state, answer, safe facts, and blockers | Withhold independently; never extract values from narrative text. |
| Thesis or invalidation | Existing frozen Decision Lab process status | Show status only; never synthesize or expose unbound prose. |
| Numeric evidence | Existing scenario or bridge field and its current independent state | Withhold that number and retain the blocker. |
| Capital allocation | Separately approved structured evidence contract | Omit in this slice. |

Candidate context, synthetic fixtures, stale observations, one ready lane, or a
valid DCF can never promote another section.

## Preservation Contract

The change must preserve all current behavior:

- exact Research Desk, Discover, Company Workbench, Monitor, Data Health, Proof
  History, Public, and Operator routing;
- exact ticker/profile scoping and no inferred ticker;
- the in-app Company Brief with Use now, Still withheld, What changed, and Next
  research task;
- one authoritative Data Health handoff;
- the complete research-only stop rule;
- the explicit `Open evidence and analysis modules` gate;
- What Changed, Research Decision Lab, Business Trend, cash-generation preview,
  Valuation, Forward View, What Remains Withheld, journal, outcome review,
  authoring, scorecard, Research Conclusion, and scenario behavior;
- all session keys, reruns, validate-preview-confirm flows, and no-write
  defaults;
- the existing HTML Research Brief expander label, download label, Streamlit
  key, MIME type, filename convention, CSP, no-JavaScript policy, deterministic
  rendering, and complete report sections; and
- fail-closed behavior for missing, stale, unverified, excluded, unsafe,
  mismatched, or rights-blocked evidence.

No existing function may be removed because it is absent from the visual
reference. The reference image supplies editorial hierarchy only; its data,
claims, scenarios, labels, colors, and implied decisions are not evidence.

## Explicit Do-Not-Copy Contract

Do not copy or introduce:

- `Certified one-pager`, `engine certified`, or a global success badge;
- `Why own it`, `Invest`, `CIO decision`, or ownership language;
- rankings, recommendations, scores, allocations, sizing, entries, exits,
  stop-losses, take-profits, or transaction behavior;
- current-price comparisons, target prices, percentage upside/downside, or
  expected-return framing;
- Blue Sky when the governed engine supplies Bull;
- Monte Carlo percentiles, model probabilities, or confidence-looking
  precision;
- generated strongest claims, generated thesis prose, or generated
  falsifiers;
- unsupported company-specific KPIs or capital-allocation metrics;
- hard-coded mixed-language copy; or
- a fixed dense canvas, tiny text, color-only status, or hidden print evidence.

## Visual Direction

Borrow the reference's editorial rhythm, not its certainty theater:

- a restrained dark summary surface with strong typographic hierarchy;
- one bright accent rule, used decoratively rather than as an approval signal;
- high-contrast text and thin separators;
- compact answer and scenario strips;
- large plain-language section headings;
- explicit state text beside every color cue; and
- a visible transition from compact summary to complete evidence.

Use the established Workbench navy, green, amber, cyan, system-sans, and
editorial-serif tokens. Do not add raster assets, logos, gradients, decorative
icons, or another design system.

## Responsive, Print, And Accessibility Contract

- The full document has one H1. The in-app fragment uses one H2 beneath the
  Workbench H1.
- Use semantic header, main, section, list, table, caption, aside, and footer
  structures where applicable.
- DOM order is header, answers, scenarios, research case, operating evidence,
  falsifiers, questions, provenance, then the full report. CSS must not reorder
  it.
- At `1440x1024` and `1280x720`, scenarios may use three columns and narrative
  sections may use two columns.
- At `390x844`, every summary block becomes one column with no document-level
  horizontal overflow or clipped boundary.
- The in-app fragment is verified at 100% and 200% browser zoom at
  `1280x720`, plus 100% at `390x844`.
- The standalone document is verified at 100% and 200% browser zoom at
  `1440x1024` and 100% at `390x844`; one 400% browser-zoom summary case must
  remain readable without lost content.
- "No two-dimensional scrolling" applies to the summary and document shell.
  Preserved full-report tables may retain their labelled horizontal-scroll
  regions.
- Status is always conveyed by text as well as color. Forced-colors preserves
  borders and labels.
- Normal text on the new dark surface must meet at least 4.5:1 contrast; large
  text and visible component boundaries must meet at least 3:1.
- The page adds no animation and remains compatible with reduced-motion.
- Existing controls retain at least a 44-by-44-pixel target and visible focus.
- The document declares its primary language. Future multilingual spans require
  correct `lang` attributes.
- Print retains provenance, blockers, assumptions, and the research-only
  boundary. No `max-height`, clipping, ellipsis, hidden overflow, or font
  shrinking may be used to force one physical page.
- Automated checks remain engineering evidence only; they do not establish
  screen-reader, human-keyboard, WCAG, or assistive-technology completion.

## Renderer Architecture

`src/company_workbench_html.py` remains the sole owner of the frozen snapshot,
safe formatting, CSS, fragment, document, bytes, and download specification.
The renderer gains pure summary helpers scoped to the existing document root.
The existing fragment and downloaded document both place the summary before the
current full-report sections. This deliberately preserves the current in-app
preview rather than replacing it with a summary-only surface. The duplicated
summary/full-report facts are an intentional progressive-disclosure trade-off:
the Streamlit expander remains collapsed by default, and the full content
remains available when opened.

The summary projector must be total for every valid
`CompanyWorkbenchHtmlSnapshot`. A bounded `TypeError` or `ValueError` raised by
summary formatting produces explicit summary-unavailable markup and must not
prevent `_html_brief_content(...)` from rendering the full report.

`src/dashboard.py` supplies the already-computed What changed answer when it
builds `CompanyWorkbenchHtmlInputs`. It continues to build one portable
snapshot and one download. No second expander, download button, Streamlit key,
route, or renderer pipeline is introduced.

Tests may add pure helpers and fixtures, but production code must not add a
second source loader, report schema, calculation engine, provider call,
persistence path, or repository artifact.

## Test Strategy

Test-first implementation must prove:

1. the four-answer portable snapshot binds an explicitly scoped,
   already-computed What changed value, preserves eligible safe source
   references, and fails closed on missing, unsafe, or mismatched input;
2. complete, partial, stale, and fully withheld snapshots render the fixed
   summary order with independent states;
3. every displayed value exactly equals an existing supplied snapshot value,
   and no narrative text becomes a new numeric or field-level claim;
4. withheld or unknown values never become zero, positive evidence, or a
   global green state;
5. no prohibited certification, recommendation, target, upside, probability,
   sizing, or transaction language appears;
6. text, references, paths, secrets, controls, and unsafe markup retain the
   existing escaping and portable-action policy;
7. a bounded summary-formatting failure renders an unavailable summary while
   the existing full report remains present with unchanged section ordering and
   security policy;
8. bytes, filename, MIME type, CSP, print output, and snapshot identity remain
   deterministic for identical inputs;
9. the in-app Company Brief, module gate, open-state functions, download
   control, and session behavior remain intact;
10. Public and Operator never receive the Personal Research portable brief;
11. browser evidence passes for complete, partial, stale, and withheld states
    using the exact in-app and standalone viewport/zoom matrix above, normal
    and forced colors, contrast, print, focus, runtime, overflow, console, and
    no-network checks; and
12. protected `data/`, `outputs/`, and `docs/assets/` bytes and topology remain
    unchanged.

The existing HTML brief browser gate should be extended rather than replaced.
If a later release promises exactly one printed sheet, that separate phase must
add deterministic content budgets and PDF page-count evidence.

## Implementation Scope

Expected production and focused-test paths:

- `src/company_workbench_html.py`;
- `src/dashboard.py`;
- `tests/test_company_workbench_html.py`;
- `tests/test_dashboard_render_smoke.py`;
- `tests/test_research_mode_dashboard_contract.py`;
- `tests/test_company_workbench_html_browser_gate.py`; and
- browser/accessibility contract files only if their exact current assertions
  require the new summary marker.

Active documentation may be updated only to describe the additive summary and
its limits. No provider, valuation, scenario, journal, readiness, source-rights,
data, output, or asset file is in scope.

## Explicit Non-Goals

- no missing-data fabrication or readiness activation;
- no source, provider, refresh, import, apply, materialize, rebuild, or
  generated-artifact mutation;
- no new route, page, report type, download, ledger, authoring type, scenario,
  or persistence model;
- no replacement of the current Company Workbench first view;
- no guarantee of one physical printed page;
- no Figma dependency or token;
- no deployment, publishing, push, PR, mark-ready, merge, or hosted-product
  claim; and
- no human, source-rights, market-fit, accessibility-conformance, or investment
  performance claim from local automation.

## Completion

The local slice is complete only when:

- every new behavior has a focused RED before production code;
- focused and affected tests pass on final bytes;
- the extended HTML browser matrix passes across required states, widths,
  zooms, print, forced colors, and no-network checks;
- current same-viewport captures are compared against the visual reference and
  all P0/P1/P2 design mismatches are either fixed or documented as intentional
  product-truth differences; if the temporary reference is unavailable, the
  owner reattaches the exact SHA-matching image before this check;
- all existing Workbench functions remain in the correct closed/open state;
- protected artifacts remain byte-for-byte unchanged;
- an independent reviewer finds no Critical or Important issue; and
- the exact changed paths are committed locally without push or merge.
