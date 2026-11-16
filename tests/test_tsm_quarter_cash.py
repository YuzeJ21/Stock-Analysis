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
