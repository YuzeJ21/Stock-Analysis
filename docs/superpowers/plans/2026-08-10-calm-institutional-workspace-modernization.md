# Calm Institutional Workspace Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Calm Institutional Workspace across Public, Personal Research, evidence, Operator, and legacy routes without changing analytics, readiness, provenance, authoring persistence, or protected artifacts.

**Architecture:** Keep Streamlit route composition and all stateful controls in `src/dashboard.py`, centralize presentation-only CSS and escaped HTML helpers in `src/dashboard_visual_system.py`, and enforce mode boundaries in pure navigation functions before rendering. Build one generalized browser acceptance gate for the full route and viewport matrix, then migrate routes in reviewable slices while keeping evidence ordering and all data behavior authoritative.

**Tech Stack:** Python 3.12, Streamlit, pandas, standard-library HTML/dataclasses/URL parsing, pytest, existing Chromium browser gates, Make.

## Global Constraints

- Work only in `/Users/yjian070/Documents/New project/.worktrees/personal-research-mode-mvp` on `codex/personal-research-mode-mvp`; this is already a linked worktree.
- Keep PR #113 open and draft. Do not push, merge, deploy, publish, or change release state.
- Preserve the exact current bytes of the 18 pre-existing modified generated paths. Never stage, restore, regenerate, normalize, or commit them.
- Use `/tmp/stock-research-modernization-baseline-1f5dfe7dd/` as the task-start preservation authority. After every task, verify `protected-working-hashes.sha256`, the complete file hashes, path list, directory list, link list, and link targets.
- The checked-in historical 18-path manifest remains unchanged and non-gating; its task-start result is 17 mismatches and one match.
- Never use `git add -A`. Stage only the exact source, test, Makefile, or documentation paths named by the current task.
- Begin every behavior change with a focused failing test and observe the expected RED before writing production code.
- Do not add a provider, external font, analytics request, frontend framework, build tool, JavaScript navigation shell, or runtime dependency.
- Do not change forecasts, valuations, eligibility, evidence states, source rights, calculations, canonical inputs, authoring receipts, append-only ledgers, or research conclusions.
- Keep research-only wording explicit. Do not add recommendations, rankings, trading instructions, or bullish/bearish semantic color.
- Public and Personal Research navigation/workspace radios are the only approved widget-key exception. Preserve every other native widget key, form boundary, session-state key, rerun, receipt, fingerprint, and confirmation contract.
- EvidenceTimeline consumes authoritative preordered proof/change payloads. It never determines latest proof or invents ordering.
- Treat `make pilot-readiness-check TOP_N=10` as a diagnostic whose current fail-closed blocked result may remain; local visual completion does not require a pilot-ready verdict.
- Keep browser screenshots, timing files, and review evidence under `/tmp/stock-research-modernization-*`; do not add generated evidence paths to the repository.

## File Map

- Modify `src/dashboard_navigation.py`: raw query recognition, per-mode allowlists, structured canonical route resolution, retained-key policy.
- Modify `src/dashboard.py`: canonicalize before render, mode-correct shell composition, route integration, Public/evidence/Operator presentation hooks.
- Modify `src/research_workspace.py`: Personal workflow navigation, tickerless Workbench state, shared evidence return links, route answer markup.
- Create `src/dashboard_visual_system.py`: tokens, contrast roles, semantic state mapping, escaped shared components, centralized CSS.
- Create `src/workspace_visual_browser_gate.py`: deterministic route/viewport geometry, overflow, control size, hierarchy, focus, and console checks.
- Modify `src/dashboard_render_smoke.py`, `src/research_accessibility_browser_gate.py`, `src/public_performance_gate.py`, and `Makefile`: migrate and extend executable route gates.
- Create `tests/test_dashboard_visual_system.py` and `tests/test_workspace_visual_browser_gate.py`.
- Modify focused navigation, dashboard, research workspace, render, accessibility, performance, wording, and launcher tests named by each task.
- Reconcile `README.md`, `ROADMAP.md`, `docs/PERSONAL_RESEARCH_MODE.md`, `docs/PUBLIC_DEMO_WALKTHROUGH.md`, accessibility/operator documentation, and the active continuation contract only after verified behavior exists.

---

## Pre-Implementation Contract Commit

Before Task 0, commit the independently audited design amendment and this
implementation plan. The audit verdicts must be `READY`, the task-start
artifact baseline must still report 18/18 protected and 150/150 complete hashes,
and only these two documentation paths may be staged:

```bash
git add -- docs/superpowers/specs/2026-08-10-calm-institutional-workspace-modernization-design.md docs/superpowers/plans/2026-08-10-calm-institutional-workspace-modernization.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Approve calm workspace modernization plan"
```

Every later instruction to “run the Task 0 artifact commands” means the full
six-part check in Task 0 Step 7: protected hashes, all hashes, file paths,
directory paths, link paths, and link targets. No abbreviated substitute is
acceptable.

---

### Task 0: Enforce Mode Isolation and Canonical Query State

