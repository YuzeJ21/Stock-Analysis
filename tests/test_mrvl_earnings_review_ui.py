"""Constructed presentation data, not MRVL financial observations."""
from copy import deepcopy


def review():
    filing = dict(accession='0001835632-26-000011', form='10-K', filed='2026-03-11',
                  period_start='2025-02-02', period_end='2026-01-31',
                  source_url='https://www.sec.gov/Archives/edgar/data/1835632/000183563226000011/mrvl-20260131.htm')
    peer = dict(accession='0001730168-25-000121', form='10-K', filed='2025-12-18',
                period_start='2024-11-04', period_end='2025-11-02',
                source_url='https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm')
    fields = []
    for field, concept, value, unit in (
        ('diluted_eps', 'EarningsPerShareDiluted', 2.5, 'USD/shares'),
        ('net_income', 'NetIncomeLoss', 250_000_000, 'USD'),
        ('cash_from_operations', 'NetCashProvidedByUsedInOperatingActivities', 180_000_000, 'USD'),
        ('capital_expenditures', 'PaymentsToAcquirePropertyPlantAndEquipment', 30_000_000, 'USD'),
        ('share_based_compensation', 'ShareBasedCompensation', 20_000_000, 'USD'),
        ('amortization_of_intangibles', 'AmortizationOfIntangibleAssets', 40_000_000, 'USD'),
        ('gain_on_sale_of_business', 'GainLossOnSaleOfBusiness', 75_000_000, 'USD'),
    ):
        fields.append(dict(field=field, concept=concept, taxonomy='us-gaap', value=value, unit=unit,
                           status='available', reason=None, **filing,
                           observed_at='2026-11-07T18:00:00Z', payload_sha256='a'*64,
                           source_ref='https://data.sec.gov/api/xbrl/companyfacts/CIK0001835632.json'))
    return dict(status='inspection_only', ticker='MRVL', sec_cik='0001835632',
                rights_status='unregistered_sec_financial_quality_personal_inspection_only',
                quality=dict(status='inspection_only', reason=None, filing=filing, fields=fields,
                             flags=['disposal_gain_affects_reported_earnings',
                                    'operating_cash_flow_differs_from_net_income',
                                    'share_based_compensation_requires_care', 'amortization_requires_care'],
                             gaps=['adjusted_after_tax_reconciliation_unresolved', 'latest_quarter_outside_annual_review']),
                peer_context=dict(status='research_context', reason='peer_fiscal_window_differs',
                                  subject_filing=filing, peer_filing=peer, relationship_supported=True,
                                  business_mix_difference=True, period_end_gap_days=90,
                                  fiscal_window_days=35, numerical_admission='not_granted'),
                source_refs=[dict(source_url=filing['source_url'], observed_at='2026-11-07T18:00:00Z',
                                  payload_sha256='b'*64)])


def test_annual_quality_explains_sale_gain_without_manufacturing_adjusted_earnings():
    from src.mrvl_earnings_review_ui import _review_html
    result = review(); before = deepcopy(result)
    html = _review_html(result)
    assert 'Earnings quality behind annual P/E' in html
    assert 'business-sale gain' in html and 'pre-tax' in html
    assert 'after-tax reconciliation' in html
    assert 'not recurring-earnings valuation' in html
    assert all(field['concept'] in html for field in result['quality']['fields'])
    assert 'USD/shares' in html and '2025-02-02' in html and '2026-01-31' in html
    assert '2026-03-11' in html and 'a'*64 in html
    assert 'Personal Research inspection only' in html
    assert 'No adjusted EPS or additional multiple is calculated' in html
    assert result == before


def test_named_peer_relevance_and_calendar_exclusion_are_both_explained():
    from src.mrvl_earnings_review_ui import _review_html
    html = _review_html(review())
    assert 'Broadcom' in html and 'direct competitor' in html
    assert 'infrastructure software' in html and 'business mix' in html
    assert '90 days' in html and '35-day' in html
    assert '2025-11-02' in html and '2026-01-31' in html
    assert 'does not admit AVGO' in html
    assert 'same-day completed prices' in html and '3 qualified' in html


def test_one_component_gap_does_not_hide_other_fields_or_become_zero():
    from src.mrvl_earnings_review_ui import _review_html
    result = review(); result['quality']['status'] = 'partial'
    field = result['quality']['fields'][2]
    field.update(status='withheld', value=None, reason='annual_component_period_mismatch')
    html = _review_html(result)
    assert 'Operating cash flow' in html and 'Withheld' in html
    assert 'period' in html.lower() and '250.0M' in html
    assert 'USD 0' not in html


