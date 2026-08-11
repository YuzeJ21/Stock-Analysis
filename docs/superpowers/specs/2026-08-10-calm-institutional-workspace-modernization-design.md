# Calm Institutional Workspace Modernization Design

## Status

The owner selected visual Option 1 on 2026-08-10. This document converts that
visual direction into an implementation contract for the Stock Research
Command Center.

The generated image is a hierarchy and visual-language reference only. Its
invented names, dates, counts, evidence categories, and actions are not product
requirements and must not enter the application. Existing application data,
readiness, provenance, source-rights, route, and research-only contracts remain
authoritative.

A repository and live-browser audit on 2026-08-10 amended the implementation
contract before source work: authoritative proof ordering is preserved,
canonical query retention is explicit, Public/Personal navigation-widget
replacement is narrowly exempted, evidence-route navigation is intentional,
Public Home has one stop-rule node, and inverse navigation colors are defined.

## Objective

Modernize the existing Streamlit product into a calm institutional research
workspace that lets a researcher answer three questions quickly:

1. What can I use now?
2. What remains withheld or stale?
3. What is the single safest next research action?

The modernization changes presentation, hierarchy, navigation density, and
responsive behavior. It does not change analytical calculations, eligibility,
research conclusions, authoring persistence, providers, artifacts, or product
scope.

## Current Problem

The product already has a credible navy, teal, and evidence-first identity, but
its visual system is spread across large inline CSS blocks and route-specific
HTML. Many surfaces use the same combination of uppercase labels, borders,
colored left rails, white panels, and heavy headings. As a result:

- navigation, mode context, page identity, status, and the primary answer often
  compete at the same visual weight;
- large bordered cards are used for both important answers and routine detail;
- desktop pages spend too much of the first viewport on framing while mobile
  pages are simultaneously oversized and clipped;
- Public mobile navigation and long labels do not fit cleanly at `390x844`;
- Research Desk, Discover, Company Workbench, and Monitor lack one consistent
  visual grammar for answer, evidence, stop rule, and next action;
- Data Health and Proof History read as generic panels instead of compact
  operational evidence surfaces; and
- repeated CSS selectors in `src/dashboard.py` make cross-route consistency and
  regression review difficult.

The problem is not missing visual decoration. It is weak prioritization and
inconsistent reuse.

## Selected Direction

### Calm Institutional Workspace

The selected direction uses:

- a warm off-white canvas;
- a midnight navigation surface;
- deep forest and restrained teal for workflow and supported evidence;
- neutral typography with monospaced numerals only for dates, values, hashes,
  and evidence identifiers;
- compact semantic status chips;
- one prominent answer panel containing or immediately followed by one next
  action and the route stop rule, then supporting evidence;
- lightweight separators before borders and borders before shadows; and
- a consistent eight-point spacing rhythm.

The product must feel like a serious research workspace, not a trading
terminal, consumer-finance app, compliance document, or decorative dashboard.

### Selective supporting patterns

The implementation uses two supporting patterns from the other visual
explorations without changing the selected direction:

- compact table-like evidence rows for dense Data Health information; and
- an evidence-led timeline for Proof History and traceable `What Changed`
  content.

These are component choices, not a second visual identity.

## Product Boundaries

The visual refresh must not:

- add buy, sell, hold, ranking, expected-return, opportunity-score, trade,
  portfolio-allocation, or broker language;
- present teal or green as a positive view, or red as a negative view, of a
  company or security;
- infer a company, event, date, price, filing, consensus value, peer,
  recommendation, reviewer, or proof record;
- turn saved-data freshness into a current-market claim;
- promote candidate context, synthetic fixtures, preview packets, or
  uncommitted artifacts into supported evidence;
- weaken independent ready, partial, blocked, stale, excluded, or withheld
  states;
- change ordinary navigation into a write, refresh, apply, review, or proof
  action;
- add a provider, external font request, analytics beacon, image service,
  network dependency, or JavaScript framework; or
- rename or remove supported Public, Personal Research, or Operator route query
  parameters. The known unsafe cross-mode advanced-route behavior is the one
  intentional compatibility correction described below.

No visual treatment may hide a research-only stop rule or make blocked evidence
look merely optional.

## Mode-Isolation Prerequisite

