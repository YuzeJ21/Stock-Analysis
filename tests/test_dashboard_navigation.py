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
        "Single-Stock Report",
        "Stock Selector",
        "Data Health",
        "Proof History",
    ]
    assert nav.public_path_label("Home") == "Start at Home"
    assert nav.public_path_label("Single-Stock Report") == "Review one stock"
    assert nav.public_path_label("Stock Selector") == "Explore ready names"
    assert nav.public_path_label("Data Health") == "Check data coverage"
    assert nav.page_title_from_public_path("Check data coverage") == "Data Health"
    assert nav.public_path_label("Proof History") == "Inspect proof"
    assert nav.page_title_from_public_path("Review one stock") == "Single-Stock Report"
    assert nav.page_title_from_public_path("Explore ready names") == "Stock Selector"
    assert nav.page_title_from_public_path("Inspect proof") == "Proof History"
    assert nav.page_title_from_public_path("Data Health") == "Data Health"


def test_dashboard_navigation_sidebar_options_keep_advanced_pages_secondary():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.sidebar_path_options("Home", advanced) == nav.PUBLIC_PATH_PAGE_TITLES
    assert nav.sidebar_path_options("Overview", advanced) == nav.PUBLIC_PATH_PAGE_TITLES + [
        nav.DETAILED_PAGE_PATH_TITLE
    ]
    assert nav.sidebar_path_index("Data Health", nav.PUBLIC_PATH_PAGE_TITLES, advanced) == 3
    assert (
        nav.sidebar_path_index(
            "Universe Manager",
            nav.PUBLIC_PATH_PAGE_TITLES + [nav.DETAILED_PAGE_PATH_TITLE],
            advanced,
        )
        == 5
    )


def test_dashboard_navigation_mode_defaults_public_unless_advanced_context():
    advanced = ["Overview", "Monthly Picks", "Universe Manager"]

    assert nav.dashboard_mode_from_query("public", "Home", advanced) == nav.PUBLIC_DEMO_MODE
    assert nav.dashboard_mode_from_query("operator", "Home", advanced) == nav.OPERATOR_DEMO_MODE
    assert nav.dashboard_mode_from_query("", "Home", advanced) == nav.PUBLIC_DEMO_MODE
    assert nav.dashboard_mode_from_query("", "Universe Manager", advanced) == nav.OPERATOR_DEMO_MODE
    assert nav.dashboard_mode_label(nav.OPERATOR_DEMO_MODE) == "Operator mode"
