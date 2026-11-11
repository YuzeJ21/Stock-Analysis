"""Personal native-currency reporting from an exact SEC 6-K statement."""
from __future__ import annotations

from calendar import monthrange
from collections.abc import Mapping
from copy import deepcopy
from datetime import timedelta
import hashlib
from html.parser import HTMLParser
import re
import time
from urllib.error import HTTPError
from urllib.request import Request

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_filing_context import _digest, _now, _ref, _sort, validated_filing_inventory
from src.online_sec_receipt import open_exact_source
from src.providers.sec_company_discovery import _modified_at
from src.sec_exact_filing import MAP_URL, RIGHTS
from src.sec_foreign_financials import validated_foreign_financials
from src.sec_online_annual_evidence import validated_archive_annual
from src.sec_online_quarter_evidence import _REF_KEYS, _held, _identity_inventory, _json, _receipt_gap

SCHEMA = 'sec-online-native-quarter-v1'
SOURCE_ID = 'sec_archive_native_quarter_html'
TAXONOMY = 'reported_consolidated_table'
MAX_PRIMARY_REQUESTS = 8
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_DTO_BYTES = 128 * 1024
MAX_EVENT_AGE = timedelta(days=180)
_FORMS = frozenset({'6-K', '6-K/A'})
_FIELD_NAMES = frozenset({'revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures'})
_UNAVAILABLE = 'native_quarter_evidence_unavailable'
_HOST = 'https://www.sec.gov'
_ARCHIVE_URL = re.compile(r'https://www\.sec\.gov/Archives/edgar/data/([1-9]\d{0,9})/(\d{18})/([A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml))\Z')
_DOCUMENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)\Z')
_QUARTER = re.compile(r'\b(?:(?:first|second|third|fourth|[1-4](?:st|nd|rd|th))\s+quarter|quarterly|quarter\s+ended|three\s+months\s+ended)\b', re.I)
_RESULTS = re.compile(r'\b(?:financial\s+results|earnings\s+release|quarterly\s+results|consolidated\s+results|consolidated\s+statement(?:s)?\s+of\s+income|reports?\s+(?:\w+\s+){0,3}quarter\s+(?:eps|earnings))\b', re.I)
_PRESS = re.compile(r'\b(?:press|news)\s+release\b', re.I)
_QUARTER_SLIDES = re.compile(r'\bquarter\s+earnings\s+conference\s+presentation\b', re.I)
_REVISION = re.compile(r'\b(?:amended|corrected|revised|restated|replacement)\b.{0,45}\b(?:financial\s+(?:statements|results)|earnings\s+release)\b', re.I)
_HIDDEN = re.compile(r'(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)\s*(?:!important\s*)?(?:;|$)', re.I)
_PROVISIONAL_COLUMN = re.compile(r'[1-4]Q(?:\d{2}|\d{4})\s*Amount\s*a', re.I)
_UNRELATED = {
    'monthly_revenue': re.compile(r'\b(?:monthly\s+(?:net\s+)?(?:revenue|sales)(?:\s+report|s)?|(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+20\d{2})?\s+revenue\s+report)\b', re.I),
    'board_resolutions': re.compile(r'\bboard\s+of\s+directors\s+meeting\s+resolutions\b', re.I),
    'monthly_security_activity': re.compile(r'\bchanges\s+in\s+the\s+shareholdings\b.{0,450}\b(?:assets|unsecured\s+bonds)\b', re.I),
}
_METADATA = ('ticker', 'sec_cik', 'accession', 'form', 'filed', 'accepted_at', 'report_date',
             'primary_document', 'primary_source_url', 'source_url', 'source_id', 'observed_at',
             'payload_sha256', 'fiscal_year_end', 'rights_status')
_PACKET_KEYS = set(_METADATA) | {'schema_version', 'status', 'reason', 'period_end', 'period_kind', 'taxonomy',
    'unit', 'periods', 'source_receipts', 'reviewed_preceding', 'selection', 'inventory_digest', 'packet_digest',
    'commercial_eligible', 'readiness_promoted', 'saved_readiness_promoted'}
_COMPARATIVE_PACKET_KEYS = {'comparative_periods', 'comparative_gaps'}
_COMPARISON_MONTHS = {'year_over_year': 12, 'sequential': 3}
_COMPARISON_KEYS = ('comparison_basis', 'current_period_end')
_COMPARISON_UNAVAILABLE = 'same_filing_comparison_unavailable'
_COMPARISON_REVISION = 'independent_comparison_revision_unresolved'


def _clean(parts):
    return ' '.join(' '.join(parts).split())


