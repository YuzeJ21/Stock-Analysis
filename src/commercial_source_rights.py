"""Fail-closed source-rights registry for Commercial Research mode."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import yaml


REQUIRED_FIELDS = (
    "source_id",
    "display_name",
    "permitted_use",
    "commercial_use",
    "redistribution",
    "storage_limits",
    "attribution",
    "rate_limits",
    "authentication",
    "expected_freshness",
    "supported_fields",
    "fallback_priority",
)
APPROVED_COMMERCIAL_USE = "approved"
COMMERCIAL_RESEARCH_MODE_ENV = "COMMERCIAL_RESEARCH_MODE"
_COMMERCIAL_MODE_ENABLED_VALUES = frozenset({"1", "true", "yes", "on", "commercial"})
_COMMERCIAL_MODE_DISABLED_VALUES = frozenset({"", "0", "false", "no", "off", "research"})
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "config" / "source_rights.yml"


@dataclass(frozen=True)
class SourceRights:
    source_id: str
    display_name: str
    permitted_use: str
    commercial_use: str
    redistribution: str
    storage_limits: str
    attribution: str
    rate_limits: str
    authentication: str
    expected_freshness: str
    supported_fields: tuple[str, ...]
    fallback_priority: int


@dataclass(frozen=True)
class CommercialEligibility:
    source_id: str
    allowed: bool
    status: str
    reason: str


@dataclass(frozen=True)
class CommercialFieldScopeReview:
    source_id: str
    rights_status: str
    commercial_rights_approved: bool
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    commercial_evidence_ready: bool


def _missing_fields(record: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)
    return missing


def _source_rights_from_record(record: Mapping[str, Any]) -> SourceRights:
    missing = _missing_fields(record)
    if missing:
        raise ValueError(f"source rights record missing required fields: {', '.join(missing)}")

    supported_fields = record["supported_fields"]
    if not isinstance(supported_fields, list) or not all(isinstance(field, str) and field.strip() for field in supported_fields):
        raise ValueError("source rights record supported_fields must be a non-empty list of strings")
    fallback_priority = record["fallback_priority"]
    if isinstance(fallback_priority, bool) or not isinstance(fallback_priority, int):
        raise ValueError("source rights record fallback_priority must be an integer")

    text_fields = set(REQUIRED_FIELDS) - {"supported_fields", "fallback_priority"}
    if any(not isinstance(record[field], str) or not record[field].strip() for field in text_fields):
        raise ValueError("source rights record text fields must be non-empty strings")

    return SourceRights(
        source_id=record["source_id"].strip(),
        display_name=record["display_name"].strip(),
        permitted_use=record["permitted_use"].strip(),
        commercial_use=record["commercial_use"].strip(),
        redistribution=record["redistribution"].strip(),
        storage_limits=record["storage_limits"].strip(),
        attribution=record["attribution"].strip(),
        rate_limits=record["rate_limits"].strip(),
        authentication=record["authentication"].strip(),
        expected_freshness=record["expected_freshness"].strip(),
        supported_fields=tuple(field.strip() for field in supported_fields),
        fallback_priority=fallback_priority,
    )


def build_source_rights_registry(records: Sequence[Mapping[str, Any]]) -> Mapping[str, SourceRights]:
    """Validate source-rights records and return an immutable source-id registry."""

    registry: dict[str, SourceRights] = {}
    for raw_record in records:
        if not isinstance(raw_record, Mapping):
            raise ValueError("source rights records must be mappings")
        record = _source_rights_from_record(raw_record)
        if record.source_id in registry:
            raise ValueError(f"duplicate source rights record: {record.source_id}")
        registry[record.source_id] = record
    if not registry:
        raise ValueError("source rights registry must contain at least one record")
    return MappingProxyType(registry)


def parse_source_rights_registry(snapshot: bytes) -> Mapping[str, SourceRights]:
    """Build an immutable source-rights registry from one verified byte snapshot."""

    try:
        raw = yaml.safe_load(snapshot.decode("utf-8")) or {}
    except (
        UnicodeDecodeError,
        yaml.YAMLError,
        RecursionError,
    ) as exc:
        raise ValueError("source_rights_registry_unreadable") from exc
    if not isinstance(raw, Mapping) or not isinstance(raw.get("sources"), list):
        raise ValueError("source rights registry must contain a sources list")
    return build_source_rights_registry(raw["sources"])


def load_source_rights_registry(path: Path | str = DEFAULT_REGISTRY_PATH) -> Mapping[str, SourceRights]:
    """Load the checked-in registry without reading credentials or license documents."""

    registry_path = Path(path)
    try:
        snapshot = registry_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read source rights registry: {registry_path}") from exc
    return parse_source_rights_registry(snapshot)


def commercial_eligibility(
    registry: Mapping[str, SourceRights], source_id: str,
) -> CommercialEligibility:
    """Return the fail-closed commercial-mode decision for one registered source."""

    normalized_source_id = str(source_id or "").strip()
    record = registry.get(normalized_source_id)
    if record is None:
        return CommercialEligibility(
            source_id=normalized_source_id,
            allowed=False,
            status="unknown_source",
            reason="Commercial mode requires a registered source with explicitly approved commercial rights.",
        )
    if record.commercial_use != APPROVED_COMMERCIAL_USE:
        return CommercialEligibility(
            source_id=record.source_id,
            allowed=False,
            status="commercial_rights_unverified",
            reason="Commercial mode refuses sources whose commercial rights are not explicitly approved.",
        )
    return CommercialEligibility(
        source_id=record.source_id,
        allowed=True,
        status="approved",
        reason="Commercial rights are explicitly approved in the checked-in registry.",
    )


def review_commercial_field_scope(
    registry: Mapping[str, SourceRights],
    source_id: str,
    required_fields: Sequence[str],
) -> CommercialFieldScopeReview:
    """Review exact-source rights and registered field scope without fetching data."""

    normalized_source_id = str(source_id or "").strip()
    normalized_fields = tuple(str(field or "").strip() for field in required_fields)
    if any(not field for field in normalized_fields) or len(set(normalized_fields)) != len(
        normalized_fields
    ):
        raise ValueError("required fields must be non-empty unique strings")

    rights = commercial_eligibility(registry, normalized_source_id)
    record = registry.get(normalized_source_id)
    supported_fields = set(record.supported_fields) if record is not None else set()
    missing_fields = tuple(
        field for field in normalized_fields if field not in supported_fields
    )
    return CommercialFieldScopeReview(
        source_id=normalized_source_id,
        rights_status=rights.status,
        commercial_rights_approved=rights.allowed,
        required_supported_fields=normalized_fields,
        missing_supported_fields=missing_fields,
        commercial_evidence_ready=rights.allowed and not missing_fields,
    )


def commercial_mode_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether the explicit commercial-mode environment gate is enabled."""

    value = (environ or os.environ).get(COMMERCIAL_RESEARCH_MODE_ENV, "").strip().lower()
    if value in _COMMERCIAL_MODE_ENABLED_VALUES:
        return True
    if value in _COMMERCIAL_MODE_DISABLED_VALUES:
        return False
    raise ValueError(
        f"{COMMERCIAL_RESEARCH_MODE_ENV} must be one of "
        "1, true, yes, on, commercial, 0, false, no, off, or research."
    )


