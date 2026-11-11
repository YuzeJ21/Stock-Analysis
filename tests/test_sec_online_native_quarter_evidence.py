from copy import deepcopy
from datetime import timedelta

import pytest

from test_sec_inline_filing import OBSERVED
from test_sec_online_annual_evidence import SOURCE, SUB, _online, _sources


def _add(sources, sequence, *, filed='2026-10-15', report_date='2026-10-15',
         form='6-K', name=None, content=None):
    accession = f'0000001234-26-{sequence:06d}'
    document = name if name is not None else f'filing{sequence}.htm'
    url = f'https://www.sec.gov/Archives/edgar/data/1234/{accession.replace("-", "")}/{document}'
    values = dict(accessionNumber=accession, reportDate=report_date, filingDate=filed,
                  acceptanceDateTime=filed + 'T12:00:00Z', form=form, primaryDocument=document,
                  isInlineXBRL=0, isXBRL=0)
    recent = sources[SUB]['filings']['recent']
    for key, entries in recent.items():
        entries.append(values[key])
    sources[url] = content
    return url


def _cover(*, href='quarterly-release.htm', label='Quarterly earnings release'):
    return f'''<html><body>FORM 6-K<table>
        <tr><th>Exhibit Number</th><th>Exhibit Description</th></tr>
        <tr><td>99.1</td><td><a href="{href}">{label}</a></td></tr>
        </table></body></html>'''


def _results():
    return '''<html><body><h1>Unaudited Consolidated Financial Results for the Third Quarter of 2026</h1>
        <p>Condensed Consolidated Statements of Income</p>
        <table><tr><td>(TWD in millions)</td><td colspan="2">Three months ended September 30,</td>
          <td colspan="2">Nine months ended September 30,</td></tr>
        <tr><td></td><td>2026</td><td>2025</td><td>2026</td><td>2025</td></tr>
        <tr><td>Revenue</td><td>1,234</td><td>1,000</td><td>3,456</td><td>3,000</td></tr>
        <tr><td>Operating income</td><td>123</td><td>100</td><td>321</td><td>300</td></tr></table></body></html>'''


def _quarter_sources():
    sources = _sources()
    cover = _add(sources, 2, content=_cover())
    exhibit = cover.rsplit('/', 1)[0] + '/quarterly-release.htm'
    sources[exhibit] = _results()
    latest = _add(sources, 3, filed='2026-10-20', content='<html><body>FORM 6-K'
                  '<h2>Monthly Sales Report</h2><p>For September 2026</p></body></html>')
    return sources, latest, cover, exhibit


def test_exact_exhibit_and_embedded_primary_keep_explicit_durations_separate():
    from src.sec_online_native_quarter_evidence import validated_native_quarter
    sources, latest, cover, exhibit = _quarter_sources()
    calls = []
    financial = _online(sources, calls)
    assert calls[-4:] == [SOURCE, latest, cover, exhibit]
    before = deepcopy(financial)
    dto = validated_native_quarter(financial, as_of=OBSERVED)
    assert financial == before
    assert dto['period_end'] == '2026-09-30' and dto['report_date'] == '2026-10-15'
    assert dto['primary_source_url'] == cover and dto['source_url'] == exhibit
    assert dto['rights_status'] == 'unregistered_sec_archive_personal_inspection_only'
    assert dto['commercial_eligible'] is dto['saved_readiness_promoted'] is False
    quarter, cumulative = dto['periods']
    assert quarter['kind'] == 'quarterly' and quarter['period_start'] == '2026-07-01'
    assert cumulative['kind'] == 'cumulative' and cumulative['period_start'] == '2026-01-01'
    assert quarter['fields']['revenue']['value'] == 1_234_000_000
    assert cumulative['fields']['revenue']['value'] == 3_456_000_000
    assert cumulative['fields']['revenue']['source_ref'] == exhibit
    sources[cover] = _results().replace('<body>', '<body>FORM 6-K')
    calls.clear()
    dto = validated_native_quarter(_online(sources, calls), as_of=OBSERVED)
    assert calls[-3:] == [SOURCE, latest, cover]
    assert dto['source_url'] == dto['primary_source_url'] == cover


