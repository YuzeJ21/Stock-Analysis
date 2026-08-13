# In-App Research-Record Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe command-line-free thesis, evidence, catalyst, and outcome authoring to Company Workbench through an exact `Validate -> Preview -> Confirm and save` flow over the existing append-only ledgers.

**Architecture:** A new pure composition module owns record construction, existing-validator dispatch, cross-ledger references, preview receipts, ledger fingerprints, and one-ledger confirmation. A small Streamlit component owns widgets and session state and is called from Company Workbench after the journal answer; production dashboard code never opens a ledger directly. Tests use temporary ledgers and a test-only Streamlit fixture, while the product route renders the composer closed by default.

**Tech Stack:** Python 3.12, frozen dataclasses, `hashlib`/`json`/`uuid`, existing CSV ledger engines, Streamlit, pytest, Streamlit AppTest, existing render/release gates.

## Global Constraints

- Research-only; no investment advice, recommendation, company ranking, expected-return score, direct buy/sell instruction, allocation, position sizing, live holding, account import, broker connection, order routing, auto-trading, or post-earnings price prediction.
- Reuse `research_thesis_journal.py`, `catalyst_evidence_timeline.py`, and `research_outcome_review.py`; do not create a generic ledger or duplicate their validators.
- Drafts, previews, and the session-only receipt are untrusted session state. Candidate context cannot become trusted evidence, and no receipt is persisted to a ledger or generated artifact.
- Profile and ticker are locked to the active Company Workbench context.
- Preview writes nothing. Confirmation requires an exact current draft, unchanged current ledger fingerprint, unchanged context, and explicit reviewed-source confirmation.
- A successful confirmation appends exactly one row to exactly one established ledger and consumes the preview receipt.
- Tests use temporary ledgers only. Do not append production research data during implementation or verification.
- Do not change readiness, canonical data, source rights, forecasts, DCF assumptions, scenarios, consensus, valuation, peers, backtests, calibration, or numerical probability.
- Empty ledgers remain empty until an explicit successful confirmation targets that exact ledger.
- EPS split basis remains unverified without explicit primary proof; Q4 actuals still require an explicit SEC-filed Q4 table; synthetic fixtures remain test-only.
- Do not run `make readiness`, broad refresh/import/apply commands, or generated CSV/JSON/report/sample-report/screenshot/timing commands.
- Stage exact intentional files only; never use `git add -A`; keep the existing 18 generated CSV/report changes unstaged.

## File Structure

- Create `src/research_record_authoring.py`: immutable authoring contracts, record mapping, preview validation, receipt and ledger fingerprints, cross-ledger reference checks, and confirmed dispatch.
- Create `src/research_record_authoring_ui.py`: record-specific field definitions, Streamlit widget rendering, session preview invalidation, confirmation, and saved-result feedback.
- Create `tests/test_research_record_authoring.py`: pure composition, read-only preview, stale receipt, cross-scope, one-ledger-only, and no-fabrication tests.
- Create `tests/fixtures/research_record_authoring_app.py`: test-only Streamlit host wired exclusively to temporary paths supplied by the test process.
- Create `tests/test_research_record_authoring_ui.py`: field-model and AppTest interaction coverage without production writes.
- Modify `src/dashboard.py`: import and render the composer after the journal/outcome answer only in Personal Research Company Workbench.
- Modify `tests/test_dashboard_helpers.py`: source-boundary and placement contracts.
- Modify `tests/test_dashboard_render_smoke.py`: closed-by-default Workbench render contract.
- Modify `src/browser_qa_evidence.py` and `tests/test_browser_qa_evidence.py`: add the collapsed authoring marker and mobile stop rule without claiming save evidence from screenshots.
- Modify `README.md`, `docs/PRODUCT_SPEC.md`, `ROADMAP.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, and `tests/test_public_v1_release_docs.py`: document the implemented workflow and truthful boundaries after runtime evidence exists.

---

### Task 1: Pure Four-Kind Preview Composition

**Files:**
- Create: `src/research_record_authoring.py`
- Create: `tests/test_research_record_authoring.py`

**Interfaces:**
- Produces: `AuthoringPaths`, `AuthoringDraft`, `AuthoringPreview`, `build_authoring_draft()`, `authoring_draft_digest()`, and `preview_authoring_record()`.
- Consumes: existing `JournalEntry`, `CatalystEvent`, `ResearchOutcome`, their load functions, and their preview/validation functions.
- Invariant: preview reads only the targeted ledger plus the thesis journal needed for evidence/outcome references and never creates a path.

- [ ] **Step 1: Write failing preview tests**

Add these contracts to `tests/test_research_record_authoring.py`:

```python
from dataclasses import replace
from pathlib import Path

import pytest

from src.research_record_authoring import (
    AuthoringPaths,
    build_authoring_draft,
    preview_authoring_record,
)
from src.research_thesis_journal import JournalEntry, append_journal_entry


def _paths(tmp_path: Path) -> AuthoringPaths:
    return AuthoringPaths(
        journal=tmp_path / "research_thesis_journal.csv",
        catalysts=tmp_path / "catalyst_evidence.csv",
        outcomes=tmp_path / "research_outcome_reviews.csv",
    )


