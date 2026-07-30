# Discover And Monitor Workflow Maturity Design

## Status

The user approved the workflow portion of approach A on 2026-07-28. This
written specification is the review gate before an implementation plan is
created.

## Decision

Make Discover answer three research-routing questions from existing saved
evidence, and make Monitor expose deterministic research-process attention
without ranking companies or inferring urgency from market performance.

Discover foregrounds:

1. why the company is reviewable;
2. what evidence can be used now; and
3. the principal blocker.

Monitor preserves focused-cohort order and adds an independent process-attention
label and reason derived only from saved research-process evidence.

## Problem

The Discover queue already contains `Why Included`, `Supported Now`, and
`Blocked / Missing`, but the compact result rows currently display only a
readiness pill and supported summary. Researchers must open several rows to
understand why each company is reviewable and what stops the next step.

Monitor already composes six independent Research Decision Lab lanes, but its
table exposes only process state, due lanes, and a generic next process step.
It does not consistently surface unresolved source-change work before overdue
reviews, and it has no explicit contract for catalyst or outcome follow-up.

## Scope

### Discover

Use only existing saved selector-row fields. Do not add a score, sort, rank, or
generated explanation.

Each visible row contains:

- ticker and optional theme;
- saved readiness label;
- `Why reviewable`: concise `Why Included` text;
- `Usable now`: concise `Supported Now` text;
- `Principal blocker`: concise `Blocked / Missing` text; and
- one uniquely named `Open {TICKER} review` action.

Missing fields fail closed with neutral copy. `no blocker` becomes
`No principal blocker is recorded in saved readiness`; it does not imply that
the company has no risk or external research need.

### Monitor

Extend the read-only discipline-row composition with:

- `attention_state`;
- `attention_reason`; and
- `attention_source`.

Keep `cohort_order`, six Decision Lab lanes, state identity, and next process
step unchanged. The table remains in saved focused-cohort order.

## Attention Precedence

The first matching saved process condition determines the displayed attention
reason:

1. `evidence_change_due`: an unresolved source-backed evidence change exists;
2. `conflict_review_needed`: recorded conflicting evidence needs review;
3. `overdue_review`: the reviewer-authored thesis review date is past;
4. `invalidation_follow_up`: a current thesis lacks a source-backed
   invalidation condition;
5. `outcome_evidence_follow_up`: an existing outcome row is blocked by exact
   source rights or field scope;
6. `scheduled_catalyst`: a cutoff-safe, reviewed upcoming catalyst exists,
   displaying its exact effective date as scheduled context, not urgent market
   prediction;
7. `scheduled_review`: a future reviewer-authored review date exists; or
8. `monitor`: no saved process item is due.

The display labels group these states as `Needs review`, `Scheduled`, or
`Monitor`. They are workflow timing labels, not severity, attractiveness,
expected return, risk grade, or investment priority.

No attention state is derived from price movement, volatility, technical
indicators, valuation upside/downside, company size, market capitalization, or
candidate context.

## Catalyst And Outcome Boundaries

- A catalyst affects Monitor only when it is a validated, cutoff-safe event in
  the selected profile/ticker scope.
- An upcoming catalyst is `Scheduled`; it is not called urgent, likely, or
  price-moving.
- A recent catalyst alone does not prove that follow-up is outstanding because
  the current ledgers do not record a catalyst-review completion link.
- An empty catalyst ledger produces no event and no attention reason.
- `outcome_evidence_follow_up` requires an existing outcome record with an
  explicit commercial source-rights or field-scope blocker.
- An empty outcome ledger is neutral. The product cannot infer that an outcome
  is overdue without an explicit closed observation window and review
  requirement.

## Architecture

Create a pure attention derivation helper alongside the Decision Lab
composition. It accepts:

- one `ResearchDecisionLabState`;
- an optional `CatalystTimeline`; and
- the existing outcome state already represented by the Learning lane.

It returns an immutable attention contract. `build_research_discipline_rows`
uses it while retaining input order.

