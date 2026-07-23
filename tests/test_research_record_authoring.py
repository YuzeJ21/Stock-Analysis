import csv
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from src import research_record_authoring
from src import research_ledger_lock
from src.research_record_authoring import (
    AuthoringPaths,
    build_authoring_draft,
    confirm_authoring_preview,
    preview_authoring_record,
)
from src.research_thesis_journal import JournalEntry, append_journal_entry, load_journal_entries
from src.catalyst_evidence_timeline import CatalystEvent, append_reviewed_event
from src.research_outcome_review import ResearchOutcome, append_reviewed_outcome


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


@pytest.mark.parametrize(
    ("kind", "ledger_name", "fields"),
    (
        (
            "catalyst",
            "catalysts",
            {
                "event_type": "earnings",
                "title": "Scheduled results",
                "summary": "Reviewed event context.",
                "effective_at": "2026-08-20T21:00:00Z",
                "published_at": "2026-07-22T09:00:00Z",
                "retrieved_at": "2026-07-22T10:00:00Z",
                "source": "company_ir",
                "source_ref": "https://example.invalid/event",
                "evidence_state": "candidate_context_only",
                "reviewer": "owner",
            },
        ),
        (
            "outcome",
            "outcomes",
            {
                "thesis_id": "thesis-syn1",
                "original_thesis_entry_id": "entry-existing",
                "reviewed_at": "2026-07-22T12:00:00Z",
                "observation_start": "2026-07-20T12:00:00Z",
                "observation_end": "2026-07-22T11:00:00Z",
                "reviewer": "owner",
                "outcome_state": "mixed",
                "summary": "Reviewed outcome.",
                "source": "reviewed_research_record",
                "source_ref": "journal://entry-existing",
                "source_published_at": "2026-07-22T11:00:00Z",
                "learning": "Separate the evidence lanes.",
            },
        ),
    ),
)
def test_preview_rejects_malformed_destination_ledger(tmp_path, kind, ledger_name, fields):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    getattr(paths, ledger_name).write_bytes(b"\xff")

    preview = preview_authoring_record(
        build_authoring_draft(kind, profile_key="demo", ticker="SYN1", fields=fields),
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id=f"{kind}-generated",
    )

    assert preview.state == "rejected"
    assert preview.receipt == ""


@pytest.mark.parametrize(
    ("kind", "loader_name", "fields"),
    (
        (
            "catalyst",
            "load_catalyst_events",
            {
                "event_type": "earnings",
                "title": "Scheduled results",
                "summary": "Reviewed event context.",
                "effective_at": "2026-08-20T21:00:00Z",
                "published_at": "2026-07-22T09:00:00Z",
                "retrieved_at": "2026-07-22T10:00:00Z",
                "source": "company_ir",
                "source_ref": "https://example.invalid/event",
                "evidence_state": "candidate_context_only",
                "reviewer": "owner",
            },
        ),
        (
            "outcome",
            "load_outcomes",
            {
                "thesis_id": "thesis-syn1",
                "original_thesis_entry_id": "entry-existing",
                "reviewed_at": "2026-07-22T12:00:00Z",
                "observation_start": "2026-07-20T12:00:00Z",
                "observation_end": "2026-07-22T11:00:00Z",
                "reviewer": "owner",
                "outcome_state": "mixed",
                "summary": "Reviewed outcome.",
                "source": "reviewed_research_record",
                "source_ref": "journal://entry-existing",
                "source_published_at": "2026-07-22T11:00:00Z",
                "learning": "Separate the evidence lanes.",
            },
        ),
    ),
)
def test_preview_rejects_destination_ledger_csv_errors(tmp_path, monkeypatch, kind, loader_name, fields):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())

    def raise_csv_error(_path):
        raise csv.Error("malformed destination ledger")

    monkeypatch.setattr(research_record_authoring, loader_name, raise_csv_error)

    preview = preview_authoring_record(
        build_authoring_draft(kind, profile_key="demo", ticker="SYN1", fields=fields),
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id=f"{kind}-generated",
    )

    assert preview.state == "rejected"
    assert preview.reason == "malformed destination ledger"
    assert preview.receipt == ""


