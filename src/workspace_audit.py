"""Local, application-append-only authorization events, separate from research.

This is a server-side sink, not a product log-reading endpoint. Its local owner
can replace the file; hosted retention, backup and tamper resistance are separate
controls. No claims, tokens, research content or caller-supplied metadata belong
in an event.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import fcntl
import os
from pathlib import Path
import re
import sqlite3
import stat
import time

from src.hosted_access_control import WorkspaceAction, WorkspaceResource

AUDIT_DB_ENV = 'STOCK_RESEARCH_WORKSPACE_AUDIT_DB'
SCHEMA_VERSION = 'research-workspace-audit-v1'
_TIMEOUT = 1.0
_REASONS = frozenset({
    'allowed', 'invalid_request', 'authentication_required', 'principal_mismatch',
    'membership_inactive', 'workspace_mismatch', 'append_only_mutation_denied',
    'role_action_denied', 'workspace_configuration_unavailable',
    'workspace_route_unavailable', 'record_destination_mismatch',
})
_FIELDS = ('sequence', 'schema_version', 'event_type', 'request_id', 'principal_id',
           'workspace_id', 'resource', 'action', 'outcome', 'reason_code', 'occurred_at')
_TABLE = """CREATE TABLE workspace_audit (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version TEXT NOT NULL CHECK (schema_version = 'research-workspace-audit-v1'),
    event_type TEXT NOT NULL CHECK (event_type = 'workspace_access_decision'),
    request_id TEXT NOT NULL UNIQUE,
    principal_id TEXT,
    workspace_id TEXT,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('allowed', 'denied')),
    reason_code TEXT NOT NULL,
    occurred_at TEXT NOT NULL
)"""
_TRIGGERS = {
    'workspace_audit_no_update': """CREATE TRIGGER workspace_audit_no_update
BEFORE UPDATE ON workspace_audit BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END""",
    'workspace_audit_no_delete': """CREATE TRIGGER workspace_audit_no_delete
