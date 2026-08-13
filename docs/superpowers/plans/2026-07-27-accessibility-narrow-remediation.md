# Accessibility Narrow Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the five reproduced keyboard, narrow-navigation, link-name, disclosure-focus, and authoring-error defects without changing research behavior.

**Architecture:** Pure HTML/CSS helpers provide deterministic navigation and link labels. A fixed local accessibility bridge may apply field ARIA attributes and focus only after rejected user-triggered validation; it never reads field values, invokes actions, transmits data, or changes draft and ledger state.

**Tech Stack:** Python 3, Streamlit, fixed same-origin JavaScript component, HTML/CSS, pytest, Streamlit AppTest, Playwright browser verification.

## Global Constraints

- This slice does not claim WCAG conformance or screen-reader success.
- The skip link is the first application-owned focus target and preserves the full current route.
- Narrow navigation contains exactly Research Desk, Discover, Company Workbench when a ticker exists, and Monitor; it never exposes Operator routes.
- Discover action names include the exact ticker without changing ordering or destinations.
- Field-error binding is presentation-only and cannot change draft digest, preview receipt, confirmation, append engine, or ledger.
- The bridge can set accessibility attributes and focus only; it cannot read or transmit field values or invoke application actions.
- No readiness, evidence, forecast, ledger, generated-data, or route-boundary change.
- Generated CSV, JSON, report, sample-report, screenshot, timing, canonical-data, and manual-review churn remain unstaged.

---

### Task 1: Deterministic Workflow Navigation, Link Names, and Focus CSS

**Files:**
- Modify: `src/research_workspace.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_workspace.py`
- Modify: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Produces: `research_workflow_navigation_html(*, active_page: str, ticker: str = "") -> str`.
- Produces: `discover_review_action_label(ticker: str) -> str`.
- Preserves: current route query format and readiness ordering.

- [ ] **Step 1: Write failing HTML and CSS contract tests**

```python
def test_mobile_workflow_navigation_is_labelled_and_has_one_current_page():
    rendered = research_workflow_navigation_html(active_page="discover", ticker="AVGO")
    assert "aria-label='Personal research workflow'" in rendered
    assert rendered.count("aria-current='page'") == 1
    assert all(label in rendered for label in ("Research Desk", "Discover", "Company Workbench", "Monitor"))
    assert "ticker=AVGO" in rendered


def test_discover_action_label_is_ticker_specific():
    assert discover_review_action_label("avgo") == "Open AVGO review"
```

Add a source-contract assertion that shared theme CSS contains `summary:focus-visible`.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python3 -m pytest tests/test_research_workspace.py tests/test_dashboard_helpers.py -q`

Expected: FAIL because the new helpers and summary focus rule do not exist.

- [ ] **Step 3: Implement escaped route HTML and the shared focus rule**

Use the existing research query parameters. Omit Company Workbench when `ticker.strip()` is empty. Apply `aria-current="page"` only to the active link. Render visible action text as `Open {TICKER} review` at both Discover action locations. Extend the existing visible focus selector group with:

```css
summary:focus-visible {
    outline: 3px solid #0f766e;
    outline-offset: 3px;
}
```

- [ ] **Step 4: Render the navigation on all four Personal Research routes**

Place the navigation directly after the skip link and before the route answer. Add narrow-width styling that keeps it visible, wraps links, preserves 44px interactive height, and produces no horizontal overflow at `390x844`.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_research_workspace.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the deterministic UI repairs**

```bash
git add src/research_workspace.py src/dashboard.py tests/test_research_workspace.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py
git commit -m "Improve research workflow accessibility"
```

### Task 2: First Application-Owned Skip Focus

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Consumes: existing `public_workflow_skip_link_html("#public-page-answer")`.
- Preserves: `mode`, `page`, `ticker`, and `open` through the fragment-only target.

- [ ] **Step 1: Add a failing render-order contract test**

```python
def test_skip_link_renders_before_application_sidebar_widgets():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    skip_call = source.index("render_public_workflow_skip_link(")
    sidebar_call = source.index("render_sidebar(")
    assert skip_call < sidebar_call
