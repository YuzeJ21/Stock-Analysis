# Accessibility Media Preferences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit forced-colors and reduced-motion behavior plus read-only automated regression evidence across the existing six-route, two-viewport Research accessibility matrix.

**Architecture:** A pure CSS helper in `src/research_workspace.py` owns the Research media-preference rules and `src/dashboard.py` injects them after the existing Research styles. Pure evaluators and bounded browser-observation helpers in `src/research_accessibility_browser_gate.py` exercise both preferences sequentially in each existing page context, restore ordinary media settings, and retain every current landmark, navigation, state, runtime, and repository-write check.

**Tech Stack:** Python 3.12, Streamlit, HTML/CSS, Playwright sync API, pytest, Make, GitHub Actions.

## Global Constraints

- Automated forced-colors and reduced-motion results are engineering evidence only; they are not manual task completion, assistive-technology validation, independent-human review, hosted validation, or WCAG conformance.
- Keep the existing six routes and `VIEWPORTS == ((1280, 720), (390, 844))`; add no route, browser context, server process, screenshot, timing file, or report artifact.
- Preserve Research Desk -> Discover -> Company Workbench -> Monitor, Data Health, Proof History, independent readiness states, research-only copy, and all fail-closed source and quantitative boundaries.
- Add no source, dataset, readiness promotion, forecast, probability, recommendation, research record, ledger mutation, or generated CSV/JSON/report/sample-report/screenshot/timing artifact.
- Ordinary media preferences must be restored even when one emulated-mode observation raises.
- Never run `make readiness`, broad refreshes, provider-wide imports, or generated report commands.
- Never use `git add -A`; stage only the exact files named by each task and keep the existing 18 generated paths unstaged.
- Keep PR #113 open and draft; push only `codex/personal-research-mode-mvp`; do not merge or deploy.

---

### Task 1: Shared Research Media-Preference CSS

**Files:**
- Modify: `src/research_workspace.py`
- Modify: `src/dashboard.py`
- Test: `tests/test_research_workspace.py`
- Test: `tests/test_research_mode_dashboard_contract.py`

**Interfaces:**
- Produces: `research_accessibility_media_preferences_css() -> str`.
- Consumes: the existing `render_research_workspace_styles()` composition point.
- Preserves: every normal-theme selector and all existing Research HTML.

- [ ] **Step 1: Write the failing CSS-helper contract test**

Add the helper to the import list in `tests/test_research_workspace.py`, then add:

```python
def test_research_accessibility_media_preferences_css_declares_bounded_fallbacks():
    css = research_accessibility_media_preferences_css()

    assert "@media (forced-colors: active)" in css
    assert ".research-workflow-link[aria-current='page']" in css
    assert ".research-workspace-boundary" in css
    assert "outline: 3px solid Highlight !important" in css
    assert "border-color: CanvasText !important" in css
    assert "box-shadow: none !important" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".stApp *::before" in css
    assert ".stApp *::after" in css
    assert "animation-duration: 0.01ms !important" in css
    assert "animation-iteration-count: 1 !important" in css
    assert "transition-duration: 0.01ms !important" in css
    assert "transition-delay: 0ms !important" in css
    assert "scroll-behavior: auto !important" in css
    assert "forced-color-adjust: none" not in css
```

Add this render-composition contract to `tests/test_research_mode_dashboard_contract.py`:

```python
def test_research_workspace_styles_inject_media_preferences_after_normal_styles():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_research_workspace_styles()")
    end = source.index("\ndef render_research_workspace_header(", start)
    styles = source[start:end]

    normal_styles = styles.index("st.markdown(")
    preferences = styles.index("research_accessibility_media_preferences_css()")
    assert normal_styles < preferences
    assert "unsafe_allow_html=True" in styles[preferences:]
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 -m pytest \
  tests/test_research_workspace.py::test_research_accessibility_media_preferences_css_declares_bounded_fallbacks \
  tests/test_research_mode_dashboard_contract.py::test_research_workspace_styles_inject_media_preferences_after_normal_styles \
  -q
```

Expected: collection or assertion failure because `research_accessibility_media_preferences_css` does not exist and the renderer does not inject it.

