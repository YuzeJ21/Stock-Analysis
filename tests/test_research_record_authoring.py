import csv
from pathlib import Path

import pytest

from src import research_record_authoring
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