BEFORE DELETE ON workspace_audit BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END""",
}


class AuditUnavailable(ValueError):
    def __init__(self):
        super().__init__('Workspace audit unavailable.')


def _digest(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _timestamp(value):
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
    if type(value) is not str or len(value) > 40:
        raise ValueError('Invalid audit timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('UTC audit timestamp required')
    return parsed.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _event(*, request_id, principal_id, workspace_id, resource, action, outcome,
           reason_code, occurred_at):
    if (type(request_id) is not str or re.fullmatch(r'[0-9a-f]{32}', request_id) is None
            or (principal_id is not None and not _digest(principal_id))
            or (workspace_id is not None and (type(workspace_id) is not str
                or not 1 <= len(workspace_id) <= 128 or workspace_id.strip() != workspace_id
                or not workspace_id.isprintable()))
            or resource not in {*WorkspaceResource, 'invalid'}
            or action not in {*WorkspaceAction, 'invalid'}
            or outcome not in {'allowed', 'denied'} or reason_code not in _REASONS
            or (outcome == 'allowed') != (reason_code == 'allowed')):
        raise ValueError('Invalid audit event')
    return (SCHEMA_VERSION, 'workspace_access_decision', request_id, principal_id,
            sha256(workspace_id.encode()).hexdigest() if workspace_id is not None else None,
            str(getattr(resource, 'value', resource)), str(getattr(action, 'value', action)),
            outcome, reason_code, _timestamp(occurred_at))


def _private_path(path, *, create):
    path = Path(path)
    if (not path.is_absolute() or path != path.resolve()
            or any(part.is_symlink() for part in (path, *path.parents))):
        raise ValueError('Canonical audit path required')
    if create:
        path.parent.mkdir(mode=0o700, exist_ok=True)
    parent = path.parent.stat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
            or stat.S_IMODE(parent.st_mode) != 0o700):
        raise ValueError('Private audit directory required')
    return path


def _file_info(descriptor):
    info = os.fstat(descriptor)
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise ValueError('Private audit file required')
    return info


def _same_file(path, descriptor):
    info, current = _file_info(descriptor), path.stat(follow_symlinks=False)
    if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
        raise ValueError('Audit file replaced')


@contextmanager
def _database(path, *, create):
    """Serialize initialization without locking SQLite's database inode."""
    descriptor = None
    lock_descriptor = None
    connection = None
    try:
        path = _private_path(path, create=create)
        lock_path = path.with_name('.' + path.name + '.lock')
        lock_descriptor = os.open(lock_path,
            ((os.O_RDWR | os.O_CREAT) if create else os.O_RDONLY) | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        _file_info(lock_descriptor)
        deadline = time.monotonic() + _TIMEOUT
        while True:
            try:
                fcntl.flock(lock_descriptor, (fcntl.LOCK_EX if create else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError('Audit busy') from None
                time.sleep(0.01)
        _same_file(lock_path, lock_descriptor)
        fresh = False
        if create:
            try:
                descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                fresh = True
            except FileExistsError:
                pass
        if descriptor is None:
            descriptor = os.open(path, (os.O_RDWR if create else os.O_RDONLY) | os.O_NOFOLLOW | os.O_NONBLOCK)
        _same_file(path, descriptor)
        if not fresh and os.fstat(descriptor).st_size == 0:
            raise ValueError('Empty existing audit database')
        uri = path.as_uri() + ('?mode=rw' if create else '?mode=ro')
        connection = sqlite3.connect(uri, uri=True, timeout=_TIMEOUT, isolation_level=None)
        connection.execute('PRAGMA trusted_schema=OFF')
        if create:
            # EXTRA also syncs the directory after rollback-journal unlink.
            if connection.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
                raise ValueError('Unsupported audit journal mode')
            connection.execute('PRAGMA synchronous=EXTRA')
            connection.execute('PRAGMA fullfsync=ON')
            if connection.execute('PRAGMA synchronous').fetchone()[0] != 3:
                raise ValueError('Audit synchronization unavailable')
            connection.execute('BEGIN IMMEDIATE')
        if fresh:
            connection.execute(_TABLE)
            for statement in _TRIGGERS.values():
                connection.execute(statement)
            connection.execute('PRAGMA user_version=1')
        _verify_schema(connection)
        yield connection
        _same_file(path, descriptor)
        if create:
            connection.commit()
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except (OSError, ValueError, TypeError, sqlite3.Error, UnicodeError):
        if connection is not None and connection.in_transaction:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
        raise AuditUnavailable() from None
    finally:
        if connection is not None:
            connection.close()
        if descriptor is not None:
            os.close(descriptor)
        if lock_descriptor is not None:
            os.close(lock_descriptor)


def _verify_schema(connection):
    objects = {name: (kind, sql) for kind, name, sql in connection.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
    expected = {'workspace_audit': ('table', _TABLE),
                **{name: ('trigger', sql) for name, sql in _TRIGGERS.items()}}
    if objects != expected or connection.execute('PRAGMA user_version').fetchone()[0] != 1:
        raise ValueError('Unsupported audit schema')


def append_workspace_audit(*, request_id, principal_id, workspace_id, resource, action,
                           outcome, reason_code, occurred_at=None):
    """Commit one authorization decision or raise; never fall back to memory."""
    try:
        event = _event(request_id=request_id, principal_id=principal_id, workspace_id=workspace_id,
            resource=resource, action=action, outcome=outcome, reason_code=reason_code,
            occurred_at=occurred_at)
        path = os.environ[AUDIT_DB_ENV]
        with _database(path, create=True) as connection:
            cursor = connection.execute('INSERT INTO workspace_audit (' + ','.join(_FIELDS[1:])
                + ') VALUES (' + ','.join('?' for _ in event) + ')', event)
            sequence = cursor.lastrowid
        return sequence
    except (KeyError, ValueError, TypeError, UnicodeError):
        raise AuditUnavailable() from None


def read_workspace_audit(path, *, limit=1000):
    """Operator-only bounded inspection; this is not exposed by app routes."""
    if type(limit) is not int or not 1 <= limit <= 10_000:
        raise AuditUnavailable()
    with _database(path, create=False) as connection:
        rows = connection.execute('SELECT ' + ','.join(_FIELDS)
            + ' FROM workspace_audit ORDER BY sequence DESC LIMIT ?', (limit,)).fetchall()
        return [dict(zip(_FIELDS, row)) for row in reversed(rows)]
