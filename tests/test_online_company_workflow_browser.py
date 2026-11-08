"""Online issuer notes and saved SEC observations survive independent Monitor routes."""

from contextlib import contextmanager
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import find_chrome_executable
from tests.test_research_monitor_roundtrip_browser import (
    assert_rendered_english,
    research_browser_server,
)


_MODEL_GAP = (
    "Online tools below use the selected company’s observations and explicit assumptions. "
    "Saved model eligibility and the full saved Research Brief retain their separate review requirements."
)


@contextmanager
def _browser(base, width, height):
    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_default_timeout(15000)
            blocked, errors = [], []

            def local_only(route):
                if route.request.url.startswith(base + "/"):
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()

            page.route("**/*", local_only)
            page.on("pageerror", lambda error: errors.append(str(error)))
            yield page, playwright.expect, blocked, errors
        finally:
            browser.close()


def _calls(root):
    path = root / "provider-calls.txt"
    return path.read_text().splitlines() if path.exists() else []


def _surface(page, width, *actions):
    assert_rendered_english(page.locator("body"))
    assert page.locator("html").evaluate("node => node.scrollWidth") <= width + 1
    assert not page.get_by_test_id("stException").count()
    assert not page.get_by_role("alert", name="Saved report unavailable", exact=True).count()
    assert not page.locator(".single-stock-report-unavailable").count()
    for action in actions:
        box = action.bounding_box()
        assert box and box["height"] >= 44, action.inner_text()


def _section(page, expect, label):
    radio = page.get_by_role("radio", name=label, exact=True)
    page.locator("label").filter(has=radio).click()
    expect(radio).to_be_checked()


def _expect_note_summary(page, expect, summary):
    rendered = page.get_by_test_id("stText").get_by_text(summary, exact=True).filter(visible=True)
    expect(rendered).to_have_count(1)
    expect(rendered).to_be_visible()


def _assert_issuer_scoped_thesis_field(field):
    assert field.evaluate("""node => node.closest('[data-testid="stElementContainer"]').classList.contains(
      'st-key-research-authoring-demo-FICT-cik-0000001234-field-thesis-thesis_id')""")


def _show_sec_evidence(page):
    summary = page.locator("summary").filter(has=page.get_by_text("Saved SEC evidence", exact=True))
    if summary.locator("..").get_attribute("open") is None:
        summary.click()


@pytest.mark.parametrize("width,height", [(1280, 900), (390, 844)], ids=["desktop", "phone"])
def test_saved_notes_only_reopen_from_monitor_without_sec_receipts_or_provider_requests(
    research_browser_server, tmp_path, width, height,
):
    from src.company_research_notes import CompanyNotesScope, notes_paths
    from src.research_thesis_journal import append_journal_entry
    from tests.test_company_research_notes import entry

    scope = CompanyNotesScope("demo", "FICT", "0000001234")
    path = notes_paths(scope, project_root=tmp_path).journal
    summary = "Disposable notes-only browser record: inspect the next cash-flow disclosure."
    append_journal_entry(path, replace(entry(), summary=summary))
    original_notes = path.read_bytes()

    with _browser(research_browser_server, width, height) as (page, expect, blocked, errors):
        page.goto(research_browser_server + "/?mode=research&page=company-workbench"
                  "&ticker=FICT&section=notes&notes_cik=0000001234")
        expect(page.get_by_role("heading", name="Your company notes", exact=True)).to_be_visible()
        _expect_note_summary(page, expect, summary)
        expect(page.get_by_text(_MODEL_GAP, exact=True)).to_be_visible()
        opacity=page.get_by_text(_MODEL_GAP,exact=True).evaluate("""element => {
          let opacity=1;
          for(let node=element;node;node=node.parentElement) opacity*=Number(getComputedStyle(node).opacity);
          return opacity;
        }""")
        assert opacity==1, 'Model gaps and note identity must not be dimmed by caption opacity'
        _surface(page, width)
        navigation = page.get_by_role("navigation", name="Personal research workflow")
        navigation.get_by_role("link", name="Monitor", exact=True).click()
        expect(page.get_by_role("heading", name="User-authored follow-ups", exact=True)).to_be_visible()
        _expect_note_summary(page, expect, summary)
        expect(page.get_by_role("heading", name="Saved SEC evidence review queue", exact=True)).to_have_count(0)
        open_notes = page.get_by_role("button", name="Open FICT notes", exact=True)
        _surface(page, width, open_notes)
        open_notes.click()
        expect(page.get_by_role("heading", name="Your company notes", exact=True)).to_be_visible()
        query = parse_qs(urlsplit(page.url).query)
        assert query.get("notes_cik") == ["0000001234"] and "online" not in query
        _expect_note_summary(page, expect, summary)
        page.reload()
        expect(page.get_by_role("heading", name="Your company notes", exact=True)).to_be_visible()
        _expect_note_summary(page, expect, summary)
        assert path.read_bytes() == original_notes
        assert not list((tmp_path / "outputs/local/sec-research-reviews").rglob("*.json"))
        assert not (tmp_path / "data").exists()
        assert _calls(tmp_path) == []
        assert not blocked and not errors
        _surface(page, width)


