"""Exercise the application workspace boundary with synthetic identity claims."""

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from src.company_research_notes import CompanyNotesScope, load_company_notes, notes_paths
from src.online_peer_sources import _cache
from src.online_research_context_store import save_research_context
from src.online_research_tools import build_online_research_context
from src.public_performance_gate import _free_port, _wait_for_health
from src.research_thesis_journal import append_journal_entry
from tests.test_company_research_notes import entry
from tests.test_online_research_tools import NOW, financial
from tests.test_private_pilot_rehearsal_browser import (
    CIK, PROJECT, TICKER, _files, _monitor, _page, _pinned_monitor, _protected,
    _saved_valuation, _scope, _settle, _workbench, browser,
)


ISSUER = "https://identity.example"
AUDIENCE = "stock-research"
DENIED = "Workspace access unavailable"


def _write_json(path, document):
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(document), encoding="utf-8")
    pending.chmod(0o600)
    pending.replace(path)


@pytest.fixture
def workspace_evidence(tmp_path):
    store = (tmp_path / "workspace-records").resolve()
    store.mkdir(mode=0o700)
    config = {
        "schema_version": "research-workspace-access-v1",
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "storage_root": str(store),
        "workspaces": {
            "alpha": {"profile_key": "workspace-alpha", "members": [
                {"subject": "alice", "role": "editor", "active": True}]},
            "beta": {"profile_key": "workspace-beta", "members": [
                {"subject": "bob", "role": "viewer", "active": True}]},
        },
    }
    cases = {}
    peer = _cache({}, TICKER, None, "vendor_context_source_unavailable", NOW)
    for workspace, metadata in config["workspaces"].items():
        profile = metadata["profile_key"]
        note = f"Synthetic starting note in {workspace} only."
        scope = CompanyNotesScope(profile, TICKER, CIK)
        journal = replace(entry(profile=profile, ticker=TICKER), summary=note,
                          recorded_at="2026-10-30T12:00:00Z", effective_at="2026-10-30T11:00:00Z")
        append_journal_entry(notes_paths(scope, project_root=store).journal, journal)
        context = build_online_research_context(financial(), {}, peer,
            ticker=TICKER, profile_key=profile, expected_cik=CIK, as_of=NOW,
            notes=load_company_notes(scope, project_root=store))
        assert context["notes_summary"]["current_thesis"] == note
        assert context["commercial_eligible"] is False
        cases[workspace] = save_research_context(context, **_scope(store, profile)), note
    assert len({snapshot["snapshot_id"] for snapshot, _ in cases.values()}) == 2
    config_path = (tmp_path / "workspaces.json").resolve()
    _write_json(config_path, config)
    return store, config_path, config, cases


@contextmanager
def _workspace_server(directory, config_file, workspace, subject):
    directory.mkdir()
    identity = directory / "server-identity.json"
    _write_json(identity, dict(is_logged_in=True, sub=subject, iss=ISSUER, aud=AUDIENCE,
                              exp=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())))
    unexpected = directory / "unexpected-outbound.txt"
    entrypoint = directory / "workspace_app.py"
    entrypoint.write_text(
        "from pathlib import Path\nfrom workspace_authorization_browser_fixture import run\n"
        f"run(Path({str(identity)!r}), Path({str(unexpected)!r}))\n", encoding="utf-8")
    address = f"http://127.0.0.1:{_free_port()}"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(PROJECT), str(PROJECT / "tests"))),
           "PYTHONDONTWRITEBYTECODE": "1", "STOCK_RESEARCH_DATA_PROFILE": "demo",
           "STOCK_RESEARCH_ACCESS_MODE": "workspace",
           "STOCK_RESEARCH_WORKSPACE_CONFIG": str(config_file), "STOCK_RESEARCH_WORKSPACE_ID": workspace}
    env.pop("COMMERCIAL_RESEARCH_MODE", None)
    env.pop("SEC_USER_AGENT", None)
    with (directory / "streamlit.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(entrypoint),
             "--server.address", "127.0.0.1", "--server.port", str(urlsplit(address).port),
             "--server.headless", "true", "--server.fileWatcherType", "none",
             "--browser.gatherUsageStats", "false"],
            cwd=PROJECT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_for_health(address, timeout_seconds=45)
            yield address
            assert not unexpected.exists()
        finally:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def _notes_url():
    return "/?" + urlencode(dict(mode="research", page="company-workbench", ticker=TICKER,
                                 notes_cik=CIK, section="notes"))


