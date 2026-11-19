"""Projection of independently validated archive quarters; no source transport."""
from copy import deepcopy
from html import escape

from src.online_research_expansion_view import financial_field_label
from src.sec_native_quarter_comparisons import BASES, REASONS, quarter_changes

_NEE_SEPTEMBER_10Q = 'https://www.sec.gov/Archives/edgar/data/753308/000075330826000081/nee-20260930.htm'
_NEE_JUNE_10Q = 'https://www.sec.gov/Archives/edgar/data/753308/000075330826000060/nee-20260630.htm'
_NEE_OCTOBER_EARNINGS = 'https://www.sec.gov/Archives/edgar/data/753308/000075330826000077/neeq32026exhibit99.htm'

_STYLE = ('<style>.company-archive-quarter{min-width:0;overflow-wrap:anywhere;margin:16px 0;padding:16px;background:#fff;color:#172522;border:1px solid #dce3de;border-radius:8px}.archive-quarter-table{max-width:100%;overflow-x:auto}'
          '.company-archive-quarter p,.company-archive-quarter th,.company-archive-quarter td,.company-archive-quarter li,.company-archive-quarter summary{color:#172522!important}.company-archive-quarter a{color:#245842!important}'
          '.archive-quarter-table table{width:100%;font-size:.86rem;border-collapse:collapse}.archive-quarter-table th,.archive-quarter-table td{padding:8px;text-align:left;border-bottom:1px solid #dce3de;overflow-wrap:normal}'
          '.archive-quarter-table td:nth-child(2){white-space:nowrap;font-variant-numeric:tabular-nums}@media(max-width:480px){.archive-quarter-table th,.archive-quarter-table td{padding:6px}}'
          '.company-archive-quarter summary{cursor:pointer;min-height:44px;align-content:center}.company-archive-quarter summary:focus-visible{outline:3px solid #245842}</style>')


def merge_archive_quarter(rows, archive, *, prefer_exact=False):
    """Keep the chosen source for the whole row and preserve distinct durations."""
    result = deepcopy(rows)
    if not archive:
        return result
    quarter = next((r for r in archive['periods'] if r['kind'] == 'quarterly'), None)
    if not quarter:
        return result
    existing = next((r for r in result if r['period_end'] == quarter['period_end']), None)
    if (existing and existing['status'] == 'available'
            and all(existing.get(k) == quarter.get(k) for k in ('accession', 'form', 'filed'))
            and not (prefer_exact and quarter['status'] == 'available')):
        return result
    row = deepcopy(quarter)
    cumulative = next((r for r in archive['periods'] if r['kind'] == 'cumulative'), {})
    row.update(cumulative_fields=deepcopy(cumulative.get('fields', {})),
               cumulative_withheld_fields=deepcopy(cumulative.get('withheld_fields', {})),
               cumulative_anchor={key:cumulative.get(key) for key in ('period_start','period_end','accession','form','filed')})
    result = [r for r in result if r['period_end'] != row['period_end']]
    return sorted([*result, row], key=lambda r: r['period_end'])


