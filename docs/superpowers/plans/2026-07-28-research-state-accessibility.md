# Research State Accessibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give user-triggered research-authoring transitions one deterministic visible announcement while keeping initial static states readable and non-noisy.

**Architecture:** A pure message module maps closed state tokens to visible alert/status HTML. The authoring UI owns transition identity and deduplication; a synthetic test-only Streamlit harness and the real Company Workbench verify semantics without writing production ledgers.

**Tech Stack:** Python 3.12, frozen dataclasses, escaped HTML, Streamlit session state, pytest, Streamlit AppTest, Playwright browser gate.

## Global Constraints

- Live announcements are limited to `validation_rejected`, `preview_ready`, `draft_changed`, `save_reloaded`, and `save_reload_unverified`.
- Initial loading, empty, withheld, stale, blocked, and failure content remains ordinary accessible content unless it changes after a user action.
- `validation_rejected` and `save_reload_unverified` use `role="alert"` and assertive semantics; other transitions use `role="status"` and polite semantics.
- Every live message is visible, atomic, scope-specific, and rendered once per exact transition identity.
- Preserve exact required-field association, focus, global-alert count, preview receipt, save, and reload semantics.
- No message claims source rights, readiness, evidence quality, forecast, commercial eligibility, or investment action changed.
- Synthetic browser fixtures are test-only and are not screen-reader, human, hosted, or WCAG evidence.
- No production ledger, generated CSV/JSON/report, screenshot, timing, or canonical-data write.

---

### Task 1: Pure State Message Contract

**Files:**
- Create: `src/research_state_accessibility.py`
- Create: `tests/test_research_state_accessibility.py`

**Interfaces:**
- Produces: `ResearchStateMessage(state: str, title: str, detail: str, role: str, live: str, message_id: str)`.
- Produces: `research_state_message(state: str, *, scope: str, title: str, detail: str, identity: str) -> ResearchStateMessage`.
- Produces: `research_state_message_html(message: ResearchStateMessage, *, announce: bool = True) -> str`.
- Produces: `research_state_transition_key(message: ResearchStateMessage) -> str`.

- [ ] **Step 1: Write failing literal semantic tests**

```python
@pytest.mark.parametrize(
    ("state", "role", "live"),
    [
        ("validation_rejected", "alert", "assertive"),
        ("preview_ready", "status", "polite"),
        ("draft_changed", "status", "polite"),
        ("save_reloaded", "status", "polite"),
        ("save_reload_unverified", "alert", "assertive"),
    ],
)
def test_state_message_semantics(state, role, live):
    message = research_state_message(
        state,
        scope="demo:NVDA:thesis",
        title="State changed",
        detail="Review the visible next step.",
        identity="receipt-1",
    )
    assert (message.role, message.live) == (role, live)
    rendered = research_state_message_html(message, announce=True)
    assert f"role='{role}'" in rendered
    assert f"aria-live='{live}'" in rendered
    assert "aria-atomic='true'" in rendered
```

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_state_accessibility.py -q`

Expected: FAIL because the module does not exist.

- [ ] **Step 2: Implement closed mapping, escaped visible HTML, and stable identity**

Use `html.escape` on all visible and attribute values. Reject empty scope/identity/title and unknown states. Generate `message_id` from normalized scope/state plus a SHA-256 prefix of the supplied identity; never place receipt contents in the DOM.

- [ ] **Step 3: Add duplicate/unsafe-content tests**

Prove identical inputs produce the same transition key, different receipt
identity produces a different key, HTML characters are escaped, and the
rendered element contains exactly one title/detail with no visually hidden
duplicate. Also prove `announce=False` renders visible text with
`role="group"` and no `aria-live` attribute.

- [ ] **Step 4: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_state_accessibility.py -q
git diff --check
git add -- src/research_state_accessibility.py tests/test_research_state_accessibility.py
make staged-hygiene-check
git commit -m "Add research state announcement contract"
```

### Task 2: Authoring Transition Integration

**Files:**
- Modify: `src/research_record_authoring_ui.py`
- Modify: `tests/test_research_record_authoring_ui.py`
- Modify: `tests/fixtures/research_record_authoring_app.py`

**Interfaces:**
- Produces: `_render_authoring_state_message(st_api, message, *, session_key: str) -> None`.
- Consumes: exact preview digest/receipt, draft digest, and persisted record ID already present in the authoring flow.

