"""Direct ledger paths cannot bypass protected Workbench record scope."""

from contextlib import contextmanager
import hashlib
import json

import pytest

from src import workspace_authorization as authorization
from src import catalyst_evidence_timeline, research_outcome_review, research_thesis_journal
from src.catalyst_evidence_timeline import append_reviewed_event, load_catalyst_events
from src.research_outcome_review import append_reviewed_outcome, load_outcomes
from src.research_thesis_journal import append_journal_entry, load_journal_entries
from tests.test_catalyst_evidence_timeline import _event
from tests.test_research_outcome_review import _outcome
from tests.test_research_thesis_journal import _entry


PROFILE = "workspace-alpha"
TICKER = "FICT"
CIK = "0000001234"
LEDGERS = (
    ("research_thesis_journal.csv", load_journal_entries, append_journal_entry,
     lambda **changes: _entry(**{"profile_key": PROFILE, "ticker": TICKER, **changes})),
    ("catalyst_evidence.csv", load_catalyst_events,
     lambda path, row: append_reviewed_event(path, row, confirm_reviewed=True),
     lambda **changes: _event(**{"profile_key": PROFILE, "ticker": TICKER, **changes})),
    ("research_outcome_reviews.csv", load_outcomes,
     lambda path, row: append_reviewed_outcome(path, row, confirm_reviewed=True),
     lambda **changes: _outcome(**{"profile_key": PROFILE, "ticker": TICKER, **changes})),
)
MODULES = {
    "research_thesis_journal.csv": research_thesis_journal,
    "catalyst_evidence.csv": catalyst_evidence_timeline,
    "research_outcome_reviews.csv": research_outcome_review,
}


def _activate(monkeypatch, tmp_path, root, *, role="editor"):
    config = {
        "schema_version": "research-workspace-access-v1",
        "issuer": "https://identity.example",
        "audience": "stock-research",
        "storage_root": str(root),
        "workspaces": {"alpha": {"profile_key": PROFILE, "members": [
            {"subject": "alice", "role": role, "active": True}
        ]}},
    }
    config_path = tmp_path / "workspace-access.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    config_path.chmod(0o600)
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_CONFIG", str(config_path))
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_ID", "alpha")
    monkeypatch.setenv("STOCK_RESEARCH_ACCESS_MODE", "workspace")
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_AUDIT_DB", str(tmp_path / "audit" / "decisions.sqlite"))
    monkeypatch.setattr(authorization, "trusted_user_claims", lambda: {
        "is_logged_in": True, "iss": "https://identity.example", "sub": "alice",
        "aud": "stock-research", "exp": 4102444800,
    })
    return config_path, config


def _private_path(root, filename):
    return (root / "outputs/local/company-research-notes"
            / hashlib.sha256(PROFILE.encode()).hexdigest() / CIK / TICKER / filename)


def _second_row(filename, row):
    if filename == "research_thesis_journal.csv":
        return row(entry_id="entry-002", entry_type="review", source_ref="review:FICT:second")
    if filename == "catalyst_evidence.csv":
        return row(event_id="event-002", source_ref="https://example.invalid/second-event")
    return row(outcome_id="outcome-002", source_ref="journal://entry-002")


@pytest.mark.parametrize("filename,loader,append,row", LEDGERS, ids=["journal", "catalyst", "outcome"])
def test_protected_direct_ledger_rejects_outside_path_before_read_or_append(
    tmp_path, monkeypatch, filename, loader, append, row,
):
    outside = tmp_path / "outside" / filename
    append(outside, row())
    original = outside.read_bytes()
    root = tmp_path / "trusted"
    root.mkdir()
    _activate(monkeypatch, tmp_path, root)

    with pytest.raises(authorization.WorkspaceAccessDenied):
        loader(outside)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        append(outside, row())
    assert outside.read_bytes() == original
    assert not (root / "outputs").exists()


@pytest.mark.parametrize("filename,loader,append,row", LEDGERS, ids=["journal", "catalyst", "outcome"])
def test_protected_direct_ledger_checks_role_and_revocation_on_each_operation(
    tmp_path, monkeypatch, filename, loader, append, row,
):
    root = tmp_path / "trusted"
    root.mkdir()
    path = _private_path(root, filename)
    config_path, config = _activate(monkeypatch, tmp_path, root)

    saved = row()
    append(path, saved)
    assert loader(path) == (saved,)
    original = path.read_bytes()
    config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert loader(path) == (saved,)
    second = _second_row(filename, row)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        append(path, second)
    assert path.read_bytes() == original

    config["workspaces"]["alpha"]["members"][0]["active"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(authorization.WorkspaceAccessDenied):
        loader(path)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        append(path, second)
    assert path.read_bytes() == original


@pytest.mark.parametrize("filename,loader,append,row", LEDGERS, ids=["journal", "catalyst", "outcome"])
def test_protected_direct_ledger_rejects_foreign_row_profile(
    tmp_path, monkeypatch, filename, loader, append, row,
):
    root = tmp_path / "trusted"
    root.mkdir()
    path = _private_path(root, filename)
    _activate(monkeypatch, tmp_path, root)
    foreign = row(profile_key="workspace-beta")

    with pytest.raises(authorization.WorkspaceAccessDenied):
        append(path, foreign)
    assert not path.exists()


@pytest.mark.parametrize("filename,loader,append,row", LEDGERS, ids=["journal", "catalyst", "outcome"])
def test_protected_ledger_rechecks_append_after_lock_when_membership_is_revoked(
    tmp_path, monkeypatch, filename, loader, append, row,
):
    root = tmp_path / "trusted"
    root.mkdir()
    path = _private_path(root, filename)
    config_path, config = _activate(monkeypatch, tmp_path, root)
    append(path, row())
    original = path.read_bytes()
    module = MODULES[filename]
    original_lock = module.ledger_write_lock

    @contextmanager
    def revoke_at_lock(destination):
        with original_lock(destination):
            config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            yield

    monkeypatch.setattr(module, "ledger_write_lock", revoke_at_lock)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        append(path, _second_row(filename, row))
    assert path.read_bytes() == original
    assert loader(path) == (row(),)


def test_journal_rechecks_append_after_existing_history_is_loaded(tmp_path, monkeypatch):
    root = tmp_path / "trusted"
    root.mkdir()
    path = _private_path(root, "research_thesis_journal.csv")
    config_path, config = _activate(monkeypatch, tmp_path, root)
    first = _entry(profile_key=PROFILE, ticker=TICKER)
    append_journal_entry(path, first)
    original = path.read_bytes()
    load = research_thesis_journal.load_journal_entries

    def downgrade_after_read(destination):
        rows = load(destination)
        config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return rows

    monkeypatch.setattr(research_thesis_journal, "load_journal_entries", downgrade_after_read)
    second = _second_row("research_thesis_journal.csv", lambda **changes: _entry(
        **{"profile_key": PROFILE, "ticker": TICKER, **changes}
    ))
    with pytest.raises(authorization.WorkspaceAccessDenied):
        append_journal_entry(path, second)
    assert path.read_bytes() == original
    assert load(path) == (first,)
