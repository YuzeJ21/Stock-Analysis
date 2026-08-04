import csv
from contextlib import contextmanager
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.research_record_authoring import AuthoringPaths
from src import research_record_authoring
from src import research_record_authoring_ui
from src.research_record_authoring_ui import authoring_field_contract, authoring_session_key
from src.catalyst_evidence_timeline import CatalystEvent, append_reviewed_event
from src.catalyst_evidence_timeline import load_catalyst_events
from src.research_outcome_review import (
    ResearchOutcome,
    append_reviewed_outcome,
    load_outcomes,
)
from src.research_thesis_journal import (
    JournalEntry,
    append_journal_entry,
    derive_journal_state,
    load_journal_entries,
)


AUTHORING_APP = Path(__file__).resolve().parent / "fixtures/research_record_authoring_app.py"


def _paths(tmp_path: Path) -> AuthoringPaths:
    return AuthoringPaths(tmp_path / "journal.csv", tmp_path / "catalysts.csv", tmp_path / "outcomes.csv")


def _thesis_entry() -> JournalEntry:
    return JournalEntry(
        "research-thesis-journal-v1", "entry-existing", "demo", "SYN1", "thesis-syn1", "thesis",
        "2026-07-20T12:00:00Z", "2026-07-20T11:00:00Z", "fixture-reviewer",
        "Existing synthetic thesis.", "", "", "", "", "0.50", "2026-08-20", "",
    )


def _app(tmp_path: Path, monkeypatch) -> AppTest:
    monkeypatch.setenv("RESEARCH_AUTHORING_FIXTURE_DIR", str(tmp_path))
    return AppTest.from_file(AUTHORING_APP).run(timeout=20)


def _field_key(kind: str, name: str) -> str:
    return authoring_session_key("demo", "SYN1", f"field:{kind}:{name}")


def _state_message_bodies(app: AppTest) -> list[str]:
    return [
        element.proto.body
        for element in app.get("html")
        if "research-state-message" in element.proto.body
    ]


def _binding_bodies(app: AppTest) -> list[str]:
    return [
        element.proto.body
        for element in app.get("html")
        if "data-research-authoring-error-owned" in element.proto.body
    ]


def _enter_valid_thesis(app: AppTest) -> AppTest:
    app.text_input(key=_field_key("thesis", "thesis_id")).set_value("thesis-new")
    app.text_area(key=_field_key("thesis", "summary")).set_value("Reviewed synthetic thesis.")
    app.text_input(key=_field_key("thesis", "effective_at")).set_value("2026-07-22T10:00:00Z")
    app.text_input(key=_field_key("thesis", "reviewer")).set_value("fixture-reviewer")
    app.text_input(key=_field_key("thesis", "confidence")).set_value("0.60")
    return app.text_input(key=_field_key("thesis", "review_due_date")).set_value("2026-08-22").run()


def _enter_valid_non_thesis_record(app: AppTest, kind: str) -> AppTest:
    app.selectbox(key=authoring_session_key("demo", "SYN1", "kind")).set_value(kind).run()
    fields = {
        "evidence": {
            "summary": "Reviewed synthetic evidence.",
            "effective_at": "2026-07-22T11:00:00Z",
            "reviewer": "fixture-reviewer",
            "source": "company_ir",
            "source_ref": "https://example.invalid/evidence",
            "source_published_at": "2026-07-22T10:00:00Z",
        },
        "catalyst": {
            "title": "Scheduled synthetic results",
            "summary": "Reviewed synthetic catalyst context.",
            "effective_at": "2026-08-20T21:00:00Z",
            "published_at": "2026-07-22T09:00:00Z",
            "retrieved_at": "2026-07-22T10:00:00Z",
            "source": "company_ir",
            "source_ref": "https://example.invalid/event",
            "reviewer": "fixture-reviewer",
        },
        "outcome": {
            "reviewed_at": "2026-07-22T12:00:00Z",
            "observation_start": "2026-07-20T12:00:00Z",
            "observation_end": "2026-07-22T11:00:00Z",
            "reviewer": "fixture-reviewer",
            "summary": "Reviewed synthetic outcome.",
            "source": "reviewed_research_record",
            "source_ref": "journal://entry-existing",
            "source_published_at": "2026-07-22T10:00:00Z",
            "learning": "Preserve explicit evidence boundaries.",
        },
    }[kind]
    for name, value in fields.items():
        widget = app.text_area if name in {"summary", "learning"} else app.text_input
        widget(key=_field_key(kind, name)).set_value(value)
    return app.run()


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
    app = _app(tmp_path, monkeypatch)

    assert not app.exception
    assert "Profile: demo | Ticker: SYN1" in "\n".join(item.value for item in app.markdown)
    assert any(item.label == "Validate and preview" for item in app.button)
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())


