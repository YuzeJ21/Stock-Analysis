# Company Workbench Task Arbitration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Company Workbench one deterministic next research task while retaining lane-specific blockers as non-competing context.

**Architecture:** Add a pure arbitration helper to `src/research_workspace.py` that combines the ticker-scoped change answer with the existing ordered Research Conclusion cards. Keep `src/dashboard.py` as a thin composer, and change only presentation labels in the existing conclusion and Forward View card builders.

**Tech Stack:** Python 3.12, Streamlit composition helpers, pytest.

## Global Constraints

- Do not change readiness, evidence, source rights, forecasts, scenarios, providers, or data files.
- Unresolved source-backed change outranks the ordered Research Conclusion priority.
- Missing inputs return a neutral wait condition and never invent evidence.
- Technical evidence remains under Advanced.
- No investment advice, buy/sell wording, post-earnings price prediction, probability, broker action, or data mutation.
- Do not create or stage generated CSV, JSON, report, sample-report, screenshot, timing, readiness, canonical-data, or manual-review churn.

## Final-review contract clarification

- `company_change_answer` carries an explicit boolean `source_backed_eligible`, set only when `event.evidence_status == "source_backed"`; the arbiter never infers eligibility from routing state, text, source references, or mapping shape.
- `company_change_answer` independently carries `change_context_kind` with exactly `none`, `snapshot_only`, or `source_backed`. Dashboard badges map from this discriminator: empty queue to `no queued change`, snapshot-only context to `snapshot evidence only`, and source-backed context to `source-backed change`.
- Eligible `open`, `still_blocked`, and `intentionally_deferred` items preserve `review_now`, `wait_for_evidence`, and `monitor` routing respectively. Blocked and deferred items preserve their non-empty wait condition, with the existing queue fallbacks when absent.
- Snapshot-only items remain in change context without a source-backed badge and cannot outrank Research Conclusion.
- Malformed arbitration inputs fail closed to the exact neutral wait task as a whole; no later card is selected after an earlier malformed card.
- The focused normal AVGO AppTest render must have zero exceptions, a scoped no-queued-change Evidence Change card without a snapshot-only badge, exactly one `ONE NEXT TASK` marker whose card title is `Add peer mappings`, one `FORWARD-VIEW LANE UNBLOCK`, and no retired uppercase `NEXT RESEARCH TASK` kicker.

---

### Task 1: Pure authoritative task arbitration

**Files:**
- Modify: `tests/test_research_workspace.py`
- Modify: `src/research_workspace.py`

**Interfaces:**
- Consumes: `company_change_answer: Mapping[str, object]` and `conclusion_cards: Iterable[Mapping[str, object]]`.
- Produces: `company_next_research_task(change_answer, conclusion_cards) -> dict[str, object]` with `title`, `body`, `state`, and `badges`; state is one of the existing research-routing states.

- [ ] **Step 1: Write failing arbitration tests**

Add the import and three tests:

```python
from src.research_workspace import company_next_research_task


def test_company_next_research_task_prioritizes_unresolved_source_change():
    task = company_next_research_task(
        {"state": "review_now", "next_task": "Review the filed evidence."},
        [{"title": "Add peer mappings", "body": "Peer context is partial.", "state": "wait_for_evidence", "badges": ["peers"]}],
    )
    assert task == {
        "title": "Review the filed evidence.",
        "body": "Complete this source-backed evidence review before starting another research task.",
        "state": "review_now",
        "badges": ["source-backed change", "research-only"],
    }


def test_company_next_research_task_uses_ordered_conclusion_priority_without_change():
    task = company_next_research_task(
        {"state": "monitor", "next_task": "Continue the current review or wait."},
        [{"title": "Add peer mappings", "body": "Peer context is partial.", "badges": ["peers"]}],
    )
    assert task["title"] == "Add peer mappings"
    assert task["body"] == "Peer context is partial."
    assert task["state"] == "wait_for_evidence"
    assert task["badges"] == ["peers", "research-only"]


def test_company_next_research_task_fails_closed_to_neutral_wait():
    task = company_next_research_task({}, [])
    assert task["title"] == "Wait for reviewed evidence or choose another company"
    assert task["state"] == "wait_for_evidence"
    assert task["badges"] == ["monitor", "research-only"]
```