Current mode isolation is incomplete. Explicit Public or Personal Research deep
links can preserve Operator pages, and Public-only pages can appear under the
Personal Research shell. The visual modernization cannot build a trustworthy
shell around those known boundary failures.

Before the visual foundation slice:

- Public allows only Home, Stock Selector, Single-Stock Report, Data Health,
  and Proof History; every Personal Research, advanced, legacy, or unknown page
  request redirects to Public Home;
- Personal Research allows only Research Desk, Discover, Company Workbench,
  Monitor, Data Health, and Proof History; every Public-only, advanced, legacy,
  or unknown page request redirects to Research Desk;
- Data Health and Proof History preserve their existing mode-aware ticker and
  return-link behavior in both allowed modes;
- Operator keeps its currently supported route set, including Overview, Market
  Direction, Universe Manager, and the five legacy compatibility pages;
- supported Public and Personal Research direct links keep their existing
  route, ticker, open-state, and evidence-return parameters; and
- the redirected URL is canonicalized so reload and browser history cannot
  restore the disallowed page under the wrong mode.

Route resolution consumes the raw `mode` and `page` query values before an
unknown page can collapse to `Home`. It returns a structured result containing
the normalized mode, requested page, canonical page, recognized state,
allowed state, redirect state, and canonical retained-query mapping. An
explicit unknown mode fails closed to Personal Research at Research Desk.

Allowed direct requests are not rewritten merely for being loaded; their
existing query state survives. Canonical redirects for disallowed or unknown
pages clear all route-specific keys and retain only the normalized mode plus
its canonical fallback page. Public Home uses canonical `?mode=public` with no
`page=home`; Personal Research uses
`?mode=research&page=research-desk`. Mode switches on Data Health or Proof
History preserve that shared evidence page and its permitted keys. Other mode
switches open the target mode's canonical home and clear route-specific keys.

The canonical link and redirect allowlists are exact:

| Mode and page | Permitted route-specific keys |
| --- | --- |
| Public Home, Stock Selector | none |
| Public Single-Stock Report | `ticker`, `open` |
| Public Data Health | `ticker`, `lane`, `drawer`, `queue_details`, `batch_details`, `proof_details`, `metric_details` |
| Public Proof History | `ticker` |
| Personal Research Desk, Discover, Monitor | none |
| Personal Company Workbench | `ticker`, `open`, `cash_preview` |
| Personal Data Health | `ticker`, `lane`, `drawer`, `queue_details`, `batch_details`, `proof_details`, `metric_details` |
| Personal Proof History | `ticker` |

`mode` and `page` are controlled canonical keys, not route-specific retained
keys. Operator retains its current supported route and query behavior. Ticker
round trips use the authoritative registry normalization and preserve valid
punctuation such as the slash in `BRK/B`; a link builder and its consuming
query parser cannot disagree about the same registered ticker.

This is a fail-closed route-boundary repair, not a new route or a removal of
Operator capability. It receives its own focused tests and review before visual
changes begin.

## Information Architecture

### Global hierarchy

Every primary page uses this visible order:

1. compact product/workspace navigation;
2. one context row for profile, saved-data cutoff or freshness, and mode;
3. one page title and one plain-language purpose line;
4. the primary answer or explicit withheld state;
5. one primary next action;
6. the research-only stop rule;
7. the smallest supporting evidence that changes interpretation; and
8. progressively disclosed detail.

The default DOM and visual order is question, answer, action, stop rule,
supporting evidence, then detail. When the stop rule is inside `AnswerPanel`, it
follows the action inside that panel. Public Home uses one semantic stop-rule
node and one DOM order on every viewport: action, stop rule, then metrics. On
desktop only, CSS grid placement presents metrics before the stop rule; the
accessibility-tree order remains action, stop rule, metrics. Public Home phone
uses the already-approved matching visual order. Evidence
routes place their mode-level research boundary before the first ledger row.
Operator and legacy routes place their operator or compatibility warning before
detail rather than inventing a research stop rule.

The answer, action, and applicable boundary must not be displaced by broad
coverage totals or technical evidence.

### Navigation

Personal Research renders one labelled in-content workflow `nav` from one route
configuration. On desktop, CSS positions this same DOM node as the compact left
rail. At `640px` and below, the same node returns to normal document flow as a
contained horizontal workflow strip. No breakpoint-specific duplicate nav is
rendered. Personal Research exposes only:

- Research Desk;
- Discover;
- Company Workbench; and
- Monitor.

Data Health and Proof History remain secondary evidence destinations and still
render this same one primary workflow nav. No core item receives
`aria-current="page"` on an evidence route; the evidence page H1 and context row
identify the current secondary destination. The Personal Research Streamlit
sidebar does not render route choices. Workspace
mode switching is a separately labelled `Workspace mode` disclosure at the end
of the same rail DOM; at phone width it follows the route strip in the same
node. Its links change mode and are not labelled as page navigation.

The rail always presents all four route names, but Company Workbench never
infers a default ticker. When no selected ticker exists, its item is a
non-link, `aria-disabled="true"` destination with the instruction to choose a
company in Discover first. When a registered ticker exists, its link preserves
that ticker and `open=1`.

Public renders one labelled in-content five-step workflow `nav`; the Streamlit
sidebar is not rendered. The same Public nav becomes a contained horizontal
strip at phone width. Public's separately labelled `Workspace mode` disclosure
lives in `ContextBar`, outside the workflow nav. Operator retains its existing
workspace switch and route controls at the top of the Streamlit sidebar as its
single route/control authority and does not render the Public or Personal
workflow nav. Operator-only advanced and legacy routes remain visibly and
behaviorally separated through the prerequisite redirect contract.

Every mode and breakpoint has exactly one visible labelled route navigation.
The current route is communicated through text plus shape or border, not color
alone.

Exactly one skip link exists per mode and keeps the existing
`#public-page-answer` destination and same-document focus behavior. In Public
and Personal Research, it is outside the unrendered sidebar and is the first
focusable element before visible route navigation. In Operator, Streamlit's DOM
ordering makes the sidebar the first focus bucket, so the skip link remains the
first sidebar child before native workspace and route controls. No client-side
DOM reordering is introduced. Public and Personal Research replace the
navigation and workspace mode radios with URL-only links; this is an explicit
exception to preserving the removed `dashboard-workspace-mode` and route-radio
widget keys. Operator retains its existing native workspace and route controls
and their widget state. All non-navigation Streamlit widget keys, session
state, form, receipt, fingerprint, and rerun contracts remain unchanged.

At phone width, the application uses a compact, labelled workflow strip with
horizontal overflow contained inside the navigation region. Labels wrap or
scroll as complete controls; they are never clipped. The page itself must not
gain horizontal overflow. A custom JavaScript drawer is outside scope.

### Page responsibilities

| Surface | Primary visual answer | Supporting treatment |
| --- | --- | --- |
| Research Desk | Today's Research Brief | evidence snapshot plus one next action |
| Discover | strict screen result or truthful empty state | clearly separate saved-company browser |
| Company Workbench | Use now, Still withheld, What changed, Next task | detailed modules under progressive disclosure |
| Monitor | Follow-up Queue or one truthful zero state | compact rows grouped by follow-up reason |
| Public Home | what the product does and where to start | stop rule before phone metrics, as already approved |
| Stock Selector | readiness-backed browse result | compact filters and result rows, never ranking |
| Single-Stock Report | usable versus withheld company evidence | progressive disclosure for detailed sections |
| Data Health | current lane status and safest next step | compact operational evidence rows |
| Proof History | latest durable proof and reconciliation state | evidence timeline or ledger |
| Operator and legacy routes | explicit operator or compatibility boundary | existing detail preserved behind the boundary |

## Visual System

### Color tokens

The implementation centralizes semantic tokens. The values below are the design
baseline and remain subject to the explicit contrast matrix that follows.

| Token | Initial value | Use |
| --- | --- | --- |
| `--sr-canvas` | `#F6F7F4` | application background |
| `--sr-surface` | `#FFFFFF` | primary reading surface |
| `--sr-surface-muted` | `#F1F4F1` | secondary grouped surface |
| `--sr-ink` | `#0F172A` | primary text |
| `--sr-text` | `#243244` | body text |
| `--sr-muted` | `#475569` | secondary text |
| `--sr-border` | `#D9E1DC` | separators and necessary borders |
| `--sr-nav` | `#0B1B2B` | navigation background |
| `--sr-nav-text` | `#F8FAFC` | primary text on navigation background |
| `--sr-nav-muted` | `#CBD5E1` | secondary text on navigation background |
| `--sr-forest` | `#155E4B` | primary workflow action |
| `--sr-teal` | `#0F766E` | supported evidence and workflow progress |
| `--sr-amber` | `#854D0E` | partial, waiting, or stale state |
| `--sr-red` | `#B42318` | blocked or unavailable state |
| `--sr-blue` | `#315D8A` | neutral traceable change context |
| `--sr-focus` | `#0B6BFF` | keyboard focus outline |