def enforce_commercial_source_rights(source_id: str) -> None:
    """Block unapproved sources before provider code executes in explicit commercial mode."""

    if not commercial_mode_enabled():
        return

    decision = commercial_eligibility(load_source_rights_registry(), source_id)
    if not decision.allowed:
        raise RuntimeError(
            f"{decision.source_id or source_id}: commercial rights are not explicitly approved "
            f"for this source ({decision.status})."
        )


def render_source_rights_status(
    registry: Mapping[str, SourceRights], source_id: str | None = None,
) -> str:
    """Render registry status without fetching data, changing configuration, or exposing credentials."""

    if source_id is not None:
        decision = commercial_eligibility(registry, source_id)
        return "\n".join(
            [
                "Commercial Source Rights",
                "Read-only: this command does not fetch data, change rights, or expose credentials.",
                f"source_id: {decision.source_id or '-'}",
                f"commercial_mode_allowed: {str(decision.allowed).lower()}",
                f"status: {decision.status}",
                f"reason: {decision.reason}",
            ]
        )

    lines = [
        "Commercial Source Rights",
        "Read-only: this command does not fetch data, change rights, or expose credentials.",
    ]
    for record in sorted(registry.values(), key=lambda item: item.fallback_priority):
        decision = commercial_eligibility(registry, record.source_id)
        lines.append(
            f"- {record.source_id}: {decision.status}; commercial_mode_allowed={str(decision.allowed).lower()}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the read-only commercial source-rights status.")
    parser.add_argument("--config", type=Path, default=DEFAULT_REGISTRY_PATH, help="Source-rights YAML path.")
    parser.add_argument("--source", help="Optional source id to evaluate in commercial mode.")
    args = parser.parse_args(argv)
    registry = load_source_rights_registry(args.config)
    print(render_source_rights_status(registry, args.source))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
