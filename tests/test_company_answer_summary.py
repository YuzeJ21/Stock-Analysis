from copy import deepcopy

from tests.test_company_workbench_sections import financial_view, price_view


def _answers(*, peer=None, financial=None, prices=None, expected_cik='0000001234'):
    from src.company_answer_summary import build_company_answers
    from src.company_workbench_sections import workbench_projection

    financial = financial_view() if financial is None else financial
    prices = price_view() if prices is None else prices
    projection = workbench_projection('FICT', financial, prices, expected_cik=expected_cik)
    return {card['key']: card for card in build_company_answers('FICT', projection, financial, prices, {}, peer)}


def _peer(count, *, status='research_comparison'):
    return dict(ticker='FICT', status=status, metric='reported_annual_diluted_pe',
                reason='at_least_three_compatible_industry_references_required',
                subject=dict(ticker='FICT', price_date='2026-10-29', multiple=24.0),
                peers=[dict(ticker=f'F{n}', price_date='2026-10-29') for n in range(count)],
                peer_count=count, peer_median=20.0, premium_fraction=0.2,
                checked_candidate_count=4, candidate_count=4)


def test_first_answers_use_verified_close_and_comparable_revenue_direction():
    result = _answers()
    assert list(result) == ['price', 'financial', 'valuation']
    assert result['price']['value'] == 'USD 11.00'
    assert '2026-10-29' in result['price']['context']
    assert 'Yahoo' in result['price']['links'][0][0]
    assert result['financial']['value'] == '营收 USD 150'
    assert '较上财年增加' in result['financial']['context']
    assert '2025-12-31' in result['financial']['context']
    assert '未核查' in result['valuation']['value']


def test_first_answers_never_use_another_tickers_prices_or_an_identity_conflict():
    prices = price_view()
    prices['ticker'] = 'OTHER'
    result = _answers(prices=prices)
    assert result['price']['value'] == '收盘价待核对'
    result = _answers(peer=_peer(3), expected_cik='0000009999')
    assert all('身份冲突' in card['context'] for card in result.values())


def test_quarter_change_requires_a_comparable_prior_year_direct_period():
    from tests.test_sec_quarterly_history import _build, _quarter_payload, _wrapped

    no_baseline = _answers(financial=_wrapped(_build()))['financial']
    assert '可比变化待核对' in no_baseline['context']
    payload = _quarter_payload()
    revenue = payload['facts']['us-gaap']['Revenues']['units']['USD']
    revenue.append(dict(revenue[2], start='2024-07-01', end='2024-09-30', val=125))
    paired = _answers(financial=_wrapped(_build(payload)))['financial']
    assert '较上年同期增加' in paired['context']
    assert '对照期截至 2024-09-30' in ' '.join(paired['evidence'])
    assert '%' not in paired['context']


def test_comparison_with_too_few_or_mixed_price_dates_stays_withheld():
    two = _answers(peer=_peer(2, status='withheld'))['valuation']
    assert '暂无法比较' in two['value']
    assert '4 家已核查' in two['context'] and '2 家合格' in two['context']
    assert '20.0×' not in str(two)
    peer = _peer(3)
    good = _answers(peer=peer)['valuation']
    assert '高于同行参照 20.0%' in good['value']
    changed = deepcopy(peer)
    changed['peers'][0]['price_date'] = '2026-10-28'
    assert '暂无法比较' in _answers(peer=changed)['valuation']['value']


def test_render_has_three_native_disclosures_and_escapes_untrusted_values():
    from src.company_answer_summary import company_answers_html

    answers = _answers()
    answers['price'].update(value='<script>bad</script>', links=(('bad', 'javascript:alert(1)'),))
    html = company_answers_html(tuple(answers.values()))
    assert html.count('<details>') == 3
    assert '<script>' not in html and 'javascript:' not in html
    assert 'data-company-answer="financial"' in html