**Files:**
- Modify: `src/dashboard_navigation.py:1-280`
- Modify: `src/dashboard.py:29384-29405, 32980-33035, 36321-36425, 36560-36590`
- Modify: `src/research_workspace.py:1106-1135, 1203-1225`
- Test: `tests/test_dashboard_navigation.py`
- Test: `tests/test_research_mode_dashboard_contract.py`
- Test: `tests/test_dashboard_helpers.py`
- Test: `tests/test_research_workspace.py`
- Test: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Produces: `WorkspaceRouteResolution` with `mode`, `requested_page`, `page`, `recognized`, `allowed`, `redirected`, and `canonical_query` fields.
- Produces: `resolve_workspace_route(raw_mode, raw_page, query_params, user_page_titles, operator_page_titles) -> WorkspaceRouteResolution`.
- Produces: `canonical_workspace_query(mode, page, query_params) -> dict[str, str]` using the exact spec allowlists.
- Produces: punctuation-safe `single_stock_query_ticker()` and `data_health_focus_ticker()` behavior bound to registered tickers.
- Preserves: Operator route behavior; allowed direct request state; Research evidence return-to-Workbench behavior.

- [ ] **Step 1: Write the raw-resolution and full route-matrix tests**

Add literal table cases that name the break: any Public or Personal request can render a page outside its allowed set, or an unknown route can be mistaken for recognized Home.

```python
@pytest.mark.parametrize(
    ("mode", "page", "expected_page", "recognized", "redirected"),
    (
        ("public", "overview", "Home", True, True),
        ("public", "research-desk", "Home", True, True),
        ("research", "home", "Research Desk", True, True),
        ("research", "single-stock-report", "Research Desk", True, True),
        ("research", "universe-manager", "Research Desk", True, True),
        ("public", "not-a-route", "Home", False, True),
        ("research", "not-a-route", "Research Desk", False, True),
        ("operator", "overview", "Overview", True, False),
    ),
)
def test_workspace_route_resolution_fails_closed_by_mode(
    mode, page, expected_page, recognized, redirected
):
    result = nav.resolve_workspace_route(
        mode,
        page,
        {"mode": mode, "page": page},
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )
    assert result.page == expected_page
    assert result.recognized is recognized
    assert result.redirected is redirected
```

- [ ] **Step 2: Write exact canonical-query tests**

Use hand-written expected dictionaries for every allowed key set. Prove disallowed redirects drop all route-specific keys, Public Home omits `page=home`, shared evidence mode switches preserve their permitted state, and allowed direct requests do not trigger rewriting.

```python
def test_public_advanced_redirect_clears_route_specific_state():
    result = nav.resolve_workspace_route(
        "public",
        "overview",
        {"mode": "public", "page": "overview", "ticker": "AVGO", "open": "1"},
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )
    assert result.canonical_query == {"mode": "public"}


def test_research_data_health_canonical_query_keeps_only_evidence_keys():
    assert nav.canonical_workspace_query(
        "research",
        "Data Health",
        {
            "ticker": "BRK/B",
            "lane": "peers",
            "drawer": "proof",
            "proof_details": "1",
            "cash_preview": "1",
        },
    ) == {
        "mode": "research",
        "page": "data-health",
        "ticker": "BRK/B",
        "lane": "peers",
        "drawer": "proof",
        "proof_details": "1",
    }
```

- [ ] **Step 3: Write ticker and evidence-return regressions**

Assert `BRK/B` survives generated link → parsed query for both Single-Stock Report and Data Health. Render Research Data Health and Proof History and assert there is one Research return path and no `mode=public` report return link.

- [ ] **Step 4: Run the focused tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_navigation.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_helpers.py \
  tests/test_research_workspace.py \
  tests/test_dashboard_render_smoke.py -q -p no:cacheprovider
