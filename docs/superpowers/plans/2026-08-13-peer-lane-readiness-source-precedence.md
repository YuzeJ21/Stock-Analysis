# Peer Lane Readiness Source Precedence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Personal and Operator selected Data Health lanes use current saved readiness counts before older project-status counts, without changing readiness data or operating context.

**Architecture:** Keep the existing two inputs to `data_health_selected_lane_answer_cards()`. Make `dashboard_readiness_summary()` record count-level source-column provenance, then make the local resolver prefer only parseable, evidence-backed selected-profile counts, including zero. Project status remains the fallback and continues to provide source-setup and next-step context.

**Tech Stack:** Python 3.12, Streamlit, pytest, existing AppTest/render-smoke and browser-gate infrastructure.

## Global Constraints

- Data readiness first, analysis second, research decision last.
- Research-only: no recommendations, rankings, allocations, sizing, entry/exit guidance, transaction instructions, broker actions, performance claims, or fabricated data.
- Do not edit, regenerate, stage, reset, or clean any `data/` or `outputs/` path.
- Do not change readiness calculations, thresholds, source-rights decisions, navigation, or shared layout.
- No push, deployment, publication, tag, release, provider call, credential use, or external communication.

---

### Task 1: Make saved readiness authoritative for selected-lane counts

**Files:**
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `src/dashboard.py:24856-24885`
- Modify: `src/data_health_summary.py:26-130`

**Interfaces:**
- Consumes: `data_health_selected_lane_answer_cards(selected_lane_key, readiness_freshness, project_status_payload=None, saved_readiness_summary=None)`.
- Produces: unchanged list-of-card interface; only readiness-count source precedence changes.

- [ ] **Step 1: Write the failing conflict and zero regressions**

Replace the stale test that expects project-status aliases to override saved readiness with behavior tests using literal conflicting values:

```python
def test_data_health_peer_lane_prefers_authoritative_saved_readiness_counts():
    cards = dashboard.data_health_selected_lane_answer_cards(
        "peers",
        dashboard.FreshnessStatus(
            "current",
            "Saved readiness artifacts are current.",
            "make readiness-preview TOP_N=20",
        ),
        project_status_payload={
            "summary": {"tickers_peer_ready": 29, "data_gaps": 207}
        },
        saved_readiness_summary={"peer_ready": 9, "blocked_by_data": 175},
    )
    rendered = " ".join(
        str(value) for card in cards for value in card.values()
    ).lower()

    assert "9 tickers have trusted peer context" in rendered
    assert "175 locked input row(s)" in rendered
    assert "29 tickers have trusted peer context" not in rendered
    assert "207 locked input row(s)" not in rendered


def test_data_health_peer_lane_treats_saved_zero_as_authoritative():
    cards = dashboard.data_health_selected_lane_answer_cards(
        "peers",
        dashboard.FreshnessStatus(
            "current",
            "Saved readiness artifacts are current.",
            "make readiness-preview TOP_N=20",
        ),
        project_status_payload={
            "summary": {"tickers_peer_ready": 29, "data_gaps": 207}
        },
        saved_readiness_summary={"peer_ready": 0, "blocked_by_data": 0},
    )
    rendered = " ".join(
        str(value) for card in cards for value in card.values()
    ).lower()

    assert "0 tickers have trusted peer context" in rendered
    assert "0 locked input row(s)" in rendered
    assert "29 tickers have trusted peer context" not in rendered
```

The production mutation these tests catch is reversing the source order back to project-status-first or treating saved zero as absent.

- [ ] **Step 2: Run the two tests and verify RED**

Run:

```bash
python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py \
  -k 'authoritative_saved_readiness_counts or treats_saved_zero_as_authoritative'
```

Expected: both tests fail because the current helper renders the project-status values 29 and 207.

- [ ] **Step 3: Implement the minimal precedence change**

Record the count keys whose source columns are present in
`dashboard_readiness_summary()` as `_count_evidence_keys`. Then change the
nested resolver so adapter-produced summaries use a saved count only when its
requested key is evidence-backed; explicit caller-supplied mappings without
metadata retain their current literal semantics:

```python
def resolved_count(*keys: str) -> int | None:
    saved_count = (
        _summary_optional_count(saved_summary, *keys)
        if saved_count_evidence is None
        or any(key in saved_count_evidence for key in keys)
        else None
    )
    if saved_count is not None:
        return saved_count
    return _summary_optional_count(project_summary, *keys)
```

Resolve `data_sources_*` directly from `project_summary`; do not route those
operating-context counts through the saved-readiness resolver. Do not alter
recommendations, lane copy, or the function signature.

- [ ] **Step 4: Verify focused GREEN and existing fallbacks**

Run:

```bash
python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py -k 'data_health_peer_lane or data_health_price_lane'
```

Expected: the new conflict/zero cases pass; missing saved readiness still falls back to project status; absent counts still render unavailable.

---

### Task 2: Verify actual Personal and Operator route truth

**Files:**
- Test: `tests/test_dashboard_render_smoke.py`
- Test: `tests/test_research_mode_dashboard_contract.py`
- Test: `tests/test_dashboard_helpers.py`
- Runtime evidence: fresh temporary AppTest/browser outputs outside the repository.

**Interfaces:**
- Consumes: exact routes `/?mode=research&page=data-health&ticker=AVGO&lane=peers&drawer=proof` and `/?mode=operator&page=data-health&ticker=AVGO&lane=peers&drawer=proof`.
- Produces: current-byte evidence that both modes render 9 and reject stale 29 while preserving hierarchy, return path, mode, runtime, and no-advice boundaries.

- [ ] **Step 1: Run the affected static/render tests**

```bash
python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py
```

Expected: all tests pass with only known third-party warnings.

- [ ] **Step 2: Run a fresh two-route AppTest or browser proof**

Use the existing route/render harness on the two exact peer URLs. Assert each rendered result contains:

- `Selected Lane Answer — Peers`;
- `9 tickers have trusted peer context`;
- no `29 tickers have trusted peer context`;
- the correct Personal or Operator mode boundary;
- no exception or traceback;
- no recommendation, ranking, sizing, allocation, transaction, or performance claim.

Store all runtime evidence under a fresh `/tmp/stock-peer-lane-readiness-*` directory. Do not write screenshots or reports into the repository.

- [ ] **Step 3: Verify repository and artifact hygiene**

```bash
git diff --check
git status --short
git diff --name-only f88c4cdcdbffbf65928671b3acbfa51f6b1cdf48...HEAD
```

Expected: only the design, plan, production helper, and focused test files are intentional; no `data/` or `outputs/` path is changed or staged.

---

### Task 3: Independent review and local commit

**Files:**
- Review: complete branch diff against `f88c4cdcdbffbf65928671b3acbfa51f6b1cdf48`.

**Interfaces:**
- Consumes: final source/test diff and fresh verification artifacts.
- Produces: reviewer verdict with Critical/Important findings or READY.

- [ ] **Step 1: Request independent read-only review**

Ask the existing independent reviewer to inspect source precedence, zero semantics, fallback behavior, mode consistency, test quality, and protected-path hygiene. Do not edit while the review is active.

- [ ] **Step 2: Resolve any Critical or Important finding test-first**

For each reproduced finding, add a focused RED before changing production. Re-run only invalidated evidence.

- [ ] **Step 3: Run final verification and commit named paths**

After a READY verdict, run the final focused suite, `git diff --check`, and protected-path status verification. Stage exact named files only and commit locally. Do not push.
