# Point-in-Time Benchmark and Universe Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved provider-neutral, read-only validator for immutable point-in-time security identity, benchmark/research-universe membership, corporate actions, delistings, source rights, cutoffs, reproduction, and leakage.

**Architecture:** Keep the new validator isolated from the ticker-centric current-universe merge path. A manifest loader proves package identity, typed parsers preserve ordered source rows, lineage and temporal validators classify evidence independently, and one composer emits status/preview packets without writing, fetching, applying, rebuilding readiness, or activating analysis.

**Tech Stack:** Python 3.12, frozen dataclasses, `csv`, `hashlib`, `json`, `pathlib`, existing `src.commercial_source_rights`, pytest, Make.

## Global Constraints

- Follow `docs/superpowers/specs/2026-07-23-point-in-time-universe-foundation-design.md` exactly.
- Research-only; no ranking, recommendations, investment advice, position sizing, broker integration, order routing, auto-trading, or price prediction.
- Do not modify or call the apply paths for `data/universe.csv`, `data/universe_master.csv`, or `data/universe_active.csv`.
- Do not fetch data, call providers, add keys, alter source rights, rebuild readiness, or write normalized/rejected/report artifacts.
- Stable `security_id` and `issuer_id` are required; ticker must never become permanent identity.
- Technical, temporal, identity, membership, corporate-action, delisting, source-rights, reproduction, and leakage states remain independent.
- Synthetic evidence exists only in pytest temporary directories and cannot complete Priority 4.
- Every production behavior starts with a failing focused test.
- Stage exact intentional product/code/docs/test files only; never use `git add -A`.
- Keep the 18 existing generated CSV/JSON/report files unstaged.
- Keep PR #113 open and draft; do not merge or deploy.

---

## File Structure

- Create `src/point_in_time_universe_manifest.py`: immutable manifest types, safe path resolution, hashes, row counts, and package loading.
- Create `src/point_in_time_universe_contracts.py`: schema constants, typed records, timestamp/date/enum parsing, and ordered raw/normalized rows.
- Create `src/point_in_time_universe_lineage.py`: generic exact-parent lineage validation and cutoff leaf selection.
- Create `src/point_in_time_universe.py`: independent decisions, identity/membership/action/delisting/rights/leakage composition, reproduction digests, rendering, and CLI.
- Create `tests/point_in_time_universe_fixture.py`: test-only package builder that writes exclusively beneath pytest `tmp_path`.
- Create `tests/test_point_in_time_universe_manifest.py`: manifest-integrity and no-write tests.
- Create `tests/test_point_in_time_universe_contracts.py`: schema, type, enum, and timestamp tests.
- Create `tests/test_point_in_time_universe_lineage.py`: root/leaf, fork, cycle, cross-scope, and cutoff tests.
- Create `tests/test_point_in_time_universe.py`: composed state, action, delisting, rights, leakage, reproduction, and no-current-fallback tests.
- Create `tests/test_point_in_time_universe_cli.py`: CLI/Make, status/preview, invocation, blocked-package, and no-write tests.
- Modify `Makefile`: add the two read-only entry points.
- Modify `ROADMAP.md`, `docs/METHODOLOGY.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, and `tests/test_public_v1_release_docs.py`: record implemented local scope without claiming Priority 4 completion.

---

### Task 1: Test-Only Package Builder and Immutable Manifest Loader

**Files:**
- Create: `tests/point_in_time_universe_fixture.py`
- Create: `tests/test_point_in_time_universe_manifest.py`
- Create: `src/point_in_time_universe_manifest.py`

**Interfaces:**
- Produces `ManifestFile`, `UniverseManifest`, and `LoadedUniversePackage`.
- Produces `load_universe_package(manifest_path: Path, registry_path: Path) -> LoadedUniversePackage`.
- Produces `build_valid_package(root: Path) -> tuple[Path, Path]` for tests only.

- [ ] **Step 1: Write the test-only package builder**

```python
# tests/point_in_time_universe_fixture.py
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_valid_package(root: Path) -> tuple[Path, Path]:
    package = root / "package"
    package.mkdir()
    identity = [{
        "identity_row_id": "id-1", "security_id": "sec-1", "issuer_id": "issuer-1",
        "ticker": "AAA", "exchange": "XNYS", "security_type": "common_stock",
        "currency": "USD", "valid_from": "2020-01-01T00:00:00Z", "valid_to": "",
        "source_id": "fixture_source", "source_ref": "fixture://identity/id-1",
        "source_published_at": "2020-01-01T00:00:00Z",
        "retrieved_at": "2020-01-02T00:00:00Z",
        "supersedes_identity_row_id": "",
    }]
    membership = [
        {
            "membership_row_id": f"member-{universe}", "universe_id": universe,
            "universe_kind": kind, "security_id": "sec-1",
            "membership_state": "included", "effective_from": "2020-01-01T00:00:00Z",
            "effective_to": "", "observation_at": "2020-01-01T00:00:00Z",
            "source_id": "fixture_source", "source_ref": f"fixture://membership/{universe}",
            "source_published_at": "2020-01-01T00:00:00Z",
            "retrieved_at": "2020-01-02T00:00:00Z",
            "supersedes_membership_row_id": "",
        }
        for universe, kind in (("bench-1", "benchmark"), ("research-1", "research_universe"))
    ]
    events = [{
        "event_row_id": "event-1", "security_id": "sec-1", "event_type": "listing",
        "effective_at": "2020-01-01T00:00:00Z", "successor_security_id": "",
        "ratio_numerator": "", "ratio_denominator": "", "listing_state_after": "active",
        "source_id": "fixture_source", "source_ref": "fixture://event/event-1",
        "source_published_at": "2020-01-01T00:00:00Z",
        "retrieved_at": "2020-01-02T00:00:00Z", "supersedes_event_row_id": "",
    }]
    evaluations = [
        {
            "evaluation_row_id": f"eval-{universe}", "universe_id": universe,
            "evaluation_at": "2021-01-01T00:00:00Z",
            "available_at": "2021-01-01T00:00:00Z", "partition": "walk_forward",
            "source_ref": f"fixture://evaluation/{universe}",
        }
        for universe in ("bench-1", "research-1")
    ]
    payloads = {
        "identity.csv": identity,
        "membership.csv": membership,
        "events.csv": events,
        "evaluations.csv": evaluations,
    }
    files = []
    contract_by_name = {
        "identity.csv": "security_identity",
        "membership.csv": "membership",
        "events.csv": "events",
        "evaluations.csv": "evaluations",
    }
    for name, rows in payloads.items():
        path = package / name
        _write_csv(path, rows)
        files.append({
            "path": name, "contract": contract_by_name[name],
            "sha256": _sha256(path), "row_count": len(rows),
        })
    registry = root / "source_rights.yml"
    registry.write_text(
        "sources:\n"
        "  - source_id: fixture_source\n"
        "    display_name: Test-only source\n"
        "    permitted_use: test_only\n"
        "    commercial_use: approved\n"
        "    redistribution: test_only\n"
        "    storage_limits: pytest temporary directory only\n"
        "    attribution: synthetic fixture\n"
        "    rate_limits: not_applicable\n"
        "    authentication: none\n"
        "    expected_freshness: point in time\n"
        "    supported_fields: [security_identity, universe_membership, corporate_actions, delistings]\n"
        "    fallback_priority: 1\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "point_in_time_universe_v1",
        "dataset_id": "fixture-dataset", "manifest_id": "fixture-manifest",
        "manifest_created_at": "2021-01-02T00:00:00Z",
        "observation_cutoff_at": "2021-01-01T00:00:00Z",
        "coverage_semantics": "complete_snapshot",
        "declared_universes": [
            {"universe_id": "bench-1", "universe_kind": "benchmark"},
            {"universe_id": "research-1", "universe_kind": "research_universe"},
        ],
        "allowed_source_ids": ["fixture_source"],
        "source_rights_registry_sha256": _sha256(registry),
        "files": files,
        "evaluation_policy": {"kind": "walk_forward", "minimum_history_count": 1},
        "corporate_action_policy": {
            "listing": "required", "ticker_change": "not_applicable",
            "exchange_change": "not_applicable", "split": "not_applicable",
            "reverse_split": "not_applicable", "merger": "not_applicable",
            "acquisition": "not_applicable", "spinoff": "not_applicable",
            "delisting": "not_applicable", "suspension": "not_applicable",
            "reactivation": "not_applicable",
        },
        "delisting_policy": {
            "retain_historical_members": True,
            "missing_evidence": "blocked",
        },
        "survivorship_policy": {
            "filter_by_current_listing_state": False,
        },
        "reproduction_contract": "membership_count_and_sha256_at_cutoff_v1",
    }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return manifest_path, registry
```

- [ ] **Step 2: Write failing manifest tests**

```python
# tests/test_point_in_time_universe_manifest.py
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
```

- [ ] **Step 3: Run the manifest tests and observe RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe_manifest.py -q
```

Expected: collection fails because `src.point_in_time_universe_manifest` does not exist.

- [ ] **Step 4: Implement the immutable manifest loader**

```python
# src/point_in_time_universe_manifest.py
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
```

- [ ] **Step 5: Add path traversal and symlink-escape tests**

