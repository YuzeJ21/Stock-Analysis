"""A bounded NYSE Texas registration audit using dated SEC filings."""
from datetime import datetime, timezone
from html import escape
import re
from urllib.error import HTTPError

from src.online_company_identity import _mode_reason
from src.online_sec_receipt import _fetch_raw, fetch_sec_json_receipt
from src.sec_exact_filing import RIGHTS, _fetch_html
from src.sec_listing_cover import (
    MAX_COVER_BYTES, FilingCase, cover_exchanges, document_receipt, filing_metadata, read_listing_cover,
)

SESSION_KEY = 'nyse_texas_reconciliation_v4'
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


CASES = (
    FilingCase('ICE', '0001571949', '0001104659-26-119880', 'tm2628301d1_8k.htm'),
    FilingCase('HAL', '0000045012', '0000045012-26-000069', 'hal-20261015.htm'),
    FilingCase('ABT', '0000001800', '0001104659-26-099247', 'tm2623675d1_8k.htm'),
    FilingCase('OIS', '0001121484', '0001121484-26-000036', 'ois-20261030.htm'),
)

DIT_FILINGS = (
    FilingCase('DIT', '0000928465', '0001104659-26-094454', 'tm2622611d1_8a12b.htm', '8-A12B'),
    FilingCase('DIT', '0000928465', '0000876882-26-000018', 'DIT081226.pdf', 'CERT'),
)
DIT_NOTICE = FilingCase('DIT', '0000928465', '0001104659-26-094451', 'tm2622611d2_8k.htm')
DIT_FILED = '2026-08-12'
DIT_ANNOUNCED_EFFECTIVE = '2026-08-13'
DIT_DIRECTORY_URL = 'https://www.nyse.com/markets/nyse-texas'
# Dated browser review of the DIT row. The exchange page supplies no as-of timestamp.
DIT_DIRECTORY_REVIEW_DATE = '2026-11-04'
DIT_FIRST_TRADE_REVIEW_DATE = '2026-11-04'
DIT_SHORT_VOLUME_URL = 'https://ftp.nyse.com/ShortData/Texasshvol/Texasshvol2026/Texasshvol202608/Texasshvol20260813.pdf'
DIT_TAQ_URL = 'https://www.nyse.com/market-data/historical/taq-trades'
DIT_TAQ_SAMPLE_URL = 'https://ftp.nyse.com/Historical%20Data%20Samples/TAQ%20NYSE%20TEXAS%20TRADES/'
DIT_TRADER_UPDATES_URL = 'https://www.nyse.com/trader-update/history'
DIT_UTP_NOTICE_URL = 'https://www.sec.gov/files/rules/sro/nysetex/2026/34-105815.pdf'
DIT_FIRST_TRADE_SOURCES = (
    ('NYSE TAQ Trades catalog', DIT_TAQ_URL,
     'Lists a historical NYSE Texas trade-by-trade product for purchase. No entitled DIT trade file was reviewed.'),
    ('NYSE Texas TAQ public sample index', DIT_TAQ_SAMPLE_URL,
     'The listed files cover July 1–2, 2026 only. The index supplies neither the August 13 file nor continuous earlier coverage.'),
    ('NYSE Trader Updates archive', DIT_TRADER_UPDATES_URL,
     'The AMCON and NYSE Texas ticker searches did not surface a notice confirming a DIT execution.'),
    ('NYSE Texas August 13 short-volume report', DIT_SHORT_VOLUME_URL,
     'Covers short-volume activity. The report did not establish a DIT execution.'),
    ('SEC June 30 notice on NYSE Texas trade reports', DIT_UTP_NOTICE_URL,
     'NYSE Texas can trade securities listed elsewhere under unlisted trading privileges. Earlier DIT executions remain possible.'),
)
# Exact reviewed bytes bind the registration pair and the issuer's announcement.
# Replacements require a fresh content review, even at the same URL.
DIT_REVIEWED_DIGESTS = {
    '8-A12B': '72f4bef64b1e8f7bcf55718f6092744066198200300b65fb891d63988907e15b',
    'CERT': '74a1dbe48d0d7c66c802acf3cbb52fe9287b90e20d8bbbe44bc0d900221ce5dd',
    '8-K': 'cf370e90e2274e9b6f90cf4c3798afa53658668d85b8cc1c203f93195e0bd52d',
}


def cover_registration(raw, symbol):
    cover = read_listing_cover(raw, symbol)
    if cover is None:
        return None
    title, venues = cover
    kind = 'common_shares' if re.fullmatch(
        r'(?:class [a-z0-9]+ )?(?:common stock|common shares)(?:,? (?:without par value|par value \$[.\d]+ per share|\$[.\d]+ par value(?: per share)?))?',
        title, re.I,
    ) else None
    return kind, cover_exchanges(venues, EXCHANGES)


