from __future__ import annotations

import re
from urllib.parse import unquote


DETAILED_PAGE_PATH_TITLE = "More research views"
PROOF_HISTORY_PATH_TITLE = "Proof History"
STOCK_SELECTOR_PATH_TITLE = "Stock Selector"
PUBLIC_PATH_PAGE_TITLES = [
    "Home",
    STOCK_SELECTOR_PATH_TITLE,
    "Single-Stock Report",
    "Data Health",
    PROOF_HISTORY_PATH_TITLE,
]
PUBLIC_PATH_LABELS = {
    "Home": "Home",
    "Single-Stock Report": "Single-Stock Report",
    STOCK_SELECTOR_PATH_TITLE: STOCK_SELECTOR_PATH_TITLE,
    "Data Health": "Data Health",
    PROOF_HISTORY_PATH_TITLE: PROOF_HISTORY_PATH_TITLE,
    DETAILED_PAGE_PATH_TITLE: "More research views",
}
LEGACY_PUBLIC_PATH_LABELS = {
    "Start at Home": "Home",
    "Review one stock": "Single-Stock Report",
    "Explore ready names": STOCK_SELECTOR_PATH_TITLE,
    "Check data coverage": "Data Health",
    "Improve data coverage": "Data Health",
    "Inspect proof": PROOF_HISTORY_PATH_TITLE,
}
PUBLIC_DEMO_MODE = "public"
OPERATOR_DEMO_MODE = "operator"
DEMO_MODE_LABELS = {
    PUBLIC_DEMO_MODE: "Public visitor mode",
    OPERATOR_DEMO_MODE: "Operator mode",
}
PUBLIC_WORKFLOW_STEPS = {
    "Home": {
        "page": "Home",
        "question": "What is this product and where do I start?",
        "short_answer": "A readiness-first research workflow; start by choosing a reviewable ticker.",
        "next_page": STOCK_SELECTOR_PATH_TITLE,
        "next_action": "Start by exploring ready names.",
        "stop_rule": "Research-only: not advice; stop before treating any output as a trade instruction.",
    },
    STOCK_SELECTOR_PATH_TITLE: {
        "page": STOCK_SELECTOR_PATH_TITLE,
        "question": "Which stock can I review?",
        "short_answer": "Use readiness filters to pick one ticker for a single-stock review.",
        "next_page": "Single-Stock Report",
        "next_action": "Pick one ticker, then open its single-stock report.",
        "stop_rule": "Research-only: not advice; stop if the selected ticker has no readiness-backed path or trade instruction.",
    },
    "Single-Stock Report": {
        "page": "Single-Stock Report",
        "question": "What can I use for this ticker right now?",
        "short_answer": "Read supported sections first; blocked inputs stay locked.",
        "next_page": "Data Health",
        "next_action": "Use supported sections first; open Data Health only for blocked inputs.",
        "stop_rule": "Research-only: not advice; stop if required inputs are blocked, excluded, candidate context, or trade instruction.",
    },
    "Data Health": {
        "page": "Data Health",
        "question": "Why is something blocked and how do I fix it?",
        "short_answer": "Check one lane answer before opening proof, queues, or advanced details.",
        "next_page": PROOF_HISTORY_PATH_TITLE,
        "next_action": "Read the lane answer, then inspect proof only when evidence changed.",
        "stop_rule": "Research-only: not advice; stop before changing local data, trusting unsupported evidence, or creating any trade instruction.",
    },
    PROOF_HISTORY_PATH_TITLE: {
        "page": PROOF_HISTORY_PATH_TITLE,
        "question": "What evidence changed a readiness state?",
        "short_answer": "Review evidence only; this page does not refresh or unlock data.",
        "next_page": "Home",
        "next_action": "Verify the latest outcome, then return to the product path.",
        "stop_rule": "Research-only: not advice; stop if evidence is missing, stale, not source-backed, or used as a trade instruction.",
    },
}


def dashboard_page_slug(page_title: str) -> str:
    slug = str(page_title or "").strip().lower()
    slug = slug.replace("&", "and")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def public_workflow_step(page_title: str) -> dict[str, str]:
    return dict(PUBLIC_WORKFLOW_STEPS.get(page_title, PUBLIC_WORKFLOW_STEPS["Home"]))


