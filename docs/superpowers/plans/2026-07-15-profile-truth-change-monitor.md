# Profile Truth Layer And Research Change Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the selected data profile, freshness, snapshot identity, and matching coverage counts visible everywhere, then add reproducible evidence-backed change detection and a derived research review queue to the existing five-page workflow.

**Architecture:** A central `ProfileContext` resolves selected paths, timestamps, identity, freshness, and counts once for both the dashboard and status commands. A separate generated `ResearchChangeSnapshot` captures comparable selected-profile research state; deterministic comparison emits immutable event candidates, while a small append-only reviewed ledger records only explicit review resolutions. The Review Queue is always derived from unresolved event candidates and ledger outcomes.

**Tech Stack:** Python 3, dataclasses, pathlib, csv/json/hashlib, pandas, Streamlit, pytest, existing Makefile launchers and browser-QA infrastructure.

## Global Constraints

- Data readiness first. Analysis second. Research decision last.
- Research-only; no investment advice, rankings, broker actions, trading, order routing, auto-trading, or direct buy/sell instructions.
- Do not fabricate prices, fundamentals, shares, peers, earnings, estimates, valuation inputs, metrics, events, timestamps, or recommendations.
- Resolve every selected-profile read through `src.paths`; never fall back to another profile.
- Candidate peer and news context cannot promote trusted readiness.
- Generated snapshots, event previews, queues, CSV, JSON, reports, and screenshots remain unstaged by default.
- Use exact file staging only; never use `git add -A`.
- Existing validate, preview, apply, rebuild, and proof gates remain the only route to readiness changes.

---

## File Structure

**Create**

- `src/profile_context.py`: authoritative selected-profile context, identity, dates, freshness, and coverage counts.
- `src/research_change_snapshot.py`: normalized generated comparison snapshot contract and snapshot builder.
- `src/research_change_monitor.py`: deterministic snapshot comparison and immutable event candidates.
- `src/research_review_queue.py`: ledger loading, review outcome resolution, queue prioritization, and render helpers.
- `tests/test_profile_context.py`: profile isolation, timestamps, identity, freshness, and count tests.
- `tests/test_research_change_snapshot.py`: snapshot normalization and generated-write boundary tests.
- `tests/test_research_change_monitor.py`: event detection, evidence states, and deduplication tests.
- `tests/test_research_review_queue.py`: priority, resolution, and no-mutation tests.
- `data/reviewed_research_events.csv`: header-only append-only review-resolution ledger.

**Modify**

- `src/paths.py`: expose public profile labels without duplicating profile resolution.
- `src/dashboard.py`: global trust strip, compact page summaries, selector filter, ticker timeline, Data Health events, Proof History outcomes, and Advanced details.
- `src/project_status.py`: print the shared profile context before selected-profile counts.
- `src/readiness_ops.py`: make root/data/output reads profile-aware and print the shared context.
- `src/trusted_data_pilot.py`: replace its path-only preamble with the shared profile context.
- `src/reviewed_batch.py`: accept selected data/output paths for freshness evaluation.
- `Makefile`: add read-only profile-context, change-snapshot, change-monitor, review-queue, and reviewed-resolution launchers.
- `tests/test_paths.py`: profile label contract.
- `tests/test_dashboard_helpers.py`: trust-strip and page integration contracts.
- `tests/test_dashboard_navigation.py`: no new top-level public page.
- `tests/test_project_status.py`: shared preamble and matching counts.
- `tests/test_readiness_ops.py`: profile-aware context and selected paths.
- `tests/test_trusted_data_pilot.py`: shared context output.
- `tests/test_launchers.py`: new launcher safety and Makefile wiring.
- `tests/test_browser_qa_evidence.py`: visible trust and change-summary markers.
- `README.md`, `ROADMAP.md`, `docs/METHODOLOGY.md`, `docs/PROVENANCE_CONTRACT.md`, `docs/OPERATOR_GUIDE.md`: behavior, boundaries, and operating workflow.

---

### Task 1: Authoritative Profile Context

**Files:**
- Create: `src/profile_context.py`
- Modify: `src/paths.py`
- Create: `tests/test_profile_context.py`
- Modify: `tests/test_paths.py`

**Interfaces:**
- Consumes: `resolve_project_root()`, `resolve_data_profile()`, `resolve_data_dir()`, and `resolve_outputs_dir()` from `src.paths`.
- Produces: `ProfileContext`, `CoverageCounts`, `build_profile_context()`, `render_profile_context_text()`, and `profile_context_payload()`.

- [ ] **Step 1: Write failing profile isolation and count tests**