def archive_quarter_html(financial, *, as_of=None):
    from src.sec_online_quarter_evidence import validated_archive_quarter
    archive = validated_archive_quarter(financial, as_of=as_of)
    if not archive:
        raw = financial.get('archive_quarterly', {})
        if not raw:
            return ''
        reason = raw.get('reason') if raw.get('status') == 'withheld' else 'archive_quarter_evidence_invalid_or_stale'
        if reason == 'archive_quarter_not_required':
            return ''
        return ('<section class="company-archive-quarter" aria-label="Exact SEC quarter"><h3>Exact SEC quarter</h3>'
                '<p>Withheld · ' + escape(str(reason).replace('_', ' ')) + '. Refresh explicitly to recheck.</p></section>')
    panels = []
    labels = {'net_interest_income': 'Net interest income', 'noninterest_income': 'Noninterest income'}
    for row in archive['periods']:
        title = 'Direct quarter' if row['kind'] == 'quarterly' else 'Cumulative period · not single-quarter cash flow'
        lines = []
        definitions = []
        for key in (*row['fields'], *row['withheld_fields']):
            field = row['fields'].get(key)
            label = labels[key] if key in labels else financial_field_label(key, field)
            amount = f"{field['unit']} {field['value']:,.0f}" if field else 'Withheld'
            reason = '' if field else row['withheld_fields'][key].replace('_', ' ')
            lines.append('<tr><th scope="row">' + escape(label) + '</th><td>' + escape(amount) + '</td><td>' + escape(reason) + '</td></tr>')
            if field:
                definitions.append('<li>' + escape(label + ': ' + field['taxonomy'] + ':' + field['concept']
                    + ' · context ' + field['context_id'] + ' · unit ' + field['unit_id'] + ' · fact ' + field['fact_id']) + '</li>')
        panels.append('<h4>' + escape(title) + '</h4><p>' + escape(row['period_start'] + ' to ' + row['period_end']) + '</p>'
                      '<div class="archive-quarter-table"><table><thead><tr><th>Field</th><th>Reported value</th><th>Missing reason</th></tr></thead><tbody>'
                      + ''.join(lines) + '</tbody></table></div><details><summary>Field definitions</summary><ul>' + ''.join(definitions) + '</ul></details>')
    refs = ''.join('<li><a target="_blank" rel="noopener noreferrer" href="' + escape(r['source_url'], quote=True) + '">SEC source</a> · observed '
                   + escape(r['observed_at']) + ' · SHA-256 ' + escape(r['payload_sha256']) + '</li>' for r in archive['source_receipts'])
    return (_STYLE + '<section class="company-archive-quarter" aria-label="Exact SEC quarter"><h3>Exact SEC quarter</h3><p>'
            + escape(archive['form'] + ' · filed ' + archive['filed'] + ' · accession ' + archive['accession'] + ' · CIK ' + archive['sec_cik']) + '</p>' + ''.join(panels)
            + '<details><summary>Source and reporting basis</summary><p>Directly reported parent-issuer facts from the exact SEC filing. Companyfacts coverage remains separate. The reported tables contain no derived quarters.</p>'
            + '<p>Personal inspection only · archive source rights are unregistered. Commercial use, redistribution and saved-model readiness remain unapproved.</p><p>'
            + escape('Accepted ' + archive['accepted_at'] + ' · Observed ' + archive['observed_at']) + '</p><ul>' + refs
            + '</ul></details></section>' + nee_quarter_cash_html(archive.get('nee_quarter_cash'))
            + capital_purchase_html(archive.get('capital_purchase_evidence')))


def nee_quarter_cash_html(evidence):
    """Present validated subtraction apart from directly reported periods."""
    if not evidence:
        return ''
    from src.sec_nee_quarter_cash import SOURCES

    six, nine = evidence['six_months'], evidence['nine_months']
    amount = (nine['value'] - six['value']) // 1_000_000
    lines = []
    for key, period in (('nine_months', 'January–September 2026'), ('six_months', 'January–June 2026')):
        row = evidence[key]
        accession, _, filed = SOURCES[key]
        source = escape(row['source_url'] + '#f-345', quote=True)
        lines.append(f'<li>{period} · USD {row["value"] // 1_000_000:,} million · '
                     f'<a href="{source}" target="_blank" rel="noopener noreferrer">{period} SEC fact</a>'
                     f'<br>Filed {filed} · Accession {accession} · Observed {escape(row["observed_at"])}'
                     f'<br>SHA-256 {escape(row["payload_sha256"])}</li>')
    return (_STYLE + '<section class="company-archive-quarter" aria-label="NEE calculated Q3 operating cash flow">'
            '<h3>Q3 operating cash flow · Calculated</h3>'
            f'<p><strong>USD {amount:,} million</strong> · July 1–September 30, 2026</p>'
            '<details><summary>Calculation and SEC sources</summary>'
            '<p>Subtract January–June from January–September. Both NextEra Energy consolidated 10-Qs '
            'report net cash provided by operating activities in USD millions. Personal inspection only.</p>'
            '<ul>' + ''.join(lines) + '</ul></details></section>')