`load_dashboard_research_discipline_rows` may read the existing catalyst and
outcome ledgers read-only. A missing ledger remains empty. Because the existing
catalyst loader validates the shared append-only ledger as one unit, a
malformed catalyst ledger makes catalyst attention unavailable for every
cohort ticker while journal, outcome, and source-change states remain
independent. It does not skip the malformed row or fabricate an attention
reason.

The dashboard renders the pure result and performs no urgency logic.

## Responsive UI

Discover rows use a compact labelled stack. Labels remain visible rather than
relying on position or color. At `390x844`, text wraps within the row and the
single action remains at least 44 CSS pixels high without horizontal overflow.

Monitor leads with one compact summary of counts by workflow label, followed by
the preserved-order table. Raw Decision Lab identity, lane detail, catalyst
source metadata, rights blockers, and exact evidence stay under Advanced.

## Error Handling

- Missing Discover fields receive truthful neutral fallbacks.
- Empty Discover filters keep the existing no-match recovery action.
- Missing or malformed process evidence returns `unavailable` for the affected
  independent evidence dimension, never `monitor`. A malformed shared catalyst
  ledger affects catalyst attention for the cohort without erasing valid
  journal, outcome, or source-change state.
- Unknown lane or attention states fail closed.
- One ticker's invalid evidence cannot change another ticker's state or order.
- Candidate-only catalyst context cannot become trusted evidence or change
  deterministic forecasts.

## Testing

Test-first coverage must prove:

- Discover displays the three exact saved evidence questions;
- missing and `no blocker` values use truthful neutral fallbacks;
- one unique ticker-bound action remains;
- search and filters continue to use saved fields without changing source
  order;
- every attention precedence branch with literal fixtures;
- unresolved source changes outrank overdue reviews;
- overdue reviews outrank invalidation follow-up;
- catalyst scheduling never becomes urgency or a market prediction;
- empty catalyst and outcome ledgers produce no fabricated attention;
- outcome follow-up requires an explicit existing source-rights/scope blocker;
- focused-cohort order is unchanged;
- no price, return, rank, score, recommendation, or transaction field affects
  attention;
- desktop and phone rendering has labelled content, 44-pixel actions, and no
  horizontal overflow; and
- the Research Desk -> Discover -> Company Workbench -> Monitor route flow,
  primary-answer-first Workbench, and Advanced evidence placement remain
  intact.

## Acceptance Criteria

1. Discover answers why reviewable, usable now, and principal blocker from
   existing saved evidence.
2. Monitor exposes deterministic process attention without company ranking.
3. Saved focused-cohort order and the immutable six-lane Decision Lab contract
   remain unchanged.
4. Catalyst and outcome attention requires explicit saved evidence and never
   invents an event, due state, or market effect.
5. Empty and malformed inputs fail closed per ticker.
6. No recommendation, score, return prediction, portfolio action, or trading
   behavior is added.
7. Focused, full, browser, render, release, hygiene, and exact-head CI gates
   pass with no generated artifact changes.

## Current Implementation Status

Local implementation commit `d353ed652` contains the three saved-evidence Discover
answers, truthful missing and `no blocker` fallbacks, fixed process-attention
precedence, preserved cohort order and Decision Lab identity, read-only
catalyst composition, malformed-ledger fail-closed behavior, summary cards,
and process-attention table columns. Focused pure, dashboard, route-contract,
and Streamlit AppTest rendering passed without production-ledger or generated
artifact writes.

This is not yet release closeout. Direct Discover/Monitor desktop and phone
assertions are integrated for three non-empty answers, ticker-bound 44-pixel
actions, semantic process-only columns, saved cohort order, and Advanced
identity separation. Exact staging hygiene passed with zero generated paths.
The clean-tree gate then verified product hygiene and excluded exactly 18
generated paths, but the managed environment terminated headless Chrome before
route execution. A supported browser run, push, draft-PR update, and exact-head
CI remain open.
