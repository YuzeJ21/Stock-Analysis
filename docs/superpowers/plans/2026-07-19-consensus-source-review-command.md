# Consensus Source Review Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a supported read-only command that loads one supplied consensus CSV and exposes the existing technical, temporal, rights, and Revenue/EPS scope review before collection preview.

**Architecture:** Extend `src.earnings_consensus_sources` with two pure presentation-boundary helpers and an explicit CLI review mode while leaving `validate_source_rows(...)` as the only validation decision. Add one bytecode-free Make target; existing provider-status behavior remains the default.

**Tech Stack:** Python 3.12 standard library (`argparse`, `csv`, `dataclasses`, `json`, `pathlib`), pytest, GNU Make, Markdown documentation.

## Global Constraints

- The command is read-only: no provider fetch, normalization, directory creation, ledger append, apply, readiness rebuild, or generated output file.
- Require explicit `INPUT`, exact `PROVIDER`, and UTC `AS_OF`; supply no defaults.
- Preserve technical acceptance, candidate/history state, commercial rights, Revenue scope, EPS scope, collection, and activation as independent evidence.
- A readable review returns zero even when rows are rejected or commercially incomplete; invocation and CSV-shape errors return nonzero.
- Keep the existing `earnings-consensus-source-status` CLI and Make behavior compatible.
- Set `PYTHONDONTWRITEBYTECODE=1` on the new Make target.
- Do not create or stage CSV, JSON, report, sample-report, screenshot, browser-timing, readiness, canonical-data, or proof-ledger churn.
- Never use `git add -A`; stage only exact reviewed product/code/docs/test paths.
- Keep PR #113 open and draft; do not merge or deploy.

---

### Task 1: Read and render one source-review CSV

**Files:**
- Modify: `src/earnings_consensus_sources.py`
- Test: `tests/test_earnings_consensus_sources.py`

**Interfaces:**
- Consumes: `validate_source_rows(provider: str, rows: Sequence[Mapping[str, object]], *, as_of: object, rights_registry: Mapping[str, SourceRights] | None = None) -> SourceValidationResult`.
- Produces: `load_source_review_csv(path: Path | str) -> tuple[dict[str, object], ...]`.
- Produces: `render_source_validation_result(result: SourceValidationResult) -> str`.

- [ ] **Step 1: Add failing loader and renderer tests**

Task 1 needs the existing `Path` and `pytest` imports. Extend the source import and add these tests:

Extend the source import to include `load_source_review_csv` and `render_source_validation_result`:

```python
from src.earnings_consensus_sources import (
    consensus_source_statuses,
    load_source_review_csv,
    render_source_validation_result,
    validate_source_rows,
)
```

