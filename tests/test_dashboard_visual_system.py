"""Contracts for the dashboard presentation seam and visual foundation."""

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

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


def test_presentation_seam_keeps_unmodified_public_helper_dom_snapshots_byte_identical():
    snapshots = _dom_snapshots()

    assert dashboard.section_header_html(
        "<Monthly Picks>", "Use <local> research coverage."
    ) == snapshots["section_header_html"]


def test_presentation_seam_escapes_text_and_quoted_attributes():
    assert visual.escape_text('<Research & "workspace">') == '&lt;Research &amp; "workspace"&gt;'
    assert visual.escape_attribute("AAPL's \"review\" & <local>") == (
        "AAPL&#x27;s &quot;review&quot; &amp; &lt;local&gt;"
    )


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_visual_tokens_match_the_approved_calm_institutional_palette():
    assert visual.visual_tokens() == {
        "--sr-canvas": "#F6F7F4",
        "--sr-surface": "#FFFFFF",
        "--sr-surface-muted": "#F1F4F1",
        "--sr-ink": "#0F172A",
        "--sr-text": "#243244",
        "--sr-muted": "#475569",
        "--sr-border": "#D9E1DC",
        "--sr-nav": "#0B1B2B",
        "--sr-nav-text": "#F8FAFC",
        "--sr-nav-muted": "#CBD5E1",
        "--sr-forest": "#155E4B",
        "--sr-teal": "#0F766E",
        "--sr-amber": "#854D0E",
        "--sr-red": "#B42318",
        "--sr-blue": "#315D8A",
        "--sr-focus": "#0B6BFF",
    }


@pytest.mark.parametrize("surface", ("--sr-surface", "--sr-surface-muted", "--sr-canvas"))
@pytest.mark.parametrize(
    "foreground",
    ("--sr-ink", "--sr-text", "--sr-muted", "--sr-forest", "--sr-teal", "--sr-amber", "--sr-red", "--sr-blue"),
)
def test_permitted_light_surface_text_pairs_are_aa_readable(surface, foreground):
    tokens = visual.visual_tokens()

    assert _contrast(tokens[foreground], tokens[surface]) >= 4.5


def test_navigation_and_focus_pairs_meet_the_approved_contrast_floor():
    tokens = visual.visual_tokens()

    assert _contrast(tokens["--sr-nav-text"], tokens["--sr-nav"]) >= 4.5
    assert _contrast(tokens["--sr-nav-muted"], tokens["--sr-nav"]) >= 4.5
    for surface in ("--sr-surface", "--sr-surface-muted", "--sr-canvas", "--sr-nav"):
        assert _contrast(tokens["--sr-focus"], tokens[surface]) >= 3


@pytest.mark.parametrize("label", ("Keep", "Strong Rotation", "Risk Reduce", "peer_discount"))
def test_analytic_labels_never_inherit_evidence_sentiment(label):
    state = visual.visual_state("analytic", label)

    assert state.semantic == "neutral"
    assert state.label == label


@pytest.mark.parametrize(
    ("role", "state", "semantic"),
    (
        ("evidence", "supported", "supported"),
        ("evidence", "partial", "partial"),
        ("evidence", "blocked", "blocked"),
        ("evidence", "stale", "stale"),
        ("evidence", "excluded", "excluded"),
        ("evidence", "withheld", "withheld"),
        ("freshness", "current", "supported"),
        ("freshness", "mixed", "partial"),
        ("freshness", "missing", "blocked"),
        ("workflow", "current", "workflow"),
        ("trace", "source_backed", "trace"),
        ("legacy", "supported", "neutral"),
        ("unknown-role", "blocked", "neutral"),
        ("", "", "neutral"),
    ),
)
def test_visual_state_mapping_is_role_aware_and_fails_closed(role, state, semantic):
    result = visual.visual_state(role, state)

    assert result.semantic == semantic
    assert result.label


def test_dashboard_visual_css_uses_local_fonts_tokens_and_responsive_complete_controls():
    css = visual.dashboard_visual_system_css()

    assert "--sr-nav: #0B1B2B" in css
    assert 'Inter, "SF Pro Text", "Segoe UI", system-ui, sans-serif' in css
    assert "url(" not in css.lower()
    assert "min-height: 44px" in css
    mobile = css[css.index("@media (max-width: 640px)") :]
    assert "overflow-x: auto" not in mobile
    assert "grid-template-columns: repeat(auto-fit, minmax(5rem, 1fr))" in mobile
    assert "overflow: visible" in mobile
    assert "text-overflow: ellipsis" not in css
    assert "line-clamp" not in css
    assert "@media (forced-colors: active)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".research-discover-browser-jump" in css
    assert "@media (max-width: 360px)" in css