def nee_gross_ppe_review_html(evidence):
    """Show the dated definition review for the exact September NEE filing."""
    if not evidence or (evidence['accession'], evidence['source_url']) != ('0000753308-26-000081', _NEE_SEPTEMBER_10Q):
        return ''
    sources = ((_NEE_JUNE_10Q, 'June 2026 SEC 10-Q', 'filed July 24, 2026'),
               (_NEE_SEPTEMBER_10Q, 'September 2026 SEC 10-Q', 'filed October 21, 2026'),
               (_NEE_OCTOBER_EARNINGS, 'October SEC earnings exhibit', 'furnished October 21, 2026'))
    links = ''.join(f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a> · {source_date}</li>'
                    for url, label, source_date in sources)
    return ('<section aria-label="Consolidated gross PP&amp;E purchases">'
            '<h4>Consolidated gross PP&amp;E purchases</h4><ul><li>July–September 2026 · Withheld</li>'
            '<li>January–September 2026 · Withheld</li></ul>'
            '<details><summary>SEC review · November 16, 2026</summary>'
            '<p>Both 10-Q cash-flow statements and the October earnings exhibit combine NextEra Energy Resources’ '
            'independent power and other investments. The broader total also includes nuclear fuel. '
            'Subtracting the cumulative totals gives spending across those same categories.</p>'
            '<p>The separate Florida Power &amp; Light statement covers only that subsidiary. The September '
            'filing lists accrued property additions under noncash investing and financing. The reviewed '
            'segment disclosures provide no consolidated gross cash-payment breakdown for PP&amp;E.</p>'
            '<ul>' + links + '</ul></details></section>')


def capital_purchase_html(evidence):
    """Display the exact issuer-specific year-to-date definition and cash-flow lines."""
    if not evidence:
        return ''
    order = ('reported_capital_investment_total', 'fpl_capital_expenditures',
             'neer_independent_power_and_other_investments', 'nuclear_fuel_purchases', 'other_capital_expenditures')
    lines = []
    for key in order:
        field = evidence['fields'].get(key)
        if not field:
            continue
        label = escape(field['label'])
        amount = escape(f"{field['unit']} {field['value']:,}")
        source = escape(field['source_ref'], quote=True)
        basis = 'Reported consolidated total' if field['presentation'] == 'reported_total' else 'Consolidated cash-flow outlay'
        lines.append(f'<li><strong>{label}</strong> · {amount} <small>({basis})</small> '
                     f'<a href="{source}" target="_blank" rel="noopener noreferrer">SEC fact</a></li>')
    dates = escape(evidence['period_start'] + ' to ' + evidence['period_end'])
    url = escape(evidence['source_url'], quote=True)
    filing = escape(f"Filed {evidence['filed']} · Accession {evidence['accession']} · Observed {evidence['observed_at']}")
    gross_review = nee_gross_ppe_review_html(evidence)
    if gross_review:
        gap = gross_review + '<p>Directly reported quarterly operating cash flow remains unavailable in this panel.</p>'
    else:
        gap = ('<p><strong>Consolidated PP&amp;E purchases need verification.</strong> '
               'The reported total includes independent power and other investments and nuclear fuel.</p>'
               '<p>Quarterly cash flow and capital purchases need direct-quarter evidence.</p>')
    return (_STYLE + '<section class="company-archive-quarter" aria-label="NEE capital investment evidence">'
            '<h3>Year-to-date capital investments</h3><p>' + dates + ' · USD · NEE consolidated filing</p><ul>'
            + ''.join(lines) + '</ul>' + gap
            + '<details><summary>Exact SEC filing and scope</summary><p><a href="' + url + '" target="_blank" '
            'rel="noopener noreferrer">Exact SEC 10-Q</a> · ' + filing + '</p>'
            '<p>Personal inspection only. Operating cash flow less PP&amp;E requires its own matched evidence.</p></details></section>')


def native_quarter_comparisons_html(current, comparatives, gaps=None):
    """Show direct-quarter comparison values and their same-document basis."""
    comparisons = quarter_changes(current, comparatives)
    panels = []
    for basis, title in BASES.items():
        panels.append(f'<h5>{title}</h5>')
        comparison = comparisons.get(basis)
        if comparison is None:
            reason = (gaps or {}).get(basis, 'same_filing_comparison_unavailable')
            panels.append('<p>' + escape(REASONS[reason]) + '</p>')
            continue
        prior = comparison['period']
        panels.append('<p>' + escape(f"{prior['period_start']} to {prior['period_end']} · "
                                     f"compared with {current['period_start']} to {current['period_end']}") + '</p>')
        lines, definitions = [], []
        for name, change in comparison['fields'].items():
            label = financial_field_label(name, change.get('current'))
            if 'prior' in change:
                previous, latest = change['prior'], change['current']
                value = f"{previous['unit']} {previous['value']:,} → {latest['value']:,}"
                fraction = change['fraction']
                change_text = f'{fraction:+.1%}' if fraction is not None else REASONS[change['reason']]
                if fraction is not None and 0 < abs(fraction) < .0005:
                    change_text = ('+' if fraction > 0 else '−') + '<0.1%'
                value += ' · ' + change_text
                if 'retrospectively adjusted' in previous['column_header'].casefold():
                    value += ' · Retrospectively adjusted prior figure'
                definitions.append('<li>' + escape(f"{label} · {previous['row_label']} · "
                    f"{previous['column_header']} → {latest['column_header']} · {previous['unit_evidence']}") + '</li>')
            else:
                value = 'Withheld · ' + REASONS[change['reason']]
            lines.append('<li><strong>' + escape(label) + '</strong> · ' + escape(value) + '</li>')
        panels.append('<ul>' + ''.join(lines) + '</ul>')
        if definitions:
            source = next(c['prior']['source_ref'] for c in comparison['fields'].values() if c.get('prior'))
            panels.append('<details><summary>Comparison evidence</summary><p><a target="_blank" '
                          'rel="noopener noreferrer" href="' + escape(source, quote=True)
                          + '">Exact SEC comparison source</a></p><ul>' + ''.join(definitions) + '</ul></details>')
    return ('<section aria-label="Quarter comparisons"><h4>Quarter comparisons</h4>'
            '<p>Changes use the three-month columns from the same filing.</p>' + ''.join(panels) + '</section>')


