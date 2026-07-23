from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


REQUIRED_CONTRACTS = frozenset({"security_identity", "membership", "events", "evaluations"})


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _safe_child(base: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ValueError("manifest_path_unsafe")
    resolved_base = base.resolve()
    resolved = (base / relative).resolve()
    if resolved == resolved_base or resolved_base not in resolved.parents:
        raise ValueError("manifest_path_unsafe")
    return resolved


def load_universe_package(manifest_path: Path, registry_path: Path) -> LoadedUniversePackage:
    manifest_path = Path(manifest_path)
    registry_path = Path(registry_path)
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("manifest_unreadable") from exc
    if raw.get("schema_version") != "point_in_time_universe_v1":
        raise ValueError("manifest_schema_unsupported")
    file_records = tuple(ManifestFile(**item) for item in raw.get("files", []))
    contracts = [item.contract for item in file_records]
    if set(contracts) != REQUIRED_CONTRACTS or len(contracts) != len(set(contracts)):
        raise ValueError("manifest_contract_set_invalid")
    resolved: dict[str, Path] = {}
    for item in file_records:
        path = _safe_child(manifest_path.parent, item.path)
        if _sha256(path) != item.sha256:
            raise ValueError("manifest_hash_mismatch")
        if _csv_row_count(path) != item.row_count:
            raise ValueError("manifest_row_count_mismatch")
        resolved[item.contract] = path
    if _sha256(registry_path) != raw.get("source_rights_registry_sha256"):
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
    )
