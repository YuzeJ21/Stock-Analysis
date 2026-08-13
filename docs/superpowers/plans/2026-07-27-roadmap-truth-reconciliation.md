# Roadmap Truth Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `ROADMAP.md` into a concise current-decision index while preserving every fail-closed boundary and routing detailed completion evidence to its canonical document.

**Architecture:** Keep current commands, product stage, ordered executable work, external dependencies, later work, completion evidence, success gates, and permanent exclusions in `ROADMAP.md`. Remove duplicated implementation chronology when the same evidence already lives in `docs/COMPLETED_MILESTONES.md`, `docs/ACCESSIBILITY_EVIDENCE.md`, `docs/internal/POINT_IN_TIME_UNIVERSE_REVIEW_HISTORY.md`, or the continuation contract. Correct the stale next-stage conclusion in the capability audit.

**Tech Stack:** Markdown, Python/pytest documentation contracts, existing Make release and hygiene gates.

## Global Constraints

- Start from current repository truth.
- Preserve independent readiness and every research-only, source-rights, explicit-Q4, EPS split-basis, synthetic-fixture, calibration, and no-fabrication boundary.
- Do not run readiness rebuilds or generate CSV, JSON, report, screenshot, or timing artifacts.
- Never stage generated working-data churn.
- Keep PR #113 open and draft.

---

### Task 1: Define the active-roadmap contract

**Files:**
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `tests/test_launchers.py`

**Interfaces:**
- Consumes: the user-approved `Now / Next / Externally blocked / Later / Completed with evidence` structure.
- Produces: a behavioral documentation contract that rejects a missing section, stale current-priority statement, or oversized active roadmap.

- [ ] **Step 1: Write the failing contract test**

```python
def test_active_roadmap_is_a_concise_current_decision_index():
    roadmap = _read("ROADMAP.md")
    for heading in (
        "## Now",
        "## Next",
        "## Externally blocked",
        "## Later",
        "## Completed with evidence",
    ):
        assert heading in roadmap
    assert len(roadmap.splitlines()) <= 320
```

- [ ] **Step 2: Run the contract test and verify the current roadmap fails**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py::test_active_roadmap_is_a_concise_current_decision_index -q`

Expected: failure because the exact new headings and line budget are not yet satisfied.

- [ ] **Step 3: Remove obsolete assertions that require completed performance work to remain in the active-priority order**

Replace the old performance-before-hosting index assertion with checks that the performance release evidence is linked under `Completed with evidence` and that hosted validation stays external.

- [ ] **Step 4: Run the focused documentation tests**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py tests/test_launchers.py -q`

Expected: failures name only roadmap phrases that must be preserved, intentionally rerouted, or updated.

### Task 2: Reconcile the active roadmap and stale capability audit

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/analysis_capability_audit.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: current HEAD, exact-head CI evidence, roadmap priorities 1–10, and the external-dependency classifications already recorded in the continuation contract.
- Produces: a concise active roadmap, a current capability conclusion, and a continuation contract pointing to the reconciled roadmap.

- [ ] **Step 1: Rewrite `ROADMAP.md` as the current decision index**

Keep:

```text
Current Truth
Now
Next
Externally blocked
Later
Completed with evidence
Success gates
Permanently out of scope
```

Preserve exact unblock conditions for point-in-time universe data, consensus, reviewed peers, hosted controls, accessibility environments, independent reviewers, and calibration.

- [ ] **Step 2: Correct the stale capability-audit conclusion**

Replace the completed performance-release recommendation with observation-recency truth, accessibility remediation, permitted point-in-time data, and independent beta validation as the next maturity work.

- [ ] **Step 3: Update the continuation contract**

Record that Stage 0 roadmap reconciliation is complete only after the focused/full suite, release checks, hygiene, commit, push, PR update, and exact-head CI pass.

- [ ] **Step 4: Run focused tests and correct only truthful compatibility failures**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py tests/test_launchers.py tests/test_pilot_review_feedback_template.py -q`

Expected: pass with no stale priority assertion.

- [ ] **Step 5: Run the complete release contract**

Run:

```text
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all executable gates pass; generated churn remains excluded.

- [ ] **Step 6: Stage, verify, commit, push, and update the draft PR**

Stage only the intentional plan, roadmap, capability-audit, continuation-contract, and test files. Run `make staged-hygiene-check` and `git diff --cached --check`, commit coherently, push only `codex/personal-research-mode-mvp`, update PR #113, and require exact-head CI.
