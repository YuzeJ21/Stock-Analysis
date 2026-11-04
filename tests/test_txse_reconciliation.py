from collections import Counter

from src.txse_reconciliation import (
    TXSE_IDENTITIES,
    txse_identity_markdown,
    txse_review_markdown,
)


def test_txse_review_separates_launch_listing_and_first_execution():
    review = txse_review_markdown()

    assert 'Texas Stock Exchange LLC and NYSE Texas are separate venues' in review
    assert '34-104146.pdf' in review and '2025-09-30' in review
    assert '2026-07-06' in review and 'test symbols' in review
    assert '2026-07-10' in review and 'scheduled' in review
    assert 'Live trading confirmed by 2026-07-31' in review
    assert 'First execution date remains unverified' in review
    assert '23 of 23' in review and '68 test rows' in review
    assert '2026-11-03' in review and 'all-listings' in review


def test_txse_reconciles_the_dated_listing_set_at_security_grain():
    assert {row.symbol for row in TXSE_IDENTITIES} == {
        'CECO', 'CTAG', 'DDS', 'DDT', 'ET', 'ET-PRI', 'FIFT', 'IBOC', 'ICOM', 'ILS', 'OBK',
        'OILT', 'PWRX', 'SCHW', 'SUN', 'SUNC', 'TCBI', 'TCBI-PRB', 'THRU', 'TXS', 'USAC', 'WSLS', 'WTAL',
    }
    assert Counter(row.kind for row in TXSE_IDENTITIES) == {
        'Common stock': 6, 'Common units': 4, 'Preferred units': 1,
        'Depositary shares': 1, 'Trust capital securities': 1, 'ETF': 10,
    }
    assert all(row.source_url.startswith('https://www.sec.gov/Archives/edgar/data/') for row in TXSE_IDENTITIES)


def test_txse_identity_details_keep_preferred_and_trust_issues_separate():
    identities = txse_identity_markdown()

    assert '**ET-PRI**' in identities and 'Series I' in identities
    assert '**TCBI-PRB**' in identities and '1/40' in identities
    assert '**DDT**' in identities and 'guaranteed by' in identities
    assert '**DIT**' not in identities
    assert identities.count('https://www.sec.gov/Archives/edgar/data/') == 23


def test_txse_reports_schwab_secondary_registration_outside_snapshot_count():
    review = txse_review_markdown()

    assert 'SCHW · Separate secondary listing' in review
    assert 'admission effective 2026-10-07' in review and '2026-10-15' in review
    assert 'TXSE_MAF_20261006_2000_FINAL_NO_CUSIP.csv' in review
    assert '22 flagged rows omit this secondary listing' in review
    assert '**SCHW**' in txse_identity_markdown()