State meaning must always be repeated in text. Supported state is not a positive
investment opinion.

Semantic color mapping is role-aware, never a flat lookup by label text:

- `evidence` uses supported, partial, blocked, stale, excluded, and withheld
  semantics;
- `freshness` uses current, mixed, stale, missing, and unavailable semantics;
- `workflow` uses forest only for the current route or primary safe action;
- `trace` uses blue for source-backed change context; and
- `analytic` and `legacy` labels such as `Keep`, `Strong Rotation`,
  `Risk Reduce`, `peer_discount`, or unknown status strings remain neutral with
  explicit text.

Red is reserved for operationally blocked or unavailable evidence. It never
represents a negative company, security, valuation, or price view. Unknown roles
fail closed to a neutral `Unknown` or existing withheld label rather than
guessing a semantic role from the string.

Before a token is accepted, an automated foreground/background matrix must
prove at least `4.5:1` for normal text and `3:1` for large text, focus outlines,
icons, borders that communicate state, and other non-text components. The
matrix covers `--sr-surface`, `--sr-surface-muted`, `--sr-canvas`, and
`--sr-nav` for every foreground token permitted on each surface. Unsupported
combinations are not used even if an individual token passes on another
surface. In particular, navigation copy uses only `--sr-nav-text` or
`--sr-nav-muted`; body, muted, teal, and forest foreground tokens are not
assumed readable on `--sr-nav`.

### Typography

No remote font is loaded. The interface uses the local system stack:

```css
font-family: Inter, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
```

Financial values, dates, hashes, and evidence IDs use:

```css
font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
```

The type scale is intentionally small:

- body: `0.9375rem` with at least `1.5` line height;
- supporting text: `0.8125rem`;
- labels: `0.75rem`, sentence case by default;
- section heading: `1.125rem`;
- page title: `1.75rem` desktop and `1.375rem` phone;
- primary answer: `1.25rem` desktop and `1.0625rem` phone.

Uppercase is reserved for rare short eyebrow labels. Narrative text containers
use `max-width: 65ch`; tables, identifiers, and compact status rows are exempt.

### Spacing and shape

Spacing uses `4, 8, 12, 16, 24, 32, 40` pixel steps. Components do not introduce
new arbitrary increments without a measured browser need.

- compact control radius: `6px`;
- panel radius: `10px`;
- large answer surface radius: `12px`;
- pill radius is reserved for short status chips;
- routine content uses dividers or whitespace instead of card borders; and
- elevation is limited to navigation overlays or a primary action hover state.

Animations are not required for completion. Any later motion must respect
`prefers-reduced-motion` and cannot delay evidence visibility.

## Component Model

The visual refresh introduces a small presentation-only component vocabulary.
Each component accepts already-derived display data and performs no provider,
readiness, authoring, persistence, or artifact work.

### `WorkspaceShell`

Owns canvas, navigation dimensions, content width, and global focus treatment.
It preserves existing Streamlit landmarks, skip-link destination, route query
parameters, and rerun behavior.

### `ContextBar`

Displays only context that changes interpretation: selected profile, saved-data
cutoff or freshness, mode, and selected ticker when applicable. It does not
reproduce the full readiness dashboard.

### `AnswerPanel`

Contains the page question, evidence-backed answer or withheld state, concise
reason, and one primary action. When the current route contract includes a stop
rule in its primary answer, the stop rule stays inside the panel; on other
routes it follows the panel immediately.

### `StatusChip`

Renders a short semantic label such as `Ready`, `Partial`, `Blocked`, `Stale`,
`Excluded`, or `Withheld`. Text is required; color is supplementary. State
labels remain mapped from authoritative existing values.

The helper requires both an explicit semantic role and state. It does not infer
the role from a state label or apply evidence colors to analytic/legacy text.

