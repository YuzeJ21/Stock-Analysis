"""Projection of independently validated archive quarters; no source transport."""
from copy import deepcopy
from html import escape

from src.online_research_expansion_view import financial_field_label
from src.sec_native_quarter_comparisons import BASES, REASONS, quarter_changes

_STYLE = ('<style>.company-archive-quarter{min-width:0;overflow-wrap:anywhere;margin:16px 0;padding:16px;background:#fff;color:#172522;border:1px solid #dce3de;border-radius:8px}.archive-quarter-table{max-width:100%;overflow-x:auto}'
          '.company-archive-quarter p,.company-archive-quarter th,.company-archive-quarter td,.company-archive-quarter li,.company-archive-quarter summary{color:#172522!important}.company-archive-quarter a{color:#245842!important}'
          '.archive-quarter-table table{width:100%;font-size:.86rem;border-collapse:collapse}.archive-quarter-table th,.archive-quarter-table td{padding:8px;text-align:left;border-bottom:1px solid #dce3de}'
          '.company-archive-quarter summary{cursor:pointer;min-height:44px;align-content:center}.company-archive-quarter summary:focus-visible{outline:3px solid #245842}</style>')


def merge_archive_quarter(rows, archive):
    """Replace a whole missing/version-mismatched row, never individual fields."""
    result = deepcopy(rows)
    if not archive:
        return result
    quarter = next((r for r in archive['periods'] if r['kind'] == 'quarterly'), None)
    if not quarter:
        return result
    existing = next((r for r in result if r['period_end'] == quarter['period_end']), None)
    if existing and existing['status'] == 'available' and all(existing.get(k) == quarter.get(k) for k in ('accession', 'form', 'filed')):
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
            + '<details><summary>Source and reporting basis</summary><p>Directly reported parent-issuer facts from the exact SEC filing. Companyfacts coverage remains separate. No quarter is derived by subtraction; no missing component is inferred.</p>'
            + '<p>Personal inspection only · archive source rights are unregistered. Commercial use, redistribution and saved-model readiness remain unapproved.</p><p>'
            + escape('Accepted ' + archive['accepted_at'] + ' · Observed ' + archive['observed_at']) + '</p><ul>' + refs + '</ul></details></section>')


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


def native_quarter_html(archive, *, show_comparisons=True):
    """Render qualified table evidence with a distinct panel for each duration."""
    if not archive:
        return ''
    periods = {row['kind']: row for row in archive['periods']}
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
    if show_comparisons and 'quarterly' in periods:
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
