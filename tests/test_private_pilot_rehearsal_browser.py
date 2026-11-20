"""Local profile partition and saved-evidence replay against the dashboard."""

from contextlib import ExitStack, contextmanager
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from src.company_research_notes import CompanyNotesScope, load_company_notes, notes_paths
from src.online_peer_sources import _cache
from src.online_research_context_store import load_research_context, save_research_context
from src.online_research_tools import build_online_research_context
from src.public_performance_gate import _free_port, _wait_for_dom_stability, _wait_for_health, find_chrome_executable
from src.research_thesis_journal import append_journal_entry
from tests.test_company_research_notes import entry
from tests.test_online_research_tools import NOW, financial
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


PROJECT = Path(__file__).resolve().parents[1]
TICKER, CIK = "FICT", "0000001234"
PROFILES = ("pilot-workbench-alpha", "pilot-workbench-beta")
PRIOR_REVISION = "c1cb630854bc2e21831d04effef248bf2a640981"
PRIVATE_DIRS = ("online-research-contexts", "company-research-notes", "sec-research-reviews")


def _files(root):
    return {
        path: sha256(path.read_bytes()).hexdigest()
        for name in PRIVATE_DIRS
        for path in (root / "outputs" / "local" / name).rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def _protected():
    canonical = {
        path: sha256(path.read_bytes()).hexdigest()
        for folder in ("data/demo", "config")
        for path in (PROJECT / folder).rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    return canonical | _files(PROJECT)


def _scope(root, profile):
    return dict(profile_key=profile, ticker=TICKER, sec_cik=CIK, project_root=root)


@pytest.fixture
def disposable_evidence(tmp_path):
    store = tmp_path / "shared-store"
    cases = {}
    peer = _cache({}, TICKER, None, "vendor_context_source_unavailable", NOW)
    for profile in PROFILES:
        scope = CompanyNotesScope(profile, TICKER, CIK)
        note = f"Synthetic thesis for {profile} only."
        journal = replace(entry(profile=profile, ticker=TICKER), summary=note,
                          recorded_at="2026-10-30T12:00:00Z", effective_at="2026-10-30T11:00:00Z")
        append_journal_entry(notes_paths(scope, project_root=store).journal, journal)
        context = build_online_research_context(financial(), {}, peer,
            ticker=TICKER, profile_key=profile, expected_cik=CIK, as_of=NOW,
            notes=load_company_notes(scope, project_root=store))
        assert context["notes_summary"]["current_thesis"] == note
        assert context["peer_read_through"]["reason"] == "vendor_context_source_unavailable"
        assert context["commercial_eligible"] is context["saved_readiness_promoted"] is False
        cases[profile] = save_research_context(context, **_scope(store, profile)), note
    assert len({snapshot["snapshot_id"] for snapshot, _ in cases.values()}) == 2
    return store, cases


@contextmanager
def _server(project, directory, store, profile):
    directory.mkdir()
    entrypoint = directory / "rehearsal_app.py"
    denied = directory / "provider-requests.txt"
    entrypoint.write_text(
        "from pathlib import Path\nfrom private_pilot_rehearsal_fixture import run\n"
        f"run(Path({str(store)!r}), {profile!r}, Path({str(denied)!r}))\n", encoding="utf-8")
    address = f"http://127.0.0.1:{_free_port()}"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(project), str(PROJECT / "tests"))),
           "PYTHONDONTWRITEBYTECODE": "1", "STOCK_RESEARCH_DATA_PROFILE": "demo",
           "SEC_USER_AGENT": "Synthetic local rehearsal contact@example.com"}
    env.pop("COMMERCIAL_RESEARCH_MODE", None)
    with (directory / "streamlit.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(entrypoint),
             "--server.address", "127.0.0.1", "--server.port", str(urlsplit(address).port),
             "--server.headless", "true", "--server.fileWatcherType", "none",
             "--browser.gatherUsageStats", "false"],
            cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_for_health(address, timeout_seconds=45)
            yield address
            assert not denied.exists()
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.fixture
def browser():
    chrome = find_chrome_executable()
    if not chrome:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        yield browser, playwright.expect


@contextmanager
def _page(browser, address, width, height):
    context = browser.new_context(viewport={"width": width, "height": height},
        is_mobile=width < 640, has_touch=width < 640, color_scheme="dark" if width < 640 else "light")
    rejected, errors = [], []

    def only_local(route):
        if route.request.url.startswith(address + "/"):
            route.continue_()
        else:
            rejected.append(route.request.url)
            route.abort()

    context.route("**/*", only_local)
    page = context.new_page()
    page.set_default_timeout(30_000)
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        yield page
        assert not rejected and not errors
    finally:
        context.close()


