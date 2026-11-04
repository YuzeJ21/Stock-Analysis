"""Read-only LTSE registration checks for the three reviewed spotlight companies."""
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import re
from urllib.error import HTTPError

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_sec_receipt import _fetch_raw, fetch_sec_json_receipt
from src.sec_exact_filing import RIGHTS, _fetch_html
from src.sec_listing_cover import (
    MAX_COVER_BYTES, FilingCase, cover_exchanges, document_receipt, filing_metadata, read_listing_cover,
)

SESSION_KEY = 'ltse_listing_reconciliation_v2'
VENUE = 'Long-Term Stock Exchange'
SPOTLIGHT_URL = 'https://ltse.com/listings/listed-companies'
SPOTLIGHT_REVIEW_DATE = '2026-11-04'
EXHIBIT_N_URL = 'https://www.sec.gov/Archives/edgar/vprr/2401/24010775.pdf'
JUNE_FORM_1_URL = 'https://www.sec.gov/Archives/edgar/vprr/2600/26000296.pdf'
OCTOBER_FORM_1_URL = 'https://www.sec.gov/Archives/edgar/vprr/2600/26000495.pdf'
LTSE_NOTICES_URL = 'https://ltse.com/trading/customer-notices'
SEC_NOTICE_SEARCH_URL = 'https://www.sec.gov/edgar/search/'
REGISTRATION_FORMS = {'8-A12B', 'CERT', '25', '25-NSE', '15-12B', '15F-12B'}
TWLO_FORM_25_URL = 'https://www.sec.gov/Archives/edgar/data/1447669/000119312522308321/d418994d25.htm'
TWLO_CIRCULAR_URL = 'https://assets-global.website-files.com/6462417e8db99f8baa06952c/6462417e8db99f8baa06a722_RIC-2022-07%20%28Twilio%20Delisting%29.pdf'
EXCHANGES = {
    'new york stock exchange': ('NYSE',),
    'the nasdaq stock market llc': ('Nasdaq',),
    'nyse american': ('NYSE American',),
    'long-term stock exchange': (VENUE,),
    'new york stock exchange long-term stock exchange': ('NYSE', VENUE),
    'the nasdaq stock market llc long-term stock exchange': ('Nasdaq', VENUE),
}


@dataclass(frozen=True)
class ListingCase:
    filing: FilingCase
    filed: str
    security_class: str
    primary_venue: str
    max_bytes: int = MAX_COVER_BYTES


CASES = (
    ListingCase(FilingCase('ASAN', '0001477720', '0001628280-26-063720', 'asan-20260925.htm'),
                '2026-09-28', 'Class A common stock', 'NYSE'),
    ListingCase(FilingCase('TDUP', '0001484778', '0001484778-26-000033', 'tdup-20260930.htm', '10-Q'),
                '2026-11-04', 'Class A common stock', 'Nasdaq'),
    ListingCase(FilingCase('BLX', '0000890541', '0001628280-26-026056', 'blx-20251231.htm', '20-F'),
                '2026-04-20', 'Class E common stock', 'NYSE', max_bytes=10 * 1024 * 1024),
)
BLX_RENAME = FilingCase('BLX', '0000890541', '0001628280-26-041363', 'a6knamechancebladexinc.htm', '6-K')
BLX_RENAME_SHA256 = '8d817468d8a73e11b6bf292951c5d744f4db624762e7cade0fae541f2d599856'