def _reviewed_dit_filing(case, metadata_receipt, transport, user_agent, observed_at):
    evidence = dict(form=case.form, accession=case.accession, source_url=case.source_url)
    metadata = filing_metadata(metadata_receipt, case, registration_date=DIT_FILED if case.form != '8-K' else None)
    if metadata is None or metadata['filed'] != DIT_FILED:
        return evidence, 'metadata_mismatch'
    evidence.update(filed=metadata['filed'], report_date=metadata['report_date'], accepted_at=metadata['accepted_at'])
    try:
        raw, _, final = transport(case.source_url, user_agent)
    except (OSError, RuntimeError, ValueError):
        return evidence, 'unavailable'
    receipt = document_receipt(raw, final, case, observed_at)
    if receipt is None:
        return evidence, 'response_unverified'
    if receipt['payload_sha256'] != DIT_REVIEWED_DIGESTS[case.form]:
        return evidence, 'digest_mismatch'
    return {**evidence, **receipt}, None


def _check_dit(user_agent, transport, observed_at, *, access_paused):
    form, certificate = DIT_FILINGS
    filings = [dict(form=case.form, accession=case.accession, source_url=case.source_url) for case in DIT_FILINGS]
    today = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()
    directory_date = DIT_DIRECTORY_REVIEW_DATE if today >= DIT_DIRECTORY_REVIEW_DATE else None
    trade_review_date = DIT_FIRST_TRADE_REVIEW_DATE if today >= DIT_FIRST_TRADE_REVIEW_DATE else None
    row = dict(symbol=form.symbol, cik=form.cik, metadata_url=form.metadata_url, filings=filings,
               confirmed=False, security_type=None, reason='filing_metadata_unavailable',
               announced_effective_date=None, first_trade_date=None, directory_observed_on=directory_date,
               first_trade_reviewed_on=trade_review_date, announcement_reason='filing_metadata_unavailable')
    if access_paused():
        row.update(reason='sec_access_paused', announcement_reason='sec_access_paused')
        return row
    metadata_receipt = fetch_sec_json_receipt(form.metadata_url, user_agent=user_agent, fetcher=transport,
                                              observed_at=observed_at)
    if metadata_receipt['status'] != 'ready':
        if access_paused():
            row.update(reason='sec_access_paused', announcement_reason='sec_access_paused')
        return row
    row.update(metadata_observed_at=metadata_receipt['observed_at'], metadata_sha256=metadata_receipt['payload_sha256'])
    for case, evidence, role in zip((form, certificate), filings, ('form_8a', 'certificate')):
        receipt, reason = _reviewed_dit_filing(case, metadata_receipt, transport, user_agent, observed_at)
        evidence.update(receipt)
        if reason is not None:
            row['reason'] = 'sec_access_paused' if access_paused() else role + '_' + reason
            break
        if case == form:
            row.update(security_type='common_shares', par_value='USD 0.01 per share', exchanges=('NYSE American',))
    else:
        row.update(confirmed=True, reason=None, exchanges=('NYSE American', 'NYSE Texas'))

    if not access_paused():
        receipt, reason = _reviewed_dit_filing(DIT_NOTICE, metadata_receipt, transport, user_agent, observed_at)
        row.update(announcement=receipt, announcement_reason='sec_access_paused' if access_paused() else reason)
        if reason is None:
            row['announced_effective_date'] = DIT_ANNOUNCED_EFFECTIVE
    else:
        row['announcement_reason'] = 'sec_access_paused'
    return row


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
                accept = 'application/pdf' if url == DIT_FILINGS[1].source_url else 'text/html'
                return _fetch_html(url, agent, max_bytes=MAX_COVER_BYTES, accept=accept)
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
        metadata = filing_metadata(receipt, case)
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
        receipt = document_receipt(raw, final, case, observed_at)
        if receipt is None:
            row['reason'] = 'filing_response_unverified'
            continue
        row.update(receipt)
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
    rows.append(_check_dit(user_agent, transport, observed_at, access_paused=lambda: paused))
    return dict(status='inspection_only', rights_status=RIGHTS, rows=rows, sample_count=len(rows),
                confirmed_count=sum(row['confirmed'] for row in rows),
                security_identity_count=sum(row['security_type'] is not None for row in rows))


def get_nyse_texas(state, *, refresh, user_agent, workspace_mode='research', fetcher=None, observed_at=None):
    if _mode_reason(workspace_mode):
        return dict(status='withheld', reason='Available in Personal Research only.')
    if refresh:
        state[SESSION_KEY] = check_nyse_texas(user_agent=user_agent, workspace_mode=workspace_mode,
                                            fetcher=fetcher, observed_at=observed_at)
    return state.get(SESSION_KEY, dict(status='not_requested'))


