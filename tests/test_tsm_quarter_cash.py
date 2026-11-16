from datetime import datetime, timezone

import pytest


@pytest.mark.parametrize(('nine_months', 'expected'), [(19_004, True), (19_005, False)])
def test_reviewed_quarter_subtracts_thousands_before_rounding(nine_months, expected):
    from src.sec_tsm_quarter_cash import cash_flow_rows

    field = 'cash_from_operations'
    inputs = {'six_months': {field: 4_005}, 'nine_months': {field: nine_months}, 'presentation': {field: 1}}
    for amounts in inputs.values():
        amounts['capital_expenditures'] = 0
    rows = cash_flow_rows({'inputs': inputs})
    assert rows[field]['quarter_thousands'] == nine_months - 4_005
    assert rows[field]['matches_presentation'] is expected


def test_tsm_cash_evidence_requires_exact_reviewed_receipt_and_scope():
    from src.sec_tsm_quarter_cash import valid_cash_reconciliation, CASH_SCOPE, CASH_SOURCES

    observed_at = '2026-11-16T20:00:00Z'
    now = datetime(2026, 11, 16, 21, tzinfo=timezone.utc)
    current = {**CASH_SCOPE, 'observed_at': observed_at, 'payload_sha256': 'a' * 64}
    cents = {'cash_from_operations': 2, 'capital_expenditures': 1}
    thousands = {'cash_from_operations': 20_000, 'capital_expenditures': 10_000}
    evidence = {'receipts': {key: {'source_url': source['source_url'], 'observed_at': observed_at,
                                  'payload_sha256': 'a' * 64, 'source_last_modified': None}
                             for key, source in CASH_SOURCES.items()},
                'inputs': {'six_months': thousands, 'nine_months': thousands, 'presentation': cents}}
    assert valid_cash_reconciliation(evidence, current=current, as_of=now)
    assert not valid_cash_reconciliation(evidence, current={**current, 'payload_sha256': 'b' * 64}, as_of=now)
    assert not valid_cash_reconciliation(evidence, current={**current, 'period_end': '2026-06-30'}, as_of=now)
    malformed = {**evidence, 'inputs': {**evidence['inputs'], 'nine_months': {**thousands, 'capital_expenditures': -1}}}
    assert not valid_cash_reconciliation(malformed, current=current, as_of=now)
    reversed_purchases = {**evidence, 'inputs': {**evidence['inputs'],
        'nine_months': {**thousands, 'capital_expenditures': 9_999}}}
    assert not valid_cash_reconciliation(reversed_purchases, current=current, as_of=now)


def test_cash_view_keeps_a_mismatch_open_with_amount_and_filing_review():
    from src.sec_online_quarter_view import tsm_cash_reconciliation_html
    from src.sec_tsm_quarter_cash import CASH_SOURCES

    june = {'cash_from_operations': 20_000, 'capital_expenditures': 10_000}
    september = {'cash_from_operations': 35_321, 'capital_expenditures': 20_000}
    presentation = {'cash_from_operations': 1, 'capital_expenditures': 1}
    evidence = {'inputs': {'six_months': june, 'nine_months': september, 'presentation': presentation},
                'receipts': {key: {'observed_at': '2026-11-16T20:00:00Z', 'payload_sha256': 'a' * 64}
                             for key in CASH_SOURCES}}

    html = tsm_cash_reconciliation_html(evidence)
    assert 'Operating cash flow discrepancy review' in html
    assert 'Open · Cause unverified as of November 16, 2026.' in html
    assert 'rounds to TWD 0.02 billion' in html and 'TWD 5,321 thousand above' in html
    assert 'November 10 board filing' in html and 'tsm-boardx202611xx.htm' in html
    assert 'TSM SEC filing history' in html

    presentation['cash_from_operations'] = 2
    assert 'Operating cash flow discrepancy review' not in tsm_cash_reconciliation_html(evidence)
    assert 'Operating cash flow discrepancy review' not in tsm_cash_reconciliation_html(None)