def _post_filing_scan(receipt, metadata):
    recent = receipt['payload']['filings']['recent']
    anchor = _utc_timestamp(metadata['accepted_at'])
    cutoff = _utc_timestamp(receipt['observed_at'])
    seen = set()
    later_count = 0
    candidates = []
    for accession, form, filed, accepted in zip(recent['accessionNumber'], recent['form'],
                                               recent['filingDate'], recent['acceptanceDateTime']):
        filed_date, accepted_at = _iso_date(filed), _utc_timestamp(accepted)
        if (not isinstance(accession, str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession)
                or accession in seen or not isinstance(form, str) or not form.strip()
                or filed_date is None or accepted_at is None):
            return None
        seen.add(accession)
        if accepted_at <= anchor or accepted_at > cutoff or filed_date > cutoff.date():
            continue
        later_count += 1
        if form.removesuffix('/A') in REGISTRATION_FORMS:
            candidates.append(dict(accession=accession, form=form, filed=filed))
    return dict(observed_at=receipt['observed_at'], later_count=later_count, registration_candidates=candidates)


def _verify_bladex_rename(receipt, anchor, transport, user_agent, observed_at):
    metadata = filing_metadata(receipt, BLX_RENAME)
    if (metadata is None or metadata['filed'] != '2026-06-08' or metadata['report_date'] != '2026-06-04'
            or _utc_timestamp(metadata['accepted_at']) <= _utc_timestamp(anchor['accepted_at'])):
        return None
    try:
        raw, _, final = transport(BLX_RENAME.source_url, user_agent)
    except (OSError, RuntimeError, ValueError):
        return None
    archive = document_receipt(raw, final, BLX_RENAME, observed_at)
    if archive is None or archive['payload_sha256'] != BLX_RENAME_SHA256:
        return None
    return dict(effective='2026-06-04', filed=metadata['filed'], source_url=BLX_RENAME.source_url, **archive)


def _apply_cover(row, raw, case):
    cover = read_listing_cover(raw, case.filing.symbol, max_bytes=case.max_bytes)
    if cover is None:
        row['reason'] = 'cover_security_row_missing_or_ambiguous'
        return
    title, venue_labels = cover
    if not re.fullmatch(re.escape(case.security_class) +
                        r'(?:,? (?:par value \$[.\d]+|\$[.\d]+ par value)(?: per share)?)?', title, re.I):
        row['reason'] = 'security_class_mismatch'
        return
    row['security_class'] = case.security_class
    exchanges = cover_exchanges(venue_labels, EXCHANGES)
    if not exchanges:
        row['reason'] = 'exchange_labels_unverified'
    elif VENUE not in exchanges:
        row['reason'] = 'ltse_missing_from_security_row'
    elif set(exchanges) != {case.primary_venue, VENUE}:
        row['reason'] = 'companion_exchange_mismatch'
    else:
        row.update(confirmed=True, reason=None, exchanges=(case.primary_venue, VENUE))