```python
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
```

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe_manifest.py -q
git diff --check
git add -- src/point_in_time_universe_manifest.py tests/point_in_time_universe_fixture.py tests/test_point_in_time_universe_manifest.py
make staged-hygiene-check
git commit -m "Add immutable universe package loader"
```

Expected: all manifest tests pass; staged generated artifacts are `0`.

---

### Task 2: Typed Evidence Contracts and Technical Validation

**Files:**
- Create: `src/point_in_time_universe_contracts.py`
- Create: `tests/test_point_in_time_universe_contracts.py`

**Interfaces:**
- Consumes `LoadedUniversePackage`.
- Produces `RawEvidenceRow`, `IdentityObservation`, `MembershipObservation`, `UniverseEvent`, `EvaluationObservation`, `ContractFinding`, and `ParsedUniverseEvidence`.
- Produces `parse_universe_evidence(package: LoadedUniversePackage) -> ParsedUniverseEvidence`.

- [ ] **Step 1: Write failing schema and type tests**

```python
# tests/test_point_in_time_universe_contracts.py
import csv
import json
import math
import pytest

from tests.point_in_time_universe_fixture import build_valid_package


def _rewrite_csv_and_manifest(manifest, contract, mutate):
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == contract)
    path = manifest.parent / entry["path"]
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    entry["sha256"] = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    entry["row_count"] = len(rows)
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def test_parser_preserves_raw_order_and_normalizes_display_ticker(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package
    from src.point_in_time_universe_contracts import parse_universe_evidence
    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(manifest, "security_identity", lambda rows: rows[0].update(ticker=" aaa "))
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))
    assert parsed.identities[0].ticker == "AAA"
    assert parsed.raw[0].contract == "security_identity"
    assert parsed.raw[0].source_row == 2


@pytest.mark.parametrize("contract,column,value,reason", [
    ("security_identity", "valid_from", "2020-01-01", "schema_timestamp_invalid"),
    ("membership", "membership_state", "maybe", "schema_enum_invalid"),
    ("membership", "universe_kind", "portfolio", "schema_enum_invalid"),
    ("events", "event_type", "dividend", "schema_enum_invalid"),
    ("events", "ratio_numerator", "nan", "schema_ratio_invalid"),
    ("evaluations", "partition", "future", "schema_enum_invalid"),
])
def test_invalid_values_become_stable_technical_findings(tmp_path, contract, column, value, reason):
    from src.point_in_time_universe_manifest import load_universe_package
    from src.point_in_time_universe_contracts import parse_universe_evidence
    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(manifest, contract, lambda rows: rows[0].update({column: value}))
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))
    assert reason in {code for finding in parsed.findings for code in finding.reason_codes}
```

- [ ] **Step 2: Run tests and observe RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe_contracts.py -q
```

Expected: collection fails because `src.point_in_time_universe_contracts` does not exist.

- [ ] **Step 3: Implement frozen record types and parsers**

```python
# src/point_in_time_universe_contracts.py
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from src.point_in_time_universe_manifest import LoadedUniversePackage


EVENT_TYPES = frozenset({"listing", "ticker_change", "exchange_change", "split", "reverse_split", "merger", "acquisition", "spinoff", "delisting", "suspension", "reactivation"})
LISTING_STATES = frozenset({"", "active", "delisted", "suspended"})
PARTITIONS = frozenset({"train", "validation", "test", "walk_forward"})


@dataclass(frozen=True)
class RawEvidenceRow:
    contract: str
    source_file: str
    source_row: int
    values: Mapping[str, str]


@dataclass(frozen=True)
class ContractFinding:
    contract: str
    source_row: int
    row_id: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class IdentityObservation:
    identity_row_id: str; security_id: str; issuer_id: str; ticker: str
    exchange: str; security_type: str; currency: str
    valid_from: datetime; valid_to: datetime | None
    source_id: str; source_ref: str; source_published_at: datetime; retrieved_at: datetime
    supersedes_identity_row_id: str


@dataclass(frozen=True)
class MembershipObservation:
    membership_row_id: str; universe_id: str; universe_kind: str; security_id: str
    membership_state: str; effective_from: datetime; effective_to: datetime | None
    observation_at: datetime; source_id: str; source_ref: str
    source_published_at: datetime; retrieved_at: datetime
    supersedes_membership_row_id: str


@dataclass(frozen=True)
class UniverseEvent:
    event_row_id: str; security_id: str; event_type: str; effective_at: datetime
    successor_security_id: str; ratio_numerator: float | None; ratio_denominator: float | None
    listing_state_after: str; source_id: str; source_ref: str
    source_published_at: datetime; retrieved_at: datetime; supersedes_event_row_id: str


@dataclass(frozen=True)
class EvaluationObservation:
    evaluation_row_id: str; universe_id: str; evaluation_at: datetime
    available_at: datetime; partition: str; source_ref: str


@dataclass(frozen=True)
class ParsedUniverseEvidence:
    raw: tuple[RawEvidenceRow, ...]
    identities: tuple[IdentityObservation, ...]
    memberships: tuple[MembershipObservation, ...]
    events: tuple[UniverseEvent, ...]
    evaluations: tuple[EvaluationObservation, ...]
    findings: tuple[ContractFinding, ...]


def parse_utc(value: str) -> datetime:
    text = str(value or "").strip()
    if not text.endswith("Z"):
        raise ValueError("schema_timestamp_invalid")
    parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError("schema_timestamp_invalid")
    return parsed


def optional_utc(value: str) -> datetime | None:
    return None if not str(value or "").strip() else parse_utc(value)


def optional_positive_float(value: str) -> float | None:
    if not str(value or "").strip():
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError("schema_ratio_invalid")
    return parsed


IDENTITY_COLUMNS = (
    "identity_row_id", "security_id", "issuer_id", "ticker", "exchange",
    "security_type", "currency", "valid_from", "valid_to", "source_id",
    "source_ref", "source_published_at", "retrieved_at",
    "supersedes_identity_row_id",
)
MEMBERSHIP_COLUMNS = (
    "membership_row_id", "universe_id", "universe_kind", "security_id",
    "membership_state", "effective_from", "effective_to", "observation_at",
    "source_id", "source_ref", "source_published_at", "retrieved_at",
    "supersedes_membership_row_id",
)
EVENT_COLUMNS = (
    "event_row_id", "security_id", "event_type", "effective_at",
    "successor_security_id", "ratio_numerator", "ratio_denominator",
    "listing_state_after", "source_id", "source_ref",
    "source_published_at", "retrieved_at", "supersedes_event_row_id",
)
EVALUATION_COLUMNS = (
    "evaluation_row_id", "universe_id", "evaluation_at", "available_at",
    "partition", "source_ref",
)
COLUMNS = {
    "security_identity": IDENTITY_COLUMNS,
    "membership": MEMBERSHIP_COLUMNS,
    "events": EVENT_COLUMNS,
    "evaluations": EVALUATION_COLUMNS,
}
ROW_ID_FIELDS = {
    "security_identity": "identity_row_id",
    "membership": "membership_row_id",
    "events": "event_row_id",
    "evaluations": "evaluation_row_id",
}


def _required(row, *names):
    values = tuple(str(row.get(name, "") or "").strip() for name in names)
    if any(not value for value in values):
        raise ValueError("schema_required_field_missing")
    return values


def _parse_identity(row):
    required = _required(
        row, "identity_row_id", "security_id", "issuer_id", "ticker",
        "exchange", "security_type", "currency", "valid_from", "source_id",
        "source_ref", "source_published_at", "retrieved_at",
    )
    return IdentityObservation(
        identity_row_id=required[0], security_id=required[1],
        issuer_id=required[2], ticker=required[3].upper(),
        exchange=required[4], security_type=required[5], currency=required[6],
        valid_from=parse_utc(required[7]), valid_to=optional_utc(row["valid_to"]),
        source_id=required[8], source_ref=required[9],
        source_published_at=parse_utc(required[10]),
        retrieved_at=parse_utc(required[11]),
        supersedes_identity_row_id=row["supersedes_identity_row_id"].strip(),
    )


def _parse_membership(row):
    required = _required(
        row, "membership_row_id", "universe_id", "universe_kind",
        "security_id", "membership_state", "effective_from",
        "observation_at", "source_id", "source_ref",
        "source_published_at", "retrieved_at",
    )
    if required[2] not in {"benchmark", "research_universe"}:
        raise ValueError("schema_enum_invalid")
    if required[4] not in {"included", "excluded"}:
        raise ValueError("schema_enum_invalid")
    return MembershipObservation(
        membership_row_id=required[0], universe_id=required[1],
        universe_kind=required[2], security_id=required[3],
        membership_state=required[4], effective_from=parse_utc(required[5]),
        effective_to=optional_utc(row["effective_to"]),
        observation_at=parse_utc(required[6]), source_id=required[7],
        source_ref=required[8], source_published_at=parse_utc(required[9]),
        retrieved_at=parse_utc(required[10]),
        supersedes_membership_row_id=row["supersedes_membership_row_id"].strip(),
    )


def _parse_event(row):
    required = _required(
        row, "event_row_id", "security_id", "event_type", "effective_at",
        "source_id", "source_ref", "source_published_at", "retrieved_at",
    )
    if required[2] not in EVENT_TYPES or row["listing_state_after"].strip() not in LISTING_STATES:
        raise ValueError("schema_enum_invalid")
    try:
        numerator = optional_positive_float(row["ratio_numerator"])
        denominator = optional_positive_float(row["ratio_denominator"])
    except (TypeError, ValueError) as exc:
        raise ValueError("schema_ratio_invalid") from exc
    if (numerator is None) != (denominator is None):
        raise ValueError("schema_ratio_pair_required")
    return UniverseEvent(
        event_row_id=required[0], security_id=required[1],
        event_type=required[2], effective_at=parse_utc(required[3]),
        successor_security_id=row["successor_security_id"].strip(),
        ratio_numerator=numerator, ratio_denominator=denominator,
        listing_state_after=row["listing_state_after"].strip(),
        source_id=required[4], source_ref=required[5],
        source_published_at=parse_utc(required[6]),
        retrieved_at=parse_utc(required[7]),
        supersedes_event_row_id=row["supersedes_event_row_id"].strip(),
    )


def _parse_evaluation(row):
    required = _required(
        row, "evaluation_row_id", "universe_id", "evaluation_at",
        "available_at", "partition", "source_ref",
    )
    if required[4] not in PARTITIONS:
        raise ValueError("schema_enum_invalid")
    return EvaluationObservation(
        evaluation_row_id=required[0], universe_id=required[1],
        evaluation_at=parse_utc(required[2]), available_at=parse_utc(required[3]),
        partition=required[4], source_ref=required[5],
    )


PARSERS = {
    "security_identity": _parse_identity,
    "membership": _parse_membership,
    "events": _parse_event,
    "evaluations": _parse_evaluation,
}


def parse_universe_evidence(package: LoadedUniversePackage) -> ParsedUniverseEvidence:
    raw_rows: list[RawEvidenceRow] = []
    parsed: dict[str, list] = {name: [] for name in COLUMNS}
    findings: list[ContractFinding] = []
    for contract in ("security_identity", "membership", "events", "evaluations"):
        path = package.files[contract]
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != COLUMNS[contract]:
                findings.append(ContractFinding(
                    contract, 1, "", ("schema_columns_invalid",),
                ))
                continue
            for source_row, values in enumerate(reader, start=2):
                clean = MappingProxyType({
                    key: str(value or "") for key, value in values.items()
                })
                raw_rows.append(RawEvidenceRow(
                    contract, path.name, source_row, clean,
                ))
                row_id = clean.get(ROW_ID_FIELDS[contract], "").strip()
                try:
                    parsed[contract].append(PARSERS[contract](clean))
                except (KeyError, TypeError, ValueError) as exc:
                    reason = str(exc)
                    if not reason.startswith("schema_"):
                        reason = "schema_value_invalid"
                    findings.append(ContractFinding(
                        contract, source_row, row_id, (reason,),
                    ))
    return ParsedUniverseEvidence(
        raw=tuple(raw_rows),
        identities=tuple(parsed["security_identity"]),
        memberships=tuple(parsed["membership"]),
        events=tuple(parsed["events"]),
        evaluations=tuple(parsed["evaluations"]),
        findings=tuple(findings),
    )
```