```

Use the actual sidebar entrypoint name found in `main()` when writing the final test; assert the exact call order, not a broad string count.

- [ ] **Step 2: Run the test and confirm it fails against current order**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py -q`

Expected: FAIL with the sidebar call before the skip-link call.

- [ ] **Step 3: Move the skip link before application-owned sidebar rendering**

Keep exactly one skip link. Do not move route content, change query parameters, or create a second destination. Ensure hidden project-controlled controls use `display: none` or are not focusable rather than merely visually hidden.

- [ ] **Step 4: Run focused contract and render tests**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the focus-entry repair**

```bash
git add src/dashboard.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py
git commit -m "Place skip link before application controls"
```

### Task 3: Field-Level Authoring Error Association

**Files:**
- Create: `src/accessibility_bridge.py`
- Create: `tests/test_accessibility_bridge.py`
- Modify: `src/research_record_authoring_ui.py`
- Modify: `tests/test_research_record_authoring_ui.py`

**Interfaces:**
- Produces: `AuthoringFieldError(field_name: str, field_label: str, message: str, error_id: str)`.
- Produces: `authoring_field_error(reason: str, *, profile_key: str, ticker: str, kind: str) -> AuthoringFieldError | None`.
- Produces: `render_authoring_error_binding(component_html: Callable[..., Any], error: AuthoringFieldError) -> None`.
- Bridge input contains field label and fixed generated error ID only; it contains no field value.

- [ ] **Step 1: Write failing deterministic-mapping and security tests**

```python
def test_required_thesis_id_maps_to_stable_field_error():
    error = authoring_field_error(
        "thesis_id is required", profile_key="personal", ticker="AVGO", kind="thesis"
    )
    assert error is not None
    assert error.field_name == "thesis_id"
    assert error.field_label == "Thesis Id"
    assert error.error_id == "research-authoring-personal-avgo-thesis-thesis-id-error"


def test_accessibility_bridge_has_no_network_or_value_reading():
    source = Path("src/accessibility_bridge.py").read_text(encoding="utf-8").lower()
    for forbidden in ("fetch(", "xmlhttprequest", "websocket", "localstorage", "sessionstorage", ".value"):
        assert forbidden not in source
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `python3 -m pytest tests/test_accessibility_bridge.py tests/test_research_record_authoring_ui.py -q`

Expected: FAIL because the mapping and bridge do not exist.

- [ ] **Step 3: Implement exact rejected-reason mapping**

Parse only the existing validation form `"<field_name> is required"` and accept the result only when `field_name` is in `authoring_field_contract(kind)`. Unknown reasons return `None`; do not guess. Build the stable ID from normalized profile, ticker, kind, and field name.

- [ ] **Step 4: Implement the bounded presentation bridge**

Render one bounded local component script through `streamlit.components.v1.html`. It finds exactly one Streamlit widget by its accessible label, sets `aria-invalid="true"` and `aria-describedby=error.error_id`, focuses it after the validation button attempt, and creates one stable text error immediately beside that widget inside the authoring expander. Escape configuration through `json.dumps`; pass only field label, fixed error ID, and deterministic validation message. Retain `st_api.error(preview.reason)` for alert announcement. If zero or multiple matching fields exist, change no field.

- [ ] **Step 5: Prove preview and ledger semantics remain unchanged**

Extend AppTest coverage to submit an empty thesis, assert one field-bound error and one global alert, and assert the journal, catalyst, and outcome ledger bytes are unchanged. Retain all existing preview-digest and confirm-before-save tests.

- [ ] **Step 6: Run focused tests**

Run: `python3 -m pytest tests/test_accessibility_bridge.py tests/test_research_record_authoring_ui.py -q`

Expected: PASS.

- [ ] **Step 7: Commit authoring accessibility**

```bash
git add src/accessibility_bridge.py src/research_record_authoring_ui.py tests/test_accessibility_bridge.py tests/test_research_record_authoring_ui.py
git commit -m "Associate authoring errors with fields"
```

### Task 4: Direct Browser Retest and Durable Evidence

**Files:**
- Create: `src/research_accessibility_browser_gate.py`
- Create: `tests/test_research_accessibility_browser_gate.py`
- Modify: `Makefile`
- Modify: `docs/ACCESSIBILITY_EVIDENCE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: running local Streamlit dashboard and the five repaired contracts.
- Produces: `run_research_accessibility_browser_gate(base_dir: Path | str, *, base_url: str = "", chrome_executable: Path | None = None) -> dict[str, object]`.
- Produces: `python3 -m src.research_accessibility_browser_gate` and `make research-accessibility-browser-check`.
- Produces: reproducible engineering evidence only, explicitly not a conformance claim.

