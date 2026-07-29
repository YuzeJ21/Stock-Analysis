# Semantic Main Transport Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the deprecated Streamlit component transport while preserving same-document semantic-main ownership and authoring field-error binding.

**Architecture:** Both fixed accessibility scripts move from `st.components.v1.html` to `st.html(..., unsafe_allow_javascript=True)`. The scripts and their ownership rules remain unchanged; dependency tests enforce `streamlit>=1.52,<2`, and direct browser gates prove landmark, validation, route, rerun, and layout behavior.

**Tech Stack:** Python 3.12, Streamlit `st.html`, fixed JavaScript, pytest, Streamlit AppTest, Playwright/Chrome browser gate.

## Global Constraints

- Supported Streamlit range is exactly `streamlit>=1.52,<2`.
- No product path calls `st.components.v1.html` or substitutes `st.iframe`.
- Only fixed local script constants may be rendered with `unsafe_allow_javascript=True`.
- Never interpolate user, URL, source, research, or form-value content into executable HTML.
- Preserve exactly one actual main landmark, answer containment, skip behavior, route/query retention, rerun recovery, and bridge ownership cleanup.
- Preserve exact authoring required-field association, cleanup, and focus behavior.
- Unsupported runtime APIs fail closed; no deprecated fallback.
- The script-only HTML creates no visible box, focus target, blank gap, or horizontal overflow.
- No readiness, research result, persistence, ledger, generated-data, or routing change.
- Automated browser evidence is not screen-reader, WCAG, hosted, or cross-major-version proof.

---

### Task 1: Dependency Compatibility Boundary

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `tests/test_hosted_demo_readiness.py`

**Interfaces:**
- Produces one exact dependency literal: `streamlit>=1.52,<2`.

- [ ] **Step 1: Write failing dependency-consistency tests**

```python
def test_streamlit_range_supports_same_document_javascript_transport():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "streamlit>=1.52,<2" in requirements
    assert '"streamlit>=1.52,<2"' in pyproject
    assert "streamlit>=1.44" not in requirements + pyproject
```

Update hosted-readiness fixtures to expect the same literal, then run:

`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_public_v1_release_docs.py tests/test_hosted_demo_readiness.py -q`

Expected: FAIL on the current `>=1.44` range.

- [ ] **Step 2: Change both dependency declarations and fixtures**

Edit only the Streamlit requirement. Do not update unrelated packages or lock files.

- [ ] **Step 3: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_public_v1_release_docs.py tests/test_hosted_demo_readiness.py -q
git diff --check
git add -- requirements.txt pyproject.toml tests/test_public_v1_release_docs.py tests/test_hosted_demo_readiness.py
make staged-hygiene-check
git commit -m "Require Streamlit same-document HTML support"
```

### Task 2: Migrate Both Fixed Accessibility Renderers

**Files:**
- Modify: `src/accessibility_bridge.py`
- Modify: `src/research_record_authoring_ui.py`
- Modify: `tests/test_accessibility_bridge.py`
- Modify: `tests/test_research_record_authoring_ui.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Produces: `render_semantic_main_bridge(*, html_renderer: Callable[..., Any] | None = None) -> None`.
- Produces: `render_authoring_error_binding(error: AuthoringFieldError | None, *, html_renderer: Callable[..., Any] | None = None) -> None`.
- Default renderer: `streamlit.html`.
- Exact call: `renderer(fixed_document, unsafe_allow_javascript=True)`.

- [ ] **Step 1: Write failing renderer-contract tests**

```python
def test_semantic_bridge_uses_same_document_html_renderer():
    calls = []
    render_semantic_main_bridge(
        html_renderer=lambda *args, **kwargs: calls.append((args, kwargs))
    )
    assert calls == [
        ((SEMANTIC_MAIN_BRIDGE_HTML,), {"unsafe_allow_javascript": True})
    ]


def test_authoring_binding_uses_same_document_html_renderer():
    calls = []
    render_authoring_error_binding(
        _field_error(),
        html_renderer=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    assert len(calls) == 1
    assert calls[0][1] == {"unsafe_allow_javascript": True}
```

Run:

