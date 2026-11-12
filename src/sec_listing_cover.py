"""Exact SEC filing metadata and visible registration-cover evidence."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from xml.etree import ElementTree as ET

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.sec_html_bank import _hidden

MAX_COVER_BYTES = 2 * 1024 * 1024
HIDDEN_TAGS = {'hidden', 'header', 'script', 'style', 'template'}
HEADERS = (
    'title of each class',
    'trading symbol',
    'name of each exchange on which registered',
)


@dataclass(frozen=True)
class FilingCase:
    symbol: str
    cik: str
    accession: str
    document: str
    form: str = '8-K'

    @property
    def metadata_url(self):
        return f'https://data.sec.gov/submissions/CIK{self.cik}.json'

    @property
    def source_url(self):
        return f'https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{self.accession.replace("-", "")}/{self.document}'


def _text(node):
    return ' '.join(' '.join(node.itertext()).split())


def read_listing_cover(raw, symbol, *, max_bytes=MAX_COVER_BYTES):
    """Read one visible section 12(b) grid, including exchange-only continuations."""
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= max_bytes
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
    return matches[0]


def cover_exchanges(venues, labels):
    """Keep the venue assertion withheld when any label is outside the reviewed vocabulary."""
    groups = [labels.get(venue.casefold(), ()) for venue in venues]
    return tuple(dict.fromkeys(exchange for group in groups for exchange in group)) if all(groups) else ()


def filing_metadata(receipt, case, *, registration_date=None):
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
        if (form != case.form or document != case.document or not all((filed_date, accepted_at, observed))
                or filed_date > observed.date() or accepted_at > observed):
            return None
        if registration_date is None:
            if report_date is None or report_date > min(filed_date, accepted_at.date()):
                return None
        elif reported != '' or filed != registration_date or accepted_at.date() != filed_date:
            return None
        return dict(filed=filed, report_date=reported or None, accepted_at=accepted,
                    metadata_observed_at=receipt['observed_at'], metadata_sha256=receipt['payload_sha256'])
    except (KeyError, TypeError, AttributeError):
        return None


def document_receipt(raw, final, case, observed_at, *, max_bytes=MAX_COVER_BYTES):
    if final != case.source_url or not isinstance(raw, bytes) or not 0 < len(raw) <= max_bytes:
        return None
    now = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return dict(observed_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'), payload_sha256=hashlib.sha256(raw).hexdigest())
