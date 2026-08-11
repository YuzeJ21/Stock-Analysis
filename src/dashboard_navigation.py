from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping
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
RESEARCH_PATH_PAGE_TITLES = [
    "Research Desk",
    "Discover",
    "Company Workbench",
    "Monitor",
]
LEGACY_RESEARCH_UTILITY_PAGES = (
    "Monthly Picks",
    "Momentum Leaders",
    "Portfolio Review",
    "Value / Re-rating",
    "Final Watchlist",
)
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
RESEARCH_MODE = "research"
WORKSPACE_MODES = frozenset((PUBLIC_DEMO_MODE, OPERATOR_DEMO_MODE, RESEARCH_MODE))
MODE_QUERY_ALIASES = {
    "operator": OPERATOR_DEMO_MODE,
    "ops": OPERATOR_DEMO_MODE,
    "internal": OPERATOR_DEMO_MODE,
    "advanced": OPERATOR_DEMO_MODE,
    "full": OPERATOR_DEMO_MODE,
    "public": PUBLIC_DEMO_MODE,
    "demo": PUBLIC_DEMO_MODE,
    "visitor": PUBLIC_DEMO_MODE,
    "share": PUBLIC_DEMO_MODE,
    "research": RESEARCH_MODE,
    "personal": RESEARCH_MODE,
    "workspace": RESEARCH_MODE,
}
PUBLIC_WORKSPACE_PAGES = frozenset(PUBLIC_PATH_PAGE_TITLES)
RESEARCH_WORKSPACE_PAGES = frozenset((*RESEARCH_PATH_PAGE_TITLES, "Data Health", PROOF_HISTORY_PATH_TITLE))
DATA_HEALTH_QUERY_KEYS = (
    "ticker",
    "lane",
    "drawer",
    "queue_details",
    "batch_details",
    "proof_details",
    "metric_details",
)
WORKSPACE_ROUTE_QUERY_KEYS = {
    (PUBLIC_DEMO_MODE, "Home"): (),
    (PUBLIC_DEMO_MODE, STOCK_SELECTOR_PATH_TITLE): (),
    (PUBLIC_DEMO_MODE, "Single-Stock Report"): ("ticker", "open"),
    (PUBLIC_DEMO_MODE, "Data Health"): DATA_HEALTH_QUERY_KEYS,
    (PUBLIC_DEMO_MODE, PROOF_HISTORY_PATH_TITLE): ("ticker",),
    (RESEARCH_MODE, "Research Desk"): (),
    (RESEARCH_MODE, "Discover"): (),
    (RESEARCH_MODE, "Company Workbench"): ("ticker", "open", "cash_preview"),
    (RESEARCH_MODE, "Monitor"): (),
    (RESEARCH_MODE, "Data Health"): DATA_HEALTH_QUERY_KEYS,
    (RESEARCH_MODE, PROOF_HISTORY_PATH_TITLE): ("ticker",),
}


@dataclass(frozen=True)
class WorkspaceRouteResolution:
    mode: str
    requested_page: str
    page: str
    recognized: bool
    allowed: bool
    redirected: bool
    canonical_query: dict[str, str]
DEMO_MODE_LABELS = {
    RESEARCH_MODE: "Personal research mode",
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
        "stop_rule": "Research-only: not advice; stop if no readiness-backed path or trade instruction.",
    },
    "Single-Stock Report": {
        "page": "Single-Stock Report",
        "question": "What can I use for this ticker right now?",
        "short_answer": "Read supported sections first; blocked inputs stay locked.",
        "next_page": "Data Health",
        "next_action": "Use supported sections first; open Data Health only for blocked inputs.",
        "stop_rule": "Research-only: not advice; stop if inputs are blocked, candidate-only, or trade instruction.",
    },
    "Data Health": {
        "page": "Data Health",
        "question": "What can I use and what stays unavailable?",
        "short_answer": "Check one lane answer before opening proof, queues, or advanced details.",
        "next_page": PROOF_HISTORY_PATH_TITLE,
        "next_action": "Use the lane answer to understand what is available, then open Proof History only when evidence needs review.",
        "stop_rule": "Research-only: not advice; stop before changing local data or trusting trade instruction.",
    },
    PROOF_HISTORY_PATH_TITLE: {
        "page": PROOF_HISTORY_PATH_TITLE,
        "question": "What evidence changed a readiness state?",
        "short_answer": "Review evidence only; proof records do not refresh or unlock data.",
        "next_page": "Home",
        "next_action": "Check the latest proof record, then return to Stock Selector or the ticker report.",
        "stop_rule": "Research-only: not advice; stop if evidence is missing, stale, or a trade instruction.",
    },
}


