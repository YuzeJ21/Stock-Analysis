# Proof-Readiness Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make historical proof outcomes impossible to mistake for current saved readiness by adding a read-only, lane-independent reconciliation engine, CLI, and Advanced Proof History answer.

**Architecture:** A new pure module consumes the append-only batch proof ledger and the three current readiness reports, maps only explicit proof lanes to explicit current fields, and emits immutable reconciliation rows plus a bounded summary. The CLI and dashboard consume that same result; neither writes data, alters readiness, or rewrites proof history.

**Tech Stack:** Python 3.12, pandas, dataclasses, argparse, pytest, Streamlit, Make.

## Global Constraints

- Research-only; no investment advice, rankings, recommendations, broker integration, order routing, or auto-trading.
- Current saved readiness remains authoritative for current lane availability.
- Historical proof remains append-only and cannot promote current readiness.
- Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, calibration, source rights, field scope, price lineage, hosted operations, and external validation stay independent.
- Do not run `make readiness`, source refreshes, imports, applies, report generation, screenshot generation, or timing generation.
- Preserve the existing 18 generated readiness files as local, unstaged churn.
- Never use `git add -A`; stage only exact intentional files.
- Keep PR #113 open and draft.

---

### Task 1: Pure Reconciliation Engine

**Files:**
- Create: `src/proof_readiness_reconciliation.py`
- Create: `tests/test_proof_readiness_reconciliation.py`

**Interfaces:**
- Consumes: `ReviewedBatchProof` objects from `src.reviewed_batch_proof`, plus ticker, DCF, and peer readiness `pandas.DataFrame` objects.
- Produces: `ProofReadinessReconciliationRow`, `ProofReadinessReconciliationSummary`, `build_proof_readiness_reconciliation`, `load_proof_readiness_reconciliation`, and `filter_reconciliation_rows`.

- [ ] **Step 1: Write failing state and independence tests**

Create `tests/test_proof_readiness_reconciliation.py` with fixtures that use real `ReviewedBatchProof` objects and in-memory readiness frames. The first tests must assert these exact states:

```python
def test_historical_supported_fundamentals_stays_blocked_when_current_readiness_is_false():
    summary = build_proof_readiness_reconciliation(
        proofs=[proof(tickers="ARCT", lane="fundamentals", outcome="auto_supported")],
        ticker_readiness=ticker_frame(ARCT={"fundamentals_ready": "False"}),
        dcf_readiness=dcf_frame(ARCT={"has_shares_outstanding": "False"}),
        peer_readiness=peer_frame(),
    )
    row = row_for(summary, "ARCT", "fundamentals")
    assert row.state == "historical_supported_currently_blocked"
    assert row.current_ready is False
    assert row.latest_batch_id == "RB-1"


def test_current_ready_without_supporting_latest_proof_is_not_proof_backed():
    summary = build_proof_readiness_reconciliation(
        proofs=[proof(tickers="ARCT", lane="fundamentals", outcome="still_blocked")],
        ticker_readiness=ticker_frame(ARCT={"fundamentals_ready": "True"}),
        dcf_readiness=dcf_frame(ARCT={"has_shares_outstanding": "False"}),
        peer_readiness=peer_frame(),
    )
    assert row_for(summary, "ARCT", "fundamentals").state == "current_ready_proof_not_supporting"
```

Add separate tests for current support with matching proof, later `still_blocked` superseding earlier support, `fundamentals_dcf`, share count, price aliases, peer mapping, peer valuation inputs, no proof, unknown lanes/outcomes, malformed dates/booleans, duplicate tickers, and descriptive ticker text.

- [ ] **Step 2: Run the new test file and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py -q
```

Expected: collection fails because `src.proof_readiness_reconciliation` does not exist.

- [ ] **Step 3: Implement immutable rows, explicit mappings, and deterministic latest-proof selection**

Create `src/proof_readiness_reconciliation.py` with these public values and signatures:

```python
SUPPORTING_OUTCOMES = frozenset({"supported", "auto_supported", "human_reviewed_supported"})

