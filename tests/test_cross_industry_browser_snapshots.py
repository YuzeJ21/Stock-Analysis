"""Readers must see a complete previous or new test-app observation."""
import io
import json

import pytest

from tests.cross_industry_browser_fixture import _publish_json_snapshot


@pytest.mark.parametrize('existing', [True, False], ids=['replace', 'first-publication'])
def test_browser_observation_is_complete_at_the_write_boundary(tmp_path, monkeypatch, existing):
    path = tmp_path / 'study-view.json'
    old = {'source_request_count': 12, 'rows': ['previous']}
    new = {'source_request_count': 13, 'rows': ['new']}
    if existing:
        path.write_text(json.dumps(old), encoding='utf-8')
    actual_open = io.open
    observed = []

    def read_during_write(file, mode='r', *args, **kwargs):
        handle = actual_open(file, mode, *args, **kwargs)
        if 'w' in mode:
            try:
                observed.append(json.loads(path.read_text()) if path.exists() else None)
            except BaseException:
                handle.close()
                raise
        return handle

    monkeypatch.setattr(io, 'open', read_during_write)
    _publish_json_snapshot(path, new)
    assert observed == [old if existing else None]
    assert json.loads(path.read_text()) == new
    assert sorted(p.name for p in tmp_path.iterdir()) == ['study-view.json']


def test_failed_observation_encoding_preserves_previous_bytes(tmp_path):
    path = tmp_path / 'study-view.json'
    old = b'{"source_request_count":12}\n'
    path.write_bytes(old)
    with pytest.raises(TypeError):
        _publish_json_snapshot(path, {'source_request_count': object()})
    assert path.read_bytes() == old
    assert sorted(p.name for p in tmp_path.iterdir()) == ['study-view.json']
