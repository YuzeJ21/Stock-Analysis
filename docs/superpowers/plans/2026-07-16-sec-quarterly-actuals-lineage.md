# SEC Quarterly Actuals Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preview-only SEC evidence pipeline that stages correctly identified Q1-Q4 Revenue and diluted GAAP EPS actuals for the five-company semiconductor Earnings Nowcast pilot without cumulative facts, period relabeling, split leakage, quarter gaps, or inferred Q4 values.

**Architecture:** A focused `earnings_nowcast_sec_actuals` module normalizes raw Companyfacts records, establishes fiscal-quarter lineage from original current-quarter filings, preserves revisions, discovers explicit Q4 earnings-release exhibits, and writes only onboarding-compatible temporary evidence plus audit output. Existing readiness and model modules gain metric-specific continuity and split-basis gates; existing onboarding remains the final validate/preview boundary.

**Tech Stack:** Python 3.12, standard-library dataclasses/HTMLParser/urllib, existing SEC provider cache APIs, CSV/JSON, pytest, Make.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, or direct buy/sell instructions.
- Never infer Revenue, EPS, Q4 values, fiscal periods, consensus, probabilities, or recommendations.
- Q4 must come from an explicit result table in an SEC-filed primary-source exhibit; annual-minus-nine-month arithmetic is prohibited.
- Historical evidence is append-only and cutoff-aware; later revisions never overwrite earlier evidence.
- Revenue and EPS readiness remain independent.
- Generated SEC staging CSV/JSON/rejected-row artifacts stay outside default staging.
- No automatic apply path is added.
- Historical point-in-time consensus remains an external input and must continue to block packet generation when absent.
- Numerical Beat/Miss probability remains hidden until at least 100 valid events pass calibration gates.

## File Map

- Create `src/earnings_nowcast_sec_actuals.py`: normalized fact types, Q1-Q3 lineage, SEC filing-index/exhibit parsing, Q4 extraction, staging CLI, and audit payload.
- Create `tests/test_earnings_nowcast_sec_actuals.py`: fixture-driven parser, lineage, revision, Q4, cutoff, and output-boundary tests.
- Modify `src/earnings_nowcast_readiness.py`: metric-specific fiscal-quarter continuity and split-basis eligibility.
- Modify `src/earnings_nowcast_model.py`: consume only the contiguous canonical metric window.
- Modify `tests/test_earnings_nowcast_readiness.py`: missing-quarter and split-basis regression tests.
- Modify `tests/test_earnings_nowcast_model.py`: prove no Q3-to-next-Q1 sequential calculation.
- Modify `tests/test_earnings_nowcast_backtest.py`: prove continuity and revisions remain cutoff-safe in walk-forward evaluation.
- Modify `Makefile`: add the narrow, read-only `earnings-nowcast-sec-actuals-stage` launcher.
- Modify `tests/test_launchers.py`: lock launcher arguments and no-apply boundary.
- Modify `docs/EARNINGS_NOWCAST_PILOT.md`, `docs/METHODOLOGY.md`, `docs/PROVENANCE_CONTRACT.md`, and `ROADMAP.md`: document actuals lineage, Q4, split, continuity, and remaining consensus dependency.

---

### Task 1: Normalize SEC facts and extract Q1-Q3 fiscal-quarter lineage

**Files:**
- Create: `src/earnings_nowcast_sec_actuals.py`
- Create: `tests/test_earnings_nowcast_sec_actuals.py`

**Interfaces:**
- Consumes: raw SEC Companyfacts JSON and an ISO cutoff timestamp.
- Produces: `normalize_sec_duration_facts(payload: Mapping[str, object]) -> tuple[SecDurationFact, ...]`.
- Produces: `extract_q1_q3_lineage(ticker: str, payload: Mapping[str, object], *, cutoff: str, retrieved_at: str) -> ExtractionResult`.
- `ExtractionResult.rows` contains onboarding `QuarterlyActual` values; `ExtractionResult.audit_rows` records accepted and rejected source facts.

- [ ] **Step 1: Write failing normalization and cumulative-fact tests**

Create fixtures directly in `tests/test_earnings_nowcast_sec_actuals.py` so one Q3 accession contains:

