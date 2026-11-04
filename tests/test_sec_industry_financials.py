"""Industry definitions must change observed support without invented amounts."""
from copy import deepcopy

import pytest

from test_sec_annual_history import _payload, _view
from test_sec_quarterly_history import _quarter_payload, _build
from test_online_company_identity import _identity


@pytest.mark.parametrize('concept', ['RevenuesNetOfInterestExpense', 'RegulatedAndUnregulatedOperatingRevenue', 'RevenueFromContractWithCustomerIncludingAssessedTax'])
def test_exact_bank_and_utility_definitions_support_annual_and_quarter(concept):
    annual = _payload()
    annual['facts']['us-gaap'][concept] = annual['facts']['us-gaap'].pop('Revenues')
    view = _view(annual)
    revenue = next((f for f in view.get('approved_direct_fields', []) if f['field'] == 'revenue'), None)
    assert revenue is not None
    assert revenue['concept'] == concept and revenue['value'] == 150
    quarterly = _quarter_payload()
    facts = quarterly['facts']['us-gaap']
    facts[concept] = facts.pop('Revenues')
    result = _build(quarterly)
    assert result['periods'][-1]['fields']['revenue']['concept'] == concept


def _record(start='2025-01-01', end='2025-12-31', value=100, filed='2026-03-01', form='20-F', accession='0000001234-26-000001'):
    return dict(start=start, end=end, val=value, filed=filed, form=form, accn=accession, fy=2025, fp='FY')


def _foreign_payload():
    annual = _record()
    q = _record('2026-04-01', '2026-06-30', 30, '2026-08-01', '6-K', '0000001234-26-000002')
    cumulative = {**q, 'start': '2026-01-01', 'val': 55}
    facts = {
        'Revenue': {'units': {'EUR': [annual, q, cumulative], 'USD': [{**r, 'val': r['val'] * 2} for r in [annual, q, cumulative]]}},
        'ProfitLossFromOperatingActivities': {'units': {'EUR': [{**annual, 'val': 10}, {**q, 'val': 4}]}},
        'CashFlowsFromUsedInOperatingActivities': {'units': {'EUR': [{**annual, 'val': 20}, {**cumulative, 'val': 12}]}},
        'PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities': {'units': {'EUR': [{**annual, 'val': 5}, {**cumulative, 'val': 3}]}},
    }
    return {'cik': 1234, 'entityName': 'Fictional Foreign Issuer', 'facts': {'ifrs-full': facts}}


def _foreign(payload=None):
    from src.sec_foreign_financials import build_sec_foreign_financials
    return build_sec_foreign_financials('FICT', payload or _foreign_payload(), expected_cik='0000001234',
        observed_at='2026-10-30T18:00:00Z', source_url='https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json', payload_sha256='a' * 64)


def _foreign_view(payload=None):
    return {'ticker': 'FICT', 'companyfacts_identity': _identity(), 'foreign_financials': _foreign(payload)}


def test_foreign_direct_evidence_prefers_reporting_currency_and_separates_cumulative_flows():
    from src.sec_foreign_financials import validated_foreign_financials
    p = _foreign_payload(); before = deepcopy(p)
    result = _foreign(p)
    assert result['status'] == 'inspection_only' and result['unit'] == 'EUR'
    assert result['annual'][-1]['fields']['revenue']['value'] == 100
    quarter = result['quarterly'][-1]
    assert quarter['fields']['revenue']['value'] == 30
    assert 'cash_from_operations' not in quarter['fields']
    assert result['interim'][-1]['fields']['cash_from_operations']['value'] == 12
    assert result['interim'][-1]['period_start'] == '2026-01-01'
    assert validated_foreign_financials(_foreign_view(p)) is not None
    assert p == before


def test_multiple_plausible_native_reporting_currencies_are_withheld():
    p = _foreign_payload(); units = p['facts']['ifrs-full']['Revenue']['units']
    units['GBP'] = deepcopy(units['EUR'])
    assert _foreign(p)['reason'] == 'ambiguous_reporting_currency'


@pytest.mark.parametrize('change', ['accession', 'start', 'form', 'filed', 'currency'])
def test_later_unusable_foreign_revision_cannot_restore_old_success(change):
    p = _foreign_payload(); units = p['facts']['ifrs-full']['Revenue']['units']
    latest = {**units['EUR'][1], 'filed': '2026-09-01', 'accn': '0000001234-26-000003'}
    if change == 'accession': latest['accn'] = 'bad'
    elif change == 'start': latest['start'] = 'bad'
    elif change == 'form': latest['form'] = 'bad'
    elif change == 'filed': latest['filed'] = 'bad'
    if change == 'currency': units['USD'].append(latest)
    else: units['EUR'].append(latest)
    result = _foreign(p)
    assert result['quarterly'][-1]['status'] == 'withheld'
    assert result['quarterly'][-1]['fields'] == {}


def test_foreign_missing_6k_quarter_is_not_invented_from_half_year_or_annual():
    p = _foreign_payload()
    for fact in p['facts']['ifrs-full'].values():
        for unit, rows in fact['units'].items():
            fact['units'][unit] = [r for r in rows if r['start'] != '2026-04-01']
    result = _foreign(p)
    assert result['quarterly'] == [] and len(result['interim']) == 1
    assert result['annual'][0]['fields']['revenue']['value'] == 100


