"""Fail-closed evidence quality for trusted peer relationships."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


ALLOWED_PEER_ROLES = frozenset(
    {
        "core_peer",
        "secondary_peer",
        "aspirational_peer",
        "negative_peer",
        "excluded_close_peer",
        "not_clean_comp",
    }
)
VALUATION_ANCHOR_ROLES = frozenset({"core_peer", "secondary_peer"})
_YES_VALUES = frozenset({"1", "true", "yes", "eligible"})
_NO_VALUES = frozenset({"0", "false", "no", "withheld", "context_only"})


@dataclass(frozen=True)
class PeerEvidenceQuality:
    peer_role: str
    relationship_state: str
    role_state: str
    comparability_state: str
    valuation_anchor_state: str
    blockers: tuple[str, ...]


def _text(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def assess_peer_evidence(row: Mapping[str, object]) -> PeerEvidenceQuality:
    """Classify one relationship without inferring missing review evidence."""

    role = _text(row.get("peer_role")).lower()
    source = _text(row.get("source"))
    as_of_date = _text(row.get("as_of_date"))
    rationale = _text(row.get("relationship_rationale"))
    comparability_basis = _text(row.get("comparability_basis"))
    anchor_decision = _text(row.get("valuation_anchor_eligible")).lower()
    candidate_state = _text(row.get("candidate_state")).lower()

    if candidate_state:
        return PeerEvidenceQuality(
            peer_role=role or "unreviewed",
            relationship_state="candidate_context_only",
            role_state="reviewed_role" if role in ALLOWED_PEER_ROLES else "unreviewed_role",
            comparability_state="context_only",
            valuation_anchor_state="withheld",
            blockers=("candidate_context_not_trusted",),
        )

    blockers: list[str] = []
    if not source:
        blockers.append("relationship_source_missing")
    if not as_of_date:
        blockers.append("relationship_as_of_missing")
    relationship_state = "source_backed" if source and as_of_date else "provenance_missing"

    if not role:
        role_state = "unreviewed_role"
        blockers.append("peer_role_missing")
    elif role not in ALLOWED_PEER_ROLES:
        role_state = "invalid_role"
        blockers.append("peer_role_invalid")
    else:
        role_state = "reviewed_role"

    if not rationale:
        blockers.append("relationship_rationale_missing")
    if not comparability_basis:
        blockers.append("comparability_basis_missing")

    if not anchor_decision:
        blockers.append("valuation_anchor_decision_missing")
    elif anchor_decision not in _YES_VALUES | _NO_VALUES:
        blockers.append("valuation_anchor_decision_invalid")
    elif anchor_decision in _NO_VALUES:
        blockers.append("valuation_anchor_explicitly_withheld")
    elif role_state == "reviewed_role" and role not in VALUATION_ANCHOR_ROLES:
        blockers.append("peer_role_not_anchor_eligible")

    anchor_ready = not blockers
    if role_state == "reviewed_role" and role not in VALUATION_ANCHOR_ROLES:
        comparability_state = "context_only"
    elif anchor_decision in _NO_VALUES and rationale and comparability_basis:
        comparability_state = "context_only"
    elif role_state == "reviewed_role" and rationale and comparability_basis:
        comparability_state = "reviewed_comparable"
    else:
        comparability_state = "unreviewed"

    return PeerEvidenceQuality(
        peer_role=role or "unreviewed",
        relationship_state=relationship_state,
        role_state=role_state,
        comparability_state=comparability_state,
        valuation_anchor_state="eligible" if anchor_ready else "withheld",
        blockers=tuple(blockers),
    )


def is_valuation_anchor_eligible(row: Mapping[str, object]) -> bool:
    return assess_peer_evidence(row).valuation_anchor_state == "eligible"