```python
def _fact(*, val, start, end, filed="2026-06-25", fy=2026, fp="Q3", frame=None):
    return {
        "val": val,
        "start": start,
        "end": end,
        "filed": filed,
        "form": "10-Q",
        "accn": "0000000000-26-000001",
        "fy": fy,
        "fp": fp,
        "frame": frame,
    }


def test_q3_lineage_keeps_aligned_quarter_and_rejects_ytd_and_comparative_period():
    payload = companyfacts_fixture(
        revenue=[
            _fact(val=30, start="2025-08-29", end="2026-05-28"),
            _fact(val=12, start="2026-02-27", end="2026-05-28", frame="CY2026Q2"),
            _fact(val=8, start="2025-02-28", end="2025-05-29", frame="CY2025Q2"),
        ],
        eps=[
            _fact(val=3.0, start="2025-08-29", end="2026-05-28"),
            _fact(val=1.2, start="2026-02-27", end="2026-05-28", frame="CY2026Q2"),
            _fact(val=0.8, start="2025-02-28", end="2025-05-29", frame="CY2025Q2"),
        ],
    )

    result = extract_q1_q3_lineage("SYN1", payload, cutoff=CUTOFF, retrieved_at=RETRIEVED_AT)

    assert [(row.fiscal_period, row.revenue_actual, row.eps_actual) for row in result.rows] == [
        ("2026-Q3", 12.0, 1.2)
    ]
    assert {row.state for row in result.audit_rows} >= {
        "accepted_explicit_quarter",
        "cumulative_fact_rejected",
        "comparative_period_relabelled",
    }
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m pytest tests/test_earnings_nowcast_sec_actuals.py::test_q3_lineage_keeps_aligned_quarter_and_rejects_ytd_and_comparative_period -q
```

Expected: collection/import failure because `src.earnings_nowcast_sec_actuals` does not exist.

- [ ] **Step 3: Implement normalized fact types and deterministic Q1-Q3 selection**

Implement these public types and functions:

```python
@dataclass(frozen=True)
class SecDurationFact:
    taxonomy: str
    concept: str
    unit: str
    value: float
    start: str
    end: str
    filed: str
    form: str
    accession: str
    fiscal_year: int
    fiscal_period: str
    frame: str

    @property
    def duration_days(self) -> int:
        return (date.fromisoformat(self.end) - date.fromisoformat(self.start)).days


@dataclass(frozen=True)
class ExtractionAuditRow:
    ticker: str
    state: str
    metric: str
    fiscal_period: str
    source_ref: str
    detail: str


@dataclass(frozen=True)
class ExtractionResult:
    rows: tuple[QuarterlyActual, ...]
    audit_rows: tuple[ExtractionAuditRow, ...]


def normalize_sec_duration_facts(payload: Mapping[str, object]) -> tuple[SecDurationFact, ...]: ...


def extract_q1_q3_lineage(
    ticker: str,
    payload: Mapping[str, object],
    *,
    cutoff: str,
    retrieved_at: str,
) -> ExtractionResult: ...
```

Implementation rules:

- accept only `10-Q` and `10-Q/A` numeric duration facts;
- accept Revenue concepts in the design's priority order and diluted EPS only;
- accept 60-120-day quarter durations;
- choose the latest `end` within each accession/`fy`/`fp` as the current quarter;
- pair metrics only when accession/start/end/filed/`fy`/`fp` match;
- reject conflicting frame or concept values;
- construct the SEC accession URL from CIK and accession;
- set date-only Companyfacts `reported_at` metadata to `23:59:59Z` on the filed date and reject rows after cutoff;
- preserve a metric-only partial row when just Revenue or EPS is proven.

- [ ] **Step 4: Add missing-frame, concept-conflict, partial-row, and cutoff tests**

Add tests proving:

```python
assert missing_frame_result.rows[0].revenue_actual == 12.0
assert ambiguous_result.rows[0].revenue_actual is None
assert revenue_only_result.rows[0].eps_actual is None
assert post_cutoff_result.rows == ()
assert "post_cutoff_rejected" in {row.state for row in post_cutoff_result.audit_rows}
```

Add a two-filing lineage test where the original Q2 filing establishes
`2025-Q2` for a period end and a later Q3 filing presents that same period as
comparative data with a different SEC `fy`/`fp`. Assert that the later row keeps
the original `2025-Q2` identity and becomes a revision candidate instead of
being relabelled from the later filing's metadata. Add a fail-closed case where
no original current-quarter filing can establish the comparative period.

- [ ] **Step 5: Run the Task 1 tests and verify GREEN**

Run:

```bash
python3 -m pytest tests/test_earnings_nowcast_sec_actuals.py -q
```