LANE_MAPPINGS = {
    "fundamentals": ("fundamentals", "ticker", "fundamentals_ready"),
    "fundamentals_dcf": ("dcf", "ticker", "dcf_ready"),
    "share_count": ("share_count", "dcf", "has_shares_outstanding"),
    "price": ("price", "ticker", "price_ready"),
    "prices": ("price", "ticker", "price_ready"),
    "price_coverage": ("price", "ticker", "price_ready"),
    "price_history": ("price", "ticker", "price_ready"),
    "peers": ("peer_mapping", "ticker", "peer_ready"),
    "peer_mapping": ("peer_mapping", "ticker", "peer_ready"),
    "peer_valuation_inputs": ("peer_valuation_inputs", "peer", "peer_valuation_ready"),
}

@dataclass(frozen=True)
class ProofReadinessReconciliationRow:
    ticker: str
    lane: str
    current_field: str
    current_ready: bool | None
    latest_batch_id: str
    latest_review_date: str
    latest_outcome: str
    review_date_valid: bool
    state: str
    reason: str


@dataclass(frozen=True)
class ProofReadinessReconciliationSummary:
    rows: tuple[ProofReadinessReconciliationRow, ...]
    status_counts: tuple[tuple[str, int], ...]
    conflict_counts_by_lane: tuple[tuple[str, int], ...]
    input_status: str
    input_message: str


def _reconciliation_state(*, current_ready: bool | None, proof_exists: bool, supporting: bool) -> str:
    if current_ready is None:
        return "not_applicable"
    if current_ready and supporting:
        return "current_supported_with_matching_proof"
    if not current_ready and supporting:
        return "historical_supported_currently_blocked"
    if current_ready:
        return "current_ready_proof_not_supporting"
    if proof_exists:
        return "currently_blocked_with_non_supporting_history"
    return "no_proof_record"
```

Expose `build_proof_readiness_reconciliation` with keyword-only `proofs`, `ticker_readiness`, `dcf_readiness`, and `peer_readiness` arguments and a `ProofReadinessReconciliationSummary` return. Expose `load_proof_readiness_reconciliation` with keyword-only `root: Path`. Expose `filter_reconciliation_rows` with `summary`, keyword-only `tickers: Sequence[str] = ()`, and `top_n: int = 20`, returning an immutable tuple of rows.

Implementation requirements:

- create six canonical rows per valid ticker: fundamentals, DCF, share count, price, peer mapping, and peer valuation inputs;
- use current ticker-readiness membership as the valid ticker set;
- split proof tickers on commas or semicolons, uppercase, deduplicate, and ignore tokens absent from the valid set;
- choose the latest proof per canonical ticker/lane by valid ISO review date then append index;
- never let a malformed date outrank a valid date; a malformed supporting outcome is non-supporting;
- parse only explicit `true` and `false`; every other value yields `current_ready=None` and `not_applicable`;
- sort conflicts first, then current-ready proof gaps, then other states, each by lane and ticker;
- calculate global counts before presentation filtering.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py -q
```

Expected: all reconciliation engine tests pass.

- [ ] **Step 5: Commit the pure engine**

Run:

```bash
git add src/proof_readiness_reconciliation.py tests/test_proof_readiness_reconciliation.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Reconcile proof history with current readiness"
```

Expected: exactly the engine and its tests are committed; generated files remain unstaged.

---

### Task 2: Read-Only CLI And Make Entry Point

**Files:**
- Modify: `src/proof_readiness_reconciliation.py`
- Modify: `tests/test_proof_readiness_reconciliation.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: `load_proof_readiness_reconciliation`, `filter_reconciliation_rows`.
- Produces: `render_proof_readiness_reconciliation`, `proof_readiness_reconciliation_payload`, module `main()`, and `make proof-readiness-reconciliation TOP_N=20`.

- [ ] **Step 1: Write failing CLI rendering tests**

Add tests asserting:

```python
def test_render_names_conflicts_and_non_promotion_boundary():
    rendered = render_proof_readiness_reconciliation(summary_with_conflict(), top_n=10)
    assert "Proof-Readiness Reconciliation" in rendered
    assert "historical_supported_currently_blocked" in rendered
    assert "Current saved readiness remains authoritative" in rendered
    assert "does not restore data, promote readiness, or rewrite proof history" in rendered