- [ ] **Step 4: Add ratio-pair and exact-column tests**

```python
def test_split_requires_both_positive_ratio_values(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package
    from src.point_in_time_universe_contracts import parse_universe_evidence
    manifest, registry = build_valid_package(tmp_path)
    def mutate(rows):
        rows[0].update(event_type="split", ratio_numerator="2", ratio_denominator="")
    _rewrite_csv_and_manifest(manifest, "events", mutate)
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))
    assert "schema_ratio_pair_required" in {c for f in parsed.findings for c in f.reason_codes}


def test_unexpected_or_missing_columns_block_contract(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package
    from src.point_in_time_universe_contracts import parse_universe_evidence
    manifest, registry = build_valid_package(tmp_path)
    path = manifest.parent / "identity.csv"
    text = path.read_text().replace("issuer_id,", "")
    path.write_text(text, encoding="utf-8")
    raw = json.loads(manifest.read_text())
    entry = next(i for i in raw["files"] if i["contract"] == "security_identity")
    entry["sha256"] = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    parsed = parse_universe_evidence(load_universe_package(manifest, registry))
    assert "schema_columns_invalid" in {c for f in parsed.findings for c in f.reason_codes}
```

- [ ] **Step 5: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe_contracts.py tests/test_point_in_time_universe_manifest.py -q
git diff --check
git add -- src/point_in_time_universe_contracts.py tests/test_point_in_time_universe_contracts.py
make staged-hygiene-check
git commit -m "Add point-in-time universe contracts"
```

Expected: contract and manifest tests pass; no repository CSV/JSON is staged.

---

### Task 3: Exact Revision Lineage, Stable Identity, and Historical Membership

**Files:**
- Create: `src/point_in_time_universe_lineage.py`
- Create: `tests/test_point_in_time_universe_lineage.py`
- Create: `src/point_in_time_universe.py`
- Create: `tests/test_point_in_time_universe.py`

**Interfaces:**
- Produces `LineageResult[T]` and `resolve_lineage(records, row_id, parent_id, scope, available_at, cutoff)`.
- Produces `Decision`, `ExcludedRow`, `MembershipDigest`, and `PointInTimeUniversePacket`.
- Produces `validate_point_in_time_universe(manifest_path, registry_path, top_n=20)`.

- [ ] **Step 1: Write failing generic lineage tests**

```python
# tests/test_point_in_time_universe_lineage.py
from dataclasses import dataclass
from datetime import datetime, timezone

from src.point_in_time_universe_lineage import resolve_lineage


@dataclass(frozen=True)
class Row:
    row_id: str
    parent_id: str
    scope: str
    available_at: datetime


T0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2021, 1, 1, tzinfo=timezone.utc)


def test_selects_latest_unambiguous_leaf_available_by_cutoff():
    rows = (Row("a", "", "scope", T0), Row("b", "a", "scope", T1))
    result = resolve_lineage(
        rows, row_id=lambda r: r.row_id, parent_id=lambda r: r.parent_id,
        scope=lambda r: r.scope, available_at=lambda r: r.available_at, cutoff=T1,
    )
    assert result.leaves == (rows[1],)
    assert result.reason_codes == ()


def test_fork_blocks_scope_instead_of_picking_a_leaf():
    rows = (Row("a", "", "scope", T0), Row("b", "a", "scope", T1), Row("c", "a", "scope", T1))
    result = resolve_lineage(
        rows, row_id=lambda r: r.row_id, parent_id=lambda r: r.parent_id,
        scope=lambda r: r.scope, available_at=lambda r: r.available_at, cutoff=T1,
    )
    assert result.leaves == ()
    assert "lineage_fork" in result.reason_codes
```

Add the remaining lineage cases with explicit rows:

```python
def _resolve(rows, cutoff=T1):
    return resolve_lineage(
        rows, row_id=lambda r: r.row_id, parent_id=lambda r: r.parent_id,
        scope=lambda r: r.scope, available_at=lambda r: r.available_at,
        cutoff=cutoff,
    )


@pytest.mark.parametrize("rows,reason", [
    ((Row("a", "", "s", T0), Row("a", "", "s", T1)), "lineage_duplicate_id"),
    ((Row("b", "missing", "s", T1),), "lineage_missing_parent"),
    ((Row("a", "", "s1", T0), Row("b", "a", "s2", T1)), "lineage_cross_scope_parent"),
    ((Row("a", "", "s", T0), Row("b", "", "s", T1)), "lineage_multiple_roots"),
    ((Row("a", "b", "s", T0), Row("b", "a", "s", T1)), "lineage_cycle"),
    ((Row("a", "", "s", T1), Row("b", "a", "s", T0)), "lineage_order_reversed"),
])
def test_invalid_lineage_is_blocked(rows, reason):
    assert reason in _resolve(rows).reason_codes


def test_post_cutoff_revision_is_not_selected():
    rows = (Row("a", "", "scope", T0), Row("b", "a", "scope", T1))
    result = _resolve(rows, cutoff=T0)
    assert tuple(row.row_id for row in result.leaves) == ("a",)
```

- [ ] **Step 2: Run lineage tests and observe RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe_lineage.py -q
```

Expected: collection fails because `src.point_in_time_universe_lineage` does not exist.

- [ ] **Step 3: Implement generic lineage resolution**

```python
# src/point_in_time_universe_lineage.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Generic, Iterable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class LineageResult(Generic[T]):
    leaves: tuple[T, ...]
    excluded: tuple[T, ...]
    reason_codes: tuple[str, ...]


def resolve_lineage(
    records: Iterable[T], *, row_id: Callable[[T], str],
    parent_id: Callable[[T], str], scope: Callable[[T], str],
    available_at: Callable[[T], datetime], cutoff: datetime,
) -> LineageResult[T]:
    eligible = tuple(record for record in records if available_at(record) <= cutoff)
    ids = [row_id(record) for record in eligible]
    reasons: set[str] = set()
    if len(ids) != len(set(ids)):
        reasons.add("lineage_duplicate_id")
    by_id = {row_id(record): record for record in eligible}
    children: dict[str, list[T]] = {}
    roots: dict[str, list[T]] = {}
    for record in eligible:
        parent = parent_id(record)
        record_scope = scope(record)
        if not parent:
            roots.setdefault(record_scope, []).append(record)
            continue
        prior = by_id.get(parent)
        if prior is None:
            reasons.add("lineage_missing_parent")
            continue
        if scope(prior) != record_scope:
            reasons.add("lineage_cross_scope_parent")
        if available_at(record) <= available_at(prior):
            reasons.add("lineage_order_reversed")
        children.setdefault(parent, []).append(record)
    if any(len(value) > 1 for value in roots.values()):
        reasons.add("lineage_multiple_roots")
    if any(len(value) > 1 for value in children.values()):
        reasons.add("lineage_fork")
    for start in eligible:
        seen: set[str] = set()
        current = start
        while parent_id(current):
            current_id = row_id(current)
            if current_id in seen:
                reasons.add("lineage_cycle")
                break
            seen.add(current_id)
            parent = by_id.get(parent_id(current))
            if parent is None:
                break
            current = parent
    if reasons:
        return LineageResult((), eligible, tuple(sorted(reasons)))
    leaves = tuple(record for record in eligible if row_id(record) not in children)
    return LineageResult(leaves, tuple(record for record in eligible if record not in leaves), ())
```

- [ ] **Step 4: Write failing identity and membership tests**