Expected: all Task 1 tests pass.

- [ ] **Step 6: Commit Task 1**

```bash
git add -- src/earnings_nowcast_sec_actuals.py tests/test_earnings_nowcast_sec_actuals.py
git commit -m "Extract SEC quarterly actual lineage"
```

---

### Task 2: Preserve append-only revisions and write preview-only staging artifacts

**Files:**
- Modify: `src/earnings_nowcast_sec_actuals.py`
- Modify: `tests/test_earnings_nowcast_sec_actuals.py`

**Interfaces:**
- Consumes: per-ticker `ExtractionResult` objects and an explicit output directory.
- Produces: `link_quarter_revisions(rows: Sequence[QuarterlyActual]) -> tuple[QuarterlyActual, ...]`.
- Produces: `write_sec_actuals_stage(output_dir: Path, results: Mapping[str, ExtractionResult]) -> StageResult`.
- Produces: `stage_sec_quarterly_actuals(tickers: Sequence[str], *, output_dir: Path, cutoff: str, user_agent: str | None, ...) -> StageResult`.

- [ ] **Step 1: Write failing revision-lineage tests**

```python
def test_later_changed_presentation_is_append_only_revision():
    original = actual("2025-Q2", revenue=100, eps=1.0, source_ref="sec://original", reported_at="2025-08-01T00:00:00Z")
    revised = actual("2025-Q2", revenue=100, eps=0.1, source_ref="sec://split-adjusted", reported_at="2025-11-01T00:00:00Z")

    linked = link_quarter_revisions([original, revised])

    assert len(linked) == 2
    assert linked[1].supersedes_source_ref == original.source_ref
    assert linked[0].eps_actual == 1.0
```

Also test unchanged later presentations are de-duplicated and an unrelated conflicting source is not silently marked as a revision.

- [ ] **Step 2: Run the revision test and verify RED**

Run:

```bash
python3 -m pytest tests/test_earnings_nowcast_sec_actuals.py::test_later_changed_presentation_is_append_only_revision -q
```

Expected: FAIL because `link_quarter_revisions` is missing.

- [ ] **Step 3: Implement revision linking and output types**

```python
@dataclass(frozen=True)
class StageResult:
    requested_tickers: tuple[str, ...]
    accepted_tickers: tuple[str, ...]
    withheld_tickers: tuple[str, ...]
    accepted_row_count: int
    rejected_row_count: int
    quarterly_actuals_path: str
    audit_path: str
    rejected_path: str
    automatic_apply: bool = False
```

Only link a later row as a revision when ticker/fiscal period/source family match and the changed row is later by `reported_at`. Keep the original row. Never mutate canonical data.

- [ ] **Step 4: Write failing output-boundary tests**

```python
def test_stage_writes_only_explicit_output_directory(tmp_path):
    result = write_sec_actuals_stage(tmp_path / "stage", {"SYN1": extraction_result()})

    assert Path(result.quarterly_actuals_path).parent == tmp_path / "stage"
    assert (tmp_path / "stage" / "quarterly_actuals.csv").exists()
    assert (tmp_path / "stage" / "consensus_snapshots.csv").read_text().count("\n") == 1
    assert result.automatic_apply is False
    assert not (tmp_path / "data").exists()
```

Verify audit JSON contains raw concept/start/end/frame/accession metadata and rejected CSV contains explicit reason codes.

- [ ] **Step 5: Implement CSV/JSON output and stage orchestrator**

Reuse `SCHEMAS` and `EVIDENCE_SCHEMA_VERSION` from `src.earnings_nowcast_onboarding`. Reuse `load_sec_ticker_map` and `fetch_companyfacts` from `src.providers.sec_companyfacts`. Dependency-inject ticker-map and Companyfacts fetchers for tests. Require `output_dir`; do not default to `data/imports`.

- [ ] **Step 6: Run Task 2 tests and existing onboarding tests**

```bash
python3 -m pytest tests/test_earnings_nowcast_sec_actuals.py tests/test_earnings_nowcast_onboarding.py -q
```

Expected: all pass and no file appears outside pytest temporary directories.

- [ ] **Step 7: Commit Task 2**

```bash
git add -- src/earnings_nowcast_sec_actuals.py tests/test_earnings_nowcast_sec_actuals.py
git commit -m "Stage SEC actuals as append-only evidence"
```

---

### Task 3: Enforce metric-specific quarter continuity and split safety

