import csv
from pathlib import Path

import pytest

from src.research_thesis_journal import (
    JOURNAL_COLUMNS,
    JournalEntry,
    append_journal_entry,
    derive_journal_state,
    load_journal_entries,
    main,
    preview_journal_entry,
    render_journal_state,
    validate_journal_entry,
)


def _entry(**overrides) -> JournalEntry:
    values = {
        "schema_version": "research-thesis-journal-v1",
        "entry_id": "entry-001",
        "profile_key": "demo",
        "ticker": "SYN1",
        "thesis_id": "thesis-syn1",
        "entry_type": "thesis",
        "recorded_at": "2026-07-15T20:00:00Z",
        "effective_at": "2026-07-15T19:00:00Z",
        "reviewer": "fixture-reviewer",
        "summary": "Test-only hypothesis for the synthetic fixture.",
        "evidence_direction": "",
        "source": "reviewer_authored",
        "source_ref": "review:SYN1:2026-07-15",
        "source_published_at": "2026-07-15T19:00:00Z",
        "confidence": "0.55",
        "review_due_date": "2026-08-15",
        "supersedes_entry_id": "",
    }
    values.update(overrides)
    return JournalEntry(**values)


def test_tracked_journal_header_matches_contract():
    with Path("data/research_thesis_journal.csv").open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == list(JOURNAL_COLUMNS)


def test_append_preserves_history_and_rejects_duplicate_entry_ids(tmp_path):
    ledger = tmp_path / "research_thesis_journal.csv"
    first = _entry()

    append_journal_entry(ledger, first)

    with pytest.raises(ValueError, match="entry_id already exists"):
        append_journal_entry(ledger, first)

    assert load_journal_entries(ledger) == (first,)


def test_evidence_requires_direction_and_durable_source_provenance():
    evidence = _entry(
        entry_id="evidence-001",
        entry_type="evidence",
        evidence_direction="",
        source="",
        source_ref="",
        source_published_at="",
        confidence="",
        supersedes_entry_id="",
    )

    with pytest.raises(ValueError, match="evidence_direction"):
        validate_journal_entry(evidence, existing_entries=())

    with pytest.raises(ValueError, match="source, source_ref, and source_published_at"):
        validate_journal_entry(
            JournalEntry(**{**evidence.__dict__, "evidence_direction": "supporting"}),
            existing_entries=(),
        )


def test_future_effective_or_source_timestamp_is_rejected():
    with pytest.raises(ValueError, match="effective_at cannot be after recorded_at"):
        validate_journal_entry(
            _entry(effective_at="2026-07-16T00:00:00Z"),
            existing_entries=(),
        )

    with pytest.raises(ValueError, match="source_published_at cannot be after recorded_at"):
        validate_journal_entry(
            _entry(source_published_at="2026-07-16T00:00:00Z"),
            existing_entries=(),
        )


@pytest.mark.parametrize("confidence", ["-0.01", "1.01", "not-a-number"])
def test_confidence_must_be_a_decimal_from_zero_through_one(confidence):
    with pytest.raises(ValueError, match="confidence"):
        validate_journal_entry(_entry(confidence=confidence), existing_entries=())


def test_thesis_revision_requires_same_profile_ticker_and_thesis(tmp_path):
    original = _entry()
    ledger = tmp_path / "research_thesis_journal.csv"
    append_journal_entry(ledger, original)

    wrong_profile = _entry(
        entry_id="entry-002",
        profile_key="local",
        supersedes_entry_id=original.entry_id,
    )
    with pytest.raises(ValueError, match="same profile, ticker, and thesis"):
        append_journal_entry(ledger, wrong_profile)

    revision = _entry(
        entry_id="entry-003",
        recorded_at="2026-07-16T20:00:00Z",
        effective_at="2026-07-16T19:00:00Z",
        source_published_at="2026-07-16T19:00:00Z",
        summary="Revised test-only hypothesis.",
        confidence="0.60",
        supersedes_entry_id=original.entry_id,
    )
    append_journal_entry(ledger, revision)

    state = derive_journal_state(
        load_journal_entries(ledger),
        profile_key="demo",
        ticker="SYN1",
        as_of="2026-07-17T00:00:00Z",
    )
    assert state.current_thesis == revision
    assert state.thesis_revision_count == 1
    assert state.confidence_history == ((original.recorded_at, 0.55), (revision.recorded_at, 0.60))


def test_second_active_thesis_must_revise_the_exact_active_lineage(tmp_path):
    ledger = tmp_path / "research_thesis_journal.csv"
    original = _entry()
    append_journal_entry(ledger, original)

    unrelated = _entry(
        entry_id="entry-unrelated",
        thesis_id="thesis-unrelated",
        recorded_at="2026-07-16T20:00:00Z",
        effective_at="2026-07-16T19:00:00Z",
        source_published_at="2026-07-16T19:00:00Z",
        supersedes_entry_id="",
    )
    with pytest.raises(ValueError, match="must supersede the active thesis entry"):
        append_journal_entry(ledger, unrelated)

    wrong_lineage = _entry(
        entry_id="entry-wrong-lineage",
        thesis_id="thesis-unrelated",
        recorded_at="2026-07-16T20:00:00Z",
        effective_at="2026-07-16T19:00:00Z",
        source_published_at="2026-07-16T19:00:00Z",
        supersedes_entry_id=original.entry_id,
    )
    with pytest.raises(ValueError, match="must preserve the active thesis_id"):
        append_journal_entry(ledger, wrong_lineage)

    revision = _entry(
        entry_id="entry-revision",
        recorded_at="2026-07-16T20:00:00Z",
        effective_at="2026-07-16T19:00:00Z",
        source_published_at="2026-07-16T19:00:00Z",
        summary="Reviewed revision on the preserved thesis lineage.",
        supersedes_entry_id=original.entry_id,
    )
    append_journal_entry(ledger, revision)

    reloaded = load_journal_entries(ledger)
    state = derive_journal_state(
        reloaded,
        profile_key="demo",
        ticker="SYN1",
        as_of="2026-07-17T00:00:00Z",
    )
    assert state.current_thesis == revision
    assert state.current_thesis.thesis_id == original.thesis_id
    assert state.thesis_revision_count == 1


