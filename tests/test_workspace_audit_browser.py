"""Rehearse durable workspace audit decisions through the real desktop and phone UI."""

from contextlib import contextmanager
from datetime import datetime, timedelta
from hashlib import sha256
import json

import pytest

from src.company_research_notes import CompanyNotesScope, load_company_notes, notes_paths
from tests.test_workspace_authorization_browser import (
    CIK, ISSUER, TICKER, _absent, _files, _monitor, _notes_url, _page,
    _pinned_monitor, _protected, _ready_note, _saved_valuation, _settle, _workbench,
    _workspace_denied, _workspace_server, _write_json, browser, workspace_evidence,
)


def _assert_decision(rows, workspace, subject, action, resource, outcome, reason):
    expected = dict(workspace_id=sha256(workspace.encode()).hexdigest(),
                    principal_id=sha256(json.dumps([ISSUER, subject]).encode()).hexdigest(),
                    action=action, resource=resource, outcome=outcome, reason_code=reason)
    assert any(all(row.get(key) == value for key, value in expected.items()) for row in rows), expected


def _new_revision(address, page, expect, width, current, note):
    page.goto(address + _notes_url())
    expect(page.get_by_text(current.summary, exact=True).first).to_be_visible(timeout=30_000)
    button = _ready_note(page, expect, width, current.entry_id, note)
    _settle(page, width)
    expect(button).to_be_enabled()
    return button


