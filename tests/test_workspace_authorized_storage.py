"""Protected saved research rejects stale membership and caller-chosen roots."""

import json
import time

import pytest

from src import online_research_context_store as snapshots
from src.company_research_notes import CompanyNotesScope, load_company_notes, notes_index, notes_paths
from src.research_record_authoring import (
    AuthoringPaths, build_authoring_draft, confirm_authoring_preview, preview_authoring_record,
)
from src.research_thesis_journal import append_journal_entry
from tests.test_company_research_notes import entry
from tests.test_online_research_context_store import context


@pytest.fixture
def protected_store(tmp_path, monkeypatch):
    from src import workspace_authorization as access

    storage = tmp_path / "trusted-storage"
    storage.mkdir(mode=0o700)
    config_path = tmp_path / "workspace-access.json"
    config = {
        "schema_version": "research-workspace-access-v1",
        "issuer": "https://identity.example",
        "audience": "stock-research",
        "storage_root": str(storage),
        "workspaces": {
            "alpha": {"profile_key": "workspace-alpha", "members": [
                {"subject": "alice", "role": "editor", "active": True},
                {"subject": "bob", "role": "viewer", "active": True},
            ]},
            "beta": {"profile_key": "workspace-beta", "members": [
                {"subject": "carol", "role": "editor", "active": True},
            ]},
        },
    }

    def publish():
        pending = config_path.with_suffix(".pending")
        pending.write_text(json.dumps(config), encoding="utf-8")
        pending.chmod(0o600)
        pending.replace(config_path)

    publish()
    claims = {"is_logged_in": True, "iss": "https://identity.example",
              "aud": "stock-research", "sub": "alice", "exp": time.time() + 3600}
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_CONFIG", str(config_path))
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_ID", "alpha")
    monkeypatch.setenv("STOCK_RESEARCH_ACCESS_MODE", "workspace")
    monkeypatch.setattr(access, "trusted_user_claims", lambda: dict(claims))
    return storage, config, claims, publish, access


def test_snapshot_reads_and_writes_use_server_root_and_live_membership(protected_store, tmp_path):
    storage, config, claims, publish, access = protected_store
    untrusted_root = tmp_path / "caller-root"
    scope = dict(profile_key="workspace-alpha", ticker="FICT", sec_cik="0000001234")
    saved = snapshots.save_research_context(context(**scope), **scope, project_root=untrusted_root)
    stored = list((storage / "outputs/local/online-research-contexts").rglob(saved["snapshot_id"] + ".json"))
    assert len(stored) == 1
    assert not untrusted_root.exists()
    original_bytes = stored[0].read_bytes()

    claims["sub"] = "bob"
    assert snapshots.load_research_context(saved["snapshot_id"], **scope, project_root=untrusted_root) == saved
    with pytest.raises(access.WorkspaceAccessDenied):
        snapshots.save_research_context(context(**scope, notes={"thesis": "second"}),
                                        **scope, project_root=untrusted_root)
    assert stored[0].read_bytes() == original_bytes

    config["workspaces"]["alpha"]["members"][1]["active"] = False
    publish()
    with pytest.raises(access.WorkspaceAccessDenied):
        snapshots.load_research_context(saved["snapshot_id"], **scope, project_root=untrusted_root)
    with pytest.raises(access.WorkspaceAccessDenied):
        snapshots.list_research_context_scopes("workspace-alpha", project_root=untrusted_root)
    claims["sub"] = "alice"
    with pytest.raises(access.WorkspaceAccessDenied):
        snapshots.list_research_contexts(profile_key="workspace-beta", ticker="FICT",
                                         sec_cik="0000001234", project_root=untrusted_root)