```

Expected: new cases fail because advanced/cross-mode pages survive, unknown pages lose recognition, queries are cleared generically, `BRK/B` is stripped, and Research Data Health adds a Public return link.

- [ ] **Step 5: Implement pure resolution before Streamlit rendering**

Add immutable mode/page sets and the structured resolver in `dashboard_navigation.py`. In `main()`, call it before bootstrap, sidebar construction, output selection, or render dispatch. Only when `redirected` is true, replace query state with `canonical_query`; otherwise leave the allowed direct query mapping untouched. Use the resolved page for all later selection and rendering.

- [ ] **Step 6: Repair punctuation and evidence-return consumption**

Make both ticker consumers preserve characters that exist in the provider's registered symbol set, including `/`. Split Data Health's public evidence-return affordance from its command-hiding flag so Research renders only the Research return link.

- [ ] **Step 7: Run GREEN and the artifact gate**

Run the Step 4 command, then:

```bash
shasum -a 256 -c /tmp/stock-research-modernization-baseline-1f5dfe7dd/protected-working-hashes.sha256
shasum -a 256 -c /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-hashes.sha256
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-paths.txt -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-dirs.txt -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-link-paths.txt -
while IFS= read -r artifact_link; do printf '%s -> %s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-link-paths.txt | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-link-targets.txt -
```

- [ ] **Step 8: Commit only Task 0**

```bash
git add -- src/dashboard_navigation.py src/dashboard.py src/research_workspace.py tests/test_dashboard_navigation.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_helpers.py tests/test_research_workspace.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Fix workspace route isolation"
```

---

### Task 1: Create a Byte-Identical Presentation Seam

**Files:**
- Create: `src/dashboard_visual_system.py`
- Create: `tests/test_dashboard_visual_system.py`
- Create: `tests/fixtures/dashboard_visual_system/research_accessibility_media_preferences.css`
- Create: `tests/fixtures/dashboard_visual_system/presentation_dom_snapshots.json`
- Modify: `src/research_workspace.py:1138-1200`
- Modify: `src/dashboard.py:2076-2500, 6658-7300, 35510-36025`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

**Interfaces:**
- Produces: `legacy_research_accessibility_css() -> str` with byte-identical output to the frozen pre-extraction fixture.
- Produces: `render_stylesheet(css: str) -> str` and escaped attribute/text primitives for later shared components.
- Preserves: all rendered CSS bytes and DOM output in this task; `apply_dashboard_theme()` and route renderers remain integration points.

- [ ] **Step 1: Characterize exact current presentation output**

Before moving code, use the current public helpers and deterministic fixtures to
write the two test fixtures named above. Inspect them, record their literal
SHA-256 digests in `tests/test_dashboard_visual_system.py`, and commit the
fixtures in this task. The CSS fixture contains the complete current media
preference string; the JSON fixture maps stable fixture names to exact current
HTML strings. After extraction, compare the new-module output to the fixture
bytes and their fixed digests—never to the delegating old wrapper.

```python
def test_presentation_seam_keeps_accessibility_css_byte_identical():
    expected = FIXTURE_CSS.read_text(encoding="utf-8")
    assert hashlib.sha256(expected.encode()).hexdigest() == FROZEN_CSS_SHA256
    assert visual.legacy_research_accessibility_css() == expected
    assert "@media (forced-colors: active)" in expected
    assert "@media (prefers-reduced-motion: reduce)" in expected
```

Freeze the DOM fixture before changing any helper, then add behavior assertions
for escaped text and quoted attributes. Do not assert that a selector remains
physically inside `src/dashboard.py`.

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_visual_system.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py -q -p no:cacheprovider
```

Expected: import failure because `src.dashboard_visual_system` does not exist.

- [ ] **Step 3: Extract the smallest pure seam**

Move the existing media-preference CSS and directly shared pure formatting helpers into the new module without editing their bytes. Re-export or delegate from the existing public function names so callers remain compatible. Keep Streamlit imports and calls out of the module.

- [ ] **Step 4: Migrate brittle source-string tests**

Replace tests that search `Path("src/dashboard.py").read_text()` for CSS selectors with assertions on exported CSS or rendered helper output. Do not duplicate CSS in both modules to satisfy old tests.

- [ ] **Step 5: Prove byte and DOM equivalence**

Run the Step 2 suite and existing render-smoke characterization:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_render_smoke.py tests/test_research_accessibility_browser_gate.py -q -p no:cacheprovider
```

- [ ] **Step 6: Verify artifacts and commit only Task 1**

Run the Task 0 artifact commands, then:

```bash
git add -- src/dashboard_visual_system.py src/research_workspace.py src/dashboard.py tests/fixtures/dashboard_visual_system/research_accessibility_media_preferences.css tests/fixtures/dashboard_visual_system/presentation_dom_snapshots.json tests/test_dashboard_visual_system.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Extract dashboard presentation seam"
```

---

### Task 2: Build the Visual Foundation, Navigation, Browser Gate, and Research Desk

**Files:**
- Modify: `src/dashboard_visual_system.py`
- Create: `src/workspace_visual_browser_gate.py`
- Create: `tests/test_workspace_visual_browser_gate.py`
- Modify: `src/dashboard.py:2076-2500, 5380-5435, 6658-7300, 7490-7510, 30950-31040, 35510-36120, 36321-36535`
- Modify: `src/research_workspace.py:1106-1225`
- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `src/dashboard_render_smoke.py`
- Modify: `scripts/public_wording_check.py`
- Modify: `tests/test_dashboard_visual_system.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_research_workspace.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_public_wording_check.py`
- Modify: `Makefile`

**Interfaces:**
- Produces these immutable typed records:

```python
@dataclass(frozen=True)
class HtmlFragment:
    value: str

@dataclass(frozen=True)
class SafeRouteAction:
    label: str
    href: str
    aria_label: str | None = None

@dataclass(frozen=True)
class EvidenceRow:
    lane: str
    role: str
    state: str
    count_or_cutoff: str
    reason: str
    evidence_action: SafeRouteAction | None = None

@dataclass(frozen=True)
class VisualState:
    role: str
    state: str
    semantic: str
    label: str
    foreground: str
    background: str
    border: str
