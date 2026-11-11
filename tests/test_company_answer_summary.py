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
    assert result['financial']['value'] == 'Revenue USD 150'
    assert 'Revenue increased vs prior fiscal year' in result['financial']['context']
    assert result['financial']['headline'] == 'Revenue up 25.0%'
    assert '2025-12-31' in result['financial']['context']
    assert any(line.startswith('Filed ') for line in result['financial']['evidence'])
    assert any(label == 'SEC filing index' and url.endswith('-index.htm') for label, url in result['financial']['links'])
    assert 'not checked' in result['valuation']['value']


def test_exact_annual_headline_can_use_compatible_operating_income_and_keep_revenue_gap():
    from src.company_answer_summary import _financial_answer

    ref = 'https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/fict.htm'
    prior = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json'
    projection = dict(period_start='2025-01-01', period_end='2025-12-31', period_kind='annual',
        facts={'revenue': dict(unit='TWD', value=2_000_000_000, taxonomy='ifrs-full',
                               concept='RevenueFromContractsWithCustomers',
                               reported_numeric_schema='sec-reported-numeric-v1', source_ref=ref),
               'operating_income': dict(unit='TWD', value=500_000_000)},
        comparative=dict(field='operating_income', value=400_000_000, current_value=500_000_000,
                         period_end='2024-12-31', source_ref=prior))
    answer = _financial_answer(projection, {'sec_cik': '0000001234'})
    assert answer['headline'] == 'Operating income up 25.0%'
    assert 'Revenue TWD 2.00B' in answer['headline_context']
    assert 'Revenue comparison needs verification' == answer['gap']
    assert ('Prior operating income source', prior) in answer['links']
    assert ('Exact SEC filing fact', ref) in answer['links']
    assert any('Comparison period ended 2024-12-31' in line and '400,000,000' in line
               for line in answer['evidence'])

    projection.pop('comparative')
    held = _financial_answer(projection, {'sec_cik': '0000001234'})
    assert 'headline' not in held
    assert held['gap'] == 'Comparable financial change needs verification'


def test_first_answers_never_use_another_tickers_prices_or_an_identity_conflict():
    prices = price_view()
    prices['ticker'] = 'OTHER'
    result = _answers(prices=prices)
    assert result['price']['value'] == 'Close needs verification'
    result = _answers(peer=_peer(3), expected_cik='0000009999')
    assert all('identity conflicts' in card['context'] for card in result.values())


def test_stale_close_and_unrequested_financials_are_labelled_separately():
    prices = price_view()
    prices['observation_state'] = 'stale_observation'
    cards = _answers(prices=prices, financial={'ticker': 'FICT', 'status': 'not_requested'})
    assert 'Stale date' in cards['price']['context']
    assert '2026-10-29' in cards['price']['context']
    assert 'Financials have not been requested' in cards['financial']['context']
    assert 'have been requested' not in cards['financial']['context']


def test_quarter_change_requires_a_comparable_prior_year_direct_period():
    from tests.test_sec_quarterly_history import _build, _quarter_payload, _wrapped

    no_baseline = _answers(financial=_wrapped(_build()))['financial']
    assert 'Comparable change needs verification' in no_baseline['context']
    payload = _quarter_payload()
    revenue = payload['facts']['us-gaap']['Revenues']['units']['USD']
    revenue.append(dict(revenue[2], start='2024-07-01', end='2024-09-30', val=125))
    paired = _answers(financial=_wrapped(_build(payload)))['financial']
    assert 'Revenue increased vs prior-year quarter' in paired['context']
    assert 'Comparison period ended 2024-09-30' in ' '.join(paired['evidence'])
    assert '%' not in paired['context']


def test_comparison_with_too_few_or_mixed_price_dates_stays_withheld():
    two = _answers(peer=_peer(2, status='withheld'))['valuation']
    assert 'Peer comparison unavailable' in two['value']
    assert '4 candidates checked' in two['context'] and '2 eligible references' in two['context']
    assert 'at least 3' in two['context'].lower()
    assert '20.0×' not in str(two)
    peer = _peer(3)
    peer['peers'][0]['price_source_ref'] = 'https://query1.finance.yahoo.com/v8/finance/chart/F0'
    good = _answers(peer=peer)['valuation']
    assert 'Annual P/E 20.0% above industry references' in good['value']
    assert ('F0 Daily price source', peer['peers'][0]['price_source_ref']) in good['links']
    changed = deepcopy(peer)
    changed['peers'][0]['price_date'] = '2026-10-28'
    assert 'Peer comparison unavailable' in _answers(peer=changed)['valuation']['value']


