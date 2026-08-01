# Company Workbench HTML Research Brief Design

## Decision

Add a read-only, evidence-gated HTML Research Brief to Company Workbench. The
brief is assembled and rendered in memory from the existing selected-company,
readiness, DCF, Scenario Lab, Research Decision Lab, and evidence objects. It can
be previewed inside Company Workbench and downloaded explicitly as one
self-contained HTML file that opens directly in a browser.

The feature does not replace Streamlit, the four-route research workflow, the
Python calculation engine, canonical source data, or reviewer-authored ledgers.
It does not automatically write HTML, CSV, JSON, Markdown, report, screenshot,
or timing artifacts to the repository.

## Why This Is The Next Product Slice

The current product is stronger than a standalone analyst page at evidence
readiness, source rights, withheld states, research records, and workflow
continuity. Its Company Workbench is less concise than the reviewed reference
HTML pages at communicating scenario values, the enterprise-to-equity bridge,
sensitivity, business drivers, and the remaining evidence gaps in one portable
view.

The repository has no Excel-generation dependency or XLSX writer. Its visible
artifact churn comes from explicit CSV/readiness/report writer commands, while
ordinary dashboard browsing is already read-only. Moving the human-facing
research brief to in-memory HTML therefore improves presentation without
turning HTML into a data store or weakening the existing evidence contract.

## Alternatives Considered

### 1. In-memory Workbench HTML brief plus explicit standalone download — selected

Keep Streamlit as the application shell, reuse the existing Python domain
objects, render a compact in-app HTML preview, and offer one explicit HTML
download. This gives the product a direct-browser, printable research artifact
with low architectural risk and no automatic repository writes.

### 2. Separate standalone HTML application beside Streamlit — deferred

A second local application could provide more control over navigation and
client-side interactions, but it would duplicate routing, workspace isolation,
accessibility, release, and browser-test surfaces before the read-only brief has
proved useful.

### 3. Replace Streamlit with an HTML or JavaScript application — rejected for this stage

A full rewrite would recreate the current workflow, authoring, readiness,
source-rights, and accessibility contracts. It is not necessary to deliver the
approved research-brief outcome.

## Architecture

Create `src/company_workbench_html.py` with two isolated responsibilities:

1. Build an immutable `CompanyWorkbenchHtmlSnapshot` from already-computed
   application objects.
2. Render that snapshot deterministically as a complete HTML document or a
   compact in-app fragment.

The snapshot builder may select, label, and format existing results. It must not
read repository files, fetch sources, refresh data, calculate a second DCF,
change readiness, append a ledger, or infer a missing value.

The renderer returns a Unicode string. It has no output-path argument and no
writer. Company Workbench encodes the string in memory for a Streamlit download
button. The browser or user-selected download location is the only place a file
can be created.

The first version uses embedded CSS and no executable JavaScript, external font,
remote stylesheet, image request, analytics call, or third-party asset. The
download must work offline. The in-app preview uses non-executable HTML and must
not request `unsafe_allow_javascript=True`.

## Authoritative Calculations

The existing Python valuation and Scenario Lab results remain authoritative.
The HTML layer displays their values; it does not port DCF, WACC, terminal-value,
sensitivity, momentum, historical-valuation, or readiness logic to JavaScript.

Scenario cards use the labels Bear, Base, and Bull and describe supported
outputs as `Scenario value/share`. They must not use `target price`, `price
target`, `upside`, `downside`, `margin of safety`, `buy`, `sell`, or equivalent
transaction or recommendation language.

A non-null DCF calculation status alone is not sufficient to expose a per-share
scenario value. The HTML display gate also requires a complete existing
enterprise-to-equity bridge and a non-null existing per-share result. If cash
and debt or net debt, diluted shares, or any other required bridge result is
unavailable, the corresponding equity or per-share value remains visibly
withheld.

## Snapshot Contract

The immutable snapshot contains only fields required by the approved brief:

- workspace-safe company identity, ticker, profile label, review cutoff, and
  model version;
