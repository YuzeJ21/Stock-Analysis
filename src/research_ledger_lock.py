"""Cooperative, reentrant write locks for append-only research ledgers."""

from __future__ import annotations

import fcntl
import hashlib
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class _LockState:
    thread_lock: threading.RLock
    depth: int = 0
    handle: object | None = None


_registry_guard = threading.Lock()
_states: dict[str, _LockState] = {}


def resolve_ledger_path(path: Path | str) -> Path:
    """Return the stable filesystem identity used by receipts and locks."""

    return Path(path).resolve(strict=False)


def _lock_artifact(identity: Path) -> Path:
    digest = hashlib.sha256(str(identity).encode("utf-8")).hexdigest()
    return Path(tempfile.gettempdir()) / "research-ledger-locks-v1" / f"{digest}.lock"


def _release_handle(state: _LockState) -> None:
    """Release a prior lock handle, retaining it when close must be retried."""

    handle = state.handle
    if handle is None:
        return
    unlock_error: OSError | None = None
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        unlock_error = exc
    try:
        handle.close()
    except OSError as close_error:
        if unlock_error is not None:
            raise unlock_error from close_error
        raise
    state.handle = None
    if unlock_error is not None:
        raise unlock_error


@contextmanager
def ledger_write_lock(path: Path | str) -> Iterator[Path]:
    """Hold the shared lock for one resolved ledger across threads and processes.

    The `RLock` makes nested calls from one thread safe; `flock` coordinates
    cooperating processes. Lock artifacts live under the system temp directory,
    never beside source or ledger files.
    """

    identity = resolve_ledger_path(path)
    key = str(identity)
    with _registry_guard:
        state = _states.setdefault(key, _LockState(threading.RLock()))
    state.thread_lock.acquire()
    entered = False
    try:
        if state.depth == 0:
            _release_handle(state)
            artifact = _lock_artifact(identity)
            artifact.parent.mkdir(parents=True, exist_ok=True)
            handle = artifact.open("a+b")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except BaseException as exc:
                try:
                    handle.close()
                except OSError as close_error:
                    state.handle = handle
                    raise close_error from exc
                raise
            state.handle = handle
        state.depth += 1
        entered = True
        yield identity
    finally:
        try:
            if entered:
                state.depth -= 1
                if state.depth == 0:
                    _release_handle(state)
        finally:
            state.thread_lock.release()
