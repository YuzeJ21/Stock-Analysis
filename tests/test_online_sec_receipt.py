from datetime import datetime, timezone

import pytest

OBSERVED = datetime(2026, 10, 30, 18, tzinfo=timezone.utc)
URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json'


def test_receipt_keeps_exact_raw_digest_source_and_dates_without_disk_writes(tmp_path, monkeypatch):
    from src.online_sec_receipt import fetch_sec_json_receipt
    monkeypatch.chdir(tmp_path)
    result = fetch_sec_json_receipt(URL, user_agent='Research contact@example.invalid', observed_at=OBSERVED,
        fetcher=lambda url, agent: (b'{"cik":1234}', {'Last-Modified':'Thu, 29 Oct 2026 18:00:00 GMT'}, url))
    assert result['status'] == 'ready'
    assert result['payload'] == {'cik':1234}
    assert result['source_url'] == URL
    assert result['observed_at'] == '2026-10-30T18:00:00Z'
    assert result['source_last_modified'] == '2026-10-29T18:00:00Z'
    assert len(result['payload_sha256']) == 64
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('raw,final_url', [
    (b'{"cik":1,"cik":1234}', URL), (b'{"cik":NaN}', URL),
    (b'[]', URL), (b'{}', 'https://example.invalid/')])
def test_invalid_or_redirected_source_is_withheld(raw, final_url):
    from src.online_sec_receipt import fetch_sec_json_receipt
    result=fetch_sec_json_receipt(URL,user_agent='Research contact',observed_at=OBSERVED,
        fetcher=lambda *_:(raw,{},final_url))
    assert result['status']=='unavailable'
    assert 'payload' not in result


def test_unapproved_url_missing_agent_and_response_size_fail_before_use(monkeypatch):
    from src import online_sec_receipt as source
    def no_fetch(*_): pytest.fail('unexpected network request')
    for url,agent in [('https://example.invalid/private','Research'),(URL,''),(URL,'x\r\nY:z')]:
        assert source.fetch_sec_json_receipt(url,user_agent=agent,fetcher=no_fetch)['status']=='unavailable'
    monkeypatch.setattr(source,'MAX_SEC_RESPONSE_BYTES',128)
    result=source.fetch_sec_json_receipt(URL,user_agent='Research',fetcher=lambda *a:(b'x'*129,{},URL))
    assert result['status']=='unavailable'


def test_receipt_digest_changes_with_the_exact_response_bytes():
    from src.online_sec_receipt import fetch_sec_json_receipt
    a=fetch_sec_json_receipt(URL,user_agent='Research',fetcher=lambda *a:(b'{"cik":1234}',{},URL))
    b=fetch_sec_json_receipt(URL,user_agent='Research',fetcher=lambda *a:(b'{ "cik":1234}',{},URL))
    assert a['payload']==b['payload'] and a['payload_sha256']!=b['payload_sha256']
