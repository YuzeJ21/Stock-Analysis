# Accessibility Task Protocol

This protocol defines repeatable manual accessibility review for the supported
Personal Research workflow:

`Research Desk -> Discover -> Company Workbench -> Monitor`

It is an execution template, not test evidence. A completed row proves only the
named task in the recorded environment. No result may be inferred from a screenshot,
source inspection, an automated contract, or a different route.
No WCAG conformance claim may be made from a partial run.

## Safety boundary

- Use a local or explicitly approved private review environment.
- Use saved readiness only. Do not refresh, import, apply, or rebuild data.
- Do not save a research record. Workbench authoring may be inspected only up
  to validation or a write-free preview.
- Do not enter personal, account, brokerage, portfolio, or confidential
  research information.
- Do not stage screenshots, timing output, CSV, JSON, reports, sample reports,
  or other generated artifacts.
- Findings must not weaken research-only, provenance, source-rights,
  calibration, explicit-Q4, EPS split-basis, or fail-closed boundaries.

## Required run metadata

Record every field before starting:

| Field | Required value |
| --- | --- |
| Run ID | Stable local identifier |
| Date and timezone | ISO date plus timezone |
| commit SHA | Exact checked-out revision |
| Route base URL | Local or approved private URL |
| Operating system | Name and version |
| Browser | Name and version |
| Input method | Keyboard and any assistive input |
| Screen reader | Name/version or `not_run` |
| Display | Resolution and scaling |
| Viewport | CSS width and height |
| Zoom | Browser zoom percentage |
| Color mode | Default, forced colors, or named contrast mode |
| Motion preference | Default or reduced motion |
| Reviewer | Non-sensitive identifier |

Stop if the checked-out revision changes during the run. Start a new run ID
after any code change or environment change that can affect the result.

## Result vocabulary

Use exactly one state per task:

- `passed_direct`: the reviewer directly completed the named task and observed
  every expected result in the recorded environment.
- `failed_reproducible`: the task failed and the reviewer recorded exact
  reproduction steps plus observed behavior.
- `not_run`: the task was not attempted.
- `blocked_environment`: the named browser, assistive technology, operating
  mode, or review capability was unavailable.
- `not_applicable`: the task does not apply, with a written reason.

Never promote `not_run`, `blocked_environment`, automated checks, screenshots,
or a result from another route to `passed_direct`.

## Core keyboard tasks

Run these tasks without a mouse or touch input.

| ID | Mode | Task | Expected direct result | Failure evidence |
| --- | --- | --- | --- | --- |
| K01 | `keyboard_only` | Reload Research Desk and press Tab until the skip link or first repeated shell control receives focus. | Focus is visible; the actual order is recorded. If repeated shell controls precede the skip link, record a defect rather than inferring success from DOM presence. | Focused control sequence and first unexpected control |
| K02 | `keyboard_only` | Activate `Skip to page answer`. | The URL retains Personal Research mode and the current route parameters; focus moves to or immediately before the route answer without changing evidence state. | URL, focused element, and visible position |
| K03 | `keyboard_only` | Traverse the route rail and open Discover. | Every route choice is reachable, visibly focused, and operable without trapping focus. | Last reachable control and blocked action |
| K04 | `keyboard_only` | Use Discover search and open one readiness-backed company. | Search, result, and open action have understandable names; no ranking or recommendation language is announced. | Control name, announced text, and route |
| K05 | `keyboard_only` | Traverse the Company Workbench primary answer and each collapsed disclosure. | Reading/focus order follows the visible research answer; Advanced evidence remains optional; disclosures expose state and respond to Enter or Space. | First order mismatch or inoperable disclosure |
| K06 | `keyboard_only` | Open the authoring composer, enter a deliberately incomplete draft, and validate without previewing or saving. | Required-field errors are programmatically associated or otherwise announced at the affected control; no confirmation action appears before an exact valid preview. | Error text, focused control, and announcement |
| K07 | `keyboard_only` | Cancel or leave the composer, then open Monitor. | No research record is written; navigation remains operable and focus is not trapped. | Unexpected write, trapped focus, or lost route |
| K08 | `keyboard_only` | Traverse Monitor in its truthful empty or current saved state. | Weekly summary, Research Discipline Review, change state, and next action are understandable without implying a ranking or fabricated event. | Announced text and first misleading state |
| K09 | `keyboard_only` | Reverse through the current route with Shift+Tab. | Visible focus remains present and no keyboard trap appears. | Trap boundary and last reachable control |