### `EvidenceRows`

Renders compact grouped rows for lane, state, evidence count or cutoff, reason,
and optional evidence link. It is used for Data Health, selected Workbench
details, and other dense operational evidence. It does not invent a readiness
summary.

### `EvidenceTimeline`

Consumes the authoritative preordered proof or change payload and never
recalculates which record is latest. Reviewed lane proof ordering remains
`(proof_date, proof_id)` descending; reviewed batch proof ordering remains
`(review_date, batch_id)` descending. The first authoritative row is pinned as
the primary record and the remaining rows retain that supplied order. Other
traceable change payloads retain their existing domain ordering contract.
Rows without a timestamp remain visible in the position supplied by the
authoritative adapter and display `Timestamp unavailable`; no date or tie-break
is inferred. Missing or non-traceable history renders a truthful empty state.
The component is not a news feed and does not imply completeness.

### `NextAction`

Presents exactly one primary route or review action derived by existing
application logic. Secondary evidence links remain visually subordinate.
Pure HTML output can represent safe route links only; it cannot emulate a write,
review, confirmation, form submit, or stateful Streamlit action.

### `EmptyState`

Explains what saved evidence is absent, what the absence does not prove, and the
safest available next route. Related zero states are consolidated rather than
repeated as full cards.

### Stable browser hooks

Shared components expose stable, unique `data-sr-region` values for
`workflow-nav`, `context`, `page-title`, `primary-answer`, `primary-action`,
`stop-rule`, `supporting-evidence`, and `advanced-detail`. Tests use these
semantic hooks instead of styling classes or visible text copied from the AI
concept.

## Presentation Architecture

The current application keeps route composition in `src/dashboard.py`. The
modernization preserves that ownership but extracts reusable visual CSS and
pure HTML presentation helpers into `src/dashboard_visual_system.py`.

The new module contains:

- token and component CSS string builders;
- pure HTML helpers for the shared components above; and
- semantic state-to-style mapping that consumes existing state names.

The module has no Streamlit import. Streamlit calls and route integration remain
in `src/dashboard.py`.

Stateful Streamlit controls stay in `src/dashboard.py`. Existing `st.button`,
`st.link_button`, selectbox, filter, form, submit, authoring, preview, receipt,
and confirmation controls are placed immediately adjacent to the relevant pure
presentation panel inside a Streamlit container; they are never nested inside a
pure HTML string. Existing widget keys, session-state names, rerun behavior,
form boundaries, receipt identity, ledger fingerprint, and append-only tests
remain unchanged. The only approved widget exception is the removal of Public
and Personal Research navigation/workspace radios in favor of the URL-only
links defined above; Operator retains those native controls.

`apply_dashboard_theme()` and route renderers remain thin integration points in
`src/dashboard.py`. Existing helpers are migrated only when directly required
by an implementation slice. This avoids an unrelated rewrite of the large
dashboard file.

No new frontend framework, build tool, asset pipeline, network request, or
runtime dependency is introduced.

## Data Flow and State

The data path remains unchanged:

```text
named local profile and saved files
  -> existing validation, readiness, provenance, rights, and route builders
  -> existing route display payloads
  -> presentation-only shared components
  -> Streamlit render
```

Presentation components cannot:

- load or mutate a provider;
- calculate readiness, valuation, nowcast, peer eligibility, or screen results;
- modify session or query state except through existing navigation controls;
- append to a research ledger;
- persist a preview or proof;
- write, refresh, apply, or promote an artifact; or
- convert a missing value to an apparent zero.

Authoring continues to use the existing preview, exact receipt, confirmation,
ledger-fingerprint, and append-only contracts.

## Responsive Contract

### Desktop

At `1280x720` and `1440x1024`:

- the page title, primary answer, primary action, and research-only boundary are
  visible without opening technical detail;
- Personal Research navigation width uses
  `clamp(12.5rem, 16vw, 14.5rem)`;
- content uses a readable maximum width rather than stretching every line to
  the full available width;
- dense rows align values consistently and avoid nested scrolling; and
- only evidence that changes the answer appears before progressive disclosure.

### Phone

At `390x844` from zero scroll:

- product title, route navigation, labels, badges, answer copy, action copy, and
  stop-rule text wrap without clipping;
