from pathlib import Path
import json
import os

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


def test_hash_and_row_count_use_the_same_immutable_file_snapshot(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    identity_path = manifest.parent / "identity.csv"
    verified_bytes = identity_path.read_bytes()
    original_sha256 = loader._sha256
    raced = False

    def hash_then_append_row(snapshot):
        nonlocal raced
        digest = original_sha256(snapshot)
        if snapshot == verified_bytes and not raced:
            raced = True
            original_row = snapshot.splitlines(keepends=True)[1]
            path.write_bytes(snapshot + original_row)
        return digest

    path = identity_path
    monkeypatch.setattr(loader, "_sha256", hash_then_append_row)

    loaded = loader.load_universe_package(manifest, registry)

    assert raced is True
    assert identity_path.read_bytes() != verified_bytes
    assert loaded.contract_snapshots["security_identity"] == verified_bytes


def test_loaded_snapshots_are_immutable(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    loaded = load_universe_package(manifest, registry)

    with pytest.raises(TypeError):
        loaded.contract_snapshots["security_identity"] = b"changed"
    with pytest.raises(TypeError):
        loaded.contract_snapshots["security_identity"][0] = 0
    with pytest.raises(TypeError):
        loaded.registry_snapshot[0] = 0


def test_bounded_reader_accepts_exact_limit_and_rejects_plus_one(tmp_path):
    from src.point_in_time_universe_manifest import _bounded_snapshot

    path = tmp_path / "snapshot.bin"
    path.write_bytes(b"abcd")
    assert _bounded_snapshot(
        path,
        maximum_bytes=4,
        size_error="too_large",
        unreadable_error="unreadable",
    ) == b"abcd"

    path.write_bytes(b"abcde")
    with pytest.raises(ValueError, match="too_large"):
        _bounded_snapshot(
            path,
            maximum_bytes=4,
            size_error="too_large",
            unreadable_error="unreadable",
        )


def test_bounded_reader_rejects_non_regular_input(tmp_path):
    from src.point_in_time_universe_manifest import _bounded_snapshot

    with pytest.raises(ValueError, match="unreadable"):
        _bounded_snapshot(
            tmp_path,
            maximum_bytes=4,
            size_error="too_large",
            unreadable_error="unreadable",
        )


def test_bounded_reader_never_requests_or_retains_more_than_limit_plus_one(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    path = tmp_path / "snapshot.bin"
    path.write_bytes(b"abcd")
    calls = []
    original_read = os.read

    def tracked_read(fd, amount):
        chunk = original_read(fd, amount)
        calls.append((amount, len(chunk)))
        return chunk

    monkeypatch.setattr(loader.os, "read", tracked_read)
    assert loader._bounded_snapshot(
        path,
        maximum_bytes=4,
        size_error="too_large",
        unreadable_error="unreadable",
    ) == b"abcd"

    assert calls
    remaining = 5
    for requested, returned in calls:
        assert requested <= remaining
        remaining -= returned
    assert remaining >= 1


def test_bounded_reader_completes_legal_short_reads_within_one_budget(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    path = tmp_path / "snapshot.bin"
    path.write_bytes(b"abcdefgh")
    original_read = os.read
    calls = []

    def short_read(descriptor, amount):
        chunk = original_read(descriptor, min(amount, 2))
        calls.append((amount, len(chunk)))
        return chunk

    monkeypatch.setattr(loader.os, "read", short_read)

    assert loader._bounded_snapshot(
        path,
        maximum_bytes=8,
        size_error="too_large",
        unreadable_error="unreadable",
    ) == b"abcdefgh"
    remaining = 9
    for requested, returned in calls:
        assert requested <= remaining
        remaining -= returned
    assert remaining == 1


def test_contract_prefix_digest_cannot_authorize_larger_stable_file(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    identity = manifest.parent / "identity.csv"
    authorized_prefix = identity.read_bytes()
    identity.write_bytes(
        authorized_prefix
        + authorized_prefix.splitlines(keepends=True)[1]
    )
    identity_inode = identity.stat().st_ino
    original_read = os.read
    shortened = False

    def prefix_first_read(descriptor, amount):
        nonlocal shortened
        if os.fstat(descriptor).st_ino == identity_inode and not shortened:
            shortened = True
            return original_read(descriptor, len(authorized_prefix))
        return original_read(descriptor, amount)

    monkeypatch.setattr(loader.os, "read", prefix_first_read)

    with pytest.raises(ValueError, match="manifest_hash_mismatch"):
        loader.load_universe_package(manifest, registry)
    assert shortened is True


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
        raw["evaluation_policy"] = {
            "kind": "walk_forward",
            "minimum_history_count": 0,
        }
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


def test_manifest_size_limit_accepts_boundary_and_rejects_boundary_plus_one(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    size = manifest.stat().st_size
    monkeypatch.setattr(loader, "MAX_MANIFEST_BYTES", size)
    loader.load_universe_package(manifest, registry)

    monkeypatch.setattr(loader, "MAX_MANIFEST_BYTES", size - 1)
    with pytest.raises(ValueError, match="manifest_size_limit_exceeded"):
        loader.load_universe_package(manifest, registry)


def test_contract_size_limits_accept_boundaries_and_reject_plus_one_before_read(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    contract_paths = tuple(
        path for path in manifest.parent.glob("*.csv")
    )
    largest = max(path.stat().st_size for path in contract_paths)
    original_read_bytes = Path.read_bytes

    monkeypatch.setattr(loader, "MAX_CONTRACT_SNAPSHOT_BYTES", largest)
    loader.load_universe_package(manifest, registry)

    read_contracts: list[Path] = []

    def track_reads(path):
        if path.suffix == ".csv":
            read_contracts.append(path)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", track_reads)
    monkeypatch.setattr(loader, "MAX_CONTRACT_SNAPSHOT_BYTES", largest - 1)
    with pytest.raises(ValueError, match="manifest_file_size_limit_exceeded"):
        loader.load_universe_package(manifest, registry)
    assert not any(
        path.stat().st_size == largest
        for path in read_contracts
    )


def test_contract_post_read_growth_past_limit_is_rejected(tmp_path, monkeypatch):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    identity = manifest.parent / "identity.csv"
    original_read = os.read
    identity_inode = identity.stat().st_ino
    limit = identity.stat().st_size
    raced = False

    def read_then_grow(descriptor, amount):
        nonlocal raced
        snapshot = original_read(descriptor, amount)
        if os.fstat(descriptor).st_ino == identity_inode and not raced:
            raced = True
            path.write_bytes(snapshot + b"x")
        return snapshot

    path = identity
    monkeypatch.setattr(loader, "MAX_CONTRACT_SNAPSHOT_BYTES", limit)
    monkeypatch.setattr(loader.os, "read", read_then_grow)
    with pytest.raises(ValueError, match="manifest_file_size_limit_exceeded"):
        loader.load_universe_package(manifest, registry)
    assert raced is True


def test_combined_contract_limit_accepts_boundary_and_rejects_plus_one(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    total = sum(path.stat().st_size for path in manifest.parent.glob("*.csv"))
    monkeypatch.setattr(loader, "MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES", total)
    loader.load_universe_package(manifest, registry)

    monkeypatch.setattr(loader, "MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES", total - 1)
    with pytest.raises(
        ValueError,
        match="manifest_total_snapshot_size_limit_exceeded",
    ):
        loader.load_universe_package(manifest, registry)


def test_registry_size_limit_accepts_boundary_and_rejects_plus_one_before_read(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    size = registry.stat().st_size
    monkeypatch.setattr(loader, "MAX_RIGHTS_REGISTRY_BYTES", size)
    loader.load_universe_package(manifest, registry)

    original_read_bytes = Path.read_bytes
    registry_reads = 0

    def track_reads(path):
        nonlocal registry_reads
        if path.resolve() == registry.resolve():
            registry_reads += 1
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", track_reads)
    monkeypatch.setattr(loader, "MAX_RIGHTS_REGISTRY_BYTES", size - 1)
    with pytest.raises(ValueError, match="manifest_registry_size_limit_exceeded"):
        loader.load_universe_package(manifest, registry)
    assert registry_reads == 0


def test_registry_post_read_growth_past_limit_is_rejected(tmp_path, monkeypatch):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    original_read = os.read
    registry_inode = registry.stat().st_ino
    limit = registry.stat().st_size
    raced = False

    def read_then_grow(descriptor, amount):
        nonlocal raced
        snapshot = original_read(descriptor, amount)
        if os.fstat(descriptor).st_ino == registry_inode and not raced:
            raced = True
            path.write_bytes(snapshot + b"x")
        return snapshot

    path = registry
    monkeypatch.setattr(loader, "MAX_RIGHTS_REGISTRY_BYTES", limit)
    monkeypatch.setattr(loader.os, "read", read_then_grow)
    with pytest.raises(ValueError, match="manifest_registry_size_limit_exceeded"):
        loader.load_universe_package(manifest, registry)
    assert raced is True


def test_declared_row_limit_accepts_boundary_and_rejects_plus_one_before_contract_read(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    monkeypatch.setattr(loader, "MAX_DECLARED_ROWS_PER_CONTRACT", 2)
    loader.load_universe_package(manifest, registry)

    original_read_bytes = Path.read_bytes
    contract_reads: list[Path] = []

    def track_reads(path):
        if path.suffix == ".csv":
            contract_reads.append(path)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", track_reads)
    monkeypatch.setattr(loader, "MAX_DECLARED_ROWS_PER_CONTRACT", 1)
    with pytest.raises(ValueError, match="manifest_row_count_limit_exceeded"):
        loader.load_universe_package(manifest, registry)
    assert contract_reads == []


def test_package_traversal_limit_accepts_boundary_and_stops_at_plus_one(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    entry_count = sum(1 for _ in manifest.parent.iterdir())
    monkeypatch.setattr(loader, "MAX_PACKAGE_TRAVERSAL_ENTRIES", entry_count)
    loader.load_universe_package(manifest, registry)

    monkeypatch.setattr(
        loader,
        "MAX_PACKAGE_TRAVERSAL_ENTRIES",
        entry_count - 1,
    )
    with pytest.raises(ValueError, match="manifest_package_entry_limit_exceeded"):
        loader.load_universe_package(manifest, registry)