def test_main_is_read_only(tmp_path, capsys):
    write_fixture_inputs(tmp_path)
    before = snapshot_files(tmp_path)
    assert main(["--root", str(tmp_path), "--top-n", "10"]) == 0
    assert snapshot_files(tmp_path) == before
    assert "Research-only" in capsys.readouterr().out
```

Add a JSON test asserting the payload retains global counts when `--tickers ARCT` narrows displayed rows.

- [ ] **Step 2: Run CLI tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py -q
```

Expected: tests fail because rendering and `main` are absent.

- [ ] **Step 3: Implement rendering, JSON, argparse, and Make target**

Add:

```python
def _parse_ticker_filter(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token.strip().upper() for token in value.split(",") if token.strip()))
```

Expose `render_proof_readiness_reconciliation` and `proof_readiness_reconciliation_payload` with the same `summary`, `tickers`, and `top_n` contract as the filter. Expose `main(argv: Sequence[str] | None = None) -> int`; it parses `--root`, `--top-n`, `--tickers`, and `--json`, prints exactly one representation to stdout, and returns zero without opening any output file for writing.

The human renderer must print input status, global state counts, conflict counts by canonical lane, bounded detail rows, the read-only boundary, and the exact next command. JSON must serialize dataclasses without changing state.

Add the target to `.PHONY`, Make help, and the command body:

```make
proof-readiness-reconciliation:
	@python3 -m src.proof_readiness_reconciliation --root . --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers "$(TICKERS)",) $(if $(filter 1,$(JSON)),--json,)
```

- [ ] **Step 4: Run focused tests and the real command**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py -q
make proof-readiness-reconciliation TOP_N=10
make diff-hygiene-summary
```

Expected: tests pass; the command reports current conflicts; diff hygiene still reports only intentional product files plus the protected 18 generated files.

- [ ] **Step 5: Commit the CLI slice**

Run:

```bash
git add Makefile src/proof_readiness_reconciliation.py tests/test_proof_readiness_reconciliation.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Expose proof readiness reconciliation"
```

---

### Task 3: Advanced Proof History Integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_render_smoke.py` only if the established route-marker contract needs the new marker.

**Interfaces:**
- Consumes: `load_proof_readiness_reconciliation`, filtered reconciliation rows, current `DATA_DIR`, and the optional `ticker` query parameter.
- Produces: `proof_readiness_reconciliation_cards` and an answer-first warning before raw ledger detail in both public and operator Proof History render paths.

- [ ] **Step 1: Write failing dashboard helper and ordering tests**

Add tests proving the card contract:

```python
def test_proof_reconciliation_cards_warn_when_historical_support_is_currently_blocked():
    cards = dashboard.proof_readiness_reconciliation_cards(summary_with_conflict(), ticker="ARCT")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    assert "historical support is not current readiness" in rendered
    assert "arct" in rendered
    assert "current saved readiness remains authoritative" in rendered
    assert "make " not in rendered
```

Add source-order assertions that reconciliation cards are rendered after the latest evidence timeline/answer but before `Advanced: proof ledger details`. Add a selected-ticker test and a no-conflict test. Keep existing tests proving primary pages and public Proof History do not expose operator commands.

- [ ] **Step 2: Run dashboard tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py -q -k 'proof_history or proof_reconciliation'
```

Expected: new tests fail because the dashboard helper and rendering call are absent.

- [ ] **Step 3: Implement the minimal answer-first integration**

Import the reconciliation loader and row filter. Add:

```python
def proof_readiness_reconciliation_cards(
    summary: ProofReadinessReconciliationSummary,
    *,
    ticker: str = "",
) -> list[dict[str, object]]:
    conflicts = [row for row in summary.rows if row.state == "historical_supported_currently_blocked"]
    selected = ticker.strip().upper()
    selected_conflicts = [row for row in conflicts if selected and row.ticker == selected]
    cards = [{
        "kicker": "PROOF / CURRENT STATE",
        "title": f"{len(conflicts):,} historical-support conflict(s)",
        "body": (
            "Historical support is not current readiness. Current saved readiness remains authoritative; "
            "reconciliation does not restore data, promote readiness, or rewrite proof history."
        ),
        "badges": [summary.input_status, "read-only"],
        "command": "",
    }]
    if selected_conflicts:
        lanes = ", ".join(row.lane.replace("_", " ") for row in selected_conflicts)
        cards.append({
            "kicker": "SELECTED TICKER",
            "title": f"{selected}: historical proof conflicts with current readiness",
            "body": f"Current blocked lane(s): {lanes}. Re-review source evidence before relying on an older supported outcome.",
            "badges": [selected, "currently blocked"],
            "command": "",
        })
    return cards