- the document width and body scroll width remain `390px`;
- the workflow navigator is compact and contained;
- the approved Public Home order remains action, stop rule, then metrics;
- Company Workbench exposes Company Brief before advanced modules;
- primary controls retain a minimum 44-pixel target; and
- status, error, and current-route meaning never depend on color alone.

The design does not claim every primary panel will fit completely inside one
phone viewport when truthful copy makes that impossible. It prioritizes the
answer, one action, and stop rule and removes duplicated framing before reducing
safety text.

## Accessibility Contract

The implementation must preserve or improve:

- one main landmark and one H1 per route;
- the existing skip-link behavior and destination;
- logical focus order through navigation, answer, action, applicable stop rule,
  and evidence;
- visible focus at ordinary and forced-color settings;
- labelled navigation regions;
- non-color state text;
- 200 percent zoom reflow;
- reduced-motion behavior;
- readable contrast for ordinary, muted, status, and disabled text; and
- table semantics or list semantics appropriate to evidence rows.

Automated checks and browser screenshots are engineering evidence only. They do
not establish WCAG conformance or replace screen-reader and independent-human
review.

## Failure and Empty-State Behavior

- Missing input remains unavailable or withheld; no skeleton becomes a value.
- A stale saved profile uses an explicit stale label and its existing safe
  interpretation.
- A partial lane does not inherit the supported visual state of another lane.
- Discover's empty strict screen does not hide saved-company browsing.
- A zero Monitor queue states that no qualifying saved follow-up is present; it
  does not claim no external event exists.
- Missing proof renders `No durable reviewed proof available` or the existing
  authoritative equivalent, never a blank timeline implying review.
- Unexpected or malformed presentation input uses the existing fail-closed
  route error treatment and must not reveal an unsupported primary action.
- Visual refresh failures must not write a fallback artifact or silently switch
  data profile.

## Implementation Sequence

The program is divided into independently reviewable, test-first slices:

0. **Mode-isolation prerequisite.** Enforce the complete per-mode allowed-page
   sets, raw-query structured resolution, exact retained-key allowlists,
   canonical fail-closed redirects, punctuation-safe ticker round trips, and
   mode-correct evidence return links before visual work.
1. **Byte-identical presentation seam.** Extract only the directly shared CSS
   and pure helpers into `src/dashboard_visual_system.py` while requiring
   byte-equivalent exported CSS and unchanged rendered DOM. Migrate affected
   source-contract tests without changing visual output.
2. **Visual foundation and Research Desk.** Introduce the approved tokens,
   single responsive Personal nav, shared components, and modern Research Desk;
   prove desktop and phone behavior.
3. **Personal Research workflow.** Apply the approved system to Discover,
   Company Workbench, and Monitor while preserving their current answer-first
   contracts.
4. **Controlled Public and evidence workflow.** Apply the system to Home, Stock
   Selector, Single-Stock Report, Data Health, and Proof History; introduce the
   approved compact rows and timeline from existing payloads and preserve the
   approved phone stop-rule order.
5. **Operator and legacy alignment.** Harmonize tokens and spacing without
   weakening operator/legacy quarantine or moving compatibility output into a
   primary workflow.
6. **Cross-route closure.** Reconcile documentation, remove superseded local
   style duplication, and complete browser, accessibility, performance, and
   artifact-integrity evidence.

No slice proceeds on top of a failed previous slice. Later slices can change
component internals, but changing token semantics, global hierarchy, or the
selected visual identity requires an explicit design-spec amendment.

## Artifact-Integrity Baseline

The checked-in 18-path manifest is a historical release reference, not the
preservation authority for this visual program. At design time its command
reports 17 checksum mismatches and one match because those exact 18 generated
paths already contain intentional unstaged working artifacts. The visual
program must not restore, regenerate, stage, or silently adopt those files in
order to make the historical command green.

Before Slice 0, run and record the historical manifest outcome without changing
it:

```bash
shasum -a 256 -c \
  .superpowers/sdd/2026-08-01-portable-html-action-policy-repair/protected-artifacts.sha256
```

