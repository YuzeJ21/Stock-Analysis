import fcntl
import threading
from pathlib import Path

import pytest

from src import research_ledger_lock


def _second_thread_completes(path: Path) -> bool:
    completed = threading.Event()

    def acquire_then_release() -> None:
        with research_ledger_lock.ledger_write_lock(path):
            completed.set()

    worker = threading.Thread(target=acquire_then_release, daemon=True)
    worker.start()
    worker.join(timeout=1)
    return completed.is_set() and not worker.is_alive()


def test_unlock_failure_releases_the_thread_lock_and_leaves_valid_state(tmp_path, monkeypatch):
    destination = tmp_path / "journal.csv"
    original_flock = research_ledger_lock.fcntl.flock
    failed = False

    def fail_first_unlock(fd, operation):
        nonlocal failed
        if operation == fcntl.LOCK_UN and not failed:
            failed = True
            raise OSError("unlock unavailable")
        return original_flock(fd, operation)

    monkeypatch.setattr(research_ledger_lock.fcntl, "flock", fail_first_unlock)

    with pytest.raises(OSError, match="unlock unavailable"):
        with research_ledger_lock.ledger_write_lock(destination):
            pass

    state = research_ledger_lock._states[str(research_ledger_lock.resolve_ledger_path(destination))]
    assert state.depth == 0
    assert state.handle is None
    assert _second_thread_completes(destination)


def test_close_failure_is_retried_before_a_second_thread_acquires(tmp_path, monkeypatch):
    destination = tmp_path / "journal.csv"
    lock_path = tmp_path / "lock-artifact"
    original_open = Path.open
    handles = []

    class FailOnceClose:
        def __init__(self, handle):
            self.handle = handle
            self.close_attempts = 0

        def fileno(self):
            return self.handle.fileno()

        def close(self):
            self.close_attempts += 1
            if self.close_attempts == 1:
                raise OSError("close unavailable")
            return self.handle.close()

    def open_lock(path, *args, **kwargs):
        handle = original_open(path, *args, **kwargs)
        if Path(path) == lock_path and not handles:
            wrapped = FailOnceClose(handle)
            handles.append(wrapped)
            return wrapped
        return handle

    monkeypatch.setattr(research_ledger_lock, "_lock_artifact", lambda _path: lock_path)
    monkeypatch.setattr(Path, "open", open_lock)

    with pytest.raises(OSError, match="close unavailable"):
        with research_ledger_lock.ledger_write_lock(destination):
            pass

    state = research_ledger_lock._states[str(research_ledger_lock.resolve_ledger_path(destination))]
    assert state.depth == 0
    assert state.handle is handles[0]
    assert _second_thread_completes(destination)
    assert handles[0].close_attempts == 2
    assert state.depth == 0
    assert state.handle is None
