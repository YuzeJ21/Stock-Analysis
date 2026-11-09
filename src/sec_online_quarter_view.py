"""Projection of independently validated archive quarters; no source transport."""
from copy import deepcopy
from html import escape

from src.online_research_expansion_view import financial_field_label


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
    return ('<style>.company-archive-quarter{min-width:0;overflow-wrap:anywhere;margin:16px 0;padding:16px;background:#fff;color:#172522;border:1px solid #dce3de;border-radius:8px}.archive-quarter-table{max-width:100%;overflow-x:auto}'
            '.company-archive-quarter p,.company-archive-quarter th,.company-archive-quarter td,.company-archive-quarter li,.company-archive-quarter summary{color:#172522!important}.company-archive-quarter a{color:#245842!important}'
            '.archive-quarter-table table{width:100%;font-size:.86rem;border-collapse:collapse}.archive-quarter-table th,.archive-quarter-table td{padding:8px;text-align:left;border-bottom:1px solid #dce3de}'
            '.company-archive-quarter summary{cursor:pointer;min-height:44px;align-content:center}.company-archive-quarter summary:focus-visible{outline:3px solid #245842}</style>'
            '<section class="company-archive-quarter" aria-label="Exact SEC quarter"><h3>Exact SEC quarter</h3><p>'
            + escape(archive['form'] + ' · filed ' + archive['filed'] + ' · accession ' + archive['accession'] + ' · CIK ' + archive['sec_cik']) + '</p>' + ''.join(panels)
            + '<details><summary>Source and reporting basis</summary><p>Directly reported parent-issuer facts from the exact SEC filing. Companyfacts coverage remains separate. No quarter is derived by subtraction; no missing component is inferred.</p>'
            + '<p>Personal inspection only · archive source rights are unregistered. Commercial use, redistribution and saved-model readiness remain unapproved.</p><p>'
            + escape('Accepted ' + archive['accepted_at'] + ' · Observed ' + archive['observed_at']) + '</p><ul>' + refs + '</ul></details></section>')
