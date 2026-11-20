"""Protected SEC receipt and disposition stores use the server workspace."""

import json
from pathlib import Path

import pytest

from src import sec_research_review as review
from src import sec_review_disposition as disposition
from src import workspace_authorization as authorization
from tests.test_sec_research_review import view


PROFILE = "workspace-alpha"


def _receipt(minute, *, profile=PROFILE):
    return review.capture_review(
        view(), profile_key=profile, saved_at=f"2026-11-02T22:{minute:02d}:00Z"
    )


def _activate(monkeypatch, tmp_path, storage_root, *, role="editor", active=True):
    config = {
        "schema_version": "research-workspace-access-v1",
        "issuer": "https://identity.example",
        "audience": "stock-research",
        "storage_root": str(storage_root),
        "workspaces": {
            "alpha": {
                "profile_key": PROFILE,
                "members": [
                    {"subject": "alice", "role": role, "active": active},
                ],
            },
        },
    }
    path = tmp_path / "workspace-access.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    path.chmod(0o600)
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_CONFIG", str(path))
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_ID", "alpha")
    monkeypatch.setenv("STOCK_RESEARCH_ACCESS_MODE", "workspace")
    monkeypatch.setenv("STOCK_RESEARCH_WORKSPACE_AUDIT_DB", str(tmp_path / "audit" / "decisions.sqlite"))
    monkeypatch.setattr(authorization, "trusted_user_claims", lambda: {
        "is_logged_in": True,
        "iss": "https://identity.example",
        "sub": "alice",
        "aud": "stock-research",
        "exp": 4102444800,
    })
    return path, config


def _seed(root):
    root.mkdir(parents=True)
    packets = [_receipt(1), _receipt(2)]
    for packet in packets:
        review.save_review(packet, root)
    return packets


def test_sec_receipts_and_dispositions_read_only_from_trusted_workspace_root(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    attacker = tmp_path / "attacker"
    before, after = _seed(trusted)
    attacker.mkdir()
    _activate(monkeypatch, tmp_path, trusted, role="viewer")

    assert review.list_reviews(attacker, PROFILE) == [before, after]
    queue = review.review_queue(attacker, PROFILE)
    assert queue["companies"] == 1 and queue["items"][0]["ticker"] == "NEM"
    assert disposition.load_disposition(attacker, PROFILE, before["receipt_id"], after["receipt_id"]) is None
    with pytest.raises(authorization.WorkspaceAccessDenied):
        review.save_review(_receipt(3), attacker)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        disposition.save_disposition(attacker, PROFILE, before["receipt_id"], after["receipt_id"],
                                     "reviewed", "Checked.")
    assert not (attacker / "outputs").exists()


def test_sec_editor_writes_trusted_root_then_revocation_blocks_every_entry(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    attacker = tmp_path / "attacker"
    before, after = _seed(trusted)
    attacker.mkdir()
    config_path, config = _activate(monkeypatch, tmp_path, trusted)

    path = review.save_review(_receipt(3), attacker)
    assert path.is_relative_to(trusted)
    decision = disposition.save_disposition(
        attacker, PROFILE, before["receipt_id"], after["receipt_id"], "still_open", "Recheck filing."
    )
    assert disposition.load_disposition(attacker, PROFILE, before["receipt_id"], after["receipt_id"]) == decision
    assert not (attacker / "outputs").exists()

    config["workspaces"]["alpha"]["members"][0]["active"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")
    for operation in (
        lambda: review.list_reviews(attacker, PROFILE),
        lambda: review.review_queue(attacker, PROFILE),
        lambda: review.save_review(_receipt(4), attacker),
        lambda: disposition.load_disposition(attacker, PROFILE, before["receipt_id"], after["receipt_id"]),
        lambda: disposition.save_disposition(attacker, PROFILE, before["receipt_id"], after["receipt_id"],
                                             "reviewed", "Checked."),
    ):
        with pytest.raises(authorization.WorkspaceAccessDenied):
            operation()


def test_sec_storage_rejects_foreign_profile_before_filesystem_use(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    attacker = tmp_path / "attacker"
    _activate(monkeypatch, tmp_path, trusted)

    for operation in (
        lambda: review.list_reviews(attacker, "workspace-beta"),
        lambda: review.review_queue(attacker, "workspace-beta"),
        lambda: review.save_review(_receipt(1, profile="workspace-beta"), attacker),
        lambda: disposition.load_disposition(attacker, "workspace-beta", "a" * 64, "b" * 64),
        lambda: disposition.save_disposition(attacker, "workspace-beta", "a" * 64, "b" * 64,
                                             "reviewed", "Checked."),
    ):
        with pytest.raises(authorization.WorkspaceAccessDenied):
            operation()
    assert not attacker.exists()


def test_disposition_rechecks_update_after_lock_wait(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    before, after = _seed(trusted)
    config_path, config = _activate(monkeypatch, tmp_path, trusted)
    original_lock = disposition.fcntl.flock

    def downgrade_at_lock(descriptor, operation):
        config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return original_lock(descriptor, operation)

    monkeypatch.setattr(disposition.fcntl, "flock", downgrade_at_lock)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        disposition.save_disposition(trusted, PROFILE, before["receipt_id"], after["receipt_id"],
                                     "reviewed", "Checked.")
    assert disposition.load_disposition(trusted, PROFILE, before["receipt_id"], after["receipt_id"]) is None


def test_receipt_save_rechecks_append_after_history_scan(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    config_path, config = _activate(monkeypatch, tmp_path, trusted)
    original_names = review._company_names

    def downgrade_after_index(root, profile_key):
        names = original_names(root, profile_key)
        config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return names

    monkeypatch.setattr(review, "_company_names", downgrade_after_index)
    packet = _receipt(1)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        review.save_review(packet, trusted)
    assert not list((trusted / "outputs/local/sec-research-reviews").rglob(packet["receipt_id"] + ".json"))


def test_disposition_rechecks_update_after_saved_read(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    before, after = _seed(trusted)
    config_path, config = _activate(monkeypatch, tmp_path, trusted)
    original_read = disposition._read

    def downgrade_after_read(directory, scope):
        result = original_read(directory, scope)
        config["workspaces"]["alpha"]["members"][0]["role"] = "viewer"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return result

    monkeypatch.setattr(disposition, "_read", downgrade_after_read)
    with pytest.raises(authorization.WorkspaceAccessDenied):
        disposition.save_disposition(trusted, PROFILE, before["receipt_id"], after["receipt_id"],
                                     "reviewed", "Checked.")
    assert not list((trusted / "outputs/local/sec-review-dispositions").rglob("*.json"))