def test_company_workbench_document_css_scopes_horizontal_navigation_and_evidence_aside():
    """Catches a Workbench document layout drifting back into the fixed rail shell."""

    css = visual.dashboard_visual_system_css()
    scope = ".stApp:has(.st-key-company-workbench-document)"
    desktop_start = css.index(f"{scope} .research-workflow-navigation {{")
    desktop_end = css.index(".public-app-shell, .research-workspace-header", desktop_start)
    desktop = css[desktop_start:desktop_end]
    tablet_start = css.index("@media (max-width: 1099px) {")
    phone_start = css.index("@media (max-width: 640px) {")
    tablet = css[tablet_start:phone_start]
    phone = css[phone_start:]

    assert "position: static !important;" in desktop
    assert "grid-template-columns: minmax(12rem, 1.1fr) minmax(0, 2fr) minmax(8rem, .7fr);" in desktop
    assert f"{scope} .research-workflow-routes {{" in desktop
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in desktop
    assert f"{scope} .st-key-company-workbench-document [data-testid=\"stColumn\"]:last-child {{" in desktop
    assert "position: sticky;" in desktop
    assert "top: 1rem;" in desktop
    assert f"{scope} .research-workflow-navigation {{" in tablet
    assert "grid-template-columns: 1fr;" in tablet
    assert f"{scope} .st-key-company-workbench-document [data-testid=\"stHorizontalBlock\"] {{" in tablet
    assert "flex-direction: column !important;" in tablet
    assert f"{scope} .research-workflow-routes {{" in phone
    assert "grid-template-columns: repeat(auto-fit, minmax(5rem, 1fr));" in phone


def test_company_workbench_tablet_layout_resets_streamlit_flex_columns_to_one_stack():
    """Catches a grid-only reset that cannot affect Streamlit's horizontal flex block."""

    css = visual.dashboard_visual_system_css()
    scope = ".stApp:has(.st-key-company-workbench-document)"
    tablet_start = css.index("@media (max-width: 1099px) {")
    tablet_end = css.index(".public-app-shell, .research-workspace-header", tablet_start)
    tablet = css[tablet_start:tablet_end]

    assert f"{scope} .st-key-company-workbench-document [data-testid=\"stHorizontalBlock\"] {{" in tablet
    assert "display: flex !important;" in tablet
    assert "flex-direction: column !important;" in tablet
    assert f"{scope} .st-key-company-workbench-document [data-testid=\"stColumn\"] {{" in tablet
    assert "flex: 1 1 100% !important;" in tablet
    assert "width: 100% !important;" in tablet
    assert "min-width: 0 !important;" in tablet


def test_company_workbench_primary_lanes_use_a_real_grid_before_mobile_reset():
    """Catches primary-lane column declarations on a non-grid block container."""

    css = visual.dashboard_visual_system_css()
    scope = ".stApp:has(.st-key-company-workbench-document)"
    desktop_start = css.index(f"{scope} .company-workbench-primary-grid {{")
    desktop_end = css.index("@media (max-width: 1099px) {", desktop_start)
    desktop = css[desktop_start:desktop_end]
    phone = css[css.index("@media (max-width: 640px) {") :]

    assert "display: grid;" in desktop
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in desktop
    assert f"{scope} .company-workbench-primary-grid {{" in phone
    assert "grid-template-columns: 1fr;" in phone


def test_company_workbench_primary_title_is_one_editorial_display_heading():
    """Catches the semantic brief title shrinking into legacy label styling."""

    css = visual.dashboard_visual_system_css()
    scope = ".stApp:has(.st-key-company-workbench-document)"
    selector = f"{scope} .company-workbench-primary-heading h2"
    start = css.index(f"{selector} {{")
    title_rule = css[start : css.index("\n}", start) + 2]

    assert 'font-family: Georgia, "Times New Roman", serif;' in title_rule
    assert "font-size: clamp(1.5rem, 3.2vw, 2.75rem);" in title_rule
    assert "font-weight: 600;" in title_rule
    assert "letter-spacing: -.03em;" in title_rule
    assert "line-height: 1.05;" in title_rule
    assert "margin: 0;" in title_rule
    assert "text-transform: none;" in title_rule

    streamlit_text_selector = f"{selector} > span:first-child"
    assert f"{streamlit_text_selector} {{" in css
    streamlit_text_start = css.index(f"{streamlit_text_selector} {{")
    streamlit_text_rule = css[
        streamlit_text_start : css.index("\n}", streamlit_text_start) + 2
    ]
    assert "color: inherit !important;" in streamlit_text_rule
    assert "font: inherit;" in streamlit_text_rule
    assert "letter-spacing: inherit;" in streamlit_text_rule
    assert "text-transform: none;" in streamlit_text_rule