@pytest.mark.parametrize('href', ['https://example.org/quarterly-release.htm', '../quarterly-release.htm',
    '//www.sec.gov/quarterly-release.htm', 'quarterly-release.htm?x=1',
    '/Archives/edgar/data/4321/000000123426000002/quarterly-release.htm'])
def test_untrusted_exhibit_href_is_never_requested(href):
    sources, latest, cover, exhibit = _quarter_sources()
    sources[cover] = _cover(href=href)
    calls = []
    financial = _online(sources, calls)
    assert calls[-2:] == [latest, cover]
    assert exhibit not in calls
    assert financial['native_archive_quarter']['reason'] == 'native_quarter_exhibit_link_unresolved'


def test_ambiguous_newer_amendment_blocks_older_result_without_fetching_it():
    sources, _, cover, exhibit = _quarter_sources()
    amendment = _add(sources, 4, filed='2026-10-26', form='6-K/A',
                     content='<html><body>FORM 6-K/A <p>Amendment and explanatory note</p></body></html>')
    calls = []
    financial = _online(sources, calls)
    assert calls[-1] == amendment
    assert cover not in calls and exhibit not in calls
    assert financial['native_archive_quarter']['reason'] == 'native_quarter_amendment_unresolved'


def test_exhibit_receipt_period_and_numeric_tampering_remain_held_after_reseal():
    from src.sec_online_native_quarter_evidence import validated_native_quarter
    from src.online_filing_context import _digest
    base = _online(_quarter_sources()[0])
    for problem in ('receipt', 'report_date', 'duration', 'literal', 'rights'):
        financial = deepcopy(base)
        dto = financial['native_archive_quarter']
        if problem == 'receipt':
            dto['source_receipts'][-1]['source_url'] = dto['primary_source_url']
        elif problem == 'report_date':
            dto['report_date'] = '2026-09-30'
        elif problem == 'duration':
            dto['periods'][0]['period_start'] = '2026-01-01'
        elif problem == 'literal':
            dto['periods'][0]['fields']['revenue']['value'] += 1
        else:
            dto['commercial_eligible'] = True
        dto['packet_digest'] = _digest({k: v for k, v in dto.items() if k != 'packet_digest'})
        assert validated_native_quarter(financial, as_of=OBSERVED) is None
    assert validated_native_quarter(base, as_of=OBSERVED + timedelta(hours=25)) is None


def test_request_bound_keeps_an_older_filing_out_of_scope():
    from src.sec_online_native_quarter_evidence import MAX_PRIMARY_REQUESTS
    sources = _sources()
    older = _add(sources, 2, filed='2026-10-01', content=_cover())
    newest = []
    for i in range(MAX_PRIMARY_REQUESTS + 2):
        newest.append(_add(sources, 10 + i, filed=f'2026-10-{10 + i}',
            content='<html><body>FORM 6-K <h2>Monthly Sales Report</h2></body></html>'))
    calls = []
    financial = _online(sources, calls)
    assert calls[-MAX_PRIMARY_REQUESTS:] == list(reversed(newest[-MAX_PRIMARY_REQUESTS:]))
    assert older not in calls
    assert financial['native_archive_quarter']['reason'] == 'native_quarter_candidate_limit'


def test_hidden_results_link_is_not_a_candidate():
    sources, latest, cover, exhibit = _quarter_sources()
    sources[cover] = sources[cover].replace('<tr><td>99.1', '<tr hidden><td>99.1')
    calls = []
    financial = _online(sources, calls)
    assert calls[-2:] == [latest, cover]
    assert exhibit not in calls
    assert financial['native_archive_quarter']['reason'] == 'native_quarter_newer_filing_scope_unresolved'


def test_provisional_marker_cannot_be_discarded_from_a_reported_row():
    from src.online_filing_context import _digest
    from src.sec_online_native_quarter_evidence import validated_native_quarter
    from test_sec_native_quarter_tables import quarter_release

    sources, _, _, exhibit = _quarter_sources()
    sources[exhibit] = quarter_release()
    financial = _online(sources)
    assert validated_native_quarter(financial, as_of=OBSERVED)['periods'][0]['provisional'] is True
    dto = financial['native_archive_quarter']
    dto['periods'][0]['provisional'] = False
    dto['packet_digest'] = _digest({key: value for key, value in dto.items() if key != 'packet_digest'})
    assert validated_native_quarter(financial, as_of=OBSERVED) is None
