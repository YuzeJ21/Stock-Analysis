"""Durable, privacy-limited authorization audit for protected workspaces."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

import pytest

from src.hosted_access_control import WorkspaceAction, WorkspaceResource
from src import workspace_audit as audit
from src import workspace_authorization as access


def _sink(tmp_path, monkeypatch):
    path = tmp_path / "private-audit" / "decisions.sqlite"
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_AUDIT_DB", str(path))
    return path


def _append(*, request_id=None, principal_id="a" * 64, workspace_id="alpha",
            resource=WorkspaceResource.RESEARCH_RECORD, action=WorkspaceAction.READ,
            outcome="allowed", reason_code="allowed"):
    return audit.append_workspace_audit(
        request_id=request_id or uuid4().hex, principal_id=principal_id,
        workspace_id=workspace_id, resource=resource, action=action,
        outcome=outcome, reason_code=reason_code,
    )


def _read(path):
    return audit.read_workspace_audit(path, limit=1000)


def test_audit_roundtrip_is_durable_ordered_and_privacy_limited(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    first_id, second_id = uuid4().hex, uuid4().hex
    first = _append(request_id=first_id)
    second = _append(request_id=second_id, principal_id=None,
                     action="append", outcome="denied", reason_code="authentication_required")
    assert isinstance(first, int) and second == first + 1
    rows = _read(path)
    assert [row["sequence"] for row in rows] == [first, second]
    assert [row["request_id"] for row in rows] == [first_id, second_id]
    assert [row["outcome"] for row in rows] == ["allowed", "denied"]
    assert rows[0]["schema_version"] == audit.SCHEMA_VERSION == "research-workspace-audit-v1"
    assert rows[0]["event_type"] == "workspace_access_decision"
    assert rows[0]["principal_id"] == "a" * 64 and rows[1]["principal_id"] is None
    assert rows[0]["workspace_id"] != "alpha" and len(rows[0]["workspace_id"]) == 64
    assert set(rows[0]) == {"schema_version", "event_type", "request_id", "principal_id",
                            "workspace_id", "resource", "action", "outcome", "reason_code",
                            "occurred_at", "sequence"}
    for row in rows:
        datetime.fromisoformat(row["occurred_at"].replace("Z", "+00:00"))
    assert b"alpha" not in path.read_bytes()
    assert path.stat().st_mode & 0o077 == 0
    assert path.parent.stat().st_mode & 0o077 == 0


def test_concurrent_processes_commit_distinct_complete_events(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    code = (
        "from uuid import uuid4\n"
        "from src.workspace_audit import append_workspace_audit\n"
        "for _ in range(4):\n"
        " append_workspace_audit(request_id=uuid4().hex, principal_id=None, workspace_id='alpha', "
        "resource='research_record', action='read', outcome='denied', reason_code='authentication_required')\n"
    )
    environment = dict(os.environ)

    def worker(_):
        subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parent.parent,
                       env=environment, check=True, capture_output=True, text=True, timeout=30)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(worker, range(4)))
    rows = _read(path)
    assert len(rows) == 16
    assert len({row["request_id"] for row in rows}) == 16
    assert [row["sequence"] for row in rows] == list(range(rows[0]["sequence"], rows[0]["sequence"] + 16))


def test_sink_rejects_symlink_writable_file_and_writable_parent(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    _append()
    linked = path.parent / "linked.sqlite"
    linked.symlink_to(path)
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_AUDIT_DB", str(linked))
    with pytest.raises(audit.AuditUnavailable):
        _append()
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_AUDIT_DB", str(path))
    path.chmod(0o666)
    with pytest.raises(audit.AuditUnavailable):
        _append()
    path.chmod(0o600)
    path.parent.chmod(0o777)
    with pytest.raises(audit.AuditUnavailable):
        _append()


def test_corrupt_or_missing_sink_fails_closed_without_partial_read(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    _append()
    path.write_bytes(b"not a SQLite database")
    with pytest.raises(audit.AuditUnavailable):
        _read(path)
    with pytest.raises(audit.AuditUnavailable):
        _append()
    monkeypatch.delenv("STOCK_RESEARCH_WORKSPACE_AUDIT_DB")
    with pytest.raises(audit.AuditUnavailable):
        _append()


def test_busy_sink_fails_closed_without_losing_prior_event(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    _append()
    monkeypatch.setattr(audit, "_TIMEOUT", 0.03)
    lock = path.with_name("." + path.name + ".lock")
    with lock.open("r+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        with pytest.raises(audit.AuditUnavailable):
            _append()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    assert len(_read(path)) == 1


def test_corrupt_schema_and_append_only_triggers_fail_closed(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    _append()
    with sqlite3.connect(path) as connection:
        for statement in ("UPDATE workspace_audit SET reason_code='role_action_denied'",
                          "DELETE FROM workspace_audit"):
            with pytest.raises(sqlite3.DatabaseError):
                connection.execute(statement)
    assert len(_read(path)) == 1
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER workspace_audit_no_delete")
    with pytest.raises(audit.AuditUnavailable):
        _read(path)
    with pytest.raises(audit.AuditUnavailable):
        _append()


def test_bounded_reader_returns_recent_events_without_silent_truncation(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    ids = [uuid4().hex for _ in range(4)]
    for request_id in ids:
        _append(request_id=request_id)
    assert [row["request_id"] for row in audit.read_workspace_audit(path, limit=2)] == ids[-2:]
    with pytest.raises(audit.AuditUnavailable):
        audit.read_workspace_audit(path, limit=0)


@pytest.mark.parametrize("change", [
    {"request_id": "private raw request"},
    {"principal_id": "alice@example.invalid"},
    {"workspace_id": "alpha\nprivate note"},
    {"reason_code": "private thesis text", "outcome": "denied"},
])
def test_event_rejects_raw_or_unlisted_metadata(tmp_path, monkeypatch, change):
    path = _sink(tmp_path, monkeypatch)
    _append()
    with pytest.raises(audit.AuditUnavailable, match="Workspace audit unavailable"):
        _append(**change)
    assert len(_read(path)) == 1


@pytest.fixture
def protected_access(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    config_path = tmp_path / "membership.json"
    config = {
        "schema_version": "research-workspace-access-v1", "issuer": "https://identity.example",
        "audience": "stock-research", "storage_root": str(tmp_path / "private-store"),
        "workspaces": {"alpha": {"profile_key": "workspace-alpha", "members": [
            {"subject": "alice", "role": "editor", "active": True},
        ]}},
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    config_path.chmod(0o600)
    monkeypatch.setenv(access.CONFIG_ENV, str(config_path))
    monkeypatch.setenv(access.WORKSPACE_ENV, "alpha")
    monkeypatch.setenv(access.MODE_ENV, "workspace")
    claims = {"is_logged_in": True, "iss": config["issuer"], "aud": config["audience"],
              "sub": "alice", "email": "private-alice@example.invalid", "exp": time.time() + 3600}
    monkeypatch.setattr(access, "trusted_user_claims", lambda: dict(claims))
    return path, config_path, config, claims


def test_authorization_records_allow_role_denial_and_missing_config(protected_access):
    path, config_path, config, _ = protected_access
    assert access.require_workspace_access("workspace-alpha").profile_key == "workspace-alpha"
    config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(access.WorkspaceAccessDenied):
        access.require_workspace_access("workspace-alpha", WorkspaceAction.APPEND)
    config_path.unlink()
    with pytest.raises(access.WorkspaceAccessDenied):
        access.require_workspace_access("workspace-alpha")
    rows = _read(path)
    assert [(row["outcome"], row["reason_code"]) for row in rows] == [
        ("allowed", "allowed"), ("denied", "role_action_denied"),
        ("denied", "workspace_configuration_unavailable"),
    ]
    assert rows[-1]["principal_id"] is None
    raw = path.read_bytes()
    for secret in (b"alice", b"identity.example", b"private-alice", b"workspace-alpha"):
        assert secret not in raw


def test_authentication_and_record_scope_denials_are_audited(protected_access, tmp_path):
    path, _, _, claims = protected_access
    claims["is_logged_in"] = False
    with pytest.raises(access.WorkspaceAccessDenied):
        access.require_workspace_access("workspace-alpha")
    claims["is_logged_in"] = True
    with pytest.raises(access.WorkspaceAccessDenied):
        access.require_record_destination(tmp_path / "outside" / "research_thesis_journal.csv",
                                          "workspace-alpha", "FICT")
    rows = _read(path)
    assert [row["reason_code"] for row in rows if row["outcome"] == "denied"] == [
        "authentication_required", "record_destination_mismatch",
    ]
    assert rows[0]["principal_id"] is None
    assert b"private-alice" not in path.read_bytes() and b"FICT" not in path.read_bytes()


def test_workspace_and_route_denials_have_no_client_route_content(protected_access):
    path, _, _, _ = protected_access
    with pytest.raises(access.WorkspaceAccessDenied):
        access.require_workspace_access("workspace-beta")
    session = access.require_workspace_access("workspace-alpha")
    with pytest.raises(access.WorkspaceAccessDenied):
        access.deny_workspace_access("workspace_route_unavailable", session=session)
    denied = [row for row in _read(path) if row["outcome"] == "denied"]
    assert [row["reason_code"] for row in denied] == ["workspace_mismatch", "workspace_route_unavailable"]
    assert b"workspace-beta" not in path.read_bytes()


def test_unavailable_audit_blocks_authorized_reads_and_writes(protected_access, monkeypatch):
    path, _, _, _ = protected_access
    access.require_workspace_access("workspace-alpha")
    path.chmod(0o666)
    for action in (WorkspaceAction.READ, WorkspaceAction.APPEND):
        with pytest.raises(access.WorkspaceAccessDenied) as denied:
            access.require_workspace_access("workspace-alpha", action)
        assert denied.value.reason == "audit_unavailable"
    with pytest.raises(audit.AuditUnavailable):
        _read(path)


def test_personal_mode_does_not_open_audit_sink(tmp_path, monkeypatch):
    path = _sink(tmp_path, monkeypatch)
    for key in (access.CONFIG_ENV, access.WORKSPACE_ENV, access.MODE_ENV):
        monkeypatch.delenv(key, raising=False)
    assert access.require_workspace_access("personal") is None
    assert not path.exists() and not path.parent.exists()
