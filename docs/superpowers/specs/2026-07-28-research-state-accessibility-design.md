# Research State Accessibility Design

## Status

The user approved the accessibility portion of approach A on 2026-07-28. This
written specification is the review gate before an implementation plan is
created.

## Decision

Keep loading, empty, withheld, stale, and failure information as ordinary
accessible page content when it is present on initial render. Add live-region
semantics only for state changes caused by a user's action in the current
session.

The first implementation is limited to the Company Workbench research-record
authoring flow because it has direct validation, preview, stale-draft, save,
and reload transitions with existing deterministic state.

## Problem

The current product already exposes:

- a polite loading status for saved public readiness;
- visible empty, withheld, and stale states;
- one global validation alert plus field association and focus for exact
  required-field errors; and
- visible success or warning messages after save-and-reload.

Turning every static state into an `aria-live` region would create repeated and
noisy announcements without proving better usability. The real gap is that
user-triggered transitions do not share one explicit, tested announcement
contract.

## Scope

Create one focused presentation helper for authoring state messages. It
produces visible HTML with deterministic semantics for:

1. exact validation rejection;
2. preview ready;
3. draft changed after preview;
4. confirmed save reloaded successfully; and
5. save recorded but read-side reload could not verify it.

Existing field-error association and focus behavior remain unchanged. The
helper does not save, validate, focus, navigate, or mutate session state.

Static loading, empty-ledger, withheld, stale, blocked, and failure cards gain
automated semantic coverage but no live-region role unless they are actually
inserted or changed after a user action.

## Announcement Contract

`ResearchStateMessage` contains:

- `state`: a closed state token;
- `title`: visible concise text;
- `detail`: visible recovery or boundary text;
- `role`: `status` or `alert`;
- `live`: `polite` or `assertive`; and
- `atomic`: always true so the complete changed message is exposed together.

Mapping:

| State | Role | Live policy |
| --- | --- | --- |
| `validation_rejected` | `alert` | `assertive` |
| `preview_ready` | `status` | `polite` |
| `draft_changed` | `status` | `polite` |
| `save_reloaded` | `status` | `polite` |
| `save_reload_unverified` | `alert` | `assertive` |

The rendered element includes `aria-atomic="true"` and one stable,
scope-specific identifier when `announce=True`. When the same exact transition
identity is rendered again, `announce=False` keeps the visible message but
uses `role="group"` with no `aria-live` attribute. It contains no visually
hidden duplicate of the same message.

Only a new state transition is rendered as a new announcement. Ordinary
Streamlit reruns with the same state and receipt must not create a second
announcement. Session-state deduplication belongs to the UI orchestration, not
the pure rendering helper.

## Authoring Behavior

- Exact validation failures keep the existing global alert, field association,
  `aria-invalid`, descriptive relationship, and focused rejected field. The new
  helper replaces rather than duplicates the global visual error.
- A valid preview politely announces that the exact record is ready for review
  and still unsaved.
- Editing after preview politely announces that the prior preview is invalid
  and confirmation is unavailable until revalidation.
- A successfully reloaded save politely announces the exact persisted record
  identifier and append-only correction rule.
- If a save receipt exists but read-side reload cannot verify the record, an
  assertive alert says that verification is incomplete and instructs the
  researcher to inspect the ledger. It must not invite a blind duplicate save.

No announcement claims that source rights, evidence quality, readiness,
forecasting, or commercial eligibility changed.

## Static-State Coverage

Automated tests cover representative initial states:

- loading: readable text, `aria-busy=true`, and no refresh claim;
- empty: truthful empty state and no fabricated row;
- withheld: principal blocker and no placeholder result;
- stale: exact historical/review-only limitation;
- failure: visible recovery path without traceback; and
- validation: one global alert plus exact field binding when eligible.

These checks prove rendered semantics only. They do not prove that a particular
screen reader announces the content correctly.

## Browser Harness

Add a synthetic, test-only Streamlit state harness under `tests/fixtures`.
The existing accessibility browser gate starts it on loopback, exercises the
same production rendering helper, and records results only in memory/stdout.

The harness:

- contains no company, forecast, probability, recommendation, or production
  ledger data;
- writes no repository file;
- exposes each static state and each user-triggered transition;
- verifies one matching status or alert, visible text, atomicity, and absence
  of duplicates; and
- is clearly classified as framework engineering evidence, not user,
  screen-reader, hosted, or WCAG evidence.

The real Company Workbench AppTest and direct browser path separately prove
that the helper is integrated with validation and authoring transitions.

## Small-Control Audit Boundary

The existing direct gate continues to check the inspected navigation,
Discover, summary, help, dataframe, and authoring controls. This slice may fix
only a target-size or focus defect directly reproduced by the expanded state
matrix. It does not declare all framework controls conformant.

True zoom, forced colors, reduced motion, screen-reader tasks, and independent
human review remain external evidence gates.

## Testing

Test-first coverage must prove:

- exact state-to-role/live mapping;
- one visible message and no hidden duplicate;
- transition deduplication by exact state and receipt identity;
- validation preserves one alert and exact field binding;
- preview ready remains explicitly unsaved;
- stale draft removes confirmation and announces revalidation;
- save reload success includes the exact record ID;
- reload-unverified state never invites another save;
- static loading, empty, withheld, stale, and failure content has the required
  semantic boundary without unnecessary live regions;
- desktop and `390x844` state-harness runs have no overflow, console error,
  traceback, missing label, or duplicate announcement; and
- repository ledgers and generated-artifact paths remain byte-identical.

## Acceptance Criteria

1. User-triggered authoring transitions have one deterministic visible live
   message with the correct urgency.
2. Static states remain readable without becoming noisy live regions.
3. Existing required-field focus and association evidence remains intact.
4. No transition message changes research, readiness, source, or persistence
   semantics.
5. Automated evidence is labelled as automation, not screen-reader or WCAG
   conformance.
6. True assistive-technology and independent-human gates remain open.
7. Focused, full, browser, render, release, hygiene, and exact-head CI gates
   pass with no generated artifact changes.
