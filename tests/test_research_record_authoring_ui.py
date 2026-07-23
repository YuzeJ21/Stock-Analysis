from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.research_record_authoring import AuthoringPaths
from src.research_record_authoring_ui import authoring_field_contract, authoring_session_key
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


def test_edit_after_preview_hides_save_until_a_fresh_preview(tmp_path, monkeypatch):
    app = _enter_valid_thesis(_app(tmp_path, monkeypatch))
    app.button(key=authoring_session_key("demo", "SYN1", "validate")).click().run()
    assert any(item.label == "Confirm and save" for item in app.button)

    app.text_area(key=_field_key("thesis", "summary")).set_value("Edited after preview.").run()

    assert "Draft changed after preview" in "\n".join(item.value for item in app.warning)
    assert not any(item.label == "Confirm and save" for item in app.button)
    assert not any(tmp_path.iterdir())
