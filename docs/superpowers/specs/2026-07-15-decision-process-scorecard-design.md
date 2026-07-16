# Decision-Process Scorecard Design

## Goal

Add a read-only, profile-scoped scorecard that evaluates whether the research process is documented and current. It does not score a company, forecast returns, rank opportunities, or evaluate investment performance.

## Placement

The scorecard sits below the Research Thesis Journal in Single-Stock Report as one collapsed detail section. This keeps the public first answer compact while making process evidence available to reviewers.

## Checks

1. Selected-profile readiness was verified.
2. A current thesis is documented.
3. At least one evidence item is recorded for a documented thesis.
4. Conflicting evidence, when present, has a later review entry.
5. An explicit invalidation condition is recorded.
6. Confidence history is documented.
7. The review date is scheduled and not overdue.
8. Open evidence-change tasks for the selected ticker are resolved or explicitly remain open.
9. DCF assumptions are visible when DCF is ready; blocked/excluded DCF remains blocked/not applicable rather than becoming a process failure.

## States

- `complete`
- `action_needed`
- `not_observed`
- `blocked`
- `not_applicable`
- `unavailable`

The summary reports counts by state, not a numeric company score or pass/fail grade.

## Evidence Rules

- Only the selected profile and ticker may contribute.
- Conflicting evidence is addressed only by a later reviewed journal entry.
- No conflicting evidence is `not_observed`, not automatically complete.
- No DCF readiness means assumptions remain `blocked`; ETF/index/fund rows are `not_applicable`.
- Open Change Monitor tasks remain `action_needed`; they cannot be silently treated as reviewed.
- Missing journal history remains visible and never gets synthesized.

## Safety Boundary

The scorecard measures documentation and review discipline only. It does not change readiness, canonical data, DCF inputs, Earnings Nowcast output, peer trust, recommendations, or actions.

## Verification

Core tests cover empty history, complete documentation, unresolved conflicts, no-conflict states, blocked/excluded DCF, open changes, profile/ticker isolation, and deterministic identity. Dashboard tests lock the compact summary and collapsed detail contract.
