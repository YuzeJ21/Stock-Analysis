"""Separate historical EUR-to-USD worksheet; never a valuation denominator."""
from decimal import Decimal
from io import BytesIO
import json
import re
from zipfile import ZIP_DEFLATED, ZipFile

from src.company_sec_online_preview import _utc_timestamp
from src.ecb_fx_reference import parse_ecb_usd, _utc, _stamp, ATTRIBUTION, URL
from src.online_peer_valuation import normalized_digest
from src.sap_price_basis import assess_sap_price_basis
from src.sec_sap_snapshot_evidence import saved_sap_numeric_observation_indices
from src.online_research_context_store import _scope
from src.workspace_authorization import protected_workspace_mode


def build_sap_fx_review(context, capture, *, reviewed_at):
    """Revalidate source bytes and preserve original versus later observations."""
    held = dict(schema_version='sap-historical-currency-review-v1', status='withheld',
        reason='historical_currency_basis_unverified', valuation_eligible=False,
        commercial_eligible=False, point_in_time_eligible=False)
    try:
        _scope(context.get('profile_key'), context.get('ticker'), context.get('sec_cik'))
        revision = context.get('source_revision')
        if not isinstance(revision, str) or re.fullmatch(r'[0-9a-f]{64}', revision) is None:
            return held
        basis = assess_sap_price_basis(context)
        if basis['status'] != 'matched_listing_context' or capture.get('status') != 'captured':
            return held
        review_time = _utc(reviewed_at)
        original_time = _utc_timestamp(context['observed_at'])
        supplied = capture['receipt']
        transport = capture['transport']
        if (not isinstance(transport, dict) or set(transport) != {'source_url','observed_at','last_modified'}
                or transport['source_url'] != URL):
            return held
        observation = _utc_timestamp(transport['observed_at'])
        if not original_time or not observation or max(original_time, observation) > review_time:
            return held
        verified = parse_ecb_usd(capture['xml'], reference_date=basis['price_date'],
            observed_at=observation, last_modified=transport['last_modified'])
        if (verified != supplied or any(type(verified[key]) is not type(supplied[key]) for key in verified)):
            return held
        scope = context['peer_read_through']['subject_source_context']['selected_security_scope']
        indices = saved_sap_numeric_observation_indices(scope, context=context)
        if indices != (2,):
            return held
        native = scope['evidence_observations'][indices[0]]
        amount = Decimal(native['raw_text']) * Decimal(verified['rate_literal'])
        return dict(held, status='derived_historical_translation', reason=None,
            method='price-date-ecb-reference-v1', ticker='SAP',
            original_context_digest=normalized_digest(context), source_revision=context['source_revision'],
            original_observed_at=context['observed_at'], price_date=basis['price_date'],
            reviewed_at=_stamp(review_time),
            fx_observed_at=verified['observed_at'],
            observation_after_original_cutoff=observation > original_time,
            first_publication_status='unverified',
            native_amount_decimal=native['raw_text'], native_unit='EUR/ordinary_share',
            native_source_ref=native['source_ref'], period_start=native['period_start'], period_end=native['period_end'],
            rate_literal=verified['rate_literal'], fx_source_ref=verified['source_url'],
            fx_payload_sha256=verified['payload_sha256'],
            derived_amount_decimal=format(amount, 'f'), unit='USD/ordinary_share',
            boundary='Derived translation of rounded filed ordinary-share EPS using the price-date informational reference. '
                     'Not reported USD EPS, an ADS/ADR mapping, accounting translation, valuation denominator, '
                     'peer comparison, transaction rate or point-in-time availability proof.')
    except (KeyError, TypeError, ValueError, AttributeError, ArithmeticError):
        return held


def currency_review_zip(context, capture, *, reviewed_at):
    """Export only the public source and minimal review, never the private context."""
    if protected_workspace_mode():
        raise ValueError('Protected currency export requires an authorized delivery path')
    review = build_sap_fx_review(context, capture, reviewed_at=reviewed_at)
    if review['status'] != 'derived_historical_translation':
        raise ValueError('Currency review is withheld')
    buffer = BytesIO()
    with ZipFile(buffer, 'w', compression=ZIP_DEFLATED) as archive:
        archive.writestr('fx.xml', capture['xml'])
        archive.writestr('receipt.json', json.dumps({key:capture[key] for key in
            ('status','receipt','transport')}, indent=2) + '\n')
        archive.writestr('SOURCE.txt', ATTRIBUTION)
        archive.writestr('review.json', json.dumps(review, indent=2) + '\n')
    return buffer.getvalue()
