from pathlib import Path
import json

import pytest

from tests.point_in_time_universe_fixture import build_valid_package


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_loads_hash_bound_manifest_without_writing(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    before = _file_bytes(tmp_path)
    loaded = load_universe_package(manifest, registry)
    assert loaded.manifest.schema_version == "point_in_time_universe_v1"
    assert set(loaded.files) == {"security_identity", "membership", "events", "evaluations"}
    assert _file_bytes(tmp_path) == before


@pytest.mark.parametrize("mutation,match", [
    ("hash", "manifest_hash_mismatch"),
    ("row_count", "manifest_row_count_mismatch"),
    ("schema", "manifest_schema_unsupported"),
    ("registry", "manifest_registry_digest_mismatch"),
])
def test_manifest_integrity_fails_closed(tmp_path, mutation, match):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    if mutation == "hash":
        raw["files"][0]["sha256"] = "0" * 64
    elif mutation == "row_count":
        raw["files"][0]["row_count"] += 1
    elif mutation == "schema":
        raw["schema_version"] = "unknown"
    else:
        registry.write_text(registry.read_text() + "\n", encoding="utf-8")
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_universe_package(manifest, registry)


def test_manifest_rejects_parent_traversal(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    raw["files"][0]["path"] = "../outside.csv"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest_path_unsafe"):
        load_universe_package(manifest, registry)


def test_manifest_rejects_symlink_escape(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    outside = tmp_path / "outside.csv"
    outside.write_text("identity_row_id\nid-1\n", encoding="utf-8")
    link = manifest.parent / "escape.csv"
    link.symlink_to(outside)
    raw = json.loads(manifest.read_text())
    raw["files"][0].update(path="escape.csv", sha256=__import__("hashlib").sha256(outside.read_bytes()).hexdigest(), row_count=1)
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest_path_unsafe"):
        load_universe_package(manifest, registry)


@pytest.mark.parametrize("unlisted_kind", ["file", "symlink"])
def test_manifest_rejects_unlisted_package_entry(tmp_path, unlisted_kind):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    extra = manifest.parent / "unlisted.csv"
    if unlisted_kind == "file":
        extra.write_text("unexpected\n", encoding="utf-8")
    else:
        extra.symlink_to(manifest.parent / "identity.csv")
    with pytest.raises(ValueError, match="manifest_unlisted_file"):
        load_universe_package(manifest, registry)


def test_manifest_rejects_missing_listed_file_with_stable_reason(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    (manifest.parent / raw["files"][0]["path"]).unlink()
    with pytest.raises(ValueError, match="manifest_file_unreadable"):
        load_universe_package(manifest, registry)


@pytest.mark.parametrize("mutation,match", [
    ("coverage", "manifest_coverage_semantics_invalid"),
    ("declared_empty", "manifest_declared_universes_invalid"),
    ("declared_blank_id", "manifest_declared_universes_invalid"),
    ("declared_invalid_kind", "manifest_declared_universes_invalid"),
    ("sources", "manifest_allowed_source_ids_invalid"),
    ("walk_forward", "manifest_evaluation_policy_invalid"),
    ("partition_boundaries", "manifest_evaluation_policy_invalid"),
    ("corporate_actions", "manifest_corporate_action_policy_invalid"),
    ("delisting", "manifest_delisting_policy_invalid"),
    ("survivorship", "manifest_survivorship_policy_invalid"),
    ("reproduction", "manifest_reproduction_contract_invalid"),
])
def test_manifest_rejects_invalid_immutable_policy_semantics(tmp_path, mutation, match):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    if mutation == "coverage":
        raw["coverage_semantics"] = "current_snapshot"
    elif mutation == "declared_empty":
        raw["declared_universes"] = []
    elif mutation == "declared_blank_id":
        raw["declared_universes"][0]["universe_id"] = ""
    elif mutation == "declared_invalid_kind":
        raw["declared_universes"][0]["universe_kind"] = "current_universe"
    elif mutation == "sources":
        raw["allowed_source_ids"] = []
    elif mutation == "walk_forward":
        raw["evaluation_policy"]["minimum_history_count"] = 0
    elif mutation == "partition_boundaries":
        raw["evaluation_policy"] = {
            "kind": "train_validation_test",
            "train_end_at": "2021-01-03T00:00:00Z",
            "validation_start_at": "2021-01-02T00:00:00Z",
            "validation_end_at": "2021-01-04T00:00:00Z",
            "test_start_at": "2021-01-05T00:00:00Z",
        }
    elif mutation == "corporate_actions":
        raw["corporate_action_policy"].pop("delisting")
    elif mutation == "delisting":
        raw["delisting_policy"]["missing_evidence"] = "ignore"
    elif mutation == "survivorship":
        raw["survivorship_policy"]["filter_by_current_listing_state"] = True
    else:
        raw["reproduction_contract"] = "membership_count_v0"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_universe_package(manifest, registry)


@pytest.mark.parametrize("mutation,match", [
    ("dataset_id", "manifest_dataset_id_invalid"),
    ("manifest_id", "manifest_id_invalid"),
    ("created_at", "manifest_created_at_invalid"),
    ("created_at_without_timezone", "manifest_created_at_invalid"),
    ("created_at_date_only_z", "manifest_created_at_invalid"),
    ("cutoff_at", "manifest_observation_cutoff_at_invalid"),
    ("cutoff_at_without_timezone", "manifest_observation_cutoff_at_invalid"),
    ("cutoff_at_date_only_z", "manifest_observation_cutoff_at_invalid"),
])
def test_manifest_rejects_invalid_identity_and_cutoff_metadata(tmp_path, mutation, match):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    if mutation == "dataset_id":
        raw["dataset_id"] = ""
    elif mutation == "manifest_id":
        raw["manifest_id"] = None
    elif mutation == "created_at":
        raw["manifest_created_at"] = "not-a-timestamp"
    elif mutation == "created_at_without_timezone":
        raw["manifest_created_at"] = "2021-01-02T00:00:00"
    elif mutation == "created_at_date_only_z":
        raw["manifest_created_at"] = "2021-01-02Z"
    elif mutation == "cutoff_at":
        raw["observation_cutoff_at"] = ""
    elif mutation == "cutoff_at_date_only_z":
        raw["observation_cutoff_at"] = "2021-01-01Z"
    else:
        raw["observation_cutoff_at"] = "2021-01-01T00:00:00"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_universe_package(manifest, registry)


@pytest.mark.parametrize("mutation", ["path", "contract", "uppercase_sha256", "short_sha256", "negative_row_count", "bool_row_count"])
def test_manifest_rejects_invalid_file_record_before_construction(tmp_path, mutation):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    file_record = raw["files"][0]
    if mutation == "path":
        file_record["path"] = ""
    elif mutation == "contract":
        file_record["contract"] = ""
    elif mutation == "uppercase_sha256":
        file_record["sha256"] = file_record["sha256"].upper()
    elif mutation == "short_sha256":
        file_record["sha256"] = "a" * 63
    elif mutation == "negative_row_count":
        file_record["row_count"] = -1
    else:
        file_record["row_count"] = True
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest_file_record_invalid"):
        load_universe_package(manifest, registry)
