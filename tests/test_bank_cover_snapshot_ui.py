"""Display every parsed cover value without confusing literal issuer symbols."""
from src.online_peer_valuation_ui import _selected_security_html


def test_versioned_cover_observations_display_literal_values_and_all_context():
    value=dict(status='supported_common',issuer_symbols=['JPM','JPM-PC'],documents=[dict(
        role='annual',cover_observation_schema='sec-cover-observations-v1',
        cover_observations=[dict(trading_symbol='JPM PR C',title='Preferred <literal> title',
            exchange='New York Stock Exchange',context_id='cover-42')])])
    html=_selected_security_html(value)
    assert 'JPM PR C' in html
    assert 'Preferred &lt;literal&gt; title' in html and '<literal>' not in html
    assert 'New York Stock Exchange' in html and 'cover-42' in html


def test_prior_live_cover_format_keeps_read_only_display_compatibility():
    value=dict(status='supported_common',issuer_symbols=['JPM'],documents=[dict(role='annual',
        raw_cover_observations=[dict(raw_symbol='JPM/32',title='Dated observation',
            exchange='NYSE',context_id='old-context')])])
    html=_selected_security_html(value)
    assert 'JPM/32' in html and 'Dated observation' in html