- [ ] **Step 2: Run the tests and verify the intended failure**

Run:

```bash
python3 -m pytest \
  tests/test_research_workspace.py::test_company_next_research_task_prioritizes_unresolved_source_change \
  tests/test_research_workspace.py::test_company_next_research_task_uses_ordered_conclusion_priority_without_change \
  tests/test_research_workspace.py::test_company_next_research_task_fails_closed_to_neutral_wait -q
```

Expected: collection fails because `company_next_research_task` does not exist.

- [ ] **Step 3: Implement the pure helper**

Import `Iterable` and `Mapping` from `collections.abc`, then add:

```python
def company_next_research_task(
    change_answer: Mapping[str, object] | None,
    conclusion_cards: Iterable[Mapping[str, object]] | None,
) -> dict[str, object]:
    change = dict(change_answer or {})
    if str(change.get("state") or "").strip() == "review_now":
        title = str(change.get("next_task") or "").strip()
        if title:
            return {
                "title": title,
                "body": "Complete this source-backed evidence review before starting another research task.",
                "state": "review_now",
                "badges": ["source-backed change", "research-only"],
            }

    for raw_card in tuple(conclusion_cards or ()):
        card = dict(raw_card or {})
        title = str(card.get("title") or "").strip()
        if not title:
            continue
        badges = [str(value).strip() for value in tuple(card.get("badges") or ()) if str(value).strip()]
        return {
            "title": title,
            "body": str(card.get("body") or "").strip(),
            "state": (
                str(card.get("state") or "").strip()
                if str(card.get("state") or "").strip() in RESEARCH_ROUTING_STATES
                else "wait_for_evidence"
            ),
            "badges": list(dict.fromkeys([*badges, "research-only"])),
        }

    return {
        "title": "Wait for reviewed evidence or choose another company",
        "body": "No source-backed change or executable company task is available. Do not infer one from missing data.",
        "state": "wait_for_evidence",
        "badges": ["monitor", "research-only"],
    }
```

- [ ] **Step 4: Run the focused helper tests**

Run the Step 2 command again.

Expected: 3 passed.

---

### Task 2: Remove competing next-task labels

**Files:**
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_forward_view.py`
- Modify: `src/dashboard.py`
- Modify: `src/forward_view.py`

**Interfaces:**
- Consumes: `stock_report_next_step_cards(...)` and `forward_view_cards(packet)`.
- Produces: first conclusion card kicker `RESEARCH PRIORITY` with explicit existing routing state; final Forward View card kicker `FORWARD-VIEW LANE UNBLOCK`.

- [ ] **Step 1: Tighten presentation tests**

Extend `test_stock_report_next_step_cards_route_to_fundamentals_then_peers_then_review` after each representative call:

```python
assert cards[0]["kicker"] == "RESEARCH PRIORITY"
assert cards[0]["state"] == "wait_for_evidence"
assert all(card["kicker"] != "NEXT STEP" for card in cards)
```

Change `test_forward_view_rows_keep_technical_details_separate_and_research_only` to:

```python
assert cards[-1]["kicker"] == "FORWARD-VIEW LANE UNBLOCK"
assert all(card["kicker"] != "NEXT RESEARCH TASK" for card in cards)
```

- [ ] **Step 2: Run the tests and verify two label failures**

Run:

```bash
python3 -m pytest \
  tests/test_dashboard_helpers.py::test_stock_report_next_step_cards_route_to_fundamentals_then_peers_then_review \
  tests/test_forward_view.py::test_forward_view_rows_keep_technical_details_separate_and_research_only -q
