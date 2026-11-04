"""A bounded NYSE Texas registration audit using dated SEC filing covers."""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from html import escape
import re
from urllib.error import HTTPError
from xml.etree import ElementTree as ET

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_sec_receipt import _fetch_raw, fetch_sec_json_receipt
from src.sec_exact_filing import RIGHTS, _fetch_html
from src.sec_html_bank import _hidden

SESSION_KEY = 'nyse_texas_reconciliation_v1'
MAX_COVER_BYTES = 2 * 1024 * 1024
HIDDEN_TAGS = {'hidden', 'header', 'script', 'style', 'template'}
HEADERS = (
    'title of each class',
    'trading symbol',
    'name of each exchange on which registered',
)
EXCHANGES = {
    'new york stock exchange': ('NYSE',),
    'nyse american': ('NYSE American',),
    'nyse texas': ('NYSE Texas',),
    'nyse texas, inc.': ('NYSE Texas',),
    'new york stock exchange nyse texas': ('NYSE', 'NYSE Texas'),
    'new york stock exchange nyse texas, inc.': ('NYSE', 'NYSE Texas'),
    'nyse american nyse texas': ('NYSE American', 'NYSE Texas'),
    'nyse american nyse texas, inc.': ('NYSE American', 'NYSE Texas'),
}


@dataclass(frozen=True)
class FilingCase:
    symbol: str
    cik: str
    accession: str
    document: str

    @property
    def metadata_url(self):
        return f'https://data.sec.gov/submissions/CIK{self.cik}.json'

    @property
    def source_url(self):
        return f'https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{self.accession.replace("-", "")}/{self.document}'


CASES = (
    FilingCase('ICE', '0001571949', '0001104659-26-119880', 'tm2628301d1_8k.htm'),
    FilingCase('HAL', '0000045012', '0000045012-26-000069', 'hal-20261015.htm'),
    FilingCase('ABT', '0000001800', '0001104659-26-099247', 'tm2623675d1_8k.htm'),
    FilingCase('OIS', '0001121484', '0001121484-26-000036', 'ois-20261030.htm'),
)


def _text(node):
    return ' '.join(' '.join(node.itertext()).split())


def cover_registration(raw, symbol):
    """Read one visible section 12(b) grid, including exchange-only continuations."""
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_COVER_BYTES
            or b'\0' in raw or b'<!doctype' in raw.lower() or b'<!entity' in raw.lower()):
        return None
    try:
        root = ET.fromstring(raw.decode('utf-8-sig'))
    except (ET.ParseError, ValueError):
        return None

    # Identify the bounded cover table and remember hidden ancestors.
    stack = [(root, False)]
    candidates = []
    table_count = 0
    while stack and table_count < 20:
        node, ancestor_hidden = stack.pop()
        hidden = ancestor_hidden or _hidden(node.attrib) or node.tag.rsplit('}', 1)[-1] in HIDDEN_TAGS
        if node.tag in {'table', '{http://www.w3.org/1999/xhtml}table'}:
            table_count += 1
            grid = [
                [cell for cell in row if cell.tag.rsplit('}', 1)[-1] in {'td', 'th'}]
                for row in node.findall('.//{*}tr')
            ]
            for index, row in enumerate(grid):
                labels = tuple(label.casefold().removesuffix('(s)') for cell in row if (label := _text(cell)))
                if labels == HEADERS:
                    candidates.append((node, hidden, grid, index))
        stack.extend((child, hidden) for child in reversed(node))

    if len(candidates) != 1:
        return None
    table, hidden, grid, header = candidates[0]
    if (hidden or len(grid) > 20 or table.find('.//{*}table') is not None
            or any(_hidden(node.attrib) or node.tag.rsplit('}', 1)[-1] in HIDDEN_TAGS
                   or node.get('rowspan', '1') != '1' for node in table.iter())):
        return None
    title_col, symbol_col, exchange_col = [i for i, cell in enumerate(grid[header]) if _text(cell)]
    columns = {title_col, symbol_col, exchange_col}
    header_spans = [cell.get('colspan', '1') for cell in grid[header]]
    if any(not re.fullmatch(r'[1-9][0-9]?', span) for span in header_spans):
        return None
    groups = []
    for cells in grid[header + 1:]:
        row = [_text(cell) for cell in cells]
        if not any(row):
            continue
        if ([cell.get('colspan', '1') for cell in cells] != header_spans
                or any(value for i, value in enumerate(row) if i not in columns)):
            return None
        title, ticker, venue = row[title_col], row[symbol_col], row[exchange_col]
        if title and ticker and venue:
            groups.append((title, ticker, [venue]))
        elif not title and not ticker and venue and groups:
            groups[-1][2].append(venue)
        else:
            return None
    matches = [(title, venues) for title, ticker, venues in groups if ticker == symbol]
    if len(matches) != 1:
        return None
    title, venues = matches[0]
    kind = 'common_shares' if re.fullmatch(
        r'(?:class [a-z0-9]+ )?(?:common stock|common shares)(?:,? (?:without par value|par value \$[.\d]+ per share|\$[.\d]+ par value(?: per share)?))?',
        title, re.I,
    ) else None
    # Unknown exchange text withholds the venue assertion for this security.
    venues = [EXCHANGES.get(venue.casefold(), ()) for venue in venues]
    return kind, tuple(dict.fromkeys(exchange for group in venues for exchange in group)) if all(venues) else ()