@pytest.mark.parametrize("profile_key, ticker", (("other", "SYN1"), ("demo", "OTHER")))
def test_preview_rejects_cross_scope_outcome_thesis_reference(tmp_path, profile_key, ticker):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    fields = {
        "thesis_id": "thesis-syn1",
        "original_thesis_entry_id": "entry-existing",
        "reviewed_at": "2026-07-22T12:00:00Z",
        "observation_start": "2026-07-20T12:00:00Z",
        "observation_end": "2026-07-22T11:00:00Z",
        "reviewer": "owner",
        "outcome_state": "mixed",
        "summary": "Reviewed outcome.",
        "source": "reviewed_research_record",
        "source_ref": "journal://entry-existing",
        "source_published_at": "2026-07-22T11:00:00Z",
        "learning": "Separate the evidence lanes.",
    }

    preview = preview_authoring_record(
        build_authoring_draft("outcome", profile_key=profile_key, ticker=ticker, fields=fields),
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id="outcome-generated",
    )

    assert preview.state == "rejected"
    assert preview.reason == "outcome must reference an existing thesis entry in this profile and ticker"
    assert preview.receipt == ""


def test_preview_propagates_programmer_errors(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    draft = build_authoring_draft(
        "thesis",
        profile_key="demo",
        ticker="SYN1",
        fields={"thesis_id": "thesis-new"},
    )

    def raise_programmer_error(*_args, **_kwargs):
        raise TypeError("unexpected dataclass shape")

    monkeypatch.setattr(research_record_authoring, "_build_record", raise_programmer_error)

    with pytest.raises(TypeError, match="unexpected dataclass shape"):
        preview_authoring_record(
            draft,
            paths=paths,
            previewed_at="2026-07-22T12:30:00Z",
            generated_id="thesis-generated",
        )


def test_confirmation_requires_review_and_appends_exactly_one_ledger(tmp_path):
    paths = _paths(tmp_path)
    draft = build_authoring_draft(
        "thesis",
        profile_key="demo",
        ticker="SYN1",
        fields={
            "thesis_id": "thesis-new",
            "summary": "Reviewed hypothesis.",
            "effective_at": "2026-07-22T10:00:00Z",
            "reviewer": "owner",
            "confidence": "0.60",
            "review_due_date": "2026-08-22",
            "supersedes_entry_id": "",
        },
    )
    preview = preview_authoring_record(
        draft,
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id="thesis-generated",
    )

    denied = confirm_authoring_preview(
        preview,
        current_draft=draft,
        paths=paths,
        active_profile_key="demo",
        active_ticker="SYN1",
        active_kind="thesis",
        confirm_reviewed=False,
    )

    assert denied.state == "confirmation_required"
    assert not any(path.exists() for path in paths.all())

    saved = confirm_authoring_preview(
        preview,
        current_draft=draft,
        paths=paths,
        active_profile_key="demo",
        active_ticker="SYN1",
        active_kind="thesis",
        confirm_reviewed=True,
    )

    assert saved.state == "saved"
    assert saved.record_id == "thesis-generated"
    assert saved.write_performed is True
    assert [row.entry_id for row in load_journal_entries(paths.journal)] == ["thesis-generated"]
    assert not paths.catalysts.exists()
    assert not paths.outcomes.exists()


def test_changed_draft_or_ledger_invalidates_preview_without_writing(tmp_path):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    fields = {
        "thesis_id": "thesis-syn1",
        "summary": "Evidence.",
        "effective_at": "2026-07-22T10:00:00Z",
        "reviewer": "owner",
        "evidence_direction": "supporting",
        "source": "company_ir",
        "source_ref": "ref",
        "source_published_at": "2026-07-22T09:00:00Z",
    }
    draft = build_authoring_draft("evidence", profile_key="demo", ticker="SYN1", fields=fields)
    preview = preview_authoring_record(
        draft,
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id="evidence-generated",
    )
    baseline = paths.journal.read_bytes()

    edited = build_authoring_draft(
        "evidence",
        profile_key="demo",
        ticker="SYN1",
        fields={**fields, "summary": "Edited after preview."},
    )
    stale_draft = confirm_authoring_preview(
        preview,
        current_draft=edited,
        paths=paths,
        active_profile_key="demo",
        active_ticker="SYN1",
        active_kind="evidence",
        confirm_reviewed=True,
    )

    assert stale_draft.state == "preview_stale"
    assert paths.journal.read_bytes() == baseline

    append_journal_entry(
        paths.journal,
        replace(_thesis_entry(), entry_id="entry-concurrent", thesis_id="thesis-other"),
    )
    concurrent = paths.journal.read_bytes()
    stale_ledger = confirm_authoring_preview(
        preview,
        current_draft=draft,
        paths=paths,
        active_profile_key="demo",
        active_ticker="SYN1",
        active_kind="evidence",
        confirm_reviewed=True,
    )

    assert stale_ledger.state == "preview_stale"
    assert paths.journal.read_bytes() == concurrent


@pytest.mark.parametrize(
    ("kind", "fields", "ledger_name"),
    (
        (
            "catalyst",
            {
                "event_type": "earnings",
                "title": "Scheduled results",
                "summary": "Reviewed event context.",
                "effective_at": "2026-08-20T21:00:00Z",
                "published_at": "2026-07-22T09:00:00Z",
                "retrieved_at": "2026-07-22T10:00:00Z",
                "source": "company_ir",
                "source_ref": "https://example.invalid/event",
                "evidence_state": "candidate_context_only",
                "reviewer": "owner",
            },
            "catalysts",
        ),
        (
            "outcome",
            {
                "thesis_id": "thesis-syn1",
                "original_thesis_entry_id": "entry-existing",
                "reviewed_at": "2026-07-22T12:00:00Z",
                "observation_start": "2026-07-20T12:00:00Z",
                "observation_end": "2026-07-22T11:00:00Z",
                "reviewer": "owner",
                "outcome_state": "mixed",
                "summary": "Reviewed outcome.",
                "source": "reviewed_research_record",
                "source_ref": "journal://entry-existing",
                "source_published_at": "2026-07-22T11:00:00Z",
                "learning": "Separate the evidence lanes.",
            },
            "outcomes",
        ),
    ),
)
def test_confirmation_dispatches_selected_nonjournal_ledger_only(tmp_path, kind, fields, ledger_name):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    draft = build_authoring_draft(kind, profile_key="demo", ticker="SYN1", fields=fields)
    preview = preview_authoring_record(
        draft,
        paths=paths,
        previewed_at="2026-07-22T12:30:00Z",
        generated_id=f"{kind}-generated",
    )

    saved = confirm_authoring_preview(
        preview,
        current_draft=draft,
        paths=paths,
        active_profile_key="demo",
        active_ticker="SYN1",
        active_kind=kind,
        confirm_reviewed=True,
    )

    assert saved.state == "saved"
    assert getattr(paths, ledger_name).exists()
    assert paths.journal.exists()
    assert (paths.outcomes if ledger_name != "outcomes" else paths.catalysts).exists() is False


@pytest.mark.parametrize("active_profile_key, active_ticker, active_kind", (("other", "SYN1", "thesis"), ("demo", "OTHER", "thesis"), ("demo", "SYN1", "evidence")))
def test_confirmation_rejects_changed_context_without_writing(tmp_path, active_profile_key, active_ticker, active_kind):
    paths = _paths(tmp_path)
    draft = build_authoring_draft("thesis", profile_key="demo", ticker="SYN1", fields={"thesis_id": "thesis-new", "summary": "Reviewed hypothesis.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "confidence": "0.60", "review_due_date": "2026-08-22"})
    preview = preview_authoring_record(draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated")

    stale = confirm_authoring_preview(preview, current_draft=draft, paths=paths, active_profile_key=active_profile_key, active_ticker=active_ticker, active_kind=active_kind, confirm_reviewed=True)

    assert stale.state == "preview_stale"
    assert not any(path.exists() for path in paths.all())


def test_confirmation_rejects_tampered_receipt_without_writing(tmp_path):
    paths = _paths(tmp_path)
    draft = build_authoring_draft("thesis", profile_key="demo", ticker="SYN1", fields={"thesis_id": "thesis-new", "summary": "Reviewed hypothesis.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "confidence": "0.60", "review_due_date": "2026-08-22"})
    preview = preview_authoring_record(draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated")

    stale = confirm_authoring_preview(replace(preview, receipt="tampered"), current_draft=draft, paths=paths, active_profile_key="demo", active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True)

    assert stale.state == "preview_stale"
    assert not any(path.exists() for path in paths.all())


def test_confirmation_propagates_programmer_errors(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    draft = build_authoring_draft("thesis", profile_key="demo", ticker="SYN1", fields={"thesis_id": "thesis-new", "summary": "Reviewed hypothesis.", "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner", "confidence": "0.60", "review_due_date": "2026-08-22"})
    preview = preview_authoring_record(draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated")

    def raise_programmer_error(*_args, **_kwargs):
        raise TypeError("unexpected append contract")

    monkeypatch.setattr(research_record_authoring, "append_journal_entry", raise_programmer_error)

    with pytest.raises(TypeError, match="unexpected append contract"):
        confirm_authoring_preview(preview, current_draft=draft, paths=paths, active_profile_key="demo", active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True)


def test_confirmation_rejects_a_same_name_ledger_at_a_different_resolved_path(tmp_path):
    paths = _paths(tmp_path)
    draft = build_authoring_draft(
        "thesis", profile_key="demo", ticker="SYN1", fields={
            "thesis_id": "thesis-new", "summary": "Reviewed hypothesis.",
            "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner",
            "confidence": "0.60", "review_due_date": "2026-08-22",
        },
    )
    preview = preview_authoring_record(
        draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated"
    )
    redirected = replace(paths, journal=tmp_path / "redirected" / paths.journal.name)

    result = confirm_authoring_preview(
        preview, current_draft=draft, paths=redirected, active_profile_key="demo",
        active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True,
    )

    assert result.state == "preview_stale"
    assert not redirected.journal.exists()


def test_confirmation_rejects_a_write_injected_after_preview_recomputation(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    draft = build_authoring_draft(
        "evidence", profile_key="demo", ticker="SYN1", fields={
            "thesis_id": "thesis-syn1", "summary": "Evidence.",
            "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner",
            "evidence_direction": "supporting", "source": "company_ir", "source_ref": "ref",
            "source_published_at": "2026-07-22T09:00:00Z",
        },
    )
    preview = preview_authoring_record(
        draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="evidence-generated"
    )
    preview_original = research_record_authoring.preview_authoring_record

    def preview_then_append(*args, **kwargs):
        refreshed = preview_original(*args, **kwargs)
        append_journal_entry(
            paths.journal,
            replace(_thesis_entry(), entry_id="entry-injected", thesis_id="thesis-injected"),
        )
        return refreshed

    monkeypatch.setattr(research_record_authoring, "preview_authoring_record", preview_then_append)
    result = confirm_authoring_preview(
        preview, current_draft=draft, paths=paths, active_profile_key="demo",
        active_ticker="SYN1", active_kind="evidence", confirm_reviewed=True,
    )

    assert result.state == "preview_stale"
    assert [entry.entry_id for entry in load_journal_entries(paths.journal)] == [
        "entry-existing", "entry-injected"
    ]


def test_confirmation_rejects_a_non_reviewable_preview_without_writing(tmp_path):
    paths = _paths(tmp_path)
    draft = build_authoring_draft("thesis", profile_key="demo", ticker="SYN1", fields={"thesis_id": "thesis-new"})
    preview = preview_authoring_record(
        draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated"
    )

    result = confirm_authoring_preview(
        preview, current_draft=draft, paths=paths, active_profile_key="demo",
        active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True,
    )

    assert result.state == "rejected"
    assert not any(path.exists() for path in paths.all())


def test_confirmation_reports_save_failed_when_the_append_engine_fails(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    draft = build_authoring_draft(
        "thesis", profile_key="demo", ticker="SYN1", fields={
            "thesis_id": "thesis-new", "summary": "Reviewed hypothesis.",
            "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner",
            "confidence": "0.60", "review_due_date": "2026-08-22",
        },
    )
    preview = preview_authoring_record(
        draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated"
    )
    monkeypatch.setattr(research_record_authoring, "append_journal_entry", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk unavailable")))

    result = confirm_authoring_preview(
        preview, current_draft=draft, paths=paths, active_profile_key="demo",
        active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True,
    )

    assert result.state == "save_failed"
    assert result.write_performed is False
    assert not paths.journal.exists()


@pytest.mark.parametrize(
    ("module", "append", "path_name", "row"),
    (
        (
            "research_thesis_journal", append_journal_entry, "journal.csv", _thesis_entry(),
        ),
        (
            "catalyst_evidence_timeline", append_reviewed_event, "catalysts.csv",
            CatalystEvent("catalyst-evidence-v1", "event-lock", "demo", "SYN1", "earnings", "Results", "2026-08-20T21:00:00Z", "2026-07-22T09:00:00Z", "2026-07-22T10:00:00Z", "company_ir", "https://example.invalid/event", "candidate_context_only", "owner", "Context."),
        ),
        (
            "research_outcome_review", append_reviewed_outcome, "outcomes.csv",
            ResearchOutcome("research-outcome-review-v1", "outcome-lock", "demo", "SYN1", "thesis-syn1", "entry-existing", "2026-07-22T12:00:00Z", "2026-07-20T12:00:00Z", "2026-07-22T11:00:00Z", "owner", "mixed", "Outcome.", "reviewed_research_record", "journal://entry-existing", "2026-07-22T11:00:00Z", "Learning."),
        ),
    ),
)
def test_direct_append_engines_participate_in_the_shared_ledger_lock(tmp_path, monkeypatch, module, append, path_name, row):
    imported = __import__(f"src.{module}", fromlist=["ledger_write_lock"])
    locked: list[Path] = []

    @contextmanager
    def probe(path):
        locked.append(Path(path))
        yield

    monkeypatch.setattr(imported, "ledger_write_lock", probe)
    kwargs = {} if module == "research_thesis_journal" else {"confirm_reviewed": True}
    append(tmp_path / path_name, row, **kwargs)

    assert locked == [tmp_path / path_name]


def test_shared_ledger_lock_releases_its_thread_state_when_lock_acquisition_fails(tmp_path, monkeypatch):
    destination = tmp_path / "journal.csv"
    lock_path = tmp_path / "lock-artifact"
    monkeypatch.setattr(research_ledger_lock, "_lock_artifact", lambda _path: lock_path)
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("lock unavailable")))

    with pytest.raises(OSError, match="lock unavailable"):
        with research_ledger_lock.ledger_write_lock(destination):
            pass

    state = research_ledger_lock._states[str(research_ledger_lock.resolve_ledger_path(destination))]
    assert state.depth == 0
    assert state.handle is None


def test_confirmation_fails_closed_when_the_shared_lock_cannot_be_acquired(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    draft = build_authoring_draft(
        "thesis", profile_key="demo", ticker="SYN1", fields={
            "thesis_id": "thesis-new", "summary": "Reviewed hypothesis.",
            "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner",
            "confidence": "0.60", "review_due_date": "2026-08-22",
        },
    )
    preview = preview_authoring_record(
        draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated"
    )

    @contextmanager
    def unavailable_lock(_path):
        raise OSError("lock unavailable")
        yield

    monkeypatch.setattr(research_record_authoring, "ledger_write_lock", unavailable_lock)
    result = confirm_authoring_preview(
        preview, current_draft=draft, paths=paths, active_profile_key="demo",
        active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True,
    )

    assert result.state == "save_failed"
    assert result.record_id == ""
    assert not paths.journal.exists()


def test_confirmation_requires_read_side_reload_when_lock_teardown_fails_after_append(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    draft = build_authoring_draft(
        "thesis", profile_key="demo", ticker="SYN1", fields={
            "thesis_id": "thesis-new", "summary": "Reviewed hypothesis.",
            "effective_at": "2026-07-22T10:00:00Z", "reviewer": "owner",
            "confidence": "0.60", "review_due_date": "2026-08-22",
        },
    )
    preview = preview_authoring_record(
        draft, paths=paths, previewed_at="2026-07-22T12:30:00Z", generated_id="thesis-generated"
    )

    @contextmanager
    def teardown_failure(path):
        yield Path(path)
        raise OSError("unlock unavailable")

    monkeypatch.setattr(research_record_authoring, "ledger_write_lock", teardown_failure)
    result = confirm_authoring_preview(
        preview, current_draft=draft, paths=paths, active_profile_key="demo",
        active_ticker="SYN1", active_kind="thesis", confirm_reviewed=True,
    )

    assert result.state == "save_pending_reload"
    assert result.record_id == "thesis-generated"
    assert result.write_performed is False
    assert [entry.entry_id for entry in load_journal_entries(paths.journal)] == ["thesis-generated"]
