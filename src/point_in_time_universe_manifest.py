from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


REQUIRED_CONTRACTS = frozenset({"security_identity", "membership", "events", "evaluations"})
ALLOWED_COVERAGE_SEMANTICS = frozenset({"complete_snapshot", "event_history"})
ALLOWED_UNIVERSE_KINDS = frozenset({"benchmark", "research_universe"})
ALLOWED_EVENT_TYPES = frozenset({
    "listing", "ticker_change", "exchange_change", "split", "reverse_split", "merger",
    "acquisition", "spinoff", "delisting", "suspension", "reactivation",
})
ALLOWED_ACTION_POLICY_STATES = frozenset({"required", "not_applicable", "unsupported"})
REPRODUCTION_CONTRACT = "membership_count_and_sha256_at_cutoff_v1"

# Local safeguards for one supplied package. These are not coverage, scale,
# hosted-reliability, or commercial-capacity claims.
MAX_MANIFEST_BYTES = 1 * 1024 * 1024
MAX_CONTRACT_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES = 64 * 1024 * 1024
MAX_RIGHTS_REGISTRY_BYTES = 4 * 1024 * 1024
MAX_DECLARED_ROWS_PER_CONTRACT = 250_000
MAX_PACKAGE_TRAVERSAL_ENTRIES = 32


@dataclass(frozen=True)
class ManifestFile:
    path: str
    contract: str
    sha256: str
    row_count: int


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
) -> bytes:
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
            os,
            "O_NONBLOCK",
            0,
        )
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(unreadable_error)
        if before.st_size > maximum_bytes:
            raise ValueError(size_error)
        snapshot = os.read(descriptor, maximum_bytes + 1)
        after = os.fstat(descriptor)
        if len(snapshot) > maximum_bytes or after.st_size > maximum_bytes:
            raise ValueError(size_error)
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
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(unreadable_error) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return snapshot


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


def _utc_timestamp(value: Any) -> datetime | None:
    if not _nonempty_string(value) or "T" not in value or not value.endswith("Z"):
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
    if not _nonempty_string(raw.get("dataset_id")):
        raise ValueError("manifest_dataset_id_invalid")
    if not _nonempty_string(raw.get("manifest_id")):
        raise ValueError("manifest_id_invalid")
    if _utc_timestamp(raw.get("manifest_created_at")) is None:
        raise ValueError("manifest_created_at_invalid")
    if _utc_timestamp(raw.get("observation_cutoff_at")) is None:
        raise ValueError("manifest_observation_cutoff_at_invalid")
    if raw.get("coverage_semantics") not in ALLOWED_COVERAGE_SEMANTICS:
        raise ValueError("manifest_coverage_semantics_invalid")
    declared_universes = raw.get("declared_universes")
    if not isinstance(declared_universes, list) or not declared_universes:
        raise ValueError("manifest_declared_universes_invalid")
    declared_ids: set[str] = set()
    for universe in declared_universes:
        if not isinstance(universe, dict):
            raise ValueError("manifest_declared_universes_invalid")
        universe_id = universe.get("universe_id")
        if not _nonempty_string(universe_id) or universe.get("universe_kind") not in ALLOWED_UNIVERSE_KINDS:
            raise ValueError("manifest_declared_universes_invalid")
        if universe_id in declared_ids:
            raise ValueError("manifest_declared_universes_invalid")
        declared_ids.add(universe_id)
    allowed_source_ids = raw.get("allowed_source_ids")
    if (
        not isinstance(allowed_source_ids, list)
        or not allowed_source_ids
        or any(not _nonempty_string(source_id) for source_id in allowed_source_ids)
        or len(allowed_source_ids) != len(set(allowed_source_ids))
    ):
        raise ValueError("manifest_allowed_source_ids_invalid")
    if not _valid_evaluation_policy(raw.get("evaluation_policy")):
        raise ValueError("manifest_evaluation_policy_invalid")
    corporate_action_policy = raw.get("corporate_action_policy")
    if (
        not isinstance(corporate_action_policy, dict)
        or set(corporate_action_policy) != ALLOWED_EVENT_TYPES
        or any(state not in ALLOWED_ACTION_POLICY_STATES for state in corporate_action_policy.values())
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
                or not _nonempty_string(item.get("path"))
                or not _nonempty_string(item.get("contract"))
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


def _reject_unlisted_files(package_dir: Path, manifest_path: Path, file_records: tuple[ManifestFile, ...]) -> None:
    listed_paths = {Path(item.path).as_posix() for item in file_records}
    pending = [package_dir]
    entry_count = 0
    try:
        while pending:
            current = pending.pop()
            with os.scandir(current) as entries:
                for entry in entries:
                    entry_count += 1
                    if entry_count > MAX_PACKAGE_TRAVERSAL_ENTRIES:
                        raise ValueError(
                            "manifest_package_entry_limit_exceeded"
                        )
                    candidate = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(candidate)
                    elif (
                        entry.is_file(follow_symlinks=False)
                        or entry.is_symlink()
                    ) and candidate != manifest_path:
                        relative_path = candidate.relative_to(
                            package_dir
                        ).as_posix()
                        if relative_path not in listed_paths:
                            raise ValueError("manifest_unlisted_file")
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError("manifest_package_unreadable") from exc


def load_universe_package(manifest_path: Path, registry_path: Path) -> LoadedUniversePackage:
    manifest_path = Path(manifest_path).resolve()
    registry_path = Path(registry_path)
    try:
        manifest_snapshot = _bounded_snapshot(
            manifest_path,
            maximum_bytes=MAX_MANIFEST_BYTES,
            size_error="manifest_size_limit_exceeded",
            unreadable_error="manifest_unreadable",
        )
        raw = json.loads(manifest_snapshot.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("manifest_unreadable") from exc
    if not isinstance(raw, dict):
        raise ValueError("manifest_unreadable")
    if raw.get("schema_version") != "point_in_time_universe_v1":
        raise ValueError("manifest_schema_unsupported")
    _validate_manifest_semantics(raw)
    file_records = _manifest_files(raw)
    contracts = [item.contract for item in file_records]
    if set(contracts) != REQUIRED_CONTRACTS or len(contracts) != len(set(contracts)):
        raise ValueError("manifest_contract_set_invalid")
    package_dir = manifest_path.parent
    resolved_paths = tuple(_safe_child(package_dir, item.path) for item in file_records)
    _reject_unlisted_files(package_dir, manifest_path, file_records)
    resolved: dict[str, Path] = {}
    contract_snapshots: dict[str, bytes] = {}
    total_snapshot_bytes = 0
    for item, path in zip(file_records, resolved_paths, strict=True):
        snapshot = _bounded_snapshot(
            path,
            maximum_bytes=MAX_CONTRACT_SNAPSHOT_BYTES,
            size_error="manifest_file_size_limit_exceeded",
            unreadable_error="manifest_file_unreadable",
        )
        total_snapshot_bytes += len(snapshot)
        if total_snapshot_bytes > MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES:
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
