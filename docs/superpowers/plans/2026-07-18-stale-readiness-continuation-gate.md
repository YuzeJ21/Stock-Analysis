# Stale Readiness Continuation Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every read-only continuation surface agree that stale selected-profile readiness permits no-write inspection only and does not authorize broad source, coverage, apply, or readiness-rebuild work.

**Architecture:** Add one pure `ContinuationGate` derived from `ProfileContext`, then consume it in project status, provider setup, and coverage-frontier rendering. Existing readiness calculations, provider availability, external dependency classifications, and ranked lane data remain unchanged; only the continuation-safe action layer overrides contradictory execution guidance while readiness is not current.

**Tech Stack:** Python 3.12, dataclasses, pytest, existing CLI renderers, Make release gates.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or post-earnings price prediction.
- Do not run `make readiness` or write generated CSV, JSON, report, sample-report, screenshot, timing, directory, or bytecode churn.
- `make readiness-preview TOP_N=20` is inspection evidence only and cannot make saved readiness current.
- Preserve independent readiness for actuals, consensus, Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, trusted relationships, peer comparability, peer valuation anchors, catalysts, outcomes, backtesting, and calibration.
- Candidate context cannot modify forecasts or become trusted evidence.
- Stage exact intentional files only; never use `git add -A`.

---

### Task 1: Pure continuation gate

**Files:**
- Create: `src/continuation_gate.py`
- Create: `tests/test_continuation_gate.py`

**Interfaces:**
- Consumes: `src.profile_context.ProfileContext`
- Produces: `ContinuationGate(state, next_safe_command, reason, rebuild_command, stop_rule, suppress_execution)` and `build_continuation_gate(context)`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from src.continuation_gate import build_continuation_gate
from src.profile_context import CoverageCounts, ProfileContext


def _context(state: str) -> ProfileContext:
    return ProfileContext(
        profile_key="default",
        profile_label="Default",
        data_dir=Path("data"),
        outputs_dir=Path("outputs"),
        source_as_of="2026-06-26",
        readiness_built_at="2026-06-07T03:00:43+00:00",
        snapshot_identity="abc",
        snapshot_identity_short="abc",
        freshness_state=state,
        freshness_message=f"Readiness is {state}.",
        refresh_command="make readiness",
        coverage=CoverageCounts(),
        lane_source_dates=(),
        snapshot_inputs=(),
    )


def test_stale_readiness_routes_to_no_write_preview():
    gate = build_continuation_gate(_context("stale"))
    assert gate.state == "inspection_only"
    assert gate.next_safe_command == "make readiness-preview TOP_N=20"
    assert gate.rebuild_command == "make readiness"
    assert gate.suppress_execution is True


def test_current_readiness_does_not_override_source_routing():
    gate = build_continuation_gate(_context("current"))
    assert gate.state == "current"
    assert gate.next_safe_command == ""
    assert gate.suppress_execution is False
```

- [ ] **Step 2: Run tests to verify the module is missing**

Run: `python3 -m pytest tests/test_continuation_gate.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.continuation_gate'`.

- [ ] **Step 3: Implement the pure gate**

