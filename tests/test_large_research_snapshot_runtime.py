"""Exercise overlapping reruns against the real compressed snapshot store."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
import socket
import pytest

from tests.test_large_research_snapshot_browser import SCOPE, _large_context, _run_app


class QueryParams(dict):
    def from_dict(self, value):
        self.clear()
        self.update(value)


def test_overlapping_monitor_reruns_keep_the_exact_snapshot_root(tmp_path, monkeypatch):
    import streamlit as st
    from src import online_research_context_store as store, online_research_tools_ui as ui

    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    # Register parent-process cleanup; the browser fixture normally owns a process.
    for module, name in ((store, 'PROJECT_ROOT'), (ui, 'PROJECT_ROOT'),
                         (socket.socket, 'connect'), (socket.socket, 'connect_ex')):
        monkeypatch.setattr(module, name, getattr(module, name))
    value, _ = _large_context()
    saved = store.save_research_context(value, **SCOPE, project_root=tmp_path)
    path = next((tmp_path / 'outputs/local/online-research-contexts').rglob('*.json'))
    before = path.read_bytes()
    older_at_picker, newer_at_picker, older_stopped = Event(), Event(), Event()
    output = {'older': [], 'newer': []}

    class StopOlderRerun(BaseException):
        pass

    def record(message, *args, **kwargs):
        output[current_thread().name].append(str(message))

    def selectbox(label, options, **kwargs):
        if current_thread().name == 'older':
            older_at_picker.set()
            assert newer_at_picker.wait(10)
            raise StopOlderRerun()
        newer_at_picker.set()
        assert older_stopped.wait(10)
        return next(iter(options))

    monkeypatch.setattr(st, 'query_params', QueryParams(page='monitor'))
    monkeypatch.setattr(st, 'set_page_config', lambda **kwargs: None)
    for name in ('markdown', 'caption', 'write', 'warning'):
        monkeypatch.setattr(st, name, record)
    monkeypatch.setattr(st, 'button', lambda *args, **kwargs: False)
    monkeypatch.setattr(st, 'selectbox', selectbox)

    def run(name):
        current_thread().name = name
        try:
            _run_app(tmp_path)
        except StopOlderRerun:
            assert name == 'older'
        finally:
            if name == 'older':
                older_stopped.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        older = pool.submit(run, 'older')
        assert older_at_picker.wait(10)
        newer = pool.submit(run, 'newer')
        older.result(timeout=15)
        newer.result(timeout=15)

    assert not any('could not be verified' in row for row in output['newer']), output['newer']
    assert 'Latest observation: ' + saved['observed_at'] in output['newer']
    assert 'validated current annual revenue required' in output['newer']
    assert store.load_research_context(saved['snapshot_id'], **SCOPE, project_root=tmp_path) == saved
    assert path.read_bytes() == before
    assert not (tmp_path / 'external-request.txt').exists()


def test_browser_process_keeps_external_transport_denied_across_reruns(tmp_path, monkeypatch):
    import streamlit as st
    from src import online_research_context_store as store, online_research_tools_ui as ui
    from tests import test_large_research_snapshot_browser as fixture

    def transport_boundary(*args):
        raise RuntimeError('loopback transport boundary reached')

    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    for module, name in ((store, 'PROJECT_ROOT'), (ui, 'PROJECT_ROOT')):
        monkeypatch.setattr(module, name, getattr(module, name))
    for name in ('connect', 'connect_ex'):
        monkeypatch.setattr(socket.socket, name, transport_boundary)
    monkeypatch.setattr(fixture, '_CONNECT', transport_boundary, raising=False)
    monkeypatch.setattr(fixture, '_CONNECT_EX', transport_boundary, raising=False)
    monkeypatch.setattr(st, 'query_params', QueryParams(page='monitor'))
    monkeypatch.setattr(st, 'set_page_config', lambda **kwargs: None)
    for name in ('markdown', 'caption', 'warning'):
        monkeypatch.setattr(st, name, lambda *args, **kwargs: None)
    for _ in range(19):
        _run_app(tmp_path)
    def stale_rerun_guard(*args):
        raise AssertionError('A new rerun wrapped the previous socket guard')
    for name in ('connect', 'connect_ex'):
        monkeypatch.setattr(socket.socket, name, stale_rerun_guard)
    _run_app(tmp_path)
    for name in ('connect', 'connect_ex'):
        with socket.socket() as sock:
            with pytest.raises(RuntimeError, match='loopback transport boundary reached'):
                getattr(sock, name)(('127.0.0.1', 12345))
            with pytest.raises(AssertionError, match='attempted external transport'):
                getattr(sock, name)(('192.0.2.1', 443))
    assert '192.0.2.1' in (tmp_path / 'external-request.txt').read_text()