```python
def test_load_source_review_csv_preserves_rows_without_writing(tmp_path: Path):
    input_path = tmp_path / "reviewed.csv"
    input_path.write_text(
        "ticker,fiscal_period,snapshot_at,retrieved_at,source_ref,revenue_consensus,eps_consensus,history_scope\n"
        "NVDA,2027-Q1,2026-07-18T05:00:00Z,2026-07-18T05:00:01Z,fixture://NVDA,1,2,current_only\n",
        encoding="utf-8",
    )
    before = input_path.read_bytes()

    rows = load_source_review_csv(input_path)

    assert rows == (
        {
            "ticker": "NVDA",
            "fiscal_period": "2027-Q1",
            "snapshot_at": "2026-07-18T05:00:00Z",
            "retrieved_at": "2026-07-18T05:00:01Z",
            "source_ref": "fixture://NVDA",
            "revenue_consensus": "1",
            "eps_consensus": "2",
            "history_scope": "current_only",
        },
    )
    assert input_path.read_bytes() == before
    assert {path.name for path in tmp_path.iterdir()} == {"reviewed.csv"}


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("", "header row"),
        ("ticker,ticker\nNVDA,NVDA\n", "non-blank unique column names"),
        ("ticker,,fiscal_period\nNVDA,x,2027-Q1\n", "non-blank unique column names"),
        ("ticker\nNVDA,extra\n", "more values than the header"),
    ],
)
def test_load_source_review_csv_rejects_ambiguous_shapes(
    tmp_path: Path,
    contents: str,
    message: str,
):
    input_path = tmp_path / "reviewed.csv"
    input_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_source_review_csv(input_path)


def test_load_source_review_csv_reports_unreadable_input(tmp_path: Path):
    with pytest.raises(ValueError, match="cannot read consensus source review CSV"):
        load_source_review_csv(tmp_path / "missing.csv")
    with pytest.raises(ValueError, match="cannot read consensus source review CSV"):
        load_source_review_csv(tmp_path)


def test_load_source_review_csv_accepts_header_only_as_empty_review(tmp_path: Path):
    input_path = tmp_path / "reviewed.csv"
    input_path.write_text("ticker,fiscal_period\n", encoding="utf-8")

    rows = load_source_review_csv(input_path)
    result = validate_source_rows(
        "reviewed_csv",
        rows,
        as_of=REVIEW_CUTOFF,
    )

    assert rows == ()
    assert result.state == "still_blocked"
    assert result.accepted_count == 0
    assert result.auto_apply is False


def test_render_source_validation_result_keeps_technical_and_commercial_evidence_separate():
    result = validate_source_rows(
        "licensed_consensus",
        [
            _historical_row(eps_consensus=""),
            _current_row(retrieved_at="2026-07-18T06:00:01Z"),
        ],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(supported_fields=("revenue_consensus",)),
    )

    rendered = render_source_validation_result(result)

    assert "Consensus Source Review" in rendered
    assert "state: historical_evidence_reviewable" in rendered
    assert "accepted_count: 1" in rendered
    assert "rejected_count: 1" in rendered
    assert "commercial_evidence_ready: true" in rendered
    assert "- row 2: retrieved_at is after review cutoff" in rendered
    assert "- row 1: required=revenue_consensus; missing=none; ready=true; blockers=none" in rendered
    assert "auto_apply: false" in rendered
    assert "collection preview remains a separate reviewed gate" in rendered
```

- [ ] **Step 2: Run the new tests and require the intended red state**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_earnings_consensus_sources.py::test_load_source_review_csv_preserves_rows_without_writing \
  tests/test_earnings_consensus_sources.py::test_load_source_review_csv_rejects_ambiguous_shapes \
  tests/test_earnings_consensus_sources.py::test_load_source_review_csv_reports_unreadable_input \
  tests/test_earnings_consensus_sources.py::test_load_source_review_csv_accepts_header_only_as_empty_review \
  tests/test_earnings_consensus_sources.py::test_render_source_validation_result_keeps_technical_and_commercial_evidence_separate -q
```

Expected: collection fails because `load_source_review_csv` and `render_source_validation_result` are not defined.

- [ ] **Step 3: Implement strict read-only CSV loading**

Import `csv`, then add:

```python
def load_source_review_csv(path: Path | str) -> tuple[dict[str, object], ...]:
    """Load supplied consensus source rows without normalizing or writing evidence."""

    review_path = Path(path)
    try:
        with review_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames is None:
                raise ValueError("consensus source review CSV must contain a header row")
            fieldnames = tuple(str(field or "") for field in reader.fieldnames)
            if (
                any(not field.strip() for field in fieldnames)
                or len(set(fieldnames)) != len(fieldnames)
            ):
                raise ValueError(
                    "consensus source review CSV headers must be non-blank unique column names"
                )
            rows: list[dict[str, object]] = []
            for row_number, row in enumerate(reader, start=1):
                if None in row:
                    raise ValueError(
                        f"consensus source review CSV row {row_number} has more values than the header"
                    )
                rows.append({str(key): value for key, value in row.items()})
            return tuple(rows)
    except ValueError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(
            f"cannot read consensus source review CSV: {review_path}"
        ) from exc
```

Do not strip or rename headers and do not coerce cells. Core validation must expose missing exact fields.

- [ ] **Step 4: Implement deterministic human rendering**

Add:

```python
def _joined(values: Sequence[object]) -> str:
    return ",".join(str(value) for value in values) if values else "none"


