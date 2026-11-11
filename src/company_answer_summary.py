"""Read-only first-screen answers from the existing Workbench observations."""

from collections.abc import Mapping
from html import escape
import re

from src.company_sec_online_preview import _iso_date
from src.online_company_identity import _mode_reason, validated_price_filing_association
from src.online_company_prices import price_source_url
from src.online_history_contract import validated_annual_history
from src.online_peer_valuation import FISCAL_WINDOW_DAYS, MIN_PEERS
from src.online_peer_valuation_ui import _link, _multiple, _number, _reason
from src.online_research_history_view import validated_online_price_history
from src.sec_native_quarter_comparisons import BASES, quarter_changes
from src.sec_quarterly_history import validated_quarterly_history


COMPANY_ANSWERS_STYLE = """
.company-answer-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0;min-width:0}
.company-answer-summary .company-answer{min-width:0;padding:12px 14px;background:#fff;color:#172522;border:1px solid #dce3de;border-radius:8px;overflow-wrap:anywhere}
.company-answer-summary .company-answer h2{margin:0 0 4px!important;padding:0!important;font-size:.88rem!important;line-height:1.35;color:#42564e}
.company-answer-summary .company-answer p{margin:0 0 4px;line-height:1.4}
.company-answer-summary .company-answer-value{font-size:1.1rem;font-weight:750}
.company-answer-summary .company-answer-context{font-size:.82rem;color:#42564e}
.company-answer-summary summary{display:list-item;align-content:center;width:fit-content;min-height:44px;cursor:pointer;font-size:.83rem;color:#245842}
.company-answer-summary ul{margin:4px 0 0;padding-left:20px;font-size:.83rem}
.company-answer-summary li{margin:4px 0}
.company-answer-summary a{color:#245842;text-decoration:underline}
.company-answer-summary summary:focus-visible,.company-answer-summary a:focus-visible{outline:3px solid #245842;outline-offset:2px}
.company-observation-context{display:flex;flex-wrap:wrap;gap:6px 18px;margin:8px 0}
.company-observation-context div{flex:1 1 15rem;min-width:0;overflow-wrap:anywhere}
.company-observation-context dt{font-size:.78rem;font-weight:600}
.company-observation-context dd{margin:3px 0;font-size:.85rem;line-height:1.4}
.company-observation-context a{font-size:.78rem;text-decoration:underline}
@media(max-width:700px){
  .company-answer-summary{grid-template-columns:minmax(0,1fr);gap:6px;margin:10px 0}
  .company-answer-summary .company-answer{display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:8px;padding:8px 10px}
  .company-answer-summary .company-answer h2,.company-answer-summary .company-answer-value,.company-answer-summary .company-answer-context{grid-column:1}
  .company-answer-summary .company-answer details{grid-column:1/-1}
  .company-answer-summary .company-answer details:not([open]){grid-column:2;grid-row:1/4;align-self:center}
  .company-answer-summary .company-answer-value{font-size:1rem}
}
@media(max-width:300px){.company-answer-summary .company-answer{display:block}}
@media(forced-colors:active){.company-answer-summary summary:focus-visible,.company-answer-summary a:focus-visible{outline-color:Highlight}}
"""

_TITLES = {'price': 'Latest close', 'financial': 'Financial changes', 'valuation': 'Peer valuation'}
_GAP_VALUES = {'price': 'Close needs verification', 'financial': 'Financial changes need verification', 'valuation': 'Peer comparison unavailable'}
_PRICE_GAPS = {
    'price_source_unavailable': 'Price source is unavailable',
    'no_completed_daily_prices': 'Completed daily closes are unavailable',
    'price_symbol_or_security_type_mismatch': 'Price symbol or security type is unverified',
    'unsupported_price_currency': 'Price currency is unverified',
}
_FINANCIAL_GAPS = {
    'sec_user_agent_required': 'An identifying SEC user agent is required.',
    'sec_fetch_unavailable': 'The SEC financial source is unavailable.',
}


