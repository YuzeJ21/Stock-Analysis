"""First-read hierarchy for the research company dossier."""

from src import dashboard, dashboard_visual_system, research_workspace


def test_discover_scope_is_compact_and_keeps_populations_distinct():
    rendered = dashboard.discover_primary_answer_html(
        25,
        0,
        research_boundary="Do not rank companies.",
    )

    assert "class='research-discover-scope'" in rendered
    assert "25 saved companies" in rendered
    assert "0 strict-screen eligible" in rendered
    assert "Do not rank companies." in rendered
    assert "The results below are alphabetical evidence paths" not in rendered


def test_research_dossier_css_uses_compact_top_navigation_and_inline_evidence():
    css = dashboard_visual_system.research_dossier_css()

    assert ".research-workflow-navigation" in css
    assert "position: sticky" in css
    assert ".company-workbench-evidence-status" in css
    assert ".company-workbench-evidence-table" in css
    assert ".research-discover-result" in css
    assert "@media (max-width: 640px)" in css


def test_company_summary_keeps_next_task_visible_and_change_detail_collapsed():
    rendered = research_workspace.company_workbench_primary_brief_html(
        {
            "ticker": "NVDA",
            "use_now": "Review saved model inputs.",
            "still_withheld": "Peer inputs are missing.",
            "what_changed": "No source-backed change is queued.",
            "next_task_title": "Review peers",
            "data_health_href": "?mode=research&page=data-health&ticker=NVDA",
        }
    )

    assert "<details class='company-workbench-follow-up'>" in rendered
    assert "<summary>What changed</summary>" in rendered
    assert "Review peers" in rendered
    assert rendered.index("<span>Next research task</span>") < rendered.index(
        "<details class='company-workbench-follow-up'>"
    )
    assert rendered.index("data-sr-region='stop-rule'") < rendered.index("<details class='company-workbench-follow-up'>")


def test_company_evidence_map_precedes_online_filing_action():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_company_workbench(")
    end = source.index("\ndef render_personal_research_route(", start)
    workbench = source[start:end]

    assert workbench.index("selected_answer_target = st.empty()") < workbench.index(
        "evidence_status_target = st.empty()"
    )
    assert workbench.index("evidence_status_target = st.empty()") < workbench.index(
        "render_company_sec_annual_check(ticker)"
    )


def test_phone_evidence_table_keeps_real_headers_accessible():
    css = dashboard_visual_system.research_dossier_css()
    rule_start = css.index(".company-workbench-evidence-table thead {", css.index("@media (max-width: 640px)"))
    rule = css[rule_start : css.index("}", rule_start)]

    assert "display: none" not in rule
    assert "position: absolute" in rule


def test_tablet_navigation_has_two_rows_before_routes_overflow():
    css = dashboard_visual_system.research_dossier_css()

    assert "@media (max-width: 900px) and (min-width: 641px)" in css
    tablet = css[css.index("@media (max-width: 900px) and (min-width: 641px)") :]
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in tablet


def test_evidence_heading_overrides_streamlit_injected_span_color():
    css = dashboard_visual_system.research_dossier_css()

    assert ".company-workbench-evidence-heading h2 > span:first-child" in css
    assert "color: inherit !important" in css


def test_two_hundred_percent_phone_zoom_keeps_navigation_targets_wide_enough():
    css = dashboard_visual_system.research_dossier_css()

    assert "@media (max-width: 300px)" in css
    narrow = css[css.index("@media (max-width: 300px)") :]
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in narrow
