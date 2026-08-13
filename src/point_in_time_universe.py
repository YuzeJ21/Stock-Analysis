from __future__ import annotations

from collections import Counter
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from src.commercial_source_rights import (
    parse_source_rights_registry,
    review_commercial_field_scope,
)
from src.point_in_time_universe_contracts import (
    EVENT_TYPES,
    IdentityObservation,
    ParsedUniverseEvidence,
    RAW_MISSING_CELL,
    parse_universe_evidence,
    parse_utc,
)
from src.point_in_time_universe_identifiers import (
    escape_structural_token,
    is_control_free,
)
from src.point_in_time_universe_lineage import resolve_lineage
from src.point_in_time_universe_manifest import UniverseManifest, load_universe_package


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
class RowReference:
    contract: str
    source_row: int
    row_id: str
    evaluation_row_id: str = ""


@dataclass(frozen=True)
class MembershipDigest:
    universe_id: str
    evaluation_at: str
    member_count: int
    sha256: str


@dataclass(frozen=True)
class EvaluationMemberScope:
    security_ids: frozenset[str]
    resolved: bool


@dataclass(frozen=True)
class ScopedLineageComposition:
    leaves: tuple
    reason_codes: tuple[str, ...]
    reason_records: Mapping[str, tuple]
    reasons_by_scope: Mapping[object, tuple[str, ...]]


@dataclass(frozen=True)
class EffectiveIdentityResolver:
    history: tuple[IdentityObservation, ...]
    invalid_scopes: frozenset[str]

    def active_at(
        self,
        security_id: str,
        effective_at: datetime,
        *,
        end_inclusive: bool = False,
        start_strict: bool = False,
    ) -> tuple[IdentityObservation, ...]:
        return tuple(
            identity
            for identity in self.history
            if (
                identity.security_id == security_id
                and (
                    identity.valid_from < effective_at
                    if start_strict
                    else identity.valid_from <= effective_at
                )
                and (
                    identity.valid_to is None
                    or (
                        effective_at <= identity.valid_to
                        if end_inclusive
                        else effective_at < identity.valid_to
                    )
                )
            )
        )

    def security_scope_invalid(self, security_id: str) -> bool:
        return security_id in self.invalid_scopes


@dataclass(frozen=True)
class RecordSourceIndex:
    source_rows: Mapping[str, Mapping[int, int]]

    def source_row(self, contract: str, record) -> int:
        return self.source_rows[contract][id(record)]


@dataclass(frozen=True)
class PointInTimeUniversePacket:
    dataset_id: str
    manifest_id: str
    analysis_eligible: bool
    decisions: Mapping[str, Decision]
    raw_count: int
    normalized_count: int
    raw_rows: tuple[RowReference, ...]
    normalized_rows: tuple[RowReference, ...]
    excluded: tuple[ExcludedRow, ...]
    excluded_count: int
    exclusion_reason_counts: Mapping[str, int]
    analysis_eligible_rows: tuple[RowReference, ...]
    analysis_eligible_row_count: int
    membership_digests: tuple[MembershipDigest, ...]
    display_tickers: Mapping[str, str]
    boundary: str


DECISION_ORDER = (
    "manifest_integrity",
    "technical_validity",
    "temporal_validity",
    "identity_coverage",
    "membership_coverage",
    "corporate_action_coverage",
    "delisting_coverage",
    "source_rights_eligibility",
    "reproduction_ready",
    "leakage_safe",
)
MAX_PREVIEW_EXCLUSION_ROWS = 100
SUCCESSOR_EVENT_TYPES = frozenset(
    {"merger", "acquisition", "spinoff"}
)
REPLACEMENT_SUCCESSOR_EVENT_TYPES = frozenset(
    {"merger", "acquisition"}
)
INVALID_SUCCESSOR_IDENTIFIERS = frozenset(
    {"unknown", "ambiguous"}
)
RESTRICTIVE_LISTING_STATE_EVENT_TYPES = MappingProxyType(
    {
        "delisted": "delisting",
        "suspended": "suspension",
    }
)
EVENT_LISTING_STATE_CONTRACT = MappingProxyType(
    {
        "listing": frozenset({"", "active"}),
        "ticker_change": frozenset(
            {"", "active", "delisted", "suspended"}
        ),
        "exchange_change": frozenset(
            {"", "active", "delisted", "suspended"}
        ),
        "split": frozenset(
            {"", "active", "delisted", "suspended"}
        ),
        "reverse_split": frozenset(
            {"", "active", "delisted", "suspended"}
        ),
        "merger": frozenset(
            {"", "active", "delisted", "suspended"}
        ),
        "acquisition": frozenset(
            {"", "active", "delisted", "suspended"}
        ),
        "spinoff": frozenset(
            {"", "active", "delisted", "suspended"}
        ),
        "delisting": frozenset({"delisted"}),
        "suspension": frozenset({"suspended"}),
        "reactivation": frozenset({"active"}),
    }
)
CONTRACT_TIMESTAMP_FIELDS = MappingProxyType({
    "security_identity": (
        "valid_from",
        "valid_to",
        "source_published_at",
        "retrieved_at",
    ),
    "membership": (
        "effective_from",
        "effective_to",
        "observation_at",
        "source_published_at",
        "retrieved_at",
    ),
    "events": (
        "effective_at",
        "source_published_at",
        "retrieved_at",
    ),
    "evaluations": (
        "evaluation_at",
        "available_at",
    ),
})


def _validate_top_n(top_n: int) -> None:
    if (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or top_n < 0
        or top_n > MAX_PREVIEW_EXCLUSION_ROWS
    ):
        raise ValueError("top_n_invalid")

ROW_ID_FIELDS = {
    "security_identity": "identity_row_id",
    "membership": "membership_row_id",
    "events": "event_row_id",
    "evaluations": "evaluation_row_id",
}

RECORD_ROW_ID_ATTRIBUTES = {
    "security_identity": "identity_row_id",
    "membership": "membership_row_id",
    "events": "event_row_id",
    "evaluations": "evaluation_row_id",
}


def _membership_digest(
    universe_id: str,
    evaluation_at: str,
    members: set[str],
) -> MembershipDigest:
    payload = "\n".join(sorted(members)).encode("utf-8")
    return MembershipDigest(
        universe_id,
        evaluation_at,
        len(members),
        hashlib.sha256(payload).hexdigest(),
    )


def _contains(start, end, at):
    return start <= at and (end is None or at < end)


def _record_row_id(contract: str, record) -> str:
    return getattr(record, RECORD_ROW_ID_ATTRIBUTES[contract])


def _record_source_rows(
    parsed: ParsedUniverseEvidence,
    contract: str,
    records,
) -> Mapping[int, int]:
    finding_rows = {
        (finding.contract, finding.source_row)
        for finding in parsed.findings
    }
    normalized_raw = tuple(
        row
        for row in parsed.raw
        if (
            row.contract == contract
            and (contract, row.source_row) not in finding_rows
        )
    )
    if len(normalized_raw) != len(records):
        raise RuntimeError("normalized_record_source_row_mismatch")
    return MappingProxyType(
        {
            id(record): raw.source_row
            for record, raw in zip(
                records,
                normalized_raw,
                strict=True,
            )
        }
    )


def _build_record_source_index(
    parsed: ParsedUniverseEvidence,
) -> RecordSourceIndex:
    records_by_contract = {
        "security_identity": parsed.identities,
        "membership": parsed.memberships,
        "events": parsed.events,
        "evaluations": parsed.evaluations,
    }
    return RecordSourceIndex(
        MappingProxyType(
            {
                contract: _record_source_rows(
                    parsed,
                    contract,
                    records,
                )
                for contract, records in records_by_contract.items()
            }
        )
    )


def _excluded_record(
    source_index: RecordSourceIndex,
    contract: str,
    record,
    reason_codes: tuple[str, ...],
) -> ExcludedRow:
    return ExcludedRow(
        contract,
        source_index.source_row(contract, record),
        _record_row_id(contract, record),
        reason_codes,
    )


def _record_exclusions(
    source_index: RecordSourceIndex,
    contract: str,
    records,
    reason_codes: tuple[str, ...],
) -> tuple[ExcludedRow, ...]:
    return tuple(
        _excluded_record(
            source_index,
            contract,
            record,
            reason_codes,
        )
        for record in records
    )


def _lineage_reason_records(
    records,
    *,
    row_id,
    parent_id,
    scope,
    available_at,
    cutoff,
) -> Mapping[str, tuple]:
    eligible = tuple(
        record for record in records if available_at(record) <= cutoff
    )
    marked: dict[str, list] = {}

    def mark(reason: str, *items) -> None:
        bucket = marked.setdefault(reason, [])
        for item in items:
            if all(existing is not item for existing in bucket):
                bucket.append(item)

    by_identifier: dict[str, list] = {}
    for record in eligible:
        by_identifier.setdefault(row_id(record), []).append(record)
    for duplicates in by_identifier.values():
        if len(duplicates) > 1:
            mark("lineage_duplicate_id", *duplicates)

    by_id = {
        identifier: items[0]
        for identifier, items in by_identifier.items()
        if len(items) == 1
    }
    roots: dict[str, list] = {}
    children: dict[str, list] = {}
    for record in eligible:
        parent_identifier = parent_id(record)
        record_scope = scope(record)
        if not parent_identifier:
            roots.setdefault(record_scope, []).append(record)
            continue
        matching_parents = by_identifier.get(parent_identifier)
        if matching_parents is None:
            mark("lineage_missing_parent", record)
            continue
        if len(matching_parents) != 1:
            mark("lineage_duplicate_id", record)
            continue
        children.setdefault(parent_identifier, []).append(record)
        parent = matching_parents[0]
        if scope(parent) != record_scope:
            mark("lineage_cross_scope_parent", parent, record)
        if available_at(record) <= available_at(parent):
            mark("lineage_order_reversed", parent, record)

    for scope_roots in roots.values():
        if len(scope_roots) > 1:
            mark("lineage_multiple_roots", *scope_roots)
    for parent_identifier, child_records in children.items():
        if len(child_records) > 1:
            mark(
                "lineage_fork",
                *by_identifier.get(parent_identifier, ()),
                *child_records,
            )

    for start in eligible:
        path: list = []
        positions: dict[str, int] = {}
        current = start
        while parent_id(current):
            current_identifier = row_id(current)
            if current_identifier in positions:
                mark(
                    "lineage_cycle",
                    *path[positions[current_identifier]:],
                )
                break
            positions[current_identifier] = len(path)
            path.append(current)
            parent = by_id.get(parent_id(current))
            if parent is None:
                break
            current = parent

    return MappingProxyType(
        {
            reason: tuple(items)
            for reason, items in sorted(marked.items())
        }
    )


