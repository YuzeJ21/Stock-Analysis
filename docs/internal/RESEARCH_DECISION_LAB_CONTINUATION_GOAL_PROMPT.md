# Research Decision Lab Continuation Goal Prompt

Use this prompt to reverify the completed local Decision Lab and continue the next Commercial Research Beta maturity gate without repeating finished implementation.

```text
/goal

Continue the Stock Research Command Center in:

/Users/yjian070/Documents/New project/.worktrees/personal-research-mode-mvp

Start from current repository truth, never chat memory.

Read:

- docs/superpowers/specs/2026-07-22-research-decision-lab-design.md
- docs/superpowers/plans/2026-07-22-research-decision-lab.md
- ROADMAP.md
- docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
- docs/METHODOLOGY.md
- docs/PROVENANCE_CONTRACT.md
- docs/PERSONAL_RESEARCH_MODE.md

Expected state to verify, never assume:

- Branch: codex/personal-research-mode-mvp
- Decision Lab Monitor anchor: c7ad977b3 or a later verified descendant
- Draft PR: https://github.com/YuzeJ21/Stock-Analysis/pull/113
- PR remains open and draft
- Branch is pushed and aligned with origin
- Existing generated CSV/JSON/report/sample-report/screenshot/timing churn remains local and unstaged

Current local milestone:

Local Decision Lab implementation is complete when current evidence reconfirms all of the following:

1. The immutable six-lane composition preserves independent Plan, Evidence, Invalidation, Scenario, Review trigger, and Learning states.
2. Company Workbench keeps Selected ticker -> Use now -> Still withheld -> Data Health first, then renders exactly one Decision Lab after What Changed.
3. Research Conclusion and Next Research Task remain authoritative and separate from the next process step.
4. Monitor keeps Weekly Research Summary first, then Research Discipline Review, then the independent Research change monitor.
5. Monitor preserves saved focused-cohort order, isolates an invalid ticker, and never ranks by severity, market value, expected return, or attractiveness.
6. Empty process evidence says only that no process item is due from saved reviewer-authored evidence; it makes no market-event, risk, or external-research claim.
7. Identities and technical evidence remain under collapsed Advanced sections.
8. The feature writes no journal, outcome, source, readiness, proof, report, screenshot, timing, or generated data artifact.

Do not reimplement or redesign this milestone if current tests, runtime behavior, docs, branch state, and exact-head CI still prove it. Fix only a directly reproduced regression.

Objective:

Reverify the Decision Lab release evidence, then advance the highest-value executable Commercial Research Beta gate. Prefer a safe local reliability, evidence-depth, or operating-contract slice already approved by ROADMAP.md. If no such local slice remains, classify the exact external dependency and its unblock condition, then move to another executable lane. Never convert an unavailable provider, dataset, hosted account, reviewer, peer source, calibration cohort, or operating owner into fabricated completion evidence.

Persistence contract:

1. Verify branch, HEAD, upstream alignment, working tree, latest commits, PR #113 status, ROADMAP.md, generated-artifact hygiene, tests, runtime gates, and exact-head CI before editing.
2. Continue automatically while any safe, meaningful, approved local task remains.
3. Classify each unavailable external dependency once, record its exact unblock condition, avoid identical retry loops, and immediately continue another executable lane.
4. Work test-first, one coherent independently verified slice at a time.
5. After each slice, run focused and full tests, required renders, wording, performance, release, pilot-boundary, PR-range, diff, whitespace, and staged-hygiene checks.
6. Stage exact intentional code/test/docs/template paths only. Never use git add -A.
7. Commit and push only to codex/personal-research-mode-mvp, update draft PR #113, and require exact-head CI before the next slice.
8. Keep PR #113 open and draft. Do not merge or deploy publicly without explicit approval.
9. Do not run make readiness, broad refresh/import/apply commands, or generate/stage CSV, JSON, readiness reports, stock reports, sample reports, screenshots, or timing artifacts for this continuation.
10. Do not claim the broader goal complete while any applicable source, hosted, reviewer, calibration, demand, or operating gate lacks direct evidence.

Research-only boundaries:

- No investment advice, recommendation, company grade, expected-return score, or research-skill score.
- No buy/sell/hold/add/trim/reduce direction, allocation, recommended position size, entry, exit, stop-loss, take-profit, live holding, account import, cost basis, broker integration, order routing, auto-trading, or real transaction record.
- Candidate context cannot populate trusted evidence, change deterministic forecasts, or promote readiness.
- Synthetic fixtures are test-only; empty ledgers remain empty.
- Q4 actuals require explicit SEC-filed Q4-table evidence; EPS split basis remains unverified without explicit proof.
- Real-company Earnings Nowcast remains blocked without permitted point-in-time consensus; numerical Beat/Miss probability remains withheld without leakage-safe calibration evidence.
- Every readiness and process lane remains independent.

Required verification for a changed slice:

- focused tests for changed modules and contracts
- python3 -m pytest tests -q
- make dashboard-smoke
- make research-dashboard-render-smoke
- make public-wording-check
- make public-check
- make browser-qa-evidence
- make commercial-beta-performance-gate when Workbench or Monitor changes
- make commercial-beta-release-check
- make pilot-readiness-check TOP_N=10
- make pr-range-hygiene-check
- make diff-hygiene-summary
- git diff --check
- make staged-hygiene-check and git diff --cached --check after exact staging

Truthful maturity boundary:

The local Decision Lab does not prove source coverage, predictive accuracy, investment performance, independent adoption, hosted reliability, commercial demand, competitive superiority, or product-market fit. Passing local tests or exact-head CI cannot satisfy those external gates.

At each handoff report:

1. Repository and PR status.
2. Current product stage.
3. Decision Lab regression audit result.
4. New maturity slice completed, if any.
5. Focused, full, runtime, performance, wording, release, and hygiene evidence.
6. Commit, push, and exact-head CI status.
7. Generated artifacts excluded.
8. External dependencies classified once with exact unblock conditions.
9. Remaining applicable gates.
10. Exact next executable step.
11. Whether the branch is safe for draft review.
12. Whether the local Decision Lab goal is complete and whether the broader Commercial Research Beta goal remains active.

Do not stop after a green Decision Lab recheck while another safe approved local task remains. Do not claim external completion. If every remaining task genuinely requires unavailable external evidence or new authority, leave the broader goal active, publish the exact dependency ledger and resume condition, and do not retry unchanged blockers.
```

This continuation is persistent but evidence-bound: it prevents one external dependency from stopping other work without redefining completion or weakening the research-only contract.