```python
def test_profile_context_uses_only_selected_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    write_readiness(tmp_path / "data/local/reports/ticker_readiness_report.csv", ticker="LOCAL", price=True)
    write_readiness(tmp_path / "data/reports/ticker_readiness_report.csv", ticker="DEFAULT", price=True)

    context = build_profile_context(project_root=tmp_path, now=utc("2026-07-15T20:00:00Z"))

    assert context.profile_key == "local"
    assert context.profile_label == "Local Research"
    assert context.coverage.total == 1
    assert context.coverage.price_ready == 1
    assert "DEFAULT" not in context.snapshot_inputs
```

```python
def test_missing_local_profile_does_not_fall_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    write_readiness(tmp_path / "data/reports/ticker_readiness_report.csv", ticker="DEFAULT", price=True)

    context = build_profile_context(project_root=tmp_path, now=utc("2026-07-15T20:00:00Z"))

    assert context.freshness_state == "missing"
    assert context.coverage.total == 0
```

- [ ] **Step 2: Run the tests and confirm the missing module failure**

Run: `python3 -m pytest tests/test_profile_context.py tests/test_paths.py -q`

Expected: FAIL because `src.profile_context` and `profile_display_label()` do not exist.

- [ ] **Step 3: Add the profile label contract**

```python
PROFILE_LABELS = {
    "default": "Default",
    "demo": "Demo",
    "local": "Local Research",
}


def profile_display_label(name: str) -> str:
    normalized = str(name or "default").strip().lower()
    if normalized not in PROFILE_LABELS:
        available = ", ".join(sorted(PROFILE_LABELS))
        raise ValueError(f"Unknown data profile '{normalized}'. Choose one of: {available}.")
    return PROFILE_LABELS[normalized]
```

- [ ] **Step 4: Implement immutable context types and selected-profile counts**

```python
@dataclass(frozen=True)
class CoverageCounts:
    total: int = 0
    price_ready: int = 0
    fundamentals_ready: int = 0
    dcf_ready: int = 0
    peer_ready: int = 0


@dataclass(frozen=True)
class ProfileContext:
    profile_key: str
    profile_label: str
    data_dir: Path
    outputs_dir: Path
    source_as_of: str
    readiness_built_at: str
    snapshot_identity: str
    snapshot_identity_short: str
    freshness_state: str
    freshness_message: str
    refresh_command: str
    coverage: CoverageCounts
    lane_source_dates: tuple[tuple[str, str], ...]
    snapshot_inputs: tuple[str, ...]
```

Use `csv.DictReader` and the selected `data_dir / "reports/ticker_readiness_report.csv"`. Count booleans with one shared `_truthy()` helper. Do not inspect `root / "data"` after the profile has been resolved.

- [ ] **Step 5: Add source-date and readiness-time tests**

```python
def test_context_separates_source_date_from_readiness_build_time(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    write_prices(tmp_path / "data/local/prices.csv", date="2026-07-14")
    report = tmp_path / "data/local/reports/ticker_readiness_report.csv"
    write_readiness(report, ticker="NVDA", price=True)
    set_mtime(report, "2026-07-15T19:30:00Z")

    context = build_profile_context(project_root=tmp_path, now=utc("2026-07-15T20:00:00Z"))

    assert context.source_as_of == "2026-07-14"
    assert context.readiness_built_at.startswith("2026-07-15T19:30:00")
```

- [ ] **Step 6: Implement lane source dates and ISO readiness time**

Read valid date columns from the selected canonical files:

```python
SOURCE_DATE_COLUMNS = {
    "prices.csv": ("date",),
    "fundamentals.csv": ("as_of_date", "updated_at"),
    "peers.csv": ("as_of_date", "review_date"),
    "earnings.csv": ("as_of_date", "reported_at"),
    "analyst_estimates.csv": ("as_of_date", "retrieved_at"),
}
```

Invalid, blank, or future-looking malformed values are ignored rather than inferred.

- [ ] **Step 7: Add deterministic identity tests**

```python
def test_local_snapshot_identity_is_stable_and_changes_with_selected_input(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    write_minimum_profile(tmp_path / "data/local")
    first = build_profile_context(project_root=tmp_path).snapshot_identity
    second = build_profile_context(project_root=tmp_path).snapshot_identity
    append_price(tmp_path / "data/local/prices.csv", "NVDA", "2026-07-15", 180.0)
    third = build_profile_context(project_root=tmp_path).snapshot_identity

    assert first == second
    assert third != first
```

```python
def test_demo_identity_uses_tracked_manifest_hashes(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "demo")
    write_demo_manifest(tmp_path / "data/demo/manifest.json", sha256="a" * 64)
    context = build_profile_context(project_root=tmp_path)
    assert context.snapshot_identity == "a" * 64
```

- [ ] **Step 8: Implement identity hashing**

For local/default, hash sorted records containing relative path, missing/present marker, file size, and SHA-256 content digest for canonical files plus the selected readiness report. For demo, parse and deterministically combine the tracked manifest hashes; fail to `missing` if the manifest is invalid.

- [ ] **Step 9: Add current, stale, missing, and mixed freshness tests**

