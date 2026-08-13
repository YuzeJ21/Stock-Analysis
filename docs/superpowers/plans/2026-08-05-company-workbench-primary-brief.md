# Company Workbench Primary Brief Implementation Plan

> **For Codex:** Execute this plan test-first, one coherent commit at a time. Do not mix Monitor, Research Desk, source activation, readiness rebuilds, or generated-artifact work into this slice.

**Goal:** Make Company Workbench answer its selected-company research question before loading the long analysis surface, while preserving every existing calculation, evidence identity, authoring contract, and fail-closed state.

**Architecture:** Compose one pure primary-brief contract from the existing selected-ticker answer, saved change answer, conclusion cards, and authoritative next-task arbitration. Render that contract through the existing top-of-route placeholder. Keep public Single-Stock Report behavior unchanged. In Personal Research mode, keep the detailed company modules closed until one explicit session-local action opens them.

**Tech stack:** Python, pandas, Streamlit, pytest, existing dashboard helpers and release gates.

---

## Scope and invariants

The primary brief answers exactly:

1. **Use now** — current supported evidence lanes.
2. **Still withheld** — missing, stale, unverified, rights-blocked, or context-only lanes.
3. **What changed** — source-backed/snapshot/no-queued-change state from the existing change contract.
4. **Next research task** — the existing authoritative arbitration result.
5. **Stop rule** — research-only; no recommendation, probability, transaction direction, or unsupported current-market conclusion.

The implementation must not:

- change report calculations, thresholds, readiness, provenance, source rights, authoring persistence, or evidence identities;
- combine independent Revenue, EPS, valuation, peer, catalyst, outcome, backtest, calibration, or consensus states;
- infer a usable lane from candidate context or a missing field;
- add a route, data source, ranking, recommendation, probability, position field, or broker behavior;
- generate or stage CSV, JSON, report, sample-report, screenshot, timing, readiness, canonical-data, or ledger output;
- change Public-mode Stock Selector or Single-Stock Report behavior.

---

### Task 0: Capture the clean release anchor

**Files:** none.

- [x] Verify the Discover slice exact-head GitHub check passed on `0e718d117`.
- [x] Record current branch/upstream divergence and PR #113 draft state.
- [x] Confirm the same 18 protected generated paths are the only generated working-data modifications and re-capture their hashes.
- [x] Run the focused Workbench baseline before changing tests:

```bash
python3 -m pytest \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py -q
```

---

### Task 1: Add a pure Company Brief contract

**Files:**

- Modify: `src/research_workspace.py`
- Modify: `tests/test_research_workspace.py`

**Contract:**

Add a pure helper similar to:

```python
def company_workbench_primary_brief(
    selected_answer_frame: pd.DataFrame,
    change_answer: Mapping[str, object],
    authoritative_task: Mapping[str, object],
) -> dict[str, object]:
    ...
```

It returns immutable presentation data for ticker, use-now answer, withheld/context answer, change answer and explicit change-context badge, authoritative task, Data Health route, and the fixed research-only stop rule.

- [x] Write behavior tests first for:
  - normal independent values;
  - empty selected answer fails closed without inventing a ticker or usable lane;
  - missing/blank change values become a truthful no-queued-change state;
  - authoritative task identity and badges pass through unchanged;
  - candidate/context text remains withheld and never enters Use now;
  - no recommendation, rank, expected return, probability, sizing, or transaction field exists.
- [x] Run the new tests and observe the correct RED because the helper is absent.
- [x] Implement the smallest pure helper that makes the tests pass.
- [x] Run the focused helper tests and the existing authoritative-task tests.
- [x] Verify protected hashes, stage only the exact source/test files, run staged hygiene, and commit:

```bash
git commit -m "Compose Company Workbench primary brief"
```

---

### Task 2: Render one accessible answer-first Company Brief

**Files:**