```python
from dataclasses import dataclass

from src.profile_context import ProfileContext


@dataclass(frozen=True)
class ContinuationGate:
    state: str
    next_safe_command: str
    reason: str
    rebuild_command: str
    stop_rule: str
    suppress_execution: bool


def build_continuation_gate(context: ProfileContext) -> ContinuationGate:
    if context.freshness_state == "current":
        return ContinuationGate("current", "", context.freshness_message, context.refresh_command, "", False)
    state = "inspection_only" if context.freshness_state == "stale" else "inspection_required"
    return ContinuationGate(
        state=state,
        next_safe_command="make readiness-preview TOP_N=20",
        reason=context.freshness_message,
        rebuild_command=context.refresh_command or "make readiness",
        stop_rule=(
            "Do not start broad refresh, source-proof, apply, or readiness-rebuild work from stale or incomplete readiness counts."
        ),
        suppress_execution=True,
    )
```

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_continuation_gate.py tests/test_profile_context.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -- src/continuation_gate.py tests/test_continuation_gate.py
git commit -m "Add stale readiness continuation gate"
```

### Task 2: Fail-closed project-status routing

**Files:**
- Modify: `src/project_status.py`
- Modify: `tests/test_project_status.py`

**Interfaces:**
- Consumes: `ContinuationGate` from Task 1
- Produces: `continuation_gate` in project-status payloads and a stale-aware human rendering contract

- [ ] **Step 1: Write the failing project-status test**

```python
def test_project_status_stale_gate_suppresses_broad_next_steps(tmp_path, monkeypatch, capsys):
    _write_fast_status_artifacts(tmp_path)
    payload = project_status._fast_status_payload_from_outputs(tmp_path, top_n=5)
    gate = ContinuationGate(
        state="inspection_only",
        next_safe_command="make readiness-preview TOP_N=20",
        reason="Selected-profile source dates are newer than saved readiness.",
        rebuild_command="make readiness",
        stop_rule="Do not start broad refresh, source-proof, apply, or readiness-rebuild work.",
        suppress_execution=True,
    )

    project_status._print_human(payload, continuation_gate=gate)
    output = capsys.readouterr().out

    assert "Continuation-safe next action: make readiness-preview TOP_N=20" in output
    assert "Rebuild boundary: make readiness" in output
    assert "make price-refresh-loop DRY_RUN=1" not in output
    assert "make trusted-data-pilot-candidates TOP_N=10" not in output
```

- [ ] **Step 2: Run the test and verify the signature/behavior fails**

Run: `python3 -m pytest tests/test_project_status.py::test_project_status_stale_gate_suppresses_broad_next_steps -q`

Expected: FAIL because `_print_human` does not accept `continuation_gate` and broad recommendations remain visible.

- [ ] **Step 3: Apply the gate in the CLI and renderer**

Build the profile context once in `main`, derive the gate, and pass it to `_print_human`. When `suppress_execution` is true:

```python
print(f"Continuation gate: {continuation_gate.state}")
print(f"- Continuation-safe next action: {continuation_gate.next_safe_command}")
print(f"- Rebuild boundary: {continuation_gate.rebuild_command} requires an intentional reviewed write.")
print(f"- Stop rule: {continuation_gate.stop_rule}")
```

Do not render ticker-specific locked-input commands or generic recommended command rows in that state. Render one replacement row for the no-write preview and keep saved/stale coverage counts visible.

- [ ] **Step 4: Run project-status tests**

Run: `python3 -m pytest tests/test_project_status.py tests/test_continuation_gate.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -- src/project_status.py tests/test_project_status.py
git commit -m "Route stale project status to inspection only"
```

### Task 3: Align provider setup and coverage frontier

**Files:**
- Modify: `src/source_activation_guide.py`
- Modify: `src/readiness_ops.py`
- Modify: `tests/test_source_activation_guide.py`
- Modify: `tests/test_readiness_ops.py`

**Interfaces:**
- Consumes: `build_continuation_gate(build_profile_context(...))`
- Produces: stale-aware provider `current_gate` and coverage-frontier continuation banner

- [ ] **Step 1: Write failing provider and frontier tests**

```python
def test_provider_checklist_stale_profile_overrides_saved_preflight_action(tmp_path, monkeypatch):
    monkeypatch.setattr(
        source_activation_guide,
        "build_profile_context",
        lambda **_kwargs: SimpleNamespace(
            freshness_state="stale",
            freshness_message="Selected-profile source dates are newer than saved readiness.",
            refresh_command="make readiness",
        ),
    )
    current_preflight = {
        "source_activation_console_v2": {
            "operator_summary": {
                "can_run_now": ["sec_fundamentals_share_count"],
                "needs_setup": ["fmp", "alpha_vantage", "finnhub"],
                "avoid_repeating": [],
                "next_step": "make coverage-frontier TOP_N=10",
            }
        }
    }
    checklist = build_provider_setup_checklist(current_preflight, root=tmp_path)
    assert checklist["current_gate"]["can_run_now"] == "inspection_only"
    assert checklist["current_gate"]["next_step"] == "make readiness-preview TOP_N=20"
    assert "fmp" in checklist["current_gate"]["needs_setup"]