```python
@pytest.mark.parametrize(
    ("sources", "readiness", "expected"),
    [
        ("older", "newer", "current"),
        ("newer", "older", "stale"),
        ("present", "missing", "missing"),
        ("partial", "present", "mixed"),
    ],
)
def test_profile_freshness_states(tmp_path, monkeypatch, sources, readiness, expected):
    arrange_profile_freshness(tmp_path, sources=sources, readiness=readiness)
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    assert build_profile_context(project_root=tmp_path).freshness_state == expected
```

- [ ] **Step 10: Run focused tests and commit**

Run: `python3 -m pytest tests/test_profile_context.py tests/test_paths.py -q`

Expected: PASS.

Commit:

```bash
git add src/profile_context.py src/paths.py tests/test_profile_context.py tests/test_paths.py
git commit -m "Add authoritative data profile context"
```

---

### Task 2: Profile-Aware Freshness And Status Commands

**Files:**
- Modify: `src/reviewed_batch.py`
- Modify: `src/project_status.py`
- Modify: `src/readiness_ops.py`
- Modify: `src/trusted_data_pilot.py`
- Modify: `tests/test_project_status.py`
- Modify: `tests/test_readiness_ops.py`
- Modify: `tests/test_trusted_data_pilot.py`

**Interfaces:**
- Consumes: `build_profile_context()` and `render_profile_context_text()` from Task 1.
- Produces: identical context preambles for every profile-specific status surface.

- [ ] **Step 1: Write failing command-output tests**

```python
def test_project_status_prints_selected_profile_context(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    seed_local_status_profile(tmp_path)
    project_status.main(["--root", str(tmp_path), "--check"])
    output = capsys.readouterr().out
    assert "Profile: Local Research" in output
    assert "Sources through:" in output
    assert "Readiness built:" in output
    assert "Snapshot:" in output
    assert "Coverage: price=" in output
```

Write equivalent assertions for `readiness_ops.main()` and `trusted_data_pilot.main()`.

- [ ] **Step 2: Run focused tests and confirm failures**

Run: `python3 -m pytest tests/test_project_status.py tests/test_readiness_ops.py tests/test_trusted_data_pilot.py -q`

Expected: FAIL because the shared context preamble is absent.

- [ ] **Step 3: Make freshness helpers accept selected paths**

Change signatures that currently derive `root / "data"` or `root / "outputs"`:

```python
def readiness_freshness_status(
    root: Path | str = ".",
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> FreshnessStatus:
    project_root = resolve_project_root(root)
    data_path = resolve_data_dir(data_dir, project_root)
    output_path = resolve_outputs_dir(output_dir, project_root)
```

All callers pass the context-selected paths or rely on profile resolution. No helper may silently reconstruct default paths.

- [ ] **Step 4: Print the shared preamble once per command**

```python
context = build_profile_context(project_root=root, data_dir=data_path, output_dir=output_path)
print(render_profile_context_text(context))
print(render_project_status(payload))
```

Avoid duplicating profile labels or count formatting inside each command.

- [ ] **Step 5: Add a cross-command consistency test**

```python
def test_profile_context_preamble_is_identical_across_status_commands(local_profile):
    outputs = [run_project_status(local_profile), run_readiness_ops(local_profile), run_trusted_candidates(local_profile)]
    preambles = [extract_profile_context_block(output) for output in outputs]
    assert preambles[0] == preambles[1] == preambles[2]
```

- [ ] **Step 6: Run focused tests and commit**

Run: `python3 -m pytest tests/test_project_status.py tests/test_readiness_ops.py tests/test_trusted_data_pilot.py -q`

Expected: PASS.

Commit:

```bash
git add src/reviewed_batch.py src/project_status.py src/readiness_ops.py src/trusted_data_pilot.py tests/test_project_status.py tests/test_readiness_ops.py tests/test_trusted_data_pilot.py
git commit -m "Show selected profile truth in status views"
```

---

### Task 3: Global Dashboard Trust Strip

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_navigation.py`

**Interfaces:**
- Consumes: `ProfileContext` and `build_profile_context()`.
- Produces: `profile_trust_strip_html(context, compact=False)` and `profile_advanced_details(context)`.

- [ ] **Step 1: Write failing HTML contract tests**

```python
def test_profile_trust_strip_shows_profile_dates_freshness_and_counts():
    context = profile_context_fixture(profile_label="Local Research", freshness_state="current")
    rendered = dashboard.profile_trust_strip_html(context)
    assert "Local Research" in rendered
    assert "Sources through" in rendered
    assert "Readiness built" in rendered
    assert "Current" in rendered
    assert "Price-ready" in rendered
    assert "DCF-ready" in rendered