- [ ] **Step 3: Implement the pure CSS helper**

Add this function near the existing Research HTML helpers in `src/research_workspace.py`:

```python
def research_accessibility_media_preferences_css() -> str:
    """Return Research-only media preference fallbacks without changing data."""

    return """
@media (forced-colors: active) {
  .stApp a:focus-visible,
  .stApp button:focus-visible,
  .stApp input:focus-visible,
  .stApp select:focus-visible,
  .stApp textarea:focus-visible,
  .stApp [role="button"]:focus-visible,
  .stApp [role="radio"]:focus-visible,
  .stApp [role="tab"]:focus-visible,
  .stApp summary:focus-visible,
  .stApp [tabindex]:not([tabindex="-1"]):focus-visible {
    outline: 3px solid Highlight !important;
    outline-offset: 3px !important;
    box-shadow: none !important;
  }
  .research-workflow-link[aria-current='page'] {
    border: 2px solid Highlight !important;
    outline: 1px solid CanvasText !important;
    outline-offset: -4px !important;
  }
  .research-workspace-boundary,
  .observation-recency-summary,
  .research-state-message,
  .signal-card {
    border-color: CanvasText !important;
  }
  .research-workspace-boundary {
    border-style: solid !important;
    border-width: 1px !important;
    border-radius: 4px;
    padding: 0.2rem 0.35rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .stApp,
  .stApp *,
  .stApp *::before,
  .stApp *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    transition-delay: 0ms !important;
    scroll-behavior: auto !important;
  }
}
""".strip()
```

- [ ] **Step 4: Inject the helper after existing Research styles**

Import `research_accessibility_media_preferences_css` in `src/dashboard.py`. At the end of `render_research_workspace_styles()`, after the existing normal style block, add:

```python
    st.markdown(
        "<style>" + research_accessibility_media_preferences_css() + "</style>",
        unsafe_allow_html=True,
    )
```

- [ ] **Step 5: Run focused CSS and render tests**

Run:

```bash
python3 -m pytest \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_render_smoke.py \
  -q
```

Expected: PASS with no generated files changed.

- [ ] **Step 6: Commit the CSS contract**

```bash
git add -- \
  src/research_workspace.py \
  src/dashboard.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add research media preference styles"
```

---

### Task 2: Pure Fail-Closed Media Observation Evaluators

**Files:**
- Modify: `src/research_accessibility_browser_gate.py`
- Test: `tests/test_research_accessibility_browser_gate.py`

**Interfaces:**
- Produces: `evaluate_forced_colors_observation(observation: dict[str, object], *, primary_route: bool) -> list[dict[str, object]]`.
- Produces: `evaluate_reduced_motion_observation(observation: dict[str, object]) -> list[dict[str, object]]`.
- Consumes: literal browser observations only; neither function receives a page object.

- [ ] **Step 1: Write the failing forced-colors evaluator test**

Add:

```python
def test_forced_colors_observation_fails_closed_for_each_required_signal():
    from src.research_accessibility_browser_gate import (
        evaluate_forced_colors_observation,
    )

    passing = {
        "media_active": True,
        "skip_count": 1,
        "skip_focused": True,
        "skip_outline_style": "solid",
        "skip_outline_width_px": 3.0,
        "current_route_count": 1,
        "current_route_value": "page",
        "current_route_marker_width_px": 2.0,
        "boundary_count": 1,
        "boundary_visible": True,
        "boundary_border_width_px": 1.0,
        "heading_visible": True,
        "boundary_text_visible": True,
        "overflow_px": 0.0,
        "traceback_visible": False,
    }
    assertions = evaluate_forced_colors_observation(passing, primary_route=True)
    assert assertions and all(item["passed"] for item in assertions)

    mutations = (
        ("forced_colors_media_active", {"media_active": False}),
        ("forced_colors_skip_focus", {"skip_focused": False}),
        ("forced_colors_focus_outline", {"skip_outline_width_px": 0.0}),
        ("forced_colors_current_route", {"current_route_value": ""}),
        ("forced_colors_current_route_marker", {"current_route_marker_width_px": 0.0}),
        ("forced_colors_boundary", {"boundary_visible": False}),
        ("forced_colors_boundary_border", {"boundary_border_width_px": 0.0}),
        ("forced_colors_required_text", {"heading_visible": False}),
        ("forced_colors_no_overflow", {"overflow_px": 2.0}),
        ("forced_colors_no_traceback", {"traceback_visible": True}),
    )
    for name, changed in mutations:
        failed = evaluate_forced_colors_observation(
            {**passing, **changed},
            primary_route=True,
        )
        assert next(item for item in failed if item["name"] == name)["passed"] is False

    secondary = evaluate_forced_colors_observation(
        {**passing, "current_route_count": 0, "current_route_value": "", "current_route_marker_width_px": 0.0},
        primary_route=False,
    )
    assert all(item["passed"] for item in secondary)
```