def _filing_metadata(receipt, case):
    if receipt['status'] != 'ready':
        return None
    try:
        body = receipt['payload']
        if str(body['cik']).zfill(10) != case.cik:
            return None
        recent = body['filings']['recent']
        keys = ('accessionNumber', 'form', 'primaryDocument', 'filingDate', 'reportDate', 'acceptanceDateTime')
        accessions = recent['accessionNumber']
        if (not isinstance(accessions, list) or not 1 <= len(accessions) <= 2000
                or any(not isinstance(recent[key], list) or len(recent[key]) != len(accessions) for key in keys)
                or accessions.count(case.accession) != 1):
            return None
        index = accessions.index(case.accession)
        _, form, document, filed, reported, accepted = (recent[key][index] for key in keys)
        filed_date, report_date = _iso_date(filed), _iso_date(reported)
        accepted_at, observed = _utc_timestamp(accepted), _utc_timestamp(receipt['observed_at'])
        if (form != '8-K' or document != case.document or not all((filed_date, report_date, accepted_at, observed))
                or not report_date <= filed_date <= observed.date()
                or not report_date <= accepted_at.date() or accepted_at > observed):
            return None
        return dict(filed=filed, report_date=reported, accepted_at=accepted,
                    metadata_observed_at=receipt['observed_at'], metadata_sha256=receipt['payload_sha256'])
    except (KeyError, TypeError, AttributeError):
        return None