```

```python
def test_public_navigation_remains_five_pages_after_monitor_integration():
    assert dashboard.PUBLIC_PATH_PAGE_TITLES == [
        "Home", "Stock Selector", "Single-Stock Report", "Data Health", "Proof History"
    ]
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py -q`

Expected: FAIL because the trust-strip helper does not exist.

- [ ] **Step 3: Implement escaped, responsive trust-strip HTML**

```python
def profile_trust_strip_html(context: ProfileContext, *, compact: bool = False) -> str:
    compact_class = " compact" if compact else ""
    coverage = context.coverage
    return (
        f"<section class='profile-trust-strip{compact_class}' aria-label='Selected data profile and freshness'>"
        f"<strong>{html.escape(context.profile_label)}</strong>"
        f"<span>Sources through {html.escape(context.source_as_of or 'Unavailable')}</span>"
        f"<span>Readiness built {html.escape(context.readiness_built_at or 'Unavailable')}</span>"
        f"<span class='freshness {html.escape(context.freshness_state)}'>{html.escape(context.freshness_state.title())}</span>"
        f"<span>Price-ready {coverage.price_ready:,}/{coverage.total:,}</span>"
        f"<span>DCF-ready {coverage.dcf_ready:,}/{coverage.total:,}</span>"
        "</section>"
    )
```

Add CSS with wrapping grid/flex constraints, no viewport-scaled fonts, and a phone breakpoint that keeps profile and freshness visible.

- [ ] **Step 4: Render the context once in both public and operator shells**

Build context after query mode/profile resolution and before `render_public_app_shell()` or `render_app_header()`. Pass it into both render paths rather than rebuilding it per page section.

- [ ] **Step 5: Add Advanced detail tests**

```python
def test_profile_advanced_details_keep_paths_and_hash_out_of_compact_strip():
    context = profile_context_fixture(snapshot_identity="f" * 64, data_dir=Path("/private/data/local"))
    compact = dashboard.profile_trust_strip_html(context)
    details = dashboard.profile_advanced_details(context)
    assert "/private/data/local" not in compact
    assert "f" * 64 not in compact
    assert details["Snapshot identity"] == "f" * 64
```

- [ ] **Step 6: Run focused tests and commit**

Run: `python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py -q`

Expected: PASS.

Commit:

```bash
git add src/dashboard.py tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py
git commit -m "Add global profile freshness trust strip"
```

---

### Task 4: Comparable Research Change Snapshots

**Files:**
- Create: `src/research_change_snapshot.py`
- Create: `tests/test_research_change_snapshot.py`

**Interfaces:**
- Consumes: `ProfileContext` from Task 1 and selected-profile canonical/readiness files.
- Produces: `ResearchChangeSnapshot`, `TickerResearchState`, `build_research_change_snapshot()`, `write_research_change_snapshot()`, and `load_research_change_snapshot()`.

- [ ] **Step 1: Write failing normalization tests**

```python
def test_snapshot_contains_only_selected_profile_state(local_profile):
    snapshot = build_research_change_snapshot(project_root=local_profile.root)
    assert snapshot.profile_key == "local"
    assert [row.ticker for row in snapshot.tickers] == ["NVDA"]
    assert snapshot.snapshot_identity == local_profile.context.snapshot_identity
```

```python
def test_snapshot_normalizes_readiness_fundamentals_filings_and_nowcast(local_profile):
    snapshot = build_research_change_snapshot(project_root=local_profile.root)
    state = snapshot.tickers[0]
    assert dict(state.readiness)["dcf_ready"] == "true"
    assert dict(state.fundamentals)["shares_outstanding"] == "24000000000"
    assert state.latest_filing_accession == "0001045810-26-000021"
    assert state.nowcast_consensus_ids == ("NVDA|FY2027-Q2|2026-07-15T20:00:00Z",)
```

- [ ] **Step 2: Run tests and confirm missing module failure**

Run: `python3 -m pytest tests/test_research_change_snapshot.py -q`

Expected: FAIL because the snapshot module does not exist.

- [ ] **Step 3: Implement immutable normalized types**

```python
@dataclass(frozen=True)
class TickerResearchState:
    ticker: str
    readiness: tuple[tuple[str, str], ...]
    fundamentals: tuple[tuple[str, str], ...]
    latest_price_date: str
    latest_filing_accession: str
    latest_filing_date: str
    nowcast_consensus_ids: tuple[str, ...]
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class ResearchChangeSnapshot:
    schema_version: str
    profile_key: str
    snapshot_identity: str
    captured_at: str
    source_as_of: str
    tickers: tuple[TickerResearchState, ...]
```

Store key/value sequences sorted and serialized as JSON objects only at the file boundary.

- [ ] **Step 4: Implement selected-profile loaders**

Load only files under `context.data_dir` and `context.outputs_dir`. Missing optional files produce empty fields and diagnostics; they never trigger reads from default paths.

- [ ] **Step 5: Add generated-write boundary tests**

```python
def test_snapshot_write_requires_explicit_output_and_never_writes_source_data(local_profile, tmp_path):
    snapshot = build_research_change_snapshot(project_root=local_profile.root)
    destination = tmp_path / "outputs/local/research_changes/snapshot.json"
    written = write_research_change_snapshot(snapshot, destination)
    assert written == destination
    assert destination.exists()
    assert not (local_profile.data_dir / "research_changes.json").exists()