def test_company_workbench_evidence_rail_uses_explicit_readable_dark_surface_tokens():
    """Catches the dark Workbench rail inheriting unreadable application text colors."""

    css = visual.dashboard_visual_system_css()
    scope = ".stApp:has(.st-key-company-workbench-document)"
    tokens = visual.visual_tokens()

    def scoped_rule(selector: str) -> str:
        start = css.index(f"{scope} {selector} {{")
        return css[start : css.index("\n}", start) + 2]

    assert _contrast(tokens["--sr-nav-text"], tokens["--sr-nav"]) >= 4.5
    assert _contrast(tokens["--sr-nav-muted"], tokens["--sr-nav"]) >= 4.5
    rail = scoped_rule(".company-workbench-evidence-status")
    heading = scoped_rule(".company-workbench-evidence-heading h2")
    heading_content = scoped_rule(".company-workbench-evidence-heading h2 *")
    meta = scoped_rule(".company-workbench-evidence-heading > span")
    lane = scoped_rule(".company-workbench-evidence-lane")
    label = scoped_rule(".company-workbench-evidence-lane span")
    state = scoped_rule(".company-workbench-evidence-lane strong")

    assert "display: grid;" in rail
    assert "gap: 12px;" in rail
    assert "color: var(--sr-nav-text);" in rail
    assert "color: var(--sr-nav-text) !important;" in heading
    assert "color: var(--sr-nav-text) !important;" in heading_content
    assert "color: var(--sr-nav-muted) !important;" in meta
    assert "display: grid;" in lane
    assert "grid-template-columns: minmax(0, 1fr) auto;" in lane
    assert "border-bottom: 1px solid rgba(248, 250, 252, .24);" in lane
    assert "color: var(--sr-nav-muted) !important;" in label
    assert "color: var(--sr-nav-text) !important;" in state
    forced = css[css.index("@media (forced-colors: active) {") :]
    assert f"{scope} .company-workbench-evidence-status" in forced
    assert f"{scope} .company-workbench-evidence-heading h2 *" in forced
    assert "color: CanvasText !important;" in forced


def test_company_workbench_primary_module_gate_uses_explicit_readable_button_tokens():
    """Catches Streamlit's nested button label inheriting low-contrast body copy."""

    css = visual.dashboard_visual_system_css()
    scope = ".stApp:has(.st-key-company-workbench-document)"
    tokens = visual.visual_tokens()
    button_selector = f'{scope} [data-testid="stBaseButton-primary"]'
    label_selector = f'{button_selector} *'

    assert _contrast(tokens["--sr-nav-text"], tokens["--sr-forest"]) >= 4.5
    button_start = css.index(f"{button_selector} {{")
    button_rule = css[button_start : css.index("\n}", button_start) + 2]
    label_start = css.index(f"{label_selector} {{")
    label_rule = css[label_start : css.index("\n}", label_start) + 2]

    assert "min-height: 44px;" in button_rule
    assert "background: var(--sr-forest) !important;" in button_rule
    assert "border-color: var(--sr-forest) !important;" in button_rule
    assert "color: var(--sr-nav-text) !important;" in label_rule
    forced = css[css.index("@media (forced-colors: active) {") :]
    assert button_selector in forced
    assert label_selector in forced
    assert "background: ButtonFace !important;" in forced
    assert "color: ButtonText !important;" in forced


def test_company_workbench_phone_lanes_compact_only_internal_spacing_before_the_action():
    """Catches the mobile brief pushing its required Data Health action below 390x844."""

    css = visual.dashboard_visual_system_css()
    scope = ".stApp:has(.st-key-company-workbench-document)"
    phone = css[css.index("@media (max-width: 640px) {") :]

    assert (
        f"{scope} .company-workbench-primary-grid {{\n"
        "    grid-template-columns: 1fr;\n"
        "    gap: 0;\n"
        "  }"
    ) in phone
    assert (
        f"{scope} .company-workbench-primary-answer {{\n"
        "    padding-top: 0;\n"
        "  }"
    ) in phone
    assert (
        f"{scope} .company-workbench-primary-answer .public-primary-action {{\n"
        "    margin-top: 0 !important;\n"
        "    min-height: 44px;\n"
        "  }"
    ) in phone
    assert (
        f"{scope} .company-workbench-primary-heading {{\n"
        "    margin-bottom: 0 !important;\n"
        "  }"
    ) in phone
    assert (
        f"{scope} .company-workbench-primary-answer p,\n"
        f"  {scope} .company-workbench-primary-answer strong,\n"
        f"  {scope} .company-workbench-primary-answer small {{\n"
        "    margin-top: 0 !important;\n"
        "  }"
    ) in phone
    assert (
        f"{scope} .company-workbench-primary-answer p {{\n"
        "    line-height: 1.15;\n"
        "  }"
    ) in phone