class _Cover(HTMLParser):
    """Collect visible text and the anchor labels and links in exhibit rows."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.rows = []
        self.stack = []
        self.ignored = None
        self.ignored_depth = 0
        self.has_base = False

    def handle_starttag(self, tag, attrs):
        if tag == 'base':
            self.has_base = True
        elif self.ignored:
            if tag == self.ignored:
                self.ignored_depth += 1
        else:
            attributes = dict(attrs)
            hidden = ('hidden' in attributes or (attributes.get('aria-hidden') or '').lower() == 'true'
                      or _HIDDEN.search(attributes.get('style') or ''))
            if tag in {'head', 'script', 'style', 'noscript', 'template', 'ix:hidden'} or hidden:
                if tag not in {'br', 'hr', 'img', 'input', 'link', 'meta', 'col', 'source', 'wbr'}:
                    self.ignored = tag
                    self.ignored_depth = 1
            elif tag == 'tr':
                self.stack.append(([], []))
            elif tag == 'a' and self.stack:
                self.stack[-1][1].extend(value for key, value in attrs if key == 'href')

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored:
                self.ignored_depth -= 1
                if self.ignored_depth == 0:
                    self.ignored = None
        elif tag == 'tr' and self.stack:
            parts, links = self.stack.pop()
            if links:
                self.rows.append((_clean(parts), links))

    def handle_data(self, data):
        if not self.ignored:
            self.text.append(data)
            if self.stack:
                self.stack[-1][0].append(data)


def _has_results(text):
    return bool(_QUARTER.search(text) and _RESULTS.search(text))


def _exhibit_url(primary_url, href):
    if not isinstance(href, str) or not 0 < len(href) <= 400 or '..' in href:
        return None
    directory = primary_url.rsplit('/', 1)[0]
    if _DOCUMENT.fullmatch(href):
        result = f'{directory}/{href}'
    elif href.startswith('/Archives/'):
        result = _HOST + href
    else:
        result = href
    if (result != primary_url and _ARCHIVE_URL.fullmatch(result)
            and result.rsplit('/', 1)[0] == directory):
        return result
    return None


def _classify_cover(raw, primary_url, form='6-K'):
    document = _Cover()
    document.feed(raw.decode('utf-8-sig'))
    document.close()
    text = _clean(document.text)
    forms = {value.upper() for value in re.findall(r'\bform\s+(6-k(?:/a)?)\b', text, re.I)}
    if document.has_base or form not in forms or form == '6-K' and '6-K/A' in forms:
        return 'ambiguous', None
    slides = _QUARTER_SLIDES.search(text)
    exhibits = []
    for label, links in document.rows:
        match = re.fullmatch(r'(99(?:\.\d{1,2})?)\s+(.{1,350})', label)
        if not match:
            continue
        number, description = match.groups()
        qualifier = ('quarterly_results' if _has_results(description) else
                     'quarterly_conference_and_press_release' if _PRESS.search(description) and slides else None)
        if qualifier:
            hrefs = set(links)
            href = next(iter(hrefs)) if len(hrefs) == 1 else None
            url = _exhibit_url(primary_url, href)
            exhibits.append((url, dict(kind='linked_results_exhibit', number=number,
                                       description=description, qualifier=qualifier, href=href,
                                       qualifier_text=slides[0] if qualifier == 'quarterly_conference_and_press_release' else None)))
    if len(exhibits) == 1 and exhibits[0][0]:
        return 'exhibit', exhibits[0][1]
    if exhibits or (_PRESS.search(text) and slides):
        return 'link_unresolved', None
    if _has_results(text) and re.search(r'\b(?:three\s+months\s+ended|consolidated\s+financial\s+results)\b', text, re.I):
        return 'primary', {'kind': 'primary_report'}
    if _REVISION.search(text):
        return 'ambiguous', None
    unrelated = [name for name, pattern in _UNRELATED.items() if pattern.search(text)]
    if len(unrelated) == 1 and not _has_results(text) and not document.rows:
        return 'unrelated', unrelated[0]
    return 'ambiguous', None


def _native_scope(financial, verified, as_of):
    annual = verified['latest']['annual']
    fiscal_year_end = verified['issuer']['fiscal_year_end']
    if not annual or annual['form'] not in {'20-F', '20-F/A'} or not fiscal_year_end:
        return None
    foreign = validated_foreign_financials(financial)
    archive = validated_archive_annual(financial, inventory=verified, as_of=as_of)
    annual_rows = foreign['annual'] if foreign else []
    current = any(row.get('status') == 'available' and all(row.get(k) == annual[k]
                  for k in ('accession', 'period_end', 'form', 'filed')) for row in annual_rows)
    unit = archive['unit'] if archive else foreign['unit'] if current else None
    if unit in {None, 'USD'}:
        return None
    return unit, fiscal_year_end


def _candidate_events(verified, now):
    cutoff = now.date() - MAX_EVENT_AGE
    events = verified['earnings_reports'] + verified.get('metadata_gaps', [])
    return sorted((event for event in events if event['form'] in _FORMS
                   and _iso_date(event['filed']) >= cutoff), key=_sort, reverse=True)


def _same_publication(first, second):
    return (first['filed'], _utc_timestamp(first['accepted_at'])) == (second['filed'], _utc_timestamp(second['accepted_at']))


def _fetch_exact_html(url, user_agent):
    try:
        with open_exact_source(Request(url, headers={'User-Agent': user_agent, 'Accept': 'text/html'}), timeout=15) as response:
            return response.read(MAX_DOCUMENT_BYTES + 1), dict(response.headers.items()), response.geturl()
    finally:
        time.sleep(0.2)


def _read_document(url, *, user_agent, source_fetcher, observed_at):
    raw, headers, final_url = (source_fetcher or _fetch_exact_html)(url, user_agent)
    now = _now(observed_at)
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_DOCUMENT_BYTES
            or final_url != url):
        raise ValueError('unverified_document')
    return raw, dict(source_url=url, observed_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        payload_sha256=hashlib.sha256(raw).hexdigest(), source_last_modified=_modified_at(headers, now))


def _later_structured_quarter(financial, verified, period_end, event):
    foreign = validated_foreign_financials(financial)
    known = [*verified['periods']['quarterly'], *(gap for gap in verified.get('metadata_gaps', [])
             if gap['form'] in {'10-Q', '10-Q/A'})]
    if foreign:
        known.extend(foreign['quarterly'])
    markers = financial.get('reported_period_anchors')
    marker = markers.get('quarterly') if isinstance(markers, Mapping) else None
    if isinstance(marker, Mapping):
        known.append(marker)
    target_end = _iso_date(period_end)
    filing_date = _iso_date(event['filed'])
    for row in known:
        row_end = _iso_date(row.get('period_end'))
        row_filed = _iso_date(row.get('filed'))
        if row_end and (row_end > target_end or row_end == target_end and row_filed and row_filed > filing_date):
            return True
    return False


def _comparison_revision_unresolved(verified, baseline_end, current, structured_rows):
    """Use report-date aliases only to find revisions to a known baseline."""
    reports = verified['earnings_reports']
    gaps = verified.get('metadata_gaps', [])
    structured = [row for row in structured_rows if row.get('period_end') == baseline_end]
    matching_reports = [report for report in reports if any(all(report.get(key) == row.get(key)
                        for key in ('accession', 'form', 'filed')) for row in structured)]
    report_dates = {baseline_end} | {report['report_date'] for report in matching_reports if report['report_date']}
    revisions = matching_reports + [report for report in reports + gaps if report['form'] == '6-K/A'
                                     and report['report_date'] in report_dates]
    revisions.extend(report for report in verified['periods']['quarterly'] + gaps
                     if report['form'] in {'10-Q', '10-Q/A'} and report['period_end'] == baseline_end)
    publication = current['filed'], _utc_timestamp(current['accepted_at'])
    return any(report['accession'] != current['accession']
               and (report['filed'], _utc_timestamp(report['accepted_at'])) >= publication for report in revisions)


def _valid_source_url(value, cik, accession):
    match = _ARCHIVE_URL.fullmatch(value) if isinstance(value, str) else None
    return bool(match and '..' not in match[3] and match[1].zfill(10) == cik
                and match[2] == accession.replace('-', ''))


def _saved_source_matches(field, context, row, observed, source, primary):
    as_of = _utc_timestamp(context.get('observed_at'))
    kind = row.get('kind')
    if (not as_of or observed > as_of or kind not in {'quarterly', 'interim'}
            or row.get('period_basis') != ('year_to_date' if kind == 'interim' else 'direct_quarter')
            or row.get('filing_status') != 'corroborated' or row.get('current') is not True
            or row.get('status') != 'available' or type(row.get('provisional')) is not bool
            or type(row.get('unaudited')) is not bool):
        return False
    coverage = context.get('filing_coverage', {})
    state = coverage.get('current', {}).get(kind, {})
    anchor = state.get('anchor') or {}
    if (state.get('status') != 'corroborated' or state.get('reason') != 'exact_native_quarter_table_and_filing'
            or state.get('source_id') != SOURCE_ID or state.get('rights_status') != RIGHTS
            or state != coverage.get('periods', {}).get(kind, {}).get(row['period_end'])
            or anchor.get('period_kind') != kind or anchor.get('period_basis') != 'exact_native_quarter_table'
            or anchor.get('source_url') != primary
            or any(field.get(k) != anchor.get(k) for k in ('accession', 'form', 'filed', 'accepted_at',
                      'primary_document', 'report_date', 'period_start', 'period_end'))):
        return False
    inventory = validated_filing_inventory(context.get('filing_inventory'), ticker=field['ticker'],
                                          expected_cik=field['sec_cik'], as_of=as_of, allow_historical=True)
    if (not inventory or inventory['issuer']['fiscal_year_end'] != field['fiscal_year_end']
            or not any(all(event.get(k) == anchor.get(k) for k in ('accession', 'form', 'filed', 'accepted_at',
                           'primary_document', 'report_date', 'source_url')) for event in inventory['earnings_reports'])):
        return False
    receipts = context.get('source_receipts')
    if not isinstance(receipts, list):
        return False
    refs = [ref for ref in receipts if isinstance(ref, Mapping) and ref.get('source') == 'exact_native_quarter_receipt']
    urls = [MAP_URL, inventory['source_receipt']['source_url'], primary]
    if source != primary:
        urls.append(source)
    return (len(refs) == len(urls) and all(ref.get('rights_status') == RIGHTS and _ref(ref, url, as_of, True)
            for ref, url in zip(refs, urls)) and all(refs[1].get(k) == inventory['source_receipt'].get(k) for k in _REF_KEYS)
            and all(field.get(k) == refs[-1].get(k) for k in _REF_KEYS))


def valid_native_quarter_field(field, *, context, row, field_name):
    """Recheck a normalized table field before a saved context displays it."""
    try:
        return _valid_field(field, context, row, field_name)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def _valid_field(field, context, row, field_name, *, comparative=False):
    from src.sec_native_quarter_tables import valid_native_table_number

    if (not isinstance(field, Mapping) or field_name not in _FIELD_NAMES
            or not valid_native_table_number(field, fiscal_year_end=field.get('fiscal_year_end'))):
        return False
    if (field.get('field') != field_name or field.get('source_id') != SOURCE_ID
            or field.get('rights_status') != RIGHTS or field.get('form') not in _FORMS
            or field.get('taxonomy') != TAXONOMY or field.get('unit') == 'USD'
            or (_PROVISIONAL_COLUMN.fullmatch(field['column_header']) and row.get('provisional') is not True)):
        return False
    if any(field.get(k) != context.get(k) for k in ('ticker', 'sec_cik')):
        return False
    saved = context.get('schema_version') == 'online-company-research-v1'
    if (any(field.get(k) != row.get(k) for k in ('accession', 'filed', 'form', 'period_start', 'period_end'))
            or field.get('unit') != row.get('currency' if saved else 'unit')):
        return False
    if any(k in row and field.get(k) != row[k] for k in _METADATA):
        return False
    if not comparative and any(key in field or key in row for key in _COMPARISON_KEYS):
        return False
    accession, cik = field.get('accession'), field.get('sec_cik')
    end, filed = (_iso_date(field.get(k)) for k in ('period_end', 'filed'))
    observed, accepted = (_utc_timestamp(field.get(k)) for k in ('observed_at', 'accepted_at'))
    report_date = field.get('report_date')
    if (not isinstance(accession, str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession)
            or not isinstance(cik, str) or not re.fullmatch(r'\d{10}', cik) or not int(cik)
            or not observed or not accepted or not end or not filed or not end <= filed <= observed.date()
            or accepted > observed or accepted.date() < end or report_date is not None and _iso_date(report_date) is None
            or not isinstance(field.get('payload_sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', field['payload_sha256'])):
        return False
    primary, source = (field.get(k) for k in ('primary_source_url', 'source_url'))
    return (_valid_source_url(primary, cik, accession) and _valid_source_url(source, cik, accession)
            and field.get('primary_document') == primary.rsplit('/', 1)[-1]
            and field.get('source_ref') == source and _valid_duration(row, field.get('fiscal_year_end'))
            and (not saved or comparative or _saved_source_matches(field, context, row, observed, source, primary)))


def _comparison_end(current_end, basis):
    end = _iso_date(current_end)
    months = _COMPARISON_MONTHS.get(basis)
    if not end or months is None:
        return None
    year, zero_month = divmod(end.year * 12 + end.month - 1 - months, 12)
    month = zero_month + 1
    return end.replace(year=year, month=month, day=monthrange(year, month)[1]).isoformat()


def _comparison_matches(field, context, row, field_name, current):
    from src.sec_native_quarter_tables import matching_native_quarter_definition

    basis, current_end = (row.get(key) for key in _COMPARISON_KEYS)
    reference = current.get('fields', {}).get(field_name)
    if (row.get('kind') != 'quarterly' or row.get('status') != 'available'
            or current.get('kind') != 'quarterly' or current_end != current.get('period_end')
            or row.get('period_end') != _comparison_end(current_end, basis)
            or type(row.get('provisional')) is not bool or type(row.get('unaudited')) is not bool
            or not isinstance(reference, Mapping) or not _valid_field(field, context, row, field_name, comparative=True)
            or any(field.get(key) != row.get(key) for key in _COMPARISON_KEYS)):
        return False
    return (all(field.get(key) == reference.get(key) for key in _METADATA)
            and matching_native_quarter_definition(reference, field))


def valid_native_quarter_comparative_field(field, *, context, row, field_name):
    """Recheck a saved comparison against its same-report current quarter and receipts."""
    try:
        if context.get('schema_version') != 'online-company-research-v1' or row.get('current') is not False:
            return False
        current = [period for period in context['business_trend']['periods'] if period.get('kind') == 'quarterly'
                   and period.get('current') is True and period.get('period_end') == row.get('current_period_end')]
        if len(current) != 1 or not _comparison_matches(field, context, row, field_name, current[0]):
            return False
        reference = current[0]['fields'][field_name]
        if not valid_native_quarter_field(reference, context=context, row=current[0], field_name=field_name):
            return False
        verified = validated_filing_inventory(context.get('filing_inventory'), ticker=field['ticker'],
                    expected_cik=field['sec_cik'], as_of=_utc_timestamp(context.get('observed_at')), allow_historical=True)
        if not verified:
            return False
        prior = context['filing_coverage']['periods'].get('quarterly', {}).get(row['period_end'], {}).get('anchor')
        return not _comparison_revision_unresolved(verified, row['period_end'], reference, [prior] if prior else [])
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def _valid_duration(row, fiscal_year_end):
    start, end = (_iso_date(row.get(k)) for k in ('period_start', 'period_end'))
    kind = row.get('kind')
    if not start or not end or not isinstance(fiscal_year_end, str) or not re.fullmatch(r'\d{4}', fiscal_year_end):
        return False
    fiscal_month, fiscal_day = int(fiscal_year_end[:2]), int(fiscal_year_end[2:])
    if (not 1 <= fiscal_month <= 12 or fiscal_day != monthrange(2000, fiscal_month)[1]
            or start.day != 1 or end.day != monthrange(end.year, end.month)[1]
            or (end.month - fiscal_month) % 3):
        return False
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    if kind == 'quarterly':
        return months == 3
    return kind in {'cumulative', 'interim'} and months in {6, 9} and start.month == fiscal_month % 12 + 1


def _selection_matches(selection, primary, source):
    if not isinstance(selection, Mapping):
        return False
    if selection.get('kind') == 'primary_report':
        return set(selection) == {'kind'} and primary == source
    if (set(selection) != {'kind', 'number', 'description', 'qualifier', 'qualifier_text', 'href'}
            or selection['kind'] != 'linked_results_exhibit' or not isinstance(selection['number'], str)
            or not re.fullmatch(r'99(?:\.\d{1,2})?', selection['number'])
            or not isinstance(selection['description'], str) or not 0 < len(selection['description']) <= 350
            or _exhibit_url(primary, selection['href']) != source):
        return False
    if selection['qualifier'] == 'quarterly_results':
        return selection['qualifier_text'] is None and _has_results(selection['description'])
    return (selection['qualifier'] == 'quarterly_conference_and_press_release' and bool(_PRESS.search(selection['description']))
            and isinstance(selection['qualifier_text'], str) and bool(_QUARTER_SLIDES.fullmatch(selection['qualifier_text'])))


def _source_receipts_match(wrapper, financial, verified, preceding, event, now):
    receipts = wrapper['source_receipts']
    primary, source = wrapper['primary_source_url'], wrapper['source_url']
    cik = wrapper['sec_cik']
    urls = [MAP_URL, f'https://data.sec.gov/submissions/CIK{cik}.json', primary]
    if primary != source:
        urls.append(source)
    if not isinstance(receipts, list) or len(receipts) != len(urls):
        return False
    if any(not _ref(receipt, url, now) for receipt, url in zip(receipts, urls)):
        return False
    identity = financial['companyfacts_identity']
    mapping = {k: identity['association_' + k] for k in _REF_KEYS}
    if (any(receipts[0][k] != mapping[k] or receipts[1][k] != verified['source_receipt'][k] for k in _REF_KEYS)
            or any(wrapper[k] != receipts[-1][k] for k in ('observed_at', 'payload_sha256'))):
        return False
    reviewed = wrapper['reviewed_preceding']
    if not isinstance(reviewed, list) or len(reviewed) != len(preceding):
        return False
    observed = [_utc_timestamp(ref['observed_at']) for ref in receipts[:2]]
    for record, anchor in zip(reviewed, preceding):
        if (not isinstance(record, Mapping) or set(record) != {'accession', 'reason', 'receipt'}
                or record['accession'] != anchor['accession'] or record['reason'] not in _UNRELATED
                or anchor['amendment'] or not anchor['source_url']
                or not _ref(record['receipt'], anchor['source_url'], now)):
            return False
        stamp = _utc_timestamp(record['receipt']['observed_at'])
        if stamp < _utc_timestamp(anchor['accepted_at']):
            return False
        observed.append(stamp)
    observed.extend(_utc_timestamp(ref['observed_at']) for ref in receipts[2:])
    return observed == sorted(observed) and observed[-1] >= _utc_timestamp(event['accepted_at'])


def _valid_periods(packet):
    periods = packet['periods']
    if not isinstance(periods, list) or not 1 <= len(periods) <= 2:
        return False
    if [row.get('kind') for row in periods] != ['quarterly', 'cumulative'][:len(periods)]:
        return False
    for row in periods:
        fields, withheld = row.get('fields'), row.get('withheld_fields')
        if (row.get('status') != 'available' or row.get('reason') is not None
                or row.get('period_end') != packet['period_end'] or row.get('unit') != packet['unit']
                or any(type(row.get(k)) is not bool for k in ('provisional', 'unaudited'))
                or not _valid_duration(row, packet['fiscal_year_end'])
                or not isinstance(fields, Mapping) or not fields or not isinstance(withheld, Mapping)
                or set(fields) | set(withheld) != _FIELD_NAMES or set(fields) & set(withheld)
                or any(not isinstance(r, str) or not re.fullmatch(r'[a-z0-9_]{1,100}', r) for r in withheld.values())
                or any(row.get(k) != packet[k] for k in _METADATA)):
            return False
        if any(not valid_native_quarter_field(field, context=packet, row=row, field_name=name)
               for name, field in fields.items()):
            return False
    return 'revenue' in periods[0]['fields']


def _valid_comparative_periods(packet, verified, structured_rows):
    if 'comparative_periods' not in packet:
        return True  # original v1 packet shape
    comparisons, gaps = packet['comparative_periods'], packet['comparative_gaps']
    if (not isinstance(comparisons, list) or len(comparisons) > len(_COMPARISON_MONTHS)
            or not isinstance(gaps, Mapping) or not all(isinstance(row, Mapping) for row in comparisons)):
        return False
    bases = [row.get('comparison_basis') for row in comparisons]
    if (bases != [basis for basis in _COMPARISON_MONTHS if basis in bases]
            or set(gaps) != set(_COMPARISON_MONTHS) - set(bases)):
        return False
    current = packet['periods'][0]
    for basis, reason in gaps.items():
        end = _comparison_end(current['period_end'], basis)
        blocked = _comparison_revision_unresolved(verified, end, current, structured_rows)
        if reason != (_COMPARISON_REVISION if blocked else _COMPARISON_UNAVAILABLE):
            return False
    for row in comparisons:
        fields, withheld = row.get('fields'), row.get('withheld_fields')
        if (row.get('unit') != current['unit'] or row.get('reason') is not None
                or any(row.get(key) != packet[key] for key in _METADATA)
                or not isinstance(fields, Mapping) or not fields or not isinstance(withheld, Mapping)
                or set(fields) | set(withheld) != _FIELD_NAMES or set(fields) & set(withheld)
                or any(not isinstance(reason, str) or not re.fullmatch(r'[a-z0-9_]{1,100}', reason) for reason in withheld.values())
                or _comparison_revision_unresolved(verified, row['period_end'], current, structured_rows)):
            return False
        if any(not _comparison_matches(field, packet, row, name, current) for name, field in fields.items()):
            return False
    return True


def _verify_packet(financial, wrapper, *, ticker, cik, inventory, as_of):
    verified = _identity_inventory(financial, ticker, cik, inventory, as_of)
    if not verified or not isinstance(wrapper, Mapping) or wrapper.get('status') != 'inspection_only':
        return None
    if (set(wrapper) not in (_PACKET_KEYS, _PACKET_KEYS | _COMPARATIVE_PACKET_KEYS)
            or wrapper.get('schema_version') != SCHEMA or wrapper.get('reason') is not None
            or wrapper.get('ticker') != ticker or wrapper.get('sec_cik') != cik
            or wrapper.get('source_id') != SOURCE_ID or wrapper.get('taxonomy') != TAXONOMY
            or wrapper.get('period_kind') != 'quarterly' or wrapper.get('rights_status') != RIGHTS
            or any(wrapper.get(k) is not False for k in ('commercial_eligible', 'readiness_promoted', 'saved_readiness_promoted'))
            or wrapper.get('inventory_digest') != verified['packet_digest'] or len(_json(wrapper)) > MAX_DTO_BYTES
            or wrapper.get('packet_digest') != _digest({k: v for k, v in wrapper.items() if k != 'packet_digest'})):
        return None
    if _native_scope(financial, verified, as_of) != (wrapper.get('unit'), wrapper.get('fiscal_year_end')):
        return None
    now = _now(as_of)
    events = _candidate_events(verified, now)
    index = next((i for i, event in enumerate(events[:MAX_PRIMARY_REQUESTS])
                  if event['accession'] == wrapper.get('accession')), None)
    if index is None:
        return None
    event = events[index]
    primary, source = wrapper.get('primary_source_url'), wrapper.get('source_url')
    end = _iso_date(wrapper.get('period_end'))
    structured = validated_foreign_financials(financial)
    if (not end or not _iso_date(verified['latest']['annual']['period_end']) <= end <= _iso_date(event['filed'])
            or any(_same_publication(a, b) for a, b in zip(events[:index + 1], events[1:index + 2]))
            or any(wrapper.get(k) != event[k] for k in ('form', 'filed', 'accepted_at', 'primary_document', 'report_date'))
            or primary != event['source_url'] or not _valid_source_url(primary, cik, event['accession'])
            or not _valid_source_url(source, cik, event['accession'])
            or not _selection_matches(wrapper.get('selection'), primary, source)
            or not _source_receipts_match(wrapper, financial, verified, events[:index], event, now)
            or not _valid_periods(wrapper)
            or not _valid_comparative_periods(wrapper, verified, structured['quarterly'] if structured else [])
            or _later_structured_quarter(financial, verified, wrapper['period_end'], event)):
        return None
    return deepcopy(dict(wrapper))


def validated_native_quarter(financial, *, ticker=None, expected_cik=None, inventory=None, as_of=None):
    """Revalidate the exact personal 6-K report and its separate durations."""
    try:
        if not isinstance(financial, Mapping):
            return None
        ticker = financial.get('ticker') if ticker is None else ticker
        cik = financial.get('sec_cik') if expected_cik is None else expected_cik
        inventory = financial.get('filing_inventory') if inventory is None else inventory
        return _verify_packet(financial, financial.get('native_archive_quarter'), ticker=ticker,
                              cik=cik, inventory=inventory, as_of=as_of)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return None


def _observed_row(row, metadata):
    fields = {name: dict(field, **metadata, source_ref=metadata['source_url'])
              for name, field in row['fields'].items()}
    return dict(row, fields=fields, status='available', reason=None, **metadata)


def _build_packet(parsed, *, verified, event, receipts, reviewed, selection, unit, fiscal_year_end, financial):
    source = receipts[-1]
    metadata = {k: event[k] for k in ('accession', 'form', 'filed', 'accepted_at', 'primary_document', 'report_date')}
    metadata.update({k: source[k] for k in _REF_KEYS})
    metadata.update(ticker=verified['ticker'], sec_cik=verified['sec_cik'], primary_source_url=event['source_url'],
                    source_id=SOURCE_ID, fiscal_year_end=fiscal_year_end, rights_status=RIGHTS)
    periods = [_observed_row(row, metadata) for row in parsed['periods'] if row['fields']]
    structured = validated_foreign_financials(financial)
    structured_rows = structured['quarterly'] if structured else []
    available = {row['comparison_basis']: row for row in parsed.get('comparative_periods', []) if row['fields']}
    comparisons, gaps = [], {}
    for basis in _COMPARISON_MONTHS:
        baseline_end = _comparison_end(periods[0]['period_end'], basis)
        if _comparison_revision_unresolved(verified, baseline_end, event, structured_rows):
            gaps[basis] = _COMPARISON_REVISION
        elif basis in available:
            comparisons.append(_observed_row(available[basis], metadata))
        else:
            gaps[basis] = _COMPARISON_UNAVAILABLE
    packet = dict(schema_version=SCHEMA, status='inspection_only', reason=None, **metadata,
                  period_end=periods[0]['period_end'], period_kind='quarterly', taxonomy=TAXONOMY, unit=unit,
                  periods=periods, comparative_periods=comparisons, comparative_gaps=gaps,
                  source_receipts=receipts, reviewed_preceding=reviewed, selection=selection,
                  inventory_digest=verified['packet_digest'], commercial_eligible=False,
                  readiness_promoted=False, saved_readiness_promoted=False)
    packet['packet_digest'] = _digest(packet)
    return packet


def fetch_native_quarter(financial, *, user_agent, ticker_map_receipt, submissions_receipt,
                         source_fetcher=None, observed_at=None):
    """Read bounded newest-first primary filings and at most one exact exhibit."""
    ticker = financial.get('ticker') if isinstance(financial, Mapping) else None
    cik = financial.get('sec_cik') if isinstance(financial, Mapping) else None

    def hold(reason):
        return _held(ticker, cik, reason, schema=SCHEMA)

    try:
        now = _now(observed_at)
        inventory = financial.get('filing_inventory')
        verified = _identity_inventory(financial, ticker, cik, inventory, now)
        if not verified:
            return hold('native_quarter_current_source_unavailable')
        annual = verified['latest']['annual']
        if not annual or annual['form'] not in {'20-F', '20-F/A'}:
            return hold('native_quarter_not_required')
        scope = _native_scope(financial, verified, now)
        if not scope:
            return hold('native_quarter_reporting_currency_unverified')
        unit, fiscal_year_end = scope
        gap = _receipt_gap(financial, verified, ticker_map_receipt, submissions_receipt, now)
        if gap:
            return hold('native_quarter_' + gap)
        if not isinstance(user_agent, str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):
            return hold('native_quarter_user_agent_required')
        events = _candidate_events(verified, now)
        reviewed = []
        for index, event in enumerate(events[:MAX_PRIMARY_REQUESTS]):
            if index + 1 < len(events) and _same_publication(event, events[index + 1]):
                return hold('native_quarter_same_timestamp_versions_unresolved')
            primary = event['source_url']
            if not _valid_source_url(primary, cik, event['accession']):
                reason = 'native_quarter_amendment_unresolved' if event['amendment'] else 'native_quarter_document_unavailable'
                return hold(reason)
            raw, cover_ref = _read_document(primary, user_agent=user_agent, source_fetcher=source_fetcher, observed_at=observed_at)
            classification, selection = _classify_cover(raw, primary, event['form'])
            if classification == 'unrelated' and not event['amendment']:
                reviewed.append(dict(accession=event['accession'], reason=selection, receipt=cover_ref))
                continue
            if classification not in {'primary', 'exhibit'}:
                if event['amendment']:
                    return hold('native_quarter_amendment_unresolved')
                return hold('native_quarter_exhibit_link_unresolved' if classification == 'link_unresolved'
                            else 'native_quarter_newer_filing_scope_unresolved')
            checked_at = _now(observed_at)
            refs = [_ref(ticker_map_receipt, MAP_URL, checked_at),
                    _ref(submissions_receipt, f'https://data.sec.gov/submissions/CIK{cik}.json', checked_at), cover_ref]
            if classification == 'exhibit':
                url = _exhibit_url(primary, selection['href'])
                raw, ref = _read_document(url, user_agent=user_agent, source_fetcher=source_fetcher, observed_at=observed_at)
                refs.append(ref)
            from src.sec_native_quarter_tables import parse_native_quarter_tables
            parsed = parse_native_quarter_tables(raw, currency=unit, fiscal_year_end=fiscal_year_end)
            if parsed['status'] != 'inspection_only':
                if event['amendment']:
                    return hold('native_quarter_amendment_unresolved')
                reason = parsed.get('reason')
                return hold('native_quarter_' + reason if isinstance(reason, str)
                            and re.fullmatch(r'[a-z0-9_]{1,80}', reason) else _UNAVAILABLE)
            packet = _build_packet(parsed, verified=verified, event=event, receipts=refs,
                                   reviewed=reviewed, selection=selection, unit=unit, fiscal_year_end=fiscal_year_end,
                                   financial=financial)
            if _later_structured_quarter(financial, verified, packet['period_end'], event):
                return hold('native_quarter_newer_structured_period_or_version')
            return (_verify_packet(financial, packet, ticker=ticker, cik=cik, inventory=verified, as_of=observed_at)
                    or hold(_UNAVAILABLE))
        return hold('native_quarter_candidate_limit' if len(events) > MAX_PRIMARY_REQUESTS
                    else 'native_quarter_earnings_report_not_verified')
    except HTTPError as exc:
        return hold('sec_archive_access_limited' if exc.code in {403, 429, 503} else 'sec_archive_http_unavailable')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError, OSError, RuntimeError):
        return hold(_UNAVAILABLE)
