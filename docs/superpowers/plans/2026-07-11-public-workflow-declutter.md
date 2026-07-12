# Public Workflow Declutter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining arbitrary, duplicated, and repetitive public UI content while preserving research-only and readiness-first boundaries.

**Architecture:** Keep the existing five-page public route structure and data models. Change only presentation helpers and route rendering in `src/dashboard.py`; use existing Streamlit controls and public QA contracts so no data pipeline, provider, or readiness behavior changes.

**Tech Stack:** Python, Streamlit, pandas, pytest, existing public route smoke and browser-QA helpers.

## Global Constraints

- Research-only; no investment advice, broker/account actions, order routing, auto-trading, or direct buy/sell language.
- Do not fabricate or alter prices, fundamentals, peers, earnings, estimates, or readiness values.
- Keep operator-only evidence and raw tables behind Advanced controls.
- Do not stage generated CSV/JSON/report/sample-report churn.

---

### Task 1: Make Stock Selector user-directed

**Files:**
- Modify: `src/dashboard.py`
- Test: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes: `stock_selector_apply_filters`, `stock_selector_result_table_html`.
- Produces: a direct public ticker search and a compact, limited initial result list without an arbitrary automatic starting ticker.

- [ ] **Step 1: Write the failing test**

```python
def test_public_selector_uses_direct_search_without_an_arbitrary_starting_ticker():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    render_index = source.index("def render_stock_selector(")
    assert '"Search this review queue"' in source[render_index:]
    assert "stock_selector_public_start_html(selector_path_cards[0])" not in source[render_index:]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q`

Expected: failure because the public selector still renders `Start with this ticker` before a user chooses one.

- [ ] **Step 3: Write minimal implementation**

```python
if public_mode:
    search = st.text_input("Search this review queue", key="stock-selector-search").strip()
```

Remove the public automatic-start surface, reuse the same search value in `stock_selector_apply_filters`, reduce public initial rows to ten, and keep the other filters behind `Advanced: refine filters`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q`

Expected: PASS.

### Task 2: Deduplicate public proof events

**Files:**
- Modify: `src/dashboard.py`
- Test: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes: `proof_history_public_timeline_html` frames.
- Produces: a maximum of three distinct public evidence events without raw ledger exposure.

- [ ] **Step 1: Write the failing test**

```python
def test_public_proof_timeline_deduplicates_identical_events():
    frame = pd.DataFrame([...two matching proof records...])
    rendered = dashboard.proof_history_public_timeline_html(pd.DataFrame(), frame)
    assert rendered.count("Yahoo returned only available post-listing history") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q`

Expected: failure because matching batch entries render twice.

- [ ] **Step 3: Write minimal implementation**

```python
seen = set()
for event in events:
    fingerprint = event[:4]
    if fingerprint not in seen:
        distinct_events.append(event)
        seen.add(fingerprint)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q`

Expected: PASS.

### Task 3: Collapse the single-stock detail gate

**Files:**
- Modify: `src/dashboard.py`
- Test: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes: `single_stock_detail_sections_visible` and the existing detailed-section button.
- Produces: one public explanation and one detail-reveal command instead of separate table and detail gates.

- [ ] **Step 1: Write the failing test**

```python
def test_public_single_stock_uses_one_detail_gate_before_report_sections():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    assert source.count('"Advanced: answer tables"') == 0
    assert '"Show detailed report sections"' in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q`

Expected: failure because answer tables and detailed sections are separately gated.

- [ ] **Step 3: Write minimal implementation**

Remove the public `Advanced: answer tables` expander. Keep its two dataframes inside the existing public detailed-report expander after the visitor explicitly chooses to show detailed report sections.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q`

Expected: PASS.

### Task 4: Verify and package the reviewed slice

**Files:**
- Modify only intentional code/tests/docs from Tasks 1-3.

- [ ] **Step 1: Run focused routes and public gates**

Run:

```bash
python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py tests/test_public_home_workflow.py tests/test_single_stock_workflow.py tests/test_data_health_pilot_console.py tests/test_browser_qa_evidence.py -q
make dashboard-smoke
make browser-qa-evidence
make public-wording-check
git diff --check
```

- [ ] **Step 2: Run the full verification**

Run: `python3 -m pytest tests -q && make public-check`

- [ ] **Step 3: Commit only the reviewed UI package**

```bash
git add -- docs/superpowers/plans/2026-07-11-public-workflow-declutter.md src/dashboard.py tests/test_dashboard_helpers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Declutter public research workflow"
```
