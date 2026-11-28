"""Bounded official ECB reference capture, separate from valuation and snapshots."""
import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from src.commercial_source_rights import commercial_mode_enabled

URL = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml'
REFERENCE_PAGE = 'https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html'
COPYRIGHT_PAGE = 'https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html'
MAX_BYTES = 2 * 1024 * 1024
G = '{http://www.gesmes.org/xml/2002-08-01}'
E = '{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}'
SCHEMA = 'ecb-eur-usd-reference-v1'
ATTRIBUTION = ('Source: European Central Bank. Original XML reproduced unchanged. '
    'Any extracted or translated amount is identified separately as derived. '
    'Reference rates are informational, not transaction rates. '
    'First publication time and point-in-time availability are unverified.\n'
    + URL + '\n' + REFERENCE_PAGE + '\n' + COPYRIGHT_PAGE + '\n')


def _day(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError('ecb_reference_date_invalid')
    return date.fromisoformat(value)


def _utc(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError('ecb_observation_time_invalid')
    return value.astimezone(timezone.utc)


def _stamp(value):
    return _utc(value).isoformat().replace('+00:00', 'Z')


def parse_ecb_usd(raw, *, reference_date, observed_at, last_modified=None):
    """Select exactly one USD-per-EUR token from original bounded source bytes."""
    target, observed = _day(reference_date), _utc(observed_at)
    if target > observed.astimezone(ZoneInfo('Europe/Berlin')).date():
        raise ValueError('ecb_reference_date_future')
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_BYTES:
        raise ValueError('ecb_reference_size_invalid')
    try:
        text = raw.decode('utf-8-sig')
        if '\x00' in text or re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', text, re.I):
            raise ValueError('ecb_reference_xml_unsafe')
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as exc:
        raise ValueError('ecb_reference_xml_invalid') from exc
    senders = root.findall(G + 'Sender')
    subjects = root.findall(G + 'subject')
    if (root.tag != G + 'Envelope' or root.attrib or len(senders) != 1
            or len(subjects) != 1 or len(root) != 3
            or subjects[0].attrib or len(subjects[0]) or subjects[0].text != 'Reference rates'
            or senders[0].attrib or len(senders[0]) != 1
            or senders[0][0].tag != G + 'name'
            or senders[0][0].attrib or len(senders[0][0])
            or senders[0][0].text != 'European Central Bank'):
        raise ValueError('ecb_reference_identity_invalid')
    containers = root.findall(E + 'Cube')
    if len(containers) != 1 or containers[0].attrib:
        raise ValueError('ecb_reference_structure_invalid')
    for node in root.iter():
        if ((node.tag not in {G + 'subject', G + 'name'} and node.text and node.text.strip())
                or node.tail and node.tail.strip()):
            raise ValueError('ecb_reference_structure_invalid')
    seen, selected = set(), None
    for group in containers[0]:
        if group.tag != E + 'Cube' or set(group.attrib) != {'time'}:
            raise ValueError('ecb_reference_structure_invalid')
        day = _day(group.attrib['time'])
        if day in seen or day > observed.astimezone(ZoneInfo('Europe/Berlin')).date():
            raise ValueError('ecb_reference_date_ambiguous_or_future')
        seen.add(day)
        currencies = set()
        for row in group:
            if (row.tag != E + 'Cube' or set(row.attrib) != {'currency', 'rate'} or len(row)
                    or re.fullmatch(r'[A-Z]{3}', row.attrib['currency']) is None):
                raise ValueError('ecb_reference_structure_invalid')
            currency, literal = row.attrib['currency'], row.attrib['rate']
            if currency in currencies or currency == 'EUR':
                raise ValueError('ecb_reference_rate_ambiguous')
            currencies.add(currency)
            digits = 3 if currency == 'USD' else 11
            if (re.fullmatch(r'(?:0|[1-9][0-9]{0,' + str(digits) + r'})(?:\.[0-9]{1,8})?', literal) is None
                    or Decimal(literal) <= 0):
                raise ValueError('ecb_reference_rate_invalid')
            if day == target and currency == 'USD':
                selected = literal
    if selected is None:
        raise ValueError('ecb_reference_date_unavailable')
    if last_modified is not None and (not isinstance(last_modified, str) or len(last_modified) > 128
            or any(ord(c) < 32 for c in last_modified)):
        raise ValueError('ecb_reference_metadata_invalid')
    return dict(schema_version=SCHEMA, source_url=URL, reference_page=REFERENCE_PAGE,
        copyright_page=COPYRIGHT_PAGE, attribution='European Central Bank',
        reference_date=reference_date, base_currency='EUR', quote_currency='USD',
        quote_convention='USD_per_EUR', rate_literal=selected, payload_sha256=sha256(raw).hexdigest(),
        observed_at=_stamp(observed), last_modified=last_modified,
        first_publication_status='unverified', commercial_eligible=False)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('ecb_endpoint_changed')


def _fetch(url):
    request = urllib.request.Request(url, headers={
        'User-Agent':'StockResearchCommandCenter (github.com/YuzeJ21/Stock-Analysis)',
        'Accept':'application/xml,text/xml', 'Accept-Encoding':'identity'})
    with urllib.request.build_opener(_NoRedirect()).open(request, timeout=20) as response:
        headers = dict(response.headers.items())
        lower = {key.lower():value for key,value in headers.items()}
        if response.getcode() != 200 or 'content-range' in lower:
            raise ValueError('ecb_response_incomplete')
        raw = response.read(MAX_BYTES + 1)
        length = lower.get('content-length')
        if length is not None and (re.fullmatch(r'[0-9]+', length) is None or int(length) != len(raw)):
            raise ValueError('ecb_response_length_invalid')
        return raw, headers, response.geturl()


def capture_ecb_usd(reference_date, *, fetcher=None, clock=None):
    """One explicit request; a failed capture contains neither a rate nor XML."""
    held = dict(status='withheld', reason='ecb_reference_unavailable', source_url=URL)
    try:
        if commercial_mode_enabled():
            return dict(held, reason='commercial_source_rights_unreviewed')
    except ValueError:
        return dict(held, reason='invalid_commercial_mode_configuration')
    try:
        _day(reference_date)
        raw, headers, final_url = (fetcher or _fetch)(URL)
        observed = _utc((clock or (lambda:datetime.now(timezone.utc)))())
        if final_url != URL or not isinstance(headers, dict):
            raise ValueError('ecb_endpoint_changed')
        headers = {key.lower():value for key,value in headers.items()}
        receipt = parse_ecb_usd(raw, reference_date=reference_date, observed_at=observed,
                                last_modified=headers.get('last-modified'))
        transport = dict(source_url=final_url, observed_at=_stamp(observed),
                         last_modified=headers.get('last-modified'))
        return dict(status='captured', receipt=receipt, transport=transport, xml=raw)
    except Exception:
        # Network errors may contain request internals. Expose no provider exception.
        return held


def main(argv=None, *, fetcher=None, clock=None):
    parser = argparse.ArgumentParser(description='One explicit public ECB reference capture; no valuation or snapshot update.')
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('capture')
    capture.add_argument('--reference-date', required=True)
    capture.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        destination = args.output_dir.resolve()
        project = Path(__file__).resolve().parent.parent
        from src.no_write_artifact_guard import PROTECTED_ROOTS
        if any(destination.is_relative_to(project / root) for root in PROTECTED_ROOTS):
            raise ValueError('protected_output_destination')
        destination.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError):
        print(json.dumps(dict(status='withheld', reason='fresh_disposable_output_directory_required')))
        return 2
    result = capture_ecb_usd(args.reference_date, fetcher=fetcher, clock=clock)
    summary = {key:value for key,value in result.items() if key != 'xml'}
    if result['status'] == 'captured':
        (destination / 'fx.xml').write_bytes(result['xml'])
    (destination / 'receipt.json').write_text(json.dumps(summary, indent=2) + '\n')
    (destination / 'SOURCE.txt').write_text(ATTRIBUTION)
    print(json.dumps(summary, sort_keys=True))
    return 0 if result['status'] == 'captured' else 2


if __name__ == '__main__':
    raise SystemExit(main())