- [ ] **Step 2: Write the failing reduced-motion evaluator test**

Add:

```python
def test_reduced_motion_observation_fails_closed_for_each_required_signal():
    from src.research_accessibility_browser_gate import (
        evaluate_reduced_motion_observation,
    )

    passing = {
        "media_active": True,
        "target_count": 3,
        "max_animation_duration_ms": 0.01,
        "max_transition_duration_ms": 0.01,
        "max_animation_iterations": 1.0,
        "scroll_behavior": "auto",
        "heading_visible": True,
        "boundary_visible": True,
        "overflow_px": 0.0,
        "traceback_visible": False,
    }
    assertions = evaluate_reduced_motion_observation(passing)
    assert assertions and all(item["passed"] for item in assertions)

    mutations = (
        ("reduced_motion_media_active", {"media_active": False}),
        ("reduced_motion_targets", {"target_count": 0}),
        ("reduced_motion_animation_duration", {"max_animation_duration_ms": 250.0}),
        ("reduced_motion_transition_duration", {"max_transition_duration_ms": 250.0}),
        ("reduced_motion_animation_iterations", {"max_animation_iterations": 2.0}),
        ("reduced_motion_scroll_behavior", {"scroll_behavior": "smooth"}),
        ("reduced_motion_required_text", {"boundary_visible": False}),
        ("reduced_motion_no_overflow", {"overflow_px": 2.0}),
        ("reduced_motion_no_traceback", {"traceback_visible": True}),
    )
    for name, changed in mutations:
        failed = evaluate_reduced_motion_observation({**passing, **changed})
        assert next(item for item in failed if item["name"] == name)["passed"] is False
```

- [ ] **Step 3: Run the evaluator tests and verify RED**

Run:

```bash
python3 -m pytest \
  tests/test_research_accessibility_browser_gate.py::test_forced_colors_observation_fails_closed_for_each_required_signal \
  tests/test_research_accessibility_browser_gate.py::test_reduced_motion_observation_fails_closed_for_each_required_signal \
  -q
```

Expected: collection failure because both evaluator functions are absent.

- [ ] **Step 4: Implement both pure evaluators**

Add the functions after `_assertion` in `src/research_accessibility_browser_gate.py`. Use these exact assertions and thresholds:

