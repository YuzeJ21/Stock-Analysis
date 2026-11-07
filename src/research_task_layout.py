"""Small task-first presentation helpers for the Personal Research routes.

The saved-card helper receives the already scoped and validated output of
``sec_research_review.review_queue``. It performs no source fetch or state write.
"""

from collections.abc import Mapping
from html import escape
from urllib.parse import quote

from src.dashboard_visual_system import context_bar_html, page_title_html
from src.sec_research_review import _ticker, _validate
from src.sec_research_review_ui import STATUS


_PURPOSE = {
    "Research Desk": "Find a company, continue research, and review evidence changes.",
    "Discover": "Find a company online or browse saved research.",
    "Monitor": "Review saved SEC evidence and research follow-ups.",
}

_HEADER_STYLE = """<style>
.research-task-header{margin:0 0 1rem;padding:0 0 .65rem;border-bottom:1px solid #dce5df}
.research-task-header .sr-page-title{margin-bottom:.15rem}
.research-task-header h1{font-size:2rem!important;line-height:1.2!important;margin:0 0 .4rem!important;padding:0!important}
.research-task-header .sr-page-purpose,.research-task-header p{margin:.3rem 0;line-height:1.4}
.research-task-section-title,.st-key-research-company-search h2{font-size:1.35rem!important;line-height:1.3!important;margin:.4rem 0 .5rem!important;padding:0!important}
.research-task-details{margin:.2rem 0 0;color:#43564a;font-size:.88rem}
.research-task-details summary{cursor:pointer;min-height:44px;display:list-item;align-content:center;width:max-content;max-width:100%}
.research-task-details summary:focus-visible,.research-task-details a:focus-visible{outline:3px solid #155e4b;outline-offset:3px}
.research-task-details .sr-context-bar{margin:.35rem 0;max-width:100%}
.research-task-details dt{font-size:.75rem;color:#52655a}.research-task-details dd{overflow-wrap:anywhere}
</style>"""

_CARD_STYLE = """<style>
.saved-sec-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:.75rem;margin:.5rem 0 1rem}
.saved-sec-card{min-width:0;padding:.85rem;border:1px solid #dce5df;border-radius:10px;background:#fff;overflow-wrap:anywhere}
.saved-sec-card h3{font-size:1.05rem;margin:.1rem 0 .45rem}.saved-sec-card p{margin:.35rem 0;line-height:1.4}
.saved-sec-card .saved-sec-kicker{font-size:.75rem;color:#52655a;text-transform:uppercase;letter-spacing:.02em}
.saved-sec-card a{display:inline-flex;align-items:center;min-height:44px;color:#155e4b;text-decoration:underline}
.saved-sec-card a:focus-visible{outline:3px solid #155e4b;outline-offset:3px}
</style>"""


def task_page_header_html(page_title: str, *, profile_label: str, freshness: str) -> str:
    """Show one task heading; retain workspace identity in a closed disclosure."""

    if page_title not in _PURPOSE:
        raise ValueError("unsupported_research_task_page")
    title = page_title_html(title=page_title, purpose=_PURPOSE[page_title]).value
    context = context_bar_html((
        ("Data profile", str(profile_label)),
        ("Saved readiness", str(freshness)),
        ("Mode", "Personal research"),
    )).value
    details = (
        '<details class="research-task-details"><summary>Workspace details</summary>'
        + context + '<a href="?mode=research&amp;page=data-health" target="_self">Open Data Health</a>'
        '</details>'
    )
    return _HEADER_STYLE + '<section class="research-task-header" aria-label="Personal research task">' + title + details + '</section>'


def _displayable_item(item: object) -> tuple[str, Mapping | None, Mapping | None, bool] | None:
    if not isinstance(item, Mapping):
        return None
    ticker = item.get("ticker")
    if not _ticker(ticker):
        return None
    if item.get("error") == "saved_receipts_unreadable":
        if item.get("latest") is None and item.get("comparison") is None:
            return ticker, None, None, True
        return None
    if item.get("error") is not None:
        return None
    latest, comparison = item.get("latest"), item.get("comparison")
    if not isinstance(latest, dict) or not isinstance(comparison, Mapping):
        return None
    try:
        _validate(latest)
    except (KeyError, TypeError, ValueError):
        return None
    status = comparison.get("status")
    if latest["ticker"] != ticker or not isinstance(status, str) or status not in STATUS:
        return None
    return ticker, latest, comparison, False


def saved_research_cards_html(queue: object, *, limit: int = 4) -> str:
    """Summarize bounded, saved SEC receipts without implying market coverage."""

    if not isinstance(queue, Mapping) or not isinstance(queue.get("items"), list):
        return '<p role="status">Saved SEC evidence summary unavailable.</p>'
    items = queue["items"]
    errors = queue.get("store_errors")
    error_count = len(errors) if isinstance(errors, list) else 0
    storage_note = (
        '<p role="status">' + str(error_count) + ' unverified storage entr'
        + ('y' if error_count == 1 else 'ies') + '. Excluded from saved company cards.</p>'
        if error_count else ''
    )
    if not items:
        return '<p>No saved SEC evidence receipts in this research profile.</p>' + storage_note
    safe_items = [display for item in items if (display := _displayable_item(item)) is not None]
    if not safe_items:
        return '<p role="status">Saved SEC evidence summary unavailable. Check the saved evidence folder.</p>' + storage_note
    bounded = min(max(limit, 1), 4) if type(limit) is int else 4
    cards = []
    for ticker, latest, comparison, unreadable in safe_items[:bounded]:
        heading = '<span class="saved-sec-kicker">Saved SEC evidence</span><h3>' + escape(ticker) + '</h3>'
        if unreadable:
            body = '<p><strong>Saved files need verification</strong></p><p>Receipt details are unavailable. Check the saved evidence folder.</p>'
            error_class = ' saved-sec-card-error'
        else:
            gap_count = len(latest["gaps"])
            gap_label = 'No open field gaps' if gap_count == 0 else f'{gap_count} open field gap' + ('s' if gap_count != 1 else '')
            body = (
                '<p>Annual period ended ' + escape(latest["period_end"]) + ' · Form ' + escape(latest["form"]) + '</p>'
                '<p><strong>' + escape(STATUS[comparison["status"]]) + '</strong> · ' + gap_label + '</p>'
                '<a href="?mode=research&amp;page=company-workbench&amp;ticker=' + quote(ticker, safe='')
                + '&amp;section=notes" target="_self">Open ' + escape(ticker) + ' saved evidence</a>'
            )
            error_class = ''
        cards.append('<article class="saved-sec-card' + error_class + '">' + heading + body + '</article>')
    more = len(safe_items) - len(cards)
    remainder = '<p>' + str(more) + ' more saved company record' + ('s' if more != 1 else '') + ' in the review queue.</p>' if more else ''
    return (
        _CARD_STYLE + '<section aria-label="Saved SEC evidence cards">'
        '<p>Explicitly saved annual SEC observations in this research profile. Listing and investment eligibility require separate evidence.</p>'
        '<div class="saved-sec-cards">' + ''.join(cards) + '</div>' + remainder + storage_note + '</section>'
    )