def _filing_html(filing):
    form = filing.get('form', '8-K')
    label = {'8-K': 'Form 8-K', '8-A12B': 'Form 8-A', 'CERT': 'Exchange certification'}[form]
    link = (f'<a href="{filing["source_url"]}" target="_blank" rel="noopener noreferrer">'
            f'{label} {filing["accession"]}</a>')
    dates = ''
    if 'filed' in filing:
        dates = f' · filed {filing["filed"]} · accepted {filing["accepted_at"]}'
        if filing['report_date']:
            dates += f' · report date {filing["report_date"]}'
    observation = (f'<br>Observed {filing["observed_at"]} · SHA-256 {filing["payload_sha256"]}'
                   if 'observed_at' in filing else '')
    return f'<p>{link}{dates}{observation}.</p>'


def _dit_trading_html(row):
    announced = row['announced_effective_date'] or 'Withheld · ' + row['announcement_reason'].replace('_', ' ')
    notice = _filing_html(row['announcement']) if 'announcement' in row else ''
    reviewed = row['directory_observed_on']
    directory = (f'Present when reviewed on {reviewed}. The directory gives no effective timestamp.'
                 if reviewed else 'Withheld · no reviewed directory observation by this cutoff.')
    trade_review = ''
    if row['first_trade_reviewed_on']:
        sources = ''.join(f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{escape(label)}</a> '
                          f'· {escape(finding)}</li>' for label, url, finding in DIT_FIRST_TRADE_SOURCES)
        trade_review = (
            f'<details><summary>First-trade sources checked · {escape(row["first_trade_reviewed_on"])}</summary>'
            '<ul>' + sources + '</ul><p>A dated execution proves trading by that date. Confirming the first date requires '
            'continuous venue coverage from initial eligibility or an exchange statement identifying the first execution.</p></details>'
        )
    return (
        '<section aria-label="DIT trading and listing evidence">'
        f'<p><strong>Announced listing effective date</strong> · {escape(announced)}</p>' + notice
        + '<p><strong>Actual first trade</strong> · Withheld. No dated NYSE Texas execution was verified for DIT.</p>'
        + trade_review + f'<p><strong>NYSE Texas directory</strong> · {escape(directory)} '
        f'<a href="{DIT_DIRECTORY_URL}" target="_blank" rel="noopener noreferrer">Official dual-listing directory</a>.</p></section>'
    )


def reconciliation_html(result):
    if result['status'] != 'inspection_only':
        return '<p>' + escape(result.get('reason', 'Run the check to inspect five selected securities in SEC filings.')) + '</p>'
    details = []
    for row in result['rows']:
        outcome = 'Dual registration observed' if row['confirmed'] else 'Withheld · ' + row['reason'].replace('_', ' ')
        venues = ', '.join(row.get('exchanges', ()))
        filings = ''.join(_filing_html(filing) for filing in row.get('filings', [row]))
        par_value = ' · ' + escape(row['par_value']) if 'par_value' in row else ''
        roles = ('<p>Form 8-A identifies the ticker, share class and NYSE American listing. '
                 'The certificate covers NYSE Texas approval for the same issuer and share class.</p>'
                 if 'filings' in row else '')
        trading = _dit_trading_html(row) if row['symbol'] == 'DIT' else ''
        metadata = (f'<p><a href="{row["metadata_url"]}">SEC submissions</a> observed {row["metadata_observed_at"]}'
                    f' · SHA-256 {row["metadata_sha256"]}.</p>' if 'metadata_sha256' in row else '')
        details.append(
            f'<li><strong>{row["symbol"]}</strong> · {escape(outcome)}'
            + (' · Common shares as filed' + par_value if row['security_type'] else '')
            + (f' · {escape(venues)}' if venues else '')
            + f'<details><summary>Filing evidence for {row["symbol"]}</summary>'
              f'<p>CIK {row["cik"]}.</p>'
            + trading + roles + filings + metadata + '</details></li>'
        )
    count = result['sample_count']
    confirmed = result['confirmed_count']
    return (
        '<section aria-label="NYSE Texas filing reconciliation" style="overflow-wrap:anywhere;min-width:0">'
        f'<h3>NYSE Texas filing reconciliation</h3>'
        f'<p><strong>{confirmed} of {count} dual registrations confirmed as filed</strong> · '
        f'{result["security_identity_count"]} security identities supported · {count - confirmed} sample records unresolved.</p>'
        '<p>Current active status beyond the dated directory review, the venue-wide count, issuer domicile, analysis eligibility, '
        'and historical membership remain unverified. Personal inspection only. The saved inventory and financial coverage are separate.</p>'
        '<ul>' + ''.join(details) + '</ul></section>'
    )