```

Expected: both tests fail on the old kickers.

- [ ] **Step 3: Change only the two presentation labels**

In every primary card branch inside `stock_report_next_step_cards`, replace:

```python
"kicker": "NEXT STEP",
```

with:

```python
"kicker": "RESEARCH PRIORITY",
```

Set `"state": "wait_for_evidence"` on the fix-price, stage/review-fundamentals, and add/review-peer branches. Set `"state": "review_now"` on the ETF/context-review and full-report-review branches. Do not introduce a new routing state.

In the appended routing card inside `forward_view_cards`, replace:

```python
"kicker": "NEXT RESEARCH TASK",
```

with:

```python
"kicker": "FORWARD-VIEW LANE UNBLOCK",
```

- [ ] **Step 4: Run the focused presentation tests**

Run the Step 2 command again.

Expected: 2 passed.

---

### Task 3: Compose one Workbench task and update contracts

**Files:**
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `src/dashboard.py`
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: `company_next_research_task(change_answer, conclusion_cards)`.
- Produces: one `ONE NEXT TASK` card in Company Workbench, with Research Conclusion and Forward View no longer claiming separate next tasks.

- [ ] **Step 1: Add a source contract test for thin composition**

Add to `tests/test_research_mode_dashboard_contract.py`:

```python
def test_company_workbench_uses_one_authoritative_task_arbitration():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    assert "company_next_research_task(" in source
    assert '"kicker": "ONE NEXT TASK"' in source
    assert '"title": str(authoritative_task["title"])' in source
    assert source.count('"kicker": "ONE NEXT TASK"') == 1
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
python3 -m pytest tests/test_research_mode_dashboard_contract.py::test_company_workbench_uses_one_authoritative_task_arbitration -q
```

Expected: fail because the dashboard does not call the helper.

- [ ] **Step 3: Wire the helper into Company Workbench**

Import `company_next_research_task` from `src.research_workspace`. In the Research Conclusion block, compute the conclusion cards once, render them, then compute the authoritative task:

```python
conclusion_cards = stock_report_next_step_cards(
    report_payload,
    coverage if provider is not None and ticker else None,
    peer_summary if provider is not None and ticker else None,
)
render_signal_cards(conclusion_cards, show_commands=False, variant="queue")
change_answer = company_change_answer(ticker, research_review_items)
authoritative_task = company_next_research_task(change_answer, conclusion_cards)
```

Render the existing `ONE NEXT TASK` card from the authoritative result:

```python
{
    "kicker": "ONE NEXT TASK",
    "title": str(authoritative_task["title"]),
    "body": str(authoritative_task["body"]),
    "badges": list(authoritative_task["badges"]),
    "state": str(authoritative_task["state"]),
    "command": "",
}
```

- [ ] **Step 4: Update product truth documentation**

Add concise current-state notes stating:

- Company Workbench now arbitrates one overall task.
- unresolved source-backed change wins;
- otherwise the existing ordered Research Conclusion priority wins;
- Forward View guidance is lane-specific, not a competing overall task;
- readiness and evidence states remain independent and unchanged.

Update ROADMAP and the continuation prompt only with this verified local capability. Do not change any external dependency classification.

- [ ] **Step 5: Run focused module and documentation tests**

Run:

```bash
python3 -m pytest \
  tests/test_research_workspace.py \
  tests/test_dashboard_helpers.py \
  tests/test_forward_view.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_public_v1_release_docs.py -q
```

Expected: all pass.

- [ ] **Step 6: Run the full verification matrix**

Run:

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make commercial-beta-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
make pr-range-hygiene-check
git diff --check
```

Expected: all commands exit 0; pilot readiness may remain truthfully blocked only by its documented external/stale gates; no generated artifact appears.

- [ ] **Step 7: Stage exact files and run staged hygiene**

Stage only the two spec/plan files and exact intentional code, test, and documentation paths. Never use `git add -A`. Then run:

```bash
make staged-hygiene-check
git diff --cached --check
```

Expected: both pass with zero generated or manual-review candidates.

- [ ] **Step 8: Commit, push, and update draft PR #113**

Commit the coherent verified slice, push only `codex/personal-research-mode-mvp`, add a concise verification update to PR #113, and keep it draft. Do not merge or deploy.