def _cash_billions(cent_billions):
    whole, cents = divmod(abs(cent_billions), 100)
    return f'{"-" if cent_billions < 0 else ""}{whole:,}.{cents:02d}'


def _tsm_operating_cash_review(row):
    if row['matches_presentation']:
        return ''
    difference = row['difference_thousands']
    direction = 'above' if difference > 0 else 'below'
    return ('<details><summary>Operating cash flow discrepancy review</summary>'
            '<p><strong>Open · Cause unverified as of November 16, 2026.</strong></p>'
            f'<p>The reviewed calculation rounds to TWD {_cash_billions(row["rounded_cent_billions"])} billion. '
            f'It is TWD {abs(difference):,} thousand {direction} the amount displayed in October.</p>'
            '<p>The October cash bridge balances at its displayed precision. The rounded bridge from the reviewed statements '
            'also balances because differences in operating cash flow and cash dividends offset at that precision.</p>'
            '<p>The reviewed accounting and cash-flow notes give no explanation. The board filing approved the statements '
            'and provides no cash-flow bridge. The SEC filing history showed no amended 6-K from August 14 through November 16.</p>'
            '<ul><li><a href="https://www.sec.gov/Archives/edgar/data/1046179/000104617926000797/tsm-boardx202611xx.htm" '
            'target="_blank" rel="noopener noreferrer">November 10 board filing</a></li>'
            '<li><a href="https://www.sec.gov/edgar/browse/?CIK=1046179" target="_blank" rel="noopener noreferrer">'
            'TSM SEC filing history</a></li></ul></details>')


def tsm_cash_reconciliation_html(evidence):
    from src.sec_tsm_quarter_cash import CASH_SOURCES, cash_flow_rows

    title = 'September quarter cash flow reconciliation'
    section = f'<section class="company-archive-quarter" aria-label="{title}"><h4>{title}</h4>'
    if not evidence:
        return _STYLE + section + '<p>Withheld · The exact three-source calculation is unavailable in this observation.</p></section>'
    labels = {'cash_from_operations': 'Operating cash flow', 'capital_expenditures': 'Gross PP&amp;E cash purchases'}
    results, cumulative = [], []
    rows = cash_flow_rows(evidence)
    for key, row in rows.items():
        slide_text = _cash_billions(row['presentation_cent_billions'])
        match = ('Agrees at the presentation’s precision.' if row['matches_presentation']
                 else 'Differs at the presentation’s precision. Cause unverified.')
        results.append(f'<li><strong>{labels[key]}</strong> · Calculated TWD {row["quarter_thousands"]:,} thousand'
                       f'<br>October presentation · TWD {slide_text} billion. {match}</li>')
        cumulative.append(f'<li><strong>{labels[key]}</strong> · Six months TWD {row["six_months_thousands"]:,} thousand'
                          f'<br>Nine months TWD {row["nine_months_thousands"]:,} thousand</li>')
    sources = {'six_months': 'June reviewed SEC exhibit', 'nine_months': 'September reviewed SEC exhibit',
               'presentation': 'October SEC cash flow presentation'}
    links = ''.join(f'<li><a href="{CASH_SOURCES[key]["source_url"]}" target="_blank" rel="noopener noreferrer">{label}</a>'
                    f' · observed {escape(evidence["receipts"][key]["observed_at"])}'
                    f' · SHA-256 {escape(evidence["receipts"][key]["payload_sha256"])}</li>' for key, label in sources.items())
    return (_STYLE + section + '<p>July 1 to September 30, 2026 · Calculated as nine months less six months.</p><ul>'
            + ''.join(results) + '</ul>' + _tsm_operating_cash_review(rows['cash_from_operations'])
            + '<details><summary>Cumulative cash-flow inputs and SEC receipts</summary>'
            '<p>January to June and January to September · Gross PP&amp;E acquisition payments follow Note 29(a).</p><ul>'
            + ''.join(cumulative) + '</ul><ul>' + links + '</ul></details></section>')


