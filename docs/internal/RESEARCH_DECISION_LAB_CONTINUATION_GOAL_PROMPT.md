# Research Decision Lab Continuation Goal Prompt

Use this prompt in a new Codex task to plan and implement the approved Research Decision Lab without weakening the Command Center's research-only boundaries.

```text
/goal

Continue the Stock Research Command Center in:

/Users/yjian070/Documents/New project/.worktrees/personal-research-mode-mvp

Start from current repository truth, never chat memory.

Read and execute the approved design contract:

docs/superpowers/specs/2026-07-22-research-decision-lab-design.md

Also read:

- ROADMAP.md, especially `Next Local Product Stage: Research Decision Lab`
- docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
- docs/METHODOLOGY.md
- docs/PROVENANCE_CONTRACT.md
- docs/PERSONAL_RESEARCH_MODE.md

Expected state to verify, never assume:

- Branch: codex/personal-research-mode-mvp
- Design anchor: 54e06e1c3 or a later verified descendant
- Draft PR: https://github.com/YuzeJ21/Stock-Analysis/pull/113
- PR remains open and draft
- Branch may contain later verified commits
- Existing generated CSV/report working-data churn must remain excluded

Objective:

Implement the approved Research Decision Lab as a read-only composition of the existing Thesis Journal, Decision-Process Scorecard, Scenario Lab, Research Outcome Review, selected-profile report, and Change Monitor contracts.

The product outcome is one coherent research-discipline loop:

Research plan -> evidence -> invalidation -> scenario -> review trigger -> learning

Company Workbench must show one compact six-lane summary after `What Changed` while preserving the existing answer-first handoff. Monitor must show a focused-cohort Research Discipline Review after Weekly Research Summary while preserving source-change and process-discipline states independently.

Persistence and non-blocking execution contract:

1. Verify branch, HEAD, upstream alignment, working-tree status, latest commits, PR #113 status, roadmap, generated-artifact hygiene, current tests, and current runtime gates before editing.
2. Treat the design as approved direction, not implementation evidence. Inspect current code and tests before choosing exact interfaces.
3. If a detailed implementation plan for this feature does not exist, create and self-review `docs/superpowers/plans/2026-07-22-research-decision-lab.md` before product-code changes.
4. Continue automatically while any safe, meaningful local task in the approved design remains. One unavailable provider, dataset, hosted account, reviewer, or calibration cohort must not stop local Decision Lab work.
5. Classify an unavailable external dependency once, record its exact unblock condition, avoid identical retry loops, and continue the next executable local slice.
6. Work one coherent independently tested slice at a time. Complete verification, exact staging, commit, push, roadmap/docs updates, draft-PR update, and exact-head CI before beginning the next slice.
7. Never claim the feature complete because a subset of tests passes. Completion requires direct evidence for every acceptance criterion in the design.
8. Keep PR #113 draft. Do not merge or deploy publicly without explicit approval.

Implementation order:

Slice 1 — Read-only composition contract

- Add a focused `src/research_decision_lab.py` module with immutable `DecisionLabLane` and `ResearchDecisionLabState` contracts.
- Derive independent Plan, Evidence, Invalidation, Scenario, Review trigger, and Learning states from existing immutable results.
- Select one deterministic next process step without replacing the authoritative company research task.
- Preserve empty, invalid, blocked, excluded, and commercial-evidence-blocked states.
- Reject mismatched profile/ticker inputs.
- Write failing tests first and prove no cross-lane promotion or trading/allocation language.
- Do not add Streamlit imports, persistence, a route, a readiness field, or a generated artifact.

Slice 2 — Company Workbench integration

- Render exactly one compact Decision Lab summary after `What Changed` and before detailed company-research sections.
- Preserve Selected ticker -> `Use now` -> `Still withheld` -> Data Health as the unchanged first answer.
- Keep Research Conclusion and Next Research Task authoritative and separate.
- Keep source rows, identities, timestamps, and technical diagnostics under Advanced.
- Verify desktop and 390x844 phone behavior, no overflow, no duplicate summary, and no first-useful performance regression.

Slice 3 — Monitor Research Discipline Review

- Compose focused-cohort rows from the same per-ticker contract.
- Render the review after Weekly Research Summary and before detailed change evidence.
- Preserve stable focused-cohort order followed by ticker.
- Do not rank by process severity, market value, expected return, or company attractiveness.
- Keep process-review empty states truthful and separate from market-event and source-change claims.

Slice 4 — Documentation and release evidence

- Update tests, docs/METHODOLOGY.md, docs/PROVENANCE_CONTRACT.md, docs/PERSONAL_RESEARCH_MODE.md, browser-QA markers, ROADMAP.md, both continuation prompts, and draft PR #113.
- Verify all design acceptance criteria against current code and runtime behavior.
- Require exact-head GitHub CI before calling the branch safe for review.

Non-negotiable boundaries:

- Research-only; no investment advice.
- No direct buy/sell/hold/add/trim/reduce instruction.
- No allocation or recommended position sizing.
- No entry, exit, stop-loss, take-profit, or price-trigger instruction.
- No live holdings, account imports, cost-basis workflow, broker integration, order routing, auto-trading, or real transaction records.
- Do not import or surface the action-oriented states from `src/portfolio_review.py` in Personal Research Mode.
- No company score, expected return, performance claim, research-skill score, or ranking.
- Candidate context cannot populate trusted evidence or change deterministic forecasts, DCF, readiness, conclusions, or process states.
- Synthetic fixtures remain test-only.
- Empty journals, outcomes, valuation, catalyst, and evidence ledgers remain empty.
- Q4 actuals still require explicit SEC-filed Q4-table evidence.
- EPS split basis remains unverified without explicit proof.
- Real-company Earnings Nowcast remains blocked without permitted point-in-time consensus.
- Numerical Beat/Miss probability remains withheld without calibration evidence.
- Every readiness lane remains independent.

Generated-artifact rules:

- Do not run `make readiness` or broad refresh/import/apply commands for this feature.
- Do not generate or stage CSV, JSON, readiness reports, stock reports, sample reports, screenshots, or timing output unless one exact artifact is explicitly required, reviewed, and approved.
- Never use `git add -A`.
- Stage exact intentional code, test, documentation, and template files only.
- Preserve all pre-existing generated working-data changes unstaged.

Verification after every meaningful slice:

- focused tests for every changed module and dashboard helper;
- python3 -m pytest tests -q;
- make dashboard-smoke;
- make research-dashboard-render-smoke;
- make public-wording-check;
- make public-check;
- make browser-qa-evidence;
- make commercial-beta-performance-gate when Workbench or Monitor behavior changes;
- make commercial-beta-release-check;
- make pilot-readiness-check TOP_N=10;
- make pr-range-hygiene-check;
- make diff-hygiene-summary;
- git diff --check;
- make staged-hygiene-check and git diff --cached --check after exact staging.

Git and PR rules:

- Commit one coherent verified slice at a time.
- Push only to codex/personal-research-mode-mvp.
- Update draft PR #113 after each verified implementation slice.
- Keep the PR draft.
- Do not merge into main or deploy publicly without explicit approval.

Completion audit:

Before claiming the Research Decision Lab complete, map every acceptance criterion in the design to current authoritative evidence. Classify each as proven, contradicted, incomplete, indirect, or missing. Screenshot-only, fixture-only, local-only, stale, or indirect evidence cannot prove a broader gate.

Required handoff after each slice:

1. Repository and PR status.
2. Current product stage.
3. Decision Lab slice completed.
4. Files and behavior changed.
5. Focused, full, runtime, performance, wording, and hygiene evidence.
6. Commit, push, and exact-head CI status.
7. Generated artifacts excluded.
8. External dependencies classified once.
9. Remaining Decision Lab acceptance criteria.
10. Exact next executable slice.
11. Whether the branch is safe for draft review.
12. Whether the Decision Lab goal and the broader Commercial Research Beta goal remain active.

Do not stop after planning or after one successful slice while another safe approved Decision Lab slice remains. Do not pretend an external gate is complete. Continue until every local Decision Lab acceptance criterion is directly proven or every remaining task genuinely requires unavailable external input or new authority.
```

This goal is intentionally persistent but evidence-bound. It prevents an unrelated external blocker from stopping local implementation while preserving explicit approval for merge, deployment, external accounts, credentials, real data mutation, and scope expansion.