```

- Produces: `visual_state(role: str, state: str, label: str | None = None) -> VisualState`; unknown, empty, analytic, or legacy inputs fail closed to the neutral semantic namespace.
- Produces: `dashboard_visual_system_css() -> str` with all approved `--sr-*` tokens.
- Produces these exact pure helpers, all returning `HtmlFragment`:

```python
workspace_shell_html(*, mode: str, navigation: HtmlFragment | None, content: Sequence[HtmlFragment])
context_bar_html(items: Sequence[tuple[str, str]])
answer_panel_html(*, question: str, answer: str, reason: str, action: SafeRouteAction | None, stop_rule: str | None)
status_chip_html(*, role: str, state: str, label: str | None = None)
evidence_rows_html(rows: Sequence[EvidenceRow])
next_action_html(action: SafeRouteAction)
empty_state_html(*, title: str, absence: str, not_proven: str, action: SafeRouteAction | None)
```

  Every string is escaped at the text or attribute boundary. Helpers may nest
  only `HtmlFragment` values created by this module; callers cannot pass raw
  trusted HTML. `SafeRouteAction` accepts only same-app query-only URLs whose
  parsed keys are in the canonical route-key union from Task 0, with no scheme,
  host, path, fragment, duplicate controlled key, or state-changing command.
  Unsafe or empty action URLs raise `ValueError` before rendering. Malformed
  evidence state renders neutral and visible rather than disappearing.
- Produces: one mode-appropriate skip link, one Public nav, and one Personal nav; only Operator renders native sidebar route controls.
- Produces: `workspace-visual-browser-check` Make target covering the deterministic matrix.

- [ ] **Step 1: Write token, contrast, semantic-role, and escaping tests**

Use literal token values from the specification. Implement a test-only WCAG ratio helper and assert every permitted foreground/background pair meets `4.5:1` for normal text; assert focus/non-text pairs meet `3:1`. Prove analytic/legacy/unknown labels remain neutral.

```python
def test_nav_tokens_are_aa_readable_on_midnight():
    tokens = visual.visual_tokens()
    assert contrast(tokens["--sr-nav-text"], tokens["--sr-nav"]) >= 4.5
    assert contrast(tokens["--sr-nav-muted"], tokens["--sr-nav"]) >= 4.5


@pytest.mark.parametrize("label", ("Keep", "Strong Rotation", "Risk Reduce", "peer_discount"))
def test_analytic_labels_never_inherit_evidence_sentiment(label):
    state = visual.visual_state("analytic", label)
    assert state.semantic == "neutral"
```

- [ ] **Step 2: Write navigation, skip-link, and semantic-region tests**

Assert evidence routes render one Personal workflow nav with no core `aria-current`; tickerless Workbench is visible but disabled; ticker-bound Workbench preserves the symbol; Public/Personal place the sole skip link first outside the sidebar; Operator places its sole skip link first inside the sidebar focus bucket; and every shared region hook is unique.

Add typed-component boundary tests: all supplied text and attributes are escaped;
only module-created `HtmlFragment` instances may be nested; unknown evidence and
legacy states render visible neutral chips; query-only canonical actions render;
and `https:`, protocol-relative, path, fragment, duplicate controlled-key, and
state-changing command links each raise `ValueError`.

Extend `scripts/public_wording_check.py` and its focused test so the new
`src/dashboard_visual_system.py` is scanned alongside `src/dashboard.py`; no
presentation helper becomes an unchecked path for recommendation or overclaim
copy.

- [ ] **Step 3: Write the generalized browser-gate contract tests**

Define literal route fixtures for Research Desk, Discover, AVGO Workbench, Monitor, Public Home, Stock Selector, AVGO Report, Public Data Health, Public Proof History, Personal Data Health, Personal Proof History, Operator Overview, Market Direction, Universe Manager, and Monthly Picks at `1280x720`, `1440x1024`, and `390x844`. Test the gate's pure evaluators for:

```python
assert evaluate_horizontal_bounds(left=-1, right=390, client_width=390).passed
assert evaluate_scroll_width(scroll_width=391, client_width=390).passed
assert not evaluate_control_target(width=43, height=44).passed
assert not evaluate_text_clipping(overflow="hidden", text_overflow="ellipsis", line_clamp="1").passed
```

- [ ] **Step 4: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_visual_system.py \
  tests/test_workspace_visual_browser_gate.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_research_accessibility_browser_gate.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_public_wording_check.py -q -p no:cacheprovider
```

Expected: missing tokens/components/gate, evidence nav count mismatch, duplicate or sidebar-bound focus behavior, and current 24-pixel phone actions.

- [ ] **Step 5: Implement presentation-only primitives and tokens**

Add the approved token set, role-aware mapping, contrast-safe CSS, and escaped helpers in `dashboard_visual_system.py`. Unknown roles and analytic/legacy labels return neutral styles. Add no data loading or Streamlit import.

- [ ] **Step 6: Implement the single navigation authority**

For Public and Personal Research, render the sole skip link before main shell output and render no sidebar controls. For Operator, keep the sole skip link as the first sidebar child before native controls. Render URL-only workspace mode links in the approved Public/Personal shell locations. Keep the Operator sidebar and native widget key. Use the same Personal nav DOM on core and evidence routes; keep Workbench disabled until a ticker is selected.

- [ ] **Step 7: Modernize Research Desk with shared regions**

Render context, H1/purpose, primary answer, next action, stop rule, supporting evidence, and advanced detail in the approved order. Preserve the existing brief payload and research-only text; add no new counts or actions.

- [ ] **Step 8: Implement the browser gate and Make target**

Reuse the existing browser-process and route-wait patterns. The exact CLI is:

```bash
python3 -m src.workspace_visual_browser_gate \
  --routes research-desk,discover,company-workbench,monitor,public-home,stock-selector,single-stock-report,public-data-health,public-proof-history,personal-data-health,personal-proof-history,operator-overview,market-direction,universe-manager,monthly-picks \
  --viewports 1280x720,1440x1024,390x844 \
  --zooms 1,2 \
  --output-dir /tmp/stock-research-modernization-example
```

`--routes`, `--viewports`, `--zooms`, and `--output-dir` are required, comma-
delimited, reject unknown or duplicate values, and preserve declared order.
`--output-dir` must resolve under `/tmp`, must not already contain files, and is
created if absent. The Make target forwards `ROUTES`, `VIEWPORTS`, `ZOOMS`, and
`OUTPUT_DIR` verbatim and fails when any is absent. Each matrix cell starts a
fresh Streamlit child plus isolated browser context, waits for the stable route
marker, and always terminates the child. The gate writes screenshots,
`results.json`, and `browser.log` only inside `OUTPUT_DIR`.

Add pure evaluators plus the CLI checks for region bounds, document/body/main overflow, unclipped text, 44-pixel targets, initial-viewport hierarchy, skip/focus behavior, console/traceback state, forced colors, reduced motion, and 200% zoom.

- [ ] **Step 9: Run GREEN and executable route checks**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_visual_system.py \
  tests/test_workspace_visual_browser_gate.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_research_accessibility_browser_gate.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_public_wording_check.py -q -p no:cacheprovider
make research-dashboard-render-smoke
make research-accessibility-browser-check
task2_visual_output=$(mktemp -d /tmp/stock-research-modernization-task-2.XXXXXX)
make workspace-visual-browser-check ROUTES=research-desk VIEWPORTS=1280x720,1440x1024,390x844 ZOOMS=1,2 OUTPUT_DIR="$task2_visual_output"
```

- [ ] **Step 10: Verify artifacts and commit only Task 2**

Open `/tmp/stock-research-modernization-audit/01-research-desk-before-1280x720.png`
and the matching new Research Desk capture together in one visual comparison
input. Compare hierarchy, tokens, spacing, complete text, and navigation
containment under the written Option 1 contract, not pixel parity. Run the Task
0 artifact commands, then:

```bash
git add -- src/dashboard_visual_system.py src/workspace_visual_browser_gate.py src/dashboard.py src/research_workspace.py src/research_accessibility_browser_gate.py src/dashboard_render_smoke.py scripts/public_wording_check.py tests/test_dashboard_visual_system.py tests/test_workspace_visual_browser_gate.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_research_accessibility_browser_gate.py tests/test_dashboard_render_smoke.py tests/test_public_wording_check.py Makefile
make staged-hygiene-check
git diff --cached --check
git commit -m "Build calm workspace visual foundation"
```

---

### Task 3: Modernize Discover, Company Workbench, and Monitor

**Files:**
- Modify: `src/dashboard.py`
- Modify: `src/dashboard_visual_system.py`
- Modify: `src/research_workspace.py`
- Modify: `src/workspace_visual_browser_gate.py`
- Modify: `tests/test_dashboard_visual_system.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_research_workspace.py`
- Modify: `tests/test_workspace_visual_browser_gate.py`

**Interfaces:**
- Produces immutable `TimelineRecord(record_id: str, timestamp: str | None, label: str, summary: str, evidence_action: SafeRouteAction | None = None)`.
- Produces: `evidence_timeline_html(records: Sequence[TimelineRecord], *, empty_title: str, empty_body: str) -> HtmlFragment` that preserves authoritative input order and marks an absent timestamp as `Timestamp unavailable`.
- Produces: `detail_disclosure_html(summary: str, body: Sequence[HtmlFragment], *, open_by_default: bool = False) -> HtmlFragment` for progressive disclosure without accepting raw trusted HTML or moving native Streamlit widgets into HTML.
- Keeps: Discover strict-screen and saved-browser semantics, Workbench preview/receipt/confirmation state, and Monitor's single truthful zero state.

- [ ] **Step 1: Write failing route hierarchy tests**

Add focused assertions that each page emits one context row, one H1, one primary answer, one next action, at most one stop rule, and supporting detail only after the stop rule. For Discover, assert the strict-screen answer precedes advanced recency and saved-browser detail. For Workbench, assert independent usable and withheld lanes remain distinct and all authoring widgets keep their current keys. For Monitor, assert one zero state rather than repeated empty cards.

- [ ] **Step 2: Write failing timeline and native-widget seam tests**

```python
def test_evidence_timeline_preserves_authoritative_order_and_undated_rows():
    rows = [
        TimelineRecord("p2", "2026-08-01", "Latest", "Supported"),
        TimelineRecord("p1", None, "Undated", "Still visible"),
    ]
    html = visual.evidence_timeline_html(rows, empty_title="No proof", empty_body="No durable proof yet.")
    assert html.index("Latest") < html.index("Undated")
    assert "Timestamp unavailable" in html
```

Add source/behavior tests proving `st.button`, `st.link_button`, `st.selectbox`, form boundaries, and the authoring receipt controls remain in `dashboard.py` adjacent to presentation helpers and keep their existing keys.

- [ ] **Step 3: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_visual_system.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_workspace_visual_browser_gate.py -q -p no:cacheprovider
```

