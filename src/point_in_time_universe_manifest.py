from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from src.point_in_time_universe_identifiers import is_control_free


REQUIRED_CONTRACTS = frozenset({"security_identity", "membership", "events", "evaluations"})
ALLOWED_COVERAGE_SEMANTICS = frozenset({"complete_snapshot", "event_history"})
ALLOWED_UNIVERSE_KINDS = frozenset({"benchmark", "research_universe"})
ALLOWED_EVENT_TYPES = frozenset({
    "listing", "ticker_change", "exchange_change", "split", "reverse_split", "merger",
    "acquisition", "spinoff", "delisting", "suspension", "reactivation",
})
ALLOWED_ACTION_POLICY_STATES = frozenset({"required", "not_applicable", "unsupported"})
REPRODUCTION_CONTRACT = "membership_count_and_sha256_at_cutoff_v1"
RFC3339_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

# Local safeguards for one supplied package. These are not coverage, scale,
# hosted-reliability, or commercial-capacity claims.
MAX_MANIFEST_BYTES = 1 * 1024 * 1024
MAX_CONTRACT_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES = 64 * 1024 * 1024
MAX_RIGHTS_REGISTRY_BYTES = 4 * 1024 * 1024
MAX_DECLARED_ROWS_PER_CONTRACT = 250_000
MAX_PACKAGE_TRAVERSAL_ENTRIES = 32
MAX_MANIFEST_NESTING_DEPTH = 64


@dataclass(frozen=True)
class ManifestFile:
    path: str
    contract: str
    sha256: str
    row_count: int


def _freeze_manifest_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({
            key: _freeze_manifest_value(item)
            for key, item in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_manifest_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_manifest_value(item) for item in value)
    return value


def _validate_manifest_nesting(value: Any) -> None:
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > MAX_MANIFEST_NESTING_DEPTH:
            raise ValueError("manifest_nesting_limit_exceeded")
        if isinstance(item, Mapping):
            pending.extend(
                (nested, depth + 1)
                for nested in item.values()
            )
        elif isinstance(item, (list, tuple, set, frozenset)):
            pending.extend(
                (nested, depth + 1)
                for nested in item
            )


@dataclass(frozen=True)
class UniverseManifest:
    schema_version: str
    dataset_id: str
    manifest_id: str
    manifest_created_at: str
    observation_cutoff_at: str
    coverage_semantics: str
    declared_universes: tuple[Mapping[str, str], ...]
    allowed_source_ids: tuple[str, ...]
    source_rights_registry_sha256: str
    files: tuple[ManifestFile, ...]
    evaluation_policy: Mapping[str, Any]
    corporate_action_policy: Mapping[str, str]
    delisting_policy: Mapping[str, Any]
    survivorship_policy: Mapping[str, Any]
    reproduction_contract: str

    def __post_init__(self) -> None:
        for name in (
            "declared_universes",
            "allowed_source_ids",
            "files",
            "evaluation_policy",
            "corporate_action_policy",
            "delisting_policy",
            "survivorship_policy",
        ):
            object.__setattr__(
                self,
                name,
                _freeze_manifest_value(getattr(self, name)),
            )


@dataclass(frozen=True)
class LoadedUniversePackage:
    manifest_path: Path
    registry_path: Path
    manifest: UniverseManifest
    files: Mapping[str, Path]
    contract_snapshots: Mapping[str, bytes]
    registry_snapshot: bytes


def _sha256(snapshot: bytes) -> str:
    return hashlib.sha256(snapshot).hexdigest()


def _csv_row_count(snapshot: bytes) -> int:
    with io.StringIO(snapshot.decode("utf-8"), newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _bounded_snapshot(
    path: Path,
    *,
    maximum_bytes: int,
    size_error: str,
    unreadable_error: str,
    combined_maximum_bytes: int | None = None,
    combined_size_error: str | None = None,
    _dir_fd: int | None = None,
    _no_follow: bool = False,
) -> bytes:
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
            os,
            "O_NONBLOCK",
            0,
        )
        if _no_follow:
            no_follow = getattr(os, "O_NOFOLLOW", None)
            if not isinstance(no_follow, int) or no_follow == 0:
                raise ValueError(unreadable_error)
            flags |= no_follow
        descriptor = os.open(path, flags, dir_fd=_dir_fd)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(unreadable_error)
        if before.st_size > maximum_bytes:
            raise ValueError(size_error)
        if (
            combined_maximum_bytes is not None
            and before.st_size > combined_maximum_bytes
        ):
            raise ValueError(combined_size_error or size_error)
        read_maximum = (
            maximum_bytes
            if combined_maximum_bytes is None
            else min(maximum_bytes, combined_maximum_bytes)
        )
        chunks: list[bytes] = []
        remaining = read_maximum + 1
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        snapshot = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(snapshot) > maximum_bytes or after.st_size > maximum_bytes:
            raise ValueError(size_error)
        if (
            combined_maximum_bytes is not None
            and (
                len(snapshot) > combined_maximum_bytes
                or after.st_size > combined_maximum_bytes
            )
        ):
            raise ValueError(combined_size_error or size_error)
        stable_metadata = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if stable_metadata != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError(size_error)
        if len(snapshot) != after.st_size:
            raise ValueError(unreadable_error)
    except ValueError:
        raise
    except (OSError, TypeError, NotImplementedError) as exc:
        raise ValueError(unreadable_error) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return snapshot


def _open_directory_descriptor(
    path: Path | str,
    *,
    unreadable_error: str,
    dir_fd: int | None = None,
) -> int:
    descriptor: int | None = None
    try:
        directory_only = getattr(os, "O_DIRECTORY", None)
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if (
            not isinstance(directory_only, int)
            or directory_only == 0
            or not isinstance(no_follow, int)
            or no_follow == 0
        ):
            raise ValueError(unreadable_error)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | directory_only
            | no_follow
        )
        descriptor = os.open(path, flags, dir_fd=dir_fd)
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ValueError(unreadable_error)
        return descriptor
    except ValueError:
        if descriptor is not None:
            os.close(descriptor)
        raise
    except (OSError, TypeError, NotImplementedError) as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise ValueError(unreadable_error) from exc


