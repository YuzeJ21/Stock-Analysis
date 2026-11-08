"""Compact personal-research explanation; source validation owns every observation."""
from collections.abc import Mapping
from html import escape
import math
from urllib.parse import urlsplit

from src.online_peer_valuation_ui import STYLE


LABELS = {
    'diluted_eps': 'Reported diluted EPS',
    'net_income': 'Reported net income',
    'cash_from_operations': 'Operating cash flow',
    'capital_expenditures': 'Purchases of property, plant and equipment',
    'share_based_compensation': 'Share-based compensation',
    'amortization_of_intangibles': 'Amortization of intangible assets',
    'gain_on_sale_of_business': 'Reported business-sale gain',
}
REASONS = {
    'annual_component_period_mismatch': 'The observation does not match the exact annual interval.',
    'annual_component_missing': 'No matching observation was found in this annual filing.',
    'annual_component_unit_conflict': 'The observation has conflicting units or currencies.',
    'annual_component_conflict': 'The filing contains conflicting observations for this component.',
    'adjusted_after_tax_reconciliation_unresolved': 'An adjusted after-tax reconciliation remains unresolved.',
    'latest_quarter_outside_annual_review': 'The latest quarter and cumulative cash-flow periods remain separate from this annual review.',
    'peer_fiscal_window_differs': 'The annual periods fall outside the existing fiscal comparison window.',
    'source_observation_stale_or_future': 'The observation is stale or future-dated. Refresh the financial evidence explicitly.',
    'review_exact_annual_fact_missing': 'No fact matched the selected accession, form, publication date and exact annual interval.',
    'review_exact_unit_or_concept_missing': 'The exact reported concept in the required unit was unavailable; no other definition was substituted.',
    'review_fact_schema_invalid': 'The component did not meet the source schema requirements.',
    'review_conflicting_annual_units': 'The same annual observation has conflicting units or currencies.',
    'review_fact_nonfinite_or_invalid': 'The source value is not a finite supported number.',
    'review_conflicting_annual_facts': 'The same annual observation has conflicting reported values.',
    'review_latest_annual_scope_unreviewed': 'The selected annual filing has changed; this named review is not qualified for that version.',
    'review_latest_annual_conflict': 'The latest annual filing version could not be selected unambiguously.',
    'review_current_annual_unavailable': 'A supported current annual filing was unavailable.',
    'review_business_relationship_evidence_missing': 'The required affirmative, visible business disclosure was not verified.',
    'review_document_metadata_unbound': 'The annual document could not be bound to its issuer and reporting context.',
    'review_document_metadata_mismatch': 'The annual document identity or period disagrees with the selected filing.',
    'review_source_stale_or_future': 'The source observation is stale or future-dated. Refresh the financial evidence explicitly.',
    'review_source_unavailable_or_mismatched': 'The required source was unavailable or did not match its exact reference.',
    'review_companyfacts_receipt_mismatch': 'The loaded company facts and review do not match the same issuer and source observation.',
    'review_packet_changed': 'The saved observation changed and could not be revalidated. Refresh explicitly.',
    'review_normalized_payload_changed': 'The source subset no longer matches its recorded digest.',
    'review_annual_fields_incomplete': 'One or more annual components remain withheld; independently verified fields are retained.',
    'review_document_unavailable': 'The exact annual document was unavailable.',
    'review_annual_scope_unavailable': 'The current annual metadata did not match this named evidence scope.',
}


def _text(value):
    return escape(str(value if value is not None else 'Unavailable'))


def _reason(value):
    if value in REASONS:
        return REASONS[value]
    if isinstance(value, str):
        for key, label in [('mrvl', 'MRVL'), ('avgo', 'AVGO'), *LABELS.items()]:
            if value.startswith(key+'_') and value[len(key)+1:] in REASONS:
                return label+': '+REASONS[value[len(key)+1:]]
    return 'Source evidence is unavailable or unverified; this item remains withheld.'


def _link(url, label):
    try:
        parsed = urlsplit(url) if isinstance(url, str) and len(url) <= 2048 else None
        if (parsed and parsed.scheme == 'https' and parsed.hostname in {'www.sec.gov', 'data.sec.gov'}
                and parsed.username is None and parsed.password is None and parsed.port is None):
            return '<a href="'+escape(url, quote=True)+'" target="_blank" rel="noopener noreferrer">'+_text(label)+'</a>'
    except ValueError:
        pass
    return _text(label)+' (link unverified)'


def _number(value):
    return type(value) in {int, float} and math.isfinite(value) and abs(value) <= 1e20


def _amount(row, *, exact=False):
    value = row.get('value')
    if row.get('status') != 'available' or not _number(value):
        return 'Withheld'
    if exact:
        return _text(format(value, ','))+' '+_text(row.get('unit'))
    if row.get('unit') == 'USD/shares':
        if value != 0 and abs(value) < .0001:
            return 'USD '+format(value, '.8g')
        return 'USD '+format(value, ',.4f').rstrip('0').rstrip('.')
    if abs(value) >= 1e9:
        return f'USD {value/1e9:,.2f}B'
    if abs(value) >= 1e6:
        return f'USD {value/1e6:,.1f}M'
    return 'USD '+(format(value, '.8g') if value != 0 and abs(value) < .00000001
                   else format(value, ',.8f').rstrip('0').rstrip('.'))


