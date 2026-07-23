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
from src.research_outcome_review import ResearchOutcome, append_reviewed_outcome
from src.research_thesis_journal import JournalEntry, append_journal_entry, load_journal_entries


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
    return AppTest.from_file("tests/fixtures/research_record_authoring_app.py").run(timeout=20)


def _field_key(kind: str, name: str) -> str:
    return authoring_session_key("demo", "SYN1", f"field:{kind}:{name}")


def _enter_valid_thesis(app: AppTest) -> AppTest:
    app.text_input(key=_field_key("thesis", "thesis_id")).set_value("thesis-new")
    app.text_area(key=_field_key("thesis", "summary")).set_value("Reviewed synthetic thesis.")
    app.text_input(key=_field_key("thesis", "effective_at")).set_value("2026-07-22T10:00:00Z")
    app.text_input(key=_field_key("thesis", "reviewer")).set_value("fixture-reviewer")
    app.text_input(key=_field_key("thesis", "confidence")).set_value("0.60")
    return app.text_input(key=_field_key("thesis", "review_due_date")).set_value("2026-08-22").run()


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
    assert "effective_at must be an ISO-8601 timestamp" in "\n".join(item.value for item in app.error)
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())


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
    assert f"Saved {saved_id}." in "\n".join(item.value for item in app.success)

    app.run()

    assert not app.exception
    assert not app.success


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
    assert not app.success
    assert "Saved record could not be reloaded; review the ledger" in "\n".join(
        item.value for item in app.warning
    )


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
    assert len(app.success) == 1

    app.run()

    assert len(load_journal_entries(paths.journal)) == 1
    assert not app.success


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

    assert "Saved record could not be reloaded; review the ledger" in "\n".join(
        item.value for item in app.warning
    )
    assert len(load_journal_entries(paths.journal)) == 0
    app.run()
    assert not app.warning


def test_edit_after_preview_hides_save_until_a_fresh_preview(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    assert any(item.label == "Confirm and save" for item in app.button)

    app.text_area(key=_field_key("thesis", "summary")).set_value("Edited after preview.").run()

    assert "Draft changed after preview" in "\n".join(item.value for item in app.warning)
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
    app.text_input(key=_field_key("thesis", "thesis_id")).set_value("thesis-after-save").run()
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()

    assert app.checkbox(key=authoring_session_key("demo", "SYN1", "confirmed")).value is False


class _ReceiptUI:
    def __init__(self, receipt):
        self.session_state = {authoring_session_key("demo", "SYN1", "pending-reload-receipt"): receipt}
        self.successes: list[str] = []
        self.warnings: list[str] = []

    def success(self, message: str) -> None:
        self.successes.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


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
    assert bool(receipt.successes) is (reload_state == "success")
    assert bool(receipt.warnings) is (reload_state != "success")