## Zoom and reflow tasks

Run at the named browser zoom with the viewport and operating-system scaling
recorded. Local scrolling inside a genuinely two-dimensional data table may be
recorded separately; it does not excuse document-level horizontal overflow.

| ID | Mode | Task | Expected direct result |
| --- | --- | --- | --- |
| Z01 | `zoom_200` | Complete Research Desk -> Discover -> Company Workbench -> Monitor at 200% zoom. | Primary answers, labels, controls, and research-only boundaries remain readable and operable without document-level horizontal scrolling. |
| Z02 | `zoom_400` | Repeat the core answer path at 400% zoom. | Content reflows to a single-column reading path; no primary content or action is clipped, overlapped, or hidden. |
| Z03 | `zoom_400` | Open each Workbench Advanced disclosure used in K05. | Disclosure content remains reachable; any table-local scrolling is bounded and does not move the whole document horizontally. |

## Color, contrast, and motion tasks

| ID | Mode | Task | Expected direct result |
| --- | --- | --- | --- |
| C01 | `forced_colors` | Traverse all four routes with the platform forced-colors mode active. | Focus, selected route, boundaries, status distinctions, and primary actions remain perceivable without color alone. |
| C02 | `forced_colors` | Inspect disabled, blocked, partial, and usable states. | Text or semantic labels preserve each distinction when authored colors are overridden. |
| M01 | `reduced_motion` | Load and navigate all four routes with reduced motion enabled. | No required information depends on animation; loading and disclosure state remain understandable. |

## Screen-reader tasks

Use a supported desktop screen reader and record its exact name, version, and
speech settings. Do not substitute an accessibility-tree snapshot for these
tasks.

| ID | Mode | Task | Expected direct result |
| --- | --- | --- | --- |
| S01 | `screen_reader` | Read the page title, route heading, and research-only boundary on each route. | One route-level heading is announced and the boundary is available without reading Advanced evidence. |
| S02 | `screen_reader` | Use the landmarks and headings lists. | Available landmarks and the heading hierarchy match the current page. If no main landmark is announced, record the open defect. |
| S03 | `screen_reader` | Activate the skip link on each route, including a ticker-bound Workbench URL. | The destination and retained route/ticker parameters are announced or directly verifiable; focus transfer is understandable. |
| S04 | `screen_reader` | Operate Discover search and open a company. | Search purpose, result identity, readiness boundary, and open action are announced without recommendation language. |
| S05 | `screen_reader` | Traverse Workbench cards, disclosures, and withheld states. | Section names, status, evidence boundary, and one next research task are understandable in reading order. |
| S06 | `screen_reader` | Trigger the incomplete authoring validation used in K06. | The invalid state, error, and affected field are announced; no record is saved. |
| S07 | `screen_reader` | Observe a Streamlit rerun or validation update. | Material status changes are announced or the missing announcement is recorded as a reproducible defect. |

## Target-size and pointer follow-up

Measure the visible hit target, not only the hidden native input:

| ID | Task | Expected direct result |
| --- | --- | --- |
| P01 | Measure framework help controls and dataframe toolbar controls used in the workflow. | Each material target meets the applicable target-size requirement or has a documented exception and adjacent-spacing evidence. |
| P02 | Measure route choices, primary links, disclosure headers, search controls, and authoring actions at phone width. | Targets do not overlap and can be activated without triggering an adjacent control. |

## Finding record

Create one record per failed task:

```text
finding_id:
run_id:
commit_sha:
task_id:
route:
severity:
environment:
precondition:
steps:
expected:
observed:
focus_or_announcement:
artifact_location:
research_boundary_impact:
proposed_fix:
retest_run_id:
retest_state:
```

Use `critical`, `high`, `medium`, or `low` severity. Severity reflects blocked
task completion and misuse risk, not investment impact.

## Completion rule

The accessibility priority remains incomplete until:

1. Every applicable task has `passed_direct` evidence in a suitable current
   environment or a reviewed, explicitly bounded exception.
2. Every material failure has a fix and direct retest or a documented product
   boundary with an owner.
3. Desktop and phone workflow evidence covers the same exact revision.
4. Automated semantic contracts and manual results agree.
5. Any public accessibility statement matches only the tested scope.

The existence of this protocol is not completion evidence.