def check_nyse_texas(*, user_agent, fetcher=None, observed_at=None, workspace_mode='research'):
    reason = _mode_reason(workspace_mode)
    if reason:
        return dict(status='withheld', reason=reason)
    if (not isinstance(user_agent, str) or not user_agent.strip() or any(c in user_agent for c in '\r\n')
            or observed_at is not None and (not isinstance(observed_at, datetime) or observed_at.utcoffset() is None)):
        return dict(status='withheld', reason='A valid SEC identifying user agent and observation time are required.')

    # SEC's access-limit responses stop the batch, including limits on metadata.
    paused = False

    def transport(url, agent):
        nonlocal paused
        try:
            if fetcher is not None:
                return fetcher(url, agent)
            if url.startswith('https://www.sec.gov/Archives/'):
                return _fetch_html(url, agent, max_bytes=MAX_COVER_BYTES)
            return _fetch_raw(url, agent)
        except HTTPError as exc:
            paused = exc.code in {403, 429, 503}
            raise

    rows = []
    for case in CASES:
        row = dict(symbol=case.symbol, cik=case.cik, accession=case.accession, source_url=case.source_url,
                   metadata_url=case.metadata_url, confirmed=False, security_type=None,
                   reason='sec_access_paused' if paused else 'filing_metadata_unavailable')
        rows.append(row)
        if paused:
            continue
        receipt = fetch_sec_json_receipt(case.metadata_url, user_agent=user_agent, fetcher=transport,
                                         observed_at=observed_at)
        metadata = _filing_metadata(receipt, case)
        if metadata is None:
            if paused:
                row['reason'] = 'sec_access_paused'
            elif receipt['status'] == 'ready':
                row['reason'] = 'filing_metadata_mismatch'
            continue
        row.update(metadata)
        try:
            raw, _, final = transport(case.source_url, user_agent)
        except (OSError, RuntimeError, ValueError):
            row['reason'] = 'sec_access_paused' if paused else 'filing_unavailable'
            continue
        if final != case.source_url or not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_COVER_BYTES:
            row['reason'] = 'filing_response_unverified'
            continue
        now = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        row.update(observed_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'), payload_sha256=hashlib.sha256(raw).hexdigest())
        registration = cover_registration(raw, case.symbol)
        if registration is None:
            row['reason'] = 'cover_security_row_missing_or_ambiguous'
            continue
        kind, venues = registration
        row.update(security_type=kind, exchanges=venues)
        if kind is None:
            row['reason'] = 'security_type_unverified'
        elif 'NYSE Texas' not in venues:
            row['reason'] = 'nyse_texas_missing_from_security_row'
        elif len(venues) < 2:
            row['reason'] = 'second_venue_unverified'
        else:
            row.update(confirmed=True, reason=None)
    return dict(status='inspection_only', rights_status=RIGHTS, rows=rows, sample_count=len(CASES),
                confirmed_count=sum(row['confirmed'] for row in rows),
                security_identity_count=sum(row['security_type'] is not None for row in rows))


def get_nyse_texas(state, *, refresh, user_agent, workspace_mode='research', fetcher=None, observed_at=None):
    if _mode_reason(workspace_mode):
        return dict(status='withheld', reason='Available in Personal Research only.')
    if refresh:
        state[SESSION_KEY] = check_nyse_texas(user_agent=user_agent, workspace_mode=workspace_mode,
                                            fetcher=fetcher, observed_at=observed_at)
    return state.get(SESSION_KEY, dict(status='not_requested'))


def reconciliation_html(result):
    if result['status'] != 'inspection_only':
        return '<p>' + escape(result.get('reason', 'Run the check to inspect the four selected SEC filings.')) + '</p>'
    details = []
    for row in result['rows']:
        outcome = 'Dual registration observed' if row['confirmed'] else 'Withheld · ' + row['reason'].replace('_', ' ')
        venues = ', '.join(row.get('exchanges', ()))
        cover = (f'<p>Filed {row["filed"]} · report date {row["report_date"]} · accepted {row["accepted_at"]}. '
                 f'Cover observed {row["observed_at"]} · SHA-256 {row["payload_sha256"]}.</p>'
                 if 'observed_at' in row else '')
        metadata = (f'<p><a href="{row["metadata_url"]}">SEC submissions</a> observed {row["metadata_observed_at"]}'
                    f' · SHA-256 {row["metadata_sha256"]}.</p>' if 'metadata_sha256' in row else '')
        details.append(
            f'<li><strong>{row["symbol"]}</strong> · {escape(outcome)}'
            + (' · Common shares as filed' if row['security_type'] else '')
            + (f' · {escape(venues)}' if venues else '')
            + f'<details><summary>Filing evidence for {row["symbol"]}</summary>'
              f'<p>CIK {row["cik"]} · <a href="{row["source_url"]}">Form 8-K {row["accession"]}</a>.</p>'
            + cover + metadata + '</details></li>'
        )
    count = result['sample_count']
    confirmed = result['confirmed_count']
    return (
        '<section aria-label="NYSE Texas filing reconciliation" style="overflow-wrap:anywhere;min-width:0">'
        f'<h3>NYSE Texas filing reconciliation</h3>'
        f'<p><strong>{confirmed} of {count} dual registrations confirmed as filed</strong> · '
        f'{result["security_identity_count"]} security identities supported · {count - confirmed} sample records unresolved.</p>'
        '<p>Selected SEC filings only. Current active status, the venue-wide count, issuer domicile, analysis eligibility, '
        'and historical membership remain unverified. Personal inspection only. The saved inventory and financial coverage are separate.</p>'
        '<ul>' + ''.join(details) + '</ul></section>'
    )