def _relative_bounded_snapshot(
    package_descriptor: int,
    relative_path: str,
    *,
    maximum_bytes: int,
    size_error: str,
    unreadable_error: str,
    combined_maximum_bytes: int | None = None,
    combined_size_error: str | None = None,
) -> bytes:
    parts = Path(relative_path).parts
    current_descriptor: int | None = None
    try:
        current_descriptor = os.dup(package_descriptor)
        for component in parts[:-1]:
            next_descriptor = _open_directory_descriptor(
                component,
                unreadable_error=unreadable_error,
                dir_fd=current_descriptor,
            )
            os.close(current_descriptor)
            current_descriptor = next_descriptor
        return _bounded_snapshot(
            Path(parts[-1]),
            maximum_bytes=maximum_bytes,
            size_error=size_error,
            unreadable_error=unreadable_error,
            combined_maximum_bytes=combined_maximum_bytes,
            combined_size_error=combined_size_error,
            _dir_fd=current_descriptor,
            _no_follow=True,
        )
    except (OSError, TypeError, NotImplementedError) as exc:
        raise ValueError(unreadable_error) from exc
    finally:
        if current_descriptor is not None:
            os.close(current_descriptor)


def _safe_child(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("manifest_path_unsafe")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("manifest_path_unsafe")
    resolved_base = base.resolve()
    resolved = (base / relative_path).resolve()
    if resolved == resolved_base or resolved_base not in resolved.parents:
        raise ValueError("manifest_path_unsafe")
    return resolved


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_identifier(value: Any) -> bool:
    return (
        _nonempty_string(value)
        and value == value.strip()
        and is_control_free(value)
    )


def _unique_json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("manifest_duplicate_key")
        result[key] = value
    return result


def _utc_timestamp(value: Any) -> datetime | None:
    if (
        not isinstance(value, str)
        or RFC3339_UTC.fullmatch(value) is None
    ):
        return None
    try:
        timestamp = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return None
    if timestamp.tzinfo is None or timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
        return None
    return timestamp


def _valid_evaluation_policy(policy: Any) -> bool:
    if not isinstance(policy, dict):
        return False
    if policy.get("kind") == "walk_forward":
        history = policy.get("minimum_history_count")
        return isinstance(history, int) and not isinstance(history, bool) and history > 0
    if policy.get("kind") != "train_validation_test":
        return False
    boundaries = [
        _utc_timestamp(policy.get("train_end_at")),
        _utc_timestamp(policy.get("validation_start_at")),
        _utc_timestamp(policy.get("validation_end_at")),
        _utc_timestamp(policy.get("test_start_at")),
    ]
    return all(boundaries) and boundaries == sorted(boundaries) and len(set(boundaries)) == 4


def _validate_manifest_semantics(raw: Mapping[str, Any]) -> None:
    if not _nonempty_identifier(raw.get("dataset_id")):
        raise ValueError("manifest_dataset_id_invalid")
    if not _nonempty_identifier(raw.get("manifest_id")):
        raise ValueError("manifest_id_invalid")
    manifest_created_at = _utc_timestamp(raw.get("manifest_created_at"))
    if manifest_created_at is None:
        raise ValueError("manifest_created_at_invalid")
    observation_cutoff_at = _utc_timestamp(
        raw.get("observation_cutoff_at")
    )
    if observation_cutoff_at is None:
        raise ValueError("manifest_observation_cutoff_at_invalid")
    if manifest_created_at < observation_cutoff_at:
        raise ValueError(
            "manifest_created_before_observation_cutoff"
        )
    coverage_semantics = raw.get("coverage_semantics")
    if (
        not isinstance(coverage_semantics, str)
        or coverage_semantics not in ALLOWED_COVERAGE_SEMANTICS
    ):
        raise ValueError("manifest_coverage_semantics_invalid")
    declared_universes = raw.get("declared_universes")
    if not isinstance(declared_universes, list) or not declared_universes:
        raise ValueError("manifest_declared_universes_invalid")
    declared_ids: set[str] = set()
    for universe in declared_universes:
        if not isinstance(universe, dict):
            raise ValueError("manifest_declared_universes_invalid")
        universe_id = universe.get("universe_id")
        universe_kind = universe.get("universe_kind")
        if (
            not _nonempty_identifier(universe_id)
            or not isinstance(universe_kind, str)
            or universe_kind not in ALLOWED_UNIVERSE_KINDS
        ):
            raise ValueError("manifest_declared_universes_invalid")
        if universe_id in declared_ids:
            raise ValueError("manifest_declared_universes_invalid")
        declared_ids.add(universe_id)
    allowed_source_ids = raw.get("allowed_source_ids")
    if (
        not isinstance(allowed_source_ids, list)
        or not allowed_source_ids
        or any(not _nonempty_identifier(source_id) for source_id in allowed_source_ids)
        or len(allowed_source_ids) != len(set(allowed_source_ids))
    ):
        raise ValueError("manifest_allowed_source_ids_invalid")
    if not _valid_evaluation_policy(raw.get("evaluation_policy")):
        raise ValueError("manifest_evaluation_policy_invalid")
    corporate_action_policy = raw.get("corporate_action_policy")
    if (
        not isinstance(corporate_action_policy, dict)
        or set(corporate_action_policy) != ALLOWED_EVENT_TYPES
        or any(
            not isinstance(state, str)
            or state not in ALLOWED_ACTION_POLICY_STATES
            for state in corporate_action_policy.values()
        )
    ):
        raise ValueError("manifest_corporate_action_policy_invalid")
    delisting_policy = raw.get("delisting_policy")
    if (
        not isinstance(delisting_policy, dict)
        or not isinstance(delisting_policy.get("retain_historical_members"), bool)
        or delisting_policy.get("missing_evidence") != "blocked"
    ):
        raise ValueError("manifest_delisting_policy_invalid")
    survivorship_policy = raw.get("survivorship_policy")
    if (
        not isinstance(survivorship_policy, dict)
        or survivorship_policy.get("filter_by_current_listing_state") is not False
    ):
        raise ValueError("manifest_survivorship_policy_invalid")
    if raw.get("reproduction_contract") != REPRODUCTION_CONTRACT:
        raise ValueError("manifest_reproduction_contract_invalid")


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_row_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _manifest_files(raw: Mapping[str, Any]) -> tuple[ManifestFile, ...]:
    try:
        files = raw["files"]
        if not isinstance(files, list):
            raise TypeError
        for item in files:
            if (
                not isinstance(item, dict)
                or not _nonempty_identifier(item.get("path"))
                or not _nonempty_identifier(item.get("contract"))
                or not _valid_sha256(item.get("sha256"))
                or not _valid_row_count(item.get("row_count"))
            ):
                raise ValueError("manifest_file_record_invalid")
            if item["row_count"] > MAX_DECLARED_ROWS_PER_CONTRACT:
                raise ValueError("manifest_row_count_limit_exceeded")
        records = tuple(ManifestFile(**item) for item in files)
    except (KeyError, TypeError) as exc:
        raise ValueError("manifest_files_invalid") from exc
    if len({item.path for item in records}) != len(records):
        raise ValueError("manifest_files_invalid")
    return records


def _reject_unlisted_files(
    package_descriptor: int,
    manifest_name: str,
    file_records: tuple[ManifestFile, ...],
) -> dict[str, int]:
    listed_paths = {Path(item.path).as_posix() for item in file_records}
    directory_descriptors: dict[str, int] = {}
    pending: list[str] = []
    entry_count = 0
    try:
        directory_descriptors[""] = os.dup(package_descriptor)
        pending.append("")
        while pending:
            prefix = pending.pop()
            current_descriptor = directory_descriptors[prefix]
            for name in sorted(os.listdir(current_descriptor)):
                entry_count += 1
                if entry_count > MAX_PACKAGE_TRAVERSAL_ENTRIES:
                    raise ValueError(
                        "manifest_package_entry_limit_exceeded"
                    )
                relative_path = (
                    f"{prefix}/{name}"
                    if prefix
                    else name
                )
                metadata = os.stat(
                    name,
                    dir_fd=current_descriptor,
                    follow_symlinks=False,
                )
                if stat.S_ISDIR(metadata.st_mode):
                    child_descriptor = (
                        _open_directory_descriptor(
                            name,
                            unreadable_error=(
                                "manifest_package_unreadable"
                            ),
                            dir_fd=current_descriptor,
                        )
                    )
                    directory_descriptors[relative_path] = (
                        child_descriptor
                    )
                    pending.append(relative_path)
                elif (
                    stat.S_ISREG(metadata.st_mode)
                    or stat.S_ISLNK(metadata.st_mode)
                ) and relative_path != manifest_name:
                    if relative_path not in listed_paths:
                        raise ValueError(
                            "manifest_unlisted_file"
                        )
        return directory_descriptors
    except ValueError:
        for descriptor in directory_descriptors.values():
            os.close(descriptor)
        raise
    except (OSError, TypeError, NotImplementedError) as exc:
        for descriptor in directory_descriptors.values():
            os.close(descriptor)
        raise ValueError("manifest_package_unreadable") from exc


def _verified_contract_parent_descriptor(
    directory_descriptors: Mapping[str, int],
    relative_path: str,
) -> tuple[int, str]:
    path = Path(relative_path)
    prefix = ""
    try:
        for component in path.parts[:-1]:
            child_prefix = (
                f"{prefix}/{component}"
                if prefix
                else component
            )
            parent_descriptor = directory_descriptors[prefix]
            child_descriptor = directory_descriptors[child_prefix]
            visible = os.stat(
                component,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            opened = os.fstat(child_descriptor)
            if (
                not stat.S_ISDIR(visible.st_mode)
                or (visible.st_dev, visible.st_ino)
                != (opened.st_dev, opened.st_ino)
            ):
                raise ValueError("manifest_file_unreadable")
            prefix = child_prefix
        return directory_descriptors[prefix], path.name
    except ValueError:
        raise
    except (
        KeyError,
        OSError,
        TypeError,
        NotImplementedError,
    ) as exc:
        raise ValueError("manifest_file_unreadable") from exc


def _validate_open_package_inventory(
    directory_descriptors: Mapping[str, int],
    manifest_name: str,
    file_records: tuple[ManifestFile, ...],
) -> None:
    expected_directories = set(directory_descriptors) - {""}
    contract_directories: set[str] = set()
    for item in file_records:
        parts = Path(item.path).parts[:-1]
        for length in range(1, len(parts) + 1):
            contract_directories.add(
                Path(*parts[:length]).as_posix()
            )
    expected_files = {
        manifest_name,
        *(Path(item.path).as_posix() for item in file_records),
    }
    observed_directories: set[str] = set()
    observed_files: set[str] = set()
    entry_count = 0

    def directory_change_error(relative_path: str) -> str:
        if relative_path in contract_directories:
            return "manifest_file_unreadable"
        return "manifest_package_unreadable"

    def expected_non_regular_error(relative_path: str) -> str:
        if relative_path == manifest_name:
            return "manifest_package_unreadable"
        if relative_path in expected_files:
            return "manifest_file_unreadable"
        if relative_path in expected_directories:
            return directory_change_error(relative_path)
        return "manifest_unlisted_file"

    try:
        for prefix, descriptor in directory_descriptors.items():
            for name in sorted(os.listdir(descriptor)):
                entry_count += 1
                if entry_count > MAX_PACKAGE_TRAVERSAL_ENTRIES:
                    raise ValueError(
                        "manifest_package_entry_limit_exceeded"
                    )
                relative_path = (
                    f"{prefix}/{name}"
                    if prefix
                    else name
                )
                metadata = os.stat(
                    name,
                    dir_fd=descriptor,
                    follow_symlinks=False,
                )
                if stat.S_ISDIR(metadata.st_mode):
                    if relative_path in expected_files:
                        raise ValueError(
                            expected_non_regular_error(relative_path)
                        )
                    observed_directories.add(relative_path)
                    mapped_descriptor = directory_descriptors.get(
                        relative_path
                    )
                    if mapped_descriptor is not None:
                        opened = os.fstat(mapped_descriptor)
                        if (metadata.st_dev, metadata.st_ino) != (
                            opened.st_dev,
                            opened.st_ino,
                        ):
                            raise ValueError(
                                directory_change_error(relative_path)
                            )
                elif stat.S_ISREG(metadata.st_mode):
                    observed_files.add(relative_path)
                else:
                    raise ValueError(
                        expected_non_regular_error(relative_path)
                    )

        extra_directories = (
            observed_directories - expected_directories
        )
        if extra_directories:
            raise ValueError("manifest_unlisted_file")
        missing_directories = (
            expected_directories - observed_directories
        )
        if missing_directories:
            error = (
                "manifest_file_unreadable"
                if missing_directories & contract_directories
                else "manifest_package_unreadable"
            )
            raise ValueError(error)

        if observed_files - expected_files:
            raise ValueError("manifest_unlisted_file")
        missing_files = expected_files - observed_files
        if manifest_name in missing_files:
            raise ValueError("manifest_package_unreadable")
        if missing_files:
            raise ValueError("manifest_file_unreadable")
    except ValueError:
        raise
    except (OSError, TypeError, NotImplementedError) as exc:
        raise ValueError("manifest_package_unreadable") from exc


def load_universe_package(manifest_path: Path, registry_path: Path) -> LoadedUniversePackage:
    requested_manifest_path = Path(manifest_path)
    package_dir = requested_manifest_path.parent.resolve()
    manifest_path = package_dir / requested_manifest_path.name
    registry_path = Path(registry_path)
    resolved: dict[str, Path] = {}
    contract_snapshots: dict[str, bytes] = {}
    total_snapshot_bytes = 0
    directory_descriptors: dict[str, int] = {}
    package_descriptor = _open_directory_descriptor(
        package_dir,
        unreadable_error="manifest_package_unreadable",
    )
    try:
        manifest_snapshot = _bounded_snapshot(
            Path(manifest_path.name),
            maximum_bytes=MAX_MANIFEST_BYTES,
            size_error="manifest_size_limit_exceeded",
            unreadable_error="manifest_unreadable",
            _dir_fd=package_descriptor,
            _no_follow=True,
        )
        try:
            raw = json.loads(
                manifest_snapshot.decode("utf-8"),
                object_pairs_hook=_unique_json_object,
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            RecursionError,
        ) as exc:
            raise ValueError("manifest_unreadable") from exc
        if not isinstance(raw, dict):
            raise ValueError("manifest_unreadable")
        _validate_manifest_nesting(raw)
        if raw.get("schema_version") != "point_in_time_universe_v1":
            raise ValueError("manifest_schema_unsupported")
        _validate_manifest_semantics(raw)
        file_records = _manifest_files(raw)
        contracts = [item.contract for item in file_records]
        if (
            set(contracts) != REQUIRED_CONTRACTS
            or len(contracts) != len(set(contracts))
        ):
            raise ValueError("manifest_contract_set_invalid")
        resolved_paths = tuple(
            _safe_child(package_dir, item.path)
            for item in file_records
        )
        directory_descriptors = _reject_unlisted_files(
            package_descriptor,
            manifest_path.name,
            file_records,
        )
        for item, path in zip(
            file_records,
            resolved_paths,
            strict=True,
        ):
            _validate_open_package_inventory(
                directory_descriptors,
                manifest_path.name,
                file_records,
            )
            remaining_combined_bytes = max(
                MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES
                - total_snapshot_bytes,
                0,
            )
            parent_descriptor, file_name = (
                _verified_contract_parent_descriptor(
                    directory_descriptors,
                    item.path,
                )
            )
            snapshot = _bounded_snapshot(
                Path(file_name),
                maximum_bytes=MAX_CONTRACT_SNAPSHOT_BYTES,
                size_error="manifest_file_size_limit_exceeded",
                unreadable_error="manifest_file_unreadable",
                combined_maximum_bytes=remaining_combined_bytes,
                combined_size_error=(
                    "manifest_total_snapshot_size_limit_exceeded"
                ),
                _dir_fd=parent_descriptor,
                _no_follow=True,
            )
            total_snapshot_bytes += len(snapshot)
            if (
                total_snapshot_bytes
                > MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES
            ):
                raise ValueError(
                    "manifest_total_snapshot_size_limit_exceeded"
                )
            file_hash = _sha256(snapshot)
            row_count = _csv_row_count(snapshot)
            if file_hash != item.sha256:
                raise ValueError("manifest_hash_mismatch")
            if row_count != item.row_count:
                raise ValueError("manifest_row_count_mismatch")
            resolved[item.contract] = path
            contract_snapshots[item.contract] = snapshot
            _validate_open_package_inventory(
                directory_descriptors,
                manifest_path.name,
                file_records,
            )
        _validate_open_package_inventory(
            directory_descriptors,
            manifest_path.name,
            file_records,
        )
    finally:
        for descriptor in directory_descriptors.values():
            os.close(descriptor)
        os.close(package_descriptor)
    registry_snapshot = _bounded_snapshot(
        registry_path,
        maximum_bytes=MAX_RIGHTS_REGISTRY_BYTES,
        size_error="manifest_registry_size_limit_exceeded",
        unreadable_error="manifest_registry_unreadable",
    )
    registry_hash = _sha256(registry_snapshot)
    if registry_hash != raw.get("source_rights_registry_sha256"):
        raise ValueError("manifest_registry_digest_mismatch")
    manifest = UniverseManifest(
        schema_version=raw["schema_version"],
        dataset_id=raw["dataset_id"],
        manifest_id=raw["manifest_id"],
        manifest_created_at=raw["manifest_created_at"],
        observation_cutoff_at=raw["observation_cutoff_at"],
        coverage_semantics=raw["coverage_semantics"],
        declared_universes=tuple(MappingProxyType(dict(item)) for item in raw["declared_universes"]),
        allowed_source_ids=tuple(raw["allowed_source_ids"]),
        source_rights_registry_sha256=raw["source_rights_registry_sha256"],
        files=file_records,
        evaluation_policy=MappingProxyType(dict(raw["evaluation_policy"])),
        corporate_action_policy=MappingProxyType(dict(raw["corporate_action_policy"])),
        delisting_policy=MappingProxyType(dict(raw["delisting_policy"])),
        survivorship_policy=MappingProxyType(dict(raw["survivorship_policy"])),
        reproduction_contract=raw["reproduction_contract"],
    )
    return LoadedUniversePackage(
        manifest_path=manifest_path.resolve(),
        registry_path=registry_path.resolve(),
        manifest=manifest,
        files=MappingProxyType(resolved),
        contract_snapshots=MappingProxyType(contract_snapshots),
        registry_snapshot=registry_snapshot,
    )
