from src import dashboard_navigation as nav


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


def test_dashboard_navigation_sidebar_options_keep_advanced_pages_secondary():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.sidebar_path_options("Home", advanced) == nav.PUBLIC_PATH_PAGE_TITLES
    assert nav.sidebar_path_options("Overview", advanced) == nav.PUBLIC_PATH_PAGE_TITLES + [
        nav.DETAILED_PAGE_PATH_TITLE
    ]
    assert nav.sidebar_path_index("Stock Selector", nav.PUBLIC_PATH_PAGE_TITLES, advanced) == 1
    assert nav.sidebar_path_index("Single-Stock Report", nav.PUBLIC_PATH_PAGE_TITLES, advanced) == 2
    assert nav.sidebar_path_index("Data Health", nav.PUBLIC_PATH_PAGE_TITLES, advanced) == 3
    assert (
        nav.sidebar_path_index(
            "Universe Manager",
            nav.PUBLIC_PATH_PAGE_TITLES + [nav.DETAILED_PAGE_PATH_TITLE],
            advanced,
        )
        == 5
    )


def test_public_workflow_steps_answer_one_question_and_next_action_per_page():
    expected = {
        "Home": ("What is this product and where do I start?", "Stock Selector"),
        "Stock Selector": ("Which stock can I review?", "Single-Stock Report"),
        "Single-Stock Report": ("What can I use for this ticker right now?", "Data Health"),
        "Data Health": ("Why is something blocked and how do I fix it?", "Proof History"),
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
        "Read why the lane is blocked, then open Proof History before trusting a change."
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


def test_dashboard_navigation_mode_defaults_public_unless_advanced_context():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.dashboard_mode_from_query("public", "Home", advanced) == nav.PUBLIC_DEMO_MODE
    assert nav.dashboard_mode_from_query("operator", "Home", advanced) == nav.OPERATOR_DEMO_MODE
    assert nav.dashboard_mode_from_query("", "Home", advanced) == nav.PUBLIC_DEMO_MODE
    assert nav.dashboard_mode_from_query("", "Universe Manager", advanced) == nav.OPERATOR_DEMO_MODE
    assert nav.dashboard_mode_label(nav.OPERATOR_DEMO_MODE) == "Operator mode"


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