Expected: missing timeline/disclosure helpers and hierarchy mismatches on the three routes.

- [ ] **Step 4: Implement Discover answer-first hierarchy**

Use existing strict-screen and saved-browser payloads. Put the screening question and strict result first, then the next action and stop rule, then place advanced recency, exclusions, and saved-browser controls in supporting detail. Preserve every existing filter, query, and result-set rule.

- [ ] **Step 5: Implement Workbench lane clarity without changing state**

Render a compact company context row, a direct primary answer, independent usable/withheld lanes, and one next action. Keep every native Streamlit widget, key, form, session-state value, preview fingerprint, exact receipt, confirmation, and append-only write path unchanged. Pure helpers may frame widgets but may not contain them.

- [ ] **Step 6: Implement Monitor's truthful single zero state**

Consolidate repeated empty panels into one answer-first empty state using current payload truth. Keep monitoring research-only and do not imply alerts, recommendations, or provider coverage that does not exist.

- [ ] **Step 7: Run focused GREEN and browser routes**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_visual_system.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_workspace_visual_browser_gate.py -q -p no:cacheprovider
task3_visual_output=$(mktemp -d /tmp/stock-research-modernization-task-3.XXXXXX)
make workspace-visual-browser-check ROUTES=discover,company-workbench,monitor VIEWPORTS=1280x720,1440x1024,390x844 ZOOMS=1,2 OUTPUT_DIR="$task3_visual_output"
make commercial-beta-performance-gate WARM_RUNS=5 COLD_RUNS=1 TIMEOUT_SECONDS=30
```

- [ ] **Step 8: Compare reference/current screenshots, verify artifacts, and commit**

Capture the same deterministic route, viewport, and fixture states used during
audit. The named baseline references are
`/tmp/stock-research-modernization-audit/02-discover-before-1280x720.png`,
`/tmp/stock-research-modernization-audit/03-company-workbench-before-1280x720.png`,
and `/tmp/stock-research-modernization-audit/05-company-workbench-before-390x844.png`.
Open each baseline and matching implementation capture together in the same
visual comparison input. Judge hierarchy, spacing, typography, navigation
containment, and clipping against the approved written Option 1 token/layout
contract; never require invented concept content or pixel parity. The owner's
final qualitative approval remains an external handoff checkpoint, not a local
test claim. Run the Task 0 artifact commands, then:

```bash
git add -- src/dashboard.py src/dashboard_visual_system.py src/research_workspace.py src/workspace_visual_browser_gate.py tests/test_dashboard_visual_system.py tests/test_research_mode_dashboard_contract.py tests/test_research_workspace.py tests/test_workspace_visual_browser_gate.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Modernize personal research workflows"
```

---

### Task 4: Modernize Public and Evidence Routes

**Files:**
- Modify: `src/dashboard.py`
- Modify: `src/dashboard_visual_system.py`
- Modify: `src/workspace_visual_browser_gate.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_workspace_visual_browser_gate.py`

**Interfaces:**
- Produces: one semantic Public Home stop-rule node with DOM order action, stop rule, metrics and desktop CSS placement action, metrics, stop rule.
- Produces: answer-first Public Home, Stock Selector, and Single-Stock Report without changing public claims or route behavior.
- Produces: mode-correct Data Health and Proof History shells using authoritative preordered evidence rows.

- [ ] **Step 1: Write failing Public Home order and uniqueness tests**

Replace the old test that requires duplicate stop copy with one unique semantic hook. Assert the HTML source order and desktop grid-area contract separately:

```python
assert html.count('data-sr-region="stop-rule"') == 1
assert html.index('data-sr-region="primary-action"') < html.index('data-sr-region="stop-rule"')
assert html.index('data-sr-region="stop-rule"') < html.index('data-sr-region="supporting-evidence"')
assert "grid-area: metrics" in css
```

- [ ] **Step 2: Write failing Public and evidence-route hierarchy tests**

Assert Public Home, Selector, and Report preserve current research-only language, data values, links, and route keys while adopting shared regions. Assert Public and Personal Data Health/Proof History differ only in their mode shell/return actions, contain no false recommendation state, retain every undated row, and preserve authoritative proof ordering.

- [ ] **Step 3: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_visual_system.py \
  tests/test_workspace_visual_browser_gate.py -q -p no:cacheprovider
```

- [ ] **Step 4: Modernize Public routes with existing content**

Use the shared context, answer, action, stop, evidence, and detail primitives. Preserve all public claims, values, research boundaries, no-fabrication behavior, and native controls. Keep the single semantic Public Home stop rule and use CSS grid placement for the desktop visual exception; phone source and visual order remain action, stop, metrics.

- [ ] **Step 5: Modernize Data Health and Proof History by mode**

Render the research boundary before the first ledger row. Feed `EvidenceTimeline` the already-authoritative ordered payload without sorting or latest inference. Keep missing dates visible and labelled. Public evidence routes expose Public returns; Personal evidence routes expose Personal returns only and keep the same Personal nav with no core item selected.

- [ ] **Step 6: Run focused GREEN and browser matrix**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_visual_system.py \
  tests/test_workspace_visual_browser_gate.py -q -p no:cacheprovider
