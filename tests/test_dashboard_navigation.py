import pytest

from src import dashboard_navigation as nav
import src.dashboard as dashboard


def test_dashboard_navigation_maps_page_query_aliases():
    pages = [
        "Home",
        "Single-Stock Report",
        "Data Health",
        "Universe Manager",
        "Value / Re-rating",
    ]

    assert nav.dashboard_page_from_query("single-stock", pages) == "Single-Stock Report"
    assert nav.dashboard_page_from_query("stock-report", pages) == "Single-Stock Report"
    assert nav.dashboard_page_from_query("data-health", pages) == "Data Health"
    assert nav.dashboard_page_from_query("proof-history", pages) == "Proof History"
    assert nav.dashboard_page_from_query("proof", pages) == "Proof History"
    assert nav.dashboard_page_from_query("universe", pages) == "Universe Manager"
    assert nav.dashboard_page_from_query("value-rerating", pages) == "Value / Re-rating"
    assert nav.dashboard_page_from_query("unknown-page", pages) == "Home"


@pytest.mark.parametrize(
    ("mode", "page", "expected_page", "recognized", "redirected"),
    (
        ("public", "overview", "Home", True, True),
        ("public", "research-desk", "Home", True, True),
        ("research", "home", "Research Desk", True, True),
        ("research", "single-stock-report", "Research Desk", True, True),
        ("research", "universe-manager", "Research Desk", True, True),
        ("public", "not-a-route", "Home", False, True),
        ("research", "not-a-route", "Research Desk", False, True),
        ("operator", "overview", "Overview", True, False),
    ),
)
def test_workspace_route_resolution_fails_closed_by_mode(
    mode, page, expected_page, recognized, redirected
):
    """Catches cross-mode and unknown deep links reaching a non-canonical shell."""

    result = nav.resolve_workspace_route(
        mode,
        page,
        {"mode": mode, "page": page},
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert result.page == expected_page
    assert result.recognized is recognized
    assert result.redirected is redirected


@pytest.mark.parametrize("personal_page", nav.RESEARCH_PATH_PAGE_TITLES)
def test_operator_rejects_personal_only_routes_to_canonical_home(personal_page):
    """Catches a Personal-only deep link being accepted into a blank Operator shell."""

    result = nav.resolve_workspace_route(
        "operator",
        nav.dashboard_page_slug(personal_page),
        {
            "mode": "operator",
            "page": nav.dashboard_page_slug(personal_page),
            "ticker": "AVGO",
            "open": "1",
            "lane": "peers",
        },
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert result.mode == nav.OPERATOR_DEMO_MODE
    assert result.requested_page == personal_page
    assert result.page == "Home"
    assert result.allowed is False
    assert result.redirected is True
    assert result.canonical_query == {"mode": "operator", "page": "home"}


@pytest.mark.parametrize(
    "operator_page",
    tuple(
        dict.fromkeys(
            (*nav.PUBLIC_PATH_PAGE_TITLES, *dashboard.ADVANCED_PAGE_TITLES)
        )
    ),
)
def test_operator_preserves_public_and_actual_operator_routes(operator_page):
    """Catches the narrow Operator allowlist dropping supported public or legacy pages."""

    expected_operator_pages = tuple(
        dict.fromkeys(
            (*nav.PUBLIC_PATH_PAGE_TITLES, *dashboard.ADVANCED_PAGE_TITLES)
        )
    )
    assert len(expected_operator_pages) == 13
    query = {
        "mode": "operator",
        "page": nav.dashboard_page_slug(operator_page),
        "sentinel": "preserve-direct-operator-state",
    }
    result = nav.resolve_workspace_route(
        "operator",
        nav.dashboard_page_slug(operator_page),
        query,
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert result.page == operator_page
    assert result.allowed is True
    assert result.redirected is False
    assert result.canonical_query == query


def test_workspace_route_resolution_marks_an_explicit_invalid_mode_as_research_desk():
    """Catches an invalid mode retaining an otherwise valid operator route."""

    result = nav.resolve_workspace_route(
        "visitor-mode",
        "overview",
        {"mode": "visitor-mode", "page": "overview", "ticker": "NVDA"},
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert result.mode == nav.RESEARCH_MODE
    assert result.page == "Research Desk"
    assert result.allowed is False
    assert result.redirected is True
    assert result.canonical_query == {"mode": "research", "page": "research-desk"}


@pytest.mark.parametrize("operator_alias", ("ops", "internal", "advanced", "full"))
def test_workspace_route_resolution_preserves_retained_operator_mode_aliases(operator_alias):
    """Catches a retained Operator alias falling through as an invalid explicit mode."""

    query = {"mode": operator_alias, "page": "overview", "ticker": "NVDA", "open": "1"}
    result = nav.resolve_workspace_route(
        operator_alias,
        "overview",
        query,
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert result.mode == nav.OPERATOR_DEMO_MODE
    assert result.page == "Overview"
    assert result.allowed is True
    assert result.redirected is False
    assert result.canonical_query == query


@pytest.mark.parametrize(
    ("mode", "page", "query_params", "expected"),
    (
        ("public", "Home", {"mode": "public", "page": "home", "ticker": "NVDA"}, {"mode": "public"}),
        ("public", "Stock Selector", {"ticker": "NVDA", "open": "1"}, {"mode": "public", "page": "stock-selector"}),
        ("public", "Single-Stock Report", {"ticker": "BRK/B", "open": "1", "lane": "proof"}, {"mode": "public", "page": "single-stock-report", "ticker": "BRK/B", "open": "1"}),
        ("public", "Data Health", {"ticker": "BRK/B", "lane": "peers", "drawer": "proof", "queue_details": "1", "batch_details": "1", "proof_details": "1", "metric_details": "1", "cash_preview": "1"}, {"mode": "public", "page": "data-health", "ticker": "BRK/B", "lane": "peers", "drawer": "proof", "queue_details": "1", "batch_details": "1", "proof_details": "1", "metric_details": "1"}),
        ("public", "Proof History", {"ticker": "BRK/B", "open": "1"}, {"mode": "public", "page": "proof-history", "ticker": "BRK/B"}),
        ("research", "Research Desk", {"ticker": "NVDA"}, {"mode": "research", "page": "research-desk"}),
        ("research", "Company Workbench", {"ticker": "BRK/B", "open": "1", "cash_preview": "1", "proof_details": "1"}, {"mode": "research", "page": "company-workbench", "ticker": "BRK/B", "open": "1", "cash_preview": "1"}),
        ("research", "Data Health", {"ticker": "BRK/B", "lane": "peers", "drawer": "proof", "proof_details": "1", "cash_preview": "1"}, {"mode": "research", "page": "data-health", "ticker": "BRK/B", "lane": "peers", "drawer": "proof", "proof_details": "1"}),
        ("research", "Proof History", {"ticker": "BRK/B", "open": "1"}, {"mode": "research", "page": "proof-history", "ticker": "BRK/B"}),
    ),
)
def test_canonical_workspace_query_keeps_only_the_exact_page_allowlist(mode, page, query_params, expected):
    """Catches a redirect carrying a route key into a page that must ignore it."""

    assert nav.canonical_workspace_query(mode, page, query_params) == expected


def test_public_advanced_redirect_clears_route_specific_state():
    result = nav.resolve_workspace_route(
        "public",
        "overview",
        {"mode": "public", "page": "overview", "ticker": "AVGO", "open": "1"},
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert result.canonical_query == {"mode": "public"}


def test_allowed_direct_request_is_not_rewritten_and_shared_evidence_mode_switch_keeps_evidence_state():
    direct_query = {"mode": "research", "page": "data-health", "ticker": "BRK/B", "lane": "peers"}
    direct = nav.resolve_workspace_route(
        "research", "data-health", direct_query, dashboard.USER_PAGE_TITLES, dashboard.ADVANCED_PAGE_TITLES
    )
    switched = nav.resolve_workspace_route(
        "public", "data-health", direct_query, dashboard.USER_PAGE_TITLES, dashboard.ADVANCED_PAGE_TITLES
    )

    assert direct.allowed is True
    assert direct.redirected is False
    assert switched.page == "Data Health"
    assert switched.canonical_query == {"mode": "public", "page": "data-health", "ticker": "BRK/B", "lane": "peers"}


@pytest.mark.parametrize(
    ("mode", "page", "query", "expected"),
    (
        ("public", "home", {"mode": "public", "page": "home", "ticker": "NVDA"}, {"mode": "public"}),
        ("public", "stock-selector", {"mode": "public", "page": "stock-selector", "open": "1"}, {"mode": "public", "page": "stock-selector"}),
        ("public", "single-stock-report", {"mode": "public", "page": "single-stock-report", "ticker": "AVGO", "lane": "peers"}, {"mode": "public", "page": "single-stock-report", "ticker": "AVGO"}),
        ("public", "data-health", {"mode": "public", "page": "data-health", "ticker": "AVGO", "lane": "peers", "cash_preview": "1"}, {"mode": "public", "page": "data-health", "ticker": "AVGO", "lane": "peers"}),
        ("public", "proof-history", {"mode": "public", "page": "proof-history", "ticker": "AVGO", "drawer": "proof"}, {"mode": "public", "page": "proof-history", "ticker": "AVGO"}),
        ("research", "research-desk", {"mode": "research", "page": "research-desk", "ticker": "NVDA", "open": "1", "lane": "peers"}, {"mode": "research", "page": "research-desk"}),
        ("research", "discover", {"mode": "research", "page": "discover", "ticker": "NVDA"}, {"mode": "research", "page": "discover"}),
        ("research", "company-workbench", {"mode": "research", "page": "company-workbench", "ticker": "AVGO", "drawer": "proof"}, {"mode": "research", "page": "company-workbench", "ticker": "AVGO"}),
        ("research", "monitor", {"mode": "research", "page": "monitor", "ticker": "NVDA", "cash_preview": "1"}, {"mode": "research", "page": "monitor"}),
        ("research", "data-health", {"mode": "research", "page": "data-health", "ticker": "AVGO", "lane": "peers", "cash_preview": "1"}, {"mode": "research", "page": "data-health", "ticker": "AVGO", "lane": "peers"}),
        ("research", "proof-history", {"mode": "research", "page": "proof-history", "ticker": "AVGO", "open": "1"}, {"mode": "research", "page": "proof-history", "ticker": "AVGO"}),
    ),
)
def test_allowed_public_and_personal_routes_canonicalize_forbidden_query_state(
    mode, page, query, expected
):
    """Catches route-specific state leaking into an otherwise valid workspace page."""

    result = nav.resolve_workspace_route(
        mode,
        page,
        query,
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert result.allowed is True
    assert result.redirected is True
    assert result.canonical_query == expected


def test_non_evidence_mode_switch_opens_the_target_mode_home_without_route_state():
    """Catches a mode switch carrying a target-mode page and its ticker state across shells."""

    switched = nav.resolve_workspace_route(
        "research",
        "company-workbench",
        {"mode": "public", "page": "company-workbench", "ticker": "BRK/B", "open": "1"},
        dashboard.USER_PAGE_TITLES,
        dashboard.ADVANCED_PAGE_TITLES,
    )

    assert switched.page == "Research Desk"
    assert switched.redirected is True
    assert switched.canonical_query == {"mode": "research", "page": "research-desk"}


def test_dashboard_navigation_public_path_labels_round_trip():
    assert nav.PUBLIC_PATH_PAGE_TITLES == [
        "Home",
        "Stock Selector",
        "Single-Stock Report",
        "Data Health",
        "Proof History",
    ]
    assert nav.public_path_label("Home") == "Home"
    assert nav.public_path_label("Single-Stock Report") == "Single-Stock Report"
    assert nav.public_path_label("Stock Selector") == "Stock Selector"
    assert nav.public_path_label("Data Health") == "Data Health"
    assert nav.page_title_from_public_path("Check data coverage") == "Data Health"
    assert nav.public_path_label("Proof History") == "Proof History"
    assert nav.page_title_from_public_path("Review one stock") == "Single-Stock Report"
    assert nav.page_title_from_public_path("Explore ready names") == "Stock Selector"
    assert nav.page_title_from_public_path("Inspect proof") == "Proof History"
    assert nav.page_title_from_public_path("Improve data coverage") == "Data Health"
    assert nav.page_title_from_public_path("Data Health") == "Data Health"


def test_public_navigation_remains_five_pages_after_profile_truth_integration():
    assert dashboard.PUBLIC_PATH_PAGE_TITLES == [
        "Home",
        "Stock Selector",
        "Single-Stock Report",
        "Data Health",
        "Proof History",
    ]


def test_dashboard_navigation_sidebar_options_keep_advanced_pages_secondary():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.sidebar_path_options("Home", advanced) == nav.PUBLIC_PATH_PAGE_TITLES
    assert nav.sidebar_path_options("Overview", advanced) == nav.PUBLIC_PATH_PAGE_TITLES + ["Overview"]
    assert nav.sidebar_path_index("Stock Selector", nav.PUBLIC_PATH_PAGE_TITLES, advanced) == 1
    assert nav.sidebar_path_index("Single-Stock Report", nav.PUBLIC_PATH_PAGE_TITLES, advanced) == 2
    assert nav.sidebar_path_index("Data Health", nav.PUBLIC_PATH_PAGE_TITLES, advanced) == 3
    assert (
        nav.sidebar_path_index(
            "Universe Manager",
            nav.PUBLIC_PATH_PAGE_TITLES + ["Universe Manager"],
            advanced,
        )
        == 5
    )


def test_dashboard_navigation_shows_the_current_advanced_page_name_in_the_route_rail():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.sidebar_path_options("Monthly Picks", advanced) == nav.PUBLIC_PATH_PAGE_TITLES + ["Monthly Picks"]
    assert nav.sidebar_path_index("Monthly Picks", nav.sidebar_path_options("Monthly Picks", advanced), advanced) == 5


def test_public_workflow_steps_answer_one_question_and_next_action_per_page():
    expected = {
        "Home": ("What is this product and where do I start?", "Stock Selector"),
        "Stock Selector": ("Which stock can I review?", "Single-Stock Report"),
        "Single-Stock Report": ("What can I use for this ticker right now?", "Data Health"),
        "Data Health": ("What can I use and what stays unavailable?", "Proof History"),
        "Proof History": ("What evidence changed a readiness state?", "Home"),
    }

    for page, (question, next_page) in expected.items():
        step = nav.public_workflow_step(page)
        assert step["page"] == page
        assert step["question"] == question
        assert step["short_answer"]
        assert step["next_page"] == next_page
        assert step["next_action"]
        assert step["stop_rule"]

    data_health_step = nav.public_workflow_step("Data Health")
    assert data_health_step["next_action"] == (
        "Use the lane answer to understand what is available, then open Proof History only when evidence needs review."
    )
    proof_step = nav.public_workflow_step("Proof History")
    assert proof_step["short_answer"] == "Review evidence only; proof records do not refresh or unlock data."
    assert proof_step["next_action"] == (
        "Check the latest proof record, then return to Stock Selector or the ticker report."
    )

    assert nav.public_workflow_step("Universe Manager") == nav.public_workflow_step("Home")


def test_public_workflow_position_labels_page_progress():
    assert nav.public_workflow_position("Home") == "Step 1 of 5"
    assert nav.public_workflow_position("Stock Selector") == "Step 2 of 5"
    assert nav.public_workflow_position("Single-Stock Report") == "Step 3 of 5"
    assert nav.public_workflow_position("Data Health") == "Step 4 of 5"
    assert nav.public_workflow_position("Proof History") == "Step 5 of 5"
    assert nav.public_workflow_position("Universe Manager") == "Step 1 of 5"


def test_public_workflow_stop_rules_keep_research_only_boundary_visible():
    for page in nav.PUBLIC_PATH_PAGE_TITLES:
        stop_rule = nav.public_workflow_step(page)["stop_rule"].lower()
        assert len(stop_rule) <= 95
        assert "research-only" in stop_rule
        assert "not advice" in stop_rule
        assert "trade instruction" in stop_rule

    data_health_stop = nav.public_workflow_step("Data Health")["stop_rule"].lower()
    assert "changing local data" in data_health_stop
    assert "applying" not in data_health_stop
    assert "trusting rows" not in data_health_stop


def test_dashboard_navigation_mode_defaults_research_unless_explicit_or_advanced_context():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.dashboard_mode_from_query("public", "Home", advanced) == nav.PUBLIC_DEMO_MODE
    assert nav.dashboard_mode_from_query("operator", "Home", advanced) == nav.OPERATOR_DEMO_MODE
    assert nav.dashboard_mode_from_query("", "Home", advanced) == nav.RESEARCH_MODE
    assert nav.dashboard_mode_from_query("", "Universe Manager", advanced) == nav.OPERATOR_DEMO_MODE
    assert nav.dashboard_mode_label(nav.OPERATOR_DEMO_MODE) == "Operator mode"


def test_legacy_research_utilities_have_an_exact_operator_only_contract():
    assert nav.LEGACY_RESEARCH_UTILITY_PAGES == (
        "Monthly Picks",
        "Momentum Leaders",
        "Portfolio Review",
        "Value / Re-rating",
        "Final Watchlist",
    )

    for page in nav.LEGACY_RESEARCH_UTILITY_PAGES:
        assert nav.legacy_research_utility_label(page) == f"Legacy utility · {page}"
        assert nav.workspace_page_for_mode(page, nav.PUBLIC_DEMO_MODE) == "Home"
        assert nav.workspace_page_for_mode(page, nav.RESEARCH_MODE) == "Research Desk"
        assert nav.workspace_page_for_mode(page, nav.OPERATOR_DEMO_MODE) == page

    assert nav.legacy_research_utility_label("Data Health") == "Data Health"
    assert nav.workspace_page_for_mode("Data Health", nav.RESEARCH_MODE) == "Data Health"


def test_legacy_aliases_remain_available_for_operator_compatibility():
    pages = nav.PUBLIC_PATH_PAGE_TITLES + list(nav.LEGACY_RESEARCH_UTILITY_PAGES)

    assert nav.dashboard_page_from_query("monthly-picks", pages) == "Monthly Picks"
    assert nav.dashboard_page_from_query("portfolio-review", pages) == "Portfolio Review"
    assert nav.dashboard_page_from_query("final-watchlist", pages) == "Final Watchlist"


def test_dashboard_navigation_supports_personal_research_mode_without_changing_public_paths():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.RESEARCH_MODE == "research"
    assert nav.RESEARCH_PATH_PAGE_TITLES == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
    ]
    assert nav.dashboard_mode_from_query("", "Home", advanced) == nav.RESEARCH_MODE
    assert nav.dashboard_mode_from_query("research", "Research Desk", advanced) == nav.RESEARCH_MODE
    assert nav.dashboard_mode_from_query("public", "Home", advanced) == nav.PUBLIC_DEMO_MODE
    assert nav.dashboard_mode_from_query("operator", "Home", advanced) == nav.OPERATOR_DEMO_MODE
    assert nav.dashboard_mode_label(nav.RESEARCH_MODE) == "Personal research mode"
    assert nav.PUBLIC_PATH_PAGE_TITLES == [
        "Home",
        "Stock Selector",
        "Single-Stock Report",
        "Data Health",
        "Proof History",
    ]


def test_research_navigation_keeps_evidence_pages_secondary_and_supports_deep_links():
    pages = nav.PUBLIC_PATH_PAGE_TITLES + nav.RESEARCH_PATH_PAGE_TITLES + ["Data Health", "Proof History"]

    assert nav.dashboard_page_from_query("research-desk", pages) == "Research Desk"
    assert nav.dashboard_page_from_query("discover", pages) == "Discover"
    assert nav.dashboard_page_from_query("company-workbench", pages) == "Company Workbench"
    assert nav.dashboard_page_from_query("monitor", pages) == "Monitor"
    assert nav.research_path_options("Data Health") == nav.RESEARCH_PATH_PAGE_TITLES + ["Data Health"]
    assert nav.research_path_options("Proof History") == nav.RESEARCH_PATH_PAGE_TITLES + ["Proof History"]
    assert nav.research_path_options("Research Desk") == nav.RESEARCH_PATH_PAGE_TITLES
    assert nav.research_path_label("Research Desk") == "Research Desk"
    assert nav.research_path_label("Discover") == "Discover"
    assert nav.research_path_label("Company Workbench") == "Company Workbench"
    assert nav.research_path_label("Monitor") == "Monitor"
    assert nav.route_rail_query_update(
        selected_page="Company Workbench",
        initial_page="Research Desk",
        mode=nav.RESEARCH_MODE,
        allowed_pages=nav.RESEARCH_PATH_PAGE_TITLES,
    ) == {"mode": "research", "page": "company-workbench"}


def test_dashboard_navigation_query_wins_only_until_route_rail_changes():
    assert (
        nav.selected_page_from_route_rail(
            initial_page="Home",
            default_path="Home",
            path_selection="Home",
            has_explicit_page_query=True,
        )
        == "Home"
    )
    assert (
        nav.selected_page_from_route_rail(
            initial_page="Home",
            default_path="Home",
            path_selection="Stock Selector",
            has_explicit_page_query=True,
        )
        == "Stock Selector"
    )
    assert (
        nav.selected_page_from_route_rail(
            initial_page="Universe Manager",
            default_path="Home",
            path_selection="Home",
            has_explicit_page_query=True,
        )
        == "Universe Manager"
    )


def test_dashboard_navigation_route_rail_query_update_is_canonical_and_clean():
    assert nav.route_rail_query_update(
        selected_page="Stock Selector",
        initial_page="Home",
        mode=nav.PUBLIC_DEMO_MODE,
    ) == {"mode": "public", "page": "stock-selector"}
    assert nav.route_rail_query_update(
        selected_page="Home",
        initial_page="Home",
        mode=nav.PUBLIC_DEMO_MODE,
    ) == {}
    assert nav.route_rail_query_update(
        selected_page=nav.DETAILED_PAGE_PATH_TITLE,
        initial_page="Universe Manager",
        mode=nav.OPERATOR_DEMO_MODE,
    ) == {}
    assert (
        nav.selected_page_from_route_rail(
            initial_page="Universe Manager",
            default_path="Home",
            path_selection="Stock Selector",
            has_explicit_page_query=True,
        )
        == "Stock Selector"
    )
    assert (
        nav.selected_page_from_route_rail(
            initial_page="Universe Manager",
            default_path="Home",
            path_selection=nav.DETAILED_PAGE_PATH_TITLE,
            has_explicit_page_query=False,
        )
        == "Universe Manager"
    )