def dashboard_page_slug(page_title: str) -> str:
    slug = str(page_title or "").strip().lower()
    slug = slug.replace("&", "and")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _query_value(value: object) -> str:
    raw = value[0] if isinstance(value, list) and value else value
    return str(raw or "").strip()


def _normalized_query_mapping(query_params: Mapping[str, object] | None) -> dict[str, str]:
    return {
        str(key): _query_value(value)
        for key, value in (query_params or {}).items()
        if _query_value(value)
    }


def _raw_page_resolution(value: object, user_page_titles: list[str]) -> tuple[str, bool]:
    raw = _query_value(value)
    if not raw:
        return "Home", True
    page = dashboard_page_from_query(raw, user_page_titles)
    if page != "Home":
        return page, True
    return page, dashboard_page_slug(unquote(raw)) in {"home", "start-at-home"}


def _workspace_page_allowed(mode: str, page: str, user_page_titles: list[str]) -> bool:
    if mode == PUBLIC_DEMO_MODE:
        return page in PUBLIC_WORKSPACE_PAGES
    if mode == RESEARCH_MODE:
        return page in RESEARCH_WORKSPACE_PAGES
    return page in {*user_page_titles, PROOF_HISTORY_PATH_TITLE}


def _workspace_fallback_page(mode: str) -> str:
    if mode == PUBLIC_DEMO_MODE:
        return "Home"
    if mode == RESEARCH_MODE:
        return "Research Desk"
    return "Home"


def canonical_workspace_query(
    mode: str,
    page: str,
    query_params: Mapping[str, object] | None,
) -> dict[str, str]:
    """Return the exact redirect-safe query mapping for a resolved Public or Research page."""
    normalized_mode = dashboard_page_slug(mode)
    normalized_page = str(page or "").strip()
    retained = _normalized_query_mapping(query_params)
    if normalized_mode not in {PUBLIC_DEMO_MODE, RESEARCH_MODE}:
        return retained
    canonical = {"mode": normalized_mode}
    if not (normalized_mode == PUBLIC_DEMO_MODE and normalized_page == "Home"):
        canonical["page"] = dashboard_page_slug(normalized_page)
    for key in WORKSPACE_ROUTE_QUERY_KEYS.get((normalized_mode, normalized_page), ()):
        if key in retained:
            canonical[key] = retained[key]
    return canonical


def resolve_workspace_route(
    raw_mode: object,
    raw_page: object,
    query_params: Mapping[str, object] | None,
    user_page_titles: list[str],
    operator_page_titles: list[str],
) -> WorkspaceRouteResolution:
    """Resolve raw route state before unknown pages can collapse to Home."""
    del operator_page_titles  # The full user page registry remains the operator compatibility contract.
    requested_page, recognized = _raw_page_resolution(raw_page, user_page_titles)
    mode_value = _query_value(raw_mode)
    mode_slug = dashboard_page_slug(unquote(mode_value))
    resolved_mode = MODE_QUERY_ALIASES.get(mode_slug)
    invalid_explicit_mode = bool(mode_value) and resolved_mode is None
    if invalid_explicit_mode:
        mode = RESEARCH_MODE
    elif resolved_mode:
        mode = resolved_mode
    elif requested_page in set(user_page_titles) - PUBLIC_WORKSPACE_PAGES - RESEARCH_WORKSPACE_PAGES:
        mode = OPERATOR_DEMO_MODE
    else:
        mode = RESEARCH_MODE

    existing_mode = MODE_QUERY_ALIASES.get(
        dashboard_page_slug(_normalized_query_mapping(query_params).get("mode", "")),
        "",
    )
    mode_switched = bool(existing_mode) and existing_mode != mode
    allowed = (
        not invalid_explicit_mode
        and recognized
        and _workspace_page_allowed(mode, requested_page, user_page_titles)
        and (not mode_switched or requested_page in {"Data Health", PROOF_HISTORY_PATH_TITLE})
    )
    page = requested_page if allowed else _workspace_fallback_page(mode)
    redirected = not allowed or mode_switched
    canonical_query = canonical_workspace_query(mode, page, query_params)
    if mode == OPERATOR_DEMO_MODE and redirected:
        canonical_query = {"mode": mode, "page": dashboard_page_slug(page)}
    return WorkspaceRouteResolution(
        mode=mode,
        requested_page=requested_page,
        page=page,
        recognized=recognized,
        allowed=allowed,
        redirected=redirected,
        canonical_query=canonical_query,
    )


