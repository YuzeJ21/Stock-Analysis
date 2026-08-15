# Product Polish And Truth Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair one Research Desk layout failure and two user-facing truth contradictions without changing readiness calculations, generated data, routes, or product scope.

**Architecture:** Keep the existing calm institutional visual system and route helpers. Add a Research Desk-specific evidence-row layout override, correct one Public Home metric label, and make the existing project-status stage classifier distinguish recorded provider status from unavailable saved evidence.

**Tech Stack:** Python 3, Streamlit HTML helpers, CSS emitted by `dashboard_visual_system_css()`, pytest, the existing workspace visual browser gate, Chrome.

## Global Constraints

- Preserve the research-only boundary and “data readiness first, analysis second, research decision last.”
- Do not edit `data/`, `outputs/`, readiness calculations, source-rights decisions, or thresholds.
- Do not add provider probes, network calls, imports, refreshes, applies, materialization, or secret output.
- Do not truncate, clamp, hide, or nest-scroll the Research Desk evidence copy.
- Use `Mapped peer trend`; do not imply reviewed peer relationships or peer-relative valuation readiness.
- Missing or malformed saved provider status must fail closed to review-required.
- Do not push, deploy, publish, merge, or update PR #114.
- Stage only named intentional files; never use `git add -A`.

---

### Task 1: Research Desk supporting-evidence layout

**Files:**
- Modify: `src/dashboard_visual_system.py:694-708, 879-930`
- Test: `tests/test_dashboard_visual_system.py:150-166`
- Test: `tests/test_research_workspace.py:1549-1570`

**Interfaces:**
- Consumes: `dashboard_visual_system_css() -> str` and the existing `.research-desk-brief .sr-evidence-row` DOM emitted by `research_desk_brief_html()`.
- Produces: a scoped two-column desktop layout and a scoped one-column phone reset; no Python API changes.

- [ ] **Step 1: Write the failing CSS and full-copy regression**

Add this independent CSS contract to `tests/test_dashboard_visual_system.py`:

```python
def test_research_desk_evidence_layout_reserves_reason_width_and_resets_on_phone():
    css = visual.dashboard_visual_system_css()
    desktop = css[
        css.index(".research-desk-brief .sr-evidence-row {") :
        css.index(".sr-status-chip {")
    ]
    mobile = css[css.index("@media (max-width: 640px)") :]

    assert "grid-template-columns: minmax(12rem, .75fr) minmax(0, 2fr)" in desktop
    assert ".research-desk-brief .sr-evidence-count" in desktop
    assert "overflow-wrap: anywhere" in desktop
    assert ".research-desk-brief .sr-evidence-row p" in desktop
    assert "grid-column: 2" in desktop
    assert ".research-desk-brief .sr-evidence-row" in mobile
    assert "grid-template-columns: 1fr" in mobile
    assert "grid-column: 1" in mobile
    assert "grid-row: auto" in mobile
```

Extend `test_research_desk_brief_and_advanced_evidence_html_stay_answer_first_and_command_free()` with these hand-derived literal assertions:

```python
assert "Saved readiness is current." in desk_html
assert "No unresolved saved source-change item is available." in desk_html
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_dashboard_visual_system.py::test_research_desk_evidence_layout_reserves_reason_width_and_resets_on_phone \
  tests/test_research_workspace.py::test_research_desk_brief_and_advanced_evidence_html_stay_answer_first_and_command_free
```

Expected: the new CSS contract fails because no scoped Research Desk layout exists; the existing DOM/full-copy assertion remains green.

- [ ] **Step 3: Add the minimum scoped CSS**

Add immediately after the generic `.sr-evidence-count` rule:

```css
.research-desk-brief .sr-evidence-row {
  grid-template-columns: minmax(12rem, .75fr) minmax(0, 2fr);
  align-items: start;
}
.research-desk-brief .sr-evidence-lane { grid-row: 1 / span 2; }
.research-desk-brief .sr-evidence-count {
  grid-column: 2;
  overflow-wrap: anywhere;
  white-space: normal;
}
.research-desk-brief .sr-evidence-row p { grid-column: 2; }
```