def render_source_validation_result(result: SourceValidationResult) -> str:
    lines = [
        "Consensus Source Review",
        "Read-only: this command does not fetch, normalize, record, apply, rebuild readiness, or write artifacts.",
        f"provider: {result.provider or '-'}",
        f"review_cutoff: {result.review_cutoff}",
        f"state: {result.state}",
        f"accepted_count: {result.accepted_count}",
        f"rejected_count: {result.rejected_count}",
        f"historical_snapshot_count: {result.historical_snapshot_count}",
        f"candidate_context_count: {result.candidate_context_count}",
        f"rights_status: {result.rights_status}",
        f"commercial_rights_approved: {str(result.commercial_rights_approved).lower()}",
        f"commercial_ready_count: {result.commercial_ready_count}",
        f"commercial_review_required_count: {result.commercial_review_required_count}",
        f"commercial_evidence_ready: {str(result.commercial_evidence_ready).lower()}",
        f"commercial_blockers: {_joined(result.commercial_blockers)}",
        "rejected_rows:",
    ]
    if result.rejected_rows:
        lines.extend(
            f"- row {row['row_number']}: {row['reason']}"
            for row in result.rejected_rows
        )
    else:
        lines.append("- none")
    lines.append("commercial_review_rows:")
    if result.commercial_review_rows:
        lines.extend(
            "- row "
            f"{row.row_number}: required={_joined(row.required_supported_fields)}; "
            f"missing={_joined(row.missing_supported_fields)}; "
            f"ready={str(row.commercial_evidence_ready).lower()}; "
            f"blockers={_joined(row.commercial_blockers)}"
            for row in result.commercial_review_rows
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            f"auto_apply: {str(result.auto_apply).lower()}",
            "next_gate: collection preview remains a separate reviewed gate after the payload and evidence are accepted.",
            "Boundary: reviewability is not collection, activation, readiness, backtesting, calibration, or investment advice.",
        ]
    )
    return "\n".join(lines)
```

- [ ] **Step 5: Run the full source test module**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_earnings_consensus_sources.py -q
```

Expected: all tests pass; no repository file changes beyond the two intentional source/test files.

- [ ] **Step 6: Review Task 1 diff**

Run `git diff --check` and inspect the source/test diff. Confirm no status or validator decision changed and no generated file exists.

---

### Task 2: Expose explicit CLI and Make review modes

**Files:**
- Modify: `src/earnings_consensus_sources.py`
- Modify: `Makefile`
- Test: `tests/test_earnings_consensus_sources.py`
- Test: `tests/test_launchers.py`

**Interfaces:**
- Consumes: `load_source_review_csv(...)`, `validate_source_rows(...)`, and `render_source_validation_result(...)` from Task 1.
- Produces: `python3 -m src.earnings_consensus_sources --review-csv PATH --provider SOURCE --as-of TIMESTAMP [--json]`.
- Produces: `make earnings-consensus-source-review INPUT=... PROVIDER=... AS_OF=... [JSON=1]`.

- [ ] **Step 1: Add failing CLI and Make contract tests**

Add `json`, `os`, `subprocess`, and `sys` imports to `tests/test_earnings_consensus_sources.py`, then add the exact test-only CSV constant and tests below.

Add this exact test-only constant:

```python
HISTORICAL_REVIEW_CSV = (
    "ticker,fiscal_period,snapshot_at,retrieved_at,source_ref,revenue_consensus,eps_consensus,history_scope,"
    "revenue_currency,revenue_unit_scale,revenue_basis,eps_currency,eps_basis,eps_share_basis,eps_operations_basis,split_adjustment_basis\n"
    "NVDA,2027-Q1,2026-07-18T05:00:00Z,2026-07-18T05:00:01Z,fixture://consensus/NVDA/2027-Q1,1,,point_in_time,"
    "USD,1,reported,USD,gaap,diluted,reported,as_reported\n"
)
```