```

- [ ] **Step 6: Run focused tests and commit**

Run: `python3 -m pytest tests/test_research_change_snapshot.py tests/test_profile_context.py -q`

Expected: PASS.

Commit:

```bash
git add src/research_change_snapshot.py tests/test_research_change_snapshot.py
git commit -m "Add comparable research change snapshots"
```

---

### Task 5: Deterministic Research Change Events

**Files:**
- Create: `src/research_change_monitor.py`
- Create: `tests/test_research_change_monitor.py`

**Interfaces:**
- Consumes: two `ResearchChangeSnapshot` values with the same profile.
- Produces: `ResearchChangeEvent`, `compare_research_snapshots()`, `event_id_for()`, and `render_change_monitor()`.

- [ ] **Step 1: Write failing transition tests**

```python
def test_monitor_detects_readiness_loss_and_gain():
    before = snapshot_with("NVDA", dcf_ready=True, peer_ready=False)
    after = snapshot_with("NVDA", dcf_ready=False, peer_ready=True)
    events = compare_research_snapshots(before, after)
    assert event(events, "dcf_readiness_changed").current_value == "false"
    assert event(events, "peer_readiness_changed").current_value == "true"
```

```python
def test_monitor_detects_filing_and_source_field_revisions():
    before = snapshot_with("NVDA", accession="A1", shares="100")
    after = snapshot_with("NVDA", accession="A2", shares="105")
    events = compare_research_snapshots(before, after)
    assert {row.subtype for row in events} >= {"sec_filing_arrived", "shares_outstanding_revised"}
```

- [ ] **Step 2: Add fail-closed comparison tests**

```python
def test_monitor_rejects_cross_profile_comparison():
    with pytest.raises(ValueError, match="same selected profile"):
        compare_research_snapshots(snapshot(profile="demo"), snapshot(profile="local"))


def test_monitor_returns_baseline_missing_without_fabricating_events():
    result = compare_optional_snapshots(None, snapshot(profile="local"))
    assert result.status == "baseline_missing"
    assert result.events == ()
```

- [ ] **Step 3: Run tests and confirm failure**

Run: `python3 -m pytest tests/test_research_change_monitor.py -q`

Expected: FAIL because the monitor module does not exist.

- [ ] **Step 4: Implement the immutable event contract**

```python
@dataclass(frozen=True)
class ResearchChangeEvent:
    event_id: str
    ticker: str
    family: str
    subtype: str
    prior_value: str
    current_value: str
    source: str
    source_ref: str
    source_published_at: str
    retrieved_at: str
    detected_at: str
    profile_key: str
    prior_snapshot_identity: str
    current_snapshot_identity: str
    evidence_status: str
    materiality: str
    suggested_research_task: str
```

- [ ] **Step 5: Implement stable IDs and detector registry**

```python
def event_id_for(event_fields: Mapping[str, str]) -> str:
    identity = "\x1f".join(event_fields[key] for key in EVENT_ID_FIELDS)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
```

Register explicit detectors for readiness, filing accession, fundamentals/share count, DCF availability, price/momentum readiness, Nowcast consensus IDs, stale, and blocked transitions. No free-text model or inferred numeric adjustment is used.

- [ ] **Step 6: Add stable deduplication and wording tests**

```python
def test_event_ids_are_stable_and_unique():
    first = compare_research_snapshots(before_snapshot(), after_snapshot())
    second = compare_research_snapshots(before_snapshot(), after_snapshot())
    assert [row.event_id for row in first] == [row.event_id for row in second]
    assert len({row.event_id for row in first}) == len(first)


def test_suggested_tasks_contain_no_investment_or_execution_language():
    rendered = " ".join(row.suggested_research_task for row in all_event_fixtures()).lower()
    assert not re.search(r"\b(buy|sell|hold|outperform|underperform|order|trade)\b", rendered)
```

- [ ] **Step 7: Run focused tests and commit**

Run: `python3 -m pytest tests/test_research_change_monitor.py tests/test_research_change_snapshot.py -q`

Expected: PASS.

Commit:

```bash
git add src/research_change_monitor.py tests/test_research_change_monitor.py
git commit -m "Add evidence-backed research change detection"
```

---

### Task 6: Append-Only Review Outcomes And Research Review Queue

**Files:**
- Create: `src/research_review_queue.py`
- Create: `tests/test_research_review_queue.py`
- Create: `data/reviewed_research_events.csv`

**Interfaces:**
- Consumes: event candidates from Task 5 and reviewed ledger rows.
- Produces: `ResearchReviewItem`, `build_research_review_queue()`, `append_review_resolution()`, `load_review_resolutions()`, and `render_research_review_queue()`.

- [ ] **Step 1: Create the exact ledger schema in a failing schema test**

```python
REVIEW_LEDGER_COLUMNS = (
    "schema_version", "event_id", "profile_key", "ticker", "review_status",
    "reviewed_at", "reviewer", "resolution_note", "source_ref",
    "prior_snapshot_identity", "current_snapshot_identity",
)


