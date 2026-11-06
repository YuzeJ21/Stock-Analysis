"""Verify the public company demo file and its offline browser controls."""

from html.parser import HTMLParser
import os
from pathlib import Path
import subprocess
import sys

import pytest


class _Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_demo_is_a_self_contained_explicit_cli_output(tmp_path):
    from scripts.build_company_demo import build_demo_html

    project = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-m", "scripts.build_company_demo"]
    env = {**os.environ, "PYTHONPATH": str(project), "PYTHONDONTWRITEBYTECODE": "1"}
    without_output = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True)
    assert without_output.returncode != 0
    assert not list(tmp_path.iterdir())

    path = tmp_path / "demo.html"
    subprocess.run([*command, "--output", str(path)], cwd=tmp_path, env=env, check=True)
    html = path.read_text(encoding="utf-8")
    assert list(tmp_path.iterdir()) == [path]
    assert html == build_demo_html()
    assert "虚构公司" in html and "合成数据" in html
    elements = _Document(html).elements
    assert "<title>Stock Research Command Center · 公司研究演示</title>" in html
    metadata = {attrs.get("name") or attrs.get("property"): attrs.get("content")
                for tag, attrs in elements if tag == "meta"}
    assert "Stock Research Command Center" in metadata["description"]
    assert metadata["og:title"] == "Stock Research Command Center · 公司研究演示"
    assert metadata["og:description"] == metadata["description"]
    assert "og:image" not in metadata
    ids = [attrs["id"] for _, attrs in elements if "id" in attrs]
    assert len(ids) == len(set(ids))
    assert not any(tag in {"script", "form", "img", "iframe", "link", "object"} for tag, _ in elements)
    assert not any({"src", "srcset", "action", "href"}.intersection(attrs) for _, attrs in elements)
    assert [attrs["data-company-answer"] for _, attrs in elements if "data-company-answer" in attrs] == [
        "price", "financial", "valuation", "price", "financial", "valuation",
    ]
    assert sum(tag == "details" for tag, _ in elements) == 6


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 720}, {"width": 390, "height": 844}], ids=["desktop", "phone"])
def test_demo_keyboard_switch_and_evidence_work_offline(tmp_path, viewport):
    from scripts.build_company_demo import build_demo_html
    from src.public_performance_gate import find_chrome_executable

    playwright = pytest.importorskip("playwright.sync_api")
    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")

    path = tmp_path / "demo.html"
    path.write_text(build_demo_html(), encoding="utf-8")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport=viewport, java_script_enabled=False)
            requests = []
            page.route("http*://**", lambda route: (requests.append(route.request.url), route.abort()))
            page.goto(path.as_uri())
            cards = page.locator("[data-company-answer]:visible")
            playwright.expect(cards).to_have_count(3)
            for card in cards.all():
                box = card.bounding_box()
                assert box["y"] >= 0 and box["y"] + box["height"] <= viewport["height"]
            assert page.locator("html").evaluate("e => e.scrollWidth") == viewport["width"]
            price, financial, valuation = cards.all()
            before = [price.inner_text(), financial.inner_text()]
            playwright.expect(price).to_contain_text("2026-10-30")
            playwright.expect(valuation).to_contain_text("20.0×")
            playwright.expect(valuation).to_contain_text("3 家符合")

            available = page.get_by_role("radio", name="3 家符合", exact=True)
            withheld = page.get_by_role("radio", name="2 家符合", exact=True)
            playwright.expect(available).to_be_checked()
            page.keyboard.press("Tab")
            playwright.expect(available).to_be_focused()
            page.keyboard.press("ArrowRight")
            playwright.expect(withheld).to_be_checked()
            playwright.expect(cards).to_have_count(3)
            price, financial, valuation = cards.all()
            assert [price.inner_text(), financial.inner_text()] == before
            playwright.expect(valuation).to_contain_text("同行比较暂缺")
            playwright.expect(valuation).to_contain_text("本公司 24.0×")
            playwright.expect(valuation).to_contain_text("至少需 3 家")
            playwright.expect(valuation).not_to_contain_text("20.0×")
            summary = valuation.locator("summary")
            summary.focus()
            page.keyboard.press("Enter")
            playwright.expect(valuation.locator("details")).to_have_attribute("open", "")
            playwright.expect(valuation).to_contain_text("2026-10-29")
            withheld.focus()
            page.keyboard.press("ArrowLeft")
            playwright.expect(available).to_be_checked()
            playwright.expect(cards.last).to_contain_text("20.0×")
            assert not requests
        finally:
            browser.close()