```python
def test_source_review_cli_renders_supplied_rows_without_artifacts(tmp_path: Path):
    input_path = tmp_path / "reviewed.csv"
    input_path.write_text(HISTORICAL_REVIEW_CSV, encoding="utf-8")
    before = input_path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.earnings_consensus_sources",
            "--review-csv",
            str(input_path),
            "--provider",
            "sec_companyfacts",
            "--as-of",
            REVIEW_CUTOFF,
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    assert result.returncode == 0
    assert "state: historical_evidence_reviewable" in result.stdout
    assert "rights_status: approved" in result.stdout
    assert "registered_consensus_scope_missing:revenue_consensus" in result.stdout
    assert input_path.read_bytes() == before
    assert {path.name for path in tmp_path.iterdir()} == {"reviewed.csv"}


def test_source_review_cli_json_matches_result_contract(tmp_path: Path):
    input_path = tmp_path / "reviewed.csv"
    input_path.write_text(HISTORICAL_REVIEW_CSV, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.earnings_consensus_sources",
            "--review-csv",
            str(input_path),
            "--provider",
            "sec_companyfacts",
            "--as-of",
            REVIEW_CUTOFF,
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["provider"] == "sec_companyfacts"
    assert payload["review_cutoff"] == REVIEW_CUTOFF
    assert payload["historical_snapshot_count"] == 1
    assert payload["commercial_rights_approved"] is True
    assert payload["commercial_evidence_ready"] is False
    assert payload["auto_apply"] is False


@pytest.mark.parametrize(
    "args",
    [
        ["--review-csv", "missing.csv", "--as-of", REVIEW_CUTOFF],
        ["--review-csv", "missing.csv", "--provider", "reviewed_csv"],
        ["--provider", "reviewed_csv", "--as-of", REVIEW_CUTOFF],
        [
            "--review-csv",
            "missing.csv",
            "--reviewed-csv",
            "other.csv",
            "--provider",
            "reviewed_csv",
            "--as-of",
            REVIEW_CUTOFF,
        ],
    ],
)
def test_source_review_cli_requires_complete_review_mode(args: list[str]):
    result = subprocess.run(
        [sys.executable, "-m", "src.earnings_consensus_sources", *args],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    assert result.returncode != 0
    assert "error:" in result.stderr


def test_source_review_cli_rejects_invalid_cutoff(tmp_path: Path):
    input_path = tmp_path / "reviewed.csv"
    input_path.write_text("ticker,fiscal_period\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.earnings_consensus_sources",
            "--review-csv",
            str(input_path),
            "--provider",
            "reviewed_csv",
            "--as-of",
            "not-a-cutoff",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    assert result.returncode != 0
    assert "review cutoff" in result.stderr
```

In `tests/test_launchers.py`, add:

```python
def test_makefile_exposes_bytecode_free_consensus_source_review_target():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "earnings-consensus-source-review:" in makefile
    assert "PYTHONDONTWRITEBYTECODE=1 python3 -m src.earnings_consensus_sources" in makefile
    assert '--review-csv "$(INPUT)"' in makefile
    assert '--provider "$(PROVIDER)"' in makefile
    assert '--as-of "$(AS_OF)"' in makefile
    assert "$(if $(JSON),--json,)" in makefile
```

- [ ] **Step 2: Run the new CLI/Make tests and require failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_earnings_consensus_sources.py \
  tests/test_launchers.py \
  -k "source_review_cli or makefile_exposes_bytecode_free_consensus_source_review_target" -q
