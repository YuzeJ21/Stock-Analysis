# Public Mobile Evidence Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the existing fail-closed Single-Stock Report reading order while making its Data Health evidence handoff fully visible in the first 390x844 phone viewport.

**Architecture:** Reuse the existing public shell and ticker-summary markup. Add only phone-scoped layout rules inside the existing `max-width: 640px` media query, protect them with a source contract, and use a fresh live browser measurement as the layout proof.

**Tech Stack:** Python 3.12, Streamlit, existing HTML/CSS renderer, pytest, in-app browser responsive audit.

## Global Constraints

- Selected ticker, Use now, and Still withheld remain before the evidence handoff.
- Desktop layout remains unchanged.
- No copy, readiness, evidence, source, forecast, probability, or data state changes.
- Advanced details remain collapsed.
- No generated research or manual-review artifact enters the repository.

---

### Task 1: Phone-Scoped Handoff Contract and CSS

**Files:**
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `src/dashboard.py`

**Interfaces:**
- Consumes: existing `render_public_shell_mode_styles()`, `.public-ticker-summary`, `.public-ticker-action`, and `.public-primary-action`.
- Produces: phone-only compact summary spacing and action-link ordering; no Python interface change.

- [ ] **Step 1: Write the failing source contract**

Add a test that extracts the `max-width: 640px` block inside `render_public_shell_mode_styles()` and requires:

```python
def test_public_single_stock_phone_keeps_evidence_handoff_in_first_view():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    shell_start = source.index("def render_public_shell_mode_styles")
    mobile_start = source.index("@media (max-width: 640px)", shell_start)
    mobile_end = source.index("</style>", mobile_start)
    mobile_css = source[mobile_start:mobile_end]

    summary_start = mobile_css.index(".public-ticker-summary {")
    summary_end = mobile_css.index("}", summary_start)
    summary_rule = mobile_css[summary_start:summary_end]
    action_start = mobile_css.index(".public-ticker-action .public-primary-action {")
    action_end = mobile_css.index("}", action_start)
    action_rule = mobile_css[action_start:action_end]

    assert "grid-template-columns: 1fr;" in summary_rule
    assert "gap: 0.25rem;" in summary_rule
    assert "padding: 0.125rem 0 0.5rem;" in summary_rule
    assert "order: -1;" in action_rule
```

- [ ] **Step 2: Run the test and confirm the current layout contract fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py::test_public_single_stock_phone_keeps_evidence_handoff_in_first_view -q
```

Expected during the final-review correction: failure because the exact summary
rule still uses `padding: 0.5rem 0`; declarations elsewhere in the mobile block
must not satisfy the selector-local contract.

- [ ] **Step 3: Add the minimal phone-only CSS**

In the existing `@media (max-width: 640px)` block, change only the ticker-summary phone rules:

```css
.public-ticker-summary {
  grid-template-columns: 1fr;
  gap: 0.25rem;
  padding: 0.125rem 0 0.5rem;
}
.public-ticker-action .public-primary-action {
  order: -1;
}
```

The DOM order and desktop CSS stay unchanged.

- [ ] **Step 4: Run focused contracts**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py::test_public_single_stock_phone_keeps_evidence_handoff_in_first_view tests/test_dashboard_helpers.py::test_public_workflow_controls_reserve_accessible_touch_targets tests/test_dashboard_helpers.py::test_public_app_shell_has_compact_mobile_rules -q
```

Expected: three passing tests.

- [ ] **Step 5: Verify the live 390x844 route**

Reload `http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1` at 390x844 and measure the existing `Open Data Health` link. Expected:

- the link top is at least 0;
- the link bottom is at most 844;
- `document.documentElement.scrollWidth <= window.innerWidth + 2`;
- no traceback is present;
- Selected ticker, Use now, and Still withheld precede the link in document order.

Save the accepted screenshot only under `/tmp/stock-command-center-public-ux-review`.
The final accepted measurement is `top=792.53125px`, `bottom=836.53125px`,
leaving `7.46875px` of clearance in the `844px` viewport. The computed summary
spacing is `gap=4px`, `padding-top=2px`, and `padding-bottom=8px`.

- [ ] **Step 6: Commit the tested product correction**

Stage exactly `src/dashboard.py` and `tests/test_dashboard_helpers.py`, run staged hygiene, and commit with:

```bash
git commit -m "Keep mobile evidence handoff in view"
```

---

### Task 2: QA and Continuation Evidence

**Files:**
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: the verified phone CSS and fresh 390x844 browser result from Task 1.
- Produces: truthful current audit evidence and the persistent continuation boundary.

- [ ] **Step 1: Update documentation contracts**

Record:

- all five public pages passed fresh desktop and phone review without overflow or tracebacks;
- Single-Stock Report required and received a phone-only evidence-handoff density correction;
- Data Health and Proof History remain answer/evidence destinations and do not gain invented calls to action;
- no readiness, source, research, or generated artifact state changed.

- [ ] **Step 2: Run focused documentation and render tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_public_v1_release_docs.py tests/test_browser_qa_evidence.py tests/test_public_ux_review_checklist.py tests/test_dashboard_render_smoke.py -q
make research-dashboard-render-smoke
```

Expected: all tests and route renders pass.

- [ ] **Step 3: Run full release verification**

Run the full pytest suite, dashboard and public render smokes, public wording, commercial beta, public, commercial release, pilot, diff, PR-range, whitespace, and staged hygiene gates required by the continuation contract.

- [ ] **Step 4: Commit, push, and verify the draft PR**

Stage exactly the three documentation files, run staged hygiene, commit with:

```bash
git commit -m "Document public mobile workflow audit"
```

Push only `codex/personal-research-mode-mvp`, update draft PR #113, and require a successful exact-head GitHub Actions result. Keep the PR draft; do not merge or deploy.