def test_valuation_gap_keeps_annual_filing_sources_when_subject_is_blocked():
    peer = _peer(0, status='withheld')
    peer.update(subject=None, reason='quote_not_same_recent_completed_day', checked_candidate_count=0)
    filing_url = 'https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/fict.htm'
    directory_url = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
    peer['subject_source_context'] = {'annual_versions': [{
        'form': '10-K', 'period_end': '2025-12-31', 'filed': '2026-02-04', 'source_ref': filing_url,
    }]}
    peer['listing_context'] = {'source_attempts': [{'source_url': directory_url}]}
    card = _answers(peer=peer)['valuation']
    assert 'The quote is not from the same recent completed trading day' in card['context']
    assert 'Company evidence is unverified. Industry references have not been checked.' in card['evidence']
    assert ('Company 10-K (filing record)', filing_url) in card['links']
    assert ('Listing source request', directory_url) not in card['links']
    peer['reason'] = 'listing_classification_unavailable'
    assert ('Listing source request', directory_url) in _answers(peer=peer)['valuation']['links']


def test_valuation_lists_every_exclusion_and_its_available_source():
    peer = _peer(2, status='withheld')
    peer.pop('checked_candidate_count')
    filing_url = 'https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/peer.htm'
    price_url = 'https://query1.finance.yahoo.com/v8/finance/chart/F2'
    peer['excluded'] = [
        {'ticker': 'F2', 'reason': 'duplicate_peer_issuer', 'diagnostics': {
            'annual_eps_observation': {'filing_ref': filing_url},
            'price_observation': {'source_ref': price_url},
        }},
        {'ticker': 'F3', 'reason': 'future_unmapped_reason'},
    ]
    card = _answers(peer=peer)['valuation']
    assert '2 eligible references' in card['context']
    assert any(line.startswith('F2 · This security has the same issuer as an included reference.') for line in card['evidence'])
    assert any(line.startswith('F3 · Source, identity, or field evidence could not be verified.') for line in card['evidence'])
    assert ('F2 Annual filing (excluded)', filing_url) in card['links']
    assert ('F2 Daily price source (excluded)', price_url) in card['links']


def test_render_has_three_native_disclosures_and_escapes_untrusted_values():
    from src.company_answer_summary import company_answers_html

    answers = _answers()
    answers['price'].update(value='<script>bad</script>', links=(('bad', 'javascript:alert(1)'),))
    html = company_answers_html(tuple(answers.values()))
    assert html.count('<details>') == 3
    assert '<script>' not in html and 'javascript:' not in html
    assert 'data-company-answer="financial"' in html
    assert 'aria-label="View financial changes evidence">View evidence</summary>' in html


def test_compact_context_preserves_loaded_dates_staleness_and_escaped_sources():
    from src.company_answer_summary import company_answers_html

    prices = price_view()
    prices['observation_state'] = 'stale_observation'
    answers = _answers(prices=prices, peer=_peer(3))
    rendered = company_answers_html(tuple(answers.values()), compact=True)
    assert 'aria-label="Loaded company observations"' in rendered
    assert 'USD 11.00' in rendered and '2026-10-29' in rendered and 'Stale date' in rendered
    assert '2025-12-31' in rendered and '3 eligible references' in rendered
    assert '<article' not in rendered and '<details' not in rendered
    assert 'data-company-answer=' not in rendered
    assert 'Revenue USD 150' not in rendered
    assert prices['source_url'].replace('&', '&amp;') in rendered
    answers['price'].update(value='<script>bad</script>', links=(('unsafe', 'javascript:alert(1)'),))
    unsafe = company_answers_html((answers['price'],), compact=True)
    assert '<script>' not in unsafe and 'javascript:' not in unsafe


def test_english_amount_scaling_keeps_the_unscaled_source_value_in_evidence():
    financial = financial_view()
    latest = financial['annual_history']['periods'][-1]
    revenue = next(field for field in latest['fields'] if field['field'] == 'revenue')
    revenue['value'] = 2_750_000_000
    latest['revenue'] = revenue['value']
    answer = _answers(financial=financial)['financial']
    assert answer['value'] == 'Revenue USD 2.75B'
    assert any('USD 2,750,000,000' in line for line in answer['evidence'])