@contextmanager
def _unavailable_audit_home(home):
    retained = home.with_name("retained-audit")
    home.rename(retained)
    home.write_text("No writable audit directory", encoding="utf-8")
    try:
        yield
    finally:
        home.unlink()
        retained.rename(home)


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)], ids=["desktop", "phone"])
def test_workspace_audit_persists_protected_actions_and_fails_closed(
    browser, workspace_evidence, tmp_path, width, height,
):
    engine, expect = browser
    store, config_path, registry, cases = workspace_evidence
    alpha, alpha_note = cases["alpha"]
    beta, beta_note = cases["beta"]
    alpha_id, beta_id = alpha["snapshot_id"], beta["snapshot_id"]
    original, protected = _files(store), _protected()
    audit_home = (tmp_path / "audit").resolve()
    audit_home.mkdir(mode=0o700)
    audit_path = audit_home / "events.sqlite3"

    with _workspace_server(tmp_path / "beta", config_path, "beta", "bob", audit_db=audit_path) as address, \
            _page(engine, address, width, height) as page:
        page.goto(address + _workbench(beta_id))
        _saved_valuation(page, expect, beta, width)
        page.get_by_role("button", name="Open Monitor", exact=True).click()
        _pinned_monitor(page, expect, beta, beta_note, width)
        page.reload()
        _pinned_monitor(page, expect, beta, beta_note, width)
        page.get_by_role("button", name="Reopen exact saved research", exact=True).click()
        _saved_valuation(page, expect, beta, width)
        page.goto(address + _workbench(alpha_id, section="notes"))
        expect(page.get_by_text(f"Saved online research is unavailable for {TICKER}", exact=True)).to_be_visible()
        _absent(page, expect, alpha_note, alpha_id[:12], "Historical replay ·")
    assert _files(store) == original
    assert audit_path.is_file(), "Protected reads did not create a durable workspace audit database"
    from src.workspace_audit import read_workspace_audit
    reader_rows = read_workspace_audit(audit_path)
    _assert_decision(reader_rows, "beta", "bob", "read", "saved_workspace_state", "allowed", "allowed")

    valid_note = "Synthetic editor revision tested with durable auditing."
    stale_note = "Synthetic unsaved revision must remain private."
    with _workspace_server(tmp_path / "alpha", config_path, "alpha", "alice", audit_db=audit_path) as address, \
            _page(engine, address, width, height) as page:
        page.goto(address + _notes_url())
        expect(page.get_by_text(alpha_note, exact=True).first).to_be_visible(timeout=30_000)
        _ready_note(page, expect, width, "entry-one", valid_note).click()
        expect(page.get_by_text("Record saved", exact=True)).to_be_visible(timeout=30_000)
        _settle(page, width)
        scope = CompanyNotesScope("workspace-alpha", TICKER, CIK)
        saved = next(row for row in load_company_notes(scope, project_root=store).journal
                     if row.summary == valid_note)
        stable = _files(store)
        assert {path for path in set(original) | set(stable) if original.get(path) != stable.get(path)} == {
            notes_paths(scope, project_root=store).journal,
        }

        stale = _new_revision(address, page, expect, width, saved, stale_note)
        before_outage = read_workspace_audit(audit_path)
        with _unavailable_audit_home(audit_home):
            stale.click()
            _workspace_denied(page, expect, width, alpha_note, valid_note, stale_note, alpha_id[:12])
            for route in (_workbench(alpha_id), _monitor(alpha_id)):
                page.goto(address + route)
                _workspace_denied(page, expect, width, alpha_note, valid_note, alpha_id[:12])
            page.screenshot(path=str(tmp_path / "audit-unavailable.png"), animations="disabled")
        assert _files(store) == stable
        assert read_workspace_audit(audit_path) == before_outage

        stale = _new_revision(address, page, expect, width, saved, stale_note)
        membership = registry["workspaces"]["alpha"]["members"][0]
        membership["role"] = "viewer"
        _write_json(config_path, registry)
        stale.click()
        _settle(page, width)
        expect(page.get_by_role("button", name="Confirm and save", exact=True)).to_have_count(0)
        assert _files(store) == stable

        page.goto(address + _monitor(alpha_id))
        _pinned_monitor(page, expect, alpha, valid_note, width)
        reopen = page.get_by_role("button", name="Reopen exact saved research", exact=True)
        expect(reopen).to_be_enabled()
        membership["active"] = False
        _write_json(config_path, registry)
        reopen.click()
        _workspace_denied(page, expect, width, alpha_note, valid_note, alpha_id[:12])
        page.screenshot(path=str(tmp_path / "revoked-monitor.png"), animations="disabled")

    with _workspace_server(tmp_path / "foreign", config_path, "beta", "alice", audit_db=audit_path) as address, \
            _page(engine, address, width, height) as page:
        page.goto(address + _monitor(beta_id))
        _workspace_denied(page, expect, width, alpha_note, beta_note, beta_id[:12])
    assert _files(store) == stable and _protected() == protected
    assert not (store / "data").exists()

    rows = read_workspace_audit(audit_path)
    assert rows[:len(reader_rows)] == reader_rows
    _assert_decision(rows, "alpha", "alice", "append", "research_record", "allowed", "allowed")
    _assert_decision(rows, "alpha", "alice", "read", "saved_workspace_state", "denied", "membership_inactive")
    _assert_decision(rows, "beta", "alice", "read", "saved_workspace_state", "denied", "membership_inactive")
    assert [row["sequence"] for row in rows] == sorted({row["sequence"] for row in rows})
    assert len({row["request_id"] for row in rows}) == len(rows)
    for row in rows:
        assert set(row) == {"sequence", "schema_version", "event_type", "request_id", "principal_id",
                            "workspace_id", "resource", "action", "outcome", "reason_code", "occurred_at"}
        assert row["schema_version"] == "research-workspace-audit-v1"
        assert row["event_type"] == "workspace_access_decision"
        assert datetime.fromisoformat(row["occurred_at"]).utcoffset() == timedelta(0)
    saved_audit = audit_path.read_bytes()
    for private_value in (alpha_note, beta_note, valid_note, stale_note, alpha_id, beta_id, CIK, TICKER, ISSUER,
                          "alice", "bob", "workspace-alpha", "workspace-beta"):
        assert private_value.encode() not in saved_audit

    (tmp_path / "audit-browser-proof.json").write_text(json.dumps({
        "status": "passed", "dimensions": [width, height], "authorized_replay": True,
        "authorized_append_count": 1, "durable_decision_count": len(rows), "restart_preserved_decisions": True,
        "audit_unavailability_blocked_reads_and_stale_write": True, "audit_excluded_private_content": True,
        "outbound_requests": 0,
    }, indent=2) + "\n", encoding="utf-8")