def ase_net_ppe_html(evidence):
    from src.sec_online_native_quarter_evidence import ASE_NET_PPE_SOURCE

    if not evidence:
        return ''
    title = 'Reported net PP&E payments'
    rows = []
    for kind, label in (('quarterly', 'Direct quarter'), ('cumulative', 'Year to date')):
        if kind not in evidence:
            continue
        field = evidence[kind]
        basis = f"{label} · {field['period_start']} to {field['period_end']}"
        if 'retrospectively adjusted' in field['column_header'].casefold():
            basis += ' · Retrospectively adjusted'
        amount = f"{field['unit']} {field['reported_text']} million"
        rows.append(f'<li>{escape(basis)}<br><strong>{escape(amount)}</strong></li>')
    return (_STYLE + f'<section class="company-archive-quarter" aria-label="{escape(title)}"><h4>{escape(title)}</h4>'
            '<ul>' + ''.join(rows) + '</ul><p><strong>Gross PP&amp;E cash purchases · Withheld</strong></p>'
            '<p>The October results show net payments and provide no separate September-quarter PP&amp;E disposal receipts. '
            'Equipment capex is a separate USD measure.</p><details><summary>SEC sources checked</summary><ul>'
            f'<li><a href="{ASE_NET_PPE_SOURCE}">October 29 SEC results</a> · Consolidated net cash payments</li>'
            '<li><a href="https://www.sec.gov/Archives/edgar/data/1122411/000095010326016323/dp255782_6k.htm">'
            'October 29 SEC earnings deck</a> · Equipment capex in USD</li>'
            '<li><a href="https://www.sec.gov/Archives/edgar/data/1122411/000119312526329634/d174900d6k.htm">'
            'March-quarter SEC statements</a> · Separate cash purchases and disposal proceeds for March</li>'
            '<li><a href="https://www.sec.gov/Archives/edgar/data/1122411/000095010326017186/dp256592_6k.htm">'
            'November 10 monthly revenue filing</a> · October sales update</li></ul></details>'
            '<details><summary>TWSE reporting-basis review</summary><p><strong>Gross Q3 PP&amp;E · Withheld</strong></p>'
            '<p>Both reviewed TWSE statements report consolidated cash flows in TWD and show gross PP&amp;E payments '
            'and disposal proceeds separately for their cumulative periods.</p>'
            '<p>June uses provisional ASEPG acquisition accounting. September finalizes that accounting and shows the change '
            'in subsidiary acquisition cash separately. The November 16 review found no restated June gross payment and disposal '
            'cash lines on the September basis. Agreement with the SEC net payment cannot verify those two components individually.</p>'
            '<ul><li><a href="https://doc.twse.com.tw/server-java/t57sb01?step=1&amp;colorchg=1&amp;co_id=3711&amp;year=115&amp;seamon=2&amp;mtype=A">'
            'June TWSE filings</a> · Cash-flow statement and Notes 29 and 31</li>'
            '<li><a href="https://doc.twse.com.tw/server-java/t57sb01?step=1&amp;colorchg=1&amp;co_id=3711&amp;year=115&amp;seamon=3&amp;mtype=A">'
            'September TWSE filings</a> · Cash-flow statement and Notes 30 and 32</li></ul>'
            '<h5>Restated June search · November 16, 2026</h5>'
            '<p>The MOPS listed-company correction registers for Q2 and Q3 had no ASE entry for either quarter. '
            'The June cash-flow query repeats the original six-month figures. The September query gives nine-month figures '
            'with a prior-year comparative.</p>'
            '<ul><li><a href="https://mopsov.twse.com.tw/mops/web/t56sb31_q1">MOPS financial-report corrections</a> '
            '· Listed companies, year 115, quarters 2 and 3</li>'
            '<li><a href="https://mopsov.twse.com.tw/mops/web/t164sb05">MOPS consolidated cash flow</a> '
            '· Issuer 3711, year 115, quarters 2 and 3</li></ul></details></section>')


