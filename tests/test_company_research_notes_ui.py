from dataclasses import replace
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import company_research_notes as notes
from src.catalyst_evidence_timeline import CatalystEvent, append_reviewed_event
from src.research_outcome_review import ResearchOutcome, append_reviewed_outcome
from src.research_record_authoring import AuthoringPaths
from src.research_thesis_journal import JournalEntry, append_journal_entry, load_journal_entries


NOTES_APP = """
import os
from pathlib import Path
import streamlit as st
from src.company_research_notes import CompanyNotesScope
from src.company_research_notes_ui import render_company_notes, render_company_notes_monitor
from src.research_record_authoring import AuthoringPaths

profile = os.environ.get("NOTES_UI_PROFILE", "demo")
if os.environ.get("NOTES_UI_PAGE") == "monitor":
    root = Path(os.environ["NOTES_UI_ROOT"])
    legacy = AuthoringPaths(*(root / "legacy" / name for name in ("journal.csv", "catalysts.csv", "outcomes.csv"))) if os.environ.get("NOTES_UI_LEGACY") == "1" else None
    render_company_notes_monitor(st, profile_key=profile, **({"legacy_paths":legacy} if legacy else {}))
elif os.environ.get("NOTES_UI_LEGACY") == "1":
    root = Path(os.environ["NOTES_UI_ROOT"])
    paths = AuthoringPaths(*(root / "legacy" / name for name in ("journal.csv", "catalysts.csv", "outcomes.csv")))
    render_company_notes(st, profile_key=profile, ticker="FICT", legacy_paths=paths)
else:
    scope = CompanyNotesScope(
        os.environ.get("NOTES_UI_SCOPE_PROFILE", profile),
        os.environ.get("NOTES_UI_SCOPE_TICKER", "FICT"),
        os.environ.get("NOTES_UI_CIK", "0000001234"),
    )
    render_company_notes(st, profile_key=profile, ticker="FICT", scope=scope)
"""


