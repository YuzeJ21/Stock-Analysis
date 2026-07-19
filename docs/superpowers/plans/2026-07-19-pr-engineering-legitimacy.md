# PR Engineering Legitimacy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one minimal pull-request-only GitHub Actions gate that reproduces the approved local engineering checks for PR #113 without data writes or external product claims.

**Architecture:** A single least-privilege workflow checks out the PR revision, installs the existing Python requirements, and runs six explicit read-only commands. A focused repository contract test prevents future expansion into schedules, secrets, readiness generation, deployment, or artifact upload.

**Tech Stack:** GitHub Actions YAML, Python 3.12, pytest, GNU Make, Markdown.

## Global Constraints

- Trigger only on pull requests targeting `main`.
- Grant only `contents: read` permission.
- Do not use providers, secrets, schedules, deployment, hosted probes, readiness generation, or artifact uploads.
- Do not generate or stage CSV, JSON, report, sample-report, screenshot, timing, readiness, or canonical-data churn.
- Never use `git add -A`; stage exact intentional paths only.
- Push only to `codex/personal-research-mode-mvp`; keep PR #113 open and draft.

---

### Task 1: Add the minimal PR engineering gate

**Files:**
- Create: `.github/workflows/commercial-research-beta.yml`
- Create: `tests/test_github_actions_workflow.py`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: the existing `requirements.txt` and Make targets `dashboard-smoke`, `research-dashboard-render-smoke`, `public-wording-check`, and `diff-hygiene-summary`.
- Produces: one GitHub pull-request status check named `Commercial Research Beta / local-engineering-gate`.

- [ ] **Step 1: Write the failing workflow contract test**

Create `tests/test_github_actions_workflow.py` with assertions that the workflow exists, targets pull requests to `main`, uses `contents: read`, selects Python 3.12, installs `requirements.txt`, contains every required command, and contains none of the prohibited trigger or action strings.

- [ ] **Step 2: Run the focused test and verify the intended red state**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_github_actions_workflow.py -q
```

Expected: fail because `.github/workflows/commercial-research-beta.yml` does not exist.

- [ ] **Step 3: Add the minimal workflow**

Create `.github/workflows/commercial-research-beta.yml` with `pull_request` as its only trigger, `contents: read`, one Ubuntu job, Python 3.12, requirement installation, and the six approved commands in order. Do not add caching, uploads, provider access, readiness, deployment, or schedules.

- [ ] **Step 4: Run the focused test and verify green**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_github_actions_workflow.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Update stage documentation**

Record the locally implemented CI contract in `ROADMAP.md` and the continuation prompt. State that independent hosted CI evidence is pending until GitHub completes the workflow and that human review remains separately unproven.

- [ ] **Step 6: Run the complete required verification**

Run the focused test, full pytest suite, dashboard and research render smokes, public wording and public checks, commercial beta and release checks, pilot readiness, diff hygiene, and whitespace checks. The pilot may truthfully remain blocked on stale readiness.

- [ ] **Step 7: Stage exact files and verify the package**

Stage only the workflow, focused test, design, plan, roadmap, and continuation contract. Run `make staged-hygiene-check` and `git diff --cached --check`.

- [ ] **Step 8: Commit, push, and update the draft PR**

Commit the coherent slice, push only the current feature branch, update PR #113 with the new scope and verification, and verify it remains open and draft. Do not claim the hosted check passed until GitHub directly reports success.
