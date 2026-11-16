"""NEE's capital-investment definition remains separate from generic capex."""
from src import sec_online_quarter_view


def test_capital_investment_panel_names_its_duration_and_pp_e_gap():
    url = 'https://www.sec.gov/Archives/edgar/data/753308/000000123426000001/constructed.htm'
    packet = dict(period_start='2026-01-01', period_end='2026-09-30', source_url=url,
                  filed='2026-10-22', accession='0000001234-26-000001', observed_at='2026-11-11T22:00:00Z',
                  fields={
                      'reported_capital_investment_total': dict(value=500_000_000, unit='USD',
                          label='Capital expenditures, independent power and other investments and nuclear fuel purchases',
                          presentation='reported_total', statement='segment_disclosure', source_ref=url+'#total', fact_id='total'),
                      'fpl_capital_expenditures': dict(value=120_000_000, unit='USD', label='Capital expenditures of FPL',
                          presentation='cash_outflow', statement='consolidated_cash_flows', source_ref=url+'#fpl', fact_id='fpl'),
                  })
    html = sec_online_quarter_view.capital_purchase_html(packet)
    assert 'Year-to-date capital investments' in html and '2026-01-01 to 2026-09-30' in html
    assert 'USD 500,000,000' in html and 'USD 120,000,000' in html
    assert 'Consolidated PP&amp;E purchases need verification' in html
    assert 'Quarterly cash flow and capital purchases need direct-quarter evidence' in html
    assert url+'#total' in html and url+'#fpl' in html
    assert 'SEC review · November 16, 2026' not in html

    exact_url = 'https://www.sec.gov/Archives/edgar/data/753308/000075330826000081/nee-20260930.htm'
    reviewed_html = sec_online_quarter_view.capital_purchase_html(dict(packet, source_url=exact_url,
        accession='0000753308-26-000081', filed='2026-10-21'))
    assert 'Consolidated gross PP&amp;E purchases' in reviewed_html
    assert 'July–September 2026 · Withheld' in reviewed_html
    assert 'January–September 2026 · Withheld' in reviewed_html
    assert 'nee-20260630.htm' in reviewed_html and exact_url in reviewed_html
    assert 'neeq32026exhibit99.htm' in reviewed_html
    assert 'SEC review · November 16, 2026' in reviewed_html
    assert 'filed July 24, 2026' in reviewed_html and 'filed October 21, 2026' in reviewed_html
    assert 'furnished October 21, 2026' in reviewed_html
    assert 'Directly reported quarterly operating cash flow remains unavailable in this panel' in reviewed_html
    assert 'accrued property additions under noncash' in reviewed_html
    assert not sec_online_quarter_view.nee_gross_ppe_review_html(dict(packet, source_url=exact_url))
