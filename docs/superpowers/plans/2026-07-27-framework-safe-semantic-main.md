# Framework-Safe Semantic Main Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the actual Streamlit primary content container the single stable `main` landmark on every Personal Research route.

**Architecture:** Extend the fixed local accessibility bridge with an idempotent same-origin script targeting exactly one `[data-testid="stMain"]`. The script sets metadata on the existing container, replaces its own prior observer on rerender, and never creates, moves, reads, transmits, or persists research content.

**Tech Stack:** Python 3, Streamlit components, fixed JavaScript, MutationObserver, pytest, Streamlit AppTest, Playwright browser verification.

## Global Constraints

- Target exactly one `[data-testid="stMain"]`; never attach the landmark to a fallback node.
- Set `role="main"`, `id="research-main"`, and `aria-label="Stock research workspace"` on the existing primary container.
- Reuse an existing native or role-based main and never create a second landmark.
- The helper is called exactly once per dashboard run after theme initialization and before page content.
- The bridge uses no user-provided interpolation, network, telemetry, cookies, storage, clipboard, form values, callbacks, navigation, or application actions.
- Absence or ambiguity produces no false landmark and no user-visible traceback; browser verification must fail until exactly one target resolves.
- No readiness, evidence, authoring, routing, generated-data, or research-result change.
- Automated DOM evidence is not screen-reader usability or WCAG conformance.

---

### Task 1: Fixed Idempotent Landmark Bridge

**Files:**
- Modify: `src/accessibility_bridge.py`
- Modify: `tests/test_accessibility_bridge.py`

**Interfaces:**
- Produces: `SEMANTIC_MAIN_BRIDGE_HTML: str`.
- Produces: `render_semantic_main_bridge(component_html: Callable[..., Any] = streamlit.components.v1.html) -> None`.
- JavaScript status attribute: `data-research-main-bridge-status`, with exact values `applied`, `missing`, or `ambiguous`.
- Reuses: the fixed local component-rendering pattern introduced by the narrow accessibility slice.

- [ ] **Step 1: Write failing source-contract tests**

```python
def test_semantic_main_bridge_is_fixed_idempotent_and_non_networked():
    source = SEMANTIC_MAIN_BRIDGE_HTML.lower()
    assert '[data-testid="stmain"]' in source
    assert 'role' in source and 'main' in source
    assert 'research-main' in source
    assert 'stock research workspace' in source
    assert 'mutationobserver' in source
    assert 'disconnect()' in source
    for forbidden in ("fetch(", "xmlhttprequest", "websocket", "localstorage", "sessionstorage", "clipboard", ".value"):
        assert forbidden not in source
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python3 -m pytest tests/test_accessibility_bridge.py -q`

Expected: FAIL because the semantic-main bridge contract is absent.

- [ ] **Step 3: Implement exact-target application and observer replacement**

The fixed script must:

```javascript
const host = window.parent.document;
const observerKey = "__stockResearchMainObserver";
const targetKey = "__stockResearchMainTarget";
if (window.parent[observerKey]) {
  window.parent[observerKey].disconnect();
}
function applyMainLandmark() {
  const nodes = host.querySelectorAll('[data-testid="stMain"]');
  const status = nodes.length === 1 ? "applied" : (nodes.length === 0 ? "missing" : "ambiguous");
  host.documentElement.setAttribute("data-research-main-bridge-status", status);
  const previous = window.parent[targetKey];
  if (previous && (nodes.length !== 1 || previous !== nodes[0])) {
    if (previous.getAttribute("data-research-main-bridge-owned") === "true") {
      previous.removeAttribute("role");
      previous.removeAttribute("id");
      previous.removeAttribute("aria-label");
      previous.removeAttribute("data-research-main-bridge-owned");
    }
    window.parent[targetKey] = null;
  }
  if (nodes.length !== 1) return;
  const target = nodes[0];
  if (target.tagName.toLowerCase() !== "main" && target.getAttribute("role") !== "main") {
    target.setAttribute("data-research-main-bridge-owned", "true");
  }
  target.setAttribute("role", "main");
  target.setAttribute("id", "research-main");
  target.setAttribute("aria-label", "Stock research workspace");
  window.parent[targetKey] = target;
}
applyMainLandmark();
window.parent[observerKey] = new MutationObserver(applyMainLandmark);
window.parent[observerKey].observe(host.body, {childList: true, subtree: true});
```