**Files:**
- Modify: `src/earnings_nowcast_readiness.py`
- Modify: `src/earnings_nowcast_model.py`
- Modify: `tests/test_earnings_nowcast_readiness.py`
- Modify: `tests/test_earnings_nowcast_model.py`
- Modify: `tests/test_earnings_nowcast_backtest.py`

**Interfaces:**
- Produces: `contiguous_metric_window(rows: Sequence[QuarterlyActual], target_period: str, metric: str, minimum_quarters: int) -> tuple[QuarterlyActual, ...]`.
- `assess_nowcast_readiness` adds `quarter_history_gap` and `incompatible_eps_definition` without changing existing public state names.
- `build_baseline_nowcast` uses the contiguous windows returned by the readiness helper.

- [ ] **Step 1: Write failing continuity tests**

```python
def test_missing_q4_withholds_both_metrics_instead_of_treating_q3_to_q1_as_sequential():
    rows = [row for row in _actuals() if row.fiscal_period != "2024-Q4"]

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert result.revenue_ready is False
    assert result.eps_ready is False
    assert "quarter_history_gap" in result.missing_evidence
```

Add a model regression test that monkeypatches or directly checks the selected input periods and proves Q3-to-Q1 is never passed to `_sequential_growth`.

- [ ] **Step 2: Run the continuity tests and verify RED**

```bash
python3 -m pytest tests/test_earnings_nowcast_readiness.py::test_missing_q4_withholds_both_metrics_instead_of_treating_q3_to_q1_as_sequential -q
```

Expected: FAIL because current readiness counts five rows without checking adjacency.

- [ ] **Step 3: Implement fiscal-period adjacency and contiguous windows**

```python
def _next_period(period: str) -> str:
    year, quarter = period.split("-Q")
    return f"{int(year) + 1}-Q1" if quarter == "4" else f"{year}-Q{int(quarter) + 1}"


def contiguous_metric_window(rows, target_period, metric, minimum_quarters):
    eligible = [row for row in rows if getattr(row, f"{metric}_actual") is not None]
    # Walk backward from the period immediately before target_period.
    # Return an empty tuple when any required period is missing.
```

Use the contiguous window for history sufficiency, stability checks, model inputs, and source IDs. Keep Revenue and EPS windows separate.

- [ ] **Step 4: Write failing split-basis tests**

```python
def test_split_basis_change_withholds_eps_but_keeps_revenue_ready():
    rows = _actuals()
    rows[0] = replace(rows[0], split_adjustment_basis="pre_split")
    consensus = replace(_consensus(), split_adjustment_basis="post_split_2024_06_10")

    result = assess_nowcast_readiness(...)

    assert result.revenue_ready is True
    assert result.eps_ready is False
    assert "incompatible_eps_definition" in result.missing_evidence
```

Also prove a source-backed append-only split-adjusted revision restores a consistent EPS window before the cutoff, while a post-cutoff revision does not.

- [ ] **Step 5: Implement split-basis filtering and cutoff-safe revision selection**

Reuse `_metric_definition` and `canonicalize_actuals`; do not add ticker-specific split constants to model code. The evidence row and consensus row carry the basis. If no five-quarter contiguous compatible EPS window exists, withhold EPS.

- [ ] **Step 6: Run readiness, model, and backtest suites**

```bash
python3 -m pytest \
  tests/test_earnings_nowcast_readiness.py \
  tests/test_earnings_nowcast_model.py \
  tests/test_earnings_nowcast_backtest.py -q
```

Expected: all pass; existing leakage and probability gates remain unchanged.

- [ ] **Step 7: Commit Task 3**

```bash
git add -- src/earnings_nowcast_readiness.py src/earnings_nowcast_model.py \
  tests/test_earnings_nowcast_readiness.py tests/test_earnings_nowcast_model.py \
  tests/test_earnings_nowcast_backtest.py
git commit -m "Require contiguous nowcast quarter history"
```

---

### Task 4: Ingest explicit Q4 results from SEC-filed earnings-release exhibits

**Files:**
- Modify: `src/earnings_nowcast_sec_actuals.py`
- Modify: `src/providers/sec_submissions.py`
- Modify: `tests/test_earnings_nowcast_sec_actuals.py`
- Modify: `tests/test_sec_submissions.py`