Inside the existing `@media (max-width: 640px)` block, after the generic evidence-row reset, add:

```css
.research-desk-brief .sr-evidence-row { grid-template-columns: 1fr; }
.research-desk-brief .sr-evidence-lane,
.research-desk-brief .sr-evidence-count,
.research-desk-brief .sr-evidence-row p {
  grid-column: 1;
  grid-row: auto;
}
```

- [ ] **Step 4: Run focused GREEN**

Run the Step 2 command. Expected: `2 passed` and no new warnings.

- [ ] **Step 5: Review Task 1 diff without committing**

Run:

```bash
git diff --check
git diff -- src/dashboard_visual_system.py tests/test_dashboard_visual_system.py tests/test_research_workspace.py
```

Confirm the generic evidence-row contract and all phone navigation rules remain unchanged.

---

### Task 2: Public Home peer wording

**Files:**
- Modify: `src/dashboard.py:6653-6683`
- Test: `tests/test_dashboard_helpers.py:31272-31288`

**Interfaces:**
- Consumes: `public_home_overview_html(summary: dict[str, object]) -> str` and its existing `peer_ready` value.
- Produces: the same count under the label `Mapped peer trend`; no calculation or payload change.

- [ ] **Step 1: Write the failing rendered-copy regression**

Extend `test_public_home_overview_keeps_one_start_action_and_compact_readiness_snapshot()`:

```python
assert "<dt>Mapped peer trend</dt><dd>29</dd>" in html
assert "Trusted peers" not in html
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_dashboard_helpers.py::test_public_home_overview_keeps_one_start_action_and_compact_readiness_snapshot
```

Expected: FAIL because the rendered label is `Trusted peers`.

- [ ] **Step 3: Replace only the visible metric label**

In `public_home_overview_html()`, change:

```python
f"<div><dt>Trusted peers</dt><dd>{peer_ready:,}</dd></div>"
```

to:

```python
f"<div><dt>Mapped peer trend</dt><dd>{peer_ready:,}</dd></div>"
```

- [ ] **Step 4: Run focused GREEN**

Run the Step 2 command. Expected: `1 passed`.

- [ ] **Step 5: Review Task 2 diff without committing**

Run:

```bash
git diff --check
git diff -- src/dashboard.py tests/test_dashboard_helpers.py
```

Confirm the count source, count formatting, route, stop rule, and action remain unchanged.

---

### Task 3: Fail-closed provider-status classification

**Files:**
- Modify: `src/project_status.py:607-703`
- Test: `tests/test_project_status.py:1172-1225, 1370-1425`

**Interfaces:**
- Consumes: `_remaining_public_stage_rows(summary, source_operator_summary=...) -> list[dict[str, str]]`.
- Produces: the existing FMP stage row with one additional state, `source_status_review_required`, when `needs_setup` evidence is absent or malformed.

- [ ] **Step 1: Write missing, malformed, missing-key, and configured-state tests**

Add a small literal `summary` fixture in each test or a local helper that returns only the hand-written counts required by `_remaining_public_stage_rows()`.