def _compose_scoped_lineage(
    records,
    *,
    row_id,
    parent_id,
    scope,
    available_at,
    cutoff,
) -> ScopedLineageComposition:
    eligible = tuple(
        record for record in records if available_at(record) <= cutoff
    )
    reason_records = _lineage_reason_records(
        records,
        row_id=row_id,
        parent_id=parent_id,
        scope=scope,
        available_at=available_at,
        cutoff=cutoff,
    )
    reasons_by_scope: dict[object, set[str]] = {}
    for reason, offenders in reason_records.items():
        for offender in offenders:
            reasons_by_scope.setdefault(scope(offender), set()).add(reason)

    records_by_scope: dict[str, list] = {}
    for record in eligible:
        records_by_scope.setdefault(scope(record), []).append(record)
    leaves: list = []
    for record_scope, scoped_records in sorted(records_by_scope.items()):
        if record_scope in reasons_by_scope:
            continue
        resolved = resolve_lineage(
            scoped_records,
            row_id=row_id,
            parent_id=parent_id,
            scope=scope,
            available_at=available_at,
            cutoff=cutoff,
        )
        if resolved.reason_codes:
            raise RuntimeError("scoped_lineage_composition_mismatch")
        leaves.extend(resolved.leaves)

    return ScopedLineageComposition(
        tuple(leaves),
        tuple(reason_records),
        MappingProxyType(dict(reason_records)),
        MappingProxyType(
            {
                record_scope: tuple(sorted(reasons))
                for record_scope, reasons in sorted(
                    reasons_by_scope.items()
                )
            }
        ),
    )


def _effective_identity_interval_history(
    records: tuple[IdentityObservation, ...],
    lineage: ScopedLineageComposition,
    cutoff: datetime,
) -> tuple[
    tuple[IdentityObservation, ...],
    frozenset[str],
]:
    eligible_by_scope: dict[
        str,
        list[IdentityObservation],
    ] = {}
    for record in records:
        record_scope = record.security_id
        if (
            max(record.source_published_at, record.retrieved_at)
            <= cutoff
            and record_scope not in lineage.reasons_by_scope
        ):
            eligible_by_scope.setdefault(
                record_scope,
                [],
            ).append(record)

    effective_history: list[IdentityObservation] = []
    invalid_scopes: set[str] = set()
    for leaf in lineage.leaves:
        record_scope = leaf.security_id
        scoped_records = eligible_by_scope[record_scope]
        by_id = {
            record.identity_row_id: record
            for record in scoped_records
        }
        chain: list[IdentityObservation] = []
        current = leaf
        while True:
            chain.append(current)
            if not current.supersedes_identity_row_id:
                break
            current = by_id[current.supersedes_identity_row_id]
        chain.reverse()

        effective: list[IdentityObservation] = []
        direct_parent: IdentityObservation | None = None
        for record in chain:
            if direct_parent is None:
                effective.append(record)
            elif (
                direct_parent.valid_from < record.valid_from
                and direct_parent.valid_to == record.valid_from
            ):
                effective.append(record)
            else:
                effective[-1] = record
                while len(effective) > 1:
                    prior_effective = effective[-2]
                    corrected_effective = effective[-1]
                    if (
                        prior_effective.valid_from
                        < corrected_effective.valid_from
                        and prior_effective.valid_to
                        == corrected_effective.valid_from
                    ):
                        break
                    del effective[-2]
            direct_parent = record

        ordered = tuple(
            sorted(
                effective,
                key=lambda record: (
                    record.valid_from,
                    record.identity_row_id,
                ),
            )
        )
        if any(
            record.valid_to is not None
            and record.valid_to < record.valid_from
            for record in ordered
        ) or any(
            prior.valid_to is None
            or prior.valid_to > current.valid_from
            for prior, current in zip(
                ordered,
                ordered[1:],
                strict=False,
            )
        ):
            invalid_scopes.add(record_scope)
            continue
        effective_history.extend(ordered)

    return tuple(effective_history), frozenset(invalid_scopes)


def _effective_identity_resolver(
    records: tuple[IdentityObservation, ...],
    lineage: ScopedLineageComposition,
    cutoff: datetime,
) -> EffectiveIdentityResolver:
    history, invalid_scopes = _effective_identity_interval_history(
        records,
        lineage,
        cutoff,
    )
    return EffectiveIdentityResolver(history, invalid_scopes)


def _event_identity_endpoints(
    event,
    resolver: EffectiveIdentityResolver,
) -> tuple[
    tuple[IdentityObservation, ...],
    tuple[IdentityObservation, ...],
]:
    if event.event_type not in SUCCESSOR_EVENT_TYPES:
        return (), ()
    replacement = (
        event.event_type in REPLACEMENT_SUCCESSOR_EVENT_TYPES
    )
    predecessors = resolver.active_at(
        event.security_id,
        event.effective_at,
        end_inclusive=replacement,
        start_strict=replacement,
    )
    successors = resolver.active_at(
        event.successor_security_id,
        event.effective_at,
    )
    return predecessors, successors


def _identity_transition_event_requirements(
    identity_history: tuple[IdentityObservation, ...],
    evaluation_at: datetime,
) -> tuple[tuple[IdentityObservation, str], ...]:
    by_security: dict[str, list[IdentityObservation]] = {}
    for identity in identity_history:
        by_security.setdefault(identity.security_id, []).append(identity)

    requirements: list[tuple[IdentityObservation, str]] = []
    for identities in by_security.values():
        ordered = sorted(
            identities,
            key=lambda identity: (
                identity.valid_from,
                identity.identity_row_id,
            ),
        )
        for prior, current in zip(
            ordered,
            ordered[1:],
            strict=False,
        ):
            if (
                prior.valid_from >= current.valid_from
                or prior.valid_to != current.valid_from
                or current.valid_from > evaluation_at
            ):
                continue
            if prior.ticker != current.ticker:
                requirements.append((current, "ticker_change"))
            if prior.exchange != current.exchange:
                requirements.append((current, "exchange_change"))
    return tuple(requirements)


def _identity_security_reuse_records(
    records: tuple[IdentityObservation, ...],
    evaluation_at: datetime,
) -> tuple[IdentityObservation, ...]:
    effective_by_security_and_start: dict[
        str,
        dict[datetime, IdentityObservation],
    ] = {}
    for record in records:
        if (
            max(record.source_published_at, record.retrieved_at)
            > evaluation_at
            or record.valid_from > evaluation_at
        ):
            continue
        by_start = effective_by_security_and_start.setdefault(
            record.security_id,
            {},
        )
        prior = by_start.get(record.valid_from)
        if prior is None or (
            max(record.source_published_at, record.retrieved_at),
            record.identity_row_id,
            record.source_ref,
        ) > (
            max(prior.source_published_at, prior.retrieved_at),
            prior.identity_row_id,
            prior.source_ref,
        ):
            by_start[record.valid_from] = record

    reuse_records: list[IdentityObservation] = []
    for by_start in effective_by_security_and_start.values():
        ordered = tuple(
            by_start[valid_from]
            for valid_from in sorted(by_start)
        )
        reuse_records.extend(
            current
            for prior, current in zip(
                ordered,
                ordered[1:],
                strict=False,
            )
            if prior.issuer_id != current.issuer_id
        )
    return tuple(
        sorted(
            reuse_records,
            key=lambda record: (
                record.security_id,
                record.valid_from,
                record.identity_row_id,
                record.source_ref,
            ),
        )
    )


def _identity_cross_issuer_security_ids(
    records: tuple[IdentityObservation, ...],
    evaluation_at: datetime,
) -> frozenset[str]:
    visible = tuple(
        record
        for record in records
        if (
            max(record.source_published_at, record.retrieved_at)
            <= evaluation_at
            and record.valid_from <= evaluation_at
        )
    )
    records_by_id: dict[str, list[IdentityObservation]] = {}
    for record in visible:
        records_by_id.setdefault(
            record.identity_row_id,
            [],
        ).append(record)
    by_id = {
        identity_row_id: matching_records[0]
        for identity_row_id, matching_records in records_by_id.items()
        if len(matching_records) == 1
    }
    children_by_parent: dict[str, list[IdentityObservation]] = {}
    for record in visible:
        if record.supersedes_identity_row_id in by_id:
            children_by_parent.setdefault(
                record.supersedes_identity_row_id,
                [],
            ).append(record)

    def edge_is_cyclic(parent_id: str, child_id: str) -> bool:
        current_id = parent_id
        visited: set[str] = set()
        while current_id in by_id and current_id not in visited:
            visited.add(current_id)
            next_id = by_id[current_id].supersedes_identity_row_id
            if next_id == child_id:
                return True
            current_id = next_id
        return False

    def is_valid_correction_edge(
        parent: IdentityObservation,
        child: IdentityObservation,
    ) -> bool:
        return (
            by_id.get(parent.identity_row_id) is parent
            and by_id.get(child.identity_row_id) is child
            and child.security_id == parent.security_id
            and child.valid_from == parent.valid_from
            and max(
                child.source_published_at,
                child.retrieved_at,
            )
            > max(
                parent.source_published_at,
                parent.retrieved_at,
            )
            and not edge_is_cyclic(
                parent.identity_row_id,
                child.identity_row_id,
            )
        )

    corrected_parent_ids: set[str] = set()
    for parent_id, children in children_by_parent.items():
        parent = by_id[parent_id]
        correction_candidates = tuple(
            child
            for child in children
            if is_valid_correction_edge(parent, child)
        )
        if len(correction_candidates) == 1:
            corrected_parent_ids.add(parent_id)
    issuers_by_security: dict[str, set[str]] = {}
    for record in visible:
        if record.identity_row_id in corrected_parent_ids:
            continue
        issuers_by_security.setdefault(
            record.security_id,
            set(),
        ).add(record.issuer_id)
    return frozenset(
        security_id
        for security_id, issuer_ids in issuers_by_security.items()
        if len(issuer_ids) > 1
    )