- Modify: `src/research_workspace.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_workspace.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

**Contract:**

Add a pure HTML renderer for the Task 1 brief and route it through the existing `selected_answer_target`. The section must use one labelled region, keep all five answers visible without opening Advanced, provide one ticker-preserving Data Health action, and keep the stop rule visible.

- [x] Write behavior tests first for:
  - the exact five answer labels;
  - HTML escaping of ticker and evidence text;
  - one Data Health link with the selected ticker;
  - one visible research-only stop rule;
  - no duplicated primary action;
  - phone-safe classes and a 44px minimum action contract;
  - public summary HTML remains byte-for-byte contract-compatible.
- [x] Observe RED before implementation.
- [x] Implement the renderer and select it only for `research_mode=True`.
- [x] Keep the existing public summary renderer unchanged for Public mode.
- [x] Run focused helper and research-route contract tests.
- [x] Verify protected hashes and commit:

```bash
git commit -m "Render answer-first Company Brief"
```

---

### Task 3: Gate long Workbench modules behind one explicit action

**Files:**

- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Contract:**

Before the first research-only module is rendered, compute the existing change answer, conclusion cards, and authoritative task once, render the primary brief, then apply a session-local detail gate:

- default state: show the Company Brief plus one `Open evidence and analysis modules` action;
- opened state: preserve the existing module sequence, authoring, HTML brief, evidence drawers, and calculations;
- closing/reloading cannot change canonical data or readiness;
- the primary brief remains exactly once in either state.

- [x] Write behavior/route tests first for:
  - default Workbench does not render Research Decision Lab, Business Trend, Valuation, Forward View, authoring forms, HTML brief, raw evidence, or conclusion modules before the explicit action;
  - the primary brief and stop rule remain visible in the default state;
  - opening details restores the existing modules and HTML download contract;
  - authoritative task arbitration runs once and is reused;
  - public report detail behavior is unchanged;
  - no file writes occur during either render state.
- [x] Observe RED against the currently always-rendered research modules.
- [x] Implement the early research-only detail gate using the existing session-state detail key or one Workbench-specific compatibility-safe wrapper.
- [x] Remove duplicated primary Next Research Task rendering from the opened detail layer while retaining the same task object for the HTML brief snapshot.
- [x] Keep detailed change, conclusion, methodology, authoring, and evidence identities available only after the explicit action or under existing Advanced drawers.
- [x] Run focused Workbench, HTML-brief, authoring, route-render, and public compatibility tests.
- [x] Verify protected hashes and commit:

```bash
git commit -m "Gate secondary Workbench modules"
```

---

### Task 4: Responsive, accessibility, documentation, and release closure

**Files:**

- Modify: `src/research_accessibility_browser_gate.py` only if the current behavior contract requires new primary-brief assertions
- Modify: `tests/test_research_accessibility_browser_gate.py`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: this plan

- [x] Add behavior-first browser assertions for one primary brief, four visible answers, two 44px actions, visible stop rule, closed detailed modules by default, no overflow, no traceback, and exact ticker preservation at `1280x720` and `390x844`.
- [x] Update docs to say Discover is complete and Company Workbench primary-brief composition is current, without claiming source, hosted, human-accessibility, demand, calibration, or market validation.
- [x] Keep Monitor consolidation as the next separate local slice, followed by Research Desk simplification and shared-shell cleanup.
- [x] Run the full local matrix at `35b355a5921bd7d7e9f3c46ab28a799f9e42818e`: 6,323 tests passed; dashboard, six-route research render, public wording, public share, and 60/60 performance checks passed; pilot readiness remained truthfully blocked on working readiness and external source proof:

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make public-performance-gate
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

- [x] Compare all 18 protected hashes byte-for-byte with Task 0.
- [x] Stage exact intentional product/code/docs/test files only; never use `git add -A`.
- [x] Run `make staged-hygiene-check` and `git diff --cached --check`.
- [x] Commit the browser closure package and run `make research-accessibility-browser-check` on the clean product tree. Exact local runtime anchor `ad431eadbd00df71419f91e3a18408b0afeb94e4` passed all six routes at `1280x720` and `390x844`, including the closed Company Brief and explicit detail restoration.
- [ ] Push only `codex/personal-research-mode-mvp`.
- [ ] Update PR #113, keep it draft, and require exact-head `local-engineering-gate` success.

---

## Completion evidence

This slice is complete only when the pushed exact HEAD directly proves:

- one answer-first Company Brief appears before all secondary Workbench modules;
- the default route is materially shorter because detailed modules are closed;
- all original calculations, identities, authoring persistence, and HTML brief behavior remain available after explicit open;
- Public mode is unchanged;
- focused/full/browser/release/hygiene gates pass;
- protected generated artifacts remain excluded and byte-identical;
- PR #113 remains open, draft, mergeable, and exact-head CI passes.

Local automation does not complete source-rights, current-data, hosted-operation, independent-human accessibility, external reviewer, demand, calibration, or product-market-fit gates.