**Interfaces:**
- Produces: `sec_filing_index_url(cik: str, accession: str) -> str` in `src.providers.sec_submissions`.
- Produces: `extract_filing_exhibits(index_html: str, *, cik: str, accession: str) -> tuple[FiledExhibit, ...]`.
- Produces: `extract_explicit_q4_actual(ticker: str, exhibit: FiledExhibit, document_text: str, *, fiscal_period: str, filed_at: str, retrieved_at: str) -> ExtractionResult`.
- `stage_sec_quarterly_actuals` combines Q1-Q3 lineage and explicit Q4 rows before revision linking.

- [ ] **Step 1: Write failing filing-index and Q4 table tests**

Use a fixture index containing an `EX-99.1` link and an earnings-release fixture containing:

```html
<p>Fourth Quarter Fiscal 2025 Summary</p>
<table>
  <tr><th></th><th>Q4 FY25</th></tr>
  <tr><td>Revenue</td><td>$39,331 million</td></tr>
  <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr>
</table>
<p>All per-share amounts are retrospectively adjusted for the ten-for-one split effective June 7, 2024.</p>
```

Assertions:

```python
assert exhibits[0].document_type == "EX-99.1"
assert result.rows[0].fiscal_period == "2025-Q4"
assert result.rows[0].revenue_actual == 39_331_000_000
assert result.rows[0].eps_actual == 0.89
assert result.rows[0].split_adjustment_basis == "split_adjusted_2024_06_07"
```

- [ ] **Step 2: Run Q4 tests and verify RED**

```bash
python3 -m pytest tests/test_earnings_nowcast_sec_actuals.py -k 'filing_index or explicit_q4' -q
```

Expected: FAIL because filing-index and Q4 interfaces are missing.

- [ ] **Step 3: Implement filing-index URL and standard-library table extraction**

Use `html.parser.HTMLParser`; do not add a new runtime dependency. The parser must preserve table row/cell text and nearby quarter/split labels. Normalize commas, currency symbols, parentheses, and explicit `million` / `billion` scale only after the metric label is matched.

- [ ] **Step 4: Add fail-closed Q4 cases**

Add tests proving these produce no actual row and explicit audit states:

- annual total without a Q4 column;
- guidance table (`outlook`, `expected`, `approximately`);
- non-GAAP EPS without GAAP diluted EPS;
- Q4 derived only by subtraction;
- ambiguous period header;
- source filed after cutoff;
- missing split note labels EPS `as_reported`; the readiness split-basis gate,
  rather than the parser, withholds EPS when the surrounding lineage requires
  an incompatible split-adjusted basis.

- [ ] **Step 5: Implement exhibit discovery and Q4 selection**

Search `8-K` / `8-K/A` filing index documents for `EX-99`, `EX-99.1`, or `EX-99.2` result exhibits. Require exact source URL, accession, filed date, quarter label, and metric labels. Issuer aliases belong in a small immutable table of labels, never values. If multiple exhibits disagree, reject Q4 as `ambiguous_concept`.

- [ ] **Step 6: Run Q4 and SEC provider tests**

```bash
python3 -m pytest tests/test_earnings_nowcast_sec_actuals.py tests/test_sec_submissions.py -q
```

Expected: all pass without network access.

- [ ] **Step 7: Commit Task 4**

```bash
git add -- src/earnings_nowcast_sec_actuals.py src/providers/sec_submissions.py \
  tests/test_earnings_nowcast_sec_actuals.py tests/test_sec_submissions.py
git commit -m "Stage explicit SEC filed Q4 actuals"
```

---

### Task 5: Add launcher, documentation, and five-company live verification

**Files:**
- Modify: `Makefile`
- Modify: `tests/test_launchers.py`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `ROADMAP.md`
- Modify: `src/earnings_nowcast_sec_actuals.py`
- Modify: `tests/test_earnings_nowcast_sec_actuals.py`

**Interfaces:**
- CLI: `python3 -m src.earnings_nowcast_sec_actuals --tickers ... --output-dir ... --cutoff ...`.
- Make: `make earnings-nowcast-sec-actuals-stage TICKERS=... OUTPUT_DIR=... AS_OF=...`.
- JSON summary exposes per-ticker accepted rows, rejected rows, missing Q4, continuity gaps, source refs, and `automatic_apply=false`.

- [ ] **Step 1: Write failing launcher tests**

Add to `tests/test_launchers.py`:

```python
assert "earnings-nowcast-sec-actuals-stage" in makefile
assert "TICKERS is required" in makefile
assert "OUTPUT_DIR is required" in makefile
assert "--cutoff $(AS_OF)" in makefile
assert "imports-apply" not in target_body(makefile, "earnings-nowcast-sec-actuals-stage")
```