def _card(key, value, context, evidence=(), links=()):
    return dict(key=key, title=_TITLES[key], value=value, context=context, evidence=evidence, links=links)


def _price_answer(ticker, prices, association):
    price = validated_online_price_history(prices, ticker=ticker)
    if price is None:
        source = prices if isinstance(prices, Mapping) else {}
        if source.get('status') in {None, 'not_requested'}:
            return _card('price', 'Close not requested', 'Refresh financials and prices to load an observation.',
                         ('The result shows a completed daily close and its trading date.',))
        reason = _PRICE_GAPS.get(source.get('reason'))
        links = (('Yahoo daily price request', price_source_url(ticker.replace('.', '-'))),) if reason and source.get('ticker') == ticker else ()
        reason = reason or 'The closing price source is unverified'
        return _card('price', _GAP_VALUES['price'], reason, (reason,), links)
    bar = price['bars'][-1]
    listing = validated_price_filing_association(association)
    matched = listing and listing['ticker'] == ticker and all(
        listing['source_receipts'][1].get(key) == price.get(key) for key in ('observed_at', 'payload_sha256'))
    scope = 'The quote venue matches the listing record.' if matched else 'The provider symbol is matched. Listing association needs its own check.'
    status = 'Stale date; recent close needs verification' if price.get('observation_state') == 'stale_observation' else 'Completed close'
    return _card('price', f"{price['currency']} {bar['close']:,.2f}", f"{bar['date']} · {status}",
                 (f"Observed {price['observed_at']} · Provider symbol {price['provider_symbol']}", scope,
                  'Historical close observation. Split and dividend adjustments require separate checks.'),
                 (('Yahoo daily price source', price['source_url']),))


def _comparable_revenue(financial, period, kind, unit='USD'):
    if kind == 'annual':
        history = validated_annual_history(financial) if financial.get('status') == 'inspection_only' else None
        if history and history['unit'] == unit:
            for comparison in history['comparisons']:
                if comparison['to_period'] == period and comparison['status'] == 'comparable':
                    prior = next(row for row in history['periods'] if row['period_end'] == comparison['from_period'])
                    return 'vs prior fiscal year', comparison['direction'], prior['period_end'], prior['revenue']
    if kind != 'quarterly':
        return None
    history = validated_quarterly_history(financial)
    from src.sec_online_quarter_evidence import validated_archive_quarter
    from src.sec_online_quarter_view import merge_archive_quarter
    archive = validated_archive_quarter(financial)
    if archive:
        history = dict(unit=archive['unit'], periods=merge_archive_quarter(history['periods'] if history else [], archive))
    if not history or history['unit'] != unit:
        return None
    periods = history['periods']
    current = next((row for row in periods if row['period_end'] == period and row['status'] == 'available'), None)
    if current is None:
        return None
    start, end = _iso_date(current['period_start']), _iso_date(period)
    matches = []
    for row in periods:
        if row['status'] != 'available':
            continue
        prior_start, prior_end = _iso_date(row['period_start']), _iso_date(row['period_end'])
        if (351 <= (start - prior_start).days <= 379 and 351 <= (end - prior_end).days <= 379
            and abs((end - start).days - (prior_end - prior_start).days) <= 14):
            matches.append(row)
    if len(matches) != 1:
        return None
    prior = matches[0]
    if any(current['fields']['revenue'].get(key) != prior['fields']['revenue'].get(key)
           for key in ('taxonomy', 'concept', 'unit')):
        return None
    latest_value, prior_value = current['fields']['revenue']['value'], prior['fields']['revenue']['value']
    direction = 'increased' if latest_value > prior_value else 'decreased' if latest_value < prior_value else 'unchanged'
    return 'vs prior-year quarter', direction, prior['period_end'], prior_value


