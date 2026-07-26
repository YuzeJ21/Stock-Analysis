from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping

from src.point_in_time_universe_identifiers import require_control_free
from src.point_in_time_universe_manifest import (
    RFC3339_UTC,
    LoadedUniversePackage,
)


EVENT_TYPES = frozenset({
    "listing", "ticker_change", "exchange_change", "split", "reverse_split", "merger",
    "acquisition", "spinoff", "delisting", "suspension", "reactivation",
})
LISTING_STATES = frozenset({"", "active", "delisted", "suspended"})
PARTITIONS = frozenset({"train", "validation", "test", "walk_forward"})
RAW_MISSING_CELL = "__missing_csv_cell__"
RAW_SURPLUS_CELL_PREFIX = "__surplus_cell_"


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
    identity_row_id: str
    security_id: str
    issuer_id: str
    ticker: str
    exchange: str
    security_type: str
    currency: str
    valid_from: datetime
    valid_to: datetime | None
    source_id: str
    source_ref: str
    source_published_at: datetime
    retrieved_at: datetime
    supersedes_identity_row_id: str


@dataclass(frozen=True)
class MembershipObservation:
    membership_row_id: str
    universe_id: str
    universe_kind: str
    security_id: str
    membership_state: str
    effective_from: datetime
    effective_to: datetime | None
    observation_at: datetime
    source_id: str
    source_ref: str
    source_published_at: datetime
    retrieved_at: datetime
    supersedes_membership_row_id: str


@dataclass(frozen=True)
class UniverseEvent:
    event_row_id: str
    security_id: str
    event_type: str
    effective_at: datetime
    successor_security_id: str
    ratio_numerator: float | None
    ratio_denominator: float | None
    listing_state_after: str
    source_id: str
    source_ref: str
    source_published_at: datetime
    retrieved_at: datetime
    supersedes_event_row_id: str


@dataclass(frozen=True)
class EvaluationObservation:
    evaluation_row_id: str
    universe_id: str
    evaluation_at: datetime
    available_at: datetime
    partition: str
    source_ref: str


