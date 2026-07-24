from __future__ import annotations

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
    IdentityObservation,
    ParsedUniverseEvidence,
    parse_universe_evidence,
    parse_utc,
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


def _row_number(
    parsed: ParsedUniverseEvidence,
    contract: str,
    row_id: str,
) -> int:
    id_field = {
        "security_identity": "identity_row_id",
        "membership": "membership_row_id",
        "events": "event_row_id",
        "evaluations": "evaluation_row_id",
    }[contract]
    return next(
        (
            row.source_row
            for row in parsed.raw
            if row.contract == contract and row.values.get(id_field) == row_id
        ),
        0,
    )


def _identity_membership_decisions(
    manifest: UniverseManifest,
    parsed: ParsedUniverseEvidence,
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
    cutoff = parse_utc(manifest.observation_cutoff_at)
    complete_snapshot_supported = (
        manifest.coverage_semantics == "complete_snapshot"
    )
    if not complete_snapshot_supported:
        membership_reasons.add(
            "membership_coverage_semantics_unsupported"
        )
    evaluations = tuple(
        sorted(
            (
                item
                for item in parsed.evaluations
                if item.evaluation_at <= cutoff
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

    for row in parsed.memberships:
        expected_kind = declared.get(row.universe_id)
        if expected_kind is None:
            membership_reasons.add("membership_universe_undeclared")
        elif row.universe_kind != expected_kind:
            membership_reasons.add("membership_universe_kind_mismatch")

    for evaluation in evaluations:
        membership_lineage = resolve_lineage(
            parsed.memberships,
            row_id=lambda row: row.membership_row_id,
            parent_id=lambda row: row.supersedes_membership_row_id,
            scope=lambda row: f"{row.universe_id}:{row.security_id}",
            available_at=lambda row: max(
                row.observation_at,
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        membership_reasons.update(membership_lineage.reason_codes)
        identity_lineage = resolve_lineage(
            parsed.identities,
            row_id=lambda row: row.identity_row_id,
            parent_id=lambda row: row.supersedes_identity_row_id,
            scope=lambda row: f"{row.security_id}:{row.issuer_id}",
            available_at=lambda row: max(
                row.source_published_at,
                row.retrieved_at,
            ),
            cutoff=evaluation.evaluation_at,
        )
        identity_reasons.update(identity_lineage.reason_codes)

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
        overlapping_identity_security_ids: set[str] = set()
        if not identity_lineage.reason_codes:
            available_identity_by_security: dict[str, list] = {}
            for row in parsed.identities:
                if (
                    max(row.source_published_at, row.retrieved_at)
                    <= evaluation.evaluation_at
                ):
                    available_identity_by_security.setdefault(
                        row.security_id,
                        [],
                    ).append(row)
            for security_id, identity_rows in (
                available_identity_by_security.items()
            ):
                active = tuple(
                    row
                    for row in identity_rows
                    if _contains(
                        row.valid_from,
                        row.valid_to,
                        evaluation.evaluation_at,
                    )
                )
                if len(active) > 1:
                    identity_reasons.add("identity_interval_overlap")
                    overlapping_identity_security_ids.add(security_id)
                elif len(active) == 1:
                    active_identity_by_security[security_id] = active[0]

        members: set[str] = set()
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
                    ExcludedRow(
                        "membership",
                        _row_number(
                            parsed,
                            "membership",
                            leaf.membership_row_id,
                        ),
                        leaf.membership_row_id,
                        ("membership_interval_inactive",),
                    )
                )
                continue
            if leaf.membership_state == "excluded":
                continue

            security_id = leaf.security_id
            members.add(security_id)
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
            if identity_lineage.reason_codes:
                if is_latest_display:
                    display_candidates[security_id] = (
                        evaluation_key,
                        None,
                    )
                excluded.append(
                    ExcludedRow(
                        "membership",
                        _row_number(
                            parsed,
                            "membership",
                            leaf.membership_row_id,
                        ),
                        leaf.membership_row_id,
                        identity_lineage.reason_codes,
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
                    ExcludedRow(
                        "membership",
                        _row_number(
                            parsed,
                            "membership",
                            leaf.membership_row_id,
                        ),
                        leaf.membership_row_id,
                        ("identity_interval_overlap",),
                    )
                )
                continue

            active_identity = active_identity_by_security.get(security_id)
            if active_identity is None:
                identity_rows = tuple(
                    row
                    for row in parsed.identities
                    if row.security_id == security_id
                )
                if identity_rows and not any(
                    max(row.source_published_at, row.retrieved_at)
                    <= evaluation.evaluation_at
                    for row in identity_rows
                ):
                    if is_latest_display:
                        display_candidates[security_id] = (
                            evaluation_key,
                            None,
                        )
                    continue
                identity_reasons.add("identity_missing")
                if is_latest_display:
                    display_candidates[security_id] = (
                        evaluation_key,
                        None,
                    )
                excluded.append(
                    ExcludedRow(
                        "membership",
                        _row_number(
                            parsed,
                            "membership",
                            leaf.membership_row_id,
                        ),
                        leaf.membership_row_id,
                        ("identity_missing",),
                    )
                )
                continue

            if is_latest_display:
                display_candidates[security_id] = (
                    evaluation_key,
                    active_identity.ticker,
                )

        if not members and (
            not scoped_memberships or cutoff_available_memberships
        ):
            membership_reasons.add("membership_no_eligible_members")
        digests.append(
            _membership_digest(
                evaluation.universe_id,
                evaluation.evaluation_at.isoformat().replace("+00:00", "Z"),
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
) -> tuple[Decision, tuple[str, ...], tuple[ExcludedRow, ...]]:
    temporal_reasons: set[str] = set()
    leakage_reasons: set[str] = set()
    exclusion_reasons: dict[tuple[str, str], set[str]] = {}
    manifest_cutoff = parse_utc(manifest.observation_cutoff_at)

    def record_exclusion(
        contract: str,
        row_id: str,
        *reason_codes: str,
    ) -> None:
        exclusion_reasons.setdefault((contract, row_id), set()).update(
            reason_codes
        )

    for evaluation in parsed.evaluations:
        if evaluation.evaluation_at > manifest_cutoff:
            temporal_reasons.add("cutoff_evaluation_after_manifest")
            leakage_reasons.add(
                "leakage_evaluation_after_manifest_cutoff"
            )
            record_exclusion(
                "evaluations",
                evaluation.evaluation_row_id,
                "cutoff_evaluation_after_manifest",
                "leakage_evaluation_after_manifest_cutoff",
                "reproduction_evaluation_after_manifest_cutoff",
            )
            continue
        if evaluation.available_at > evaluation.evaluation_at:
            temporal_reasons.add("cutoff_evaluation_unavailable")
            leakage_reasons.add("leakage_evaluation_available_late")
            record_exclusion(
                "evaluations",
                evaluation.evaluation_row_id,
                "cutoff_evaluation_unavailable",
                "leakage_evaluation_available_late",
            )

        def classify_scope(
            contract,
            rows,
            available_at,
            row_id,
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
                        row_id(row),
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
                record_exclusion(contract, row_id(row), reason)

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
                lambda row: row.membership_row_id,
                required=(
                    not cutoff_available_memberships
                    or group[0].security_id
                    in latest_snapshot_security_ids
                ),
            )

        membership_lineage = resolve_lineage(
            parsed.memberships,
            row_id=lambda row: row.membership_row_id,
            parent_id=lambda row: row.supersedes_membership_row_id,
            scope=lambda row: f"{row.universe_id}:{row.security_id}",
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
                lambda row: row.identity_row_id,
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
                lambda row: row.event_row_id,
                required=(
                    security_id in member_security_ids
                    and manifest.corporate_action_policy.get(event_type)
                    == "required"
                ),
            )

    excluded = tuple(
        ExcludedRow(
            contract,
            _row_number(parsed, contract, row_id),
            row_id,
            tuple(sorted(reasons)),
        )
        for (contract, row_id), reasons in sorted(
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


def _partition_validation(
    manifest,
    evaluations,
    extra_reasons=(),
    parsed: ParsedUniverseEvidence | None = None,
) -> tuple[Decision, tuple[ExcludedRow, ...]]:
    reasons = set(extra_reasons)
    exclusion_reasons: dict[str, set[str]] = {}

    def exclude(evaluation, reason: str) -> None:
        reasons.add(reason)
        exclusion_reasons.setdefault(
            evaluation.evaluation_row_id,
            set(),
        ).add(reason)

    manifest_cutoff = (
        parse_utc(manifest.observation_cutoff_at)
        if hasattr(manifest, "observation_cutoff_at")
        else None
    )
    cutoff_evaluations = tuple(
        evaluation
        for evaluation in evaluations
        if (
            manifest_cutoff is None
            or evaluation.evaluation_at <= manifest_cutoff
        )
    )
    policy = manifest.evaluation_policy
    if not isinstance(policy, Mapping):
        reasons.add("partition_policy_invalid")
    elif policy.get("kind") == "walk_forward":
        minimum = policy.get("minimum_history_count")
        if (
            not isinstance(minimum, int)
            or isinstance(minimum, bool)
            or minimum <= 0
        ):
            reasons.add("partition_minimum_history_invalid")
        else:
            history_by_universe: dict[str, set[datetime]] = {}
            for evaluation in cutoff_evaluations:
                if evaluation.partition != "walk_forward":
                    exclude(evaluation, "partition_assignment_invalid")
                history_by_universe.setdefault(
                    evaluation.universe_id,
                    set(),
                ).add(evaluation.evaluation_at)
            for evaluation in cutoff_evaluations:
                if (
                    len(history_by_universe[evaluation.universe_id])
                    < minimum
                ):
                    exclude(
                        evaluation,
                        "partition_minimum_history_unmet",
                    )
    elif policy.get("kind") == "train_validation_test":
        try:
            train_end = parse_utc(policy["train_end_at"])
            validation_start = parse_utc(policy["validation_start_at"])
            validation_end = parse_utc(policy["validation_end_at"])
            test_start = parse_utc(policy["test_start_at"])
        except (KeyError, TypeError, ValueError):
            reasons.add("partition_schema_invalid")
        else:
            if (
                train_end > validation_start
                or validation_end > test_start
            ):
                reasons.add("partition_overlap")
            if not (
                train_end
                < validation_start
                < validation_end
                < test_start
            ):
                reasons.add("partition_order_invalid")
            if not reasons.intersection(
                {
                    "partition_overlap",
                    "partition_order_invalid",
                }
            ):
                for evaluation in cutoff_evaluations:
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
                        exclude(
                            evaluation,
                            "partition_boundary_unassigned",
                        )
                    elif evaluation.partition != expected_partition:
                        exclude(
                            evaluation,
                            "partition_assignment_invalid",
                        )
    else:
        reasons.add("partition_policy_invalid")
    excluded = tuple(
        ExcludedRow(
            "evaluations",
            (
                _row_number(parsed, "evaluations", row_id)
                if parsed is not None
                else 0
            ),
            row_id,
            tuple(sorted(row_reasons)),
        )
        for row_id, row_reasons in sorted(exclusion_reasons.items())
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


def _event_decisions(
    manifest,
    parsed,
) -> tuple[Decision, Decision, tuple[ExcludedRow, ...]]:
    action_reasons: set[str] = set()
    delisting_reasons: set[str] = set()
    exclusion_reasons: dict[str, set[str]] = {}
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
            event.event_row_id,
            set(),
        ).update(reasons)

    if any(
        finding.contract == "events"
        and "schema_delisting_listing_state_invalid"
        in finding.reason_codes
        for finding in parsed.findings
    ):
        delisting_reasons.add("delisting_state_invalid")

    manifest_cutoff = parse_utc(manifest.observation_cutoff_at)
    evaluation_cutoffs = tuple(
        sorted(
            {
                evaluation.evaluation_at
                for evaluation in parsed.evaluations
                if (
                    evaluation.evaluation_at <= manifest_cutoff
                    and evaluation.available_at <= evaluation.evaluation_at
                )
            }
        )
    )
    delisting_applicable = any(
        manifest.corporate_action_policy.get(event_type) == "required"
        for event_type in listing_state_event_types
    )

    for evaluation_at in evaluation_cutoffs:
        visible_events = tuple(
            event
            for event in parsed.events
            if max(
                event.effective_at,
                event.source_published_at,
                event.retrieved_at,
            )
            <= evaluation_at
        )
        visible_by_id = {
            event.event_row_id: event
            for event in visible_events
        }
        events_by_scope: dict[tuple[str, str], list] = {}
        for event in visible_events:
            events_by_scope.setdefault(
                (event.security_id, event.event_type),
                [],
            ).append(event)

        leaves: list = []
        for scope, scope_events in sorted(events_by_scope.items()):
            cross_scope_events = tuple(
                event
                for event in scope_events
                if (
                    event.supersedes_event_row_id
                    and event.supersedes_event_row_id in visible_by_id
                    and (
                        visible_by_id[
                            event.supersedes_event_row_id
                        ].security_id,
                        visible_by_id[
                            event.supersedes_event_row_id
                        ].event_type,
                    )
                    != scope
                )
            )
            if cross_scope_events:
                target_reasons(scope[1]).add(
                    "lineage_cross_scope_parent"
                )
                for event in cross_scope_events:
                    exclude(event, "lineage_cross_scope_parent")
                continue

            lineage = resolve_lineage(
                scope_events,
                row_id=lambda event: event.event_row_id,
                parent_id=lambda event: event.supersedes_event_row_id,
                scope=lambda event: (
                    f"{event.security_id}:{event.event_type}"
                ),
                available_at=lambda event: max(
                    event.effective_at,
                    event.source_published_at,
                    event.retrieved_at,
                ),
                cutoff=evaluation_at,
            )
            if lineage.reason_codes:
                target_reasons(scope[1]).update(
                    lineage.reason_codes
                )
                for event in lineage.excluded:
                    exclude(event, *lineage.reason_codes)
                continue
            leaves.extend(lineage.leaves)

        leaves_by_type: dict[str, list] = {}
        listing_state_by_security: dict[
            str,
            tuple[str, datetime],
        ] = {}
        for event in sorted(
            leaves,
            key=lambda item: (
                item.security_id,
                item.effective_at,
                item.event_row_id,
            ),
        ):
            leaves_by_type.setdefault(event.event_type, []).append(event)
            reasons: set[str] = set()
            policy = manifest.corporate_action_policy.get(
                event.event_type
            )
            if policy == "unsupported":
                reasons.add("corporate_action_policy_unsupported")
            if event.event_type in {"split", "reverse_split"} and (
                event.ratio_numerator is None
                or event.ratio_denominator is None
            ):
                reasons.add("corporate_action_ratio_required")
            if (
                event.event_type
                in {"merger", "acquisition", "spinoff"}
                and not event.successor_security_id
            ):
                reasons.add("corporate_action_successor_required")
            if (
                event.event_type == "delisting"
                and event.listing_state_after != "delisted"
            ):
                reasons.add("delisting_state_invalid")
            if (
                event.event_type == "suspension"
                and event.listing_state_after != "suspended"
            ):
                reasons.add("delisting_transition_invalid")
            if event.event_type == "reactivation":
                prior_listing_state = listing_state_by_security.get(
                    event.security_id
                )
                if (
                    event.listing_state_after != "active"
                    or prior_listing_state is None
                    or prior_listing_state[0] != "suspended"
                    or prior_listing_state[1] >= event.effective_at
                ):
                    reasons.add("delisting_transition_invalid")
            if event.listing_state_after:
                listing_state_by_security[event.security_id] = (
                    event.listing_state_after,
                    event.effective_at,
                )
            if reasons:
                target_reasons(event.event_type).update(reasons)
                exclude(event, *reasons)

        for event_type, state in (
            manifest.corporate_action_policy.items()
        ):
            if state != "required" or leaves_by_type.get(event_type):
                continue
            if event_type in listing_state_event_types:
                delisting_reasons.add("delisting_evidence_missing")
            else:
                action_reasons.add(
                    "corporate_action_evidence_missing"
                )
        delisting_applicable = (
            delisting_applicable
            or any(
                event.event_type in listing_state_event_types
                for event in leaves
            )
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
            _row_number(parsed, "events", row_id),
            row_id,
            tuple(sorted(reasons)),
        )
        for row_id, reasons in sorted(exclusion_reasons.items())
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


def _rights_decision(manifest, parsed, registry) -> Decision:
    blockers: set[str] = set()
    for source_id in sorted(
        {
            row.source_id
            for rows in (
                parsed.identities,
                parsed.memberships,
                parsed.events,
            )
            for row in rows
        }
    ):
        if source_id not in manifest.allowed_source_ids:
            blockers.add("source_rights_source_not_allowed")
        required: set[str] = set()
        if any(row.source_id == source_id for row in parsed.identities):
            required.add("security_identity")
        if any(row.source_id == source_id for row in parsed.memberships):
            required.add("universe_membership")
        source_events = tuple(
            row for row in parsed.events if row.source_id == source_id
        )
        if any(row.event_type != "delisting" for row in source_events):
            required.add("corporate_actions")
        if any(row.event_type == "delisting" for row in source_events):
            required.add("delistings")
        review = review_commercial_field_scope(
            registry,
            source_id,
            tuple(sorted(required)),
        )
        if not review.commercial_rights_approved:
            blockers.add(f"source_rights_{review.rights_status}")
        if review.missing_supported_fields:
            blockers.add("source_rights_field_scope_missing")
    return Decision(
        "source_rights_eligibility",
        "blocked" if blockers else "passed",
        tuple(sorted(blockers)),
    )


def validate_point_in_time_universe(
    manifest_path: Path,
    registry_path: Path,
    *,
    top_n: int = 20,
) -> PointInTimeUniversePacket:
    if (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or top_n < 0
    ):
        raise ValueError("top_n_invalid")

    package = load_universe_package(manifest_path, registry_path)
    parsed = parse_universe_evidence(package)
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
    identity, membership, digests, display, composed_excluded = (
        _identity_membership_decisions(package.manifest, parsed)
    )
    decisions[identity.area] = identity
    decisions[membership.area] = membership
    excluded.extend(composed_excluded)
    temporal, cutoff_leakage, temporal_excluded = _temporal_decision(
        package.manifest,
        parsed
    )
    decisions[temporal.area] = temporal
    excluded.extend(temporal_excluded)
    corporate_action, delisting, event_excluded = _event_decisions(
        package.manifest,
        parsed,
    )
    source_rights = _rights_decision(
        package.manifest,
        parsed,
        parse_source_rights_registry(package.registry_snapshot),
    )
    decisions[corporate_action.area] = corporate_action
    decisions[delisting.area] = delisting
    decisions[source_rights.area] = source_rights
    excluded.extend(event_excluded)
    reproduction = _reproduction_decision(
        package.manifest,
        digests,
        parsed.evaluations,
    )
    decisions[reproduction.area] = reproduction
    leakage, partition_excluded = _partition_validation(
        package.manifest,
        parsed.evaluations,
        cutoff_leakage,
        parsed,
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

    return PointInTimeUniversePacket(
        dataset_id=package.manifest.dataset_id,
        manifest_id=package.manifest.manifest_id,
        analysis_eligible=_final_eligibility(
            ordered_decisions,
            digests,
            package.manifest.declared_universes,
        ),
        decisions=ordered_decisions,
        raw_count=len(parsed.raw),
        normalized_count=sum(
            (
                len(parsed.identities),
                len(parsed.memberships),
                len(parsed.events),
                len(parsed.evaluations),
            )
        ),
        excluded=canonical_excluded[:top_n],
        membership_digests=digests,
        display_tickers=display,
        boundary=(
            "Local evidence eligibility only; no readiness, backtest, probability, "
            "recommendation, or trading activation."
        ),
    )


def render_status(packet: PointInTimeUniversePacket) -> str:
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
        f"dataset_id: {packet.dataset_id}",
        f"manifest_id: {packet.manifest_id}",
        f"analysis_eligible: {str(packet.analysis_eligible).lower()}",
    ]
    lines.extend(
        (
            f"{name}: {packet.decisions[name].status}; "
            f"reasons={','.join(packet.decisions[name].reason_codes) or 'none'}"
        )
        for name in DECISION_ORDER
    )
    lines.append(f"boundary: {packet.boundary}")
    return "\n".join(lines)


def render_preview(
    packet: PointInTimeUniversePacket,
    *,
    top_n: int = 20,
) -> str:
    if (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or top_n < 0
    ):
        raise ValueError("top_n_invalid")

    lines = [render_status(packet), "", "Membership reproduction:"]
    lines.extend(
        (
            f"- {item.universe_id} @ {item.evaluation_at}: "
            f"members={item.member_count}; sha256={item.sha256}"
        )
        for item in packet.membership_digests
    )
    lines.append("Excluded sample:")
    lines.extend(
        (
            f"- {item.contract}:{item.source_row}:{item.row_id}; "
            f"reasons={','.join(item.reason_codes)}"
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
    if args.top_n < 0:
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
