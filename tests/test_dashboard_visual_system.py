"""Byte-level characterization for the initial dashboard presentation seam."""

import hashlib
import json
from pathlib import Path

from src import dashboard
from src import dashboard_visual_system as visual
from src import research_workspace


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "dashboard_visual_system"
FIXTURE_CSS = FIXTURE_DIR / "research_accessibility_media_preferences.css"
FIXTURE_DOM = FIXTURE_DIR / "presentation_dom_snapshots.json"
FROZEN_CSS_SHA256 = "47e5d109fdc596795fedf32118a769c9d3c610bb766bad382e306934c1f7cc90"
FROZEN_DOM_SHA256 = "6b87d41542dc613ce4b5222025aa69fa4f86f5ebb82fe7c0b551c4a45f03a129"


def _dom_snapshots() -> dict[str, str]:
    return json.loads(FIXTURE_DOM.read_text(encoding="utf-8"))


def test_presentation_seam_keeps_accessibility_css_byte_identical():
    expected = FIXTURE_CSS.read_text(encoding="utf-8")

    assert hashlib.sha256(expected.encode()).hexdigest() == FROZEN_CSS_SHA256
    assert visual.legacy_research_accessibility_css() == expected
    assert "@media (forced-colors: active)" in expected
    assert "@media (prefers-reduced-motion: reduce)" in expected


def test_presentation_seam_keeps_rendered_stylesheet_byte_identical():
    expected_css = FIXTURE_CSS.read_text(encoding="utf-8")
    snapshots = _dom_snapshots()

    assert hashlib.sha256(FIXTURE_DOM.read_bytes()).hexdigest() == FROZEN_DOM_SHA256
    assert visual.render_stylesheet(visual.legacy_research_accessibility_css()) == snapshots[
        "accessibility_stylesheet"
    ]
    assert visual.render_stylesheet(expected_css) == snapshots["accessibility_stylesheet"]


def test_presentation_seam_keeps_public_helper_dom_snapshots_byte_identical():
    snapshots = _dom_snapshots()

    assert research_workspace.research_workflow_navigation_html(
        active_page="Company Workbench", ticker="brk/b"
    ) == snapshots["research_workflow_navigation_html"]
    assert dashboard.public_workflow_skip_link_html(
        "?mode=research&page=company-workbench&ticker=AAPL's&open=1"
    ) == snapshots["public_workflow_skip_link_html"]
    assert dashboard.section_header_html(
        "<Monthly Picks>", "Use <local> research coverage."
    ) == snapshots["section_header_html"]


def test_presentation_seam_escapes_text_and_quoted_attributes():
    assert visual.escape_text('<Research & "workspace">') == '&lt;Research &amp; "workspace"&gt;'
    assert visual.escape_attribute("AAPL's \"review\" & <local>") == (
        "AAPL&#x27;s &quot;review&quot; &amp; &lt;local&gt;"
    )