@pytest.mark.parametrize("width,height", [(1280, 900), (390, 844)], ids=["desktop", "phone"])
def test_online_company_authors_notes_saves_real_sec_baseline_and_returns_without_refetch(
    research_browser_server, tmp_path, width, height,
):
    from src.company_research_notes import CompanyNotesScope, notes_paths
    from src.research_thesis_journal import load_journal_entries
    from src.sec_research_review import compare_reviews, list_reviews

    scope = CompanyNotesScope("demo", "FICT", "0000001234")
    journal = notes_paths(scope, project_root=tmp_path).journal
    summary = "Synthetic reviewed thesis: revisit the next directly reported cash-flow period."
    with _browser(research_browser_server, width, height) as (page, expect, blocked, errors):
        page.goto(research_browser_server + "/?mode=research&page=discover")
        query = page.get_by_role("textbox", name="Company name or ticker", exact=True)
        query.fill("FICT")
        search = page.get_by_role("button", name="Search company", exact=True)
        _surface(page, width, search)
        search.click()
        result = page.get_by_role("region", name="SEC online company results", exact=True)
        expect(result).to_contain_text("No local ticker row")
        assert _calls(tmp_path) == ["search"]
        open_company = result.get_by_role("link", name="Open company evidence", exact=True)
        _surface(page, width, open_company)
        open_company.click()
        brief = page.get_by_role("region", name="Company Brief", exact=True)
        expect(brief.get_by_role("heading", name="FICT Company Brief", exact=True)).to_be_visible()
        _section(page, expect, "Research Notes")
        expect(page.get_by_role("heading", name="Your company notes", exact=True)).to_be_visible()
        expect(page.get_by_text(_MODEL_GAP, exact=True)).to_be_visible()
        page.get_by_text("Add a reviewed research record", exact=True).click()
        thesis_id = page.get_by_role("textbox", name="Thesis Id", exact=True)
        _assert_issuer_scoped_thesis_field(thesis_id)
        fields = {
            "Thesis Id": "browser-fict-thesis",
            "Summary": summary,
            "Effective At": "2026-11-07T11:00:00Z",
            "Reviewer": "Synthetic browser reviewer",
            "Confidence": "0.50",
            "Review Due Date": "2026-12-01",
        }
        for label, value in fields.items():
            page.get_by_role("textbox", name=label, exact=True).fill(value)
        validate = page.get_by_role("button", name="Validate and preview", exact=True)
        _surface(page, width, validate)
        validate.click()
        expect(page.get_by_role("heading", name="Exact append-only preview", exact=True)).to_be_visible()
        expect(page.get_by_text("Preview ready", exact=True)).to_be_visible()
        assert not journal.exists(), "Preview wrote a research record before explicit confirmation"
        save_note = page.get_by_role("button", name="Confirm and save", exact=True)
        _surface(page, width, save_note)
        save_note.click()
        expect(page.get_by_text("Review and confirm the exact preview before saving.", exact=True)).to_be_visible()
        assert not journal.exists(), "An unchecked confirmation saved the note"
        confirmation = page.get_by_role("checkbox", name="I reviewed this exact record and its source evidence", exact=True)
        page.locator("label").filter(has=confirmation).click()
        expect(confirmation).to_be_checked()
        save_note.click()
        expect(page.get_by_text("Record saved", exact=True)).to_be_visible()
        _expect_note_summary(page, expect, summary)
        rows = load_journal_entries(journal)
        assert len(rows) == 1 and rows[0].summary == summary
        assert (rows[0].profile_key, rows[0].ticker, rows[0].thesis_id) == ("demo", "FICT", "browser-fict-thesis")
        note_bytes = journal.read_bytes()

        page.reload()
        expect(page.get_by_role("heading", name="Your company notes", exact=True)).to_be_visible()
        _expect_note_summary(page, expect, summary)
        page.get_by_text("Add a reviewed research record", exact=True).click()
        expect(thesis_id).to_have_value("browser-fict-thesis")
        expect(thesis_id).to_be_disabled()
        _assert_issuer_scoped_thesis_field(thesis_id)
        assert journal.read_bytes() == note_bytes
        assert not (tmp_path / "data").exists()

        refresh = page.get_by_role("button", name="Research company", exact=True)
        _surface(page, width, refresh)
        refresh.click()
        expect(page.get_by_label("Loaded company observations", exact=True)).to_be_visible()
        _section(page, expect, "Overview")
        expect(brief.locator(".company-answer")).to_have_count(4)
        expect(page.get_by_role("region", name="Reported annual financials", exact=True)).to_be_visible()
        page.get_by_text("Price history", exact=True).click()
        prices = page.get_by_role("region", name="Daily price history", exact=True)
        expect(prices).to_contain_text("USD 11")
        original_prices = prices.inner_text()
        _section(page, expect, "Research Notes")
        _show_sec_evidence(page)
        panel = page.locator(".st-key-sec-review-panel")
        save_sec = panel.get_by_role("button", name="Save current SEC evidence", exact=True)
        expect(save_sec).to_be_enabled()
        _surface(page, width, save_sec)
        save_sec.click()
        expect(panel.get_by_role("heading", name="Replay saved evidence", exact=True)).to_be_visible()
        expect(panel).to_contain_text("Saved, awaiting a comparison baseline")
        save_sec.click()
        expect(panel.get_by_role("status").filter(has_text="No change")).to_contain_text(
            "Saved field values and reporting basis match."
        )
        receipts = list_reviews(tmp_path, "demo", "FICT")
        assert len(receipts) == 2
        assert receipts[0]["receipt_id"] != receipts[1]["receipt_id"]
        assert receipts[0]["fields"] == receipts[1]["fields"]
        assert receipts[0]["raw_payload_sha256"] == receipts[1]["raw_payload_sha256"]
        assert all(packet["sec_cik"] == "0000001234" for packet in receipts)
        assert compare_reviews(*receipts)["status"] == "unchanged"
        receipt_root = tmp_path / "outputs/local/sec-research-reviews"
        receipt_bytes = {path: path.read_bytes() for path in receipt_root.rglob("*.json")}
        assert len(receipt_bytes) == 2
        calls_before_monitor = _calls(tmp_path)
        assert calls_before_monitor.count("financial") == 1
        assert calls_before_monitor.count("prices") == 1
        assert calls_before_monitor.count("company-profile") == 1
        assert set(calls_before_monitor) == {"search", "financial", "prices", "company-profile", "peer-valuation"}
        original_brief = brief.inner_text()

        handoff = panel.get_by_role("link", name="View review items in Monitor", exact=True)
        _surface(page, width, handoff)
        handoff.click()
        expect(page.get_by_role("heading", name="FICT SEC evidence review", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="User-authored follow-ups", exact=True)).to_be_visible()
        expect(page.get_by_text("No change", exact=True)).to_be_visible()
        _expect_note_summary(page, expect, summary)
        expect(page.get_by_text("Saved companies 1", exact=False)).to_be_visible()
        expect(page.get_by_text("Saved company notes in this profile. These are user records, separate from saved SEC evidence and its company counts.", exact=True)).to_be_visible()
        back = page.get_by_role("button", name="Return to FICT Company Workbench", exact=True)
        _surface(page, width, back, page.get_by_role("button", name="Open FICT notes", exact=True))
        back.click()
        expect(page.get_by_role("radio", name="Research Notes", exact=True)).to_be_checked()
        _expect_note_summary(page, expect, summary)
        _show_sec_evidence(page)
        expect(panel.get_by_role("status").filter(has_text="No change")).to_contain_text(
            "Saved field values and reporting basis match."
        )
        expect(panel).to_contain_text("Selected issuer CIK 0000001234")
        assert brief.inner_text() == original_brief
        route = parse_qs(urlsplit(page.url).query)
        assert route.get("online") == ["1"] and route.get("ticker") == ["FICT"] and route.get("section") == ["notes"]
        assert _calls(tmp_path) == calls_before_monitor
        _section(page, expect, "Overview")
        expect(brief.locator(".company-answer")).to_have_count(4)
        page.get_by_text("Price history", exact=True).click()
        expect(prices).to_be_visible()
        assert prices.inner_text() == original_prices
        assert _calls(tmp_path) == calls_before_monitor

        _section(page, expect, "Research Notes")
        _show_sec_evidence(page)
        panel.get_by_role("link", name="View review items in Monitor", exact=True).click()
        open_notes = page.get_by_role("button", name="Open FICT notes", exact=True)
        expect(open_notes).to_be_visible()
        open_notes.click()
        expect(page.get_by_role("heading", name="Your company notes", exact=True)).to_be_visible()
        route = parse_qs(urlsplit(page.url).query)
        assert route.get("notes_cik") == ["0000001234"] and "online" not in route
        _expect_note_summary(page, expect, summary)
        page.reload()
        expect(page.get_by_role("heading", name="Your company notes", exact=True)).to_be_visible()
        _expect_note_summary(page, expect, summary)
        expect(page.get_by_text(_MODEL_GAP, exact=True)).to_be_visible()
        assert _calls(tmp_path) == calls_before_monitor
        assert journal.read_bytes() == note_bytes
        assert {path: path.read_bytes() for path in receipt_root.rglob("*.json")} == receipt_bytes
        assert not (tmp_path / "data").exists()
        assert not blocked and not errors
        _surface(page, width)