- [ ] **Step 1: Write failing AppTest transition tests**

```python
def test_valid_preview_announces_unsaved_state_once(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=_validate_key()).click().run()
    statuses = app.get("html")
    assert _messages(statuses, role="status") == [
        "Preview ready This exact record is ready for review and is not saved."
    ]
    app.run()
    assert len(_messages(app.get("html"), role="status")) == 1
```

Add separate tests for rejected validation, changed draft, reloaded save, and reload-unverified receipt. Assert one message, correct role, exact recovery wording, and no production-ledger write.

- [ ] **Step 2: Run focused tests and confirm missing announcements**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring_ui.py -q`

Expected: FAIL because transitions use existing Streamlit alerts/captions without the shared contract.

- [ ] **Step 3: Integrate one visible message per exact transition**

Use the pure helper to replace, not duplicate, the corresponding `st.error`,
`st.warning`, and `st.success` messages. Store the last rendered transition key
under the existing profile/ticker/kind authoring namespace. A normal rerun
with the same transition key calls
`research_state_message_html(message, announce=False)` so the state remains
visible but does not insert another live node.

Keep field-error binding called once. Validation rejection remains one global alert and focuses only exact supported required-field errors.

- [ ] **Step 4: Verify save recovery language**

`save_reloaded` includes the exact record ID and append-only correction rule. `save_reload_unverified` says verification is incomplete and directs ledger inspection; it must not display `Retry save`, `Save again`, or any equivalent duplicate-write invitation.

- [ ] **Step 5: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_state_accessibility.py tests/test_research_record_authoring_ui.py tests/test_research_record_authoring.py -q
git diff --check
git add -- src/research_record_authoring_ui.py tests/test_research_record_authoring_ui.py tests/fixtures/research_record_authoring_app.py
make staged-hygiene-check
git commit -m "Announce research authoring transitions"
```

### Task 3: Static-State and Direct Browser Evidence

**Files:**
- Create: `tests/fixtures/research_state_accessibility_app.py`
- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `docs/ACCESSIBILITY_EVIDENCE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-07-28-research-state-accessibility-design.md`

**Interfaces:**
- Adds a loopback, synthetic, in-memory/stdout-only state harness to the existing browser gate.
- Produces per-state assertions for role, live policy, atomicity, visible text, duplicates, overflow, console errors, and traceback.

- [ ] **Step 1: Write failing harness contract tests**

Assert the harness exposes exactly five transition controls and six static cases: loading, empty, withheld, stale, failure, and validation. Assert the gate rejects duplicate live nodes, hidden-only messages, wrong role, missing atomicity, and any repository write.

- [ ] **Step 2: Implement the synthetic harness using production render helpers**

The fixture imports `research_state_message` and `research_state_message_html`. It uses synthetic labels such as `TEST1` and contains no real company evidence, forecast, probability, or ledger. The gate starts it on an isolated loopback port and records results only in memory/stdout.

- [ ] **Step 3: Add static-state semantic assertions**

Loading retains readable text and `aria-busy=true`. Empty, withheld, stale, and failure initial content has no `aria-live` attribute. Validation has one alert and, in the real Company Workbench regression, exact field association and focus.

- [ ] **Step 4: Run direct desktop and phone evidence**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_accessibility_browser_gate.py tests/test_dashboard_helpers.py -q
make research-accessibility-browser-check
```

Require `1280x720` and `390x844`, zero overflow, zero duplicate announcement, zero console/page error, zero traceback, and unchanged production ledger hashes.

- [ ] **Step 5: Update bounded evidence and run full gates**

Document automation-only evidence and keep zoom, forced colors, reduced motion, screen-reader, and independent-human gates open.

Run:

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
git add -- tests/fixtures/research_state_accessibility_app.py src/research_accessibility_browser_gate.py tests/test_research_accessibility_browser_gate.py tests/test_dashboard_helpers.py docs/ACCESSIBILITY_EVIDENCE.md ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/superpowers/specs/2026-07-28-research-state-accessibility-design.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Verify accessible research state transitions"
git push origin codex/personal-research-mode-mvp
gh pr checks 113 --watch
```

Expected: PR remains draft, exact-head CI succeeds, and generated working data remains unstaged.
