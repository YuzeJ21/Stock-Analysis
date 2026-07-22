# Research Decision Lab Design

**Date:** 2026-07-22
**Status:** Approved product direction; ready for implementation planning
**Scope:** Personal Research Mode only

## Purpose

The Research Decision Lab turns the Command Center's existing research-process capabilities into one visible, repeatable loop:

```text
Research plan -> evidence -> invalidation -> scenario -> review trigger -> learning
```

It helps a researcher document and review how a conclusion was formed without becoming a trading system. It produces no recommendation, transaction direction, position size, allocation, stop-loss price, take-profit price, expected return, company score, or broker action.

The first version is a composition layer over existing verified capabilities. It does not introduce a new persistent ledger, top-level route, data provider, generated report, or readiness state.

## User Outcome

For one selected company, a researcher can answer:

1. Is a current reviewer-authored thesis documented?
2. Is supporting or conflicting evidence recorded and reviewed?
3. Is a source-backed invalidation condition documented?
4. Is scenario review available, blocked, or not applicable?
5. What evidence event or review date requires attention?
6. Has a prior research outcome and learning been reviewed?
7. What is the next research-process step?

For the focused cohort, Monitor can show which research-process items require review without ranking companies or implying an investment action.

## Product Placement

### Company Workbench

The existing answer-first handoff remains unchanged:

```text
Selected ticker -> Use now -> Still withheld -> Data Health handoff
```

The Decision Lab appears after `What Changed` and before the detailed company-research sections. It is a compact process summary, not a replacement for the Workbench answer, Research Conclusion, or authoritative Next Research Task.

The summary contains six independently derived lanes:

| Lane | Primary answer | Truth boundary |
| --- | --- | --- |
| Plan | Current thesis documented, not started, or unavailable | Generated thesis text cannot populate reviewer history. |
| Evidence | Current, conflict review needed, not started, or unavailable | Candidate context and unreviewed text cannot become evidence. |
| Invalidation | Documented, missing, or unavailable | No invalidation condition is inferred from risks or price movement. |
| Scenario | Reviewable, blocked, excluded, or unavailable | Scenario math appears only when the existing DCF gate passes. |
| Review trigger | Evidence change due, overdue, scheduled, unscheduled, or unavailable | A review trigger is a research task, never a transaction trigger. |
| Learning | Reviewed, not started, commercial-evidence blocked, or unavailable | Outcome review never becomes return attribution or skill scoring. |

One `Next process step` is derived from the first explicit process gap in the deterministic order below. It remains separate from the existing authoritative company research task.

1. Review recorded conflicting evidence that has no later review.
2. Review an overdue thesis.
3. Record a current reviewer-authored thesis.
4. Record a source-backed invalidation condition.
5. Record source-backed research evidence.
6. Schedule the next evidence review.
7. Restore visible DCF assumptions only when DCF is already ready.
8. Continue monitoring when no process gap is present.

This order represents documentation workflow, not company attractiveness, expected return, or portfolio priority.

### Monitor

Monitor keeps its existing Weekly Research Summary and source-backed change answer first. A new `Research Discipline Review` appears immediately afterward and before detailed change evidence.

The review uses the focused cohort only and groups items by process state:

- conflicting evidence awaiting later review;
- overdue thesis reviews;
- missing current thesis;
- missing invalidation conditions;
- missing evidence;
- unscheduled reviews;
- reviewed or not-started outcome learning.

Empty state copy must say that no process item is currently due from saved reviewer-authored evidence. It must not say that no risk exists, no research is needed, or no market event occurred.

The cohort display must not calculate a score, rank, winner, expected return, allocation, position size, or action. Stable display order is the existing focused-cohort order followed by ticker, not process severity or market value.

## Architecture

Create one focused derivation module:

```text
src/research_decision_lab.py
```

The module consumes existing immutable results:

- selected-profile stock report payload;
- `JournalState` from `src/research_thesis_journal.py`;
- `DecisionProcessScorecard` from `src/decision_process_scorecard.py`;
- `OutcomeStatus` from `src/research_outcome_review.py`;
- selected-profile research change items;
- existing scenario and valuation readiness fields.

It produces immutable display contracts:

```python
@dataclass(frozen=True)
class DecisionLabLane:
    key: str
    label: str
    state: str
    answer: str
    evidence: str
    next_step: str


@dataclass(frozen=True)
class ResearchDecisionLabState:
    profile_key: str
    ticker: str
    status: str
    lanes: tuple[DecisionLabLane, ...]
    next_process_step: str
    boundary: str
    identity: str
```

The module also produces cohort rows from already derived per-ticker states. Dashboard helpers convert these contracts into cards and tables; the derivation module must not import Streamlit.

No Decision Lab code may import from `src/portfolio_review.py`. Its historical `Keep`, `Risk Reduce`, `Constructive Review`, cost-basis, and position-risk language is outside the Personal Research contract and must not be surfaced or repurposed by this feature.

## Data Flow

```text
Saved selected-profile evidence
  -> existing report, journal, scorecard, outcome, change, and scenario derivations
  -> Research Decision Lab composition
  -> Company Workbench summary and Monitor cohort review
  -> details remain in existing journal, scorecard, scenario, outcome, and Advanced evidence sections
```

The composition cannot write to the thesis journal, outcome ledger, source data, canonical data, readiness, proof history, reports, screenshots, or timing artifacts. It cannot resolve a Change Monitor item or change an existing research conclusion.

## Fail-Closed Behavior

