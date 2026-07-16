# Source Freshness Timeline Design

## Purpose

Add one read-only chronology to the selected-ticker report so a reviewer can see when each visible input became effective, was retrieved, or was assembled into the report. The timeline reduces confusion between financial period dates, market timestamps, retrieval timestamps, forecast cutoffs, and report generation time.

## Product Boundary

The timeline is evidence display only. It never refreshes a source, applies an import, changes readiness, creates a proof record, or infers a missing timestamp. Unknown publication or retrieval dates remain visibly unknown. A recent retrieval time cannot make an old reporting period current, and a report generation time cannot become source freshness proof.

## Approaches Considered

1. **Recommended: derive a typed timeline from the selected report payload.** Reuse existing provenance and freshness fields, deduplicate repeated source records, and show one summary plus a collapsed chronology in Sources & Gaps. This is deterministic, profile-aligned, and adds no new canonical state.
2. **Persist a new freshness ledger.** This would support long histories but would duplicate provenance and introduce a new write/review workflow before the display contract is proven.
3. **Build a new Freshness page.** This would make the feature prominent but would repeat Data Health and fragment the existing five-page workflow.

Use approach 1. Historical revisions and nowcast cutoffs can appear when those records already exist in a payload; the timeline must not fabricate them.

## Data Contract

`FreshnessTimelineEvent` contains:

- deterministic event ID
- ticker and lane
- event type and timestamp kind
- timestamp, or an explicit unknown state
- source and source reference when supplied
- freshness state and concise evidence note
- selected profile and report identity

The builder consumes the stock-report payload plus selected profile. It may create events for price observation, financial reporting period, source retrieval, forecast cutoff, source publication, explicit revision, and report generation. Events are sorted newest-known first, then unknown-timestamp records. Exact duplicates collapse by deterministic identity.

## UI Contract

The existing Sources & Gaps tab shows:

1. one compact answer: latest known source event, unknown timestamp count, and stale/unknown count;
2. a chronological table under `Source freshness timeline`;
3. raw source fields and deterministic IDs only under `Advanced: freshness provenance`.

The timeline is not added to the first public viewport and does not create a new page. Blocked and excluded report states stay unchanged.

## Error And Trust Behavior

- Invalid timestamps are retained as unknown, not parsed heuristically.
- Missing source references remain missing.
- Provider freshness labels are normalized only into `current`, `stale`, `unknown`, or `missing_timestamp`; original text remains in the note.
- Cross-profile records are never merged.
- No event may use recommendation, ranking, or transaction language.

## Verification

Tests cover deterministic identity, ordering, deduplication, missing timestamps, stale-state preservation, profile separation, report-payload mapping, collapsed UI placement, and public wording. Full dashboard, browser, pilot, and public gates must pass before completion.