```python
# tests/test_point_in_time_universe.py
import csv
import json

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe_contracts import _rewrite_csv_and_manifest


def test_ticker_change_preserves_security_identity_without_current_ticker_fallback(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    def mutate(rows):
        prior = dict(rows[0])
        rows[0]["valid_to"] = "2020-06-01T00:00:00Z"
        rows.append({
            **prior, "identity_row_id": "id-2", "ticker": "BBB",
            "valid_from": "2020-06-01T00:00:00Z", "valid_to": "",
            "source_ref": "fixture://identity/id-2",
            "source_published_at": "2020-06-01T00:00:00Z",
            "retrieved_at": "2020-06-02T00:00:00Z",
            "supersedes_identity_row_id": "id-1",
        })
    _rewrite_csv_and_manifest(manifest, "security_identity", mutate)
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.decisions["identity_coverage"].status == "passed"
    assert packet.display_tickers["sec-1"] == "BBB"


def test_same_ticker_for_two_security_ids_does_not_merge_membership(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    def mutate(rows):
        rows.append({**rows[0], "identity_row_id": "id-2", "security_id": "sec-2", "issuer_id": "issuer-2", "source_ref": "fixture://identity/id-2"})
    _rewrite_csv_and_manifest(manifest, "security_identity", mutate)
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.membership_digests[0].member_count == 1
```

Add explicit identity and membership failure cases:

```python
@pytest.mark.parametrize("case,reason", [
    ("overlapping_identity", "identity_interval_overlap"),
    ("missing_identity", "identity_missing"),
    ("membership_outside_interval", "membership_interval_inactive"),
    ("undeclared_universe", "membership_universe_undeclared"),
    ("kind_mismatch", "membership_universe_kind_mismatch"),
])
def test_identity_and_membership_fail_closed(tmp_path, case, reason):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    mutate_identity_membership_case(manifest, case)
    packet = validate_point_in_time_universe(manifest, registry)
    assert reason in {
        code for decision in packet.decisions.values()
        for code in decision.reason_codes
    }
    assert packet.analysis_eligible is False


def mutate_identity_membership_case(manifest, case):
    if case == "overlapping_identity":
        def mutate(rows):
            rows.append({
                **rows[0], "identity_row_id": "id-overlap",
                "source_ref": "fixture://identity/id-overlap",
                "source_published_at": "2020-02-01T00:00:00Z",
                "retrieved_at": "2020-02-02T00:00:00Z",
                "supersedes_identity_row_id": "id-1",
            })
        _rewrite_csv_and_manifest(manifest, "security_identity", mutate)
    elif case == "missing_identity":
        _rewrite_csv_and_manifest(
            manifest, "membership",
            lambda rows: rows[0].update(security_id="sec-missing"),
        )
    elif case == "membership_outside_interval":
        _rewrite_csv_and_manifest(
            manifest, "membership",
            lambda rows: rows[0].update(effective_to="2020-06-01T00:00:00Z"),
        )
    elif case == "undeclared_universe":
        _rewrite_csv_and_manifest(
            manifest, "membership",
            lambda rows: rows[0].update(universe_id="unknown"),
        )
    elif case == "kind_mismatch":
        _rewrite_csv_and_manifest(
            manifest, "membership",
            lambda rows: rows[0].update(universe_kind="research_universe"),
        )
```

- [ ] **Step 5: Implement packet types and identity/membership composition**

```python
# src/point_in_time_universe.py
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from src.point_in_time_universe_contracts import parse_universe_evidence, parse_utc
from src.point_in_time_universe_lineage import resolve_lineage
from src.point_in_time_universe_manifest import load_universe_package


@dataclass(frozen=True)
class Decision:
    area: str
    status: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ExcludedRow:
    contract: str
    source_row: int
    row_id: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class MembershipDigest:
    universe_id: str
    evaluation_at: str
    member_count: int
    sha256: str


@dataclass(frozen=True)
class PointInTimeUniversePacket:
    dataset_id: str
    manifest_id: str
    analysis_eligible: bool
    decisions: Mapping[str, Decision]
    raw_count: int
    normalized_count: int
    excluded: tuple[ExcludedRow, ...]
    membership_digests: tuple[MembershipDigest, ...]
    display_tickers: Mapping[str, str]
    boundary: str


def _membership_digest(universe_id: str, evaluation_at: str, members: set[str]) -> MembershipDigest:
    payload = "\n".join(sorted(members)).encode("utf-8")
    return MembershipDigest(universe_id, evaluation_at, len(members), hashlib.sha256(payload).hexdigest())


def _contains(start, end, at):
    return start <= at and (end is None or at < end)


def _row_number(parsed, contract, row_id):
    id_field = {
        "security_identity": "identity_row_id",
        "membership": "membership_row_id",
    }[contract]
    return next(
        (row.source_row for row in parsed.raw if row.contract == contract and row.values.get(id_field) == row_id),
        0,
    )


def _identity_membership_decisions(manifest, parsed):
    declared = {
        item["universe_id"]: item["universe_kind"]
        for item in manifest.declared_universes
    }
    identity_reasons: set[str] = set()
    membership_reasons: set[str] = set()
    excluded: list[ExcludedRow] = []
    digests: list[MembershipDigest] = []
    display: dict[str, str] = {}
    cutoff = parse_utc(manifest.observation_cutoff_at)
    evaluations = tuple(item for item in parsed.evaluations if item.evaluation_at <= cutoff)
    for evaluation in evaluations:
        expected_kind = declared.get(evaluation.universe_id)
        if expected_kind is None:
            membership_reasons.add("membership_universe_undeclared")
            continue
        grouped: dict[str, list] = {}
        for row in parsed.memberships:
            if row.universe_id != evaluation.universe_id:
                continue
            if row.universe_kind != expected_kind:
                membership_reasons.add("membership_universe_kind_mismatch")
                continue
            grouped.setdefault(row.security_id, []).append(row)
        members: set[str] = set()
        for security_id, rows in grouped.items():
            lineage = resolve_lineage(
                rows,
                row_id=lambda row: row.membership_row_id,
                parent_id=lambda row: row.supersedes_membership_row_id,
                scope=lambda row: f"{row.universe_id}:{row.security_id}",
                available_at=lambda row: max(row.observation_at, row.source_published_at, row.retrieved_at),
                cutoff=evaluation.evaluation_at,
            )
            membership_reasons.update(lineage.reason_codes)
            for leaf in lineage.leaves:
                if not _contains(leaf.effective_from, leaf.effective_to, evaluation.evaluation_at):
                    membership_reasons.add("membership_interval_inactive")
                    excluded.append(ExcludedRow(
                        "membership", _row_number(parsed, "membership", leaf.membership_row_id),
                        leaf.membership_row_id, ("membership_interval_inactive",),
                    ))
                    continue
                if leaf.membership_state == "excluded":
                    continue
                identity_rows = tuple(row for row in parsed.identities if row.security_id == security_id)
                identity_lineage = resolve_lineage(
                    identity_rows,
                    row_id=lambda row: row.identity_row_id,
                    parent_id=lambda row: row.supersedes_identity_row_id,
                    scope=lambda row: row.security_id,
                    available_at=lambda row: max(row.source_published_at, row.retrieved_at),
                    cutoff=evaluation.evaluation_at,
                )
                identity_reasons.update(identity_lineage.reason_codes)
                active = tuple(
                    row for row in identity_lineage.leaves
                    if _contains(row.valid_from, row.valid_to, evaluation.evaluation_at)
                )
                if not active:
                    identity_reasons.add("identity_missing")
                    excluded.append(ExcludedRow(
                        "membership", _row_number(parsed, "membership", leaf.membership_row_id),
                        leaf.membership_row_id, ("identity_missing",),
                    ))
                    continue
                if len(active) != 1:
                    identity_reasons.add("identity_interval_overlap")
                    continue
                members.add(security_id)
                display[security_id] = active[0].ticker
        if not members:
            membership_reasons.add("membership_no_eligible_members")
        digests.append(_membership_digest(
            evaluation.universe_id,
            evaluation.evaluation_at.isoformat().replace("+00:00", "Z"),
            members,
        ))
    kinds = set(declared.values())
    if "benchmark" not in kinds:
        membership_reasons.add("membership_benchmark_missing")
    if "research_universe" not in kinds:
        membership_reasons.add("membership_research_universe_missing")
    if not evaluations:
        membership_reasons.add("membership_no_evaluation")
    return (
        Decision("identity_coverage", "blocked" if identity_reasons else "passed", tuple(sorted(identity_reasons))),
        Decision("membership_coverage", "blocked" if membership_reasons else "passed", tuple(sorted(membership_reasons))),
        tuple(digests),
        MappingProxyType(display),
        tuple(excluded),
    )


def validate_point_in_time_universe(manifest_path: Path, registry_path: Path, *, top_n: int = 20) -> PointInTimeUniversePacket:
    package = load_universe_package(manifest_path, registry_path)
    parsed = parse_universe_evidence(package)
    cutoff = parse_utc(package.manifest.observation_cutoff_at)
    decisions: dict[str, Decision] = {}
    excluded: list[ExcludedRow] = [
        ExcludedRow(f.contract, f.source_row, f.row_id, f.reason_codes)
        for f in parsed.findings
    ]
    decisions["technical_validity"] = Decision(
        "technical_validity", "blocked" if parsed.findings else "passed",
        tuple(sorted({code for finding in parsed.findings for code in finding.reason_codes})),
    )
    identity, membership, digests, display, composed_excluded = (
        _identity_membership_decisions(package.manifest, parsed)
    )
    decisions[identity.area] = identity
    decisions[membership.area] = membership
    excluded.extend(composed_excluded)
    return PointInTimeUniversePacket(
        dataset_id=package.manifest.dataset_id,
        manifest_id=package.manifest.manifest_id,
        analysis_eligible=False,
        decisions=MappingProxyType(decisions),
        raw_count=len(parsed.raw),
        normalized_count=sum((len(parsed.identities), len(parsed.memberships), len(parsed.events), len(parsed.evaluations))),
        excluded=tuple(excluded[:top_n]),
        membership_digests=digests,
        display_tickers=display,
        boundary="Local evidence eligibility only; no readiness, backtest, probability, recommendation, or trading activation.",
    )
```