Before setting attributes, remove no native semantics and create no element. On a missing or ambiguous rerender, remove only attributes previously owned by this bridge; never remove attributes from a native or pre-existing main. The Python helper renders only this constant and accepts no research-content arguments.

- [ ] **Step 4: Add missing and ambiguous behavior tests**

Use a small JavaScript-capable DOM test if already available; otherwise source-contract tests must prove `nodes.length !== 1` returns before any target mutation and that all three deterministic statuses exist.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_accessibility_bridge.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the bridge**

```bash
git add src/accessibility_bridge.py tests/test_accessibility_bridge.py
git commit -m "Add idempotent semantic main bridge"
```

### Task 2: Exactly-Once Dashboard Integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Consumes: `render_semantic_main_bridge(st_api: Any) -> None`.
- Produces: exactly one call in the main dashboard execution path after `apply_dashboard_theme()` and before sidebar or route content.

- [ ] **Step 1: Write a failing call-order and call-count test**

```python
def test_semantic_main_bridge_runs_once_after_theme_before_route_content():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    assert source.count("render_semantic_main_bridge()") == 1
    theme_index = source.index("apply_dashboard_theme()")
    bridge_index = source.index("render_semantic_main_bridge()")
    route_index = source.index("render_research_desk(")
    assert theme_index < bridge_index < route_index
```

Anchor the final route-order assertion to the actual route dispatch block so function definitions earlier in the file cannot create a false result.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q`

Expected: FAIL because the bridge is not called.

- [ ] **Step 3: Import and call the bridge once**

Add one top-level import and one execution-path call. Do not call it inside individual route renderers. Preserve the existing `#public-page-answer` target and all sidebar, routing, authoring, and readiness behavior.

- [ ] **Step 4: Run focused contract and smoke tests**

Run: `python3 -m pytest tests/test_accessibility_bridge.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the integration**

```bash
git add src/dashboard.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py
git commit -m "Apply semantic main landmark once"
```

### Task 3: Six-Route Desktop and Phone Verification

**Files:**
- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`
- Modify: `docs/ACCESSIBILITY_EVIDENCE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: Research Desk, Discover, ticker-bound Company Workbench, Monitor, Data Health, and Proof History.
- Extends: `run_research_accessibility_browser_gate(...)` with the landmark assertions; it remains in-memory and non-writing.
- Produces: direct current DOM evidence at desktop and `390x844`.

- [ ] **Step 1: Add browser assertions for the complete landmark contract**

For each of the six routes and both viewports, assert:

```javascript
const mains = page.getByRole("main");
await expect(mains).toHaveCount(1);
await expect(mains).toHaveAttribute("id", "research-main");
await expect(mains).toHaveAttribute("aria-label", "Stock research workspace");
await expect(mains.locator("#public-page-answer")).toHaveCount(1);
await expect(mains.getByRole("heading", {level: 1})).toHaveCount(1);
```

Navigate away and back once to force rerender, then repeat the count. Assert `data-research-main-bridge-status="applied"`, no console error, and no traceback. Activate the skip link and assert the focused target is inside the main landmark.

- [ ] **Step 2: Extend the route contract unit test**

```python
def test_accessibility_browser_gate_covers_all_six_personal_research_routes():
    assert [route.name for route in RESEARCH_ROUTES] == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
        "Data Health",
        "Proof History",
    ]
```

- [ ] **Step 3: Run the six-route browser verification**

Run:

```bash
python3 -m pytest tests/test_research_accessibility_browser_gate.py -q
make research-accessibility-browser-check
```

Expected: exactly one main landmark on all twelve route/viewport combinations, including after rerender.

- [ ] **Step 4: Update evidence and roadmap boundaries**

Record current commit, routes, viewports, commands, and outcomes. State explicitly that automated DOM verification does not prove screen-reader landmark navigation, WCAG conformance, hosted behavior, or independent-human accessibility validation.

- [ ] **Step 5: Run full release and hygiene gates**

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

- [ ] **Step 6: Stage exact files, run staged hygiene, commit, push, and require exact-head CI**

```bash
git add src/accessibility_bridge.py src/dashboard.py src/research_accessibility_browser_gate.py tests/test_accessibility_bridge.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_research_accessibility_browser_gate.py docs/ACCESSIBILITY_EVIDENCE.md ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git commit -m "Verify semantic main landmark"
git push origin codex/personal-research-mode-mvp
gh pr checks 113 --watch
```

Expected: PR #113 remains open and draft; exact-head CI passes; generated working-data churn remains unstaged.
