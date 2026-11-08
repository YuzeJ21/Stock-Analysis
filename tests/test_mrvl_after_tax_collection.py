"""Collector request boundaries with constructed SEC transport, no real figures."""
from copy import deepcopy
import sys
from types import SimpleNamespace

import pytest

from tests.test_mrvl_earnings_sources import (
    _collect, _facts_receipt, _fetcher, _sources, MRVL_PROFILE, AVGO_PROFILE,
    MRVL_DOCUMENT, AVGO_DOCUMENT,
)

PRIMARY = 'https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/mrvl-20260305.htm'
EXHIBIT = 'https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/q426_8kx1312026ex-991.htm'


def _install_selector(monkeypatch, *, qualified=True):
    observations = []
    def select(receipt, *, as_of=None):
        observations.append((receipt, as_of))
        return ({'status': 'selected'} if qualified else
                {'status': 'withheld', 'reason': 'reconciliation_8k_scope_unavailable'})
    monkeypatch.setitem(sys.modules, 'src.mrvl_after_tax_reconciliation', SimpleNamespace(
        select_mrvl_after_tax_source=select,
        RECONCILIATION_POLICY={'primary_url': PRIMARY, 'exhibit_url': EXHIBIT},
    ))
    return observations


def test_qualified_reconciliation_reuses_profile_and_adds_only_two_fixed_html_requests(monkeypatch):
    observations = _install_selector(monkeypatch)
    sources = _sources(); sources.update({PRIMARY: b'<html>Constructed primary</html>',
                                         EXHIBIT: b'<html>Constructed exhibit</html>'})
    calls = []; facts = _facts_receipt(); before = deepcopy(facts)
    packet = _collect(facts, source_fetcher=_fetcher(sources, calls))
    assert calls == [MRVL_PROFILE, MRVL_DOCUMENT, AVGO_PROFILE, AVGO_DOCUMENT, PRIMARY, EXHIBIT]
    assert len(observations) == 1
    assert observations[0][0] == packet['profiles']['MRVL']
    extension = packet['after_tax_reconciliation']
    assert extension['schema_version'] == 'mrvl-after-tax-reconciliation-v1'
    assert extension['primary']['source_url'] == PRIMARY
    assert extension['exhibit']['source_url'] == EXHIBIT
    assert extension['primary']['status'] == extension['exhibit']['status'] == 'ready'
    assert set(packet['profiles']) == set(packet['documents']) == {'MRVL', 'AVGO'}
    assert facts == before


def test_unqualified_8k_metadata_never_requests_an_earnings_document(monkeypatch):
    _install_selector(monkeypatch, qualified=False)
    calls = []
    packet = _collect(source_fetcher=_fetcher(_sources(), calls))
    assert calls == [MRVL_PROFILE, MRVL_DOCUMENT, AVGO_PROFILE, AVGO_DOCUMENT]
    assert packet['after_tax_reconciliation']['reason'] == 'reconciliation_8k_scope_unavailable'


def test_failed_primary_does_not_request_exhibit_or_erase_annual_receipts(monkeypatch):
    _install_selector(monkeypatch)
    sources = _sources(); sources[PRIMARY] = OSError('Constructed source failure')
    calls = []; packet = _collect(source_fetcher=_fetcher(sources, calls))
    assert calls == [MRVL_PROFILE, MRVL_DOCUMENT, AVGO_PROFILE, AVGO_DOCUMENT, PRIMARY]
    assert packet['after_tax_reconciliation']['primary']['status'] == 'unavailable'
    assert packet['after_tax_reconciliation']['exhibit']['status'] == 'unavailable'
    assert packet['documents']['MRVL']['status'] == packet['documents']['AVGO']['status'] == 'ready'


def test_failed_exhibit_preserves_the_independent_primary_and_annual_receipts(monkeypatch):
    _install_selector(monkeypatch)
    sources = _sources(); sources.update({PRIMARY: b'<html>Constructed primary</html>',
                                         EXHIBIT: TimeoutError('Constructed timeout')})
    calls = []; packet = _collect(source_fetcher=_fetcher(sources, calls))
    assert len(calls) == 6 and calls[-1] == EXHIBIT
    assert packet['after_tax_reconciliation']['primary']['status'] == 'ready'
    assert packet['after_tax_reconciliation']['exhibit']['status'] == 'unavailable'
    assert packet['facts']['status'] == 'ready'


@pytest.mark.parametrize('failure', ['changed_annual', 'profile_unavailable'])
def test_unqualified_current_annual_scope_prevents_extra_reconciliation_requests(monkeypatch, failure):
    _install_selector(monkeypatch)
    sources = _sources()
    if failure == 'profile_unavailable':
        sources[MRVL_PROFILE] = OSError('Constructed missing profile')
    else:
        sources[MRVL_PROFILE]['filings']['recent']['accessionNumber'][0] = '0001835632-26-000099'
    calls = []; packet = _collect(source_fetcher=_fetcher(sources, calls))
    assert PRIMARY not in calls and EXHIBIT not in calls
    assert packet['after_tax_reconciliation']['status'] == 'unavailable'
    assert packet['documents']['AVGO']['status'] == 'ready'
