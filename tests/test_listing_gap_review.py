def test_dated_listing_gap_review_preserves_both_populations_and_the_original_inventory():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert '2026-11-12' in review and '13,791' in review and '38 test issues excluded' in review
    assert '544 SEC-only' in review and '282 unresolved directory types' in review
    assert '246' in review and '19' in review and '17' in review
    assert '540 still unreviewed' in review and '279 still unreviewed' in review
    assert all(symbol in review for symbol in ('ABR-PD', 'ABR-PE', 'ABR-PF', 'ALUR', 'GOOG', 'ADSEW', 'PFBC'))
    assert 'Form 25' in review and 'Class C Capital Stock' in review and 'Nasdaq warrant' in review
    assert 'PFBC · Type remains unresolved' in review
    assert 'Full U.S. coverage remains unverified' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1253986/000125398626000064/abr-20261030.htm' in review


def test_dated_listing_gap_review_is_limited_to_personal_research(monkeypatch):
    from src.listing_gap_review import listing_gap_review_markdown

    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    assert listing_gap_review_markdown() == ''