def _thesis_entry() -> JournalEntry:
    return JournalEntry(
        schema_version="research-thesis-journal-v1",
        entry_id="entry-existing",
        profile_key="demo",
        ticker="SYN1",
        thesis_id="thesis-syn1",
        entry_type="thesis",
        recorded_at="2026-07-20T12:00:00Z",
        effective_at="2026-07-20T11:00:00Z",
        reviewer="fixture-reviewer",
        summary="Existing synthetic thesis.",
        evidence_direction="",
        source="",
        source_ref="",
        source_published_at="",
        confidence="0.50",
        review_due_date="2026-08-20",
        supersedes_entry_id="",
    )


@pytest.mark.parametrize(
    ("kind", "fields", "destination"),
    (
        ("thesis", {"thesis_id": "thesis-new", "summary": "Reviewed hypothesis.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "confidence": "0.60", "review_due_date": "2026-08-22", "supersedes_entry_id": ""}, "research_thesis_journal.csv"),
        ("evidence", {"thesis_id": "thesis-syn1", "summary": "Source-backed evidence.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "evidence_direction": "supporting", "source": "company_ir", "source_ref": "https://example.invalid/source", "source_published_at": "2026-07-22T09:00:00Z"}, "research_thesis_journal.csv"),
        ("catalyst", {"event_type": "earnings", "title": "Scheduled results", "summary": "Reviewed event context.", "effective_at": "2026-08-20T21:00:00Z", "published_at": "2026-07-22T09:00:00Z", "retrieved_at": "2026-07-22T10:00:00Z", "source": "company_ir", "source_ref": "https://example.invalid/event", "evidence_state": "candidate_context_only", "reviewer": "owner"}, "catalyst_evidence.csv"),
        ("outcome", {"thesis_id": "thesis-syn1", "original_thesis_entry_id": "entry-existing", "reviewed_at": "2026-07-22T12:00:00Z", "observation_start": "2026-07-20T12:00:00Z", "observation_end": "2026-07-22T11:00:00Z", "reviewer": "owner", "outcome_state": "mixed", "summary": "Reviewed outcome.", "source": "reviewed_research_record", "source_ref": "journal://entry-existing", "source_published_at": "2026-07-22T11:00:00Z", "learning": "Separate the evidence lanes."}, "research_outcome_reviews.csv"),
    ),
)
def test_preview_maps_all_four_kinds_without_writing(tmp_path, kind, fields, destination):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    before = {path: path.read_bytes() if path.exists() else None for path in paths.all()}
    draft = build_authoring_draft(kind, profile_key="demo", ticker="syn1", fields=fields)

    preview = preview_authoring_record(
        draft,
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id=f"{kind}-generated",
    )

    assert preview.state == "reviewable"
    assert preview.profile_key == "demo"
    assert preview.ticker == "SYN1"
    assert preview.destination_label == destination
    assert preview.write_performed is False
    assert preview.receipt
    assert {path: path.read_bytes() if path.exists() else None for path in paths.all()} == before


def test_preview_rejects_cross_scope_evidence_and_outcome_references(tmp_path):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    fields = {"thesis_id": "thesis-syn1", "summary": "Evidence.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "evidence_direction": "supporting", "source": "company_ir", "source_ref": "ref", "source_published_at": "2026-07-22T09:00:00Z"}

    preview = preview_authoring_record(
        build_authoring_draft("evidence", profile_key="other", ticker="SYN1", fields=fields),
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id="evidence-generated",
    )

    assert preview.state == "rejected"
    assert preview.reason == "thesis_id must reference an existing thesis in this profile and ticker"
    assert preview.receipt == ""
```

- [ ] **Step 2: Run the tests and verify the missing-module failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'src.research_record_authoring'`.

- [ ] **Step 3: Implement immutable preview composition**

Create `src/research_record_authoring.py` with these public contracts and complete internal dispatch:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from src.catalyst_evidence_timeline import CatalystEvent, load_catalyst_events, preview_event
from src.research_outcome_review import ResearchOutcome, load_outcomes, preview_outcome
from src.research_thesis_journal import (
    JOURNAL_SCHEMA_VERSION,
    JournalEntry,
    load_journal_entries,
    validate_journal_entry,
)

RECORD_KINDS = ("thesis", "evidence", "catalyst", "outcome")


@dataclass(frozen=True)
class AuthoringPaths:
    journal: Path
    catalysts: Path
    outcomes: Path

    def all(self) -> tuple[Path, Path, Path]:
        return (self.journal, self.catalysts, self.outcomes)


@dataclass(frozen=True)
class AuthoringDraft:
    record_kind: str
    profile_key: str
    ticker: str
    fields: tuple[tuple[str, str], ...]

    def field_map(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.fields))


@dataclass(frozen=True)
class AuthoringPreview:
    state: str
    reason: str
    record_kind: str
    profile_key: str
    ticker: str
    destination_label: str
    previewed_at: str
    persisted_fields: tuple[tuple[str, str], ...]
    receipt: str
    draft_digest: str
    ledger_fingerprint: str
    record: JournalEntry | CatalystEvent | ResearchOutcome | None
    write_performed: bool = False


def build_authoring_draft(record_kind: str, *, profile_key: str, ticker: str, fields: Mapping[str, object]) -> AuthoringDraft:
    kind = str(record_kind or "").strip().lower()
    if kind not in RECORD_KINDS:
        raise ValueError(f"Unsupported record kind: {record_kind!r}")
    profile = str(profile_key or "").strip()
    symbol = str(ticker or "").strip().upper()
    if not profile:
        raise ValueError("profile_key is required")
    if not symbol:
        raise ValueError("ticker is required")
    normalized = tuple(sorted((str(key), str(value or "").strip()) for key, value in fields.items()))
    return AuthoringDraft(kind, profile, symbol, normalized)


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def authoring_draft_digest(draft: AuthoringDraft) -> str:
    return _stable_digest(asdict(draft))


def _ledger_fingerprint(path: Path) -> str:
    payload = b"missing\0" if not path.exists() else b"present\0" + path.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def _destination(draft: AuthoringDraft, paths: AuthoringPaths) -> Path:
    return paths.journal if draft.record_kind in {"thesis", "evidence"} else paths.catalysts if draft.record_kind == "catalyst" else paths.outcomes


def _scoped_theses(paths: AuthoringPaths, draft: AuthoringDraft) -> tuple[JournalEntry, ...]:
    return tuple(row for row in load_journal_entries(paths.journal) if row.entry_type == "thesis" and row.profile_key == draft.profile_key and row.ticker.upper() == draft.ticker)


def _build_record(draft: AuthoringDraft, *, previewed_at: str, generated_id: str, paths: AuthoringPaths):
    values = dict(draft.fields)
    if draft.record_kind in {"thesis", "evidence"}:
        if draft.record_kind == "evidence" and not any(row.thesis_id == values.get("thesis_id") for row in _scoped_theses(paths, draft)):
            raise ValueError("thesis_id must reference an existing thesis in this profile and ticker")
        return JournalEntry(
            schema_version=JOURNAL_SCHEMA_VERSION,
            entry_id=generated_id,
            profile_key=draft.profile_key,
            ticker=draft.ticker,
            thesis_id=values.get("thesis_id", ""),
            entry_type=draft.record_kind,
            recorded_at=previewed_at,
            effective_at=values.get("effective_at", ""),
            reviewer=values.get("reviewer", ""),
            summary=values.get("summary", ""),
            evidence_direction=values.get("evidence_direction", ""),
            source=values.get("source", ""),
            source_ref=values.get("source_ref", ""),
            source_published_at=values.get("source_published_at", ""),
            confidence=values.get("confidence", ""),
            review_due_date=values.get("review_due_date", ""),
            supersedes_entry_id=values.get("supersedes_entry_id", ""),
        )
    if draft.record_kind == "catalyst":
        return CatalystEvent(schema_version="catalyst-evidence-v1", event_id=generated_id, profile_key=draft.profile_key, ticker=draft.ticker, **values)
    theses = _scoped_theses(paths, draft)
    if not any(row.thesis_id == values.get("thesis_id") and row.entry_id == values.get("original_thesis_entry_id") for row in theses):
        raise ValueError("outcome must reference an existing thesis entry in this profile and ticker")
    return ResearchOutcome(schema_version="research-outcome-review-v1", outcome_id=generated_id, profile_key=draft.profile_key, ticker=draft.ticker, **values)


def preview_authoring_record(draft: AuthoringDraft, *, paths: AuthoringPaths, previewed_at: str, generated_id: str) -> AuthoringPreview:
    destination = _destination(draft, paths)
    draft_digest = authoring_draft_digest(draft)
    ledger_fingerprint = _ledger_fingerprint(destination)
    try:
        record = _build_record(draft, previewed_at=previewed_at, generated_id=generated_id, paths=paths)
        if isinstance(record, JournalEntry):
            validate_journal_entry(record, existing_entries=load_journal_entries(paths.journal))
        elif isinstance(record, CatalystEvent):
            event_preview = preview_event(record, existing=load_catalyst_events(paths.catalysts))
            if event_preview.state == "rejected":
                raise ValueError(event_preview.reason)
        else:
            outcome_preview = preview_outcome(record, existing=load_outcomes(paths.outcomes))
            if outcome_preview.state == "rejected":
                raise ValueError(outcome_preview.reason)
    except (OSError, ValueError) as exc:
        return AuthoringPreview("rejected", str(exc), draft.record_kind, draft.profile_key, draft.ticker, destination.name, previewed_at, (), "", draft_digest, ledger_fingerprint, None)
    persisted = tuple((key, str(value)) for key, value in asdict(record).items())
    receipt = _stable_digest({"draft": draft_digest, "ledger": ledger_fingerprint, "record": persisted, "destination": destination.name})
    return AuthoringPreview("reviewable", "", draft.record_kind, draft.profile_key, draft.ticker, destination.name, previewed_at, persisted, receipt, draft_digest, ledger_fingerprint, record)
```

The implementation must catch read/validation errors as rejected previews, but must not catch programmer errors such as an unexpected dataclass shape.

- [ ] **Step 4: Run focused preview tests**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring.py -q`

Expected: all Task 1 tests pass; no file other than the pre-seeded temporary journal changes.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add -- src/research_record_authoring.py tests/test_research_record_authoring.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Add research record authoring previews"
```

### Task 2: Exact Confirmation, Stale Receipts, And One-Ledger Dispatch

**Files:**
- Modify: `src/research_record_authoring.py`
- Modify: `tests/test_research_record_authoring.py`

**Interfaces:**
- Produces: `AuthoringSaveResult` and `confirm_authoring_preview()`.
- Consumes: the Task 1 immutable preview and the three existing append functions.
- Invariant: any context, draft, receipt, or ledger mismatch returns `preview_stale` and writes nothing.

- [ ] **Step 1: Add failing confirmation tests**

Add tests that seed a valid preview, then prove confirmation is denied without the checkbox, denied after draft edits, denied after a concurrent append, and writes only its selected ledger:

```python
from src.research_record_authoring import confirm_authoring_preview
from src.research_thesis_journal import load_journal_entries


def test_confirmation_requires_review_and_appends_exactly_one_ledger(tmp_path):
    paths = _paths(tmp_path)
    draft = build_authoring_draft("thesis", profile_key="demo", ticker="SYN1", fields={"thesis_id": "thesis-new", "summary": "Reviewed hypothesis.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "confidence": "0.60", "review_due_date": "2026-08-22", "supersedes_entry_id": ""})
    preview = preview_authoring_record(draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated")

    denied = confirm_authoring_preview(preview, current_draft=draft, paths=paths, active_profile_key="demo", active_ticker="SYN1", active_kind="thesis", confirm_reviewed=False)
    assert denied.state == "confirmation_required"
    assert not any(path.exists() for path in paths.all())

    saved = confirm_authoring_preview(preview, current_draft=draft, paths=paths, active_profile_key="demo", active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True)
    assert saved.state == "saved"
    assert saved.record_id == "thesis-generated"
    assert saved.write_performed is True
    assert [row.entry_id for row in load_journal_entries(paths.journal)] == ["thesis-generated"]
    assert not paths.catalysts.exists()
    assert not paths.outcomes.exists()


def test_changed_draft_or_ledger_invalidates_preview_without_writing(tmp_path):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    fields = {"thesis_id": "thesis-syn1", "summary": "Evidence.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "evidence_direction": "supporting", "source": "company_ir", "source_ref": "ref", "source_published_at": "2026-07-22T09:00:00Z"}
    draft = build_authoring_draft("evidence", profile_key="demo", ticker="SYN1", fields=fields)
    preview = preview_authoring_record(draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="evidence-generated")
    baseline = paths.journal.read_bytes()

    edited = build_authoring_draft("evidence", profile_key="demo", ticker="SYN1", fields={**fields, "summary": "Edited after preview."})
    stale_draft = confirm_authoring_preview(preview, current_draft=edited, paths=paths, active_profile_key="demo", active_ticker="SYN1", active_kind="evidence", confirm_reviewed=True)
    assert stale_draft.state == "preview_stale"
    assert paths.journal.read_bytes() == baseline

    append_journal_entry(paths.journal, replace(_thesis_entry(), entry_id="entry-concurrent", thesis_id="thesis-other"))
    concurrent = paths.journal.read_bytes()
    stale_ledger = confirm_authoring_preview(preview, current_draft=draft, paths=paths, active_profile_key="demo", active_ticker="SYN1", active_kind="evidence", confirm_reviewed=True)
    assert stale_ledger.state == "preview_stale"
    assert paths.journal.read_bytes() == concurrent
```

- [ ] **Step 2: Run and verify the missing-interface failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring.py -q`

Expected: import fails because `confirm_authoring_preview` does not exist.

- [ ] **Step 3: Implement exact confirmation**

Add this public contract and explicit dispatch to `src/research_record_authoring.py`:

```python
import hmac

from src.catalyst_evidence_timeline import append_reviewed_event
from src.research_outcome_review import append_reviewed_outcome
from src.research_thesis_journal import append_journal_entry


@dataclass(frozen=True)
class AuthoringSaveResult:
    state: str
    reason: str
    record_kind: str
    record_id: str
    destination_label: str
    write_performed: bool


def _record_id(record: JournalEntry | CatalystEvent | ResearchOutcome) -> str:
    if isinstance(record, JournalEntry):
        return record.entry_id
    if isinstance(record, CatalystEvent):
        return record.event_id
    return record.outcome_id


def confirm_authoring_preview(
    preview: AuthoringPreview,
    *,
    current_draft: AuthoringDraft,
    paths: AuthoringPaths,
    active_profile_key: str,
    active_ticker: str,
    active_kind: str,
    confirm_reviewed: bool,
) -> AuthoringSaveResult:
    rejected = lambda state, reason: AuthoringSaveResult(state, reason, preview.record_kind, "", preview.destination_label, False)
    if not confirm_reviewed:
        return rejected("confirmation_required", "Review and confirm the exact preview before saving.")
    if preview.state != "reviewable" or preview.record is None or not preview.receipt:
        return rejected("rejected", "Only a valid preview can be confirmed.")
    active = (str(active_profile_key or "").strip(), str(active_ticker or "").strip().upper(), str(active_kind or "").strip().lower())
    if active != (preview.profile_key, preview.ticker, preview.record_kind):
        return rejected("preview_stale", "Selected profile, ticker, or record type changed; preview again.")
    if not hmac.compare_digest(_stable_digest(asdict(current_draft)), preview.draft_digest):
        return rejected("preview_stale", "Draft changed after preview; preview again.")
    destination = _destination(current_draft, paths)
    if not hmac.compare_digest(_ledger_fingerprint(destination), preview.ledger_fingerprint):
        return rejected("preview_stale", "Ledger changed after preview; reload and preview again.")
    refreshed = preview_authoring_record(current_draft, paths=paths, previewed_at=preview.previewed_at, generated_id=_record_id(preview.record))
    if refreshed.state != "reviewable" or not hmac.compare_digest(refreshed.receipt, preview.receipt):
        return rejected("preview_stale", "Record no longer matches the validated preview; preview again.")
    try:
        if isinstance(preview.record, JournalEntry):
            append_journal_entry(paths.journal, preview.record)
        elif isinstance(preview.record, CatalystEvent):
            append_reviewed_event(paths.catalysts, preview.record, confirm_reviewed=True)
        else:
            append_reviewed_outcome(paths.outcomes, preview.record, confirm_reviewed=True)
    except (OSError, ValueError) as exc:
        return rejected("save_failed", f"Record was not saved: {exc}")
    return AuthoringSaveResult("saved", "Saved append-only reviewed record.", preview.record_kind, _record_id(preview.record), destination.name, True)
```

- [ ] **Step 4: Run focused and adjacent persistence tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring.py tests/test_research_thesis_journal.py tests/test_catalyst_evidence_timeline.py tests/test_research_outcome_review.py -q
```

Expected: all tests pass; byte assertions prove rejected confirmations are write-free.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add -- src/research_record_authoring.py tests/test_research_record_authoring.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Add exact research record confirmation"
```

### Task 3: Streamlit Composer And Session-State Contract

**Files:**
- Create: `src/research_record_authoring_ui.py`
- Create: `tests/test_research_record_authoring_ui.py`
- Create: `tests/fixtures/research_record_authoring_app.py`

**Interfaces:**
- Produces: `authoring_field_contract()`, `authoring_session_key()`, and `render_research_record_authoring()`.
- Consumes: Task 1/2 composition APIs and an injected `AuthoringPaths`.
- Invariant: widgets never receive editable profile/ticker values, and the fixture refuses paths outside the temporary directory passed by the test.
- Usability contract: controlled vocabularies use select controls, and thesis/supersession references are selected only from thesis rows in the active profile/ticker scope.

- [ ] **Step 1: Write failing field and AppTest contracts**

Add tests requiring the four record types, locked scope, source fields only where appropriate, preview-before-confirm order, and no production paths:

```python
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.research_record_authoring import AuthoringPaths
from src.research_record_authoring_ui import authoring_field_contract, authoring_session_key
from src.research_thesis_journal import JournalEntry, append_journal_entry


def _paths(tmp_path: Path) -> AuthoringPaths:
    return AuthoringPaths(tmp_path / "journal.csv", tmp_path / "catalysts.csv", tmp_path / "outcomes.csv")


def _thesis_entry() -> JournalEntry:
    return JournalEntry(
        "research-thesis-journal-v1", "entry-existing", "demo", "SYN1", "thesis-syn1", "thesis",
        "2026-07-20T12:00:00Z", "2026-07-20T11:00:00Z", "fixture-reviewer",
        "Existing synthetic thesis.", "", "", "", "", "0.50", "2026-08-20", "",
    )


def test_field_contract_is_kind_specific_and_never_exposes_scope_for_editing():
    thesis = authoring_field_contract("thesis")
    evidence = authoring_field_contract("evidence")
    catalyst = authoring_field_contract("catalyst")
    outcome = authoring_field_contract("outcome")

    assert "profile_key" not in thesis and "ticker" not in thesis
    assert tuple(thesis) == ("thesis_id", "summary", "effective_at", "reviewer", "confidence", "review_due_date", "supersedes_entry_id")
    assert {"evidence_direction", "source", "source_ref", "source_published_at"} <= set(evidence)
    assert {"event_type", "evidence_state", "retrieved_at"} <= set(catalyst)
    assert {"original_thesis_entry_id", "observation_start", "observation_end", "learning"} <= set(outcome)
    assert all("return" not in field and "skill" not in field and "rank" not in field for field in outcome)


def test_session_key_is_profile_ticker_and_kind_scoped():
    assert authoring_session_key("demo", "nvda", "preview") == "research-authoring:demo:NVDA:preview"


def test_fixture_renders_locked_scope_and_no_confirmation_before_preview(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_AUTHORING_FIXTURE_DIR", str(tmp_path))
    app = AppTest.from_file("tests/fixtures/research_record_authoring_app.py")
    app.run(timeout=20)

    assert not app.exception
    assert "Profile: demo | Ticker: SYN1" in "\n".join(item.value for item in app.markdown)
    assert any(item.label == "Validate and preview" for item in app.button)
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())


def test_fixture_uses_controlled_choices_and_scoped_thesis_references(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    monkeypatch.setenv("RESEARCH_AUTHORING_FIXTURE_DIR", str(tmp_path))
    app = AppTest.from_file("tests/fixtures/research_record_authoring_app.py").run(timeout=20)
    app.selectbox(key="research-authoring:demo:SYN1:kind").set_value("evidence").run()

    assert app.selectbox(key="research-authoring:demo:SYN1:field:evidence:thesis_id").options == ["thesis-syn1"]
    assert app.selectbox(key="research-authoring:demo:SYN1:field:evidence:evidence_direction").options == ["supporting", "conflicting", "context"]
```

- [ ] **Step 2: Verify the missing-UI-module failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring_ui.py -q`

Expected: collection fails because `src.research_record_authoring_ui` does not exist.

- [ ] **Step 3: Implement field contracts and renderer**

Create `src/research_record_authoring_ui.py` with immutable field definitions and a renderer using widgets outside a Streamlit form so every edit causes a rerun and invalidates a mismatched preview:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import uuid4

from src.research_record_authoring import (
    AuthoringPaths,
    AuthoringPreview,
    authoring_draft_digest,
    build_authoring_draft,
    confirm_authoring_preview,
    preview_authoring_record,
)

FIELD_CONTRACTS = {
    "thesis": ("thesis_id", "summary", "effective_at", "reviewer", "confidence", "review_due_date", "supersedes_entry_id"),
    "evidence": ("thesis_id", "summary", "effective_at", "reviewer", "evidence_direction", "source", "source_ref", "source_published_at"),
    "catalyst": ("event_type", "title", "summary", "effective_at", "published_at", "retrieved_at", "source", "source_ref", "evidence_state", "reviewer"),
    "outcome": ("thesis_id", "original_thesis_entry_id", "reviewed_at", "observation_start", "observation_end", "reviewer", "outcome_state", "summary", "source", "source_ref", "source_published_at", "learning"),
}

SELECT_OPTIONS = {
    "evidence_direction": ("supporting", "conflicting", "context"),
    "event_type": ("earnings", "product", "regulatory", "customer", "industry", "capital_allocation", "management", "macro"),
    "evidence_state": ("candidate_context_only", "supported", "still_blocked", "skipped", "excluded"),
    "outcome_state": ("supported", "mixed", "not_supported", "inconclusive"),
}


def authoring_field_contract(record_kind: str) -> tuple[str, ...]:
    try:
        return FIELD_CONTRACTS[record_kind]
    except KeyError as exc:
        raise ValueError(f"Unsupported record kind: {record_kind!r}") from exc


def authoring_session_key(profile_key: str, ticker: str, suffix: str) -> str:
    return f"research-authoring:{profile_key}:{ticker.upper()}:{suffix}"


def _generated_id(kind: str) -> str:
    return f"{kind}-{uuid4().hex}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _scoped_thesis_options(paths: AuthoringPaths, profile_key: str, ticker: str) -> tuple[tuple[str, str], ...]:
    from src.research_thesis_journal import load_journal_entries

    return tuple(
        (row.thesis_id, row.entry_id)
        for row in load_journal_entries(paths.journal)
        if row.entry_type == "thesis" and row.profile_key == profile_key and row.ticker.upper() == ticker.upper()
    )


def render_research_record_authoring(*, st_api: Any, profile_key: str, ticker: str, paths: AuthoringPaths) -> None:
    symbol = ticker.upper()
    with st_api.expander("Add a reviewed research record", expanded=False):
        st_api.caption(f"Profile: {profile_key} | Ticker: {symbol} — locked to this Company Workbench.")
        kind = st_api.selectbox("Record type", tuple(FIELD_CONTRACTS), format_func=str.title, key=authoring_session_key(profile_key, symbol, "kind"))
        thesis_options = _scoped_thesis_options(paths, profile_key, symbol)
        fields: dict[str, str] = {}
        for name in authoring_field_contract(kind):
            label = name.replace("_", " ").title()
            key = authoring_session_key(profile_key, symbol, f"field:{kind}:{name}")
            if name == "thesis_id" and kind in {"evidence", "outcome"}:
                fields[name] = st_api.selectbox(label, tuple(dict.fromkeys(item[0] for item in thesis_options)), key=key)
            elif name == "original_thesis_entry_id":
                fields[name] = st_api.selectbox(label, tuple(item[1] for item in thesis_options if item[0] == fields.get("thesis_id")), key=key)
            elif name == "supersedes_entry_id":
                fields[name] = st_api.selectbox(label, ("", *(item[1] for item in thesis_options)), key=key)
            elif name in SELECT_OPTIONS:
                fields[name] = st_api.selectbox(label, SELECT_OPTIONS[name], key=key)
            elif name in {"summary", "learning"}:
                fields[name] = st_api.text_area(label, key=key)
            else:
                fields[name] = st_api.text_input(label, key=key)
        draft = build_authoring_draft(kind, profile_key=profile_key, ticker=symbol, fields=fields)
        preview_key = authoring_session_key(profile_key, symbol, "preview")
        if st_api.button("Validate and preview", key=authoring_session_key(profile_key, symbol, "validate"), use_container_width=True):
            st_api.session_state[preview_key] = preview_authoring_record(draft, paths=paths, previewed_at=_utc_now(), generated_id=_generated_id(kind))
        preview: AuthoringPreview | None = st_api.session_state.get(preview_key)
        if preview is None:
            st_api.caption("No record is saved until this draft passes preview and you confirm the exact reviewed source evidence.")
            return
        if preview.draft_digest != authoring_draft_digest(draft):
            st_api.warning("Draft changed after preview. Validate and preview again before saving.")
            return
        if preview.state == "rejected":
            st_api.error(preview.reason)
            return
        st_api.markdown("#### Exact append-only preview")
        st_api.dataframe(dict(preview.persisted_fields), width="stretch")
        confirmed = st_api.checkbox("I reviewed this exact record and its source evidence", key=authoring_session_key(profile_key, symbol, "confirmed"))
        if st_api.button("Confirm and save", key=authoring_session_key(profile_key, symbol, "save"), use_container_width=True):
            result = confirm_authoring_preview(preview, current_draft=draft, paths=paths, active_profile_key=profile_key, active_ticker=symbol, active_kind=kind, confirm_reviewed=confirmed)
            if result.state == "saved":
                del st_api.session_state[preview_key]
                st_api.success(f"Saved {result.record_id}. Corrections require a new append-only record; history is never edited or deleted.")
            else:
                st_api.error(result.reason)
```

Create `tests/fixtures/research_record_authoring_app.py`:

```python
import os
from pathlib import Path

import streamlit as st

from src.research_record_authoring import AuthoringPaths
from src.research_record_authoring_ui import render_research_record_authoring

root = Path(os.environ["RESEARCH_AUTHORING_FIXTURE_DIR"]).resolve()
if not root.is_dir() or "pytest-" not in str(root):
    raise RuntimeError("The authoring fixture requires a pytest temporary directory.")
render_research_record_authoring(
    st_api=st,
    profile_key="demo",
    ticker="SYN1",
    paths=AuthoringPaths(root / "journal.csv", root / "catalysts.csv", root / "outcomes.csv"),
)
```

- [ ] **Step 4: Expand AppTest through rejected preview and successful temporary save**

Use widget keys rather than positional indexes. Enter a synthetic thesis, click `Validate and preview`, assert the exact preview and confirmation control appear while files remain absent, then check confirmation, click save, reload the temporary journal, and assert one row. Add a second test that edits the summary after preview and proves the save button is unavailable until re-preview.

- [ ] **Step 5: Run focused UI and composition tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring.py tests/test_research_record_authoring_ui.py -q
```

Expected: all tests pass; only pytest temporary directories contain new ledgers.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add -- src/research_record_authoring.py src/research_record_authoring_ui.py tests/test_research_record_authoring.py tests/test_research_record_authoring_ui.py tests/fixtures/research_record_authoring_app.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Add research record authoring composer"
```

### Task 4: Company Workbench Integration And Read-Side Reload

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_research_record_authoring_ui.py`

**Interfaces:**
- Consumes: `render_research_record_authoring()` with production paths explicitly provided by Company Workbench.
- Produces: one collapsed composer after the journal/outcome answer and before Advanced thesis history.
- Invariant: Public and Operator routes do not render an authoring composer; only Personal Research Company Workbench can invoke it.

- [ ] **Step 1: Add failing source and render contracts**

Add source-boundary assertions to `tests/test_dashboard_helpers.py`:

```python
def test_company_workbench_authoring_is_research_only_and_below_the_journal_answer():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    render_start = source.index("def render_single_stock_report(")
    render_end = source.index("def ", render_start + 4)
    render_source = source[render_start:render_end]

    assert "render_research_record_authoring" in render_source
    assert render_source.index("research_thesis_journal_html") < render_source.index("render_research_record_authoring")
    assert render_source.index("render_research_record_authoring") < render_source.index("Advanced: thesis and evidence history")
    assert "if research_mode:" in render_source
    assert "AuthoringPaths(" in render_source
```

Add a render test to `tests/test_dashboard_render_smoke.py` requiring exactly one closed `Add a reviewed research record` expander on Research Company Workbench, no expanded Advanced section, and no composer marker on the equivalent Public Single-Stock Report.

- [ ] **Step 2: Run and verify placement failures**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py -k research_record_authoring -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_render_smoke.py -k authoring -q
```

Expected: failures show the renderer import/call and route marker are absent.

- [ ] **Step 3: Wire the composer into Company Workbench**

Add imports:

```python
from src.research_record_authoring import AuthoringPaths
from src.research_record_authoring_ui import render_research_record_authoring
```

Immediately after `outcome_status_cards()` and before `Advanced: thesis and evidence history`, add:

```python
if research_mode:
    render_research_record_authoring(
        st_api=st,
        profile_key=selected_context.profile_key,
        ticker=ticker,
        paths=AuthoringPaths(
            journal=DATA_DIR / "research_thesis_journal.csv",
            catalysts=DATA_DIR / "catalyst_evidence.csv",
            outcomes=DATA_DIR / "research_outcome_reviews.csv",
        ),
    )
```

Do not add the renderer to Public or Operator branches. After a successful save, call `st.rerun()` only after the success receipt has been placed in session state; on the next run, reload all three existing read-side states and show the receipt once. The UI module must never claim persistence solely from the prior button callback.

- [ ] **Step 4: Add read-side reload test**

In the test-only fixture, confirm a record, rerun AppTest, and assert the saved receipt is displayed only when `load_journal_entries()` contains the record identifier. Delete the temporary row before rerun in a separate test and assert the UI reports `Saved record could not be reloaded; review the ledger` instead of a success claim.

- [ ] **Step 5: Run focused Workbench tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring.py tests/test_research_record_authoring_ui.py tests/test_dashboard_helpers.py -k 'authoring or research_thesis' -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_render_smoke.py -q
```

Expected: all focused tests pass, Public and Operator routes contain no composer, and no repository ledger changes.

- [ ] **Step 6: Commit Task 4**

Run:

```bash
git add -- src/dashboard.py src/research_record_authoring_ui.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_research_record_authoring_ui.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Integrate research authoring in Company Workbench"
```

### Task 5: Responsive Workflow Evidence And Release Documentation

**Files:**
- Modify: `src/browser_qa_evidence.py`
- Modify: `tests/test_browser_qa_evidence.py`
- Modify: `README.md`
- Modify: `docs/PRODUCT_SPEC.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-07-22-in-app-research-record-authoring-design.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Produces: truthful release and responsive evidence for the completed Priority 3 implementation.
- Consumes: current runtime results only; screenshots remain route-marker evidence, not proof that a record was persisted.
- Invariant: Priority 4 becomes the earliest incomplete lane only after every Priority 3 acceptance criterion has direct current evidence.

- [ ] **Step 1: Add failing browser and documentation contracts**

Require the Research Company Workbench route to include `Add a reviewed research record` under its details boundary and a stop rule that rejects any visible confirmation before preview. Require README/Product Spec/Roadmap/continuation docs to state:

- all four record types are available;
- exact preview and explicit confirmation are required;
- drafts are untrusted and preview receipts are session-only;
- production tests do not append repository ledgers;
- saves cannot change readiness, forecasts, probabilities, recommendations, or another ledger; and
- Priority 3 is complete locally while Priority 4 is next and still requires a permitted point-in-time dataset for exit.

Use exact assertions in `tests/test_public_v1_release_docs.py`; do not use broad keyword-count assertions.

- [ ] **Step 2: Run and verify documentation failures**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_browser_qa_evidence.py tests/test_public_v1_release_docs.py -q
```

Expected: failures name the missing implemented-status and responsive-authoring contracts.

- [ ] **Step 3: Update evidence and documentation**

Update the Company Workbench browser-QA row to keep the composer below the primary answer and collapsed by default. State explicitly that route-marker screenshots do not prove validation, confirmation, or persistence; the temporary-ledger AppTest and direct persistence tests provide that evidence.

Update the design `Status` and add an `Implementation Evidence` section containing commit identifiers only after those commits exist. Update `ROADMAP.md` and the continuation prompt to mark Priority 3 complete locally only after desktop/phone route review and all automated acceptance tests pass.

- [ ] **Step 4: Run the complete required verification matrix**

Run each command and record the actual result:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_record_authoring.py tests/test_research_record_authoring_ui.py tests/test_research_thesis_journal.py tests/test_catalyst_evidence_timeline.py tests/test_research_outcome_review.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_browser_qa_evidence.py tests/test_public_v1_release_docs.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make linkedin-share-check
make browser-qa-evidence
make pilot-readiness-check TOP_N=10
make commercial-beta-release-check
make diff-hygiene-summary
git diff --check
```

Expected: focused and full tests pass; all read-only release gates pass; pilot readiness may remain truthfully blocked on external/source-depth gates; diff hygiene reports only intentional product files plus the same excluded generated churn.

- [ ] **Step 5: Perform live desktop and phone review**

Open `http://localhost:8501/?mode=research&page=company-workbench&ticker=NVDA&open=1` at `1280x720` and `390x844`. Verify:

1. The primary selected-company answer precedes the collapsed composer.
2. The composer opens without horizontal overflow.
3. Locked profile/ticker and the four record types are understandable.
4. Invalid source/timestamp input shows a field-level rejection and writes nothing.
5. Editing after preview removes or blocks confirmation until re-preview.
6. A successful persistence rehearsal uses only the test fixture with temporary ledgers, never the production NVDA ledger.
7. Advanced evidence stays collapsed and the Research Conclusion/Next Research Task remain below the journal workflow.

Record measurements and text findings in the design's `Implementation Evidence` section. Keep screenshots ephemeral and unstaged.

- [ ] **Step 6: Stage exact files and commit the release slice**

Run `git status --short`, review every intentional path, then stage only the implementation/docs/tests named by `git diff --name-only`:

```bash
git add -- src/research_record_authoring.py src/research_record_authoring_ui.py src/dashboard.py src/browser_qa_evidence.py tests/test_research_record_authoring.py tests/test_research_record_authoring_ui.py tests/fixtures/research_record_authoring_app.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_browser_qa_evidence.py tests/test_public_v1_release_docs.py README.md docs/PRODUCT_SPEC.md ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/superpowers/specs/2026-07-22-in-app-research-record-authoring-design.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Complete in-app research record authoring"
```

If a listed file is unchanged, omit it from the exact `git add --` command rather than staging a broader path.

- [ ] **Step 7: Push, update draft PR #113, and require exact-head CI**

Run:

```bash
git push origin codex/personal-research-mode-mvp
gh pr view 113 --json state,isDraft,mergeable,headRefOid,statusCheckRollup,url
gh pr checks 113 --watch --interval 20
```

Update the draft PR with the exact commit, test counts, runtime evidence, generated-artifact exclusion, and remaining external gates. Confirm the PR remains open and draft and the successful hosted check's head SHA equals local `HEAD`.

- [ ] **Step 8: Rescan Priorities 1-10**

Run the current roadmap/status/hygiene checks. If Priority 3 has direct evidence for every acceptance criterion, select Priority 4's earliest safe local contract slice. Do not call Priority 4 complete without one bounded permitted real point-in-time dataset that passes rights, identity, corporate-action, delisting, survivorship, cutoff, reproduction, and leakage gates.
