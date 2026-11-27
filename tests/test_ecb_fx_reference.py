"""Exact source/decimal selection, bounded transport, and public-only capture output."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from fx_reference_fixtures import XML, URL, NOW


def parse(raw=XML, **changes):
    from src.ecb_fx_reference import parse_ecb_usd
    return parse_ecb_usd(raw, **dict(reference_date='2026-11-06', observed_at=NOW, **changes))


def test_exact_usd_token_retains_direction_precision_and_original_byte_digest():
    receipt = parse()
    assert receipt['rate_literal'] == '1.2500'
    assert receipt['base_currency'] == 'EUR' and receipt['quote_currency'] == 'USD'
    assert receipt['quote_convention'] == 'USD_per_EUR'
    assert receipt['reference_date'] == '2026-11-06'
    assert receipt['payload_sha256'] == sha256(XML).hexdigest()
    assert receipt['observed_at'] == '2026-11-09T12:00:00Z'
    assert receipt['first_publication_status'] == 'unverified'
    assert receipt['commercial_eligible'] is False


def test_large_non_usd_quote_does_not_invalidate_the_selected_usd_observation():
    raw = XML.replace(b'<Cube currency="CAD" rate="1.5000"/>', b'<Cube currency="IDR" rate="20000.1234"/>')
    assert parse(raw)['rate_literal'] == '1.2500'


@pytest.mark.parametrize('raw', [
    XML.replace(b'1.2500',b'0'), XML.replace(b'1.2500',b'-1.2'), XML.replace(b'1.2500',b'NaN'),
    XML.replace(b'1.2500',b'1e2'), XML.replace(b'1.2500',b'1.123456789'),
    XML.replace(b'currency="USD"',b'currency="EUR"'),
    XML.replace(b'rate="1.2500"',b'rate="1.2500" unit="EUR/USD"'),
    XML.replace(b'2026-11-06',b'2026-11-05'),
    XML.replace(b'European Central Bank',b'Another Bank'),
    XML.replace(b'www.ecb.int/vocabulary',b'example.invalid/vocabulary'),
    XML.replace(b'www.gesmes.org',b'example.invalid'),
    XML.replace(b'<Cube>',b'<Cube base="USD">'),
    XML.replace(b'</gesmes:name>',b'</gesmes:name><gesmes:name>Another Bank</gesmes:name>'),
    XML.replace(b'</gesmes:name>',b'<nested/></gesmes:name>'),
    XML.replace(b'<Cube>',b'<foreign/> <Cube>'),
    XML.replace(b'<Cube>',b'Base currency USD<Cube>'),
    XML.replace(b'1.2500', '1.２５００'.encode()),
    XML.replace(b'currency="CAD" rate="1.5000"', b'currency="EUR" rate="0.8000"'),
    XML.replace(b'<Cube currency="CAD" rate="1.5000"/>',b'<Cube currency="USD" rate="1.2500"/>'),
    XML.replace(b'</Cube></Cube>',b'</Cube><Cube time="2026-11-06"><Cube currency="USD" rate="1.2500"/></Cube></Cube>'),
    b'<!DOCTYPE x [<!ENTITY x "bad">]>' + XML, XML.replace(b'<Cube>',b'<Cube>&unresolved;'),
    b'\xff\xfe'+XML, b'<html>Unavailable</html>', b'<' + b'x' * (2*1024*1024),
], ids=lambda raw:sha256(raw).hexdigest()[:10])
def test_ambiguous_foreign_or_malformed_source_never_produces_a_rate(raw):
    with pytest.raises(ValueError): parse(raw)


def test_future_reference_date_or_naive_observation_is_rejected():
    from src.ecb_fx_reference import parse_ecb_usd
    with pytest.raises(ValueError):
        parse_ecb_usd(XML, reference_date='2026-11-06', observed_at=datetime(2026,11,5,12,tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        parse_ecb_usd(XML, reference_date='2026-11-06', observed_at=datetime(2026,11,9,12))


def test_capture_is_one_exact_request_and_records_time_after_transport():
    from src.ecb_fx_reference import capture_ecb_usd
    events = []
    def fetch(url):
        assert url == URL
        events.append('fetch')
        return XML, {'Last-Modified':'Mon, 09 Nov 2026 11:00:00 GMT'}, URL
    def clock():
        events.append('clock')
        return NOW
    result = capture_ecb_usd('2026-11-06', fetcher=fetch, clock=clock)
    assert result['status'] == 'captured' and result['xml'] == XML
    assert result['receipt']['last_modified'] == 'Mon, 09 Nov 2026 11:00:00 GMT'
    assert events == ['fetch', 'clock']


@pytest.mark.parametrize('change', ['redirect','oversize','failure'])
def test_unavailable_or_changed_endpoint_has_no_rate_and_no_retry(change):
    from src.ecb_fx_reference import capture_ecb_usd
    calls = []
    def fetch(url):
        calls.append(url)
        if change == 'failure': raise OSError('Unavailable')
        return (XML if change != 'oversize' else b'x' * (2*1024*1024+1), {},
                'https://example.invalid/' if change == 'redirect' else URL)
    result = capture_ecb_usd('2026-11-06', fetcher=fetch, clock=lambda:NOW)
    assert result['status'] == 'withheld' and 'xml' not in result and 'receipt' not in result
    assert calls == [URL]


def test_commercial_mode_cannot_reach_transport(monkeypatch):
    from src.ecb_fx_reference import capture_ecb_usd
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    result = capture_ecb_usd('2026-11-06', fetcher=lambda url:pytest.fail('Blocked mode fetched source'))
    assert result['status'] == 'withheld'


def test_cli_outputs_public_source_allowlist_and_refuses_overwriting_a_capture(tmp_path):
    from src.ecb_fx_reference import main
    out = tmp_path / 'capture'
    fetch = lambda url:(XML, {}, URL)
    assert main(['capture','--reference-date','2026-11-06','--output-dir',str(out)], fetcher=fetch, clock=lambda:NOW) == 0
    assert {p.name for p in out.iterdir()} == {'fx.xml','receipt.json','SOURCE.txt'}
    assert (out/'fx.xml').read_bytes() == XML
    receipt = json.loads((out/'receipt.json').read_text())
    assert receipt['status'] == 'captured' and receipt['receipt']['rate_literal'] == '1.2500'
    before = {p.name:p.read_bytes() for p in out.iterdir()}
    assert main(['capture','--reference-date','2026-11-06','--output-dir',str(out)],
        fetcher=lambda url:pytest.fail('Existing output reached transport')) == 2
    assert {p.name:p.read_bytes() for p in out.iterdir()} == before


def test_cli_held_capture_is_explicit_and_has_no_fabricated_xml(tmp_path):
    from src.ecb_fx_reference import main
    out = tmp_path / 'held'
    def unavailable(url): raise OSError('offline')
    assert main(['capture','--reference-date','2026-11-06','--output-dir',str(out)], fetcher=unavailable) == 2
    assert {p.name for p in out.iterdir()} == {'receipt.json','SOURCE.txt'}
    assert json.loads((out/'receipt.json').read_text())['status'] == 'withheld'


def test_cli_refuses_a_canonical_destination_before_any_source_request(tmp_path, monkeypatch):
    import src.ecb_fx_reference as fx
    project = tmp_path / 'project'
    monkeypatch.setattr(fx, '__file__', str(project/'src/ecb_fx_reference.py'))
    destination = project / 'data' / 'capture'
    assert fx.main(['capture','--reference-date','2026-11-06','--output-dir',str(destination)],
        fetcher=lambda url:pytest.fail('Canonical output reached transport')) == 2
    assert not destination.exists()


def test_minimal_capture_cli_does_not_import_optional_research_or_ui_dependencies(tmp_path):
    project = Path(__file__).resolve().parents[1]
    code = f'''import sys,importlib.abc
sys.path.insert(0,{str(project)!r})
class BlockHeavy(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {{'pandas','numpy','streamlit','lxml'}}:
   raise ModuleNotFoundError('Workflow does not install '+fullname)
sys.meta_path.insert(0,BlockHeavy())
from src.ecb_fx_reference import main
def offline(url): raise OSError('offline')
assert main(['capture','--reference-date','2026-11-06','--output-dir',{str(tmp_path/'minimal')!r}],fetcher=offline)==2
'''
    result = subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path/'minimal/receipt.json').read_text())['status'] == 'withheld'


@pytest.mark.parametrize('status,headers,body,want', [
    (206,{},XML,'withheld'), (200,{'Content-Range':'bytes 0-100/200'},XML,'withheld'),
    (200,{'Content-Length':str(len(XML)+1)},XML,'withheld'),
    (200,{'Content-Length':str(len(XML))},XML,'captured'),
],ids=['partial-status','content-range','length-conflict','complete-response'])
def test_production_transport_checks_response_completeness(monkeypatch,status,headers,body,want):
    import src.ecb_fx_reference as fx
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): return None
        def read(self,limit): return body[:limit]
        def geturl(self): return URL
        def getcode(self): return status
    response=Response();response.headers=headers
    class Opener:
        def open(self,request,timeout): return response
    monkeypatch.setattr(fx.urllib.request,'build_opener',lambda *args:Opener())
    result=fx.capture_ecb_usd('2026-11-06',clock=lambda:NOW)
    assert result['status']==want