```

Expected: CLI tests fail because the review arguments are unknown and the Make target assertion fails.

- [ ] **Step 3: Extend CLI argument routing without changing status mode**

Add arguments:

```python
parser.add_argument("--review-csv", type=Path)
parser.add_argument("--provider")
parser.add_argument("--as-of")
```

Before the existing status rendering, add:

```python
if args.review_csv is not None:
    if args.reviewed_csv is not None:
        parser.error("--review-csv cannot be combined with --reviewed-csv")
    if not str(args.provider or "").strip():
        parser.error("--provider is required with --review-csv")
    if not str(args.as_of or "").strip():
        parser.error("--as-of is required with --review-csv")
    try:
        result = validate_source_rows(
            args.provider,
            load_source_review_csv(args.review_csv),
            as_of=args.as_of,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    else:
        print(render_source_validation_result(result))
    return 0

if args.provider is not None or args.as_of is not None:
    parser.error("--provider and --as-of require --review-csv")
```

Leave the existing `consensus_source_statuses(...)` branch and its JSON/list shape unchanged.

- [ ] **Step 4: Add the Make target**

Add `earnings-consensus-source-review` to the existing `.PHONY` line and add after status:

```make
earnings-consensus-source-review:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.earnings_consensus_sources --review-csv "$(INPUT)" --provider "$(PROVIDER)" --as-of "$(AS_OF)" $(if $(JSON),--json,)
```

- [ ] **Step 5: Run focused CLI, launcher, and existing-status tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_earnings_consensus_sources.py \
  tests/test_launchers.py -q
```

Expected: all tests pass and existing status tests remain unchanged.

- [ ] **Step 6: Run a temporary-directory CLI smoke**

Use `mktemp -d`, copy a test-only CSV into it, run the Python review command with `PYTHONDONTWRITEBYTECODE=1`, inspect the output, and confirm the directory still contains only the input. Do not place the fixture under `data/`, `outputs/`, or the repository.

---

### Task 3: Document the Stage 2 review gate and release the slice

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: the verified command and Make target from Task 2.
- Produces: roadmap item 34, Stage 2 command ordering, design/plan lineage anchor, and truthful review boundaries.

- [ ] **Step 1: Update roadmap and methodology documentation**

Add roadmap item 34: one supplied consensus CSV can now enter a read-only, explicit-provider, explicit-cutoff source review before collection preview. State that it improves Stage 2 operating reliability and rejection visibility but supplies no source, rights, payload proof, collection, readiness, backtesting, calibration, hosting, reviewers, or market validation.

Document the command sequence:

```bash
SOURCE_INPUT=<reviewed_source_export.csv>
make earnings-consensus-source-review INPUT=$SOURCE_INPUT PROVIDER=<source_id> AS_OF=<timestamp>
COLLECTION_INPUT=<prospective_consensus.csv>
make earnings-consensus-collection-preview INPUT=$COLLECTION_INPUT AS_OF=<timestamp>
```

Clarify that these are distinct input contracts: the second command is appropriate only after separate payload/evidence review and explicit evidence-preserving mapping into the checked-in prospective schema. No command infers or writes that mapping, and neither gate writes without the explicit later record command.

- [ ] **Step 2: Update data strategy, pilot, provenance, and continuation contract**

Record:

- strict CSV header/shape checks;
- original one-based rejected row numbers;
- explicit provider and cutoff;
- human/JSON stdout only;
- `auto_apply=false`;
- checked-in registry evidence remains metadata, not payload permission;
- no default provider, cutoff, collection, or readiness promotion;
- current consensus source/data/right classifications remain external and unchanged.

Add design/plan lineage anchor `6aa9c0c44` or the later plan commit, the capability bullet, truthful boundary, and Stage 2 source-review-before-preview instruction to the continuation prompt.

- [ ] **Step 3: Add a failing documentation contract test, then make it pass**

Add to `tests/test_public_v1_release_docs.py`:

```python
def test_consensus_source_review_docs_keep_review_collection_and_activation_separate():
    roadmap = _read("ROADMAP.md")
    data_strategy = _read("docs/DATA_STRATEGY.md")
    pilot = _read("docs/EARNINGS_NOWCAST_PILOT.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, data_strategy, pilot, methodology, provenance, prompt):
        assert "earnings-consensus-source-review" in text
        assert "collection preview" in text.lower()
        assert "read-only" in text.lower()
    assert "explicit provider" in roadmap.lower()
    assert "original one-based" in provenance.lower()
    assert "auto_apply=false" in pilot
    assert "source-review-before-preview" in prompt.lower()
```

Run this exact test before the docs edit and require failure, then rerun it after the six documentation changes and require a pass.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_earnings_consensus_sources.py \
  tests/test_launchers.py \
  tests/test_public_v1_release_docs.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
```

Expected: zero failures; the existing third-party dateutil warning may remain.

- [ ] **Step 5: Run all required non-writing product gates**

Run:

```bash
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

Expected: executable gates pass, pilot readiness remains blocked by stale saved readiness, and generated churn remains zero.

- [ ] **Step 6: Stage exact files and verify hygiene**

Stage only the source module, Makefile, the two or three named test files actually changed, the six named product documents, and this plan if corrected during execution. Run:

```bash
make staged-hygiene-check
git diff --cached --check
```

Expected: only intentional product/code/docs/test files; zero generated or manual-review paths.

- [ ] **Step 7: Commit, push, and update draft PR #113**

Commit the implementation/docs slice with message `Add consensus source review command`. Push only `codex/personal-research-mode-mvp`. Post the exact command, red-green evidence, full gate results, no-write proof, unchanged external classifications, and next external unblock to PR #113. Keep it draft.

- [ ] **Step 8: Re-audit the handoff**

Verify clean status, 0/0 upstream alignment, open/draft/mergeable PR state, generated-artifact hygiene, stale readiness, and active overall goal. Do not merge or deploy.
