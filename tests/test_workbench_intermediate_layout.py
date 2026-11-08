"""The horizontal company navigation needs a full row through the tablet breakpoint."""

from pathlib import Path

import pytest

from src.public_performance_gate import _local_demo_server, find_chrome_executable


@pytest.fixture(scope="module")
def workbench_page(tmp_path_factory):
    """Render real Streamlit columns with disposable, deterministic observations."""
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parents[1]
    fixture_root = tmp_path_factory.mktemp("workbench-intermediate-layout")
    (fixture_root / "src").mkdir()
    (fixture_root / "src/dashboard.py").write_text(
        "import sys\nimport streamlit as st\n"
        f"sys.path.insert(0, {str(root)!r})\n"
        "from src.dashboard import apply_dashboard_theme, render_research_workspace_styles\n"
        "import src.company_workbench_ui as ui\n"
        "from src.company_workbench_sections import workbench_projection\n"
        "from tests.test_company_workbench_sections import financial_view, price_view\n"
        "st.set_page_config(layout='wide')\n"
        "apply_dashboard_theme()\nrender_research_workspace_styles()\n"
        "financial, prices = financial_view(), price_view()\n"
        "ui.load_workbench_observations = lambda *a, **k: dict(\n"
        "    financial=financial, prices=prices, association={'status':'not_requested'},\n"
        "    projection=workbench_projection('FICT', financial, prices))\n"
        "ui.get_online_peer_valuation = lambda *a, **k: {'ticker':'FICT','status':'not_requested'}\n"
        "ui.render_integrated_company(st, 'FICT', profile_scope='synthetic',\n"
        "    saved_available=False, render_saved=lambda section: None,\n"
        "    render_sources=lambda bundle: None)\n",
        encoding="utf-8",
    )
    with _local_demo_server(fixture_root, timeout_seconds=30) as base:
        with sync_playwright() as runtime:
            chrome = find_chrome_executable()
            browser = runtime.chromium.launch(
                headless=True, **({"executable_path": str(chrome)} if chrome else {})
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(base, wait_until="domcontentloaded")
            page.get_by_role("heading", name="FICT Company Brief", exact=True).wait_for(timeout=15000)
            assert not page.get_by_test_id("stException").count()
            yield page
            browser.close()


@pytest.mark.parametrize("width", [390, 711, 726, 767, 768, 1440])
def test_horizontal_navigation_has_full_width_before_desktop_rail(workbench_page, width):
    page = workbench_page
    page.set_viewport_size({"width": width, "height": 1000})
    # Wait for the viewport's media rules and Streamlit's responsive wrappers to settle.
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    layout = page.evaluate("""() => {
      const bounds = element => {
        const r = element.getBoundingClientRect();
        return {left:r.left, right:r.right, top:r.top, bottom:r.bottom, width:r.width, height:r.height};
      };
      const root = document.querySelector('.st-key-company-workbench-layout');
      const rail = root.querySelector('.st-key-company-workbench-rail').closest('[data-testid="stColumn"]');
      const content = root.querySelector('.company-integrated-header').closest('[data-testid="stColumn"]');
      const navigation = root.querySelector('.st-key-company-section-navigation [role="radiogroup"]');
      return {
        root:bounds(root), rail:bounds(rail), content:bounds(content), navigation:bounds(navigation),
        direction:getComputedStyle(navigation).flexDirection,
        cards:[...root.querySelectorAll('.company-answer')].map(bounds),
        control_heights:[...root.querySelectorAll('.st-key-company-section-navigation label, .st-key-company-update-actions button')]
          .filter(e=>e.getClientRects().length).map(e=>bounds(e).height),
        nested_actions_direction:getComputedStyle(root.querySelector('.st-key-company-update-actions')).flexDirection,
        page_width:document.documentElement.scrollWidth
      };
    }""")
    assert layout["page_width"] <= width + 1, layout
    assert len(layout["control_heights"]) == 7, layout
    assert all(height >= 44 for height in layout["control_heights"]), layout
    assert layout["nested_actions_direction"] == "row", layout

    if width <= 767:
        assert layout["direction"] == "row", layout
        assert layout["content"]["top"] >= layout["rail"]["bottom"], layout
        assert abs(layout["rail"]["width"] - layout["root"]["width"]) <= 1, layout
        assert abs(layout["content"]["width"] - layout["root"]["width"]) <= 1, layout
        assert layout["navigation"]["left"] >= layout["rail"]["left"], layout
        assert layout["navigation"]["right"] <= layout["rail"]["right"], layout
    else:
        assert layout["direction"] == "column", layout
        assert abs(layout["content"]["top"] - layout["rail"]["top"]) <= 1, layout
        assert layout["content"]["left"] >= layout["rail"]["right"], layout

    if width == 390:
        first, second, third, fourth = layout["cards"]
        assert abs(first["top"] - second["top"]) <= 1, layout
        assert abs(third["top"] - fourth["top"]) <= 1, layout
        assert third["top"] >= max(first["bottom"], second["bottom"]), layout