def _workbench(snapshot_id, *, section="valuation"):
    return "/?" + urlencode(dict(mode="research", page="company-workbench", ticker=TICKER,
                                 section=section, research_cik=CIK, research_snapshot=snapshot_id))


def _monitor(snapshot_id):
    return "/?" + urlencode(dict(mode="research", page="monitor", return_ticker=TICKER,
        return_section="valuation", return_research_cik=CIK, return_research_snapshot=snapshot_id))


def _settle(page, width):
    page.wait_for_function("""() => document.querySelector('[data-testid="stApp"]')
                              ?.getAttribute('data-test-script-state') === 'notRunning'""")
    _wait_for_dom_stability(page, timeout_seconds=12, stable_checks=2)
    assert page.get_by_test_id("stException").count() == 0
    assert page.locator("html").evaluate("element => element.scrollWidth") == width


def _saved_valuation(page, expect, snapshot, width):
    snapshot_id = snapshot["snapshot_id"]
    expect(page.get_by_text("Snapshot " + snapshot_id[:12] + " · SEC CIK " + CIK, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Historical replay · " + snapshot["observed_at"], exact=True)).to_be_visible()
    expect(page.get_by_role("radio", name="Valuation & Peers", exact=True)).to_be_checked()
    query = parse_qs(urlsplit(page.url).query)
    assert query["ticker"] == [TICKER] and query["research_cik"] == [CIK]
    assert query["section"] == ["valuation"] and query["research_snapshot"] == [snapshot_id]
    assert "online" not in query
    peer = page.get_by_role("region", name="Online peer valuation", exact=True)
    expect(peer.get_by_role("heading", name="Relative valuation withheld", exact=True)).to_be_visible()
    details = peer.locator("details > summary").filter(has_text="View actual fiscal periods, prices, and sources")
    if details.locator("..").get_attribute("open") is None:
        details.click()
    expect(peer.get_by_text("Commercial use and redistribution of price and provider data remain unreviewed.", exact=False)).to_be_visible()
    assert_rendered_english(page.locator("body"))
    _settle(page, width)


def _pinned_monitor(page, expect, snapshot, own_note, width):
    expect(page.get_by_text("Snapshot " + snapshot["snapshot_id"][:12], exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Selected observation: " + snapshot["observed_at"], exact=True)).to_be_visible()
    expect(page.get_by_text(own_note, exact=True)).to_be_visible()
    assert parse_qs(urlsplit(page.url).query) == parse_qs(urlsplit(_monitor(snapshot["snapshot_id"])).query)
    _settle(page, width)


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)], ids=["desktop", "phone"])
def test_local_pilot_profile_partition_and_exact_monitor_replay(browser, disposable_evidence, tmp_path, width, height):
    engine, expect = browser
    store, cases = disposable_evidence
    stored, protected = _files(store), _protected()
    checked = {}
    with ExitStack() as stack:
        addresses = {profile: stack.enter_context(_server(PROJECT, tmp_path / profile, store, profile))
                     for profile in PROFILES}
        for profile, other in (PROFILES, PROFILES[::-1]):
            snapshot, note = cases[profile]
            foreign, foreign_note = cases[other]
            own_id, foreign_id = snapshot["snapshot_id"], foreign["snapshot_id"]
            address = addresses[profile]
            with _page(engine, address, width, height) as page:
                page.goto(address + _workbench(own_id))
                _saved_valuation(page, expect, snapshot, width)
                page.get_by_role("button", name="Open Monitor", exact=True).click()
                _pinned_monitor(page, expect, snapshot, note, width)
                page.get_by_role("button", name="Reopen exact saved research", exact=True).click()
                _saved_valuation(page, expect, snapshot, width)
                page.screenshot(path=str(tmp_path / f"{profile}-exact-return.png"), animations="disabled")
                page.reload()
                _saved_valuation(page, expect, snapshot, width)
            with _page(engine, address, width, height) as page:
                page.goto(address + _monitor(own_id))
                _pinned_monitor(page, expect, snapshot, note, width)
                page.get_by_role("button", name=f"Return to {TICKER} Company Workbench", exact=True).click()
                _saved_valuation(page, expect, snapshot, width)
                notes = page.get_by_role("radio", name="Research Notes", exact=True)
                page.locator("label").filter(has=notes).click()
                expect(page.get_by_text(note, exact=True)).to_be_visible()
                expect(page.get_by_text(foreign_note, exact=True)).to_have_count(0)
            with _page(engine, address, width, height) as page:
                page.goto(address + _workbench(foreign_id, section="notes"))
                expect(page.get_by_text(f"Saved online research is unavailable for {TICKER}", exact=True)).to_be_visible(timeout=30_000)
                expect(page.get_by_text("Historical replay ·", exact=False)).to_have_count(0)
                expect(page.get_by_text(foreign_note, exact=True)).to_have_count(0)
                _settle(page, width)
                page.screenshot(path=str(tmp_path / f"{profile}-foreign-workbench.png"), animations="disabled")
                page.goto(address + _monitor(foreign_id))
                expect(page.get_by_text(note, exact=True)).to_be_visible(timeout=30_000)
                _settle(page, width)
                assert "return_research_snapshot" not in parse_qs(urlsplit(page.url).query)
                expect(page.get_by_text(foreign_note, exact=True)).to_have_count(0)
                expect(page.get_by_text(foreign_id[:12], exact=False)).to_have_count(0)
                expect(page.get_by_role("button", name=f"Return to {TICKER} Company Workbench", exact=True)).to_have_count(0)
                page.screenshot(path=str(tmp_path / f"{profile}-foreign-monitor.png"), animations="disabled")
                page.get_by_role("button", name="Reopen exact saved research", exact=True).click()
                expect(page.get_by_text("Snapshot " + own_id[:12] + " · SEC CIK " + CIK, exact=True)).to_be_visible(timeout=30_000)
                assert parse_qs(urlsplit(page.url).query)["research_snapshot"] == [own_id]
            assert load_research_context(own_id, **_scope(store, profile)) == snapshot
            checked[profile] = dict(snapshot_id=own_id, return_section="valuation", cold_reload=True,
                                   foreign_workbench_denied=True, foreign_monitor_denied=True)
    assert _files(store) == stored and _protected() == protected
    assert not (store / "data").exists()
    proof = dict(status="passed", dimensions=[width, height], profiles=checked,
                 passive_provider_requests=0, protected_files=len(protected), saved_files_unchanged=True)
    (tmp_path / "browser-proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")


def test_local_pilot_previous_application_reopens_current_saved_snapshot(browser, disposable_evidence, tmp_path):
    if subprocess.run(["git", "cat-file", "-e", PRIOR_REVISION + "^{commit}"], cwd=PROJECT,
                      capture_output=True).returncode:
        pytest.skip("Local rollback rehearsal requires the prior application commit")
    prior = tmp_path / "prior-application"
    prior.mkdir()
    with subprocess.Popen(["git", "archive", PRIOR_REVISION], cwd=PROJECT, stdout=subprocess.PIPE) as archive:
        with tarfile.open(fileobj=archive.stdout, mode="r|") as files:
            files.extractall(prior, filter="data")
        assert archive.wait(timeout=30) == 0
    workbench = "src/company_workbench_ui.py"
    assert (prior / workbench).read_bytes() != (PROJECT / workbench).read_bytes()
    engine, expect = browser
    store, cases = disposable_evidence
    profile = PROFILES[0]
    snapshot, note = cases[profile]
    stored, protected = _files(store), _protected()
    for label, project in (("current-before", PROJECT), ("previous", prior), ("current-after", PROJECT)):
        with _server(project, tmp_path / label, store, profile) as address, _page(engine, address, 1440, 1000) as page:
            page.goto(address + _monitor(snapshot["snapshot_id"]))
            _pinned_monitor(page, expect, snapshot, note, 1440)
            page.get_by_role("button", name="Reopen exact saved research", exact=True).click()
            _saved_valuation(page, expect, snapshot, 1440)
            page.screenshot(path=str(tmp_path / f"{label}-exact-return.png"), animations="disabled")
        assert load_research_context(snapshot["snapshot_id"], **_scope(store, profile)) == snapshot
        assert _files(store) == stored
    assert _protected() == protected
    proof = dict(status="passed", prior_revision=PRIOR_REVISION, snapshot_id=snapshot["snapshot_id"],
                 prior_and_current_workbench_differ=True, saved_files_unchanged=True, passive_provider_requests=0)
    (tmp_path / "browser-proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