def check_ltse(*, user_agent, fetcher=None, observed_at=None, workspace_mode='research'):
    reason = _mode_reason(workspace_mode)
    if reason:
        return dict(status='withheld', reason='Available in Personal Research only.')
    if (not isinstance(user_agent, str) or not user_agent.strip() or any(c in user_agent for c in '\r\n')
            or observed_at is not None and (not isinstance(observed_at, datetime) or observed_at.utcoffset() is None)):
        return dict(status='withheld', reason='A valid SEC identifying user agent and observation time are required.')

    paused = False
    archive_limits = {case.filing.source_url: case.max_bytes for case in CASES}
    archive_limits[BLX_RENAME.source_url] = MAX_COVER_BYTES

    def transport(url, agent):
        nonlocal paused
        try:
            if fetcher is not None:
                return fetcher(url, agent)
            if url in archive_limits:
                return _fetch_html(url, agent, max_bytes=archive_limits[url])
            return _fetch_raw(url, agent)
        except HTTPError as exc:
            paused = exc.code in {403, 429, 503}
            raise

    rows = []
    for case in CASES:
        filing = case.filing
        row = dict(symbol=filing.symbol, cik=filing.cik, accession=filing.accession, form=filing.form,
                   source_url=filing.source_url, metadata_url=filing.metadata_url, confirmed=False,
                   current_listing_status='withheld', security_class=None,
                   reason='sec_access_paused' if paused else 'filing_metadata_unavailable')
        rows.append(row)
        if paused:
            continue
        receipt = fetch_sec_json_receipt(filing.metadata_url, user_agent=user_agent, fetcher=transport,
                                         observed_at=observed_at)
        metadata = filing_metadata(receipt, filing)
        if metadata is None or metadata['filed'] != case.filed:
            if paused:
                row['reason'] = 'sec_access_paused'
            elif receipt['status'] == 'ready':
                row['reason'] = 'filing_metadata_mismatch'
            continue
        row.update(metadata)
        row['post_filing_scan'] = _post_filing_scan(receipt, metadata)
        try:
            raw, _, final = transport(filing.source_url, user_agent)
        except (OSError, RuntimeError, ValueError):
            row['reason'] = 'sec_access_paused' if paused else 'filing_unavailable'
            continue
        archive = document_receipt(raw, final, filing, observed_at, max_bytes=case.max_bytes)
        if archive is None:
            row['reason'] = 'filing_response_unverified'
            continue
        row.update(archive)
        _apply_cover(row, raw, case)
        if filing.cik == BLX_RENAME.cik:
            row['issuer_change'] = _verify_bladex_rename(receipt, metadata, transport, user_agent, observed_at)
    today = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()
    return dict(status='inspection_only', rights_status=RIGHTS, rows=rows, sample_count=len(rows), roster_status='withheld',
                spotlight_observed_on=SPOTLIGHT_REVIEW_DATE if today >= SPOTLIGHT_REVIEW_DATE else None,
                confirmed_count=sum(row['confirmed'] for row in rows),
                security_identity_count=sum(row['security_class'] is not None for row in rows))


def get_ltse(state, *, refresh, user_agent, workspace_mode='research', fetcher=None, observed_at=None):
    if _mode_reason(workspace_mode):
        return dict(status='withheld', reason='Available in Personal Research only.')
    if refresh:
        state[SESSION_KEY] = check_ltse(user_agent=user_agent, workspace_mode=workspace_mode,
                                       fetcher=fetcher, observed_at=observed_at)
    return state.get(SESSION_KEY, dict(status='not_requested'))


def _source_link(url, label):
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{escape(label)}</a>'


def _post_filing_html(row, spotlight_date):
    status = (f'Featured on the exchange spotlight when reviewed on {spotlight_date}. ' if spotlight_date else '')
    status += 'Current roster status withheld.'
    scan = row.get('post_filing_scan')
    scan_text = 'SEC post-filing screen unavailable.'
    candidates_html = ''
    if scan is not None:
        candidates = scan['registration_candidates']
        scan_text = (f'SEC recent filings observed {scan["observed_at"]} · {scan["later_count"]} later filings · '
                     f'{len(candidates)} registration-form candidates. This screen covers filing metadata.')
        if candidates:
            links = []
            for candidate in candidates:
                accession = candidate['accession']
                url = f'https://www.sec.gov/Archives/edgar/data/{int(row["cik"])}/{accession.replace("-", "")}/{accession}-index.htm'
                links.append('<li>' + _source_link(url, candidate['form'] + ' · ' + candidate['filed']) + '</li>')
            candidates_html = '<p>Venue and share class require review.</p><ul>' + ''.join(links) + '</ul>'
    change = row.get('issuer_change')
    change_html = ''
    if change:
        change_html = (
            f'<p>Issuer renamed Bladex, Inc. effective {change["effective"]}. The issuer reported that the '
            f'outstanding securities were unaffected. {_source_link(change["source_url"], "Form 6-K")} filed {change["filed"]} '
            f'· observed {change["observed_at"]} · SHA-256 {change["payload_sha256"]}.</p>'
        )
    elif row['symbol'] == 'BLX':
        change_html = '<p>Exact name-change filing evidence unavailable in this check.</p>'
    return f'<p>{escape(status)}</p><p>{escape(scan_text)}</p>' + candidates_html + change_html


