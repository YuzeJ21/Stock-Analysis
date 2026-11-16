from src import sec_online_quarter_view as view


def test_ase_net_payments_keep_gross_withheld_and_durations_visible():
    direct = dict(unit='TWD', reported_text='(125)', scale=6, period_start='2026-07-01',
                  period_end='2026-09-30', column_header='September 30 2026')
    ytd = dict(direct, reported_text='(250)', period_start='2026-01-01',
               column_header='September 30 2026 (Retrospectively Adjusted)')

    rendered = view.ase_net_ppe_html({'quarterly': direct, 'cumulative': ytd})
    assert 'Gross PP&amp;E cash purchases · Withheld' in rendered
    assert 'Direct quarter · 2026-07-01 to 2026-09-30' in rendered
    assert 'TWD (125) million' in rendered
    assert 'Year to date · 2026-01-01 to 2026-09-30 · Retrospectively adjusted' in rendered
    assert 'TWD (250) million' in rendered
    assert 'Equipment capex' in rendered and 'dp255782_6k.htm' in rendered
    assert 'd174900d6k.htm' in rendered and 'dp256592_6k.htm' in rendered
    assert 'TWSE reporting-basis review' in rendered and 'Gross Q3 PP&amp;E · Withheld' in rendered
    assert 'June TWSE filings' in rendered and 'seamon=2' in rendered
    assert 'September TWSE filings' in rendered and 'seamon=3' in rendered
    assert 'no restated June gross payment and disposal cash lines' in rendered
    assert 'Restated June search · November 16, 2026' in rendered
    assert 'no ASE entry for either quarter' in rendered
    assert 'MOPS financial-report corrections' in rendered and 't56sb31_q1' in rendered
    assert 'MOPS consolidated cash flow' in rendered and 't164sb05' in rendered
    assert 'Year to date' not in view.ase_net_ppe_html({'quarterly': direct})