def test_negative_and_zero_observations_are_preserved_as_reported_values():
    from src.mrvl_earnings_review_ui import _review_html
    result = review()
    result['quality']['fields'][0]['value'] = -0.5
    result['quality']['fields'][3]['value'] = 0
    html = _review_html(result)
    assert 'non-positive' in html and 'USD -0.5' in html
    assert 'USD 0' in html and 'Recurring EPS: USD' not in html


def test_sources_mode_retains_actual_definitions_and_safe_links_with_no_valuation_claim():
    from src.mrvl_earnings_review_ui import _review_html
    result = review()
    result['source_refs'][0]['source_url'] = 'javascript:alert(1)'
    result['quality']['fields'][1]['source_ref'] = 'https://www.sec.gov.evil.test/data'
    html = _review_html(result, sources_only=True)
    assert 'MRVL earnings review sources' in html and '0001835632-26-000011' in html
    assert 'NetIncomeLoss' in html and 'observed' in html.lower()
    assert 'javascript:' not in html and 'evil.test' not in html
    assert 'b'*64 in html and 'commercial approval' in html


def test_incomplete_relationship_and_unknown_reason_stay_visible_without_fake_support():
    from src.mrvl_earnings_review_ui import _review_html
    result = review()
    result['peer_context'].update(status='withheld', reason='source_component_unavailable',
                                  relationship_supported=False, business_mix_difference=False)
    html = _review_html(result)
    assert 'AVGO comparison context remains incomplete' in html
    assert 'Source evidence' in html
    assert 'direct competitor' not in html and 'infrastructure software' not in html


def test_non_mrvl_page_does_not_receive_company_specific_explanation():
    from src.mrvl_earnings_review_ui import mrvl_earnings_review_html
    assert mrvl_earnings_review_html({'ticker':'AMD','status':'inspection_only'}) == ''


def test_gap_text_names_the_component_and_specific_unmet_source_requirement():
    from src.mrvl_earnings_review_ui import _reason
    text = _reason('cash_from_operations_review_exact_annual_fact_missing')
    assert 'Operating cash flow' in text and 'annual interval' in text
    assert 'changed' in _reason('avgo_review_latest_annual_scope_unreviewed')
    assert 'AVGO' in _reason('avgo_review_latest_annual_scope_unreviewed')


def test_small_values_are_not_displayed_as_zero_and_source_value_keeps_precision():
    from src.mrvl_earnings_review_ui import _amount
    assert _amount(dict(status='available', value=0.000001, unit='USD/shares')) != 'USD 0'
    assert '1,234,567,890,123' in _amount(dict(status='available', value=1234567890123, unit='USD'), exact=True)


def test_validated_annual_caution_links_to_evidence_and_holds_an_identity_conflict():
    from src.mrvl_earnings_review_ui import mrvl_earnings_caution_html
    from tests.test_mrvl_earnings_review import packet, financial_view, NOW
    view = financial_view(packet()); before = deepcopy(view)
    html = mrvl_earnings_caution_html(view, expected_cik='0001835632', as_of=NOW)
    assert 'business-sale gain' in html and 'View earnings basis' in html
    assert 'href="#mrvl-earnings-review"' in html
    held = mrvl_earnings_caution_html(view, expected_cik='0001730168', as_of=NOW)
    assert 'source gaps' in held and 'business-sale gain' not in held
    assert view == before


def after_tax_review():
    """Constructed presentation fixture, independently different from live data."""
    result = review()
    url = 'https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/q426_8kx1312026ex-991.htm'
    components = []
    for field, label, value, unit, scale in (
        ('gaap_net_income', 'GAAP net income (loss)', 250_000_000, 'USD', 1_000_000),
        ('pretax_special_items_total', 'Pre-tax total special items', 30_000_000, 'USD', 1_000_000),
        ('tax_effects', 'Other income tax effects and adjustments (d)', -5_000_000, 'USD', 1_000_000),
        ('issuer_non_gaap_net_income', 'Non-GAAP net income', 275_000_000, 'USD', 1_000_000),
        ('gaap_diluted_shares', 'GAAP weighted-average shares — diluted', 100_000_000, 'shares', 1_000_000),
        ('issuer_non_gaap_diluted_eps', 'Non-GAAP diluted net income per share', 2.75, 'USD/shares', 1),
    ):
        components.append(dict(field=field, label=label, value=value, unit=unit, scale=scale,
            source_value=str(value/scale), raw_text=str(value/scale), source_ref=url,
            observed_at='2026-11-07T18:00:00Z', payload_sha256='c'*64,
            table_index=3, row_index=len(components)+10, column_span=[24,27]))
    result['quality']['after_tax_reconciliation'] = dict(status='verified_issuer_reconciliation', reason=None,
        basis='issuer_reported_non_gaap', components=components,
        filing=dict(accession='0001835632-26-000006', form='8-K', filed='2026-03-05',
                    primary_url=url.replace('q426_8kx1312026ex-991.htm','mrvl-20260305.htm'), exhibit_url=url),
        annual_period=dict(period_start='2025-02-02', period_end='2026-01-31'),
        checks=dict(pretax_components_residual_usd=0, net_income_residual_usd=0,
                    gaap_eps={'passed':True}, issuer_non_gaap_eps={'passed':True}),
        gaps=['sale_specific_tax_allocation_unavailable','item_specific_after_tax_eps_unavailable',
              'normalized_earnings_not_qualified','adjusted_valuation_denominator_not_qualified'],
        source_refs=[dict(source_url=url, observed_at='2026-11-07T18:00:00Z',payload_sha256='c'*64)])
    result['quality']['gaps'] = ['latest_quarter_outside_annual_review']
    return result