`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_accessibility_bridge.py tests/test_research_record_authoring_ui.py -q`

Expected: FAIL because current calls use `height=0`, `scrolling=False`, and the deprecated component.

- [ ] **Step 2: Implement renderer resolution with an explicit compatibility error**

```python
def _same_document_html_renderer(
    renderer: Callable[..., Any] | None,
) -> Callable[..., Any]:
    resolved = renderer if renderer is not None else getattr(streamlit, "html", None)
    if not callable(resolved):
        raise RuntimeError(
            "Streamlit >=1.52,<2 with st.html JavaScript support is required."
        )
    return resolved
```

Call the resolved renderer with only the fixed document and `unsafe_allow_javascript=True`. Remove `streamlit.components.v1` imports. Update authoring call sites to pass the error first and use renderer injection only in tests. Keep every JavaScript byte unchanged except transport-neutral comments if tests require them.

- [ ] **Step 3: Update AppTest inspection to `html` elements**

Replace iframe `srcdoc` lookups with the actual Streamlit AppTest element type exposed by the installed 1.59.2 runtime. Characterize it first in a focused test and assert the exact fixed document or authoring payload; do not mock away Streamlit rendering.

- [ ] **Step 4: Preserve authoring error binding behavior**

Run required-field tests proving Thesis Id and Effective At association, stale-error cleanup, exact focus, one global alert, and no ledger write. The renderer migration must not change the error contract or allow arbitrary validation reasons to bind a field.

- [ ] **Step 5: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_accessibility_bridge.py tests/test_research_record_authoring_ui.py tests/test_dashboard_render_smoke.py -q
git diff --check
git add -- src/accessibility_bridge.py src/research_record_authoring_ui.py tests/test_accessibility_bridge.py tests/test_research_record_authoring_ui.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git commit -m "Migrate accessibility bridges to st html"
```

### Task 3: Direct Runtime Regression and Warning Removal

**Files:**
- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`
- Modify: `docs/ACCESSIBILITY_EVIDENCE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-07-28-semantic-main-transport-migration-design.md`

**Interfaces:**
- Extends the existing six-route/two-viewport gate with bridge layout and deprecation-warning assertions.

- [ ] **Step 1: Add failing browser-result assertions**

Add result fields for:

```python
{
    "deprecated_component_warning_count": 0,
    "bridge_iframe_count": 0,
    "bridge_focusable_count": 0,
    "bridge_height": 0,
}
```

The gate must fail when stderr/console contains `st.components.v1.html`, when an accessibility bridge iframe exists, or when the script-only HTML has positive visible height or a focusable descendant.

- [ ] **Step 2: Run the focused gate tests and confirm the old transport fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_accessibility_browser_gate.py -q
make research-dashboard-render-smoke
```

Expected before migration: the render smoke reproduces the deprecation warning.

- [ ] **Step 3: Run direct desktop and phone evidence after migration**

Run:

`make research-accessibility-browser-check`

Require all six Research routes at `1280x720` and `390x844` to retain exactly one main, one contained answer, route H1, skip focus, exact query, same-document rerun recovery, mutation recovery, zero overflow, zero browser error, zero deprecated warning, zero bridge iframe, and zero visible bridge footprint.

- [ ] **Step 4: Update evidence and roadmap with exact tested boundaries**

Record the exact commit, installed Streamlit version, dependency range, routes, viewports, authoring validation regression, and warning count. Keep manual assistive-technology and hosted evidence open.

- [ ] **Step 5: Run full release gates**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make research-accessibility-browser-check
make diff-hygiene-summary
git diff --check
```

- [ ] **Step 6: Stage exact files, commit, push, update PR, and require exact-head CI**

```bash
git add -- src/research_accessibility_browser_gate.py tests/test_research_accessibility_browser_gate.py docs/ACCESSIBILITY_EVIDENCE.md ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/superpowers/specs/2026-07-28-semantic-main-transport-migration-design.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Verify same-document accessibility transport"
git push origin codex/personal-research-mode-mvp
gh pr checks 113 --watch
```

Expected: PR #113 remains draft, exact-head CI passes, and the 18 existing generated differences remain unstaged.
