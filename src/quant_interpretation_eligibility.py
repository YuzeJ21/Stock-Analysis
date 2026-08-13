"""Fail-closed evidence eligibility for quantitative research interpretation."""

from dataclasses import dataclass
from datetime import date


INTERPRETATION_BOUNDARY = (
    "Research interpretation only; this does not change readiness, create a "
    "forecast or probability, rank a company, or provide an investment action."
)

_FAMILIES = frozenset({"valuation", "indicator", "review_metric"})
_CALCULATION_STATES = frozenset({"available", "partial", "unavailable", "excluded"})
_OBSERVATION_STATES = frozenset({"current", "stale_review_only", "unavailable"})
_PROVENANCE_STATES = frozenset({"verified", "unverified", "missing", "invalid"})
_RIGHTS_STATES = frozenset({"permitted", "unverified", "restricted", "not_applicable"})


@dataclass(frozen=True)
class QuantEvidenceAssessment:
    family: str
    scope: str
    calculation_state: str
    observation_state: str
    observation_through_date: str
    provenance_state: str
    rights_state: str
    field_scope_state: str
    evidence_notes: tuple[str, ...]

    def validate(self) -> None:
        _validate_token("family", self.family, _FAMILIES)
        _validate_nonempty("scope", self.scope)
        _validate_token("calculation_state", self.calculation_state, _CALCULATION_STATES)
        _validate_token("observation_state", self.observation_state, _OBSERVATION_STATES)
        _validate_token("provenance_state", self.provenance_state, _PROVENANCE_STATES)
        _validate_token("rights_state", self.rights_state, _RIGHTS_STATES)
        _validate_token("field_scope_state", self.field_scope_state, _RIGHTS_STATES)


@dataclass(frozen=True)
class QuantInterpretationEligibility:
    family: str
    scope: str
    interpretation_state: str
    commercial_eligible: bool
    reasons: tuple[str, ...]
    summary: str
    boundary: str


def evaluate_quant_interpretation(
    assessment: QuantEvidenceAssessment,
) -> QuantInterpretationEligibility:
    """Return a separate, research-only decision without modifying assessment data."""
    assessment.validate()
    reasons = _ordered_reasons(assessment)
    if _must_withhold(assessment):
        state = "withheld"
    elif _can_be_current(assessment):
        state = "current_context_eligible"
    else:
        state = "historical_review_only"
    return QuantInterpretationEligibility(
        family=assessment.family,
        scope=assessment.scope,
        interpretation_state=state,
        commercial_eligible=(
            state == "current_context_eligible"
            and assessment.rights_state == "permitted"
            and assessment.field_scope_state == "permitted"
        ),
        reasons=reasons,
        summary=_summary(state, assessment.observation_through_date),
        boundary=INTERPRETATION_BOUNDARY,
    )


def _validate_nonempty(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_token(name: str, value: object, allowed: frozenset[str]) -> None:
    if not isinstance(value, str) or not value or value not in allowed:
        raise ValueError(f"{name} has an unsupported value")


def _ordered_reasons(assessment: QuantEvidenceAssessment) -> tuple[str, ...]:
    candidates = (
        {
            "partial": "calculation_partial",
            "unavailable": "calculation_unavailable",
            "excluded": "calculation_excluded",
        }.get(assessment.calculation_state),
        {
            "stale_review_only": "observation_stale",
            "unavailable": "observation_unavailable",
        }.get(assessment.observation_state),
        {
            "unverified": "provenance_unverified",
            "missing": "provenance_missing",
            "invalid": "provenance_invalid",
        }.get(assessment.provenance_state),
        {
            "unverified": "rights_unverified",
            "restricted": "rights_restricted",
        }.get(assessment.rights_state),
        {
            "unverified": "field_scope_unverified",
            "restricted": "field_scope_restricted",
        }.get(assessment.field_scope_state),
    )
    if _observation_is_rejected(assessment):
        candidates = ("observation_unavailable",) + candidates
    return tuple(dict.fromkeys(reason for reason in candidates if reason is not None))


def _must_withhold(assessment: QuantEvidenceAssessment) -> bool:
    return (
        assessment.calculation_state in {"unavailable", "excluded"}
        or assessment.observation_state == "unavailable"
        or _observation_is_rejected(assessment)
        or assessment.provenance_state == "invalid"
        or assessment.rights_state == "restricted"
        or assessment.field_scope_state == "restricted"
    )


def _observation_is_rejected(assessment: QuantEvidenceAssessment) -> bool:
    if assessment.observation_state == "unavailable":
        return False
    try:
        return date.fromisoformat(assessment.observation_through_date) > date.today()
    except (TypeError, ValueError):
        return True


def _can_be_current(assessment: QuantEvidenceAssessment) -> bool:
    return (
        assessment.calculation_state == "available"
        and assessment.observation_state == "current"
        and assessment.provenance_state == "verified"
        and assessment.rights_state in {"permitted", "not_applicable"}
        and assessment.field_scope_state in {"permitted", "not_applicable"}
    )


def _summary(state: str, observation_through_date: str) -> str:
    if state == "current_context_eligible":
        return f"Current research context eligible through {observation_through_date}."
    if state == "historical_review_only":
        return f"Historical review only through {observation_through_date}."
    return "Interpretation withheld pending eligible quantitative evidence."
