from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import pytest
from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import (
    _decision,
    _rewrite_manifest,
)
from tests.test_point_in_time_universe_cli import (
    _run_cli,
    _run_make,
    _snapshot,
)
from dataclasses import FrozenInstanceError, replace
import json


def _set_manifest_enum_value(
    manifest,
    location: str,
    value,
) -> None:
    def mutate(raw):
        if location == "coverage_semantics":
            raw["coverage_semantics"] = value
        elif location == "universe_kind":
            raw["declared_universes"][0]["universe_kind"] = value
        else:
            raw["corporate_action_policy"]["listing"] = value

    _rewrite_manifest(manifest, mutate)


@pytest.mark.parametrize(
    ("location", "value", "error"),
    [
        (
            "coverage_semantics",
            ["complete_snapshot"],
            "manifest_coverage_semantics_invalid",
        ),
        (
            "coverage_semantics",
            {"state": "complete_snapshot"},
            "manifest_coverage_semantics_invalid",
        ),
        (
            "universe_kind",
            ["benchmark"],
            "manifest_declared_universes_invalid",
        ),
        (
            "universe_kind",
            {"kind": "benchmark"},
            "manifest_declared_universes_invalid",
        ),
        (
            "corporate_action_policy",
            ["required"],
            "manifest_corporate_action_policy_invalid",
        ),
        (
            "corporate_action_policy",
            {"state": "required"},
            "manifest_corporate_action_policy_invalid",
        ),
    ],
)
def test_non_scalar_manifest_enum_has_stable_validator_failure(
    tmp_path,
    location,
    value,
    error,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _set_manifest_enum_value(manifest, location, value)

    with pytest.raises(ValueError, match=f"^{error}$"):
        validate_point_in_time_universe(manifest, registry)


def test_non_scalar_manifest_enum_is_readable_and_write_free_everywhere(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _set_manifest_enum_value(
        manifest,
        "corporate_action_policy",
        {"state": "required"},
    )
    before = _snapshot(tmp_path)
    error = "manifest_corporate_action_policy_invalid"

    with pytest.raises(ValueError, match=f"^{error}$"):
        validate_point_in_time_universe(manifest, registry)

    cli = _run_cli(
        "status",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )
    make = _run_make(
        "point-in-time-universe-status",
        f"MANIFEST={manifest}",
        f"REGISTRY={registry}",
    )

    for result in (cli, make):
        assert result.returncode == 2
        assert error in result.stderr
        assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_scalar_manifest_enum_values_remain_valid(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "manifest_integrity").status == "passed"
    assert packet.analysis_eligible is True


def _set_contract_path(manifest, contract: str, path: str) -> None:
    def mutate(raw):
        entry = next(
            item
            for item in raw["files"]
            if item["contract"] == contract
        )
        entry["path"] = path

    _rewrite_manifest(manifest, mutate)


def test_final_contract_symlink_swap_cannot_escape_package(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    identity = manifest.parent / "identity.csv"
    outside = tmp_path / "outside-identity.csv"
    outside.write_bytes(identity.read_bytes())
    original_open = loader.os.open
    swapped = False

    def swap_before_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if not swapped and Path(path).name == "identity.csv":
            swapped = True
            identity.unlink()
            identity.symlink_to(outside)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(loader.os, "open", swap_before_open)

    with pytest.raises(ValueError, match="^manifest_file_unreadable$"):
        loader.load_universe_package(manifest, registry)
    assert swapped is True


def test_intermediate_contract_symlink_swap_cannot_escape_package(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    nested = manifest.parent / "nested"
    nested.mkdir()
    identity = manifest.parent / "identity.csv"
    nested_identity = nested / "identity.csv"
    identity.rename(nested_identity)
    _set_contract_path(
        manifest,
        "security_identity",
        "nested/identity.csv",
    )
    outside = tmp_path / "outside-package"
    outside.mkdir()
    (outside / "identity.csv").write_bytes(
        nested_identity.read_bytes()
    )
    saved = tmp_path / "saved-nested"
    original_inventory = loader._reject_unlisted_files

    def inventory_then_swap(*args, **kwargs):
        result = original_inventory(*args, **kwargs)
        nested.rename(saved)
        nested.symlink_to(outside, target_is_directory=True)
        return result

    monkeypatch.setattr(
        loader,
        "_reject_unlisted_files",
        inventory_then_swap,
    )

    with pytest.raises(ValueError, match="^manifest_file_unreadable$"):
        loader.load_universe_package(manifest, registry)


def test_package_directory_descriptor_survives_path_rename(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    package = manifest.parent
    moved = tmp_path / "moved-package"
    expected = (package / "identity.csv").read_bytes()
    original_inventory = loader._reject_unlisted_files

    def rename_then_inventory(*args, **kwargs):
        package.rename(moved)
        return original_inventory(*args, **kwargs)

    monkeypatch.setattr(
        loader,
        "_reject_unlisted_files",
        rename_then_inventory,
    )

    loaded = loader.load_universe_package(manifest, registry)

    assert loaded.contract_snapshots["security_identity"] == expected


def test_valid_nested_contract_path_loads_from_verified_snapshot(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    nested = manifest.parent / "nested"
    nested.mkdir()
    identity = manifest.parent / "identity.csv"
    expected = identity.read_bytes()
    identity.rename(nested / "identity.csv")
    _set_contract_path(
        manifest,
        "security_identity",
        "nested/identity.csv",
    )

    loaded = load_universe_package(manifest, registry)

    assert loaded.contract_snapshots["security_identity"] == expected


@pytest.mark.parametrize("kind", ("fifo", "directory"))
def test_contract_special_file_is_stably_unreadable(tmp_path, kind):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    identity = manifest.parent / "identity.csv"
    identity.unlink()
    if kind == "fifo":
        os.mkfifo(identity)
    else:
        identity.mkdir()

    with pytest.raises(ValueError, match="^manifest_file_unreadable$"):
        load_universe_package(manifest, registry)


def test_standalone_rights_rejects_final_symlink(tmp_path):
    from src.commercial_source_rights import load_source_rights_registry

    _, registry = build_valid_package(tmp_path)
    outside = tmp_path / "outside-rights.yml"
    outside.write_bytes(registry.read_bytes())
    link = tmp_path / "rights-link.yml"
    link.symlink_to(outside)

    with pytest.raises(
        ValueError,
        match="^source_rights_registry_unreadable$",
    ):
        load_source_rights_registry(link)


def test_standalone_rights_rejects_directory(tmp_path):
    from src.commercial_source_rights import load_source_rights_registry

    directory = tmp_path / "rights-directory"
    directory.mkdir()

    with pytest.raises(
        ValueError,
        match="^source_rights_registry_unreadable$",
    ):
        load_source_rights_registry(directory)


def test_standalone_rights_fifo_is_nonblocking_and_unreadable(tmp_path):
    fifo = tmp_path / "rights.fifo"
    os.mkfifo(fifo)
    script = (
        "import sys\n"
        "from src.commercial_source_rights import "
        "load_source_rights_registry\n"
        "try:\n"
        f"    load_source_rights_registry({str(fifo)!r})\n"
        "except ValueError as exc:\n"
        "    print(exc, file=sys.stderr)\n"
        "    raise SystemExit(2)\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parent.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=2,
    )

    assert result.returncode == 2
    assert "source_rights_registry_unreadable" in result.stderr
    assert "Traceback" not in result.stderr


def test_standalone_rights_rejects_size_limit_plus_one(
    tmp_path,
    monkeypatch,
):
    import src.commercial_source_rights as rights

    _, registry = build_valid_package(tmp_path)
    size = registry.stat().st_size
    monkeypatch.setattr(
        rights,
        "MAX_SOURCE_RIGHTS_REGISTRY_BYTES",
        size,
        raising=False,
    )
    rights.load_source_rights_registry(registry)

    registry.write_bytes(registry.read_bytes() + b" ")
    with pytest.raises(
        ValueError,
        match="^source_rights_registry_size_limit_exceeded$",
    ):
        rights.load_source_rights_registry(registry)


def test_standalone_rights_completes_short_reads(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader
    import src.commercial_source_rights as rights

    _, registry = build_valid_package(tmp_path)
    original_read = loader.os.read
    calls = 0

    def short_read(descriptor, amount):
        nonlocal calls
        calls += 1
        return original_read(descriptor, min(amount, 7))

    monkeypatch.setattr(loader.os, "read", short_read)

    parsed = rights.load_source_rights_registry(registry)

    assert "fixture_source" in parsed
    assert calls > 1


def test_standalone_rights_rejects_post_read_growth(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader
    import src.commercial_source_rights as rights

    _, registry = build_valid_package(tmp_path)
    original_read = loader.os.read
    inode = registry.stat().st_ino
    size = registry.stat().st_size
    grew = False

    def read_then_grow(descriptor, amount):
        nonlocal grew
        chunk = original_read(descriptor, amount)
        if os.fstat(descriptor).st_ino == inode and not grew:
            grew = True
            registry.write_bytes(chunk + b" ")
        return chunk

    monkeypatch.setattr(
        rights,
        "MAX_SOURCE_RIGHTS_REGISTRY_BYTES",
        size,
        raising=False,
    )
    monkeypatch.setattr(loader.os, "read", read_then_grow)

    with pytest.raises(
        ValueError,
        match="^source_rights_registry_size_limit_exceeded$",
    ):
        rights.load_source_rights_registry(registry)
    assert grew is True


def test_default_standalone_rights_registry_remains_valid():
    from src.commercial_source_rights import load_source_rights_registry

    registry = load_source_rights_registry()

    assert set(registry) == {"sec_companyfacts", "yfinance"}


def test_package_view_is_bound_before_manifest_read(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    package = manifest.parent
    replacement = tmp_path / "replacement-staged"
    shutil.copytree(package, replacement)
    (replacement / "unlisted-after-swap.txt").write_text(
        "replacement marker",
        encoding="utf-8",
    )
    original_package = tmp_path / "original-package"
    expected = (package / "identity.csv").read_bytes()
    original_open = loader.os.open
    swapped = False

    def swap_before_manifest(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if not swapped and Path(path).name == "manifest.json":
            swapped = True
            package.rename(original_package)
            replacement.rename(package)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(loader.os, "open", swap_before_manifest)

    loaded = loader.load_universe_package(manifest, registry)

    assert swapped is True
    assert loaded.contract_snapshots["security_identity"] == expected


@pytest.mark.parametrize("flag", ("O_NOFOLLOW", "O_DIRECTORY"))
def test_package_open_capability_gap_fails_closed(
    tmp_path,
    monkeypatch,
    flag,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    monkeypatch.delattr(loader.os, flag)

    with pytest.raises(
        ValueError,
        match="^manifest_package_unreadable$",
    ):
        loader.load_universe_package(manifest, registry)


def test_relative_open_not_implemented_is_stably_unreadable(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    original_open = loader.os.open

    def reject_relative_open(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None:
            raise NotImplementedError("relative open unsupported")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(loader.os, "open", reject_relative_open)

    with pytest.raises(ValueError, match="^manifest_unreadable$"):
        loader.load_universe_package(manifest, registry)


def test_standalone_rights_symlink_fails_closed_without_nofollow(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader
    from src.commercial_source_rights import load_source_rights_registry

    _, registry = build_valid_package(tmp_path)
    link = tmp_path / "rights-link-without-nofollow.yml"
    link.symlink_to(registry)
    monkeypatch.delattr(loader.os, "O_NOFOLLOW")

    with pytest.raises(
        ValueError,
        match="^source_rights_registry_unreadable$",
    ):
        load_source_rights_registry(link)


@pytest.mark.parametrize("with_unlisted_file", (False, True))
def test_nested_contract_read_reuses_inventoried_directory_view(
    tmp_path,
    monkeypatch,
    with_unlisted_file,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    nested = manifest.parent / "nested"
    nested.mkdir()
    identity = manifest.parent / "identity.csv"
    expected = identity.read_bytes()
    identity.rename(nested / "identity.csv")
    _set_contract_path(
        manifest,
        "security_identity",
        "nested/identity.csv",
    )
    replacement = tmp_path / "replacement-nested"
    shutil.copytree(nested, replacement)
    if with_unlisted_file:
        (replacement / "unlisted.txt").write_text(
            "replacement marker",
            encoding="utf-8",
        )
    original_nested_inode = nested.stat().st_ino
    saved = tmp_path / "saved-nested"
    original_inventory = loader._reject_unlisted_files
    swapped = False

    def inventory_then_swap(*args, **kwargs):
        nonlocal swapped
        result = original_inventory(*args, **kwargs)
        nested.rename(saved)
        replacement.rename(nested)
        swapped = True
        return result

    monkeypatch.setattr(
        loader,
        "_reject_unlisted_files",
        inventory_then_swap,
    )

    with pytest.raises(
        ValueError,
        match="^manifest_file_unreadable$",
    ):
        loader.load_universe_package(manifest, registry)
    assert swapped is True
    assert (saved / "identity.csv").read_bytes() == expected
    assert saved.stat().st_ino == original_nested_inode


def test_valid_multi_level_nested_contract_uses_verified_snapshot(
    tmp_path,
):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    nested = manifest.parent / "one" / "two"
    nested.mkdir(parents=True)
    identity = manifest.parent / "identity.csv"
    expected = identity.read_bytes()
    identity.rename(nested / "identity.csv")
    _set_contract_path(
        manifest,
        "security_identity",
        "one/two/identity.csv",
    )

    loaded = load_universe_package(manifest, registry)

    assert loaded.contract_snapshots["security_identity"] == expected


def test_inventoried_multi_level_view_rejects_rename_before_read(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    parent = manifest.parent / "one"
    nested = parent / "two"
    nested.mkdir(parents=True)
    identity = manifest.parent / "identity.csv"
    expected = identity.read_bytes()
    identity.rename(nested / "identity.csv")
    _set_contract_path(
        manifest,
        "security_identity",
        "one/two/identity.csv",
    )
    moved = tmp_path / "moved-one"
    original_inventory = loader._reject_unlisted_files

    def inventory_then_rename(*args, **kwargs):
        result = original_inventory(*args, **kwargs)
        parent.rename(moved)
        return result

    monkeypatch.setattr(
        loader,
        "_reject_unlisted_files",
        inventory_then_rename,
    )

    with pytest.raises(
        ValueError,
        match="^manifest_file_unreadable$",
    ):
        loader.load_universe_package(manifest, registry)
    assert (moved / "two" / "identity.csv").read_bytes() == expected


def test_unlisted_file_added_to_inventoried_view_before_read_is_rejected(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    nested = manifest.parent / "nested"
    nested.mkdir()
    identity = manifest.parent / "identity.csv"
    identity.rename(nested / "identity.csv")
    _set_contract_path(
        manifest,
        "security_identity",
        "nested/identity.csv",
    )
    original_inventory = loader._reject_unlisted_files

    def inventory_then_add_unlisted(*args, **kwargs):
        result = original_inventory(*args, **kwargs)
        (nested / "unlisted.txt").write_text(
            "added after inventory",
            encoding="utf-8",
        )
        return result

    monkeypatch.setattr(
        loader,
        "_reject_unlisted_files",
        inventory_then_add_unlisted,
    )

    with pytest.raises(
        ValueError,
        match="^manifest_unlisted_file$",
    ):
        loader.load_universe_package(manifest, registry)


def test_nested_contract_directory_replacement_after_snapshot_is_rejected(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    nested = manifest.parent / "nested"
    nested.mkdir()
    identity = manifest.parent / "identity.csv"
    identity.rename(nested / "identity.csv")
    _set_contract_path(
        manifest,
        "security_identity",
        "nested/identity.csv",
    )
    replacement = tmp_path / "replacement-nested-after-read"
    shutil.copytree(nested, replacement)
    saved = tmp_path / "saved-nested-after-read"
    original_snapshot = loader._bounded_snapshot
    swapped = False

    def snapshot_then_replace(path, **kwargs):
        nonlocal swapped
        snapshot = original_snapshot(path, **kwargs)
        if not swapped and Path(path).name == "identity.csv":
            nested.rename(saved)
            replacement.rename(nested)
            swapped = True
        return snapshot

    monkeypatch.setattr(
        loader,
        "_bounded_snapshot",
        snapshot_then_replace,
    )

    with pytest.raises(
        ValueError,
        match="^manifest_file_unreadable$",
    ):
        loader.load_universe_package(manifest, registry)
    assert swapped is True


def test_contract_free_directory_replacement_is_rejected(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    auxiliary = manifest.parent / "auxiliary"
    auxiliary.mkdir()
    replacement = tmp_path / "replacement-auxiliary"
    replacement.mkdir()
    saved = tmp_path / "saved-auxiliary"
    original_inventory = loader._reject_unlisted_files

    def inventory_then_replace(*args, **kwargs):
        result = original_inventory(*args, **kwargs)
        auxiliary.rename(saved)
        replacement.rename(auxiliary)
        return result

    monkeypatch.setattr(
        loader,
        "_reject_unlisted_files",
        inventory_then_replace,
    )

    with pytest.raises(
        ValueError,
        match="^manifest_package_unreadable$",
    ):
        loader.load_universe_package(manifest, registry)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("add", "manifest_unlisted_file"),
        ("remove", "manifest_file_unreadable"),
    ],
)
def test_final_inventory_validation_rejects_late_file_set_change(
    tmp_path,
    monkeypatch,
    mutation,
    error,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    identity = manifest.parent / "identity.csv"
    original_validate = loader._validate_open_package_inventory
    validation_calls = 0

    def mutate_after_last_post_validation(*args, **kwargs):
        nonlocal validation_calls
        result = original_validate(*args, **kwargs)
        validation_calls += 1
        if validation_calls == 8:
            if mutation == "add":
                (manifest.parent / "late-unlisted.txt").write_text(
                    "late addition",
                    encoding="utf-8",
                )
            else:
                identity.unlink()
        return result

    monkeypatch.setattr(
        loader,
        "_validate_open_package_inventory",
        mutate_after_last_post_validation,
    )

    with pytest.raises(ValueError, match=f"^{error}$"):
        loader.load_universe_package(manifest, registry)
    assert validation_calls >= 8


@pytest.mark.parametrize("kind", ("fifo", "socket"))
def test_unlisted_special_entry_is_rejected(
    monkeypatch,
    kind,
):
    from src.point_in_time_universe_manifest import load_universe_package

    if kind == "socket" and not hasattr(socket, "AF_UNIX"):
        pytest.skip("local sockets are unavailable")
    short_tmp_path = Path(tempfile.mkdtemp(prefix="pit-", dir="/tmp"))
    manifest, registry = build_valid_package(short_tmp_path)
    special = manifest.parent / f"unlisted-{kind}"
    local_socket = None
    if kind == "fifo":
        os.mkfifo(special)
    else:
        monkeypatch.chdir(manifest.parent)
        local_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            local_socket.bind(special.name)
        except OSError:
            local_socket.close()
            shutil.rmtree(short_tmp_path)
            pytest.skip("local socket paths are unavailable")

    try:
        with pytest.raises(
            ValueError,
            match="^manifest_unlisted_file$",
        ):
            load_universe_package(manifest, registry)
    finally:
        if local_socket is not None:
            local_socket.close()
        shutil.rmtree(short_tmp_path)


@pytest.mark.parametrize(
    ("api", "exception_type", "error"),
    [
        ("dup", TypeError, "manifest_package_unreadable"),
        ("dup", NotImplementedError, "manifest_package_unreadable"),
        ("dup", OSError, "manifest_package_unreadable"),
        ("listdir", TypeError, "manifest_package_unreadable"),
        ("listdir", NotImplementedError, "manifest_package_unreadable"),
        ("listdir", OSError, "manifest_package_unreadable"),
        ("stat", TypeError, "manifest_package_unreadable"),
        ("stat", NotImplementedError, "manifest_package_unreadable"),
        ("stat", OSError, "manifest_package_unreadable"),
        ("open", TypeError, "manifest_unreadable"),
        ("open", NotImplementedError, "manifest_unreadable"),
        ("open", OSError, "manifest_unreadable"),
    ],
)
def test_descriptor_api_failures_are_stably_unreadable(
    tmp_path,
    monkeypatch,
    api,
    exception_type,
    error,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    original = getattr(loader.os, api)

    if api == "dup":
        def fail_api(*args, **kwargs):
            raise exception_type("simulated descriptor API failure")
    elif api == "listdir":
        def fail_api(path):
            if isinstance(path, int):
                raise exception_type("simulated descriptor API failure")
            return original(path)
    elif api == "stat":
        def fail_api(path, *args, dir_fd=None, **kwargs):
            if dir_fd is not None:
                raise exception_type("simulated descriptor API failure")
            return original(path, *args, dir_fd=dir_fd, **kwargs)
    else:
        def fail_api(path, flags, mode=0o777, *, dir_fd=None):
            if dir_fd is not None:
                raise exception_type("simulated descriptor API failure")
            return original(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(loader.os, api, fail_api)

    with pytest.raises(ValueError, match=f"^{error}$"):
        loader.load_universe_package(manifest, registry)


def test_package_directory_descriptors_are_closed_after_load(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe_manifest as loader

    manifest, registry = build_valid_package(tmp_path)
    nested = manifest.parent / "one" / "two"
    nested.mkdir(parents=True)
    identity = manifest.parent / "identity.csv"
    identity.rename(nested / "identity.csv")
    _set_contract_path(
        manifest,
        "security_identity",
        "one/two/identity.csv",
    )
    original_open = loader.os.open
    original_dup = loader.os.dup
    original_close = loader.os.close
    active_tokens = {}
    close_counts = {}
    next_token = 0

    def track_descriptor(descriptor):
        nonlocal next_token
        token = next_token
        next_token += 1
        active_tokens.setdefault(descriptor, []).append(token)
        close_counts[token] = 0

    def capture_directory_open(
        path,
        flags,
        mode=0o777,
        *,
        dir_fd=None,
    ):
        descriptor = original_open(
            path,
            flags,
            mode,
            dir_fd=dir_fd,
        )
        if flags & loader.os.O_DIRECTORY:
            track_descriptor(descriptor)
        return descriptor

    def capture_directory_dup(descriptor):
        duplicate = original_dup(descriptor)
        track_descriptor(duplicate)
        return duplicate

    def capture_directory_close(descriptor):
        tokens = active_tokens.get(descriptor)
        if tokens:
            token = tokens.pop(0)
            close_counts[token] += 1
            if not tokens:
                del active_tokens[descriptor]
        return original_close(descriptor)

    monkeypatch.setattr(loader.os, "open", capture_directory_open)
    monkeypatch.setattr(loader.os, "dup", capture_directory_dup)
    monkeypatch.setattr(loader.os, "close", capture_directory_close)

    loader.load_universe_package(manifest, registry)

    assert len(close_counts) >= 4
    assert set(close_counts.values()) == {1}
    assert active_tokens == {}


def _add_nested_extensions(manifest) -> None:
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["declared_universes"][0]["metadata"] = {
        "labels": ["stable"],
    }
    raw["evaluation_policy"]["metadata"] = {
        "windows": ["strict"],
    }
    raw["delisting_policy"]["metadata"] = {
        "reviewed": True,
    }
    raw["survivorship_policy"]["metadata"] = {
        "notes": ["point-in-time"],
    }
    manifest.write_text(
        json.dumps(raw, sort_keys=True),
        encoding="utf-8",
    )


def test_loaded_manifest_rejects_top_level_and_nested_mutation(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _add_nested_extensions(manifest)
    loaded = load_universe_package(manifest, registry).manifest

    with pytest.raises(FrozenInstanceError):
        loaded.dataset_id = "changed"
    with pytest.raises(TypeError):
        loaded.evaluation_policy["kind"] = "walk_forward"
    with pytest.raises(TypeError):
        loaded.declared_universes[0]["metadata"]["labels"][0] = "changed"
    with pytest.raises(TypeError):
        loaded.evaluation_policy["metadata"]["windows"][0] = "changed"
    with pytest.raises(TypeError):
        loaded.delisting_policy["metadata"]["reviewed"] = False
    with pytest.raises(TypeError):
        loaded.survivorship_policy["metadata"]["notes"][0] = "changed"

    assert loaded.declared_universes[0]["metadata"]["labels"] == (
        "stable",
    )
    assert loaded.evaluation_policy["metadata"]["windows"] == ("strict",)
    assert loaded.delisting_policy["metadata"]["reviewed"] is True
    assert loaded.survivorship_policy["metadata"]["notes"] == (
        "point-in-time",
    )


def test_manifest_constructor_defensively_copies_nested_inputs(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    loaded = load_universe_package(manifest, registry).manifest
    declared = [
        {
            "universe_id": "bench-1",
            "universe_kind": "benchmark",
            "metadata": {"labels": ["stable"]},
        },
    ]
    policy = {
        "kind": "walk_forward",
        "minimum_history_count": 1,
        "metadata": {"windows": ["strict"]},
    }

    copied = replace(
        loaded,
        declared_universes=declared,
        evaluation_policy=policy,
    )
    declared[0]["universe_id"] = "mutated"
    declared[0]["metadata"]["labels"][0] = "mutated"
    policy["kind"] = "mutated"
    policy["metadata"]["windows"][0] = "mutated"

    assert copied.declared_universes[0]["universe_id"] == "bench-1"
    assert copied.declared_universes[0]["metadata"]["labels"] == (
        "stable",
    )
    assert copied.evaluation_policy["kind"] == "walk_forward"
    assert copied.evaluation_policy["metadata"]["windows"] == ("strict",)


def test_independently_loaded_nested_manifests_remain_equal(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    _add_nested_extensions(manifest)

    first = load_universe_package(manifest, registry).manifest
    second = load_universe_package(manifest, registry).manifest

    assert first == second


@pytest.mark.parametrize("command", ("status", "preview"))
def test_nested_manifest_extensions_remain_cli_compatible_and_write_free(
    tmp_path,
    command,
):
    manifest, registry = build_valid_package(tmp_path)
    _add_nested_extensions(manifest)
    before = _snapshot(tmp_path)

    result = _run_cli(
        command,
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 0
    assert "technical_validity: passed" in result.stdout
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_excessively_deep_manifest_extension_fails_closed_and_write_free(
    tmp_path,
):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    nested = {"leaf": "value"}
    for _ in range(80):
        nested = {"next": nested}
    raw["evaluation_policy"]["metadata"] = nested
    manifest.write_text(
        json.dumps(raw, sort_keys=True),
        encoding="utf-8",
    )
    before = _snapshot(tmp_path)
    error = "manifest_nesting_limit_exceeded"

    with pytest.raises(ValueError, match=f"^{error}$"):
        load_universe_package(manifest, registry)

    result = _run_cli(
        "status",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 2
    assert error in result.stderr
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before