- one primary `Usable now` answer and one `Still withheld` answer;
- market-observation recency and independent readiness states;
- existing Bear, Base, and Bull scenario assumptions and results;
- projected free cash flows, discounted explicit cash-flow total, discounted
  terminal value, enterprise value, cash/debt or net-debt bridge state, equity
  value, diluted-share state, and scenario value/share when supported;
- the existing WACC by terminal-growth sensitivity matrix;
- business-trend, forward-view, catalyst, thesis, evidence, invalidation,
  review-trigger, outcome-learning, and next-task summaries;
- source ID, safe source reference, source as-of/retrieval state, rights state,
  model/input identity, and precise blocker text for displayed sections;
- a fixed research-only and no-recommendation boundary.

The snapshot does not contain credentials, environment variables, API keys,
cookies, account identifiers, absolute local paths, repository paths, raw source
payloads, hidden Streamlit state, or unrestricted user-provided markup.

## Page Structure

The full HTML document is ordered for a 15-minute company review:

1. Company identity, review cutoff, data freshness, source-rights state, and the
   research-only boundary.
2. `Usable now`, `Still withheld`, and the exact next research task.
3. Bear, Base, and Bull scenario cards.
4. DCF value bridge and projected free-cash-flow schedule.
5. WACC by terminal-growth sensitivity matrix.
6. Business trend, key drivers, risks, catalysts, and evidence gaps.
7. Research Decision Lab summary: Plan, Evidence, Invalidation, Scenario, Review
   Trigger, and Learning.
8. Advanced evidence and methodology details.

Technical evidence remains below the primary research answer. Empty thesis,
catalyst, outcome, historical-valuation, peer, consensus, or quarterly-actuals
lanes render an explicit empty or withheld state; they never render sample or
synthetic content.

## Company Workbench Integration

Add one collapsed `HTML Research Brief` section after the authoritative next
research task and before the existing detailed-report gate. The section contains:

- a compact static HTML preview;
- a short statement that the brief is a snapshot of current saved evidence and
  scenario math, not a recommendation or current-market claim;
- `Download HTML Research Brief`, supplied with in-memory UTF-8 bytes and a
  deterministic safe filename based on ticker and review date.

Preparing the preview or download data must not refresh sources, rebuild
readiness, write a preview file, or record an event. A user must not need to
expand Advanced evidence before reaching the download.

Scenario changes continue through the existing session-local Scenario Lab.
When those controls produce a new valid Python result, a subsequent HTML brief
reflects that result and its modified-scenario state. The downloaded document
does not expose editable controls in this version.

## Fail-Closed Rendering

Each section has an independent display state: `available`, `partial`,
`withheld`, `stale`, `not recorded`, or `excluded`. No section can inherit a
green state from another section.

- Stale market observations are historical context only and show no current-
  market conclusion.
- DCF scenario math does not unlock peer-relative valuation, historical
  valuation, consensus, quarterly trends, catalysts, outcomes, backtesting, or
  calibration.
- Candidate peer or catalyst context cannot become trusted evidence or alter a
  deterministic scenario.
- Numerical Beat/Miss probability remains withheld without valid calibration.
- Q4 actuals require explicit filed-Q4 evidence.
- EPS split basis remains unverified without explicit proof.
- Synthetic fixtures remain test-only and cannot appear in a real-company
  downloaded brief.

## Security And Privacy

All dynamic text is escaped in text, attribute, table, and metadata contexts.
Safe hyperlinks, if retained, must use an allowlisted `https` scheme and a
display-safe reference; all other references render as plain text. No field may
inject a script, style block, event handler, URL scheme, or raw HTML fragment.

The document includes no scripts in version 1. Content Security Policy metadata
must prohibit scripts, remote connections, framing, form submission, and object
embedding while permitting only the inline stylesheet needed by the document.

The renderer must omit secret values and machine-local details even in Personal
Research Mode. Its output is a portable artifact and cannot rely on the current
workspace authorization context after download.

## Visual, Print, And Accessibility Contract

The visual direction borrows the useful information architecture of the
reviewed analyst HTML pages without copying their certification or action
language. The brief uses the existing Stock Research Command Center colors and
typography hierarchy, compact scenario cards, clearly separated business and
valuation sections, and evidence labels that remain visible in print.