```python
@pytest.mark.parametrize(
    "source_operator_summary",
    (None, {}, {"needs_setup": "fmp"}),
)
def test_project_status_fmp_stage_fails_closed_without_recorded_provider_state(
    source_operator_summary,
):
    rows = project_status._remaining_public_stage_rows(
        {
            "tickers_total": 10,
            "tickers_with_prices": 2,
            "tickers_usable_for_momentum": 2,
            "tickers_fundamentals_ready": 1,
            "tickers_dcf_ready": 1,
            "tickers_peer_ready": 0,
            "data_gaps": 8,
            "data_sources_optional_locked": 3,
        },
        source_operator_summary=source_operator_summary,
        git_status_line="## main...origin/main",
    )
    stage = next(row for row in rows if row["Stage"] == "FMP provider activation")

    assert stage["State"] == "source_status_review_required"
    assert stage["Diagnostic State"] == "source_status_unavailable"
    assert "not established from saved session status" in stage["Evidence"]
    assert stage["Next Action"] == "Run make provider-setup-checklist to inspect current local setup."
    assert "appears configured" not in " ".join(stage.values())


@pytest.mark.parametrize(
    ("needs_setup", "expected_state", "expected_diagnostic"),
    (
        (["fmp", "alpha_vantage", "finnhub"], "awaiting_external_setup", "external_key_required"),
        (["alpha_vantage", "finnhub"], "configured_smoke_required", "configured_smoke_required"),
        ([], "configured_smoke_required", "configured_smoke_required"),
    ),
)
def test_project_status_fmp_stage_preserves_explicit_saved_provider_states(
    needs_setup,
    expected_state,
    expected_diagnostic,
):
    rows = project_status._remaining_public_stage_rows(
        {
            "tickers_total": 10,
            "tickers_with_prices": 2,
            "tickers_usable_for_momentum": 2,
            "tickers_fundamentals_ready": 1,
            "tickers_dcf_ready": 1,
            "tickers_peer_ready": 0,
            "data_gaps": 8,
            "data_sources_optional_locked": 3,
        },
        source_operator_summary={"needs_setup": needs_setup},
        git_status_line="## main...origin/main",
    )
    stage = next(row for row in rows if row["Stage"] == "FMP provider activation")

    assert stage["State"] == expected_state
    assert stage["Diagnostic State"] == expected_diagnostic
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_project_status.py::test_project_status_fmp_stage_fails_closed_without_recorded_provider_state \
  tests/test_project_status.py::test_project_status_fmp_stage_preserves_explicit_saved_provider_states
```

Expected: the unavailable/malformed cases fail because they are currently classified as configured; explicit-state cases pass.

- [ ] **Step 3: Implement the recorded-status boundary**

Before normalizing `needs_setup`, retain the raw value and require the canonical list shape:

```python
source_operator_summary = (
    source_operator_summary if isinstance(source_operator_summary, dict) else {}
)
raw_needs_setup = source_operator_summary.get("needs_setup")
provider_status_recorded = isinstance(raw_needs_setup, list)
needs_setup = [
    str(item).strip().lower()
    for item in (raw_needs_setup if provider_status_recorded else [])
    if str(item).strip()
]
```

Build the FMP row before `rows`:

```python
if not provider_status_recorded:
    fmp_stage = {
        "State": "source_status_review_required",
        "Diagnostic State": "source_status_unavailable",
        "Evidence": "FMP configuration is not established from saved session status.",
        "Next Action": "Run make provider-setup-checklist to inspect current local setup.",
    }
elif fmp_missing:
    fmp_stage = {
        "State": "awaiting_external_setup",
        "Diagnostic State": "external_key_required",
        "Evidence": "FMP_API_KEY is not configured in the saved session source status.",
        "Next Action": "Set FMP_API_KEY outside the repo, then run one reviewed ticker smoke.",
    }
else:
    fmp_stage = {
        "State": "configured_smoke_required",
        "Diagnostic State": "configured_smoke_required",
        "Evidence": "Saved session source status records FMP as configured; provider setup still needs a reviewed one-ticker smoke.",
        "Next Action": "Run make fmp-smoke TICKER=<ticker>.",
    }
```

Use `fmp_stage` for the four varying values in the existing FMP stage row. Keep its completion gate and provider-setup boundary unchanged.

- [ ] **Step 4: Run focused GREEN and affected project-status tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_project_status.py::test_project_status_fmp_stage_fails_closed_without_recorded_provider_state \
  tests/test_project_status.py::test_project_status_fmp_stage_preserves_explicit_saved_provider_states \
  tests/test_project_status.py::test_project_status_stage_map_classifies_remaining_public_items \
  tests/test_project_status.py::test_project_status_cli_check_uses_fast_generated_artifacts \
  tests/test_next_stage.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Verify current command truth without writing artifacts**

Run:

```bash
make project-status-check > /tmp/stock-product-polish-project-status.log
make next-stage > /tmp/stock-product-polish-next-stage.log
rg -n "FMP provider activation|FMP_API_KEY|Provider key status|source status" \
  /tmp/stock-product-polish-project-status.log \
  /tmp/stock-product-polish-next-stage.log
```

Expected: project status does not claim FMP appears configured when saved source status is unavailable; next-stage retains its current local provider classification.

---

### Task 4: Affected verification and before/after evidence

**Files:**
- Verify: `src/dashboard_visual_system.py`
- Verify: `src/dashboard.py`
- Verify: `src/project_status.py`
- Verify: `tests/test_dashboard_visual_system.py`
- Verify: `tests/test_research_workspace.py`
- Verify: `tests/test_dashboard_helpers.py`
- Verify: `tests/test_project_status.py`
- Evidence only: `/tmp/stock-research-product-polish-*`

**Interfaces:**
- Consumes: all three GREEN tasks.
- Produces: focused test evidence, route screenshots, DOM geometry, and an independent review verdict; no repository artifact.

- [ ] **Step 1: Run the complete affected test set**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_visual_system.py \
  tests/test_research_workspace.py \
  tests/test_dashboard_helpers.py \
  tests/test_project_status.py \
  tests/test_next_stage.py
```

Expected: all tests pass; only previously documented third-party warnings are acceptable.

- [ ] **Step 2: Run the smallest affected browser matrix**

Run:

```bash
POLISH_BROWSER_DIR="$(mktemp -d /tmp/stock-research-product-polish-browser.XXXXXX)"
make workspace-visual-browser-check \
  ROUTES=research-desk,public-home \
  VIEWPORTS=1280x720,390x844 \
  ZOOMS=1,2 \
  OUTPUT_DIR="$POLISH_BROWSER_DIR"
```

Expected: 8/8 cells pass with zero runtime, overflow, focus, hierarchy, or external-network failures.

- [ ] **Step 3: Measure the corrected live layout**

Using the same local browser session, record the Research Desk desktop
`.sr-evidence-row p` width and height, row height, full text, and horizontal
bounds. Acceptance:

- reason width is at least 240 CSS pixels at `1280x720` and 100% zoom;
- row height is below 300 CSS pixels;
- both freshness and reason text are complete;
- no horizontal overflow; and
- phone layout is one column with no clipping.

Save the measurement JSON under `/tmp/stock-research-product-polish-layout.json`.

- [ ] **Step 4: Build and inspect before/after comparisons**

Use the accepted prior audit screenshots:

- `/tmp/stock-research-product-audit-2026-08-14/01-research-desk-desktop.png`
- `/tmp/stock-research-product-audit-2026-08-14/08-research-desk-fullpage-diagnostic.png`
- `/tmp/stock-research-product-audit-2026-08-14/09-public-home-desktop.png`
- `/tmp/stock-research-product-audit-2026-08-14/06-research-desk-phone.png`

Pair each with its same-viewport current screenshot in a single side-by-side comparison image under `/tmp/stock-research-product-polish-comparison/`. Inspect each combined image and reject any loading, crop, typography, spacing, border, radius, focus, or copy regression.

- [ ] **Step 5: Run final hygiene and independent review**

Run:

```bash
git diff --check
git status --short
git diff --name-only HEAD
```

Confirm no `data/` or `outputs/` path changed. Ask an independent reviewer for Critical/Important findings against the approved spec and final evidence.

- [ ] **Step 6: Commit the verified named files only**

Only after independent READY:

```bash
git add -- \
  src/dashboard_visual_system.py \
  src/dashboard.py \
  src/project_status.py \
  tests/test_dashboard_visual_system.py \
  tests/test_research_workspace.py \
  tests/test_dashboard_helpers.py \
  tests/test_project_status.py \
  docs/superpowers/plans/2026-08-14-product-polish-truth-fixes.md
git diff --cached --check
git commit -m "Polish research evidence and status truth"
```

Do not push the commit.
