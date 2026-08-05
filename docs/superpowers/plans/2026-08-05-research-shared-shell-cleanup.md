# Personal Research Shared-Shell Cleanup Plan

**Goal:** Make the existing top Personal Research workflow navigation the only visible page-navigation authority and remove duplicated main-column readiness/profile chrome before each route answer.

**Design anchor:** `docs/superpowers/specs/2026-08-04-answer-first-research-workflow-simplification-design.md`, especially **Shared shell and navigation** and implementation slice 5.

**Architecture:** Preserve every route URL and the existing workspace-mode radio. In Personal Research mode only, stop rendering the sidebar `Choose your path` radio and derive the page from the current/default route. Keep the top `research_workflow_navigation_html(...)` navigation. Do not render the operator command header or global profile trust strip in the Research main column; route-specific answer contracts continue to expose only freshness or readiness that changes the answer. Public and Operator shells remain unchanged.

## Boundaries

- No new route, calculation, source, data write, readiness state, ranking, recommendation, or persistence contract.
- Workspace switching remains available in the sidebar.
- Data Health and Proof History remain direct-link secondary routes.
- No readiness rebuild, broad refresh, generated report, screenshot, timing, CSV, JSON, output, or canonical-data command.
- Keep the same 18 protected generated paths unstaged and byte-identical.
- Work test-first; stage exact named files only; never use `git add -A`.

## Task 1 — One page-navigation authority

- [x] Add failing source/route tests proving Research mode does not instantiate the sidebar page radio while Public and Operator still do.
- [x] Preserve `selected_page_from_route_rail(...)`, exact route queries, workspace switching, and the top Personal Research navigation.
- [x] Implement the smallest conditional around the existing sidebar page selector.
- [x] Run focused navigation, dashboard-helper, and research-mode tests.
- [x] Stage exact code/tests, run staged hygiene and whitespace checks, and commit.

## Task 2 — Remove duplicate primary readiness/profile chrome

- [x] Add failing tests proving Research mode renders top workflow navigation, skip target, and route styles without `render_app_header(...)` or `render_profile_trust_strip(...)` before the answer.
- [x] Prove Public and Operator shell branches remain unchanged.
- [x] Implement the smallest Research-only shell branch.
- [x] Update direct-browser assertions to require one labelled workflow navigation, one H1, one main landmark, route/action visibility, and no horizontal overflow at `1280x720` and `390x844`.
- [x] Stage exact code/tests, run staged hygiene and whitespace checks, and commit.

## Task 3 — Release evidence

- [x] Update README, ROADMAP, Personal Research documentation, dashboard QA, continuation prompt, and this plan. Draft PR #113 remains the GitHub closure step.
- [x] Run focused tests and `python3 -m pytest tests -q`.
- [x] Run dashboard startup/render, public wording/performance/check, pilot-readiness, accessibility-browser, diff-hygiene, and whitespace checks.
- [x] Recompute protected-artifact hashes and require byte identity.
- [x] Commit exact documentation, push only `codex/personal-research-mode-mvp`, keep PR #113 draft, and require exact-head CI.

## Acceptance

- Research mode has one visible page-navigation authority in the main column.
- The sidebar retains workspace selection but no Research page selector.
- Main-column command/readiness/profile strips no longer precede Personal Research answers.
- Direct links and selected-ticker query parameters remain stable.
- Public and Operator shells do not regress.
- No research, quant, evidence, authoring, readiness, source-rights, or generated-artifact contract changes.
