def test_dated_listing_gap_review_preserves_both_populations_and_the_original_inventory():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert '2026-11-12' in review and '13,791' in review and '38 test issues excluded' in review
    assert '544 SEC-only' in review and '282 unresolved directory types' in review
    assert '246' in review and '19' in review and '17' in review
    assert '527 still unreviewed' in review and '279 still unreviewed' in review
    assert all(symbol in review for symbol in ('ABR-PD', 'ABR-PE', 'ABR-PF', 'ALUR', 'GOOG', 'ADSEW', 'PFBC'))
    assert 'Form 25' in review and 'Class C Capital Stock' in review and 'Nasdaq warrant' in review
    assert 'Full U.S. coverage remains unverified' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1253986/000125398626000064/abr-20261030.htm' in review


def test_farmer_mac_review_uses_exact_series_and_symbol_spellings():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Six NYSE preferred share classes matched' in review
    assert all(f'AGM-P{series}' in review and f'AGM.PR{series}' in review and f'AGM${series}' in review
               for series in 'DEFGHI')
    assert 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000143/agm-20261112.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000139/agm-20260930.htm' in review


def test_triton_review_keeps_the_seven_distinct_preference_share_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Seven NYSE preference share classes matched' in review
    for series in 'ABCDEFG':
        assert f'TRTN-P{series}' in review and f'TRTN PR{series}' in review and f'TRTN${series}' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1660734/000166073426000005/trtn-20251231.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1660734/000162828026071407/trtn-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1660734/000087666126000041/TRTNPRG011326.pdf' in review


def test_pfbc_common_stock_is_dated_to_the_fdic_covers():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'PFBC · Nasdaq common stock confirmed as filed' in review
    assert 'November 9' in review and 'September 30' in review and '33539' in review
    assert 'PFBC · Type remains unresolved' not in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12041/attachment/1' in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11872/attachment/1' in review


def test_pfbc_filing_patterns_keep_the_irs_number_unreconciled():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'PFBC IRS number · Unreconciled' in review
    assert 'Six quarterly covers from 2025 and 2026 show `95-4340119`' in review
    assert 'October 27 Form 8-K show `95-4340199`' in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11687/attachment/1' in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/cert/33539' in review


def test_dated_listing_gap_review_is_limited_to_personal_research(monkeypatch):
    from src.listing_gap_review import listing_gap_review_markdown

    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    assert listing_gap_review_markdown() == ''