```

The first card must report the global conflict count. When the selected ticker has conflicts, a second card must name only that ticker's canonical lanes. When no conflict exists, the card must say that reconciliation found no historical-support/current-readiness conflict while still refusing to prove source rights or payload truth. Cards must have empty commands.

In `render_proof_history`, load the summary from the current repository root, read `ticker` from `st.query_params`, and render reconciliation cards before the ledger expander. Do not add the cards to Research Desk, Discover, Company Workbench, or Monitor.

- [ ] **Step 4: Run focused dashboard and render tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py -q
make research-dashboard-render-smoke
```

Expected: all focused dashboard tests and six research route renders pass.

- [ ] **Step 5: Commit the dashboard slice**

Run:

```bash
git add src/dashboard.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Show proof readiness conflicts in Proof History"
```

Stage `tests/test_dashboard_render_smoke.py` only if it changed.

---

### Task 4: Methodology, Roadmap, Continuation Contract, And Release Verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/OPERATOR_GUIDE.md`
- Modify: documentation contract tests selected by existing repository patterns.

**Interfaces:**
- Consumes: verified CLI output, focused tests, and dashboard behavior.
- Produces: durable stage truth and the exact continuation command.

- [ ] **Step 1: Write failing documentation contract assertions**

Add assertions to the existing documentation tests that require:

```text
make proof-readiness-reconciliation TOP_N=20
historical_supported_currently_blocked
current saved readiness remains authoritative
```

The continuation contract must require reconciliation before reusing a supporting proof outcome and must preserve all external classifications.

- [ ] **Step 2: Run documentation tests and verify RED**

Run the selected documentation test module identified by `rg` and confirm the new assertions fail before documentation changes.

- [ ] **Step 3: Update documentation truthfully**

Document the implemented read-only behavior, the current-snapshot audit finding, and these limits:

- reconciliation does not repair or restore canonical data;
- historical proof remains append-only;
- current readiness does not prove source rights, field scope, provenance, payload truth, or commercial use;
- the audit count is current-snapshot evidence, not a durable coverage total;
- future runs inspect reconciliation once before restarting a proof lane.

- [ ] **Step 4: Run focused documentation checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q -k 'public_v1_release_docs or proof_readiness_reconciliation'
make public-wording-check
git diff --check
```

- [ ] **Step 5: Run the complete release matrix**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
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

Expected: every gate passes; the pilot remains truthful about manual source-proof and generated-artifact gates; no new generated churn appears.

- [ ] **Step 6: Stage exact files, verify, commit, push, and update PR #113**

Run exact `git add` commands for only changed product, tests, Makefile, and documentation. Then run:

```bash
make staged-hygiene-check
git diff --cached --check
git diff --cached --name-only
git commit -m "Document proof readiness reconciliation"
git push origin codex/personal-research-mode-mvp
```

Update draft PR #113 with the defect, state contract, test evidence, commit range, generated-artifact exclusion, and remaining external gates. Confirm exact-head CI passes before claiming the branch safe for review.

---

## Plan Self-Review

- Spec coverage: engine, CLI, Advanced Proof History, selected ticker, fail-closed states, documentation, full gates, artifact hygiene, PR update, and independent readiness are covered.
- Placeholder scan: no deferred runtime behavior or incomplete acceptance step remains in the plan.
- Type consistency: all tasks use the same `ProofReadinessReconciliationRow` and `ProofReadinessReconciliationSummary` interfaces.
- Scope: one read-only proof-interpretation slice; no canonical-data repair, source activation, provider work, readiness rebuild, or external claim.