@pytest.fixture
def note_store(tmp_path, monkeypatch):
    monkeypatch.setattr(notes, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("NOTES_UI_ROOT", str(tmp_path))
    for name in ("NOTES_UI_PROFILE", "NOTES_UI_SCOPE_PROFILE", "NOTES_UI_SCOPE_TICKER", "NOTES_UI_CIK", "NOTES_UI_PAGE", "NOTES_UI_LEGACY"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _scope(*, profile="demo", cik="0000001234"):
    return notes.CompanyNotesScope(profile, "FICT", cik)


def _entry(*, profile="demo", summary="Check the next reported cash-flow period."):
    return JournalEntry(
        "research-thesis-journal-v1", "entry-one", profile, "FICT", "thesis-one", "thesis",
        "2026-11-07T12:00:00Z", "2026-11-07T11:00:00Z", "Synthetic reviewer", summary,
        "", "", "", "", "0.50", "2026-12-01", "",
    )


def _snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _visible(app):
    return "\n".join(
        str(element.value)
        for kind in ("markdown", "caption", "text", "warning", "info")
        for element in app.get(kind)
    )


def _enter_thesis(app, *, legacy=False):
    prefix = "research-authoring:demo:FICT:" + ("" if legacy else "cik:0000001234:")
    for field, value in {
        "thesis_id": "authored-thesis", "summary": "User-authored follow-up without company CSV inputs.",
        "effective_at": "2026-11-01T11:00:00Z", "reviewer": "Synthetic reviewer",
        "confidence": "0.50", "review_due_date": "2026-12-02",
    }.items():
        widget = app.text_area if field == "summary" else app.text_input
        widget(key=prefix + "field:thesis:" + field).set_value(value)
    return app.run(), prefix


def test_empty_notes_reads_and_previews_do_not_prepare_files_or_require_company_csv(note_store):
    app = AppTest.from_string(NOTES_APP).run(timeout=20)
    assert not app.exception
    assert "No thesis saved" in _visible(app)
    assert "CIK 0000001234" in _visible(app)
    assert "saved note identity" in _visible(app)
    assert not _snapshot(note_store)
    assert not any(note_store.iterdir())
    app, prefix = _enter_thesis(app)
    app.button(key=prefix + "validate").click().run()

    assert not app.exception
    assert any(button.label == "Confirm and save" for button in app.button)
    assert not _snapshot(note_store)
    assert not any(note_store.iterdir())
    assert not (note_store / "data").exists()


def test_notes_save_and_reload_retains_actual_profile_and_exact_company_identity(note_store):
    app, prefix = _enter_thesis(AppTest.from_string(NOTES_APP).run(timeout=20))
    app.button(key=prefix + "validate").click().run()
    app.checkbox(key=prefix + "confirmed").check()
    app.button(key=prefix + "save").click().run()

    assert not app.exception
    rows = notes.load_company_notes(_scope()).journal
    assert len(rows) == 1
    assert (rows[0].profile_key, rows[0].ticker) == ("demo", "FICT")
    assert "User-authored follow-up without company CSV inputs." in _visible(app)
    assert "2026-12-02" in _visible(app)
    assert not (note_store / "data").exists()
    before = _snapshot(note_store)
    reopened = AppTest.from_string(NOTES_APP).run(timeout=20)
    assert not reopened.exception
    assert "User-authored follow-up without company CSV inputs." in _visible(reopened)
    assert _snapshot(note_store) == before


def test_note_history_catalysts_and_outcomes_are_visible_without_mutating_ledgers(note_store):
    scope = _scope()
    paths = notes.notes_paths(scope)
    initial = _entry()
    append_journal_entry(paths.journal, initial)
    append_journal_entry(paths.journal, replace(
        initial, entry_id="entry-two", recorded_at="2026-11-07T13:00:00Z",
        effective_at="2026-11-07T12:00:00Z", summary="Latest revised user thesis.",
        supersedes_entry_id="entry-one", review_due_date="2026-12-03",
    ))
    append_reviewed_event(paths.catalysts, CatalystEvent(
        "catalyst-evidence-v1", "event-one", "demo", "FICT", "earnings", "Next reported results",
        "2026-12-01T21:00:00Z", "2026-11-01T10:00:00Z", "2026-11-01T11:00:00Z",
        "company_ir", "https://example.invalid/results", "candidate_context_only", "Synthetic reviewer",
        "User-authored catalyst context.",
    ), confirm_reviewed=True)
    append_reviewed_outcome(paths.outcomes, ResearchOutcome(
        "research-outcome-review-v1", "outcome-one", "demo", "FICT", "thesis-one", "entry-one",
        "2026-11-07T13:00:00Z", "2026-11-01T10:00:00Z", "2026-11-06T10:00:00Z",
        "Synthetic reviewer", "inconclusive", "User-authored outcome review.", "company_ir",
        "https://example.invalid/outcome", "2026-11-06T10:00:00Z", "Keep the original observation window.",
    ), confirm_reviewed=True)
    before = _snapshot(note_store)

    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    visible = _visible(app)
    for expected in ("Latest revised user thesis.", "2026-12-03", "Check the next reported cash-flow period.",
                     "Next reported results", "User-authored catalyst context.", "User-authored outcome review.",
                     "Keep the original observation window."):
        assert expected in visible
    assert _snapshot(note_store) == before


def test_legacy_combined_journal_is_filtered_and_uses_original_authoring_keys(note_store, monkeypatch):
    monkeypatch.setenv("NOTES_UI_LEGACY", "1")
    path = note_store / "legacy" / "journal.csv"
    append_journal_entry(path, _entry())
    append_journal_entry(path, replace(_entry(profile="other"), entry_id="other-entry", summary="Other profile private note."))
    before = _snapshot(note_store)

    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    assert "Check the next reported cash-flow period." in _visible(app)
    assert "Other profile private note." not in _visible(app)
    assert app.text_input(key="research-authoring:demo:FICT:field:thesis:thesis_id").value == "thesis-one"
    assert _snapshot(note_store) == before
    assert load_journal_entries(path)[0].profile_key == "demo"


@pytest.mark.parametrize("env,value", (("NOTES_UI_SCOPE_PROFILE", "other"), ("NOTES_UI_SCOPE_TICKER", "OTHER")))
def test_scope_mismatch_stops_before_exposing_notes_or_authoring(note_store, monkeypatch, env, value):
    append_journal_entry(notes.notes_paths(_scope()).journal, _entry())
    monkeypatch.setenv(env, value)
    before = _snapshot(note_store)

    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    assert "does not match" in _visible(app)
    assert "Check the next reported cash-flow period." not in _visible(app)
    assert not app.text_input
    assert _snapshot(note_store) == before


def test_other_cik_with_the_same_symbol_does_not_load_another_issuers_note(note_store, monkeypatch):
    append_journal_entry(notes.notes_paths(_scope()).journal, _entry())
    monkeypatch.setenv("NOTES_UI_CIK", "0000005678")
    before = _snapshot(note_store)

    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    assert "No thesis saved" in _visible(app)
    assert "Check the next reported cash-flow period." not in _visible(app)
    assert app.text_input(key="research-authoring:demo:FICT:cik:0000005678:field:thesis:thesis_id").value == ""
    assert _snapshot(note_store) == before


@pytest.mark.parametrize("invalid_content", (b"wrong,header\n", b"\xff\xfe", b"x" * (notes.MAX_NOTE_BYTES + 1)), ids=("invalid-header", "invalid-utf8", "oversize"))
def test_corrupt_or_oversize_store_shows_a_gap_and_never_opens_an_empty_composer(note_store, invalid_content):
    paths = notes.notes_paths(_scope())
    paths.journal.parent.mkdir(parents=True)
    paths.journal.write_bytes(invalid_content)
    before = _snapshot(note_store)

    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    assert "could not be verified" in _visible(app)
    assert not app.text_input
    assert not any(button.label == "Validate and preview" for button in app.button)
    assert _snapshot(note_store) == before


def test_monitor_lists_user_notes_and_opens_the_exact_saved_cik_without_sec_evidence(note_store, monkeypatch):
    append_journal_entry(notes.notes_paths(_scope()).journal, _entry())
    append_journal_entry(notes.notes_paths(_scope(cik="0000005678")).journal,
                         _entry(summary="Same symbol, different issuer follow-up."))
    append_journal_entry(notes.notes_paths(_scope(profile="other")).journal,
                         _entry(profile="other", summary="Other profile private note."))
    monkeypatch.setenv("NOTES_UI_PAGE", "monitor")
    before = _snapshot(note_store)
    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    assert "User-authored follow-ups" in _visible(app)
    assert "2026-12-01" in _visible(app)
    assert "Other profile private note." not in _visible(app)
    selector = app.selectbox(key="company-notes-monitor:demo")
    assert selector.options == ["FICT · CIK 0000001234", "FICT · CIK 0000005678"]
    selector.set_value("FICT · CIK 0000005678").run()
    assert "Same symbol, different issuer follow-up." in _visible(app)
    app.button(key="company-notes-monitor-open:demo").click().run()

    assert not app.exception
    assert dict(app.query_params) == {
        "mode": ["research"], "page": ["company-workbench"], "ticker": ["FICT"],
        "section": ["notes"], "notes_cik": ["0000005678"],
    }
    assert _snapshot(note_store) == before
    assert not (note_store / "outputs/local/sec-research").exists()
    assert not (note_store / "data").exists()


def test_monitor_excludes_corrupt_scopes_but_keeps_valid_followups(note_store, monkeypatch):
    append_journal_entry(notes.notes_paths(_scope()).journal, _entry())
    bad = notes.notes_paths(_scope(cik="0000005678")).journal
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"invalid,header\n")
    monkeypatch.setenv("NOTES_UI_PAGE", "monitor")
    before = _snapshot(note_store)

    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    assert "could not be verified" in _visible(app)
    assert "Check the next reported cash-flow period." in _visible(app)
    assert app.selectbox(key="company-notes-monitor:demo").options == ["FICT · CIK 0000001234"]
    assert _snapshot(note_store) == before


def test_empty_monitor_does_not_create_store_or_offer_a_company(note_store, monkeypatch):
    monkeypatch.setenv("NOTES_UI_PAGE", "monitor")

    app = AppTest.from_string(NOTES_APP).run(timeout=20)

    assert not app.exception
    assert "No saved company notes" in _visible(app)
    assert not app.selectbox
    assert not app.button
    assert not _snapshot(note_store)
    assert not any(note_store.iterdir())


def test_large_valid_legacy_journal_is_not_hidden_by_online_store_limit(note_store,monkeypatch):
    paths=AuthoringPaths(*(note_store/'legacy'/name for name in ('journal.csv','catalysts.csv','outcomes.csv')))
    append_journal_entry(paths.journal,_entry(summary='Legacy thesis'))
    for index in range(18):
        append_journal_entry(paths.journal,replace(_entry(),entry_id=f'evidence-{index}',entry_type='evidence',
            summary='x'*120000,evidence_direction='context',source='Synthetic fixture',
            source_ref='https://example.test/source',source_published_at='2026-11-07T10:00:00Z',
            confidence='',review_due_date=''))
    assert paths.journal.stat().st_size > notes.MAX_NOTE_BYTES
    monkeypatch.setenv('NOTES_UI_LEGACY','1')
    app=AppTest.from_string(NOTES_APP).run(timeout=30)
    assert not app.exception
    assert 'Legacy thesis' in _visible(app)
    assert any(b.label=='Validate and preview' for b in app.button)


def test_monitor_can_open_legacy_journal_only_company_without_model_or_sec(note_store,monkeypatch):
    paths=AuthoringPaths(*(note_store/'legacy'/name for name in ('journal.csv','catalysts.csv','outcomes.csv')))
    append_journal_entry(paths.journal,_entry())
    append_journal_entry(paths.journal,replace(_entry(profile='other'),entry_id='other-profile'))
    before=_snapshot(note_store)
    monkeypatch.setenv('NOTES_UI_LEGACY','1');monkeypatch.setenv('NOTES_UI_PAGE','monitor')
    app=AppTest.from_string(NOTES_APP).run(timeout=20)
    assert not app.exception
    assert app.selectbox(key='company-notes-monitor:demo').options == ['FICT · saved workspace']
    app.button(key='company-notes-monitor-open:demo').click().run()
    assert app.query_params['ticker']==['FICT'] and app.query_params['section']==['notes']
    assert 'notes_cik' not in app.query_params and 'online' not in app.query_params
    assert _snapshot(note_store)==before
