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