- [ ] **Step 1: Write failing gate-contract tests**

```python
def test_accessibility_browser_gate_covers_both_viewports_and_research_routes():
    assert VIEWPORTS == ((1280, 720), (390, 844))
    assert [route.name for route in RESEARCH_ROUTES[:4]] == [
        "Research Desk", "Discover", "Company Workbench", "Monitor"
    ]


def test_makefile_exposes_non_writing_browser_gate():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    assert "research-accessibility-browser-check:" in makefile
    assert "python3 -m src.research_accessibility_browser_gate" in makefile
```

- [ ] **Step 2: Run the new contract tests and confirm failure**

Run: `python3 -m pytest tests/test_research_accessibility_browser_gate.py -q`

Expected: FAIL because the gate module and Make target do not exist.

- [ ] **Step 3: Implement a read-only local browser harness**

Reuse the Chrome discovery and local Streamlit server lifecycle patterns from `src/public_performance_gate.py`, but record no timing or report file. Return a structured in-memory payload with one result per route, viewport, and assertion. Exit nonzero when any required assertion fails or Chrome/Playwright is unavailable.

- [ ] **Step 4: Add browser assertions for the five defects**

At desktop and `390x844`, assert: the skip link precedes application controls in Tab order; activation preserves the URL and focuses `#public-page-answer`; labelled mobile navigation is visible; ten Discover actions have unique ticker-specific names; `summary` shows a non-none focus outline; empty thesis preview binds one error to Thesis Id; document width does not exceed viewport; no traceback appears.

- [ ] **Step 5: Run unit and direct browser verification**

Run:

```bash
python3 -m pytest tests/test_research_accessibility_browser_gate.py -q
make research-accessibility-browser-check
```

Expected: PASS on all five direct retests at both viewports.

- [ ] **Step 6: Update evidence and roadmap truth**

Record the commands, viewports, exact five results, current commit, and explicit limitation: zoom, forced colors, reduced motion, screen-reader navigation, and independent human testing remain incomplete.

- [ ] **Step 7: Run full release and hygiene gates**

Run:

```bash
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

Expected: all pass without new generated artifact churn.

- [ ] **Step 8: Stage exact files, check hygiene, commit, push, and require exact-head CI**

```bash
git add src/dashboard.py src/research_workspace.py src/accessibility_bridge.py src/research_record_authoring_ui.py src/research_accessibility_browser_gate.py tests/test_dashboard_helpers.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_accessibility_bridge.py tests/test_research_record_authoring_ui.py tests/test_research_accessibility_browser_gate.py Makefile docs/ACCESSIBILITY_EVIDENCE.md ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git commit -m "Verify narrow accessibility remediations"
git push origin codex/personal-research-mode-mvp
gh pr checks 113 --watch
```

Expected: PR #113 remains open and draft; exact-head CI passes; generated working-data churn remains unstaged.