def test_research_desk_evidence_layout_reserves_reason_width_and_resets_on_phone():
    css = visual.dashboard_visual_system_css()
    desktop = css[
        css.index(".research-desk-brief .sr-evidence-row {") :
        css.index(".sr-status-chip {")
    ]
    mobile = css[css.index("@media (max-width: 640px)") :]

    assert "grid-template-columns: minmax(12rem, .75fr) minmax(0, 2fr)" in desktop
    assert ".research-desk-brief .sr-evidence-count" in desktop
    assert "overflow-wrap: anywhere" in desktop
    assert ".research-desk-brief .sr-evidence-row p" in desktop
    assert "grid-column: 2" in desktop
    assert ".research-desk-brief .sr-evidence-row" in mobile
    assert "grid-template-columns: 1fr" in mobile
    assert "grid-column: 1" in mobile
    assert "grid-row: auto" in mobile


def test_typed_components_escape_every_text_and_attribute_boundary():
    action = visual.SafeRouteAction(
        label="Open <Desk>",
        href="?mode=research&page=discover",
        aria_label='Open "Desk" & continue',
    )
    rendered = visual.workspace_shell_html(
        mode='research\" onmouseover="alert(1)',
        navigation=visual.next_action_html(action),
        content=(
            visual.context_bar_html((("<Profile>", 'Demo & "local"'),)),
            visual.answer_panel_html(
                question="<Question>",
                answer="Use & verify",
                reason='Reason "quoted"',
                action=action,
                stop_rule="Stop <now>",
            ),
        ),
    ).value

    assert "<Profile>" not in rendered
    assert "&lt;Profile&gt;" in rendered
    assert "Demo &amp; \"local\"" in rendered
    assert "Open &lt;Desk&gt;" in rendered
    assert "Open &quot;Desk&quot; &amp; continue" in rendered
    assert "research&quot; onmouseover=&quot;alert(1)" in rendered


def test_workspace_shell_rejects_raw_or_foreign_nested_html():
    with pytest.raises(TypeError):
        visual.workspace_shell_html(mode="research", navigation=None, content=("<b>raw</b>",))
    with pytest.raises(TypeError):
        visual.workspace_shell_html(mode="research", navigation="<nav>raw</nav>", content=())


def test_html_fragment_creation_is_module_controlled_and_forged_instances_are_rejected():
    with pytest.raises(TypeError, match="module presentation helpers"):
        visual.HtmlFragment("<script>alert('forged')</script>")

    forged = object.__new__(visual.HtmlFragment)
    object.__setattr__(forged, "value", "<script>alert('forged')</script>")
    with pytest.raises(TypeError, match="trusted HtmlFragment"):
        visual.workspace_shell_html(mode="research", navigation=forged, content=())

    class ForeignFragment(visual.HtmlFragment):
        pass

    subclass_forgery = object.__new__(ForeignFragment)
    object.__setattr__(subclass_forgery, "value", "<nav>forged</nav>")
    with pytest.raises(TypeError, match="trusted HtmlFragment"):
        visual.workspace_shell_html(
            mode="research",
            navigation=None,
            content=(subclass_forgery,),
        )


@pytest.mark.parametrize("role", ("analytic", "legacy", "unknown-role"))
@pytest.mark.parametrize("state", ("excluded", "withheld"))
def test_excluded_and_withheld_semantics_remain_evidence_only(role, state):
    assert visual.visual_state(role, state).semantic == "neutral"


@pytest.mark.parametrize(
    "href",
    (
        "",
        "https://example.com/?mode=research&page=discover",
        "//example.com/?mode=research&page=discover",
        "/?mode=research&page=discover",
        "?mode=research&page=discover#answer",
        "?mode=research&mode=public&page=discover",
        "?mode=research&page=discover&command=make+status-check",
        "?mode=research&page=discover&apply=1",
    ),
)
def test_safe_route_action_rejects_noncanonical_or_state_changing_links(href):
    with pytest.raises(ValueError):
        visual.SafeRouteAction(label="Open", href=href)