make demo-data-check
make dashboard-smoke
make public-wording-check
make public-performance-gate WARM_RUNS=5 COLD_RUNS=1 TIMEOUT_SECONDS=30
task4_visual_output=$(mktemp -d /tmp/stock-research-modernization-task-4.XXXXXX)
make workspace-visual-browser-check ROUTES=public-home,stock-selector,single-stock-report,public-data-health,public-proof-history,personal-data-health,personal-proof-history VIEWPORTS=1280x720,1440x1024,390x844 ZOOMS=1,2 OUTPUT_DIR="$task4_visual_output"
```

- [ ] **Step 7: Compare screenshots, verify artifacts, and commit**

Use `/tmp/stock-research-modernization-audit/04-public-home-before-390x844.png`
and `/tmp/stock-research-modernization-audit/06-data-health-before-1280x720.png`
as the named baseline references. Open each with its matching new capture in the
same comparison input and assess the approved hierarchy/tokens, complete copy,
spacing, and containment without pixel matching. Run the Task 0 artifact
commands, then:

```bash
git add -- src/dashboard.py src/dashboard_visual_system.py src/workspace_visual_browser_gate.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py tests/test_workspace_visual_browser_gate.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Modernize public and evidence workflows"
```

---

### Task 5: Modernize Operator and Legacy Shells Without Reframing Them

**Files:**
- Modify: `src/dashboard.py`
- Modify: `src/dashboard_visual_system.py`
- Modify: `src/workspace_visual_browser_gate.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_workspace_visual_browser_gate.py`

**Interfaces:**
- Keeps: Operator's native sidebar route/workspace controls and widget state.
- Produces: a compact Operator shell and neutral compatibility shell for legacy utilities.
- Keeps: Overview, Market Direction, Universe Manager, and legacy utility payloads/labels as operator or analytic data, never evidence sentiment.

- [ ] **Step 1: Write failing Operator/legacy isolation and semantics tests**

Assert advanced and legacy routes remain reachable only in Operator; Operator keeps its native route/workspace widget keys; its skip link is the first sidebar focus child; exactly one visible labelled route navigation exists; and analytic labels such as `Keep`, `Strong Rotation`, `Risk Reduce`, and `peer_discount` remain neutral rather than inheriting readiness colors.

- [ ] **Step 2: Write failing shell hierarchy tests**

Assert Overview, Market Direction, Universe Manager, and one explicit legacy utility show the operator or compatibility warning before detail, do not invent research stop rules, and keep current route titles, payloads, controls, and data tables.

- [ ] **Step 3: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_visual_system.py \
  tests/test_workspace_visual_browser_gate.py -q -p no:cacheprovider
```

- [ ] **Step 4: Apply the calm shell without changing operator behavior**

Use the shared canvas, type, spacing, surface, and neutral-state tokens around existing Operator and legacy content. Retain native sidebar controls, widget keys, route behavior, tables, analytic values, and all operator warnings. Use readiness semantic colors only when the source state belongs to the evidence/readiness namespace; unknown or legacy states fail closed to neutral.

- [ ] **Step 5: Run GREEN and Operator/legacy browser checks**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_visual_system.py \
  tests/test_workspace_visual_browser_gate.py -q -p no:cacheprovider
task5_visual_output=$(mktemp -d /tmp/stock-research-modernization-task-5.XXXXXX)
make workspace-visual-browser-check ROUTES=operator-overview,market-direction,universe-manager,monthly-picks VIEWPORTS=1280x720,1440x1024,390x844 ZOOMS=1,2 OUTPUT_DIR="$task5_visual_output"
make dashboard-render-smoke
```

- [ ] **Step 6: Compare screenshots, verify artifacts, and commit**

Use `/tmp/stock-research-modernization-audit/07-public-operator-leak-before-1280x720.png`
only as the named baseline for the existing Operator content density, not as a
valid mode shell. Open it and the corrected Operator Overview capture together;
verify the Operator content remains while the Public leak is absent and the
approved shell/tokens are applied. Run the Task 0 artifact commands, then:

```bash
git add -- src/dashboard.py src/dashboard_visual_system.py src/workspace_visual_browser_gate.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py tests/test_workspace_visual_browser_gate.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Unify operator and compatibility shells"
```

---

### Task 6: Close Cross-Route Quality, Documentation, and Release Diagnostics

**Files:**
- Modify: `src/workspace_visual_browser_gate.py`
- Modify: `tests/test_workspace_visual_browser_gate.py`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/PUBLIC_DEMO_WALKTHROUGH.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/ACCESSIBILITY_EVIDENCE.md`
- Modify: `docs/OPERATOR_GUIDE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `tests/test_launchers.py`
- Modify: `Makefile` only if final matrix orchestration needs correction

**Interfaces:**
- Produces: one full deterministic browser matrix with screenshots and machine-readable results written only under `/tmp`.
- Produces: documentation that consistently names Personal Research as the default workspace and separates Public, Personal Research, Operator, and compatibility routes.
- Keeps: `pilot-readiness-check` as a diagnostic whose expected external/manual blockers do not become a local design failure.

- [ ] **Step 1: Write failing full-matrix and documentation tests**

Add tests that require the complete spec route/viewport matrix, unique critical-region selectors, initial-viewport answer/action/stop geometry on primary routes, no document overflow, no clipped critical text, minimum 44-pixel controls, same-document skip behavior, forced-colors/reduced-motion checks, and no console error/traceback/loading capture. Update documentation tests to require Personal Research as the default and remove the contradictory Public-default statement.

- [ ] **Step 2: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_workspace_visual_browser_gate.py tests/test_public_v1_release_docs.py tests/test_launchers.py tests/test_research_mode_dashboard_contract.py -q -p no:cacheprovider
```

