from src.gix_reconciliation import gix_review_markdown


def test_gix_review_keeps_registration_and_opening_separate():
    review = gix_review_markdown()

    assert 'Reviewed 2026-11-12' in review
    assert 'SEC registration · Confirmed' in review
    assert '2025-04-11' in review and '34-102853.pdf' in review
    assert 'Trading launch · Unverified' in review
    assert 'First trading day remains unknown' in review
    assert '2026-05-28' in review and '34-105650.pdf' in review
    assert 'Q1 2027' in review and 'H2 2026' in review
    assert '2026-07-01' in review


def test_gix_review_keeps_unknown_roster_distinct_from_search_result():
    review = gix_review_markdown()

    assert 'Current listings · Count unknown' in review
    assert '0 security identities verified in this review' in review
    assert '2024-05-09' in review and 'exhibit-n-green-impact-exchange-llc.pdf' in review
    assert '0 EDGAR matches' in review and 'paper filings' in review
    assert 'enddt=2026-11-12' in review
    assert 'unlisted trading privileges' in review