def test_derived_state_is_strictly_profile_and_ticker_scoped():
    entries = (
        _entry(entry_id="demo-syn1"),
        _entry(entry_id="local-syn1", profile_key="local"),
        _entry(entry_id="demo-syn2", ticker="SYN2", thesis_id="thesis-syn2"),
    )

    state = derive_journal_state(entries, profile_key="demo", ticker="SYN1", as_of="2026-07-16T00:00:00Z")

    assert [entry.entry_id for entry in state.entries] == ["demo-syn1"]
    assert state.profile_key == "demo"
    assert state.ticker == "SYN1"


def test_invalidation_and_conflicting_evidence_keep_journal_incomplete_until_recorded():
    thesis = _entry()
    supporting = _entry(
        entry_id="evidence-support",
        entry_type="evidence",
        evidence_direction="supporting",
        confidence="",
        supersedes_entry_id="",
    )
    conflicting = _entry(
        entry_id="evidence-conflict",
        entry_type="evidence",
        evidence_direction="conflicting",
        confidence="",
        supersedes_entry_id="",
    )

    incomplete = derive_journal_state(
        (thesis, supporting, conflicting),
        profile_key="demo",
        ticker="SYN1",
        as_of="2026-07-16T00:00:00Z",
    )
    assert incomplete.status == "incomplete"
    assert len(incomplete.supporting_evidence) == 1
    assert len(incomplete.conflicting_evidence) == 1

    invalidation = _entry(
        entry_id="invalidation-001",
        entry_type="invalidation",
        evidence_direction="context",
        confidence="",
        supersedes_entry_id="",
        summary="Invalidate if the source-backed operating assumption no longer holds.",
    )
    complete = derive_journal_state(
        (thesis, supporting, conflicting, invalidation),
        profile_key="demo",
        ticker="SYN1",
        as_of="2026-07-16T00:00:00Z",
    )
    assert complete.status == "current"
    assert complete.invalidation_conditions == (invalidation,)


def test_empty_journal_renders_not_started_without_generated_thesis():
    state = derive_journal_state((), profile_key="demo", ticker="SYN1", as_of="2026-07-16T00:00:00Z")

    rendered = render_journal_state(state)

    assert "Status: not_started" in rendered
    assert "No reviewed thesis is recorded" in rendered
    assert "Record a reviewed hypothesis" in rendered


def test_incomplete_and_overdue_states_explain_the_exact_next_research_action():
    incomplete = derive_journal_state(
        (_entry(),),
        profile_key="demo",
        ticker="SYN1",
        as_of="2026-07-16T00:00:00Z",
    )
    assert "Record at least one source-backed invalidation condition" in render_journal_state(incomplete)

    invalidation = _entry(
        entry_id="invalidation-001",
        entry_type="invalidation",
        evidence_direction="context",
        confidence="",
        supersedes_entry_id="",
        review_due_date="2026-07-01",
    )
    overdue = derive_journal_state(
        (_entry(review_due_date="2026-07-01"), invalidation),
        profile_key="demo",
        ticker="SYN1",
        as_of="2026-07-16T00:00:00Z",
    )
    assert overdue.status == "overdue"
    assert "Review the recorded hypothesis and its conflicting evidence" in render_journal_state(overdue)


def test_preview_validates_without_writing(tmp_path):
    ledger = tmp_path / "journal.csv"

    preview = preview_journal_entry(_entry(), existing_entries=load_journal_entries(ledger))

    assert "Preview only" in preview
    assert "entry-001" in preview
    assert not ledger.exists()


def _entry_cli_args(ledger: Path) -> list[str]:
    entry = _entry()
    args = ["--ledger", str(ledger)]
    for field in JOURNAL_COLUMNS:
        args.extend(["--" + field.replace("_", "-"), str(getattr(entry, field))])
    return args


def test_cli_record_requires_explicit_review_confirmation(tmp_path):
    ledger = tmp_path / "journal.csv"

    with pytest.raises(ValueError, match="--confirm-reviewed"):
        main(["--record", *_entry_cli_args(ledger)])

    assert not ledger.exists()


def test_cli_preview_then_confirmed_record_preserves_append_only_boundary(tmp_path, capsys):
    ledger = tmp_path / "journal.csv"

    assert main(["--preview", *_entry_cli_args(ledger)]) == 0
    assert "Preview only" in capsys.readouterr().out
    assert not ledger.exists()

    assert main(["--record", "--confirm-reviewed", *_entry_cli_args(ledger)]) == 0
    assert "Appended reviewed thesis journal entry" in capsys.readouterr().out
    assert [row.entry_id for row in load_journal_entries(ledger)] == ["entry-001"]


def test_rendered_journal_avoids_transaction_or_recommendation_language():
    invalidation = _entry(
        entry_id="invalidation-001",
        entry_type="invalidation",
        evidence_direction="context",
        confidence="",
        supersedes_entry_id="",
    )
    rendered = render_journal_state(
        derive_journal_state(
            (_entry(), invalidation),
            profile_key="demo",
            ticker="SYN1",
            as_of="2026-07-16T00:00:00Z",
        )
    ).lower()

    for prohibited in ("buy", "sell", "hold", "order", "position size", "recommendation"):
        assert prohibited not in rendered