- [ ] **Step 3: Finish deterministic gate coverage and documentation**

Complete the route matrix using real demo fixtures and current route content.
Write screenshots, geometry JSON, and browser logs only to a fresh
`/tmp/stock-research-modernization-*` directory. Reconcile each exact document
listed in this task: README/default entry point; ROADMAP/current stage and next
slice; Personal Research workflow; Public walkthrough; dashboard QA matrix;
accessibility evidence and limits; Operator/legacy isolation; and the active
continuation contract. Retain research-only, snapshot, source-rights, and
external-gate boundaries.

- [ ] **Step 4: Run the complete browser and static quality suite**

```bash
task6_visual_output=$(mktemp -d /tmp/stock-research-modernization-task-6.XXXXXX)
make workspace-visual-browser-check \
  ROUTES=research-desk,discover,company-workbench,monitor,public-home,stock-selector,single-stock-report,public-data-health,public-proof-history,personal-data-health,personal-proof-history,operator-overview,market-direction,universe-manager,monthly-picks \
  VIEWPORTS=1280x720,1440x1024,390x844 \
  ZOOMS=1,2 \
  OUTPUT_DIR="$task6_visual_output"
make research-accessibility-browser-check
make research-dashboard-render-smoke
make dashboard-smoke
make dashboard-render-smoke
make demo-data-check
make public-wording-check
make public-performance-gate WARM_RUNS=5 COLD_RUNS=1 TIMEOUT_SECONDS=30
make commercial-beta-performance-gate WARM_RUNS=5 COLD_RUNS=1 TIMEOUT_SECONDS=30
make browser-qa-evidence
make public-check
```

The `ZOOMS=1,2` full-matrix run is the explicit 100%/200% zoom acceptance
check; `results.json` must contain a passing cell for every declared
route × viewport × zoom combination.

Run the full Python suite with the repository's existing cache-safe pattern:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
```

Run release diagnostics without converting expected external/manual blockers into a design failure:

```bash
make readiness-ops-center
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
```

Record the readiness decision, freshness/evidence state, and each remaining owner/external gate exactly as reported. The command must execute and remain fail closed; local modernization completion does not require hosted accounts, commercial rights, reviewers, or calibration to become ready.

- [ ] **Step 5: Verify protected artifacts and source hygiene**

```bash
shasum -a 256 -c /tmp/stock-research-modernization-baseline-1f5dfe7dd/protected-working-hashes.sha256
shasum -a 256 -c /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-hashes.sha256
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-paths.txt -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-dirs.txt -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-link-paths.txt -
while IFS= read -r artifact_link; do printf '%s -> %s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-link-paths.txt | diff -u /tmp/stock-research-modernization-baseline-1f5dfe7dd/artifact-link-targets.txt -
git diff --check
git status --short
```

Expected: every baseline file reports `OK`; no new data/output/docs-asset path,
directory, link, or link-target change exists; the same 18 protected working
files remain the only generated/data modifications; source/docs/test files are
intentional.

- [ ] **Step 6: Review the combined diff and commit final closure**

Request a fresh spec-compliance review and a code-quality review over the complete branch range. Fix every actionable finding test-first, rerun the affected and full gates, then stage only named source/test/docs/Makefile paths:

```bash
git add -- src/workspace_visual_browser_gate.py tests/test_workspace_visual_browser_gate.py tests/test_public_v1_release_docs.py tests/test_launchers.py README.md ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/PUBLIC_DEMO_WALKTHROUGH.md docs/DASHBOARD_QA.md docs/ACCESSIBILITY_EVIDENCE.md docs/OPERATOR_GUIDE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md Makefile
make staged-hygiene-check
git diff --cached --check
git commit -m "Close workspace modernization quality gates"
```

If a listed file has no intentional Task 6 change, omit it from the named staging command. Never stage the 18 generated/data paths.

- [ ] **Step 7: Final handoff**

Re-open the verified local Product page at Research Desk in the in-app browser, keep the preview running, and include current desktop/phone screenshots. Report implemented slices, exact test/browser evidence, unchanged artifact proof, current readiness/manual gates, branch/PR state, and the safest next action. Do not push, merge, deploy, promote artifacts, or claim external review without separate authorization.

---

## Completion Criteria

The modernization is complete only when Tasks 0-6 are committed in reviewable slices; all focused and full gates above are green except explicitly reported fail-closed external/manual pilot diagnostics; the full route/viewport browser matrix has no overflow, clipping, duplicate route navigation, traceback, or false semantic state; the task-start data/output bytes and path/type/link manifest are unchanged; and the local preview is open for inspection.