def native_quarter_html(archive, *, show_comparisons=True):
    """Render qualified table evidence with a distinct panel for each duration."""
    if not archive:
        return ''
    periods = {row['kind']: row for row in archive['periods']}
    cash_review = archive.get('cash_reconciliation')
    panels = []
    for kind, title in (('quarterly', 'Direct quarter'), ('cumulative', 'Year to date')):
        row = periods.get(kind)
        panels.append(f'<h4>{title}</h4>')
        if row is None:
            if kind in archive.get('excluded_kinds', []):
                panels.append('<p>Check filing coverage for the current evidence on this reporting basis.</p>')
            else:
                panels.append('<p>Year-to-date values are unavailable in this results document.</p>')
            continue
        basis = [row['period_start'] + ' to ' + row['period_end'], row['unit']]
        if row.get('unaudited'):
            basis.append('Unaudited')
        if row['provisional']:
            basis.append('Provisional when published')
        lines, definitions = [], []
        for key in (*row['fields'], *row['withheld_fields']):
            field = row['fields'].get(key)
            label = financial_field_label(key, field)
            if field:
                value = f"{field['unit']} {field['value']:,}"
                definitions.append('<li>' + escape(f"{label} · {field['row_label']} · {field['column_header']} · "
                    f"{field['unit_evidence']} · {field['period_evidence']}") + '</li>')
            elif kind == 'cumulative' and key == 'capital_expenditures' and cash_review:
                purchases = cash_review['inputs']['nine_months'][key] * 1000
                value = f'TWD {purchases:,}'
                definitions.append('<li>Capital spending · Gross cash payments for PP&amp;E acquisitions · Note 29(a)</li>')
            else:
                reason = row['withheld_fields'][key]
                explanation = {
                    'non_equivalent_reported_component': REASONS['non_equivalent_reported_component'],
                    'direct_reported_row_unavailable': 'A matching value is absent from this duration in the results document.',
                }.get(reason, reason.replace('_', ' '))
                value = 'Withheld · ' + explanation
            lines.append('<tr><th scope="row">' + escape(label) + '</th><td>' + escape(value) + '</td></tr>')
        panels.append('<p>' + escape(' · '.join(basis)) + '</p><div class="archive-quarter-table"><table>'
                      '<thead><tr><th scope="col">Field</th><th scope="col">Reported value</th></tr></thead><tbody>'
                      + ''.join(lines) + '</tbody></table></div><details><summary>Field definitions</summary><ul>'
                      + ''.join(definitions) + '</ul></details>')
    if show_comparisons and archive.get('ase_net_ppe_payments'):
        net = archive['ase_net_ppe_payments']
        panels.append(ase_net_ppe_html({kind: net[kind] for kind in periods if kind in net}))
    if show_comparisons and 'quarterly' in periods:
        from src.sec_tsm_quarter_cash import is_reviewed_cash_scope

        if is_reviewed_cash_scope(archive):
            panels.append(tsm_cash_reconciliation_html(cash_review))
        panels.append(native_quarter_comparisons_html(periods['quarterly'], archive.get('comparative_periods', ()),
                                                      archive.get('comparative_gaps')))
    refs = ''.join('<li><a target="_blank" rel="noopener noreferrer" href="' + escape(r['source_url'], quote=True)
                   + '">SEC document</a> · observed ' + escape(r['observed_at']) + ' · SHA-256 '
                   + escape(r['payload_sha256']) + '</li>' for r in archive['source_receipts'])
    return (_STYLE + '<section class="company-archive-quarter" aria-label="Exact SEC native-currency results">'
            '<h3>Exact SEC native-currency results</h3><p>'
            + escape(f"{archive['form']} · Filed {archive['filed']} · Accession {archive['accession']}") + '</p>'
            + ''.join(panels) + '<details><summary>SEC source and reporting basis</summary>'
            '<p><a target="_blank" rel="noopener noreferrer" href="' + escape(archive['source_url'], quote=True)
            + '">Open exact SEC results document</a></p><p>Reported consolidated results · Personal inspection only.</p><p>'
            + escape('Accepted ' + archive['accepted_at'] + ' · Observed ' + archive['observed_at'])
            + '</p><ul>' + refs + '</ul></details></section>')