def _filing_html(filing, label):
    filing = filing if isinstance(filing, Mapping) else {}
    return ('<p><strong>'+_text(label)+'</strong> '+_text(filing.get('period_start'))+' to '
            +_text(filing.get('period_end'))+' · '+_text(filing.get('form'))+' · filed '
            +_text(filing.get('filed'))+' · '+_text(filing.get('accession'))+' · '
            +_link(filing.get('source_url', filing.get('source_ref')), 'SEC filing')+'</p>')


def _field_table(fields):
    rows = []
    for row in fields:
        if not isinstance(row, Mapping) or row.get('field') not in LABELS:
            continue
        meta = '<p>'+_text(_reason(row.get('reason')))+'</p>' if row.get('status') != 'available' else ''
        meta += ('<details><summary>Field evidence</summary><p>'+_text(row.get('taxonomy'))+':'
                 +_text(row.get('concept'))+' · '+_text(row.get('unit'))+'</p><p>Exact value: '
                 +_amount(row, exact=True)+'</p><p>'+_text(row.get('period_start'))+' to '
                 +_text(row.get('period_end'))+' · '+_text(row.get('accession'))+' · '
                 +_text(row.get('form'))+' · filed '+_text(row.get('filed'))+'</p><p>Observed '
                 +_text(row.get('observed_at'))+' · '+_link(row.get('source_ref'), 'SEC Companyfacts')
                 +'</p><p>Original response SHA-256 <code>'+_text(row.get('payload_sha256'))+'</code></p></details>')
        rows.append('<tr><td data-label="Reported item">'+LABELS[row['field']]+'</td>'
                    '<td data-label="Value">'+_amount(row)+'</td><td data-label="Evidence">'+meta+'</td></tr>')
    return ('<table><caption>Annual observations; rounded display values. Exact values and units are in each field’s evidence.</caption>'
            '<thead><tr><th>Reported item</th><th>Value</th><th>Evidence</th></tr></thead><tbody>'
            +''.join(rows)+'</tbody></table>')


def _sources_html(refs):
    items = []
    for ref in refs:
        if not isinstance(ref, Mapping):
            continue
        item = _link(ref.get('source_url', ref.get('source_ref')), 'Official SEC source')
        item += ' · observed '+_text(ref.get('observed_at'))
        if ref.get('payload_sha256'):
            item += '<br>Original response SHA-256 <code>'+_text(ref['payload_sha256'])+'</code>'
        if ref.get('normalized_sha256'):
            item += '<br>Normalized subset SHA-256 <code>'+_text(ref['normalized_sha256'])+'</code>'
        items.append('<li>'+item+'</li>')
    return '<ul>'+''.join(items)+'</ul>'


