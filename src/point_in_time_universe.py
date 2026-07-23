from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from src.point_in_time_universe_contracts import (
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
    display: dict[str, str] = {}
    cutoff = parse_utc(manifest.observation_cutoff_at)
    evaluations = tuple(
        item for item in parsed.evaluations if item.evaluation_at <= cutoff
    )

    for row in parsed.memberships:
        expected_kind = declared.get(row.universe_id)
        if expected_kind is None:
            membership_reasons.add("membership_universe_undeclared")
        elif row.universe_kind != expected_kind:
            membership_reasons.add("membership_universe_kind_mismatch")

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
                available_at=lambda row: max(
                    row.observation_at,
                    row.source_published_at,
                    row.retrieved_at,
                ),
                cutoff=evaluation.evaluation_at,
            )
            membership_reasons.update(lineage.reason_codes)
            for leaf in lineage.leaves:
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

                identity_rows = tuple(
                    row
                    for row in parsed.identities
                    if row.security_id == security_id
                )
                identity_lineage = resolve_lineage(
                    identity_rows,
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

                available_identity_rows = tuple(
                    row
                    for row in identity_rows
                    if max(row.source_published_at, row.retrieved_at)
                    <= evaluation.evaluation_at
                )
                active = tuple(
                    row
                    for row in available_identity_rows
                    if _contains(
                        row.valid_from,
                        row.valid_to,
                        evaluation.evaluation_at,
                    )
                )
                if not active:
                    identity_reasons.add("identity_missing")
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
                if len(active) != 1:
                    identity_reasons.add("identity_interval_overlap")
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

                members.add(security_id)
                display[security_id] = active[0].ticker

        if not members:
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
    if not evaluations:
        membership_reasons.add("membership_no_evaluation")

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
        tuple(digests),
        MappingProxyType(display),
        tuple(excluded),
    )


def validate_point_in_time_universe(
    manifest_path: Path,
    registry_path: Path,
    *,
    top_n: int = 20,
) -> PointInTimeUniversePacket:
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

    return PointInTimeUniversePacket(
        dataset_id=package.manifest.dataset_id,
        manifest_id=package.manifest.manifest_id,
        analysis_eligible=False,
        decisions=MappingProxyType(decisions),
        raw_count=len(parsed.raw),
        normalized_count=sum(
            (
                len(parsed.identities),
                len(parsed.memberships),
                len(parsed.events),
                len(parsed.evaluations),
            )
        ),
        excluded=tuple(excluded[:top_n]),
        membership_digests=digests,
        display_tickers=display,
        boundary=(
            "Local evidence eligibility only; no readiness, backtest, probability, "
            "recommendation, or trading activation."
        ),
    )