def public_workflow_step(page_title: str) -> dict[str, str]:
    return dict(PUBLIC_WORKFLOW_STEPS.get(page_title, PUBLIC_WORKFLOW_STEPS["Home"]))


def public_workflow_position(page_title: str) -> str:
    """Return a compact visible progress cue for the public five-page flow."""
    canonical_page = public_workflow_step(page_title)["page"]
    try:
        index = PUBLIC_PATH_PAGE_TITLES.index(canonical_page) + 1
    except ValueError:
        index = 1
    return f"Step {index} of {len(PUBLIC_PATH_PAGE_TITLES)}"


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
        "research-desk": "Research Desk",
        "desk": "Research Desk",
        "discover": "Discover",
        "company-workbench": "Company Workbench",
        "workbench": "Company Workbench",
        "monitor": "Monitor",
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
    if mode := MODE_QUERY_ALIASES.get(slug):
        return mode
    if initial_page in advanced_titles:
        return OPERATOR_DEMO_MODE
    return RESEARCH_MODE


def dashboard_mode_label(mode: str) -> str:
    return DEMO_MODE_LABELS.get(mode, DEMO_MODE_LABELS[PUBLIC_DEMO_MODE])


def legacy_research_utility_label(page_title: str) -> str:
    if page_title in LEGACY_RESEARCH_UTILITY_PAGES:
        return f"Legacy utility · {page_title}"
    return page_title


def workspace_page_for_mode(page_title: str, mode: str) -> str:
    """Fail closed when a compatibility-only route is requested outside Operator."""
    if page_title not in LEGACY_RESEARCH_UTILITY_PAGES:
        return page_title
    if mode == OPERATOR_DEMO_MODE:
        return page_title
    if mode == RESEARCH_MODE:
        return "Research Desk"
    return "Home"


def sidebar_path_options(initial_page: str, advanced_titles: list[str]) -> list[str]:
    """Return visitor paths plus the active advanced route when one is open."""
    if initial_page in advanced_titles:
        return PUBLIC_PATH_PAGE_TITLES + [initial_page]
    return PUBLIC_PATH_PAGE_TITLES


def research_path_options(initial_page: str) -> list[str]:
    """Return the personal research path plus an active evidence route."""
    if initial_page in {"Data Health", PROOF_HISTORY_PATH_TITLE}:
        return RESEARCH_PATH_PAGE_TITLES + [initial_page]
    return RESEARCH_PATH_PAGE_TITLES


def research_path_label(page_title: str) -> str:
    return page_title if page_title in RESEARCH_PATH_PAGE_TITLES else PUBLIC_PATH_LABELS.get(page_title, page_title)


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


def route_rail_query_update(
    *,
    selected_page: str,
    initial_page: str,
    mode: str,
    allowed_pages: list[str] | None = None,
) -> dict[str, str]:
    selected_page = page_title_from_public_path(selected_page)
    if selected_page == initial_page:
        return {}
    if selected_page not in (allowed_pages or PUBLIC_PATH_PAGE_TITLES):
        return {}
    return {
        "mode": dashboard_page_slug(mode),
        "page": dashboard_page_slug(selected_page),
    }