def _identity_interval_overlap_records(
    records: tuple[IdentityObservation, ...],
    evaluation_at: datetime,
) -> tuple[IdentityObservation, ...]:
    visible_active = tuple(
        record
        for record in records
        if (
            max(record.source_published_at, record.retrieved_at)
            <= evaluation_at
            and _contains(
                record.valid_from,
                record.valid_to,
                evaluation_at,
            )
        )
    )
    superseded_same_effective_ids = {
        record.supersedes_identity_row_id
        for record in visible_active
        for parent in visible_active
        if (
            record.supersedes_identity_row_id
            == parent.identity_row_id
            and record.security_id == parent.security_id
            and record.valid_from == parent.valid_from
            and record.valid_to == parent.valid_to
        )
    }
    effective = tuple(
        record
        for record in visible_active
        if record.identity_row_id not in superseded_same_effective_ids
    )
    by_security: dict[str, list[IdentityObservation]] = {}
    for record in effective:
        by_security.setdefault(record.security_id, []).append(record)
    return tuple(
        sorted(
            (
                record
                for security_records in by_security.values()
                if len(security_records) > 1
                for record in security_records
            ),
            key=lambda record: (
                record.security_id,
                record.valid_from,
                record.identity_row_id,
                record.source_ref,
            ),
        )
    )


def _unexplained_snapshot_omissions(
    memberships,
    lineage: ScopedLineageComposition,
    *,
    universe_id: str,
    universe_kind: str,
    latest_snapshot_at: datetime | None,
    evaluation_at: datetime,
):
    if latest_snapshot_at is None:
        return ()
    explicit_latest_security_ids = {
        row.security_id
        for row in lineage.leaves
        if (
            row.universe_id == universe_id
            and row.universe_kind == universe_kind
            and row.observation_at == latest_snapshot_at
            and _contains(
                row.effective_from,
                row.effective_to,
                evaluation_at,
            )
        )
    }
    prior_inclusion_by_security = {}
    for row in memberships:
        if (
            row.universe_id != universe_id
            or row.universe_kind != universe_kind
            or row.membership_state != "included"
            or row.observation_at >= latest_snapshot_at
            or max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            )
            > evaluation_at
            or not _contains(
                row.effective_from,
                row.effective_to,
                evaluation_at,
            )
        ):
            continue
        prior = prior_inclusion_by_security.get(row.security_id)
        if prior is None or (
            row.observation_at,
            row.source_published_at,
            row.retrieved_at,
            row.membership_row_id,
            row.source_ref,
        ) > (
            prior.observation_at,
            prior.source_published_at,
            prior.retrieved_at,
            prior.membership_row_id,
            prior.source_ref,
        ):
            prior_inclusion_by_security[row.security_id] = row
    return tuple(
        prior_inclusion_by_security[security_id]
        for security_id in sorted(
            set(prior_inclusion_by_security)
            - explicit_latest_security_ids
        )
    )