def _row_html(row, spotlight_date):
    outcome = ' · '.join(row['exchanges']) if row['confirmed'] else 'Withheld · ' + row['reason'].replace('_', ' ')
    security = ' · ' + row['security_class'] if row['security_class'] else ''
    date = (f'<p>Filed {row["filed"]} · report date {row["report_date"]} · accepted {row["accepted_at"]}.</p>'
            if 'filed' in row else '')
    archive = (f'<p>Cover observed {row["observed_at"]} · SHA-256 {row["payload_sha256"]}.</p>'
               if 'payload_sha256' in row else '')
    submissions = (f'<p>{_source_link(row["metadata_url"], "SEC submissions")} observed {row["metadata_observed_at"]}'
                   f' · SHA-256 {row["metadata_sha256"]}.</p>' if 'metadata_sha256' in row else '')
    return (
        f'<li><strong>{row["symbol"]}</strong>{escape(security)} · {escape(outcome)}'
        f'<details><summary>Filing evidence for {row["symbol"]}</summary>'
        f'<p>CIK {row["cik"]} · {_source_link(row["source_url"], "Form " + row["form"] + " " + row["accession"])}.</p>'
        + date + archive + _post_filing_html(row, spotlight_date) + submissions + '</details></li>'
    )


def ltse_html(result):
    if result['status'] != 'inspection_only':
        return '<p>' + escape(result.get('reason', 'Run the check to verify the three spotlight securities in SEC filings.')) + '</p>'
    count = result['sample_count']
    confirmed = result['confirmed_count']
    spotlight_date = result['spotlight_observed_on']
    spotlight = (f' observed on {spotlight_date}.' if spotlight_date
                 else ' has no reviewed observation by this cutoff.')
    notice_review = ''
    if spotlight_date:
        notice_review = (
            f'<p>Public review on {spotlight_date} found no listing or removal notice for the three sample securities after '
            f'their respective filings in the reviewed {_source_link(LTSE_NOTICES_URL, "LTSE customer notices")} and '
            f'{_source_link(SEC_NOTICE_SEARCH_URL, "SEC registration and removal form search")}.</p>'
            f'<p>Reviewed {_source_link(JUNE_FORM_1_URL, "June 30 Form 1 amendment")} and '
            f'{_source_link(OCTOBER_FORM_1_URL, "October 30 Form 1 amendment")}. The public filings did not supply a complete roster.</p>'
        )
    return (
        '<section aria-label="LTSE filing reconciliation" style="overflow-wrap:anywhere;min-width:0">'
        '<h3>LTSE listing evidence</h3>'
        f'<p><strong>{confirmed} of {count} LTSE dual listings confirmed as filed</strong> · '
        f'{result["security_identity_count"]} security identities supported · {count - confirmed} sample records unresolved.</p>'
        f'<p>{_source_link(SPOTLIGHT_URL, "Official company spotlight")}{spotlight} '
        'The spotlight defines the sample. Complete dated roster withheld. The filing checks apply to each filing date.</p>'
        '<ul>' + ''.join(_row_html(row, spotlight_date) for row in result['rows']) + '</ul>'
        '<details><summary>Historical case and remaining gaps</summary>'
        '<p>TWLO is separate from this sample. LTSE set removal of its Class A common stock for the close on 2022-12-29. '
        + _source_link(TWLO_CIRCULAR_URL, 'LTSE circular') + ' · ' + _source_link(TWLO_FORM_25_URL, 'SEC Form 25') + '.</p>'
        + notice_review + '<p>Current roster status, first trades and continuous venue membership remain unverified. '
        'LTSE’s filed Exhibit N makes its schedule available on request. '
        + _source_link(EXHIBIT_N_URL, 'SEC Exhibit N') + '.</p></details>'
        '<p>Personal inspection only. Saved inventory, issuer domicile, financial coverage and analysis eligibility are separate.</p>'
        '</section>'
    )