def test_review_ledger_header_matches_contract():
    assert read_header(Path("data/reviewed_research_events.csv")) == list(REVIEW_LEDGER_COLUMNS)
```

- [ ] **Step 2: Write failing deterministic priority tests**

```python
def test_queue_prioritizes_lost_readiness_before_new_context():
    queue = build_research_review_queue([
        event_fixture(subtype="momentum_readiness_changed", materiality="context"),
        event_fixture(subtype="dcf_readiness_changed", prior_value="true", current_value="false"),
        event_fixture(subtype="sec_filing_arrived"),
    ], resolutions=[])
    assert [row.event.subtype for row in queue] == [
        "dcf_readiness_changed", "sec_filing_arrived", "momentum_readiness_changed"
    ]
```

- [ ] **Step 3: Write failing append-only resolution tests**

```python
def test_review_resolution_appends_and_does_not_mutate_source_files(tmp_path):
    source = tmp_path / "data/local/fundamentals.csv"
    source.write_text("ticker,revenue\nNVDA,1\n", encoding="utf-8")
    before = source.read_bytes()
    ledger = tmp_path / "data/reviewed_research_events.csv"
    append_review_resolution(ledger, resolution_fixture(status="reviewed_supported"))
    append_review_resolution(ledger, resolution_fixture(status="still_blocked", reviewed_at="2026-07-16T00:00:00Z"))
    assert source.read_bytes() == before
    assert len(list(csv.DictReader(ledger.open()))) == 2
```

- [ ] **Step 4: Run tests and confirm failure**

Run: `python3 -m pytest tests/test_research_review_queue.py -q`

Expected: FAIL because the queue module and ledger do not exist.

- [ ] **Step 5: Implement queue and latest-resolution semantics**

Resolve duplicate event IDs by the latest valid `reviewed_at`, while preserving all ledger rows. Exclude resolved statuses from the open queue except `still_blocked` and `intentionally_deferred`, which remain visible with their wait condition.

```python
OPEN_STATUSES = {"open", "still_blocked", "intentionally_deferred"}
RESOLVED_STATUSES = {"reviewed_no_change", "reviewed_supported", "skipped", "excluded"}
```

- [ ] **Step 6: Implement deterministic priority keys**

```python
PRIORITY_BY_SUBTYPE = {
    "dcf_readiness_changed": 40,
    "fundamentals_readiness_changed": 40,
    "input_became_stale": 10,
    "sec_filing_arrived": 20,
    "shares_outstanding_revised": 30,
    "fundamentals_revised": 30,
    "nowcast_consensus_changed": 30,
    "readiness_improved": 40,
    "momentum_readiness_changed": 50,
}


def priority_for_event(event: ResearchChangeEvent) -> int:
    if event.subtype in {"dcf_readiness_changed", "fundamentals_readiness_changed"}:
        if event.prior_value == "true" and event.current_value == "false":
            return 10
    return PRIORITY_BY_SUBTYPE.get(event.subtype, 60)
```

Tie break by materiality, source publication time, detection time, ticker, and event ID.

- [ ] **Step 7: Run focused tests and commit**

Run: `python3 -m pytest tests/test_research_review_queue.py tests/test_research_change_monitor.py -q`

Expected: PASS.

Commit:

```bash
git add src/research_review_queue.py tests/test_research_review_queue.py data/reviewed_research_events.csv
git commit -m "Add deterministic research review queue"
```

---

### Task 7: Safe CLI And Makefile Workflow

**Files:**
- Modify: `src/research_change_snapshot.py`
- Modify: `src/research_change_monitor.py`
- Modify: `src/research_review_queue.py`
- Modify: `Makefile`
- Modify: `tests/test_launchers.py`

**Interfaces:**
- Consumes: Task 4-6 builders and renderers.
- Produces Make targets: `profile-context`, `research-change-snapshot`, `research-change-monitor`, `research-review-queue`, and `research-event-review-record`.

- [ ] **Step 1: Write failing launcher contract tests**

```python
def test_research_change_launchers_exist_and_are_read_only_by_default():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    assert "profile-context:" in makefile
    assert "research-change-snapshot:" in makefile
    assert "research-change-monitor:" in makefile
    assert "research-review-queue:" in makefile
    monitor = makefile_section(makefile, "research-change-monitor")
    assert "imports-apply" not in monitor
    assert "git add" not in monitor
    assert "git push" not in monitor