def _identity_membership_decisions(
    manifest: UniverseManifest,
    parsed: ParsedUniverseEvidence,
    source_index: RecordSourceIndex,
    evaluations,
    evaluation_reasons: Mapping[str, tuple[str, ...]],
):
    declared = {
        item["universe_id"]: item["universe_kind"]
        for item in manifest.declared_universes
    }
    identity_reasons: set[str] = set()
    membership_reasons: set[str] = set()
    excluded: list[ExcludedRow] = []
    digests: list[MembershipDigest] = []
    display_candidates: dict[str, tuple[tuple, str | None]] = {}
    complete_snapshot_supported = (
        manifest.coverage_semantics == "complete_snapshot"
    )
    if not complete_snapshot_supported:
        membership_reasons.add(
            "membership_coverage_semantics_unsupported"
        )
    for evaluation in parsed.evaluations:
        owned_reasons = tuple(
            reason
            for reason in evaluation_reasons[
                evaluation.evaluation_row_id
            ]
            if reason.startswith("membership_")
        )
        if not owned_reasons:
            continue
        membership_reasons.update(owned_reasons)
        excluded.append(
            ExcludedRow(
                "evaluations",
                source_index.source_row("evaluations", evaluation),
                evaluation.evaluation_row_id,
                owned_reasons,
            )
        )
    evaluations = tuple(
        sorted(
            (
                item
                for item in evaluations
            ),
            key=lambda item: (
                item.evaluation_at,
                item.universe_id,
                item.evaluation_row_id,
                item.available_at,
                item.partition,
                item.source_ref,
            ),
        )
    )

    for evaluation in evaluations:
        visible_memberships = tuple(
            row
            for row in parsed.memberships
            if max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            )
            <= evaluation.evaluation_at
        )
        for row in visible_memberships:
            expected_row_kind = declared.get(row.universe_id)
            if expected_row_kind is None:
                reason = "membership_universe_undeclared"
            elif row.universe_kind != expected_row_kind:
                reason = "membership_universe_kind_mismatch"
            else:
                continue
            membership_reasons.add(reason)
            excluded.append(
                _excluded_record(
                    source_index,
                    "membership",
                    row,
                    (reason,),
                )
            )

        membership_lineage = _compose_scoped_lineage(
            parsed.memberships,
            row_id=lambda row: row.membership_row_id,
            parent_id=lambda row: row.supersedes_membership_row_id,
            scope=lambda row: (row.universe_id, row.security_id),
            available_at=lambda row: max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        membership_reasons.update(membership_lineage.reason_codes)
        if membership_lineage.reason_codes:
            for reason in membership_lineage.reason_codes:
                excluded.extend(
                    _record_exclusions(
                        source_index,
                        "membership",
                        membership_lineage.reason_records.get(
                            reason,
                            (),
                        ),
                        (reason,),
                    )
                )
        identity_lineage = _compose_scoped_lineage(
            parsed.identities,
            row_id=lambda row: row.identity_row_id,
            parent_id=lambda row: row.supersedes_identity_row_id,
            scope=lambda row: row.security_id,
            available_at=lambda row: max(
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        identity_reasons.update(identity_lineage.reason_codes)
        if identity_lineage.reason_codes:
            for reason in identity_lineage.reason_codes:
                excluded.extend(
                    _record_exclusions(
                        source_index,
                        "security_identity",
                        identity_lineage.reason_records.get(
                            reason,
                            (),
                        ),
                        (reason,),
                    )
                )

        issuer_reuse_records = _identity_security_reuse_records(
            parsed.identities,
            evaluation.evaluation_at,
        )
        cross_issuer_security_ids = _identity_cross_issuer_security_ids(
            parsed.identities,
            evaluation.evaluation_at,
        )
        issuer_reuse_records = tuple(
            record
            for record in issuer_reuse_records
            if not (
                set(
                    identity_lineage.reasons_by_scope.get(
                        record.security_id,
                        (),
                    )
                )
                - {"lineage_multiple_roots"}
            )
        )
        if issuer_reuse_records:
            reason = "identity_security_id_reused_across_issuers"
            identity_reasons.add(reason)
            excluded.extend(
                _record_exclusions(
                    source_index,
                    "security_identity",
                    issuer_reuse_records,
                    (reason,),
                )
            )

        overlap_records = _identity_interval_overlap_records(
            parsed.identities,
            evaluation.evaluation_at,
        )
        overlap_records = tuple(
            record
            for record in overlap_records
            if not (
                set(
                    identity_lineage.reasons_by_scope.get(
                        record.security_id,
                        (),
                    )
                )
                - {"lineage_multiple_roots"}
            )
        )
        if overlap_records:
            identity_reasons.add("identity_interval_overlap")
            excluded.extend(
                _record_exclusions(
                    source_index,
                    "security_identity",
                    overlap_records,
                    ("identity_interval_overlap",),
                )
            )

        identity_resolver = _effective_identity_resolver(
            parsed.identities,
            identity_lineage,
            evaluation.evaluation_at,
        )
        identity_interval_history = identity_resolver.history
        expected_kind = declared.get(evaluation.universe_id)
        if expected_kind is None:
            membership_reasons.add("membership_universe_undeclared")
            continue

        scoped_memberships = tuple(
            row
            for row in parsed.memberships
            if row.universe_id == evaluation.universe_id
        )
        cutoff_available_memberships = tuple(
            row
            for row in scoped_memberships
            if max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            )
            <= evaluation.evaluation_at
        )
        latest_snapshot_at = max(
            (
                row.observation_at
                for row in cutoff_available_memberships
            ),
            default=None,
        )
        if not complete_snapshot_supported:
            continue

        active_identity_by_security: dict[str, IdentityObservation] = {}
        issuer_reuse_security_ids = {
            record.security_id
            for record in issuer_reuse_records
        }
        overlapping_identity_security_ids = {
            record.security_id
            for record in overlap_records
        }
        identity_lineage_reasons_by_security: dict[str, set[str]] = {}
        for reason, offenders in identity_lineage.reason_records.items():
            for offender in offenders:
                identity_lineage_reasons_by_security.setdefault(
                    offender.security_id,
                    set(),
                ).add(reason)
        available_identity_by_security: dict[str, list] = {}
        for row in identity_interval_history:
            available_identity_by_security.setdefault(
                row.security_id,
                [],
            ).append(row)
        for security_id in available_identity_by_security:
            active = identity_resolver.active_at(
                security_id,
                evaluation.evaluation_at,
            )
            if len(active) > 1:
                identity_reasons.add("identity_interval_overlap")
                overlapping_identity_security_ids.add(security_id)
                excluded.extend(
                    _record_exclusions(
                        source_index,
                        "security_identity",
                        active,
                        ("identity_interval_overlap",),
                    )
                )
            elif len(active) == 1:
                active_identity_by_security[security_id] = active[0]

        omission_records = _unexplained_snapshot_omissions(
            scoped_memberships,
            membership_lineage,
            universe_id=evaluation.universe_id,
            universe_kind=expected_kind,
            latest_snapshot_at=latest_snapshot_at,
            evaluation_at=evaluation.evaluation_at,
        )
        if omission_records:
            reason = "membership_snapshot_omission_unexplained"
            membership_reasons.add(reason)
            excluded.extend(
                _record_exclusions(
                    source_index,
                    "membership",
                    omission_records,
                    (reason,),
                )
            )
            continue

        members: set[str] = set()
        structurally_eligible_members = 0
        digest_eligible = True
        for leaf in membership_lineage.leaves:
            if leaf.universe_id != evaluation.universe_id:
                continue
            if leaf.observation_at != latest_snapshot_at:
                continue
            if leaf.universe_kind != expected_kind:
                membership_reasons.add("membership_universe_kind_mismatch")
                continue
            if not _contains(
                leaf.effective_from,
                leaf.effective_to,
                evaluation.evaluation_at,
            ):
                membership_reasons.add("membership_interval_inactive")
                excluded.append(
                    _excluded_record(
                        source_index,
                        "membership",
                        leaf,
                        ("membership_interval_inactive",),
                    )
                )
                continue
            if leaf.membership_state == "excluded":
                continue

            security_id = leaf.security_id
            structurally_eligible_members += 1
            evaluation_key = (
                evaluation.evaluation_at,
                evaluation.universe_id,
                evaluation.evaluation_row_id,
                evaluation.available_at,
                evaluation.partition,
                evaluation.source_ref,
            )
            prior_display = display_candidates.get(security_id)
            is_latest_display = (
                prior_display is None
                or evaluation_key > prior_display[0]
            )
            if security_id in issuer_reuse_security_ids:
                digest_eligible = False
                if is_latest_display:
                    display_candidates[security_id] = (
                        evaluation_key,
                        None,
                    )
                excluded.append(
                    _excluded_record(
                        source_index,
                        "membership",
                        leaf,
                        ("identity_missing",),
                    )
                )
                continue
            if security_id in overlapping_identity_security_ids:
                if is_latest_display:
                    display_candidates[security_id] = (
                        evaluation_key,
                        None,
                    )
                excluded.append(
                    _excluded_record(
                        source_index,
                        "membership",
                        leaf,
                        ("identity_interval_overlap",),
                    )
                )
                continue
            if security_id in identity_lineage_reasons_by_security:
                if security_id in cross_issuer_security_ids:
                    digest_eligible = False
                if is_latest_display:
                    display_candidates[security_id] = (
                        evaluation_key,
                        None,
                    )
                excluded.append(
                    _excluded_record(
                        source_index,
                        "membership",
                        leaf,
                        ("identity_missing",),
                    )
                )
                continue

            active_identity = active_identity_by_security.get(security_id)
            if active_identity is None:
                identity_rows = tuple(
                    row
                    for row in identity_interval_history
                    if row.security_id == security_id
                )
                identity_reasons.add("identity_missing")
                if is_latest_display:
                    display_candidates[security_id] = (
                        evaluation_key,
                        None,
                    )
                excluded.append(
                    _excluded_record(
                        source_index,
                        "membership",
                        leaf,
                        ("identity_missing",),
                    )
                )
                excluded.extend(
                    _record_exclusions(
                        source_index,
                        "security_identity",
                        identity_rows,
                        ("identity_missing",),
                    )
                )
                continue

            if is_latest_display:
                display_candidates[security_id] = (
                    evaluation_key,
                    active_identity.ticker,
                )
            members.add(security_id)

        if structurally_eligible_members == 0:
            membership_reasons.add("membership_no_eligible_members")
        if digest_eligible:
            digests.append(
                _membership_digest(
                    evaluation.universe_id,
                    evaluation.evaluation_at.isoformat().replace(
                        "+00:00",
                        "Z",
                    ),
                    members,
                )
            )

    kinds = set(declared.values())
    if "benchmark" not in kinds:
        membership_reasons.add("membership_benchmark_missing")
    if "research_universe" not in kinds:
        membership_reasons.add("membership_research_universe_missing")
    evaluated_universes = {item.universe_id for item in evaluations}
    if any(
        universe_id not in evaluated_universes
        for universe_id in declared
    ):
        membership_reasons.add("membership_no_evaluation")

    display = {
        security_id: candidate[1]
        for security_id, candidate in sorted(display_candidates.items())
        if candidate[1] is not None
    }
    sorted_digests = tuple(
        sorted(
            digests,
            key=lambda item: (
                item.evaluation_at,
                item.universe_id,
                item.sha256,
                item.member_count,
            ),
        )
    )
    canonical_digests: list[MembershipDigest] = []
    first_digest_by_cutoff: dict[
        tuple[str, str],
        MembershipDigest,
    ] = {}
    for digest in sorted_digests:
        key = (digest.universe_id, digest.evaluation_at)
        first_digest = first_digest_by_cutoff.get(key)
        if first_digest == digest:
            continue
        canonical_digests.append(digest)
        first_digest_by_cutoff.setdefault(key, digest)
    return (
        Decision(
            "identity_coverage",
            "blocked" if identity_reasons else "passed",
            tuple(sorted(identity_reasons)),
        ),
        Decision(
            "membership_coverage",
            "blocked" if membership_reasons else "passed",
            tuple(sorted(membership_reasons)),
        ),
        tuple(canonical_digests),
        MappingProxyType(display),
        tuple(excluded),
    )


def _temporal_decision(
    manifest: UniverseManifest,
    parsed: ParsedUniverseEvidence,
    source_index: RecordSourceIndex,
    evaluations,
    evaluation_reasons: Mapping[str, tuple[str, ...]],
) -> tuple[Decision, tuple[str, ...], tuple[ExcludedRow, ...]]:
    temporal_reasons: set[str] = set()
    leakage_reasons: set[str] = set()
    exclusion_reasons: dict[tuple[str, int, str], set[str]] = {}
    valid_evaluation_ids = {
        evaluation.evaluation_row_id
        for evaluation in evaluations
    }
    declared_universe_ids = {
        item["universe_id"]
        for item in manifest.declared_universes
    }

    def record_exclusion(
        contract: str,
        record,
        *reason_codes: str,
    ) -> None:
        exclusion_reasons.setdefault(
            (
                contract,
                source_index.source_row(contract, record),
                _record_row_id(contract, record),
            ),
            set(),
        ).update(reason_codes)

    manifest_created_at = parse_utc(manifest.manifest_created_at)
    for raw_row in parsed.raw:
        post_creation_timestamp = False
        for field in CONTRACT_TIMESTAMP_FIELDS[raw_row.contract]:
            value = raw_row.values.get(field, "")
            if not value:
                continue
            try:
                timestamp = parse_utc(value)
            except (TypeError, ValueError):
                continue
            if timestamp > manifest_created_at:
                post_creation_timestamp = True
        if not post_creation_timestamp:
            continue
        temporal_reasons.add(
            "temporal_evidence_after_manifest_creation"
        )
        exclusion_reasons.setdefault(
            (
                raw_row.contract,
                raw_row.source_row,
                raw_row.values.get(
                    ROW_ID_FIELDS[raw_row.contract],
                    "",
                ),
            ),
            set(),
        ).add("temporal_evidence_after_manifest_creation")

    for evaluation in parsed.evaluations:
        classified_reasons = evaluation_reasons[
            evaluation.evaluation_row_id
        ]
        if "cutoff_evaluation_after_manifest" in classified_reasons:
            temporal_reasons.add("cutoff_evaluation_after_manifest")
            leakage_reasons.add(
                "leakage_evaluation_after_manifest_cutoff"
            )
            record_exclusion(
                "evaluations",
                evaluation,
                "cutoff_evaluation_after_manifest",
                "leakage_evaluation_after_manifest_cutoff",
            )
            continue
        if "cutoff_evaluation_unavailable" in classified_reasons:
            temporal_reasons.add("cutoff_evaluation_unavailable")
            leakage_reasons.add("leakage_evaluation_available_late")
            record_exclusion(
                "evaluations",
                evaluation,
                "cutoff_evaluation_unavailable",
                "leakage_evaluation_available_late",
            )
        if evaluation.evaluation_row_id not in valid_evaluation_ids:
            continue

        def classify_scope(
            contract,
            rows,
            available_at,
            *,
            required,
        ) -> None:
            available = tuple(
                row
                for row in rows
                if available_at(row) <= evaluation.evaluation_at
            )
            post_cutoff = tuple(
                row
                for row in rows
                if available_at(row) > evaluation.evaluation_at
            )
            if not post_cutoff:
                return
            if required and not available:
                temporal_reasons.update(
                    {
                        "cutoff_post_evaluation_evidence",
                        "cutoff_required_scope_unavailable",
                    }
                )
                leakage_reasons.add("leakage_post_cutoff_evidence")
                for row in post_cutoff:
                    record_exclusion(
                        contract,
                        row,
                        "cutoff_post_evaluation_evidence",
                        "cutoff_required_scope_unavailable",
                        "leakage_post_cutoff_evidence",
                    )
                return
            reason = (
                "cutoff_later_revision_invisible"
                if required
                else "cutoff_unrelated_scope_invisible"
            )
            for row in post_cutoff:
                record_exclusion(contract, row, reason)

        membership_rows = tuple(
            row
            for row in parsed.memberships
            if row.universe_id == evaluation.universe_id
        )
        cutoff_available_memberships = tuple(
            row
            for row in membership_rows
            if max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            )
            <= evaluation.evaluation_at
        )
        latest_snapshot_at = max(
            (
                row.observation_at
                for row in cutoff_available_memberships
            ),
            default=None,
        )
        latest_snapshot_security_ids = (
            {
                row.security_id
                for row in cutoff_available_memberships
                if row.observation_at == latest_snapshot_at
            }
            if manifest.coverage_semantics == "complete_snapshot"
            else set()
        )
        memberships_by_security: dict[str, list] = {}
        for row in membership_rows:
            memberships_by_security.setdefault(
                row.security_id,
                [],
            ).append(row)
        for group in memberships_by_security.values():
            classify_scope(
                "membership",
                group,
                lambda row: max(
                    row.observation_at,
                    row.source_published_at,
                    row.retrieved_at,
                ),
                required=(
                    not cutoff_available_memberships
                    or group[0].security_id
                    in latest_snapshot_security_ids
                ),
            )
        undeclared_memberships_by_scope: dict[
            tuple[str, str],
            list,
        ] = {}
        for row in parsed.memberships:
            if row.universe_id in declared_universe_ids:
                continue
            undeclared_memberships_by_scope.setdefault(
                (row.universe_id, row.security_id),
                [],
            ).append(row)
        for group in undeclared_memberships_by_scope.values():
            classify_scope(
                "membership",
                group,
                lambda row: max(
                    row.observation_at,
                    row.source_published_at,
                    row.retrieved_at,
                ),
                required=False,
            )

        membership_lineage = _compose_scoped_lineage(
            parsed.memberships,
            row_id=lambda row: row.membership_row_id,
            parent_id=lambda row: row.supersedes_membership_row_id,
            scope=lambda row: (row.universe_id, row.security_id),
            available_at=lambda row: max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        member_security_ids = {
            row.security_id
            for row in membership_lineage.leaves
            if (
                manifest.coverage_semantics == "complete_snapshot"
                and row.universe_id == evaluation.universe_id
                and row.observation_at == latest_snapshot_at
                and row.membership_state == "included"
                and _contains(
                    row.effective_from,
                    row.effective_to,
                    evaluation.evaluation_at,
                )
            )
        }

        identities_by_security: dict[str, list] = {}
        for row in parsed.identities:
            identities_by_security.setdefault(
                row.security_id,
                [],
            ).append(row)
        for security_id, group in identities_by_security.items():
            classify_scope(
                "security_identity",
                group,
                lambda row: max(
                    row.source_published_at,
                    row.retrieved_at,
                ),
                required=security_id in member_security_ids,
            )

        events_by_scope: dict[tuple[str, str], list] = {}
        for row in parsed.events:
            events_by_scope.setdefault(
                (row.security_id, row.event_type),
                [],
            ).append(row)
        for (security_id, event_type), group in events_by_scope.items():
            classify_scope(
                "events",
                group,
                lambda row: max(
                    row.effective_at,
                    row.source_published_at,
                    row.retrieved_at,
                ),
                required=(
                    security_id in member_security_ids
                    and manifest.corporate_action_policy.get(event_type)
                    == "required"
                    and any(
                        row.effective_at <= evaluation.evaluation_at
                        for row in group
                    )
                ),
            )

    excluded = tuple(
        ExcludedRow(
            contract,
            source_row,
            row_id,
            tuple(sorted(reasons)),
        )
        for (
            contract,
            source_row,
            row_id,
        ), reasons in sorted(
            exclusion_reasons.items()
        )
    )
    return (
        Decision(
            "temporal_validity",
            "blocked" if temporal_reasons else "passed",
            tuple(sorted(temporal_reasons)),
        ),
        tuple(sorted(leakage_reasons)),
        excluded,
    )


def _classify_evaluations(
    manifest,
    evaluations,
) -> tuple[tuple, Mapping[str, tuple[str, ...]], tuple[str, ...]]:
    evaluations = tuple(evaluations)
    row_reasons: dict[str, set[str]] = {
        evaluation.evaluation_row_id: set()
        for evaluation in evaluations
    }
    global_reasons: set[str] = set()
    manifest_cutoff = (
        parse_utc(manifest.observation_cutoff_at)
        if hasattr(manifest, "observation_cutoff_at")
        else None
    )
    declared_universe_ids = (
        {
            item["universe_id"]
            for item in manifest.declared_universes
        }
        if hasattr(manifest, "declared_universes")
        else None
    )
    for evaluation in evaluations:
        reasons = row_reasons[evaluation.evaluation_row_id]
        if (
            manifest_cutoff is not None
            and evaluation.evaluation_at > manifest_cutoff
        ):
            reasons.add("cutoff_evaluation_after_manifest")
        if evaluation.available_at > evaluation.evaluation_at:
            reasons.add("cutoff_evaluation_unavailable")
        if (
            declared_universe_ids is not None
            and evaluation.universe_id not in declared_universe_ids
        ):
            reasons.add("membership_universe_undeclared")

    policy = manifest.evaluation_policy
    if not isinstance(policy, Mapping):
        global_reasons.add("partition_policy_invalid")
    elif policy.get("kind") == "walk_forward":
        minimum = policy.get("minimum_history_count")
        if (
            not isinstance(minimum, int)
            or isinstance(minimum, bool)
            or minimum <= 0
        ):
            global_reasons.add("partition_minimum_history_invalid")
        else:
            for evaluation in evaluations:
                if evaluation.partition != "walk_forward":
                    row_reasons[evaluation.evaluation_row_id].add(
                        "partition_assignment_invalid"
                    )
            history_by_universe: dict[str, set[datetime]] = {}
            for evaluation in evaluations:
                if row_reasons[evaluation.evaluation_row_id]:
                    continue
                history_by_universe.setdefault(
                    evaluation.universe_id,
                    set(),
                ).add(evaluation.evaluation_at)
            for evaluation in evaluations:
                reasons = row_reasons[evaluation.evaluation_row_id]
                if reasons:
                    continue
                prior_history = {
                    timestamp
                    for timestamp in history_by_universe.get(
                        evaluation.universe_id,
                        set(),
                    )
                    if timestamp < evaluation.evaluation_at
                }
                if len(prior_history) < minimum:
                    reasons.add("partition_minimum_history_unmet")
    elif policy.get("kind") == "train_validation_test":
        try:
            train_end = parse_utc(policy["train_end_at"])
            validation_start = parse_utc(policy["validation_start_at"])
            validation_end = parse_utc(policy["validation_end_at"])
            test_start = parse_utc(policy["test_start_at"])
        except (KeyError, TypeError, ValueError):
            global_reasons.add("partition_schema_invalid")
        else:
            if (
                train_end > validation_start
                or validation_end > test_start
            ):
                global_reasons.add("partition_overlap")
            if not (
                train_end
                < validation_start
                < validation_end
                < test_start
            ):
                global_reasons.add("partition_order_invalid")
            if not global_reasons:
                for evaluation in evaluations:
                    reasons = row_reasons[
                        evaluation.evaluation_row_id
                    ]
                    if reasons.intersection(
                        {
                            "cutoff_evaluation_after_manifest",
                            "cutoff_evaluation_unavailable",
                            "membership_universe_undeclared",
                        }
                    ):
                        continue
                    at = evaluation.evaluation_at
                    if at <= train_end:
                        expected_partition = "train"
                    elif validation_start <= at <= validation_end:
                        expected_partition = "validation"
                    elif at >= test_start:
                        expected_partition = "test"
                    else:
                        expected_partition = None
                    if expected_partition is None:
                        reasons.add("partition_boundary_unassigned")
                    elif evaluation.partition != expected_partition:
                        reasons.add("partition_assignment_invalid")
    else:
        global_reasons.add("partition_policy_invalid")

    valid = (
        ()
        if global_reasons
        else tuple(
            evaluation
            for evaluation in evaluations
            if not row_reasons[evaluation.evaluation_row_id]
        )
    )
    return (
        valid,
        MappingProxyType(
            {
                row_id: tuple(sorted(reasons))
                for row_id, reasons in sorted(row_reasons.items())
            }
        ),
        tuple(sorted(global_reasons)),
    )


def _partition_validation(
    manifest,
    evaluations,
    extra_reasons=(),
    parsed: ParsedUniverseEvidence | None = None,
    *,
    source_index: RecordSourceIndex | None = None,
    evaluation_reasons: Mapping[str, tuple[str, ...]] | None = None,
    evaluation_global_reasons: tuple[str, ...] | None = None,
) -> tuple[Decision, tuple[ExcludedRow, ...]]:
    reasons = set(extra_reasons)
    exclusion_reasons: dict[int, tuple[object, set[str]]] = {}

    def exclude(evaluation, reason: str) -> None:
        if reason != "partition_minimum_history_unmet":
            reasons.add(reason)
        _, row_reasons = exclusion_reasons.setdefault(
            id(evaluation),
            (evaluation, set()),
        )
        row_reasons.add(reason)

    if (
        evaluation_reasons is None
        or evaluation_global_reasons is None
    ):
        _, validity_reasons, global_reasons = _classify_evaluations(
            manifest,
            evaluations,
        )
    else:
        validity_reasons = evaluation_reasons
        global_reasons = evaluation_global_reasons
    reasons.update(global_reasons)
    for evaluation in evaluations:
        for reason in validity_reasons[evaluation.evaluation_row_id]:
            if reason.startswith("partition_"):
                exclude(evaluation, reason)
    excluded = tuple(
        ExcludedRow(
            "evaluations",
            (
                source_index.source_row("evaluations", evaluation)
                if source_index is not None
                else 0
            ),
            evaluation.evaluation_row_id,
            tuple(sorted(row_reasons)),
        )
        for evaluation, row_reasons in sorted(
            exclusion_reasons.values(),
            key=lambda item: (
                item[0].evaluation_row_id,
                item[0].evaluation_at,
                item[0].source_ref,
            ),
        )
    )
    return (
        Decision(
            "leakage_safe",
            "blocked" if reasons else "passed",
            tuple(sorted(reasons)),
        ),
        excluded,
    )


def _partition_decision(
    manifest,
    evaluations,
    extra_reasons=(),
) -> Decision:
    return _partition_validation(
        manifest,
        evaluations,
        extra_reasons,
    )[0]


def _reproduction_decision(
    manifest,
    digests,
    evaluations=(),
) -> Decision:
    reasons: set[str] = set()
    if (
        getattr(
            manifest,
            "coverage_semantics",
            "complete_snapshot",
        )
        != "complete_snapshot"
    ):
        reasons.add("reproduction_coverage_semantics_unsupported")
    if (
        manifest.reproduction_contract
        != "membership_count_and_sha256_at_cutoff_v1"
    ):
        reasons.add("reproduction_contract_unsupported")
    keys = [
        (item.universe_id, item.evaluation_at)
        for item in digests
    ]
    if len(keys) != len(set(keys)):
        reasons.add("reproduction_duplicate_evaluation")
    if evaluations:
        manifest_cutoff = parse_utc(manifest.observation_cutoff_at)
        if any(
            evaluation.evaluation_at > manifest_cutoff
            for evaluation in evaluations
        ):
            reasons.add("reproduction_evaluation_after_manifest_cutoff")
        expected_keys = {
            (
                evaluation.universe_id,
                evaluation.evaluation_at.isoformat().replace(
                    "+00:00",
                    "Z",
                ),
            )
            for evaluation in evaluations
        }
        if (
            manifest.coverage_semantics == "complete_snapshot"
            and expected_keys - set(keys)
        ):
            reasons.add("reproduction_digest_missing")
    for item in digests:
        try:
            parse_utc(item.evaluation_at)
        except (TypeError, ValueError):
            valid_evaluation_at = False
        else:
            valid_evaluation_at = True
        if (
            not isinstance(item.universe_id, str)
            or not item.universe_id
            or not valid_evaluation_at
            or not isinstance(item.member_count, int)
            or isinstance(item.member_count, bool)
            or item.member_count < 0
            or not isinstance(item.sha256, str)
            or len(item.sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in item.sha256
            )
        ):
            reasons.add("reproduction_digest_invalid")
    return Decision(
        "reproduction_ready",
        "blocked" if reasons else "passed",
        tuple(sorted(reasons)),
    )


def _final_eligibility(
    decisions,
    digests,
    declared_universes,
) -> bool:
    if any(
        decision.status != "passed"
        and not (
            area == "delisting_coverage"
            and decision.status == "not_applicable"
        )
        for area, decision in decisions.items()
    ):
        return False
    kinds = {
        item["universe_id"]: item["universe_kind"]
        for item in declared_universes
    }
    eligible_ids = {
        digest.universe_id
        for digest in digests
        if digest.member_count > 0
    }
    return (
        any(kinds.get(item) == "benchmark" for item in eligible_ids)
        and any(
            kinds.get(item) == "research_universe"
            for item in eligible_ids
        )
    )


def _member_security_ids_for_evaluation(
    manifest,
    parsed,
    evaluation,
) -> EvaluationMemberScope:
    if manifest.coverage_semantics != "complete_snapshot":
        return EvaluationMemberScope(frozenset(), False)
    expected_kind = {
        item["universe_id"]: item["universe_kind"]
        for item in manifest.declared_universes
    }.get(evaluation.universe_id)
    if expected_kind is None:
        return EvaluationMemberScope(frozenset(), False)
    scoped_memberships = tuple(
        row
        for row in parsed.memberships
        if row.universe_id == evaluation.universe_id
    )
    cutoff_available = tuple(
        row
        for row in scoped_memberships
        if max(
            row.observation_at,
            row.source_published_at,
            row.retrieved_at,
        )
        <= evaluation.evaluation_at
    )
    latest_snapshot_at = max(
        (row.observation_at for row in cutoff_available),
        default=None,
    )
    if latest_snapshot_at is None:
        return EvaluationMemberScope(frozenset(), False)
    lineage = _compose_scoped_lineage(
        parsed.memberships,
        row_id=lambda row: row.membership_row_id,
        parent_id=lambda row: row.supersedes_membership_row_id,
        scope=lambda row: (row.universe_id, row.security_id),
        available_at=lambda row: max(
            row.observation_at,
            row.source_published_at,
            row.retrieved_at,
        ),
        cutoff=evaluation.evaluation_at,
    )
    universe_scope_invalid = any(
        record_scope[0] == evaluation.universe_id
        for record_scope in lineage.reasons_by_scope
    )
    security_ids = frozenset({
        row.security_id
        for row in lineage.leaves
        if (
            row.universe_id == evaluation.universe_id
            and row.universe_kind == expected_kind
            and row.observation_at == latest_snapshot_at
            and row.membership_state == "included"
            and _contains(
                row.effective_from,
                row.effective_to,
                evaluation.evaluation_at,
            )
        )
    })
    return EvaluationMemberScope(
        security_ids,
        bool(security_ids) and not universe_scope_invalid,
    )


def _event_touches_member(event, member_security_ids) -> bool:
    return (
        event.security_id in member_security_ids
        or (
            event.event_type in SUCCESSOR_EVENT_TYPES
            and event.successor_security_id in member_security_ids
        )
    )


def _state_event_matches_action(manifest, state_event, action) -> bool:
    return (
        state_event.event_type
        == RESTRICTIVE_LISTING_STATE_EVENT_TYPES[
            action.listing_state_after
        ]
        and state_event.security_id == action.security_id
        and state_event.effective_at == action.effective_at
        and state_event.listing_state_after == action.listing_state_after
        and manifest.corporate_action_policy.get(
            state_event.event_type
        )
        == "required"
    )


def _event_is_applicable(
    manifest,
    event,
    member_security_ids,
    restrictive_state_actions,
) -> bool:
    return (
        _event_touches_member(event, member_security_ids)
        or (
            event.event_type
            in RESTRICTIVE_LISTING_STATE_EVENT_TYPES.values()
            and any(
                _event_touches_member(action, member_security_ids)
                and _state_event_matches_action(
                    manifest,
                    event,
                    action,
                )
                for action in restrictive_state_actions
            )
        )
    )


def _event_decisions(
    manifest,
    parsed,
    source_index: RecordSourceIndex,
    evaluations,
) -> tuple[Decision, Decision, tuple[ExcludedRow, ...]]:
    action_reasons: set[str] = set()
    delisting_reasons: set[str] = set()
    exclusion_reasons: dict[tuple[int, str], set[str]] = {}
    listing_state_event_types = {
        "delisting",
        "suspension",
        "reactivation",
    }

    def target_reasons(event_type: str) -> set[str]:
        if event_type in listing_state_event_types:
            return delisting_reasons
        return action_reasons

    def exclude(event, *reasons: str) -> None:
        exclusion_reasons.setdefault(
            (
                source_index.source_row("events", event),
                event.event_row_id,
            ),
            set(),
        ).update(reasons)

    if any(
        finding.contract == "events"
        and "schema_delisting_listing_state_invalid"
        in finding.reason_codes
        for finding in parsed.findings
    ):
        delisting_reasons.add("delisting_state_invalid")

    evaluations = tuple(
        sorted(
            evaluations,
            key=lambda evaluation: (
                evaluation.evaluation_at,
                evaluation.universe_id,
                evaluation.evaluation_row_id,
            ),
        )
    )
    delisting_applicable = any(
        manifest.corporate_action_policy.get(event_type) == "required"
        for event_type in listing_state_event_types
    )
    covered_required_event_types: set[str] = set()
    required_member_scope_unresolved = False

    if not evaluations:
        for event_type, state in (
            manifest.corporate_action_policy.items()
        ):
            if state != "required":
                continue
            if event_type in listing_state_event_types:
                delisting_reasons.add("delisting_evidence_missing")
            else:
                action_reasons.add(
                    "corporate_action_evidence_missing"
                )

    for evaluation in evaluations:
        evaluation_at = evaluation.evaluation_at
        member_scope = _member_security_ids_for_evaluation(
            manifest,
            parsed,
            evaluation,
        )
        required_member_scope_unresolved = (
            required_member_scope_unresolved
            or not member_scope.resolved
        )
        member_security_ids = member_scope.security_ids
        lineage = _compose_scoped_lineage(
            parsed.events,
            row_id=lambda event: event.event_row_id,
            parent_id=lambda event: event.supersedes_event_row_id,
            scope=lambda event: (
                event.security_id,
                event.event_type,
            ),
            available_at=lambda event: max(
                event.effective_at,
                event.source_published_at,
                event.retrieved_at,
            ),
            cutoff=evaluation_at,
        )
        for reason, offenders in lineage.reason_records.items():
            for event in offenders:
                target_reasons(event.event_type).add(reason)
                exclude(event, reason)
        leaves = lineage.leaves

        identity_lineage = _compose_scoped_lineage(
            parsed.identities,
            row_id=lambda row: row.identity_row_id,
            parent_id=lambda row: row.supersedes_identity_row_id,
            scope=lambda row: row.security_id,
            available_at=lambda row: max(
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation_at,
        )
        identity_resolver = _effective_identity_resolver(
            parsed.identities,
            identity_lineage,
            evaluation_at,
        )
        identity_interval_history = identity_resolver.history
        identity_transition_requirements = (
            _identity_transition_event_requirements(
                identity_interval_history,
                evaluation_at,
            )
        )
        for identity, event_type in identity_transition_requirements:
            matching_event = any(
                event.event_type == event_type
                and event.security_id == identity.security_id
                and event.effective_at == identity.valid_from
                for event in leaves
            )
            if (
                manifest.corporate_action_policy.get(event_type)
                != "required"
                or not matching_event
            ):
                action_reasons.add("corporate_action_evidence_missing")

        restrictive_state_actions = tuple(
            event
            for event in leaves
            if (
                event.event_type != "listing"
                and event.event_type not in listing_state_event_types
                and event.listing_state_after
                in RESTRICTIVE_LISTING_STATE_EVENT_TYPES
            )
        )

        for action in restrictive_state_actions:
            if not any(
                _state_event_matches_action(
                    manifest,
                    event,
                    action,
                )
                for event in leaves
            ):
                delisting_reasons.add("delisting_evidence_missing")
                exclude(action, "delisting_evidence_missing")

        applicable_leaves = tuple(
            event
            for event in leaves
            if _event_is_applicable(
                manifest,
                event,
                member_security_ids,
                restrictive_state_actions,
            )
        )
        listing_state_by_security: dict[
            str,
            tuple[str, datetime],
        ] = {}
        listing_state_events: dict[
            tuple[str, datetime],
            list,
        ] = {}
        invalid_transition_ids: set[str] = set()
        for event in sorted(
            leaves,
            key=lambda item: (
                item.security_id,
                item.effective_at,
                item.event_row_id,
            ),
        ):
            reasons: set[str] = set()
            policy = manifest.corporate_action_policy.get(
                event.event_type
            )
            if policy == "unsupported":
                reasons.add("corporate_action_policy_unsupported")
            elif policy == "not_applicable":
                reasons.add(
                    "corporate_action_policy_not_applicable"
                )
            allowed_listing_states = (
                EVENT_LISTING_STATE_CONTRACT[event.event_type]
            )
            listing_state_valid = (
                event.listing_state_after
                in allowed_listing_states
            )
            if not listing_state_valid:
                if event.event_type in listing_state_event_types:
                    reasons.add(
                        "delisting_state_invalid"
                        if event.event_type == "delisting"
                        else "delisting_transition_invalid"
                    )
                else:
                    reasons.add(
                        "corporate_action_listing_state_invalid"
                    )
            if event.event_type in {"split", "reverse_split"} and (
                event.ratio_numerator is None
                or event.ratio_denominator is None
            ):
                reasons.add("corporate_action_ratio_required")
            if event.event_type in SUCCESSOR_EVENT_TYPES:
                predecessor_scope_invalid = (
                    event.security_id
                    in identity_lineage.reasons_by_scope
                ) or identity_resolver.security_scope_invalid(
                    event.security_id
                )
                (
                    active_predecessor_identities,
                    active_successor_identities,
                ) = _event_identity_endpoints(
                    event,
                    identity_resolver,
                )
                predecessor_identity_resolved = True
                predecessor_identity_reason = ""
                if (
                    predecessor_scope_invalid
                    or len(active_predecessor_identities) > 1
                ):
                    predecessor_identity_resolved = False
                    predecessor_identity_reason = (
                        "corporate_action_predecessor_identity_ambiguous"
                    )
                elif not active_predecessor_identities:
                    predecessor_identity_resolved = False
                    predecessor_identity_reason = (
                        "corporate_action_predecessor_identity_missing"
                    )
                successor = event.successor_security_id
                if not successor:
                    reasons.add(
                        "corporate_action_successor_required"
                    )
                elif successor == event.security_id:
                    reasons.add("corporate_action_successor_self")
                elif (
                    successor.casefold()
                    in INVALID_SUCCESSOR_IDENTIFIERS
                ):
                    reasons.add(
                        "corporate_action_successor_invalid"
                    )
                else:
                    successor_scope_invalid = (
                        successor
                        in identity_lineage.reasons_by_scope
                    ) or identity_resolver.security_scope_invalid(
                        successor
                    )
                    if (
                        successor_scope_invalid
                        or len(active_successor_identities) > 1
                    ):
                        reasons.add(
                            "corporate_action_successor_identity_ambiguous"
                        )
                    elif not active_successor_identities:
                        reasons.add(
                            "corporate_action_successor_identity_missing"
                        )
                    else:
                        if predecessor_identity_reason:
                            reasons.add(predecessor_identity_reason)
                        if (
                            event.event_type
                            in REPLACEMENT_SUCCESSOR_EVENT_TYPES
                            and event.security_id in member_security_ids
                            and predecessor_identity_resolved
                        ):
                            reasons.add(
                                "corporate_action_successor_"
                                "membership_inconsistent"
                            )
            if (
                event.event_type
                in {
                    "listing",
                    "delisting",
                    "suspension",
                    "reactivation",
                }
                and event.listing_state_after
                and listing_state_valid
            ):
                listing_state_events.setdefault(
                    (event.security_id, event.effective_at),
                    [],
                ).append(event)
            if reasons:
                target_reasons(event.event_type).update(reasons)
                exclude(event, *reasons)
                if "delisting_transition_invalid" in reasons:
                    invalid_transition_ids.add(event.event_row_id)

        for (
            security_id,
            effective_at,
        ), simultaneous_events in sorted(
            listing_state_events.items()
        ):
            states = {
                event.listing_state_after
                for event in simultaneous_events
            }
            if len(states) > 1 or len(simultaneous_events) > 1:
                delisting_reasons.add(
                    "delisting_transition_invalid"
                )
                for event in simultaneous_events:
                    exclude(event, "delisting_transition_invalid")
                continue
            if any(
                event.event_row_id in invalid_transition_ids
                for event in simultaneous_events
            ):
                continue
            prior_listing_state = listing_state_by_security.get(
                security_id
            )
            allowed_prior_states = {
                "listing": {None, "delisted"},
                "suspension": {None, "active"},
                "reactivation": {"suspended"},
                "delisting": {None, "active", "suspended"},
            }
            invalid_transitions = tuple(
                event
                for event in simultaneous_events
                if (
                    (
                        None
                        if prior_listing_state is None
                        else prior_listing_state[0]
                    )
                    not in allowed_prior_states[event.event_type]
                    or (
                        prior_listing_state is not None
                        and prior_listing_state[1] >= effective_at
                    )
                )
            )
            if invalid_transitions:
                delisting_reasons.add(
                    "delisting_transition_invalid"
                )
                for event in invalid_transitions:
                    exclude(event, "delisting_transition_invalid")
                continue
            listing_state_by_security[security_id] = (
                next(iter(states)),
                effective_at,
            )

        for event_type, state in (
            manifest.corporate_action_policy.items()
        ):
            if state != "required":
                continue
            if member_scope.resolved and any(
                    event.event_type == event_type
                    and _event_is_applicable(
                        manifest,
                        event,
                        member_security_ids,
                        restrictive_state_actions,
                    )
                    for event in leaves
            ):
                covered_required_event_types.add(event_type)
        delisting_applicable = (
            delisting_applicable
            or bool(restrictive_state_actions)
            or any(
                event.event_type in listing_state_event_types
                for event in applicable_leaves
            )
        )

    if evaluations:
        for event_type, state in (
            manifest.corporate_action_policy.items()
        ):
            if (
                state != "required"
                or (
                    not required_member_scope_unresolved
                    and event_type in covered_required_event_types
                )
            ):
                continue
            if event_type in listing_state_event_types:
                delisting_reasons.add("delisting_evidence_missing")
            else:
                action_reasons.add(
                    "corporate_action_evidence_missing"
                )

    if manifest.delisting_policy.get("retain_historical_members") is not True:
        delisting_reasons.add("delisting_survivorship_policy_invalid")
    if (
        manifest.survivorship_policy.get("filter_by_current_listing_state")
        is not False
    ):
        delisting_reasons.add("delisting_survivorship_policy_invalid")
    excluded = tuple(
        ExcludedRow(
            "events",
            source_row,
            row_id,
            tuple(sorted(reasons)),
        )
        for (
            source_row,
            row_id,
        ), reasons in sorted(exclusion_reasons.items())
    )
    return (
        Decision(
            "corporate_action_coverage",
            "blocked" if action_reasons else "passed",
            tuple(sorted(action_reasons)),
        ),
        Decision(
            "delisting_coverage",
            "blocked"
            if delisting_reasons
            else "passed"
            if delisting_applicable
            else "not_applicable",
            tuple(sorted(delisting_reasons)),
        ),
        excluded,
    )


def _raw_required_rights_scope(row) -> tuple[str, ...] | None:
    if row.contract == "security_identity":
        return ("security_identity",)
    if row.contract == "membership":
        return ("universe_membership",)
    if row.contract != "events":
        return ()
    event_type = row.values.get("event_type", "")
    if event_type == "delisting":
        return ("delistings",)
    if event_type in {"suspension", "reactivation"}:
        return ("corporate_actions", "delistings")
    if event_type in EVENT_TYPES:
        return ("corporate_actions",)
    return None


def _rights_decision(
    manifest,
    parsed,
    registry,
) -> tuple[Decision, tuple[ExcludedRow, ...]]:
    blockers: set[str] = set()
    row_blockers: dict[tuple[str, int, str], set[str]] = {}

    def block(row, reason: str) -> None:
        blockers.add(reason)
        row_id = row.values.get(ROW_ID_FIELDS[row.contract], "")
        row_blockers.setdefault(
            (row.contract, row.source_row, row_id),
            set(),
        ).add(reason)

    source_rows = tuple(
        row
        for row in parsed.raw
        if row.contract in {"security_identity", "membership", "events"}
    )
    for row in source_rows:
        source_id = row.values.get("source_id", RAW_MISSING_CELL)
        if source_id == "":
            block(row, "source_rights_source_missing")
            continue
        if (
            source_id == RAW_MISSING_CELL
            or source_id != source_id.strip()
            or not is_control_free(source_id)
        ):
            block(row, "source_rights_source_unreadable")
            continue
        if source_id not in manifest.allowed_source_ids:
            block(row, "source_rights_source_not_allowed")
        required_scope = _raw_required_rights_scope(row)
        if required_scope is None:
            block(row, "source_rights_event_scope_unreadable")
            required_scope = ()
        review = review_commercial_field_scope(
            registry,
            source_id,
            required_scope,
        )
        if not review.commercial_rights_approved:
            block(row, f"source_rights_{review.rights_status}")
        if review.missing_supported_fields:
            block(row, "source_rights_field_scope_missing")

    raw_locations = {
        (row.contract, row.source_row)
        for row in source_rows
    }
    for finding in parsed.findings:
        if (
            finding.contract
            in {"security_identity", "membership", "events"}
            and "schema_columns_invalid" in finding.reason_codes
            and (finding.contract, finding.source_row)
            not in raw_locations
        ):
            blockers.add("source_rights_source_unreadable")
            row_blockers.setdefault(
                (
                    finding.contract,
                    finding.source_row,
                    finding.row_id,
                ),
                set(),
            ).add("source_rights_source_unreadable")

    return (
        Decision(
            "source_rights_eligibility",
            "blocked" if blockers else "passed",
            tuple(sorted(blockers)),
        ),
        tuple(
            ExcludedRow(
                contract,
                source_row,
                row_id,
                tuple(sorted(reasons)),
            )
            for (
                contract,
                source_row,
                row_id,
            ), reasons in sorted(row_blockers.items())
        ),
    )


def _row_reference(
    source_index: RecordSourceIndex,
    contract: str,
    record,
    *,
    evaluation_row_id: str = "",
) -> RowReference:
    return RowReference(
        contract,
        source_index.source_row(contract, record),
        _record_row_id(contract, record),
        evaluation_row_id,
    )


def _complete_row_references(
    parsed: ParsedUniverseEvidence,
) -> tuple[tuple[RowReference, ...], tuple[RowReference, ...]]:
    raw_rows = tuple(
        RowReference(
            row.contract,
            row.source_row,
            row.values.get(ROW_ID_FIELDS[row.contract], ""),
        )
        for row in parsed.raw
    )
    finding_rows = {
        (finding.contract, finding.source_row)
        for finding in parsed.findings
    }
    normalized_rows = tuple(
        row
        for row in raw_rows
        if (row.contract, row.source_row) not in finding_rows
    )
    return raw_rows, normalized_rows


def _analysis_row_references(
    manifest: UniverseManifest,
    parsed: ParsedUniverseEvidence,
    source_index: RecordSourceIndex,
    evaluations,
) -> tuple[RowReference, ...]:
    references: set[RowReference] = set()
    declared = {
        item["universe_id"]: item["universe_kind"]
        for item in manifest.declared_universes
    }
    for evaluation in sorted(
        evaluations,
        key=lambda row: (
            row.evaluation_at,
            row.universe_id,
            row.evaluation_row_id,
        ),
    ):
        evaluation_row_id = evaluation.evaluation_row_id
        references.add(
            _row_reference(
                source_index,
                "evaluations",
                evaluation,
                evaluation_row_id=evaluation_row_id,
            )
        )
        membership_lineage = _compose_scoped_lineage(
            parsed.memberships,
            row_id=lambda row: row.membership_row_id,
            parent_id=lambda row: row.supersedes_membership_row_id,
            scope=lambda row: (row.universe_id, row.security_id),
            available_at=lambda row: max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        identity_lineage = _compose_scoped_lineage(
            parsed.identities,
            row_id=lambda row: row.identity_row_id,
            parent_id=lambda row: row.supersedes_identity_row_id,
            scope=lambda row: row.security_id,
            available_at=lambda row: max(
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        if (
            membership_lineage.reason_codes
            or identity_lineage.reason_codes
        ):
            return ()
        identity_resolver = _effective_identity_resolver(
            parsed.identities,
            identity_lineage,
            evaluation.evaluation_at,
        )
        if identity_resolver.invalid_scopes:
            return ()

        cutoff_memberships = tuple(
            row
            for row in parsed.memberships
            if (
                row.universe_id == evaluation.universe_id
                and max(
                    row.observation_at,
                    row.source_published_at,
                    row.retrieved_at,
                )
                <= evaluation.evaluation_at
            )
        )
        latest_snapshot_at = max(
            (row.observation_at for row in cutoff_memberships),
            default=None,
        )
        expected_kind = declared.get(evaluation.universe_id)
        member_leaves = tuple(
            row
            for row in membership_lineage.leaves
            if (
                row.universe_id == evaluation.universe_id
                and row.universe_kind == expected_kind
                and row.observation_at == latest_snapshot_at
                and row.membership_state == "included"
                and _contains(
                    row.effective_from,
                    row.effective_to,
                    evaluation.evaluation_at,
                )
            )
        )
        member_security_ids: set[str] = set()
        for member in member_leaves:
            active_identities = identity_resolver.active_at(
                member.security_id,
                evaluation.evaluation_at,
            )
            if len(active_identities) != 1:
                return ()
            active_identity = active_identities[0]
            member_security_ids.add(member.security_id)
            references.add(
                _row_reference(
                    source_index,
                    "membership",
                    member,
                    evaluation_row_id=evaluation_row_id,
                )
            )
            references.add(
                _row_reference(
                    source_index,
                    "security_identity",
                    active_identity,
                    evaluation_row_id=evaluation_row_id,
                )
            )

        event_lineage = _compose_scoped_lineage(
            parsed.events,
            row_id=lambda event: event.event_row_id,
            parent_id=lambda event: event.supersedes_event_row_id,
            scope=lambda event: (
                event.security_id,
                event.event_type,
            ),
            available_at=lambda event: max(
                event.effective_at,
                event.source_published_at,
                event.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        if event_lineage.reason_codes:
            return ()
        restrictive_state_actions = tuple(
            event
            for event in event_lineage.leaves
            if (
                event.event_type != "listing"
                and event.event_type
                not in RESTRICTIVE_LISTING_STATE_EVENT_TYPES.values()
                and event.listing_state_after
                in RESTRICTIVE_LISTING_STATE_EVENT_TYPES
            )
        )
        for event in event_lineage.leaves:
            if not _event_is_applicable(
                manifest,
                event,
                member_security_ids,
                restrictive_state_actions,
            ):
                continue
            references.add(
                _row_reference(
                    source_index,
                    "events",
                    event,
                    evaluation_row_id=evaluation_row_id,
                )
            )
            predecessors, successors = _event_identity_endpoints(
                event,
                identity_resolver,
            )
            if event.event_type in SUCCESSOR_EVENT_TYPES and (
                len(predecessors) != 1
                or len(successors) != 1
            ):
                return ()
            for endpoint_identity in predecessors + successors:
                references.add(
                    _row_reference(
                        source_index,
                        "security_identity",
                        endpoint_identity,
                        evaluation_row_id=evaluation_row_id,
                    )
                )

    return tuple(
        sorted(
            references,
            key=lambda row: (
                row.evaluation_row_id,
                row.contract,
                row.source_row,
                row.row_id,
            ),
        )
    )


def validate_point_in_time_universe(
    manifest_path: Path,
    registry_path: Path,
    *,
    top_n: int = 20,
) -> PointInTimeUniversePacket:
    _validate_top_n(top_n)

    package = load_universe_package(manifest_path, registry_path)
    parsed = parse_universe_evidence(package)
    source_index = _build_record_source_index(parsed)
    decisions: dict[str, Decision] = {}
    excluded: list[ExcludedRow] = [
        ExcludedRow(
            finding.contract,
            finding.source_row,
            finding.row_id,
            finding.reason_codes,
        )
        for finding in parsed.findings
    ]
    decisions["manifest_integrity"] = Decision(
        "manifest_integrity",
        "passed",
        (),
    )
    decisions["technical_validity"] = Decision(
        "technical_validity",
        "blocked" if parsed.findings else "passed",
        tuple(
            sorted(
                {
                    code
                    for finding in parsed.findings
                    for code in finding.reason_codes
                }
            )
        ),
    )
    (
        valid_evaluations,
        evaluation_reasons,
        evaluation_global_reasons,
    ) = _classify_evaluations(
        package.manifest,
        parsed.evaluations,
    )
    identity, membership, digests, display, composed_excluded = (
        _identity_membership_decisions(
            package.manifest,
            parsed,
            source_index,
            valid_evaluations,
            evaluation_reasons,
        )
    )
    decisions[identity.area] = identity
    decisions[membership.area] = membership
    excluded.extend(composed_excluded)
    temporal, cutoff_leakage, temporal_excluded = _temporal_decision(
        package.manifest,
        parsed,
        source_index,
        valid_evaluations,
        evaluation_reasons,
    )
    decisions[temporal.area] = temporal
    excluded.extend(temporal_excluded)
    corporate_action, delisting, event_excluded = _event_decisions(
        package.manifest,
        parsed,
        source_index,
        valid_evaluations,
    )
    source_rights, rights_excluded = _rights_decision(
        package.manifest,
        parsed,
        parse_source_rights_registry(package.registry_snapshot),
    )
    decisions[corporate_action.area] = corporate_action
    decisions[delisting.area] = delisting
    decisions[source_rights.area] = source_rights
    excluded.extend(event_excluded)
    excluded.extend(rights_excluded)
    reproduction = _reproduction_decision(
        package.manifest,
        digests,
        valid_evaluations,
    )
    decisions[reproduction.area] = reproduction
    leakage, partition_excluded = _partition_validation(
        package.manifest,
        parsed.evaluations,
        cutoff_leakage,
        parsed,
        source_index=source_index,
        evaluation_reasons=evaluation_reasons,
        evaluation_global_reasons=evaluation_global_reasons,
    )
    decisions[leakage.area] = leakage
    excluded.extend(partition_excluded)
    ordered_decisions = MappingProxyType(
        {
            name: decisions[name]
            for name in DECISION_ORDER
        }
    )
    canonical_exclusion_reasons: dict[
        tuple[str, int, str],
        set[str],
    ] = {}
    for item in excluded:
        canonical_exclusion_reasons.setdefault(
            (item.contract, item.source_row, item.row_id),
            set(),
        ).update(item.reason_codes)
    canonical_excluded = tuple(
        ExcludedRow(
            contract,
            source_row,
            row_id,
            tuple(sorted(reason_codes)),
        )
        for (
            contract,
            source_row,
            row_id,
        ), reason_codes in sorted(canonical_exclusion_reasons.items())
    )
    raw_rows, normalized_rows = _complete_row_references(parsed)
    exclusion_reason_counts = MappingProxyType(
        dict(
            sorted(
                Counter(
                    reason
                    for item in canonical_excluded
                    for reason in item.reason_codes
                ).items()
            )
        )
    )
    analysis_eligible = _final_eligibility(
        ordered_decisions,
        digests,
        package.manifest.declared_universes,
    )
    analysis_eligible_rows = (
        _analysis_row_references(
            package.manifest,
            parsed,
            source_index,
            valid_evaluations,
        )
        if analysis_eligible
        else ()
    )

    return PointInTimeUniversePacket(
        dataset_id=package.manifest.dataset_id,
        manifest_id=package.manifest.manifest_id,
        analysis_eligible=analysis_eligible,
        decisions=ordered_decisions,
        raw_count=len(raw_rows),
        normalized_count=len(normalized_rows),
        raw_rows=raw_rows,
        normalized_rows=normalized_rows,
        excluded=canonical_excluded,
        excluded_count=len(canonical_excluded),
        exclusion_reason_counts=exclusion_reason_counts,
        analysis_eligible_rows=analysis_eligible_rows,
        analysis_eligible_row_count=len(analysis_eligible_rows),
        membership_digests=digests,
        display_tickers=display,
        boundary=(
            "Local evidence eligibility only; no readiness, backtest, probability, "
            "recommendation, or trading activation."
        ),
    )


def render_status(packet: PointInTimeUniversePacket) -> str:
    token = escape_structural_token
    lines = [
        "Point-in-Time Universe Status",
        (
            "Read-only: validates one supplied immutable package; it does not "
            "fetch, write, apply, refresh, or rebuild data."
        ),
        (
            "Research-only: this does not activate readiness, backtesting, "
            "calibration, or probability and is not investment advice."
        ),
        (
            "Synthetic or technically valid packages are local software "
            "evidence only."
        ),
        (
            "Priority 4 still requires one independently reviewed, permitted "
            "real dataset."
        ),
        f"dataset_id: {token(packet.dataset_id)}",
        f"manifest_id: {token(packet.manifest_id)}",
        f"analysis_eligible: {str(packet.analysis_eligible).lower()}",
        f"raw_count: {packet.raw_count}",
        f"normalized_count: {packet.normalized_count}",
        f"excluded_count: {packet.excluded_count}",
        (
            "analysis_eligible_row_count: "
            f"{packet.analysis_eligible_row_count}"
        ),
    ]
    lines.extend(
        (
            f"{name}: {token(packet.decisions[name].status)}; "
            "reasons="
            f"{','.join(token(reason) for reason in packet.decisions[name].reason_codes) or 'none'}"
        )
        for name in DECISION_ORDER
    )
    lines.append(f"boundary: {token(packet.boundary)}")
    return "\n".join(lines)


def render_preview(
    packet: PointInTimeUniversePacket,
    *,
    top_n: int = 20,
) -> str:
    _validate_top_n(top_n)
    token = escape_structural_token

    lines = [render_status(packet), "", "Membership reproduction:"]
    lines.extend(
        (
            f"- {token(item.universe_id)} @ {token(item.evaluation_at)}: "
            f"members={item.member_count}; sha256={token(item.sha256)}"
        )
        for item in packet.membership_digests
    )
    lines.append("Exclusion reason counts:")
    if packet.exclusion_reason_counts:
        lines.extend(
            f"- {token(reason)}: {count}"
            for reason, count in packet.exclusion_reason_counts.items()
        )
    else:
        lines.append("- none")
    lines.append("Excluded sample:")
    lines.extend(
        (
            f"- {token(item.contract)}:{item.source_row}:"
            f"{token(item.row_id)}; "
            f"reasons={','.join(token(reason) for reason in item.reason_codes)}"
        )
        for item in packet.excluded[:top_n]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import csv

    import yaml

    parser = argparse.ArgumentParser(
        description="Validate one immutable point-in-time universe package."
    )
    parser.add_argument("mode", choices=("status", "preview"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("config/source_rights.yml"),
    )
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args(argv)
    if args.manifest is None:
        parser.error("MANIFEST is required")
    if args.top_n < 0 or args.top_n > MAX_PREVIEW_EXCLUSION_ROWS:
        parser.error("top_n_invalid")

    try:
        packet = validate_point_in_time_universe(
            args.manifest,
            args.registry,
            top_n=args.top_n,
        )
    except (csv.Error, OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    except RuntimeError as exc:
        if "Symlink loop" not in str(exc):
            raise
        parser.error(str(exc))

    output = (
        render_preview(packet, top_n=args.top_n)
        if args.mode == "preview"
        else render_status(packet)
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