Then derive the exact 18 protected paths from that checked-in manifest and
capture their current working-tree SHA-256 values in a task-start manifest under
`/tmp/stock-research-modernization-*`. Also capture the complete path,
directory, file type, symbolic-link target, and SHA-256 baseline for `data/`,
`outputs/`, and `docs/assets/` using the procedure in
`docs/superpowers/plans/2026-08-02-no-write-derived-artifact-boundary.md`, with
task-specific files under the same prefix. The capture command and resulting
manifest location must be recorded in the slice report before any source edit.
The task-start current-byte snapshot, not the historical release hashes, is the
preservation authority.

After every slice and at final closure:

- the task-start current-byte manifest for all 18 paths must report every entry
  as `OK`;
- the complete path, directory, link, and hash baselines must compare equal;
- the checked-in historical manifest file must remain unchanged, and its
  pass/fail outcome may not be represented as a visual-program regression or
  success criterion;
- no new generated, screenshot, timing, report, canonical-data, or review path
  may appear; and
- `git status --short` must keep those exact 18 paths unstaged and must not add a
  different generated path.

An external data-release workflow can supersede this baseline only through a
separate reviewed decision; the visual program cannot absorb that change.

## Test Strategy

Every slice begins with a focused failing test for the contract it changes.

### Pure presentation tests

- token names, contrast matrix, and role-aware semantic state mapping;
- neutral treatment for unknown and analytic/legacy labels;
- required text labels for every status;
- no network font or asset URL;
- no forbidden recommendation or trading language;
- no duplicated ID, main landmark, H1, or navigation label;
- mobile wrapping and contained workflow navigation source contract; and
- shared component HTML escaping and malformed-input fail-closed behavior.

Existing tests that inspect literal CSS or selectors inside `src/dashboard.py`
must migrate intentionally to assertions against the exported CSS/helper output
from `src/dashboard_visual_system.py` or the rendered browser DOM. Old CSS is
not copied into both modules merely to keep source-string tests green. Thin
`apply_dashboard_theme()` and route wrappers remain covered in
`src/dashboard.py`.

### Route contract tests

- unchanged supported route/query mapping;
- raw unknown pages remain distinguishable from recognized Home until route
  policy resolves them;
- canonical Public-to-Home and Personal-Research-to-Research-Desk redirects for
  every disallowed cross-mode, advanced, legacy, and unknown page;
- invalid explicit modes fail closed to canonical Personal Research Desk;
- allowed direct requests preserve their current query mapping, while redirect
  and mode-switch results keep only the exact page allowlist above;
- punctuation-bearing registered tickers round-trip through link generation and
  query parsing;
- preserved shared Data Health and Proof History ticker/return behavior;
- Personal evidence routes expose only the Personal return path and never add a
  Public report return link;
- unchanged Operator access to advanced and legacy routes;
- one visible navigation authority;
- evidence routes render the same one Personal workflow nav with no false core
  `aria-current` item;
- tickerless navigation shows a disabled Company Workbench destination and does
  not infer a company;
- the mode-appropriate sole skip link is first in the Public/Personal document
  or Operator sidebar focus bucket and keeps its same-document target;
- default question, answer, next action, stop rule, evidence, then detail source
  order, plus Public Home's desktop-only visual grid exception;
- unchanged widget keys, session-state names, form boundaries, authoring receipt
  and fingerprint behavior, and native-control rerun semantics outside the
  explicit Public/Personal navigation-widget replacement;
- Discover strict-screen and saved-browser separation;
- Workbench independent usable and withheld lanes;
- Monitor's single truthful zero state;
- one Public Home stop-rule node, with action, stop rule, metrics DOM order and
  action, metrics, stop desktop visual placement;
- Data Health and Proof History remain evidence-only; and
- operator and legacy isolation remains intact.

### Runtime and visual verification

- fresh-process render at `1280x720`, `1440x1024`, and `390x844` using the demo
  profile for Research Desk, Discover, AVGO Company Workbench, Monitor, Public
  Home, Stock Selector, AVGO Single-Stock Report, Public Data Health, Public
  Proof History, Personal Data Health, Personal Proof History, Operator
  Overview, Market Direction, Universe Manager, and one legacy compatibility
  page;
- each critical `data-sr-region` bounding box satisfies `left >= -1` and
  `right <= clientWidth + 1` at every viewport;
- `documentElement.scrollWidth <= documentElement.clientWidth + 1` and the same
  assertion holds for `body` and the main application container;