def dashboard_page_from_query(value: object, user_page_titles: list[str]) -> str:
    raw = value[0] if isinstance(value, list) and value else value
    slug = dashboard_page_slug(unquote(str(raw or "").strip()))
    aliases = {
        "data": "Data Health",
        "data-health": "Data Health",
        "datahealth": "Data Health",
        "final": "Final Watchlist",
        "final-watchlist": "Final Watchlist",
        "market": "Market Direction",
        "market-direction": "Market Direction",
        "momentum": "Momentum Leaders",
        "momentum-leaders": "Momentum Leaders",
        "monthly": "Monthly Picks",
        "monthly-picks": "Monthly Picks",
        "portfolio": "Portfolio Review",
        "portfolio-review": "Portfolio Review",
        "proof": PROOF_HISTORY_PATH_TITLE,
        "proof-history": PROOF_HISTORY_PATH_TITLE,
        "proof-ledger": PROOF_HISTORY_PATH_TITLE,
        "proof-history-lane": PROOF_HISTORY_PATH_TITLE,
        "explore-ready-names": STOCK_SELECTOR_PATH_TITLE,
        "ready-names": STOCK_SELECTOR_PATH_TITLE,
        "research-queue": STOCK_SELECTOR_PATH_TITLE,
        "selector": STOCK_SELECTOR_PATH_TITLE,
        "single": "Single-Stock Report",
        "single-stock": "Single-Stock Report",
        "single-stock-report": "Single-Stock Report",
        "stock-filter": STOCK_SELECTOR_PATH_TITLE,
        "stock-selector": STOCK_SELECTOR_PATH_TITLE,
        "stock-report": "Single-Stock Report",
        "universe": "Universe Manager",
        "universe-manager": "Universe Manager",
        "undervalued-candidates": "Value / Re-rating",
        "valuation": "Value / Re-rating",
        "value": "Value / Re-rating",
        "value-re-rating": "Value / Re-rating",
        "value-rerating": "Value / Re-rating",
    }
    if slug in aliases:
        return aliases[slug]
    for title in user_page_titles:
        if dashboard_page_slug(title) == slug:
            return title
    return "Home"


def advanced_page_titles(user_page_titles: list[str]) -> list[str]:
    return [title for title in user_page_titles if title not in PUBLIC_PATH_PAGE_TITLES]


def dashboard_mode_from_query(value: object, initial_page: str, advanced_titles: list[str]) -> str:
    raw = value[0] if isinstance(value, list) and value else value
    slug = dashboard_page_slug(unquote(str(raw or "").strip()))
    if slug in {"operator", "ops", "internal", "advanced", "full"}:
        return OPERATOR_DEMO_MODE
    if slug in {"public", "demo", "visitor", "share"}:
        return PUBLIC_DEMO_MODE
    if initial_page in advanced_titles:
        return OPERATOR_DEMO_MODE
    return PUBLIC_DEMO_MODE


def dashboard_mode_label(mode: str) -> str:
    return DEMO_MODE_LABELS.get(mode, DEMO_MODE_LABELS[PUBLIC_DEMO_MODE])


def sidebar_path_options(initial_page: str, advanced_titles: list[str]) -> list[str]:
    """Return visitor path choices without pretending detailed pages are Home."""
    if initial_page in advanced_titles:
        return PUBLIC_PATH_PAGE_TITLES + [DETAILED_PAGE_PATH_TITLE]
    return PUBLIC_PATH_PAGE_TITLES


def sidebar_path_index(initial_page: str, path_options: list[str], advanced_titles: list[str]) -> int:
    if initial_page in path_options:
        return path_options.index(initial_page)
    if initial_page in advanced_titles and DETAILED_PAGE_PATH_TITLE in path_options:
        return path_options.index(DETAILED_PAGE_PATH_TITLE)
    return path_options.index("Home") if "Home" in path_options else 0


def page_title_from_public_path(value: object) -> str:
    """Map a sidebar path value or display label back to the canonical page title."""
    text = str(value or "").strip()
    if text in PUBLIC_PATH_LABELS:
        return text
    label_to_page = {label: page for page, label in PUBLIC_PATH_LABELS.items()}
    return label_to_page.get(text, LEGACY_PUBLIC_PATH_LABELS.get(text, text))


def public_path_label(page_title: str) -> str:
    return PUBLIC_PATH_LABELS.get(page_title, page_title)


def selected_page_from_route_rail(
    *,
    initial_page: str,
    default_path: str,
    path_selection: str,
    has_explicit_page_query: bool,
) -> str:
    selected_path = page_title_from_public_path(path_selection)
    default_path = page_title_from_public_path(default_path)
    if selected_path == DETAILED_PAGE_PATH_TITLE:
        return initial_page
    if has_explicit_page_query and selected_path == default_path:
        return initial_page
    return selected_path


def route_rail_query_update(*, selected_page: str, initial_page: str, mode: str) -> dict[str, str]:
    selected_page = page_title_from_public_path(selected_page)
    if selected_page == initial_page:
        return {}
    if selected_page not in PUBLIC_PATH_PAGE_TITLES:
        return {}
    return {
        "mode": dashboard_page_slug(mode),
        "page": dashboard_page_slug(selected_page),
    }