def test_notes_read_and_index_follow_trusted_root_then_revoke(protected_store, tmp_path):
    storage, config, claims, publish, access = protected_store
    untrusted_root = tmp_path / "caller-root"
    scope = CompanyNotesScope("workspace-alpha", "FICT", "0000001234")
    paths = notes_paths(scope, project_root=untrusted_root)
    assert paths.journal.is_relative_to(storage / "outputs/local/company-research-notes")
    append_journal_entry(paths.journal, entry(profile="workspace-alpha"))
    assert load_company_notes(scope, project_root=untrusted_root).record_count == 1
    assert notes_index(scope.profile_key, project_root=untrusted_root).scopes == (scope,)
    assert not untrusted_root.exists()

    config["workspaces"]["alpha"]["members"][0]["active"] = False
    publish()
    with pytest.raises(access.WorkspaceAccessDenied):
        load_company_notes(scope, project_root=untrusted_root)
    with pytest.raises(access.WorkspaceAccessDenied):
        notes_index(scope.profile_key, project_root=untrusted_root)


def test_authoring_rechecks_membership_and_rejects_forged_destination(protected_store, tmp_path):
    storage, config, claims, publish, access = protected_store
    scope = CompanyNotesScope("workspace-alpha", "FICT", "0000001234")
    paths = notes_paths(scope, project_root=tmp_path / "caller-root")
    draft = build_authoring_draft("thesis", profile_key=scope.profile_key, ticker=scope.ticker,
        fields={"thesis_id": "synthetic-thesis", "summary": "Review source period.",
                "effective_at": "2026-11-20T10:00:00Z", "reviewer": "fixture"})
    options = dict(previewed_at="2026-11-20T12:00:00Z", generated_id="entry-one")
    valid = preview_authoring_record(draft, paths=paths, **options)
    assert valid.state == "reviewable"

    outside = tmp_path / "outside"
    forged = AuthoringPaths(outside / "research_thesis_journal.csv",
                           outside / "catalyst_evidence.csv", outside / "research_outcome_reviews.csv")
    denied = preview_authoring_record(draft, paths=forged, **options)
    assert denied.state == "rejected" and not denied.receipt and not outside.exists()

    config["workspaces"]["alpha"]["members"][0]["active"] = False
    publish()
    with pytest.raises(access.WorkspaceAccessDenied):
        confirm_authoring_preview(valid, current_draft=draft, paths=paths,
            active_profile_key=scope.profile_key, active_ticker=scope.ticker,
            active_kind="thesis", confirm_reviewed=True)
    assert not paths.journal.exists()


def test_snapshot_save_rechecks_append_after_lock_wait(protected_store, tmp_path, monkeypatch):
    import fcntl

    storage, config, _, publish, access = protected_store
    scope = dict(profile_key="workspace-alpha", ticker="FICT", sec_cik="0000001234")
    original_lock = fcntl.flock

    def downgrade_at_lock(descriptor, operation):
        config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
        publish()
        return original_lock(descriptor, operation)

    monkeypatch.setattr(fcntl, "flock", downgrade_at_lock)
    with pytest.raises(access.WorkspaceAccessDenied):
        snapshots.save_research_context(context(**scope), **scope, project_root=tmp_path / "caller-root")
    assert not list((storage / "outputs/local/online-research-contexts").rglob("*.json"))


def test_snapshot_save_rechecks_append_after_history_scan(protected_store, tmp_path, monkeypatch):
    storage, config, _, publish, access = protected_store
    scope = dict(profile_key="workspace-alpha", ticker="FICT", sec_cik="0000001234")
    original_list = snapshots.list_research_contexts

    def downgrade_after_scan(**kwargs):
        result = original_list(**kwargs)
        config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
        publish()
        return result

    monkeypatch.setattr(snapshots, "list_research_contexts", downgrade_after_scan)
    with pytest.raises(access.WorkspaceAccessDenied):
        snapshots.save_research_context(context(**scope), **scope, project_root=tmp_path / "caller-root")
    assert not list((storage / "outputs/local/online-research-contexts").rglob("*.json"))
