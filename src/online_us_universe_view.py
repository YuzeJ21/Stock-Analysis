"""Compact full-inventory progress and native-unit IFRS evidence presentation."""
from collections.abc import Mapping
from html import escape

from src.online_company_identity import _mode_reason
from src.online_research_expansion_view import _STYLE, _amount, _receipts, _reason
from src.online_research_coverage import METRICS
from src.online_us_universe import validated_us_universe, build_universe_coverage, validated_access_pause
from src.sec_foreign_financials import validated_foreign_financials
from src.sec_quarterly_history import FIELDS

STYLE = _STYLE + '<style>.online-universe,.online-foreign{margin:16px 0;padding:16px;border:1px solid #d9e0dc;border-radius:8px;min-width:0;overflow-wrap:anywhere;box-sizing:border-box}.online-foreign-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,20rem),1fr));gap:12px}.online-foreign article{padding:12px;border:1px solid #d9e0dc;border-radius:8px;min-width:0;box-sizing:border-box;background:white}.online-foreign dl div{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px}.online-foreign dd{margin:0;font-weight:650}.online-universe li,.online-foreign li{overflow-wrap:anywhere}</style>'
LABELS = {'revenue': 'Revenue', 'operating_income': 'Operating profit / loss',
          'cash_from_operations': 'Operating cash flow', 'capital_expenditures': 'PP&E purchases · investing activities'}


def foreign_financials_html(view):
    if _mode_reason('research'): return '<p>Personal IFRS inspection unavailable in this mode.</p>'
    raw = view.get('foreign_financials') if isinstance(view, Mapping) else None
    if raw is None or isinstance(raw, Mapping) and raw.get('reason') == 'ifrs_standard_facts_unavailable': return ''
    h = validated_foreign_financials(view)
    if h is None:
        return '<section class="online-foreign"><h3>IFRS financials</h3><p>Withheld · ' + _reason(raw.get('reason') if isinstance(raw, Mapping) else None) + '.</p></section>'
    sections = []
    for kind, title in [('annual', 'Annual'), ('quarterly', 'Direct reported quarters'), ('interim', 'Cumulative / interim · not a single quarter')]:
        cards = []
        for row in reversed(h[kind]):
            if row['status'] != 'available':
                cards.append('<article><h5>Period ended ' + escape(row['period_end']) + '</h5><p>Withheld · ' + _reason(row['reason']) + '</p></article>')
                continue
            values = ''.join('<div><dt>' + LABELS[name] + (' · continuing operations' if name in row['fields'] and row['fields'][name]['concept'].endswith('ContinuingOperations') else '')
                + '</dt><dd>' + (escape(h['unit']) + ' ' + _amount(row['fields'][name]['value']) if name in row['fields'] else 'Withheld') + '</dd></div>' for name in FIELDS)
            definitions = '; '.join(name + ': ifrs-full:' + f['concept'] for name, f in row['fields'].items())
            gaps = '; '.join(LABELS[name] + ': ' + reason.replace('_', ' ') for name, reason in row['withheld_fields'].items())
            cards.append('<article><h5>Period ended ' + escape(row['period_end']) + '</h5><p>' + escape(row['period_start']) + ' to ' + escape(row['period_end']) + ' · ' + escape(h['unit']) + '</p><dl>' + values
                + '</dl><details><summary>Filing evidence and gaps</summary><p>Filed ' + escape(row['filed']) + ' · ' + escape(row['form']) + ' · accession ' + escape(row['accession']) + '</p><p>' + escape(definitions) + '</p><p>' + escape(gaps) + '</p></details></article>')
        recent = '<div class="online-foreign-grid">' + ''.join(cards[:2]) + '</div>' if cards else '<p>No compatible directly reported periods found.</p>'
        earlier = '<details><summary>Earlier ' + escape(title.lower()) + ' periods (' + str(len(cards)-2) + ')</summary><div class="online-foreign-grid">' + ''.join(cards[2:]) + '</div></details>' if len(cards) > 2 else ''
        sections.append('<h4>' + title + '</h4>' + recent + earlier)
    return (STYLE + '<section class="online-foreign" aria-label="IFRS financials"><h3>IFRS financials · ' + escape(h['unit']) + '</h3>'
        '<p>Direct standard IFRS facts as observed now, including revisions; not point-in-time history. A single non-USD source currency is preferred to convenience USD translations. No FX conversion, missing quarter, ADS ratio or valuation is inferred.</p>'
        + ''.join(sections) + '<details><summary>Source and rights</summary><p>SEC CIK ' + escape(h['sec_cik']) + ' · ifrs-full:Revenue · direct-field scope inspected; raw redistribution held.</p>'
        + _receipts([h]) + '</details></section>')