```python
def evaluate_forced_colors_observation(
    observation: dict[str, object],
    *,
    primary_route: bool,
) -> list[dict[str, object]]:
    current_route_passed = (
        int(observation.get("current_route_count", 0)) == 1
        and str(observation.get("current_route_value") or "") == "page"
    ) if primary_route else int(observation.get("current_route_count", 0)) == 0
    marker_passed = (
        float(observation.get("current_route_marker_width_px", 0)) > 0
        if primary_route
        else True
    )
    return [
        _assertion("forced_colors_media_active", observation.get("media_active") is True, "forced-colors media query active"),
        _assertion("forced_colors_skip_focus", int(observation.get("skip_count", 0)) == 1 and observation.get("skip_focused") is True, "one physical Tab focused the sole skip link"),
        _assertion("forced_colors_focus_outline", str(observation.get("skip_outline_style") or "") != "none" and float(observation.get("skip_outline_width_px", 0)) > 0, "focused skip link retains a visible outline"),
        _assertion("forced_colors_current_route", current_route_passed, "current-route semantic state preserved"),
        _assertion("forced_colors_current_route_marker", marker_passed, "current route retains a non-color marker"),
        _assertion("forced_colors_boundary", int(observation.get("boundary_count", 0)) == 1 and observation.get("boundary_visible") is True, "one research boundary remains visible"),
        _assertion("forced_colors_boundary_border", float(observation.get("boundary_border_width_px", 0)) > 0, "research boundary retains a visible border"),
        _assertion("forced_colors_required_text", observation.get("heading_visible") is True and observation.get("boundary_text_visible") is True, "heading and research-only text remain visible"),
        _assertion("forced_colors_no_overflow", float(observation.get("overflow_px", math.inf)) <= 1, f"horizontal overflow={observation.get('overflow_px')}px"),
        _assertion("forced_colors_no_traceback", observation.get("traceback_visible") is False, "no traceback rendered"),
    ]


def evaluate_reduced_motion_observation(
    observation: dict[str, object],
) -> list[dict[str, object]]:
    return [
        _assertion("reduced_motion_media_active", observation.get("media_active") is True, "reduced-motion media query active"),
        _assertion("reduced_motion_targets", int(observation.get("target_count", 0)) > 0, "application-owned motion targets observed"),
        _assertion("reduced_motion_animation_duration", float(observation.get("max_animation_duration_ms", math.inf)) <= 0.1, f"max animation duration={observation.get('max_animation_duration_ms')}ms"),
        _assertion("reduced_motion_transition_duration", float(observation.get("max_transition_duration_ms", math.inf)) <= 0.1, f"max transition duration={observation.get('max_transition_duration_ms')}ms"),
        _assertion("reduced_motion_animation_iterations", float(observation.get("max_animation_iterations", math.inf)) <= 1, f"max animation iterations={observation.get('max_animation_iterations')}"),
        _assertion("reduced_motion_scroll_behavior", str(observation.get("scroll_behavior") or "") != "smooth", f"scroll behavior={observation.get('scroll_behavior')!r}"),
        _assertion("reduced_motion_required_text", observation.get("heading_visible") is True and observation.get("boundary_visible") is True, "heading and research boundary remain visible"),
        _assertion("reduced_motion_no_overflow", float(observation.get("overflow_px", math.inf)) <= 1, f"horizontal overflow={observation.get('overflow_px')}px"),
        _assertion("reduced_motion_no_traceback", observation.get("traceback_visible") is False, "no traceback rendered"),
    ]
```

- [ ] **Step 5: Run focused evaluator and existing gate-contract tests**

