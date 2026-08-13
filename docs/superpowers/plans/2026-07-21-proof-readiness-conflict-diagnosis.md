# Proof-Readiness Conflict Diagnosis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make proof-readiness reconciliation require explicit ticker-level historical change evidence and separately diagnose authoritative current blockers without inferring an unknowable historical cause.

**Architecture:** Extend the existing read-only reconciliation module rather than introducing another command. Historical applicability is derived only from structured batch fields, current blocker diagnosis is derived only from saved current inputs, and the two axes are carried through immutable rows, summary counts, CLI/JSON output, and Advanced Proof History cards.

**Tech Stack:** Python 3.12, dataclasses, pandas, pytest, Streamlit AppTest, Make, GitHub Actions.

## Global Constraints

- Current saved readiness remains authoritative.
- Only a valid supporting proof whose normalized `changed_tickers` explicitly contains the ticker is ticker-level supporting evidence.
- Do not parse narrative proof fields to infer source identity, rights, field scope, provenance, payload truth, or historical cause.
- Missing, malformed, placeholder, ambiguous, or scope-only proof fails closed.
- Preserve independent readiness for fundamentals, DCF, share count, price, peer mapping, and peer valuation inputs.
- Keep detailed diagnosis in the existing CLI/JSON contract and Advanced Proof History; do not change Research Desk, Discover, Company Workbench, or Monitor.
- Do not rebuild readiness or write canonical data, proof history, CSV, JSON, reports, screenshots, timing evidence, or bytecode artifacts.
- Keep the existing 18 generated-file modifications unstaged and uncommitted.
- Stage exact files only; never use `git add -A`.
- Keep PR #113 open and draft; push only `codex/personal-research-mode-mvp`.
- Preserve all research-only, no-investment-advice, no-trading, explicit-Q4, EPS split-basis, synthetic-fixture, candidate-context, consensus, and calibration boundaries.

---

## File Structure

- Modify `src/proof_readiness_reconciliation.py`: structured applicability, blocker diagnosis, immutable row/summary fields, loader, JSON, and text rendering.
- Modify `tests/test_proof_readiness_reconciliation.py`: red-green coverage for applicability, blocker diagnosis, output, input isolation, and read-only behavior.
- Modify `src/dashboard.py`: Advanced Proof History summaries only.
- Modify `tests/test_dashboard_helpers.py`: reconciliation-card contract and fixture updates.
- Modify `tests/test_dashboard_render_smoke.py` only if an existing constructor or render marker requires an explicit update.
- Modify `ROADMAP.md`: implemented result and current-snapshot counts.
- Modify `docs/OPERATOR_GUIDE.md`: two-axis interpretation and safe next-review boundary.
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`: continuation rule and next maturity stage.
- Modify `tests/test_public_v1_release_docs.py`: durable documentation contract.

---

### Task 1: Ticker-Level Applicability And Current Blocker Model

**Files:**
- Modify: `tests/test_proof_readiness_reconciliation.py`
- Modify: `src/proof_readiness_reconciliation.py`

**Interfaces:**
- Consumes: `ReviewedBatchProof.changed_tickers`, current ticker readiness, DCF readiness, peer readiness, and canonical fundamentals frames.
- Produces: new immutable row fields `proof_applicability`, `current_blocker_code`, `current_blocker_fields`, `current_blocker_detail`, `next_safe_review`, `historical_payload_status`, and `historical_evidence_limit`.
- Produces: new summary tuples `proof_applicability_counts` and `current_blocker_counts`.
- Preserves: existing state names, ordering, current-readiness authority, and lane independence.

- [ ] **Step 1: Extend test helpers without changing production code**

Update `_proof` so tests can independently set batch scope and explicit changed tickers:

```python
def _proof(
    *,
    tickers: str = "ARCT",
    changed_tickers: str | None = None,
    lane: str = "fundamentals",
    outcome: str = "auto_supported",
    review_date: str = "2026-06-26",
    batch_id: str = "RB-1",
) -> ReviewedBatchProof:
    return ReviewedBatchProof(
        batch_id=batch_id,
        review_date=review_date,
        reviewer="reviewer",
        lane=lane,
        scope="one reviewed scope",
        tickers=tickers,
        command_run="read-only fixture command",
        validation_result="passed",
        preview_result="reviewed",
        apply_result="applied",
        pre_run_readiness_snapshot="before",
        post_run_readiness_snapshot="after",
        changed_readiness_counts="one lane changed",
        changed_tickers=tickers if changed_tickers is None else changed_tickers,
        source_files="reviewed source",
        generated_artifacts_reviewed="excluded",
        final_outcome=outcome,
        notes="fixture proof",
    )