def universe_coverage_html(state):
    if _mode_reason('research'): return '<p>Personal listing inspection unavailable in this mode.</p>'
    if not isinstance(state, Mapping) or state.get('status') == 'not_requested':
        return '<p>Load the dated official U.S. listing inventory, then check issuer financial coverage in batches. No company CSV or background source request is required.</p>'
    inventory = validated_us_universe(state.get('inventory'))
    coverage = build_universe_coverage(inventory, state.get('observations', []))
    if inventory is None or coverage['status'] != 'inspection_only':
        return '<p>Listing coverage unavailable · ' + _reason(state.get('reason') or coverage.get('reason')) + '.</p>'
    pause=state.get('source_access_pause')
    if pause is not None:
        pause=validated_access_pause(pause)
        if pause is None:return '<p>Listing coverage unavailable · invalid source pause.</p>'
    pause_html='<p><strong>SEC access paused.</strong> Verified progress is retained; resume after '+escape(pause['resume_after'])+'. No further issuer request is made during the pause.</p>' if isinstance(pause,Mapping) else ''
    n = coverage['issuer_denominator']
    venues = ''.join('<li>' + escape(venue) + ': ' + str(count) + ' listing records</li>' for venue, count in sorted(inventory['by_venue'].items()))
    counts = ''.join('<li>' + escape(name.replace('_', ' ')) + ': ' + str(coverage['counts'][name]) + '/' + str(n) + ' issuer candidates</li>' for name in METRICS)
    gaps = ''.join('<li>' + escape(row['venue']) + ': ' + _reason(row['status']) + '</li>' for row in inventory['venue_gaps'])
    industries = ''.join('<li>SIC ' + escape(row['sic'] or 'unknown') + ': ' + str(row['attempted_issuer_count']) + ' attempted; annual revenue ' + str(row['counts']['annual_revenue']) + ', quarterly revenue ' + str(row['counts']['quarterly_revenue']) + '</li>' for row in coverage['by_industry'])
    rows = ''.join('<li>' + escape(r['ticker']) + ': annual ' + _reason(r['annual_reason']) + '; quarterly ' + _reason(r['quarterly_reason']) + '; annual unit ' + escape(r['annual_unit'] or 'withheld') + '; latest reporting periods annual ' + escape(r['annual_period'] or 'unavailable') + ', quarter ' + escape(r['quarterly_period'] or 'unavailable') + '</li>' for r in coverage['rows'])
    return (STYLE + '<section class="online-universe" aria-label="U.S. listing coverage"><h3>U.S. listing coverage · full observed inventory</h3>'
        + pause_html + '<p><strong>' + str(inventory['listing_count']) + ' observed listings</strong> · ' + str(n) + ' issuer candidates · ' + str(inventory['known_etf_count']) + ' known ETF records · ' + str(inventory['excluded_test_issue_count']) + ' test issues excluded.</p>'
        '<p><strong>' + str(coverage['attempted_issuer_count']) + ' attempted · ' + str(coverage['unprobed_issuer_count']) + ' unprobed</strong> · ' + str(coverage['source_failure_count']) + ' financial source failures · ' + str(coverage['unsupported_financial_count']) + ' unsupported financial paths.</p>'
        '<p>Complete U.S. market coverage is not yet established. This denominator is the union of the fetched official inventories. Issuer domicile, active status, non-ETF security type, analysis eligibility and point-in-time coverage remain unverified. Multiple share classes count once in the financial queue.</p>'
        '<p>' + str(inventory['resolved_issuer_count']) + ' CIKs resolved across listing records; ' + str(inventory['unmatched_listing_count']) + ' listing records unmatched, including ETFs. Non-ETF does not establish an operating company. SIC unknown or unprobed: ' + str(coverage['unknown_industry_count']) + ' issuer candidates.</p>'
        '<details><summary>Field coverage across the full candidate denominator</summary><ul>' + counts + '</ul><p>Native currencies are retained; availability counts never compare financial amounts. Interim and cumulative periods do not count as direct quarters.</p></details>'
        '<details><summary>Venues, reconciliation and remaining gaps</summary><ul>' + venues + gaps + '</ul><p>Unrecognized directory venue codes: ' + escape(', '.join(inventory['unknown_venue_codes']) or 'none in this receipt') + '. SEC-only listing records: ' + str(inventory['sec_only_listing_count']) + '; OTC records outside the exchange-listing denominator: ' + str(inventory['otc_record_count']) + '; null exchange records: ' + str(inventory['unknown_exchange_record_count']) + '.</p></details>'
        '<details><summary>Industry availability and attempted issuers</summary><ul>' + industries + rows + '</ul></details>'
        '<details><summary>Dated source receipts and rights</summary>' + _receipts(inventory['source_receipts']) + '<p>Inventory observation span ' + escape(inventory['observed_from']) + ' to ' + escape(inventory['observed_to']) + '. Listing/SIC metadata: unregistered personal inspection only. SEC direct financial field scope remains separate; raw redistribution held.</p></details></section>')