def _money(currency, value):
    for scale, suffix in ((1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if abs(value) >= scale:
            return f'{currency} {value / scale:,.2f}{suffix}'
    return f'{currency} {value:,.0f}' if value % 1 == 0 else f'{currency} {value:,.2f}'


def _direction(current, prior):
    return 'increased' if current > prior else 'decreased' if current < prior else 'unchanged'


def _change_headline(label, current, prior, direction):
    if direction == 'unchanged':
        return f'{label} unchanged'
    if prior > 0:
        change = abs(current - prior) / prior * 100
        if _number(change):
            amount = f'{change:,.1f}%' if change >= .05 else '<0.1%'
            return f"{label} {'up' if direction == 'increased' else 'down'} {amount}"
    return f'{label} {direction}'


def _financial_answer(projection, financial):
    financial = financial if isinstance(financial, Mapping) else {}
    fact = projection.get('facts', {}).get('revenue')
    if not fact:
        if financial.get('status') in {None, 'not_requested'}:
            message = 'Financials have not been requested. Refresh financials and prices to load a verified period.'
        else:
            message = _FINANCIAL_GAPS.get(financial.get('reason'), 'The request returned no verified reported revenue.')
        return _card('financial', _GAP_VALUES['financial'], message, (message,))
    start, end, kind = (projection[key] for key in ('period_start', 'period_end', 'period_kind'))
    unit, value = fact['unit'], fact['value']
    observed = fact.get('observed_at') or fact.get('observed_at_utc')
    accession = fact.get('accession')
    evidence = [f"{'Direct quarter' if kind == 'quarterly' else 'Reported annual period'} {start} to {end} · {unit} {value:,}",
                f"Concept {fact.get('taxonomy', '')}:{fact.get('concept', '')}",
                f"Filing {accession or 'Unavailable'} · Observed {observed or 'Unavailable'}"]
    filed = projection.get('filed') or fact.get('filed')
    if _iso_date(filed):
        evidence.append(f'Filed {filed}')
    exact = fact.get('reported_numeric_schema') == 'sec-reported-numeric-v1'
    native_quarter = projection.get('native_quarter_selected') is True
    source_label = 'Exact SEC results document' if native_quarter else 'Exact SEC filing fact' if exact else 'SEC financial facts'
    links = [(source_label, fact['source_ref'])] if fact.get('source_ref') else []
    if exact or native_quarter:
        evidence.append('Exact archive source · Personal inspection only; commercial rights and saved-model readiness remain unapproved.')
    if native_quarter:
        row = next(p for p in projection['native_quarter_archive']['periods'] if p['kind'] == 'quarterly')
        evidence.append(f"Reported consolidated table · {fact['row_label']} · {fact['column_header']}")
        if row['provisional']:
            evidence.append('The results release identified these figures as provisional when published.')
        if row.get('unaudited'):
            evidence.append('The reported table is unaudited.')
    cik = financial.get('sec_cik')
    if isinstance(cik, str) and re.fullmatch(r'\d{10}', cik) and isinstance(accession, str) and re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
        links.append(('SEC filing index', f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{accession}-index.htm'))
    label = 'Revenue net of interest expense' if fact.get('concept') == 'RevenuesNetOfInterestExpense' else 'Revenue'
    value_text = f'{label} {_money(unit, value)}'
    change_label = 'Net revenue' if label != 'Revenue' else label
    comparison_value = value
    comparison_label = 'Year over year'
    native_comparison_gaps = []
    native_annual = exact and kind == 'annual' and unit != 'USD'
    if native_annual:
        prior = projection.get('comparative') or {}
        field_name = prior.get('field')
        current = projection['facts'].get(field_name, {})
        prior_value = prior.get('value')
        comparison = None
        if (field_name in {'revenue', 'operating_income'} and current.get('unit') == unit
                and _number(current.get('value')) and current['value'] == prior.get('current_value')
                and _number(prior_value) and _iso_date(prior.get('period_end'))):
            comparison_value = current['value']
            comparison = ('vs prior fiscal year', _direction(comparison_value, prior_value),
                          prior['period_end'], prior_value)
            if field_name == 'operating_income':
                change_label = 'Operating income'
                evidence.append(f'Operating income for this period · {unit} {comparison_value:,}')
                if current.get('source_ref'):
                    links.append(('Exact SEC operating income fact', current['source_ref']))
            if prior.get('source_ref'):
                links.append((f'Prior {change_label.lower()} source', prior['source_ref']))
    elif native_quarter:
        comparison = None
        results = quarter_changes(row, projection['native_quarter_archive'].get('comparative_periods', ()))
        for basis, description in BASES.items():
            change = results.get(basis, {}).get('fields', {}).get('revenue', {})
            if not change.get('prior'):
                native_comparison_gaps.append(description + ' revenue needs verification')
                continue
            prior = change['prior']
            comparison_note = (_change_headline(change_label, value, prior['value'], _direction(value, prior['value']))
                               if change['fraction'] is not None else 'Percentage needs a positive baseline')
            evidence.append(f"{description} · {prior['period_start']} to {prior['period_end']} · "
                            f"{unit} {prior['value']:,} · {prior['column_header']} · {comparison_note}")
            if change['fraction'] is None:
                native_comparison_gaps.append(description + ' revenue percentage needs a positive baseline')
                continue
            if comparison is None:
                comparison_label = 'Year over year' if basis == 'year_over_year' else 'Quarter over quarter'
                comparison = ('vs ' + description.lower(), _direction(value, prior['value']), prior['period_end'], prior['value'])
    else:
        comparison = _comparable_revenue(financial, end, kind, unit)
    context = f'Period ended {end}'
    extra = {'native_archive_annual': native_annual, 'headline_context': context}
    if native_quarter:
        extra['native_quarter_end'] = end
        extra['native_comparison_gaps'] = native_comparison_gaps
    if comparison:
        basis, direction, prior_date, prior_value = comparison
        context += f' · {change_label} {direction} {basis}'
        evidence.append(f'Comparison period ended {prior_date} · {change_label} {unit} {prior_value:,}.')
        period_label = 'quarter ended' if kind == 'quarterly' else 'year ended'
        extra.update(headline=_change_headline(change_label, comparison_value, prior_value, direction),
                     headline_context=f'{comparison_label} · {period_label} {end} · {value_text}')
        if change_label == 'Operating income':
            extra['gap'] = 'Revenue comparison needs verification'
            evidence.append('A comparable revenue baseline or reporting basis is unverified.')
    else:
        context += ' · Comparable change needs verification'
        evidence.append('A comparable baseline or reporting basis is unverified.')
        extra['gap'] = 'Comparable financial change needs verification'
    if projection.get('withheld_periods'):
        context += ' · Newer period needs verification'
        evidence.extend(f"Newer period ended {row['period_end']}. See Data Sources for details." for row in projection['withheld_periods'])
        extra['headline_context'] += ' · Newer period needs verification'
    return dict(_card('financial', value_text, context, tuple(evidence), tuple(links)), **extra)


def _annual_filing_links(label, context):
    if not isinstance(context, Mapping):
        return []
    return [
        (f"{label} {row['form']} (filing record)", row['source_ref'])
        for row in context.get('annual_versions', ())
        if isinstance(row, Mapping) and row.get('form') and row.get('source_ref')
    ]


def _valuation_answer(ticker, view, *, native_archive_annual=False):
    method = f'Reported annual diluted P/E · Same-day closes · Fiscal-year window {FISCAL_WINDOW_DAYS} days · At least {MIN_PEERS} references'
    if not isinstance(view, Mapping) or view.get('status') == 'not_requested':
        return _card('valuation', 'Peer valuation not checked', 'Open Valuation & Peers to request a comparison.', (method,))
    if view.get('ticker') != ticker:
        return _card('valuation', _GAP_VALUES['valuation'], 'No verified peer observation for this security.', (method,))
    subject = view.get('subject')
    subject = subject if isinstance(subject, Mapping) and subject.get('ticker') == ticker else {}
    day = subject.get('price_date')
    peers = view.get('peers')
    peers = peers if isinstance(peers, list) else []
    count = view.get('peer_count')
    valid_count = type(count) is int and count == len(peers) and all(isinstance(row, Mapping) for row in peers)
    context_parts = [f'{day} close'] if _iso_date(day) else []
    checked = view.get('checked_candidate_count')
    if type(checked) is int and checked >= 0:
        context_parts.append(f'{checked} candidates checked')
    if subject and valid_count:
        context_parts.append(f'{count} eligible references')
    evidence = [method]
    links = [('Industry candidate source', view['industry_source_ref'])] if view.get('industry_source_ref') else []
    for label, key in (('Company annual filing', 'filing_ref'), ('Company price source', 'price_source_ref')):
        if subject.get(key):
            links.append((label, subject[key]))
    if not subject:
        source = view.get('subject_source_context')
        links.extend(_annual_filing_links('Company', source))
        dates = source.get('close_date_observation') if isinstance(source, Mapping) else None
        if isinstance(dates, Mapping) and _iso_date(dates.get('quote_day')) and _iso_date(dates.get('close_day')):
            evidence.append(f"Provider quote date {dates['quote_day']} · Daily close {dates['close_day']}.")
            for label, key in (('Company provider quote source', 'quote_source_ref'), ('Company daily price source', 'close_source_ref')):
                if dates.get(key):
                    links.append((label, dates[key]))
        listing = view.get('listing_context')
        if isinstance(listing, Mapping) and view.get('reason') in {
            'listing_classification_unavailable', 'selected_listing_or_cik_unverified',
        }:
            for label, key in (('Listing source request', 'source_attempts'), ('Listing verification source', 'source_receipts')):
                links.extend((label, row['source_url']) for row in listing.get(key, ())
                             if isinstance(row, Mapping) and row.get('source_url'))
    amendment = subject.get('amendment_scope')
    if isinstance(amendment, Mapping) and amendment.get('status') == 'supported':
        receipts = amendment.get('source_receipts', ())
        if len(receipts) == 2 and isinstance(receipts[1], Mapping) and receipts[1].get('source_url'):
            links.append(('Company annual amendment source', receipts[1]['source_url']))
    if subject and _number(subject.get('multiple')) and subject['multiple'] > 0:
        evidence.append(f"Company annual P/E {_multiple(subject['multiple'])}.")
    supported = (
        view.get('status') == 'research_comparison' and view.get('metric') == 'reported_annual_diluted_pe'
        and _iso_date(day) and valid_count and count >= MIN_PEERS
        and all(isinstance(row.get('ticker'), str) and row.get('price_date') == day for row in peers)
        and _number(subject.get('multiple')) and subject['multiple'] > 0
        and _number(view.get('peer_median')) and view['peer_median'] > 0 and _number(view.get('premium_fraction'))
    )
    if supported:
        premium = view['premium_fraction']
        magnitude = f'{abs(premium) * 100:.1f}%' if abs(premium) >= .0005 else '<0.1%'
        value = ('Annual P/E matches industry references' if premium == 0 else
                 f"Annual P/E {magnitude} {'above' if premium > 0 else 'below'} industry references")
        evidence.append(f"Industry-reference median {_multiple(view['peer_median'])} · " + ', '.join(row['ticker'] for row in peers))
        for peer in peers:
            for label, key in (('Annual filing', 'filing_ref'), ('Daily price source', 'price_source_ref')):
                if peer.get(key):
                    links.append((f"{peer['ticker']} {label}", peer[key]))
    else:
        reason = _reason(view.get('reason'))
        if view.get('status') == 'research_comparison':
            reason = 'Reference count, multiple, or same-day close evidence is unverified.'
        value = _GAP_VALUES['valuation']
        short_reason = reason
        if native_archive_annual and view.get('reason') == 'latest_annual_filing_not_corroborated':
            short_reason = 'Annual EPS on the traded security basis needs verification.'
        context_parts.insert(0, short_reason)
        evidence.append(reason)
        if not subject:
            evidence.append('Company evidence is unverified. Industry references have not been checked.')
    for row in view.get('excluded') or ():
        if not isinstance(row, Mapping) or not row.get('ticker'):
            continue
        symbol = row['ticker']
        evidence.append(f"{symbol} · {_reason(row.get('reason'))}")
        diagnostics = row.get('diagnostics')
        if not isinstance(diagnostics, Mapping):
            continue
        eps = diagnostics.get('annual_eps_observation')
        if isinstance(eps, Mapping) and eps.get('filing_ref'):
            links.append((f'{symbol} Annual filing (excluded)', eps['filing_ref']))
        else:
            links.extend(_annual_filing_links(symbol, diagnostics))
        price = diagnostics.get('price_observation')
        if isinstance(price, Mapping) and price.get('source_ref'):
            links.append((f'{symbol} Daily price source (excluded)', price['source_ref']))
        audit = diagnostics.get('annual_eps_audit')
        if isinstance(audit, Mapping) and audit.get('source_url'):
            links.append((f'{symbol} Annual EPS source', audit['source_url']))
    return _card('valuation', value, ' · '.join(context_parts), tuple(evidence), tuple(links))


def build_company_answers(ticker, projection, financial, prices, association, peer_view):
    """Return display cards without fetching data or changing saved research."""
    if _mode_reason('research') or projection.get('identity_conflict'):
        reason = 'Company or security identity conflicts. Values are withheld.' if projection.get('identity_conflict') else 'Personal research observations are unavailable in this workspace.'
        return tuple(_card(key, _GAP_VALUES[key], reason, (reason,)) for key in _TITLES)
    financial_answer = _financial_answer(projection, financial)
    return (_price_answer(ticker, prices, association), financial_answer,
            _valuation_answer(ticker, peer_view, native_archive_annual=financial_answer.get('native_archive_annual', False)))


def company_answers_html(answers, *, compact=False, gaps=()):
    """Render escaped cards and native evidence disclosures in both surfaces."""
    if compact:
        rows = []
        for answer in answers:
            value = answer['context'] if answer['key'] == 'financial' else answer['value'] + ' · ' + answer['context']
            links = answer.get('links', ())
            source = _link(links[0][1], 'Source') if links else ''
            rows.append('<div><dt>' + escape(answer['title']) + '</dt><dd>' + escape(value)
                        + ' ' + source + '</dd></div>')
        return '<dl class="company-observation-context" aria-label="Loaded company observations">' + ''.join(rows) + '</dl>'
    cards = []
    for answer in answers:
        title, value, context = (escape(answer[key]) for key in ('title', 'value', 'context'))
        lines = ''.join(f'<li>{escape(line)}</li>' for line in answer['evidence'])
        links = ''.join(f'<li>{_link(url, label)}</li>' for label, url in answer.get('links', ()))
        cards.append(
            f'<article class="company-answer" data-company-answer="{escape(answer["key"], quote=True)}">'
            f'<h2>{title}</h2><p class="company-answer-value">{value}</p>'
            f'<p class="company-answer-context">{context}</p>'
            f'<details><summary aria-label="View {title.lower()} evidence">View evidence</summary><ul>{lines}{links}</ul></details></article>'
        )
    gap_strip = ('<aside class="company-answer-gaps" aria-label="Research gaps"><strong>Research gaps</strong>'
                 '<span>' + escape(' · '.join(gaps)) + '</span></aside>') if gaps else ''
    return '<section class="company-answer-summary" aria-label="Company research summary">' + ''.join(cards) + gap_strip + '</section>'