def test_coverage_frontier_stale_banner_marks_rows_planning_only():
    gate = ContinuationGate(
        state="inspection_only",
        next_safe_command="make readiness-preview TOP_N=20",
        reason="Selected-profile source dates are newer than saved readiness.",
        rebuild_command="make readiness",
        stop_rule="Do not start broad refresh, source-proof, apply, or readiness-rebuild work.",
        suppress_execution=True,
    )
    rendered = render_coverage_frontier([], continuation_gate=gate)
    assert "Continuation gate: inspection_only" in rendered
    assert "make readiness-preview TOP_N=20" in rendered
    assert "ranked rows below are planning context only" in rendered.lower()
    assert "make readiness is a separate intentional reviewed write" in rendered
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python3 -m pytest tests/test_source_activation_guide.py tests/test_readiness_ops.py -q`

Expected: FAIL because neither surface consumes the continuation gate.

- [ ] **Step 3: Implement provider checklist override**

In `build_provider_setup_checklist`, build the selected profile context for `root`, derive the gate, and override only action fields when fail-closed:

```python
current_gate.update(
    {
        "can_run_now": gate.state,
        "avoid_repeating": "broad_refresh, source_proof, readiness_rebuild",
        "next_step": gate.next_safe_command,
        "next_step_reason": gate.reason,
    }
)
```

Preserve `needs_setup`, provider rows, key-state classifications, and source-rights boundaries.

- [ ] **Step 4: Implement coverage-frontier banner**

Add an optional `continuation_gate` parameter to `render_coverage_frontier`. When fail-closed, render the gate before ranked lanes and state that lane commands are planning context only. In the CLI, build the selected profile context and pass the gate; keep pure frontier ranking unchanged.

- [ ] **Step 5: Run focused status tests**

Run: `python3 -m pytest tests/test_continuation_gate.py tests/test_project_status.py tests/test_source_activation_guide.py tests/test_readiness_ops.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -- src/source_activation_guide.py src/readiness_ops.py tests/test_source_activation_guide.py tests/test_readiness_ops.py
git commit -m "Align stale readiness operator guidance"
```

### Task 4: Documentation, full verification, and release handoff

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: verified runtime behavior from Tasks 1-3
- Produces: durable operating-maturity and continuation-contract evidence

- [ ] **Step 1: Add a failing documentation contract**

Require all four documents to contain the phrases `stale readiness continuation gate`, `make readiness-preview TOP_N=20`, `planning context only`, and `separate intentional reviewed write`.

- [ ] **Step 2: Run the documentation test and verify failure**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py -q`

Expected: FAIL until the docs describe the verified gate.

- [ ] **Step 3: Update documentation**

Document that project status, provider setup, and coverage frontier now agree on inspection-only routing while selected-profile readiness is stale. State that this improves operating reliability but does not refresh data, prove source correctness, authorize a rebuild, satisfy hosted/reviewer/source/calibration gates, or establish market validation.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
python3 -m pytest tests/test_continuation_gate.py tests/test_project_status.py tests/test_source_activation_guide.py tests/test_readiness_ops.py tests/test_public_v1_release_docs.py -q
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all tests and local release gates pass; pilot readiness remains truthfully blocked by stale readiness and external evidence; generated churn remains zero.

- [ ] **Step 5: Stage exact files and verify staged hygiene**

```bash
git add -- ROADMAP.md docs/DATA_STRATEGY.md docs/DASHBOARD_QA.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
```

- [ ] **Step 6: Commit, push, and update draft PR #113**

```bash
git commit -m "Document stale readiness continuation gate"
git push origin codex/personal-research-mode-mvp
```

Update PR #113 with the implementation, direct checks, zero-artifact result, current external classifications, and exact next external resume condition. Keep the PR draft and do not merge or deploy.