def _review_html(review, *, sources_only=False):
    """Present a validated review. The public wrapper always revalidates the source packet."""
    review = review if isinstance(review, Mapping) else {}
    quality = review.get('quality') if isinstance(review.get('quality'), Mapping) else {}
    peer = review.get('peer_context') if isinstance(review.get('peer_context'), Mapping) else {}
    valid = review.get('status') == 'inspection_only'
    fields = [row for row in quality.get('fields', []) if isinstance(row, Mapping)] if valid else []
    by_name = {row.get('field'): row for row in fields}
    flags = quality.get('flags', []) if valid else []
    title = 'MRVL earnings review sources' if sources_only else 'Earnings quality behind annual P/E'
    caption_style = '<style>@media(max-width:640px){.mrvl-earnings-review caption{display:block;width:100%;text-align:left;line-height:1.5}}</style>'
    body = STYLE+caption_style+'<section id="mrvl-earnings-review" class="online-peer-valuation mrvl-earnings-review" aria-label="MRVL earnings and peer context"><h3>'+title+'</h3>'
    eps = by_name.get('diluted_eps', {})
    if eps.get('status') == 'available' and _number(eps.get('value')) and eps['value'] <= 0:
        body += '<p>Reported annual EPS is non-positive. It cannot establish a positive earnings multiple.</p>'
    elif 'disposal_gain_affects_reported_earnings' in flags:
        gain = by_name.get('gain_on_sale_of_business', {})
        body += '<p><strong>A business-sale gain needs attention: '+_amount(gain)+'.</strong> Reported annual P/E is not recurring-earnings valuation.</p>'
    else:
        body += '<p>Review the reported components before interpreting the annual earnings multiple.</p>'
    if not valid:
        body += '<p>'+_text(_reason(review.get('reason')))+'</p>'
    income, cash = by_name.get('net_income', {}), by_name.get('cash_from_operations', {})
    if income.get('status') == cash.get('status') == 'available':
        body += '<p>Reported net income '+_amount(income)+' · operating cash flow '+_amount(cash)+'. They measure different aspects of the business.</p>'
    body += '<details><summary>Inspect annual earnings and cash-flow evidence</summary>'
    body += _filing_html(quality.get('filing'), 'MRVL annual basis')
    body += _field_table(fields) if fields else '<p>Annual components remain withheld until their source and period can be verified.</p>'
    body += ('<p>The business-sale gain is pre-tax. Subtracting it from after-tax net income or EPS would not establish normalized earnings. '
             'Cash-flow addbacks for share-based compensation and amortization do not by themselves provide an after-tax reconciliation. '
             'Operating cash flow and PP&E purchases are separate observations; no free-cash-flow multiple is inferred.</p></details>')
    supported_peer = (valid and peer.get('status') == 'research_context'
                      and peer.get('relationship_supported') is True and peer.get('business_mix_difference') is True)
    body += '<h4>Broadcom: economic relevance and valuation eligibility</h4>'
    if supported_peer:
        body += ('<p>MRVL names Broadcom as a direct competitor. Broadcom also has infrastructure software, '
                 'so business mix needs separate consideration.</p>')
    else:
        body += '<p>AVGO comparison context remains incomplete. '+_text(_reason(peer.get('reason')))+'</p>'
    body += '<details><summary>Why consider AVGO, and why is the annual comparison held?</summary>'
    if supported_peer:
        body += _filing_html(peer.get('subject_filing'), 'MRVL annual period')
        body += _filing_html(peer.get('peer_filing'), 'AVGO annual period')
        gap = peer.get('period_end_gap_days')
        if type(gap) is int and gap >= 0:
            body += '<p>The annual end dates are '+str(gap)+' days apart. The existing 35-day window applies to both start and end dates.</p>'
        body += ('<p>This business context does not admit AVGO to the numerical comparison or approve an economic peer set. '
                 'Independent security identity, same-day completed prices and at least 3 qualified references are still required. '
                 'The existing peer panel owns the current admission and exclusion results.</p>')
    else:
        body += '<p>'+_text(_reason(peer.get('reason')))+'</p>'
    body += '</details><details><summary>Remaining earnings-quality gaps and source permissions</summary>'
    gaps = quality.get('gaps') if isinstance(quality.get('gaps'), list) else []
    body += '<ul>'+''.join('<li>'+_text(_reason(gap))+'</li>' for gap in gaps)+'</ul>'
    body += ('<p>No adjusted EPS or additional multiple is calculated. A validated after-tax reconciliation is needed before recurring or issuer-adjusted earnings can support another method.</p>'
             '<p>Personal Research inspection only. These observations do not grant commercial approval, source redistribution rights, '
             'canonical-field approval, saved-receipt eligibility or model readiness.</p>')
    body += _sources_html(review.get('source_refs', []))+'</details></section>'
    return body


def mrvl_earnings_review_html(financial_view, *, expected_cik=None, as_of=None, sources_only=False):
    if not isinstance(financial_view, Mapping) or financial_view.get('ticker') != 'MRVL':
        return ''
    if financial_view.get('status') == 'not_requested' and not financial_view.get('mrvl_earnings_review'):
        return '<p id="mrvl-earnings-review" class="company-scope-note">Refresh financials and prices to inspect MRVL annual earnings and the named AVGO comparison.</p>'
    from src.mrvl_earnings_review import validated_mrvl_review
    return _review_html(validated_mrvl_review(financial_view, expected_cik=expected_cik, as_of=as_of),
                        sources_only=sources_only)


def mrvl_earnings_caution_html(financial_view, *, expected_cik=None, as_of=None):
    """Keep a validated annual caveat beside the multiple, linking to the full review."""
    if not isinstance(financial_view, Mapping) or financial_view.get('ticker') != 'MRVL':
        return ''
    if not financial_view.get('mrvl_earnings_review'):
        return ''
    from src.mrvl_earnings_review import validated_mrvl_review
    review = validated_mrvl_review(financial_view, expected_cik=expected_cik, as_of=as_of)
    if review.get('status') != 'inspection_only':
        text = 'MRVL annual earnings review has unresolved source gaps.'
    elif 'disposal_gain_affects_reported_earnings' in review['quality'].get('flags', []):
        text = 'MRVL’s annual filing reports a business-sale gain; recurring earnings remain unresolved.'
    else:
        text = 'MRVL annual components are available for review; adjusted earnings remain unqualified.'
    return ('<style>.mrvl-earnings-caution{padding:.3rem .7rem;border-left:3px solid #bbd6c7;line-height:1.5}'
            '.mrvl-earnings-caution a{display:inline-flex;align-items:center;min-height:44px;padding:.2rem .45rem;'
            'color:#144c3d;text-decoration:underline}.mrvl-earnings-caution a:focus-visible{outline:3px solid #196853;outline-offset:2px}</style>'
            '<p class="company-scope-note mrvl-earnings-caution">'+_text(text)
            +' <a href="#mrvl-earnings-review">View earnings basis</a></p>')