- Missing journal: Plan, Evidence, Invalidation, and Review Trigger remain `not_started`; no thesis or evidence is synthesized.
- Invalid journal: the Decision Lab becomes `unavailable` for that ticker and shows the existing verification error without partial journal-derived claims.
- Missing outcome ledger: Learning is `not_started`; no learning is fabricated.
- Commercial outcome blocker: Learning is `commercial_evidence_blocked`; local technical history is not presented as commercially usable evidence.
- DCF blocked: Scenario is `blocked`; no baseline, sensitivity, or valuation number appears.
- DCF excluded: Scenario is `excluded`; the state is method-fit context, not a negative company signal.
- Missing or mismatched profile/ticker inputs: derivation raises `ValueError`; the dashboard renders one compact unavailable state while preserving the rest of Company Workbench.
- Candidate peer, news, catalyst, or generated narrative context cannot populate a lane unless the existing source-backed contract already accepts it.

Independent lanes must remain independent. A complete thesis cannot unlock Scenario, reviewed Learning cannot clear an evidence conflict, and current readiness cannot create journal history.

## Interaction And Copy

- Keep the Workbench first viewport and `USE NOW` performance marker unchanged.
- Do not add a top-level navigation item in version one.
- Use plain labels: `Plan`, `Evidence`, `Invalidation`, `Scenario`, `Review trigger`, and `Learning`.
- Use `Action needed` only for research documentation work. Never use `Buy`, `Sell`, `Hold`, `Add`, `Trim`, `Reduce`, `Entry`, `Exit`, `Stop loss`, `Take profit`, or `Position size`.
- Keep source rows, identities, timestamps, and raw evidence under existing Advanced disclosures.
- Desktop may use a compact multi-column layout. Phone must reflow to one column without horizontal scrolling and retain the next process step before Advanced details.

## Testing Strategy

### Derivation tests

Cover each lane independently and prove that one lane cannot promote another. Required cases include:

- empty journal and outcome ledger;
- current thesis with evidence, invalidation, and scheduled review;
- conflicting evidence without a later review;
- later review clearing only the conflict-review process gap;
- overdue and unscheduled review states;
- DCF ready with visible assumptions;
- DCF blocked and DCF excluded;
- commercial outcome evidence blocked;
- mismatched profile or ticker;
- deterministic identity and stable lane order;
- absence of trading and allocation language.

### Dashboard tests

- Company Workbench renders exactly one Decision Lab summary after `What Changed`.
- The existing answer-first handoff remains earlier in document order.
- The Decision Lab does not replace Research Conclusion or Next Research Task.
- Monitor keeps Weekly Research Summary first and groups process states without ranking.
- Empty states display no fabricated thesis, evidence, risk, scenario, or learning.
- Technical evidence remains collapsed.

### Runtime and release tests

- Personal Research render smoke for all four routes.
- Desktop and `390x844` phone browser review for Company Workbench and Monitor.
- No horizontal overflow, traceback, duplicated summary, or raw-table-first view.
- Commercial Research performance thresholds continue to pass with `USE NOW` as Workbench first useful evidence.
- Public wording, research-only language, full tests, PR-range hygiene, diff hygiene, and staged hygiene remain green.

## Implementation Slices

### Slice 1 — Read-only Decision Lab composition

Add the immutable derivation module, independent lane states, deterministic next-process-step selection, render helpers, and focused tests. No dashboard placement or persistence change.

### Slice 2 — Company Workbench integration

Render the compact summary after `What Changed`, preserve the existing first viewport and authoritative research task, and verify desktop/phone behavior.

### Slice 3 — Monitor discipline review

Compose focused-cohort process rows, render the grouped review after Weekly Research Summary, and verify truthful empty states and stable no-ranking order.

### Slice 4 — Documentation and release evidence

Update methodology, provenance, Personal Research documentation, browser-QA markers, ROADMAP, continuation contracts, and the draft PR. Run the complete local release matrix and require exact-head GitHub CI.

Each slice must be independently testable and committed before the next begins.

## Later, Separately Approved Work

An append-only pre-commitment record may be designed only after Decision Lab usage shows that the existing Thesis Journal cannot capture the required research plan. A hypothetical paper-position laboratory would require a separate design, private-data policy, language review, and explicit approval. Neither is part of this design.

Live holdings, account imports, recommended position sizing, price-triggered stop or profit rules, broker integration, order routing, auto-trading, and real transaction records remain out of scope.

## Acceptance Criteria

The design is implemented only when all of the following are directly verified:

1. Company Workbench displays one compact six-lane process summary without changing its answer-first handoff.
2. Monitor displays a focused-cohort Research Discipline Review after its weekly summary without ranking companies.
3. Empty, blocked, excluded, invalid, and commercially blocked states remain explicit and independent.
4. No new ledger, readiness state, generated data artifact, route, transaction field, or trading instruction is introduced.
5. Existing journal, scorecard, scenario, outcome, change-monitor, and conclusion contracts remain authoritative.
6. Focused and full tests, route renders, browser review, performance, wording, and hygiene checks pass on the implementation revision.
7. Draft PR #113 remains draft; no merge or public deployment occurs without explicit approval.

## Product-Maturity Boundary

The Decision Lab can improve workflow coherence, research discipline, repeat-use value, and portfolio-demo differentiation. It does not prove source coverage, predictive accuracy, investment performance, independent reviewer adoption, hosted reliability, commercial demand, competitive superiority, or product-market fit.
