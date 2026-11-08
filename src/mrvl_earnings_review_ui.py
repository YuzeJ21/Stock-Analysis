"""Compact personal-research explanation; source validation owns every observation."""
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
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
    'review_reconciliation_document_oversized': 'The reconciliation source exceeds the supported document-size limit.',
    'sale_specific_tax_allocation_unavailable': 'The aggregate tax adjustment does not establish tax on the business-sale gain alone.',
    'item_specific_after_tax_eps_unavailable': 'The issuer does not provide an item-by-item after-tax EPS bridge in this table.',
    'normalized_earnings_not_qualified': 'Issuer non-GAAP results are not recurring or normalized earnings.',
    'adjusted_valuation_denominator_not_qualified': 'Issuer non-GAAP EPS is not qualified as another valuation denominator.',
}

AFTER_TAX_REASONS = {
    'reconciliation_not_requested': 'Refresh financials and prices to inspect the exact issuer reconciliation.',
    'reconciliation_annual_scope_unavailable': 'The annual filing context did not qualify for this reconciliation.',
    'reconciliation_primary_unavailable': 'The exact SEC earnings report was unavailable.',
    'reconciliation_exhibit_unavailable': 'The exact SEC earnings exhibit was unavailable.',
    'primary_source_unavailable': 'The exact SEC earnings report was unavailable.',
    'exhibit_source_unavailable': 'The exact SEC earnings exhibit was unavailable.',
    'exact_8k_missing_or_conflicting': 'The exact earnings report is absent or ambiguous in the current SEC submissions.',
    'exact_8k_metadata_mismatch': 'The earnings report identity, date or document did not match the reviewed source.',
    '8k_metadata_invalid': 'The earnings report dates could not be verified.',
    '8k_amendment_unreviewed': 'An amendment to this earnings report requires a separate source review.',
    'profile_identity_mismatch': 'The SEC profile does not establish the same MRVL issuer.',
    'profile_schema_invalid': 'The SEC submissions metadata could not be validated.',
    'primary_metadata_mismatch': 'The earnings document does not match the expected issuer, form and report date.',
    'primary_amendment_unreviewed': 'The earnings document is an unreviewed amendment.',
    'primary_visible_identity_missing': 'The earnings report identity was not established from its visible content.',
    'primary_item_202_missing': 'The required Item 2.02 earnings disclosure was not verified.',
    'primary_furnished_status_missing': 'The report did not establish the furnished status of Exhibit 99.1.',
    'primary_exact_exhibit_link_missing': 'The earnings report did not verify its exact Exhibit 99.1 link.',
    'evidence_schema_invalid': 'The exact reconciliation evidence has not been collected or could not be validated.',
    'raw_bytes_missing_or_oversized': 'The original source bytes are missing or exceed the supported size.',
    'raw_digest_changed': 'The original document no longer matches its recorded digest.',
    'document_malformed_markup': 'The document structure could not support unambiguous extraction.',
    'net_income_arithmetic_mismatch': 'The signed adjustments do not reconcile at the disclosed reporting precision.',
    'disclosed_eps_rounding_mismatch': 'Reported EPS does not agree with its own income and diluted-share observations at source precision.',
    'gaap_shares_invalid': 'The source share observations could not be verified.',
    'diluted_shares_invalid': 'The source diluted-share denominator could not be verified.',
    'extra_reconciliation_row': 'The table contains an additional adjustment outside this reviewed source definition.',
    'reconciliation_rows_missing_extra_or_conflicting': 'The reconciliation rows are missing, repeated or conflicting.',
    'reconciliation_rows_incomplete': 'The annual reconciliation is incomplete.',
    'conflicting_section_context': 'A section heading conflicts with the reviewed currency, units or annual duration.',
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


def _after_tax_reason(reason):
    while isinstance(reason, str) and reason.startswith('after_tax_'):
        reason = reason[len('after_tax_'):]
    return AFTER_TAX_REASONS.get(reason, REASONS.get(reason,
        'The exact issuer reconciliation could not be verified. The annual fields retain their own evidence status.'))


def _after_tax_amount(component):
    """Keep source precision and a consistent million-dollar basis for the bridge."""
    try:
        value = Decimal(str(component.get('source_value')))
        if not value.is_finite():
            return 'Withheld'
        text = format(value, ',f')
        if component.get('unit') == 'shares' and component.get('scale') == 1_000_000:
            return text+'M shares'
        if component.get('unit') == 'USD' and component.get('scale') == 1_000_000:
            return 'USD '+text+'M'
        if component.get('unit') == 'USD/shares' and component.get('scale') == 1:
            return 'USD '+text
    except (ValueError, TypeError, InvalidOperation):
        pass
    return 'Withheld'


def _after_tax_html(reconciliation):
    r = reconciliation if isinstance(reconciliation, Mapping) else {}
    valid = r.get('status') == 'verified_issuer_reconciliation'
    title = 'Issuer after-tax reconciliation — '+('verified' if valid else 'withheld')
    body = '<details class="mrvl-after-tax"><summary>'+title+'</summary>'
    if not valid:
        return body+'<p>'+_text(_after_tax_reason(r.get('reason')))+('</p><p>The annual fields and peer context retain their independent evidence status. '
            'A pretax gain cannot be subtracted from after-tax net income or EPS to establish normalized earnings.</p></details>')
    filing = r.get('filing') if isinstance(r.get('filing'), Mapping) else {}
    period = r.get('annual_period') if isinstance(r.get('annual_period'), Mapping) else {}
    body += ('<p><strong>Issuer-reported GAAP to non-GAAP, not recurring or normalized earnings.</strong></p>'
             '<p>Year ended '+_text(period.get('period_end'))+' · annual interval '
             +_text(period.get('period_start'))+' to '+_text(period.get('period_end'))
             +' anchored to the independently verified 10-K.</p><p>Form '+_text(filing.get('form'))
             +' · filed '+_text(filing.get('filed'))+' · '+_text(filing.get('accession'))
             +' · Exhibit 99.1 furnished under Item 2.02 · '+_link(filing.get('primary_url'), 'SEC earnings report')
             +' · '+_link(filing.get('exhibit_url'), 'SEC reconciliation exhibit')+'</p>')
    rows = []
    adjustment_fields = {'stock_based_compensation','amortization_of_acquired_intangibles','restructuring_related_charges',
                         'other_cost_of_goods_sold','gain_on_sale_of_business','other','pretax_special_items_total','tax_effects'}
    for component in r.get('components', []):
        if not isinstance(component, Mapping):
            continue
        amount = _after_tax_amount(component)
        if component.get('field') in adjustment_fields and _number(component.get('value')) and component['value'] > 0:
            amount = amount.replace('USD ', 'USD +', 1)
        meta = ('<details><summary>Source observation</summary><p>Exact displayed number: '
                +_text(component.get('source_value'))+' · source scale '+_text(component.get('scale'))
                +' · normalized unit '+_text(component.get('unit'))+'</p><p>Original cell: '
                +_text(component.get('raw_text'))+' · table '+_text(component.get('table_index'))
                +' · row '+_text(component.get('row_index'))+' · source column span '
                +_text(component.get('column_span'))+' (zero-based, end exclusive)</p><p>Observed '
                +_text(component.get('observed_at'))+' · '+_link(component.get('source_ref'), 'Exact SEC exhibit')
                +'</p><p>Original response SHA-256 <code>'+_text(component.get('payload_sha256'))+'</code></p></details>')
        rows.append('<tr><td data-label="Reported item">'+_text(component.get('label'))+'</td>'
                    '<td data-label="Value">'+amount+'</td><td data-label="Evidence">'+meta+'</td></tr>')
    body += ('<table><caption>Reported annual reconciliation. Monetary amounts and shares are in millions in the source; EPS is per share. '
             'USD is bound to the matching annual GAAP observations.</caption><thead><tr><th>Reported item</th><th>Value</th><th>Evidence</th>'
             '</tr></thead><tbody>'+''.join(rows)+'</tbody></table>')
    checks = r.get('checks') if isinstance(r.get('checks'), Mapping) else {}
    body += '<p>The signed special items and aggregate tax adjustment reconcile at the reported precision. No item-specific EPS adjustment is derived.</p>'
    if all(isinstance(checks.get(k), Mapping) and checks[k].get('passed') is True for k in ('gaap_eps','issuer_non_gaap_eps')):
        body += '<p>Reported GAAP and issuer non-GAAP EPS are consistent with their respective disclosed diluted-share observations at source precision.</p>'
    body += '<ul>'+''.join('<li>'+_text(_reason(g))+'</li>' for g in r.get('gaps', []))+'</ul>'
    body += _sources_html(r.get('source_refs', []))+'</details>'
    return body


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
    reconciliation = quality.get('after_tax_reconciliation') if valid else None
    body += _after_tax_html(reconciliation)
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
    if isinstance(reconciliation, Mapping) and reconciliation.get('status') == 'verified_issuer_reconciliation':
        body += '<p>Issuer non-GAAP EPS is an inspected source observation. No adjusted multiple or recurring-earnings estimate is calculated.</p>'
    else:
        body += '<p>No adjusted EPS or additional multiple is calculated. A validated after-tax reconciliation is needed before recurring or issuer-adjusted earnings can support another method.</p>'
    body += ('<p>Personal Research inspection only. These observations do not grant commercial approval, source redistribution rights, '
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
