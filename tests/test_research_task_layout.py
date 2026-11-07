"""Task-first research layout contracts using saved SEC receipts only."""

import re

import pytest

from src.sec_research_review import review_queue, save_review
from tests.test_multi_company_sec_review import capture


@pytest.mark.parametrize("page,purpose", [
    ("Research Desk", "Find a company, continue research"),
    ("Discover", "Find a company online or browse saved research"),
    ("Monitor", "Review saved SEC evidence and research follow-ups"),
])
def test_task_header_has_one_clear_title_and_closed_workspace_details(page, purpose):
    from src.research_task_layout import task_page_header_html

    html = task_page_header_html(page, profile_label="Local default", freshness="Current for saved sources")
    assert html.count("<h1>") == 1
    assert f"<h1>{page}</h1>" in html and purpose in html
    assert "<details" in html and "<summary>Workspace details</summary>" in html
    assert "<details open" not in html
    assert "data-sr-region='page-title'" in html
    assert "data-sr-region='context'" in html
    assert "Local default" in html and "Current for saved sources" in html
    assert "Personal research" in html
    assert 'href="?mode=research&amp;page=data-health"' in html
    assert html.index("<h1>") < html.index("<details")
    assert html.index("<details") < html.index("data-sr-region='context'")


def test_task_header_escapes_workspace_values_and_rejects_other_pages():
    from src.research_task_layout import task_page_header_html

    html = task_page_header_html("Discover", profile_label="<script>bad</script>", freshness='bad" onfocus="alert(1)')
    assert "<script>" not in html and '<dd onfocus=' not in html
    assert "&lt;script&gt;bad&lt;/script&gt;" in html
    assert '<dd>bad" onfocus="alert(1)</dd>' in html
    with pytest.raises(ValueError):
        task_page_header_html("Data Health", profile_label="Local", freshness="Current")


def _saved_queue(tmp_path):
    save_review(capture(), tmp_path)
    duk = capture("DUK", "0001326160")
    duk["fields"].pop()
    duk["gaps"] = [{"field": "capital_expenditures", "reason": "direct_field_missing"}]
    from tests.test_sec_research_review import reseal
    save_review(reseal(duk), tmp_path)
    bad_path = save_review(capture("FICT", "0000001234"), tmp_path)
    bad_path.write_bytes(b"{}")
    return review_queue(tmp_path, "test")


def test_saved_cards_show_only_validated_receipt_identity_period_status_and_gap(tmp_path):
    from src.research_task_layout import saved_research_cards_html

    html = saved_research_cards_html(_saved_queue(tmp_path))
    assert "Saved SEC evidence" in html
    assert "AMD" in html and "DUK" in html and "FICT" in html
    assert "2025-12-31" in html and "Saved, awaiting a comparison baseline" in html
    assert "1 open field gap" in html and "Saved files need verification" in html
    assert 'href="?mode=research&amp;page=company-workbench&amp;ticker=AMD&amp;section=notes"' in html
    assert 'href="?mode=research&amp;page=company-workbench&amp;ticker=DUK&amp;section=notes"' in html
    assert "ticker=FICT" not in html
    assert "Companyfacts" not in html and "USD" not in html
    assert "<h2" not in html  # The caller owns the page section heading.


def test_saved_cards_limit_is_bounded_and_empty_or_bad_queue_is_safe(tmp_path):
    from src.research_task_layout import saved_research_cards_html

    queue = _saved_queue(tmp_path)
    assert saved_research_cards_html(queue, limit=1).count('class="saved-sec-card"') == 1
    assert saved_research_cards_html(queue, limit=99).count('class="saved-sec-card"') <= 4
    assert "No saved SEC evidence receipts" in saved_research_cards_html(review_queue(tmp_path, "other"))
    assert "summary unavailable" in saved_research_cards_html(None)
    forged = {"items": [{"ticker": "<script>bad</script>", "latest": {}, "comparison": {"status": "unchanged"}, "error": None}]}
    html = saved_research_cards_html(forged)
    assert "<script>" not in html and "company-workbench" not in html
    assert not re.search(r"ticker=%3C", html)


def test_saved_cards_keep_unverified_storage_separate_from_empty_receipts(tmp_path):
    from src.research_task_layout import saved_research_cards_html

    queue = review_queue(tmp_path, "test")
    queue["store_errors"] = [{"entry": "<script>bad</script>", "reason": "invalid_company_store"}]
    html = saved_research_cards_html(queue)
    assert "No saved SEC evidence receipts" in html
    assert "1 unverified storage entry" in html
    assert "<script>" not in html and "bad" not in html


def test_saved_cards_reject_malformed_comparison_without_crashing(tmp_path):
    from src.research_task_layout import saved_research_cards_html

    item = _saved_queue(tmp_path)["items"][0].copy()
    item["comparison"] = {"status": []}
    html = saved_research_cards_html({"items": [item]})
    assert "summary unavailable" in html
    assert "company-workbench" not in html