```

Add a canonical fundamentals helper and pass it through `_summary`:

```python
def _fundamentals(**rows: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame([{"ticker": ticker, **values} for ticker, values in rows.items()])


def _summary(*, proofs, ticker, dcf=None, peer=None, fundamentals=None):
    return build_proof_readiness_reconciliation(
        proofs=proofs,
        ticker_readiness=ticker,
        dcf_readiness=dcf if dcf is not None else pd.DataFrame(),
        peer_readiness=peer if peer is not None else pd.DataFrame(),
        fundamentals=fundamentals if fundamentals is not None else pd.DataFrame(),
    )
```

- [ ] **Step 2: Write failing applicability tests**

Add these tests:

```python
def test_scope_only_support_is_not_ticker_level_support():
    summary = _summary(
        proofs=[_proof(tickers="ARCT,ARDX", changed_tickers="ARDX")],
        ticker=_ticker_readiness(
            ARCT={"fundamentals_ready": "False"},
            ARDX={"fundamentals_ready": "False"},
        ),
    )

    arct = _row(summary, "ARCT", "fundamentals")
    ardx = _row(summary, "ARDX", "fundamentals")

    assert arct.proof_applicability == "scope_only_not_supported"
    assert arct.state == "currently_blocked_with_non_supporting_history"
    assert ardx.proof_applicability == "explicit_ticker_change"
    assert ardx.state == "historical_supported_currently_blocked"
    assert dict(summary.conflict_counts_by_lane) == {"fundamentals": 1}


@pytest.mark.parametrize(
    "changed_tickers",
    ["", "-", "none", "n/a", "not available", "unknown", "3289 changed tickers"],
)
def test_placeholder_changed_tickers_cannot_support(changed_tickers):
    summary = _summary(
        proofs=[_proof(changed_tickers=changed_tickers)],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.proof_applicability == "missing_ticker_change_detail"
    assert row.state == "currently_blocked_with_non_supporting_history"


def test_latest_non_supporting_proof_does_not_fall_back_to_older_explicit_support():
    summary = _summary(
        proofs=[
            _proof(batch_id="RB-OLD", review_date="2026-06-25", changed_tickers="ARCT"),
            _proof(batch_id="RB-NEW", review_date="2026-06-26", changed_tickers="-"),
        ],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.latest_batch_id == "RB-NEW"
    assert row.proof_applicability == "missing_ticker_change_detail"
    assert row.state == "currently_blocked_with_non_supporting_history"
```

Import `pytest` at the top of the test file.

- [ ] **Step 3: Run the applicability tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_proof_readiness_reconciliation.py::test_scope_only_support_is_not_ticker_level_support \
  tests/test_proof_readiness_reconciliation.py::test_placeholder_changed_tickers_cannot_support \
  tests/test_proof_readiness_reconciliation.py::test_latest_non_supporting_proof_does_not_fall_back_to_older_explicit_support \
  -q
```

Expected: failures because the row has no `proof_applicability` field and `_summary` passes an unsupported `fundamentals` argument.

- [ ] **Step 4: Write failing current-blocker tests**

Add:

```python
def test_missing_current_canonical_fundamentals_row_is_diagnosed_without_historical_cause_inference():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
        dcf=_dcf_readiness(
            ARCT={
                "missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin, price"
            }
        ),
        fundamentals=_fundamentals(ARDX={"source": "sec_companyfacts"}),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.current_blocker_code == "current_canonical_row_missing"
    assert row.current_blocker_fields == (
        "free_cash_flow",
        "shares_outstanding",
        "revenue",
        "fcf_margin",
    )
    assert row.historical_payload_status == "structured_payload_not_recorded"
    assert "cannot distinguish" in row.historical_evidence_limit.lower()
    assert "yfinance" not in row.current_blocker_detail.lower()


def test_incomplete_current_canonical_fundamentals_row_reports_exact_current_fields():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, revenue, fcf_margin, price"}
        ),
        fundamentals=_fundamentals(
            ARCT={"shares_outstanding": "100", "source": "sec_companyfacts"}
        ),
    )

    row = _row(summary, "ARCT", "fundamentals")
    assert row.current_blocker_code == "current_required_fields_missing"
    assert row.current_blocker_fields == ("free_cash_flow", "revenue", "fcf_margin")
    assert "price" not in row.current_blocker_fields


def test_share_count_diagnosis_reports_only_shares_outstanding():
    summary = _summary(
        proofs=[_proof(lane="share_count")],
        ticker=_ticker_readiness(ARCT={}),
        dcf=_dcf_readiness(
            ARCT={
                "has_shares_outstanding": "False",
                "missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin, price",
            }
        ),
    )

    row = _row(summary, "ARCT", "share_count")
    assert row.current_blocker_code == "current_required_fields_missing"
    assert row.current_blocker_fields == ("shares_outstanding",)


def test_price_and_peer_blockers_remain_independent():
    summary = _summary(
        proofs=[
            _proof(lane="price_history", batch_id="RB-PRICE"),
            _proof(lane="peer_mapping", batch_id="RB-PEER"),
            _proof(lane="peer_valuation_inputs", batch_id="RB-PEER-VAL"),
        ],
        ticker=_ticker_readiness(
            ARCT={"price_ready": "False", "peer_ready": "False"}
        ),
        peer=_peer_readiness(ARCT={"peer_valuation_ready": "False"}),
    )

    assert _row(summary, "ARCT", "price").current_blocker_code == "current_price_missing"
    assert _row(summary, "ARCT", "peer_mapping").current_blocker_code == "current_peer_mapping_missing"
    assert (
        _row(summary, "ARCT", "peer_valuation_inputs").current_blocker_code
        == "current_peer_valuation_inputs_missing"
    )
```

Add an unavailable-input isolation test:

```python
def test_missing_canonical_fundamentals_input_affects_only_dependent_diagnosis():
    summary = _summary(
        proofs=[
            _proof(lane="fundamentals", batch_id="RB-FUND"),
            _proof(lane="price", batch_id="RB-PRICE"),
            _proof(lane="peer_mapping", batch_id="RB-PEER"),
        ],
        ticker=_ticker_readiness(
            ARCT={
                "fundamentals_ready": "False",
                "price_ready": "False",
                "peer_ready": "False",
            }
        ),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"}
        ),
        peer=_peer_readiness(ARCT={"peer_valuation_ready": "False"}),
        fundamentals=pd.DataFrame(),
    )

    assert (
        _row(summary, "ARCT", "fundamentals").current_blocker_code
        == "current_readiness_input_unavailable"
    )
    assert _row(summary, "ARCT", "price").current_blocker_code == "current_price_missing"
    assert _row(summary, "ARCT", "peer_mapping").current_blocker_code == "current_peer_mapping_missing"
```

- [ ] **Step 5: Run the blocker tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py \
  -k 'canonical or share_count_diagnosis or price_and_peer_blockers' -q
```

Expected: failures because the new blocker and evidence-limitation fields do not exist.

- [ ] **Step 6: Add immutable contracts and constants**

In `src/proof_readiness_reconciliation.py`, add:

```python
PLACEHOLDER_TICKER_VALUES = frozenset({"-", "none", "n/a", "na", "not available", "unknown"})
CANONICAL_DCF_FIELDS = (
    "free_cash_flow",
    "shares_outstanding",
    "revenue",
    "fcf_margin",
    "price",
)
FUNDAMENTALS_FIELDS = CANONICAL_DCF_FIELDS[:-1]
HISTORICAL_EVIDENCE_LIMIT = (
    "Historical batch proof cannot distinguish payload removal, readiness-contract change, "
    "source-rights change, field-scope change, or another historical cause."
)
```

Extend `ProofReadinessReconciliationRow`:

```python
    proof_applicability: str
    current_blocker_code: str
    current_blocker_fields: tuple[str, ...]
    current_blocker_detail: str
    next_safe_review: str
    historical_payload_status: str
    historical_evidence_limit: str
```

Extend `ProofReadinessReconciliationSummary`:

```python
    proof_applicability_counts: tuple[tuple[str, int], ...]
    current_blocker_counts: tuple[tuple[str, int], ...]
```

- [ ] **Step 7: Implement normalized explicit applicability**

Replace `_proof_tickers` with a shared normalized-token helper that excludes placeholders and only retains current-universe tickers:

```python
def _ticker_tokens(value: object, valid_tickers: set[str]) -> tuple[str, ...]:
    tokens = (token.strip().upper() for token in re.split(r"[,;]", str(value or "")))
    return tuple(
        dict.fromkeys(
            token
            for token in tokens
            if token
            and token.lower() not in PLACEHOLDER_TICKER_VALUES
            and token in valid_tickers
        )
    )


def _proof_applicability(
    latest_proof: _LatestProof | None,
    *,
    ticker: str,
    valid_tickers: set[str],
) -> str:
    if latest_proof is None:
        return "no_applicable_proof"
    if not latest_proof.review_date_valid:
        return "malformed_review_date"
    outcome = str(latest_proof.proof.final_outcome or "").strip().lower()
    if outcome not in SUPPORTING_OUTCOMES:
        return "non_supporting_outcome"
    changed = _ticker_tokens(latest_proof.proof.changed_tickers, valid_tickers)
    if ticker in changed:
        return "explicit_ticker_change"
    if not changed:
        return "missing_ticker_change_detail"
    return "scope_only_not_supported"
```

Use `_ticker_tokens` for scope matching. Set `supporting = proof_applicability == "explicit_ticker_change"` before calling `_reconciliation_state`.

- [ ] **Step 8: Implement current blocker diagnosis**

Add a frozen internal result:

```python
@dataclass(frozen=True)
class _CurrentBlocker:
    code: str
    fields: tuple[str, ...]
    detail: str
    next_safe_review: str
```

Add helpers that:

- parse `missing_dcf_fields` only into `CANONICAL_DCF_FIELDS` order;
- determine input availability from a nonempty normalized frame containing the required `ticker` and lane columns;
- return `current_readiness_input_unavailable` for fundamentals when the canonical fundamentals input is unavailable, rather than treating an unavailable file as an empty canonical universe;
- use the canonical fundamentals ticker set only to distinguish missing from incomplete payload;
- return `none` for current-ready lanes;
- return `current_readiness_input_unavailable` when the authoritative current field is `None`;
- return lane-specific codes exactly as specified in the design;
- never inspect proof notes, source files, or command text.

Use this exact next-review copy:

```python
NEXT_SAFE_REVIEW = {
    "current_canonical_row_missing": (
        "Obtain and review a permitted source payload for the exact ticker before any import or readiness rebuild."
    ),
    "current_required_fields_missing": (
        "Review the named current fields through the existing source-review and preview-first workflow."
    ),
    "current_price_missing": (
        "Inspect the exact ticker's current price evidence without inferring a provider."
    ),
    "current_peer_mapping_missing": (
        "Review a source-backed relationship through the existing peer evidence contract."
    ),
    "current_peer_valuation_inputs_missing": (
        "Review current peer valuation inputs independently from mapping readiness."
    ),
    "current_readiness_input_unavailable": (
        "Restore or inspect the current saved input before drawing a conclusion."
    ),
    "none": "No current blocker is reported for this lane.",
}
```

For `scope_only_not_supported` or `missing_ticker_change_detail`, prefix the row's safe review with:

```text
Review the proof row; do not reuse it as ticker-level support.
```

- [ ] **Step 9: Wire the canonical frame and summary counts**

Change the builder signature:

```python
def build_proof_readiness_reconciliation(
    *,
    proofs: Sequence[ReviewedBatchProof],
    ticker_readiness: pd.DataFrame,
    dcf_readiness: pd.DataFrame,
    peer_readiness: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> ProofReadinessReconciliationSummary:
```

In the loader, add:

```python
fundamentals=_read_csv(data / "fundamentals.csv"),
```

Populate every new row field. For rows with an applicable proof, use:

```python
historical_payload_status="structured_payload_not_recorded"
historical_evidence_limit=HISTORICAL_EVIDENCE_LIMIT
```

For rows with no proof, use empty strings for those two fields.

Build deterministic summary counters:

```python
proof_applicability_counts = Counter(row.proof_applicability for row in rows)
current_blocker_counts = Counter(row.current_blocker_code for row in rows)
```

Ensure the unavailable early return includes empty tuples for the new summary fields.

- [ ] **Step 10: Run core tests and make them GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py -q
```

Expected: all core reconciliation tests pass.

- [ ] **Step 11: Commit the core model**

Run:

```bash
git add -- src/proof_readiness_reconciliation.py tests/test_proof_readiness_reconciliation.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Diagnose proof readiness conflicts"
```

Expected: only the two named product/test files are committed; no generated artifacts are staged.

---

### Task 2: CLI And JSON Two-Axis Evidence

**Files:**
- Modify: `tests/test_proof_readiness_reconciliation.py`
- Modify: `src/proof_readiness_reconciliation.py`

**Interfaces:**
- Consumes: Task 1 row and summary fields.
- Produces: stable JSON keys `proof_applicability_counts` and `current_blocker_counts`, plus new row fields through `asdict`.
- Produces: text sections `Proof applicability counts` and `Current blocker counts`.
- Preserves: current command name, ticker filtering, top-N behavior, existing payload keys, and read-only guarantee.

- [ ] **Step 1: Write failing JSON and text tests**

Add:

```python
def test_payload_exposes_applicability_and_current_blocker_axes():
    summary = _summary(
        proofs=[_proof(tickers="ARCT,ARDX", changed_tickers="ARDX")],
        ticker=_ticker_readiness(
            ARCT={"fundamentals_ready": "False"},
            ARDX={"fundamentals_ready": "False"},
        ),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"},
            ARDX={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"},
        ),
        fundamentals=_fundamentals(),
    )

    payload = proof_readiness_reconciliation_payload(summary, top_n=20)

    assert payload["proof_applicability_counts"]["scope_only_not_supported"] == 1
    assert payload["proof_applicability_counts"]["explicit_ticker_change"] == 1
    assert payload["current_blocker_counts"]["current_canonical_row_missing"] == 2
    assert payload["rows"][0]["historical_payload_status"] == "structured_payload_not_recorded"
    assert "historical cause" in payload["boundary"].lower()


def test_render_exposes_two_axes_without_claiming_historical_cause():
    summary = _summary(
        proofs=[_proof()],
        ticker=_ticker_readiness(ARCT={"fundamentals_ready": "False"}),
        dcf=_dcf_readiness(
            ARCT={"missing_dcf_fields": "free_cash_flow, shares_outstanding, revenue, fcf_margin"}
        ),
        fundamentals=_fundamentals(),
    )

    rendered = render_proof_readiness_reconciliation(summary, top_n=10)

    assert "Proof applicability counts:" in rendered
    assert "Current blocker counts:" in rendered
    assert "explicit_ticker_change" in rendered
    assert "current_canonical_row_missing" in rendered
    assert "Proof applicability | Current blocker | Next safe review" in rendered
    assert "does not establish the historical cause" in rendered
```

- [ ] **Step 2: Run output tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py \
  -k 'payload_exposes_applicability or render_exposes_two_axes' -q
```

Expected: failures because the new summary keys and rendered sections are absent.

- [ ] **Step 3: Extend JSON payload**

Add to `proof_readiness_reconciliation_payload`:

```python
"proof_applicability_counts": dict(summary.proof_applicability_counts),
"current_blocker_counts": dict(summary.current_blocker_counts),
```

Replace the boundary with:

```python
"Current saved readiness remains authoritative; reconciliation does not restore data, promote readiness, "
"or rewrite proof history. Current blocker diagnosis describes observable saved inputs and does not establish "
"the historical cause."
```

- [ ] **Step 4: Extend text rendering**

After state counts, render both deterministic summary sections. Change the table header to:

```text
Ticker | Lane | Current ready | Latest proof | Review date | Reconciliation state | Proof applicability | Current blocker | Next safe review
```

Render `current_blocker_fields` in parentheses after the blocker code when nonempty. Keep the existing current-readiness and research-only boundaries, then add:

```text
Boundary: current blocker diagnosis describes observable saved inputs; it does not establish the historical cause, source rights, field scope, provenance, payload truth, or commercial use.
```

- [ ] **Step 5: Verify CLI, JSON, filtering, and filesystem immutability**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_proof_readiness_reconciliation.py -q
make proof-readiness-reconciliation TOP_N=20
make proof-readiness-reconciliation TICKERS=ARCT TOP_N=20 JSON=1
git status --short
```

Expected:

- focused tests pass;
- text and JSON expose both axes;
- current saved readiness remains authoritative;
- no file is created or modified by either command;
- only the pre-existing 18 generated modifications remain outside intentional product edits.

- [ ] **Step 6: Commit CLI and JSON evidence**

Run:

```bash
git add -- src/proof_readiness_reconciliation.py tests/test_proof_readiness_reconciliation.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Expose proof conflict diagnosis"
```

---

### Task 3: Advanced Proof History Diagnosis

**Files:**
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `src/dashboard.py`
- Inspect: `tests/test_dashboard_render_smoke.py`; modify it only when the focused RED run proves that an existing constructor or route marker must change

**Interfaces:**
- Consumes: Task 1 summary rows and counts.
- Produces: answer-first global and selected-ticker evidence cards under Proof History.
- Preserves: empty card commands, raw-ledger collapse, primary route order, and current readiness authority.

- [ ] **Step 1: Update the dashboard summary fixture**

Extend `_proof_reconciliation_summary` row construction with:

```python
proof_applicability="explicit_ticker_change",
current_blocker_code="current_canonical_row_missing" if conflict else "none",
current_blocker_fields=("free_cash_flow", "shares_outstanding", "revenue", "fcf_margin") if conflict else (),
current_blocker_detail="No current canonical fundamentals row is present." if conflict else "No current blocker.",
next_safe_review=(
    "Obtain and review a permitted source payload for the exact ticker before any import or readiness rebuild."
    if conflict
    else "No current blocker is reported for this lane."
),
historical_payload_status="structured_payload_not_recorded",
historical_evidence_limit="Historical proof cannot distinguish the historical cause.",
```

Extend summary construction with:

```python
proof_applicability_counts=(("explicit_ticker_change", 1),),
current_blocker_counts=(("current_canonical_row_missing" if conflict else "none", 1),),
```

- [ ] **Step 2: Write failing card tests**

Extend the conflict-card test:

```python
assert "current canonical row missing" in rendered
assert "observable current blocker" in rendered
assert "does not establish the historical cause" in rendered
assert "obtain and review a permitted source payload" in rendered
```

Add:

```python
def test_proof_reconciliation_selected_card_does_not_infer_source_or_historical_cause():
    cards = dashboard.proof_readiness_reconciliation_cards(
        _proof_reconciliation_summary(),
        ticker="ARCT",
    )
    selected = cards[1]
    rendered = " ".join(str(value) for value in selected.values()).lower()

    assert "explicit ticker change" in rendered
    assert "free cash flow" in rendered
    assert "current canonical row missing" in rendered
    assert "yfinance" not in rendered
    assert "source rights changed" not in rendered
    assert selected["command"] == ""
```

- [ ] **Step 3: Run dashboard tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py \
  -k 'proof_reconciliation' -q
```

Expected: failures because the cards do not yet show blocker/applicability fields.

- [ ] **Step 4: Implement concise Advanced cards**

In `proof_readiness_reconciliation_cards`:

- find the largest non-`none` current blocker count from `summary.current_blocker_counts`;
- render labels by replacing underscores with spaces;
- keep the global conflict count unchanged;
- state: `Observable current blockers describe saved inputs; they do not establish the historical cause.`;
- for the selected ticker, combine only that ticker's conflict rows;
- show canonical lanes, applicability labels, blocker labels/fields, and the first deterministic safe next review;
- keep every command empty.

Use this global body shape:

```python
body = (
    "Historical support is not current readiness. Current saved readiness remains authoritative. "
    f"Largest observable current blocker: {largest_blocker_label} ({largest_blocker_count:,}). "
    "Observable current blockers describe saved inputs; they do not establish the historical cause, "
    "restore data, promote readiness, or rewrite proof history."
)
```

Use this selected-ticker body shape:

```python
body = (
    f"Current blocked lane(s): {lanes}. Proof applicability: {applicability}. "
    f"Current blocker(s): {blockers}. Next safe review: {next_safe_review} "
    "Reconciliation itself does not unlock the lane."
)
```

Do not add technical cards to any primary research route.

- [ ] **Step 5: Run focused dashboard and route verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py -q
make research-dashboard-render-smoke
```

Expected: focused dashboard tests pass and all six Research Mode routes render.

- [ ] **Step 6: Commit the Advanced UI slice**

Run:

```bash
git add -- src/dashboard.py tests/test_dashboard_helpers.py
git add -- tests/test_dashboard_render_smoke.py  # only if intentionally changed
make staged-hygiene-check
git diff --cached --check
git commit -m "Show current blockers in Proof History"
```

Expected: no screenshot or generated artifact is staged.

---

### Task 4: Methodology, Roadmap, Continuation Contract, And Release Verification

**Files:**
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `ROADMAP.md`
- Modify: `docs/OPERATOR_GUIDE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: verified Task 1-3 behavior and current-snapshot output.
- Produces: durable operator and continuation rules without turning snapshot counts into permanent claims.
- Preserves: draft PR, generated-artifact exclusion, external dependency boundaries, and release-gate wording.

- [ ] **Step 1: Write the failing documentation contract**

Extend `test_proof_readiness_reconciliation_docs_keep_historical_proof_separate_from_current_state`:

```python
for text in (roadmap, operator, prompt):
    assert "explicit_ticker_change" in text
    assert "current_canonical_row_missing" in text
    assert "does not establish the historical cause" in text.lower()

assert "changed_tickers" in operator
assert "structured per-ticker" in prompt.lower()
assert "future" in roadmap.lower()
```

- [ ] **Step 2: Run the documentation test and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_public_v1_release_docs.py::test_proof_readiness_reconciliation_docs_keep_historical_proof_separate_from_current_state -q
```

Expected: failure because the new two-axis terms are not documented.

- [ ] **Step 3: Capture the verified current snapshot without writing artifacts**

Run:

```bash
make proof-readiness-reconciliation TOP_N=20
make proof-readiness-reconciliation TOP_N=0 JSON=1
```

Record only values directly emitted by the current command. Expected methodological change from the audited starting snapshot is that 44 scope-only rows no longer count as ticker-level supporting conflicts; do not state the exact resulting count until the command proves it.

- [ ] **Step 4: Update ROADMAP.md**

Add the next numbered implemented item stating:

- `changed_tickers` is the only ticker-level support attribution;
- `proof_applicability` and `current_blocker_code` remain independent;
- current observable blockers do not establish historical cause;
- no canonical data, readiness, or history was rewritten;
- current-snapshot counts come from the verified command and are not durable coverage totals;
- a prospective structured per-ticker/per-field proof contract is the next evidence-integrity maturity stage.

- [ ] **Step 5: Update operator and continuation guidance**

In `docs/OPERATOR_GUIDE.md`, explain:

```text
explicit_ticker_change means the latest supporting proof explicitly names the ticker in changed_tickers. Scope membership alone is not ticker-level support.
current_canonical_row_missing and other current blocker codes describe current saved inputs. They do not establish the historical cause.
```

In `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, require future continuations to:

- keep scope-only outcomes non-supporting at ticker level;
- route current blockers to the named safe review;
- never infer historical source, rights, scope, or cause from narrative proof;
- treat a structured per-ticker/per-field proof record as prospective future work, not a retroactive upgrade.

- [ ] **Step 6: Run focused documentation and wording checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_public_v1_release_docs.py \
  tests/test_proof_readiness_reconciliation.py -q
make public-wording-check
git diff --check
```

Expected: all focused tests and wording/whitespace checks pass.

- [ ] **Step 7: Run full local verification**

Run each command and require exit zero:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make commercial-beta-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected:

- full tests pass;
- all six Research Mode routes render;
- public, commercial-beta, release, and pilot packaging gates report their truthful states;
- generated churn remains excluded;
- no completion claim exceeds local evidence.

- [ ] **Step 8: Stage exact documentation/test files and verify**

Run:

```bash
git add -- \
  ROADMAP.md \
  docs/OPERATOR_GUIDE.md \
  docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md \
  tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git diff --cached --name-only
```

Expected: exactly the four named files are staged and all generated files remain unstaged.

- [ ] **Step 9: Commit documentation**

Run:

```bash
git commit -m "Document proof conflict diagnosis"
```

- [ ] **Step 10: Final local branch audit**

Run:

```bash
git status --short --branch
git log -6 --oneline --decorate
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
make diff-hygiene-summary
```

Expected: only the 18 pre-existing generated modifications remain; the branch is ahead only by intentional reviewed commits.

- [ ] **Step 11: Push and update draft PR #113**

Run:

```bash
git push origin codex/personal-research-mode-mvp
gh pr view 113 --json number,state,isDraft,mergeable,headRefName,headRefOid,url,statusCheckRollup
```

Add a PR comment summarizing:

- the false scope-level attribution defect;
- the two-axis contract;
- verified current-snapshot counts;
- focused/full verification;
- zero staged generated artifacts;
- unchanged external source, hosted, reviewer, consensus, calibration, and operating gates.

Keep the PR draft. Do not merge or deploy.

- [ ] **Step 12: Verify exact-head GitHub CI**

Wait for the `Commercial Research Beta` workflow whose `headSha` equals the pushed HEAD. Require `local-engineering-gate` conclusion `SUCCESS` before reporting review safety.

- [ ] **Step 13: Select the next safe maturity lane**

Run the final read-only reconciliation and roadmap audit. The preferred next design subject is the prospective versioned per-ticker/per-field proof contract. Do not implement that new behavior without its own design approval. If a higher-value executable local gap is proven by current evidence, document the choice and its boundary instead.

Report:

1. repository and PR status;
2. product stage;
3. lane audited;
4. root cause and false-attribution count;
5. changes made;
6. tests and gates;
7. commits and push;
8. generated artifacts excluded;
9. external dependencies;
10. remaining maturity gaps;
11. exact next executable step;
12. review safety;
13. whether the overall goal remains active.