def test_fixture_uses_controlled_choices_and_scoped_thesis_references(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    append_journal_entry(paths.journal, _thesis_entry())
    app = _app(tmp_path, monkeypatch)
    app.selectbox(key=authoring_session_key("demo", "SYN1", "kind")).set_value("evidence").run()

    assert app.selectbox(key=_field_key("evidence", "thesis_id")).options == ["thesis-syn1"]
    assert app.selectbox(key=_field_key("evidence", "evidence_direction")).options == ["supporting", "conflicting", "context"]


def test_existing_active_thesis_is_presented_as_a_locked_revision_lineage(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    active = _thesis_entry()
    append_journal_entry(paths.journal, active)

    app = _app(tmp_path, monkeypatch)

    assert not app.exception
    thesis_id = app.text_input(key=_field_key("thesis", "thesis_id"))
    supersedes = app.selectbox(key=_field_key("thesis", "supersedes_entry_id"))
    assert thesis_id.value == active.thesis_id
    assert thesis_id.disabled is True
    assert supersedes.options == [active.entry_id]
    assert supersedes.value == active.entry_id
    assert "revision of the active thesis" in "\n".join(item.value for item in app.caption)


def test_empty_scoped_thesis_options_fail_closed_with_a_readable_message(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    app.selectbox(key=authoring_session_key("demo", "SYN1", "kind")).set_value("evidence").run()

    assert not app.exception
    assert "requires an existing thesis in this locked profile and ticker" in "\n".join(item.value for item in app.warning)
    assert not any(item.label == "Validate and preview" for item in app.button)
    assert not any(tmp_path.iterdir())


def test_invalid_thesis_preview_shows_error_without_confirmation_or_writing(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.text_input(key=_field_key("thesis", "effective_at")).set_value("not-a-timestamp").run()
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert not app.exception
    assert "effective_at must be an ISO-8601 timestamp" in _state_message_bodies(app)[0]
    assert len(_binding_bodies(app)) == 1
    cleanup = _binding_bodies(app)[0]
    assert '"fieldLabel": null' in cleanup
    assert '"errorId": null' in cleanup
    assert '"message": null' in cleanup
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())


def test_valid_preview_announces_unsaved_state_once(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    messages = _state_message_bodies(app)
    assert len(messages) == 1
    assert "role='status'" in messages[0]
    assert "aria-live='polite'" in messages[0]
    assert "Preview ready" in messages[0]
    assert "This exact record is ready for review and is not saved." in messages[0]
    assert not any(tmp_path.iterdir())

    app.run()
    messages = _state_message_bodies(app)
    assert len(messages) == 1
    assert "role='group'" in messages[0]
    assert "aria-live" not in messages[0]


def test_rejected_validation_announces_one_alert_then_stays_visible(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.text_input(key=_field_key("thesis", "effective_at")).set_value("not-a-timestamp").run()

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    messages = _state_message_bodies(app)
    assert len(messages) == 1
    assert "role='alert'" in messages[0]
    assert "aria-live='assertive'" in messages[0]
    assert "Validation rejected" in messages[0]
    assert "effective_at must be an ISO-8601 timestamp" in messages[0]
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())

    app.run()
    messages = _state_message_bodies(app)
    assert len(messages) == 1
    assert "role='group'" in messages[0]
    assert "aria-live" not in messages[0]


def test_changed_draft_announces_revalidation_without_saving(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    app.text_area(key=_field_key("thesis", "summary")).set_value("Edited after preview.").run()

    messages = _state_message_bodies(app)
    assert len(messages) == 1
    assert "role='status'" in messages[0]
    assert "Draft changed" in messages[0]
    assert "Validate and preview this edited draft again before saving." in messages[0]
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())


def test_empty_thesis_binds_first_required_field_and_preserves_all_ledger_bytes(
    tmp_path, monkeypatch
):
    paths = _paths(tmp_path)
    before = tuple(path.read_bytes() if path.exists() else None for path in paths.all())
    app = _app(tmp_path, monkeypatch)

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert not app.exception
    assert "thesis_id is required" in _state_message_bodies(app)[0]
    assert len(_binding_bodies(app)) == 1
    binding = _binding_bodies(app)[0]
    assert '"fieldLabel": "Thesis Id"' in binding
    assert '"message": "thesis_id is required"' in binding
    assert (
        '"errorId": "research-authoring-demo-syn1-thesis-thesis-id-error"'
        in binding
    )
    assert not any(item.label == "Confirm and save" for item in app.button)
    after = tuple(path.read_bytes() if path.exists() else None for path in paths.all())
    assert after == before == (None, None, None)


def test_required_field_binding_advances_from_thesis_id_to_effective_at_without_writing(
    tmp_path, monkeypatch
):
    paths = _paths(tmp_path)
    before = tuple(path.read_bytes() if path.exists() else None for path in paths.all())
    app = _app(tmp_path, monkeypatch)
    validate_key = authoring_session_key("demo", "SYN1", "validate")

    app.button(key=validate_key).click().run()
    assert "thesis_id is required" in _state_message_bodies(app)[0]
    first_binding = _binding_bodies(app)[0]
    assert '"fieldLabel": "Thesis Id"' in first_binding

    app.text_input(key=_field_key("thesis", "thesis_id")).set_value(
        "thesis-new"
    ).run()
    cleanup = _binding_bodies(app)[0]
    assert '"fieldLabel": null' in cleanup
    assert '"errorId": null' in cleanup
    assert "Draft changed" in _state_message_bodies(app)[0]

    app.button(key=validate_key).click().run()
    assert "effective_at is required" in _state_message_bodies(app)[0]
    second_binding = _binding_bodies(app)[0]
    assert '"fieldLabel": "Effective At"' in second_binding
    assert '"message": "effective_at is required"' in second_binding
    after = tuple(path.read_bytes() if path.exists() else None for path in paths.all())
    assert after == before == (None, None, None)


def test_accepted_preview_renders_cleanup_binding_without_changing_ledger_bytes(
    tmp_path, monkeypatch
):
    paths = _paths(tmp_path)
    before = tuple(path.read_bytes() if path.exists() else None for path in paths.all())
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert any(item.label == "Confirm and save" for item in app.button)
    assert len(_binding_bodies(app)) == 1
    cleanup = _binding_bodies(app)[0]
    assert '"fieldLabel": null' in cleanup
    assert '"errorId": null' in cleanup
    after = tuple(path.read_bytes() if path.exists() else None for path in paths.all())
    assert after == before == (None, None, None)


def test_preview_then_confirm_saves_only_the_temporary_journal(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert not app.exception
    assert any(item.value == "#### Exact append-only preview" for item in app.markdown)
    assert any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())

    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    paths = _paths(tmp_path)
    assert [entry.thesis_id for entry in load_journal_entries(paths.journal)] == ["thesis-new"]
    assert not paths.catalysts.exists()
    assert not paths.outcomes.exists()


def test_confirmed_record_receipt_is_shown_once_after_the_correct_temporary_ledger_reloads(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    assert not app.exception
    saved_id = load_journal_entries(paths.journal)[0].entry_id
    assert f"Saved {saved_id}." in _state_message_bodies(app)[0]

    app.run()

    assert not app.exception
    assert not _state_message_bodies(app)


@pytest.mark.parametrize("kind", ("evidence", "catalyst", "outcome"))
def test_non_thesis_composer_saves_exactly_once_only_after_preview_confirmation_and_reload(
    tmp_path, monkeypatch, kind
):
    paths = _paths(tmp_path)
    thesis = _thesis_entry()
    append_journal_entry(paths.journal, thesis)
    app = _enter_valid_non_thesis_record(_app(tmp_path, monkeypatch), kind)

    assert not app.exception
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not _state_message_bodies(app)
    assert load_journal_entries(paths.journal) == (thesis,)
    assert not paths.catalysts.exists()
    assert not paths.outcomes.exists()

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert not app.exception
    assert any(item.value == "#### Exact append-only preview" for item in app.markdown)
    assert any(item.label == "Confirm and save" for item in app.button)
    assert "Preview ready" in _state_message_bodies(app)[0]
    assert load_journal_entries(paths.journal) == (thesis,)
    assert not paths.catalysts.exists()
    assert not paths.outcomes.exists()

    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    assert not app.exception
    assert len(_state_message_bodies(app)) == 1
    if kind == "evidence":
        rows = load_journal_entries(paths.journal)
        assert len(rows) == 2
        saved = rows[-1]
        assert saved.entry_type == "evidence"
        assert saved.profile_key == "demo"
        assert saved.ticker == "SYN1"
        assert saved.thesis_id == thesis.thesis_id
        assert saved.summary == "Reviewed synthetic evidence."
        assert saved.effective_at == "2026-07-22T11:00:00Z"
        assert saved.reviewer == "fixture-reviewer"
        assert saved.evidence_direction == "supporting"
        assert saved.source == "company_ir"
        assert saved.source_ref == "https://example.invalid/evidence"
        assert saved.source_published_at == "2026-07-22T10:00:00Z"
        assert not paths.catalysts.exists()
        assert not paths.outcomes.exists()
    elif kind == "catalyst":
        assert load_journal_entries(paths.journal) == (thesis,)
        rows = load_catalyst_events(paths.catalysts)
        assert len(rows) == 1
        saved = rows[0]
        assert saved.profile_key == "demo"
        assert saved.ticker == "SYN1"
        assert saved.event_type == "earnings"
        assert saved.title == "Scheduled synthetic results"
        assert saved.summary == "Reviewed synthetic catalyst context."
        assert saved.effective_at == "2026-08-20T21:00:00Z"
        assert saved.published_at == "2026-07-22T09:00:00Z"
        assert saved.retrieved_at == "2026-07-22T10:00:00Z"
        assert saved.source == "company_ir"
        assert saved.source_ref == "https://example.invalid/event"
        assert saved.evidence_state == "candidate_context_only"
        assert saved.reviewer == "fixture-reviewer"
        assert not paths.outcomes.exists()
    else:
        assert load_journal_entries(paths.journal) == (thesis,)
        rows = load_outcomes(paths.outcomes)
        assert len(rows) == 1
        saved = rows[0]
        assert saved.profile_key == "demo"
        assert saved.ticker == "SYN1"
        assert saved.thesis_id == thesis.thesis_id
        assert saved.original_thesis_entry_id == thesis.entry_id
        assert saved.reviewed_at == "2026-07-22T12:00:00Z"
        assert saved.observation_start == "2026-07-20T12:00:00Z"
        assert saved.observation_end == "2026-07-22T11:00:00Z"
        assert saved.reviewer == "fixture-reviewer"
        assert saved.outcome_state == "supported"
        assert saved.summary == "Reviewed synthetic outcome."
        assert saved.source == "reviewed_research_record"
        assert saved.source_ref == "journal://entry-existing"
        assert saved.source_published_at == "2026-07-22T10:00:00Z"
        assert saved.learning == "Preserve explicit evidence boundaries."
        assert not paths.catalysts.exists()

    saved_message = _state_message_bodies(app)[0]
    assert "Corrections require a new append-only record" in saved_message
    app.run()

    assert not app.exception
    assert not _state_message_bodies(app)
    if kind == "evidence":
        assert len(load_journal_entries(paths.journal)) == 2
    elif kind == "catalyst":
        assert len(load_catalyst_events(paths.catalysts)) == 1
    else:
        assert len(load_outcomes(paths.outcomes)) == 1


def test_deleted_confirmed_record_warns_after_temporary_ledger_reload(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    monkeypatch.setattr(st, "rerun", lambda: None)
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    assert [entry.thesis_id for entry in load_journal_entries(paths.journal)] == ["thesis-new"]
    paths.journal.unlink()
    app.run()

    assert not app.exception
    assert "Saved record could not be reloaded; review the ledger" in _state_message_bodies(app)[0]
    assert "save another record" in _state_message_bodies(app)[0]


def test_teardown_uncertainty_reloads_once_and_never_retries_the_append(tmp_path, monkeypatch):
    paths = _paths(tmp_path)

    @contextmanager
    def teardown_failure(path):
        yield Path(path)
        raise OSError("unlock unavailable")

    monkeypatch.setattr(research_record_authoring, "ledger_write_lock", teardown_failure)
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    assert [entry.entry_id for entry in load_journal_entries(paths.journal)]
    assert len(load_journal_entries(paths.journal)) == 1
    assert "Record saved" in _state_message_bodies(app)[0]

    app.run()

    assert len(load_journal_entries(paths.journal)) == 1
    assert not _state_message_bodies(app)


def test_teardown_uncertainty_warns_once_when_the_follow_up_reload_is_missing(tmp_path, monkeypatch):
    paths = _paths(tmp_path)

    @contextmanager
    def teardown_failure(path):
        yield Path(path)
        raise OSError("unlock unavailable")

    monkeypatch.setattr(research_record_authoring, "ledger_write_lock", teardown_failure)
    monkeypatch.setattr(st, "rerun", lambda: None)
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()
    paths.journal.unlink()

    app.run()

    assert "Saved record could not be reloaded; review the ledger" in _state_message_bodies(app)[0]
    assert len(load_journal_entries(paths.journal)) == 0
    app.run()
    assert not _state_message_bodies(app)


def test_edit_after_preview_hides_save_until_a_fresh_preview(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    assert any(item.label == "Confirm and save" for item in app.button)

    app.text_area(key=_field_key("thesis", "summary")).set_value("Edited after preview.").run()

    assert "Draft changed" in _state_message_bodies(app)[0]
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())


def test_repreview_of_the_same_draft_resets_confirmation(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).value is False


def test_preview_of_a_changed_draft_resets_confirmation(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.text_area(key=_field_key("thesis", "summary")).set_value("Changed before re-preview.").run()

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).value is False


def test_preview_of_a_different_kind_resets_confirmation(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.selectbox(key=authoring_session_key("demo", "SYN1", "kind")).set_value("catalyst").run()
    app.selectbox(key=_field_key("catalyst", "event_type")).set_value("earnings")
    for name, value in {
        "title": "Scheduled results", "summary": "Reviewed context.",
        "effective_at": "2026-08-20T21:00:00Z", "published_at": "2026-07-22T09:00:00Z",
        "retrieved_at": "2026-07-22T10:00:00Z", "source": "company_ir",
        "source_ref": "https://example.invalid/event", "reviewer": "owner",
    }.items():
        widget = app.text_area if name == "summary" else app.text_input
        widget(key=_field_key("catalyst", name)).set_value(value)
    app.selectbox(key=_field_key("catalyst", "evidence_state")).set_value("candidate_context_only").run()

    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).value is False


def test_post_save_repreview_resets_confirmation(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    app = _enter_valid_thesis(app)
    app.text_area(key=_field_key("thesis", "summary")).set_value(
        "Reviewed synthetic thesis revision."
    ).run()
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).value is False


def test_initial_thesis_then_ui_revision_reloads_as_one_active_lineage(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    original = load_journal_entries(paths.journal)[0]
    assert app.text_input(key=_field_key("thesis", "thesis_id")).value == original.thesis_id
    assert app.text_input(key=_field_key("thesis", "thesis_id")).disabled is True
    assert app.selectbox(key=_field_key("thesis", "supersedes_entry_id")).value == original.entry_id

    app.text_area(key=_field_key("thesis", "summary")).set_value(
        "Reviewed synthetic thesis revision."
    ).run()
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).check()
    app.button(key=authoring_session_key("demo", "SYN1", "save")).click().run()

    reloaded = load_journal_entries(paths.journal)
    state = derive_journal_state(
        reloaded,
        profile_key="demo",
        ticker="SYN1",
        as_of="2026-07-23T00:00:00Z",
    )
    assert len(reloaded) == 2
    assert state.current_thesis == reloaded[-1]
    assert state.current_thesis.thesis_id == original.thesis_id
    assert state.current_thesis.supersedes_entry_id == original.entry_id


class _ReceiptUI:
    def __init__(self, receipt):
        self.session_state = {authoring_session_key("demo", "SYN1", "pending-reload-receipt"): receipt}
        self.rendered_html: list[str] = []

    def html(self, rendered: str) -> None:
        self.rendered_html.append(rendered)


def _receipt_record(kind: str):
    if kind == "thesis":
        return _thesis_entry(), "journal"
    if kind == "evidence":
        return JournalEntry(
            "research-thesis-journal-v1", "evidence-receipt", "demo", "SYN1", "thesis-syn1", "evidence",
            "2026-07-22T12:00:00Z", "2026-07-22T11:00:00Z", "owner", "Evidence.", "supporting",
            "company_ir", "https://example.invalid/evidence", "2026-07-22T10:00:00Z", "", "", "",
        ), "journal"
    if kind == "catalyst":
        return CatalystEvent(
            "catalyst-evidence-v1", "catalyst-receipt", "demo", "SYN1", "earnings", "Results",
            "2026-08-20T21:00:00Z", "2026-07-22T09:00:00Z", "2026-07-22T10:00:00Z", "company_ir",
            "https://example.invalid/event", "candidate_context_only", "owner", "Context.",
        ), "catalysts"
    return ResearchOutcome(
        "research-outcome-review-v1", "outcome-receipt", "demo", "SYN1", "thesis-syn1", "entry-existing",
        "2026-07-22T12:00:00Z", "2026-07-20T12:00:00Z", "2026-07-22T11:00:00Z", "owner", "mixed",
        "Outcome.", "reviewed_research_record", "journal://entry-existing", "2026-07-22T11:00:00Z", "Learning.",
    ), "outcomes"


@pytest.mark.parametrize("kind", ("thesis", "evidence", "catalyst", "outcome"))
@pytest.mark.parametrize("reload_state", ("success", "missing", "invalid_utf8", "malformed_csv", "unreadable"))
def test_pending_receipt_is_consumed_once_and_fails_closed_for_every_temporary_ledger(
    tmp_path, monkeypatch, kind, reload_state
):
    paths = _paths(tmp_path)
    record, path_name = _receipt_record(kind)
    destination = getattr(paths, path_name)
    loader_names = {"journal": "load_journal_entries", "catalysts": "load_catalyst_events", "outcomes": "load_outcomes"}
    if reload_state == "success":
        if kind in {"thesis", "evidence"}:
            append_journal_entry(destination, record)
        elif kind == "catalyst":
            append_reviewed_event(destination, record, confirm_reviewed=True)
        else:
            append_reviewed_outcome(destination, record, confirm_reviewed=True)
    elif reload_state == "invalid_utf8":
        destination.write_bytes(b"\xff\xfe")
    elif reload_state in {"malformed_csv", "unreadable"}:
        destination.write_text("not,the,expected,header\n", encoding="utf-8")
        error = csv.Error("malformed csv") if reload_state == "malformed_csv" else OSError("unreadable")
        monkeypatch.setattr(research_record_authoring_ui, loader_names[path_name], lambda _path: (_ for _ in ()).throw(error))
    receipt = _ReceiptUI({"record_kind": kind, "record_id": getattr(record, "entry_id", getattr(record, "event_id", getattr(record, "outcome_id", "")))})

    research_record_authoring_ui._show_reloaded_save_receipt(
        receipt, profile_key="demo", ticker="SYN1", paths=paths
    )

    receipt_key = authoring_session_key("demo", "SYN1", "pending-reload-receipt")
    assert receipt_key not in receipt.session_state
    assert len(receipt.rendered_html) == 1
    if reload_state == "success":
        assert "role='status'" in receipt.rendered_html[0]
        assert "Record saved" in receipt.rendered_html[0]
    else:
        assert "role='alert'" in receipt.rendered_html[0]
        assert "Save verification incomplete" in receipt.rendered_html[0]
        assert "Retry save" not in receipt.rendered_html[0]
        assert "Save again" not in receipt.rendered_html[0]