Add a CLI test that dependency-injects cached fixtures and confirms JSON output contains `automatic_apply: false`.

- [ ] **Step 2: Run launcher tests and verify RED**

```bash
python3 -m pytest tests/test_launchers.py tests/test_earnings_nowcast_sec_actuals.py -q
```

Expected: launcher assertion fails.

- [ ] **Step 3: Implement CLI and Make target**

Add to `.PHONY` and Makefile:

```make
earnings-nowcast-sec-actuals-stage:
ifndef TICKERS
	$(error TICKERS is required, for example: make earnings-nowcast-sec-actuals-stage TICKERS=NVDA OUTPUT_DIR=/tmp/sec-actuals AS_OF=2026-07-16T03:59:59Z)
endif
ifndef OUTPUT_DIR
	$(error OUTPUT_DIR is required; use a generated temporary/review directory)
endif
ifndef AS_OF
	$(error AS_OF is required for cutoff-safe evidence staging)
endif
	@python3 -m src.earnings_nowcast_sec_actuals --tickers "$(TICKERS)" --output-dir "$(OUTPUT_DIR)" --cutoff "$(AS_OF)"
```

The Python CLI accepts `--no-network`, `--sec-refresh`, and `--json`. It never accepts an apply flag.

- [ ] **Step 4: Update methodology and roadmap truth**

Document:

- Q1-Q3 duration and fiscal-lineage rules;
- explicit Q4 source rule and no-derivation boundary;
- revision/cutoff behavior;
- quarter-continuity and EPS split-basis withholding;
- five-company pilot scope;
- real output still `awaiting_point_in_time_consensus`;
- probability still `awaiting_calibration_evidence`.

Do not claim real Nowcast coverage merely because actuals stage successfully.

- [ ] **Step 5: Run focused and full deterministic verification**

```bash
python3 -m pytest \
  tests/test_earnings_nowcast_sec_actuals.py \
  tests/test_earnings_nowcast_onboarding.py \
  tests/test_earnings_nowcast_readiness.py \
  tests/test_earnings_nowcast_model.py \
  tests/test_earnings_nowcast_backtest.py \
  tests/test_sec_submissions.py \
  tests/test_launchers.py -q
python3 -m pytest tests -q
make public-wording-check
make dashboard-smoke
make browser-qa-evidence
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all tests and gates pass. Generated readiness/report files remain unstaged.

- [ ] **Step 6: Run the live read-only five-company smoke**

```bash
rm -rf /tmp/stock-nowcast-five-company/sec-lineage-stage
make earnings-nowcast-sec-actuals-stage \
  TICKERS=NVDA,AMD,AVGO,MU,QCOM \
  OUTPUT_DIR=/tmp/stock-nowcast-five-company/sec-lineage-stage \
  AS_OF=2026-07-16T03:59:59Z
make earnings-nowcast-validate \
  INPUT_DIR=/tmp/stock-nowcast-five-company/sec-lineage-stage \
  AS_OF=2026-07-16T03:59:59Z
make earnings-nowcast-preview \
  INPUT_DIR=/tmp/stock-nowcast-five-company/sec-lineage-stage \
  AS_OF=2026-07-16T03:59:59Z
```

Inspect per ticker:

- at least five consecutive Revenue quarters or an explicit truthful gap;
- EPS ready only within one source-backed split basis;
- Q4 rows have exact SEC-filed exhibit URLs;
- zero post-cutoff rows;
- zero cumulative facts;
- preview remains `ready_for_packet=false` with `point_in_time_consensus_missing` when consensus is absent.

Do not stage `/tmp` output.

- [ ] **Step 7: Commit Task 5**

```bash
git add -- Makefile ROADMAP.md \
  docs/EARNINGS_NOWCAST_PILOT.md docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md \
  src/earnings_nowcast_sec_actuals.py tests/test_earnings_nowcast_sec_actuals.py \
  tests/test_launchers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add SEC quarterly actuals staging workflow"
```

## Final Review Gate

After all task commits:

```bash
git status --short --branch
git log -8 --oneline
git diff origin/main...HEAD --stat
python3 -m pytest tests -q
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

The feature is complete only when fixture validation, full regression gates, and live read-only evidence agree. Real Earnings Nowcast remains blocked until historical point-in-time consensus snapshots are separately source-backed and validated.