```

- [ ] **Step 2: Run launcher tests and confirm failure**

Run: `python3 -m pytest tests/test_launchers.py -q`

Expected: FAIL because the targets do not exist.

- [ ] **Step 3: Add explicit CLI parsers**

Use these command contracts:

```text
python3 -m src.profile_context --root . --json
python3 -m src.research_change_snapshot --root . --output outputs/local/research_changes/snapshot.json
python3 -m src.research_change_monitor --before /tmp/stock-research-change-before.json --after /tmp/stock-research-change-after.json --json
python3 -m src.research_review_queue --before /tmp/stock-research-change-before.json --after /tmp/stock-research-change-after.json --top-n 25
python3 -m src.research_review_queue --record --event-id 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef --status reviewed_no_change --reviewed-at 2026-07-15T23:59:59Z --reviewer codex-review --resolution-note "Reviewed source evidence; no readiness mutation required."
```

The snapshot command is the only generated-write command. Monitor and queue commands are read-only. Recording requires every ledger field and appends one reviewed row.

- [ ] **Step 4: Wire Make targets with explicit variables**

```make
profile-context:
	@python3 -m src.profile_context --root .

research-change-snapshot:
	@python3 -m src.research_change_snapshot --root . $(if $(OUTPUT),--output "$(OUTPUT)",)

research-change-monitor:
	@python3 -m src.research_change_monitor --before "$(BEFORE)" --after "$(AFTER)"

research-review-queue:
	@python3 -m src.research_review_queue --before "$(BEFORE)" --after "$(AFTER)" --top-n $(or $(TOP_N),25)
```

- [ ] **Step 5: Test missing-baseline and cross-profile CLI outcomes**

Expected behavior:

- missing baseline exits successfully with `baseline_missing` and no events
- malformed snapshot exits nonzero with a clear schema error
- cross-profile comparison exits nonzero with no queue
- no command changes source CSVs or readiness artifacts

- [ ] **Step 6: Run tests and commit**

Run: `python3 -m pytest tests/test_launchers.py tests/test_research_change_snapshot.py tests/test_research_change_monitor.py tests/test_research_review_queue.py -q`

Expected: PASS.

Commit:

```bash
git add Makefile src/profile_context.py src/research_change_snapshot.py src/research_change_monitor.py src/research_review_queue.py tests/test_launchers.py
git commit -m "Add safe research change workflow commands"
```

---

### Task 8: Existing Five-Page Workflow Integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_navigation.py`
- Modify: `tests/test_browser_qa_evidence.py`

**Interfaces:**
- Consumes: selected `ProfileContext`, event candidates, and `ResearchReviewItem` rows.
- Produces compact summary helpers for Home, Stock Selector, Single-Stock Report, Data Health, and Proof History.

- [ ] **Step 1: Write failing page-contract tests**

```python
def test_home_change_summary_has_one_answer_and_one_action():
    summary = dashboard.research_change_home_summary(queue_fixture())
    assert summary["title"] == "Changed since your last review"
    assert summary["primary_action"] == "Review 2 evidence changes"
    assert "buy" not in str(summary).lower()


def test_ticker_timeline_filters_to_selected_ticker():
    rows = dashboard.ticker_change_timeline(event_fixtures("NVDA", "AMD"), ticker="NVDA")
    assert {row["ticker"] for row in rows} == {"NVDA"}
```

- [ ] **Step 2: Add selector needs-review filter tests**

```python
def test_selector_needs_review_filter_is_derived_from_open_events():
    filtered = dashboard.filter_selector_needs_review(selector_frame(), open_event_ids_by_ticker={"NVDA": 2})
    assert filtered["ticker"].tolist() == ["NVDA"]
    assert filtered.iloc[0]["change_reason"]
```

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py -q`

Expected: FAIL because change-summary helpers do not exist.

- [ ] **Step 4: Implement compact integration helpers outside the render body**

Add pure helpers for:

- `research_change_home_summary()`
- `filter_selector_needs_review()`
- `ticker_change_timeline()`
- `data_health_change_summary()`
- `proof_history_event_outcomes()`

Keep these helpers free of Streamlit calls and test them directly.

- [ ] **Step 5: Integrate without adding a public route**

Render:

- Home summary after the profile trust strip
- selector filter alongside existing readiness filters
- ticker timeline after the selected-ticker answer and before Advanced report details
- Data Health event summary before operator proof controls
- Proof History outcomes before raw ledger rows

Raw event candidates, paths, hashes, and commands remain inside one Advanced expander.

- [ ] **Step 6: Add empty, stale, and missing-baseline UI tests**

```python
@pytest.mark.parametrize("status", ["no_changes", "stale", "baseline_missing"])
def test_change_summary_states_do_not_claim_detected_changes(status):
    rendered = dashboard.research_change_state_html(change_state_fixture(status))
    assert "evidence-backed changes detected" not in rendered.lower()
    assert "investment recommendation" not in rendered.lower()