def test_verified_issuer_bridge_is_distinct_from_normalized_earnings_and_keeps_signed_tax():
    from src.mrvl_earnings_review_ui import _review_html
    result = after_tax_review(); before = deepcopy(result)
    html = _review_html(result)
    assert 'Issuer after-tax reconciliation — verified' in html
    assert 'USD 275.0M' in html and 'USD -5.0M' in html and 'USD 2.75' in html
    assert '100.0M shares' in html and 'Year ended 2026-01-31' in html
    assert 'furnished' in html.lower() and '0001835632-26-000006' in html
    assert 'source column' in html.lower() and 'c'*64 in html
    assert 'gain alone' in html and 'not recurring or normalized earnings' in html
    assert 'An adjusted after-tax reconciliation remains unresolved' not in html
    assert 'before recurring or issuer-adjusted earnings can support another method' not in html
    assert 'No adjusted EPS or additional multiple is calculated' not in html
    assert result == before


def test_failed_issuer_bridge_drops_its_numbers_and_explains_local_source_gap():
    from src.mrvl_earnings_review_ui import _review_html
    result = after_tax_review()
    result['quality']['after_tax_reconciliation'].update(status='withheld', reason='reconciliation_exhibit_unavailable')
    html = _review_html(result)
    assert 'Issuer after-tax reconciliation — withheld' in html
    assert 'earnings exhibit was unavailable' in html
    assert 'USD 275.0M' not in html and 'USD 2.75' not in html
    assert 'USD 250.0M' in html and 'direct competitor' in html


def test_source_mode_reuses_exact_bridge_and_escapes_untrusted_metadata():
    from src.mrvl_earnings_review_ui import _review_html
    result = after_tax_review()
    result['quality']['after_tax_reconciliation']['components'][0]['label'] = '<script>unsafe</script>'
    html = _review_html(result, sources_only=True)
    assert 'MRVL earnings review sources' in html and 'Issuer after-tax reconciliation — verified' in html
    assert '<script>unsafe</script>' not in html and '&lt;script&gt;unsafe&lt;/script&gt;' in html
    assert 'Personal Research inspection only' in html


def test_actual_builder_output_preserves_millions_in_the_rendered_share_count():
    from src.mrvl_earnings_review_ui import _review_html
    from src.mrvl_earnings_review import build_mrvl_earnings_review
    from tests.test_mrvl_after_tax_review_integration import qualified_packet, NOW
    result = build_mrvl_earnings_review(qualified_packet(), as_of=NOW)
    assert result['quality']['after_tax_reconciliation']['status'] == 'verified_issuer_reconciliation'
    html = _review_html(result)
    assert '100.0M shares' in html and '>100.0 shares<' not in html
    assert 'source scale 1000000' in html and 'USD 1.76' in html


def test_bridge_money_keeps_original_millions_precision_for_readable_arithmetic():
    from src.mrvl_earnings_review_ui import _after_tax_html
    r = after_tax_review()['quality']['after_tax_reconciliation']
    for row in r['components']:
        if row['field'] == 'gaap_net_income':
            row.update(value=1_234_500_000, source_value='1234.5')
        elif row['field'] == 'issuer_non_gaap_net_income':
            row.update(value=1_340_600_000, source_value='1340.6')
    html = _after_tax_html(r)
    assert 'USD 1,234.5M' in html and 'USD 1,340.6M' in html
    assert 'USD 1.23B' not in html and 'USD 1.34B' not in html