- page titles, nav controls, labels, badges, actions, and stop rules do not use
  `text-overflow: ellipsis`, line clamping, or hidden/clipped text overflow; the
  workflow strip is the only allowed horizontal scroll container;
- every primary control has a computed height and width of at least `44px`;
- at `1280x720`, the primary answer, action, and applicable boundary are fully
  inside the initial viewport on primary Public and Personal Research routes;
- at `390x844`, the top of `primary-answer`, `primary-action`, and `stop-rule`
  is inside the initial viewport on primary routes, and Public Home's complete
  stop rule ends at or above `844px`;
- exactly one `[data-sr-region="stop-rule"]` exists on routes with a stop rule;
- keyboard focus and skip-link behavior;
- forced-colors and reduced-motion engineering checks;
- no traceback, browser console error, or loading-state capture; and
- qualitative reference-versus-implementation screenshot review at matching
  viewports for hierarchy, token use, spacing rhythm, and density only.

The real demo fixture text and current application state remain authoritative
during screenshot review. Pixel matching and content parity with the generated
concept are prohibited because the concept contains invented illustrative data.

### Regression and release verification

- focused unit and route suites;
- full repository test suite;
- dashboard and research render smoke;
- public wording, performance, and accessibility gates;
- pilot-readiness check executed as a diagnostic, with its fail-closed blocked
  decision preserved and reported unless separately reviewed external evidence
  has actually changed;
- diff, whitespace, and staged hygiene;
- before/after hashes for the 18 protected generated artifacts; and
- exact-head CI before any release decision.

## Performance Budget

The visual refresh adds no network dependency. Each replaced framing element is
removed when its shared component is introduced; the implementation does not
render both old and new shells. Every slice must preserve the existing
exact-head performance gate and avoid adding a second rendering pass,
client-side script, animated background, or unbounded list above progressive
disclosure.

## Documentation

After verified implementation, reconcile:

- `README.md`;
- `ROADMAP.md`;
- `docs/PERSONAL_RESEARCH_MODE.md`;
- `docs/PUBLIC_DEMO_WALKTHROUGH.md`;
- relevant accessibility and operator documentation; and
- the active continuation contract.

Documentation must describe the implemented hierarchy and route boundaries. It
must not treat an AI visual concept as product evidence or claim current-market,
hosted, licensed, calibrated, validated-user, or commercial readiness.

## Out of Scope

- new routes or a second application;
- dark-mode preference;
- provider or data expansion;
- new valuation, screen, ranking, peer, forecast, or nowcast logic;
- chart redesign beyond token alignment required by a changed page;
- bespoke illustration, photography, video, or decorative hero imagery;
- new user identity, authentication, settings, notification, reminder, or
  collaboration features shown only in the generated concept;
- custom JavaScript navigation shell;
- hosted deployment or release promotion; and
- proof of independent accessibility, target-user validation, or market
  performance.

## Acceptance Criteria

The design is locally complete when:

1. all primary routes use the Calm Institutional visual tokens and shared
   hierarchy without changing research behavior;
2. Research Desk, Discover, Workbench, and Monitor expose one clear answer and
   one primary action before technical detail;
3. Public Home, Stock Selector, Single-Stock Report, Data Health, and Proof
   History use the same system while retaining their distinct workflow roles;
4. operator-only advanced and legacy content is explicitly quarantined by both
   presentation and canonical route behavior;
5. desktop and phone evidence shows no clipping or page-level horizontal
   overflow;
6. semantic state, research-only, provenance, freshness, and stop-rule meanings
   remain explicit;
7. no generated artifact, provider, calculation, or authoring contract changes;
   route behavior changes only through the approved mode-isolation prerequisite;
8. focused, full, render, browser, accessibility, wording, performance, and
   hygiene gates pass, while the pilot-readiness diagnostic is recorded without
   requiring a pilot-ready verdict; and
9. the task-start current-byte manifest for the exact 18 protected paths and the
   task-start complete artifact baseline remain path-, type-, target-, and
   byte-identical, while the checked-in historical manifest itself remains
   unchanged, unless a separate reviewed data-release workflow explicitly
   authorizes a replacement baseline.

Hosted operation, commercial source rights, independent human review, target
user validation, and calibration remain separate external maturity gates.