def test_foreign_unsupported_combined_investing_components_are_not_called_ppe_capex():
    p = _foreign_payload(); facts = p['facts']['ifrs-full']
    facts['PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets'] = facts.pop('PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities')
    result = _foreign(p)
    assert 'capital_expenditures' not in result['annual'][0]['fields']
    assert result['annual'][0]['withheld_fields']['capital_expenditures']


def test_native_cached_values_require_matching_currency_source_digest_and_context():
    from src.sec_foreign_financials import validated_foreign_financials
    for mutate in ['unit', 'digest', 'accession', 'period', 'rights']:
        view = _foreign_view(); f = view['foreign_financials']['quarterly'][0]['fields']['revenue']
        if mutate == 'unit': f['unit'] = 'USD'
        elif mutate == 'digest': view['foreign_financials']['payload_sha256'] = 'b' * 64
        elif mutate == 'accession': f['accession'] = '0000001234-26-999999'
        elif mutate == 'period': f['period_start'] = '2026-01-01'
        else: f['rights_status'] = 'unreviewed'
        assert validated_foreign_financials(view) is None


def test_foreign_wrong_issuer_and_unreviewed_field_scope_are_held(monkeypatch):
    from src import sec_foreign_financials
    p = _foreign_payload(); p['cik'] = 9999
    assert _foreign(p)['status'] == 'withheld'
    monkeypatch.setattr(sec_foreign_financials, 'field_is_permitted', lambda *_: False)
    assert _foreign()['reason'] == 'field_scope_unreviewed'


def test_online_coverage_counts_native_annual_quarter_and_interim_separately_without_amounts():
    import json
    from datetime import datetime, timezone
    from src.online_research_coverage import run_online_coverage_study, validated_coverage_summary
    from test_online_company_identity import _profile_payload
    def fetch(url, agent):
        if 'company_tickers' in url: body = {'0': {'ticker': 'FICT', 'cik_str': 1234}}
        elif '/companyfacts/' in url: body = _foreign_payload()
        else: body = _profile_payload()
        return json.dumps(body).encode(), {}, url
    result = run_online_coverage_study(['FICT'], user_agent='Research', source_fetcher=fetch, observed_at=datetime(2026, 10, 30, 18, tzinfo=timezone.utc))
    assert result['counts']['annual_revenue'] == result['counts']['quarterly_revenue'] == 1
    assert result['counts']['quarterly_cash_from_operations'] == 0
    assert result['counts']['interim_cash_from_operations'] == 1
    assert result['rows'][0]['annual_unit'] == result['rows'][0]['interim_unit'] == 'EUR'
    assert validated_coverage_summary(result) is not None
    assert '"value"' not in json.dumps(result)


@pytest.mark.parametrize('bad_form', [[], {}, 3])
def test_malformed_foreign_form_is_held_without_exception(bad_form):
    p = _foreign_payload()
    for unit in p['facts']['ifrs-full']['Revenue']['units'].values(): unit[1]['form'] = bad_form
    result = _foreign(p)
    assert not any(r['status'] == 'available' for r in result['quarterly'])


def test_foreign_same_start_revision_with_malformed_end_holds_the_old_quarter():
    p = _foreign_payload(); rows = p['facts']['ifrs-full']['Revenue']['units']['EUR']
    rows.append({**rows[1], 'end': 'bad', 'filed': '2026-09-01', 'accn': '0000001234-26-000003'})
    result = _foreign(p)
    assert result['quarterly'][-1]['status'] == 'withheld'
    assert not result['quarterly'][-1]['fields']


@pytest.mark.parametrize('start,end,kind', [('2026-07-01','2026-09-30','quarterly'), ('2026-01-01','2026-09-30','interim')])
def test_later_ifrs_6k_reporting_period_without_revenue_stays_in_coverage(start,end,kind):
    import json
    from datetime import datetime, timezone
    from src.online_research_coverage import run_online_coverage_study
    from src.sec_foreign_financials import validated_foreign_financials
    from test_online_company_identity import _profile_payload
    p = _foreign_payload()
    p['facts']['ifrs-full']['ProfitLossFromOperatingActivities']['units']['EUR'].append(
        _record(start,end,9,'2026-10-20','6-K','0000001234-26-000003'))
    view = _foreign_view(p)
    latest = view['foreign_financials'][kind][-1]
    assert latest['period_end'] == end and latest['status'] == 'withheld'
    assert validated_foreign_financials(view) is not None
    def fetch(url,agent):
        body = {'0':{'ticker':'FICT','cik_str':1234}} if 'company_tickers' in url else p if '/companyfacts/' in url else _profile_payload()
        return json.dumps(body).encode(),{},url
    result = run_online_coverage_study(['FICT'],user_agent='Research',source_fetcher=fetch,observed_at=datetime(2026,10,30,18,tzinfo=timezone.utc))
    assert result['rows'][0][kind+'_period'] == end
    assert result['counts'][kind+'_revenue'] == 0