```

- [ ] **Step 7: Update browser-QA markers**

Require the selected profile label and either `Changed since your last review`, `No evidence-backed changes`, or `Change baseline unavailable` on the relevant routes. Do not require raw ledger content in the first viewport.

- [ ] **Step 8: Run focused tests and commit**

Run: `python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py tests/test_browser_qa_evidence.py -q`

Expected: PASS.

Commit:

```bash
git add src/dashboard.py tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py tests/test_browser_qa_evidence.py
git commit -m "Integrate research changes into guided workflow"
```

---

### Task 9: Documentation, Roadmap, And Provenance

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/OPERATOR_GUIDE.md`

**Interfaces:**
- Consumes: final command names and UI behavior from Tasks 1-8.
- Produces: one consistent user and operator explanation.

- [ ] **Step 1: Update README first-review copy**

Document:

- how to identify the selected profile and freshness
- what snapshot identity does and does not prove
- how `Changed since last review` is derived
- why the queue contains research tasks rather than recommendations

- [ ] **Step 2: Update the authoritative roadmap**

Move the Profile Truth Layer and local Change Monitor/Review Queue to completed milestones only after verification. Keep hosted alerts and scheduled mutation under Later.

- [ ] **Step 3: Update methodology and provenance contracts**

State explicitly:

- events require comparable before/after evidence
- source publication, retrieval, and detection times are separate
- event identity is deterministic
- resolution does not mutate readiness
- candidate context cannot become trusted evidence through the monitor

- [ ] **Step 4: Update operator workflow**

Document exact sequence:

```text
make profile-context
STOCK_RESEARCH_DATA_PROFILE=local make research-change-snapshot OUTPUT=outputs/local/research_changes/snapshot-current.json
make research-change-monitor BEFORE=outputs/local/research_changes/snapshot-prior.json AFTER=outputs/local/research_changes/snapshot-current.json
make research-review-queue BEFORE=outputs/local/research_changes/snapshot-prior.json AFTER=outputs/local/research_changes/snapshot-current.json TOP_N=25
```

State that generated snapshots and queue exports remain unstaged.

- [ ] **Step 5: Run wording and diff checks, then commit**

Run:

```bash
make public-wording-check
git diff --check
```

Expected: both pass.

Commit:

```bash
git add README.md ROADMAP.md docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md docs/OPERATOR_GUIDE.md
git commit -m "Document profile truth and research change workflow"
```

---

### Task 10: Full Verification And Release Audit

**Files:**
- No implementation files unless a test exposes a defect.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: completion evidence for the approved design.

- [ ] **Step 1: Run focused feature suites**

```bash
python3 -m pytest tests/test_profile_context.py tests/test_paths.py tests/test_project_status.py tests/test_readiness_ops.py tests/test_trusted_data_pilot.py tests/test_research_change_snapshot.py tests/test_research_change_monitor.py tests/test_research_review_queue.py tests/test_dashboard_helpers.py tests/test_dashboard_navigation.py tests/test_browser_qa_evidence.py tests/test_launchers.py -q
```

Expected: PASS with no skipped feature-contract tests.

- [ ] **Step 2: Verify all three profiles**

```bash
STOCK_RESEARCH_DATA_PROFILE=default make profile-context
STOCK_RESEARCH_DATA_PROFILE=demo make profile-context
STOCK_RESEARCH_DATA_PROFILE=local make profile-context
```

Expected: each prints a distinct profile label, selected paths, selected identity, freshness, and selected counts; no profile prints another profile's paths or counts.

- [ ] **Step 3: Verify the generated comparison workflow**

Create two generated snapshots in a temporary directory from controlled test fixtures, compare them, and confirm stable events and queue order. Confirm no canonical data file changes by comparing `git status --short` before and after.

- [ ] **Step 4: Run the full suite and public gates**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make browser-qa-evidence
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all commands exit zero. Browser QA must cover desktop and mobile public routes with the profile trust marker and compact change-state marker.

- [ ] **Step 5: Inspect staging hygiene**

Stage only intentional source, docs, tests, Makefile, and the header-only reviewed ledger. Then run:

```bash
make staged-hygiene-check
git diff --cached --check
git diff --cached --name-only
```

Expected: no generated snapshots, event previews, queue exports, broad CSV/JSON/report churn, or screenshots are staged.

- [ ] **Step 6: Completion audit against the design**

For each acceptance criterion in `docs/superpowers/specs/2026-07-15-profile-truth-change-monitor-design.md`, cite the implementing file, focused test, and live command/browser evidence. Treat any missing or indirect evidence as incomplete.

- [ ] **Step 7: Close verification without hiding failed work**

If verification exposes a defect, return to the task that owns the failing behavior, add a regression test, implement the correction, rerun that task's focused checks, and commit only that task's exact files. Do not create a catch-all integration commit. Do not push unless the user explicitly requests it.