def _absent(page, expect, *texts):
    for value in texts:
        expect(page.get_by_text(value, exact=False)).to_have_count(0)


def _workspace_denied(page, expect, width, *private_values):
    expect(page.get_by_role("heading", name=DENIED, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Sign in with an active membership for this workspace.", exact=True)).to_be_visible()
    _settle(page, width)
    _absent(page, expect, *private_values)
    expect(page.get_by_role("button", name="Reopen exact saved research", exact=True)).to_have_count(0)


def _ready_note(page, expect, width, active_entry_id, note):
    authoring = page.locator("details > summary").filter(
        has=page.get_by_text("Add a reviewed research record", exact=True))
    expect(authoring).to_be_visible(timeout=30_000)
    if authoring.locator("..").get_attribute("open") is None:
        authoring.click()
    thesis_id = page.get_by_role("textbox", name="Thesis Id", exact=True)
    expect(thesis_id).to_be_disabled()
    expect(thesis_id).to_have_value("thesis-one")
    expect(page.get_by_role("combobox", name="Supersedes Entry Id", exact=True)).to_have_value(active_entry_id)
    now = datetime.now(timezone.utc)
    values = {"Summary": note, "Reviewer": "Synthetic workspace reviewer",
              "Effective At": (now - timedelta(hours=1)).isoformat(), "Confidence": "0.50",
              "Review Due Date": (now + timedelta(days=7)).date().isoformat()}
    for label, value in values.items():
        page.get_by_role("textbox", name=label, exact=True).fill(value)
    page.get_by_role("textbox", name="Review Due Date", exact=True).press("Tab")
    _settle(page, width)
    validate = page.get_by_role("button", name="Validate and preview", exact=True)
    expect(validate).to_be_enabled()
    validate.press("Enter")
    expect(page.get_by_role("heading", name="Exact append-only preview", exact=True)).to_be_visible()
    confirmed = page.get_by_role("checkbox", name="I reviewed this exact record and its source evidence", exact=True)
    page.locator("label").filter(has=confirmed).click()
    expect(confirmed).to_be_checked()
    save = page.get_by_role("button", name="Confirm and save", exact=True)
    expect(save).to_be_enabled()
    return save


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)], ids=["desktop", "phone"])
def test_workspace_auth_controls_workbench_monitor_and_stale_writes(browser, workspace_evidence, tmp_path, width, height):
    engine, expect = browser
    store, config_file, config, cases = workspace_evidence
    alpha, alpha_note = cases["alpha"]
    beta, beta_note = cases["beta"]
    alpha_id, beta_id = alpha["snapshot_id"], beta["snapshot_id"]
    protected, original = _protected(), _files(store)

    for workspace, subject, (own, note), (foreign, foreign_note) in (
        ("alpha", "alice", cases["alpha"], cases["beta"]),
        ("beta", "bob", cases["beta"], cases["alpha"]),
    ):
        own_id, foreign_id = own["snapshot_id"], foreign["snapshot_id"]
        with _workspace_server(tmp_path / subject, config_file, workspace, subject) as address, \
                _page(engine, address, width, height) as page:
            page.goto(address + _workbench(own_id))
            _saved_valuation(page, expect, own, width)
            page.get_by_role("button", name="Open Monitor", exact=True).click()
            _pinned_monitor(page, expect, own, note, width)
            _absent(page, expect, foreign_note, foreign_id[:12])
            page.get_by_role("button", name="Reopen exact saved research", exact=True).click()
            _saved_valuation(page, expect, own, width)
            page.reload()
            _saved_valuation(page, expect, own, width)
            page.screenshot(path=str(tmp_path / f"{subject}-own-return.png"), animations="disabled")

            page.goto(address + _workbench(foreign_id, section="notes"))
            expect(page.get_by_text(f"Saved online research is unavailable for {TICKER}", exact=True)).to_be_visible(timeout=30_000)
            _absent(page, expect, foreign_note, foreign_id[:12], "Historical replay ·")
            page.goto(address + _monitor(foreign_id))
            expect(page.get_by_text(note, exact=True).first).to_be_visible(timeout=30_000)
            _settle(page, width)
            assert "return_research_snapshot" not in parse_qs(urlsplit(page.url).query)
            _absent(page, expect, foreign_note, foreign_id[:12], "Selected observation:")
            page.screenshot(path=str(tmp_path / f"{subject}-foreign-monitor.png"), animations="disabled")

            forged = "&workspace=beta&profile_key=workspace-beta&role=owner" if subject == "alice" else \
                "&workspace=alpha&profile_key=workspace-alpha&role=owner"
            page.goto(address + _notes_url() + forged)
            expect(page.get_by_text(note, exact=True).first).to_be_visible(timeout=30_000)
            _settle(page, width)
            _absent(page, expect, foreign_note)
            if subject == "bob":
                _absent(page, expect, "Add a reviewed research record")
                expect(page.get_by_role("button", name="Save research snapshot", exact=True, disabled=False)).to_have_count(0)
                assert _files(store) == original
                continue

            valid_note = "Synthetic editor note committed in its own workspace."
            _ready_note(page, expect, width, "entry-one", valid_note).click()
            expect(page.get_by_text("Record saved", exact=True)).to_be_visible(timeout=30_000)
            _settle(page, width)
            scope = CompanyNotesScope("workspace-alpha", TICKER, CIK)
            saved = next(row for row in load_company_notes(scope, project_root=store).journal
                         if row.summary == valid_note)
            assert saved.thesis_id == "thesis-one" and saved.supersedes_entry_id == "entry-one"
            current = _files(store)
            changed = {path for path in set(original) | set(current) if original.get(path) != current.get(path)}
            assert changed == {notes_paths(scope, project_root=store).journal}
            page.goto(address + _notes_url())
            expect(page.get_by_text(valid_note, exact=True).first).to_be_visible(timeout=30_000)
            stale = _ready_note(page, expect, width, saved.entry_id, "Synthetic stale confirmation must be denied.")
            _settle(page, width)
            expect(stale).to_be_enabled()
            membership = config["workspaces"]["alpha"]["members"][0]
            membership["role"] = "viewer"
            _write_json(config_file, config)
            stale.click()
            _settle(page, width)
            expect(page.get_by_role("button", name="Confirm and save", exact=True)).to_have_count(0)
            assert _files(store) == current

            page.goto(address + _monitor(own_id))
            _pinned_monitor(page, expect, own, valid_note, width)
            reopen = page.get_by_role("button", name="Reopen exact saved research", exact=True)
            expect(reopen).to_be_enabled()
            membership["active"] = False
            _write_json(config_file, config)
            reopen.click()
            _workspace_denied(page, expect, width, note, valid_note, own_id[:12])
            for route in (_workbench(own_id), _monitor(own_id)):
                page.goto(address + route)
                _workspace_denied(page, expect, width, note, valid_note, own_id[:12])
            page.screenshot(path=str(tmp_path / "alice-revoked-cold-monitor.png"), animations="disabled")
            assert _files(store) == current
            original = current

    # Alice's valid credentials do not authorize the separately configured beta process.
    with _workspace_server(tmp_path / "alice-on-beta", config_file, "beta", "alice") as address, \
            _page(engine, address, width, height) as page:
        for route in (_workbench(beta_id), _monitor(beta_id)):
            page.goto(address + route + "&workspace=alpha&role=owner")
            _workspace_denied(page, expect, width, alpha_note, beta_note, alpha_id[:12], beta_id[:12])
        page.screenshot(path=str(tmp_path / "alice-beta-membership-denied.png"), animations="disabled")

    assert _files(store) == original and _protected() == protected
    assert not (store / "data").exists()
    proof = dict(status="passed", dimensions=[width, height], allowed_editor_write=True,
                 stale_write_denied=True, viewer_read_only=True, forged_profile_ignored=True,
                 foreign_saved_routes_denied=True, foreign_workspace_access_denied=True,
                 revocation_rechecked=True, cold_returns_verified=True, outbound_requests=0)
    (tmp_path / "browser-proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