```bash
python3 -m pytest tests/test_research_accessibility_browser_gate.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the pure contracts**

```bash
git add -- src/research_accessibility_browser_gate.py tests/test_research_accessibility_browser_gate.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add accessibility media evaluators"
```

---

### Task 3: Integrate Media Emulation Into Every Route Measurement

**Files:**
- Modify: `src/research_accessibility_browser_gate.py`
- Test: `tests/test_research_accessibility_browser_gate.py`

**Interfaces:**
- Produces: `_forced_colors_observation(page: Any, route: ResearchRoute) -> dict[str, object]`.
- Produces: `_reduced_motion_observation(page: Any, route: ResearchRoute) -> dict[str, object]`.
- Produces: `_media_preference_assertions(page: Any, route: ResearchRoute) -> list[dict[str, object]]`.
- Consumes: the Task 2 evaluator functions and existing `_horizontal_overflow_pixels` helper.
- Preserves: `_measure_route(...) -> dict[str, object]` and its current result schema.

- [ ] **Step 1: Write the failing emulation-order and restoration test**

Add:

```python
def test_media_preference_assertions_emulate_both_modes_and_restore_each(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        def __init__(self):
            self.calls = []

        def emulate_media(self, **kwargs):
            self.calls.append(kwargs)

    page = FakePage()
    monkeypatch.setattr(gate, "_forced_colors_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "_reduced_motion_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "evaluate_forced_colors_observation", lambda observation, *, primary_route: [{"name": "forced", "passed": True, "detail": "ok"}])
    monkeypatch.setattr(gate, "evaluate_reduced_motion_observation", lambda observation: [{"name": "motion", "passed": True, "detail": "ok"}])

    assertions = gate._media_preference_assertions(page, gate.RESEARCH_ROUTES[0])

    assert all(item["passed"] for item in assertions)
    assert page.calls == [
        {"forced_colors": "active", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "reduce"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
    ]
```

Add this restoration regression:

```python
def test_media_preference_assertions_restore_and_continue_after_probe_failure(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        def __init__(self):
            self.calls = []

        def emulate_media(self, **kwargs):
            self.calls.append(kwargs)

    def fail_forced(page, route):
        raise RuntimeError("forced probe")

    page = FakePage()
    monkeypatch.setattr(gate, "_forced_colors_observation", fail_forced)
    monkeypatch.setattr(gate, "_reduced_motion_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "evaluate_reduced_motion_observation", lambda observation: [{"name": "motion", "passed": True, "detail": "ok"}])

    assertions = gate._media_preference_assertions(page, gate.RESEARCH_ROUTES[0])

    forced = next(item for item in assertions if item["name"] == "forced_colors_execution")
    assert forced["passed"] is False
    assert "RuntimeError: forced probe" in forced["detail"]
    assert next(item for item in assertions if item["name"] == "motion")["passed"] is True
    assert page.calls == [
        {"forced_colors": "active", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "reduce"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
    ]
```

- [ ] **Step 2: Run the integration tests and verify RED**

Run:

```bash
python3 -m pytest tests/test_research_accessibility_browser_gate.py -q
```

Expected: failure because `_media_preference_assertions` and both observation helpers are absent.

- [ ] **Step 3: Implement bounded forced-colors observation**

Implement `_forced_colors_observation` with one bounded `page.evaluate` call that returns:

```python
{
    "media_active": bool(window.matchMedia("(forced-colors: active)").matches),
    "skip_count": int,
    "skip_focused": bool,
    "skip_outline_style": str,
    "skip_outline_width_px": float,
    "current_route_count": int,
    "current_route_value": str,
    "current_route_marker_width_px": float,
    "boundary_count": int,
    "boundary_visible": bool,
    "boundary_border_width_px": float,
    "heading_visible": bool,
    "boundary_text_visible": bool,
    "overflow_px": float,
    "traceback_visible": bool,
}
```

Before reading computed focus styles, clear application focus with the existing body-focus pattern and send one physical `page.keyboard.press("Tab")`. Require the focused element to be the sole `a.public-skip-link[href='#public-page-answer']`. For primary routes, inspect exactly one `.research-workflow-link[aria-current='page']`; for secondary routes, record zero. Inspect exactly one `.research-workspace-boundary` and the exact route H1.

Use this implementation shape so the browser returns only bounded literal
observations:

```python
def _forced_colors_observation(
    page: Any,
    route: ResearchRoute,
) -> dict[str, object]:
    page.evaluate(
        """
() => {
  if (document.activeElement && document.activeElement !== document.body) {
    document.activeElement.blur();
  }
  document.body.setAttribute("tabindex", "-1");
  document.body.focus({preventScroll: true});
}
"""
    )
    page.keyboard.press("Tab")
    page.evaluate("document.body.removeAttribute('tabindex')")
    return page.evaluate(
        """
(primaryRoute) => {
  const visible = (node) => {
    if (!node) return false;
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const width = (style, names) => Math.max(
    ...names.map((name) => Number.parseFloat(style[name]) || 0)
  );
  const skips = [...document.querySelectorAll(
    "a.public-skip-link[href='#public-page-answer']"
  )];
  const currents = [...document.querySelectorAll(
    ".research-workflow-link[aria-current='page']"
  )];
  const boundaries = [...document.querySelectorAll(
    ".research-workspace-boundary"
  )];
  const skipStyle = skips.length === 1 ? getComputedStyle(skips[0]) : null;
  const currentStyle = currents.length === 1 ? getComputedStyle(currents[0]) : null;
  const boundaryStyle = boundaries.length === 1 ? getComputedStyle(boundaries[0]) : null;
  const heading = document.querySelector("[role='main'] h1");
  return {
    media_active: matchMedia("(forced-colors: active)").matches,
    skip_count: skips.length,
    skip_focused: skips.length === 1 && document.activeElement === skips[0],
    skip_outline_style: skipStyle ? skipStyle.outlineStyle : "",
    skip_outline_width_px: skipStyle ? Number.parseFloat(skipStyle.outlineWidth) || 0 : 0,
    current_route_count: currents.length,
    current_route_value: currents.length === 1 ? currents[0].getAttribute("aria-current") || "" : "",
    current_route_marker_width_px: currentStyle ? width(currentStyle, ["borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth", "outlineWidth"]) : 0,
    boundary_count: boundaries.length,
    boundary_visible: boundaries.length === 1 && visible(boundaries[0]),
    boundary_border_width_px: boundaryStyle ? width(boundaryStyle, ["borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth"]) : 0,
    heading_visible: visible(heading),
    boundary_text_visible: boundaries.length === 1 && visible(boundaries[0]) && boundaries[0].innerText.includes("Research-only"),
    overflow_px: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    traceback_visible: document.body.innerText.includes("Traceback (most recent call last)"),
    primary_route: primaryRoute,
  };
}
""",
        route.requires_primary_navigation,
    )
```

- [ ] **Step 4: Implement bounded reduced-motion observation**

Use one `page.evaluate` call over `.stApp`, `.research-workflow-link`, `.research-workspace-boundary`, and `.research-state-message`. Parse every comma-separated CSS duration as milliseconds in the browser function: values ending in `ms` keep their numeric value; values ending in `s` multiply by `1000`; missing or unparsable values become the JSON-safe fail-closed sentinel `Number.MAX_SAFE_INTEGER`. Return the maximum animation duration, transition duration, and finite animation iteration count, plus media match, target count, computed `.stApp` scroll behavior, heading/boundary visibility, overflow, and traceback state.

Use this exact observation shape:

```python
def _reduced_motion_observation(
    page: Any,
    route: ResearchRoute,
) -> dict[str, object]:
    return page.evaluate(
        """
() => {
  const app = document.querySelector(".stApp");
  const visible = (node) => {
    if (!node) return false;
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const toMilliseconds = (value) => value.split(",").map((part) => {
    const token = part.trim();
    const amount = Number.parseFloat(token);
    if (!Number.isFinite(amount)) return Number.MAX_SAFE_INTEGER;
    if (token.endsWith("ms")) return amount;
    if (token.endsWith("s")) return amount * 1000;
    return Number.MAX_SAFE_INTEGER;
  });
  const toIterations = (value) => value.split(",").map((part) => {
    const token = part.trim();
    if (token === "infinite") return Number.MAX_SAFE_INTEGER;
    const amount = Number.parseFloat(token);
    return Number.isFinite(amount) ? amount : Number.MAX_SAFE_INTEGER;
  });
  const targets = [...new Set([
    app,
    ...document.querySelectorAll(".research-workflow-link"),
    ...document.querySelectorAll(".research-workspace-boundary"),
    ...document.querySelectorAll(".research-state-message"),
  ].filter(Boolean))];
  const styles = targets.map((node) => getComputedStyle(node));
  const animationDurations = styles.flatMap((style) => toMilliseconds(style.animationDuration));
  const transitionDurations = styles.flatMap((style) => toMilliseconds(style.transitionDuration));
  const iterations = styles.flatMap((style) => toIterations(style.animationIterationCount));
  const boundary = document.querySelector(".research-workspace-boundary");
  const heading = document.querySelector("[role='main'] h1");
  return {
    media_active: matchMedia("(prefers-reduced-motion: reduce)").matches,
    target_count: targets.length,
    max_animation_duration_ms: animationDurations.length ? Math.max(...animationDurations) : Number.MAX_SAFE_INTEGER,
    max_transition_duration_ms: transitionDurations.length ? Math.max(...transitionDurations) : Number.MAX_SAFE_INTEGER,
    max_animation_iterations: iterations.length ? Math.max(...iterations) : Number.MAX_SAFE_INTEGER,
    scroll_behavior: app ? getComputedStyle(app).scrollBehavior : "",
    heading_visible: visible(heading),
    boundary_visible: visible(boundary),
    overflow_px: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    traceback_visible: document.body.innerText.includes("Traceback (most recent call last)"),
  };
}
"""
    )
```

- [ ] **Step 5: Implement restoration and failure isolation**

Implement `_media_preference_assertions` with separate phase blocks and a
fail-closed restore helper:

```python
def _media_preference_assertions(
    page: Any,
    route: ResearchRoute,
) -> list[dict[str, object]]:
    assertions: list[dict[str, object]] = []

    def restore() -> None:
        try:
            page.emulate_media(
                forced_colors="none",
                reduced_motion="no-preference",
            )
        except Exception as exc:
            assertions.append(
                _assertion(
                    "media_preferences_restore",
                    False,
                    f"{type(exc).__name__}: {exc}",
                )
            )

    try:
        page.emulate_media(forced_colors="active", reduced_motion="no-preference")
        assertions.extend(
            evaluate_forced_colors_observation(
                _forced_colors_observation(page, route),
                primary_route=route.requires_primary_navigation,
            )
        )
    except Exception as exc:
        assertions.append(_assertion("forced_colors_execution", False, f"{type(exc).__name__}: {exc}"))
    finally:
        restore()

    try:
        page.emulate_media(forced_colors="none", reduced_motion="reduce")
        assertions.extend(
            evaluate_reduced_motion_observation(
                _reduced_motion_observation(page, route)
            )
        )
    except Exception as exc:
        assertions.append(_assertion("reduced_motion_execution", False, f"{type(exc).__name__}: {exc}"))
    finally:
        restore()
    return assertions
```

Add this restore-failure case so a reset failure cannot disappear into the
route-level exception:

```python
def test_media_preference_assertions_report_each_restore_failure(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        def __init__(self):
            self.calls = []

        def emulate_media(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs == {"forced_colors": "none", "reduced_motion": "no-preference"}:
                raise RuntimeError("restore failed")

    page = FakePage()
    monkeypatch.setattr(gate, "_forced_colors_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "_reduced_motion_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "evaluate_forced_colors_observation", lambda observation, *, primary_route: [{"name": "forced", "passed": True, "detail": "ok"}])
    monkeypatch.setattr(gate, "evaluate_reduced_motion_observation", lambda observation: [{"name": "motion", "passed": True, "detail": "ok"}])

    assertions = gate._media_preference_assertions(page, gate.RESEARCH_ROUTES[0])

    restores = [item for item in assertions if item["name"] == "media_preferences_restore"]
    assert len(restores) == 2
    assert all(item["passed"] is False for item in restores)
    assert all("RuntimeError: restore failed" in item["detail"] for item in restores)
```

- [ ] **Step 6: Insert the media checks into `_measure_route`**

Immediately after the route-specific initial assertions and before `_same_document_streamlit_rerun_assertions`, add:

```python
        assertions.extend(_media_preference_assertions(page, route))
```

Update `test_route_result_includes_fail_closed_bridge_transport_fields` to monkeypatch `_media_preference_assertions` to `[]`; do not add `emulate_media` to the unrelated fake page.

- [ ] **Step 7: Run focused gate and workflow tests**

```bash
python3 -m pytest \
  tests/test_research_accessibility_browser_gate.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_render_smoke.py \
  -q
```

Expected: PASS.

- [ ] **Step 8: Commit the complete implementation candidate**

```bash
git add -- src/research_accessibility_browser_gate.py tests/test_research_accessibility_browser_gate.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Verify accessibility media preferences"
```

- [ ] **Step 9: Run the clean-tree direct browser gate**

```bash
make research-accessibility-browser-check TIMEOUT_SECONDS=90
```

Expected: `verdict=passed`; all 12 route/viewport results contain passing forced-colors and reduced-motion assertions; the state harness remains green; the repository fingerprint is unchanged; only the existing 18 generated paths are excluded.

Record the implementation anchor:

```bash
git rev-parse HEAD
```

Do not create a JSON, timing, screenshot, or report artifact from this run.

---

### Task 4: Durable Evidence, Full Verification, and Draft-PR Synchronization

**Files:**
- Modify: `docs/ACCESSIBILITY_EVIDENCE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: the exact Task 3 implementation SHA and direct browser output.
- Produces: durable, bounded engineering evidence and truthful next-stage routing.
- Preserves: `accessibility_manual_review_environment_required` and every other external dependency classification.

- [ ] **Step 1: Record direct evidence without upgrading manual tasks**

Append a dated section to `docs/ACCESSIBILITY_EVIDENCE.md` containing:

- the exact implementation SHA;
- `make research-accessibility-browser-check TIMEOUT_SECONDS=90`;
- all six routes and both viewports;
- passing automated forced-colors and reduced-motion emulation;
- unchanged landmark, focus, navigation, authoring, dynamic-state, runtime, overflow, and repository-write checks; and
- the explicit statement that C01, C02, M01, zoom, screen-reader, assistive-technology, independent-human, hosted, and WCAG evidence remain incomplete.

- [ ] **Step 2: Update roadmap and continuation routing**

In Priority 7 of `ROADMAP.md`, add the implementation anchor and automated media-preference result. Keep Priority 7 incomplete and keep its external unblock condition unchanged except to clarify that automated emulation now exists but direct platform/human evidence does not.

In `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, mark the local media-preference engineering slice complete and route the next local scan to the previously reproduced Discover primary-copy containment gap. Do not mark independent accessibility, hosted controls, source evidence, reviewers, or calibration complete.

- [ ] **Step 3: Run documentation and full local verification before staging**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make commercial-beta-release-check
make diff-hygiene-summary
git diff --check
```

Expected: all commands pass; diff hygiene reports only the intentional product/docs/test files plus the same 18 unstaged generated artifacts.

- [ ] **Step 4: Stage only durable documentation and commit**

```bash
git add -- \
  docs/ACCESSIBILITY_EVIDENCE.md \
  ROADMAP.md \
  docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Document accessibility media evidence"
```

- [ ] **Step 5: Verify the exact final HEAD**

Run the full required gate set again at the final documentation commit:

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make research-accessibility-browser-check TIMEOUT_SECONDS=90
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make commercial-beta-release-check
make diff-hygiene-summary
git diff --check
```

Expected: all pass; the browser gate reports all 12 route/viewport media contracts and the state harness green; generated churn remains exactly excluded and unstaged.

- [ ] **Step 6: Push only the approved branch**

```bash
git status --short --branch
git rev-list --left-right --count HEAD...origin/codex/personal-research-mode-mvp
git push origin codex/personal-research-mode-mvp
```

Expected: push succeeds and local/upstream divergence becomes `0 0`.

- [ ] **Step 7: Update draft PR #113 without changing its draft state**

Post a concise PR comment containing the final HEAD, implementation anchor, direct browser result, focused/full test totals, release-gate results, 18 excluded generated paths, and the manual accessibility boundary. Confirm:

```bash
gh pr view 113 --json state,isDraft,mergeable,headRefOid,url
```

Expected: `state=OPEN`, `isDraft=true`, and `headRefOid` equals local `HEAD`.

- [ ] **Step 8: Require exact-head GitHub CI**

Identify the Commercial Research Beta run whose `headSha` equals local `HEAD`, then watch it:

```bash
EXACT_HEAD_SHA="$(git rev-parse HEAD)"
EXACT_CI_RUN_ID="$(gh run list --branch codex/personal-research-mode-mvp --workflow "Commercial Research Beta" --limit 10 --json databaseId,headSha --jq ".[] | select(.headSha == \"$EXACT_HEAD_SHA\") | .databaseId" | head -1)"
test -n "$EXACT_CI_RUN_ID"
gh run watch "$EXACT_CI_RUN_ID" --exit-status
```

Expected: the exact-head run concludes `success`. Do not use an older green run as evidence.

- [ ] **Step 9: Final hygiene and next-lane scan**

```bash
git status --short --branch
git rev-list --left-right --count HEAD...origin/codex/personal-research-mode-mvp
make diff-hygiene-summary
git diff --check
```

Expected: product/code/docs/tests clean, divergence `0 0`, and exactly the known generated paths remain unstaged. Rescan the ordered roadmap and begin the first safe executable item; do not retry unchanged external dependencies.