- [ ] **Step 6: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_point_in_time_universe_lineage.py \
  tests/test_point_in_time_universe.py \
  tests/test_point_in_time_universe_contracts.py \
  tests/test_point_in_time_universe_manifest.py -q
git diff --check
git add -- src/point_in_time_universe_lineage.py src/point_in_time_universe.py tests/test_point_in_time_universe_lineage.py tests/test_point_in_time_universe.py
make staged-hygiene-check
git commit -m "Validate historical universe identity and membership"
```

Expected: lineage, identity, membership, contracts, and manifest tests pass.

---

### Task 4: Corporate Actions, Delistings, and Exact-Source Rights

**Files:**
- Modify: `src/point_in_time_universe.py`
- Modify: `tests/test_point_in_time_universe.py`

**Interfaces:**
- Adds `corporate_action_coverage`, `delisting_coverage`, and `source_rights_eligibility` decisions.
- Uses `load_source_rights_registry` and `review_commercial_field_scope`.

- [ ] **Step 0: Add the existing source-rights imports**

```python
# src/point_in_time_universe.py
from src.commercial_source_rights import (
    load_source_rights_registry,
    review_commercial_field_scope,
)
```

- [ ] **Step 1: Write failing action and delisting tests**

```python
def test_split_requires_positive_explicit_ratio_and_does_not_rewrite_membership(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    def mutate(rows):
        rows[0].update(event_type="split", ratio_numerator="2", ratio_denominator="1")
    _rewrite_csv_and_manifest(manifest, "events", mutate)
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.decisions["corporate_action_coverage"].status == "passed"
    assert packet.membership_digests[0].member_count == 1


def test_delisted_historical_member_is_retained_and_not_filtered_by_current_state(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    def mutate(rows):
        rows.append({
            **rows[0], "event_row_id": "event-2", "event_type": "delisting",
            "effective_at": "2022-01-01T00:00:00Z", "listing_state_after": "delisted",
            "source_ref": "fixture://event/event-2",
            "source_published_at": "2022-01-01T00:00:00Z",
            "retrieved_at": "2022-01-02T00:00:00Z",
            "supersedes_event_row_id": "",
        })
    _rewrite_csv_and_manifest(manifest, "events", mutate)
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"]["delisting"] = "required"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    packet = validate_point_in_time_universe(manifest, registry)
    assert all(d.member_count == 1 for d in packet.membership_digests)
    assert packet.decisions["delisting_coverage"].status == "passed"
```

Add the remaining explicit action-policy cases:

```python
@pytest.mark.parametrize("event_type,updates,reason", [
    ("merger", {"successor_security_id": ""}, "corporate_action_successor_required"),
    ("acquisition", {"successor_security_id": ""}, "corporate_action_successor_required"),
    ("spinoff", {"successor_security_id": ""}, "corporate_action_successor_required"),
    ("delisting", {"listing_state_after": "active"}, "delisting_state_invalid"),
    ("reactivation", {"listing_state_after": "active"}, "delisting_transition_invalid"),
])
def test_invalid_action_or_listing_transition_is_blocked(tmp_path, event_type, updates, reason):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    def mutate(rows):
        rows[0].update(event_type=event_type, **updates)
    _rewrite_csv_and_manifest(manifest, "events", mutate)
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"][event_type] = "required"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    packet = validate_point_in_time_universe(manifest, registry)
    assert reason in {
        code for decision in packet.decisions.values()
        for code in decision.reason_codes
    }


def test_present_event_marked_unsupported_is_blocked(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"]["listing"] = "unsupported"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    packet = validate_point_in_time_universe(manifest, registry)
    assert "corporate_action_policy_unsupported" in packet.decisions["corporate_action_coverage"].reason_codes
```

- [ ] **Step 2: Write failing independent rights tests**

```python
def test_technical_pass_does_not_promote_unverified_rights(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    registry.write_text(registry.read_text().replace("commercial_use: approved", "commercial_use: unverified"), encoding="utf-8")
    raw = json.loads(manifest.read_text())
    raw["source_rights_registry_sha256"] = __import__("hashlib").sha256(registry.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.decisions["technical_validity"].status == "passed"
    assert packet.decisions["source_rights_eligibility"].status == "blocked"
    assert packet.analysis_eligible is False


def test_missing_registered_delisting_scope_blocks_only_rights_state(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest, "events",
        lambda rows: rows[0].update(
            event_type="delisting", listing_state_after="delisted",
        ),
    )
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"]["listing"] = "not_applicable"
    raw["corporate_action_policy"]["delisting"] = "required"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    registry.write_text(registry.read_text().replace(", delistings", ""), encoding="utf-8")
    raw = json.loads(manifest.read_text())
    raw["source_rights_registry_sha256"] = __import__("hashlib").sha256(registry.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.decisions["technical_validity"].status == "passed"
    assert "source_rights_field_scope_missing" in packet.decisions["source_rights_eligibility"].reason_codes
```

- [ ] **Step 3: Run focused tests and observe RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe.py -q
```

Expected: new assertions fail because the three independent decisions are absent.

- [ ] **Step 4: Implement actions, delistings, and rights composition**

Add these exact helpers:

```python
def _event_decisions(manifest, parsed) -> tuple[Decision, Decision, tuple[ExcludedRow, ...]]:
    action_reasons: set[str] = set()
    delisting_reasons: set[str] = set()
    excluded: list[ExcludedRow] = []
    events_by_type: dict[str, list] = {}
    for event in parsed.events:
        events_by_type.setdefault(event.event_type, []).append(event)
        reasons: set[str] = set()
        policy = manifest.corporate_action_policy.get(event.event_type)
        if policy == "unsupported":
            reasons.add("corporate_action_policy_unsupported")
        if event.event_type in {"split", "reverse_split"} and (
            event.ratio_numerator is None or event.ratio_denominator is None
        ):
            reasons.add("corporate_action_ratio_required")
        if event.event_type in {"merger", "acquisition", "spinoff"} and not event.successor_security_id:
            reasons.add("corporate_action_successor_required")
        if event.event_type == "delisting" and event.listing_state_after != "delisted":
            reasons.add("delisting_state_invalid")
        if event.event_type == "suspension" and event.listing_state_after != "suspended":
            reasons.add("delisting_transition_invalid")
        if event.event_type == "reactivation":
            prior_suspension = any(
                prior.security_id == event.security_id
                and prior.event_type == "suspension"
                and prior.effective_at < event.effective_at
                for prior in parsed.events
            )
            if event.listing_state_after != "active" or not prior_suspension:
                reasons.add("delisting_transition_invalid")
        if reasons:
            target = delisting_reasons if event.event_type in {"delisting", "suspension", "reactivation"} else action_reasons
            target.update(reasons)
            source_row = next(
                (row.source_row for row in parsed.raw if row.contract == "events" and row.values.get("event_row_id") == event.event_row_id),
                0,
            )
            excluded.append(ExcludedRow("events", source_row, event.event_row_id, tuple(sorted(reasons))))
    for event_type, state in manifest.corporate_action_policy.items():
        if state == "required" and not events_by_type.get(event_type):
            if event_type == "delisting":
                delisting_reasons.add("delisting_evidence_missing")
            else:
                action_reasons.add("corporate_action_evidence_missing")
    if manifest.delisting_policy.get("retain_historical_members") is not True:
        delisting_reasons.add("delisting_survivorship_policy_invalid")
    if manifest.survivorship_policy.get("filter_by_current_listing_state") is not False:
        delisting_reasons.add("delisting_survivorship_policy_invalid")
    delisting_applicable = (
        manifest.corporate_action_policy.get("delisting") == "required"
        or any(event.event_type in {"delisting", "suspension", "reactivation"} for event in parsed.events)
    )
    return (
        Decision("corporate_action_coverage", "blocked" if action_reasons else "passed", tuple(sorted(action_reasons))),
        Decision(
            "delisting_coverage",
            "blocked" if delisting_reasons else "passed" if delisting_applicable else "not_applicable",
            tuple(sorted(delisting_reasons)),
        ),
        tuple(excluded),
    )


def _rights_decision(manifest, parsed, registry) -> Decision:
    blockers: set[str] = set()
    for source_id in sorted({row.source_id for rows in (parsed.identities, parsed.memberships, parsed.events) for row in rows}):
        if source_id not in manifest.allowed_source_ids:
            blockers.add("source_rights_source_not_allowed")
        required: set[str] = set()
        if any(row.source_id == source_id for row in parsed.identities):
            required.add("security_identity")
        if any(row.source_id == source_id for row in parsed.memberships):
            required.add("universe_membership")
        source_events = tuple(row for row in parsed.events if row.source_id == source_id)
        if any(row.event_type != "delisting" for row in source_events):
            required.add("corporate_actions")
        if any(row.event_type == "delisting" for row in source_events):
            required.add("delistings")
        review = review_commercial_field_scope(registry, source_id, tuple(sorted(required)))
        if not review.commercial_rights_approved:
            blockers.add(f"source_rights_{review.rights_status}")
        if review.missing_supported_fields:
            blockers.add("source_rights_field_scope_missing")
    return Decision("source_rights_eligibility", "blocked" if blockers else "passed", tuple(sorted(blockers)))
```

Call `_event_decisions(package.manifest, parsed)` and
`_rights_decision(package.manifest, parsed,
load_source_rights_registry(package.registry_path))` from the packet composer,
then append their decisions and exclusions without changing the already
computed identity or membership decisions.

- [ ] **Step 5: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe.py tests/test_commercial_source_rights.py -q
git diff --check
git add -- src/point_in_time_universe.py tests/test_point_in_time_universe.py
make staged-hygiene-check
git commit -m "Enforce universe action and rights gates"
```

Expected: action, delisting, rights, and existing commercial-rights tests pass.

---

### Task 5: Evaluation Cutoffs, Leakage Safety, and Deterministic Reproduction

**Files:**
- Modify: `src/point_in_time_universe.py`
- Modify: `tests/test_point_in_time_universe.py`

**Interfaces:**
- Adds `temporal_validity`, `reproduction_ready`, and `leakage_safe`.
- Completes `analysis_eligible` as the conjunction of all applicable independent states plus one eligible benchmark and one eligible research universe.

- [ ] **Step 1: Write failing cutoff and leakage tests**

```python
import pytest


@pytest.mark.parametrize("contract,column", [
    ("security_identity", "source_published_at"),
    ("security_identity", "retrieved_at"),
    ("membership", "observation_at"),
    ("membership", "source_published_at"),
    ("membership", "retrieved_at"),
    ("events", "effective_at"),
    ("events", "source_published_at"),
    ("events", "retrieved_at"),
])
def test_post_cutoff_evidence_is_excluded_without_poisoning_independent_states(tmp_path, contract, column):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(manifest, contract, lambda rows: rows[0].update({column: "2022-01-01T00:00:00Z"}))
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.decisions["leakage_safe"].status == "blocked"
    assert any(code.startswith("leakage_") or code.startswith("cutoff_") for row in packet.excluded for code in row.reason_codes)
    assert packet.analysis_eligible is False


def test_later_revision_is_invisible_at_earlier_evaluation(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    # Add a post-evaluation membership revision that excludes sec-1.
    def mutate(rows):
        rows.append({
            **rows[0], "membership_row_id": "member-late",
            "membership_state": "excluded",
            "source_ref": "fixture://membership/late",
            "source_published_at": "2022-01-01T00:00:00Z",
            "retrieved_at": "2022-01-02T00:00:00Z",
            "supersedes_membership_row_id": rows[0]["membership_row_id"],
        })
    _rewrite_csv_and_manifest(manifest, "membership", mutate)
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.membership_digests[0].member_count == 1
```

- [ ] **Step 2: Write failing partition and reproduction tests**

```python
def test_repeated_validation_reproduces_counts_digests_and_reasons(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    first = validate_point_in_time_universe(manifest, registry)
    second = validate_point_in_time_universe(manifest, registry)
    assert first.membership_digests == second.membership_digests
    assert first.decisions == second.decisions
    assert first.excluded == second.excluded
    assert {d.universe_id: d.member_count for d in first.membership_digests} == {"bench-1": 1, "research-1": 1}


def test_partition_policy_rejects_overlap_and_post_hoc_order(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    raw["evaluation_policy"] = {
        "kind": "partitioned",
        "train": {"start": "2020-01-01T00:00:00Z", "end": "2021-01-01T00:00:00Z"},
        "validation": {"start": "2020-12-01T00:00:00Z", "end": "2021-06-01T00:00:00Z"},
        "test": {"start": "2021-06-01T00:00:00Z", "end": "2022-01-01T00:00:00Z"},
    }
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    packet = validate_point_in_time_universe(manifest, registry)
    assert "partition_overlap" in packet.decisions["leakage_safe"].reason_codes
```

- [ ] **Step 3: Run focused tests and observe RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe.py -q
```

Expected: cutoff, partition, reproduction, or final eligibility assertions fail.

- [ ] **Step 4: Implement temporal, partition, and reproduction helpers**

```python
def _temporal_decision(parsed) -> tuple[Decision, tuple[str, ...], tuple[ExcludedRow, ...]]:
    reasons: set[str] = set()
    leakage_reasons: set[str] = set()
    excluded: list[ExcludedRow] = []
    for evaluation in parsed.evaluations:
        if evaluation.available_at > evaluation.evaluation_at:
            reasons.add("cutoff_evaluation_unavailable")
            leakage_reasons.add("leakage_evaluation_available_late")
            excluded.append(ExcludedRow(
                "evaluations", 0, evaluation.evaluation_row_id,
                ("cutoff_evaluation_unavailable", "leakage_evaluation_available_late"),
            ))
        scoped = (
            (
                "security_identity", parsed.identities,
                lambda row: row.security_id,
                lambda row: max(row.source_published_at, row.retrieved_at),
                lambda row: row.identity_row_id,
            ),
            (
                "membership",
                tuple(row for row in parsed.memberships if row.universe_id == evaluation.universe_id),
                lambda row: f"{row.universe_id}:{row.security_id}",
                lambda row: max(row.observation_at, row.source_published_at, row.retrieved_at),
                lambda row: row.membership_row_id,
            ),
            (
                "events", parsed.events,
                lambda row: f"{row.security_id}:{row.event_type}",
                lambda row: max(row.effective_at, row.source_published_at, row.retrieved_at),
                lambda row: row.event_row_id,
            ),
        )
        for contract, rows, scope, available_at, row_id in scoped:
            groups: dict[str, list] = {}
            for row in rows:
                groups.setdefault(scope(row), []).append(row)
            for group in groups.values():
                if any(available_at(row) <= evaluation.evaluation_at for row in group):
                    continue
                reasons.add("cutoff_required_scope_unavailable")
                leakage_reasons.add("leakage_post_cutoff_evidence")
                for row in group:
                    source_row = next(
                        (
                            raw.source_row for raw in parsed.raw
                            if raw.contract == contract
                            and row_id(row) in raw.values.values()
                        ),
                        0,
                    )
                    excluded.append(ExcludedRow(
                        contract, source_row, row_id(row),
                        ("cutoff_required_scope_unavailable", "leakage_post_cutoff_evidence"),
                    ))
    return (
        Decision("temporal_validity", "blocked" if reasons else "passed", tuple(sorted(reasons))),
        tuple(sorted(leakage_reasons)),
        tuple(excluded),
    )


def _partition_decision(manifest, evaluations, extra_reasons=()) -> Decision:
    policy = manifest.evaluation_policy
    reasons = set(extra_reasons)
    if policy.get("kind") == "walk_forward":
        minimum = policy.get("minimum_history_count")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum <= 0:
            reasons.add("partition_minimum_history_invalid")
    elif policy.get("kind") == "partitioned":
        try:
            train_start = parse_utc(policy["train"]["start"])
            train_end = parse_utc(policy["train"]["end"])
            validation_start = parse_utc(policy["validation"]["start"])
            validation_end = parse_utc(policy["validation"]["end"])
            test_start = parse_utc(policy["test"]["start"])
            test_end = parse_utc(policy["test"]["end"])
        except (KeyError, TypeError, ValueError):
            reasons.add("partition_schema_invalid")
        else:
            if not all((
                train_start < train_end,
                validation_start < validation_end,
                test_start < test_end,
            )):
                reasons.add("partition_order_invalid")
            if train_end > validation_start or validation_end > test_start:
                reasons.add("partition_overlap")
    else:
        reasons.add("partition_policy_invalid")
    return Decision("leakage_safe", "blocked" if reasons else "passed", tuple(sorted(reasons)))


def _reproduction_decision(manifest, digests) -> Decision:
    reasons: set[str] = set()
    if manifest.reproduction_contract != "membership_count_and_sha256_at_cutoff_v1":
        reasons.add("reproduction_contract_unsupported")
    keys = [(item.universe_id, item.evaluation_at) for item in digests]
    if len(keys) != len(set(keys)):
        reasons.add("reproduction_duplicate_evaluation")
    if any(len(item.sha256) != 64 for item in digests):
        reasons.add("reproduction_digest_invalid")
    return Decision("reproduction_ready", "blocked" if reasons else "passed", tuple(sorted(reasons)))


def _final_eligibility(decisions, digests, declared_universes) -> bool:
    applicable_pass = all(decision.status in {"passed", "not_applicable"} for decision in decisions.values())
    kinds = {item["universe_id"]: item["universe_kind"] for item in declared_universes}
    eligible_ids = {digest.universe_id for digest in digests}
    return (
        applicable_pass
        and any(kinds.get(item) == "benchmark" for item in eligible_ids)
        and any(kinds.get(item) == "research_universe" for item in eligible_ids)
    )
```

Compose the final packet in this fixed decision order:

```python
DECISION_ORDER = (
    "manifest_integrity", "technical_validity", "temporal_validity",
    "identity_coverage", "membership_coverage", "corporate_action_coverage",
    "delisting_coverage", "source_rights_eligibility",
    "reproduction_ready", "leakage_safe",
)
```

Update `validate_point_in_time_universe` after identity/membership composition
with these exact calls:

```python
decisions["manifest_integrity"] = Decision("manifest_integrity", "passed", ())
temporal, cutoff_leakage, temporal_excluded = _temporal_decision(parsed)
decisions[temporal.area] = temporal
excluded.extend(temporal_excluded)
action, delisting, event_excluded = _event_decisions(package.manifest, parsed)
decisions[action.area] = action
decisions[delisting.area] = delisting
excluded.extend(event_excluded)
registry = load_source_rights_registry(package.registry_path)
rights = _rights_decision(package.manifest, parsed, registry)
decisions[rights.area] = rights
reproduction = _reproduction_decision(package.manifest, digests)
decisions[reproduction.area] = reproduction
leakage = _partition_decision(
    package.manifest, parsed.evaluations, cutoff_leakage,
)
decisions[leakage.area] = leakage
ordered_decisions = MappingProxyType({
    name: decisions[name] for name in DECISION_ORDER
})
analysis_eligible = _final_eligibility(
    ordered_decisions, digests, package.manifest.declared_universes,
)
```

Pass `ordered_decisions` and `analysis_eligible` into the final packet. A
missing decision key is an implementation error and must fail tests rather
than be defaulted to passed.

- [ ] **Step 5: Add empty, all-excluded, missing-benchmark, and missing-research-universe tests**

```python
@pytest.mark.parametrize("mutation,reason", [
    ("no_evaluations", "membership_no_evaluation"),
    ("benchmark_only", "membership_research_universe_missing"),
    ("research_only", "membership_benchmark_missing"),
    ("all_excluded", "membership_no_eligible_members"),
])
def test_empty_or_one_sided_packages_fail_closed(tmp_path, mutation, reason):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    mutate_package_for_empty_case(manifest, mutation)
    packet = validate_point_in_time_universe(manifest, registry)
    assert packet.analysis_eligible is False
    assert reason in {code for decision in packet.decisions.values() for code in decision.reason_codes}
```

Add these exact test helpers above the parametrized test:

```python
def _replace_contract_rows(manifest, contract, rows):
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == contract)
    path = manifest.parent / entry["path"]
    with path.open(encoding="utf-8", newline="") as handle:
        fieldnames = next(csv.reader(handle))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    entry["sha256"] = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    entry["row_count"] = len(rows)
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def _read_contract_rows(manifest, contract):
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == contract)
    with (manifest.parent / entry["path"]).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mutate_package_for_empty_case(manifest, mutation):
    memberships = _read_contract_rows(manifest, "membership")
    evaluations = _read_contract_rows(manifest, "evaluations")
    raw = json.loads(manifest.read_text())
    if mutation == "no_evaluations":
        _replace_contract_rows(manifest, "evaluations", [])
        return
    if mutation == "benchmark_only":
        memberships = [row for row in memberships if row["universe_kind"] == "benchmark"]
        evaluations = [row for row in evaluations if row["universe_id"] == "bench-1"]
        raw["declared_universes"] = [
            item for item in raw["declared_universes"]
            if item["universe_kind"] == "benchmark"
        ]
    elif mutation == "research_only":
        memberships = [row for row in memberships if row["universe_kind"] == "research_universe"]
        evaluations = [row for row in evaluations if row["universe_id"] == "research-1"]
        raw["declared_universes"] = [
            item for item in raw["declared_universes"]
            if item["universe_kind"] == "research_universe"
        ]
    elif mutation == "all_excluded":
        for row in memberships:
            row["membership_state"] = "excluded"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    _replace_contract_rows(manifest, "membership", memberships)
    _replace_contract_rows(manifest, "evaluations", evaluations)
```

- [ ] **Step 6: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe.py tests/test_point_in_time_universe_lineage.py -q
git diff --check
git add -- src/point_in_time_universe.py tests/test_point_in_time_universe.py
make staged-hygiene-check
git commit -m "Add leakage-safe universe reproduction"
```

Expected: all composed validator and lineage tests pass.

---

### Task 6: Read-Only CLI and Make Interfaces

**Files:**
- Create: `tests/test_point_in_time_universe_cli.py`
- Modify: `src/point_in_time_universe.py`
- Modify: `Makefile`

**Interfaces:**
- Produces `render_status(packet) -> str` and `render_preview(packet, top_n=20) -> str`.
- Produces `main(argv: list[str] | None = None) -> int`.
- Adds `make point-in-time-universe-status MANIFEST=<path> [REGISTRY=<path>]`.
- Adds `make point-in-time-universe-preview MANIFEST=<path> [REGISTRY=<path>] [TOP_N=20]`.

- [ ] **Step 1: Write failing CLI and Make tests**

```python
# tests/test_point_in_time_universe_cli.py
from pathlib import Path
import subprocess
import sys

from tests.point_in_time_universe_fixture import build_valid_package


def _bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_status_and_preview_are_read_only_and_truthful(tmp_path):
    manifest, registry = build_valid_package(tmp_path)
    before = _bytes(tmp_path)
    for mode in ("status", "preview"):
        result = subprocess.run(
            [sys.executable, "-m", "src.point_in_time_universe", mode,
             "--manifest", str(manifest), "--registry", str(registry), "--top-n", "5"],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        assert "Research-only" in result.stdout
        assert "does not activate readiness, backtesting, calibration, or probability" in result.stdout
        assert "analysis_eligible:" in result.stdout
    assert _bytes(tmp_path) == before


def test_invalid_invocation_is_nonzero_without_traceback():
    result = subprocess.run(
        [sys.executable, "-m", "src.point_in_time_universe", "status"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "MANIFEST is required" in result.stderr
    assert "Traceback" not in result.stderr


def test_readable_blocked_package_returns_zero_with_blocked_states(tmp_path):
    manifest, registry = build_valid_package(tmp_path)
    registry.write_text(registry.read_text().replace("commercial_use: approved", "commercial_use: unverified"), encoding="utf-8")
    raw = __import__("json").loads(manifest.read_text())
    raw["source_rights_registry_sha256"] = __import__("hashlib").sha256(registry.read_bytes()).hexdigest()
    manifest.write_text(__import__("json").dumps(raw), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "src.point_in_time_universe", "status",
         "--manifest", str(manifest), "--registry", str(registry)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "source_rights_eligibility: blocked" in result.stdout
```

- [ ] **Step 2: Run CLI tests and observe RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_point_in_time_universe_cli.py -q
```

Expected: CLI and Make assertions fail because rendering and targets are absent.

- [ ] **Step 3: Implement rendering and CLI**

```python
def render_status(packet: PointInTimeUniversePacket) -> str:
    lines = [
        "Point-in-Time Universe Status",
        "Read-only: validates one supplied immutable package; it does not fetch, write, apply, refresh, or rebuild data.",
        "Research-only: this does not activate readiness, backtesting, calibration, or probability and is not investment advice.",
        f"dataset_id: {packet.dataset_id}",
        f"manifest_id: {packet.manifest_id}",
        f"analysis_eligible: {str(packet.analysis_eligible).lower()}",
    ]
    lines.extend(
        f"{name}: {packet.decisions[name].status}; reasons={','.join(packet.decisions[name].reason_codes) or 'none'}"
        for name in DECISION_ORDER
    )
    lines.append(f"boundary: {packet.boundary}")
    return "\n".join(lines)


def render_preview(packet: PointInTimeUniversePacket, *, top_n: int = 20) -> str:
    lines = [render_status(packet), "", "Membership reproduction:"]
    lines.extend(
        f"- {item.universe_id} @ {item.evaluation_at}: members={item.member_count}; sha256={item.sha256}"
        for item in packet.membership_digests
    )
    lines.append("Excluded sample:")
    lines.extend(
        f"- {item.contract}:{item.source_row}:{item.row_id}; reasons={','.join(item.reason_codes)}"
        for item in packet.excluded[:top_n]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Validate one immutable point-in-time universe package.")
    parser.add_argument("mode", choices=("status", "preview"))
    parser.add_argument("--manifest")
    parser.add_argument("--registry", default="config/source_rights.yml")
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args(argv)
    if not args.manifest:
        parser.error("MANIFEST is required")
    try:
        packet = validate_point_in_time_universe(Path(args.manifest), Path(args.registry), top_n=args.top_n)
    except ValueError as exc:
        parser.error(str(exc))
    print(render_preview(packet, top_n=args.top_n) if args.mode == "preview" else render_status(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add exact Make targets**

```make
.PHONY: point-in-time-universe-status point-in-time-universe-preview

point-in-time-universe-status:
	@test -n "$(MANIFEST)" || (echo "MANIFEST is required" >&2; exit 2)
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.point_in_time_universe status \
		--manifest "$(MANIFEST)" \
		--registry "$(or $(REGISTRY),config/source_rights.yml)" \
		--top-n "$(or $(TOP_N),20)"

point-in-time-universe-preview:
	@test -n "$(MANIFEST)" || (echo "MANIFEST is required" >&2; exit 2)
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.point_in_time_universe preview \
		--manifest "$(MANIFEST)" \
		--registry "$(or $(REGISTRY),config/source_rights.yml)" \
		--top-n "$(or $(TOP_N),20)"
```

Add both names to the top-level `.PHONY` declaration and help output. Do not
add stage, apply, record, refresh, or output parameters.

- [ ] **Step 5: Add Make no-write test**

```python
def test_make_status_and_preview_use_exact_read_only_contract(tmp_path):
    manifest, registry = build_valid_package(tmp_path)
    before = _bytes(tmp_path)
    for target in ("point-in-time-universe-status", "point-in-time-universe-preview"):
        result = subprocess.run(
            ["make", "--no-print-directory", target, f"MANIFEST={manifest}",
             f"REGISTRY={registry}", "TOP_N=5"],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        assert "Read-only" in result.stdout
    assert _bytes(tmp_path) == before
```

- [ ] **Step 6: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_point_in_time_universe_cli.py \
  tests/test_point_in_time_universe.py \
  tests/test_makefile_test_targets.py -q
git diff --check
git add -- Makefile src/point_in_time_universe.py tests/test_point_in_time_universe_cli.py
make staged-hygiene-check
git commit -m "Add read-only universe validation commands"
```

Expected: CLI, Make, composed validator, and existing Make target tests pass.

---

### Task 7: Full Acceptance Matrix and No-Write Proof

**Files:**
- Modify: `tests/test_point_in_time_universe_manifest.py`
- Modify: `tests/test_point_in_time_universe_contracts.py`
- Modify: `tests/test_point_in_time_universe_lineage.py`
- Modify: `tests/test_point_in_time_universe.py`
- Modify: `tests/test_point_in_time_universe_cli.py`

**Interfaces:**
- No new production interface.
- Completes every test group named in the approved specification.

- [ ] **Step 1: Add the complete stable reason-code matrix**

```python
EXPECTED_REASON_PREFIXES = {
    "manifest_", "schema_", "lineage_", "identity_", "membership_",
    "corporate_action_", "delisting_", "source_rights_", "cutoff_",
    "leakage_", "partition_", "reproduction_",
}


def test_every_exclusion_uses_an_approved_stable_reason_family(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(manifest, "membership", lambda rows: rows[0].update(retrieved_at="2022-01-01T00:00:00Z"))
    packet = validate_point_in_time_universe(manifest, registry)
    for item in packet.excluded:
        for code in item.reason_codes:
            assert any(code.startswith(prefix) for prefix in EXPECTED_REASON_PREFIXES)
```

- [ ] **Step 2: Add the whole-root no-write test**

```python
def test_library_cli_and_make_leave_entire_root_byte_identical(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    before = _bytes(tmp_path)
    validate_point_in_time_universe(manifest, registry)
    subprocess.run(
        [sys.executable, "-m", "src.point_in_time_universe", "preview",
         "--manifest", str(manifest), "--registry", str(registry)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["make", "--no-print-directory", "point-in-time-universe-preview",
         f"MANIFEST={manifest}", f"REGISTRY={registry}"],
        check=True, capture_output=True, text=True,
    )
    assert _bytes(tmp_path) == before
```

- [ ] **Step 3: Add explicit no-current-universe dependency test**

```python
def test_validator_result_is_unchanged_when_current_universe_files_change(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    first = validate_point_in_time_universe(manifest, registry)
    data = tmp_path / "data"
    data.mkdir()
    (data / "universe.csv").write_text("ticker\nZZZ\n", encoding="utf-8")
    (data / "universe_master.csv").write_text("ticker,is_active_listing\nAAA,false\n", encoding="utf-8")
    second = validate_point_in_time_universe(manifest, registry)
    assert first == second
```

- [ ] **Step 4: Add test-only and no-completion assertions**

```python
def test_synthetic_package_never_claims_priority_four_completion(tmp_path):
    from src.point_in_time_universe import render_status, validate_point_in_time_universe
    manifest, registry = build_valid_package(tmp_path)
    output = render_status(validate_point_in_time_universe(manifest, registry))
    assert "Priority 4 complete" not in output
    assert "real permitted dataset" in output
    assert "synthetic" in output.lower()
```

Update `render_status` boundary text so it explicitly says a synthetic or
technically valid package is local software evidence only and Priority 4 still
requires one independently reviewed permitted real dataset.

- [ ] **Step 5: Run all focused tests and fix only proven gaps**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_point_in_time_universe_manifest.py \
  tests/test_point_in_time_universe_contracts.py \
  tests/test_point_in_time_universe_lineage.py \
  tests/test_point_in_time_universe.py \
  tests/test_point_in_time_universe_cli.py \
  tests/test_commercial_source_rights.py \
  tests/test_makefile_test_targets.py -q
```

Expected: all focused tests pass. If a test fails, use
`superpowers:systematic-debugging`; do not weaken the assertion to match an
unsafe implementation.

- [ ] **Step 6: Commit the acceptance hardening**

```bash
git diff --check
git add -- src/point_in_time_universe.py tests/test_point_in_time_universe_manifest.py tests/test_point_in_time_universe_contracts.py tests/test_point_in_time_universe_lineage.py tests/test_point_in_time_universe.py tests/test_point_in_time_universe_cli.py
make staged-hygiene-check
git commit -m "Complete universe foundation acceptance matrix"
```

Expected: only Python product/test files are staged; generated artifacts are `0`.

---

### Task 8: Documentation, Release Gates, PR, and Exact-Head CI

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Records local implementation truth and exact external exit condition.
- Does not change public product claims or call Priority 4 complete.

- [ ] **Step 1: Write failing documentation-contract test**

```python
def test_priority_four_local_validator_is_documented_without_claiming_real_data_completion():
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")
    for text in (roadmap, methodology, prompt):
        assert "make point-in-time-universe-status MANIFEST=<path>" in text
        assert "make point-in-time-universe-preview MANIFEST=<path> TOP_N=20" in text
        assert "membership_count_and_sha256_at_cutoff_v1" in text
        assert "Synthetic fixtures remain test-only" in text
        assert "one bounded permitted real dataset" in text
    assert "Priority 4 is complete" not in roadmap
```

- [ ] **Step 2: Run the documentation test and observe RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_public_v1_release_docs.py::test_priority_four_local_validator_is_documented_without_claiming_real_data_completion -q
```

Expected: fails because implementation evidence is not yet recorded in all three documents.

- [ ] **Step 3: Update documentation with exact boundaries**

Add these facts to all required documents:

```text
Implemented locally: read-only immutable package status/preview with independent
manifest, technical, temporal, identity, membership, corporate-action,
delisting, source-rights, reproduction, and leakage states.

Reproduction contract: membership_count_and_sha256_at_cutoff_v1.

Synthetic fixtures remain test-only. Priority 4 remains incomplete until one
bounded permitted real dataset reproduces the independently reviewed expected
membership count and digest and passes rights, identity, corporate-action,
delisting, survivorship, cutoff, and leakage gates.
```

Document only the two read-only commands. Do not document an apply, record,
refresh, readiness, or broad-source command.

- [ ] **Step 4: Run focused and full verification**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_point_in_time_universe_manifest.py \
  tests/test_point_in_time_universe_contracts.py \
  tests/test_point_in_time_universe_lineage.py \
  tests/test_point_in_time_universe.py \
  tests/test_point_in_time_universe_cli.py \
  tests/test_public_v1_release_docs.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected:

- focused tests pass;
- full suite passes;
- dashboard and all six Personal Research routes pass;
- public and commercial-beta gates pass;
- pilot is `pilot-ready with manual gates` after commit;
- diff hygiene lists only intentional product files plus the 18 excluded generated files.

- [ ] **Step 5: Stage exact files and verify hygiene**

```bash
git add -- ROADMAP.md docs/METHODOLOGY.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
```

Expected: staged generated CSV/JSON/report churn is `0`.

- [ ] **Step 6: Commit documentation**

```bash
git commit -m "Document point-in-time universe validator"
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: no product candidate remains; 18 generated files remain local and unstaged.

- [ ] **Step 7: Push only the approved branch**

```bash
git status --short --branch
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
git push origin codex/personal-research-mode-mvp
```

Expected: push succeeds only to `codex/personal-research-mode-mvp`.

- [ ] **Step 8: Update draft PR #113 and require exact-head CI**

Use the PR comment to report:

```text
Priority 4 local validator implemented:
- immutable manifest and file integrity
- stable identity and timestamped membership
- corporate-action and delisting policy
- exact-source rights and registered field scope
- cutoff/leakage and deterministic membership digest
- status/preview only; no write/apply/readiness activation
- synthetic fixtures test-only; real dataset gate remains open
- focused/full/release/hygiene evidence
```

Then:

```bash
gh pr view 113 --repo YuzeJ21/Stock-Analysis --json state,isDraft,mergeable,headRefOid,statusCheckRollup
gh run list --repo YuzeJ21/Stock-Analysis --branch codex/personal-research-mode-mvp --event pull_request --limit 5
gh run watch <exact-head-run-id> --repo YuzeJ21/Stock-Analysis --exit-status
git fetch origin codex/personal-research-mode-mvp
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
```

Expected:

- PR #113 remains open and draft;
- exact-head `Commercial Research Beta / local-engineering-gate` succeeds;
- branch divergence is `0 0`;
- no merge or deployment occurs.

---

## Plan Completion Audit

Before calling the local implementation slice complete, verify each approved
spec requirement against direct evidence:

| Requirement | Direct evidence |
| --- | --- |
| Immutable package identity | Manifest hash, row-count, registry-digest, path, and schema tests |
| Stable security identity | Ticker-change, ticker-reuse, overlap, and missing-identity tests |
| Historical membership | Complete-snapshot/event-history, effective interval, declared universe, and kind tests |
| Revision lineage | Duplicate, parent, scope, root, fork, cycle, order, and cutoff tests |
| Corporate actions | Split ratio, successor, policy, suspension/reactivation tests |
| Delistings/survivorship | Explicit delisting state and historical-member retention tests |
| Source rights | Approved/unverified/unknown/missing-scope independent-state tests |
| Cutoff/leakage | Publication, retrieval, observation, event, evaluation, and later-revision tests |
| Reproduction | Repeated count/digest/state/exclusion equality tests |
| Raw/normalized/excluded/eligible | Packet counts, exclusions, reason families, and eligibility tests |
| Read-only operation | Whole-root byte snapshots across library, CLI, and Make |
| No current fallback | Result unchanged after current universe files are created or changed |
| Synthetic test-only boundary | Rendered boundary and documentation tests |
| Release safety | Focused/full/release/hygiene/exact-head CI |
| Real-data exit gate remains open | ROADMAP, methodology, prompt, PR, and rendered boundary |

Do not mark Priority 4 complete unless one independently reviewed permitted
real dataset later passes every applicable gate and reproduces the expected
membership count and digest. Completing this plan proves only the local
validator implementation.
