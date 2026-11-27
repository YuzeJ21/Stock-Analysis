"""Explicit, separate currency review; never mutates an original research context."""
from datetime import datetime, timezone
from html import escape

from src.ecb_fx_reference import capture_ecb_usd, _utc
from src.online_company_identity import _mode_reason
from src.online_peer_valuation import normalized_digest
from src.sap_price_basis import assess_sap_price_basis
from src.sap_fx_review import build_sap_fx_review, currency_review_zip
from src.workspace_authorization import protected_workspace_mode

STATE_KEY = 'sap_currency_review_v1'


def render_sap_fx_review(st, context, *, fetcher=None, clock=None):
    if context.get('ticker') != 'SAP':
        return
    if _mode_reason('research'):
        st.caption('Personal currency review is unavailable in this workspace.')
        return
    try:
        fingerprint = normalized_digest(context)
    except (ValueError, TypeError):
        return
    basis = assess_sap_price_basis(context)
    now = clock or (lambda:datetime.now(timezone.utc))
    with st.expander('Currency conversion review', expanded=False):
        st.caption('Starts a separate historical review using an ECB informational reference. '
                   'It does not refresh, rewrite or add FX to the original saved research.')
        if basis['status'] != 'matched_listing_context':
            st.caption('A matched dated SAP listing/price context is required before fetching FX.')
        if st.button('Fetch FX reference', key='sap-fx-fetch:' + fingerprint,
                     disabled=basis['status'] != 'matched_listing_context'):
            capture = capture_ecb_usd(basis['price_date'], fetcher=fetcher, clock=now)
            st.session_state[STATE_KEY] = dict(context_digest=fingerprint, capture=capture, reviewed_at=_utc(now()))
        cached = st.session_state.get(STATE_KEY)
        if not isinstance(cached, dict) or cached.get('context_digest') != fingerprint:
            return
        review = build_sap_fx_review(context, cached.get('capture'), reviewed_at=cached.get('reviewed_at'))
        if review['status'] != 'derived_historical_translation':
            st.warning('FX reference or historical currency basis could not be verified. No currency amount was produced.')
            return
        text = lambda value:escape(str(value), quote=True)
        html = ('<section aria-label="Historical currency translation"><h3>Historical currency translation</h3>'
            '<p><strong>' + text(review['derived_amount_decimal']) + ' USD/ordinary share</strong> · derived</p>'
            '<p>' + text(review['native_amount_decimal']) + ' EUR/ordinary share × '
            + text(review['rate_literal']) + ' USD per EUR · reference date ' + text(review['price_date']) + '.</p>'
            '<p>Original research observed ' + text(review['original_observed_at']) + '. FX retrieved '
            + text(review['fx_observed_at']) + '. Review ' + text(review['reviewed_at']) + '.</p>'
            '<p>First publication and point-in-time availability remain unverified. A later retrieval does not establish '
            'availability at the original cutoff. Extra decimal places are arithmetic on rounded filed EPS.</p>'
            '<p>This is not reported USD EPS, EPS per ADS/ADR, a valuation denominator or a peer comparison. '
            'Valuation, accounting comparability and commercial permissions remain withheld.</p>'
            '<p><a href="' + text(review['native_source_ref']) + '" target="_blank" rel="noopener noreferrer">Native filing fact</a> · '
            '<a href="' + text(review['fx_source_ref']) + '" target="_blank" rel="noopener noreferrer">European Central Bank source</a>'
            '</p></section>')
        st.markdown(html, unsafe_allow_html=True)
        if protected_workspace_mode():
            st.caption('Currency review export requires an authorized delivery path for this workspace.')
            return
        package = currency_review_zip(context, cached['capture'], reviewed_at=cached['reviewed_at'])
        st.download_button('Download currency review', package, 'SAP-historical-currency-review.zip',
                           mime='application/zip', key='sap-fx-download:' + fingerprint)
