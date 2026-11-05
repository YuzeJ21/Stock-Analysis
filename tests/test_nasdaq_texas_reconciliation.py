from src.nasdaq_texas_reconciliation import (
    EQUITY_COVERS,
    FUND_COHORTS,
    nasdaq_texas_detail_markdown,
    nasdaq_texas_review_markdown,
)


def test_nasdaq_texas_distinguishes_conversion_execution_and_listing_scope():
    review = nasdaq_texas_review_markdown()

    assert '2026-02-13' in review and 'Nasdaq BX' in review
    assert '2026-03-05' in review and '34-104907' in review
    assert 'September 2026' in review and 'matched volume' in review
    assert 'TXSE and NYSE Texas' in review
    assert '38 securities' in review and 'Full current roster remains unverified' in review
    assert 'Q2 2027' in review and 'primary-listing target' in review


def test_nasdaq_texas_counts_distinct_classes_and_certified_funds():
    assert {record.symbol for record in EQUITY_COVERS} == {
        'ACDC', 'APA', 'HBAN', 'JBHT', 'NDAQ', 'RMIX', 'ROAD', 'RUSHA', 'RUSHB', 'SPCX',
    }
    assert [len(group.members) for group in FUND_COHORTS] == [25, 3]
    assert len({symbol for group in FUND_COHORTS for symbol, _ in group.members}) == 28
    assert 'RUSHA** · Class A common stock' in nasdaq_texas_detail_markdown()
    assert 'RUSHB** · Class B common stock' in nasdaq_texas_detail_markdown()


def test_certification_and_effective_dates_are_separate_from_open_admissions():
    detail = nasdaq_texas_detail_markdown()

    assert '2026-10-26' in detail and '2026-10-27' in detail
    assert '2026-10-30' in detail and '2026-11-02' in detail
    assert 'BWIN' in detail and 'CSTL' in detail and 'NUTX' in detail
    assert 'admission unconfirmed' in detail
    assert '26000457.pdf' in detail


def test_candidate_followup_keeps_distinct_evidence_out_of_the_confirmed_count():
    review = nasdaq_texas_review_markdown()
    detail = nasdaq_texas_detail_markdown()

    assert '0 of 3 independently confirmed' in review
    assert '38 securities' in review
    _, candidates = detail.split('- **BWIN**', 1)
    bwin, candidates = candidates.split('- **CSTL**', 1)
    cstl, candidates = candidates.split('- **NUTX**', 1)
    nutx, _ = candidates.split('**Current roster**', 1)
    assert '2026-05-11' in bwin and '2026-10-27' in bwin
    assert 'seven subsequent SEC covers' in bwin and 'only Nasdaq Global Select Market' in bwin
    assert '2026-08-17' in cstl and 'Issuer-reported' in cstl
    assert 'no later SEC cover' in cstl and 'linkedin.com/' in cstl
    assert '2026-09-23' in nutx and 'no submissions' in nutx
    assert all('Form 8-A' in row and 'exchange certification' in row for row in (bwin, cstl, nutx))


def test_public_directory_presence_does_not_establish_nasdaq_texas_roster_membership():
    detail = nasdaq_texas_detail_markdown()

    assert 'SymbolDirDefs' in detail
    assert 'no Nasdaq Texas dual-listing field' in detail
    assert 'trading-system changes' in detail
    assert 'archiveheadlines' in detail
