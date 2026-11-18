from copy import deepcopy
from hashlib import sha256

import pytest

from test_sec_inline_filing import OBSERVED, _extract, _selection, _xml
from test_sec_online_quarter_evidence import CIK, _financial, _profile_receipt


def _context(*, later=False, concept=None):
    from src.online_filing_context import build_filing_inventory
    from src.online_research_tools import build_online_research_context
    from src.sec_inline_filing import extract_inline_filing
    from src.sec_online_quarter_evidence import build_archive_quarter

    financial = _financial()
    packet = _extract()
    if later:
        source = _selection()
        source.update(period_end='2026-09-30', filed='2026-10-29', accepted_at='2026-10-29T12:00:00Z',
                      accession='0000004321-26-000002', primary_document='fict-20260930.htm')
        source['source_url'] = 'https://www.sec.gov/Archives/edgar/data/1234/000000432126000002/fict-20260930.htm'
        profile = _profile_receipt()
        profile['payload']['filings']['recent'].update({
            'reportDate': [source['period_end']], 'filingDate': [source['filed']],
            'acceptanceDateTime': [source['accepted_at']], 'accessionNumber': [source['accession']],
            'primaryDocument': [source['primary_document']],
        })
        financial['filing_inventory'] = build_filing_inventory(profile, ticker='FICT', expected_cik=CIK, as_of=OBSERVED)
        xml = _xml().replace('2026-04-01', '2026-07-01').replace('2026-06-30', '2026-09-30').replace('1,234', '1,500')
        if concept:
            xml = xml.replace('RegulatedAndUnregulatedOperatingRevenue', concept)
        raw = xml.encode()
        receipt = dict(status='ready', source_url=source['source_url'], observed_at='2026-10-30T21:00:00Z',
                       payload_sha256=sha256(raw).hexdigest(), source_last_modified=None)
        packet = extract_inline_filing(raw, source, receipt)
    financial['archive_quarterly'] = build_archive_quarter(financial, packet, as_of=OBSERVED)
    return build_online_research_context(financial, {}, ticker='FICT', profile_key='research', as_of=OBSERVED)


def test_adjacent_archive_quarters_replay_exact_saved_pair(tmp_path):
    from src.online_research_context_store import (
        compare_exact_filing_pair, find_saved_filing_pair, load_research_context, save_research_context,
    )

    baseline, current = _context(), _context(later=True)
    scope = dict(profile_key='research', ticker='FICT', sec_cik=CIK, project_root=tmp_path)
    earlier = save_research_context(baseline, **scope)
    later = save_research_context(current, **scope)
    matched, result = find_saved_filing_pair([later, earlier], current)
    assert matched['snapshot_id'] == earlier['snapshot_id']
    assert result['comparison_basis'] == 'quarter_over_quarter'
    assert result['baseline']['period_start'] == '2026-04-01'
    assert result['current']['period_end'] == '2026-09-30'
    assert result['baseline']['payload_sha256'] != result['current']['payload_sha256']
    assert result['fields']['revenue']['status'] == 'increased'
    assert result['fields']['revenue']['change'] == 266_000_000
    assert result['fields']['operating_income']['status'] == 'unchanged'
    for name in ('cash_from_operations', 'capital_expenditures'):
        field = result['fields'][name]
        assert field['status'] == 'withheld' and field['change'] is None
        assert field['baseline'] is None and field['current'] is None
        assert field['reason'] == 'Both filings report only a year-to-date figure'
    paths = list(tmp_path.rglob('*.json'))
    snapshots = [path.read_bytes() for path in paths]
    restored = [load_research_context(item['snapshot_id'], **scope) for item in (earlier, later)]
    assert compare_exact_filing_pair(*restored) == result
    assert [path.read_bytes() for path in paths] == snapshots


def test_archive_pair_requires_compatible_facts_and_original_receipts():
    from src.online_research_context_store import compare_exact_filing_pair, find_saved_filing_pair

    baseline, current = _context(), _context(later=True, concept='Revenues')
    earnings = compare_exact_filing_pair(baseline, current)['fields']
    assert earnings['revenue']['reason'] == 'Filing field definitions differ'
    assert earnings['operating_income']['status'] == 'unchanged'
    assert compare_exact_filing_pair(current, baseline)['status'] == 'withheld'
    assert compare_exact_filing_pair(current, current)['status'] == 'same_filing'
    with pytest.raises(ValueError, match='scope'):
        compare_exact_filing_pair(baseline, {**current, 'profile_key': 'another-profile'})

    altered = deepcopy(baseline)
    receipt = next(ref for ref in altered['source_receipts']
                   if ref['source'] == 'exact_quarter_receipt' and ref['source_url'].endswith('.htm'))
    receipt['payload_sha256'] = 'e' * 64
    assert compare_exact_filing_pair(altered, current)['status'] == 'withheld'
    assert find_saved_filing_pair([{'context': altered}], current) is None