The document must provide:

- one descriptive level-one heading and a logical heading hierarchy;
- semantic header, main, section, table, caption, and footer elements;
- a skip link and visible keyboard focus;
- readable labels that do not rely on color alone;
- responsive reflow at desktop and phone widths with no document-level
  horizontal overflow;
- usable 200% zoom and print layout;
- forced-colors and reduced-motion compatibility;
- no hidden provenance, blocker, or research-only boundary in print.

Because version 1 has no animation or JavaScript, reduced-motion behavior is
inherently static. Automated browser evidence does not replace independent
human or screen-reader validation.

## Testing

### Pure renderer tests

Cover:

- deterministic complete-document and compact-fragment output;
- proper escaping of text, attributes, source references, and filenames;
- absence of scripts, event handlers, remote requests, credentials, absolute
  paths, and untrusted raw markup;
- complete and incomplete DCF value bridges;
- exact equality between every displayed DCF/sensitivity value and its supplied
  Python result;
- independent ready, partial, stale, withheld, not-recorded, and excluded
  states;
- empty valuation, catalyst, thesis, outcome, consensus, peer, and quarterly
  evidence;
- explicit Q4, EPS split-basis, candidate-context, calibration, synthetic-
  fixture, and research-only boundaries;
- prohibited recommendation, target-price, ranking, transaction, and position
  language;
- deterministic safe download filename and UTF-8 document metadata;
- zero file, network, readiness, refresh, or ledger side effects.

### Dashboard tests

Cover one Workbench render with the collapsed section, one complete preview and
download payload, one partial bridge, one fully withheld state, and one modified
session-local scenario. Confirm that the ordinary Workbench route does not call
any writer or refresh path.

### Browser and accessibility tests

Capture direct current-run evidence at desktop and phone widths for complete,
partial, and withheld briefs. Verify headings, skip target, keyboard focus,
tables, print stylesheet, forced colors, reduced motion, no console/page error,
and no horizontal overflow. Validate the downloaded document by opening the
actual in-memory bytes in a browser; a Streamlit preview alone is insufficient.

### Artifact tests

Snapshot the tracked working tree before and after preview, download-payload
preparation, focused tests, dashboard smoke, and HTML browser review. The same
pre-existing generated-artifact set must remain byte-for-byte unchanged and no
repository HTML output may appear.

Extend public-wording and hygiene coverage so the new renderer source and its
rendered fixture states are scanned. A future explicit file-output command, if
separately approved, must add HTML to generated-artifact classification before
it can write inside the workspace.

## Verification

After implementation, run:

- focused HTML snapshot, renderer, dashboard, security, and browser tests;
- `python3 -m pytest tests -q`;
- `make dashboard-smoke`;
- the research dashboard render and accessibility browser gates;
- `make public-wording-check`;
- `make public-check`;
- `make pilot-readiness-check TOP_N=10`;
- `make diff-hygiene-summary`;
- `git diff --check`;
- `make staged-hygiene-check` after exact staging.

Do not use writer-heavy `make readiness`, `make pipeline`, `make verify`,
`make validate-all`, broad refreshes, or report generators merely to validate
this feature. Those commands are outside the no-generated-artifact acceptance
path.

## Documentation And Release Evidence

Update README, methodology, ROADMAP, relevant accessibility and browser-QA
documentation, and the continuation prompt after implementation. Describe HTML
as a portable presentation of saved evidence and existing scenario math, not a
new source, calculation engine, readiness activation, model certification, or
market validation result.

Update draft PR #113 with the implemented files, exact-head tests, direct
downloaded-document browser evidence, and zero-new-artifact result. Keep the PR
draft. Do not merge or deploy without explicit approval.

## Completion Boundary

This slice is complete only when Company Workbench produces the approved compact
preview and a self-contained offline HTML download from existing Python results;
all readiness and empty states remain truthful; security, visual, accessibility,
and wording tests pass; and no repository artifact is created or changed by the
feature or its verification path.

Completion does not make the DCF a professional line-item forecast model, prove
source rights, provide current market data, validate a screening strategy,
establish calibration, constitute investment advice, or complete hosted and
independent-user gates.