def test_safe_route_action_renders_canonical_query_only_links():
    rendered = visual.next_action_html(
        visual.SafeRouteAction(
            label="Open Workbench",
            href="?mode=research&page=company-workbench&ticker=BRK%2FB&open=1",
        )
    ).value

    assert "href='?mode=research&amp;page=company-workbench&amp;ticker=BRK%2FB&amp;open=1'" in rendered
    assert "data-sr-region='primary-action'" in rendered


def test_shared_components_emit_unique_regions_and_malformed_evidence_stays_visible_neutral():
    action = visual.SafeRouteAction(label="Open Discover", href="?mode=research&page=discover")
    shell = visual.workspace_shell_html(
        mode="research",
        navigation=None,
        content=(
            visual.context_bar_html((("Mode", "Personal research"),)),
            visual.answer_panel_html(
                question="What needs attention?",
                answer="Review one saved evidence change.",
                reason="The saved queue has a review item.",
                action=action,
                stop_rule="Research-only. Stop when evidence is unavailable.",
            ),
            visual.evidence_rows_html(
                (
                    visual.EvidenceRow(
                        lane="Price setup",
                        role="evidence",
                        state="not-a-real-state",
                        count_or_cutoff="Unavailable",
                        reason="Malformed source state remains visible.",
                    ),
                )
            ),
        ),
    ).value

    for region in ("context", "primary-answer", "primary-action", "stop-rule", "supporting-evidence"):
        assert shell.count(f"data-sr-region='{region}'") == 1
    assert "not-a-real-state" in shell
    assert "sr-status-neutral" in shell


def test_evidence_timeline_preserves_authoritative_order_and_undated_rows():
    rows = (
        visual.TimelineRecord("p2", "2026-08-01", "Latest", "Supported"),
        visual.TimelineRecord("p1", None, "Undated", "Still visible"),
    )

    rendered = visual.evidence_timeline_html(
        rows,
        empty_title="No proof",
        empty_body="No durable proof yet.",
    ).value

    assert rendered.index("Latest") < rendered.index("Undated")
    assert "Timestamp unavailable" in rendered
    assert rendered.count("data-timeline-record-id=") == 2
    with pytest.raises(FrozenInstanceError):
        rows[0].label = "Changed"


def test_evidence_timeline_escapes_rows_and_renders_one_truthful_empty_state():
    action = visual.SafeRouteAction(
        label="Open <proof>",
        href="?mode=research&page=proof-history&ticker=AVGO",
    )
    rendered = visual.evidence_timeline_html(
        (
            visual.TimelineRecord(
                "proof<'1",
                None,
                "Changed <source>",
                "Evidence & review",
                action,
            ),
        ),
        empty_title="No proof",
        empty_body="No durable proof yet.",
    ).value

    assert "proof&lt;&#x27;1" in rendered
    assert "Changed &lt;source&gt;" in rendered
    assert "Evidence &amp; review" in rendered
    assert "Open &lt;proof&gt;" in rendered
    assert rendered.count("data-sr-region='supporting-evidence'") == 1

    empty = visual.evidence_timeline_html(
        (),
        empty_title="No <proof>",
        empty_body="No durable & reviewed proof yet.",
    ).value
    assert empty.count("No &lt;proof&gt;") == 1
    assert "No durable &amp; reviewed proof yet." in empty
    assert "Timestamp unavailable" not in empty


def test_detail_disclosure_accepts_only_sealed_fragments_and_preserves_body_order():
    first = visual.detail_item_html(label="First <lane>", body="Evidence & detail")
    second = visual.status_chip_html(role="evidence", state="withheld", label="Second")

    rendered = visual.detail_disclosure_html(
        "Review <detail>",
        (first, second),
        open_by_default=True,
    ).value

    assert (
        "<details class='sr-detail-disclosure' data-sr-region='advanced-detail' open>"
        in rendered
    )
    assert "Review &lt;detail&gt;" in rendered
    assert "First &lt;lane&gt;" in rendered
    assert "Evidence &amp; detail" in rendered
    assert rendered.index("First") < rendered.index("Second")
    with pytest.raises(TypeError, match="trusted HtmlFragment"):
        visual.detail_disclosure_html("Unsafe", ("<script>raw</script>",))


def test_disabled_workbench_nav_positions_its_hidden_suffix_inside_the_nav_scroller():
    css = visual.dashboard_visual_system_css()
    rule = css[css.index("\n.research-workflow-disabled {") :]
    rule = rule[: rule.index("}")]

    assert "position: relative;" in rule


def test_next_step_prompt_labels_native_control_without_impersonating_the_action():
    rendered = visual.next_step_prompt_html(
        title="Search saved companies",
        body="Use the adjacent native search control.",
    ).value

    assert "Search saved companies" in rendered
    assert "data-sr-region='primary-action'" not in rendered