@dataclass(frozen=True)
class ParsedUniverseEvidence:
    raw: tuple[RawEvidenceRow, ...]
    identities: tuple[IdentityObservation, ...]
    memberships: tuple[MembershipObservation, ...]
    events: tuple[UniverseEvent, ...]
    evaluations: tuple[EvaluationObservation, ...]
    findings: tuple[ContractFinding, ...]


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not RFC3339_UTC.fullmatch(value):
        raise ValueError("schema_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("schema_timestamp_invalid") from exc
    if parsed.tzinfo != timezone.utc:
        raise ValueError("schema_timestamp_invalid")
    return parsed


def optional_utc(value: str) -> datetime | None:
    return None if value == "" else parse_utc(value)


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
    "source_ref", "source_published_at", "retrieved_at", "supersedes_identity_row_id",
)
MEMBERSHIP_COLUMNS = (
    "membership_row_id", "universe_id", "universe_kind", "security_id",
    "membership_state", "effective_from", "effective_to", "observation_at",
    "source_id", "source_ref", "source_published_at", "retrieved_at",
    "supersedes_membership_row_id",
)
EVENT_COLUMNS = (
    "event_row_id", "security_id", "event_type", "effective_at", "successor_security_id",
    "ratio_numerator", "ratio_denominator", "listing_state_after", "source_id",
    "source_ref", "source_published_at", "retrieved_at", "supersedes_event_row_id",
)
EVALUATION_COLUMNS = (
    "evaluation_row_id", "universe_id", "evaluation_at", "available_at", "partition",
    "source_ref",
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
STRUCTURAL_IDENTIFIER_FIELDS = frozenset({
    "identity_row_id",
    "security_id",
    "issuer_id",
    "ticker",
    "exchange",
    "security_type",
    "currency",
    "source_id",
    "source_ref",
    "supersedes_identity_row_id",
    "membership_row_id",
    "universe_id",
    "universe_kind",
    "membership_state",
    "supersedes_membership_row_id",
    "event_row_id",
    "event_type",
    "successor_security_id",
    "listing_state_after",
    "supersedes_event_row_id",
    "evaluation_row_id",
    "partition",
})


def _required(
    row: Mapping[str, str],
    *names: str,
    display_normalized: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    values = tuple(row.get(name, "") for name in names)
    for name, value in zip(names, values, strict=True):
        if not value or (name in display_normalized and not value.strip()):
            raise ValueError("schema_required_field_missing")
        if name not in display_normalized and value != value.strip():
            raise ValueError("schema_whitespace_invalid")
        if name in STRUCTURAL_IDENTIFIER_FIELDS:
            require_control_free(
                value,
                "schema_identifier_control_character",
            )
    return values


def _optional_opaque(row: Mapping[str, str], name: str) -> str:
    value = row[name]
    if value and value != value.strip():
        raise ValueError("schema_whitespace_invalid")
    require_control_free(
        value,
        "schema_identifier_control_character",
    )
    return value


def _has_exact_row_shape(values: Mapping[object, object], columns: tuple[str, ...]) -> bool:
    return (
        tuple(values) == columns
        and all(isinstance(key, str) and isinstance(values[key], str) for key in columns)
    )


def _raw_values(values: Mapping[object, object], columns: tuple[str, ...]) -> Mapping[str, str]:
    raw = {
        column: values[column] if isinstance(values.get(column), str) else RAW_MISSING_CELL
        for column in columns
    }
    surplus = values.get(None, ())
    if isinstance(surplus, list):
        for index, value in enumerate(surplus):
            key = f"{RAW_SURPLUS_CELL_PREFIX}{index}__"
            while key in raw:
                key = f"_{key}"
            raw[key] = value if isinstance(value, str) else RAW_MISSING_CELL
    return MappingProxyType(raw)


def _require_publication_before_retrieval(
    source_published_at: datetime,
    retrieved_at: datetime,
) -> None:
    if retrieved_at < source_published_at:
        raise ValueError("schema_retrieved_before_publication")


def _parse_identity(row: Mapping[str, str]) -> IdentityObservation:
    required = _required(
        row, "identity_row_id", "security_id", "issuer_id", "ticker", "exchange",
        "security_type", "currency", "valid_from", "source_id", "source_ref",
        "source_published_at", "retrieved_at",
        display_normalized=frozenset({"ticker"}),
    )
    if required[1] == required[2]:
        raise ValueError("schema_identity_issuer_matches_security")
    observation = IdentityObservation(
        identity_row_id=required[0], security_id=required[1], issuer_id=required[2],
        ticker=required[3].strip().upper(), exchange=required[4], security_type=required[5],
        currency=required[6], valid_from=parse_utc(required[7]),
        valid_to=optional_utc(row["valid_to"]), source_id=required[8], source_ref=required[9],
        source_published_at=parse_utc(required[10]), retrieved_at=parse_utc(required[11]),
        supersedes_identity_row_id=_optional_opaque(row, "supersedes_identity_row_id"),
    )
    if (
        observation.valid_to is not None
        and observation.valid_to <= observation.valid_from
    ):
        raise ValueError("schema_identity_interval_reversed")
    _require_publication_before_retrieval(
        observation.source_published_at,
        observation.retrieved_at,
    )
    return observation


def _parse_membership(row: Mapping[str, str]) -> MembershipObservation:
    required = _required(
        row, "membership_row_id", "universe_id", "universe_kind", "security_id",
        "membership_state", "effective_from", "observation_at", "source_id", "source_ref",
        "source_published_at", "retrieved_at",
    )
    if required[2] not in {"benchmark", "research_universe"}:
        raise ValueError("schema_enum_invalid")
    if required[4] not in {"included", "excluded"}:
        raise ValueError("schema_enum_invalid")
    observation = MembershipObservation(
        membership_row_id=required[0], universe_id=required[1], universe_kind=required[2],
        security_id=required[3], membership_state=required[4],
        effective_from=parse_utc(required[5]), effective_to=optional_utc(row["effective_to"]),
        observation_at=parse_utc(required[6]), source_id=required[7], source_ref=required[8],
        source_published_at=parse_utc(required[9]), retrieved_at=parse_utc(required[10]),
        supersedes_membership_row_id=_optional_opaque(row, "supersedes_membership_row_id"),
    )
    if (
        observation.effective_to is not None
        and observation.effective_to <= observation.effective_from
    ):
        raise ValueError("schema_membership_interval_reversed")
    _require_publication_before_retrieval(
        observation.source_published_at,
        observation.retrieved_at,
    )
    return observation


def _parse_event(row: Mapping[str, str]) -> UniverseEvent:
    required = _required(
        row, "event_row_id", "security_id", "event_type", "effective_at", "source_id",
        "source_ref", "source_published_at", "retrieved_at",
    )
    listing_state_after = require_control_free(
        row["listing_state_after"],
        "schema_identifier_control_character",
    )
    if required[2] not in EVENT_TYPES or listing_state_after not in LISTING_STATES:
        raise ValueError("schema_enum_invalid")
    try:
        numerator = optional_positive_float(row["ratio_numerator"])
        denominator = optional_positive_float(row["ratio_denominator"])
    except (TypeError, ValueError) as exc:
        raise ValueError("schema_ratio_invalid") from exc
    if (numerator is None) != (denominator is None):
        raise ValueError("schema_ratio_pair_required")
    if required[2] in {"split", "reverse_split"} and numerator is None:
        raise ValueError("schema_ratio_pair_required")
    if required[2] == "delisting" and listing_state_after != "delisted":
        raise ValueError("schema_delisting_listing_state_invalid")
    observation = UniverseEvent(
        event_row_id=required[0], security_id=required[1], event_type=required[2],
        effective_at=parse_utc(required[3]),
        successor_security_id=_optional_opaque(row, "successor_security_id"), ratio_numerator=numerator,
        ratio_denominator=denominator, listing_state_after=listing_state_after,
        source_id=required[4], source_ref=required[5],
        source_published_at=parse_utc(required[6]), retrieved_at=parse_utc(required[7]),
        supersedes_event_row_id=_optional_opaque(row, "supersedes_event_row_id"),
    )
    _require_publication_before_retrieval(
        observation.source_published_at,
        observation.retrieved_at,
    )
    return observation


def _parse_evaluation(row: Mapping[str, str]) -> EvaluationObservation:
    required = _required(
        row, "evaluation_row_id", "universe_id", "evaluation_at", "available_at", "partition",
        "source_ref",
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
        snapshot = package.contract_snapshots[contract]
        with io.StringIO(snapshot.decode("utf-8"), newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != COLUMNS[contract]:
                raise ValueError("package_csv_columns_invalid")
            for source_row, values in enumerate(reader, start=2):
                clean = _raw_values(values, COLUMNS[contract])
                raw_rows.append(RawEvidenceRow(
                    contract,
                    path.relative_to(package.manifest_path.parent).as_posix(),
                    source_row,
                    clean,
                ))
                row_id = clean.get(ROW_ID_FIELDS[contract], "")
                if not _has_exact_row_shape(values, COLUMNS[contract]):
                    findings.append(ContractFinding(
                        contract,
                        source_row,
                        row_id,
                        ("schema_columns_invalid",),
                    ))
                    continue
                try:
                    parsed[contract].append(PARSERS[contract](clean))
                except (KeyError, TypeError, ValueError) as exc:
                    reason = str(exc)
                    if not reason.startswith("schema_"):
                        reason = "schema_value_invalid"
                    findings.append(ContractFinding(contract, source_row, row_id, (reason,)))
    event_rows_by_id: dict[str, list[int]] = {}
    evaluation_rows_by_id: dict[str, list[int]] = {}
    for row in raw_rows:
        if row.contract == "events":
            row_id = row.values.get("event_row_id", "")
            row_numbers = event_rows_by_id
        elif row.contract == "evaluations":
            row_id = row.values.get("evaluation_row_id", "")
            row_numbers = evaluation_rows_by_id
        else:
            continue
        if row_id and row_id != RAW_MISSING_CELL:
            row_numbers.setdefault(row_id, []).append(
                row.source_row
            )
    duplicate_event_ids = {
        row_id
        for row_id, source_rows in event_rows_by_id.items()
        if len(source_rows) > 1
    }
    if duplicate_event_ids:
        parsed["events"] = [
            row
            for row in parsed["events"]
            if row.event_row_id not in duplicate_event_ids
        ]
        findings.extend(
            ContractFinding(
                "events",
                source_row,
                row_id,
                ("schema_event_row_id_duplicate",),
            )
            for row_id in sorted(duplicate_event_ids)
            for source_row in event_rows_by_id[row_id]
        )
    duplicate_evaluation_ids = {
        row_id
        for row_id, source_rows in evaluation_rows_by_id.items()
        if len(source_rows) > 1
    }
    if duplicate_evaluation_ids:
        parsed["evaluations"] = [
            row
            for row in parsed["evaluations"]
            if row.evaluation_row_id not in duplicate_evaluation_ids
        ]
        findings.extend(
            ContractFinding(
                "evaluations",
                source_row,
                row_id,
                ("schema_evaluation_row_id_duplicate",),
            )
            for row_id in sorted(duplicate_evaluation_ids)
            for source_row in evaluation_rows_by_id[row_id]
        )
    return ParsedUniverseEvidence(
        raw=tuple(raw_rows),
        identities=tuple(parsed["security_identity"]),
        memberships=tuple(parsed["membership"]),
        events=tuple(parsed["events"]),
        evaluations=tuple(parsed["evaluations"]),
        findings=tuple(findings),
    )
